"""Inspect or explicitly clear one account's stop latch; never clicks the game."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from module.config.runtime_safety import RuntimeSafetyState


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('account', help='Account config name, without .json')
    parser.add_argument('--clear-stop', action='store_true', help='Use only after manually inspecting the game')
    args = parser.parse_args()
    state = RuntimeSafetyState(args.account)
    if args.clear_stop:
        state.clear_stop()
    print(json.dumps(state.read(), ensure_ascii=False, indent=2))
