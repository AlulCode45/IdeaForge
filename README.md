# BrainstormingAgent

Workspace terstruktur untuk **Brainstorming Partner & Strategic Analysis Agent** berbasis Antigravity Customizations (`AGENTS.md` + `.agents/skills/`). Dirancang untuk membantu eksplorasi ide, validasi bisnis, penyusunan PRP (*Project Requirements & Plan*), riset pasar, pemodelan keuangan, hingga laporan eksekutif siap cetak (PDF) menggunakan **Python 3 stdlib** (tanpa dependency `pip` eksternal).

---

## Fitur Utama

- **Engagement Tracks (Tidak One-Size-Fits-All)**: Pilih kedalaman sesuai kebutuhan lewat `project-intake` (`quick` brief di `ideas/`, `tech` PRP, `business` feasibility, atau `full` pipeline) dan scaffold otomatis dengan `scripts/init_project.py`.
- **Alur Bertahap dengan Checkpoint**: Analisis berjalan langkah demi langkah; agent merangkum hasil, menjalankan *red-team* singkat, dan meminta persetujuan sebelum lanjut ke tahap berikutnya.
- **Standar Bukti & Linter Otomatis**: Setiap klaim dilabeli (`[Verified]`, `[Estimate]`, `[Assumption]`, `[Unverified]`), sumber diberi skor (`A`/`B`/`C`) beserta tanggal akses, dan divalidasi otomatis oleh `scripts/lint_project.py`.
- **Model Keuangan Terhitung (Transactional & SaaS)**: Mendukung mode unit transaksional (perbaikan akuntansi CAC vs repeat order) maupun SaaS (MRR, churn, payback), CAPEX, channel fee, pajak, sensitivitas 2-dimensi, dan generator grafik SVG otomatis via `model.py`.
- **Riset Pasar, Kompetitor & Eksperimen**: Triangulasi TAM/SAM/SOM (Top-Down vs Bottom-Up), matriks kompetitor + *review mining* + ERRC, serta Experiment Cards dengan *Pass/Kill criteria* numerik sebelum eksekusi.
- **Red-Team, Rubrik Scorecard & Retrospective**: Rubrik penilaian 1–5 anti-*grade inflation*, uji sensitivitas bobot, pencatatan ADR, dan pelacakan aktual vs proyeksi (`19-retrospective.md`).
- **Export PDF Editorial + Mermaid**: Mendukung mode `--mode executive|technical|full`, cover page & daftar isi (TOC) otomatis, tabel multi-halaman rapi, grafik SVG, serta rendering diagram Mermaid.

---

## Prasyarat & Cara Mulai (Quick Start)

### Prasyarat
- **Antigravity** (otomatis membaca `AGENTS.md` dan seluruh skill di `.agents/skills/`).
- **Python 3** (hanya stdlib; tidak memerlukan paket `pip` tambahan).
- **Brave Browser / Google Chrome / Chromium** (digunakan oleh `export_pdf.py` dalam mode headless untuk merender PDF; path dapat dioverride lewat env `PDF_BROWSER`).

### Langkah Awal
1. Clone repository ini:
   ```bash
   git clone https://github.com/AlulCode45/BrainstormingAgent.git
   cd BrainstormingAgent
   ```
2. Buka folder `BrainstormingAgent` sebagai workspace di Antigravity.
3. Mulai sesi dengan menceritakan ide, tugas, atau masalah Anda, misalnya:
   - *"Aku mau brainstorm ide SaaS kasir untuk bengkel..."*
   - *"Inisialisasi project full feasibility untuk ide ini."*
   - *"Bantu validasi pricing dan hitung proyeksi SaaS 12 bulan."*
   - *"Audit bukti project ini dengan lint_project.py lalu export PDF."*

---

## Alur Kerja Analisis (Engagement Tracks & Staged Pipeline)

| Track | Kapan Dipakai | Output |
|---|---|---|
| `quick` | Eksplorasi awal / catatan cepat 1–2 halaman | `ideas/<slug>/YYYY-MM-DD-brief.md` |
| `tech` | Spesifikasi produk & arsitektur software | `prps/YYYY-MM-DD-<slug>/` (`00`–`06`, `13`, `17`) |
| `business` | Kelayakan bisnis & finansial tanpa spek teknis | `prps/YYYY-MM-DD-<slug>/` (`00`, `07`–`19`) |
| `full` | Produk + bisnis + finansial + kepatuhan lengkap | `prps/YYYY-MM-DD-<slug>/` (`00`–`19`) |

```text
Intake & Scaffold
  └─> PRP Teknis (00–06)
        └─> Riset Pasar (07) -> Kompetitor (15) -> Customer Discovery (14)
              └─> SWOT (08) -> Peluang (09) -> Manajemen (10)
                    └─> Pricing & Keuangan Terhitung (11)
                          └─> Kepatuhan & Legal (16) -> GTM & Risiko Bisnis (12)
                                └─> Audit Bukti & Linter (13) -> Scorecard Go/No-Go (17)
                                      └─> Executive Summary & PDF (18) -> Retrospective (19)
```

---

## Daftar Skill (20 Skill di `.agents/skills/`)

| Skill | Fungsi Utama | Output Utama |
|---|---|---|
| `project-intake` | Triase awal, pilih track (`quick`/`tech`/`business`/`full`), scaffold folder | Scaffold project |
| `ideation-facilitator` | Eksplorasi ide (*First Principles*, *SCAMPER*, *HMW*, *3-Horizon*) | Opsi & arah ide |
| `business-validator` | Validasi cepat (*Lean Canvas*, ICP, eksperimen dengan *Pass/Kill criteria*) | Ringkasan validasi |
| `project-scoper` | Pemecahan ide menjadi MVP (*MoSCoW*), arsitektur ringkas, dan task | Scope MVP & tugas |
| `prp-writer` | Penyusunan PRP detail per folder lengkap dengan diagram Mermaid | `prps/<project>/00`–`06` |
| `tech-feasibility-estimator` | Build-vs-buy, estimasi effort (man-days), infra/AI COGS, & baseline security | Update `03`, `06`, `inputs.json` |
| `market-researcher` | Riset TAM/SAM/SOM (Top-Down + Bottom-Up), tren, dan sumber bergrade `A`/`B`/`C` | `07-market-research.md` |
| `competitor-analyst` | Matriks kompetitor, *review mining*, peta posisi, dan ERRC (*Blue Ocean*) | `15-competitor-analysis.md` |
| `customer-discovery` | Panduan wawancara *Mom Test*, desain survei, JTBD, dan sintesis persona | `14-customer-discovery.md` |
| `experiment-designer` | Kartu eksperimen terstruktur dengan *Pass/Kill criteria* numerik & jadwal 1–4 minggu | Experiment cards |
| `pricing-strategist` | *Value metric*, paket tiering, WTP (Van Westendorp), dan *channel margin waterfall* | Pricing & input model |
| `strategy-analyst` | Analisis bertahap: SWOT/TOWS, PESTEL & Five Forces, manajemen, GTM & risiko bisnis | `08`–`12` |
| `financial-modeler` | Simulasi `transactional` & `saas`, CAPEX, pajak, sensitivitas 2-arah, & grafik SVG | `model/inputs.json` & `11` |
| `compliance-checker` | Checklist perizinan RI (OSS/NIB, BPOM, halal, pajak, DJKI, PSE, UU PDP) | `16-compliance-and-legal.md` |
| `devils-advocate` | Uji ketahanan ide (*pre-mortem*, identifikasi asumsi rapuh, mitigasi risiko) | Kritik & mitigasi |
| `evidence-auditor` | Audit sumber (`A`/`B`/`C`), penanda `[Stale]`, register asumsi, & run `lint_project.py` | `13-assumption-register.md` |
| `decision-scorecard` | Red-team otomatis, rubrik 1–5, scorecard Go/No-Go, uji sensitivitas bobot, & ADR | `17-scorecard-and-decision.md` |
| `executive-reporter` | Ringkasan 1 halaman, grafik SVG, *pitch/backlog outline*, dan export PDF | `18-executive-summary.md` & PDF |
| `retrospective-tracker` | Evaluasi aktual vs proyeksi, update asumsi/model, dan log keputusan pivot/scale | `19-retrospective.md` |
| `idea-logger` | Pengarsipan catatan brainstorming ke folder topik masing-masing | `ideas/<topic-slug>/` |

---

## Struktur Direktori

```text
BrainstormingAgent/
├── AGENTS.md                           # Aturan utama, tracks, quality gates, & privasi Git
├── README.md                           # Dokumentasi project
├── LICENSE                             # Lisensi repository
├── .gitignore
├── scripts/                            # Utilitas deterministik (Python 3 stdlib)
│   ├── init_project.py                 # Scaffold folder prps/ atau ideas/ + update INDEX.md
│   └── lint_project.py                 # Validator link, aritmatika scorecard, tag bukti, & anti-slop
├── tests/                              # Suite unit & integration test (unittest)
│   ├── test_model.py
│   ├── test_export_pdf.py
│   └── test_project_tools.py
├── .agents/
│   └── skills/                         # 20 skill modular (SKILL.md + scripts/)
├── templates/                          # Template baku dokumen
│   ├── assumption-register.md
│   ├── changelog.md
│   ├── decision-log-adr.md
│   ├── executive-summary.md
│   ├── experiment-card.md
│   ├── pricing-architecture.md
│   ├── retrospective.md
│   └── scorecard.md
├── examples/
│   └── sample-report/                  # Contoh laporan Markdown, SVG chart, & hasil export PDF
├── ideas/                              # Catatan brainstorming lokal (dikelompokkan per topik)
└── prps/                               # Dokumen PRP & analisa lengkap lokal per project
    └── INDEX.md                        # Daftar portofolio & status semua project
```

---

## Menjalankan Skrip & Test Secara Langsung

### 1. Inisialisasi Project (`init_project.py`)
```bash
python3 scripts/init_project.py --slug kasir-bengkel --title "Kasir Bengkel SaaS" --track full --model-type saas
```

### 2. Model Keuangan (`financial-modeler`)
Mode transaksional atau SaaS dengan output grafik SVG & ringkasan JSON:
```bash
python3 .agents/skills/financial-modeler/scripts/model.py \
  .agents/skills/financial-modeler/scripts/example_inputs.json \
  --months 12 --locale auto \
  --chart-out examples/sample-report/cash-projection.svg \
  --json-out /tmp/summary.json
```

### 3. Audit Kualitas Otomatis (`lint_project.py`)
```bash
python3 scripts/lint_project.py prps/<project-slug>
```

### 4. Export Laporan ke PDF (`executive-reporter`)
Export satu file Markdown dengan TOC:
```bash
python3 .agents/skills/executive-reporter/scripts/export_pdf.py \
  --input examples/sample-report/sample-executive-report.md \
  --output examples/sample-report/sample-executive-report.pdf \
  --title "Contoh Laporan Analisa Bisnis (Sample)" --toc
```
Atau gabungkan folder PRP berdasarkan mode (`executive`, `technical`, atau `full`):
```bash
python3 .agents/skills/executive-reporter/scripts/export_pdf.py \
  --project prps/<project-slug> --mode executive \
  --output prps/<project-slug>/assets/<project-slug>-report.pdf \
  --title "Nama Project"
```

### 5. Menjalankan Unit & Integration Tests
```bash
python3 -m unittest discover -s tests -v
```

---

## Aturan Git & Privasi Data

- **Tooling** (`.agents/skills/`, `scripts/`, `templates/`, `tests/`, `examples/`, `AGENTS.md`, `README.md`): commit dan push ke `origin` (`main`).
- **Data Proyek & Klien** (`prps/` dan `ideas/`): bersifat lokal secara default. **Jangan** di-push ke repository publik `origin` tanpa persetujuan eksplisit pengguna.

---

## Lisensi

Lihat file [LICENSE](LICENSE) untuk detail lisensi penggunaan dan distribusi.
