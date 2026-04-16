"""
style_profile_importer.py — Sprint 14A
Menerima file style profile yang sudah diedit user,
memvalidasi terhadap editor contract, dan menghasilkan
style_profile_reviewed.json sebagai ground truth.

Usage:
  python style_profile_importer.py --input style_profile_edited.json
  python style_profile_importer.py --input /p/edited.json --output /p/reviewed.json
  python style_profile_importer.py --demo   # demo mode: generate reviewed dari v1 tanpa edit
"""

import json, sys, argparse, copy
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--input",  default=None, help="Path ke file hasil edit user")
parser.add_argument("--output", default=None, help="Path output reviewed profile")
parser.add_argument("--demo",   action="store_true", help="Demo: approve v1 tanpa perubahan")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
V1_PATH      = SCRIPT_DIR / "style_profile_v1.json"
CONTRACT_PATH= SCRIPT_DIR / "style_profile_editor_contract.json"
OUTPUT_PATH  = Path(args.output) if args.output \
    else SCRIPT_DIR / "style_profile_reviewed.json"

for f in [V1_PATH, CONTRACT_PATH]:
    if not f.exists():
        print(f"FAIL: {f} tidak ditemukan"); sys.exit(1)

v1       = json.load(open(V1_PATH))
contract = json.load(open(CONTRACT_PATH))

EDITABLE     = set(contract["editable_fields"])
NON_EDITABLE = set(contract["non_editable_fields"])
FIELD_C      = contract.get("field_contracts", {})
HEDGING_ENUM = FIELD_C.get("hedging_profile", {}).get("level_enum", [])

ERRORS   = []
WARNINGS = []
DELTA    = []

def error(msg):   ERRORS.append(msg);   print(f"  ✕ {msg}")
def warn(msg):    WARNINGS.append(msg); print(f"  ⚠ {msg}")
def ok(msg):      print(f"  ✓ {msg}")


def compute_delta(original: dict, edited: dict, path: str = "") -> list:
    """Hitung delta antara dua dict secara rekursif."""
    changes = []
    all_keys = set(original.keys()) | set(edited.keys())
    for k in sorted(all_keys):
        full_path = f"{path}.{k}" if path else k
        if k not in original:
            changes.append({"field": full_path, "change": "added", "new_value": edited[k]})
        elif k not in edited:
            changes.append({"field": full_path, "change": "removed"})
        elif original[k] != edited[k]:
            if isinstance(original[k], dict) and isinstance(edited[k], dict):
                changes.extend(compute_delta(original[k], edited[k], full_path))
            else:
                changes.append({
                    "field":     full_path,
                    "change":    "modified",
                    "old_value": original[k],
                    "new_value": edited[k],
                })
    return changes


def validate_edited(edited: dict) -> bool:
    """Validasi file hasil edit terhadap contract. Return True jika valid."""
    print("\n--- Validation ---")

    # 1. Non-editable fields tidak boleh berubah
    for field in NON_EDITABLE:
        if field in edited and edited[field] != v1.get(field):
            error(f"Non-editable field '{field}' diubah — tidak diizinkan")

    # 2. Tidak ada field baru di luar editable + non-editable
    all_known = EDITABLE | NON_EDITABLE
    for field in edited:
        if field not in all_known:
            error(f"Unknown field '{field}' ditemukan — bukan bagian dari contract")

    # 3. Tone: tidak boleh ada key baru
    if "tone" in edited:
        allowed_tone_keys = set(FIELD_C.get("tone", {}).get("allowed_keys", []))
        for k in edited["tone"]:
            if k not in allowed_tone_keys:
                error(f"tone.{k}: key baru tidak diizinkan di field tone")
            elif not isinstance(edited["tone"][k], bool):
                error(f"tone.{k}: harus boolean, dapat: {type(edited['tone'][k])}")

    # 4. Hedging level harus dari enum
    if "hedging_profile" in edited:
        level = edited["hedging_profile"].get("level")
        if level and level not in HEDGING_ENUM:
            error(f"hedging_profile.level '{level}' tidak valid — harus salah satu dari {HEDGING_ENUM}")
        # preferred/avoided markers harus list of strings
        for field in ["preferred_markers","avoided_markers"]:
            val = edited["hedging_profile"].get(field)
            if val is not None:
                if not isinstance(val, list):
                    error(f"hedging_profile.{field} harus array, dapat: {type(val)}")
                elif not all(isinstance(m, str) for m in val):
                    error(f"hedging_profile.{field} harus array of strings")
                else:
                    ok(f"hedging_profile.{field}: {len(val)} items")

    # 5. notes harus array of strings
    if "notes" in edited:
        if not isinstance(edited["notes"], list):
            error("notes harus array of strings")
        elif not all(isinstance(n, str) for n in edited["notes"]):
            error("notes: semua item harus string")
        else:
            ok(f"notes: {len(edited['notes'])} items")

    # 6. preferred_opening_variations harus array of strings
    var_pref = edited.get("variation_preferences", {})
    pov = var_pref.get("preferred_opening_variations")
    if pov is not None:
        if not isinstance(pov, list) or not all(isinstance(s, str) for s in pov):
            error("variation_preferences.preferred_opening_variations harus array of strings")
        else:
            ok(f"preferred_opening_variations: {len(pov)} items")

    return len(ERRORS) == 0


# ══════════════════════════════════════════════════════════════
# DEMO MODE — approve v1 tanpa perubahan
# ══════════════════════════════════════════════════════════════
if args.demo:
    print("DEMO MODE: menghasilkan reviewed profile dari v1 tanpa perubahan")
    edited_input = copy.deepcopy(v1)
    input_path   = V1_PATH
else:
    if not args.input:
        print("FAIL: --input wajib (atau gunakan --demo)")
        sys.exit(1)
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"FAIL: {input_path} tidak ditemukan")
        sys.exit(1)
    print(f"Input  : {input_path.resolve()}")
    edited_input = json.load(open(input_path))

print(f"Output : {OUTPUT_PATH.resolve()}")

# Validate
is_valid = validate_edited(edited_input)

if not is_valid:
    print(f"\n{'='*55}")
    print(f"IMPORT FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(f"  ✕ {e}")
    print("\nPerbaiki error di atas lalu jalankan importer kembali.")
    sys.exit(1)

# Compute delta
delta = compute_delta(v1, edited_input)

if delta:
    print(f"\n  {len(delta)} field berubah dari v1:")
    for d in delta:
        print(f"    [{d['change']}] {d['field']}")
else:
    print("\n  Tidak ada perubahan dari v1 (demo/approve tanpa edit)")

# Build reviewed profile
reviewed = copy.deepcopy(edited_input)
reviewed["profile_id"]        = "style_profile_reviewed"
reviewed["parent_profile_id"] = v1["profile_id"]
reviewed["reviewed_by"]       = "user"
reviewed["review_timestamp"]  = datetime.now().isoformat()
reviewed["changes_summary"]   = delta
reviewed["import_source"]     = str(input_path.resolve()) if not args.demo else "demo_mode"

# Write
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
json.dump(reviewed, open(OUTPUT_PATH,"w"), indent=2, ensure_ascii=False)

print(f"\n{'='*55}")
print("IMPORT COMPLETE")
print(f"  Changes : {len(delta)}")
print(f"  Output  : {OUTPUT_PATH.resolve()}")
print(f"  Status  : style_profile_reviewed.json siap sebagai ground truth")
if WARNINGS:
    print(f"  Warnings: {len(WARNINGS)}")
    for w in WARNINGS: print(f"    ⚠ {w}")
print("="*55)
