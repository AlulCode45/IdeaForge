---
name: strategy-analyst
description: >-
  Use this skill when the user wants strategic analysis of a project or
  business: SWOT, opportunities and threats, PESTEL, Porter's Five Forces,
  management and operations planning, team, finance and unit economics, and
  go-to-market, ideally built on market research findings.
---

# Strategy Analyst

Run the analysis in stages. Each stage ends with a checkpoint question; never start the next stage without the user's approval.

## Stages

1. **SWOT & TOWS** -> `08-swot.md`
   - Tie every Strength, Weakness, Opportunity, Threat to evidence in `07-market-research.md`, `14-customer-discovery.md`, and `15-competitor-analysis.md`. Add a TOWS action matrix (SO, WO, ST, WT).
2. **Opportunity & Environment** -> `09-opportunity-analysis.md`
   - Ranked opportunities (Impact vs Effort), PESTEL, Porter's Five Forces, and positioning.
3. **Management & Operations** -> `10-management-plan.md`
   - Team, key hires, operational SOPs, tools, partnerships, governance, KPIs/OKRs.
4. **Pricing & Computed Finance** -> `11-financial-plan.md`
   - **Mandatory delegation**: Use `pricing-strategist` for pricing/channel waterfall and `financial-modeler` (`model.py`) for 3-scenario numbers, cash chart, and sensitivity. Do NOT invent financial projections in prose.
5. **Go-to-Market & Business Risk Register** -> `12-go-to-market-and-risk.md`
   - Channels, launch plan, first 90 days, and the canonical **Business/Market Risk Register** (likelihood, impact, mitigation; technical/delivery risks stay in `06-risks-and-mitigation.md`).

## Rules

- If market research is missing, offer to run `market-researcher` first.
- Use tables and Mermaid charts for clarity; label every claim (`Verified`, `Estimate`, `Assumption`).
- **Checkpoint after each stage**: summarize in 3–5 bullets, then ask "Lanjut ke tahap berikutnya: <nama tahap>?" (lanjut / revisi / berhenti).
