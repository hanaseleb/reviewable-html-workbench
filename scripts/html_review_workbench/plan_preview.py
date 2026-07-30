"""Ephemeral plan preview support for Plan Mode helper views."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.common import now_iso, pid_is_alive, write_json
from scripts.html_review_workbench.markdown_lite import (
    Section,
    heading_texts,
    normalize_heading_text,
    split_sections,
    to_html,
)
from scripts.html_review_workbench.preview_server import PreviewConfigurationError, PreviewMode, start_preview
from scripts.html_review_workbench.render import render_bundle
from scripts.html_review_workbench.validate_bundle import validate_bundle


MAX_PAYLOAD_BYTES = 512 * 1024
MARKER_FILE = ".rhw-plan-preview"
ROOT_PREFIX = "rhw-plan-preview-"
PLAN_PREVIEW_SENTINEL_DIR_NAME = "claude-plan-preview"
DEFAULT_TTL_SECONDS = 1800.0
_CLEANUP_WATCHERS: list[subprocess.Popen[bytes]] = []


class PlanPreviewError(ValueError):
    """Raised when a plan preview cannot be created or cleaned up."""


@dataclass(frozen=True)
class PlanPreviewResult:
    id: str
    url: str
    root: Path
    pid: int
    ttl: float
    expires_at: str
    stop_command: str
    process: subprocess.Popen[bytes] | None = None
    cleanup_process: subprocess.Popen[bytes] | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "status": "running",
            "ephemeral": True,
            "id": self.id,
            "url": self.url,
            "root": str(self.root),
            "pid": self.pid,
            "ttl": self.ttl,
            "expires_at": self.expires_at,
            "stop_command": self.stop_command,
        }


@dataclass(frozen=True)
class NormalizedPlanDiagram:
    after_heading: str
    mermaid: str
    title: str


@dataclass(frozen=True)
class NormalizedPlanPreviewPayload:
    title: str
    source_text: str
    diagrams: tuple[NormalizedPlanDiagram, ...] = ()


def read_payload(source: str | None) -> dict[str, Any]:
    if source in (None, "-"):
        raw = sys.stdin.buffer.read(MAX_PAYLOAD_BYTES + 1)
    else:
        path = Path(source)
        raw = path.read_bytes()
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise PlanPreviewError("plan preview payload exceeds 512 KiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanPreviewError(f"plan preview payload is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanPreviewError("plan preview payload must be a JSON object")
    _reject_remote_assets(payload)
    return payload


def create_plan_preview(
    payload: dict[str, Any],
    ttl: float = DEFAULT_TTL_SECONDS,
    mode: PreviewMode = "auto",
    preview_starter: Any = start_preview,
    cleanup_starter: Any = None,
    bundle_validator: Any = validate_bundle,
) -> PlanPreviewResult:
    if ttl <= 0:
        raise PlanPreviewError("ttl must be positive")
    if cleanup_starter is None:
        cleanup_starter = _start_cleanup_watcher
    normalized = validate_plan_preview_payload(payload)
    preview_id = uuid.uuid4().hex[:12]
    root = Path(tempfile.mkdtemp(prefix=ROOT_PREFIX)).resolve()
    _assert_plan_preview_root(root)
    write_json(root / MARKER_FILE, {"id": preview_id, "created_at": now_iso()}, indent=None)

    model = build_plan_preview_model(normalized, preview_id)
    model_path = root / "document-model.json"
    try:
        write_json(model_path, model)
        render_bundle(model_path, root)
        _validate_rendered_bundle(root, bundle_validator)
    except (OSError, ValueError, PlanPreviewError):
        shutil.rmtree(root, ignore_errors=True)
        raise
    session = preview_starter(root, mode, idle_timeout=ttl)
    expires_at = (now_iso_datetime() + timedelta(seconds=ttl)).isoformat()
    cleanup_process = cleanup_starter(root, session.pid, ttl)
    _write_plan_preview_sentinel(preview_id)
    return PlanPreviewResult(
        id=preview_id,
        url=session.url,
        root=root,
        pid=session.pid,
        ttl=ttl,
        expires_at=expires_at,
        stop_command=(
            "python3 -m scripts.html_review_workbench.cli plan-preview-stop "
            f"--root {root} --pid {session.pid}"
        ),
        process=session.process,
        cleanup_process=cleanup_process,
    )


def validate_plan_preview_payload(payload: dict[str, Any]) -> NormalizedPlanPreviewPayload:
    allowed_keys = {"title", "source_text", "diagrams"}
    unknown_keys = sorted(set(payload) - allowed_keys)
    if unknown_keys:
        joined = ", ".join(unknown_keys)
        raise PlanPreviewError(
            f"plan preview payload has unsupported key(s): {joined}; "
            "new plan previews must pass the original markdown in source_text"
        )
    title = _optional_string(payload.get("title"))
    source_text = _optional_string(payload.get("source_text"))
    if not source_text:
        raise PlanPreviewError("plan preview payload requires non-empty source_text")

    diagrams_value = payload.get("diagrams", [])
    if diagrams_value is None:
        diagrams_value = []
    if not isinstance(diagrams_value, list):
        raise PlanPreviewError("plan preview diagrams must be a list")
    diagrams: list[NormalizedPlanDiagram] = []
    for index, diagram in enumerate(diagrams_value, 1):
        if not isinstance(diagram, dict):
            raise PlanPreviewError(f"plan preview diagram {index} must be an object")
        unknown_diagram_keys = sorted(set(diagram) - {"after_heading", "title", "mermaid"})
        if unknown_diagram_keys:
            joined = ", ".join(unknown_diagram_keys)
            raise PlanPreviewError(f"plan preview diagram {index} has unsupported key(s): {joined}")
        after_heading = _optional_string(diagram.get("after_heading"))
        mermaid = _optional_string(diagram.get("mermaid"))
        if not after_heading or not mermaid:
            raise PlanPreviewError(
                f"plan preview diagram {index} requires non-empty after_heading and mermaid"
            )
        title_value = _optional_string(diagram.get("title")) or f"図: {after_heading}"
        diagrams.append(
            NormalizedPlanDiagram(
                after_heading=normalize_heading_text(after_heading),
                mermaid=mermaid,
                title=title_value,
            )
        )
    return NormalizedPlanPreviewPayload(title=title, source_text=source_text, diagrams=tuple(diagrams))


def build_plan_preview_model(payload: NormalizedPlanPreviewPayload, preview_id: str) -> dict[str, Any]:
    document_title, sections = split_sections(payload.source_text)
    title = payload.title or document_title or "Plan Preview"
    summary = "Proposed plan preview (original structure preserved)."
    blocks = _build_section_blocks(sections)
    blocks = _insert_diagrams(blocks, sections, payload.diagrams)
    return {
        "schema_version": "1.0",
        "document_id": f"plan-preview-{preview_id}",
        "title": title,
        "generated_at": now_iso(),
        "summary": summary,
        "metadata": {
            "status": "draft",
            "status_label": "Plan preview",
            "eyebrow": "RHW Plan Preview",
            "lang": "ja",
        },
        "blocks": blocks,
    }


def _build_section_blocks(sections: list[Section]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, section in enumerate(sections, 1):
        block_id = "plan-section-0" if section.is_preamble else f"plan-section-{index}"
        block: dict[str, Any] = {
            "id": block_id,
            "type": "html",
            "heading_level": 2,
            "content": to_html(section.body),
            "review_required": True,
        }
        if not section.is_preamble and section.heading_text:
            block["title"] = section.heading_text
        blocks.append(block)
    return blocks


def _insert_diagrams(
    blocks: list[dict[str, Any]],
    sections: list[Section],
    diagrams: tuple[NormalizedPlanDiagram, ...],
) -> list[dict[str, Any]]:
    if not diagrams:
        return blocks
    output = list(blocks)
    inserted = 0
    for diagram_index, diagram in enumerate(diagrams, 1):
        section_index = _find_diagram_section(sections, diagram.after_heading)
        if section_index is None:
            raise PlanPreviewError(
                f"plan preview diagram after_heading not found in source_text: {diagram.after_heading}"
            )
        output.insert(
            section_index + 1 + inserted,
            {
                "id": f"plan-diagram-{diagram_index}",
                "type": "diagram",
                "heading_level": 3,
                "title": diagram.title,
                "content": diagram.mermaid,
                "review_required": True,
            },
        )
        inserted += 1
    return output


def _find_diagram_section(sections: list[Section], after_heading: str) -> int | None:
    normalized = normalize_heading_text(after_heading)
    for index, section in enumerate(sections):
        candidates = [section.heading_text, *heading_texts(section.body)]
        if normalized in candidates:
            return index
    return None


def _validate_rendered_bundle(root: Path, bundle_validator: Any) -> None:
    result = bundle_validator(root)
    if result.ok:
        return
    details = "; ".join(str(error) for error in result.errors) or "unknown error"
    raise PlanPreviewError(f"plan preview bundle validation failed: {details}")


def stop_plan_preview(
    root: Path,
    pid: int | None = None,
    process: subprocess.Popen[bytes] | None = None,
    cleanup_process: subprocess.Popen[bytes] | None = None,
) -> dict[str, object]:
    root = root.resolve()
    _assert_plan_preview_root(root)
    stopped = False
    if pid is not None and pid_is_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            stopped = True
        except PermissionError as exc:
            raise PlanPreviewError(f"cannot stop plan preview pid {pid}: {exc}") from exc
    if process is not None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.kill(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
    if cleanup_process is not None and cleanup_process.poll() is None:
        try:
            os.kill(cleanup_process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        cleanup_process.wait(timeout=5)
    _cleanup_root(root)
    return {"status": "stopped", "root": str(root), "pid": pid, "process_signalled": stopped}


def _optional_string(value: object) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _reject_remote_assets(payload: dict[str, Any]) -> None:
    for key in ("assets", "images", "remote_assets", "remote_asset_urls"):
        if key in payload:
            raise PlanPreviewError(f"plan preview payload must not include {key}")


def _assert_plan_preview_root(root: Path) -> None:
    resolved = root.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root not in resolved.parents:
        raise PlanPreviewError("plan preview root must be under the system temp directory")
    if not resolved.name.startswith(ROOT_PREFIX):
        raise PlanPreviewError(f"plan preview root must start with {ROOT_PREFIX}")
    if not (resolved / MARKER_FILE).exists() and resolved.exists():
        # Creation path calls this before writing the marker.
        if any(resolved.iterdir()):
            raise PlanPreviewError("plan preview root is missing marker")


def _cleanup_root(root: Path) -> None:
    _assert_plan_preview_root(root)
    if not (root / MARKER_FILE).exists():
        raise PlanPreviewError("refusing to clean unmarked plan preview root")
    shutil.rmtree(root)


def _start_cleanup_watcher(root: Path, pid: int, ttl: float) -> subprocess.Popen[bytes]:
    code = (
        "import os, signal, shutil, sys, time\n"
        "pid=int(sys.argv[1]); root=sys.argv[2]; ttl=float(sys.argv[3])\n"
        "time.sleep(ttl)\n"
        "try:\n"
        "    os.kill(pid, signal.SIGTERM)\n"
        "except ProcessLookupError:\n"
        "    pass\n"
        "except PermissionError:\n"
        "    pass\n"
        "marker=os.path.join(root, '.rhw-plan-preview')\n"
        "if os.path.basename(root).startswith('rhw-plan-preview-') and os.path.exists(marker):\n"
        "    shutil.rmtree(root, ignore_errors=True)\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", code, str(pid), str(root), str(ttl)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _CLEANUP_WATCHERS.append(process)
    return process


def _plan_preview_sentinel_path() -> Path | None:
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id or "/" in session_id or session_id in {".", ".."}:
        return None
    sentinel_dir = Path(tempfile.gettempdir()) / PLAN_PREVIEW_SENTINEL_DIR_NAME
    return sentinel_dir / session_id


def _write_plan_preview_sentinel(preview_id: str) -> None:
    sentinel = _plan_preview_sentinel_path()
    if sentinel is None:
        return
    write_json(
        sentinel,
        {"preview_id": preview_id, "created_at": now_iso()},
        ensure_parent=True,
        indent=None,
    )


def _remove_plan_preview_sentinel() -> None:
    """Remove the test-visible session sentinel if one was written."""
    sentinel = _plan_preview_sentinel_path()
    if sentinel is None:
        return
    sentinel.unlink(missing_ok=True)


def now_iso_datetime() -> "datetime":
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
