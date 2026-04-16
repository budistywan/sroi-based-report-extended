# Aturan Editing Semantic JSON — Global
**SROI Report Generation System | Semantic Editor**

Baca dokumen ini sebelum mengedit file apapun.

---

## Prinsip dasar

File `*_editable.json` adalah representasi laporan dalam format JSON.
Setiap `block` adalah satu unit konten: paragraf, judul, tabel, callout, dll.

**Apa yang kamu ubah di sini akan langsung menjadi konten laporan.**

---

## ✅ Selalu boleh

### Mengubah teks narasi
Field `"text"` di block `paragraph`, `paragraph_lead`, `paragraph_small`,
`callout_info`, `callout_warning`, `callout_success`:
```json
{
  "type": "paragraph",
  "text": "Ganti atau perluas narasi di sini. Tulis sepanjang yang diperlukan."
}
```

### Mengubah judul sub-bab
```json
{ "type": "heading_2", "text": "Judul Sub-bab yang Baru" }
```

### Menambah paragraf baru
Sisipkan di mana saja dalam array `blocks`:
```json
{
  "type": "paragraph",
  "text": "Paragraf tambahan. Bisa sepanjang apapun."
}
```

### Menambah callout
```json
{
  "type": "callout_info",
  "text": "Informasi tambahan atau catatan konteks.",
  "display_status": "show"
}
```

### Menambah bullet list
```json
{
  "type": "bullet_list",
  "items": ["Poin satu", "Poin dua", "Poin tiga"]
}
```

### Menghapus paragraf
Hapus seluruh block dari array — kecuali yang bertanda `"_protected": true`.

---

## ❌ Jangan lakukan ini

### 1. Jangan ubah `"type"`
```json
// SALAH — ini akan merusak renderer
{ "type": "table", ... }  →  { "type": "paragraph", ... }
```

### 2. Jangan ubah `"chapter_id"` di level atas
```json
// SALAH
"chapter_id": "bab_7"  →  "chapter_id": "bab_8"
```

### 3. Jangan hapus atau ubah angka di block `_protected`
Block yang ditandai `"_protected": true` adalah block finansial.
Data di `rows`, `items`, `data_points` bersumber dari Financial Engine —
jangan ubah nilainya.

```json
// BOLEH — ubah judul tabel
{ "type": "table", "_protected": true, "title": "Judul Baru", ... }

// JANGAN — ubah data tabel
{ "rows": [["bab_7", "2023", "Rp 999.999"]] }  // ← jangan diubah
```

### 4. Jangan hapus `"source_refs"`
Block yang punya `source_refs` terhubung ke audit log.
Boleh tambah teks, tapi jangan hapus field ini.

### 5. Jangan ubah `"column_widths"`, `"table_id"`, `"gap_type"`
Ini field teknis untuk renderer — kalau diubah, format dokumen bisa rusak.

---

## Tanda-tanda yang perlu diperhatikan

| Tanda | Artinya |
|-------|---------|
| `"_protected": true` | Block finansial — jangan ubah data |
| `"_edit_note": "..."` | Panduan spesifik untuk block ini |
| `"data_status": "proxy"` | Angka estimasi — boleh tambah narasi, jangan ubah angka |
| `"data_status": "pending"` | Data belum final — ini yang paling perlu dilengkapi |
| `"source_refs": [...]` | Ada referensi sumber — jangan hapus |

---

## Cara menambah block di posisi tertentu

Blocks adalah array — urutan penting. Sisipkan block baru di antara block yang ada:

```json
"blocks": [
  { "type": "heading_2", "text": "Sub-bab 4.1" },
  { "type": "paragraph", "text": "Paragraf asli." },
  
  // ← TAMBAHKAN BLOCK BARU DI SINI
  { "type": "paragraph", "text": "Paragraf tambahan yang memperkaya konteks." },
  
  { "type": "callout_info", "text": "Catatan berikutnya." }
]
```

---

## Workflow lengkap

```
1. Export
   python exporter.py bab_4
   → menghasilkan: exports/bab_4_editable.json
                   exports/bab_4_original.json
                   exports/bab_4_EDITING_GUIDE.md

2. Edit
   Buka bab_4_editable.json di text editor
   Edit sesuai aturan di dokumen ini

3. Validasi
   python validator.py exports/bab_4_editable.json \
     --original exports/bab_4_original.json
   → Harus muncul: "VALID — aman untuk diimport"

4. Import
   python importer.py exports/bab_4_editable.json \
     --original exports/bab_4_original.json
   → Menghasilkan: output/esl/work/chapter_semantic_bab_4_enriched.json

5. (Opsional) Render langsung
   python importer.py exports/bab_4_editable.json \
     --original exports/bab_4_original.json --render
   → Menghasilkan docx dari bab yang sudah diedit
```

---

## Tips editing yang baik

**Untuk Bab IV–VI (analytic register):**
Ini bab yang paling perlu diperkaya. Tambahkan:
- Data kondisi wilayah/sasaran yang spesifik
- Statistik yang mendukung problem framing
- Cerita kondisi nyata di lapangan

**Untuk Bab VIII (reflective register):**
Triple Loop Learning butuh narasi yang konkret. Tambahkan:
- Kejadian spesifik yang terjadi selama implementasi
- Keputusan yang berubah dan mengapa
- Pembelajaran yang tidak terduga

**Untuk Bab IX (conclusive register):**
Rekomendasi harus spesifik dan actionable. Tambahkan:
- Rekomendasi konkret per temuan
- Prioritas tindak lanjut

---

*Dokumen ini dihasilkan otomatis oleh SROI Semantic Editor.*
