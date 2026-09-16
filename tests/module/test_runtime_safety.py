import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import numpy as np

from module.config.runtime_safety import RuntimeSafetyState
from module.device.safety_screen import template, violation_visible
from module.exception import RuntimeSafetyStop, GameStuckError, GameTooManyClickError


class RuntimeSafetyTest(unittest.TestCase):
    def test_latch_survives_restart_and_clear_preserves_budget(self):
        with tempfile.TemporaryDirectory() as root:
            state = RuntimeSafetyState('test', Path(root))
            state.begin_activity()
            state.reserve_activity('ap', 999)
            state.record_activity_items(801)
            state.stop('violation')
            resumed = RuntimeSafetyState('test', Path(root))
            with self.assertRaises(RuntimeSafetyStop):
                resumed.ensure_running()
            resumed.clear_stop()
            resumed.ensure_running()
            self.assertEqual(resumed.begin_activity(), {'ap': 1})
            self.assertEqual(resumed.read()['activity']['last_items'], 801)

    def test_recovery_budget_across_tasks_and_processes(self):
        with tempfile.TemporaryDirectory() as root:
            now = datetime(2026, 9, 16, 6)
            self.assertTrue(RuntimeSafetyState('test', Path(root)).record_recovery('A', now))
            state = RuntimeSafetyState('test', Path(root))
            self.assertFalse(state.record_recovery('B', now + timedelta(minutes=5)))
            with self.assertRaises(RuntimeSafetyStop):
                state.ensure_running()

    def test_activity_limit_survives_midnight_restart(self):
        with tempfile.TemporaryDirectory() as root:
            state = RuntimeSafetyState('test', Path(root))
            state.begin_activity()
            for _ in range(3):
                state.reserve_activity('ap', 3)
            resumed = RuntimeSafetyState('test', Path(root))
            self.assertEqual(resumed.begin_activity()['ap'], 3)
            with self.assertRaises(RuntimeSafetyStop):
                resumed.reserve_activity('ap', 3)
            resumed.finish_activity()
            self.assertEqual(resumed.begin_activity(), {})

    def test_notice_requires_multiple_features(self):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        def put(name, x, y):
            t = template(name)
            image[y:y+t.shape[0], x:x+t.shape[1]] = t[:, :, None]
        self.assertFalse(violation_visible(image))
        put('violation_title', 591, 237)
        self.assertFalse(violation_visible(image))
        put('violation_body', 450, 300)
        self.assertTrue(violation_visible(image))
        image[:] = 0
        put('violation_title_covered', 591, 237)
        put('disconnected_text', 443, 313)
        self.assertTrue(violation_visible(image))

    def test_script_click_failure_stops_without_restart(self):
        from script import Script
        with tempfile.TemporaryDirectory() as root:
            script = object.__new__(Script)
            script.config_name = 'test'
            script.runtime_safety = RuntimeSafetyState('test', Path(root))
            script._try_acquire_queue_token = Mock(return_value=True)
            script.instance_guard = None
            script.device = Mock()
            script.device.screenshot.side_effect = GameTooManyClickError('same target')
            script.config = Mock()
            script.save_error_log = Mock()
            with self.assertRaises(SystemExit):
                script.run('ActivityShikigami')
            script.config.task_call.assert_not_called()
            self.assertIn('same target', script.runtime_safety.read()['stopped'])

    def test_device_blocks_control_before_recording_or_sending(self):
        from module.device.device import Device
        device = object.__new__(Device)
        device._runtime_safety = Mock()
        device.image = np.zeros((720, 1280, 3), dtype=np.uint8)
        for name, x, y in [('violation_title', 591, 237), ('violation_body', 450, 300)]:
            t = template(name)
            device.image[y:y+t.shape[0], x:x+t.shape[1]] = t[:, :, None]
        device.click_record_add = Mock()
        with self.assertRaises(RuntimeSafetyStop):
            device.handle_control_check('PAGE_MAIN_GOTO_GUILD')
        device.click_record_add.assert_not_called()
        device._runtime_safety.stop.assert_called_once()

    def test_script_allows_only_one_stuck_recovery(self):
        from script import Script
        with tempfile.TemporaryDirectory() as root:
            script = object.__new__(Script)
            script.config_name = 'test'
            script.runtime_safety = RuntimeSafetyState('test', Path(root))
            script._try_acquire_queue_token = Mock(return_value=True)
            script.instance_guard = None
            script.device = Mock()
            script.device.screenshot.side_effect = GameStuckError('wait')
            script.config = Mock()
            script.save_error_log = Mock()
            script.exception_handler = Mock()
            self.assertFalse(script.run('ActivityShikigami'))
            script.config.task_call.assert_called_once_with('Restart')
            with self.assertRaises(SystemExit):
                script.run('AreaBoss')
            self.assertEqual(script.config.task_call.call_count, 1)


if __name__ == '__main__':
    unittest.main()
