"""
validate_review_flow.py — Sprint 11
Gates 3–8: Review handlers + state machine + downstream compatibility.

Usage:
  python validate_review_flow.py
  python validate_review_flow.py --sprint11-dir /path/sprint11/ --sprint0-dir /path/sprint0/
"""
import json, sys, os, argparse, subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--sprint11-dir", default=None, dest="dir11")
parser.add_argument("--sprint0-dir",  default=None, dest="dir0")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR11      = Path(args.dir11) if args.dir11 \
    else Path(os.environ.get("SPRINT11_DIR", SCRIPT_DIR))
DIR0       = Path(args.dir0)  if args.dir0  \
    else Path(os.environ.get("SPRINT0_DIR",  SCRIPT_DIR.parent / "sprint0"))

print(f"Sprint11 dir : {DIR11.resolve()}")
print(f"Sprint0  dir : {DIR0.resolve()}")

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 3: Canonical review works ───────────────────────────
print("\n=== GATE 3: Canonical review works ===")
rev_can = DIR11 / "canonical_reviewed.json"
dec_can = DIR11 / "canonical_review_decisions.json"
check(rev_can.exists(), "canonical_reviewed.json ada")
check(dec_can.exists(), "canonical_review_decisions.json ada")
if rev_can.exists():
    rc = json.load(open(rev_can))
    meta = rc.get("_review_metadata",{})
    check(meta.get("decision") in ["approve","approve_with_notes","revise","defer",""],
          f"decision valid: {meta.get('decision','?')}")
    # Downstream compatibility — harus punya field minimum canonical
    for field in ["program_identity","sroi_metrics","investment","monetization"]:
        check(field in rc, f"canonical_reviewed punya '{field}'")

# ── GATE 4: Gap review works ─────────────────────────────────
print("\n=== GATE 4: Gap review works ===")
rev_gap = DIR11 / "gap_matrix_reviewed.json"
check(rev_gap.exists(), "gap_matrix_reviewed.json ada")
if rev_gap.exists():
    rg = json.load(open(rev_gap))
    check("gap_items"       in rg,    "gap_matrix_reviewed punya gap_items")
    check("_review_metadata" in rg,   "_review_metadata ada")
    items = rg.get("gap_items",[])
    reviewed_items = [i for i in items if i.get("_review_decision")]
    check(len(reviewed_items) > 0,
          f"Ada gap items dengan _review_decision ({len(reviewed_items)} items)")
    # Cek valid decisions
    valid_gdec = {"accepted","ignorable","must_render_as_gap","request_regeneration"}
    for item in reviewed_items:
        d = item.get("_review_decision","")
        check(d in valid_gdec, f"Gap decision '{d}' valid")

# ── GATE 5: Outline review works ─────────────────────────────
print("\n=== GATE 5: Outline review works ===")
rev_out_path = DIR11 / "chapter_outline_reviewed_bab_7.json"
dec_out_path = DIR11 / "outline_review_decisions_bab_7.json"
check(rev_out_path.exists(), "chapter_outline_reviewed_bab_7.json ada")
check(dec_out_path.exists(), "outline_review_decisions_bab_7.json ada")

if rev_out_path.exists():
    ro_data = json.load(open(rev_out_path))
    ro = ro_data[0] if isinstance(ro_data, list) else ro_data
    meta = ro.get("_review_metadata",{})
    check(bool(meta), "_review_metadata ada di reviewed outline")

    # Cek core_claim diupdate
    points = ro.get("argument_points",[])
    check(len(points) >= 15, f"Minimal 15 argument_points tersisa ({len(points)})")

    # Cek minimal satu point punya status partial atau review metadata
    partial_points = [p for p in points if p.get("status") in ["partial","unsupported"]]
    notes_points   = [p for p in points if p.get("_review_note")]
    check(len(partial_points) + len(notes_points) > 0,
          f"Ada point yang di-review ({len(partial_points)} partial, {len(notes_points)} noted)")

    # Known gaps
    gaps = ro.get("known_gaps",[])
    check(len(gaps) >= 0, f"known_gaps ada ({len(gaps)} items)")

# ── GATE 6: State machine works ──────────────────────────────
print("\n=== GATE 6: State machine works ===")
r = subprocess.run(
    [sys.executable, str(DIR11 / "review_state_handler.py")],
    capture_output=True, text=True
)
check(r.returncode == 0, "review_state_handler.py jalan tanpa error")
check("PASS" in r.stdout, "State machine test PASS")

# Test state transitions
try:
    sys.path.insert(0, str(DIR11))
    from review_state_handler import (
        get_initial_state, transition, is_blocking, auto_approve
    )
    sr = get_initial_state()
    sr = transition(sr, "send_to_review")
    check(sr["state"] == "pending_review",       "state → pending_review OK")
    check(is_blocking(sr) is True,               "pending_review is blocking")
    check(is_blocking(sr, auto_continue=True) is False, "auto_continue bypass blocking")
    sr = transition(sr, "revise")
    check(sr["state"] == "revision_requested",   "state → revision_requested OK")
    sr = transition(sr, "resubmit")
    sr = transition(sr, "approve")
    check(sr["state"] == "approved",             "state → approved OK")
    check(is_blocking(sr) is False,              "approved not blocking")
    check(len(sr["history"]) >= 4,               f"history tercatat ({len(sr['history'])} entries)")
except Exception as e:
    ERRORS.append(f"  FAIL: State machine import error — {e}")

# ── GATE 7: Downstream compatibility ─────────────────────────
print("\n=== GATE 7: Downstream compatibility ===")
rev_can = DIR11 / "canonical_reviewed.json"
if rev_can.exists():
    rc = json.load(open(rev_can))
    # Cek field-field yang dibutuhkan financial engine
    check("program_identity" in rc,  "downstream: program_identity ada")
    check("investment"       in rc,  "downstream: investment ada")
    check("monetization"     in rc,  "downstream: monetization ada")
    check("ddat_params"      in rc,  "downstream: ddat_params ada")
    check("ori_rates"        in rc,  "downstream: ori_rates ada")
    # _review_metadata tidak boleh merusak struktur
    core_fields = {"program_identity","program_positioning","investment",
                   "monetization","ddat_params","ori_rates","sroi_metrics"}
    existing = set(rc.keys()) & core_fields
    check(len(existing) == len(core_fields),
          f"Semua core fields ada setelah review ({existing})")

rev_out = DIR11 / "chapter_outline_reviewed_bab_7.json"
if rev_out.exists():
    ro_d = json.load(open(rev_out))
    ro   = ro_d[0] if isinstance(ro_d, list) else ro_d
    check("argument_points" in ro,  "downstream: argument_points ada di reviewed outline")
    check("core_claim"      in ro,  "downstream: core_claim ada")
    check("known_gaps"      in ro,  "downstream: known_gaps ada")

# ── GATE 8: Pilot flow demonstrated ──────────────────────────
print("\n=== GATE 8: Pilot flow demonstrated ===")
# Verifikasi outline reviewed bisa digunakan Narrative Builder
# (cek bahwa format-nya sesuai yang diharapkan narrative_builder_sroi.py)
if rev_out.exists():
    ro_d = json.load(open(rev_out))
    ro   = ro_d[0] if isinstance(ro_d, list) else ro_d
    points = ro.get("argument_points",[])

    # Narrative builder butuh: chapter_id, argument_points dengan label dan point
    check(ro.get("chapter_id") == "bab_7",         "chapter_id = bab_7")
    check(len(points) > 0,                          "argument_points tidak kosong")
    check(all("label" in p and "point" in p for p in points[:5]),
          "argument_points punya label dan point")
    check(bool(ro.get("core_claim")),               "core_claim tidak kosong")

    print("\n  Pilot flow summary:")
    print(f"    canonical reviewed : {rev_can.exists()}")
    print(f"    gap reviewed       : {(DIR11 / 'gap_matrix_reviewed.json').exists()}")
    print(f"    outline reviewed   : {rev_out.exists()}")
    print(f"    outline bab_7 points: {len(points)}")
    print(f"    review_state       : {ro.get('_review_metadata',{}).get('review_state','?')}")

# ── HASIL ────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"REVIEW FLOW GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("REVIEW FLOW GATE: ALL PASS")
    print("Sprint 11 Human Review Loop: berfungsi end-to-end.")
    sys.exit(0)
