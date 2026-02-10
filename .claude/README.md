# Claude Assets Status (.claude)

**Project**: EmotionQuant
**Status**: Historical compatibility assets (Spiral-first)
**Last updated**: 2026-02-07

---

## Canonical workflow

The canonical workflow is **not** defined in `.claude/`.
Use these sources in order:

1. `README.md`
2. `CLAUDE.md`
3. `Governance/steering/` (especially `CORE-PRINCIPLES.md` and `workflow/6A-WORKFLOW-task-to-step.md`)
4. `Governance/ROADMAP/`

`.claude/` is kept for tooling compatibility and local ergonomics.

---

## Current effective hooks

The active configuration is in `.claude/settings.json`.

| Hook | Script |
|---|---|
| `SessionStart` | `.claude/hooks/session_start.py` |
| `UserPromptSubmit` | `.claude/hooks/user_prompt_submit.py` |
| `PreToolUse.Edit` | `.claude/hooks/pre_edit_check.py` |
| `PreToolUse.Write` | `.claude/hooks/pre_edit_check.py` |
| `PostToolUse.Edit` | `.claude/hooks/post_edit_check.py` |
| `PostToolUse.Write` | `.claude/hooks/post_edit_check.py` |

Notes:
- `pre_edit_orchestrator.py` is retained for compatibility experiments, but not wired in `settings.json`.
- Current stage detection reads `Governance/record/development-status.md` (Spiral `S0-S6`).

---

## Principles enforced by hooks (current)

- No hardcoded absolute paths in edited Python content.
- S6 only: block simplification markers (`HACK`, `临时绕过`, `hardcoded`).
- Development stages allow `TODO/FIXME` per governance policy.

---

## Commands and agents

Many legacy command docs still use "Phase" wording. Treat them as historical examples.
When conflict occurs, follow:

- `Spiral` execution terms from governance docs
- `Capability Pack (CP)` naming from repository policy

---

## Maintenance rule

When `.claude/` docs conflict with governance/docs:

1. Fix `settings.json` + hook scripts first (runtime truth)
2. Sync this README summary
3. Keep long historical notes optional and clearly labeled

---

## Quick self-check

```powershell
python .claude/hooks/session_start.py
python .claude/hooks/pre_edit_check.py < $null
```

(Second command validates script availability; real checks depend on `CLAUDE_FILE_PATH` and stdin content.)
