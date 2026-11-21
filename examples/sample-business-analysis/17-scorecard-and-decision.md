# Go/No-Go Scorecard - BengkelKu SaaS

Date: 2026-11-22

## Weighted Evaluation

| Criterion | Weight | Score (1-5) | Weighted | Justification (link) |
|---|---|---|---|---|
| Market demand | 20 | 4 | 0.80 | 30.000+ bengkel urban belum terdigitalisasi ([07](07-market-research.md)) |
| Evidence quality | 15 | 2 | 0.30 | Masih tahap pra-pilot, butuh validasi 15 bengkel ([13](13-assumption-register.md)) |
| Unit economics | 20 | 5 | 1.00 | Gross margin 86,4%, LTV/CAC 13,7x, BEP Month 7 ([11](11-financial-plan.md)) |
| Feasibility | 15 | 4 | 0.60 | Arsitektur web POS ringan & modal IDR 75 juta aman ([00](00-overview.md)) |
| Competitive edge | 10 | 4 | 0.40 | Fitur vertikal komisi mekanik + katalog part ([15](15-competitor-analysis.md)) |
| Risk and compliance | 10 | 4 | 0.40 | Jalur OSS/PSE/UU PDP jelas & terjangkau ([16](16-compliance-and-legal.md)) |
| Founder fit | 10 | 4 | 0.40 | Eksekusi GTM terfokus pada klaster lokal ([12](12-go-to-market-and-risk.md)) |
| **Total** | 100 | | **3.90/5.0** | |

## Verdict
Go with conditions (3.0-3.9)

## Sensitivity Check (Weight Shift +/- 10 pts)
- Jika bobot `Evidence quality` dinaikkan +10% (25%) dan `Unit economics` diturunkan -10% (10%), skor total menjadi `3.60/5.0` — verdict tetap **Go with conditions**.

## Conditions / What would change this verdict
- Wajib lulus pilot 14 hari (>= 4 dari 15 bengkel konversi ke berbayar) sebelum menambah biaya tetap atau iklan berbayar.
- Lihat keputusan strategi akuisisi di [ADR-001](decisions/ADR-001-trial-vs-freemium.md).

## Red-team summary
- Ekonomi unit SaaS di atas kertas sangat tinggi (LTV/CAC 13,7x), tetapi sepenuhnya bergantung pada retensi pemilik bengkel setelah minggu ke-2.
