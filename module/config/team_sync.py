# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
"""跨实例组队同步屏障。

通过共享 JSON 状态文件协调同一台机器上的多个脚本实例（如 oas1 和 oppo），
用于御魂等组队任务：各实例在任务开始时写入 ready，
队长确认队员就绪后再建房邀请，先就绪的一方在屏障处等待另一方。

文件格式:
    {
        "orochi": {
            "oas1": {"phase": "ready",  "timestamp": "2026-07-29T14:00:00"},
            "oppo": {"phase": "synced", "timestamp": "2026-07-29T14:01:00"}
        }
    }

phase 取值:
    ready  —— 实例已启动组队任务，等待配对
    synced —— 屏障已被队长消费（双方已配对，进入邀请流程）
"""
import json
from pathlib import Path
from datetime import datetime

from filelock import FileLock
from module.logger import logger


class TeamSync:
    """组队同步屏障（跨进程安全）。

    用法:
        sync = TeamSync(scope='orochi', config_name='oas1')
        sync.set_phase('ready')
        if sync.partner_ready('oppo', stale_seconds=600):
            sync.mark_synced('oppo')
    """

    STATE_FILE = Path.cwd() / "log" / ".team_sync_state.json"

    def __init__(self, scope: str, config_name: str):
        """Args:
            scope: 同步域，一般为任务名小写，如 'orochi'。
            config_name: 当前实例的配置名，如 'oas1'。
        """
        self.scope = scope
        self.config_name = config_name
        self._lock = FileLock(str(self.STATE_FILE) + ".lock", timeout=5)

    def _read(self) -> dict:
        """读取状态文件。调用方需持有 _lock。文件不存在或损坏时返回空状态。"""
        if not self.STATE_FILE.exists():
            return {}
        try:
            with open(self.STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("[TeamSync] State file corrupted, resetting")
            return {}

    def _write(self, state: dict) -> None:
        """写入状态文件。调用方需持有 _lock。"""
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def set_phase(self, phase: str) -> None:
        """写入自己的相位并刷新时间戳。"""
        with self._lock:
            state = self._read()
            scope = state.setdefault(self.scope, {})
            scope[self.config_name] = {
                "phase": phase,
                "timestamp": datetime.now().isoformat(),
            }
            self._write(state)
        logger.info(f"[TeamSync] '{self.config_name}' -> '{phase}' (scope={self.scope})")

    def partner_ready(self, partner: str, stale_seconds: float) -> bool:
        """判断队友是否处于有效的 ready 状态。

        队友的 ready 时间戳超过 stale_seconds 视为过期（来自上一轮任务的残留），
        不算就绪。
        """
        with self._lock:
            state = self._read()
        entry = state.get(self.scope, {}).get(partner)
        if not entry or entry.get("phase") != "ready":
            return False
        try:
            ts = datetime.fromisoformat(entry.get("timestamp", ""))
        except (ValueError, TypeError):
            return False
        return (datetime.now() - ts).total_seconds() <= stale_seconds

    def mark_synced(self, partner: str) -> None:
        """队长消费屏障：把双方（已在场的一方法）相位标记为 synced。

        标记后旧的 ready 不再生效，下一轮组队需要双方重新写入 ready。
        """
        now = datetime.now().isoformat()
        with self._lock:
            state = self._read()
            scope = state.setdefault(self.scope, {})
            for name in (self.config_name, partner):
                if name in scope:
                    scope[name]["phase"] = "synced"
                    scope[name]["timestamp"] = now
            self._write(state)
        logger.info(f"[TeamSync] '{self.config_name}' and '{partner}' synced (scope={self.scope})")
