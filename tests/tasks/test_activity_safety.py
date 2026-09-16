import unittest
from datetime import datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from module.config.anti_ban import AntiBanGuard
from module.exception import RuntimeSafetyStop
from tasks.ActivityShikigami.script_task import ScriptTask, LimitCountOut
from tasks.Component.GeneralBattle.general_battle import GeneralBattle


class ActivitySafetyTest(unittest.TestCase):
    def test_resource_zero_is_not_trusted_after_large_balance(self):
        task = object.__new__(ScriptTask)
        task.device = Mock()
        task.screenshot = Mock()
        task.O_REMAIN_AP_ITEM = Mock()
        for previous, samples, expected in [(801, [800]*3, 800), (1, [0]*3, 0),
                                            (801, [0]*3, None), (801, [800, 0, 800], None)]:
            with self.subTest(previous=previous, samples=samples):
                task._last_activity_items = previous
                task.O_REMAIN_AP_ITEM.ocr.side_effect = samples
                if expected is None:
                    with self.assertRaises(RuntimeSafetyStop):
                        task.read_activity_items()
                else:
                    self.assertEqual(task.read_activity_items(), expected)

    def entry_task(self):
        task = object.__new__(ScriptTask)
        task.run_idx = 0
        task.conf = SimpleNamespace(general_climb=SimpleNamespace(run_sequence_v=['ap']))
        task.device = Mock()
        task.screenshot = Mock()
        task.click = Mock()
        task.is_in_battle = Mock(return_value=False)
        task.appear = Mock(side_effect=lambda asset, **kw: asset == task.I_CHECK_BATTLE_MAIN)
        task.ocr_appear = Mock(return_value=True)
        task.ocr_appear_click = Mock(return_value=True)
        task.reserve_battle = Mock()
        task.run_general_battle = Mock()
        return task

    def test_entry_budget_does_not_restart_outer_loop(self):
        task = self.entry_task()
        with patch('tasks.ActivityShikigami.script_task.matches', return_value=False):
            with self.assertRaisesRegex(RuntimeSafetyStop, '3 challenge clicks'):
                task.start_battle()
        self.assertEqual(task.ocr_appear_click.call_count, 3)
        task.reserve_battle.assert_called_once()
        task.run_general_battle.assert_not_called()

    def test_supply_retries_close_only_then_stops(self):
        task = self.entry_task()
        with patch('tasks.ActivityShikigami.script_task.matches', return_value=True):
            with self.assertRaisesRegex(RuntimeSafetyStop, 'supply popup'):
                task.start_battle()
        self.assertEqual(task.click.call_count, 2)
        task.ocr_appear_click.assert_not_called()
        task.reserve_battle.assert_not_called()

    def test_limit_uses_restored_counts(self):
        task = object.__new__(ScriptTask)
        task.device = SimpleNamespace()
        task.run_idx = 0
        task.limit_time = None
        task._count_map = {'ap': 999}
        task.conf = SimpleNamespace(general_climb=SimpleNamespace(run_sequence_v=['ap'], ap_limit=999))
        with self.assertRaises(LimitCountOut):
            task.put_status()

    def test_rest_can_interrupt_long_activity_at_boundary(self):
        guard = AntiBanGuard()
        config = SimpleNamespace(enable=True, sleep_start=time(2), sleep_end=time(8),
                                 daily_active_limit=timedelta(hours=1))
        self.assertTrue(guard.task_rest_due(datetime(2026, 9, 16, 1), config, datetime(2026, 9, 16, 2)))
        self.assertTrue(guard.task_rest_due(datetime(2026, 9, 16, 10), config, datetime(2026, 9, 16, 11)))
        self.assertFalse(guard.task_rest_due(datetime(2026, 9, 16, 10), config, datetime(2026, 9, 16, 10, 20)))

    def test_prepare_retries_have_hard_limit(self):
        for method in [GeneralBattle.battle_wait, GeneralBattle.battle_wait_v2]:
            task = Mock()
            task.appear.return_value = True
            task.appear_then_click.return_value = True
            with self.assertRaises(RuntimeSafetyStop):
                method(task, False)
            self.assertEqual(task.appear_then_click.call_count, 3)


if __name__ == '__main__':
    unittest.main()
