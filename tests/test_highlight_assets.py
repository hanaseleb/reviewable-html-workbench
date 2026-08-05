"""highlight.js 同梱 asset の render / publish 経路の検査。

何が壊れたらこの test は落ちるか (利用者に起きる不都合):
  コード入り資料をブラウザで開いた利用者が、着色されない読みにくいコードを見る。
判定基準の出所:
  判定基準 (assets/highlight.min.js と init script tag が bundle に存在) は
  TASK-7 / plan 受入条件 (SC-3) から転記。
落ちるのを見た記録:
  実装前 (render.py に highlight 経路が無い状態) で走らせ、asset 未出力で FAIL を確認した。
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.render import render_bundle


ROOT = Path(__file__).resolve().parents[1]


def _model_with_code(tmp: Path, *, with_code: bool) -> Path:
    blocks = [
        {
            "id": "overview",
            "type": "html",
            "title": "Overview",
            "heading_level": 2,
            "review_required": True,
            "content": (
                '<pre><code class="language-python">print("hello")</code></pre>'
                if with_code
                else "<p>No code here.</p>"
            ),
        }
    ]
    model = {
        "schema_version": "1.0",
        "document_id": "highlight-asset-test",
        "title": "Highlight asset test",
        "generated_at": "2026-08-04T00:00:00Z",
        "summary": "code presence probe",
        "metadata": {},
        "blocks": blocks,
    }
    path = tmp / "model.json"
    path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return path


class HighlightRenderAssetsTest(unittest.TestCase):
    def test_render_copies_highlight_assets_when_pre_code_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            model = _model_with_code(Path(tmp), with_code=True)
            index_path = render_bundle(model, output_dir)
            html = index_path.read_text(encoding="utf-8")

            self.assertTrue((output_dir / "assets" / "highlight.min.js").is_file())
            self.assertTrue((output_dir / "assets" / "highlight-init.js").is_file())
            self.assertIn("assets/highlight.min.js", html)
            self.assertIn("assets/highlight-init.js", html)

            # BSD-3-Clause 表記が vendored file に残っていること (R-003)
            hljs = (output_dir / "assets" / "highlight.min.js").read_text(encoding="utf-8")
            self.assertIn("BSD-3-Clause", hljs)
            self.assertIn("Redistributions of source code", hljs)

            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn("assets/highlight.min.js", manifest["outputs"]["assets"])
            self.assertIn("assets/highlight-init.js", manifest["outputs"]["assets"])

    def test_render_skips_highlight_assets_without_pre_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            model = _model_with_code(Path(tmp), with_code=False)
            index_path = render_bundle(model, output_dir)
            html = index_path.read_text(encoding="utf-8")

            self.assertFalse((output_dir / "assets" / "highlight.min.js").exists())
            self.assertFalse((output_dir / "assets" / "highlight-init.js").exists())
            self.assertNotIn("assets/highlight.min.js", html)
            self.assertNotIn("assets/highlight-init.js", html)

    def test_render_copies_highlight_assets_for_attributed_pre_code(self) -> None:
        """属性付き <pre ...><code ...> でも asset が copy される (NG-1 / SC-1a)。

        何が壊れたら落ちるか: agent が普通に属性を付けた code block を書くと着色されない。
        判定基準の出所: lead 差し戻し 2 巡目 NG-1 SC-1a (属性付きでも検出)。
        落ちるのを見た: 修正前 `"<pre><code" in body_html` では
        `<pre id="auto"><code class="language-python">` が false になり FAIL した。
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            output_dir = tmp_path / "out"
            model = {
                "schema_version": "1.0",
                "document_id": "attr-pre-code",
                "title": "Attributed pre/code",
                "generated_at": "2026-08-05T00:00:00Z",
                "summary": "attr probe",
                "metadata": {},
                "blocks": [
                    {
                        "id": "code",
                        "type": "html",
                        "title": "Code",
                        "heading_level": 2,
                        "review_required": True,
                        "content": (
                            '<pre id="auto"><code class="language-python">'
                            "print(1)</code></pre>"
                        ),
                    }
                ],
            }
            model_path = tmp_path / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            index_path = render_bundle(model_path, output_dir)
            html = index_path.read_text(encoding="utf-8")
            self.assertTrue((output_dir / "assets" / "highlight.min.js").is_file())
            self.assertIn("assets/highlight.min.js", html)
            self.assertIn("assets/highlight-init.js", html)


if __name__ == "__main__":
    unittest.main()
