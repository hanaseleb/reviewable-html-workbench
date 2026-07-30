"""作業チェックリスト asset の bundle 組み込みと publish inline 化のテスト。"""

from __future__ import annotations

import json
import os
import shutil
import socket
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts.html_review_workbench.cli import build_parser
from scripts.html_review_workbench.preview_server import start_preview
from scripts.html_review_workbench.publish import publish_bundle
from scripts.html_review_workbench.render import render_bundle

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"
CHECKLIST_JS = TEMPLATE_DIR / "assets" / "task-checklist.js"


def _write_model(model_path: Path, *, with_checkbox: bool) -> None:
    """チェックボックスの有無だけが異なる最小の文書モデルを書き出す。"""
    row = (
        '<tr><td><input type="checkbox" data-task-check="A-1"> A-1</td><td>作業</td></tr>'
        if with_checkbox
        else "<tr><td>A-1</td><td>作業</td></tr>"
    )
    model = {
        "schema_version": "1.0",
        "document_id": "checklist-test",
        "title": "チェックリスト検証",
        "summary": "チェックボックスの組み込みを検証する。",
        "generated_at": "2026-07-27T00:00:00+09:00",
        "review_settings": {"enabled": True, "mode": "review-server"},
        "blocks": [
            {
                "id": "tasks",
                "type": "html",
                "heading_level": 2,
                "title": "作業",
                "content": f"<table><tbody>{row}</tbody></table>",
            }
        ],
    }
    model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")


def _bundle_with_checkbox(bundle_dir: Path, *, with_checkbox: bool) -> None:
    """publish 入力となる render 済みバンドルの最小構成を作る。"""
    assets_dir = bundle_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_DIR / "style.css", assets_dir / "style.css")
    shutil.copyfile(CHECKLIST_JS, assets_dir / "task-checklist.js")

    cell = (
        '<input type="checkbox" data-task-check="A-1"> A-1'
        if with_checkbox
        else "A-1"
    )
    html = (
        '<!doctype html>\n<html lang="ja" data-theme="light" data-density="compact">\n'
        '<head><meta charset="utf-8"><title>T</title>'
        '<link rel="stylesheet" href="assets/style.css?v=test"></head>\n'
        '<body>\n  <div class="app" data-document-id="checklist-test">\n'
        '    <main class="canvas" id="canvas">\n      <div class="doc-shell">\n'
        '        <div class="doc-grid">\n          <article class="doc-main">\n'
        '            <div class="paper">\n'
        '              <header class="doc-headrow document-header"'
        ' data-review-block="document-header" data-block-type="header"'
        ' data-review-required="false">\n'
        '                <h1 class="doc-title">T</h1>\n              </header>\n'
        '              <div class="prose document-content" id="content">\n'
        '                <section data-review-block="tasks" data-block-type="html"'
        ' data-review-required="true">\n'
        "                  <h2>作業</h2>\n"
        f"                  <table><tbody><tr><td>{cell}</td></tr></tbody></table>\n"
        "                </section>\n              </div>\n"
        "            </div>\n          </article>\n        </div>\n"
        "      </div>\n    </main>\n  </div>\n</body>\n</html>\n"
    )
    (bundle_dir / "index.html").write_text(html, encoding="utf-8")


class ChecklistAssetTest(unittest.TestCase):
    def test_checklist_js_exposes_required_behaviour(self) -> None:
        script = CHECKLIST_JS.read_text(encoding="utf-8")
        for token in [
            "data-task-check",
            "rhw-checklist:",
            "resolveStorage",
            "exportState",
            "importState",
            "applyState",
            "refresh",
        ]:
            self.assertIn(token, script)

    def test_checklist_js_survives_without_local_storage(self) -> None:
        """localStorage が例外を投げる環境でも動くよう try/catch で包んでいること。"""
        script = CHECKLIST_JS.read_text(encoding="utf-8")
        probe_index = script.index("window.localStorage.setItem")
        self.assertIn("try", script[:probe_index])


class ChecklistRenderTest(unittest.TestCase):
    def test_render_bundle_ships_checklist_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "document-model.json"
            _write_model(model_path, with_checkbox=True)
            output = Path(tmpdir) / "out"
            render_bundle(model_path, output)

            self.assertTrue((output / "assets" / "task-checklist.js").is_file())
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("assets/task-checklist.js", html)
            self.assertIn('data-task-check="A-1"', html)

            manifest = json.loads((output / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("assets/task-checklist.js", manifest["outputs"]["assets"])


class ChecklistPublishTest(unittest.TestCase):
    def test_publish_inlines_checklist_when_checkboxes_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / "bundle"
            bundle.mkdir()
            _bundle_with_checkbox(bundle, with_checkbox=True)
            output = Path(tmpdir) / "out"
            publish_bundle(bundle, output)

            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('data-task-check="A-1"', html)
            self.assertIn("rhw-checklist:", html)
            self.assertIn('data-document-id="checklist-test"', html)
            # 外部参照ではなく inline 化されていること
            self.assertNotIn('src="assets/task-checklist.js', html)

    def test_publish_skips_checklist_without_checkboxes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / "bundle"
            bundle.mkdir()
            _bundle_with_checkbox(bundle, with_checkbox=False)
            output = Path(tmpdir) / "out"
            publish_bundle(bundle, output)

            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("rhw-checklist:", html)

    def test_publish_falls_back_to_template_asset(self) -> None:
        """旧 bundle に asset が無くても template 側から inline できること。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            bundle = Path(tmpdir) / "bundle"
            bundle.mkdir()
            _bundle_with_checkbox(bundle, with_checkbox=True)
            (bundle / "assets" / "task-checklist.js").unlink()
            output = Path(tmpdir) / "out"
            publish_bundle(bundle, output)

            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("rhw-checklist:", html)


class ChecklistRemoteStateTest(unittest.TestCase):
    """preview server 経由でチェック状態を共有できることを確かめる。"""

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def test_preview_accepts_fixed_port(self) -> None:
        args = build_parser().parse_args(["preview", "--root", "/tmp/out", "--mode", "local"])
        self.assertEqual(args.port, 0)

        port = self._free_port()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0, port=port)
            try:
                self.assertEqual(session.port, port)
                self.assertEqual(session.url, f"http://127.0.0.1:{port}/index.html")
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_checklist_state_survives_a_new_browser(self) -> None:
        """保存した状態が、別ブラウザ相当の素の GET でも読めること。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            base = f"http://127.0.0.1:{session.port}"
            try:
                payload = {"schema_version": "1.0", "document_id": "d", "state": {"A-0": True}}
                request = urllib.request.Request(
                    f"{base}/annotations/checklist-state.json",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    self.assertEqual(json.loads(response.read())["ok"], True)

                saved = json.loads((root / "annotations" / "checklist-state.json").read_text(encoding="utf-8"))
                self.assertEqual(saved["state"], {"A-0": True})

                with urllib.request.urlopen(f"{base}/annotations/checklist-state.json", timeout=5) as response:
                    self.assertEqual(json.loads(response.read())["state"], {"A-0": True})
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_checklist_state_rejects_payload_without_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{session.port}/annotations/checklist-state.json",
                    data=json.dumps({"state": "not-an-object"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(ctx.exception.code, 400)
                self.assertFalse((root / "annotations" / "checklist-state.json").exists())
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_checklist_js_prefers_server_state_and_falls_back(self) -> None:
        script = CHECKLIST_JS.read_text(encoding="utf-8")
        for token in ["resolveRemoteUrl", "loadRemote", "saveRemote", "persistLocal", "restoreLocal"]:
            self.assertIn(token, script)
        # file:// では保存先が無いので remote を無効にすること
        self.assertIn('window.location.protocol !== "http:"', script)


if __name__ == "__main__":
    unittest.main()
