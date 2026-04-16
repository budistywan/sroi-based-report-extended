"""
validate_chat_patch_flow.py — Sprint 13
Gates 4-8: validator + commit + audit + context + downstream.

Usage:
  python validate_chat_patch_flow.py
  python validate_chat_patch_flow.py --dir /path/sprint13/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR13      = Path(args.dir) if args.dir else SCRIPT_DIR
DIR12      = DIR13.parent / "sprint12"

sys.path.insert(0, str(DIR13))
from chat_patch_validator import validate_patch, _contains_numeric_change

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 4: Patch validator works ────────────────────────────
print("\n=== GATE 4: Patch validator scope enforcement ===")

# Load sample packet for testing
pkt_b7_path = DIR13 / "semantic_packets_bab7.json"
if pkt_b7_path.exists():
    pkt_b7 = json.load(open(pkt_b7_path))[0]
    orig_text = pkt_b7["context"]["current_text"]

    # Test A: valid accept
    valid_p = {
        "patch_id":"v_test","source_packet_id":pkt_b7["packet_id"],
        "decision":"accept","review_basis":"terminology",
        "original_text":orig_text,"final_text":orig_text,
        "reviewer_note":"OK","rejection_reason":None,
        "timestamp":"2026-04-10T00:00:00","review_context":"Sprint13_ESL_Pilot",
        "applicability_context":"ESL_Pertamina_2025",
    }
    errs_valid = validate_patch(valid_p, pkt_b7)
    check(len(errs_valid) == 0, f"Valid accept patch passes ({errs_valid})")

    # Test B: numeric change in text_only packet
    numeric_p = dict(valid_p, patch_id="n_test", decision="revise",
                     final_text="SROI adalah 1 : 1,10 bukan yang lama")
    errs_num = validate_patch(numeric_p, pkt_b7)
    check(any("numeric" in e.lower() or "scope" in e.lower() for e in errs_num),
          f"Numeric change rejected in text_only packet")

    # Test C: missing context
    no_ctx_p = dict(valid_p, patch_id="c_test", applicability_context="")
    errs_ctx = validate_patch(no_ctx_p, pkt_b7)
    check(any("context" in e.lower() for e in errs_ctx),
          "Missing applicability_context rejected")

    # Test D: reject without reason
    bad_rej = dict(valid_p, patch_id="r_test", decision="reject",
                   rejection_reason=None)
    errs_rej = validate_patch(bad_rej, pkt_b7)
    check(any("rejection_reason" in e.lower() for e in errs_rej),
          "Reject without rejection_reason rejected")

    # Test E: invalid context (unregistered)
    bad_ctx = dict(valid_p, patch_id="bc_test", applicability_context="UNKNOWN_2099")
    errs_bctx = validate_patch(bad_ctx, pkt_b7)
    check(any("invalid_context" in e.lower() or "invalid context" in e.lower()
              or "tidak terdaftar" in e.lower() for e in errs_bctx),
          "Invalid/unregistered context rejected")

# ── GATE 5: Commit-back works ─────────────────────────────────
print("\n=== GATE 5: Commit-back artifacts ===")
for fname, label in [
    ("committed_bab4_outline.json",   "Bab IV committed"),
    ("committed_bab7_outline.json",   "Bab VII committed"),
    ("committed_closing_notes.json",  "Closing committed"),
    ("accepted_chat_patch.json",      "Accepted patches"),
    ("rejected_chat_log.json",        "Rejected log"),
]:
    check((DIR13 / fname).exists(), f"{label} ({fname}) ada")

# Cek bab4 punya _chat_review_patches
b4_path = DIR13 / "committed_bab4_outline.json"
if b4_path.exists():
    d4 = json.load(open(b4_path))
    ch4 = d4[0] if isinstance(d4,list) else d4
    patches4 = ch4.get("_chat_review_patches",[])
    check(len(patches4) > 0,            f"Bab IV punya _chat_review_patches ({len(patches4)})")
    p4 = patches4[0]
    check("original_text" in p4,        "Bab IV patch punya original_text (before)")
    check("final_text"    in p4,        "Bab IV patch punya final_text (after)")
    check("decision"      in p4,        "Bab IV patch punya decision")
    check(p4["original_text"] != p4["final_text"],
          "Bab IV: final_text berbeda dari original (revise diterapkan)")

# Cek bab7 punya _chat_review_patches (accept)
b7_path = DIR13 / "committed_bab7_outline.json"
if b7_path.exists():
    d7 = json.load(open(b7_path))
    ch7 = d7[0] if isinstance(d7,list) else d7
    patches7 = ch7.get("_chat_review_patches",[])
    check(len(patches7) > 0,  f"Bab VII punya _chat_review_patches ({len(patches7)})")
    check(patches7[0].get("decision") == "accept", "Bab VII decision = accept")

# Cek rejected log tidak mengubah outline
rej_path = DIR13 / "rejected_chat_log.json"
if rej_path.exists():
    rejlog = json.load(open(rej_path))
    check(len(rejlog) >= 1,     f"Rejected log punya entries ({len(rejlog)})")
    check(all("rejection_reason" in r or "decision" in r for r in rejlog),
          "Rejected entries punya reason atau decision")

# ── GATE 6: Audit trail ───────────────────────────────────────
print("\n=== GATE 6: Audit trail ===")
for path, label in [
    (DIR13 / "committed_bab4_outline.json", "Bab IV"),
    (DIR13 / "committed_bab7_outline.json", "Bab VII"),
]:
    if path.exists():
        d  = json.load(open(path))
        ch = d[0] if isinstance(d,list) else d
        patches = ch.get("_chat_review_patches",[])
        for p in patches[:1]:
            check("original_text"  in p, f"{label}: original_text ada (before)")
            check("final_text"     in p, f"{label}: final_text ada (after)")
            check("committed_at"   in p, f"{label}: committed_at ada")
            check("applicability_context" in p, f"{label}: applicability_context di trace")

# ── GATE 7: Context safety ────────────────────────────────────
print("\n=== GATE 7: Context safety ===")
registry_path = DIR13 / "review_context_registry.json"
check(registry_path.exists(), "review_context_registry.json ada")
if registry_path.exists():
    reg = json.load(open(registry_path))
    contexts = reg.get("contexts",[])
    check(len(contexts) >= 1,   f"Registry punya setidaknya 1 context ({len(contexts)})")
    active = [c for c in contexts if c.get("active")]
    check(len(active) >= 1,     f"Ada context yang active ({len(active)})")
    check(any(c["context_id"] == "ESL_Pertamina_2025" for c in contexts),
          "ESL_Pertamina_2025 terdaftar di registry")

# Cek semua committed artifacts punya applicability_context
for fname in ["committed_bab4_outline.json","committed_bab7_outline.json","committed_closing_notes.json"]:
    fpath = DIR13 / fname
    if fpath.exists():
        d  = json.load(open(fpath))
        ch = d[0] if isinstance(d,list) else d
        patches = ch.get("_chat_review_patches",[])
        for p in patches:
            check(bool(p.get("applicability_context")),
                  f"{fname}: patch punya applicability_context")

# ── GATE 8: Downstream compatibility ─────────────────────────
print("\n=== GATE 8: Downstream compatibility ===")
b7_path = DIR13 / "committed_bab7_outline.json"
if b7_path.exists():
    d7 = json.load(open(b7_path))
    ch7 = d7[0] if isinstance(d7,list) else d7
    check("argument_points" in ch7, "Bab VII: argument_points masih ada")
    check("core_claim"      in ch7, "Bab VII: core_claim masih ada")
    check("chapter_id"      in ch7, "Bab VII: chapter_id masih ada")
    check(ch7.get("chapter_id") == "bab_7", "Bab VII: chapter_id = bab_7")
    points = ch7.get("argument_points",[])
    check(len(points) >= 15, f"Bab VII: argument_points intact ({len(points)})")
    check(all("label" in p for p in points[:3]), "Bab VII: argument_points schema intact")

# _chat_review_patches tidak merusak schema utama
for fname in ["committed_bab4_outline.json","committed_bab7_outline.json"]:
    fpath = DIR13 / fname
    if fpath.exists():
        d  = json.load(open(fpath))
        ch = d[0] if isinstance(d,list) else d
        # Core fields tetap ada
        check("chapter_id" in ch, f"{fname}: chapter_id ada setelah commit")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"CHAT PATCH FLOW GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("CHAT PATCH FLOW GATE: ALL PASS")
    print("Sprint 13 Chat Review Bridge: berfungsi end-to-end.")
    sys.exit(0)
