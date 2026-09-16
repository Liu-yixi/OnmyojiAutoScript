import unittest
from unittest.mock import Mock, patch

from module.exception import GameStuckError
from tasks.GameUi.page import page_main, page_mall
from tasks.RichMan.mall.navbar import MallNavbar
from tasks.RichMan.mall.scales import Scales


class RichManNavigationTest(unittest.TestCase):
    def test_back_accepts_mall_or_courtyard_without_clicking(self):
        for destination in (page_main, page_mall):
            with self.subTest(destination=destination):
                task = object.__new__(MallNavbar)
                task.screenshot = Mock()
                task.ui_page_appear = Mock(side_effect=lambda page: page is destination)
                task.appear_then_click = Mock()
                task.back_mall()
                task.appear_then_click.assert_not_called()

    def test_back_stops_after_arrival(self):
        task = object.__new__(MallNavbar)
        task.screenshot = Mock()
        task.ui_page_appear = Mock(side_effect=[False, False, True])
        task.appear_then_click = Mock()
        task.back_mall()
        task.appear_then_click.assert_called_once_with(task.I_UI_BACK_YELLOW, interval=1.5)

    def run_purchase(self, states, select_soul=True):
        task = object.__new__(Scales)
        clock = [0]
        current = [set()]
        frames = iter(states)

        class Timer:
            def __init__(self, limit, count=0):
                self.limit, self.count = limit, count

            def start(self):
                self.reset()
                return self

            def reset(self):
                self.started, self.checks = clock[0], 0

            def reached(self):
                self.checks += 1
                return clock[0] - self.started > self.limit and self.checks > self.count

        def screenshot():
            clock[0] += 0.6
            current[0] = set(next(frames))

        task.screenshot = Mock(side_effect=screenshot)
        task.appear = Mock(side_effect=lambda asset: asset.name in current[0])
        task.click = Mock(return_value=True)
        task.appear_then_click = Mock(side_effect=lambda asset, **kw: asset.name in current[0])
        task.ui_reward_appear_click = Mock(side_effect=lambda: 'reward' in current[0])
        task.ui_click_until_disappear = Mock()
        with patch('tasks.RichMan.mall.scales.Timer', Timer):
            task._scales_wait_result(task.I_SCA_PICTURE_BOOK, select_soul)
        return task

    @staticmethod
    def shop():
        return [Scales.I_SCA_PICTURE_BOOK.name, Scales.I_MALL_SCCALES_CHECK.name]

    def test_direct_return_after_purchase_stops_confirm_clicks(self):
        for mode in (True, False):
            with self.subTest(select_soul=mode):
                task = self.run_purchase([[Scales.I_BUY_PLUS.name]] + [self.shop()] * 3, mode)
                task.click.assert_called_once_with(task.C_BUY_MORE, interval=5)

    def test_missed_reward_does_not_click_on_shop(self):
        task = self.run_purchase([self.shop()] * 3)
        task.click.assert_not_called()

    def test_selection_and_reward_still_work(self):
        task = self.run_purchase([
            [Scales.I_BUY_PLUS.name], [Scales.I_SCA_SELECT_1.name],
            [Scales.I_SCA_SIX_STAR.name], ['reward'],
        ] + [self.shop()] * 3)
        task.appear_then_click.assert_any_call(task.I_SCA_SELECT_1, interval=1.6)
        task.click.assert_any_call(task.C_SCA_SOULS_GET, interval=1.6)
        self.assertEqual(task.click.call_count, 2)

    def test_auto_result_uses_back_action(self):
        task = self.run_purchase([[Scales.I_SCA_SIX_STAR.name]] + [self.shop()] * 3, False)
        task.click.assert_called_once_with(task.C_SCA_SOULS_BACK, interval=1.6)

    def test_dialog_over_shop_is_not_finished(self):
        task = self.run_purchase([self.shop() + [Scales.I_BUY_PLUS.name]] * 4 + [self.shop()] * 3)
        self.assertEqual(task.click.call_count, 4)

    def test_unknown_page_times_out(self):
        with self.assertRaisesRegex(GameStuckError, '30 seconds'):
            self.run_purchase([[]] * 60)


if __name__ == '__main__':
    unittest.main()
