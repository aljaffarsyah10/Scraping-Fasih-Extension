import requests, urllib3, time
import pandas as pd
urllib3.disable_warnings()

with open('fresh_cookie.txt') as f:
    cookie = f.read().strip()

url = 'https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode'
headers = {
    'Accept': '*/*',
    'Content-Type': 'application/json',
    'Origin': 'https://fasih-sm.bps.go.id',
    'Referer': 'https://fasih-sm.bps.go.id/app/surveys/a0429e96-51a5-477b-a415-485f9c153004/fd68e454-ba45-4b85-8205-f3bf777ded24/data',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 9 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Mobile Safari/537.36',
    'X-XSRF-TOKEN': '55edd9d0-2888-4d52-8572-a96445cd513d',
    'Cookie': cookie
}

df = pd.read_csv('Master_Data_Assignment_SE2026_Sitaro.csv', low_memory=False, dtype=str)
df['kode_kec'] = df['codeIdentity'].astype(str).str.slice(0, 7)

kecs = [
    ('7108000', 'Tingkat Kabupaten'),
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

print(f"{'Kode Kec':<10} | {'Nama Kecamatan':<22} | {'Server Total':<12} | {'Master Kita':<12} | {'Selisih':<10}")
print("-" * 75)
tot_srv = 0
tot_our = 0

for k, nama in kecs:
    payload = {
        'start': 0, 'length': 1,
        'columns': [{'data': 'id'}],
        'order': [],
        'search': {'value': k, 'regex': False},
        'assignmentExtraParam': {
            'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
            'assignmentErrorStatusType': -1,
            'filterTargetType': 'TARGET_ONLY'
        }
    }
    r = requests.post(url, json=payload, headers=headers, verify=False, timeout=10)
    server_cnt = r.json().get('totalHit', 0) if r.status_code == 200 else -1
    our_cnt = int((df['kode_kec'] == k).sum())
    diff = server_cnt - our_cnt
    tot_srv += server_cnt
    tot_our += our_cnt
    print(f"{k:<10} | {nama:<22} | {server_cnt:<12} | {our_cnt:<12} | {diff:<10}")
    time.sleep(0.3)

print("-" * 75)
print(f"{'TOTAL':<10} | {'Semua Wilayah':<22} | {tot_srv:<12} | {tot_our:<12} | {tot_srv - tot_our:<10}")
