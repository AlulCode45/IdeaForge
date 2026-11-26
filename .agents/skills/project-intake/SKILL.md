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

## Engagement Tracks

| Track | When to use | Output location |
|---|---|---|
| `quick` | Early exploration, 1–2 page note, rapid validation | `ideas/<slug>/YYYY-MM-DD-brief.md` |
| `prd` | Standalone product/feature PRD (coding-agent ready) | `prds/YYYY-MM-DD-<slug>/` (`PRD.md`, `13-assumption-register.md`) |
| `tech` | Software/architecture spec without full business case | `prps/YYYY-MM-DD-<slug>/` (`00`–`06`, `13`, `17`) |
| `business` | Commercial/business feasibility without deep code spec | `prps/YYYY-MM-DD-<slug>/` (`00`, `07`–`19`) |
| `full` | End-to-end product + business + financial + compliance | `prps/YYYY-MM-DD-<slug>/` (`00`–`19`) |

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
