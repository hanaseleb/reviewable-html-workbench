from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
import urllib.request
from pathlib import Path
from types import SimpleNamespace

from scripts.html_review_workbench.plan_preview import (
    MARKER_FILE,
    PLAN_PREVIEW_SENTINEL_DIR_NAME,
    ROOT_PREFIX,
    PlanPreviewError,
    _remove_plan_preview_sentinel,
    build_plan_preview_model,
    create_plan_preview,
    read_payload,
    stop_plan_preview,
    validate_plan_preview_payload,
)
from scripts.html_review_workbench.render import render_bundle


class PlanPreviewTest(unittest.TestCase):
    def test_build_plan_preview_model_preserves_source_section_order_and_inserts_diagram(self) -> None:
        model = build_plan_preview_model(validate_plan_preview_payload(_payload()), "abc123")

        self.assertEqual(model["document_id"], "plan-preview-abc123")
        self.assertEqual(model["title"], "Plan Preview Test")
        self.assertEqual(model["summary"], "Proposed plan preview (original structure preserved).")
        blocks = model["blocks"]
        self.assertEqual(
            [block.get("title") for block in blocks],
            ["Context", "実装手順", "処理フロー", "検証"],
        )
        self.assertEqual([block["id"] for block in blocks], ["plan-section-1", "plan-section-2", "plan-diagram-1", "plan-section-3"])
        self.assertNotIn("type=\"code\"", json.dumps(blocks))
        section = blocks[1]
        self.assertEqual(section["type"], "html")
        self.assertEqual(section["heading_level"], 2)
        self.assertIn("<li>CLIで本文をHTML化する。</li>", section["content"])
        diagram = blocks[2]
        self.assertEqual(
            diagram,
            {
                "id": "plan-diagram-1",
                "type": "diagram",
                "heading_level": 3,
                "title": "処理フロー",
                "content": "flowchart TD\n  source --> html",
                "review_required": True,
            },
        )

    def test_build_plan_preview_model_uses_first_matching_duplicate_heading(self) -> None:
        payload = validate_plan_preview_payload(
            {
                "source_text": "\n".join(
                    [
                        "# Duplicate",
                        "",
                        "## Phase",
                        "first",
                        "",
                        "## Phase",
                        "second",
                    ]
                ),
                "diagrams": [{"after_heading": "Phase", "mermaid": "flowchart TD\n  a --> b"}],
            }
        )
        model = build_plan_preview_model(payload, "dup")

        self.assertEqual([block["id"] for block in model["blocks"]], ["plan-section-1", "plan-diagram-1", "plan-section-2"])
        self.assertIn("first", model["blocks"][0]["content"])

    def test_build_plan_preview_model_allows_diagram_after_subheading(self) -> None:
        payload = validate_plan_preview_payload(
            {
                "source_text": "\n".join(
                    [
                        "# Plan",
                        "",
                        "## Parent",
                        "intro",
                        "",
                        "### Child",
                        "detail",
                    ]
                ),
                "diagrams": [{"after_heading": "Child", "mermaid": "flowchart TD\n  a --> b"}],
            }
        )
        model = build_plan_preview_model(payload, "sub")

        self.assertEqual([block["id"] for block in model["blocks"]], ["plan-section-1", "plan-diagram-1"])

    def test_create_plan_preview_local_mode_returns_localhost_temp_url_and_cleans_up(self) -> None:
        result = create_plan_preview(_payload(), ttl=60, mode="local")
        try:
            self.assertTrue(result.url.startswith("http://127.0.0.1:"), result.url)
            self.assertTrue(result.root.name.startswith(ROOT_PREFIX), result.root)
            self.assertEqual(result.root.parent, Path(tempfile.gettempdir()).resolve())
            self.assertTrue((result.root / MARKER_FILE).exists())
            self.assertTrue((result.root / "document-model.json").exists())
            self.assertTrue((result.root / "renderer-manifest.json").exists())
            self.assertIn("plan-preview-stop", result.stop_command)

            with urllib.request.urlopen(result.url, timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Plan Preview Test", html)
            self.assertIn("<h2>Context</h2>", html)
            self.assertIn("<h2>実装手順</h2>", html)
            self.assertIn("CLIで本文をHTML化する。", html)
            self.assertNotIn("Original Plan Text", html)
        finally:
            if result.root.exists():
                stop_plan_preview(result.root, result.pid, result.process, result.cleanup_process)
        self.assertFalse(result.root.exists())

    def test_rendered_html_does_not_create_javascript_links_or_raw_html_tags(self) -> None:
        model = build_plan_preview_model(
            validate_plan_preview_payload(
                {
                    "source_text": "\n".join(
                        [
                            "# Safety",
                            "",
                            "## Links",
                            "[bad](javascript:alert(1)) and [ok](https://example.com)",
                            "",
                            "<script>alert(1)</script>",
                        ]
                    )
                }
            ),
            "safe",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model_path = root / "document-model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            render_bundle(model_path, root)
            html = (root / "index.html").read_text(encoding="utf-8")

        self.assertNotIn('href="javascript:alert(1)"', html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn('href="https://example.com"', html)

    def test_create_plan_preview_auto_mode_can_return_tailscale_url(self) -> None:
        seen: dict[str, object] = {}

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            seen["root"] = root
            seen["mode"] = mode
            seen["idle_timeout"] = idle_timeout
            return SimpleNamespace(
                url="http://100.64.12.34:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        result = create_plan_preview(
            _payload(),
            ttl=60,
            mode="auto",
            preview_starter=fake_start_preview,
            cleanup_starter=lambda root, pid, ttl: None,
        )
        try:
            self.assertEqual(result.url, "http://100.64.12.34:54321/index.html")
            self.assertEqual(seen["mode"], "auto")
            self.assertEqual(seen["idle_timeout"], 60)
        finally:
            if result.root.exists():
                stop_plan_preview(result.root)

    def test_create_plan_preview_writes_claude_session_sentinel(self) -> None:
        old_session_id = os.environ.get("CLAUDE_SESSION_ID")
        session_id = f"test-plan-preview-{os.getpid()}"
        os.environ["CLAUDE_SESSION_ID"] = session_id
        _remove_plan_preview_sentinel()
        result = None

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        try:
            result = create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
            )
            sentinel = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME / session_id
            payload = json.loads(sentinel.read_text(encoding="utf-8"))
            self.assertEqual(payload["preview_id"], result.id)
            self.assertIsInstance(payload["created_at"], str)
            self.assertTrue(payload["created_at"])
        finally:
            _remove_plan_preview_sentinel()
            if old_session_id is None:
                os.environ.pop("CLAUDE_SESSION_ID", None)
            else:
                os.environ["CLAUDE_SESSION_ID"] = old_session_id
            if result is not None and result.root.exists():
                stop_plan_preview(result.root)

    def test_create_plan_preview_does_not_write_sentinel_without_claude_session_id(self) -> None:
        old_session_id = os.environ.pop("CLAUDE_SESSION_ID", None)
        sentinel_dir = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME
        before = set(sentinel_dir.iterdir()) if sentinel_dir.exists() else set()
        result = None

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        try:
            result = create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
            )
            after = set(sentinel_dir.iterdir()) if sentinel_dir.exists() else set()
            self.assertEqual(after, before)
        finally:
            if old_session_id is not None:
                os.environ["CLAUDE_SESSION_ID"] = old_session_id
            if result is not None and result.root.exists():
                stop_plan_preview(result.root)

    def test_create_plan_preview_validates_bundle_before_starting_preview(self) -> None:
        seen: dict[str, object] = {}

        def fake_start_preview(root: Path, mode: str, idle_timeout: float) -> SimpleNamespace:
            seen["started"] = True
            return SimpleNamespace(
                url="http://127.0.0.1:54321/index.html",
                pid=os.getpid(),
                process=None,
            )

        def fake_validate_bundle(root: Path) -> SimpleNamespace:
            seen["root"] = root
            return SimpleNamespace(ok=False, errors=["missing review blocks"], review_blocks=0)

        with self.assertRaisesRegex(PlanPreviewError, "bundle validation failed"):
            create_plan_preview(
                _payload(),
                ttl=60,
                mode="local",
                preview_starter=fake_start_preview,
                cleanup_starter=lambda root, pid, ttl: None,
                bundle_validator=fake_validate_bundle,
            )
        self.assertNotIn("started", seen)
        root = seen.get("root")
        self.assertIsInstance(root, Path)
        self.assertFalse(root.exists())

    def test_create_plan_preview_rejects_invalid_payload_before_temp_root_creation(self) -> None:
        temp_root = Path(tempfile.gettempdir()).resolve()
        before = {path for path in temp_root.glob(f"{ROOT_PREFIX}*") if path.is_dir()}
        with self.assertRaisesRegex(PlanPreviewError, "source_text"):
            create_plan_preview({"title": "missing source"}, ttl=60, mode="local")
        after = {path for path in temp_root.glob(f"{ROOT_PREFIX}*") if path.is_dir()}
        self.assertEqual(after, before)

    def test_validate_plan_preview_payload_rejects_unknown_keys_and_old_aliases(self) -> None:
        for key in ["summary", "phases", "key_changes", "flow", "sections", "test_plan", "assumptions", "visual_notes"]:
            with self.subTest(key=key):
                with self.assertRaisesRegex(PlanPreviewError, "unsupported key"):
                    validate_plan_preview_payload({"source_text": "# Plan", key: "old"})
        for key in ["proposed_plan", "plan_text", "full_text"]:
            with self.subTest(key=key):
                with self.assertRaisesRegex(PlanPreviewError, "unsupported key"):
                    validate_plan_preview_payload({key: "# Plan"})

    def test_build_plan_preview_model_rejects_missing_diagram_heading(self) -> None:
        payload = validate_plan_preview_payload(
            {
                "source_text": "# Plan\n\n## Existing\nbody",
                "diagrams": [{"after_heading": "Missing", "mermaid": "flowchart TD\n  a --> b"}],
            }
        )

        with self.assertRaisesRegex(PlanPreviewError, "after_heading not found"):
            build_plan_preview_model(payload, "missing")

    def test_read_payload_rejects_remote_assets(self) -> None:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            json.dump({"title": "bad", "remote_asset_urls": ["https://example.com/a.png"]}, tmp)
            tmp_path = Path(tmp.name)
        try:
            with self.assertRaisesRegex(PlanPreviewError, "remote_asset_urls"):
                read_payload(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_stop_refuses_unmarked_temp_root(self) -> None:
        root = Path(tempfile.mkdtemp(prefix=ROOT_PREFIX)).resolve()
        try:
            with self.assertRaisesRegex(PlanPreviewError, "refusing to clean unmarked"):
                stop_plan_preview(root)
            self.assertTrue(root.exists())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_create_plan_preview_rejects_non_positive_ttl(self) -> None:
        with self.assertRaisesRegex(PlanPreviewError, "ttl must be positive"):
            create_plan_preview(_payload(), ttl=0)


def _payload() -> dict[str, object]:
    return {
        "title": "Plan Preview Test",
        "source_text": "\n".join(
            [
                "# Plan Preview Test",
                "",
                "## Context",
                "CLI側で `source_text` を変換する。",
                "",
                "## 実装手順",
                "",
                "- CLIで本文をHTML化する。",
                "- 図は指定章の直後へ挿入する。",
                "",
                "## 検証",
                "",
                "1. unit test",
                "2. local preview",
            ]
        ),
        "diagrams": [
            {
                "after_heading": "実装手順",
                "title": "処理フロー",
                "mermaid": "flowchart TD\n  source --> html",
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
