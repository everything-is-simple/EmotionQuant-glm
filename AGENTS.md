# AGENTS.md

This file is the concise entrypoint for automated agents in this repository.
Canonical policy is now **Spiral-first** and aligned with `README.md` + `CLAUDE.md`.

---

## Mandatory reading order

1. `README.md`
2. `CLAUDE.md` (system entry + workflow)
3. `docs/system-overview.md`, `docs/module-index.md`, `docs/naming-conventions.md`
4. `Governance/steering/系统铁律.md` and `Governance/steering/CORE-PRINCIPLES.md`
5. `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md`

---

## Non-negotiables (summary)

- **Sentiment-first**; single technical indicator must not independently trigger trading decisions.
- **Local-data first**; remote data is for supplementation only.
- **No hardcoded paths/secrets**; use Config/env.
- **Spiral delivery first**: each spiral must close with command + test + artifact + review + sync.
- **Workflow grading**: default `Scope -> Build -> Verify -> Sync`; escalate to strict 6A only for high-risk changes.
- **Keep docs in sync** with code and governance.

---

## Terminology

- Use `Capability Pack (CP)` as the execution term.
- Current files keep compatibility naming `ROADMAP-PHASE-*.md`.
- Do not interpret `Phase` in file names as linear stage gates.

---

## Quick references

- Project status: `Governance/record/development-status.md`
- Debts: `Governance/record/debts.md`
- Reusable assets: `Governance/record/reusable-assets.md`
- Tests & tooling: `pyproject.toml`, `requirements.txt`

---

## Tooling note (.claude)

- `.claude/` is retained as historical tooling assets.
- Reusable governance rules have been migrated to `Governance/steering/` and `Governance/ROADMAP/`.
- Do not treat `.claude` commands as canonical workflow requirements.
