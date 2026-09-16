# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import cv2
import numpy as np
import random
import re
from module.atom.click import RuleClick
from module.base.timer import Timer
from tasks.base_task import BaseTask
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_area_boss, page_shikigami_records
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.AreaBoss.assets import AreaBossAssets
from tasks.AreaBoss.config_boss import AreaBossFloor
from module.logger import logger
from module.exception import TaskEnd
from module.atom.image import RuleImage
from typing import List


class ScriptTask(GeneralBattle, GameUi, SwitchSoul, AreaBossAssets):

    def _get_dynamic_boss_count(self) -> int:
        """
        从地域鬼王主界面 OCR 声望值，动态决定可挑战次数
        :return: 可挑战鬼王数量 (1/2/3)
        """
        self.screenshot()
        rep = self.O_AB_REPUTATION.ocr_digit(self.device.image)
        logger.info(f"Area boss reputation: {rep}")
        if rep >= 10000:
            return 3
        elif rep >= 2000:
            return 2
        else:
            return 1

    def run(self) -> bool:
        """
        运行脚本
        :return:
        """
        # 直接手动关闭这个锁定阵容的设置
        self.config.area_boss.general_battle.lock_team_enable = False
        con = self.config.area_boss.boss

        if self.config.area_boss.switch_soul.enable:
            self.ui_get_current_page()
            self.ui_goto(page_shikigami_records)
            self.run_switch_soul(self.config.area_boss.switch_soul.switch_group_team)

        if self.config.area_boss.switch_soul.enable_switch_by_name:
            self.ui_get_current_page()
            self.ui_goto(page_shikigami_records)
            self.run_switch_soul_by_name(self.config.area_boss.switch_soul.group_name,
                                         self.config.area_boss.switch_soul.team_name)

        self.ui_get_current_page()
        self.ui_goto(page_area_boss)

        # 先查「今日挑战」已完成次数，识别失败按 0 处理（后续流程兜底）
        fought = self.get_daily_fought_count()
        # 动态获取可挑战次数（声望决定每日上限）
        dynamic_count = self._get_dynamic_boss_count()
        remaining = dynamic_count - (fought if fought is not None else 0)
        if remaining <= 0:
            logger.info('Daily area boss challenges are already complete')
            self.go_back()
            self.set_next_run(task='AreaBoss', success=True, finish=False)
            raise TaskEnd

        if con.boss_reward:
            if self.fight_reward_boss():  # 挑战成功则剩余次数减一
                remaining -= 1

        self.open_filter()
        # 切换到对应集合(热门/收藏)
        if con.use_collect:
            has_available_boss = self.switch_to_collect()
        else:
            has_available_boss = self.switch_to_famous()

        if has_available_boss:
            for battle in (self.I_BATTLE_1, self.I_BATTLE_2, self.I_BATTLE_3):
                if remaining <= 0:
                    break
                if self.boss_fight(battle):
                    remaining -= 1
        else:
            logger.info("No area boss available in filter list")
        # 退出
        self.go_back()
        self.set_next_run(task='AreaBoss', success=True, finish=False)

        # 以抛出异常的形式结束
        raise TaskEnd

    def get_daily_fought_count(self):
        """
        在地域鬼王主界面展开左侧「今日挑战」面板，识别今天已完成的挑战次数。
        面板空槽显示「未选择」，已完成则显示鬼王头像。
        :return: 已完成次数(0-3)，识别失败返回 None
        """
        logger.info('Check daily area boss challenge count')
        expand_timer = Timer(8).start()
        while 1:
            self.screenshot()
            # 面板展开后左侧是一条深色底纹，收起时是浅色的地图
            bar = self.device.image[355:445, 140:470]
            if bar.mean() < 120:
                break
            if expand_timer.reached():
                logger.warning('Expand daily challenge panel timeout')
                return None
            self.click(self.C_AB_DAILY_CHALLENGE, interval=2)
        text = self.O_AB_DAILY_SLOTS.ocr(self.device.image)
        empty = max(0, min(3, text.count('未选择')))
        fought = 3 - empty
        logger.info(f'Daily area boss fought: {fought}/3 (ocr: {text})')
        # 收起面板，避免遮挡地图
        self.click(self.C_AB_DAILY_CHALLENGE, interval=2)
        return fought

    def go_back(self) -> None:
        """
        返回, 要求这个时候是出现在地域鬼王的主界面
        :return:
        """
        # 点击返回
        logger.info("Script back home")
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_UI_BACK_YELLOW, threshold=0.6, interval=2):
                continue
            if self.appear(self.I_CHECK_MAIN, threshold=0.6):
                break

    def boss(self, battle: RuleImage, collect: bool = False):

        # 点击右上角的鬼王选择
        logger.info("Script filter")
        while 1:
            self.screenshot()
            # 如果筛选界面已经打开 点击热门按钮
            if self.appear(self.I_AB_FILTER_OPENED):
                self.click(self.C_AB_FAMOUS_BTN)
                break
            if self.appear_then_click(self.I_FILTER, interval=3):
                continue

        if collect:
            self.switch_to_collect()
        # 页面没有可挑战的BOSS
        if not (self.appear(self.I_BATTLE_1) or self.appear(self.I_BATTLE_2) or self.appear(self.I_BATTLE_3)):
            logger.error("There is no boss could be challenged")
            return
        # 点击第几个鬼王
        logger.info(f'Script area boss {battle}')
        self.ui_click(battle, self.I_AB_CLOSE_RED)
        # 点击挑战
        logger.info("Script fire ")
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_FIRE, interval=1):
                continue
            if not self.appear(self.I_AB_CLOSE_RED):  # 如果这个红色的关闭不见了才可以进行继续
                break
        if not self.run_general_battle(self.config.area_boss.general_battle):
            logger.info("地域鬼王第2只战斗失败")
        # 红色关闭
        logger.info("Script close red")
        self.wait_until_appear(self.I_AB_CLOSE_RED)
        self.ui_click(self.I_AB_CLOSE_RED, self.I_FILTER)

    def boss_fight(self, battle: RuleImage, fileter_open: bool = True) -> bool:
        """
            完成挑战一个鬼王的全流程
            从打开筛选界面开始 到关闭鬼王详情界面结束
        @param battle: 挑战按钮,鬼王头像也可,只要点击能进入详情界面
        @type battle:
        @return:    True        挑战成功
                    False       挑战失败
        @rtype:
        """
        reward_floor = self.config.area_boss.boss.reward_floor
        if fileter_open and not self.appear(self.I_AB_FILTER_OPENED):
            self.open_filter()
        # 如果打不开鬼王详情界面,直接退出
        if not self.open_boss_detail(battle, 3):
            return False

        # 如果已经打过该BOSS,直接跳过不打了
        # 注意：今日挑战面板的计数已包含它，所以返回 False 表示本次没有新打
        if self.is_group_ranked():
            logger.warning("There is no boss could be challenged")
            self.ui_click_until_disappear(self.I_AB_CLOSE_RED, interval=3)
            return False

        # 根据 reward_floor 决定模式
        if reward_floor in (AreaBossFloor.ONE, AreaBossFloor.TEN):
            # 极模式分支
            if self.setup_ultra(reward_floor):
                pass
        elif reward_floor == AreaBossFloor.NORMAL_LV60:
            # 普通模式-拉到60级
            self.setup_normal()
            self.switch_to_level_60()
        elif reward_floor == AreaBossFloor.NORMAL_LV1:
            # 普通模式-保持1级
            self.setup_normal()
        # DEFAULT: 不更改，直接打

        result = True
        if not self.start_fight():
            result = False
            logger.warning("Area Boss Fight Failed ")
        # 每日次数用完后挑战胜利没有奖励结算页，而是停在评分/分享页，先退出来
        self.exit_score_page()
        if not self.wait_until_appear(self.I_AB_CLOSE_RED, wait_time=15):
            logger.warning('Not in boss detail page after fight, back to map')
            back_timer = Timer(10).start()
            while 1:
                self.screenshot()
                if self.appear(self.I_FILTER):
                    break
                if back_timer.reached():
                    logger.warning('Cannot back to area boss map')
                    break
                self.appear_then_click(self.I_UI_BACK_BLUE, interval=2)
            return False
        self.ui_click_until_disappear(self.I_AB_CLOSE_RED, interval=1)
        return result

    def exit_score_page(self):
        """
        每日挑战次数用完后，挑战胜利会停在评分/分享页而不是奖励结算页。
        检测到评分/分享页就点左上角返回键退出。
        """
        for _ in range(6):
            self.screenshot()
            if not self.appear(self.I_AB_SCORE_SHARE):
                return
            logger.info('Exit boss score/share page')
            self.appear_then_click(self.I_UI_BACK_BLUE, interval=1.5)

    def start_fight(self) -> bool:
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_FIRE, interval=1):
                continue
            if not self.appear(self.I_AB_CLOSE_RED):  # 如果这个红色的关闭不见了才可以进行继续
                break

        return self.run_general_battle(self.config.area_boss.general_battle)

    def setup_ultra(self, floor: AreaBossFloor = AreaBossFloor.ONE) -> bool:
        # 确定进入鬼王界面
        self.wait_until_appear(self.I_AB_CLOSE_RED)
        # 尝试切换
        if not self.get_difficulty():
            # 如果可以切换，直接切换
            if self.appear(self.I_AB_DIFFICULTY_NORMAL):
                self.switch_difficulty(True)
            else:
                logger.warning("Cannot switch difficulty")
                return False
        # 调整极地鬼层数
        match floor:
            case AreaBossFloor.ONE:
                self.switch_to_floor_1()
            case AreaBossFloor.TEN:
                self.switch_to_floor_10()
        return True

    def setup_normal(self) -> bool:
        """
        确保当前为普通地鬼模式
        :return: True 成功（已处于普通模式），False 失败
        """
        self.wait_until_appear(self.I_AB_CLOSE_RED)
        if self.get_difficulty():
            # 当前是极地鬼，需要切回普通
            if self.appear(self.I_AB_DIFFICULTY_JI):
                self.switch_difficulty(False)
            else:
                logger.warning("Cannot switch to normal difficulty")
                return False
        return True

    def switch_to_level_60(self):
        logger.info("Switch to level 60")
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_LEVEL_60):
                break
            if self.appear(self.I_AB_LEVEL_HANDLE):
                x, y = self.I_AB_LEVEL_HANDLE.front_center()
                self.S_AB_LEVEL_RIGHT.roi_front = (x, y, 10, 10)
                self.swipe(self.S_AB_LEVEL_RIGHT, interval=3)

    def get_difficulty(self) -> bool:
        """
        @return:    True           极地鬼
                    False           普通地鬼
        @rtype: bool
        """
        self.screenshot()
        return self.appear(self.I_AB_DIFFICULTY_JI)

    def switch_difficulty(self, ultra: bool = True):
        """
            切换普通地鬼/极地鬼
        @param ultra:  是否切换到极地鬼
                    True        切换到极地鬼
                    False       切换到普通地鬼
        @type ultra:
        """
        _from = self.I_AB_DIFFICULTY_NORMAL if ultra else self.I_AB_DIFFICULTY_JI
        _to = self.I_AB_DIFFICULTY_JI if ultra else self.I_AB_DIFFICULTY_NORMAL
        while 1:
            self.screenshot()
            if self.appear(_to):
                break
            if self.appear(_from):
                self.click(_from, interval=3)
                continue

    def switch_to_floor_1(self):
        """
            更改层数为一层
        """
        # _Floor = ["壹星", "贰星", "叁星", "肆星", "伍星", "陆星", "柒星", "捌星", "玖星", "拾星"]
        # 打开选择列表
        self.ui_click(self.C_AB_JI_FLOOR_SELECTED, self.I_AB_JI_FLOOR_LIST_CHECK, interval=3)
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_JI_FLOOR_ONE):
                self.click(self.I_AB_JI_FLOOR_ONE)
                logger.info("Switch to floor 1")
                break
            self.swipe(self.S_AB_FLOOR_DOWN, interval=1)
            # 等待滑动动画
            self.wait_until_appear(self.I_AB_JI_FLOOR_ONE, False, 1)

    def switch_to_floor_10(self):
        """
            更改层数为十层
        """
        # 打开选择列表
        self.ui_click(self.C_AB_JI_FLOOR_SELECTED, self.I_AB_JI_FLOOR_LIST_CHECK, interval=3)
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_JI_FLOOR_TEN):
                self.click(self.I_AB_JI_FLOOR_TEN)
                logger.info("Switch to floor 10")
                break
            self.wait_until_appear(self.I_AB_JI_FLOOR_TEN, False, 1)

    def fight_reward_boss(self):
        BOSS_REWARD_PHOTO1 = [self.C_AB_BOSS_REWARD_PHOTO_1, self.C_AB_BOSS_REWARD_PHOTO_2, self.C_AB_BOSS_REWARD_PHOTO_3]
        BOSS_REWARD_PHOTO2 = [self.C_AB_BOSS_REWARD_PHOTO_MINUS_2, self.C_AB_BOSS_REWARD_PHOTO_MINUS_1]
        need_open_filter, boss_name, photo = self.get_hot_in_reward()  # 获取挑战人数最多的Boss的名字
        if photo is None or boss_name == '声望不够':
            return False
        # 不需要打开筛选界面说明直接找到了目标boss, 直接挑战
        if not need_open_filter:
            return self.boss_fight(photo, fileter_open=False)
        # 滑动到最顶层
        logger.info("Swipe to top")
        for i in range(random.randint(1, 3)):
            self.swipe(self.S_AB_FILTER_DOWN)
        # 遍历所有boss找到名称一致的即目前挑战人数最多的
        for PHOTO in BOSS_REWARD_PHOTO1:
            self.open_filter()
            name = self.get_bossName(PHOTO)
            if self.check_common_chars(str(name), boss_name):
                return self.boss_fight(PHOTO, fileter_open=False)
            self.ui_click_until_disappear(self.I_AB_CLOSE_RED)
        # 倒数一和二
        for i in range(random.randint(1, 3)):
            self.swipe(self.S_AB_FILTER_UP)
        for PHOTO in BOSS_REWARD_PHOTO2:
            self.open_filter()
            name = self.get_bossName(PHOTO)
            if self.check_common_chars(str(name), boss_name):
                return self.boss_fight(PHOTO, fileter_open=False)
            self.ui_click_until_disappear(self.I_AB_CLOSE_RED)
        self.ui_click_until_disappear(self.I_AB_CLOSE_RED)

    def get_hot_in_reward(self):
        """
            返回挑战人数最多的悬赏鬼王
        @return: 是否打开筛选界面, boss名称, boss图片的click
        @rtype:
        """
        self.switch_to_reward()
        boss_configs = [
            {"photo": self.C_AB_BOSS_REWARD_PHOTO_1, "need_swipe": False},
            {"photo": self.C_AB_BOSS_REWARD_PHOTO_2, "need_swipe": False},
            {"photo": self.C_AB_BOSS_REWARD_PHOTO_3, "need_swipe": False},
            {"photo": self.C_AB_BOSS_REWARD_PHOTO_MINUS_2, "need_swipe": True},
            {"photo": self.C_AB_BOSS_REWARD_PHOTO_MINUS_1, "need_swipe": True},
        ]

        def check_boss(photo: RuleClick):
            """
            检查boss是否满足条件
            :param photo:
            :return: 是否满足条件, 挑战数量, boss名称
            """
            self.open_filter()
            num = self.get_num_challenge(photo) or 0
            if not num:
                name = '声望不够'
            else:
                name = self.get_bossName(photo)
                if num >= 20000 and not self.appear(self.I_AB_NUM_CHALLENGE_RAIL):
                    logger.info("The number of challenges is enough")
                    return True, num, name
            # 没找到满足的则关闭boss页面
            self.ui_click_until_disappear(self.I_AB_CLOSE_RED)
            return False, num, name

        mx_challenge_boss_name = None
        mx_challenge_num = 0
        photo = None
        # 遍历所有boss配置, 找挑战人数最多的boss
        for cfg in boss_configs:
            if cfg["need_swipe"]:
                self.open_filter()
                for _ in range(random.randint(1, 3)):
                    self.swipe(self.S_AB_FILTER_UP)
                self.wait_until_appear(cfg["photo"], wait_time=1)
            ret, challenge_num, boss_name = check_boss(cfg["photo"])
            if ret:  # 直接找到满足条件的, 则不需要打开筛选界面直接挑战即可
                return False, boss_name, cfg["photo"]
            if challenge_num > mx_challenge_num:
                mx_challenge_num = challenge_num
                mx_challenge_boss_name = boss_name
                photo = cfg['photo']
                logger.attr(mx_challenge_num, f'Select:{boss_name},{photo.name}')
        return True, mx_challenge_boss_name if mx_challenge_boss_name else '声望不够', photo if mx_challenge_boss_name else None

    def get_num_challenge(self, click_area):
        """
            获取鬼王挑战人数
        @param click_area: 鬼王相应的挑战按钮
        @type click_area:
        @return:
        @rtype:
        """
        # 如果鬼王不可挑战(未解锁),限制3次尝试打开鬼王详情界面
        if not self.open_boss_detail(click_area, 3):
            logger.info("%s unavailable", str(click_area))
            return 0
        return self.O_AB_NUM_OF_CHALLENGE.ocr_digit(self.device.image)

    def get_bossName(self, click_area):
        """
            获取鬼王名字
        @param click_area: 鬼王相应的挑战按钮
        @type click_area:
        @return:
        @rtype:
        """
        # 如果鬼王不可挑战(未解锁),限制3次尝试打开鬼王详情界面
        if not self.open_boss_detail(click_area, 3):
            logger.info("%s unavailable", str(click_area))
            return 0
        ocrName = self.O_AB_BOSS_NAME.detect_and_ocr(self.device.image)
        bossName = re.sub(r"[\'\[\]]", "", str([result.ocr_text for result in ocrName]))
        return bossName

    def open_boss_detail(self, battle: RuleImage, try_num: int = 3) -> bool:
        """
            打开鬼王详情界面
        @param battle:
        @type battle:
        @param try_num: 重试次数
        @type try_num:
        @return:    True        打开成功
                    False       打开失败
        @rtype:
        """
        try_count = 0
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_CLOSE_RED) and self.appear(self.I_FIRE):
                self.screenshot()
                if not self.appear(self.I_FIRE):
                    continue
                return True
            if try_count >= try_num:
                logger.warning(f"Cannot boss_detail, try {try_count} times")
                return False
            if self.click(battle, interval=3):
                try_count += 1
                continue
        return True

    def is_group_ranked(self):
        """
            判断该鬼王是否已经获取到小组排名
        """
        return not self.appear(self.I_AB_GROUP_RANK_NONE)
        pass

    def open_filter(self):
        """打开筛选界面"""
        logger.info("openFilter")
        self.ui_click(self.I_FILTER, self.I_AB_FILTER_OPENED, interval=3)

    def switch_to_collect(self) -> bool:
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_FILTER_TITLE_COLLECTION):
                return True
            if self.appear(self.I_AB_FILTER_OPENED):
                self.click(self.C_AB_COLLECTION_BTN, 1.5)
                continue
            # 筛选面板处于关闭状态时不再死等，由调用方决定如何处理
            if self.appear(self.I_FILTER):
                return False

    def switch_to_famous(self) -> bool:
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_FILTER_TITLE_FAMOUS):
                return True
            if self.appear(self.I_AB_FILTER_OPENED):
                self.click(self.C_AB_FAMOUS_BTN, 1.5)
                continue
            # 筛选面板处于关闭状态时不再死等，由调用方决定如何处理
            if self.appear(self.I_FILTER):
                return False

    def switch_to_reward(self):
        self.open_filter()
        while 1:
            self.screenshot()
            if self.appear(self.I_AB_FILTER_TITLE_REWARD):
                break
            if self.appear(self.I_AB_FILTER_OPENED):
                self.click(self.C_AB_REWARD_BTN, 1.5)
                continue

    def check_common_chars(self, bossName, name):
        # 将两个字符串转为集合，去除重复的字符
        set_boss = set(bossName)
        set_name = set(name)

        # 计算交集，判断交集的元素个数
        common_chars = set_boss & set_name  # & 是集合的交集运算符

        if len(common_chars) >= 2:
            return 1
        else:
            return 0  # 如果交集的字符少于2个，可以根据需要返回其他值
if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)
    # time.sleep(3)
    # t.switchFloor2One()
    # t.switch2Level60()
    t.run()
