import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tasks.Component.GeneralBattle.general_battle import GeneralBattle


class BattlePrepareTest(unittest.TestCase):
    def test_slow_preset_and_missed_prepare_click(self):
        clock = [0]

        class Timer:
            def __init__(self, limit):
                self.limit = limit

            def start(self):
                self.reset()
                return self

            def reset(self):
                self.started = clock[0]

            def reached(self):
                return clock[0] - self.started > self.limit

        task = MagicMock()
        task.current_count = 1
        task.is_in_prepare.return_value = True
        clicks = []

        def screenshot():
            clock[0] += 1

        def preset(*args):
            clock[0] += 8

        def click(button, **kwargs):
            if button is task.I_PREPARE_HIGHLIGHT:
                clicks.append(clock[0])
                return True
            return False

        task.screenshot.side_effect = screenshot
        task.switch_preset_team.side_effect = preset
        task.appear_then_click.side_effect = click
        task.is_in_real_battle.side_effect = lambda *args: len(clicks) >= 2
        config = SimpleNamespace(lock_team_enable=False, preset_enable=True,
                                 preset_group=1, preset_team=2)
        with patch('tasks.Component.GeneralBattle.general_battle.Timer', Timer):
            self.assertTrue(GeneralBattle.battle_before(task, None, config))
        self.assertEqual(len(clicks), 2)
        task.switch_preset_team.assert_called_once_with(True, 1, 2)
        self.assertGreater(clicks[0], 9)  # New screenshot after preset selection.

    def test_both_wait_loops_retry_prepare(self):
        class StopLoop(Exception):
            pass

        for method in (GeneralBattle.battle_wait, GeneralBattle.battle_wait_v2):
            with self.subTest(method=method.__name__):
                task = MagicMock()
                task.screenshot.side_effect = [None, StopLoop()]
                task.appear.return_value = False
                task.appear_then_click.side_effect = (
                    lambda button, **kwargs: button is task.I_PREPARE_HIGHLIGHT
                )
                with self.assertRaises(StopLoop):
                    method(task, False)
                task.appear_then_click.assert_any_call(task.I_PREPARE_HIGHLIGHT, interval=0.8)
                self.assertEqual(task.device.stuck_record_add.call_count, 2)


if __name__ == '__main__':
    unittest.main()
