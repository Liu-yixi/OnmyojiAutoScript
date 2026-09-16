from datetime import time
from pydantic import BaseModel, ConfigDict, Field, model_validator
from tasks.Component.config_base import Time


# First version only supports tasks whose normal completion schedules a new run.
SUPPORTED = {'DailyTrifles', 'AreaBoss', 'SoulsTidy', 'RichMan', 'WeeklyTrifles'}


class TaskWindows(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    enabled: bool = Field(False, title='启用任务批次', description='普通任务按批次日历执行；关闭后恢复原调度。')
    morning_tasks: str = Field('', title='早间任务', description='英文任务名，逗号分隔：DailyTrifles,AreaBoss')
    morning_start: Time = Field(time(9, 5), title='早间开始')
    morning_end: Time = Field(time(10, 30), title='早间结束')
    evening_tasks: str = Field('', title='晚间任务', description='英文任务名，逗号分隔：SoulsTidy')
    evening_start: Time = Field(time(21, 5), title='晚间开始')
    evening_end: Time = Field(time(22), title='晚间结束')
    weekly_tasks: str = Field('', title='每周任务', description='英文任务名，逗号分隔：RichMan,WeeklyTrifles')
    weekly_day: int = Field(1, ge=1, le=7, title='每周执行日', description='1=周一，7=周日；漏跑可在后续日期补跑。')
    weekly_start: Time = Field(time(9, 5), title='每周开始')
    weekly_end: Time = Field(time(11), title='每周结束')
    makeup_enabled: bool = Field(True, title='启用补跑窗口', description='当天日常可晚间补跑；未完成周任务可在后续早间或补跑窗口执行。')
    makeup_start: Time = Field(time(21, 5), title='补跑开始')
    makeup_end: Time = Field(time(22), title='补跑结束')
    retry_minutes: int = Field(10, ge=1, le=120, title='失败重试间隔（分钟）')

    @model_validator(mode='after')
    def valid_windows(self):
        seen = set()
        for name in ('morning', 'evening', 'weekly', 'makeup'):
            if getattr(self, name + '_start') >= getattr(self, name + '_end'):
                raise ValueError('时间段开始必须早于结束，第一版不支持跨午夜时间段')
            if name == 'makeup':
                continue
            for task in self.members(name):
                if task not in SUPPORTED:
                    raise ValueError(f'不支持批次任务 {task}；可用任务：{sorted(SUPPORTED)}')
                if task in seen:
                    raise ValueError(f'{task} 不能同时出现在多个批次')
                seen.add(task)
        return self

    def members(self, group):
        return [s.strip() for s in getattr(self, group + '_tasks').replace('，', ',').split(',') if s.strip()]
