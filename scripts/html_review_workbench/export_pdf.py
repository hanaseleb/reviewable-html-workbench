"""rendered bundle の index.html を headless Chrome で PDF 化する。

外部サービスへ送信しない。Chrome が無い環境では error を返す。

この環境の Chrome は PDF を書き終えたあともプロセスが終了しないことがある
(updater crash-handler 等が残る)。そのため「プロセス終了」ではなく
「非空の PDF が安定して存在する」ことを成功条件とする。
"""

from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


class ExportPdfError(Exception):
    """export-pdf の実行失敗。"""


# macOS 標準候補 (外部 skill render-pdf.sh と同系) + env 上書き
_DEFAULT_CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)

CHROME_ENV = "HTML_REVIEW_WORKBENCH_CHROME"

# PDF 監視の既定上限 (秒)。Chrome が残っても PDF が揃えば早期終了する
DEFAULT_TIMEOUT_SECONDS = 60.0
# サイズが変わらないことを何回連続で見たら「書き込み完了」とみなすか
_STABLE_POLLS = 2
_POLL_INTERVAL_SECONDS = 0.25


def _chrome_candidates() -> list[str]:
    """探索候補一覧。env 指定があれば先頭に置く。"""
    candidates: list[str] = []
    env = os.environ.get(CHROME_ENV, "").strip()
    if env:
        candidates.append(env)
    candidates.extend(_DEFAULT_CHROME_CANDIDATES)
    return candidates


def find_chrome() -> str | None:
    """利用可能な Chrome / Chromium 実行ファイルを返す。見つからなければ None。"""
    for path in _chrome_candidates():
        if path and Path(path).is_file() and os.access(path, os.X_OK):
            return path
    return None


def _close_pipes(proc: subprocess.Popen[Any]) -> None:
    for stream in (proc.stdout, proc.stderr, proc.stdin):
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _terminate_process_group(proc: subprocess.Popen[Any]) -> None:
    """Chrome とその子プロセスを落とす。終了しない残存を避ける。"""
    if proc.poll() is not None:
        _close_pipes(proc)
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except (ProcessLookupError, OSError):
            _close_pipes(proc)
            return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass
    _close_pipes(proc)


def _pdf_ready(path: Path) -> bool:
    """非空 PDF が一定間隔で同じサイズなら書き込み完了とみなす。"""
    if not path.is_file():
        return False
    try:
        size1 = path.stat().st_size
    except OSError:
        return False
    if size1 <= 0:
        return False
    # %PDF ヘッダがあること (途中ファイルを ok にしない)
    try:
        with path.open("rb") as fh:
            magic = fh.read(5)
    except OSError:
        return False
    if magic != b"%PDF-":
        return False
    stable = 1
    while stable < _STABLE_POLLS:
        time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            size2 = path.stat().st_size
        except OSError:
            return False
        if size2 != size1 or size2 <= 0:
            return False
        stable += 1
        size1 = size2
    return True


def export_pdf(
    root: Path,
    output: Path | None = None,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """bundle root の index.html を PDF 化する。

    Args:
        root: render 済み bundle ディレクトリ (index.html を含む)
        output: 出力 PDF path。省略時は ``<root>/<root 名>.pdf``
        timeout_seconds: PDF が揃うまでの上限秒。プロセス終了は待たない。

    Returns:
        ``{"status": "ok", "pdf_path": "<path>"}``

    Raises:
        ExportPdfError: index 不在 / Chrome 不在 / PDF 未生成
    """
    root = root.resolve()
    index_path = root / "index.html"
    if not index_path.is_file():
        raise ExportPdfError(f"index.html not found in {root}")

    chrome = find_chrome()
    if chrome is None:
        raise ExportPdfError(
            "Chrome not found. Set HTML_REVIEW_WORKBENCH_CHROME or install "
            "Google Chrome / Chromium / Microsoft Edge."
        )

    if output is None:
        output = root / f"{root.name}.pdf"
    else:
        output = Path(output)
        if output.is_dir():
            output = output / f"{root.name}.pdf"
    output = output.resolve()

    output.parent.mkdir(parents=True, exist_ok=True)
    # 前回の残骸を成功と誤認しない
    if output.is_file():
        try:
            output.unlink()
        except OSError as exc:
            raise ExportPdfError(f"could not clear previous PDF: {output}: {exc}") from exc

    file_url = index_path.resolve().as_uri()
    deadline = time.monotonic() + max(1.0, float(timeout_seconds))

    with tempfile.TemporaryDirectory(prefix="rhw-chrome-") as user_data:
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output}",
            "--virtual-time-budget=15000",
            f"--user-data-dir={user_data}",
            "--no-first-run",
            "--disable-extensions",
            file_url,
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except OSError as exc:
            raise ExportPdfError(f"Chrome failed to start: {exc}") from exc

        try:
            while True:
                if _pdf_ready(output):
                    _terminate_process_group(proc)
                    return {"status": "ok", "pdf_path": str(output)}

                rc = proc.poll()
                if rc is not None:
                    # プロセスは終わったが PDF 判定がまだ
                    if _pdf_ready(output):
                        return {"status": "ok", "pdf_path": str(output)}
                    err = ""
                    try:
                        err = (proc.stderr.read() if proc.stderr else "") or ""
                    except OSError:
                        err = ""
                    detail = err.strip()[:500]
                    raise ExportPdfError(
                        f"Chrome print-to-pdf failed (exit {rc})"
                        + (f": {detail}" if detail else f"; PDF missing at {output}")
                    )

                if time.monotonic() >= deadline:
                    _terminate_process_group(proc)
                    if _pdf_ready(output):
                        # タイムアウト直前に揃った場合は成功扱い
                        return {"status": "ok", "pdf_path": str(output)}
                    raise ExportPdfError(
                        f"timed out after {timeout_seconds:g}s waiting for PDF at {output}"
                    )

                time.sleep(_POLL_INTERVAL_SECONDS)
        finally:
            # どの経路でも headless Chrome を残さない
            _terminate_process_group(proc)
