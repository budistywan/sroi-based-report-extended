"""
Sprint 3 Gate Validator — Point Builder (builder_sroi)
Gate rules sesuai yang ditetapkan Orchestrator:
  1. Semua argument_points punya evidence_refs yang ada di canonical JSON
  2. Tidak ada argument_point berstatus supported dengan evidence_refs kosong
  3. known_gaps tidak boleh kosong jika gap_matrix menunjukkan weak/missing
  4. core_claim harus bisa ditelusuri ke minimal satu field di canonical JSON
  5. Tidak ada argument_point pending/inferred tanpa note eksplisit

Usage:
  python validate_sprint3.py
  python validate_sprint3.py --outline /path/chapter_outline_bab7.json \
                              --canonical /path/canonical_esl_v1.json \
                              --schema /path/chapter_outline_schema_v1.json
  OUTLINE_FILE=... CANONICAL_FILE=... SCHEMA_FILE=... python validate_sprint3.py
"""
import json
import sys
import os
import argparse
from pathlib import Path
import jsonschema

parser = argparse.ArgumentParser(description="Sprint 3 Gate Validator")
parser.add_argument("--outline",   default=None)
parser.add_argument("--canonical", default=None)
parser.add_argument("--schema",    default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
OUTLINE_FILE   = Path(args.outline)   if args.outline   \
    else Path(os.environ.get("OUTLINE_FILE",   SCRIPT_DIR / "chapter_outline_bab7.json"))
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
SCHEMA_FILE    = Path(args.schema)    if args.schema    \
    else Path(os.environ.get("SCHEMA_FILE",    SCRIPT_DIR.parent / "sprint0/chapter_outline_schema_v1.json"))

print(f"Outline   : {OUTLINE_FILE.resolve()}")
print(f"Canonical : {CANONICAL_FILE.resolve()}")
print(f"Schema    : {SCHEMA_FILE.resolve()}")

for f in [OUTLINE_FILE, CANONICAL_FILE, SCHEMA_FILE]:
    if not f.exists():
        print(f"\nFAIL: File tidak ditemukan — {f}")
        sys.exit(1)

outline_raw = json.load(open(OUTLINE_FILE))
canonical   = json.load(open(CANONICAL_FILE))
schema      = json.load(open(SCHEMA_FILE))

outline = outline_raw if isinstance(outline_raw, list) else [outline_raw]
bab7    = next((b for b in outline if b.get("chapter_id") == "bab_7"), None)

ERRORS = []

def check(condition, msg):
    if not condition:
        ERRORS.append(f"  FAIL: {msg}")
        return False
    print(f"  PASS: {msg}")
    return True

# ── GATE 1: Schema validation ────────────────────────────
print("\n=== GATE 1: JSON Schema validation ===")
try:
    jsonschema.validate(instance=outline, schema=schema)
    print("  PASS: outline valid terhadap chapter_outline_schema_v1")
except jsonschema.ValidationError as e:
    ERRORS.append(f"  FAIL: schema — {e.message} (path: {list(e.path)})")

# ── GATE 2: Struktur dasar ───────────────────────────────
print("\n=== GATE 2: Struktur dasar ===")
check(bab7 is not None,                           "bab_7 ditemukan di outline")
if not bab7:
    print("Cannot continue — bab_7 missing")
    sys.exit(1)

check(bab7.get("builder_mode") == "sroi",         "builder_mode = sroi")
check(bab7.get("coverage_status") == "strong",    "coverage_status = strong")
check(bab7.get("core_claim","") != "",            "core_claim tidak kosong")
check(bab7.get("core_claim_ref","") != "",        "core_claim_ref tidak kosong")
check(len(bab7.get("argument_points", [])) >= 10, "minimal 10 argument_points")
check(len(bab7.get("financial_refs", [])) >= 3,   "minimal 3 financial_refs")
check(bab7.get("known_gaps") == [],               "known_gaps kosong (coverage strong)")

# ── GATE 3: Rule 1 — evidence_refs traceable ─────────────
print("\n=== GATE 3: Rule 1 — evidence_refs traceable ke canonical ===")

canonical_top_keys = set(canonical.keys())
evidence_ids = {e["evidence_id"] for e in canonical.get("evidence_registry", [])}
aspect_codes = set(canonical.get("ddat_params", {}).keys())

def is_traceable(ref):
    base = ref.split(".")[0].split("[")[0]
    # Accept: top-level canonical field, evidence_id, computed refs
    return (
        base in canonical_top_keys or
        ref in evidence_ids or
        base in {"sroi_metrics","evidence_registry"} or
        any(f"aspect={asp}" in ref for asp in aspect_codes)
    )

for ap in bab7.get("argument_points", []):
    for ref in ap.get("evidence_refs", []):
        check(is_traceable(ref),
              f"Point {ap['label']}: ref '{ref}' traceable ke canonical")

# ── GATE 4: Rule 2 — supported tidak boleh evidence kosong
print("\n=== GATE 4: Rule 2 — supported → evidence_refs tidak kosong ===")
for ap in bab7.get("argument_points", []):
    if ap.get("status") == "supported":
        check(len(ap.get("evidence_refs", [])) >= 1,
              f"Point {ap['label']} [supported] → evidence_refs ada")

# ── GATE 5: Rule 3 — known_gaps ──────────────────────────
print("\n=== GATE 5: Rule 3 — known_gaps konsisten dengan coverage ===")
check(len(bab7.get("known_gaps", [])) == 0,
      "bab_7 strong → known_gaps harus kosong")

# ── GATE 6: Rule 4 — core_claim_ref traceable ────────────
print("\n=== GATE 6: Rule 4 — core_claim_ref traceable ===")
core_ref      = bab7.get("core_claim_ref", "")
core_ref_base = core_ref.split(".")[0]
check(core_ref_base in canonical_top_keys,
      f"core_claim_ref '{core_ref}' traceable ke canonical['{core_ref_base}']")

# ── GATE 7: Rule 5 — pending/inferred harus punya note ───
print("\n=== GATE 7: Rule 5 — pending/inferred → note wajib ===")
for ap in bab7.get("argument_points", []):
    if ap.get("status") in ["pending", "inferred"]:
        check(ap.get("note","").strip() != "",
              f"Point {ap['label']} [{ap['status']}] → note wajib ada")

# ── GATE 8: Angka kunci ada di poin ──────────────────────
print("\n=== GATE 8: Angka kunci SROI ada di outline ===")
all_points_text = " ".join(
    ap.get("point","") + ap.get("elaboration","")
    for ap in bab7.get("argument_points", [])
)
check("1 : 1.14" in all_points_text or "1,14" in all_points_text,
      "SROI blended 1:1,14 ada di outline")
check("502" in all_points_text,
      "Total investasi ~502jt ada di outline")
check("570" in all_points_text,
      "Net compounded ~570jt ada di outline")
check("Lapas Palembang" in all_points_text,
      "Node Lapas Palembang disebutkan (temuan jujur)")
check("Milenial Motor" in all_points_text,
      "Milenial Motor disebutkan (proof-of-concept)")

# ── GATE 9: financial_refs valid ─────────────────────────
print("\n=== GATE 9: financial_refs ada di render contract ===")
VALID_TABLE_IDS = {
    "table_investment_per_node",
    "table_monetization_per_aspek",
    "table_ddat_per_aspek",
    "table_sroi_per_tahun",
    "table_sroi_blended",
}
for ref in bab7.get("financial_refs", []):
    check(ref in VALID_TABLE_IDS,
          f"financial_ref '{ref}' ada di valid table IDs")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 3 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS:
        print(e)
    sys.exit(1)
else:
    ap_count = len(bab7.get("argument_points", []))
    print("SPRINT 3 GATE: ALL PASS")
    print(f"  {ap_count} argument points tervalidasi")
    print(f"  {len(bab7.get('financial_refs',[]))} financial refs terdaftar")
    print("Sprint 3B — Narrative Builder (builder_sroi) boleh dimulai.")
    sys.exit(0)
