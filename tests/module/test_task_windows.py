import tempfile
import unittest
from datetime import datetime, date, timedelta, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from pydantic import ValidationError
from module.config.task_windows import WindowPlanner, WindowState, apply_pending
from module.config.config import Config
from tasks.Script.config_task_windows import TaskWindows


class TaskWindowsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = WindowState(Path(self.temp.name) / 'state.json')
        self.settings = TaskWindows(enabled=True, morning_tasks='DailyTrifles,AreaBoss',
                                    evening_tasks='SoulsTidy', weekly_tasks='RichMan,WeeklyTrifles')
        self.planner = WindowPlanner(self.settings, self.state)

    def next(self, now, task='DailyTrifles', due='2026-09-01 00:00:00'):
        return self.planner.next(task, datetime.fromisoformat(due), datetime.fromisoformat(now))[0]

    def test_daily_start_and_late_start(self):
        for now, expected in [('08:00', '09:05'), ('09:05', '09:05'), ('10:00', '10:00')]:
            self.assertEqual(self.next('2026-09-14 ' + now), datetime.fromisoformat('2026-09-14 ' + expected))

    def test_end_is_exclusive_and_makeup(self):
        self.assertEqual(self.next('2026-09-14 10:30'), datetime(2026, 9, 14, 21, 5))
        self.assertEqual(self.next('2026-09-14 22:00'), datetime(2026, 9, 15, 9, 5))

    def test_task_original_due_is_respected(self):
        self.assertEqual(self.next('2026-09-14 09:10', due='2026-09-16 00:00:00'), datetime(2026, 9, 16, 9, 5))

    def test_completion_survives_restart_and_is_per_task(self):
        self.planner.after_success('DailyTrifles', date(2026, 9, 14))
        self.planner = WindowPlanner(self.settings, WindowState(self.state.path))
        self.assertEqual(self.next('2026-09-14 09:20'), datetime(2026, 9, 15, 9, 5))
        self.assertEqual(self.next('2026-09-14 09:20', 'AreaBoss'), datetime(2026, 9, 14, 9, 20))

    def test_weekly_catchup_and_no_repeat(self):
        self.assertEqual(self.next('2026-09-15 08:00', 'RichMan'), datetime(2026, 9, 15, 9, 5))
        self.assertEqual(self.planner.after_success('RichMan', date(2026, 9, 14)), datetime(2026, 9, 21, 9, 5))
        self.assertEqual(self.next('2026-09-15 09:30', 'RichMan'), datetime(2026, 9, 21, 9, 5))

    def test_without_makeup(self):
        self.settings.makeup_enabled = False
        self.assertEqual(self.next('2026-09-14 10:30'), datetime(2026, 9, 15, 9, 5))
        self.assertEqual(self.next('2026-09-15 09:00', 'RichMan'), datetime(2026, 9, 21, 9, 5))

    def test_evening_not_run_in_morning(self):
        self.assertEqual(self.next('2026-09-14 09:00', 'SoulsTidy'), datetime(2026, 9, 14, 21, 5))

    def test_force_is_one_shot_and_bypasses_completion(self):
        self.planner.after_success('DailyTrifles', date(2026, 9, 14))
        self.state.force('DailyTrifles')
        self.assertEqual(self.next('2026-09-14 12:00'), datetime(2026, 9, 14, 12))
        self.state.consume_force('DailyTrifles')
        self.assertEqual(self.next('2026-09-14 12:00'), datetime(2026, 9, 15, 9, 5))

    def test_disabled_and_ungrouped_unchanged(self):
        self.assertEqual(self.next('2026-09-14 12:00', 'Restart'), datetime(2026, 9, 1))
        self.settings.enabled = False
        self.assertEqual(self.next('2026-09-14 12:00'), datetime(2026, 9, 1))

    def test_invalid_settings_rejected(self):
        for fields in ({'morning_start': '23:00:00'}, {'morning_tasks': 'Restart'},
                       {'morning_tasks': 'RichMan', 'weekly_tasks': 'RichMan'}, {'weekly_day': 8}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                TaskWindows(**fields)

    def test_corrupt_completion_record_is_not_silently_discarded(self):
        self.state.path.write_text('broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.next('2026-09-14 09:10')

    def test_config_completed_task_reanchors_to_calendar(self):
        config = object.__new__(Config)
        config.config_name = 'test'
        scheduler = SimpleNamespace(success_interval=timedelta(days=1), failure_interval=timedelta(days=1),
                                    server_update=time(9), float_time=time(), next_run=datetime(2026, 9, 14))
        config.model = SimpleNamespace(running_task='DailyTrifles', daily_trifles=SimpleNamespace(scheduler=scheduler))
        config.reload = Mock()
        config.save = Mock()
        config.window_run_context = {'command': 'DailyTrifles', 'cycle': '2026-09-14'}
        with patch.object(Config, 'window_planner', new_callable=PropertyMock, return_value=self.planner):
            # A run finishing across midnight still completes its original cycle.
            config.task_delay('DailyTrifles', start_time=datetime(2026, 9, 15, 0, 1), success=True)
        self.assertEqual(scheduler.next_run, datetime(2026, 9, 15, 9, 5))
        self.assertEqual(self.state.read()['completed']['morning/DailyTrifles'], '2026-09-14')

    def test_schedule_uses_effective_time_without_changing_config(self):
        raw = {'daily_trifles': {'scheduler': {'enable': True, 'next_run': datetime(2026, 9, 14), 'priority': 5}}}
        config = object.__new__(Config)
        config.model = SimpleNamespace(dict=lambda: raw, running_task='',
                                      script=SimpleNamespace(optimization=SimpleNamespace(schedule_rule='Filter')))
        class ClockMeta(type):
            def __instancecheck__(cls, instance):
                return isinstance(instance, datetime)
        class Clock(datetime, metaclass=ClockMeta):
            @classmethod
            def now(cls):
                return cls(2026, 9, 14, 12)
        raw['daily_trifles']['scheduler']['next_run'] = Clock(2026, 9, 14)
        with patch('module.config.config.datetime', Clock), patch.object(Config, 'window_planner', new_callable=PropertyMock, return_value=self.planner):
            config.update_scheduler()
        self.assertFalse(config.pending_task)
        self.assertEqual(config.waiting_task[0].next_run, datetime(2026, 9, 14, 21, 5))
        self.assertEqual(raw['daily_trifles']['scheduler']['next_run'], datetime(2026, 9, 14))

    def test_queue_acquisition_rechecks_window(self):
        from script import Script
        class WaitReached(Exception):
            pass
        now = datetime.now()
        ready = SimpleNamespace(command='DailyTrifles', next_run=now - timedelta(seconds=1))
        deferred = SimpleNamespace(command='DailyTrifles', next_run=now + timedelta(hours=1), batch=None)
        script = object.__new__(Script)
        script.__dict__['config'] = Mock()
        script.config.get_next.side_effect = [ready, deferred, deferred]
        script.state_queue = None
        script.anti_ban_guard = Mock()
        script.anti_ban_guard.wake_time.return_value = None
        script._try_acquire_queue_token = Mock(return_value=True)
        script._handle_wait_during_idle = Mock(side_effect=WaitReached)
        with self.assertRaises(WaitReached):
            script.get_next_task()
        script._handle_wait_during_idle.assert_called_once_with(deferred.next_run)
        script.config.window_planner.state.consume_force.assert_not_called()

    def test_config_ui_exposes_window_controls(self):
        from module.config.config_model import ConfigModel
        model = ConfigModel()
        fields = model.script_task('Script')['task_windows']
        values = {field['name']: field for field in fields}
        self.assertIn('enabled', values)
        self.assertEqual(values['morning_start']['type'], 'time')
        self.assertIn('weekly_tasks', values)
        self.assertIn('makeup_enabled', values)

    def test_staged_migration_applies_once_and_preserves_latest_account_values(self):
        import json
        root = Path(self.temp.name)
        pending = root / 'task_windows' / 'pending'
        pending.mkdir(parents=True)
        settings = TaskWindows(enabled=True, morning_tasks='DailyTrifles')
        (pending / 'account.json').write_text(settings.model_dump_json(), encoding='utf-8')
        account = {'script': {'optimization': {'queue_mode': False}},
                   'daily_trifles': {'scheduler': {'enable': True, 'next_run': '2026-09-16 15:10:00'}},
                   'unrelated': {'value': 123}}
        path = root / 'account.json'
        path.write_text(json.dumps(account), encoding='utf-8')
        self.assertTrue(apply_pending('account', root))
        data = json.loads(path.read_text(encoding='utf-8'))
        self.assertTrue(data['script']['task_windows']['enabled'])
        self.assertEqual(data['daily_trifles']['scheduler']['next_run'], '2026-09-16 09:05:00')
        self.assertEqual(data['unrelated'], account['unrelated'])
        self.assertEqual(len(list((root / 'task_windows' / 'backups').glob('*/account.json'))), 1)
        self.assertFalse(apply_pending('account', root))
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), data)

    def test_failure_does_not_mark_complete(self):
        config = object.__new__(Config)
        config.config_name = 'test'
        scheduler = SimpleNamespace(success_interval=timedelta(days=1), failure_interval=timedelta(days=1),
                                    next_run=datetime(2026, 9, 14))
        config.model = SimpleNamespace(running_task='DailyTrifles', daily_trifles=SimpleNamespace(scheduler=scheduler))
        config.reload = Mock()
        config.save = Mock()
        before = datetime.now()
        with patch.object(Config, 'window_planner', new_callable=PropertyMock, return_value=self.planner):
            config.task_delay('DailyTrifles', success=False, server=False)
        self.assertGreaterEqual(scheduler.next_run, before + timedelta(minutes=10))
        self.assertLessEqual(scheduler.next_run, datetime.now() + timedelta(minutes=10))
        self.assertEqual(self.state.read()['completed'], {})


if __name__ == '__main__':
    unittest.main()
