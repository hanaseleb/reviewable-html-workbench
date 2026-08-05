from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.common import (
    MERMAID_INIT_JS,
    PUBLISH_EXPORT_JS_PATH,
    pid_is_alive,
    resolve_bundle_json_path,
    unique_path,
    write_json,
)


class CommonHelpersTest(unittest.TestCase):
    # write_json call-site mkdir behavior:
    # mkdirあり: comment_store.py:44-48, model_builder.py:39-40,
    # ingest_review.py:134-135, image_assets.py:53-54,
    # preview_server.py:244-246, plan_preview.py:427-435
    # mkdirなし: render.py:105-108, ingest_review.py:274-276,
    # plan_preview.py:96-104

    def test_write_json_preserves_default_no_parent_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "payload.json"

            with self.assertRaises(FileNotFoundError):
                write_json(path, {"status": "ok"})

    def test_write_json_can_create_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "payload.json"

            write_json(path, {"status": "ok"}, ensure_parent=True)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"status": "ok"})

    def test_write_json_can_preserve_compact_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.json"

            write_json(path, {"status": "ok"}, indent=None)

            self.assertEqual(path.read_text(encoding="utf-8"), '{"status": "ok"}\n')

    def test_unique_path_chooses_numbered_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.png"
            path.write_text("one", encoding="utf-8")

            result = unique_path(path, on_exhausted=lambda p: ValueError(f"exhausted: {p}"))

            self.assertEqual(result.name, "asset-2.png")

    def test_resolve_bundle_json_path_preserves_label_in_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "state path must be relative"):
                resolve_bundle_json_path(root, str(root / "state.json"), label="state", error=ValueError)
            with self.assertRaisesRegex(ValueError, "comments path must be a JSON file"):
                resolve_bundle_json_path(root, "comments.txt", label="comments", error=ValueError)

    def test_pid_is_alive_accepts_current_process(self) -> None:
        self.assertTrue(pid_is_alive(os.getpid()))

    def test_pid_is_alive_rejects_reaped_child(self) -> None:
        # A spawned-then-exited process must report not-alive on every platform.
        # On Windows os.kill(pid, 0) raises WinError 87 instead, so this
        # guards the ctypes-based liveness probe.
        import subprocess

        proc = subprocess.Popen([sys.executable, "-c", ""])
        proc.wait()

        self.assertFalse(pid_is_alive(proc.pid))

    def test_pid_is_alive_rejects_non_positive_pids(self) -> None:
        self.assertFalse(pid_is_alive(0))
        self.assertFalse(pid_is_alive(-1))

    def test_mermaid_init_js_follows_page_theme(self) -> None:
        """theme を固定すると、片方の theme で図の文字が紙面と同化して読めなくなる。

        判定基準の出所: 2026-08-05 のユーザー報告 (light 表示で sequence diagram の
        矢印ラベルが薄すぎて読めない = 紙面 light に theme 'dark' の図が乗っていた) と、
        その修正設計 (preview は html[data-theme]、data-theme を持たない公開版は
        prefers-color-scheme を見る)。
        """
        self.assertNotIn("theme: 'dark'", MERMAID_INIT_JS)
        self.assertIn("document.documentElement.dataset.theme", MERMAID_INIT_JS)
        self.assertIn("prefers-color-scheme: dark", MERMAID_INIT_JS)

    def test_mermaid_init_js_keeps_source_for_rerender(self) -> None:
        """source を退避しないと theme 切替後に描き直せず、図だけ前の theme で固まる。

        判定基準の出所: 上と同じ修正設計 (描画で .mermaid の中身が SVG に置換されるため、
        描画前に data-mermaid-source へ退避し、切替時に書き戻して run する)。
        """
        self.assertIn("data-mermaid-source", MERMAID_INIT_JS)
        self.assertIn("__rhwRerenderMermaid", MERMAID_INIT_JS)

    def test_publish_export_js_mermaid_init_matches_common(self) -> None:
        """予備定数がずれると、init script を拾えない経路で書き出した公開版だけ theme が固定される。

        判定基準の出所: publish-export.js の collectMermaidInitScript が
        「既存 init script が取れなければこの定数を使う」実装であること。
        """
        source = PUBLISH_EXPORT_JS_PATH.read_text(encoding="utf-8")
        self.assertIn(MERMAID_INIT_JS, source)


if __name__ == "__main__":
    unittest.main()
