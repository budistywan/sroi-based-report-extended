"""
Sprint 1 Gate Validator — Financial Calculation Engine
Gate: output Financial Engine harus identik dengan kalkulasi manual S10.

Usage:
  python validate_sprint1.py                                         # default: cari file relatif ke script
  python validate_sprint1.py --handoff /path/handoff_b.json \
                              --canonical /path/canonical_esl_v1.json
  HANDOFF_FILE=... CANONICAL_FILE=... python validate_sprint1.py
"""
import json
import sys
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Sprint 1 Gate Validator")
parser.add_argument("--handoff",   default=None, help="Path ke handoff_b.json")
parser.add_argument("--canonical", default=None, help="Path ke canonical_esl_v1.json")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent

# Resolusi path: CLI → env var → default relatif ke script
HANDOFF_FILE   = Path(args.handoff)   if args.handoff   \
    else Path(os.environ.get("HANDOFF_FILE",   SCRIPT_DIR / "handoff_b.json"))
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))

print(f"Handoff B : {HANDOFF_FILE.resolve()}")
print(f"Canonical : {CANONICAL_FILE.resolve()}")

# ── cek file ada sebelum mulai ───────────────────────────
for f, label in [(HANDOFF_FILE, "handoff_b.json"), (CANONICAL_FILE, "canonical_esl_v1.json")]:
    if not f.exists():
        print(f"\nFAIL: File tidak ditemukan — {f}")
        print("Gunakan --handoff dan --canonical untuk menentukan path eksplisit.")
        sys.exit(1)

ERRORS  = []
TOLERANCE = 1.0  # Rp 1 toleransi floating point

def check(condition, msg):
    if not condition:
        ERRORS.append(f"  FAIL: {msg}")
        return False
    print(f"  PASS: {msg}")
    return True

def near(a, b, tol=TOLERANCE):
    return abs(a - b) <= tol

# ── REFERENSI MANUAL S10 ─────────────────────────────────
REFERENCE = {
    "total_investment":     502_460_181,
    "total_net_compounded": 570_672_411,
    "sroi_blended":         1.1359,
    "avg_fiksasi_pct":      45.1,
    "per_year": {
        2023: {"investment": 128_108_409, "gross": 299_530_066,
               "net": 164_256_055, "compounded": 184_820_913, "sroi": 1.4426},
        2024: {"investment": 179_351_772, "gross": 312_942_092,
               "net": 171_858_476, "compounded": 182_599_631, "sroi": 1.0181},
        2025: {"investment": 195_000_000, "gross": 369_718_930,
               "net": 203_251_867, "compounded": 203_251_867, "sroi": 1.0423},
    }
}

hb        = json.load(open(HANDOFF_FILE))
canonical = json.load(open(CANONICAL_FILE))
calc      = hb["sroi_metrics"]["calculated"]

# ── GATE 1: Status & struktur ────────────────────────────
print("\n=== GATE 1: Status & struktur ===")
check(hb["sroi_metrics"]["status"] == "calculated",   "status = calculated")
check("calc_audit_log"   in hb,                       "calc_audit_log ada di Handoff B")
check("financial_tables" in hb,                       "financial_tables ada di Handoff B")
check(len(hb["calc_audit_log"]) > 0,                  "audit_log tidak kosong")
check(len(hb["financial_tables"]) == 5,               "5 tabel dihasilkan")
check(canonical["sroi_metrics"]["status"] == "calculated",
      "canonical sroi_metrics.status sudah diupdate ke calculated")

# ── GATE 2: Angka top-level ──────────────────────────────
print("\n=== GATE 2: Angka top-level vs referensi manual S10 ===")
check(near(calc["total_investment_idr"],     REFERENCE["total_investment"]),
      f"total_investment     Rp{calc['total_investment_idr']:,.0f}")
check(near(calc["total_net_compounded_idr"], REFERENCE["total_net_compounded"]),
      f"total_net_compounded Rp{calc['total_net_compounded_idr']:,.0f}")
check(abs(calc["sroi_blended"] - REFERENCE["sroi_blended"]) < 0.001,
      f"sroi_blended         {calc['sroi_blended']:.4f}")
check(abs(calc["avg_fiksasi_pct"] - REFERENCE["avg_fiksasi_pct"]) < 0.5,
      f"avg_fiksasi          {calc['avg_fiksasi_pct']:.1f}%")

# ── GATE 3: Angka per tahun ──────────────────────────────
print("\n=== GATE 3: Angka per tahun vs referensi ===")
for row in calc["per_year"]:
    yr  = row["year"]
    ref = REFERENCE["per_year"][yr]
    check(near(row["investment"],  ref["investment"]),  f"{yr} investment  Rp{row['investment']:,.0f}")
    check(near(row["gross"],       ref["gross"]),        f"{yr} gross       Rp{row['gross']:,.0f}")
    check(near(row["net"],         ref["net"]),          f"{yr} net          Rp{row['net']:,.0f}")
    check(near(row["compounded"],  ref["compounded"]),  f"{yr} compounded  Rp{row['compounded']:,.0f}")
    check(abs(row["sroi_ratio"] - ref["sroi"]) < 0.001, f"{yr} sroi_ratio  1:{row['sroi_ratio']:.4f}")

# ── GATE 4: Audit log coverage ───────────────────────────
print("\n=== GATE 4: Audit log coverage ===")
audit_fields = {e["field"] for e in hb["calc_audit_log"]}
for field in [
    "total_investment", "sroi_blended",
    "net_compounded_2023", "net_compounded_2024", "net_compounded_2025",
    "sroi_ratio_2023",    "sroi_ratio_2024",    "sroi_ratio_2025",
]:
    check(field in audit_fields, f"audit_log berisi field '{field}'")

# ── GATE 5: Column widths ────────────────────────────────
print("\n=== GATE 5: Tabel column_widths = 9638 DXA ===")
for tbl in hb["financial_tables"]:
    total_w = sum(tbl["column_widths"])
    check(total_w == 9638, f"{tbl['table_id']}: column_widths total = {total_w} DXA")

# ── GATE 6: Cross-check tabel vs calc ───────────────────
print("\n=== GATE 6: Cross-check tabel vs calc ===")
blended_tbl = next((t for t in hb["financial_tables"]
                    if t["table_id"] == "table_sroi_blended"), None)
if blended_tbl:
    sroi_row = next((r for r in blended_tbl["rows"] if "SROI" in r[0]), None)
    if sroi_row:
        check("1.14" in sroi_row[1],
              f"table_sroi_blended SROI = {sroi_row[1]}")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 1 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS:
        print(e)
    sys.exit(1)
else:
    print("SPRINT 1 GATE: ALL PASS")
    print("Sprint 2 — Report Architect boleh dimulai.")
    sys.exit(0)
