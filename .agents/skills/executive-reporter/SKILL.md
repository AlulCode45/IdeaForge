---
name: executive-reporter
description: >-
  Use this skill to turn a finished or in-progress PRP into decision-ready
  output: a one-page executive summary, decision memo, consistent charts, and
  an exportable report or pitch outline for investors, mentors, or partners.
---

# Executive Reporter

Busy decision-makers need the answer first, backed by consistent numbers.

## Workflow

1. **Read & Verify Consistency**:
   - Read `prps/<project>/` and `model/summary.json`. Never invent data not in the folder; flag gaps instead.
   - Ensure consistent number formatting (`IDR` uses `.` thousands and `,` decimals; `USD` uses `,` thousands and `.` decimals).
2. **Write Executive Summary** (`prps/<project>/18-executive-summary.md`) using [the template](../../../templates/executive-summary.md): start with `**Recommendation**: ...` (rendered as a highlight banner) and a 4-card `<!-- kpi-grid -->` strip (Target/Verdict, Break-Even, Gross Margin & LTV/CAC, Cash Runway), followed by problem, solution, market, evidence quality, economics, top risks, compliance blockers, and 30-day actions.
3. **Visuals & Diagrams**:
   - Embed the 4 computed SVG charts from `financial-modeler` (`assets/cash-projection.svg`, `assets/revenue-profit.svg`, `assets/unit-economics.svg`, `assets/sensitivity-heatmap.svg`).
   - Use Mermaid diagrams (` ```mermaid `) where helpful; `export_pdf.py` renders them to SVG automatically and adds clickable TOC + "↑ Daftar Isi" links + visual score bars on `Score (1-5)` tables.
4. **Run Linter Before Export**:
   ```bash
   python3 scripts/lint_project.py prps/<project>
   ```
   Fix any `FAIL` or anti-slop warnings before generating PDFs.
5. **Export PDF** (choose `--mode executive|technical|full`, and `--lang id|en` matching the document language):
   ```bash
   python3 .agents/skills/executive-reporter/scripts/export_pdf.py \
     --project prps/<project> --mode executive --lang <id|en> \
     --output prps/<project>/assets/<project>-report.pdf \
     --title "<Project Name>"
   ```
   Verify the printed byte size and page count.
6. **Optional Handoff Formats** (when requested):
   - **Slide Deck Outline** (`assets/pitch-outline.md`): 10-slide structure (Problem, Solution, Market, Traction/Discovery, Business Model, Competition, GTM, Financials, Risks, Ask).
   - **Action Backlog** (`assets/action-backlog.md`): Epic/Task list ready to import into Jira, Linear, or GitHub Issues.
7. **Update** `prps/INDEX.md` and `prps/<project>/CHANGELOG.md`.
