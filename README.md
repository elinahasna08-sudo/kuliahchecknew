# KuliahCheck - Cek Kesiapan Kuliah

Website sederhana untuk mengecek barang sebelum berangkat kuliah (laptop, charger,
buku, alat tulis, tugas, ID card, uang). Setiap barang dicentang, lalu muncul
persentase kesiapan dan tas yang terisi sesuai persentasenya.

Dibuat dengan **Python (Flask)** tanpa database. Data disimpan di file JSON.

## Cara menjalankan

Butuh Python 3.9 atau lebih baru.

```bash
# 1. (opsional) buat virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 2. pasang Flask
pip install -r requirements.txt

# 3. jalankan
python app.py
```

Buka http://127.0.0.1:5000 di browser. Untuk mode debug: `FLASK_DEBUG=1 python app.py`
(di Windows PowerShell: `$env:FLASK_DEBUG="1"; python app.py`).

## Fitur

- Checklist harian dengan persentase kesiapan dan pesan otomatis
- Tas yang terisi sesuai persentase, confetti saat 100%
- Tambah dan hapus barang, bisa diatur per hari (misal jas lab hanya hari Rabu)
- Riwayat 7 hari, rata-rata kesiapan, hari berturut-turut siap, dan barang yang paling sering ketinggalan
- Tampilan mobile-first, mendukung mode gelap

## Struktur proyek

```
kuliahcheck/
├── app.py               # server Flask: halaman, API, logika persentase
├── requirements.txt
├── data/                # dibuat otomatis saat pertama dijalankan
│   ├── items.json       # daftar barang
│   └── riwayat.json     # centang per tanggal
├── templates/           # Jinja2: base, index, riwayat
└── static/
    ├── css/style.css
    └── js/app.js        # toggle centang tanpa reload (fetch ke API)
```

## Alur kerja (untuk presentasi)

1. Browser membuka `/`, Flask membaca `data/items.json` dan `data/riwayat.json`.
2. Python menghitung persentase: `barang tercentang / barang hari ini x 100`.
3. Saat barang diklik, JavaScript memanggil `POST /api/toggle/<id>`, Python mengubah
   data, menyimpannya ke JSON, lalu mengirim persentase terbaru ke halaman.

## Catatan dan keterbatasan

- Tanpa database, jadi cocok untuk satu pengguna atau prototipe. Jika dipakai banyak
  orang, data akan tercampur dan sebaiknya dipindah ke database (misalnya SQLite).
- Penulisan file memakai lock dan penggantian file atomik agar tidak rusak saat ada
  dua permintaan bersamaan.
- Zona waktu memakai WIB (UTC+7). Ubah `WIB` di `app.py` jika perlu.
- Statistik "paling sering ketinggalan" hanya menghitung hari yang ada centangnya.
