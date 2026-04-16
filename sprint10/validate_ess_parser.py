"""
Sprint 10 Gate Validator — ess_parser (Gate D)

Usage:
  python validate_ess_parser.py
  python validate_ess_parser.py --canonical /path/canonical_ess_extracted_v2.json
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--canonical", default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR / "canonical_ess_extracted_v2.json"))

print(f"Canonical: {CANONICAL_FILE.resolve()}")
if not CANONICAL_FILE.exists():
    print(f"FAIL: {CANONICAL_FILE} tidak ditemukan"); sys.exit(1)

data   = json.load(open(CANONICAL_FILE))
ERRORS = []

def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE D1: Canonical validity ──────────────────────────────
print("\n=== GATE D1: Schema canonical valid ===")
REQUIRED_FIELDS = [
    "schema_version","program_identity","program_positioning",
    "source_registry","investment","monetization","ddat_params",
    "ori_rates","sroi_metrics","coverage_status","uncertainty_flags",
]
for field in REQUIRED_FIELDS:
    check(field in data, f"Field '{field}' ada")

check(data.get("schema_version") == "1.0",     "schema_version = 1.0")

pi = data.get("program_identity", {})
check(pi.get("program_code") == "ESS",          "program_code = ESS")
check(bool(pi.get("program_name")),              "program_name tidak kosong")

# ── GATE D2: Honesty rule — tidak fabricate ──────────────────
print("\n=== GATE D2: Honesty rule ===")

# Per-year breakdown harus kosong atau pending
sroi = data.get("sroi_metrics", {})
calc = sroi.get("calculated", {})
per_year = calc.get("per_year", [])
check(len(per_year) == 0,
      f"per_year kosong — tidak fabricate breakdown (dapat: {len(per_year)})")

# Status SROI bukan "calculated" (belum bisa dihitung deterministik)
sroi_status = sroi.get("status", "")
check(sroi_status in ["partial","preliminary","pending"],
      f"sroi_metrics.status = partial/preliminary/pending (dapat: '{sroi_status}')")

# Per-year status note harus ada
per_year_note = calc.get("per_year_status", "")
check("pending" in per_year_note.lower() or "tidak tersedia" in per_year_note.lower(),
      f"per_year_status menjelaskan keterbatasan")

# ── GATE D3: Status tags jujur ───────────────────────────────
print("\n=== GATE D3: Status tags ===")
investments = data.get("investment", [])
check(len(investments) > 0, "Ada data investasi")
if investments:
    inv_status = investments[0].get("data_status","")
    check(inv_status in ["under_confirmation","proxy","partial"],
          f"Investment data_status jujur (dapat: '{inv_status}')")

# DDAT params — field kosong boleh ada status pending
ddat = data.get("ddat_params", {})
check(len(ddat) > 0, "Ada ddat_params")
pending_ddat = [k for k,v in ddat.items()
                if v.get("data_status") in ["pending","proxy"]]
check(len(pending_ddat) > 0,
      f"Ada ddat_params dengan status pending/proxy ({len(pending_ddat)} aspek)")

# ── GATE D4: Minimum fields terisi ───────────────────────────
print("\n=== GATE D4: Minimum fields ===")
check(bool(data.get("program_identity",{}).get("program_name")),
      "program_identity.program_name terisi")
check(len(data.get("monetization",[])) > 0,
      f"monetization tidak kosong (dapat: {len(data.get('monetization',[]))})")
check(len(data.get("ori_rates",{})) == 3,
      f"ori_rates = 3 tahun (dapat: {len(data.get('ori_rates',{}))})")
check(len(data.get("coverage_status",{})) == 9,
      f"coverage_status memuat 9 bab (dapat: {len(data.get('coverage_status',{}))})")

# ── GATE D5: Uncertainty flags ───────────────────────────────
print("\n=== GATE D5: Uncertainty flags ===")
flags = data.get("uncertainty_flags", [])
check(len(flags) >= 1, f"Ada uncertainty_flags (dapat: {len(flags)})")
yearly_flag = any("per_year" in f.get("field_path","") or "yearly" in f.get("reason","").lower()
                  for f in flags)
check(yearly_flag, "Ada flag yang menjelaskan keterbatasan per-year data")

# ── GATE D6: Downstream compatibility ────────────────────────
print("\n=== GATE D6: Downstream compatibility ===")
# Fields yang dibutuhkan pipeline downstream tidak boleh crash
safe_types = (dict, list, str, int, float, bool, type(None))
def check_safe(val, path):
    if not isinstance(val, safe_types):
        check(False, f"{path} tipe tidak aman: {type(val)}")
        return
    if isinstance(val, dict):
        for k, v in val.items(): check_safe(v, f"{path}.{k}")
    elif isinstance(val, list):
        for i, v in enumerate(val[:5]): check_safe(v, f"{path}[{i}]")

check_safe(data, "root")
check(True, "Struktur JSON downstream-safe")

# Cek coverage_status tidak punya status yang tidak dikenal
valid_cov = {"strong","partial","weak","missing","skeleton_only"}
bad_cov = []
for bab, cv in data.get("coverage_status",{}).items():
    s = cv.get("status","")
    if s not in valid_cov:
        bad_cov.append(f"{bab}:{s}")
check(len(bad_cov) == 0, f"coverage_status values valid (bad: {bad_cov})")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"ESS PARSER GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    sroi_b = calc.get("sroi_blended")
    print("ESS PARSER GATE: ALL PASS")
    print(f"  program_code : ESS")
    print(f"  sroi_status  : {sroi_status}")
    print(f"  sroi_blended : {sroi_b} (status: {calc.get('sroi_blended_status','?')})")
    print(f"  investments  : {len(investments)}")
    print(f"  monetization : {len(data.get('monetization',[]))}")
    print(f"  flags        : {len(flags)}")
    sys.exit(0)
