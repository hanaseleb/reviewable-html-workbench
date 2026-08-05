"""Shared low-level helpers for Reviewable HTML Workbench modules."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENTS_SCHEMA_PATH = REPO_ROOT / "schemas" / "comments.schema.json"
# theme (light / dark) を body 描画前に確定させる。Mermaid が初期化時の theme を SVG へ
# 焼き込むため、保存済み theme の反映を DOMContentLoaded 後にすると図だけ逆の theme で固まる。
EARLY_THEME_JS = (
    "(function(){"
    "try{var s=localStorage.getItem('reviewable-theme');"
    "if(s==='light'||s==='dark'){document.documentElement.dataset.theme=s;return;}}catch(e){}"
    "if(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)"
    "{document.documentElement.dataset.theme='dark';}"
    "})()"
)

# Mermaid の theme は紙面の theme に合わせる。固定すると片方の theme で図の文字が紙と同化する。
# 判定は preview (html[data-theme]) と公開版 (data-theme を持たず prefers-color-scheme 追従) の
# 両方を見る。startOnLoad を切って自前で run するのは、描画で失われる source を先に退避するため
# (theme 切替時の描き直しに元テキストが要る)。
MERMAID_INIT_JS = (
    "(function(){"
    "function t(){"
    "var d=document.documentElement.dataset.theme;"
    "if(d!=='dark'&&d!=='light'){"
    "d=(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light';}"
    "return d==='dark'?'dark':'default';}"
    "function boot(){mermaid.initialize({startOnLoad:false,theme:t(),securityLevel:'strict'});}"
    "window.__rhwRerenderMermaid=function(){"
    "var n=Array.prototype.slice.call(document.querySelectorAll('.mermaid[data-mermaid-source]'));"
    "if(!n.length){return Promise.resolve();}"
    "n.forEach(function(el){el.removeAttribute('data-processed');"
    "el.textContent=el.getAttribute('data-mermaid-source');});"
    "boot();"
    "return Promise.resolve(mermaid.run({nodes:n})).catch(function(){});};"
    "boot();"
    "document.addEventListener('DOMContentLoaded',function(){"
    "document.querySelectorAll('.mermaid').forEach(function(el){"
    "el.setAttribute('data-mermaid-source',el.textContent);});"
    "mermaid.run();"
    "if(window.matchMedia){"
    "var mq=window.matchMedia('(prefers-color-scheme: dark)');"
    "var f=function(){var d=document.documentElement.dataset.theme;"
    "if(d==='dark'||d==='light'){return;}window.__rhwRerenderMermaid();};"
    "if(mq.addEventListener){mq.addEventListener('change',f);}"
    "else if(mq.addListener){mq.addListener(f);}}"
    "});"
    "})()"
)
PUBLISH_EXPORT_JS_PATH = REPO_ROOT / "templates" / "assets" / "publish-export.js"
PUBLISH_OVERRIDES_CSS_PATH = REPO_ROOT / "templates" / "assets" / "publish-overrides.css"
TASK_CHECKLIST_JS_PATH = REPO_ROOT / "templates" / "assets" / "task-checklist.js"
INTERACTIVE_STATE_JS_PATH = REPO_ROOT / "templates" / "assets" / "interactive-state.js"
TOC_NAV_JS_PATH = REPO_ROOT / "templates" / "assets" / "toc-nav.js"

# block の title を出す見出しの階層。2 = 章、3 = 節、4 = 項。
# h1 は文書タイトル専用、h5 以下は content 内の小見出しに残す。
MIN_HEADING_LEVEL = 2
MAX_HEADING_LEVEL = 4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        return _pid_is_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _pid_is_alive_windows(pid: int) -> bool:
    # os.kill(pid, 0) is a POSIX idiom; on Windows it raises OSError
    # (WinError 87, invalid parameter) instead of probing liveness, so query
    # the process handle through the Win32 API via ctypes (stdlib, no deps).
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    ERROR_ACCESS_DENIED = 5
    STILL_ACTIVE = 259

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # The process exists but we lack access rights -> treat as alive,
        # mirroring the POSIX PermissionError branch above.
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return True
        return exit_code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def write_json(path: Path, payload: dict[str, Any], *, ensure_parent: bool = False, indent: int | None = 2) -> None:
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def unique_path(path: Path, *, on_exhausted: Callable[[Path], Exception]) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise on_exhausted(path)


def resolve_bundle_json_path(
    root: Path,
    relative_path: str,
    *,
    label: str,
    error: Callable[[str], Exception],
) -> Path:
    if not relative_path:
        raise error(f"{label} path is required")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise error(f"{label} path must be relative")
    if any(part == ".." for part in candidate.parts):
        raise error(f"{label} path must not contain parent traversal")

    resolved_root = root.resolve()
    resolved_path = (resolved_root / candidate).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise error(f"{label} path must stay inside the bundle root")
    if resolved_path.suffix != ".json":
        raise error(f"{label} path must be a JSON file")
    return resolved_path
