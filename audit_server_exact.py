import json
import time
import requests
import urllib3

urllib3.disable_warnings()

with open('fresh_cookie.txt') as f:
    cookie = f.read().strip()

url = 'https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode'
url_agg = 'https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode-aggregation'

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

def query(search_val="", extra=None):
    if extra is None:
        extra = {}
    payload = {
        'start': 0,
        'length': 1,
        'columns': [{'data': 'id', 'orderable': True}],
        'order': [],
        'search': {'value': str(search_val), 'regex': False},
        'assignmentExtraParam': {
            'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24',
            'assignmentErrorStatusType': -1,
            'filterTargetType': 'TARGET_ONLY',
            **extra
        }
    }
    r = requests.post(url, json=payload, headers=headers, verify=False, timeout=15)
    if r.status_code == 200:
        return r.json()
    return {'error': r.status_code, 'text': r.text[:100]}

# 1. Total di database saat ini
res_global = query("")
print(f"Total di Database Fasih (recordsTotal) : {res_global.get('recordsTotal')}")
print(f"Total Hit tanpa filter (totalHit)      : {res_global.get('totalHit')}")

# 2. Cek Agregasi Status
r_agg = requests.post(url_agg, json={'search': {'value': '', 'regex': False}, 'assignmentExtraParam': {'surveyPeriodId': 'fd68e454-ba45-4b85-8205-f3bf777ded24', 'assignmentErrorStatusType': -1, 'filterTargetType': 'TARGET_ONLY'}}, headers=headers, verify=False)
if r_agg.status_code == 200:
    agg = r_agg.json().get('searchAggregation', [])
    tot_agg = sum(item.get('docCount', 0) for item in agg)
    print(f"\nTotal dari searchAggregation: {tot_agg} data")
    for a in agg:
        print(f"  • {a.get('keyAggregation'):<35}: {a.get('docCount'):>6} data")
