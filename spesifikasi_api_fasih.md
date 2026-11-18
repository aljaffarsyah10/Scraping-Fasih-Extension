# Deliverable Fase 1: Spesifikasi API Daftar Assignment Fasih SM (Tervalidasi)

Berdasarkan hasil tangkapan riil dari web Fasih SM, berikut adalah spesifikasi resmi endpoint daftar penugasan / assignment:

---

## 1. Detail Endpoint

| Parameter | Nilai Resmi |
|---|---|
| **URL Endpoint** | `/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode` |
| **Full URL** | `https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode` |
| **HTTP Method** | `GET` |
| **Autentikasi** | Browser Cookies / SSO BPS (`credentials: 'include'`) |
| **Header Wajib** | `accept: application/json`<br>`x-requested-with: XMLHttpRequest` |

---

## 2. Parameter Query (GET)

| Parameter | Tipe | Nilai Contoh | Keterangan |
|---|---|---|---|
| `page` | Integer | `0`, `1`, `2`, ... | Indeks halaman (0-based) |
| `size` | Integer | `10`, `25`, `50`, `100` | Jumlah baris per halaman |
| `periodeId` | UUID | `a0429e96-51a5-477b-a415-485f9c153004` | ID Survei / Periode SE2026 |

---

## 3. Contoh Request Asli dari Browser

```javascript
fetch("https://fasih-sm.bps.go.id/app/api/analytic/api/v2/assignment/datatable-all-user-survey-periode?page=0&size=50&periodeId=a0429e96-51a5-477b-a415-485f9c153004", {
  "headers": {
    "accept": "application/json",
    "x-requested-with": "XMLHttpRequest"
  },
  "method": "GET",
  "credentials": "include"
});
```
