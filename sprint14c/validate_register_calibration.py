"""
validate_register_calibration.py — Sprint 14C
Gates A-H: register coverage, signature validity, differentiation,
register collapse check, map validity, compatibility, downstream.

Usage:
  python validate_register_calibration.py
  python validate_register_calibration.py --dir /path/sprint14c/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR14C     = Path(args.dir) if args.dir else SCRIPT_DIR
DIR14A     = DIR14C.parent / "sprint14a"
DIR14B     = DIR14C.parent / "sprint14b"

REGISTERS   = ["framing","analytic","evaluative","reflective","conclusive"]
ALL_BAB     = ["bab_1","bab_2","bab_3","bab_4","bab_5","bab_6","bab_7","bab_8","bab_9"]

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE A: Artefak wajib ─────────────────────────────────────
print("\n=== GATE A: Artefak wajib ===")
required = (["register_tagged_exemplars.json","register_style_map.json",
             "validate_register_calibration.py","README_sprint14c.md"] +
            [f"style_signature_{r}.json" for r in REGISTERS])
for fname in required:
    check((DIR14C / fname).exists(), f"{fname} ada")

# ── GATE B: Register exemplar coverage ───────────────────────
print("\n=== GATE B: Register exemplar coverage ===")
rte_path = DIR14C / "register_tagged_exemplars.json"
if rte_path.exists():
    rte = json.load(open(rte_path))
    regs = rte.get("registers",[])
    reg_names = {r["register"] for r in regs}
    for reg in ["framing_register","analytic_register","evaluative_register",
                "reflective_register","conclusive_register"]:
        check(reg in reg_names, f"Register '{reg}' ada di tagged exemplars")
    for r in regs:
        exs = r.get("exemplars",[])
        check(len(exs) >= 1, f"{r['register']}: minimal 1 exemplar ({len(exs)})")
        for ex in exs:
            check("exemplar_id"   in ex, f"{r['register']}/{ex.get('exemplar_id','?')}: exemplar_id ada")
            check("text"          in ex, f"{r['register']}/{ex.get('exemplar_id','?')}: text ada")
            check(len(ex.get("text","")) >= 80,
                  f"{r['register']}/{ex.get('exemplar_id','?')}: text ≥ 80 chars")

# ── GATE C: Signature validity ────────────────────────────────
print("\n=== GATE C: Signature per register valid ===")
signatures = {}
REQUIRED_DIMS = ["opening_style","hedging_degree","transition_style","closing_style","sentence_rhythm"]
for reg in REGISTERS:
    fpath = DIR14C / f"style_signature_{reg}.json"
    if fpath.exists():
        sig = json.load(open(fpath))
        signatures[reg] = sig
        check(sig.get("register") == f"{reg}_register",    f"{reg}: register field benar")
        check("dimensions"      in sig,                     f"{reg}: dimensions ada")
        check("variation_rules" in sig,                     f"{reg}: variation_rules ada")
        check("special_emphasis"in sig,                     f"{reg}: special_emphasis ada")
        check("guard_rails"     in sig,                     f"{reg}: guard_rails ada")
        dims = sig.get("dimensions",{})
        for dim in REQUIRED_DIMS:
            check(dim in dims, f"{reg}: dimension '{dim}' ada")
        # Opening harus punya pattern
        check(bool(dims.get("opening_style",{}).get("pattern")), f"{reg}: opening pattern terdefinisi")
        # Hedging harus punya level
        check(bool(dims.get("hedging_degree",{}).get("level")), f"{reg}: hedging level terdefinisi")

# ── GATE D: Differentiation meaningful ───────────────────────
print("\n=== GATE D: Diferensiasi antar register ===")
if len(signatures) == 5:
    def get_dim_val(sig, dim, subfield):
        return sig.get("dimensions",{}).get(dim,{}).get(subfield,"")

    pairs = [
        ("framing",    "analytic"),
        ("analytic",   "evaluative"),
        ("evaluative", "reflective"),
        ("reflective", "conclusive"),
    ]
    for r1, r2 in pairs:
        if r1 not in signatures or r2 not in signatures: continue
        s1, s2 = signatures[r1], signatures[r2]
        diffs = 0
        for dim, sub in [("opening_style","pattern"),("hedging_degree","level"),
                         ("closing_style","pattern"),("sentence_rhythm","style")]:
            v1 = get_dim_val(s1, dim, sub)
            v2 = get_dim_val(s2, dim, sub)
            if v1 != v2:
                diffs += 1
        check(diffs >= 2, f"{r1} vs {r2}: berbeda di ≥ 2 dimensi ({diffs} diffs found)")

# ── GATE E: No register collapse ─────────────────────────────
print("\n=== GATE E: Anti register collapse ===")
if len(signatures) == 5:
    # Evaluative ≠ Reflective (paling rawan collapse)
    ev = signatures.get("evaluative",{})
    rf = signatures.get("reflective",{})
    ev_open  = ev.get("dimensions",{}).get("opening_style",{}).get("pattern","")
    rf_open  = rf.get("dimensions",{}).get("opening_style",{}).get("pattern","")
    ev_firm  = ev.get("dimensions",{}).get("hedging_degree",{}).get("firmness","")
    rf_firm  = rf.get("dimensions",{}).get("hedging_degree",{}).get("firmness","")
    check(ev_open != rf_open or ev_firm != rf_firm,
          f"evaluative ≠ reflective (opening: {ev_open} vs {rf_open}, firmness: {ev_firm} vs {rf_firm})")

    # Framing ≠ Conclusive
    fr  = signatures.get("framing",{})
    con = signatures.get("conclusive",{})
    fr_close  = fr.get("dimensions",{}).get("closing_style",{}).get("pattern","")
    con_close = con.get("dimensions",{}).get("closing_style",{}).get("pattern","")
    check(fr_close != con_close,
          f"framing ≠ conclusive closing (framing: {fr_close}, conclusive: {con_close})")

    # Semua special_emphasis harus berbeda minimal 1 item
    all_emphasis = {r: set(signatures[r].get("special_emphasis",[])) for r in REGISTERS}
    for r1 in REGISTERS:
        for r2 in REGISTERS:
            if r1 >= r2: continue
            diff = all_emphasis[r1].symmetric_difference(all_emphasis[r2])
            check(len(diff) >= 2,
                  f"special_emphasis {r1} vs {r2}: ≥ 2 perbedaan ({len(diff)} found)")

# ── GATE F: Register style map valid ─────────────────────────
print("\n=== GATE F: register_style_map.json ===")
map_path = DIR14C / "register_style_map.json"
if map_path.exists():
    smap = json.load(open(map_path))
    check("mapping"          in smap, "mapping ada")
    check("default_register" in smap, "default_register ada")
    check("override_allowed" in smap, "override_allowed ada")
    check("lookup"           in smap, "lookup table ada")
    # Semua bab terpetakan
    mapped_babs = set()
    for entry in smap.get("mapping",[]):
        for b in entry.get("bab",[]):
            mapped_babs.add(b)
    for bab in ALL_BAB:
        check(bab in mapped_babs, f"{bab} terpetakan di register_style_map")
    # Default register valid
    check(smap.get("default_register","") in
          [f"{r}_register" for r in REGISTERS],
          f"default_register valid: {smap.get('default_register','')}")
    # Lookup table lengkap
    lookup = smap.get("lookup",{})
    for bab in ALL_BAB:
        check(bab in lookup, f"lookup[{bab}] ada")

# ── GATE G: 14A & 14B compatibility ──────────────────────────
print("\n=== GATE G: Compatibility dengan 14A dan 14B ===")
for reg, sig in signatures.items():
    guard = sig.get("guard_rails",{})
    check(guard.get("anti_bombastic") is True,  f"{reg}: anti_bombastic aktif")
    check(guard.get("anti_ai_generic") is True,  f"{reg}: anti_ai_generic aktif")
    check(bool(sig.get("parent_global_signature")),
          f"{reg}: parent_global_signature ada (14B lineage)")
    check(bool(sig.get("parent_style_profile")),
          f"{reg}: parent_style_profile ada (14A lineage)")

# ── GATE H: Downstream readiness ─────────────────────────────
print("\n=== GATE H: Downstream readiness ===")
if map_path.exists() and len(signatures) == 5:
    smap   = json.load(open(map_path))
    lookup = smap.get("lookup",{})
    # Setiap bab bisa resolve ke signature file
    for bab in ALL_BAB:
        reg_name = lookup.get(bab,"")
        reg_key  = reg_name.replace("_register","")
        sig_file = DIR14C / f"style_signature_{reg_key}.json"
        check(sig_file.exists(), f"{bab} → {sig_file.name} resolves to existing file")
    # Machine-readable: semua entry punya signature_file field
    for entry in smap.get("mapping",[]):
        check("signature_file" in entry,
              f"mapping entry {entry.get('bab',[])} punya signature_file field")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 14C GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 14C GATE: ALL PASS")
    print("Five register signatures + style map siap untuk downstream.")
    sys.exit(0)
