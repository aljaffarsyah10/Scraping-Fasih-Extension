# Spesifikasi Resmi API Fasih SM (Tervalidasi 100%)

Berdasarkan hasil tangkapan riil dari transmisi tabel penugasan Fasih SM:

---

## 1. Detail Endpoint & Protokol

| Parameter | Spesifikasi Resmi |
|---|---|
| **URL Endpoint** | `/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode` |
| **Full URL** | `https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode` |
| **HTTP Method** | **`POST`** (Bukan `GET`) |
| **Content-Type** | `application/json` |
| **Header Wajib** | `X-XSRF-TOKEN: <token-dari-cookie>`<br>`Accept: */*`<br>`X-Requested-With: XMLHttpRequest` |
| **Credentials** | `include` (Cookie sesi aktif) |

---

## 2. Struktur Payload Body (JSON POST)

```json
{
  "start": 0,
  "length": 50,
  "columns": [
    {"data": "id", "orderable": true},
    {"data": "codeIdentity", "orderable": true},
    {"data": "data1", "orderable": true},
    {"data": "data2", "orderable": true},
    {"data": "data3", "orderable": true},
    {"data": "data4", "orderable": true},
    {"data": "data5", "orderable": true},
    {"data": "data6", "orderable": true},
    {"data": "data7", "orderable": true},
    {"data": "data8", "orderable": true},
    {"data": "data9", "orderable": true},
    {"data": "data10", "orderable": true}
  ],
  "order": [],
  "search": {"value": "", "regex": false},
  "assignmentExtraParam": {
    "surveyPeriodId": "fd68e454-ba45-4b85-8205-f3bf777ded24",
    "assignmentErrorStatusType": -1,
    "filterTargetType": "TARGET_ONLY"
  }
}
```

---

## 3. Skema Data Respons (DataTables Standard)

- `recordsTotal`: Total data (contoh: `35585`)
- `recordsFiltered`: Total data terfilter
- `data`: Array objek baris (`id`, `codeIdentity`, `data1` s.d `data10`, dsb.)
