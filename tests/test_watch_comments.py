"""watch-comments のゲート付与テスト。"""

from pathlib import Path
from unittest.mock import patch
import unittest


class TestCheckGateStatus(unittest.TestCase):
    def test_passes_through_full_gate_payload(self):
        """gate payload が欠落なく通知側へ渡ることを見張る。

        壊れたら起きる不都合: 通知行から返信待ちスレッドの id や件数が落ち、
        agent が「自分宛ての差し戻しは無い」と読み違える。
        期待値の出所: 承認済み plan の gate payload 定義 (空でも全 key)。
        """
        from scripts.html_review_workbench.resolution_gate import GateResult
        from scripts.html_review_workbench.watch_comments import _check_gate_status

        result = GateResult(
            gate="blocked",
            needs_agent_review_threads=["cmt_1"],
            resolved_threads=["cmt_2"],
            status_counts={"needs_agent_review": 1, "needs_user_reply": 0, "resolved": 1},
        )
        with patch("scripts.html_review_workbench.resolution_gate.check_gate", return_value=result):
            payload = _check_gate_status(Path("/tmp/test"))
        self.assertEqual(payload, result.to_payload())

    def test_returns_none_on_error(self):
        from scripts.html_review_workbench.watch_comments import _check_gate_status

        with patch("scripts.html_review_workbench.resolution_gate.check_gate", side_effect=FileNotFoundError):
            payload = _check_gate_status(Path("/tmp/nonexistent"))
        self.assertIsNone(payload)


if __name__ == "__main__":
    unittest.main()
