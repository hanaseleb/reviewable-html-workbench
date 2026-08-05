"""notify-update の分岐を検査する。

何が壊れたらこの test が落ちるか: 資料を更新して notify-update を実行しても、
利用者のブラウザに更新バナーが出ない。skill は --url を渡さない形で notify-update を
呼ぶよう指示しているため、壊れていると agent の更新通知が毎回無言で失敗する。
"""

from __future__ import annotations

import argparse
import unittest
from unittest import mock

from scripts.html_review_workbench import cli


class NotifyUpdateTest(unittest.TestCase):
    def test_uses_active_session_url_when_url_omitted(self) -> None:
        """--url 省略時、起動中の preview が見つかれば通知を送る。

        期待値の出所: 2026-08-05 に preview 起動状態で --url を明示して実測した
        `{"ok": true, "event_type": "document_updated"}` / exit 0。
        --url の有無で結果が変わらないことが仕様。
        """
        args = argparse.Namespace(root=".", url=None, message="更新しました")
        with (
            mock.patch.object(cli, "active_session_base_url", return_value="http://127.0.0.1:9999"),
            mock.patch(
                "scripts.html_review_workbench.watch_comments.send_notify", return_value=0
            ) as send_notify,
        ):
            result = cli.notify_update(args)

        send_notify.assert_called_once_with("http://127.0.0.1:9999", message="更新しました")
        self.assertEqual(result, 0)

    def test_reports_failure_when_no_active_session(self) -> None:
        """起動中の preview が無ければ failed を出力して 2 を返す。

        期待値の出所: cli.py の既存実装が出力する
        `{"status": "failed", "error": "no active preview session found"}` と exit 2。
        """
        args = argparse.Namespace(root=".", url=None, message="更新しました")
        with (
            mock.patch.object(cli, "active_session_base_url", return_value=None),
            mock.patch("scripts.html_review_workbench.watch_comments.send_notify") as send_notify,
        ):
            result = cli.notify_update(args)

        send_notify.assert_not_called()
        self.assertEqual(result, 2)

    def test_explicit_url_bypasses_session_lookup(self) -> None:
        """--url を明示した場合は session を探さずそのまま送る。"""
        args = argparse.Namespace(root=".", url="http://127.0.0.1:8888", message="更新しました")
        with (
            mock.patch.object(cli, "active_session_base_url") as lookup,
            mock.patch(
                "scripts.html_review_workbench.watch_comments.send_notify", return_value=0
            ) as send_notify,
        ):
            result = cli.notify_update(args)

        lookup.assert_not_called()
        send_notify.assert_called_once_with("http://127.0.0.1:8888", message="更新しました")
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
