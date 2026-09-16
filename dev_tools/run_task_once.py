# 一次性验收脚本：对指定实例直接跑一次指定任务
# 用法: PYTHONPATH=. python dev_tools/run_task_once.py <config_name> <TaskName>
import sys

from script import Script

config_name, task = sys.argv[1], sys.argv[2]
s = Script(config_name)
success = s.run(task)
print(f'{task} on {config_name} finished, success={success}')
