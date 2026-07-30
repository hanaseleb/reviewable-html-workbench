from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.html_review_workbench.render import render_bundle

DIAGRAM_ZOOM_JS = Path(__file__).resolve().parents[1] / "templates" / "assets" / "diagram-zoom.js"
STYLE_CSS = Path(__file__).resolve().parents[1] / "templates" / "style.css"


def _diagram_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "document_id": "zoom-doc",
        "title": "Zoom Doc",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [
            {
                "id": "customer-order",
                "type": "diagram",
                "heading_level": 2,
                "title": "Customer Order",
                "content": "erDiagram\n  CUSTOMER ||--o{ ORDER : places",
                "review_required": True,
            }
        ],
    }


def _generated_image_diagram_model() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "document_id": "generated-diagram-doc",
        "title": "Generated Diagram Doc",
        "generated_at": "2026-05-17T00:00:00+09:00",
        "blocks": [
            {
                "id": "generated-flow",
                "type": "diagram",
                "heading_level": 2,
                "title": "Generated Flow",
                "content": "flowchart TD\n  A --> B",
                "image": {
                    "prompt": "Generate a flow diagram.",
                    "alt": "Generated flow diagram",
                    "caption": "Generated Flow",
                    "generation_status": "generated",
                    "source_path": "generated-flow.png",
                },
                "review_required": True,
            }
        ],
    }


def _minimal_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
        b"\xdc\xccY\xe7"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class RenderDiagramZoomTest(unittest.TestCase):
    def test_rendered_mermaid_diagram_gets_zoom_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_diagram_model()), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            self.assertIn('<figure class="diagram-wrap">', html)
            self.assertIn('class="diagram-zoom-btn"', html)
            self.assertIn('<pre class="mermaid">erDiagram', html)

    def test_rendered_mermaid_diagram_copies_zoom_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_diagram_model()), encoding="utf-8")

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertIn('src="assets/diagram-zoom.js?', html)
            self.assertTrue((output_dir / "assets" / "diagram-zoom.js").is_file())
            self.assertIn("assets/diagram-zoom.js", manifest["outputs"]["assets"])

    def test_generated_image_diagram_does_not_copy_zoom_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "bundle"
            model_path = root / "model.json"
            model_path.write_text(json.dumps(_generated_image_diagram_model()), encoding="utf-8")
            (root / "generated-flow.png").write_bytes(_minimal_png_bytes())

            index_path = render_bundle(model_path, output_dir)

            html = index_path.read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "renderer-manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn('<figure class="diagram-wrap">', html)
            self.assertNotIn("diagram-zoom.js", html)
            self.assertFalse((output_dir / "assets" / "diagram-zoom.js").exists())
            self.assertNotIn("assets/diagram-zoom.js", manifest["outputs"]["assets"])

    def test_diagram_zoom_sets_absolute_svg_size_and_restores_attributes(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("sourceSvg.viewBox?.baseVal", script)
        self.assertIn('sourceSvg.setAttribute("width", String(svgBox.width))', script)
        self.assertIn('sourceSvg.setAttribute("height", String(svgBox.height))', script)
        self.assertIn('restoreAttribute(sourceSvg, "width", originalSvgAttrs.width)', script)
        self.assertIn('restoreAttribute(sourceSvg, "height", originalSvgAttrs.height)', script)
        self.assertIn("node.removeAttribute(name)", script)
        self.assertIn("node.setAttribute(name, value)", script)

    def test_diagram_zoom_overlay_capture_does_not_block_drag_handlers(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertNotIn('overlay.addEventListener("pointerup", stopGlobalEvent, true)', script)
        self.assertNotIn('overlay.addEventListener("mousedown", stopGlobalEvent, true)', script)
        self.assertIn('viewport.addEventListener("pointerleave", cancelDrag)', script)

    def test_diagram_zoom_distinguishes_click_drag_pan_and_zoom(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn('if (activeDragType) {', script)
        self.assertIn("if (!dragging && Math.abs(dx) + Math.abs(dy) <= 2)", script)
        self.assertIn("dragging = true;", script)
        self.assertIn("suppressNextClick = event.target !== viewport && event.target !== overlay", script)
        self.assertIn("panBy(event.deltaX, event.deltaY)", script)
        self.assertIn("if (event.ctrlKey || event.metaKey)", script)

    def test_diagram_zoom_overlay_background_is_opaque(self) -> None:
        """拡大表示の背景に半透明トークンを使わない (背後の本文が透けるため)。"""
        css = STYLE_CSS.read_text(encoding="utf-8")
        start = css.index(".diagram-zoom-overlay {")
        overlay_rule = css[start : css.index("}", start)]
        self.assertIn("background: var(--surface-dark)", overlay_rule)
        self.assertNotIn("background: var(--overlay-strong)", overlay_rule)

    def test_diagram_zoom_toolbar_has_download_button(self) -> None:
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn('data-zoom="download"', script)
        self.assertIn("downloadDiagram(sourceSvg)", script)

    def test_diagram_download_renders_png_with_svg_fallback(self) -> None:
        """PNG (2x) を第一候補にし、canvas 失敗時は SVG ダウンロードへ fallback する。"""
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("new XMLSerializer().serializeToString", script)
        self.assertIn('canvas.toBlob', script)
        self.assertIn("const scale = 2;", script)
        self.assertIn("downloadSvgFallback(xml, stem)", script)
        self.assertIn("image.onerror = () => downloadSvgFallback(xml, stem)", script)
        # download 属性で保存する (外部送信しない)
        self.assertIn('link.download = filename', script)
        self.assertNotIn("fetch(", script)
        self.assertNotIn("XMLHttpRequest", script)

    def test_diagram_download_flattens_foreign_object_labels(self) -> None:
        """Mermaid の foreignObject ラベルを <text> へ平坦化してから PNG 化する。

        Mermaid v11 の getEffectiveHtmlLabels は既定 true (mermaid.min.js 実測) で
        flowchart のラベルを foreignObject の HTML として描く。data URI の SVG を
        canvas に描くと中身が落ちて文字なし PNG になるため、事前に置き換える。
        """
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("flattenForeignObjects(sourceSvg, clone)", script)
        self.assertIn('createElementNS("http://www.w3.org/2000/svg", "text")', script)
        self.assertIn('createElementNS("http://www.w3.org/2000/svg", "tspan")', script)
        self.assertIn("flattenLabels: true", script)

    def test_diagram_download_refuses_png_when_foreign_object_remains(self) -> None:
        """平坦化しきれなかった場合は PNG を作らず SVG へ落とす (無言の文字落ちを防ぐ)。"""
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("if (/<foreignObject/i.test(flattened.xml))", script)

    def test_diagram_download_restores_label_background_rect(self) -> None:
        """edge ラベルの背景を矩形で復元する (線が文字を横切るのを防ぐ)。

        verifier 実測の欠陥: text だけへ置換した PNG では edge 線が
        「style 注入」等のラベル文字を横切っていた。
        """
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("function resolveLabelBackground(", script)
        self.assertIn('createElementNS("http://www.w3.org/2000/svg", "rect")', script)
        self.assertIn("target.parentNode.insertBefore(rect, target)", script)
        # 透明なラベル (ノード内側) では矩形を作らない
        self.assertIn('return ""', script)

    def test_diagram_download_background_falls_back_when_transparent(self) -> None:
        """overlay が閉じている / 変数未解決でも透明背景の PNG を作らない。"""
        script = DIAGRAM_ZOOM_JS.read_text(encoding="utf-8")

        self.assertIn("function overlayBackgroundColor()", script)
        self.assertIn('const fallback = "#1c1f24"', script)
        self.assertIn('color === "transparent"', script)


if __name__ == "__main__":
    unittest.main()
