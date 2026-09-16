# Dev Todo

## 双实例御魂组队 —— 第二步：突破券满联动打结界突破

> 第一步「组队同步屏障」已完成（2026-07-29）：
> `module/config/team_sync.py`（TeamSync 共享状态文件）、
> `tasks/Orochi/config.py`（`team_sync` 配置组）、
> `tasks/Orochi/script_task.py`（`team_sync_barrier()`，run() 开加成前调用）。
> 已确定的设计决策：突破切换走**任务内直接调用**（不经调度器接力）；
> 票数估算用**掉落计数 + 起始 OCR**。

### 目标

刷御魂会掉落「结界突破券」（上限 30）。任一号券接近满时，两个号协同暂停御魂、
各自去打结界突破，打完互相等齐，再由队长重新邀请、无缝继续刷御魂。

### 状态机（TeamSync 相位扩展）

```
ready → synced → farming → need_raid → raiding → raid_done →（双方等齐）→ 重新 ready/synced → farming ...
```

`TeamSync`（`module/config/team_sync.py`）直接加相位即可，文件格式已支持。

### 实施要点

1. **起始票数 OCR**：御魂任务开始时（屏障通过后）去结界突破页读一次票数。
   现成资产：`tasks/RealmRaid/assets.py:71` `O_NUMBER`（DigitCounter，"27/30" 格式），
   参考用法 `tasks/RealmRaid/script_task.py` `is_ticket()` / `check_ticket()`。
2. **掉落计数**：每局结算界面用模板图 `I_REALM_RAID_PASS`
   （`tasks/Component/LootStatistics/assets.py:15`，配套 `loot_detect()` 目前是空壳）
   统计本局是否掉券。估算：`当前票 ≈ 起始票 + 掉落数`。
   模板在御魂结算界面的匹配阈值需实测调整。
   注意结算界面点击逻辑在 `tasks/Orochi/script_task.py` `battle_wait()`（418 行附近），
   队长/队员两侧都要接入（队员走 `check_take_over_battle`）。
3. **触发与暂停**：估算票 ≥ 阈值（建议配置项，默认 27~28）→ 本方写 `need_raid`；
   双方每局循环读状态文件，看到任一方 `need_raid` 就一起退房间
   （`exit_room()` / `exit_team()`），写 `raiding`。
4. **任务内打突破**：当前进程内直接调用 RealmRaid 任务逻辑
   （`tasks/RealmRaid/script_task.py` 的 `ScriptTask`，注意其 `run()` 结尾会
   `set_next_run` + `raise TaskEnd`，需捕获 TaskEnd 或小改使其支持内部调用）。
5. **恢复组队**：本方打完写 `raid_done`，等对方也 `raid_done`（屏障复用），
   队长重新建房邀请（回到 `run_leader` 流程），队员重新等邀请。
   注意 `limit_count` / `limit_time` 是整个 run() 的，突破期间是否计时要想清楚。
6. **容错**：状态条目带时间戳；对方崩溃/超时要有兜底（如超过 N 分钟单方面继续御魂）。
7. **配置项**：`team_sync` 组下加 `raid_trigger_enable`、`ticket_threshold`（默认 27）、
   `raid_sync_timeout` 等。

### 参考代码位置

- 探索任务的先例（票够阈值立即调度突破）：`tasks/Exploration/base.py:328` `activate_realm_raid()`
- 邀请/再次邀请：`tasks/Component/GeneralInvite/general_invite.py` `run_invite()` / `check_and_invite()`
- 队员等待：`tasks/Orochi/script_task.py` `run_member()`
- OCR 数字工具：`module/ocr/sub_ocr.py` `DigitCounter`
