# ADR-001: 14-Day Free Trial vs Permanent Freemium

- **Date**: 2026-11-22
- **Status**: Accepted

## Context
SME workshops are price-sensitive upfront, but a permanent freemium tier would incur ongoing WhatsApp/server variable costs (`IDR 22,000/shop/month`) from non-paying users.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| A. Permanent freemium (basic tier free) | Fast top-of-funnel sign-ups | Ongoing variable cost from non-paying users |
| B. 14-Day Free Trial + Concierge Setup | Controlled COGS, filters serious buyers | Requires fast Week-1 onboarding |

## Decision
Select Option B: 14-day free trial with guided setup of the top 100 popular spare parts.

## Rationale and evidence
Protects the 86.4% gross margin and 1.6-month CAC payback in [11-financial-plan.md](../11-financial-plan.md).

## Consequences and revisit trigger
If trial-to-paid conversion is < 25% after 30 pilot workshops, evaluate a stripped-down Starter tier without automated WhatsApp notifications.
