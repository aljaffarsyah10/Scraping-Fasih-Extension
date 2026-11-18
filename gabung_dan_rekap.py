"""
Skrip Penggabungan Master & Rekapitulasi Bangunan Fisik per SLS (SE2026)
Menggabungkan seluruh dataset hasil scraping, menduplikasi ID penugasan,
dan menghitung total bangunan fisik riil per SLS se-Kabupaten Sitaro.
"""

import pandas as pd
import re

def sort_key_bangunan(val):
    s = str(val).strip()
    if s.isdigit():
        return (0, int(s), "")
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
    parts = s.split("/")
    return parts[0].strip()

print("=" * 75)
print("🏢 PENGGABUNGAN MASTER DATASET & REKAP BANGUNAN FISIK PER SLS")
print("=" * 75)

# 1. Baca File 1 (Full 83 Kolom - 32.282 baris)
print("📂 Membaca Dataset 1 (32,282 baris)...", end="", flush=True)
df1 = pd.read_csv("Raw_Assignment_SE2026_Full_20261118_130132.csv", low_memory=False, dtype=str)
print(f" [SELESAI] ({len(df1):,} baris)")

# Siapkan kolom seragam dari df1
df1_clean = pd.DataFrame()
df1_clean["id"] = df1["id"]
df1_clean["codeIdentity"] = df1["codeIdentity"]
df1_clean["kode_sls"] = df1["region_level1_level2_level3_level4_level5_fullCode"].fillna(
    df1["codeIdentity"].astype(str).str.slice(0, 14)
)
df1_clean["nama_sls"] = df1.get("region_level1_level2_level3_level4_level5_name", "")
df1_clean["nama_desa"] = df1.get("region_level1_level2_level3_level4_name", "")
df1_clean["nama_kecamatan"] = df1.get("region_level1_level2_level3_name", "")
df1_clean["nama_assignment_keluarga"] = df1.get("data1_Nama_Keluarga_Bangunan_Usaha", df1.get("data1", ""))
df1_clean["alamat"] = df1.get("data2_Alamat_Prelist", df1.get("data2", ""))
df1_clean["nomor_bangunan_raw"] = df1.get("data3_No_Urut_Bangunan_IDSBR", df1.get("data3", ""))
df1_clean["nomor_bangunan_bersih"] = df1_clean["nomor_bangunan_raw"].apply(extract_clean_no_bangunan)
df1_clean["status_penugasan"] = df1.get("assignmentStatusAlias", "")

# 2. Baca File 2 (Minimal - 16.195 baris)
print("📂 Membaca Dataset 2 (16,195 baris)...", end="", flush=True)
df2 = pd.read_csv("Raw_Assignment_SE2026_Minimal_20261118_181546.csv", low_memory=False, dtype=str)
print(f" [SELESAI] ({len(df2):,} baris)")

# 3. Gabungkan dan Deduplikasi Berdasarkan ID
print("⚙️ Menggabungkan dan mendeduplikasi data...", end="", flush=True)
df_master = pd.concat([df1_clean, df2]).drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
print(f" [SELESAI]")

print("\n" + "=" * 75)
print(f"📊 TOTAL DATASET MASTER GABUNGAN: {len(df_master):,} BARIS UNIK")
print("=" * 75)

# Cek sebaran per kecamatan
print("\nSebaran Data per Kecamatan di Dataset Master:")
kec_counts = df_master["nama_kecamatan"].value_counts()
for k, v in kec_counts.items():
    print(f"   • {k:<24}: {v:>5,} baris")

# 4. Rekapitulasi Bangunan Fisik Riil per SLS
df_valid_bgn = df_master[df_master["nomor_bangunan_bersih"] != ""].copy()
print(f"\n✓ Dari {len(df_master):,} baris, terdapat {len(df_valid_bgn):,} baris dengan nomor bangunan fisik terisi.")

group_cols = ["nama_kecamatan", "nama_desa", "kode_sls", "nama_sls"]
rekap_sls = df_valid_bgn.groupby(group_cols, dropna=False).agg(
    total_assignment=("id", "count"),
    total_bangunan_fisik=("nomor_bangunan_bersih", "nunique"),
    daftar_sampel_bangunan=("nomor_bangunan_bersih", lambda s: ", ".join(
        sorted(set(str(x) for x in s if str(x).strip()), key=sort_key_bangunan)[:15]
    ))
).reset_index()

rekap_sls["rasio_keluarga_per_bangunan"] = (
    rekap_sls["total_assignment"] / rekap_sls["total_bangunan_fisik"]
).round(2)

total_bgn_kab = rekap_sls["total_bangunan_fisik"].sum()
total_asg_kab = rekap_sls["total_assignment"].sum()

print("\n" + "=" * 75)
print("🏆 HASIL AKHIR REKAPITULASI KABUPATEN SITARO:")
print(f"   🏛️ Total SLS Terdata          : {len(rekap_sls):,} SLS")
print(f"   🏠 Total Bangunan Fisik Riil   : {total_bgn_kab:,} Bangunan (COUNT DISTINCT)")
print(f"   👨‍👩‍👧‍👦 Total Assignment / Keluarga: {total_asg_kab:,} Data")
print(f"   📈 Rata-rata Keluarga/Bangunan : {(total_asg_kab / total_bgn_kab):.2f} per bangunan fisik")
print("=" * 75)

# 5. Ekspor ke Excel Master
out_excel = "Master_Rekap_Bangunan_SE2026_Sitaro.xlsx"
out_csv = "Master_Data_Assignment_SE2026_Sitaro.csv"

print(f"\n💾 Menyimpan ke Excel: {out_excel} ...", end="", flush=True)
with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
    rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)
    df_master.to_excel(writer, sheet_name="Semua_Data_Assignment", index=False)
print(" [SELESAI]")

print(f"💾 Menyimpan ke CSV  : {out_csv} ...", end="", flush=True)
df_master.to_csv(out_csv, index=False, encoding="utf-8-sig")
print(" [SELESAI]")

print("\n✅ MASTER DATA & REKAP SELESAI!")
print(f"   📁 File Excel : {out_excel}")
print(f"   📁 File CSV   : {out_csv}")
