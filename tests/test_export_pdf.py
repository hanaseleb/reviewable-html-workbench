"""export-pdf の検査。

失敗経路 (Chrome 不在等):
  何が壊れたら落ちるか: PDF 化を頼んだユーザーが無言の失敗で PDF を得られない。
  判定基準の出所: cli.py の _fail (status/error) と plan 実装設計 1 / SC-5。
  落ちるのを見た: 実装前は ModuleNotFoundError。Chrome 全滅条件で status=failed を確認。

成功経路 (Chrome が PDF を書いたあと終了しない — SC-5 差し戻し):
  何が壊れたら落ちるか: PDF は出来ているのに長時間待たされた末に failed を受け取り、
  成果物に気づかず「この機能は壊れている」と判断して使わなくなる。
  判定基準の出所: lead 差し戻し (2026-08-04) SC-5a〜5d の成功条件を転記。
  落ちるのを見た: 修正前は subprocess.run(timeout=120) がプロセス終了だけを待つため、
  「PDF を書いて sleep し続ける偽 Chrome」で TimeoutExpired → failed になる
  (lead 実測: PDF 394KB 生成済みでも failed)。修正後は同シナリオで ok になる。
"""

from __future__ import annotations

import json
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from scripts.html_review_workbench.export_pdf import (
    ExportPdfError,
    export_pdf,
    find_chrome,
)


def _write_hanging_chrome(script_path: Path, *, write_pdf: bool) -> None:
    """--print-to-pdf= を解釈し、必要なら PDF を書いてから終了しない偽 Chrome。"""
    body = """#!/usr/bin/env bash
set -euo pipefail
out=""
for arg in "$@"; do
  case "$arg" in
    --print-to-pdf=*) out="${arg#--print-to-pdf=}" ;;
  esac
done
if [[ -z "${out}" ]]; then
  echo "missing --print-to-pdf" >&2
  exit 2
fi
"""
    if write_pdf:
        body += r"""
# 最小の PDF シグネチャ (export_pdf は %PDF- を見る)
printf '%%PDF-1.4\n%%EOF\n' > "$out"
"""
    body += """
# 本番 Chrome 同様、PDF 後も終了しない
sleep 300
"""
    script_path.write_text(body, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)


class ExportPdfFailureTest(unittest.TestCase):
    def test_find_chrome_returns_none_when_candidates_empty(self) -> None:
        with mock.patch.dict("os.environ", {"HTML_REVIEW_WORKBENCH_CHROME": ""}, clear=False):
            with mock.patch(
                "scripts.html_review_workbench.export_pdf._chrome_candidates",
                return_value=[],
            ):
                self.assertIsNone(find_chrome())

    def test_export_pdf_raises_when_chrome_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bundle"
            root.mkdir()
            (root / "index.html").write_text("<html><body>hi</body></html>", encoding="utf-8")
            with mock.patch(
                "scripts.html_review_workbench.export_pdf.find_chrome",
                return_value=None,
            ):
                with self.assertRaises(ExportPdfError) as ctx:
                    export_pdf(root)
                self.assertIn("Chrome", str(ctx.exception))

    def test_export_pdf_raises_when_index_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "empty"
            root.mkdir()
            with mock.patch(
                "scripts.html_review_workbench.export_pdf.find_chrome",
                return_value="/usr/bin/false",
            ):
                with self.assertRaises(ExportPdfError):
                    export_pdf(root)

    def test_cli_export_pdf_returns_error_json_when_chrome_missing(self) -> None:
        """cli 経路: Chrome 全滅時に status/error の JSON を stdout に出す。"""
        import io
        from contextlib import redirect_stdout

        from scripts.html_review_workbench import cli as cli_mod

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bundle"
            root.mkdir()
            (root / "index.html").write_text("<html></html>", encoding="utf-8")
            parser = cli_mod.build_parser()
            args = parser.parse_args(["export-pdf", "--root", str(root)])
            with mock.patch(
                "scripts.html_review_workbench.export_pdf.find_chrome",
                return_value=None,
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = cli_mod.export_pdf_cmd(args)
            self.assertEqual(code, 2)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["status"], "failed")
            self.assertIn("error", payload)


class ExportPdfHangAfterWriteTest(unittest.TestCase):
    """Chrome が PDF を書いたあと終了しない状況 (SC-5 差し戻し)。"""

    def test_ok_when_chrome_hangs_after_writing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "bundle"
            root.mkdir()
            (root / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
            fake = tmp_path / "fake-chrome"
            _write_hanging_chrome(fake, write_pdf=True)

            started = time.monotonic()
            with mock.patch(
                "scripts.html_review_workbench.export_pdf.find_chrome",
                return_value=str(fake),
            ):
                result = export_pdf(root, timeout_seconds=15)
            elapsed = time.monotonic() - started

            self.assertEqual(result["status"], "ok")
            pdf_path = Path(result["pdf_path"])
            self.assertTrue(pdf_path.is_file())
            self.assertGreater(pdf_path.stat().st_size, 0)
            self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF-"))
            # 120 秒 timeout を待たずに返ること
            self.assertLess(elapsed, 10.0)
            leftover = subprocess.run(
                ["pgrep", "-f", str(fake)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                leftover.returncode,
                1,
                f"fake chrome still running: {leftover.stdout!r}",
            )

    def test_failed_when_chrome_hangs_without_writing_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = tmp_path / "bundle"
            root.mkdir()
            (root / "index.html").write_text("<html><body>x</body></html>", encoding="utf-8")
            fake = tmp_path / "fake-chrome-nowrite"
            _write_hanging_chrome(fake, write_pdf=False)

            with mock.patch(
                "scripts.html_review_workbench.export_pdf.find_chrome",
                return_value=str(fake),
            ):
                with self.assertRaises(ExportPdfError) as ctx:
                    export_pdf(root, timeout_seconds=2)
            self.assertIn("timed out", str(ctx.exception).lower())
            leftover = subprocess.run(
                ["pgrep", "-f", str(fake)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(leftover.returncode, 1, leftover.stdout)


if __name__ == "__main__":
    unittest.main()
