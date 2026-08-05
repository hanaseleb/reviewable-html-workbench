"""publish standalone への highlight.js inline 化の検査。

何が壊れたらこの test は落ちるか (利用者に起きる不都合):
  publish した単一 HTML をオフラインで開くと着色が消える / 外部参照が残ると self-contained が壊れる。
判定基準の出所:
  「standalone は外部 <script src= を持たない」は既存 publish 仕様 (publish.py docstring /
  既存 test_publish.py) と plan SC-4 から転記。BSD-3-Clause banner 残存は TASK-7 AC #5 から転記。
落ちるのを見た記録:
  実装前 (_inline_highlight_script が無い状態) で走らせ、inline 化未実施で FAIL を確認した。
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.publish import publish_bundle
from scripts.html_review_workbench.render import render_bundle


ROOT = Path(__file__).resolve().parents[1]


class PublishHighlightInlineTest(unittest.TestCase):
    def test_publish_inlines_highlight_and_keeps_license(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model = {
                "schema_version": "1.0",
                "document_id": "publish-hljs-test",
                "title": "Publish highlight test",
                "generated_at": "2026-08-04T00:00:00Z",
                "summary": "probe",
                "metadata": {},
                "blocks": [
                    {
                        "id": "code",
                        "type": "html",
                        "title": "Code",
                        "heading_level": 2,
                        "review_required": True,
                        "content": '<pre><code class="language-python">x = 1</code></pre>',
                    }
                ],
            }
            model_path = tmp_path / "model.json"
            model_path.write_text(json.dumps(model), encoding="utf-8")
            bundle = tmp_path / "bundle"
            published = tmp_path / "published"
            render_bundle(model_path, bundle)

            # 実装前は highlight asset が無いので、vendored を手動配置して publish 経路を先に赤にする
            assets = bundle / "assets"
            assets.mkdir(parents=True, exist_ok=True)
            hljs_src = ROOT / "templates" / "assets" / "highlight.min.js"
            init_src = ROOT / "templates" / "assets" / "highlight-init.js"
            if hljs_src.is_file() and not (assets / "highlight.min.js").is_file():
                shutil.copyfile(hljs_src, assets / "highlight.min.js")
            if init_src.is_file() and not (assets / "highlight-init.js").is_file():
                shutil.copyfile(init_src, assets / "highlight-init.js")
            index = bundle / "index.html"
            html = index.read_text(encoding="utf-8")
            if "assets/highlight.min.js" not in html:
                # render が未対応でも publish 対象として script tag を差し込む
                html = html.replace(
                    "</head>",
                    '  <script src="assets/highlight.min.js?v=test"></script>\n'
                    '  <script src="assets/highlight-init.js?v=test"></script>\n</head>',
                    1,
                )
                index.write_text(html, encoding="utf-8")

            result = publish_bundle(bundle, published)
            self.assertEqual(result["status"], "ok")
            content = (published / "index.html").read_text(encoding="utf-8")

            # 外部 script / link が残っていない
            self.assertIsNone(re.search(r'<script\s+src=', content))
            self.assertIsNone(re.search(r'<link\s+[^>]*href="https://', content))

            # highlight 本体と init が inline されている
            self.assertIn("hljs", content)
            self.assertIn("highlightElement", content)
            self.assertIn("BSD-3-Clause", content)
            self.assertIn("Redistributions of source code", content)


if __name__ == "__main__":
    unittest.main()
