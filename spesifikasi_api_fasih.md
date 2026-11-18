# Deliverable Fase 1: Spesifikasi API Daftar Assignment Fasih SM

Dokumen ini mencatat hasil observasi (*reconnaissance*) terhadap endpoint internal web Fasih SM BPS untuk digunakan pada **Fase 2 (Core Fetching Engine)**.

---

## 1. Ringkasan Endpoint

| Parameter | Nilai / Spesifikasi |
|---|---|
| **URL Endpoint** | *(Akan diisi dari tangkapan sniffer, misal: `/app/api/assignment-general/api/assignment/list` atau serupa)* |
| **HTTP Method** | `GET` / `POST` |
| **Autentikasi** | Browser Cookies / Session Keycloak SSO BPS (`credentials: 'include'`) |
| **Header Khusus** | `Content-Type: application/json`, `Accept: application/json` |

---

## 2. Parameter Request (Query Params / Payload)

| Parameter | Tipe | Keterangan / Contoh Nilai |
|---|---|---|
| `periodeId` | String (UUID) | ID periode survei yang sedang aktif (misal: `fd68e454-...`) |
| `page` | Integer | Indeks halaman (dimulai dari `0` atau `1`) |
| `size` / `limit` | Integer | Jumlah baris per halaman (biasanya `10`, `25`, atau `50`) |
| `sort` | String | Format pengurutan (misal: `createdDate,desc`) |
| `status` | String (Opsional) | Filter status penugasan (contoh: *SUBMITTED*, *APPROVED*) |
| `kecamatan` / `desa` | String (Opsional) | Filter kode wilayah kerja |

---

## 3. Struktur Skema Respons JSON

```json
{
  "status": "SUCCESS / 200",
  "data": {
    "content": [
      {
        "id": "assignment-uuid",
        "kodeWilayah": "7108...",
        "namaUsaha": "NAMA USAHA / KRT",
        "status": "APPROVED",
        "pcl": "Nama Petugas PCL",
        "pml": "Nama Pengawas PML",
        "updatedAt": "2026-10-20T10:00:00Z"
      }
    ],
    "totalElements": 1500,
    "totalPages": 30,
    "size": 50,
    "number": 0
  }
}
```

---

## 4. Pemetaan Kolom untuk Ekspor (Target Output)

| Nama Kolom Output (Excel/CSV) | Path JSON di Fasih API | Contoh Data |
|---|---|---|
| **ID Assignment** | `item.id` / `item.assignmentId` | `c0fcb836-7108-410a-...` |
| **Kecamatan** | `item.kecamatan` / `item.kodeKec` | `010 - TABUKAN UTARA` |
| **Desa / Kelurahan** | `item.desa` / `item.kodeDesa` | `001 - BENGKET` |
| **Nama Usaha / KRT** | `item.namaUsaha` / `item.namaKrt` | `WARUNG MAKAN SEJAHTERA` |
| **Status Dokumen** | `item.status` | `APPROVED` / `SUBMITTED` |
| **Petugas Pencacah (PCL)** | `item.pclName` / `item.petugasPcl` | `Ahmad ...` |
| **Pengawas (PML)** | `item.pmlName` / `item.petugasPml` | `Siti ...` |
| **Waktu Pembaruan** | `item.updatedAt` | `2026-10-22 14:00` |

---

*Catatan: Dokumen ini akan diperbarui secara otomatis setelah data tangkapan Fase 1 dimasukkan.*
