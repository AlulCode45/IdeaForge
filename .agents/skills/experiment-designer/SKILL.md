---
name: experiment-designer
description: >-
  Use this skill to design concrete, low-cost validation experiments with
  pre-committed numeric Pass/Kill criteria, sample sizes, guardrail metrics,
  and a 1–4 week test calendar before committing full build or launch budget.
---

# Experiment Designer

Every high-risk assumption deserves a cheap, falsifiable test before full execution.

## Workflow

1. **Select Target Assumptions**: Pick the top 1–3 Low-confidence x High-impact assumptions from `13-assumption-register.md`.
2. **Create Experiment Cards** using [the template](../../../templates/experiment-card.md):
   - **Hypothesis**: If [action], then [segment] will [behavior], because [rationale].
   - **Test Type**: smoke test landing page, concierge MVP, pre-order/DP, outbound cold test, or pricing A/B.
   - **Sample Size & Duration**: realistic for the budget (e.g., 7–14 days).
   - **Pre-committed Pass / Iterate / Kill Thresholds**: exact numbers decided *before* running.
   - **Guardrail Metrics**: e.g., max CAC, min margin, max refund rate.
3. **Sequence into a 1–4 Week Calendar**: order tests by cheapest/fastest first so a `Kill` stops wasted spend early.
4. **Save & Link**: Store cards in `prps/<project>/14-customer-discovery.md` (or `ideas/<topic>/` for Quick Briefs) and update `Test method` + `Kill trigger` in `13-assumption-register.md`.
