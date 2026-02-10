# .claude Integration Notes (Historical)

**Status**: Historical reference, not canonical governance source.
**Last updated**: 2026-02-07

---

## Scope

This file only explains how local `.claude` tooling maps to current repo workflow.
Canonical policy lives in:

- `README.md`
- `CLAUDE.md`
- `Governance/steering/`

---

## Runtime truth

- Hook wiring: `.claude/settings.json`
- Hook scripts: `.claude/hooks/*.py`
- Spiral stage source: `Governance/record/development-status.md`

If any old `.claude` markdown conflicts with runtime truth, runtime truth wins.

---

## Mapping

| Concern | Current source |
|---|---|
| Workflow terms | Spiral (`S0-S6`) |
| Task governance | `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md` |
| Path/security checks | `.claude/hooks/pre_edit_check.py` + `scripts/quality/local_quality_check.py` |
| Session reminders | `.claude/hooks/session_start.py` |
| Prompt hints | `.claude/hooks/user_prompt_submit.py` |

---

## De-risking rules

- Do not treat legacy "Phase" wording as stage-gate requirements.
- Do not rely on undocumented orchestrators unless `settings.json` explicitly wires them.
- Keep `.claude/` lightweight; avoid duplicating governance docs.
