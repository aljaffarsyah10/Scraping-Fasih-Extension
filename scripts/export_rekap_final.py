import pandas as pd
import re
import datetime

def sort_key_bangunan(val):
    s = str(val).strip()
    if s.isdigit():
        return (0, int(s), "")
    m = re.match(r"^(\d+)(.*)$", s)
    if m:
        return (0, int(m.group(1)), m.group(2))
    return (1, 0, s)

def format_daftar_bangunan(series):
    clean_list = [str(x).strip() for x in series if pd.notna(x) and str(x).strip() != ""]
    unique_sorted = sorted(set(clean_list), key=sort_key_bangunan)
    return ", ".join(unique_sorted)

print("=" * 80)
print("📊 EXPORT REKAPITULASI BANGUNAN FISIK SE2026 SITARO (100% COVERAGE)")
print("=" * 80)

# Baca master CSV yang sudah berhasil tersimpan 35.585 baris
df_final = pd.read_csv('Master_Data_Assignment_SE2026_Sitaro.csv', low_memory=False, dtype=str)
print(f"✓ Berhasil membaca master CSV: {len(df_final):,} baris.")

df_valid_bgn = df_final[df_final["nomor_bangunan_bersih"] != ""].copy()
print(f"✓ Baris dengan nomor bangunan fisik terisi: {len(df_valid_bgn):,} baris.")

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

print("\n" + "=" * 80)
print("🏆 HASIL AKHIR REKAPITULASI:")
print(f"   • Total Seluruh Penugasan (Assignment)   : {len(df_final):,} baris")
print(f"   • Total Penugasan dengan No. Bangunan    : {total_assign_valid:,} baris")
print(f"   • Total SLS / Satuan Lingkungan          : {total_sls:,} SLS")
print(f"   • TOTAL BANGUNAN FISIK RIIL (SE2026)     : {total_bangunan_sum:,} BANGUNAN")
print("=" * 80)

# Simpan ke Excel Final
excel_filename = "Master_Rekap_Bangunan_SE2026_Sitaro_35k_Final.xlsx"
print(f"\n💾 Menyimpan workbook Excel ke '{excel_filename}'...")

with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
    rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)
    # Sheet Semua Assignment (35.585 baris)
    df_final.to_excel(writer, sheet_name="Semua_Assignment", index=False)

print(f"✓ Sukses menyimpan: {excel_filename}")

# Coba juga simpan ke Master_Rekap_Bangunan_SE2026_Sitaro.xlsx jika sudah tidak dikunci Excel
try:
    with pd.ExcelWriter("Master_Rekap_Bangunan_SE2026_Sitaro.xlsx", engine="openpyxl") as writer:
        rekap_sls.to_excel(writer, sheet_name="Rekap_Bangunan_per_SLS", index=False)
        df_final.to_excel(writer, sheet_name="Semua_Assignment", index=False)
    print("✓ Sukses mengupdate: Master_Rekap_Bangunan_SE2026_Sitaro.xlsx")
except PermissionError:
    print("ℹ️ Catatan: 'Master_Rekap_Bangunan_SE2026_Sitaro.xlsx' sedang dibuka di Excel pengguna.")
    print(f"   Data lengkap 35k tersimpan aman di '{excel_filename}'.")
