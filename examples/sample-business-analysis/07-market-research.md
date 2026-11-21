# Riset Pasar - BengkelKu SaaS (Sample)

- **Tanggal Riset**: 2026-11-22
- **Geografi**: Indonesia (fokus awal Jawa Timur & Jabodetabek)

## 1. Triangulasi Ukuran Pasar (TAM / SAM / SOM)

| Lapisan | Top-Down [Estimate] | Bottom-Up [Estimate] | Catatan |
|---|---|---|---|
| **TAM** | ~120.000 bengkel motor independen di Indonesia x IDR 2,388 juta/tahun = ~IDR 286,5 miliar/tahun | 120.000 bengkel x IDR 199.000/bln x 12 = IDR 286,5 miliar/tahun | Selaras (rasio 1,0x) |
| **SAM** | Bengkel urban 2–6 stall yang siap digital (~25% TAM) = IDR 71,6 miliar/tahun | 30.000 bengkel urban x IDR 199.000 x 12 = IDR 71,6 miliar/tahun | Target pasar yang terjangkau digital |
| **SOM (Tahun 1)** | 0,7% SAM = ~IDR 500 juta ARR | 204 bengkel aktif di Bulan ke-12 x IDR 199.000 x 12 = IDR 487,1 juta ARR | Sesuai proyeksi skenario dasar `model.py` |

## 2. Sinyal Permintaan & Segmen

- **Segmen Primer**: Pemilik bengkel motor independen (usia 25–45 tahun, 2–6 mekanik, omzet IDR 30–120 juta/bulan) yang sering kehilangan margin akibat stok sparepart tidak tercatat [Assumption].
- **Pemicu Pembelian**: Kebocoran stok oli/kampas rem, kerumitan hitung bagi hasil mekanik tiap minggu, dan keinginan meningkatkan *repeat service* pelanggan [Assumption].

## Sources (Ilustratif)

| Sumber | Grade | Tanggal Akses | Catatan |
|---|---|---|---|
| Data populasi bengkel UMKM Jawa Timur (ilustratif) | C (Sample) | (accessed 2026-11-22) | Angka simulasi untuk contoh format |
| Benchmark harga POS UMKM Indonesia (Rp 150rb–350rb/bln) | C (Sample) | (accessed 2026-11-22) | Referensi posisi harga IDR 199.000 |
