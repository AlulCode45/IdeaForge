---
name: pricing-strategist
description: >-
  Use this skill to design pricing and packaging strategy: value metrics,
  tiering (Good/Better/Best), willingness-to-pay (Van Westendorp) testing,
  channel margin & discount waterfalls, and finalized pricing inputs for
  financial-modeler.
---

# Pricing Strategist

Treat pricing as the highest-leverage driver of unit economics, not a single guessed number.

## Workflow

1. **Define the Value Metric**: What scales naturally with customer value (e.g., per seat, per outlet, per transaction, per bottle)?
2. **Benchmark & Anchor**: Pull competitor price tiers from `15-competitor-analysis.md` or `07-market-research.md` (`[Verified]` or `[Unverified]`).
3. **Design Packaging & Tiers** using [the template](../../../templates/pricing-architecture.md):
   - Entry (acquisition/wedge), Core (anchor tier), Pro/Enterprise (expansion margin).
4. **Compute Channel & Discount Waterfall**:
   - List Price -> (-) Marketplace / Payment Gateway Fee -> (-) Promo/Discount Allowance -> (-) Unit COGS = **Net Unit Contribution Margin**.
5. **WTP Validation Design**: Draft 4 Van Westendorp questions or a price-ladder test for `14-customer-discovery.md` / `experiment-designer`.
6. **Hand Off to `financial-modeler`**: Export finalized `price`, `unit_variable_cost`, and `channel_fee_rate` into `prps/<project>/model/inputs.json` and log key pricing assumptions in `13-assumption-register.md`.
