---
name: market-researcher
description: >-
  Use this skill when the user wants market research for a project, product, or
  business idea: market size, trends, target customers, competitors, pricing
  benchmarks, and demand signals, using live web/browser research with sources.
---

# Market Researcher

Research the market with live sources using whatever web search, fetch, or browser tools are available in your agent environment (e.g., `search_web`, `WebSearch`/`WebFetch`, browser subagent, or MCP browser tools).

## Workflow

1. **Scope the Research**: Confirm industry, geography (default: Indonesia), target segment, and decision supported.
2. **Triangulate Market Size (Mandatory)**:
   - Compute **TAM / SAM / SOM** using **both** Top-Down (industry reports) and Bottom-Up (`target customers x ARPU x realistic capture %`).
   - Show explicit formulas and flag if Top-Down vs Bottom-Up diverges by >2x.
3. **Research These Areas** (cite URL + `(accessed YYYY-MM-DD)` + source grade `A`/`B`/`C`):
   - **Trends & demand signals**: search interest, regulation, community discussions.
   - **Target customers**: segments, pain points, buying behavior, willingness to pay.
   - **Market-level competitor landscape** (high-level 3–5 players & pricing benchmarks; deep feature/review mining belongs to `competitor-analyst`).
4. **Evidence Discipline**:
   - Label every figure `[Verified]` (2+ A/B sources), `[Estimate]` (derived with formula), or `[Unverified]`. Never invent numbers; if unavailable, state "Data not found".
5. **Save**: Write to `prps/<project>/07-market-research.md` (or `ideas/<topic>/` if Quick Brief) with a `Sources` table.
6. **Checkpoint**: Summarize top 3 findings + biggest data gap, then ask: "Lanjut ke tahap berikutnya (`competitor-analyst` -> `15-competitor-analysis.md`)?"
