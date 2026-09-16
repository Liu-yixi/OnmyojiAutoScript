# Personal fork maintenance

## Repositories

- `origin`: https://github.com/Liu-yixi/OnmyojiAutoScript.git
- `upstream`: https://github.com/runhey/OnmyojiAutoScript.git
- Reference implementation: https://github.com/AzurTian/OnmyojiAutoScript (branch `mine`).

Keep the upstream license and author attribution. Do not copy reference changes without reviewing dependencies and attribution.

## Initial local baseline (2026-09-16)

The installed checkout starts at `00888a40` on the upstream development history.
At inspection it was 49 commits behind `upstream/dev`, with no unique committed changes.
Uncommitted changes include the following independent workstreams:

1. Task execution windows: configuration, scheduler integration, persistence, UI descriptions, documentation and tests.
2. Battle and activity fixes: preparation retries, reward exclusion defaults, activity entry assets, resource OCR, reward popup handling and navigation.
3. Mall navigation and scales purchase completion, with regression tests.
4. Existing local work requiring separate review: AreaBoss, KekkaiUtilize, ReplaceShikigami, DemonEncounter, HeroTest and Orochi team synchronization.

Preserve these workstreams in separate commits. Do not overwrite the fork's `master` or `dev` with the older installed baseline. Use a dedicated work branch and review before merging. The baseline is not a stable release.

## Known unresolved issues

- Activity count limit reads a counter that is not updated by the current battle flow.
- Activity resource OCR can drop leading digits; a single zero reading can stop the task incorrectly.
- The midnight activity supply popup can leave the script clicking the underlying challenge button.
- Violation notices are not handled as an immediate stop condition.
- Generic stuck/click protection can restart and retry despite an unresolved blocking window.
- Post-activity SoulsTidy was scheduled but not started in the inspected run; scheduling needs investigation.

## Data boundaries

Do not commit account configuration, credentials, logs, complete game screenshots, runtime state or emulator files. Keep small recognition templates only after checking that they contain no account identifiers. Existing tracked generic configuration templates are distinct from account configuration.

Before every push inspect `git diff --cached --stat` and `git diff --cached`. Do not stage the entire workspace without reviewing new files. Preserve unrelated staged changes.

## Baseline validation

The following suite passed 32 tests during initial inspection. It does not validate all existing local work or resolve the issues above.

```powershell
.\toolkit\python.exe -m unittest tests.module.test_task_windows tests.tasks.test_rich_man_navigation tests.tasks.test_activity_shikigami_reward tests.tasks.test_activity_shikigami_resources tests.tasks.Component.GeneralBattle.test_reward_exclusions tests.tasks.Component.GeneralBattle.test_battle_prepare
```

## Future changes

Use a separate branch for each fix; record the trigger, resulting behavior, validation and remaining limitations. Fetch upstream updates first, review their changes, then integrate on a separate branch. Validate before updating the running installation. Do not force-push shared branches.
