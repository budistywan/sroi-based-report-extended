"""
importer.py — Semantic Editor
Import chapter semantic JSON yang sudah diedit user
kembali ke pipeline, setelah melewati validator.

Output:
  - chapter_semantic_{bab}_enriched.json  → siap dirender
  - import_log_{bab}.json                 → audit trail

Usage:
  python importer.py exports/bab_4_editable.json
  python importer.py exports/bab_4_editable.json --original exports/bab_4_original.json
  python importer.py exports/bab_4_editable.json --render   # langsung render ke .docx
"""

import json, sys, argparse, subprocess
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser(description="Semantic JSON Importer")
parser.add_argument("edited",
                    help="Path ke file hasil edit user")
parser.add_argument("--original", "-o", default=None,
                    help="Path ke original (untuk diff + substance lock)")
parser.add_argument("--output-dir",     default=None,
                    help="Direktori output pipeline (default: output/esl/work/)")
parser.add_argument("--render",         action="store_true",
                    help="Langsung render ke .docx setelah import berhasil")
parser.add_argument("--force",          action="store_true",
                    help="Import meski ada warnings (tidak untuk errors)")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
VALIDATOR    = SCRIPT_DIR / "validator.py"
RENDERER     = SCRIPT_DIR.parent / "sprint4/renderer.js"

OUTPUT_DIR   = Path(args.output_dir) if args.output_dir else next((
    p for p in [
        SCRIPT_DIR.parent / "output/esl/work",
        SCRIPT_DIR.parent / "sprint9/output/esl/work",
    ] if p.exists()
), SCRIPT_DIR / "imports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PYTHON = sys.executable

edited_path = Path(args.edited)
if not edited_path.exists():
    print(f"FAIL: {edited_path} tidak ditemukan")
    sys.exit(1)


# ── STEP 1: Validasi dulu ─────────────────────────────────────
print(f"\n{'='*55}")
print(f"SEMANTIC IMPORTER")
print(f"  Input   : {edited_path.name}")
print(f"  Output  : {OUTPUT_DIR.resolve()}")
print(f"{'='*55}")

print("\n[1/3] Menjalankan validator...")

validator_cmd = [PYTHON, str(VALIDATOR), str(edited_path)]
if args.original:
    validator_cmd += ["--original", args.original]

r = subprocess.run(validator_cmd, capture_output=True, text=True)
print(r.stdout)

if r.returncode != 0:
    print("IMPORT DIBATALKAN — perbaiki errors di atas dulu.")
    print(f"Jalankan: python validator.py {edited_path} "
          + (f"--original {args.original}" if args.original else ""))
    sys.exit(1)

# Cek ada warning tapi tidak --force
if "Warning" in r.stdout and not args.force:
    print("Ada warnings. Gunakan --force untuk import meski ada warnings.")
    print("Atau perbaiki warnings dulu untuk hasil terbaik.")
    sys.exit(1)


# ── STEP 2: Bersihkan annotation fields (_edit_note, _protected, dll) ──
print("[2/3] Membersihkan annotation fields...")

data    = json.load(open(edited_path, encoding="utf-8"))
chapter = data[0] if isinstance(data, list) else data

# Hapus _export_metadata (tidak dibutuhkan pipeline)
chapter.pop("_export_metadata", None)

# Bersihkan annotation di setiap block
cleaned_blocks = []
for block in chapter.get("blocks", []):
    clean = {k: v for k, v in block.items()
             if not k.startswith("_")}
    cleaned_blocks.append(clean)

chapter["blocks"] = cleaned_blocks

# Update metadata chapter
chapter["last_edited_at"] = datetime.now().isoformat()
chapter["edit_source"]    = edited_path.name

# Hitung stats
block_count = len(cleaned_blocks)
print(f"   {block_count} blocks dibersihkan dari annotations")


# ── STEP 3: Tulis output ──────────────────────────────────────
print("[3/3] Menulis output...")

chapter_id = chapter.get("chapter_id", "bab_unknown")

# Output enriched — ini yang dipakai pipeline
out_path = OUTPUT_DIR / f"chapter_semantic_{chapter_id}_enriched.json"
json.dump([chapter], open(out_path, "w"), indent=2, ensure_ascii=False)
print(f"   Enriched: {out_path}")

# Audit log
if args.original and Path(args.original).exists():
    orig = json.load(open(args.original))
    orig_ch = orig[0] if isinstance(orig, list) else orig
    orig_blocks = orig_ch.get("blocks", [])

    added   = block_count - len(orig_blocks)
    import_log = {
        "import_id":        f"import_{chapter_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "chapter_id":       chapter_id,
        "imported_at":      datetime.now().isoformat(),
        "source_file":      edited_path.name,
        "original_file":    args.original,
        "blocks_original":  len(orig_blocks),
        "blocks_imported":  block_count,
        "blocks_delta":     added,
        "validation_passed": True,
        "forced":           args.force,
        "output_file":      str(out_path),
    }
    log_path = OUTPUT_DIR / f"import_log_{chapter_id}.json"
    json.dump(import_log, open(log_path, "w"), indent=2, ensure_ascii=False)
    print(f"   Log     : {log_path}")

    delta_str = f"+{added}" if added >= 0 else str(added)
    print(f"   Delta   : {delta_str} blocks dari original")


# ── Optional: Render langsung ─────────────────────────────────
if args.render:
    print(f"\n[Bonus] Rendering ke .docx...")
    if not RENDERER.exists():
        print(f"  WARN: renderer.js tidak ditemukan di {RENDERER}")
    else:
        docx_out = OUTPUT_DIR / f"{chapter_id}_enriched.docx"
        r2 = subprocess.run(
            ["node", str(RENDERER),
             "--semantic", str(out_path),
             "--output",   str(docx_out)],
            capture_output=True, text=True
        )
        if r2.returncode == 0 and docx_out.exists():
            print(f"  Docx    : {docx_out} ({docx_out.stat().st_size:,} bytes)")
        else:
            print(f"  WARN: render gagal — {r2.stderr[:80]}")

print(f"\n{'='*55}")
print(f"IMPORT COMPLETE — {chapter_id}")
print(f"  File siap dipakai pipeline: {out_path.name}")
print(f"{'='*55}")
