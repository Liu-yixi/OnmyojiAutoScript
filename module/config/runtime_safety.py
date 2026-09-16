"""Persistent stop latch and conservative activity budgets; no emulator access."""
from datetime import datetime, timedelta
from pathlib import Path

from module.config.task_windows import WindowState
from module.exception import RuntimeSafetyStop


class RuntimeSafetyState(WindowState):
    def __init__(self, config_name, root=Path('config/runtime_safety')):
        if Path(config_name).name != config_name or '/' in config_name or '\\' in config_name:
            raise ValueError('Expected an account config name, not a path')
        super().__init__(Path(root) / (config_name + '.json'))

    def ensure_running(self):
        reason = self.read().get('stopped')
        if reason:
            raise RuntimeSafetyStop(reason)

    def stop(self, reason):
        def change(data):
            data['stopped'] = str(reason)
            data['stopped_at'] = datetime.now().isoformat()
        self.update(change)

    def clear_stop(self):
        # Clearing a stop must not reset a partly consumed activity budget.
        def change(data):
            data.pop('stopped', None)
            data.pop('stopped_at', None)
            data['recoveries'] = []
        self.update(change)

    def record_recovery(self, command, now=None):
        """Allow one automatic recovery per account within 30 minutes."""
        now = now or datetime.now()
        allowed = False
        def change(data):
            nonlocal allowed
            recent = [r for r in data.get('recoveries', [])
                      if datetime.fromisoformat(r['at']) > now - timedelta(minutes=30)]
            allowed = not recent
            recent.append({'task': command, 'at': now.isoformat()})
            data['recoveries'] = recent
            if not allowed:
                data['stopped'] = 'Repeated recovery within 30 minutes: ' + command
                data['stopped_at'] = now.isoformat()
        self.update(change)
        return allowed

    def begin_activity(self):
        def change(data):
            if not data.get('activity') or data['activity'].get('complete'):
                data['activity'] = {'started': datetime.now().isoformat(), 'counts': {}, 'complete': False}
        self.update(change)
        return self.read()['activity']['counts'].copy()

    def reserve_activity(self, mode, limit):
        def change(data):
            counts = data['activity']['counts']
            count = counts.get(mode, 0)
            if count >= limit:
                raise RuntimeSafetyStop('Activity budget exhausted: ' + mode)
            counts[mode] = count + 1
        self.update(change)
        return self.read()['activity']['counts'][mode]

    def finish_activity(self):
        def change(data):
            if 'activity' in data:
                data['activity']['complete'] = True
        self.update(change)

    def record_activity_items(self, items):
        self.update(lambda data: data['activity'].update({'last_items': items}))
