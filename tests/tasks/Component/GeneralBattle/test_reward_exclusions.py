import unittest
from unittest.mock import Mock

from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBattle.battle_wait import BattleWaitContext, HookSignal


class RewardExclusionsTest(unittest.TestCase):
    def test_soul_wait_on_battle_frame(self):
        for options in (None, {}, {'success': {}}, {'success': {'excludes': None}}, {'success': {'excludes': []}}):
            with self.subTest(options=options):
                battle = object.__new__(GeneralBattle)
                battle.appear_then_click = Mock(return_value=False)
                battle.appear = Mock(return_value=False)
                self.assertEqual(battle._bw_success_soul(BattleWaitContext(options=options)), HookSignal.CONTINUE)

    def test_default_empty_and_custom(self):
        battle = object.__new__(GeneralBattle)
        default = battle.reward_exclude_click()
        explicit = battle.reward_exclude_click(battle.exclude_button_stage_1)
        self.assertEqual(default._excluded, explicit._excluded)
        self.assertTrue(default._excluded)
        self.assertFalse(battle.reward_exclude_click([])._excluded)
        self.assertEqual(len(battle.reward_exclude_click(['C_END_SOUL_RECORD'])._excluded), 1)
        with self.assertRaisesRegex(ValueError, 'Unknown success exclusion'):
            battle.reward_exclude_click(['NO_SUCH_ASSET'])


if __name__ == '__main__':
    unittest.main()
