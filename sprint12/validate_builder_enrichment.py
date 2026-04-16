"""
validate_builder_enrichment.py — Sprint 12 Gates 6-9
Validasi builder integration + Bab IV/VII behavior + downstream safety.

Usage:
  python validate_builder_enrichment.py
  python validate_builder_enrichment.py --dir /path/sprint12/
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

# ── GATE 6: Builder integration works ────────────────────────
print("\n=== GATE 6: Builder integration ===")
enr7 = DIR12 / "enriched_outline_bab7.json"
enr4 = DIR12 / "enriched_outline_bab4.json"

check(enr7.exists(), "enriched_outline_bab7.json ada")
check(enr4.exists(), "enriched_outline_bab4.json ada")

if enr7.exists():
    d7 = json.load(open(enr7))
    ch7 = d7[0] if isinstance(d7,list) else d7
    hints7 = ch7.get("_enrichment_hints",{})

    check("_enrichment_hints"  in ch7,         "bab7 punya _enrichment_hints")
    check(hints7.get("total_hints",0) > 0,      f"bab7 hints > 0 ({hints7.get('total_hints',0)})")
    check("hints"              in hints7,        "hints array ada")
    check("usage_note"         in hints7,        "usage_note ada (builder bisa abaikan hints)")

    # CRITICAL: argument_points harus tidak berubah
    points7 = ch7.get("argument_points",[])
    check(len(points7) >= 15, f"argument_points bab7 masih lengkap: {len(points7)}")
    check("core_claim"  in ch7, "core_claim bab7 masih ada")
    check("known_gaps"  in ch7, "known_gaps bab7 masih ada")

if enr4.exists():
    d4 = json.load(open(enr4))
    ch4 = d4[0] if isinstance(d4,list) else d4
    hints4 = ch4.get("_enrichment_hints",{})
    check("_enrichment_hints" in ch4, "bab4 punya _enrichment_hints")

# ── GATE 7: Bab IV behaves better ────────────────────────────
print("\n=== GATE 7: Bab IV gap-aware framing ===")
if enr4.exists():
    d4 = json.load(open(enr4))
    ch4 = d4[0] if isinstance(d4,list) else d4
    hints4 = ch4.get("_enrichment_hints",{})
    hint_texts = " ".join(h["text"] for h in hints4.get("hints",[]))

    check("baseline programatik" in hint_texts.lower() or "baseline" in hint_texts.lower(),
          "Bab IV hints menyebut baseline programatik")
    check("gap" in hint_texts.lower() or "must_render" in hint_texts.lower() or
          len(ch4.get("known_gaps",[])) > 0,
          "Bab IV punya gap acknowledgement")

    # Bab IV tidak boleh punya argument_points palsu
    fake_points = [p for p in ch4.get("argument_points",[])
                   if "generated" in p.get("point","").lower() and
                   "data tidak tersedia" not in p.get("point","").lower()]
    check(len(fake_points) == 0,
          f"Bab IV tidak punya fabricated argument points ({len(ch4.get('argument_points',[]))} points)")

# ── GATE 8: Bab VII terminology improves ─────────────────────
print("\n=== GATE 8: Bab VII terminology ===")
if enr7.exists():
    d7 = json.load(open(enr7))
    ch7 = d7[0] if isinstance(d7,list) else d7
    hint_texts7 = " ".join(h["text"] for h in
                            ch7.get("_enrichment_hints",{}).get("hints",[]))

    check("blended sroi" in hint_texts7.lower() or "terminology" in hint_texts7.lower(),
          "Bab VII hints mencakup Blended SROI terminology")
    check("proxy" in hint_texts7.lower(),
          "Bab VII hints mencakup proxy caution")
    # Pastikan terminology note ada
    term_hints = [h for h in ch7.get("_enrichment_hints",{}).get("hints",[])
                  if h.get("category") in ["terminology","caution"]]
    check(len(term_hints) > 0, f"Ada terminology/caution hints di bab7 ({len(term_hints)})")

# ── GATE 9: Downstream compatibility ─────────────────────────
print("\n=== GATE 9: Downstream compatibility ===")
if enr7.exists():
    d7 = json.load(open(enr7))
    ch7 = d7[0] if isinstance(d7,list) else d7
    # Field yang dibutuhkan narrative_builder_sroi.py
    for field in ["chapter_id","argument_points","core_claim","known_gaps"]:
        check(field in ch7, f"enriched_outline_bab7 punya '{field}'")
    check(ch7.get("chapter_id") == "bab_7", "chapter_id = bab_7")

    # _enrichment_hints tidak boleh merusak schema
    points = ch7.get("argument_points",[])
    for p in points[:3]:
        check("label" in p and "point" in p,
              f"argument_point {p.get('label','?')} schema intact")

# Cek canonical_enriched masih downstream-safe
can_enr = DIR12 / "canonical_enriched.json"
if can_enr.exists():
    ce = json.load(open(can_enr))
    for field in ["program_identity","investment","monetization",
                  "ddat_params","ori_rates","sroi_metrics"]:
        check(field in ce, f"canonical_enriched punya '{field}'")

print("\n" + "="*55)
if ERRORS:
    print(f"BUILDER ENRICHMENT GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("BUILDER ENRICHMENT GATE: ALL PASS")
    sys.exit(0)
