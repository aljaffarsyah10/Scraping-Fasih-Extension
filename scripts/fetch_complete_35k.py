import json
import time
import requests
import urllib3
import pandas as pd
import re

urllib3.disable_warnings()

# 1. Baca cookie & headers
with open('fresh_cookie.txt') as f:
    cookie = f.read().strip()

url = 'https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode'
headers = {
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/json',
    'Origin': 'https://fasih-sm.bps.go.id',
    'Referer': 'https://fasih-sm.bps.go.id/app/surveys/a0429e96-51a5-477b-a415-485f9c153004/fd68e454-ba45-4b85-8205-f3bf777ded24/data',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Mobile Safari/537.36',
    'X-XSRF-TOKEN': '55edd9d0-2888-4d52-8572-a96445cd513d',
    'Cookie': cookie
}

def extract_clean_no_bangunan(val):
    if not val or pd.isna(val):
        return ""
    s = str(val).strip()
    if not s or s == "-":
        return ""
    parts = s.split("/")
    return parts[0].strip()

def sort_key_bangunan(val):
    s = str(val).strip()
    if s.isdigit():
        return (0, int(s), "")
    m = re.match(r"^(\d+)(.*)$", s)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, s)

def parse_item(it):
    reg = it.get('region', {})
    l1 = reg.get('level1', {})
    l2 = l1.get('level2', {}) if isinstance(l1, dict) else {}
    l3 = l2.get('level3', {}) if isinstance(l2, dict) else {}
    l4 = l3.get('level4', {}) if isinstance(l3, dict) else {}
    l5 = l4.get('level5', {}) if isinstance(l4, dict) else {}

    code_id = str(it.get('codeIdentity', ''))
    kode_sls = l5.get('fullCode') or (code_id[:14] if len(code_id) >= 14 else code_id)

    raw_bgn = it.get('data3') or ""
    clean_bgn = extract_clean_no_bangunan(raw_bgn)

    return {
        'id': str(it.get('id', '')),
        'codeIdentity': code_id,
        'kode_sls': str(kode_sls),
        'nama_sls': l5.get('name') or "",
        'nama_desa': l4.get('name') or "",
        'nama_kecamatan': l3.get('name') or "",
        'nama_assignment_keluarga': it.get('data1') or "",
        'alamat': it.get('data2') or "",
        'nomor_bangunan_raw': str(raw_bgn),
        'nomor_bangunan_bersih': str(clean_bgn),
        'status_penugasan': it.get('assignmentStatusAlias') or ""
    }

def fetch_partition(search_val="", status_alias=None, label=""):
    print(f"\n[PARTISI] {label} (Search: '{search_val}', Status: '{status_alias or 'SEMUA'}')")
    items = []
    page = 0
    page_size = 100
    retries = 0

    while True:
        extra_param = {
            'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
            'assignmentErrorStatusType': -1,
            'filterTargetType': 'TARGET_ONLY'
        }
        if status_alias:
            extra_param['assignmentStatusAlias'] = status_alias

        payload = {
            'start': page * page_size,
            'length': page_size,
            'columns': [{'data': 'id', 'orderable': True}],
            'order': [],
            'search': {'value': str(search_val), 'regex': False},
            'assignmentExtraParam': extra_param
        }

        try:
            r = requests.post(url, json=payload, headers=headers, verify=False, timeout=20)
            if r.status_code == 429:
                print(f"  ⚠️ Rate limit (429), tidur 3 detik...")
                time.sleep(3)
                continue
            if r.status_code != 200:
                print(f"  ❌ Error HTTP {r.status_code} pada page {page}. Retrying...")
                retries += 1
                if retries > 3:
                    break
                time.sleep(2)
                continue

            retries = 0
            data = r.json()
            total_hit = data.get('totalHit', 0)
            batch = data.get('searchData', [])

            if not batch:
                break

            for it in batch:
                items.append(parse_item(it))

            print(f"  Progress: {len(items):>5} / {total_hit:<5} (Page {page})", end="\r", flush=True)

            if len(items) >= total_hit:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"  ⚠️ Exception pada page {page}: {e}. Retrying...")
            retries += 1
            if retries > 3:
                break
            time.sleep(2)

    print(f"  ✓ Selesai: {len(items):,} data berhasil diambil.")
    return items

def main():
    print("=" * 80)
    print("🚀 FASIH SM EXHAUSTIVE DATA HARVESTER (TARGET: 35,585 PENUGASAN)")
    print("=" * 80)

    # Baca data master yang ada
    print("📂 Membaca master data saat ini...", end="", flush=True)
    try:
        df_existing = pd.read_csv('Master_Data_Assignment_SE2026_Sitaro.csv', low_memory=False, dtype=str)
        existing_ids = set(df_existing['id'])
        print(f" Ditemukan {len(existing_ids):,} baris eksisting.")
    except Exception as e:
        df_existing = pd.DataFrame()
        existing_ids = set()
        print(f" Belum ada atau gagal baca ({e}).")

    all_harvested = []

    # 1. PARTISI STATUS NON-APPROVED (11 Status, Total ~10.873 data)
    non_approved_statuses = [
        'EDITED BY Admin Kabupaten',
        'COMPLETED BY Admin Kabupaten',
        'OPEN',
        'SUBMITTED BY Pencacah',
        'REVOKED BY Admin Kabupaten',
        'SUBMITTED RESPONDENT',
        'REJECTED BY Admin Kabupaten',
        'REJECTED BY Pengawas FROM Admin Kabupaten',
        'REVOKED BY Pengawas',
        'DRAFT',
        'REJECTED BY Pengawas'
    ]

    for st in non_approved_statuses:
        items = fetch_partition(search_val="", status_alias=st, label=f"Status: {st}")
        all_harvested.extend(items)

    # 2. PARTISI STATUS APPROVED PER KECAMATAN (10 Kecamatan, Total 24.712 data)
    kecs = [
        ('7108010', 'Siau Timur Selatan'),
        ('7108020', 'Siau Timur'),
        ('7108030', 'Siau Barat'),
        ('7108040', 'Siau Tengah'),
        ('7108050', 'Siau Barat Selatan'),
        ('7108060', 'Siau Barat Utara'),
        ('7108070', 'Tagulandang'),
        ('7108080', 'Tagulandang Utara'),
        ('7108090', 'Tagulandang Selatan'),
        ('7108100', 'Biaro')
    ]

    for kode, nama in kecs:
        items = fetch_partition(search_val=kode, status_alias='APPROVED BY Pengawas', label=f"APPROVED - {kode} ({nama})")
        all_harvested.extend(items)

    # 3. PARTISI TINGKAT KABUPATEN
    kab_items = fetch_partition(search_val="7108000", status_alias=None, label="Tingkat Kabupaten (7108000)")
    all_harvested.extend(kab_items)

    print("\n" + "=" * 80)
    print(f"📦 Total raw penugasan yang terkumpul dari penarikan: {len(all_harvested):,} baris")
    print("=" * 80)

    # Gabung dengan master data
    df_new = pd.DataFrame(all_harvested)
    if not df_existing.empty:
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_new

    # Deduplikasi ID
    df_final = df_final.drop_duplicates(subset=['id'], keep='last').reset_index(drop=True)

    print(f"🎯 TOTAL MASTER DATA UNIK SETELAH DEDUPLIKASI: {len(df_final):,} BARIS")

    # Simpan ke CSV Master
    df_final.to_csv('Master_Data_Assignment_SE2026_Sitaro.csv', index=False)
    print("✓ Berhasil menyimpan: Master_Data_Assignment_SE2026_Sitaro.csv")

    # 4. REKAPITULASI JUMLAH BANGUNAN FISIK PER SLS
    print("\n" + "=" * 80)
    print("🏢 MEMPROSES REKAPITULASI JUMLAH BANGUNAN FISIK PER SLS...")
    print("=" * 80)

    df_valid_bgn = df_final[df_final["nomor_bangunan_bersih"] != ""].copy()
    print(f"✓ Dari {len(df_final):,} baris, terdapat {len(df_valid_bgn):,} baris dengan nomor bangunan fisik terisi.")

    group_cols = ["nama_kecamatan", "nama_desa", "kode_sls", "nama_sls"]
    rekap_sls = df_valid_bgn.groupby(group_cols, dropna=False).agg(
        total_assignment=("id", "count"),
        total_bangunan_fisik=("nomor_bangunan_bersih", "nunique"),
        daftar_nomor_bangunan=("nomor_bangunan_bersih", lambda s: ", ".join(sorted(set(s), key=sort_key_bangunan)))
    ).reset_index()

    rekap_sls["rasio_keluarga_per_bangunan"] = (
        rekap_sls["total_assignment"] / rekap_sls["total_bangunan_fisik"]
    ).round(2)

    total_sls = len(rekap_sls)
    total_assign_valid = rekap_sls["total_assignment"].sum()
    total_bangunan_sum = rekap_sls["total_bangunan_fisik"].sum()

    print(f"\n📊 HASIL REKAPITULASI FINAL:")
    print(f"   • Total SLS / Satuan Lingkungan      : {total_sls:,} SLS")
    print(f"   • Total Assignment Terdaftar di SLS : {total_assign_valid:,} penugasan")
    print(f"   • TOTAL BANGUNAN FISIK RIIL (COUNT) : {total_bangunan_sum:,} BANGUNAN")

    # Export ke Excel Master Rekap
    excel_path = "Master_Rekap_Bangunan_SE2026_Sitaro.xlsx"
    print(f"\n💾 Menyimpan workbook Excel berformat rapi ke '{excel_path}'...")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)
        df_final.to_excel(writer, sheet_name="Semua_Assignment", index=False)

    print("✓ SELESAI DENGAN SUKSES!")

if __name__ == '__main__':
    main()
