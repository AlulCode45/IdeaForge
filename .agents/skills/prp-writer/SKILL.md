---
name: prp-writer
description: >-
  Use this skill when discussing a software or technical project and the user
  wants a very detailed, clear, sequential, and thorough Project Requirements &
  Plan (PRP), complete with architecture, user flows, data models, milestones,
  and visual diagrams or charts stored in a structured project folder.
---

# PRP Writer (Project Requirements & Plan)

Produce a crystal-clear, sequential PRP inside `prps/YYYY-MM-DD-<project-slug>/`.

## Initialization

Always scaffold the folder deterministically first:
```bash
python3 scripts/init_project.py --slug <project-slug> --title "<Project Name>" --track <tech|full>
```

## Folder Structure

- `00-overview.md` — Executive summary, goals, metrics, non-goals
- `01-users-and-flows.md` — Personas, journeys, Mermaid user flows
- `02-requirements.md` — Functional (MoSCoW + acceptance criteria) & non-functional
- `03-architecture.md` — System architecture, tech stack, sequence diagrams (use `tech-feasibility-estimator` for infra COGS & effort)
- `04-data-model.md` — ERD & schema definitions
- `05-roadmap-and-tasks.md` — Phased milestones & actionable tasks
- `06-risks-and-mitigation.md` — **Technical & delivery risks** (business/market risks live in `12-go-to-market-and-risk.md`)
- `07`–`19` — Business, market, financial, compliance, scorecard, executive summary, and retrospective modules
- `decisions/`, `model/`, `assets/`, `CHANGELOG.md`, `README.md`

## Workflow

1. **Ensure Context Is Complete**: Verify problem, target users, core features, stack constraints, and success criteria. Ask 2–4 targeted questions if gaps remain.
2. **Write Sequentially**: Keep each numbered file focused, cross-linked from `README.md`, with Mermaid diagrams (`01`, `03`, `04`, `05`) and optional assets in `assets/`.
3. **Privacy & Git Rule**: Keep `prps/` local by default. **Never** push `prps/` to `origin` unless the user explicitly approves.
