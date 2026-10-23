from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.html_review_workbench.pptx_review import PptxReviewError, build_pdf_review


class PdfReviewTest(unittest.TestCase):
    def test_builds_page_blocks_and_fixes_final_format_to_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pdf"
            source.write_bytes(b"%PDF-1.7\n")
            pages = [_png(root / "one.png", 1600, 900), _png(root / "two.png", 1200, 1200)]

            with patch("scripts.html_review_workbench.pptx_review._render_pdf_to_pngs", return_value=pages):
                result = build_pdf_review(source, root / "review")

            model = json.loads((root / "review/document-model.json").read_text())
            self.assertEqual([block["id"] for block in model["blocks"]], ["page-001", "page-002"])
            self.assertEqual(model["metadata"]["pdf"]["final_format"], "pdf")
            self.assertEqual(model["blocks"][0]["image"]["aspect_ratio"], 1.777778)
            self.assertEqual(model["blocks"][1]["image"]["aspect_ratio"], 1.0)
            self.assertEqual(result.slide_count, 2)

    def test_rejects_invalid_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "deck.pdf"
            source.write_bytes(b"not a pdf")
            with self.assertRaisesRegex(PptxReviewError, "valid .pdf"):
                build_pdf_review(source, Path(tmp) / "review")


def _png(path: Path, width: int, height: int) -> Path:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height))
    return path


if __name__ == "__main__":
    unittest.main()
