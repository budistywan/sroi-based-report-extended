"""
exporter.py — Semantic Editor
Export chapter semantic JSON dari pipeline output ke format
yang siap diedit user, lengkap dengan companion editing guide.

Usage:
  python exporter.py bab_4
  python exporter.py bab_7 --semantic-dir /path/output/esl/work/
  python exporter.py all   --semantic-dir /path/output/esl/work/
"""

import json, shutil, argparse, sys
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser(description="Semantic JSON Exporter")
parser.add_argument("chapter",
                    help="ID bab (bab_1 ... bab_9) atau 'all'")
parser.add_argument("--semantic-dir", "-s", default=None,
                    help="Direktori berisi chapter_semantic_bab*.json")
parser.add_argument("--output-dir",   "-o", default=None,
                    help="Direktori output editable files (default: ./exports/)")
parser.add_argument("--no-guide",     action="store_true",
                    help="Jangan generate companion editing guide")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
# Cari semantic dir — prefer output/esl/work dari production bundle
SEMANTIC_DIR = Path(args.semantic_dir) if args.semantic_dir else next((
    p for p in [
        SCRIPT_DIR.parent / "output/esl/work",
        SCRIPT_DIR.parent / "sprint9/output/esl/work",
        SCRIPT_DIR.parent / "data/semantic",
    ] if p.exists()
), None)

OUTPUT_DIR   = Path(args.output_dir) if args.output_dir \
    else SCRIPT_DIR / "exports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not SEMANTIC_DIR or not SEMANTIC_DIR.exists():
    print("FAIL: semantic-dir tidak ditemukan. Jalankan pipeline dulu atau "
          "gunakan --semantic-dir /path/to/chapter_semantics/")
    sys.exit(1)

# Register pemetaan per bab
REGISTER_MAP = {
    "bab_1": "framing",    "bab_2": "framing",    "bab_3": "framing",
    "bab_4": "analytic",   "bab_5": "analytic",   "bab_6": "analytic",
    "bab_7": "evaluative", "bab_8": "reflective",  "bab_9": "conclusive",
}

EDITABLE_SUMMARY = {
    "framing":    "Bab ini bersifat metodologis dan orientatif. Bebas memperkaya narasi konteks dan framing.",
    "analytic":   "Bab ini bersifat diagnostik. Sangat dianjurkan memperkaya data kondisi awal, masalah, dan potensi.",
    "evaluative": "Bab ini berisi data finansial. Narasi boleh diedit, tapi ANGKA TIDAK BOLEH DIUBAH.",
    "reflective": "Bab ini bersifat reflektif. Bebas memperkaya learning signals dan cerita pembelajaran.",
    "conclusive": "Bab ini bersifat penutup. Bebas memperkaya kesimpulan dan rekomendasi.",
}

FINANCIAL_WARNING = {
    "evaluative": True,
}


def find_semantic_file(chapter_id: str) -> Path | None:
    """Cari file semantic untuk chapter_id tertentu."""
    candidates = [
        SEMANTIC_DIR / f"chapter_semantic_{chapter_id}.json",
        # bab_7 naming quirk
        SEMANTIC_DIR / "chapter_semantic_bab7.json"
        if chapter_id == "bab_7" else None,
    ]
    for c in candidates:
        if c and c.exists():
            return c
    return None


def mark_protected_blocks(blocks: list) -> list:
    """Tandai block yang tidak boleh dihapus atau diubah."""
    import re
    NUM = re.compile(r'Rp\s*[\d.,]+|1\s*:\s*[\d.,]+|\d{6,}')
    marked = []
    for b in blocks:
        b = dict(b)  # copy
        btype = b.get("type", "")
        # Financial blocks: protected
        if btype in ("table", "table_borderless", "metric_card_3col", "bar_chart_text"):
            b["_protected"] = True
            b["_edit_note"] = "JANGAN ubah rows/data — hanya title dan note boleh diedit"
        # Callout dengan source_refs: semi-protected
        elif b.get("source_refs"):
            b["_edit_note"] = "source_refs jangan dihapus — boleh tambah teks"
        # Paragraf yang mengandung angka kritis
        elif btype == "paragraph" and NUM.search(b.get("text", "")):
            b["_edit_note"] = ("Paragraf ini mengandung angka finansial. "
                               "Boleh ubah gaya kalimat, tapi JANGAN ubah angkanya.")
        marked.append(b)
    return marked


def generate_editing_guide(chapter_id: str, register: str,
                           block_count: int, financial_blocks: int) -> str:
    """Generate companion markdown editing guide."""
    summary   = EDITABLE_SUMMARY.get(register, "")
    fin_warn  = FINANCIAL_WARNING.get(register, False)

    guide = f"""# Panduan Editing: {chapter_id.upper()}
**Register**: {register} | **Blocks**: {block_count}

## Karakter bab ini
{summary}

## Status edit
- File editable: `{chapter_id}_editable.json`
- File original : `{chapter_id}_original.json` (jangan ubah)

---

## ✅ Boleh dilakukan

| Aksi | Cara |
|------|------|
| Mengubah teks narasi | Edit field `"text"` di block paragraph |
| Mengubah judul sub-bab | Edit field `"text"` di block heading_2 |
| Menambah paragraf baru | Tambahkan block dengan `"type": "paragraph"` |
| Menambah callout info | Tambahkan block dengan `"type": "callout_info"` |
| Memperkaya bullet list | Edit array `"items"` di block bullet_list |
| Menghapus paragraf | Hapus block (kecuali yang bertanda `_protected`) |

---

## ❌ TIDAK boleh dilakukan

| Larangan | Alasan |
|----------|--------|
| Ubah field `"type"` | Akan merusak renderer |
| Ubah `"chapter_id"` | Referensi internal pipeline |
| Ubah angka di block berlabel `_protected` | Terhubung ke audit log finansial |
| Hapus `"source_refs"` | Merusak auditability |
| Ubah `"column_widths"` | Format tabel akan rusak |
| Ubah `"table_id"` | Referensi internal |
"""

    if fin_warn:
        guide += f"""
---

## ⚠️ Perhatian khusus — Block finansial

Bab ini mengandung **{financial_blocks} block finansial** yang datanya bersumber dari Financial Engine.
Block-block ini ditandai `"_protected": true`.

Yang **boleh** diedit di block finansial:
- `"title"` — judul tabel
- `"note"` — catatan bawah tabel

Yang **tidak boleh** diedit:
- `"rows"` — data tabel
- `"headers"` — header kolom
- `"items"` — data metric card
"""

    guide += f"""
---

## Format block yang bisa ditambahkan

### Paragraf baru
```json
{{
  "type": "paragraph",
  "text": "Tulis narasi di sini."
}}
```

### Callout info (kotak informasi)
```json
{{
  "type": "callout_info",
  "text": "Catatan atau informasi tambahan.",
  "display_status": "show"
}}
```

### Bullet list
```json
{{
  "type": "bullet_list",
  "items": [
    "Poin pertama",
    "Poin kedua",
    "Poin ketiga"
  ]
}}
```

---

## Setelah selesai edit

```bash
# Validasi dulu
python validator.py {chapter_id}_editable.json --original {chapter_id}_original.json

# Kalau VALID, import ke pipeline
python importer.py {chapter_id}_editable.json --original {chapter_id}_original.json
```
"""
    return guide


def export_chapter(chapter_id: str):
    sem_file = find_semantic_file(chapter_id)
    if not sem_file:
        print(f"  ✗ {chapter_id}: file tidak ditemukan di {SEMANTIC_DIR}")
        return False

    data    = json.load(open(sem_file))
    chapter = data[0] if isinstance(data, list) else data
    register = REGISTER_MAP.get(chapter_id, "framing")

    blocks          = chapter.get("blocks", [])
    marked_blocks   = mark_protected_blocks(blocks)
    financial_count = sum(1 for b in blocks
                          if b.get("type") in
                          {"table","table_borderless","metric_card_3col","bar_chart_text"})

    # Editable version — dengan _edit_note annotations
    editable = dict(chapter)
    editable["blocks"] = marked_blocks
    editable["_export_metadata"] = {
        "exported_at":    datetime.now().isoformat(),
        "source_file":    sem_file.name,
        "register":       register,
        "edit_note":      "Edit field 'text' bebas. Jangan ubah field bertanda _protected.",
        "import_command": f"python importer.py {chapter_id}_editable.json "
                          f"--original {chapter_id}_original.json",
    }

    # Write editable
    edit_path = OUTPUT_DIR / f"{chapter_id}_editable.json"
    json.dump(editable, open(edit_path, "w"), indent=2, ensure_ascii=False)

    # Write original (read-only reference)
    orig_path = OUTPUT_DIR / f"{chapter_id}_original.json"
    json.dump(chapter, open(orig_path, "w"), indent=2, ensure_ascii=False)

    # Companion guide
    if not args.no_guide:
        guide = generate_editing_guide(
            chapter_id, register, len(blocks), financial_count
        )
        guide_path = OUTPUT_DIR / f"{chapter_id}_EDITING_GUIDE.md"
        guide_path.write_text(guide, encoding="utf-8")
        print(f"  ✓ {chapter_id}: {len(blocks)} blocks → "
              f"{edit_path.name} + guide")
    else:
        print(f"  ✓ {chapter_id}: {len(blocks)} blocks → {edit_path.name}")

    return True


# ── Copy global rules ──────────────────────────────────────────
global_rules = SCRIPT_DIR / "templates/EDITING_RULES_GLOBAL.md"
if global_rules.exists():
    shutil.copy2(global_rules, OUTPUT_DIR / "EDITING_RULES_GLOBAL.md")

# ── Run ───────────────────────────────────────────────────────
print(f"\nExporting to: {OUTPUT_DIR.resolve()}")

ALL_CHAPTERS = [f"bab_{i}" for i in range(1, 10)]

if args.chapter.lower() == "all":
    print("Exporting all chapters...")
    for ch in ALL_CHAPTERS:
        export_chapter(ch)
else:
    export_chapter(args.chapter)

print(f"\nDone. Edit file(s) di {OUTPUT_DIR}, lalu:")
print(f"  python validator.py exports/<bab>_editable.json "
      f"--original exports/<bab>_original.json")
print(f"  python importer.py  exports/<bab>_editable.json "
      f"--original exports/<bab>_original.json")
