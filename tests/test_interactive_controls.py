"""操作部品 (スライダー・トグル・並べ替え) と状態保存のテスト。

Artifact が CSP 下の inline JavaScript で作れる操作部品を、RHW でも同じように
書けることを確かめる。加えて、触った結果を agent が読める場所へ保存できることを見る。
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from scripts.html_review_workbench.preview_server import start_preview
from scripts.html_review_workbench.publish import publish_bundle
from scripts.html_review_workbench.render import render_bundle

ROOT = Path(__file__).resolve().parents[1]
INTERACTIVE_STATE_JS = ROOT / "templates" / "assets" / "interactive-state.js"

SLIDER_HTML = (
    '<label>duration <input type="range" id="dur" min="0" max="2000" value="300"></label>'
    "<script>document.getElementById('dur').addEventListener('input', function () {"
    "  window.RHWState.save('tuning', {duration: this.value});"
    "});</script>"
)


def _write_model(model_path: Path, *, content: str) -> None:
    model = {
        "schema_version": "1.0",
        "document_id": "interactive-test",
        "title": "操作部品の検証",
        "summary": "操作部品と状態保存の組み込みを検証する。",
        "generated_at": "2026-07-30T00:00:00+09:00",
        "review_settings": {"enabled": True, "mode": "review-server"},
        "blocks": [
            {
                "id": "controls",
                "type": "html",
                "heading_level": 2,
                "title": "操作",
                "content": content,
            }
        ],
    }
    model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")


class InteractiveStateAssetTest(unittest.TestCase):
    def test_helper_falls_back_when_no_server_and_no_storage(self) -> None:
        """server も localStorage も無い環境で例外を投げず動き続けること。"""
        script = INTERACTIVE_STATE_JS.read_text(encoding="utf-8")
        for token in ["resolveRemoteUrl", "resolveStorage", "memory", "window.RHWState"]:
            self.assertIn(token, script)
        # file:// で開いた場合に保存先を null にする判定
        self.assertIn('protocol !== "http:"', script)

    def test_helper_rejects_unsafe_state_names(self) -> None:
        """path traversal になる名前を JS 側でも弾くこと。"""
        script = INTERACTIVE_STATE_JS.read_text(encoding="utf-8")
        self.assertIn("STATE_NAME_RE", script)
        self.assertIn("A-Za-z0-9", script)

    def test_helper_debounces_server_writes_but_not_local(self) -> None:
        """連続入力で server への PUT だけをまとめ、手元の保存は毎回行うこと。

        スライダーを動かす間ずっと save() を呼べる設計にするため、
        debounce 経路でも localStorage への書き込みは即時に行う必要がある。
        """
        script = INTERACTIVE_STATE_JS.read_text(encoding="utf-8")
        self.assertIn("saveDebounced", script)
        self.assertIn("clearTimeout", script)
        self.assertIn("superseded", script)
        debounced = script[script.index("function saveDebounced") : script.index("async function saveNow")]
        # 予約を取り直す前に手元の保存を済ませていること
        self.assertLess(debounced.index("storage.setItem"), debounced.index("clearTimeout"))
        # server への書き込みは setTimeout の中だけで行うこと
        self.assertNotIn("fetch(", debounced)

    def test_helper_load_prefers_pending_value(self) -> None:
        """debounce 待ちの間は、server の古い値ではなく手元の値を返すこと。"""
        script = INTERACTIVE_STATE_JS.read_text(encoding="utf-8")
        load_body = script[script.index("async function load(name)") : script.index("async function save(")]
        self.assertIn("pending[name]", load_body)
        self.assertLess(load_body.index("pending[name]"), load_body.index("resolveRemoteUrl"))


class InteractiveRenderTest(unittest.TestCase):
    def test_render_ships_state_helper_before_inline_scripts(self) -> None:
        """html block の inline script より先に RHWState が定義されること。

        helper が </body> 直前だと inline script の実行時に未定義になるため、
        head での読み込みを検査する。
        """
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            _write_model(model_path, content=SLIDER_HTML)
            out = Path(tmp) / "out"
            render_bundle(model_path, out)

            self.assertTrue((out / "assets" / "interactive-state.js").is_file())
            html = (out / "index.html").read_text(encoding="utf-8")
            head_end = html.index("</head>")
            helper_at = html.index("assets/interactive-state.js")
            self.assertLess(helper_at, head_end, "helper は head 内で読み込む必要がある")
            self.assertLess(helper_at, html.index("RHWState.save"))

    def test_render_keeps_inline_script_verbatim(self) -> None:
        """html block の inline script が escape されずそのまま残ること。"""
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            _write_model(model_path, content=SLIDER_HTML)
            out = Path(tmp) / "out"
            render_bundle(model_path, out)

            html = (out / "index.html").read_text(encoding="utf-8")
            self.assertIn('<input type="range" id="dur"', html)
            self.assertIn("addEventListener('input'", html)
            self.assertNotIn("&lt;script&gt;", html)


class InteractivePublishTest(unittest.TestCase):
    def test_publish_inlines_helper_when_state_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            _write_model(model_path, content=SLIDER_HTML)
            out = Path(tmp) / "out"
            render_bundle(model_path, out)
            published = Path(tmp) / "published"
            publish_bundle(out, published)

            html = (published / "index.html").read_text(encoding="utf-8")
            self.assertIn("window.RHWState", html)
            self.assertIn("resolveStorage", html)
            # inline された helper が article の前にあること
            self.assertLess(html.index("resolveStorage"), html.index("RHWState.save"))
            # 操作部品そのものも残ること
            self.assertIn('<input type="range" id="dur"', html)

    def test_publish_skips_helper_without_state_usage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.json"
            _write_model(model_path, content="<p>操作部品のない資料</p>")
            out = Path(tmp) / "out"
            render_bundle(model_path, out)
            published = Path(tmp) / "published"
            publish_bundle(out, published)

            html = (published / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("resolveStorage", html)


class InteractiveStateRouteTest(unittest.TestCase):
    """preview server の汎用状態保存を確かめる。"""

    def test_state_survives_a_new_browser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            base = f"http://127.0.0.1:{session.port}"
            try:
                payload = {"state": {"duration": "420"}, "updated_at": "2026-07-30T00:00:00Z"}
                request = urllib.request.Request(
                    f"{base}/annotations/state/tuning.json",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    body = json.loads(response.read())
                self.assertTrue(body["ok"])
                self.assertEqual(body["path"], "annotations/state/tuning.json")

                # agent が読む経路: ファイルとして存在する
                saved = json.loads(
                    (root / "annotations" / "state" / "tuning.json").read_text(encoding="utf-8")
                )
                self.assertEqual(saved["state"], {"duration": "420"})

                # 別ブラウザ相当の素の GET でも読める
                with urllib.request.urlopen(f"{base}/annotations/state/tuning.json", timeout=5) as r:
                    self.assertEqual(json.loads(r.read())["state"], {"duration": "420"})
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_state_rejects_path_traversal(self) -> None:
        """`..` を含む名前で bundle の外へ書けないこと。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                for name in ["../escape.json", "a/b.json", "..%2Fescape.json", ".json", "x.txt"]:
                    with self.subTest(name=name):
                        request = urllib.request.Request(
                            f"http://127.0.0.1:{session.port}/annotations/state/{name}",
                            data=json.dumps({"state": {"x": 1}}).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="PUT",
                        )
                        with self.assertRaises(urllib.error.HTTPError) as ctx:
                            urllib.request.urlopen(request, timeout=5)
                        self.assertIn(ctx.exception.code, (400, 404))
                self.assertFalse((root.parent / "escape.json").exists())
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)

    def test_state_rejects_payload_without_state_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("<h1>Preview</h1>", encoding="utf-8")
            session = start_preview(root, "local", owner_pid=os.getpid(), idle_timeout=0)
            try:
                request = urllib.request.Request(
                    f"http://127.0.0.1:{session.port}/annotations/state/tuning.json",
                    data=json.dumps({"state": "not-an-object"}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(request, timeout=5)
                self.assertEqual(ctx.exception.code, 400)
                self.assertFalse((root / "annotations" / "state" / "tuning.json").exists())
            finally:
                session.process.terminate()
                session.process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
