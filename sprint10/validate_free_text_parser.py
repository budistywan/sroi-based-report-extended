"""
Sprint 10 Gate Validator — free_text_parser (Gate C)

Usage:
  python validate_free_text_parser.py
  python validate_free_text_parser.py --parsed /path/parsed_free_text_example.json
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--parsed", default=None)
args = parser.parse_args()

SCRIPT_DIR  = Path(__file__).parent
PARSED_FILE = Path(args.parsed) if args.parsed \
    else Path(os.environ.get("PARSED_FILE", SCRIPT_DIR / "parsed_free_text_example.json"))

print(f"Parsed: {PARSED_FILE.resolve()}")
if not PARSED_FILE.exists():
    print(f"FAIL: {PARSED_FILE} tidak ditemukan"); sys.exit(1)

data   = json.load(open(PARSED_FILE))
ERRORS = []

def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

items = data.get("items", [])
item_types = {it["item_type"] for it in items}

# ── GATE C1: Struktur output ────────────────────────────────
print("\n=== GATE C1: Struktur output ===")
check(data.get("source_type") == "free_text",    "source_type = free_text")
check(isinstance(items, list) and len(items) > 0,"items tidak kosong")
check("stats" in data,                           "stats ada")
check(data["stats"].get("items_extracted", 0) > 0,"items_extracted > 0")

# ── GATE C2: Item typing ────────────────────────────────────
print("\n=== GATE C2: Item typing ===")
VALID_TYPES = {"fact_candidate","instruction","interpretation_candidate","limitation_note"}
invalid_types = item_types - VALID_TYPES
check(len(invalid_types) == 0,
      f"Semua item_type valid (invalid: {invalid_types})")

for req_type in ["fact_candidate", "instruction", "limitation_note"]:
    present = any(it["item_type"] == req_type for it in items)
    check(present, f"Ada minimal 1 item tipe '{req_type}'")

# ── GATE C3: Number preservation ────────────────────────────
print("\n=== GATE C3: Number preservation ===")
items_with_numbers = [it for it in items if it.get("numbers")]
check(len(items_with_numbers) > 0,
      f"Ada items dengan angka terekstrak (dapat: {len(items_with_numbers)})")

# Semua item tidak harus jadi final fact
non_fact = [it for it in items if it["item_type"] != "fact_candidate"]
check(len(non_fact) > 0,
      f"Tidak semua item menjadi fact_candidate (non-fact: {len(non_fact)})")

# ── GATE C4: Terminology capture ────────────────────────────
print("\n=== GATE C4: Terminology capture ===")
items_with_terms = [it for it in items if it.get("terminology")]
terms_found = set()
for it in items_with_terms:
    for t in it.get("terminology", []):
        terms_found.add(t.get("semantic_tag",""))

check("observed_direct_return" in terms_found or
      any("observed" in str(it).lower() for it in items),
      "Terminologi 'Observed direct return' terdeteksi")
check("blended_sroi" in terms_found or
      any("blended" in str(it).lower() for it in items),
      "Terminologi 'Blended SROI' terdeteksi")

# ── GATE C5: Confidence discipline ──────────────────────────
print("\n=== GATE C5: Confidence discipline ===")
items_with_confidence = [it for it in items if "confidence" in it]
check(len(items_with_confidence) == len(items),
      f"Semua items punya confidence ({len(items_with_confidence)}/{len(items)})")

# Confidence harus antara 0 dan 1
invalid_conf = [it for it in items if not (0 <= it.get("confidence",0) <= 1)]
check(len(invalid_conf) == 0,
      f"Semua confidence dalam range [0,1] (invalid: {len(invalid_conf)})")

# ── GATE C6: Raw text preserved ─────────────────────────────
print("\n=== GATE C6: Raw text preserved ===")
items_with_text = [it for it in items if it.get("text")]
check(len(items_with_text) == len(items),
      f"Semua items punya text asli ({len(items_with_text)}/{len(items)})")

# ── GATE C7: Limitation tidak jadi fact ─────────────────────
print("\n=== GATE C7: Limitation notes dipisahkan ===")
limitation_items = [it for it in items if it["item_type"] == "limitation_note"]
check(len(limitation_items) > 0,
      f"Ada limitation_note items (dapat: {len(limitation_items)})")

# Pastikan limitation note tidak punya confidence = 1.0
high_conf_limitations = [
    it for it in limitation_items if it.get("confidence",0) >= 0.99
]
check(len(high_conf_limitations) == 0,
      f"Tidak ada limitation_note dengan confidence = 1.0")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"FREE TEXT PARSER GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("FREE TEXT PARSER GATE: ALL PASS")
    by_type = data["stats"].get("by_type", {})
    print(f"  {len(items)} items extracted")
    for t, n in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"    {t:<30} × {n}")
    sys.exit(0)
