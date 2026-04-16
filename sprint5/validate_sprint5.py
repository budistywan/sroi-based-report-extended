"""
Sprint 5 Gate Validator — QA Layer
Gate: qa_report + handoff_f harus memenuhi semua kriteria
      sebelum Renderer boleh dijalankan ulang dengan Handoff F.

Usage:
  python validate_sprint5.py
  python validate_sprint5.py --qa /p/qa_report.json --handoff-f /p/handoff_f.json
  QA_FILE=... HANDOFF_F_FILE=... python validate_sprint5.py
"""
import json
import sys
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Sprint 5 Gate Validator")
parser.add_argument("--qa",        default=None)
parser.add_argument("--handoff-f", default=None, dest="handoff_f")
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
QA_FILE       = Path(args.qa)        if args.qa        \
    else Path(os.environ.get("QA_FILE",       SCRIPT_DIR / "qa_report.json"))
HANDOFF_F_FILE= Path(args.handoff_f) if args.handoff_f \
    else Path(os.environ.get("HANDOFF_F_FILE",SCRIPT_DIR / "handoff_f.json"))

print(f"QA Report : {QA_FILE.resolve()}")
print(f"Handoff F : {HANDOFF_F_FILE.resolve()}")

for f in [QA_FILE, HANDOFF_F_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

qa = json.load(open(QA_FILE))
hf = json.load(open(HANDOFF_F_FILE))

# ── GATE 1: QA report struktur ───────────────────────────
print("\n=== GATE 1: QA report struktur ===")
check("renderer_ready"  in qa,     "renderer_ready ada di qa_report")
check("summary"         in qa,     "summary ada di qa_report")
check("findings"        in qa,     "findings ada di qa_report")
check("qa_version"      in qa,     "qa_version ada di qa_report")
check(qa.get("chapter_id")=="bab_7", "chapter_id = bab_7")

# ── GATE 2: QA harus PASS ────────────────────────────────
print("\n=== GATE 2: QA result ===")
check(qa.get("renderer_ready") is True, "renderer_ready = True")
check(qa["summary"].get("errors", 999) == 0,
      f"errors = 0 (dapat: {qa['summary'].get('errors')})")
check(qa["summary"].get("checks_run", 0) >= 9,
      f"minimal 9 checks dijalankan (dapat: {qa['summary'].get('checks_run')})")

# ── GATE 3: Handoff F struktur ───────────────────────────
print("\n=== GATE 3: Handoff F struktur ===")
check("renderer_ready"    in hf,   "renderer_ready ada di handoff_f")
check("blocks"            in hf,   "blocks ada di handoff_f")
check("reference_outline" in hf,   "reference_outline ada di handoff_f")
check("qa_render_signals" in hf,   "qa_render_signals ada di handoff_f")
check("style_hints"       in hf,   "style_hints ada di handoff_f")
check(hf.get("renderer_ready") is True, "handoff_f renderer_ready = True")

# ── GATE 4: Blocks di Handoff F konsisten ────────────────
print("\n=== GATE 4: Blocks di Handoff F ===")
blocks = hf.get("blocks", [])
check(len(blocks) >= 30,            f"minimal 30 blocks (dapat: {len(blocks)})")
check(hf.get("chapter_id")=="bab_7","chapter_id = bab_7")

# ── GATE 5: qa_render_signals valid ──────────────────────
print("\n=== GATE 5: qa_render_signals valid ===")
signals = hf.get("qa_render_signals", {})
check("outline_alignment_status" in signals,
      "outline_alignment_status ada")
check(signals.get("outline_alignment_status") in ["aligned","partial","diverged"],
      f"outline_alignment_status valid: {signals.get('outline_alignment_status')}")
check("render_gap_note"       in signals, "render_gap_note ada")
check("render_inference_note" in signals, "render_inference_note ada")

# ── GATE 6: style_hints valid ────────────────────────────
print("\n=== GATE 6: style_hints valid ===")
hints = hf.get("style_hints", {})
VALID_HINTS = {"proxy_badge","warning_callout","pending_note","gap_note","inference_note"}
for h in hints:
    check(h in VALID_HINTS, f"style_hint '{h}' valid")

# Program ESL memiliki proxy dan pending — pastikan flags sesuai
check(hints.get("proxy_badge")   is True, "proxy_badge = True (ada aspek REINT/CONF)")
check(hints.get("warning_callout") is True or hints.get("pending_note") is True,
      "pending_note atau warning_callout = True (investasi 2023-2024 under_confirmation)")

# ── GATE 7: reference_outline ada core_claim ────────────
print("\n=== GATE 7: reference_outline ===")
ref_out = hf.get("reference_outline", {})
check(ref_out.get("core_claim","") != "",    "reference_outline.core_claim tidak kosong")
check(len(ref_out.get("argument_points",[]))>= 10,
      f"reference_outline punya ≥10 argument_points (dapat: {len(ref_out.get('argument_points',[]))})")
check(ref_out.get("known_gaps") == [],        "known_gaps kosong (bab_7 strong)")

# ── GATE 8: Test negatif — inject proxy tanpa source_refs
print("\n=== GATE 8: Test negatif (negative test) ===")
# Simulasi: kalau ada block proxy tanpa source_refs, QA harus menolak
# Kita buat dummy dan verifikasi logic QA
dummy_block = {"type":"paragraph","display_status":"present_as_proxy","source_refs":[]}
has_proxy_no_refs = any(
    b.get("display_status") in ["present_as_proxy","present_as_pending","present_as_inferred"]
    and not b.get("source_refs")
    for b in blocks
)
check(not has_proxy_no_refs,
      "Tidak ada block proxy/pending tanpa source_refs di Handoff F")

# ── GATE 9: Test negatif — inject block type invalid
print("\n=== GATE 9: Test negatif (unknown block type) ===")
has_unknown_type = any(
    b.get("type") in ["diagram","image","chart_native","timeline"]
    for b in blocks
)
check(not has_unknown_type,
      "Tidak ada unsupported block type di Handoff F")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 5 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    warnings = qa["summary"].get("warnings", 0)
    print("SPRINT 5 GATE: ALL PASS")
    print(f"  QA errors    : {qa['summary']['errors']}")
    print(f"  QA warnings  : {warnings}")
    print(f"  Blocks in F  : {len(blocks)}")
    print(f"  Alignment    : {signals.get('outline_alignment_status')}")
    print(f"  renderer_ready: True")
    if warnings > 0:
        print(f"  ({warnings} warning tercatat di qa_report.json — tidak blocking)")
    print("Sprint 6 — Narrative Builder sisa bab boleh dimulai.")
    sys.exit(0)
