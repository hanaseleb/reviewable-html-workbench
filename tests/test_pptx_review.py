from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts.html_review_workbench.pptx_review import PptxReviewError, build_pptx_review


class PptxReviewTest(unittest.TestCase):
    def test_builds_slide_blocks_with_stable_ids_and_preserves_comments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            output = root / "review"
            _write_minimal_pptx(source, [256, 412], 12_192_000, 6_858_000)
            rendered = [_png(root / "first.png"), _png(root / "second.png")]

            with patch("scripts.html_review_workbench.pptx_review._convert_to_pdf", return_value=root / "deck.pdf"), patch(
                "scripts.html_review_workbench.pptx_review._render_pdf_to_pngs", return_value=rendered
            ):
                first = build_pptx_review(source, output)

            model = json.loads((output / "document-model.json").read_text(encoding="utf-8"))
            self.assertEqual([block["id"] for block in model["blocks"]], ["slide-256", "slide-412"])
            self.assertAlmostEqual(model["blocks"][0]["image"]["aspect_ratio"], 16 / 9, places=4)
            self.assertEqual(first.slide_count, 2)
            self.assertIn('data-review-block="slide-256"', (output / "index.html").read_text(encoding="utf-8"))

            comments_path = output / "annotations" / "comments.json"
            comments = json.loads(comments_path.read_text(encoding="utf-8"))
            comments["comments"].append(_comment(first.document_id))
            comments_path.write_text(json.dumps(comments), encoding="utf-8")

            with patch("scripts.html_review_workbench.pptx_review._convert_to_pdf", return_value=root / "deck.pdf"), patch(
                "scripts.html_review_workbench.pptx_review._render_pdf_to_pngs", return_value=rendered
            ):
                second = build_pptx_review(source, output)

            self.assertEqual(second.document_id, first.document_id)
            self.assertEqual(len(json.loads(comments_path.read_text(encoding="utf-8"))["comments"]), 1)

    def test_rejects_non_pptx_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "deck.pdf"
            source.write_bytes(b"pdf")
            with self.assertRaisesRegex(PptxReviewError, "input must be a .pptx"):
                build_pptx_review(source, Path(tmp) / "review")

    def test_changed_source_requires_explicit_review_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            revision = root / "deck-revised.pptx"
            output = root / "review"
            _write_minimal_pptx(source, [256], 12_192_000, 6_858_000)
            _write_minimal_pptx(revision, [256], 12_192_001, 6_858_000)
            rendered = [_png(root / "slide.png")]

            with patch("scripts.html_review_workbench.pptx_review._convert_to_pdf", return_value=root / "deck.pdf"), patch(
                "scripts.html_review_workbench.pptx_review._render_pdf_to_pngs", return_value=rendered
            ):
                first = build_pptx_review(source, output)
                with self.assertRaisesRegex(PptxReviewError, "--continue-review"):
                    build_pptx_review(revision, output)
                continued = build_pptx_review(revision, output, continue_review=True)

            self.assertEqual(continued.document_id, first.document_id)


def _write_minimal_pptx(path: Path, slide_ids: list[int], cx: int, cy: int) -> None:
    slides = "".join(
        f'<p:sldId id="{slide_id}" r:id="rId{index}"/>' for index, slide_id in enumerate(slide_ids, 1)
    )
    xml = (
        f'<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        f'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<p:sldIdLst>{slides}</p:sldIdLst><p:sldSz cx="{cx}" cy="{cy}"/></p:presentation>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/presentation.xml", xml)


def _png(path: Path) -> Path:
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return path


def _comment(document_id: str) -> dict[str, object]:
    return {
        "id": "cmt-1",
        "document_id": document_id,
        "block_id": "slide-256",
        "selected_text": "スライド 1",
        "comment": "タイトルを短くしてください",
        "status": "needs_agent_review",
        "created_at": "2026-09-05T00:00:00+00:00",
        "replies": [],
    }


if __name__ == "__main__":
    unittest.main()
