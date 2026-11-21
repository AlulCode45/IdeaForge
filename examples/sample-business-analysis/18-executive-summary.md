# Executive Summary - BengkelKu SaaS (Sample)

Date: 2026-11-22 | Version: v1.0 | Track: business | Currency: IDR | Confidentiality: Client-ready (Sample) | Decision status: Conditional

**Recommendation**: Lanjutkan ke **Concierge Pilot 14 hari pada 15 bengkel motor** dengan paket *free trial* 14 hari (bukan *freemium* permanen). Secara finansial skenario dasar mencapai titik impas di Month 7 dengan saldo kas tetap positif di ketiga skenario.

<!-- kpi-grid -->
Skor Keputusan | 3,90 / 5.0 | Go dengan syarat | good
Break-Even (Base) | Month 7 | 204 bengkel aktif M12 | good
Unit Economics | LTV/CAC 13,7x | Margin 86,4% · Payback 1,6 bln | good
Fokus Validasi | Churn <= 4,5% | Syarat utama pilot 14 hari | warn
<!-- /kpi-grid -->

| Section | Summary | Evidence Status |
|---|---|---|
| Problem | Bengkel motor UMKM kehilangan margin karena pencatatan part & komisi manual | [Assumption] |
| Solution | SaaS kasir bengkel + komisi mekanik + pengingat servis WhatsApp (IDR 199rb/bln) | [Assumption] |
| Target market and size | SAM 30.000 bengkel urban (~IDR 71,6M/thn); SOM Tahun 1 ~IDR 487 juta ARR | [Estimate] |
| Evidence quality | Contoh kasus ilustratif; perlu validasi pilot 15 bengkel | [Unverified] |
| Economics | ARPU IDR 199.000, margin 86,4%, BEP Month 7, kas M12 IDR 87,9 juta | [Estimate] |
| Top 3 risks and mitigations | Churn tinggi (pre-load part); CAC mahal (referral); WA gateway (retry queue) | [Estimate] |
| Compliance blockers | NIB/PT Perorangan, pendaftaran PSE Komdigi, kebijakan privasi UU PDP | [Estimate] |
| Next 30-day actions | 1) Bangun MVP katalog part; 2) Pilot 15 bengkel; 3) Update `inputs.json` | [Assumption] |

![Proyeksi Saldo Kas 12 Bulan](assets/cash-projection.svg)

![Struktur Ekonomi Unit & LTV vs CAC](assets/unit-economics.svg)

Links: [scorecard](17-scorecard-and-decision.md), [assumptions](13-assumption-register.md), [financials](11-financial-plan.md).
