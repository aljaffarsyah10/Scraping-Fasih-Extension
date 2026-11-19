"""
Script Otomatisasi Pengolahan Muatan Titik Bangunan (SE2026)
Meniru dan memverifikasi secara langsung logika QGIS 04 Pengolahan Muatan.model3:
1. Tahap 1: Agregasi Tingkat Bangunan Fisik Riil (GROUP BY: unique_bang)
2. Tahap 2: Agregasi Tingkat SLS / Sub-SLS (GROUP BY: idsubsls_261)
3. Ekspor ke Excel Workbook & GeoJSON
"""

import os
import sys
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
OUTPUT_DIR = ROOT_DIR / "output"

def cari_file_landmark():
    """Mencari file GeoJSON landmark di folder Titik Bangunan"""
    # 1. Cari yang spesifik Landmark Final Sitaro 12 November
    target_pattern = list(BASE_DIR.glob("*Landmark*Final*.geojson"))
    if target_pattern:
        return target_pattern[0]
    
    # 2. Cari file .geojson apa pun di folder
    all_geojson = list(BASE_DIR.glob("*.geojson"))
    if all_geojson:
        return all_geojson[0]
        
    return None

def proses_pengolahan_muatan(file_input=None):
    if file_input is None:
        file_input = cari_file_landmark()

    if not file_input or not Path(file_input).exists():
        print("❌ Tidak ditemukan file GeoJSON Landmark titik bangunan di folder 'Titik Bangunan'.")
        return

    print("=" * 75)
    print("📍 PENGOLAHAN MUATAN TITIK BANGUNAN (SE2026)")
    print(f"📂 File Sumber: {Path(file_input).name}")
    print("=" * 75)

    print("⏳ Membaca dan mem-parsing data GeoJSON...")
    with open(file_input, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    features = geojson_data.get("features", [])
    print(f"✓ Berhasil membaca {len(features):,} titik landmark/bangunan.")

    rows = []
    for feat in features:
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry", {}) or {}
        coords = geom.get("coordinates", [None, None]) if geom else [None, None]
        
        # Ekstrak atribut inti dengan fallback yang fleksibel
        assignment_id = props.get("assignment_id") or props.get("id_assignment") or props.get("id") or ""
        subsls = props.get("idsubsls_edited") or props.get("level_6_full_code") or props.get("idsubsls_origin") or props.get("idsubsls") or ""
        no_bang = str(props.get("no_bang", "") or "").strip()
        
        # Pastikan unique_bang terbentuk sempurna
        unique_bang = props.get("unique_bang")
        if not unique_bang or pd.isna(unique_bang):
            unique_bang = f"{subsls}#{no_bang.zfill(4)}"

        # Tangani koordinat
        lng = props.get("longitude_edited") or (coords[0] if coords and len(coords) > 0 else None)
        lat = props.get("latitude_edited") or (coords[1] if coords and len(coords) > 1 else None)

        rows.append({
            "assignment_id": str(assignment_id),
            "unique_bang": str(unique_bang),
            "idsubsls_261": str(subsls),
            "idsls": str(subsls)[:14] if len(str(subsls)) >= 14 else str(subsls),
            "kdprov": str(props.get("kdprov", "71") or "71"),
            "nmprov": str(props.get("nmprov", "SULAWESI UTARA") or "SULAWESI UTARA"),
            "kdkab": str(props.get("kdkab", "08") or "08"),
            "nmkab": str(props.get("nmkab", "SIAU TAGULANDANG BIARO") or "SIAU TAGULANDANG BIARO"),
            "kdkec": str(props.get("kdkec", "") or ""),
            "nmkec": str(props.get("nmkec", "") or ""),
            "kddesa": str(props.get("kddesa", "") or ""),
            "nmdesa": str(props.get("nmdesa", "") or ""),
            "nmsls": str(props.get("nmsls", "") or ""),
            "no_bang": no_bang,
            "kode_bang_value": props.get("kode_bang_value"),
            "kk": pd.to_numeric(props.get("kk", 0), errors="coerce") or 0,
            "btt": pd.to_numeric(props.get("btt", 0), errors="coerce") or 0,
            "bttk": pd.to_numeric(props.get("bttk", 0), errors="coerce") or 0,
            "bku": pd.to_numeric(props.get("bku", 0), errors="coerce") or 0,
            "bbtt": pd.to_numeric(props.get("bbtt", 0), errors="coerce") or 0,
            "usaha": pd.to_numeric(props.get("usaha") or props.get("jumlah_usaha_ditemukan") or 0, errors="coerce") or 0,
            "longitude": lng,
            "latitude": lat,
            "jml_bgn": 1,
            "jml_titik": 1
        })

    df = pd.DataFrame(rows)

    # =========================================================================
    # TAHAP 1: Agregasi per Bangunan Fisik (GROUP BY: unique_bang)
    # =========================================================================
    print("\n⚙️ Menjalankan Tahap 1: Agregasi Tingkat Bangunan Fisik (unique_bang)...")
    agg_bangunan = df.groupby("unique_bang", as_index=False).agg(
        idsubsls_261=("idsubsls_261", "first"),
        idsls=("idsls", "first"),
        kdprov=("kdprov", "first"),
        nmprov=("nmprov", "first"),
        kdkab=("kdkab", "first"),
        nmkab=("nmkab", "first"),
        kdkec=("kdkec", "first"),
        nmkec=("nmkec", "first"),
        kddesa=("kddesa", "first"),
        nmdesa=("nmdesa", "first"),
        nmsls=("nmsls", "first"),
        no_bang=("no_bang", "first"),
        jml_bgn=("jml_bgn", "max"),
        btt=("btt", "max"),
        bttk=("bttk", "max"),
        bku=("bku", "max"),
        bbtt=("bbtt", "max"),
        kk=("kk", "sum"),
        usaha=("usaha", "sum"),
        jml_titik=("jml_titik", "sum"),
        longitude=("longitude", "mean"),
        latitude=("latitude", "mean")
    )
    print(f"✓ Dihasilkan {len(agg_bangunan):,} Bangunan Fisik Riil Unik.")

    # =========================================================================
    # TAHAP 2: Agregasi per SLS / Sub-SLS (GROUP BY: idsubsls_261)
    # =========================================================================
    print("⚙️ Menjalankan Tahap 2: Agregasi Tingkat Sub-SLS & SLS...")
    agg_sls = agg_bangunan.groupby("idsubsls_261", as_index=False).agg(
        idsls=("idsls", "first"),
        kdprov=("kdprov", "first"),
        nmprov=("nmprov", "first"),
        kdkab=("kdkab", "first"),
        nmkab=("nmkab", "first"),
        kdkec=("kdkec", "first"),
        nmkec=("nmkec", "first"),
        kddesa=("kddesa", "first"),
        nmdesa=("nmdesa", "first"),
        nmsls=("nmsls", "first"),
        total_bangunan=("jml_bgn", "sum"),
        total_btt=("btt", "sum"),
        total_bttk=("bttk", "sum"),
        total_bku=("bku", "sum"),
        total_bbtt=("bbtt", "sum"),
        total_kk=("kk", "sum"),
        total_usaha=("usaha", "sum"),
        total_titik=("jml_titik", "sum")
    )

    # Tambahkan rekapitulasi tingkat kecamatan untuk ringkasan eksekutif
    agg_kec = agg_sls.groupby("nmkec", as_index=False).agg(
        total_sls=("idsls", "nunique"),
        total_subsls=("idsubsls_261", "count"),
        total_bangunan=("total_bangunan", "sum"),
        total_btt=("total_btt", "sum"),
        total_bttk=("total_bttk", "sum"),
        total_bku=("total_bku", "sum"),
        total_bbtt=("total_bbtt", "sum"),
        total_kk=("total_kk", "sum"),
        total_usaha=("total_usaha", "sum"),
        total_titik=("total_titik", "sum")
    )

    print("\n" + "=" * 75)
    print("🏆 RINGKASAN HASIL PENGOLAHAN MUATAN TITIK BANGUNAN:")
    print("=" * 75)
    print(f"   🏛️ Total Satuan Lingkungan (Sub-SLS) : {len(agg_sls):,} Sub-SLS ({agg_sls['idsls'].nunique():,} SLS)")
    print(f"   🏠 TOTAL BANGUNAN FISIK RIIL         : {agg_sls['total_bangunan'].sum():,} BANGUNAN")
    print(f"      • Bangunan Tempat Tinggal (BTT)   : {agg_sls['total_btt'].sum():,} Bangunan")
    print(f"      • Bangunan Tinggal Kosong (BTTK)  : {agg_sls['total_bttk'].sum():,} Bangunan")
    print(f"      • Bangunan Khusus Usaha (BKU)     : {agg_sls['total_bku'].sum():,} Bangunan")
    print(f"      • Bangunan Bukan Tmp Tinggal(BBTT): {agg_sls['total_bbtt'].sum():,} Bangunan")
    print(f"   👨‍👩‍👧‍👦 Total Keluarga (KK) Terdata     : {agg_sls['total_kk'].sum():,} KK")
    print(f"   🏢 Total Usaha Terdata               : {agg_sls['total_usaha'].sum():,} Usaha")
    print(f"   📍 Total Titik Muatan Asal           : {agg_sls['total_titik'].sum():,} Titik")
    print("=" * 75)

    print("\nSebaran Muatan Bangunan Fisik per Kecamatan:")
    print(agg_kec[["nmkec", "total_sls", "total_bangunan", "total_btt", "total_bttk", "total_bku", "total_bbtt", "total_kk"]].to_string(index=False))

    # =========================================================================
    # SIMPAN KE EXCEL & GEOJSON
    # =========================================================================
    OUTPUT_DIR.mkdir(exist_ok=True)
    excel_path = OUTPUT_DIR / "Hasil_Pengolahan_Muatan_Titik_Bangunan.xlsx"
    print(f"\n💾 Menyimpan hasil olah muatan ke Excel: '{excel_path}'...")
    
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        agg_sls.to_excel(writer, sheet_name="Muatan_per_SLS", index=False)
        agg_kec.to_excel(writer, sheet_name="Ringkasan_Kecamatan", index=False)
        agg_bangunan.to_excel(writer, sheet_name="Data_Bangunan_Fisik", index=False)

    print("✓ Berhasil menyimpan workbook Excel.")
    return agg_sls

if __name__ == "__main__":
    proses_pengolahan_muatan()
