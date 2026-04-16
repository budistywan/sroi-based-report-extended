"""
validate_ontology.py — Sprint 12 Gate 1-2
Validasi ontology + lexicon.

Usage:
  python validate_ontology.py
  python validate_ontology.py --dir /path/sprint12/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR12      = Path(args.dir) if args.dir else SCRIPT_DIR

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 1: Ontology valid ────────────────────────────────────
print("\n=== GATE 1: Ontology valid ===")
ont_path = DIR12 / "ontology_v1.json"
check(ont_path.exists(), "ontology_v1.json ada")
if ont_path.exists():
    o = json.load(open(ont_path))
    check("entities"       in o, "entities ada")
    check("relations"      in o, "relations ada")
    check("semantic_rules" in o, "semantic_rules ada")
    check(len(o.get("entities",{})) >= 5, f"Minimal 5 entity types (dapat: {len(o.get('entities',{}))})")
    check(len(o.get("relations",[])) >= 5, f"Minimal 5 relasi (dapat: {len(o.get('relations',[]))})")
    check(len(o.get("semantic_rules",[])) >= 5, f"Minimal 5 semantic rules")

    # Cek tidak ada relasi absurd
    valid_types = {"produces","leads_to","experienced_by","monetized_by",
                   "adjustable_by","affects_quality","enables","targets",
                   "classified_as","supports","informs","addresses","blocks"}
    for r in o["relations"]:
        check("from" in r and "type" in r and "to" in r,
              f"Relasi lengkap: {r}")

sch_path = DIR12 / "ontology_schema.json"
check(sch_path.exists(), "ontology_schema.json ada")

# ── GATE 2: Lexicon valid ─────────────────────────────────────
print("\n=== GATE 2: Lexicon valid ===")
lex_path = DIR12 / "domain_lexicon_v1.json"
check(lex_path.exists(), "domain_lexicon_v1.json ada")
if lex_path.exists():
    l = json.load(open(lex_path))
    terms = l.get("terms",[])
    check(len(terms) >= 10, f"Minimal 10 terms (dapat: {len(terms)})")

    # Cek istilah penting ada
    term_names = [t["term"].lower() for t in terms]
    for must_have in ["Blended SROI","Observed direct return","DDAT","proxy","LFA"]:
        check(must_have.lower() in term_names, f"Term '{must_have}' ada")

    # Cek semua term punya definition + aliases
    for t in terms:
        check("definition" in t and t["definition"], f"Term '{t['term']}' punya definition")
        check("aliases"    in t,                       f"Term '{t['term']}' punya aliases")

print("\n" + "="*50)
if ERRORS:
    print(f"ONTOLOGY GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("ONTOLOGY GATE: ALL PASS")
    sys.exit(0)
