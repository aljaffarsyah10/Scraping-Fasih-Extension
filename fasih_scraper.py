"""
Fasih Assignment Scraper - Python CLI (High-Performance Parallel Edition)
Script mandiri untuk menarik seluruh data penugasan (hingga puluhan ribu) dari Fasih SM BPS
secara paralel (multi-threaded) dengan HTTP Connection Pooling dan Adaptive Recursive Sharding.

Fitur Utama:
- Multi-threaded Worker Pool (Concurrency terkontrol 3-5 workers) untuk mempercepat penarikan hingga 4-5x lipat.
- HTTP Keep-Alive Connection Pooling via requests.Session() (mengeliminasi overhead negosiasi SSL/TLS berulang).
- Auto-Sharding / Partisi Otomatis per Wilayah (Kecamatan/Desa) untuk menembus limit 1.000 data Elasticsearch.
- Thread-safe deduplikasi otomatis berbasis UUID penugasan (`id`).
- Mode Hemat Kolom (--minimal) untuk langsung fokus ke nomor bangunan, nama keluarga/usaha, dan kode SLS.
"""

import argparse
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
import pandas as pd
import urllib3

# Nonaktifkan peringatan SSL tidak terverifikasi agar tampilan konsol bersih
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_ENDPOINT = "https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode"
DEFAULT_SURVEY_PERIOD_ID = "fd68e454-ba45-4b85-8205-f3bf777ded24"
DEFAULT_XSRF_TOKEN = "55edd9d0-2888-4d52-8572-a96445cd513d"

# Daftar 10 Kecamatan resmi di Kabupaten Kepulauan Siau Tagulandang Biaro (7108)
KECAMATAN_SITARO = [
    ("7108010", "BIARO"),
    ("7108020", "TAGULANDANG SELATAN"),
    ("7108030", "TAGULANDANG"),
    ("7108040", "TAGULANDANG UTARA"),
    ("7108050", "SIAU TIMUR SELATAN"),
    ("7108060", "SIAU TIMUR"),
    ("7108070", "SIAU BARAT SELATAN"),
    ("7108080", "SIAU BARAT"),
    ("7108090", "SIAU TENGAH"),
    ("7108100", "SIAU BARAT UTARA"),
]

FASIH_COLUMN_LABELS = {
    "data1": "data1_Nama_Keluarga_Bangunan_Usaha",
    "data2": "data2_Alamat_Prelist",
    "data3": "data3_No_Urut_Bangunan_IDSBR",
    "data4": "data4_NIB_No_KK",
    "data5": "data5_Email",
    "data6": "data6_Skala_Usaha_Jenis_Prelist",
    "data7": "data7_Jumlah_Usaha",
    "data8": "data8_Kode_Pos",
    "data9": "data9_Perubahan_SLS",
    "data10": "data10_IDSBR_UMKM_SLS_Sama"
}

def flatten_record(obj, prefix="", res=None):
    if res is None:
        res = {}
    if not isinstance(obj, dict):
        return res

    for key, val in obj.items():
        prop_name = f"{prefix}_{key}" if prefix else key
        if val is None:
            res[prop_name] = ""
        elif isinstance(val, dict):
            flatten_record(val, prop_name, res)
        elif isinstance(val, list):
            if len(val) == 0:
                res[prop_name] = ""
            elif not isinstance(val[0], dict):
                res[prop_name] = ", ".join(str(x) for x in val)
            else:
                res[prop_name] = json.dumps(val)
        else:
            res[prop_name] = str(val) if isinstance(val, (int, float)) and key.startswith("data") else val
    return res

def extract_minimal_record(it):
    """Ekstraksi ringan: hanya kolom-kolom inti untuk analisis bangunan & SLS"""
    reg = it.get("region", {})
    l1 = reg.get("level1", {})
    l2 = l1.get("level2", {})
    l3 = l2.get("level3", {})
    l4 = l3.get("level4", {})
    l5 = l4.get("level5", {})

    data3_raw = str(it.get("data3", "") or "")
    no_bgn = data3_raw.split("/")[0].strip() if data3_raw else ""

    return {
        "id": it.get("id", ""),
        "codeIdentity": it.get("codeIdentity", ""),
        "kode_sls": l5.get("fullCode", "") or (it.get("codeIdentity", "")[:14] if it.get("codeIdentity") else ""),
        "nama_sls": l5.get("name", ""),
        "nama_desa": l4.get("name", ""),
        "nama_kecamatan": l3.get("name", ""),
        "nama_assignment_keluarga": it.get("data1", "") or "",
        "alamat": it.get("data2", "") or "",
        "nomor_bangunan_raw": data3_raw,
        "nomor_bangunan_bersih": no_bgn,
        "status_penugasan": it.get("assignmentStatusAlias", "")
    }

class ParallelFasihScraper:
    def __init__(self, cookie_header, xsrf_token, survey_period_id, max_workers=4, page_size=100, is_minimal=False):
        self.cookie_header = cookie_header
        self.xsrf_token = xsrf_token
        self.survey_period_id = survey_period_id
        self.max_workers = max_workers
        self.page_size = min(page_size, 150)
        self.is_minimal = is_minimal

        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=max_workers, pool_maxsize=max_workers * 2, max_retries=3)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://fasih-sm.bps.go.id",
            "Referer": f"https://fasih-sm.bps.go.id/app/surveys/a0429e96-51a5-477b-a415-485f9c153004/{survey_period_id}/data",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-XSRF-TOKEN": xsrf_token,
            "Cookie": cookie_header
        })

        self.records_lock = threading.Lock()
        self.all_records = {} # ID -> dict
        self.print_lock = threading.Lock()

    def log(self, msg):
        with self.print_lock:
            print(msg, flush=True)

    def fetch_api(self, search_val="", start=0, length=100):
        payload = {
            "start": start,
            "length": length,
            "columns": [{"data": "id", "orderable": True}],
            "order": [],
            "search": {"value": str(search_val), "regex": False},
            "assignmentExtraParam": {
                "surveyPeriodId": self.survey_period_id,
                "assignmentErrorStatusType": -1,
                "filterTargetType": "TARGET_ONLY"
            }
        }

        retries = 3
        wait_time = 3
        while retries > 0:
            try:
                resp = self.session.post(DEFAULT_ENDPOINT, json=payload, verify=False, timeout=25)
                if resp.status_code == 429:
                    self.log(f"⚠️ Terkena limitasi kecepatan server (HTTP 429). Menunggu {wait_time} detik...")
                    time.sleep(wait_time)
                    wait_time *= 2
                    retries -= 1
                    continue

                if resp.status_code == 401:
                    raise PermissionError(
                        "Sesi login Fasih SM Anda telah KEDALUWARSA (HTTP 401 Unauthorized).\n"
                        "💡 Solusi:\n"
                        "1. (Paling Praktis) Buka web Fasih SM di Chrome (login jika logout), lalu gunakan Ekstensi Chrome 'Ekspor Raw Assignment' yang langsung memakai sesi browser Anda.\n"
                        "2. Atau salin Cookie terbaru dari DevTools Network (F12) dan jalankan: python fasih_scraper.py --cookie \"COOKIE_BARU\" --xsrf \"XSRF_BARU\""
                    )

                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:150]}")

                text = resp.text
                if text.startswith("<!DOCTYPE") or "<script" in text:
                    raise ValueError("Tantangan WAF / Sesi Login Kedaluwarsa. Silakan perbarui cookie sesi.")

                return resp.json()
            except requests.RequestException as e:
                retries -= 1
                if retries <= 0:
                    raise e
                time.sleep(2)

        return {}

    def fetch_slice_to_end(self, search_val, label):
        """Menarik seluruh halaman dari satu shard pencarian hingga tuntas"""
        collected = []
        page = 0
        total_hit = None

        while True:
            start_offset = page * self.page_size
            if total_hit is not None and start_offset >= total_hit:
                break
            if start_offset >= 1000:
                # Batas Elasticsearch 1.000
                break

            data = self.fetch_api(search_val=search_val, start=start_offset, length=self.page_size)
            items = data.get("searchData") or []

            if total_hit is None:
                total_hit = data.get("totalHit", 0)
                if total_hit == 0:
                    break

            if not items:
                break

            collected.extend(items)
            page += 1
            time.sleep(0.15) # Jeda sopan mikro

        # Simpan ke storage thread-safe
        with self.records_lock:
            for it in collected:
                if self.is_minimal:
                    self.all_records[it["id"]] = extract_minimal_record(it)
                else:
                    self.all_records[it["id"]] = flatten_record(it)

        return len(collected), total_hit or 0

    def process_kecamatan(self, kec_code, kec_name):
        """Memproses satu kecamatan secara paralel: mempartisi ke desa, dan ke SLS jika desa >= 1.000"""
        probe = self.fetch_api(search_val=kec_code, start=0, length=1)
        kec_total = probe.get("totalHit", 0)

        if kec_total == 0:
            return kec_name, 0, 0

        if kec_total <= 1000:
            self.log(f"   ⚡ [{kec_name}] Total: {kec_total} data (<=1000). Mengunduh langsung...")
            fetched, target = self.fetch_slice_to_end(kec_code, kec_name)
            self.log(f"   ✓ [{kec_name}] Selesai: {fetched} data.")
            return kec_name, fetched, kec_total
        else:
            self.log(f"   ⚠️ [{kec_name}] Total: {kec_total} data (>1000). Mempartisi per desa (001-040)...")
            kec_collected = 0
            for d in range(1, 41):
                desa_code = f"{kec_code}{d:03d}"
                d_probe = self.fetch_api(search_val=desa_code, start=0, length=1)
                desa_total = d_probe.get("totalHit", 0)
                if desa_total == 0:
                    continue

                if desa_total < 1000:
                    # Desa aman (< 1000), tarik langsung
                    d_fetched, _ = self.fetch_slice_to_end(desa_code, desa_code)
                    kec_collected += d_fetched
                else:
                    # Desa padat (>= 1000), partisi ke tingkat SLS (0001 - 0025) agar tidak terpotong!
                    self.log(f"      🏘️ [{desa_code}] Desa Padat ({desa_total} >= 1000). Mempartisi per SLS...")
                    for s in range(1, 26):
                        sls_code = f"{desa_code}{s:04d}"
                        s_probe = self.fetch_api(search_val=sls_code, start=0, length=1)
                        sls_total = s_probe.get("totalHit", 0)
                        if sls_total == 0:
                            continue
                        s_fetched, _ = self.fetch_slice_to_end(sls_code, sls_code)
                        kec_collected += s_fetched

            self.log(f"   ✓ [{kec_name}] Selesai seluruh desa: {kec_collected} / {kec_total} data.")
            return kec_name, kec_collected, kec_total

    def run(self):
        t0 = time.time()
        self.log("=" * 70)
        self.log("🚀 FASIH SM PARALLEL SCRAPER (HIGH PERFORMANCE)")
        self.log(f"📅 Survey Period ID : {self.survey_period_id}")
        self.log(f"⚡ Pekerja Paralel  : {self.max_workers} Workers (Simultan)")
        self.log(f"📦 Batch Size       : {self.page_size} baris/request")
        self.log(f"🎯 Mode Ekstraksi   : {'Ringkas (Nomor Bangunan + SLS)' if self.is_minimal else 'Lengkap (Semua Kolom)'}")
        self.log("=" * 70)

        # Cek total global
        init_res = self.fetch_api(search_val="", start=0, length=1)
        grand_total = init_res.get("recordsTotal") or init_res.get("totalHit") or 35585
        self.log(f"\n📊 Total Database: ~{grand_total:,} data penugasan.")
        self.log(f"⚙️ Menjalankan {self.max_workers} thread paralel untuk 10 Kecamatan...\n")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_kec = {
                executor.submit(self.process_kecamatan, code, name): (code, name)
                for code, name in KECAMATAN_SITARO
            }

            for future in as_completed(future_to_kec):
                code, name = future_to_kec[future]
                try:
                    k_name, fetched, target = future.result()
                    with self.records_lock:
                        curr_total = len(self.all_records)
                    self.log(f"📈 [Progres Gabungan] Terkumpul {curr_total:,} data unik...")
                except Exception as e:
                    self.log(f"❌ Galat pada Kecamatan {name}: {e}")

        durasi = time.time() - t0
        self.log("\n" + "=" * 70)
        self.log(f"🎉 SELESAI PARALEL dalam {durasi:.1f} detik ({durasi/60:.1f} menit)!")
        self.log(f"📊 Total Data Terkumpul: {len(self.all_records):,} / ~{grand_total:,} baris unik.")
        self.log("=" * 70)

        return list(self.all_records.values())

def main():
    parser = argparse.ArgumentParser(description="Fasih SM BPS High-Performance Parallel Scraper")
    parser.add_argument("--cookie", help="Cookie header string dari browser", default="")
    parser.add_argument("--xsrf", help="XSRF-TOKEN header", default=DEFAULT_XSRF_TOKEN)
    parser.add_argument("--period", help="Survey Period ID", default=DEFAULT_SURVEY_PERIOD_ID)
    parser.add_argument("--workers", type=int, help="Jumlah request paralel bersamaan (default: 4)", default=4)
    parser.add_argument("--page-size", type=int, help="Ukuran batch per request (default: 100)", default=100)
    parser.add_argument("--minimal", action="store_true", help="Hanya simpan kolom inti (Nomor Bangunan, Nama Keluarga/Usaha, SLS) agar proses jauh lebih cepat")
    parser.add_argument("--output", help="Nama file output tanpa ekstensi", default="")

    args = parser.parse_args()

    cookie = args.cookie or (
        f"XSRF-TOKEN={args.xsrf}; "
        "JSESSIONID=00ED19F826396DC2FDF9E14A044174C9; "
        "SESSION=82285aa4-2720-46ac-87de-767b7340d9e6"
    )

    scraper = ParallelFasihScraper(
        cookie_header=cookie,
        xsrf_token=args.xsrf,
        survey_period_id=args.period,
        max_workers=args.workers,
        page_size=args.page_size,
        is_minimal=args.minimal
    )

    try:
        rows = scraper.run()
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan fatal: {e}")
        return

    if not rows:
        print("❌ Tidak ada data yang berhasil diekstrak.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_tag = "Minimal" if args.minimal else "Full"
    out_base = args.output or f"Raw_Assignment_SE2026_{mode_tag}_{timestamp}"

    df = pd.DataFrame(rows)

    if not args.minimal:
        df.rename(columns=FASIH_COLUMN_LABELS, inplace=True)

    # Format teks untuk menjaga leading zero
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["code", "kode", "wilker", "id", "data", "phone", "telp", "nomor"]):
            df[col] = df[col].astype(str)

    xlsx_path = f"{out_base}.xlsx"
    print(f"\n💾 Menyimpan ke Excel: {xlsx_path} ...", end="", flush=True)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(" [SELESAI]")

    csv_path = f"{out_base}.csv"
    print(f"💾 Menyimpan ke CSV: {csv_path} ...", end="", flush=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(" [SELESAI]")

    print(f"\n✅ BERHASIL SELESAI:")
    print(f"   📊 Total Baris : {len(df):,} baris")
    print(f"   📁 File Excel   : {xlsx_path}")
    print(f"   📁 File CSV     : {csv_path}")

    # Jika user menjalankan mode minimal, langsung tawarkan rekapitulasi SLS otomatis
    print("\n💡 Tips: Untuk langsung melihat rekapitulasi bangunan fisik per SLS, jalankan:")
    print(f"   python rekap_bangunan_sls.py {csv_path}")

if __name__ == "__main__":
    main()
