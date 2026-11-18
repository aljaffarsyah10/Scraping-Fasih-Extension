"""
Rekapitulasi Bangunan Fisik per SLS - Fasih SM SE2026
Script otomatis untuk menganalisis data hasil scraping Fasih SM:
1. Mengekstrak nomor urut bangunan fisik murni dari kolom data3.
2. Menghitung jumlah bangunan fisik riil per SLS menggunakan metode COUNT DISTINCT (Unik).
   - Mengatasi kasus 2+ assignment di 1 nomor bangunan yang sama (multi-keluarga/usaha).
   - Mengatasi kasus nomor bangunan yang loncat/terlewat (bukan sekadar mengambil nilai Max).
3. Mengekspor rekapitulasi ke Excel (.xlsx) dengan Sheet Ringkasan per SLS dan Rekap per Desa/Kecamatan.
"""

import os
import sys
import glob
import pandas as pd

def sort_key_bangunan(val):
    s = str(val).strip()
    if s.isdigit():
        return (0, int(s), "")
    import re
    m = re.match(r"^(\d+)(.*)$", s)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, s)

def extract_clean_no_bangunan(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if not s or s == "-":
        return ""
    # Format data3 biasanya: "13 / " atau "15 / 13084791" atau "015"
    parts = s.split("/")
    no_bgn = parts[0].strip()
    return no_bgn

def proses_rekap(input_file, output_file=None):
    print("=" * 70)
    print("🏢 REKAPITULASI JUMLAH BANGUNAN FISIK PER SLS (SE2026)")
    print(f"📂 File Sumber: {input_file}")
    print("=" * 70)

    if input_file.endswith(".csv"):
        df = pd.read_csv(input_file, dtype=str)
    else:
        df = pd.read_excel(input_file, dtype=str)

    print(f"✓ Berhasil membaca {len(df):,} baris data.")

    # Cari nama kolom yang sesuai
    col_data3 = next((c for c in df.columns if "data3" in c), None)
    col_data1 = next((c for c in df.columns if "data1" in c), None)
    col_sls_code = next((c for c in df.columns if "level5_fullCode" in c or "sls_code" in c.lower()), None)
    col_sls_name = next((c for c in df.columns if "level5_name" in c or "sls_name" in c.lower()), None)
    col_desa_name = next((c for c in df.columns if "level4_name" in c or "desa" in c.lower()), None)
    col_kec_name = next((c for c in df.columns if "level3_name" in c or "kecamatan" in c.lower()), None)

    if not col_data3:
        print("❌ Kolom nomor bangunan (data3) tidak ditemukan dalam data.")
        return

    # Bersihkan nomor bangunan
    df["no_bangunan_bersih"] = df[col_data3].apply(extract_clean_no_bangunan)

    # Identifikasi SLS jika belum ada kolom wilayah khusus
    if not col_sls_code and "codeIdentity" in df.columns:
        # Ekstrak 14 digit pertama dari codeIdentity
        df["kode_sls"] = df["codeIdentity"].astype(str).str.extract(r"^(\d{14})")[0].fillna("NON_SLS")
        col_sls_code = "kode_sls"

    # Filter data yang memiliki SLS dan nomor bangunan
    df_valid = df[df["no_bangunan_bersih"] != ""].copy()
    print(f"✓ Ditemukan {len(df_valid):,} baris dengan nomor bangunan terisi.")

    group_cols = [c for c in [col_kec_name, col_desa_name, col_sls_code, col_sls_name] if c and c in df.columns]
    if not group_cols:
        group_cols = [col_sls_code] if col_sls_code else ["codeIdentity"]

    # Agregasi per SLS
    rekap_sls = df_valid.groupby(group_cols, dropna=False).agg(
        total_assignment=("id", "count") if "id" in df.columns else ("no_bangunan_bersih", "count"),
        total_bangunan_fisik=("no_bangunan_bersih", "nunique"),
        daftar_sampel_bangunan=("no_bangunan_bersih", lambda s: ", ".join(
            sorted(set(str(x) for x in s if str(x).strip()), key=sort_key_bangunan)[:15]
        ))
    ).reset_index()

    # Hitung rasio keluarga/usaha per bangunan
    rekap_sls["rasio_keluarga_per_bangunan"] = (
        rekap_sls["total_assignment"] / rekap_sls["total_bangunan_fisik"]
    ).round(2)

    total_bangunan_semua = rekap_sls["total_bangunan_fisik"].sum()
    total_assignment_semua = rekap_sls["total_assignment"].sum()

    print("\n" + "=" * 70)
    print("📊 RINGKASAN HASIL PERHITUNGAN:")
    print(f"   🏛️ Total SLS Terdata        : {len(rekap_sls):,} SLS")
    print(f"   🏠 Total Bangunan Fisik Riil : {total_bangunan_semua:,} Bangunan (Metode Unik / Distinct)")
    print(f"   👨‍👩‍👧‍👦 Total Assignment / Keluarga: {total_assignment_semua:,} Data")
    if total_bangunan_semua > 0:
        print(f"   📈 Rata-rata Keluarga/Bangunan: {(total_assignment_semua/total_bangunan_semua):.2f} per bangunan")
    print("=" * 70)

    # Simpan hasil ke Excel
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_REKAP_BANGUNAN_SLS.xlsx"

    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        # Sheet 1: Rekapitulasi SLS
        rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)

        # Sheet 2: Data Ringkas Kolom Inti Saja (untuk kemudahan cek silang)
        clean_cols = [c for c in [
            col_kec_name, col_desa_name, col_sls_code, col_sls_name,
            "codeIdentity", col_data1, col_data3, "no_bangunan_bersih", "assignmentStatusAlias"
        ] if c and c in df.columns]
        df[clean_cols].to_excel(writer, sheet_name="Data_Ringkas", index=False)

    print(f"\n💾 Hasil rekapitulasi berhasil disimpan ke Excel:")
    print(f"   📁 {output_file}")
    return output_file

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Cari file CSV atau XLSX hasil scrape terbaru di folder kerja
        csvs = glob.glob("Raw_Assignment_*.csv")
        target_file = max(csvs, key=os.path.getmtime) if csvs else None

    if not target_file:
        print("❌ Tidak ditemukan file hasil scraping (Raw_Assignment_*.csv).")
        sys.exit(1)

    proses_rekap(target_file)
