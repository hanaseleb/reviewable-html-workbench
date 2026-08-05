"""render 済み HTML バンドルからレビュー UI を除去した公開用 standalone HTML を生成する。

renderer が出力する HTML は構造が既知のため、stdlib の文字列操作と regex で
レビュー要素を除去し、CSS インライン化・画像 embed 済みの単一 HTML を出力する。
外部依存なし（Python stdlib のみ）。
"""

from __future__ import annotations

import base64
import mimetypes
import re
from html import escape
from pathlib import Path
from typing import Any

# render.py と同じ検出 (属性付き pre/code の取りこぼし防止)
_PRE_CODE_RE = re.compile(
    r"<pre\b[^>]*>\s*<code\b",
    re.IGNORECASE,
)

from scripts.html_review_workbench.common import (
    INTERACTIVE_STATE_JS_PATH,
    MERMAID_INIT_JS,
    PUBLISH_OVERRIDES_CSS_PATH,
    REPO_ROOT,
    TASK_CHECKLIST_JS_PATH,
    TOC_NAV_JS_PATH,
)

ROOT = REPO_ROOT
DIAGRAM_ZOOM_JS_PATH = ROOT / "templates" / "assets" / "diagram-zoom.js"


class PublishError(Exception):
    pass


def publish_bundle(root: Path, output: Path) -> dict[str, Any]:
    """render 済みバンドルから公開用 standalone HTML を生成する。

    renderer 出力の index.html から article 部分を抽出し、レビュー UI を除去、
    CSS をインライン化、画像を base64 data URI に変換して単一 HTML を出力する。

    Args:
        root: render 済みバンドルのディレクトリ（index.html を含む）
        output: 出力先ディレクトリ

    Returns:
        {"status": "ok", "output": "<path>"} 形式の dict

    Raises:
        PublishError: バンドルが不正な場合
    """
    index_path = root / "index.html"
    style_path = root / "assets" / "style.css"

    if not index_path.is_file():
        raise PublishError(f"index.html not found in {root}")
    if not style_path.is_file():
        raise PublishError(f"assets/style.css not found in {root}")

    source_html = index_path.read_text(encoding="utf-8")
    css = style_path.read_text(encoding="utf-8")
    publish_overrides = _load_publish_overrides(root)

    lang = _extract_attr(source_html, r'<html[^>]*\blang="([^"]*)"') or "ja"
    density = _extract_attr(source_html, r'data-density="([^"]*)"') or "compact"

    canvas_match = re.search(r'<main[^>]*class="canvas([^"]*)"', source_html)
    is_wide = bool(canvas_match and "is-wide" in canvas_match.group(1))

    article = _extract_article(source_html)
    article = _strip_review_attrs(article)
    article = _strip_review_elements(article)
    article = _embed_images(article, root)
    # 目次は本文と同じ doc-grid に置く。標準表示では出し、最大化 (is-wide) では CSS 側で隠す
    toc = _fill_toc_heading(_strip_review_attrs(_extract_toc(source_html)), lang)
    mermaid_script = _inline_mermaid_script(source_html, article, root)
    highlight_script = _inline_highlight_script(source_html, article, root)
    checklist_script = _inline_checklist_script(article, root)
    interactive_state_script = _inline_interactive_state_script(article, root)
    toc_nav_script = _inline_toc_nav_script(toc, root)
    document_id = _extract_attr(source_html, r'data-document-id="([^"]*)"') or ""

    title = _extract_text(article, r'<h1 class="doc-title">(.*?)</h1>') or "document"
    description = _extract_description(article)

    html = _assemble(
        lang=lang,
        density=density,
        title=title,
        description=description,
        css=css,
        publish_overrides=publish_overrides,
        article=article,
        toc=toc,
        is_wide=is_wide,
        mermaid_script=mermaid_script,
        highlight_script=highlight_script,
        checklist_script=checklist_script,
        interactive_state_script=interactive_state_script,
        toc_nav_script=toc_nav_script,
        document_id=document_id,
    )

    output.mkdir(parents=True, exist_ok=True)
    output_path = output / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return {"status": "ok", "output": str(output_path)}


def _extract_attr(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html)
    return m.group(1) if m else None


def _extract_article(html: str) -> str:
    """<article class="doc-main">...</article> を抽出する。"""
    start_marker = '<article class="doc-main">'
    start = html.find(start_marker)
    if start == -1:
        raise PublishError("article.doc-main not found in index.html")
    end = html.find("</article>", start)
    if end == -1:
        raise PublishError("closing </article> not found")
    return html[start : end + len("</article>")]


def _extract_toc(html: str) -> str:
    """<nav class="toc">...</nav> を抽出する。

    見つからない場合は空文字を返す。目次を持たない文書 (block が 1 つも title を
    持たない場合) でも publish は成立させる。
    """
    m = re.search(r'<nav class="toc"[^>]*>', html)
    if not m:
        return ""
    start = m.start()
    end = html.find("</nav>", start)
    if end == -1:
        return ""
    return html[start : end + len("</nav>")]


def _fill_toc_heading(toc: str, lang: str) -> str:
    """目次の見出しを文字で埋める。

    preview では review-comments.js が i18n で入れるが、standalone に JS は無いため
    空の見出しが余白だけ残ってしまう。
    """
    label = "目次" if lang.startswith("ja") else "Contents"
    return re.sub(r'(<p class="toc-h"[^>]*>)\s*(</p>)', rf"\g<1>{label}\g<2>", toc)


def _strip_review_attrs(html: str) -> str:
    """レビュー用 data 属性を除去する。"""
    for attr in ("data-review-block", "data-review-required", "data-block-type"):
        html = re.sub(rf'\s+{attr}="[^"]*"', "", html)
    return html


def _strip_review_elements(html: str) -> str:
    """レビュー専用の DOM 要素を除去する。

    byline: <div class="byline">...(span のみ)...</div>
    doc-status: <span class="doc-status ...">...</span>
    """
    html = re.sub(
        r'<div class="byline">.*?</div>', "", html, flags=re.DOTALL
    )
    html = re.sub(
        r'<span class="doc-status[^"]*">.*?</span>', "", html, flags=re.DOTALL
    )
    return html


def _embed_images(html: str, root: Path) -> str:
    """<img src="..."> の画像をファイルから読み取り base64 data URI に変換する。"""

    def _replace(match: re.Match[str]) -> str:
        src = match.group(1)
        if src.startswith("data:"):
            return match.group(0)
        img_path = root / src
        if not img_path.is_file():
            return match.group(0)
        mime, _ = mimetypes.guess_type(str(img_path))
        if not mime:
            mime = "application/octet-stream"
        data = base64.b64encode(img_path.read_bytes()).decode("ascii")
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]*)"', _replace, html)


def _inline_mermaid_script(source_html: str, article: str, root: Path) -> str:
    """Mermaid 図 bundle の Mermaid / zoom asset を standalone HTML に inline 化する。"""
    needs_mermaid = "assets/mermaid.min.js" in source_html or 'class="mermaid"' in article
    if not needs_mermaid:
        return ""
    mermaid_path = root / "assets" / "mermaid.min.js"
    zoom_path = root / "assets" / "diagram-zoom.js"
    if not mermaid_path.is_file():
        raise PublishError(f"assets/mermaid.min.js not found in {root}")
    if not zoom_path.is_file():
        zoom_path = DIAGRAM_ZOOM_JS_PATH
    if not zoom_path.is_file():
        raise PublishError(f"assets/diagram-zoom.js not found in {root}")
    script = mermaid_path.read_text(encoding="utf-8")
    zoom_script = zoom_path.read_text(encoding="utf-8")
    return (
        f"<script>\n{script}\n</script>\n"
        f'<script data-role="reviewable-mermaid-init">{MERMAID_INIT_JS}</script>\n'
        f"<script>\n{zoom_script}\n</script>\n"
    )


def _inline_highlight_script(source_html: str, article: str, root: Path) -> str:
    """highlight.js 本体と init を standalone HTML に inline 化する。

    本文に <pre><code が無い (または highlight asset が無い) 文書では何も差し込まない。
    BSD-3-Clause banner は file 先頭の /*! */ として残る。
    """
    needs_highlight = (
        "assets/highlight.min.js" in source_html
        or "assets/highlight-init.js" in source_html
        or _PRE_CODE_RE.search(article) is not None
    )
    if not needs_highlight:
        return ""
    hljs_path = root / "assets" / "highlight.min.js"
    init_path = root / "assets" / "highlight-init.js"
    if not hljs_path.is_file():
        # render 済み bundle に無い場合は template 同梱へ fallback
        hljs_path = ROOT / "templates" / "assets" / "highlight.min.js"
    if not init_path.is_file():
        init_path = ROOT / "templates" / "assets" / "highlight-init.js"
    if not hljs_path.is_file():
        raise PublishError(f"assets/highlight.min.js not found in {root}")
    if not init_path.is_file():
        raise PublishError(f"assets/highlight-init.js not found in {root}")
    hljs_script = hljs_path.read_text(encoding="utf-8")
    init_script = init_path.read_text(encoding="utf-8")
    return (
        f"<script>\n{hljs_script}\n</script>\n"
        f"<script>\n{init_script}\n</script>\n"
    )


def _inline_checklist_script(article: str, root: Path) -> str:
    """作業チェックリスト asset を standalone HTML に inline 化する。

    チェックボックスを含まない資料では何も差し込まない。
    """
    if "data-task-check" not in article:
        return ""
    path = root / "assets" / "task-checklist.js"
    if not path.is_file():
        path = TASK_CHECKLIST_JS_PATH
    if not path.is_file():
        raise PublishError(f"assets/task-checklist.js not found in {root}")
    return f"<script>\n{path.read_text(encoding='utf-8')}\n</script>\n"


def _inline_toc_nav_script(toc: str, root: Path) -> str:
    """目次の移動と現在位置ハイライトの script を inline 化する。

    公開出力には review-comments.js が入らないため、目次があっても現在位置が光らず、
    ジャンプ位置の調整も効かない。目次を出す文書にだけ差し込む。
    """
    if not toc:
        return ""
    path = root / "assets" / "toc-nav.js"
    if not path.is_file():
        path = TOC_NAV_JS_PATH
    if not path.is_file():
        raise PublishError(f"assets/toc-nav.js not found in {root}")
    return f"<script>\n{path.read_text(encoding='utf-8')}\n</script>\n"


def _inline_interactive_state_script(article: str, root: Path) -> str:
    """操作部品の状態保存ヘルパーを standalone HTML に inline 化する。

    RHWState を使わない資料では何も差し込まない。
    standalone では preview server が無いため、保存は localStorage へ落ちる。
    """
    if "RHWState" not in article:
        return ""
    path = root / "assets" / "interactive-state.js"
    if not path.is_file():
        path = INTERACTIVE_STATE_JS_PATH
    if not path.is_file():
        raise PublishError(f"assets/interactive-state.js not found in {root}")
    return f"<script>\n{path.read_text(encoding='utf-8')}\n</script>\n"


def _load_publish_overrides(root: Path) -> str:
    """公開用 CSS override を bundle asset から読み、旧 bundle では template asset に fallback する。"""
    path = root / "assets" / "publish-overrides.css"
    if not path.is_file():
        path = PUBLISH_OVERRIDES_CSS_PATH
    if not path.is_file():
        raise PublishError(f"assets/publish-overrides.css not found in {root}")
    return path.read_text(encoding="utf-8")


def _extract_text(html: str, pattern: str) -> str:
    """regex でマッチしたタグの text content を返す。"""
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        return ""
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def _extract_description(article: str) -> str:
    """OG description 用のテキストを抽出する（最大 200 文字）。"""
    for pattern in [
        r'<section class="summary">.*?<p>(.*?)</p>',
        r'<div class="block-content"[^>]*>.*?<p[^>]*>(.*?)</p>',
    ]:
        text = _extract_text(article, pattern)
        if text:
            return text[:200]
    return ""


def _assemble(
    *,
    lang: str,
    density: str,
    title: str,
    description: str,
    css: str,
    publish_overrides: str,
    article: str,
    toc: str,
    is_wide: bool,
    mermaid_script: str = "",
    highlight_script: str = "",
    checklist_script: str = "",
    interactive_state_script: str = "",
    toc_nav_script: str = "",
    document_id: str = "",
) -> str:
    """公開用 standalone HTML を組み立てる。"""
    esc_title = escape(title)
    esc_desc = escape(description)
    wide_class = " is-wide" if is_wide else ""
    # 目次は本文と同じ doc-grid の先頭に置く (report.html.j2 と同じ並び)。
    # 目次を持たない文書では空にして 1 カラムのままにする
    toc_block = f"{toc}\n" if toc else ""
    # チェックリストの保存 key は文書識別子に紐づくため、publish 版でも同じ値を残す
    doc_id_attr = f' data-document-id="{escape(document_id, quote=True)}"' if document_id else ""

    return (
        f'<!DOCTYPE html>\n<html lang="{escape(lang)}" data-density="{escape(density)}">\n'
        f"<head>\n<meta charset=\"utf-8\">\n"
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{esc_title}</title>\n"
        f'<meta property="og:title" content="{esc_title}">\n'
        f'<meta property="og:description" content="{esc_desc}">\n'
        f'<meta property="og:type" content="article">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{esc_title}">\n'
        f'<meta name="twitter:description" content="{esc_desc}">\n'
        f"<style>\n{css}\n"
        f"/* published export overrides */\n"
        f"{publish_overrides}"
        f"</style>\n"
        f"{mermaid_script}"
        f"{highlight_script}"
        # article 内の inline script より先に RHWState を定義する必要があるため head に置く
        f"{interactive_state_script}"
        f"</head>\n"
        f'<body class="is-published"{doc_id_attr}>\n'
        f'<main class="canvas{wide_class}">\n'
        f'<div class="doc-shell">\n<div class="doc-grid">\n'
        f"{toc_block}"
        f"{article}\n"
        f"</div>\n</div>\n"
        f"</main>\n"
        f"{checklist_script}"
        f"{toc_nav_script}"
        f"</body>\n</html>\n"
    )
