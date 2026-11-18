import json
import requests
import urllib3
import pandas as pd

urllib3.disable_warnings()

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

df_master = pd.read_csv('Master_Data_Assignment_SE2026_Sitaro.csv', low_memory=False)
our_ids = set(df_master['id'])
print(f"Total ID di file master kita: {len(our_ids):,}")

# Tarik seluruh status OPEN (374 data) dari server
open_items = []
page = 0
page_size = 100

print("Mengambil seluruh status OPEN dari server...")
while True:
    payload = {
        'start': page * page_size,
        'length': page_size,
        'columns': [{'data': 'id', 'orderable': True}],
        'order': [],
        'search': {'value': '', 'regex': False},
        'assignmentExtraParam': {
            'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
            'assignmentErrorStatusType': -1,
            'filterTargetType': 'TARGET_ONLY',
            'assignmentStatusAlias': 'OPEN'
        }
    }
    r = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
    if r.status_code != 200:
        print(f"Error {r.status_code}")
        break
    data = r.json()
    items = data.get('searchData', [])
    if not items:
        break
    open_items.extend(items)
    print(f"  Page {page}: didapat {len(items)} items. Total: {len(open_items)} / {data.get('totalHit')}")
    if len(open_items) >= data.get('totalHit'):
        break
    page += 1

print(f"\nTotal status OPEN yang didapat langsung dari server: {len(open_items)} data")

# Cek berapa yang belum ada di database kita
missing_in_our_data = []
for it in open_items:
    if it['id'] not in our_ids:
        missing_in_our_data.append(it)

print(f"Jumlah data OPEN yang belum ada di database kita: {len(missing_in_our_data)} data")

# Tampilkan sampel data yang belum ada
if missing_in_our_data:
    print("\nSampel data yang belum terambil sebelumnya:")
    for it in missing_in_our_data[:10]:
        reg = it.get('region', {})
        kec = reg.get('level1', {}).get('level2', {}).get('level3', {})
        desa = kec.get('level4', {})
        sls = desa.get('level5', {})
        print(f"  • ID: {it['id']}")
        print(f"    CodeIdentity: {it.get('codeIdentity')}")
        print(f"    Kecamatan: {kec.get('name')} (Kode: {kec.get('fullCode')})")
        print(f"    Desa: {desa.get('name')} (Kode: {desa.get('fullCode')})")
        print(f"    SLS: {sls.get('name')} (Kode: {sls.get('fullCode')})")
        print(f"    Data1: {it.get('data1')}")
        print(f"    Data3: {it.get('data3')}")
        print("-" * 50)
