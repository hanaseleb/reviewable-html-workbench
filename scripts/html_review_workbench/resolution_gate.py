"""Resolution gate: block document edits while threads await an agent reply."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.html_review_workbench.comment_store import CommentStore

# comments.json が取りうる status。UI と comment_store の遷移と同じ 3 値。
GATE_STATUS_VALUES = ("needs_agent_review", "needs_user_reply", "resolved")


@dataclass(frozen=True)
class GateResult:
    gate: str
    needs_agent_review_threads: list[str]
    resolved_threads: list[str]
    status_counts: dict[str, int]

    def to_payload(self) -> dict[str, Any]:
        # 空でも全 key を出す。key を省くと返信待ち無しの時に {"gate": "open"} へ
        # 縮退し、watch-comments の通知行から判断材料が消えるため
        return {
            "gate": self.gate,
            "needs_agent_review_threads": list(self.needs_agent_review_threads),
            "resolved_threads": list(self.resolved_threads),
            "status_counts": dict(self.status_counts),
        }


def check_gate(
    root: Path,
    comments_path: str = "annotations/comments.json",
) -> GateResult:
    """Check whether the resolution gate is open or blocked.

    The gate is **blocked** when any thread has status ``needs_agent_review``
    (the user is waiting for an agent reply).  ``status`` is maintained by
    :mod:`comment_store` on every reply, so it is the only input here: comment
    text, surrounding document text and reply order are deliberately ignored.
    """
    root = root.resolve()
    store = CommentStore(root, comments_path)
    payload = store.read("document")

    status_counts = {value: 0 for value in GATE_STATUS_VALUES}
    needs_agent_review_threads: list[str] = []
    resolved_threads: list[str] = []

    for thread in payload.get("comments", []):
        thread_id = thread.get("id", "")
        status = thread.get("status", "")
        if status in status_counts:
            status_counts[status] += 1
        if status == "needs_agent_review":
            needs_agent_review_threads.append(thread_id)
        elif status == "resolved":
            resolved_threads.append(thread_id)

    gate = "blocked" if needs_agent_review_threads else "open"
    return GateResult(
        gate=gate,
        needs_agent_review_threads=needs_agent_review_threads,
        resolved_threads=resolved_threads,
        status_counts=status_counts,
    )


def try_check_gate(
    root: Path,
    comments_path: str = "annotations/comments.json",
) -> GateResult | None:
    try:
        return check_gate(root, comments_path=comments_path)
    except Exception:
        return None
