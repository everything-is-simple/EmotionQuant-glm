# EmotionQuant

EmotionQuant is a sentiment-driven quantitative system for China A-shares.
The project now follows a **Spiral closed-loop model** instead of a linear Stage pipeline.

## Current status (Truth First)

- Repository status: `Skeleton + documentation baseline`.
- Design, roadmap, and governance are aligned to Spiral execution.
- Production-grade business loops are not finished yet; implementation starts from `S0`.

## Core principles

1. Sentiment-first; a single technical indicator must not independently trigger trading.
2. Local data is the default source; remote APIs are supplemental.
3. No hardcoded paths/secrets; use config/env injection.
4. Enforce A-share rules (T+1, limit-up/down, trading sessions).
5. Every spiral must close with command, test, artifact, review, and sync.

## Architecture (implementation baseline)

- Data Layer
- Signal Layer (MSS / IRS / PAS)
- Validation Layer (factor + weight validation gates)
- Integration Layer
- Backtest Layer (interface-first, replaceable engine)
- Trading Layer
- Analysis Layer
- GUI Layer

Primary references:

- `docs/system-overview.md`
- `docs/module-index.md`
- `Governance/ROADMAP/ROADMAP-OVERVIEW.md`

## Development model (Spiral)

- Default: 7 days per spiral, one primary objective per spiral.
- Scope: 1-3 capability slices per spiral.
- Terminology: use **Capability Pack (CP)**; existing `ROADMAP-PHASE-*.md` names are compatibility only.
- Closure gates are mandatory:
  - runnable command
  - automated test
  - inspectable artifact
  - synced docs/records

Workflow references:

- `Governance/steering/workflow/6A-WORKFLOW-phase-to-task.md`
- `Governance/steering/workflow/6A-WORKFLOW-task-to-step.md`
- `Governance/ROADMAP/TASK-TEMPLATE.md`

## Quick setup

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

Optional extras:

```bash
pip install -e ".[backtest]"
pip install -e ".[visualization]"
```

Basic check:

```bash
pytest -v
```

## Repository

- `origin`: `https://github.com/everything-is-simple/EmotionQuant_beta.git`
