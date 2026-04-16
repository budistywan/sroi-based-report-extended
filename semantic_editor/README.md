# Semantic Editor
**SROI Report Generation System — Extension Layer**

Ekstensi untuk export, edit, dan import kembali chapter semantic JSON
dari pipeline SROI tanpa menyentuh core pipeline.

---

## Cara kerja

```
pipeline output (chapter_semantic_bab_X.json)
        ↓
   exporter.py          → bab_X_editable.json + EDITING_GUIDE.md
        ↓
   [USER EDIT]          → edit teks, tambah paragraf, perkaya konteks
        ↓
   validator.py         → cek schema, substance lock, block integrity
        ↓
   importer.py          → chapter_semantic_bab_X_enriched.json
        ↓
   renderer/assembler   → .docx final yang lebih kaya
```

---

## Instalasi

Tidak ada dependensi tambahan — semua berjalan dengan Python standar
yang sudah ada di production bundle.

---

## Penggunaan

### 1. Export satu bab
```bash
python exporter.py bab_4
# Output: exports/bab_4_editable.json + exports/bab_4_EDITING_GUIDE.md
```

### 2. Export semua bab
```bash
python exporter.py all
```

### 3. Edit file
Buka `exports/bab_4_editable.json` di text editor.
Baca `exports/bab_4_EDITING_GUIDE.md` dan `templates/EDITING_RULES_GLOBAL.md` dulu.

### 4. Validasi
```bash
python validator.py exports/bab_4_editable.json \
  --original exports/bab_4_original.json
```

### 5. Import
```bash
python importer.py exports/bab_4_editable.json \
  --original exports/bab_4_original.json
```

### 6. Import + render langsung ke .docx
```bash
python importer.py exports/bab_4_editable.json \
  --original exports/bab_4_original.json --render
```

---

## Apa yang boleh dan tidak boleh diedit

Lihat `templates/EDITING_RULES_GLOBAL.md` untuk aturan lengkap.

**Ringkasan:**
- ✅ Field `text` di paragraph, callout, heading — bebas diedit
- ✅ Menambah paragraf, callout, bullet list baru
- ✅ Menghapus paragraf (kecuali yang `_protected`)
- ❌ Field `type` — jangan ubah
- ❌ Angka di block finansial (`_protected: true`)
- ❌ `chapter_id`, `source_refs`, `table_id`, `column_widths`

---

## Validator checks

| Check | Keterangan |
|-------|-----------|
| JSON valid | File bisa di-parse |
| chapter_id terjaga | Tidak berubah dari original |
| block_type valid | Semua type dikenal renderer |
| block_type tidak berubah | Financial block types tidak diganti |
| Substance lock | Angka finansial identik dengan original |
| source_refs | Tidak dihilangkan dari block yang memilikinya |
| Protected blocks | Block `_protected` tidak dihapus |

---

## Struktur folder

```
semantic_editor/
  exporter.py              ← export semantic JSON ke editable
  importer.py              ← import + validate kembali ke pipeline
  validator.py             ← standalone validator
  templates/
    EDITING_RULES_GLOBAL.md  ← kontrak editing
  examples/                ← contoh edit yang valid
  exports/                 ← output exporter (git-ignored)
  README.md
```

---

## Catatan penting

- `exports/` folder sebaiknya di-gitignore — berisi data program yang mungkin sensitif
- File `*_original.json` jangan diedit — ini referensi untuk validator
- Setelah import, file `*_enriched.json` yang dipakai pipeline (bukan `*_editable.json`)
