# Go-to-Market & Risiko Bisnis - BengkelKu SaaS (Sample)

## 1. Alur Eksekusi 90 Hari Pertama

```mermaid
flowchart LR
    P1["Hari 1–14: Concierge Pilot 15 Bengkel"] --> G{"Konversi >= 4 bengkel?"}
    G -- "Ya" --> P2["Hari 15–45: Kanvas Klaster + Iklan Lokal"]
    G -- "Tidak" --> R["Revisi Onboarding / Value Metric"]
    P2 --> P3["Hari 46–90: Target 40+ Bengkel Aktif & Referral"]
```

## 2. Register Risiko Bisnis

| Risiko | Kemungkinan | Dampak | Mitigasi |
|---|---|---|---|
| *Churn* > 6%/bulan karena malas input stok | Tinggi | Tinggi | Pre-load katalog 100 sparepart populer & sesi onboarding 30 menit |
| CAC lapangan > IDR 280.000/bengkel | Sedang | Sedang | Program referral "Gratis 1 bulan" untuk bengkel yang mereferensikan rekan |
| Gangguan integrasi WhatsApp gateway | Rendah | Tinggi | Sediakan antrean retry + fallback notif via email/in-app |
