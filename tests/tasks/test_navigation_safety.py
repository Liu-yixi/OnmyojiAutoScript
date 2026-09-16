import unittest
from unittest.mock import Mock, patch

from module.exception import RuntimeSafetyStop
from tasks.GameUi.game_ui import GameUi


class NavigationSafetyTest(unittest.TestCase):
    def test_repeated_transition_failure_stops_after_three_attempts(self):
        class Timer:
            def __init__(self, *args):
                self.calls = 0
            def start(self):
                return self
            def reset(self):
                self.calls = 0
            def reached(self):
                self.calls += 1
                return self.calls > 1

        task = object.__new__(GameUi)
        source, destination = Mock(), Mock()
        source.name, destination.name = 'main', 'guild'
        button = object()
        source.links = {destination: button}
        task.ui_current = source
        task._navigation_failures = {}
        task.run_additional = Mock()
        task.appear_then_operate = Mock(return_value=True)
        task.ui_wait_until_appear = Mock(return_value=False)
        task.ui_get_current_page = Mock()
        timeout = Mock()
        timeout.reached.return_value = False
        with patch('tasks.GameUi.game_ui.Timer', Timer):
            self.assertFalse(task._execute_path([source, destination], timeout))
            self.assertFalse(task._execute_path([source, destination], timeout))
            with self.assertRaises(RuntimeSafetyStop):
                task._execute_path([source, destination], timeout)
        self.assertEqual(task.appear_then_operate.call_count, 3)


if __name__ == '__main__':
    unittest.main()
