# ADR-001: Free Trial 14 Hari vs Freemium Permanen

- **Date**: 2026-11-22
- **Status**: Accepted

## Context
Bengkel UMKM sensitif terhadap biaya di awal, tetapi model *freemium* permanen berisiko membebani biaya variabel WhatsApp/server (`IDR 22.000/bengkel/bulan`) tanpa konversi.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| A. Freemium permanen (fitur dasar gratis) | Akuisisi cepat | Biaya variabel terus berjalan dari user non-bayar |
| B. Free Trial 14 hari + Concierge Setup | Biaya terkontrol, memfilter user serius | Butuh onboarding cepat di minggu ke-1 |

## Decision
Pilih Opsi B: Free Trial 14 hari dengan bantuan setup katalog 100 sparepart populer.

## Rationale and evidence
Menjaga gross margin 86,4% dan payback CAC 1,6 bulan pada [11-financial-plan.md](../11-financial-plan.md).

## Consequences and revisit trigger
Jika konversi trial-to-paid < 25% setelah 30 bengkel uji, pertimbangkan paket Starter terbatas tanpa notifikasi WhatsApp otomatis.
