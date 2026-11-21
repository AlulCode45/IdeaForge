---
name: tech-feasibility-estimator
description: >-
  Use this skill to evaluate technical feasibility, build-vs-buy choices,
  cloud/infrastructure/AI API unit costs (COGS), engineering effort (man-days
  with contingency), and baseline security/privacy requirements for a software
  or technical project.
---

# Tech Feasibility Estimator

Ground technical plans in realistic cost, effort, and operational risk numbers.

## Workflow

1. **Build vs Buy / Reuse Triage**:
   - For each major capability (auth, billing, hosting, AI/LLM, analytics), compare Build vs SaaS/OSS on setup time, monthly fixed cost, and lock-in risk.
2. **Estimate Engineering Effort**:
   - Break MVP features (`02-requirements.md`) into T-shirt sizes (`S`/`M`/`L`/`XL`) and man-day ranges (optimistic–pessimistic) plus a 20–30% integration/QA buffer.
3. **Estimate Infra & API COGS** (feeds `financial-modeler`):
   - **Monthly Fixed Infra**: base DB, hosting, monitoring -> feeds `monthly_fixed_costs`.
   - **Unit Variable Tech Cost**: cloud bandwidth/storage/LLM API calls per active user or transaction -> feeds `unit_variable_cost`.
   - **Upfront Build CAPEX**: one-time setup, licenses, dev contractor cost -> feeds `capex`.
4. **Baseline Security & Reliability Checklist**:
   - Auth/RBAC, encryption in transit/at rest, backup/RPO, rate limiting, and UU PDP personal-data minimization.
5. **Save**: Append findings to `prps/<project>/03-architecture.md` and technical risks to `06-risks-and-mitigation.md`. Checkpoint: ask whether to continue.
