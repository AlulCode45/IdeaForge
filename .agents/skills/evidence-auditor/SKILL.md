---
name: evidence-auditor
description: >-
  Use this skill to audit the quality of evidence behind any analysis: build and
  maintain the Assumption Register, score sources, separate facts from
  assumptions, and flag stale research. Use before trusting or presenting
  market research, financials, or strategy conclusions.
---

# Evidence Auditor

Make every claim traceable, dated, and testable.

## Source Scoring

| Score | Meaning |
|---|---|
| A | Primary or official (government `.go.id`, filings, company data, own interviews) |
| B | Reputable secondary (established media, industry bodies, research firms) |
| C | Weak or biased (blogs, vendor marketing, forums, undated pages) |

Require at least 2 independent `A` or `B` sources for any decision-driving number. A single `C`-only claim is `[Unverified]`.

## Workflow

1. **Run Automated Linter First**:
   ```bash
   python3 scripts/lint_project.py prps/<project>
   ```
   Review all `FAIL` and `WARN` items (broken links, arithmetic mismatches, missing tags, stale dates).
2. **Extract & Label**: Audit every key claim and number as `[Verified]`, `[Estimate]` (show formula), `[Assumption]`, or `[Unverified]`.
3. **Update Assumption Register** at `prps/<project>/13-assumption-register.md` using [the template](../../../templates/assumption-register.md) (include `Kill trigger`, `Owner`, `Date reviewed`).
4. **Flag Staleness**: Mark data older than 12 months (6 months for fast-moving tech/AI markets) as `[Stale]` and recommend a refresh.
5. **Report Top 5 Riskiest Assumptions** (Low confidence x High impact) with the cheapest experiment to test each.
6. **Checkpoint**: ask whether to continue to `decision-scorecard`.
