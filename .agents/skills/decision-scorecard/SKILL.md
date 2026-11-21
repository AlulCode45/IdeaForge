---
name: decision-scorecard
description: >-
  Use this skill when the user must decide between go, no-go, pivot, or choose
  among several ideas: weighted Go/No-Go scorecard, portfolio comparison
  matrix, automatic red-team review, and Decision Log (ADR) entries.
---

# Decision Scorecard

Make decisions auditable and immune to grade inflation.

## Scoring Rubric (1 to 5)

| Score | Standard |
|---|---|
| 1 | No evidence / critical blocker / negative unit economics |
| 2 | Weak signal / major unmitigated risk / thin margin |
| 3 | Mixed evidence / viable only under explicit conditions |
| 4 | Strong multi-source signal (`A`/`B`) / healthy LTV:CAC (>=3x) / manageable risk |
| 5 | Verified demand (LOI, pre-orders, paid pilots) / defensible edge / clear compliance path |

Rule: **Never assign 4 or 5 without citing a `Verified` or `A`/`B` source file.**

## Workflow

1. **Red-team first**: apply `devils-advocate` (core assumptions, 6-month pre-mortem, top risks) before scoring.
2. **Score** using [the template](../../../templates/scorecard.md). Default weights (sum = 100): Market demand 20, Evidence quality 15, Unit economics 20, Feasibility 15, Competitive edge 10, Risk and compliance 10, Founder fit 10.
3. **Verdict & Sensitivity**:
   - `>= 4.0` = Go | `3.0-3.9` = Go with conditions (list them) | `< 3.0` = No-Go or Pivot.
   - Run a +/-10 pt weight-shift check on the top two criteria to see if the verdict flips.
   - State the exact evidence that would change the verdict.
4. **Compare ideas** (when several): one matrix, same criteria, ranked, saved to `ideas/<topic>/` or `prps/INDEX.md`.
5. **Log the decision** in `prps/<project>/decisions/ADR-NNN-<slug>.md` using [the ADR template](../../../templates/decision-log-adr.md), and save `prps/<project>/17-scorecard-and-decision.md`.
6. **Checkpoint**: ask the user to confirm the decision before proceeding to `executive-reporter`.
