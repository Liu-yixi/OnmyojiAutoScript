import unittest
from unittest.mock import Mock

from tasks.ActivityShikigami.script_task import ScriptTask
from tasks.Component.GeneralBattle.battle_wait import BattleWaitContext, HookSignal


class ActivityRewardTest(unittest.TestCase):
    def make_task(self):
        task = object.__new__(ScriptTask)
        task.appear = Mock(return_value=False)
        task.click = Mock()
        task._bw_success_soul = Mock(return_value=HookSignal.CONTINUE)
        return task

    def test_reward_transition_and_return(self):
        task = self.make_task()
        ctx = BattleWaitContext()
        for _ in range(2):
            task.appear.side_effect = lambda asset: asset == task.I_UI_REWARD
            task._bw_success_activity(ctx)
            self.assertFalse(ctx.completion)
        self.assertEqual(task.click.call_count, 2)
        task.click.assert_called_with(task.C_ACTIVITY_REWARD_CONTINUE, interval=1.5)
        task.appear.side_effect = lambda asset: False
        task._bw_success_activity(ctx)
        self.assertFalse(ctx.completion)
        task.appear.side_effect = lambda asset: asset == task.I_CHECK_BATTLE_MAIN
        task._bw_success_activity(ctx)
        self.assertTrue(ctx.success)
        self.assertTrue(ctx.completion)
        task._bw_success_soul.assert_not_called()

    def test_no_reward_does_not_complete_and_keeps_legacy_flow(self):
        task = self.make_task()
        ctx = BattleWaitContext()
        task.appear.side_effect = lambda asset: asset == task.I_CHECK_BATTLE_MAIN
        task._bw_success_activity(ctx)
        self.assertFalse(ctx.completion)
        task.click.assert_not_called()
        task._bw_success_soul.assert_called_once_with(ctx)


if __name__ == '__main__':
    unittest.main()
