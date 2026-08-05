"""SSE の配信開始位置を検査する。

何が壊れたらこの test が落ちるか: 更新通知バナーの「リロード」を押しても、リロード後に
過去の通知が再送されてバナーがまた出る。利用者はバナーを消せず、何度押しても同じ状態に見える。
"""

from __future__ import annotations

import unittest

from scripts.html_review_workbench.event_bus import EventBus
from scripts.html_review_workbench.preview_runtime import resolve_sse_start_id


class ResolveSseStartIdTest(unittest.TestCase):
    def test_first_connection_skips_history(self) -> None:
        """初回接続では履歴を送らない。

        判定基準の出所: SSE の仕様上、ブラウザは初回接続で Last-Event-ID を送らない。
        ここで 0 を返すと EventBus が保持している過去の document_updated が全て再送され、
        2026-08-05 に実機で確認した「リロードしてもバナーが消えない」状態になる。
        """
        self.assertEqual(resolve_sse_start_id(None, 7), 7)

    def test_reconnect_resumes_after_last_seen_event(self) -> None:
        """再接続では受け取り済みの次から送り、切断中のイベントを取りこぼさない。

        判定基準の出所: SSE の Last-Event-ID の仕様 (受信済みの最後の id を送り返す)。
        """
        self.assertEqual(resolve_sse_start_id("3", 7), 3)

    def test_invalid_header_skips_history(self) -> None:
        """壊れた Last-Event-ID は初回接続と同じ扱いにする。"""
        self.assertEqual(resolve_sse_start_id("bogus", 7), 7)

    def test_no_history_is_replayed_to_a_fresh_subscriber(self) -> None:
        """EventBus と組み合わせて、初回接続に過去のイベントが渡らないことを確かめる。"""
        bus = EventBus()
        bus.publish("document_updated", {"message": "1 回目"})
        bus.publish("document_updated", {"message": "2 回目"})

        start_id = resolve_sse_start_id(None, bus.last_id)
        pending = [event for event in bus._events if event.id > start_id]

        self.assertEqual(pending, [])

    def test_reconnect_receives_events_missed_while_disconnected(self) -> None:
        """切断中に発生したイベントは再接続で届く。"""
        bus = EventBus()
        seen = bus.publish("document_updated", {"message": "受信済み"})
        missed = bus.publish("document_updated", {"message": "切断中に発生"})

        start_id = resolve_sse_start_id(str(seen.id), bus.last_id)
        pending = [event for event in bus._events if event.id > start_id]

        self.assertEqual([event.id for event in pending], [missed.id])


if __name__ == "__main__":
    unittest.main()
