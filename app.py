"""KuliahCheck - cek kesiapan kuliah.

Flask + Jinja2, tanpa database. Data disimpan di file JSON (folder data/):
  - items.json    : daftar barang yang harus dibawa
  - riwayat.json  : centang per tanggal (untuk halaman riwayat)
"""
import json
import os
import re
import tempfile
import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template, request

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ITEMS_FILE = os.path.join(DATA_DIR, "items.json")
HISTORY_FILE = os.path.join(DATA_DIR, "riwayat.json")

WIB = timezone(timedelta(hours=7))  # ubah jika berada di zona waktu lain
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
HARI_SINGKAT = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]

MAX_ITEMS = 30
KEEP_DAYS = 90

DEFAULT_ITEMS = [
    {"id": "laptop", "name": "Laptop", "emoji": "💻", "days": []},
    {"id": "charger", "name": "Charger", "emoji": "🔌", "days": []},
    {"id": "buku", "name": "Buku/catatan", "emoji": "📓", "days": []},
    {"id": "alat-tulis", "name": "Alat tulis", "emoji": "✏️", "days": []},
    {"id": "tugas", "name": "Tugas", "emoji": "📄", "days": []},
    {"id": "id-card", "name": "ID card", "emoji": "🪪", "days": []},
    {"id": "uang", "name": "Uang/alat pembayaran", "emoji": "💳", "days": []},
]

# Cek struktur folder di awal supaya pesan errornya jelas (bukan "Internal Server Error").
REQUIRED_FILES = [
    "templates/base.html", "templates/index.html", "templates/riwayat.html",
    "static/css/style.css", "static/js/app.js",
]
_missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(BASE_DIR, f))]
if _missing:
    raise SystemExit(
        "\nStruktur folder belum benar. File berikut tidak ditemukan di " + BASE_DIR + ":\n  - "
        + "\n  - ".join(_missing)
        + "\n\nPastikan file HTML ada di folder 'templates' dan CSS/JS di folder 'static',"
        + "\nsejajar dengan app.py. Cara termudah: ekstrak kuliahcheck.zip lalu jalankan dari dalam folder itu.\n"
    )

app = Flask(__name__)
lock = threading.Lock()


# ---------- penyimpanan file JSON ----------
def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, data):
    """Tulis atomik: tulis ke file sementara lalu ganti file asli."""
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_items():
    items = read_json(ITEMS_FILE, None)
    if items is None:
        items = DEFAULT_ITEMS
        write_json(ITEMS_FILE, items)
    return items


# ---------- logika kesiapan ----------
def now_wib():
    return datetime.now(WIB)


def date_key(dt):
    return dt.strftime("%Y-%m-%d")


def format_tanggal(dt):
    return f"{HARI[dt.weekday()]}, {dt.day} {BULAN[dt.month - 1]} {dt.year}"


def items_for_weekday(items, weekday):
    """Barang tanpa pilihan hari berlaku setiap hari."""
    return [i for i in items if not i.get("days") or weekday in i["days"]]


def sync_entry(history, scheduled, key):
    """Pastikan entri hari ini ada dan sesuai daftar barang terbaru."""
    entry = history.setdefault(key, {"scheduled": {}, "checked": []})
    entry["scheduled"] = {i["id"]: i["name"] for i in scheduled}
    entry["checked"] = [c for c in entry.get("checked", []) if c in entry["scheduled"]]
    return entry


def prune(history):
    cutoff = date_key(now_wib() - timedelta(days=KEEP_DAYS))
    for k in [k for k in history if k < cutoff]:
        del history[k]


def percent_of(done, total):
    return int(done * 100 / total + 0.5) if total else 0


def message_for(percent, missing, total):
    if total == 0:
        return "Belum ada barang untuk hari ini. Tambahkan dulu di bagian Kelola barang."
    if percent == 100:
        return "Siap berangkat! Semua sudah masuk tas."
    if percent < 50:
        return "Tunggu dulu. Masih banyak yang belum masuk tas."
    if len(missing) <= 3:
        daftar = missing[0] if len(missing) == 1 else ", ".join(missing[:-1]) + " dan " + missing[-1]
        return f"Hampir siap. Tinggal {daftar}."
    return f"Hampir siap. Tinggal {len(missing)} barang lagi."


def build_status(scheduled, entry):
    checked = set(entry["checked"])
    rows = [{"id": i["id"], "name": i["name"], "emoji": i.get("emoji", "🎒"),
             "checked": i["id"] in checked} for i in scheduled]
    total = len(rows)
    done = sum(1 for r in rows if r["checked"])
    percent = percent_of(done, total)
    missing = [r["name"] for r in rows if not r["checked"]]
    if total == 0:
        level = "empty"
    elif percent == 100:
        level = "success"
    elif percent < 50:
        level = "danger"
    else:
        level = "warning"
    return {"rows": rows, "total": total, "done": done, "percent": percent,
            "message": message_for(percent, missing, total), "level": level}


def load_state():
    """Baca semua data dan kembalikan keadaan hari ini (panggil di dalam lock)."""
    now = now_wib()
    items = load_items()
    history = read_json(HISTORY_FILE, {})
    scheduled = items_for_weekday(items, now.weekday())
    entry = sync_entry(history, scheduled, date_key(now))
    return now, items, history, scheduled, entry


# ---------- halaman ----------
@app.route("/")
def index():
    with lock:
        now, items, history, scheduled, entry = load_state()
        prune(history)
        write_json(HISTORY_FILE, history)
        status = build_status(scheduled, entry)
    return render_template("index.html", s=status, items=items, tanggal=format_tanggal(now),
                           hari=HARI, hari_singkat=HARI_SINGKAT, active="hari-ini")


@app.route("/riwayat")
def riwayat():
    with lock:
        now, _, history, _, _ = load_state()
        today = date_key(now)

    hari_list = []
    for offset in range(6, -1, -1):
        d = now - timedelta(days=offset)
        entry = history.get(date_key(d))
        sched = entry["scheduled"] if entry else {}
        pct = percent_of(len(set(entry["checked"]) & set(sched)), len(sched)) if sched else None
        hari_list.append({"label": HARI_SINGKAT[d.weekday()], "tanggal": f"{d.day} {BULAN[d.month - 1][:3]}",
                          "percent": pct, "today": offset == 0})

    nilai = [h["percent"] for h in hari_list if h["percent"] is not None]
    rata = int(sum(nilai) / len(nilai) + 0.5) if nilai else None
    penuh = sum(1 for n in nilai if n == 100)

    # streak: hari berturut-turut dengan kesiapan 100%
    streak, d = 0, now
    if (history.get(today) is None) or percent_of(
            len(set(history[today]["checked"]) & set(history[today]["scheduled"])),
            len(history[today]["scheduled"])) < 100:
        d = now - timedelta(days=1)
    while True:
        e = history.get(date_key(d))
        if not e or not e["scheduled"] or set(e["scheduled"]) - set(e["checked"]):
            break
        streak += 1
        d -= timedelta(days=1)

    # barang yang paling sering terlewat (hari lampau yang ada centangnya)
    lupa = Counter()
    for key, e in history.items():
        if key == today or not e.get("checked"):
            continue
        for item_id, name in e["scheduled"].items():
            if item_id not in e["checked"]:
                lupa[name] += 1
    paling_lupa = lupa.most_common(5)

    return render_template("riwayat.html", hari_list=hari_list, rata=rata, penuh=penuh,
                           streak=streak, paling_lupa=paling_lupa, active="riwayat")


# ---------- API (dipanggil oleh JavaScript) ----------
def error(msg, code=400):
    return jsonify(error=msg), code


@app.post("/api/toggle/<item_id>")
def api_toggle(item_id):
    with lock:
        now, _, history, scheduled, entry = load_state()
        if item_id not in entry["scheduled"]:
            return error("Barang itu tidak ada di daftar hari ini.", 404)
        if item_id in entry["checked"]:
            entry["checked"].remove(item_id)
        else:
            entry["checked"].append(item_id)
        write_json(HISTORY_FILE, history)
        return jsonify(build_status(scheduled, entry))


@app.post("/api/reset")
def api_reset():
    with lock:
        now, _, history, scheduled, entry = load_state()
        entry["checked"] = []
        write_json(HISTORY_FILE, history)
        return jsonify(build_status(scheduled, entry))


@app.post("/api/items")
def api_add_item():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    emoji = str(data.get("emoji", "")).strip()[:8] or "🎒"
    days = sorted({d for d in data.get("days", []) if isinstance(d, int) and 0 <= d <= 6})
    if not name or len(name) > 30:
        return error("Nama barang harus diisi, maksimal 30 karakter.")
    with lock:
        items = load_items()
        if len(items) >= MAX_ITEMS:
            return error(f"Maksimal {MAX_ITEMS} barang.")
        if any(i["name"].lower() == name.lower() for i in items):
            return error("Barang itu sudah ada di daftar.")
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "barang"
        items.append({"id": f"{slug}-{uuid.uuid4().hex[:6]}", "name": name, "emoji": emoji, "days": days})
        write_json(ITEMS_FILE, items)
    return jsonify(ok=True), 201


@app.delete("/api/items/<item_id>")
def api_delete_item(item_id):
    with lock:
        items = load_items()
        sisa = [i for i in items if i["id"] != item_id]
        if len(sisa) == len(items):
            return error("Barang tidak ditemukan.", 404)
        write_json(ITEMS_FILE, sisa)
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
