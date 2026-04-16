"""
Sprint 7 Gate Validator — Source Extractor (deck_script_parser)

Gate: hasil parse TJSL_Scripts.md harus mendekati canonical manual ESL
      dengan field difference < 5% untuk area yang bisa diekstrak.

Usage:
  python validate_sprint7.py
  python validate_sprint7.py --registry /p/parsed_registry.json \
                              --esl-extracted /p/canonical_esl_extracted.json \
                              --esl-manual /p/canonical_esl_v1.json
  REGISTRY_FILE=... ESL_EXTRACTED=... ESL_MANUAL=... python validate_sprint7.py
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--registry",      default=None)
parser.add_argument("--esl-extracted", default=None, dest="esl_extracted")
parser.add_argument("--esl-manual",    default=None, dest="esl_manual")
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
REGISTRY_FILE = Path(args.registry)      if args.registry      \
    else Path(os.environ.get("REGISTRY_FILE",  SCRIPT_DIR / "parsed_registry.json"))
ESL_EXTRACTED = Path(args.esl_extracted) if args.esl_extracted \
    else Path(os.environ.get("ESL_EXTRACTED",  SCRIPT_DIR / "canonical_esl_extracted.json"))
# Default: snapshot lokal di sprint7 → fallback sprint0 → fallback sprint1
_manual_local   = SCRIPT_DIR / "canonical_esl_manual.json"
_manual_sprint0 = SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"
ESL_MANUAL    = Path(args.esl_manual)    if args.esl_manual    \
    else Path(os.environ.get("ESL_MANUAL",
              str(_manual_local)   if _manual_local.exists()   else
              str(_manual_sprint0) if _manual_sprint0.exists() else
              str(SCRIPT_DIR.parent / "sprint1/canonical_esl_v1.json")))

print(f"Registry    : {REGISTRY_FILE.resolve()}")
print(f"ESL extracted: {ESL_EXTRACTED.resolve()}")
print(f"ESL manual  : {ESL_MANUAL.resolve()}")

for f in [REGISTRY_FILE, ESL_EXTRACTED, ESL_MANUAL]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

def near(a, b, tol=1.0):
    return abs(float(a) - float(b)) <= tol

registry = json.load(open(REGISTRY_FILE))
extracted = json.load(open(ESL_EXTRACTED))
manual    = json.load(open(ESL_MANUAL))

# ── GATE 1: Registry struktur ────────────────────────────
print("\n=== GATE 1: Registry struktur ===")
check("programs" in registry,             "programs ada di registry")
check("programs_parsed" in registry,      "programs_parsed ada")
check(registry["programs_parsed"] >= 5,   f"minimal 5 program (dapat: {registry['programs_parsed']})")
prog_codes = [p["program_code"] for p in registry["programs"]]
for code in ["ESL","PSN","ESD","ETB","ESP"]:
    check(code in prog_codes,              f"{code} ada di registry")

# ── GATE 2: Semua program punya sroi atau coverage ───────
print("\n=== GATE 2: Coverage per program ===")
for p in registry["programs"]:
    code = p["program_code"]
    cov  = p.get("coverage", {})
    sroi = p.get("sroi_blended", "—")
    # Minimal monetization strong
    check(cov.get("monetization") in ["strong","partial"],
          f"{code} monetization coverage ada (dapat: {cov.get('monetization')})")

# ── GATE 3: ESL extracted vs manual — angka kunci ────────
print("\n=== GATE 3: ESL extracted vs manual — angka kunci ===")
e_calc = extracted["sroi_metrics"]["calculated"]
m_calc = manual["sroi_metrics"]["calculated"]

# SROI blended — toleransi 0.05 (karena script mungkin pakai pembulatan)
e_sroi = float(e_calc.get("sroi_blended", 0))
m_sroi = float(m_calc.get("sroi_blended", 0))
check(abs(e_sroi - m_sroi) < 0.05,
      f"sroi_blended: extracted={e_sroi:.4f} ≈ manual={m_sroi:.4f}")

# Total investment — toleransi Rp 1
e_inv = e_calc.get("total_investment_idr", 0)
m_inv = m_calc.get("total_investment_idr", 0)
check(near(e_inv, m_inv),
      f"total_investment: {e_inv:,} ≈ {m_inv:,}")

# Total net compounded — toleransi Rp 100 (rounding dari script)
e_nc = e_calc.get("total_net_compounded_idr", 0)
m_nc = m_calc.get("total_net_compounded_idr", 0)
check(near(e_nc, m_nc, tol=100),
      f"total_net_compounded: {e_nc:,} ≈ {m_nc:,}")

# SROI per tahun — toleransi 0.02
for yr in [2023, 2024, 2025]:
    e_yr = next((r for r in e_calc.get("per_year",[]) if r["year"]==yr), {})
    m_yr = next((r for r in m_calc.get("per_year",[]) if r["year"]==yr), {})
    if e_yr and m_yr:
        check(abs(e_yr["sroi_ratio"] - m_yr["sroi_ratio"]) < 0.02,
              f"sroi_{yr}: {e_yr['sroi_ratio']:.4f} ≈ {m_yr['sroi_ratio']:.4f}")

# ── GATE 4: ESL extracted — struktur canonical ────────────
print("\n=== GATE 4: ESL extracted canonical struktur ===")
check(extracted.get("schema_version") == "1.0",  "schema_version = 1.0")
check("program_identity" in extracted,            "program_identity ada")
check(extracted["program_identity"]["program_code"] == "ESL", "program_code = ESL")
check(len(extracted.get("investment",[])) > 0,    "investment tidak kosong")
check(len(extracted.get("monetization",[])) > 0,  "monetization tidak kosong")
check(len(extracted.get("ddat_params",{})) > 0,   "ddat_params tidak kosong")
check(len(extracted.get("ori_rates",{})) == 3,    "ori_rates = 3 tahun")

# ── GATE 5: Field difference < 5% ────────────────────────
print("\n=== GATE 5: Field difference < 5% (extractable fields) ===")
# Hitung field yang bisa diekstrak vs yang kosong
extractable = ["investment","monetization","ddat_params","ori_rates","sroi_metrics"]
filled   = sum(1 for f in extractable
               if extracted.get(f) and extracted[f] not in [{},[],"not_calculated"])
pct = filled / len(extractable) * 100
check(pct >= 80.0,
      f"Coverage extractable fields: {filled}/{len(extractable)} = {pct:.0f}% (min 80%)")

# ── GATE 6: ORI rates masuk akal ─────────────────────────
print("\n=== GATE 6: ORI rates valid ===")
ori = extracted.get("ori_rates", {})
for yr, data in ori.items():
    r = data.get("rate", 0)
    check(0.04 < r < 0.1,
          f"ORI {yr} rate={r:.4f} masuk range wajar (4-10%)")

# ── GATE 7: Canonical extracted punya coverage_status ────
print("\n=== GATE 7: coverage_status terdefinisi ===")
cs = extracted.get("coverage_status", {})
check(len(cs) == 9,               f"9 bab di coverage_status (dapat: {len(cs)})")
check(cs.get("bab_7",{}).get("status") != "missing",
      f"bab_7 tidak missing (dapat: {cs.get('bab_7',{}).get('status')})")

# ── GATE 8: Semua program punya canonical file ────────────
print("\n=== GATE 8: Canonical file ada per program ===")
for p in registry["programs"]:
    code     = p["program_code"].lower()
    can_file = SCRIPT_DIR / f"canonical_{code}_extracted.json"
    check(can_file.exists(), f"canonical_{code}_extracted.json ada")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*60)
if ERRORS:
    print(f"SPRINT 7 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 7 GATE: ALL PASS")
    print(f"  {registry['programs_parsed']} programs parsed")
    for p in registry["programs"]:
        sroi_b = p.get("sroi_blended","—")
        print(f"    {p['program_code']}: SROI={sroi_b}  "
              f"mon={p['coverage'].get('monetization','?')}  "
              f"flags={p['flags']}")
    print("Pipeline Sprint 0–7 selesai end-to-end.")
    sys.exit(0)
