"""
validate_style_profile.py — Sprint 14A
Gates 1-8: validasi seluruh artefak Sprint 14A.

Usage:
  python validate_style_profile.py
  python validate_style_profile.py --dir /path/sprint14a/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR14A     = Path(args.dir) if args.dir else SCRIPT_DIR

print(f"Sprint14A dir: {DIR14A.resolve()}")

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 1: Profile generation works ─────────────────────────
print("\n=== GATE 1: style_profile_v1.json ===")
v1_path = DIR14A / "style_profile_v1.json"
check(v1_path.exists(), "style_profile_v1.json ada")
if v1_path.exists():
    v1 = json.load(open(v1_path))
    for f in ["profile_id","target_style","tone","paragraph_formula",
              "hedging_profile","preferred_connectors","notes"]:
        check(f in v1, f"v1 punya field '{f}'")
    check(v1.get("target_style") == "indonesian_academic_evaluative",
          f"target_style = indonesian_academic_evaluative")
    check(v1["tone"].get("firm_but_guarded") is True,   "tone.firm_but_guarded = true")
    check(v1["tone"].get("anti_bombastic")   is True,   "tone.anti_bombastic = true")
    check(v1["tone"].get("anti_ai_generic")  is True,   "tone.anti_ai_generic = true")
    hp = v1.get("hedging_profile",{})
    check(len(hp.get("preferred_markers",[])) >= 4,
          f"preferred_markers ≥ 4 ({len(hp.get('preferred_markers',[]))})")
    check(len(hp.get("avoided_markers",[])) >= 3,
          f"avoided_markers ≥ 3 ({len(hp.get('avoided_markers',[]))})")
    check(len(v1.get("notes",[])) >= 3,
          f"notes ≥ 3 instruksi ({len(v1.get('notes',[]))})")
    check(isinstance(v1.get("paragraph_formula",{}).get("preferred_pattern"), str),
          "paragraph_formula.preferred_pattern ada")

# ── GATE 2: Rules are operational ────────────────────────────
print("\n=== GATE 2: style_rules_v1.json ===")
rules_path = DIR14A / "style_rules_v1.json"
check(rules_path.exists(), "style_rules_v1.json ada")
if rules_path.exists():
    r = json.load(open(rules_path))
    rules = r.get("rules",[])
    check(len(rules) >= 5, f"Minimal 5 rules ({len(rules)})")
    for rule in rules:
        check("rule_id"     in rule, f"rule {rule.get('rule_id','?')} punya rule_id")
        check("description" in rule, f"rule {rule.get('rule_id','?')} punya description")
        check("severity"    in rule, f"rule {rule.get('rule_id','?')} punya severity")
        check(rule.get("severity") in ["low","medium","high"],
              f"rule {rule.get('rule_id','?')} severity valid")
    # Rules kritis harus ada
    rule_ids = {rule["rule_id"] for rule in rules}
    for must_have in ["SR_OPENING_CONTEXT","SR_LOCKED_CLOSING","SR_NO_BOMBASTIC_CLAIM","SR_NO_AI_GENERIC"]:
        check(must_have in rule_ids, f"Rule '{must_have}' ada")

# ── GATE 3: Disliked patterns useful ─────────────────────────
print("\n=== GATE 3: disliked_patterns.json ===")
dp_path = DIR14A / "disliked_patterns.json"
check(dp_path.exists(), "disliked_patterns.json ada")
if dp_path.exists():
    dp = json.load(open(dp_path))
    patterns = dp.get("patterns",[])
    check(len(patterns) >= 5, f"Minimal 5 patterns ({len(patterns)})")
    for p in patterns:
        check("pattern_id"  in p, f"pattern {p.get('pattern_id','?')} punya pattern_id")
        check("description" in p, f"pattern {p.get('pattern_id','?')} punya description")
        check("severity"    in p, f"pattern {p.get('pattern_id','?')} punya severity")
    pattern_ids = {p["pattern_id"] for p in patterns}
    for must_have in ["DP_AI_GENERIC","DP_BOMBASTIC","DP_MECHANICAL_EXPANSION","DP_FLAT_PARAGRAPH"]:
        check(must_have in pattern_ids, f"Pattern '{must_have}' ada")
    # Minimal beberapa patterns punya examples
    with_examples = [p for p in patterns if p.get("examples")]
    check(len(with_examples) >= 3, f"Minimal 3 patterns punya examples ({len(with_examples)})")

# ── GATE 4: Edit contract works ───────────────────────────────
print("\n=== GATE 4: style_profile_editor_contract.json ===")
ctr_path = DIR14A / "style_profile_editor_contract.json"
check(ctr_path.exists(), "style_profile_editor_contract.json ada")
if ctr_path.exists():
    c = json.load(open(ctr_path))
    check("editable_fields"     in c, "editable_fields ada")
    check("non_editable_fields" in c, "non_editable_fields ada")
    check("how_to_edit"         in c, "how_to_edit ada")
    check("validation_behavior" in c, "validation_behavior ada")
    check("profile_id" in c.get("non_editable_fields",[]),  "profile_id di non_editable")
    check("tone"       in c.get("editable_fields",[]),      "tone di editable")
    check("notes"      in c.get("editable_fields",[]),      "notes di editable")
    # Contract harus menjelaskan field_contracts
    check("field_contracts" in c, "field_contracts ada di contract")
    fc = c.get("field_contracts",{})
    check("hedging_profile" in fc, "hedging_profile field contract ada")
    check(bool(fc.get("hedging_profile",{}).get("level_enum")), "hedging level_enum terdefinisi")

# ── GATE 5: Importer works ────────────────────────────────────
print("\n=== GATE 5: style_profile_importer.py ===")
imp_path = DIR14A / "style_profile_importer.py"
check(imp_path.exists(), "style_profile_importer.py ada")

import subprocess, sys as _sys
if imp_path.exists():
    # Test demo mode
    r = subprocess.run(
        [_sys.executable, str(imp_path), "--demo",
         "--output", "/tmp/sp14a_test_reviewed.json"],
        capture_output=True, text=True
    )
    check(r.returncode == 0,            "importer --demo exit 0")
    check("IMPORT COMPLETE" in r.stdout,"IMPORT COMPLETE di output")

    # Test invalid edit rejected
    import json as _json, copy
    v1_data = _json.load(open(DIR14A / "style_profile_v1.json"))
    bad = copy.deepcopy(v1_data)
    bad["profile_id"] = "hack"
    _json.dump(bad, open("/tmp/sp14a_bad.json","w"))
    r2 = subprocess.run(
        [_sys.executable, str(imp_path), "--input", "/tmp/sp14a_bad.json"],
        capture_output=True, text=True
    )
    check(r2.returncode != 0 or "IMPORT FAILED" in r2.stdout,
          "Invalid edit (non-editable field) ditolak importer")

# ── GATE 6: Reviewed profile traceable ───────────────────────
print("\n=== GATE 6: style_profile_reviewed.json ===")
rev_path = DIR14A / "style_profile_reviewed.json"
check(rev_path.exists(), "style_profile_reviewed.json ada")
if rev_path.exists():
    rev = json.load(open(rev_path))
    check(rev.get("profile_id")        == "style_profile_reviewed",
          "profile_id = style_profile_reviewed")
    check(rev.get("parent_profile_id") == "style_profile_v1",
          "parent_profile_id = style_profile_v1 (lineage jelas)")
    check("reviewed_by"      in rev,   "reviewed_by ada")
    check("review_timestamp" in rev,   "review_timestamp ada")
    check("changes_summary"  in rev,   "changes_summary ada (delta tercatat)")
    # Core preferensi tetap ada
    check("tone"              in rev,  "tone masih ada di reviewed")
    check("hedging_profile"   in rev,  "hedging_profile masih ada di reviewed")
    check("paragraph_formula" in rev,  "paragraph_formula masih ada di reviewed")

# ── GATE 7: Tidak ada kontradiksi fatal ──────────────────────
print("\n=== GATE 7: Konsistensi rules vs disliked_patterns ===")
if rules_path.exists() and dp_path.exists():
    rules_data = json.load(open(rules_path))
    dp_data    = json.load(open(dp_path))
    # SR_NO_BOMBASTIC_CLAIM harus konsisten dengan DP_BOMBASTIC
    rule_ids   = {r["rule_id"] for r in rules_data.get("rules",[])}
    pattern_ids= {p["pattern_id"] for p in dp_data.get("patterns",[])}
    check("SR_NO_BOMBASTIC_CLAIM" in rule_ids and "DP_BOMBASTIC" in pattern_ids,
          "Rule dan pattern bombastis konsisten")
    check("SR_NO_AI_GENERIC" in rule_ids and "DP_AI_GENERIC" in pattern_ids,
          "Rule dan pattern AI-generic konsisten")
    check("SR_NO_MECHANICAL_EXPANSION" in rule_ids and "DP_MECHANICAL_EXPANSION" in pattern_ids,
          "Rule dan pattern mechanical konsisten")

# ── GATE 8: Downstream compatibility ─────────────────────────
print("\n=== GATE 8: Downstream compatibility ===")
if rev_path.exists():
    rev = json.load(open(rev_path))
    # Fields yang dibutuhkan Sprint 14B dan refinement layer
    for f in ["tone","paragraph_formula","hedging_profile","preferred_connectors",
              "variation_preferences","notes","parent_profile_id","review_timestamp"]:
        check(f in rev, f"downstream field '{f}' ada di reviewed profile")
    check(rev.get("profile_id") != v1.get("profile_id",""),
          "reviewed dan v1 punya profile_id berbeda (tidak identik)")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 14A GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 14A GATE: ALL PASS")
    print("style_profile_reviewed.json siap sebagai fondasi Sprint 14B.")
    sys.exit(0)
