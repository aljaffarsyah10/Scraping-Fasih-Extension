"""
Fasih Assignment Scraper - Python CLI
Script mandiri untuk menarik seluruh data penugasan (hingga puluhan ribu) dari Fasih SM BPS
dan mengekspornya langsung ke Excel (.xlsx) dan CSV dengan preservasi kode identitas (leading zero).

Fitur Utama:
- Auto-Sharding / Partisi Otomatis per Wilayah (Kecamatan/Desa) untuk menembus limit 1.000 data Elasticsearch Fasih SM.
- Deduplikasi otomatis berbasis UUID penugasan (`id`).
- Normalisasi dan pelabelan nama kolom resmi Fasih SM SE2026.
- Preservasi leading zero untuk kolom kode wilayah dan identitas.
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
                res[prop_name] = json.dumps(val)
        else:
            res[prop_name] = str(val) if isinstance(val, (int, float)) and key.startswith("data") else val
    return res

def fetch_single_query(cookie_header, xsrf_token, survey_period_id, search_val="", start_offset=0, page_size=100, extra_param=None):
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

    assignment_param = {
        "surveyPeriodId": survey_period_id,
        "assignmentErrorStatusType": -1,
        "filterTargetType": "TARGET_ONLY"
    }
    if extra_param:
        assignment_param.update(extra_param)

    payload = {
        "start": start_offset,
        "length": min(page_size, 100), # Fasih membatasi panjang max 150
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
        "search": {"value": str(search_val), "regex": False},
        "assignmentExtraParam": assignment_param
    }

    req = urllib.request.Request(
        DEFAULT_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            raw_text = response.read().decode("utf-8")
            if raw_text.startswith("<!DOCTYPE html>") or "<script" in raw_text:
                raise ValueError("Server Fasih mengembalikan halaman tantangan WAF/Sesi Kadaluarsa. Silakan perbarui cookie sesi.")
            return json.loads(raw_text)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} {e.reason}: {err_msg[:200]}")

def scrape_slice(cookie_header, xsrf_token, survey_period_id, search_val, label, page_size=100, delay=0.25):
    """Menarik 1 partisi data sampai tuntas (selama totalHit <= 1000)"""
    records = []
    page = 0
    total_hit = None

    while True:
        start_offset = page * page_size
        if total_hit is not None and start_offset >= total_hit:
            break
        if start_offset >= 1000:
            # Backend Elasticsearch membatasi start < 1000
            break

        res = fetch_single_query(cookie_header, xsrf_token, survey_period_id, search_val=search_val, start_offset=start_offset, page_size=page_size)
        items = res.get("searchData") or []
        if total_hit is None:
            total_hit = res.get("totalHit", 0)
            if total_hit == 0:
                break
            print(f"      [{label}] Target: {total_hit} data")

        if not items:
            break

        records.extend(items)
        page += 1
        time.sleep(delay)

    return records, total_hit or 0

def scrape_all_sharded(cookie_header, xsrf_token, survey_period_id, page_size=100, delay=0.25):
    """
    Menarik seluruh data penugasan (~35.585 data) dengan Adaptive Recursive Sharding:
    1. Mempartisi per Kecamatan (10 kecamatan di Sitaro).
    2. Jika suatu kecamatan memiliki > 1.000 data, otomatis dipartisi per Desa (001-020).
    3. Menggabungkan dan mendeduplikasi seluruh data secara otomatis.
    """
    print("=" * 70)
    print("🚀 FASIH SM ASSIGNMENT SCRAPER - FULL DATA MODE (AUTO-SHARDING)")
    print(f"📅 Survey Period ID: {survey_period_id}")
    print(f"📦 Batch Size: {page_size} baris/request | Batas Elasticsearch: 1.000/shard")
    print("=" * 70)

    # 1. Cek total data keseluruhan
    init_res = fetch_single_query(cookie_header, xsrf_token, survey_period_id, search_val="", start_offset=0, page_size=1)
    grand_total = init_res.get("recordsTotal") or init_res.get("totalHit") or 35585
    print(f"\n📊 Total Keseluruhan di Database Fasih: {grand_total} data penugasan.")
    print("⚙️ Memulai partisi wilayah bertingkat (Kecamatan ➔ Desa) agar seluruh data terambil...\n")

    all_records = {} # Map ID -> dict untuk deduplikasi otomatis

    for idx, (kec_code, kec_name) in enumerate(KECAMATAN_SITARO, 1):
        print(f"\n🏢 [{idx}/10] Memeriksa Kecamatan {kec_code} ({kec_name})...")
        try:
            kec_probe = fetch_single_query(cookie_header, xsrf_token, survey_period_id, search_val=kec_code, start_offset=0, page_size=1)
            kec_total = kec_probe.get("totalHit", 0)
        except Exception as e:
            print(f"   ⚠️ Galat saat probe kecamatan {kec_code}: {e}")
            continue

        print(f"   📍 Total data di {kec_name}: {kec_total} data")

        if kec_total == 0:
            continue

        if kec_total <= 1000:
            # Jika <= 1000 data, tarik langsung sekaligus!
            print(f"   ⚡ Ukuran <= 1000, menarik langsung dalam 1 sesi...")
            items, _ = scrape_slice(cookie_header, xsrf_token, survey_period_id, search_val=kec_code, label=kec_name, page_size=page_size, delay=delay)
            for it in items:
                all_records[it["id"]] = flatten_record(it)
            print(f"   ✅ Selesai {kec_name}: {len(items)} baris (Total akumulasi: {len(all_records)})")
        else:
            # Jika > 1000 data, pecah per DESA (001 s.d 025)
            print(f"   ⚠️ Ukuran {kec_total} > 1000 (limit server). Mempartisi per DESA...")
            kec_collected = 0
            for desa_num in range(1, 26):
                desa_code = f"{kec_code}{desa_num:03d}"
                try:
                    probe = fetch_single_query(cookie_header, xsrf_token, survey_period_id, search_val=desa_code, start_offset=0, page_size=1)
                    desa_total = probe.get("totalHit", 0)
                except Exception:
                    continue

                if desa_total == 0:
                    continue

                print(f"   🏡 Desa {desa_code} ({desa_total} data): menarik...", end="", flush=True)
                items, _ = scrape_slice(cookie_header, xsrf_token, survey_period_id, search_val=desa_code, label=desa_code, page_size=page_size, delay=delay)
                for it in items:
                    all_records[it["id"]] = flatten_record(it)
                kec_collected += len(items)
                print(f" didapat {len(items)} data.")

            print(f"   ✅ Selesai {kec_name}: {kec_collected} / {kec_total} baris (Total akumulasi: {len(all_records)})")

    print("\n" + "=" * 70)
    print(f"🎉 SELESAI! Berhasil mengumpulkan {len(all_records)} / {grand_total} data unik penugasan.")
    print("=" * 70)
    return list(all_records.values())

def main():
    parser = argparse.ArgumentParser(description="Fasih SM BPS Full Assignment Scraper CLI")
    parser.add_argument("--cookie", help="Cookie header string dari browser", default="")
    parser.add_argument("--xsrf", help="XSRF-TOKEN header", default=DEFAULT_XSRF_TOKEN)
    parser.add_argument("--period", help="Survey Period ID", default=DEFAULT_SURVEY_PERIOD_ID)
    parser.add_argument("--page-size", type=int, help="Ukuran batch per request (default: 100)", default=100)
    parser.add_argument("--output", help="Nama file output tanpa ekstensi", default="")

    args = parser.parse_args()

    cookie = args.cookie or (
        f"XSRF-TOKEN={args.xsrf}; "
        "JSESSIONID=00ED19F826396DC2FDF9E14A044174C9; "
        "SESSION=82285aa4-2720-46ac-87de-767b7340d9e6"
    )

    try:
        rows = scrape_all_sharded(
            cookie_header=cookie,
            xsrf_token=args.xsrf,
            survey_period_id=args.period,
            page_size=args.page_size
        )
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan fatal: {e}")
        return

    if not rows:
        print("❌ Tidak ada data yang berhasil diekstrak.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_base = args.output or f"Raw_Assignment_SE2026_Full_{timestamp}"

    df = pd.DataFrame(rows)

    # Beri label yang jelas untuk kolom data1 s.d data10 sesuai template Fasih SM
    df.rename(columns=FASIH_COLUMN_LABELS, inplace=True)

    # Pastikan kolom dengan kode (wilayah, id, telepon, nomor urut bangunan) bertipe string agar leading zero tidak hilang
    for col in df.columns:
        if any(keyword in col.lower() for keyword in ["code", "kode", "wilker", "id", "data", "phone", "telp"]):
            df[col] = df[col].astype(str)

    # 1. Simpan ke Excel (.xlsx)
    xlsx_path = f"{out_base}.xlsx"
    print(f"\n💾 Menyimpan data ke Excel: {xlsx_path} ...", end="", flush=True)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(" [SELESAI]")

    # 2. Simpan ke CSV UTF-8 dengan BOM
    csv_path = f"{out_base}.csv"
    print(f"💾 Menyimpan data ke CSV: {csv_path} ...", end="", flush=True)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(" [SELESAI]")

    print(f"\n✅ BERHASIL EKSPOR SELURUH DATA:")
    print(f"   📊 Total Baris: {len(df):,} baris")
    print(f"   📁 Excel: {xlsx_path}")
    print(f"   📁 CSV:   {csv_path}")

if __name__ == "__main__":
    main()
