"""Runtime HTTP serving primitives for preview sessions."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import threading
import time
from collections import deque
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scripts.html_review_workbench.comment_store import CommentStore, CommentStoreError
from scripts.html_review_workbench.common import pid_is_alive
from scripts.html_review_workbench.event_bus import EventBus, format_sse

DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS = 24 * 60 * 60


STATE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def resolve_sse_start_id(header_value: str | None, current_last_id: int) -> int:
    """SSE でどのイベントから送り始めるかを決める。

    初回接続 (Last-Event-ID が無い) では履歴を送らず、今の位置から始める。
    ブラウザは初回接続でこの header を送らないため、ここで 0 を返すと EventBus が
    保持している過去の document_updated が再送され、更新バナーの「リロード」を押した
    直後にまた同じバナーが出てしまう。
    再接続 (header あり) では受け取り済みの次から送り、切断中のイベントを取りこぼさない。
    """
    if header_value is None:
        return current_last_id
    try:
        return int(header_value)
    except ValueError:
        return current_last_id


class CommentChangeTracker:
    """server 経由で通知済みの comments.json 変更 (mtime) を記録する。

    add-reply などの書き手は、ファイルを書いた後に自分で comment_updated を配信する。
    file_watcher が同じ変更を mtime で再検知してもう一度配信すると、source:"agent" の
    filter を素通りする複製イベントになり、書いた本人に「新着」通知が届いてしまう。
    通知済みの mtime を覚えておき、file_watcher はそれと一致する変化を配信しない。
    記録に無い mtime (エディタでの直接編集など) は今までどおり配信される。
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._announced: deque[float] = deque(maxlen=8)

    def announce(self, mtime: float) -> None:
        if mtime <= 0:
            return
        with self._lock:
            self._announced.append(mtime)

    def should_publish(self, mtime: float) -> bool:
        with self._lock:
            return mtime not in self._announced


class ReviewPreviewHandler(SimpleHTTPRequestHandler):
    comments_route = "/annotations/comments.json"
    checklist_route = "/annotations/checklist-state.json"
    state_route_prefix = "/annotations/state/"
    events_route = "/events"
    _last_activity: float = 0.0
    _lock = threading.Lock()

    @classmethod
    def touch_activity(cls) -> None:
        with cls._lock:
            cls._last_activity = time.monotonic()

    @classmethod
    def seconds_since_last_activity(cls) -> float:
        with cls._lock:
            if cls._last_activity == 0.0:
                return 0.0
            return time.monotonic() - cls._last_activity

    def __init__(
        self,
        *args: object,
        root: Path,
        event_bus: EventBus,
        change_tracker: CommentChangeTracker | None = None,
        **kwargs: object,
    ) -> None:
        self.root = root.resolve()
        self.store = CommentStore(self.root)
        self.event_bus = event_bus
        self.change_tracker = change_tracker or CommentChangeTracker()
        super().__init__(*args, directory=str(self.root), **kwargs)

    def _comments_mtime(self) -> float:
        try:
            return (self.root / "annotations" / "comments.json").stat().st_mtime
        except OSError:
            return 0.0

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:
        self.touch_activity()
        path = self._path()
        if path == self.comments_route:
            payload = self.store.read(self._document_id())
            self._send_json(payload, headers={"ETag": _comments_etag(payload)})
            return
        if path == self.events_route:
            self._handle_sse()
            return
        super().do_GET()

    def do_PUT(self) -> None:
        self.touch_activity()
        if self._path() == self.checklist_route:
            self._handle_checklist_put()
            return
        if self._path().startswith(self.state_route_prefix):
            self._handle_state_put(self._path())
            return
        if self._path() != self.comments_route:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            payload = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
            with self.store.locked():
                current = self.store.read(self._document_id())
                expected = self.headers.get("If-Match")
                if expected and expected != _comments_etag(current):
                    self._send_json(
                        {"ok": False, "error": "comments changed since they were loaded; reload and retry"},
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                self.store.write(payload)
        except (json.JSONDecodeError, CommentStoreError, OSError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        # この書き込みはこの場で配信するので、file_watcher が再配信しないよう記録する
        self.change_tracker.announce(self._comments_mtime())
        source = self.headers.get("X-Comment-Source", "browser")
        self.event_bus.publish("comment_updated", {"source": source})
        self._send_json(
            {"ok": True, "path": "annotations/comments.json"},
            headers={"ETag": _comments_etag(payload)},
        )

    def do_POST(self) -> None:
        self.touch_activity()
        if self._path() != self.events_route:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            body = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
        except (json.JSONDecodeError, CommentStoreError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        event_type = body.get("type", "custom")
        data = {k: v for k, v in body.items() if k != "type"}
        if event_type == "comment_updated":
            # 送信者がファイルを書いた直後の通知。file_watcher の再検知を配信させない
            self.change_tracker.announce(self._comments_mtime())
        self.event_bus.publish(event_type, data)
        self._send_json({"ok": True, "event_type": event_type})

    def _handle_checklist_put(self) -> None:
        """作業チェックリストの状態を保存する。

        読み出しは静的配信をそのまま使うため、ここでは書き込みだけを扱う。
        端末をまたいで同じ状態を見せることが目的で、同時更新は後勝ちとする。
        """
        try:
            payload = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("state"), dict):
            self._send_json(
                {"ok": False, "error": "checklist payload must contain a state object"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        target = self.root / "annotations" / "checklist-state.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._send_json({"ok": True, "path": "annotations/checklist-state.json"})

    def _handle_state_put(self, path: str) -> None:
        """操作部品が触った結果を任意の名前で保存する。

        `PUT /annotations/state/<name>.json` を受け、`annotations/state/<name>.json` へ書く。
        名前は英数字とハイフン・アンダースコアだけに限り、path traversal を防ぐ。
        読み出しは静的配信をそのまま使うため、ここでは書き込みだけを扱う。
        端末をまたいで同じ状態を見せることが目的で、同時更新は後勝ちとする。
        """
        name = path[len(self.state_route_prefix) :]
        if not name.endswith(".json") or not STATE_NAME_RE.match(name[: -len(".json")]):
            self._send_json(
                {"ok": False, "error": "state name must match [A-Za-z0-9][A-Za-z0-9_-]{0,63}.json"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        try:
            payload = json.loads(self.rfile.read(_content_length(self)).decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(payload, dict) or not isinstance(payload.get("state"), dict):
            self._send_json(
                {"ok": False, "error": "state payload must contain a state object"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        target = self.root / "annotations" / "state" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._send_json({"ok": True, "path": f"annotations/state/{name}"})

    def _handle_sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        last_id = resolve_sse_start_id(self.headers.get("Last-Event-ID"), self.event_bus.last_id)

        try:
            for event in self.event_bus.subscribe(last_event_id=last_id):
                self.wfile.write(format_sse(event))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _send_json(
        self,
        payload: dict[str, object],
        status: HTTPStatus = HTTPStatus.OK,
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _document_id(self) -> str:
        manifest_path = self.root / "renderer-manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                document = manifest.get("document", {})
                if isinstance(document, dict) and isinstance(document.get("id"), str):
                    return document["id"]
            except json.JSONDecodeError:
                pass
        return "document"

    def _path(self) -> str:
        return urlparse(self.path).path


def serve(
    root: Path,
    bind: str,
    port: int,
    owner_pid: int | None = None,
    idle_timeout: float = DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    owner_grace: float = 300.0,
) -> None:
    from scripts.html_review_workbench.preview_server import PreviewConfigurationError, _validate_bind

    bind = _validate_bind(bind)
    root = root.resolve()
    if not root.is_dir():
        raise PreviewConfigurationError(f"preview root does not exist: {root}")
    handler_class = ReviewPreviewHandler
    event_bus = EventBus()
    change_tracker = CommentChangeTracker()
    handler = partial(handler_class, root=root, event_bus=event_bus, change_tracker=change_tracker)
    with ThreadingHTTPServer((bind, port), handler) as server:
        server.event_bus = event_bus
        actual_port = server.server_address[1]
        sys.stdout.buffer.write(
            json.dumps({"ready": True, "port": actual_port}).encode() + b"\n"
        )
        sys.stdout.buffer.flush()
        if idle_timeout > 0:
            handler_class.touch_activity()
            _start_idle_watchdog(server, handler_class, idle_timeout)
        if owner_pid and owner_pid > 1:
            _start_owner_watchdog(
                server,
                owner_pid,
                handler_class,
                grace_seconds=owner_grace,
                idle_timeout=idle_timeout,
            )
        _start_comments_file_watcher(root, event_bus, change_tracker=change_tracker)
        server.serve_forever()


def _content_length(handler: SimpleHTTPRequestHandler) -> int:
    header = handler.headers.get("Content-Length")
    try:
        length = int(header or "0")
    except ValueError as exc:
        raise CommentStoreError("Content-Length must be an integer") from exc
    if length <= 0:
        raise CommentStoreError("request body is required")
    return length


def _comments_etag(payload: dict[str, object]) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f'"{hashlib.sha256(body).hexdigest()}"'


def _start_owner_watchdog(
    server: ThreadingHTTPServer,
    owner_pid: int,
    handler_class: type[ReviewPreviewHandler],
    grace_seconds: float = 300.0,
    idle_timeout: float = DEFAULT_PREVIEW_IDLE_TIMEOUT_SECONDS,
    interval_seconds: float = 2.0,
) -> None:
    def watch() -> None:
        while True:
            if not pid_is_alive(owner_pid):
                if idle_timeout > 0 and grace_seconds > 0:
                    time.sleep(grace_seconds)
                    return
                _run_grace_period(server, handler_class, grace_seconds, interval_seconds)
                return
            time.sleep(interval_seconds)

    thread = threading.Thread(target=watch, name="preview-owner-watchdog", daemon=True)
    thread.start()


def _run_grace_period(
    server: ThreadingHTTPServer,
    handler_class: type[ReviewPreviewHandler],
    grace_seconds: float,
    check_interval: float,
) -> None:
    if grace_seconds <= 0:
        server.shutdown()
        return

    grace_start = time.monotonic()
    effective_interval = min(check_interval, max(grace_seconds / 2, 0.1))
    while True:
        time.sleep(effective_interval)
        elapsed = time.monotonic() - grace_start
        idle = handler_class.seconds_since_last_activity()
        if handler_class._last_activity > 0 and idle >= grace_seconds:
            server.shutdown()
            return
        if handler_class._last_activity == 0.0 and elapsed >= grace_seconds:
            server.shutdown()
            return


def _start_idle_watchdog(
    server: ThreadingHTTPServer,
    handler_class: type[ReviewPreviewHandler],
    timeout: float,
    check_interval: float = 30.0,
) -> None:
    effective_interval = min(check_interval, max(timeout / 2, 0.1))

    def watch() -> None:
        while True:
            time.sleep(effective_interval)
            idle = handler_class.seconds_since_last_activity()
            if handler_class._last_activity > 0 and idle >= timeout:
                server.shutdown()
                return

    thread = threading.Thread(target=watch, name="preview-idle-watchdog", daemon=True)
    thread.start()


def _start_comments_file_watcher(
    root: Path,
    event_bus: EventBus,
    interval: float = 2.0,
    change_tracker: CommentChangeTracker | None = None,
) -> None:
    comments_path = root / "annotations" / "comments.json"

    def watch() -> None:
        last_mtime = 0.0
        try:
            last_mtime = comments_path.stat().st_mtime
        except OSError:
            pass
        while True:
            time.sleep(interval)
            try:
                current_mtime = comments_path.stat().st_mtime
            except OSError:
                continue
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                # server 経由で配信済みの変更 (agent の add-reply や browser の保存) は
                # 再配信しない。書いた本人へ「新着」通知が届いてしまうため
                if change_tracker is None or change_tracker.should_publish(current_mtime):
                    event_bus.publish("comment_updated", {"source": "file_watcher"})

    thread = threading.Thread(target=watch, name="comments-file-watcher", daemon=True)
    thread.start()
