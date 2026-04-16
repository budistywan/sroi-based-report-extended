"""
validate_enrichment_engine.py — Sprint 12 Gates 3-5
Validasi enrichment engine output: suggestions + no fact override + reviewable.

Usage:
  python validate_enrichment_engine.py
  python validate_enrichment_engine.py --dir /path/sprint12/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR12      = Path(args.dir) if args.dir else SCRIPT_DIR
DIR0       = DIR12.parent / "sprint0"

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 3: Enrichment engine works ──────────────────────────
print("\n=== GATE 3: Enrichment engine output ===")
can_enr = DIR12 / "canonical_enriched.json"
out_sug = DIR12 / "outline_enrichment_suggestions.json"
gap_sug = DIR12 / "gap_aware_suggestions.json"

check(can_enr.exists(), "canonical_enriched.json ada")
check(out_sug.exists(), "outline_enrichment_suggestions.json ada")
check(gap_sug.exists(), "gap_aware_suggestions.json ada")

if can_enr.exists():
    ce = json.load(open(can_enr))
    suggestions = ce.get("_enrichment_suggestions",[])
    meta        = ce.get("_enrichment_metadata",{})

    check(len(suggestions) > 0, f"Ada suggestions ({len(suggestions)})")
    check(meta.get("facts_preserved") is True, "facts_preserved = True")

    # Cek setiap suggestion punya fields wajib
    for s in suggestions:
        check("suggestion_type" in s, f"suggestion_type ada: {s.get('rule_id','?')}")
        check("confidence"      in s, f"confidence ada: {s.get('rule_id','?')}")
        check("source"          in s, f"source ada: {s.get('rule_id','?')}")
        check(0 < s.get("confidence",0) <= 1.0,
              f"confidence valid [0,1]: {s.get('confidence','?')}")

    # Cek categories cover key areas
    categories = {s.get("category","") for s in suggestions}
    for req_cat in ["caution","terminology"]:
        check(req_cat in categories, f"Category '{req_cat}' ada dalam suggestions")

# ── GATE 4: No fact override ──────────────────────────────────
print("\n=== GATE 4: No fact override ===")
if can_enr.exists() and (DIR0 / "canonical_esl_v1.json").exists():
    ce  = json.load(open(can_enr))
    orig = json.load(open(DIR0 / "canonical_esl_v1.json"))

    CORE_FIELDS = ["program_identity","program_positioning","investment",
                   "monetization","ddat_params","ori_rates","sroi_metrics",
                   "activities","outcomes","stakeholders"]

    for field in CORE_FIELDS:
        orig_val = orig.get(field)
        enr_val  = ce.get(field)
        if orig_val is not None:
            check(orig_val == enr_val,
                  f"Field '{field}' tidak berubah setelah enrichment")

    # Enrichment hanya ada di _enrichment_* keys
    enrichment_keys = [k for k in ce.keys() if k.startswith("_enrichment")]
    check(len(enrichment_keys) >= 1, f"Enrichment tersimpan di _enrichment_* keys ({enrichment_keys})")

    # Tidak ada key baru yang bukan _enrichment_*
    orig_keys = set(orig.keys())
    enr_keys  = set(ce.keys())
    new_keys  = enr_keys - orig_keys - {"_enrichment_metadata","_enrichment_suggestions"}
    check(len(new_keys) == 0, f"Tidak ada key baru di luar _enrichment_* (extra: {new_keys})")

# ── GATE 5: Reviewable suggestions ───────────────────────────
print("\n=== GATE 5: Reviewable suggestions ===")
rev_view = DIR12 / "enrichment_review_view.json"
rev_dec  = DIR12 / "enrichment_review_decisions.json"
rev_done = DIR12 / "canonical_enriched_reviewed.json"

check(rev_view.exists(), "enrichment_review_view.json ada")
check(rev_dec.exists(),  "enrichment_review_decisions.json ada")
check(rev_done.exists(), "canonical_enriched_reviewed.json ada")

if rev_view.exists():
    v = json.load(open(rev_view))
    check("by_category" in v, "review view punya by_category")
    check(v.get("total_suggestions",0) > 0, "ada suggestions di view")
    # Cek available_actions ada
    for cat_items in v.get("by_category",{}).values():
        for item in cat_items[:1]:
            check("available_actions" in item, "item punya available_actions")
            check(set(item["available_actions"]) >= {"accept","reject"},
                  "available_actions include accept + reject")

if rev_done.exists():
    rd = json.load(open(rev_done))
    meta = rd.get("_enrichment_metadata",{})
    reviewed_sugg = rd.get("_enrichment_suggestions",[])
    check(meta.get("review_completed") is True, "review_completed = True")
    accepted = [s for s in reviewed_sugg if s["status"] == "accepted"]
    check(len(accepted) > 0, f"Ada suggestion yang di-accept ({len(accepted)})")

print("\n" + "="*50)
if ERRORS:
    print(f"ENRICHMENT ENGINE GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("ENRICHMENT ENGINE GATE: ALL PASS")
    sys.exit(0)
