"""Ingest review comments and write review-cycle state."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.comment_store import (
    CommentStore,
    CommentStoreError,
    make_reply,
    validate_comments_payload,
)
from scripts.html_review_workbench.common import (
    now_iso,
    resolve_bundle_json_path as _resolve_bundle_json_path,
    write_json,
)
from scripts.html_review_workbench.resolution_gate import GATE_STATUS_VALUES


DEFAULT_STATE_PATH = "annotations/review-cycle-state.json"
DEFAULT_AGENT_AUTHOR = "codex"

COMMENT_STATUS_VALUES = GATE_STATUS_VALUES

_REPLACEMENT_PATTERNS = (
    re.compile(r"replace\s+['\"](?P<old>.+?)['\"]\s+with\s+['\"](?P<new>.+?)['\"]", re.IGNORECASE),
    re.compile(r"replace\s+selected\s+text\s+with\s+['\"](?P<new>.+?)['\"]", re.IGNORECASE),
)


class ReviewIngestionError(ValueError):
    """Raised when review ingestion cannot be completed."""


@dataclass(frozen=True)
class ReviewIngestionResult:
    payload: dict[str, Any]
    comments_path: Path
    state_path: Path
    model_path: Path | None = None


def ingest_review(
    root: Path,
    *,
    comments_path: str = "annotations/comments.json",
    state_path: str = DEFAULT_STATE_PATH,
    model_path: Path | None = None,
    apply_model: bool = False,
    agent_author: str = DEFAULT_AGENT_AUTHOR,
) -> ReviewIngestionResult:
    root = root.resolve()
    store = CommentStore(root, comments_path)
    payload = store.read("document")
    validate_comments_payload(payload)

    threads = payload["comments"]
    replies_added = 0

    model_update_result: dict[str, Any] = {"applied": 0, "skipped": []}
    resolved_model_path = None
    if model_path is not None:
        resolved_model_path = model_path.resolve()
        if not apply_model:
            model_update_result = {"applied": 0, "skipped": ["model updates require --apply-model"]}
        elif _count_status(threads)["needs_agent_review"]:
            # 返信待ちが 1 件でも残る間は文書を変えない。gate が blocked のまま
            # 先に model を書き換えると、返信 → 反映の順序が壊れるため
            model_update_result = {
                "applied": 0,
                "skipped": ["gate is blocked: threads await an agent reply"],
            }
        else:
            model_update_result = apply_limited_model_updates(resolved_model_path, threads)
            replies_added += add_implementation_replies(
                payload,
                model_update_result.get("applied_comment_ids", []),
                agent_author=agent_author,
            )

    store.write(payload)

    state = build_review_cycle_state(
        document_id=str(payload["document_id"]),
        comments_path=comments_path,
        threads=threads,
        replies_added=replies_added,
        model_updates=model_update_result,
    )
    resolved_state_path = resolve_bundle_json_path(root, state_path)
    write_json(resolved_state_path, state, ensure_parent=True)

    from scripts.html_review_workbench.resolution_gate import try_check_gate

    gate_result = try_check_gate(root, comments_path=comments_path)
    if gate_result is not None:
        gate_payload = gate_result.to_payload()
    else:
        gate_payload = {"gate": "unknown"}

    return ReviewIngestionResult(
        payload={
            "status": "ok",
            "document_id": payload["document_id"],
            "comments_path": comments_path,
            "state_path": state_path,
            "summary": state["summary"],
            "model_updates": model_update_result,
            "gate": gate_payload,
        },
        comments_path=store.path,
        state_path=resolved_state_path,
        model_path=resolved_model_path,
    )


def build_review_cycle_state(
    *,
    document_id: str,
    comments_path: str,
    threads: list[dict[str, Any]],
    replies_added: int,
    model_updates: dict[str, Any],
) -> dict[str, Any]:
    counts = _count_status(threads)
    return {
        "schema_version": "2.0",
        "document_id": document_id,
        "comments_path": comments_path,
        "generated_at": now_iso(),
        "summary": {
            "total": len(threads),
            **counts,
            "replies_added": replies_added,
            "model_updates_applied": model_updates.get("applied", 0),
        },
        "needs_agent_review_ids": [
            thread["id"] for thread in threads if thread.get("status") == "needs_agent_review"
        ],
        "resolved_ids": [thread["id"] for thread in threads if thread.get("status") == "resolved"],
        "replacement_hints": replacement_hints(threads),
        "model_updates": model_updates,
    }


def replacement_hints(threads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """コメント本文から機械的に取り出せる置換指示だけを集める。

    分類の推定はしない。`replace "x" with "y"` の形が書かれた thread だけが残る。
    """
    hints: list[dict[str, Any]] = []
    for thread in threads:
        replacement = extract_replacement(thread)
        if replacement is None:
            continue
        hints.append(
            {
                "comment_id": thread["id"],
                "block_id": thread["block_id"],
                "status": thread.get("status", ""),
                "replacement": replacement,
            }
        )
    return hints


def apply_limited_model_updates(
    model_path: Path, threads: list[dict[str, Any]]
) -> dict[str, Any]:
    try:
        model = json.loads(model_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReviewIngestionError(f"document model is invalid JSON: {model_path}") from exc
    if not isinstance(model, dict) or not isinstance(model.get("blocks"), list):
        raise ReviewIngestionError("document model must contain a blocks array")

    applied = 0
    applied_comment_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for thread in threads:
        comment_id = thread["id"]
        # 解決済みのスレッドだけを反映する。未解決の指摘を先回りで適用しない
        if thread.get("status") != "resolved":
            skipped.append({"comment_id": comment_id, "reason": "thread_not_resolved"})
            continue
        replacement = extract_replacement(thread)
        if replacement is None:
            skipped.append({"comment_id": comment_id, "reason": "no_limited_replacement"})
            continue
        block = _find_model_block(model["blocks"], thread["block_id"])
        if block is None:
            skipped.append({"comment_id": comment_id, "reason": "block_not_found"})
            continue
        content = block.get("content")
        if not isinstance(content, str):
            skipped.append({"comment_id": comment_id, "reason": "block_content_not_string"})
            continue
        old = replacement["old"]
        new = replacement["new"]
        if old not in content:
            skipped.append({"comment_id": comment_id, "reason": "selected_text_not_found"})
            continue
        block["content"] = content.replace(old, new, 1)
        applied += 1
        applied_comment_ids.append(comment_id)

    if applied:
        write_json(model_path, model)
    return {"applied": applied, "applied_comment_ids": applied_comment_ids, "skipped": skipped}


def add_implementation_replies(
    payload: dict[str, Any],
    applied_comment_ids: object,
    *,
    agent_author: str,
) -> int:
    if not isinstance(applied_comment_ids, list):
        return 0
    applied_ids = {comment_id for comment_id in applied_comment_ids if isinstance(comment_id, str)}
    if not applied_ids:
        return 0
    replies_added = 0
    for thread in payload["comments"]:
        if thread["id"] not in applied_ids:
            continue
        if _has_agent_implementation_reply(thread):
            continue
        thread["replies"].append(
            make_reply(
                author=agent_author,
                role="agent",
                kind="implementation_note",
                body=implementation_reply_body(extract_replacement(thread)),
            )
        )
        replies_added += 1
    return replies_added


def implementation_reply_body(replacement: object) -> str:
    if isinstance(replacement, dict) and replacement.get("old") and replacement.get("new"):
        return f"Applied replacement: {replacement['old']} -> {replacement['new']}"
    return "Applied this review comment."


def extract_replacement(thread: dict[str, Any]) -> dict[str, str] | None:
    comment = str(thread.get("comment", ""))
    selected_text = str(thread.get("selected_text", ""))
    for pattern in _REPLACEMENT_PATTERNS:
        match = pattern.search(comment)
        if not match:
            continue
        old = match.groupdict().get("old") or selected_text
        new = match.group("new")
        if old and new:
            return {"operation": "replace_text", "old": old, "new": new}
    return None


def resolve_bundle_json_path(root: Path, relative_path: str) -> Path:
    return _resolve_bundle_json_path(root, relative_path, label="state", error=ReviewIngestionError)


def _count_status(threads: list[dict[str, Any]]) -> dict[str, int]:
    counts = {value: 0 for value in COMMENT_STATUS_VALUES}
    for thread in threads:
        status = thread.get("status", "")
        if status in counts:
            counts[status] += 1
    return counts


def _find_model_block(blocks: list[Any], block_id: str) -> dict[str, Any] | None:
    for block in blocks:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    return None


def _has_agent_implementation_reply(thread: dict[str, Any]) -> bool:
    return any(
        isinstance(reply, dict) and reply.get("role") == "agent" and reply.get("kind") == "implementation_note"
        for reply in thread.get("replies", [])
    )
