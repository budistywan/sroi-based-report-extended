"""
validate_review_contract.py — Sprint 11
Gate 1–2: Review contract valid + persistence valid.

Usage:
  python validate_review_contract.py
  python validate_review_contract.py --sprint11-dir /path/sprint11/
"""
import json, sys, os, argparse
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--sprint11-dir", default=None, dest="dir11")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR11      = Path(args.dir11) if args.dir11 \
    else Path(os.environ.get("SPRINT11_DIR", SCRIPT_DIR))

print(f"Sprint11 dir: {DIR11.resolve()}")

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 1: Review contract valid ────────────────────────────
print("\n=== GATE 1: Review contract valid ===")
contract_path = DIR11 / "review_contract_v1.json"
check(contract_path.exists(), "review_contract_v1.json ada")
if contract_path.exists():
    c = json.load(open(contract_path))
    check("decision_enum"        in c,   "decision_enum ada")
    check("change_types"         in c,   "change_types ada")
    check("review_record_schema" in c,   "review_record_schema ada")
    check("pipeline_gates"       in c,   "pipeline_gates ada")

    # Cek decision enum benar
    valid_decisions = {"approve","approve_with_notes","revise","defer"}
    dec_enum = set(c.get("decision_enum",[]))
    check(dec_enum == valid_decisions,
          f"decision_enum = {valid_decisions} (dapat: {dec_enum})")

    # Cek change_types
    REQUIRED_CHANGES = {"replace_value","append_note","set_status","mark_as_gap",
                        "request_regeneration","approve_without_change"}
    ct_keys = set(c.get("change_types",{}).keys())
    missing = REQUIRED_CHANGES - ct_keys
    check(len(missing) == 0, f"Semua change_types ada (missing: {missing})")

    # Cek pipeline gates
    gates = c.get("pipeline_gates",{})
    check("review_point_a" in gates, "pipeline_gate review_point_a ada")
    check("review_point_b" in gates, "pipeline_gate review_point_b ada")

schema_path = DIR11 / "review_schema.json"
check(schema_path.exists(), "review_schema.json ada")
if schema_path.exists():
    s = json.load(open(schema_path))
    check(s.get("type") == "object",            "schema type = object")
    check("required" in s,                       "schema required ada")
    check("review_id" in s.get("required",[]),   "review_id di required")
    check("decision"  in s.get("required",[]),   "decision di required")

# ── GATE 2: Review persistence valid ─────────────────────────
print("\n=== GATE 2: Review persistence valid ===")

# Cek decisions files ada
for fname, label in [
    ("canonical_review_decisions.json", "canonical decisions"),
    ("gap_review_decisions.json",       "gap decisions"),
    ("outline_review_decisions_bab_7.json", "outline decisions"),
]:
    check((DIR11 / fname).exists(), f"{label} tersimpan ({fname})")

# Cek reviewed output files ada
for fname, label in [
    ("canonical_reviewed.json",             "canonical reviewed"),
    ("gap_matrix_reviewed.json",            "gap matrix reviewed"),
    ("chapter_outline_reviewed_bab_7.json", "outline reviewed"),
]:
    check((DIR11 / fname).exists(), f"{label} tersimpan ({fname})")

# Cek reviewed canonical punya _review_metadata
rev_can_path = DIR11 / "canonical_reviewed.json"
if rev_can_path.exists():
    rc = json.load(open(rev_can_path))
    check("_review_metadata" in rc,                   "canonical_reviewed punya _review_metadata")
    check(rc.get("_review_metadata",{}).get("reviewed_at"), "reviewed_at tercatat")

# Cek outline reviewed punya _review_metadata
rev_out_path = DIR11 / "chapter_outline_reviewed_bab_7.json"
if rev_out_path.exists():
    ro_data = json.load(open(rev_out_path))
    ro = ro_data[0] if isinstance(ro_data, list) else ro_data
    check("_review_metadata" in ro, "outline_reviewed punya _review_metadata")

# ── GATE 3: Decisions schema-valid ───────────────────────────
print("\n=== GATE 3: Decisions schema-valid ===")
REQUIRED_DECISION_FIELDS = ["review_id","review_target_type","decision","reviewer","timestamp"]
for fname in ["canonical_review_decisions.json","gap_review_decisions.json",
              "outline_review_decisions_bab_7.json"]:
    fpath = DIR11 / fname
    if fpath.exists():
        d = json.load(open(fpath))
        for field in REQUIRED_DECISION_FIELDS:
            check(field in d, f"{fname}: field '{field}' ada")
        check(d.get("decision") in ["approve","approve_with_notes","revise","defer",""],
              f"{fname}: decision value valid")

# ── HASIL ────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"REVIEW CONTRACT GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("REVIEW CONTRACT GATE: ALL PASS")
    print("Sprint 11 contract dan persistence valid.")
    sys.exit(0)
