from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from scripts.html_review_workbench.preview_server import start_preview


ROOT = Path(__file__).resolve().parents[1]


class AddReplyCliTest(unittest.TestCase):
    def test_add_reply_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            result = _run_cli("add-reply", "--root", str(root), "--thread-id", "cmt-1", "--body", "Applied this change.")

            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "ok")
            self.assertEqual(output["thread_id"], "cmt-1")
            self.assertEqual(output["thread_status"], "needs_user_reply")
            self.assertTrue(output["reply_id"].startswith("reply_"))

            thread = _read_comments(root)["comments"][0]
            self.assertEqual(thread["status"], "needs_user_reply")
            self.assertEqual(len(thread["replies"]), 1)
            self.assertEqual(thread["replies"][0]["role"], "agent")
            self.assertEqual(thread["replies"][0]["kind"], "answer")
            self.assertEqual(thread["replies"][0]["body"], "Applied this change.")

    def test_add_reply_reports_thread_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            result = _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "missing-thread",
                "--body",
                "This should not be written.",
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            output = json.loads(result.stdout)
            self.assertEqual(output["status"], "failed")
            self.assertIn("comment thread not found: missing-thread", output["error"])

            thread = _read_comments(root)["comments"][0]
            self.assertEqual(thread["replies"], [])

    def test_add_reply_accepts_custom_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-1")])

            _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "cmt-1",
                "--kind",
                "implementation_note",
                "--body",
                "Implemented by updating the renderer.",
            )

            reply = _read_comments(root)["comments"][0]["replies"][0]
            self.assertEqual(reply["kind"], "implementation_note")
            self.assertEqual(reply["body"], "Implemented by updating the renderer.")

    def test_add_reply_publishes_agent_comment_updated_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            _write_comments(root, [_thread("cmt-1")])

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                with _open_sse(session.url.replace("/index.html", "/events")) as stream:
                    _run_cli(
                        "add-reply",
                        "--root",
                        str(root),
                        "--thread-id",
                        "cmt-1",
                        "--body",
                        "Applied this change.",
                    )

                    event = _read_sse_event(stream)
                self.assertEqual(event["event"], "comment_updated")
                self.assertEqual(event["data"]["source"], "agent")
                self.assertEqual(event["data"]["thread_id"], "cmt-1")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_file_watcher_does_not_rebroadcast_agent_reply(self) -> None:
        """agent が add-reply すると、file_watcher の mtime 再検知が source:"file_watcher"
        で複製イベントを流し、source:"agent" filter を素通りして agent 自身に「新着」
        通知が届く (自分の返信で起こされる)。

        判定基準の出所: 2026-08-06 のユーザー報告 (自分の返信の通知が届いた画面) と
        TASK-19 の決定事項 (通知済みの書き込みは file_watcher が再配信しない。
        通知なしの直接編集は今までどおり配信する)。
        """
        import select

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            _write_comments(root, [_thread("cmt-1")])

            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                with _open_sse(session.url.replace("/index.html", "/events")) as stream:
                    _run_cli("add-reply", "--root", str(root), "--thread-id", "cmt-1", "--body", "self reply")
                    # 1 件目は agent 自身の通知 (これは watch-comments 側で filter される)
                    event = _read_sse_event(stream)
                    self.assertEqual(event["data"]["source"], "agent")

                    # file_watcher の周期 (2s) を跨いでも複製イベントが来ないこと
                    ready, _, _ = select.select([stream], [], [], 3.5)
                    self.assertEqual(ready, [], "file_watcher が agent の書き込みを再配信した")

                    # 通知なしの直接編集 (外部エディタ相当) は今までどおり配信されること
                    payload = _read_comments(root)
                    payload["comments"][0]["comment"] = "edited directly"
                    (root / "annotations/comments.json").write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                    ready, _, _ = select.select([stream], [], [], 4.0)
                    self.assertNotEqual(ready, [], "直接編集が配信されなかった")
                    event = _read_sse_event(stream)
                self.assertEqual(event["data"]["source"], "file_watcher")
            finally:
                self.assertIsNotNone(session.process)
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_add_reply_coexists_with_ingest_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_comments(root, [_thread("cmt-clarify", comment="Which audience should this target?")])

            _run_cli(
                "add-reply",
                "--root",
                str(root),
                "--thread-id",
                "cmt-clarify",
                "--kind",
                "clarification_request",
                "--body",
                "Please specify the target audience.",
            )
            _run_cli("ingest-review", "--root", str(root))

            comments = _read_comments(root)
            self.assertEqual(len(comments["comments"][0]["replies"]), 1)
            self.assertEqual(comments["comments"][0]["status"], "needs_user_reply")

            state = json.loads((root / "annotations/review-cycle-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["summary"]["total"], 1)
            self.assertEqual(state["summary"]["already_addressed"], 1)
            self.assertEqual(state["summary"]["replies_added"], 0)


def _run_cli(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.html_review_workbench.cli", *args],
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def _write_comments(root: Path, threads: list[dict[str, object]]) -> None:
    annotations = root / "annotations"
    annotations.mkdir(parents=True)
    payload = {"schema_version": "1.0", "document_id": "doc-1", "comments": threads}
    (annotations / "comments.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_comments(root: Path) -> dict[str, object]:
    return json.loads((root / "annotations/comments.json").read_text(encoding="utf-8"))


def _open_sse(url: str):
    """SSE の接続を先に開く。

    実運用ではブラウザが先に接続していて、agent が後から通知を publish する。
    接続より前に publish されたイベントは配信対象にならない (履歴を再送すると
    ページを開くたびに過去の通知が再表示されるため) ので、test も同じ順序で書く。
    """
    response = urllib.request.urlopen(url, timeout=10)
    time.sleep(0.3)  # server 側が購読を開始するまで待つ
    return response


def _read_sse_event(response) -> dict[str, object]:
    """開いておいた接続から 1 件読む。"""
    event: dict[str, object] = {}
    data = ""
    while True:
        line = response.readline().decode("utf-8").strip()
        if line == "":
            break
        if line.startswith("id: "):
            event["id"] = line[4:]
        elif line.startswith("event: "):
            event["event"] = line[7:]
        elif line.startswith("data: "):
            data = line[6:]
    event["data"] = json.loads(data)
    return event


def _thread(thread_id: str, *, comment: str = "Please update this section.") -> dict[str, object]:
    return {
        "id": thread_id,
        "document_id": "doc-1",
        "block_id": "overview",
        "selected_text": "selected text",
        "prefix": "",
        "suffix": "",
        "comment": comment,
        "status": "needs_agent_review",
        "created_at": "2026-05-17T00:00:00+00:00",
        "replies": [],
    }


if __name__ == "__main__":
    unittest.main()
