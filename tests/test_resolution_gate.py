"""解決待ちゲートのテスト。

このゲートが守るもの: ユーザーが書いた指摘・差し戻しに agent が返信するまで、
設計反映へ進ませないこと。判定は comments.json の status だけで行う。
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from scripts.html_review_workbench.resolution_gate import check_gate, GateResult
from scripts.html_review_workbench.cli import check_gates


def _write_comments(root: Path, threads: list[dict]) -> None:
    path = root / "annotations" / "comments.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "1.0", "document_id": "doc", "comments": threads}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_thread(
    thread_id: str,
    comment: str,
    status: str = "needs_agent_review",
    replies: list | None = None,
    suffix: str = "",
) -> dict:
    return {
        "id": thread_id,
        "document_id": "doc",
        "block_id": "block-1",
        "selected_text": "some text",
        "suffix": suffix,
        "comment": comment,
        "status": status,
        "created_at": "2026-01-01T00:00:00Z",
        "replies": replies or [],
    }


def _agent_reply(kind: str = "implementation_note") -> dict:
    return {
        "id": "rep-agent",
        "author": "agent",
        "role": "agent",
        "kind": kind,
        "body": "修正しました。",
        "created_at": "2026-01-01T01:00:00Z",
    }


def _user_reply(body: str) -> dict:
    return {
        "id": "rep-user",
        "author": "user",
        "role": "user",
        "kind": "note",
        "body": body,
        "created_at": "2026-01-01T02:00:00Z",
    }


class GateIsDecidedByStatusAloneTest(unittest.TestCase):
    """status だけで gate が決まることを見張る。

    壊れたら起きる不都合: ユーザーの差し戻しが「返信済み」「対応不要」と誤判定され、
    通知にも出ず、ユーザーが催促するまで放置される (2026-08-08 の実事故)。
    期待値の出所: 承認済み plan の gate 定義と、実事故 bundle
    output/2026-08-08_hospital-recognition/annotations/comments.json の 2 スレッド。
    """

    def test_gate_follows_status_regardless_of_body_suffix_or_reply_history(self) -> None:
        cases = [
            # (case 名, thread, 期待 gate)
            (
                "実事故 cmt_msk04ndv: agent が返信した後にユーザーが再指摘した",
                _make_thread(
                    "cmt-redirect",
                    "FTE?",
                    status="needs_agent_review",
                    replies=[
                        _agent_reply(),
                        _user_reply("常勤換算を割くという言葉だと読んでも意味が分からない"),
                    ],
                ),
                "blocked",
            ),
            (
                "実事故 cmt_msk03cbq: 本文側に操作語を含む未返信の質問",
                _make_thread(
                    "cmt-question",
                    "ここで言う公式化の意味は?",
                    status="needs_agent_review",
                    suffix="委員会運営や新人指導に要する時間を勤務表に明示的に確保する。",
                ),
                "blocked",
            ),
            (
                "agent が返信済みでユーザーの応答待ち",
                _make_thread(
                    "cmt-answered",
                    "何の話?",
                    status="needs_user_reply",
                    replies=[_agent_reply(kind="answer")],
                ),
                "open",
            ),
            (
                "解決済み",
                _make_thread("cmt-done", "ここを直して", status="resolved"),
                "open",
            ),
        ]
        for label, thread, expected in cases:
            with self.subTest(label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    _write_comments(root, [thread])
                    self.assertEqual(check_gate(root).gate, expected)

    def test_gate_open_when_no_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [])
            self.assertEqual(check_gate(root).gate, "open")

    def test_strict_cli_gate_requires_every_thread_to_be_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_make_thread("cmt-waiting", "確認してください", status="needs_user_reply")])
            output = io.StringIO()
            with redirect_stdout(output):
                code = check_gates(
                    argparse.Namespace(
                        root=str(root),
                        comments="annotations/comments.json",
                        require_resolved=True,
                    )
                )

            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output.getvalue())["unresolved_threads"], ["cmt-waiting"])

    def test_mixed_threads_report_ids_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [
                _make_thread("cmt-1", "ここを直して", status="resolved"),
                _make_thread("cmt-2", "これはどういう意味?", status="needs_agent_review"),
                _make_thread("cmt-3", "回答済み", status="needs_user_reply"),
            ])
            result = check_gate(root)
            self.assertEqual(result.gate, "blocked")
            self.assertEqual(result.needs_agent_review_threads, ["cmt-2"])
            self.assertEqual(result.resolved_threads, ["cmt-1"])
            self.assertEqual(
                result.status_counts,
                {"needs_agent_review": 1, "needs_user_reply": 1, "resolved": 1},
            )


class GatePayloadContractTest(unittest.TestCase):
    """payload が空でも全 key を出すことを見張る。

    壊れたら起きる不都合: 返信待ちが無い時に payload が {"gate": "open"} だけに縮退し、
    watch-comments の通知行から判断材料が消えて、agent が「自分宛て無し」と読み違える。
    期待値の出所: 承認済み plan「to_payload() は空でも全 key を出す」。
    """

    def test_payload_always_contains_all_keys(self) -> None:
        payload = GateResult(
            gate="open",
            needs_agent_review_threads=[],
            resolved_threads=[],
            status_counts={"needs_agent_review": 0, "needs_user_reply": 0, "resolved": 0},
        ).to_payload()
        self.assertEqual(
            payload,
            {
                "gate": "open",
                "needs_agent_review_threads": [],
                "resolved_threads": [],
                "status_counts": {"needs_agent_review": 0, "needs_user_reply": 0, "resolved": 0},
            },
        )


if __name__ == "__main__":
    unittest.main()
