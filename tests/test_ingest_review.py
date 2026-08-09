from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.ingest_review import (
    COMMENT_STATUS_VALUES,
    ingest_review,
)


ROOT = Path(__file__).resolve().parents[1]

_MODEL = {
    "schema_version": "1.0",
    "document_id": "minimal-design-doc",
    "title": "Minimal Design Doc",
    "generated_at": "2026-05-17T00:00:00+09:00",
    "blocks": [
        {
            "id": "overview",
            "type": "section",
            "content": "A minimal section for future renderer tests.",
        }
    ],
}


class IngestReviewStateTest(unittest.TestCase):
    def test_state_records_status_counts_and_ids_without_writing_replies(self) -> None:
        """取り込みが status の集計と id の記録だけを行うことを見張る。

        壊れたら起きる不都合: 誰の番かの記録が state から落ち、返信すべき
        スレッドを agent が見つけられなくなる。または勝手な返信が書き込まれる。
        期待値の出所: 承認済み plan の state v2 定義。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(
                root,
                [
                    _thread("cmt-waiting", "overview", "minimal section", "これはどういう意味?"),
                    _thread("cmt-answered", "overview", "text", "何の話?", status="needs_user_reply"),
                    _thread("cmt-done", "overview", "text", "直した", status="resolved"),
                ],
            )

            result = ingest_review(root)

            self.assertEqual(result.payload["summary"]["total"], 3)
            self.assertEqual(result.payload["summary"]["needs_agent_review"], 1)
            self.assertEqual(result.payload["summary"]["needs_user_reply"], 1)
            self.assertEqual(result.payload["summary"]["resolved"], 1)
            self.assertEqual(result.payload["summary"]["replies_added"], 0)
            self.assertEqual(result.payload["gate"]["gate"], "blocked")
            self.assertEqual(result.payload["gate"]["needs_agent_review_threads"], ["cmt-waiting"])

            comments = json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))
            waiting = _find_thread(comments, "cmt-waiting")
            self.assertEqual(waiting["status"], "needs_agent_review")
            self.assertEqual(waiting["replies"], [])

            state = json.loads((root / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["schema_version"], "2.0")
            self.assertEqual(state["needs_agent_review_ids"], ["cmt-waiting"])
            self.assertEqual(state["resolved_ids"], ["cmt-done"])

    def test_comment_status_values_are_the_three_ui_states(self) -> None:
        self.assertEqual(
            set(COMMENT_STATUS_VALUES), {"needs_agent_review", "needs_user_reply", "resolved"}
        )


class ApplyModelTest(unittest.TestCase):
    def test_apply_model_uses_limited_exact_replacement_on_resolved_thread(self) -> None:
        """解決済みスレッドの機械置換だけが文書へ反映されることを見張る。

        壊れたら起きる不都合: 合意した文言修正が反映されないまま「反映済み」と
        報告される。期待値の出所: 承認済み plan の反映候補 = status=resolved。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "document-model.json"
            model_path.write_text(json.dumps(_MODEL), encoding="utf-8")
            _write_comments(
                root,
                [
                    _thread(
                        "cmt-replace",
                        "overview",
                        "future renderer tests",
                        'Replace "future renderer tests" with "review workflow checks".',
                        status="resolved",
                    )
                ],
            )

            result = ingest_review(root, model_path=model_path, apply_model=True)

            model = json.loads(model_path.read_text(encoding="utf-8"))
            self.assertEqual(model["blocks"][0]["content"], "A minimal section for review workflow checks.")
            self.assertEqual(result.payload["model_updates"]["applied"], 1)
            self.assertEqual(result.payload["summary"]["replies_added"], 1)
            comments = json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))
            applied = _find_thread(comments, "cmt-replace")
            self.assertEqual(applied["replies"][0]["kind"], "implementation_note")

    def test_model_unchanged_while_a_thread_awaits_agent_reply(self) -> None:
        """返信待ちが残る間は文書を書き換えないことを見張る。

        壊れたら起きる不都合: ユーザーの差し戻しに答えないまま資料だけが
        書き換わり、返信 → 反映の順序が崩れる。
        期待値の出所: 承認済み plan「needs_agent_review が残る間は apply しない」。
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "document-model.json"
            model_path.write_text(json.dumps(_MODEL), encoding="utf-8")
            _write_comments(
                root,
                [
                    _thread(
                        "cmt-replace",
                        "overview",
                        "future renderer tests",
                        'Replace "future renderer tests" with "review workflow checks".',
                        status="resolved",
                    ),
                    _thread("cmt-waiting", "overview", "text", "これはまだ答えて無い"),
                ],
            )

            result = ingest_review(root, model_path=model_path, apply_model=True)

            model = json.loads(model_path.read_text(encoding="utf-8"))
            self.assertEqual(model["blocks"][0]["content"], _MODEL["blocks"][0]["content"])
            self.assertEqual(result.payload["model_updates"]["applied"], 0)
            self.assertEqual(result.payload["gate"]["gate"], "blocked")

    def test_ingest_review_uses_unknown_gate_payload_when_gate_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-action", "overview", "text", "Fix this.")])

            from unittest.mock import patch

            with patch("scripts.html_review_workbench.resolution_gate.try_check_gate", return_value=None):
                result = ingest_review(root)

            self.assertEqual(result.payload["gate"], {"gate": "unknown"})


def _write_comments(root: Path, threads: list[dict[str, object]]) -> None:
    annotations = root / "annotations"
    annotations.mkdir(parents=True)
    payload = {"schema_version": "1.0", "document_id": "minimal-design-doc", "comments": threads}
    (annotations / "comments.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _thread(
    thread_id: str,
    block_id: str,
    selected_text: str,
    comment: str,
    *,
    status: str = "needs_agent_review",
) -> dict[str, object]:
    return {
        "id": thread_id,
        "document_id": "minimal-design-doc",
        "block_id": block_id,
        "selected_text": selected_text,
        "prefix": "",
        "suffix": "",
        "comment": comment,
        "status": status,
        "created_at": "2026-05-17T00:00:00+00:00",
        "replies": [],
    }


def _find_thread(payload: dict[str, object], thread_id: str) -> dict[str, object]:
    for thread in payload["comments"]:
        if isinstance(thread, dict) and thread["id"] == thread_id:
            return thread
    raise AssertionError(f"missing thread: {thread_id}")


if __name__ == "__main__":
    unittest.main()
