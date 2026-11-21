---
name: retrospective-tracker
description: >-
  Use this skill after running validation experiments or launching an MVP to
  compare actual results against forecasts, update the Assumption Register and
  financial model inputs, and log Scale, Optimize, or Pivot decisions.
---

# Retrospective Tracker

Close the loop between desk projections and real-world evidence.

## Workflow

1. **Gather Actuals**: Ask the user for observed metrics (actual price/ARPU, units/active users, variable cost, CAC, repeat/churn rate, cash balance, experiment outcomes).
2. **Compute Variance**:
   - Compare actuals vs `prps/<project>/model/inputs.json` using [the template](../../../templates/retrospective.md).
   - Highlight every metric with `>20%` variance and state the root cause.
3. **Re-run Financial Model**:
   - Update `model/inputs.json` (or create a `v2` scenario) and re-run `model.py` to see updated break-even and runway.
4. **Update Evidence & Assumptions**:
   - Mark tested items in `13-assumption-register.md` as `confirmed` or `refuted`, and promote verified metrics to `[Verified]`.
5. **Log Decision**: Save to `prps/<project>/19-retrospective.md`. If the review triggers a pivot, pricing change, or stop, record an ADR in `decisions/ADR-NNN-<slug>.md` and update `prps/INDEX.md` + `CHANGELOG.md`.
