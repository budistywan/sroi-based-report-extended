"""
Sprint 2 Gate Validator — Report Architect
Gate: blueprint + gap_matrix harus konsisten dengan coverage riil canonical JSON.

Usage:
  python validate_sprint2.py
  python validate_sprint2.py --blueprint /path/report_blueprint.json \
                              --gap       /path/gap_matrix.json \
                              --handoff   /path/handoff_c.json
  BLUEPRINT_FILE=... GAP_FILE=... HANDOFF_C_FILE=... python validate_sprint2.py
"""
import json
import sys
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Sprint 2 Gate Validator")
parser.add_argument("--blueprint", default=None)
parser.add_argument("--gap",       default=None)
parser.add_argument("--handoff",   default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
BLUEPRINT_FILE = Path(args.blueprint) if args.blueprint \
    else Path(os.environ.get("BLUEPRINT_FILE", SCRIPT_DIR / "report_blueprint.json"))
GAP_FILE       = Path(args.gap)       if args.gap \
    else Path(os.environ.get("GAP_FILE",       SCRIPT_DIR / "gap_matrix.json"))
HANDOFF_C_FILE = Path(args.handoff)   if args.handoff \
    else Path(os.environ.get("HANDOFF_C_FILE", SCRIPT_DIR / "handoff_c.json"))

print(f"Blueprint : {BLUEPRINT_FILE.resolve()}")
print(f"Gap Matrix: {GAP_FILE.resolve()}")
print(f"Handoff C : {HANDOFF_C_FILE.resolve()}")

for f in [BLUEPRINT_FILE, GAP_FILE, HANDOFF_C_FILE]:
    if not f.exists():
        print(f"\nFAIL: File tidak ditemukan — {f}")
        sys.exit(1)

ERRORS = []

def check(condition, msg):
    if not condition:
        ERRORS.append(f"  FAIL: {msg}")
        return False
    print(f"  PASS: {msg}")
    return True

bp  = json.load(open(BLUEPRINT_FILE))
gap = json.load(open(GAP_FILE))
hc  = json.load(open(HANDOFF_C_FILE))

# ── GATE 1: Struktur blueprint ───────────────────────────
print("\n=== GATE 1: Struktur blueprint ===")
check("chapters"      in bp,              "chapters ada di blueprint")
check("report_mode"   in bp,              "report_mode ada di blueprint")
check("mode_reason"   in bp,              "mode_reason ada di blueprint")
check("program_code"  in bp,              "program_code ada di blueprint")
check(len(bp["chapters"]) == 9,           f"9 bab terdefinisi (dapat: {len(bp['chapters'])})")
check(bp["program_code"] == "ESL",        "program_code = ESL")

chapter_ids = [c["chapter_id"] for c in bp["chapters"]]
for i in range(1, 10):
    check(f"bab_{i}" in chapter_ids,      f"bab_{i} ada di blueprint")

# ── GATE 2: Bab 7 harus strong ──────────────────────────
print("\n=== GATE 2: Coverage Bab 7 ===")
bab7 = next((c for c in bp["chapters"] if c["chapter_id"] == "bab_7"), None)
check(bab7 is not None,                   "bab_7 ditemukan")
if bab7:
    check(bab7["coverage_status"] == "strong",  "bab_7 coverage_status = strong")
    check(bab7["risk"] == "reliable",           "bab_7 risk = reliable")
    check("sroi_metrics" in bab7["canonical_inputs"], "bab_7 canonical_inputs berisi sroi_metrics")
    fd = bab7.get("field_detail", {})
    check(fd.get("sroi_metrics") == "strong",   "bab_7 field_detail sroi_metrics = strong")
    check(fd.get("ddat_params")  == "strong",   "bab_7 field_detail ddat_params = strong")
    check(fd.get("ori_rates")    == "strong",   "bab_7 field_detail ori_rates = strong")

# ── GATE 3: Mode selection logis ────────────────────────
print("\n=== GATE 3: Mode selection ===")
mode = bp["report_mode"]
check(mode in ["full","partial","skeleton"],  f"report_mode valid: {mode}")
check(mode == "partial",                      "report_mode = partial (Bab 4 & 5 partial, tidak ada missing)")

statuses = {c["chapter_id"]: c["coverage_status"] for c in bp["chapters"]}
check(statuses.get("bab_4") == "partial",    "bab_4 = partial (context_baseline tipis)")
check(statuses.get("bab_5") == "partial",    "bab_5 = partial (ideal_conditions derived)")
check(all(s != "missing" for s in statuses.values()), "tidak ada bab dengan status missing")

# ── GATE 4: Gap matrix konsisten dengan blueprint ────────
print("\n=== GATE 4: Gap matrix ===")
check(isinstance(gap, list),                 "gap_matrix adalah array")
gap_ids = {g["chapter_id"] for g in gap}
check("bab_4" in gap_ids,                    "bab_4 ada di gap matrix")
check("bab_5" in gap_ids,                    "bab_5 ada di gap matrix")
check("bab_7" not in gap_ids,               "bab_7 tidak ada di gap matrix (sudah strong)")

for g in gap:
    check(g.get("recommendation") in ["full","placeholder","skip"],
          f"{g['chapter_id']} recommendation valid: {g.get('recommendation')}")

# ── GATE 5: Handoff C struktur ───────────────────────────
print("\n=== GATE 5: Handoff C ===")
check("report_blueprint_json" in hc,         "report_blueprint_json ada di Handoff C")
check("gap_matrix"            in hc,         "gap_matrix ada di Handoff C")
check("program_canonical_ref" in hc,         "program_canonical_ref ada di Handoff C")
check("financial_handoff_ref" in hc,         "financial_handoff_ref ada di Handoff C")
check(hc["report_blueprint_json"]["report_mode"] == mode,
      "Handoff C mode konsisten dengan blueprint")

# ── GATE 6: Semua bab punya builder_mode ────────────────
print("\n=== GATE 6: Builder mode assignment ===")
builder_modes = {"framing","context","sroi","learning"}
for c in bp["chapters"]:
    check(c.get("builder_mode") in builder_modes,
          f"{c['chapter_id']} builder_mode = {c.get('builder_mode')}")

# Cek assignment yang benar
bab_modes = {c["chapter_id"]: c["builder_mode"] for c in bp["chapters"]}
check(bab_modes.get("bab_7") == "sroi",     "bab_7 builder_mode = sroi")
check(bab_modes.get("bab_8") == "learning", "bab_8 builder_mode = learning")
check(bab_modes.get("bab_1") == "framing",  "bab_1 builder_mode = framing")
check(bab_modes.get("bab_4") == "context",  "bab_4 builder_mode = context")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 2 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS:
        print(e)
    sys.exit(1)
else:
    print("SPRINT 2 GATE: ALL PASS")
    print("Sprint 3 — Point Builder boleh dimulai.")
    sys.exit(0)
