---
name: compliance-checker
description: >-
  Use this skill to identify legal, regulatory, and operational compliance
  requirements for a project or business, with Indonesia as the default
  jurisdiction: business licensing, product permits, tax, intellectual
  property, data protection, and supply-chain dependencies.
---

# Compliance Checker

This is a **research checklist, not legal advice**. Always advise the user to confirm with a licensed lawyer, notary, or tax consultant.

## Indonesia Regulatory Quick-Checklist (verify live `.go.id` sources)

| Domain | Common Checkpoints | Official Reference |
|---|---|---|
| Entity & Licensing | PT / PT Perorangan / CV, NIB & KBLI risk level via OSS RBA | `oss.go.id` |
| Sector Permits | BPOM / PIRT (food/cosmetics), Halal (BPJPH), SNI, PSE (Komdigi) | `pom.go.id`, `halal.go.id`, `komdigi.go.id` |
| Tax | NPWP, PPh Final UMKM 0,5% (omzet <= Rp 4,8M/tahun), PKP/PPN threshold | `pajak.go.id` |
| IP & Consumer | Merek/Hak Cipta (DJKI), UU Perlindungan Konsumen, aturan e-commerce | `dgip.go.id` |
| Data Privacy | UU PDP No. 27/2022 (consent, retention, breach notice, cross-border) | Official UU PDP text |

## Workflow

1. **Classify the business**: product vs service, physical vs digital, B2C vs B2B, online sales, personal data handling, import/export, regulated sector.
2. **Research current rules** with live sources (`.go.id` / primary law first, score source grade `A`/`B`/`C` and record `(accessed YYYY-MM-DD)`).
3. **Compliance Table**: Requirement | Applies (Yes/No/Unsure) | Authority | Est. Cost & Lead Time | Deadline | Source (`A`/`B`/`C`) | Status.
4. **Operations & Supply Chain**: key suppliers, single points of failure, capacity limits, lead times, backup options.
5. **Launch Blockers (Red Flags)**: list any mandatory permit before revenue/launch and how to verify.
6. **Save** to `prps/<project>/16-compliance-and-legal.md`. Checkpoint: ask whether to continue.
