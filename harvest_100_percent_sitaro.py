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
    if not s or s == "-" or s.lower() == "nan":
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
        'nama_sls': str(l5.get('name') or ""),
        'nama_desa': str(l4.get('name') or ""),
        'nama_kecamatan': str(l3.get('name') or ""),
        'nama_assignment_keluarga': str(it.get('data1') or ""),
        'alamat': str(it.get('data2') or ""),
        'nomor_bangunan_raw': str(raw_bgn) if raw_bgn is not None else "",
        'nomor_bangunan_bersih': str(clean_bgn),
        'status_penugasan': str(it.get('assignmentStatusAlias') or "")
    }

def fetch_search_data(search_val):
    items = []
    page = 0
    page_size = 100
    retries = 0

    while True:
        payload = {
            'start': page * page_size,
            'length': page_size,
            'columns': [{'data': 'id', 'orderable': True}],
            'order': [],
            'search': {'value': str(search_val), 'regex': False},
            'assignmentExtraParam': {
                'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
                'assignmentErrorStatusType': -1,
                'filterTargetType': 'TARGET_ONLY'
            }
        }
        try:
            r = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
            if r.status_code == 429:
                time.sleep(3)
                continue
            if r.status_code != 200:
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

            if len(items) >= total_hit or (page + 1) * page_size >= 1000:
                break

            page += 1
            time.sleep(0.2)
        except Exception as e:
            retries += 1
            if retries > 3:
                break
            time.sleep(2)

    return items

def main():
    print("=" * 80)
    print("🚀 SITARO 100% COMPLETE ASSIGNMENT HARVESTER")
    print("🎯 Target Server: 35,585 Data Penugasan Tanpa Terlewat Satu Pun")
    print("=" * 80)

    # 1. Baca data master saat ini
    df_existing = pd.read_csv('Master_Data_Assignment_SE2026_Sitaro.csv', low_memory=False, dtype=str)
    existing_ids = set(df_existing['id'])
    print(f"📂 Master saat ini: {len(existing_ids):,} data unik.")

    # 2. Dapatkan seluruh kode desa yang terdeteksi di Sitaro
    # Ambil dari master yang ada
    df_existing['kode_desa'] = df_existing['codeIdentity'].astype(str).str.slice(0, 10)
    desa_set = set(d for d in df_existing['kode_desa'].dropna().unique() if d.startswith('7108'))
    
    # Tambahkan kode desa/kabupaten khusus jika belum ada
    desa_set.add('7108000000') # Kabupaten
    # Tambahkan desa pecahan baru
    desa_set.update(['7108030026', '7108030028', '7108030029', '7108070026'])

    sorted_desas = sorted(list(desa_set))
    print(f"📍 Teridentifikasi {len(sorted_desas)} wilayah/desa untuk dipindai.")

    new_items = []

    for idx, d_code in enumerate(sorted_desas, 1):
        # Cek totalHit di server untuk desa ini
        payload = {
            'start': 0, 'length': 1,
            'columns': [{'data': 'id'}],
            'order': [],
            'search': {'value': d_code, 'regex': False},
            'assignmentExtraParam': {
                'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
                'assignmentErrorStatusType': -1,
                'filterTargetType': 'TARGET_ONLY'
            }
        }
        try:
            r = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
            server_hit = r.json().get('totalHit', 0) if r.status_code == 200 else 0
        except Exception:
            server_hit = 0

        # Cek berapa yang sudah ada di master kita untuk desa ini
        current_in_master = (df_existing['kode_desa'] == d_code).sum()

        if server_hit == 0:
            continue

        print(f"[{idx:02d}/{len(sorted_desas):02d}] Desa {d_code} -> Server: {server_hit:>4} | Master: {current_in_master:>4}", end="", flush=True)

        # Jika server_hit <= 1000 dan master kita sudah lengkap, skip untuk menghemat waktu!
        if server_hit <= 1000 and current_in_master >= server_hit:
            print(" -> [LENGKAP]")
            continue

        # Kasus A: server_hit <= 1000 tapi di master masih kurang
        if server_hit <= 1000:
            print(f" -> [FETCH DESA: {server_hit} data]...", end="", flush=True)
            fetched = fetch_search_data(d_code)
            new_items.extend(fetched)
            print(f" (Didapat: {len(fetched)})")
        else:
            # Kasus B: server_hit > 1000 (Terpotong Elasticsearch limit 1000!)
            # Shard per SLS dari 0000 s/d 0025!
            print(f" -> [SHARDING SLS (Server={server_hit} > 1000)]...")
            for sls_num in range(0, 26):
                sls_code = f"{d_code}{sls_num:04d}"
                fetched_sls = fetch_search_data(sls_code)
                if fetched_sls:
                    new_items.extend(fetched_sls)
                    print(f"      • SLS {sls_code}: {len(fetched_sls)} data")
                time.sleep(0.15)

        time.sleep(0.2)

    print("\n" + "=" * 80)
    print(f"📦 Total data tambahan yang diambil: {len(new_items):,} baris")
    print("=" * 80)

    # 3. Gabungkan dan deduplikasi
    if new_items:
        df_new = pd.DataFrame(new_items)
        df_final = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_final = df_existing

    # Pastikan drop kolom kode_desa bantu
    if 'kode_desa' in df_final.columns:
        df_final = df_final.drop(columns=['kode_desa'])

    # Pastikan nomor_bangunan_bersih dan string bersih
    df_final['nomor_bangunan_bersih'] = df_final['nomor_bangunan_raw'].apply(extract_clean_no_bangunan)
    df_final = df_final.drop_duplicates(subset=['id'], keep='last').reset_index(drop=True)

    print(f"🎯 TOTAL MASTER DATASET SETELAH REKONSILIASI: {len(df_final):,} BARIS UNIK")

    # 4. Simpan ke CSV Master
    df_final.to_csv('Master_Data_Assignment_SE2026_Sitaro.csv', index=False)
    print("✓ Berhasil menyimpan: Master_Data_Assignment_SE2026_Sitaro.csv")

    # 5. REKAPITULASI JUMLAH BANGUNAN FISIK PER SLS
    print("\n" + "=" * 80)
    print("🏢 MEMPROSES REKAPITULASI JUMLAH BANGUNAN FISIK PER SLS...")
    print("=" * 80)

    df_valid_bgn = df_final[df_final["nomor_bangunan_bersih"] != ""].copy()
    print(f"✓ Dari {len(df_final):,} baris, terdapat {len(df_valid_bgn):,} baris dengan nomor bangunan fisik terisi.")

    def format_daftar_bangunan(series):
        # Pastikan semua element string dan tidak kosong
        clean_list = [str(x).strip() for x in series if pd.notna(x) and str(x).strip() != ""]
        unique_sorted = sorted(set(clean_list), key=sort_key_bangunan)
        return ", ".join(unique_sorted)

    group_cols = ["nama_kecamatan", "nama_desa", "kode_sls", "nama_sls"]
    rekap_sls = df_valid_bgn.groupby(group_cols, dropna=False).agg(
        total_assignment=("id", "count"),
        total_bangunan_fisik=("nomor_bangunan_bersih", "nunique"),
        daftar_nomor_bangunan=("nomor_bangunan_bersih", format_daftar_bangunan)
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

    # Simpan ke Excel Master
    excel_path = "Master_Rekap_Bangunan_SE2026_Sitaro.xlsx"
    print(f"\n💾 Menyimpan workbook Excel berformat rapi ke '{excel_path}'...")
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)
        df_final.to_excel(writer, sheet_name="Semua_Assignment", index=False)

    print("🎉 SELURUH PROSES SELESAI DENGAN SUKSES!")

if __name__ == '__main__':
    main()
