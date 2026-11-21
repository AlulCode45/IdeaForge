---
name: financial-modeler
description: >-
  Use this skill when the user needs a real, testable financial model for a
  project or business: three scenarios, unit economics (CAC, LTV, margin),
  break-even, cash runway, and sensitivity analysis, computed by script rather
  than described in prose.
---

# Financial Modeler

Numbers must be computed by script, never narrated or guessed in prose.

## Supported Modes (`model_type`)
- `transactional`: unit sales, repeat orders (CAC charged only on newly acquired customers `units / repeat_orders_per_customer`), CAPEX, channel fee, tax rate.
- `saas`: monthly ARPU, active customer retention/churn (`monthly_churn_rate`), new customer acquisition growth, LTV (`unit_margin / churn`), CAC payback months.

## Workflow

1. **Collect Inputs** (align pricing with `pricing-strategist` and infra/COGS with `tech-feasibility-estimator`; log guesses in `13-assumption-register.md`):
   - `price`, `unit_variable_cost`, `channel_fee_rate`, `tax_rate`, `capex`, `monthly_fixed_costs`, `starting_cash`, `cac`, volume/growth/churn/repeat parameters.
2. **Write** `prps/<project>/model/inputs.json` (see [example_inputs.json](./scripts/example_inputs.json) or [example_saas_inputs.json](./scripts/example_saas_inputs.json)).
3. **Run the Model**:
   ```bash
   python3 .agents/skills/financial-modeler/scripts/model.py prps/<project>/model/inputs.json \
     --months 12 --locale auto \
     --charts-dir prps/<project>/assets \
     --json-out prps/<project>/model/summary.json
   ```
   This generates 4 SVG charts in `assets/`: `cash-projection.svg`, `revenue-profit.svg`, `unit-economics.svg`, and `sensitivity-heatmap.svg`.
4. **Save & Embed**: Paste/append the generated Markdown output into `prps/<project>/11-financial-plan.md` and embed all 4 SVG charts (`assets/*.svg`) so numbers are immediately scannable.
5. **Sanity Checks**:
   - Gross margin plausible for industry?
   - `LTV / CAC >= 3.0x` and CAC payback `<= 12 months`?
   - Lowest cash point stays positive in base case (and document required cash buffer if pessimistic goes negative)?
6. **Checkpoint**: explain the top sensitivity driver from the 2-way table and ask whether to continue.
