"""Calendar windows and durable per-account completion records (no device access)."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from filelock import FileLock


def apply_pending(config_name, config_root=Path('config')):
    """Apply a staged profile only when the updated script process starts.

    Old running processes discard unknown fields when saving their config, so
    staging must remain separate from the account JSON until the restart.
    """
    from tasks.Script.config_task_windows import TaskWindows
    from module.config.utils import convert_to_underscore
    root = Path(config_root)
    pending = root / 'task_windows' / 'pending' / f'{config_name}.json'
    if not pending.exists():
        return False
    with FileLock(str(pending) + '.lock', timeout=10):
        if not pending.exists():
            return False
        settings = TaskWindows.model_validate(json.loads(pending.read_text(encoding='utf-8')))
        path = root / f'{config_name}.json'
        original = path.read_bytes()
        data = json.loads(original.decode('utf-8'))
        data['script']['task_windows'] = settings.model_dump(mode='json')
        for group in ('morning', 'evening', 'weekly'):
            for command in settings.members(group):
                scheduler = data[convert_to_underscore(command)]['scheduler']
                old = datetime.fromisoformat(scheduler['next_run'])
                scheduler['next_run'] = datetime.combine(old.date(), getattr(settings, group + '_start')).isoformat(sep=' ')
        backup = root / 'task_windows' / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True, exist_ok=True)
        (backup / path.name).write_bytes(original)
        if path.read_bytes() != original:
            raise RuntimeError('Account config changed during window migration; restart all old OAS processes')
        temporary = path.with_suffix('.windows.tmp')
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, path)
        pending.unlink()
        return True


class WindowState:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return {'completed': {}, 'forced': {}}
        # Invalid records must surface, rather than silently repeat purchases.
        return json.loads(self.path.read_text(encoding='utf-8'))

    def update(self, change):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.path) + '.lock', timeout=10):
            data = self.read()
            change(data)
            temporary = self.path.with_suffix('.tmp')
            with temporary.open('w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)

    def force(self, command):
        self.update(lambda data: data['forced'].update({command: datetime.now().isoformat()}))

    def consume_force(self, command):
        if command in self.read()['forced']:
            self.update(lambda data: data['forced'].pop(command, None))

    def complete(self, group, command, cycle):
        key = group + '/' + command
        def change(data):
            data['completed'][key] = max(data['completed'].get(key, ''), cycle.isoformat())
        self.update(change)


class WindowPlanner:
    def __init__(self, settings, state):
        self.settings, self.state = settings, state

    def group(self, command):
        if self.settings.enabled:
            for group in ('morning', 'evening', 'weekly'):
                if command in self.settings.members(group):
                    return group
        return None

    def cycle(self, group, day):
        if group == 'weekly':
            return day - timedelta(days=(day.isoweekday() - self.settings.weekly_day) % 7)
        return day

    def windows(self, group, day):
        conf = self.settings
        cycle = self.cycle(group, day)
        if group != 'weekly' or day == cycle:
            spans = [(getattr(conf, group + '_start'), getattr(conf, group + '_end'))]
        elif conf.makeup_enabled:
            spans = [(conf.morning_start, conf.morning_end)]
        else:
            spans = []
        if conf.makeup_enabled:
            # A makeup window must not run a batch before its scheduled start.
            start = max(conf.makeup_start, getattr(conf, group + '_start')) if day == cycle else conf.makeup_start
            if start < conf.makeup_end:
                spans.append((start, conf.makeup_end))
        return sorted((datetime.combine(day, start), datetime.combine(day, end)) for start, end in spans)

    def next(self, command, due, now, records=None):
        group = self.group(command)
        if not group:
            return due, None
        records = self.state.read() if records is None else records
        if command in records['forced']:
            return now, {'group': group, 'cycle': self.cycle(group, now.date()).isoformat(), 'forced': True}
        cursor = max(due, now)
        completed = records['completed'].get(group + '/' + command, '')
        # Account for arbitrary future next_run dates without scanning from today.
        for offset in range(15):
            day = cursor.date() + timedelta(days=offset)
            cycle = self.cycle(group, day)
            if cycle.isoformat() <= completed:
                continue
            for start, end in self.windows(group, day):
                candidate = max(cursor, start)
                if candidate < end:
                    return candidate, {'group': group, 'cycle': cycle.isoformat(),
                                       'window_end': end.isoformat(sep=' '), 'forced': False}
        raise ValueError(f'No task window found for {command}; check completion records and calendar')

    def after_success(self, command, cycle):
        group = self.group(command)
        self.state.complete(group, command, cycle)
        period = 7 if group == 'weekly' else 1
        return datetime.combine(cycle + timedelta(days=period), getattr(self.settings, group + '_start'))
