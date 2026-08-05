"""公開用 standalone に目次が含まれることを検査する。

何が壊れたらこの test が落ちるか: 公開した資料に目次が無く、読み手が節を辿れない。
長い資料ほど「どこに何が書いてあるか」を掴めないまま読み進めることになる。
"""

from __future__ import annotations

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.publish import publish_bundle

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates"


def _bundle(bundle_dir: Path, *, toc_html: str, lang: str = "ja") -> None:
    """render 済み bundle の最小構成を作る。toc_html だけを差し替えられる形にする。"""
    assets = bundle_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE_DIR / "style.css", assets / "style.css")
    (bundle_dir / "index.html").write_text(
        "<!doctype html>\n"
        f'<html lang="{lang}" data-theme="light" data-density="compact">\n'
        "<head><meta charset=\"utf-8\"><title>Test</title></head>\n"
        "<body>\n"
        '  <div class="app" data-document-id="test-doc">\n'
        '    <main class="canvas" id="canvas">\n'
        '      <div class="doc-shell">\n'
        '        <div class="doc-grid">\n'
        f"          {toc_html}\n"
        '          <article class="doc-main">\n'
        '            <div class="paper">\n'
        '              <header class="doc-headrow document-header" data-review-block="document-header"'
        ' data-block-type="header" data-review-required="false">\n'
        '                <h1 class="doc-title">Test Document</h1>\n'
        "              </header>\n"
        '              <div class="prose document-content" id="content">\n'
        '                <section id="intro" data-review-block="intro" data-block-type="html"'
        ' data-review-required="true">\n'
        "                  <h2>はじめに</h2><p>Hello</p>\n"
        "                </section>\n"
        '                <section id="detail" data-review-block="detail" data-block-type="html"'
        ' data-review-required="true">\n'
        "                  <h3>詳細</h3><p>World</p>\n"
        "                </section>\n"
        "              </div>\n"
        "            </div>\n"
        "          </article>\n"
        '          <aside class="cmt-rail"><div class="cmt-layer" id="cmtLayer"></div></aside>\n'
        "        </div>\n      </div>\n    </main>\n  </div>\n</body>\n</html>\n",
        encoding="utf-8",
    )


TOC_WITH_ITEMS = (
    '<nav class="toc" aria-label="目次" data-i18n="tocLabel">'
    '<p class="toc-h" data-i18n="tocHeader"></p>'
    '<ol class="toc-list">'
    '<li class="toc-h2"><a href="#intro">はじめに</a>'
    '<ol><li><a href="#detail">詳細</a></li></ol></li>'
    "</ol></nav>"
)


class PublishTocTest(unittest.TestCase):
    def test_standalone_contains_toc(self) -> None:
        """公開出力に目次が含まれ、リンク先が本文に存在する。

        判定基準の出所: TASK-9 の受入基準「公開用 standalone HTML の標準表示に目次が含まれ、
        各項目が本文の見出しへ移動する」。
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html=TOC_WITH_ITEMS)
            publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        self.assertIn('<nav class="toc"', html)
        hrefs = re.findall(r'href="#([^"]+)"', html)
        self.assertIn("intro", hrefs)
        self.assertIn("detail", hrefs)
        for anchor in ("intro", "detail"):
            self.assertIn(f'id="{anchor}"', html, f"目次のリンク先 {anchor} が本文に無い")

    def test_toc_heading_is_filled(self) -> None:
        """目次の見出しが文字で埋まる。

        判定基準の出所: preview では review-comments.js の i18n (ja は「目次」) が入れる。
        standalone には JS が無いため、空のままだと余白だけが残る。
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html=TOC_WITH_ITEMS, lang="ja")
            publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        m = re.search(r'<p class="toc-h"[^>]*>(.*?)</p>', html)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "目次")

    def test_toc_heading_uses_english_for_non_ja(self) -> None:
        """lang が ja 以外なら英語の見出しにする。"""
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html=TOC_WITH_ITEMS, lang="en")
            publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        m = re.search(r'<p class="toc-h"[^>]*>(.*?)</p>', html)
        self.assertEqual(m.group(1), "Contents")

    def test_comment_rail_is_not_published(self) -> None:
        """コメント rail は公開出力に含めない。

        判定基準の出所: TASK-9 の受入基準「コメント rail は標準・最大化とも非表示のまま」。
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html=TOC_WITH_ITEMS)
            publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        # standalone は CSS 全文を inline するため、セレクタ定義側に .cmt-rail が現れる。
        # DOM に出ていないことを見たいので </style> より後ろだけを対象にする
        body = html.split("</style>", 1)[1]
        self.assertNotIn("cmt-rail", body)
        self.assertNotIn("cmtLayer", body)

    def test_standalone_toc_toggle_is_wired(self) -> None:
        """公開出力で「目次を隠して本文を全幅で読む」手段が失われたら落ちる。

        判定基準の出所: TASK-15 の受入基準 (目次を隠すと本文が全幅になる / 戻せる /
        切替は既存の is-wide class で行う) と、2026-08-05 のユーザー指示
        「目次ボタンは閉じたときも開いたときも同じ場所」(左端固定タブ 1 つに一本化)。
        toc-nav.js は publish が standalone に inline するので、その中身を検査する。
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html=TOC_WITH_ITEMS)
            publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        css, body = html.split("</style>", 1)
        for marker in ("toc-toggle-tab", "initTocToggle", "HIDE_TOC_KEY"):
            self.assertIn(marker, body, f"目次トグルの {marker} が standalone に無い")
        # 切替は is-wide class の付け外しで行い、全幅化は既存 CSS に任せる
        self.assertIn('classList.toggle("is-wide"', body)
        # タブは開閉共通の 1 つ。開いている間は矢印を反転して見せる
        self.assertIn(".is-published .toc-toggle-tab { display: inline-flex; }", css)
        self.assertIn(".canvas:not(.is-wide) .toc-toggle-tab .tt-chev", css)
        # iframe 埋め込みホストには body>* へ width:100%!important を注入するものがあり、
        # タブは body 直下ではなく canvas 内に置く (2026-08-05 実表示で全幅化を確認)
        self.assertIn("canvas.appendChild(tab)", body)
        self.assertNotIn("document.body.appendChild(tab)", body)

    def test_document_without_toc_still_publishes(self) -> None:
        """目次を持たない文書でも publish が成立する。

        判定基準の出所: block が 1 つも title を持たない文書では render が目次を出さない。
        その場合に publish が失敗すると、これまで公開できていた資料が公開できなくなる。
        """
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            out = Path(tmp) / "out"
            _bundle(src, toc_html="")
            result = publish_bundle(src, out)
            html = (out / "index.html").read_text(encoding="utf-8")

        self.assertEqual(result["status"], "ok")
        self.assertNotIn('<nav class="toc"', html)
        self.assertIn('<h1 class="doc-title">Test Document</h1>', html)


if __name__ == "__main__":
    unittest.main()
