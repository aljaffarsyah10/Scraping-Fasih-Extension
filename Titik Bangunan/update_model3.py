import xml.etree.ElementTree as ET
import shutil
from pathlib import Path

BASE_DIR = Path('Titik Bangunan')
MODEL_PATH = BASE_DIR / '04 Pengolahan Muatan.model3'
BACKUP_PATH = BASE_DIR / '04 Pengolahan Muatan_backup_asli.model3'

if not BACKUP_PATH.exists():
    shutil.copyfile(MODEL_PATH, BACKUP_PATH)
    print(f"✓ Backup dibuat di: {BACKUP_PATH}")

def create_field_map_option(name, expr, f_type, type_name=""):
    opt = ET.Element('Option', {'type': 'Map'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': expr, 'name': 'expression'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': '0', 'name': 'length'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': name, 'name': 'name'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': '0', 'name': 'precision'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': '0', 'name': 'sub_type'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': str(f_type), 'name': 'type'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': type_name, 'name': 'type_name'})
    return opt

def create_aggregate_option(name, input_expr, agg_func, f_type=10):
    opt = ET.Element('Option', {'type': 'Map'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': agg_func, 'name': 'aggregate'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': ',', 'name': 'delimiter'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': input_expr, 'name': 'input'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': '0', 'name': 'length'})
    ET.SubElement(opt, 'Option', {'type': 'QString', 'value': name, 'name': 'name'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': '0', 'name': 'precision'})
    ET.SubElement(opt, 'Option', {'type': 'int', 'value': str(f_type), 'name': 'type'})
    return opt

tree = ET.parse(BACKUP_PATH)
root = tree.getroot()

# ==========================================
# 1. Update native:refactorfields_3
# ==========================================
rf_node = root.find('.//Option[@name="native:refactorfields_3"]')
fields_mapping_static = rf_node.find('.//Option[@name="FIELDS_MAPPING"]//Option[@name="static_value"]')
fields_mapping_static.clear()

refactor_fields = [
    ("id_assignment", 'coalesce("assignment_id", "id_assignment", "id", \'\')', 10, "text"),
    ("unique_bang", 'coalesce("unique_bang", coalesce("idsubsls_edited", "level_6_full_code", "idsubsls_origin", "idsubsls") || \'#\' || lpad(to_string("no_bang"), 4, \'0\'))', 10, "text"),
    ("kdprov", 'coalesce("kdprov", \'71\')', 10, "text"),
    ("nmprov", 'coalesce("nmprov", \'SULAWESI UTARA\')', 10, "text"),
    ("kdkab", 'coalesce("kdkab", \'08\')', 10, "text"),
    ("nmkab", 'coalesce("nmkab", \'SIAU TAGULANDANG BIARO\')', 10, "text"),
    ("kdkec", 'coalesce("kdkec", \'\')', 10, "text"),
    ("nmkec", 'coalesce("nmkec", \'\')', 10, "text"),
    ("kddesa", 'coalesce("kddesa", \'\')', 10, "text"),
    ("nmdesa", 'coalesce("nmdesa", \'\')', 10, "text"),
    ("idsls", 'coalesce("idsls", substr(coalesce("idsubsls_edited", "level_6_full_code", "idsubsls_origin", "idsubsls"), 1, 14), \'\')', 10, "text"),
    ("nmsls", 'coalesce("nmsls", \'\')', 10, "text"),
    ("idsubsls_origin", 'coalesce("idsubsls_origin", "level_6_full_code", \'\')', 10, "text"),
    ("idsubsls_261", 'coalesce("idsubsls_261", "idsubsls_edited", "level_6_full_code", "idsubsls_origin", "idsubsls", \'\')', 10, "text"),
    ("latitude_origin", 'to_real(coalesce("latitude_origin", "latitude_edited", $y))', 6, "double precision"),
    ("longitude_origin", 'to_real(coalesce("longitude_origin", "longitude_edited", $x))', 6, "double precision"),
    ("latitude_edited", 'to_real(coalesce("latitude_edited", $y, "latitude_origin"))', 6, "double precision"),
    ("longitude_edited", 'to_real(coalesce("longitude_edited", $x, "longitude_origin"))', 6, "double precision"),
    ("no_bang", 'coalesce("no_bang", \'\')', 10, "text"),
    ("kode_bang_value", 'to_int(coalesce("kode_bang_value", 0))', 2, "integer"),
    ("kk", 'to_int(coalesce("kk", 0))', 4, "int8"),
    ("btt", 'to_int(coalesce("btt", 0))', 4, "int8"),
    ("bttk", 'to_int(coalesce("bttk", 0))', 4, "int8"),
    ("bku", 'to_int(coalesce("bku", 0))', 4, "int8"),
    ("bbtt", 'to_int(coalesce("bbtt", 0))', 4, "int8"),
    ("usaha", 'to_int(coalesce("usaha", "jumlah_usaha_ditemukan", 0))', 4, "int8"),
    ("jml_bgn", '1', 4, "int8"),
    ("jml_titik", '1', 4, "int8")
]

for f_name, expr, f_type, t_name in refactor_fields:
    fields_mapping_static.append(create_field_map_option(f_name, expr, f_type, t_name))

# ==========================================
# 2. Update native:aggregate_1 (Group By: unique_bang)
# ==========================================
agg1_node = root.find('.//Option[@name="native:aggregate_1"]')
agg1_static = agg1_node.find('.//Option[@name="AGGREGATES"]//Option[@name="static_value"]')
agg1_static.clear()

aggregates_step1 = [
    ("unique_bang", '"unique_bang"', "majority", 10),
    ("idsubsls_261", '"idsubsls_261"', "majority", 10),
    ("idsls", '"idsls"', "majority", 10),
    ("kdprov", '"kdprov"', "majority", 10),
    ("nmprov", '"nmprov"', "majority", 10),
    ("kdkab", '"kdkab"', "majority", 10),
    ("nmkab", '"nmkab"', "majority", 10),
    ("kdkec", '"kdkec"', "majority", 10),
    ("nmkec", '"nmkec"', "majority", 10),
    ("kddesa", '"kddesa"', "majority", 10),
    ("nmdesa", '"nmdesa"', "majority", 10),
    ("nmsls", '"nmsls"', "majority", 10),
    ("no_bang", '"no_bang"', "majority", 10),
    ("jml_bgn", '"jml_bgn"', "maximum", 4),
    ("btt", '"btt"', "maximum", 4),
    ("bttk", '"bttk"', "maximum", 4),
    ("bku", '"bku"', "maximum", 4),
    ("bbtt", '"bbtt"', "maximum", 4),
    ("kk", '"kk"', "sum", 4),
    ("usaha", '"usaha"', "sum", 4),
    ("jml_titik", '"jml_titik"', "sum", 4)
]

for name, inp, agg_func, f_type in aggregates_step1:
    agg1_static.append(create_aggregate_option(name, inp, agg_func, f_type))

# ==========================================
# 3. Update native:aggregate_2 (Group By: idsubsls_261)
# ==========================================
agg2_node = root.find('.//Option[@name="native:aggregate_2"]')
agg2_static = agg2_node.find('.//Option[@name="AGGREGATES"]//Option[@name="static_value"]')
agg2_static.clear()

aggregates_step2 = [
    ("idsubsls_261", '"idsubsls_261"', "majority", 10),
    ("idsls", '"idsls"', "majority", 10),
    ("kdprov", '"kdprov"', "majority", 10),
    ("nmprov", '"nmprov"', "majority", 10),
    ("kdkab", '"kdkab"', "majority", 10),
    ("nmkab", '"nmkab"', "majority", 10),
    ("kdkec", '"kdkec"', "majority", 10),
    ("nmkec", '"nmkec"', "majority", 10),
    ("kddesa", '"kddesa"', "majority", 10),
    ("nmdesa", '"nmdesa"', "majority", 10),
    ("nmsls", '"nmsls"', "majority", 10),
    ("total_bangunan", '"jml_bgn"', "sum", 4),
    ("total_btt", '"btt"', "sum", 4),
    ("total_bttk", '"bttk"', "sum", 4),
    ("total_bku", '"bku"', "sum", 4),
    ("total_bbtt", '"bbtt"', "sum", 4),
    ("total_kk", '"kk"', "sum", 4),
    ("total_usaha", '"usaha"', "sum", 4),
    ("total_titik", '"jml_titik"', "sum", 4)
]

for name, inp, agg_func, f_type in aggregates_step2:
    agg2_static.append(create_aggregate_option(name, inp, agg_func, f_type))

# Tulis ulang XML dengan header DOCTYPE model
xml_str = ET.tostring(root, encoding='utf-8').decode('utf-8')
full_content = f"<!DOCTYPE model>\n{xml_str}"

with open(MODEL_PATH, 'w', encoding='utf-8') as f:
    f.write(full_content)

print("✅ Model 04 Pengolahan Muatan.model3 BERHASIL DIUPDATE!")
