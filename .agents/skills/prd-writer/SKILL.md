---
name: prd-writer
description: >-
  Use this skill when the user wants to write, structure, or refine a
  comprehensive, coding-agent-ready Product Requirements Document (PRD) for a
  product or feature: problem statement, goals/non-goals, success metrics,
  personas/JTBD, user flows (Mermaid), user stories with Given/When/Then
  acceptance criteria, prioritized FR/NFR IDs, edge cases, data/API contracts,
  analytics events, rollout/feature flags, and test/verification criteria.
---

# PRD Writer (Product Requirements Document)

Write a crystal-clear, testable, coding-agent-ready PRD that aligns product, design, engineering, QA, and stakeholders on **what** to build and **why** (complementing `prp-writer`, which owns deep system architecture, full ERD, and end-to-end delivery planning).

## Storage Modes (Flexible)

- **Standalone Feature / Product PRD (`--track prd`)**:
  Scaffold deterministically into `prds/YYYY-MM-DD-<slug>/`:
  ```bash
  python3 scripts/init_project.py --slug <slug> --title "<Product or Feature Name>" --track prd
  ```
  Creates `PRD.md`, `README.md`, `CHANGELOG.md`, `13-assumption-register.md`, `decisions/`, `assets/`, and registers in `prds/INDEX.md`.
- **Embedded inside an Existing PRP (`tech` or `full` track)**:
  Save as `prps/<project>/PRD.md` (or `prps/<project>/prds/<feature-slug>.md` for multi-feature specs) and cross-link from `README.md` and `02-requirements.md`.

## Workflow

1. **Clarify Gaps (2-4 focused questions)**:
   - Target user (ICP/persona) and the specific pain or job to be done.
   - Primary product goal, target metric, and target release scope.
   - Hard constraints (platform, timeline, compliance/UU PDP, dependencies).
   - Explicit **Non-Goals / Out of Scope** boundaries to prevent scope creep.
2. **Author the PRD** using [the template](../../../templates/prd.md):
   - **Document Control & Summary**: Status, Owner, Target Release, KPI strip (`<!-- kpi-grid -->`), and `**Recommendation**:` / release objective.
   - **Problem Statement & Evidence**: Ground claims with `[Verified]`, `[Estimate]`, `[Assumption]`, or `[Unverified]` and link to discovery/market docs if available.
   - **Goals, Non-Goals & Success Metrics**: North Star metric, primary KPIs, and guardrail metrics (e.g., error rate, latency, churn).
   - **Target Users, Personas & JTBD**: Who benefits, frequency, current workaround, and Jobs-to-be-Done statements.
   - **User Flows & UX States**: Mermaid `flowchart` / `stateDiagram-v2` + explicit UI states (Empty, Loading, Error, Success, Offline/Permission Denied).
   - **User Stories & Acceptance Criteria**: Unique IDs (`US-001`, ...) with testable **Given / When / Then** (or **Diberikan / Ketika / Maka**) acceptance criteria.
   - **Functional Requirements (`FR-001`, ...)**: Unique IDs, priority (`P0 Must` / `P1 Should` / `P2 Could`), linked `US-xxx`, concrete behavior, and dependencies.
   - **Non-Functional Requirements (`NFR-001`, ...)**: Performance targets, security/RBAC, UU PDP data minimization, accessibility, and availability.
   - **Edge Cases & Error Handling (`EC-001`, ...)**: Boundary conditions, concurrency/retry, partial failures, and user-facing recovery paths.
   - **Data & API Contract Outline**: Coding-agent-friendly summary of core entities, key endpoints/events, and invariants (defer full ERD/architecture to `prp-writer` if needed).
   - **Analytics & Telemetry Events**: Event name, trigger, properties, and owner so success metrics are actually measurable.
   - **Rollout, Feature Flags & Test Criteria (`TC-001`, ...)**: Phased rollout, feature flag strategy, rollback trigger, and unit/integration/E2E/UAT verification checklist.
   - **Dependencies, Open Questions & Risks**: Track unresolved product assumptions in `13-assumption-register.md`.
3. **Validate Quality Gates**:
   ```bash
   python3 scripts/lint_project.py prds/YYYY-MM-DD-<slug>
   ```
   Fix all `FAIL` and `WARN` items (missing sections, duplicate requirement IDs, missing Given/When/Then criteria, broken links, or editorial slop).
4. **Optional Editorial PDF & Interactive Web GUI Export**:
   ```bash
   python3 .agents/skills/executive-reporter/scripts/export_pdf.py \
     --project prds/YYYY-MM-DD-<slug> --mode prd --lang <id|en> \
     --output prds/YYYY-MM-DD-<slug>/assets/<slug>-prd.pdf \
     --title "<Product or Feature Name> PRD"

   python3 .agents/skills/executive-reporter/scripts/export_web.py \
     --project prds/YYYY-MM-DD-<slug> --mode prd --lang <id|en> \
     --output prds/YYYY-MM-DD-<slug>/assets/<slug>-prd.html \
     --title "<Product or Feature Name> PRD"
   ```
5. **Red-Team Pass & Checkpoint**:
   - Highlight the top 3 product, scope-creep, or edge-case risks.
   - Ask the user whether to approve/revise the PRD, or continue to `prp-writer` (`03-architecture.md` / `04-data-model.md`), `tech-feasibility-estimator`, or `experiment-designer`.
6. **Git & Privacy Rule**:
   - Keep `prds/` local by default. **Never** push `prds/` to `origin` without explicit user confirmation.
