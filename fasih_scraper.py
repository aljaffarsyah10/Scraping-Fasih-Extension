"""
Fasih Assignment Scraper - Python CLI
Script mandiri untuk menarik data penugasan dari Fasih SM BPS dan mengekspornya langsung ke Excel (.xlsx) dan CSV.
"""

import argparse
import json
import ssl
import sys
import time
import urllib.request
from datetime import datetime
import pandas as pd

DEFAULT_ENDPOINT = "https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode"
DEFAULT_SURVEY_PERIOD_ID = "fd68e454-ba45-4b85-8205-f3bf777ded24"
DEFAULT_XSRF_TOKEN = "55edd9d0-2888-4d52-8572-a96445cd513d"

# Kamus label kolom resmi Fasih SM SE2026 (dari template custom-data)
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
                # Untuk array of dict (misal assignmentResponsibility), simpan ringkasan JSON
                res[prop_name] = json.dumps(val)
        else:
            res[prop_name] = str(val) if isinstance(val, (int, float)) and key.startswith("data") else val
    return res

def fetch_page(cookie_header, xsrf_token, survey_period_id, start_offset, page_size=50):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://fasih-sm.bps.go.id",
        "Referer": f"https://fasih-sm.bps.go.id/app/surveys/a0429e96-51a5-477b-a415-485f9c153004/{survey_period_id}/data",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-XSRF-TOKEN": xsrf_token,
        "Cookie": cookie_header
    }

    payload = {
        "start": start_offset,
        "length": page_size,
        "columns": [
            {"data": "id", "orderable": True},
            {"data": "codeIdentity", "orderable": True},
            {"data": "data1", "orderable": True},
            {"data": "data2", "orderable": True},
            {"data": "data3", "orderable": True},
            {"data": "data4", "orderable": True},
            {"data": "data5", "orderable": True},
            {"data": "data6", "orderable": True},
            {"data": "data7", "orderable": True},
            {"data": "data8", "orderable": True},
            {"data": "data9", "orderable": True},
            {"data": "data10", "orderable": True}
        ],
        "order": [],
        "search": {"value": "", "regex": False},
        "assignmentExtraParam": {
            "surveyPeriodId": survey_period_id,
            "assignmentErrorStatusType": -1,
            "filterTargetType": "TARGET_ONLY"
        }
    }

    req = urllib.request.Request(
        DEFAULT_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(req, context=ctx) as response:
        return json.loads(response.read().decode("utf-8"))

def scrape_all(cookie_header, xsrf_token, survey_period_id, max_pages=None, page_size=50, delay=0.3):
    print("=" * 60)
    print("🚀 FASIH SM ASSIGNMENT SCRAPER (PYTHON)")
    print(f"📅 Survey Period ID: {survey_period_id}")
    print(f"📦 Batch Size: {page_size} baris per request")
    print("=" * 60)

    all_rows = []
    start_offset = 0
    page = 1
    total_hits = None

    while True:
        if max_pages and page > max_pages:
            print(f"🛑 Mencapai batas maksimal {max_pages} halaman.")
            break

        print(f"📄 Mengambil halaman {page} (Offset {start_offset})...", end="", flush=True)
        try:
            res = fetch_page(cookie_header, xsrf_token, survey_period_id, start_offset, page_size)
        except Exception as e:
            print(f"\n❌ Galat saat mengambil offset {start_offset}: {e}")
            break

        items = res.get("searchData") or res.get("data") or []
        if total_hits is None:
            total_hits = res.get("totalHit") or res.get("recordsTotal") or 0
            print(f" [Total Server: {total_hits} data]")
        else:
            print(f" [{len(items)} data]")

        if not items:
            print("ℹ️ Tidak ada data lagi dari server. Selesai.")
            break

        for item in items:
            all_rows.append(flatten_record(item))

        print(f"   ✓ Terkumpul {len(all_rows)} / {total_hits} baris...")

        start_offset += page_size
        page += 1

        if start_offset >= total_hits:
            print("🎉 Semua data penugasan telah berhasil diunduh!")
            break

        time.sleep(delay)

    return all_rows

def main():
    parser = argparse.ArgumentParser(description="Fasih SM BPS Assignment Scraper CLI")
    parser.add_argument("--cookie", help="Cookie header string dari browser", default="")
    parser.add_argument("--xsrf", help="XSRF-TOKEN header", default=DEFAULT_XSRF_TOKEN)
    parser.add_argument("--period", help="Survey Period ID", default=DEFAULT_SURVEY_PERIOD_ID)
    parser.add_argument("--max-pages", type=int, help="Maksimal halaman yang diambil (default: semua)", default=None)
    parser.add_argument("--page-size", type=int, help="Ukuran batch per request (default: 50)", default=50)
    parser.add_argument("--output", help="Nama file output tanpa ekstensi", default="")

    args = parser.parse_args()

    # Cookie default dari sesi aktif user jika tidak disediakan argumen
    cookie = args.cookie or (
        f"XSRF-TOKEN={args.xsrf}; "
        "JSESSIONID=00ED19F826396DC2FDF9E14A044174C9; "
        "SESSION=82285aa4-2720-46ac-87de-767b7340d9e6"
    )

    rows = scrape_all(
        cookie_header=cookie,
        xsrf_token=args.xsrf,
        survey_period_id=args.period,
        max_pages=args.max_pages,
        page_size=args.page_size
    )

    if not rows:
        print("❌ Tidak ada data yang berhasil diekstrak.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_base = args.output or f"Raw_Assignment_SE2026_{timestamp}"

    df = pd.DataFrame(rows)

    # Beri label yang jelas untuk kolom data1 s.d data10 sesuai template Fasih SM
    df.rename(columns=FASIH_COLUMN_LABELS, inplace=True)

    # Pastikan kolom dengan kode (seperti wilayah, id) bertipe string agar leading zero tidak hilang
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["code", "kode", "wilker", "id", "data", "phone", "telp"]):
            df[col] = df[col].astype(str)

    # 1. Simpan ke Excel (.xlsx)
    xlsx_path = f"{out_base}.xlsx"
    print(f"💾 Menyimpan data ke Excel: {xlsx_path} ...", end="", flush=True)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(" [SELESAI]")

    # 2. Simpan ke CSV UTF-8 dengan BOM
    csv_path = f"{out_base}.csv"
    print(f"💾 Menyimpan data ke CSV: {csv_path} ...", end="", flush=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(" [SELESAI]")

    print(f"\n✅ BERHASIL: {len(df)} baris data berhasil diekspor ke:")
    print(f"   📁 {xlsx_path}")
    print(f"   📁 {csv_path}")

if __name__ == "__main__":
    main()
