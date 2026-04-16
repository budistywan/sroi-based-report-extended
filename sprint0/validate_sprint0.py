"""
Sprint 0 Validator
Memvalidasi semua artefak Sprint 0 sebelum Sprint 1 dimulai.
Gate: semua harus PASS sebelum Financial Engine bisa dijalankan.

Usage:
  python validate_sprint0.py                        # default: ./
  python validate_sprint0.py --base /path/to/dir   # custom path
  BASE_DIR=/path/to/dir python validate_sprint0.py  # env var
"""
import json
import sys
import os
import argparse
from pathlib import Path
import jsonschema

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="Sprint 0 Validator")
parser.add_argument("--base", type=str, default=None,
                    help="Base directory Sprint 0 artifacts (default: env BASE_DIR or script dir)")
args = parser.parse_args()

if args.base:
    BASE = Path(args.base)
elif os.environ.get("BASE_DIR"):
    BASE = Path(os.environ["BASE_DIR"])
else:
    BASE = Path(__file__).parent  # default: same dir as script

print(f"Base directory: {BASE.resolve()}")

ERRORS = []

def load_json(path):
    with open(path) as f:
        return json.load(f)

def check(condition, msg):
    if not condition:
        ERRORS.append(f"  FAIL: {msg}")
        return False
    print(f"  PASS: {msg}")
    return True

def validate_schema(instance, schema, name):
    try:
        jsonschema.validate(instance=instance, schema=schema)
        print(f"  PASS: {name} valid terhadap schema")
        return True
    except jsonschema.ValidationError as e:
        ERRORS.append(f"  FAIL: {name} — {e.message} (path: {list(e.path)})")
        return False

# ── GATE 1: File ada semua ───────────────────────────────
print("\n=== GATE 1: Artefak Sprint 0 ada semua ===")
required_files = [
    "render_contract_v1.json",
    "canonical_json_schema_v1.json",
    "handoff_contracts_v1.json",
    "chapter_outline_schema_v1.json",
    "canonical_esl_v1.json",
    "outline_esl_bab7_v1.json",
]
for f in required_files:
    check((BASE / f).exists(), f"File ada: {f}")

# ── GATE 2: Render Contract ──────────────────────────────
print("\n=== GATE 2: Render Contract ===")
rc = load_json(BASE / "render_contract_v1.json")
check("callout_gap" in rc["supported_block_types"],           "callout_gap ada di supported_block_types")
check("gap_note" in rc["style_hints_accepted"],               "gap_note ada di style_hints_accepted")
check("inference_note" in rc["style_hints_accepted"],         "inference_note ada di style_hints_accepted")
check("callout_gap" in rc["required_fields_per_block"],       "callout_gap punya required_fields")
check("gap_type" in rc["required_fields_per_block"]["callout_gap"], "callout_gap requires gap_type")
check("diagram" in rc["unsupported_block_types"],             "diagram ada di unsupported_block_types")

# ── GATE 3: Canonical JSON Schema ───────────────────────
print("\n=== GATE 3: Canonical JSON Schema ===")
cs = load_json(BASE / "canonical_json_schema_v1.json")
check("sroi_metrics"  in cs["properties"], "sroi_metrics ada di schema")
check("monetization"  in cs["properties"], "monetization ada di schema")
check("ddat_params"   in cs["properties"], "ddat_params ada di schema")
check("ori_rates"     in cs["properties"], "ori_rates ada di schema")
check("data_status"   in cs["definitions"], "data_status enum terdefinisi")
check("display_status" in cs["definitions"], "display_status enum terdefinisi")
for status in ["observed","derived","proxy","pending","under_confirmation","final"]:
    check(status in cs["definitions"]["data_status"]["enum"],
          f"data_status includes '{status}'")

# ── GATE 4: Handoff Contracts ────────────────────────────
print("\n=== GATE 4: Handoff Contracts ===")
hc = load_json(BASE / "handoff_contracts_v1.json")
for contract in ["A","B","C","D","E","F"]:
    check(contract in hc["contracts"], f"Handoff {contract} ada")
check("calc_audit_log"   in str(hc["contracts"]["B"]), "Handoff B punya calc_audit_log")
check("renderer_ready"   in str(hc["contracts"]["F"]), "Handoff F punya renderer_ready")
check("reference_outline" in str(hc["contracts"]["F"]), "Handoff F punya reference_outline")
check("qa_render_signals" in str(hc["contracts"]["F"]), "Handoff F punya qa_render_signals")

# ── GATE 5: Chapter Outline Schema ──────────────────────
print("\n=== GATE 5: Chapter Outline Schema ===")
os_ = load_json(BASE / "chapter_outline_schema_v1.json")
check(os_["type"] == "array", "Outline schema adalah array")
props = os_["items"]["properties"]
check("core_claim"       in props, "core_claim ada di outline schema")
check("argument_points"  in props, "argument_points ada di outline schema")
check("known_gaps"       in props, "known_gaps ada di outline schema")
check("builder_mode"     in props, "builder_mode ada di outline schema")
ap_item = props["argument_points"]["items"]["properties"]
check("evidence_refs" in ap_item, "argument_point punya evidence_refs")
check("status"        in ap_item, "argument_point punya status")
check("note"          in ap_item, "argument_point punya note")

# ── GATE 6: Canonical JSON ESL ──────────────────────────
print("\n=== GATE 6: Canonical JSON ESL ===")
if (BASE / "canonical_esl_v1.json").exists():
    esl = load_json(BASE / "canonical_esl_v1.json")
    check(esl.get("case_id") is not None, "case_id ada")
    check(esl.get("program_identity", {}).get("program_code") == "ESL", "program_code = ESL")
    check(len(esl.get("investment",   [])) > 0, "investment tidak kosong")
    check(len(esl.get("monetization", [])) > 0, "monetization tidak kosong")
    check(len(esl.get("ddat_params",  {})) > 0, "ddat_params tidak kosong")
    check(len(esl.get("ori_rates",    {})) > 0, "ori_rates tidak kosong")
    check(esl.get("sroi_metrics", {}).get("status") == "not_calculated",
          "sroi_metrics.status = not_calculated (siap untuk Financial Engine)")
    first_mon = esl.get("monetization", [{}])[0]
    check("data_status"    in first_mon,
          f"monetization {first_mon.get('monetization_id','')} punya data_status")
    check("display_status" in first_mon,
          f"monetization {first_mon.get('monetization_id','')} punya display_status")
    validate_schema(esl, cs, "canonical_esl_v1.json")
else:
    ERRORS.append("  FAIL: canonical_esl_v1.json belum ada")

# ── GATE 7: Outline ESL Bab 7 ───────────────────────────
print("\n=== GATE 7: Outline ESL Bab 7 ===")
if (BASE / "outline_esl_bab7_v1.json").exists():
    raw = load_json(BASE / "outline_esl_bab7_v1.json")
    outline = raw if isinstance(raw, list) else [raw]
    bab7 = next((b for b in outline if b.get("chapter_id") == "bab_7"), None)
    check(bab7 is not None, "bab_7 ditemukan di outline")
    if bab7:
        check(bab7.get("core_claim") not in [None, ""],  "core_claim tidak kosong")
        check(bab7.get("core_claim_ref") is not None,     "core_claim_ref ada")
        check(len(bab7.get("argument_points", [])) >= 3,  "minimal 3 argument_points")
        for ap in bab7.get("argument_points", []):
            if ap.get("status") == "supported":
                check(len(ap.get("evidence_refs", [])) >= 1,
                      f"Point {ap.get('label','')} supported → evidence_refs tidak kosong")
            if ap.get("status") in ["pending","inferred","partial"]:
                check(ap.get("note") not in [None, ""],
                      f"Point {ap.get('label','')} status={ap.get('status','')} → note wajib ada")
        if bab7.get("coverage_status") in ["weak","missing"]:
            check(len(bab7.get("known_gaps", [])) >= 1,
                  "Bab weak/missing harus punya known_gaps")
    validate_schema(outline, os_, "outline_esl_bab7_v1.json")
else:
    ERRORS.append("  FAIL: outline_esl_bab7_v1.json belum ada")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 0 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS:
        print(e)
    print("\nSprint 1 tidak boleh dimulai sebelum semua gate PASS.")
    sys.exit(1)
else:
    print("SPRINT 0 GATE: ALL PASS")
    print("Sprint 1 — Financial Calculation Engine boleh dimulai.")
    sys.exit(0)
