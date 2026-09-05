"""Build a reviewable HTML bundle from a PPTX file."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree

from scripts.html_review_workbench.comment_store import CommentStore, empty_comments
from scripts.html_review_workbench.common import now_iso, write_json
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


PRESENTATION_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
SLIDE_IMAGE_RE = re.compile(r"slide-(\d+)\.png$")


class PptxReviewError(ValueError):
    """Raised when a PPTX review bundle cannot be built safely."""


@dataclass(frozen=True)
class PptxReviewResult:
    output: Path
    model: Path
    index: Path
    slide_count: int
    document_id: str

    def to_payload(self) -> dict[str, object]:
        return {
            "status": "ok",
            "output": str(self.output),
            "model": str(self.model),
            "index": str(self.index),
            "slide_count": self.slide_count,
            "document_id": self.document_id,
        }


def build_pptx_review(
    pptx_path: Path,
    output_dir: Path,
    *,
    title: str | None = None,
    lang: str = "ja",
    dpi: int = 150,
    continue_review: bool = False,
) -> PptxReviewResult:
    pptx_path = pptx_path.resolve()
    output_dir = output_dir.resolve()
    if not pptx_path.is_file():
        raise PptxReviewError(f"PPTX file not found: {pptx_path}")
    if pptx_path.suffix.lower() != ".pptx":
        raise PptxReviewError(f"input must be a .pptx file: {pptx_path}")
    if lang not in {"ja", "en"}:
        raise PptxReviewError("lang must be ja or en")
    if not 72 <= dpi <= 300:
        raise PptxReviewError("dpi must be between 72 and 300")

    slide_ids, aspect_ratio = read_slide_ids_and_aspect_ratio(pptx_path)
    source_sha256 = hashlib.sha256(pptx_path.read_bytes()).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "document-model.json"
    existing_model = _read_existing_model(model_path)
    document_id = _existing_document_id(existing_model) or f"pptx-{source_sha256[:12]}"
    _check_review_continuation(
        output_dir,
        existing_model,
        source_sha256,
        {f"slide-{slide_id}" for slide_id in slide_ids},
        continue_review,
    )

    with tempfile.TemporaryDirectory(prefix="rhw-pptx-") as tmp:
        tmp_dir = Path(tmp)
        pdf_path = _convert_to_pdf(pptx_path, tmp_dir)
        rendered = _render_pdf_to_pngs(pdf_path, tmp_dir / "rendered", dpi)
        if len(rendered) != len(slide_ids):
            raise PptxReviewError(
                f"PPTX contains {len(slide_ids)} slides but conversion produced {len(rendered)} PNG files"
            )
        slide_dir = output_dir / "pptx-slides"
        slide_dir.mkdir(parents=True, exist_ok=True)
        for old in slide_dir.glob("slide-*.png"):
            old.unlink()
        for number, source in enumerate(rendered, 1):
            shutil.copy2(source, slide_dir / f"slide-{number:03d}.png")

    generated_at = now_iso()
    blocks = []
    slide_map = []
    for number, slide_id in enumerate(slide_ids, 1):
        block_id = f"slide-{slide_id}"
        relative_image = f"pptx-slides/slide-{number:03d}.png"
        label = f"スライド {number}" if lang == "ja" else f"Slide {number}"
        blocks.append(
            {
                "id": block_id,
                "type": "image",
                "title": label,
                "heading_level": 2,
                "content": label,
                "review_required": True,
                "image": {
                    "prompt": f"Rendered preview of {label}",
                    "alt": label,
                    "caption": label,
                    "generation_status": "generated",
                    "source_path": relative_image,
                    "generated_at": generated_at,
                    "aspect_ratio": aspect_ratio,
                },
            }
        )
        slide_map.append({"block_id": block_id, "slide_number": number, "slide_id": slide_id})

    model = {
        "schema_version": "1.0",
        "document_id": document_id,
        "title": title or pptx_path.stem,
        "summary": (
            "各スライド画像をクリックして修正コメントを追加してください。"
            if lang == "ja"
            else "Click a slide image to add review comments."
        ),
        "generated_at": generated_at,
        "metadata": {
            "lang": lang,
            "eyebrow": "PPTX Review",
            "deck": pptx_path.name,
            "status": "draft",
            "status_label": "レビュー中" if lang == "ja" else "In review",
            "pptx": {
                "source_name": pptx_path.name,
                "source_sha256": source_sha256,
                "dpi": dpi,
                "slide_count": len(slide_ids),
                "slides": slide_map,
            },
        },
        "review_settings": {"enabled": True, "mode": "review-server"},
        "blocks": blocks,
    }
    write_json(model_path, model)

    comments_path = output_dir / "annotations" / "comments.json"
    if not comments_path.is_file():
        CommentStore(output_dir).write(empty_comments(document_id))

    for stale in (output_dir / "assets" / "images").glob("slide-*.png"):
        stale.unlink()
    index_path = render_bundle(model_path, output_dir)
    validation = validate_bundle(output_dir)
    if not validation.ok:
        raise PptxReviewError("generated review bundle is invalid: " + "; ".join(validation.errors))
    return PptxReviewResult(output_dir, model_path, index_path, len(slide_ids), document_id)


def read_slide_ids_and_aspect_ratio(pptx_path: Path) -> tuple[list[str], float]:
    try:
        with zipfile.ZipFile(pptx_path) as archive:
            root = ElementTree.fromstring(archive.read("ppt/presentation.xml"))
    except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise PptxReviewError(f"invalid PPTX package: {pptx_path}") from exc

    slide_list = root.find(f"{{{PRESENTATION_NS}}}sldIdLst")
    if slide_list is None:
        raise PptxReviewError("PPTX has no slide list")
    slide_ids = [str(node.get("id")) for node in slide_list if node.get("id")]
    if not slide_ids:
        raise PptxReviewError("PPTX contains no slides")

    slide_size = root.find(f"{{{PRESENTATION_NS}}}sldSz")
    try:
        aspect_ratio = int(slide_size.get("cx")) / int(slide_size.get("cy"))  # type: ignore[union-attr]
    except (AttributeError, TypeError, ValueError, ZeroDivisionError):
        aspect_ratio = 16 / 9
    return slide_ids, round(aspect_ratio, 6)


def _convert_to_pdf(pptx_path: Path, tmp_dir: Path) -> Path:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable is None:
        raise PptxReviewError("LibreOffice (soffice) is required to render PPTX files")
    profile_dir = tmp_dir / "libreoffice-profile"
    profile_dir.mkdir()
    command = [
        executable,
        f"-env:UserInstallation={profile_dir.as_uri()}",
        "--headless",
        "--convert-to",
        'pdf:impress_pdf_Export:{"ExportHiddenSlides":{"type":"boolean","value":"true"}}',
        "--outdir",
        str(tmp_dir),
        str(pptx_path),
    ]
    _run(command, "LibreOffice PPTX conversion")
    pdf_path = tmp_dir / f"{pptx_path.stem}.pdf"
    if not pdf_path.is_file():
        raise PptxReviewError("LibreOffice did not produce a PDF")
    return pdf_path


def _render_pdf_to_pngs(pdf_path: Path, output_dir: Path, dpi: int) -> list[Path]:
    executable = shutil.which("pdftoppm")
    if executable is None:
        raise PptxReviewError("Poppler (pdftoppm) is required to render slide PNGs")
    output_dir.mkdir()
    _run([executable, "-png", "-r", str(dpi), str(pdf_path), str(output_dir / "slide")], "PDF rendering")
    images = []
    for path in output_dir.glob("slide-*.png"):
        match = SLIDE_IMAGE_RE.match(path.name)
        if match:
            images.append((int(match.group(1)), path))
    return [path for _, path in sorted(images)]


def _run(command: list[str], label: str) -> None:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as exc:
        raise PptxReviewError(f"{label} timed out") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise PptxReviewError(f"{label} failed: {detail or f'exit {result.returncode}'}")


def _read_existing_model(model_path: Path) -> dict[str, object] | None:
    if not model_path.is_file():
        return None
    try:
        value = json.loads(model_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _existing_document_id(model: dict[str, object] | None) -> str | None:
    value = model.get("document_id") if model else None
    return value if isinstance(value, str) and value else None


def _check_review_continuation(
    output_dir: Path,
    existing_model: dict[str, object] | None,
    source_sha256: str,
    new_block_ids: set[str],
    continue_review: bool,
) -> None:
    if existing_model is None:
        return
    metadata = existing_model.get("metadata")
    pptx = metadata.get("pptx") if isinstance(metadata, dict) else None
    previous_sha256 = pptx.get("source_sha256") if isinstance(pptx, dict) else None
    if previous_sha256 == source_sha256:
        return
    if not continue_review:
        raise PptxReviewError(
            "output already contains a different PPTX review; use --continue-review only for its verified revision"
        )
    comments = CommentStore(output_dir).read(_existing_document_id(existing_model) or "document")
    orphaned = sorted(
        thread["block_id"]
        for thread in comments.get("comments", [])
        if thread.get("status") != "resolved" and thread.get("block_id") not in new_block_ids
    )
    if orphaned:
        raise PptxReviewError("revised PPTX no longer contains unresolved reviewed slides: " + ", ".join(orphaned))
