---
name: project-intake
description: >-
  Use this skill at the start of a new project or brainstorming request to
  classify the engagement track (Quick Brief, Product PRD, Tech PRP, Business
  Feasibility, or Full), capture constraints (audience, currency, jurisdiction,
  confidentiality), and scaffold the project folder.
---

# Project Intake

Route every new request to the right depth before generating heavy documents.

## Engagement Tracks (Modular Super PRD)

Every product/project starts in `prds/YYYY-MM-DD-<slug>/` with a coding-agent-ready `PRD.md` and can be upgraded progressively in-place (`--upgrade <dir> --add tech|business|full`) without moving folders (`prps/` remains legacy-compatible):

| Track | When to use | Output location |
|---|---|---|
| `quick` | Early exploration, 1–2 page note, rapid validation | `ideas/<slug>/YYYY-MM-DD-brief.md` |
| `prd` *(default)* | Core PRD (problem, visual flows, stories + AC, FR/NFR, API) | `prds/YYYY-MM-DD-<slug>/` (`PRD.md`, `13-assumption-register.md`) |
| `tech` | Core PRD + architecture, ERD, roadmap, tech risks, scorecard | `prds/YYYY-MM-DD-<slug>/` (`PRD.md`, `03`–`06`, `13`, `17`) |
| `business` | Core PRD + market, competitors, strategy, financial model, compliance | `prds/YYYY-MM-DD-<slug>/` (`PRD.md`, `07`–`19`, `model/inputs.json`) |
| `full` | Complete Super PRD (Core + Technical + Business + Finance + Compliance) | `prds/YYYY-MM-DD-<slug>/` (`PRD.md`, `03`–`19`, `model/inputs.json`) |

## Workflow

1. **Ask 3–4 Intake Questions** (only what is missing):
   - **Goal & Audience**: personal decision, internal team, investor pitch, or client deliverable?
   - **Track & Model Type**: `quick` / `prd` / `tech` / `business` / `full`, and `transactional` vs `saas` (if business/full)?
   - **Context**: currency (`IDR`/`USD`), jurisdiction (default `Indonesia`), timeline/budget constraints.
   - **Confidentiality**: local-only (default) or cleared for sharing?
2. **Scaffold Deterministically**:
   ```bash
   python3 scripts/init_project.py --slug <slug> --title "<Title>" --track <track> --currency <IDR|USD> --model-type <transactional|saas>
   ```
3. **Hand Off**: Propose the first skill (`ideation-facilitator`, `business-validator`, `prd-writer`, `prp-writer`, or `market-researcher`) and wait for confirmation.
