"""
review.py — Sprint 11F
CLI Human Review Interface untuk SROI pipeline.

Usage:
  python review.py --type canonical --input canonical_review_view.json
  python review.py --type outline --chapter bab_7 --input outline_review_view_bab_7.json
  python review.py --type gap --input gap_review_view.json

  # Non-interactive (pakai existing decisions file)
  python review.py --type canonical --input view.json --decisions decisions.json --apply
"""

import json, sys, os, argparse, uuid
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser(description="SROI Human Review CLI")
parser.add_argument("--type",      choices=["canonical","outline","gap"], required=True)
parser.add_argument("--input",     default=None, help="Path ke review view JSON")
parser.add_argument("--decisions", default=None, help="Path ke existing decisions JSON")
parser.add_argument("--apply",     action="store_true", help="Apply decisions langsung")
parser.add_argument("--output",    default=None)
parser.add_argument("--chapter",   default="bab_7")
parser.add_argument("--auto",      action="store_true", help="Auto-approve semua (non-interactive)")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(args.output) if args.output else SCRIPT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── TERMINAL HELPERS ──────────────────────────────────────────
def hr(char="─", width=60): return char * width
def header(text):           print(f"\n{hr('═')}\n  {text}\n{hr('═')}")
def section(text):          print(f"\n{hr()}\n  {text}")
def prompt(text):           return input(f"\n  → {text}: ").strip()
def info(text):             print(f"    {text}")
def ok(text):               print(f"  ✓ {text}")
def warn(text):             print(f"  ⚠ {text}")


def auto_approve_session(view: dict, review_type: str) -> dict:
    """Auto-approve tanpa interaksi."""
    return {
        "review_id":          uuid.uuid4().hex[:8],
        "review_target_type": review_type,
        "review_target_id":   view.get("chapter_id") or view.get("program_code") or "all",
        "program_code":       "ESL",
        "decision":           "approve",
        "pipeline_gate":      "review_point_a" if review_type in ["canonical","gap"] else "review_point_b",
        "reviewer":           "auto",
        "timestamp":          datetime.now().isoformat(),
        "notes":              "Auto-approved — --auto flag set",
        "changes":            [{"change_type":"approve_without_change","field_path":"*"}],
        "review_state":       "approved",
    }


# ══════════════════════════════════════════════════════════════
# CANONICAL REVIEW
# ══════════════════════════════════════════════════════════════
def review_canonical(view: dict) -> dict:
    header("CANONICAL REVIEW — " + view.get("program_code","?"))

    # Program identity
    section("Program Identity")
    pi = view.get("program_identity_summary",{})
    info(f"Program Name : {pi.get('program_name','?')}")
    info(f"Tagline      : {pi.get('program_tagline','?')}")
    info(f"Company      : {pi.get('company','?')}")
    info(f"Period       : {pi.get('period','?')}")

    # Key metrics
    section("Key Metrics")
    km = view.get("key_metrics",{})
    info(f"SROI blended    : {km.get('sroi_blended','?')} [{km.get('sroi_blended_status','?')}]")
    inv = km.get("total_investment_idr",0)
    info(f"Total investasi : Rp {int(inv):,}" if inv else "Total investasi : ?")
    nc  = km.get("net_compounded_idr",0)
    if nc: info(f"Net compounded  : Rp {int(nc):,}")

    # Investment summary
    section("Investment Summary")
    is_ = view.get("investment_summary",{})
    info(f"Statuses: {is_.get('statuses',[])} | Items: {is_.get('items',0)}")
    if is_.get("note"):
        warn(is_["note"])

    # Coverage
    section("Coverage Status per Bab")
    for bab, cv in view.get("coverage_status",{}).items():
        sym = "✓" if cv["status"]=="strong" else "~" if cv["status"] in ["partial","weak"] else "✗"
        info(f"  {sym} {bab}: {cv['status']} [{cv['risk']}]")

    # Review prompts
    section("Review Prompts")
    for i, q in enumerate(view.get("review_prompts",[]), 1):
        info(f"  {i}. {q}")

    print()
    decision = prompt("Decision [approve/approve_with_notes/revise/defer]") or "approve"
    notes    = prompt("Notes (kosong = skip)") or ""

    changes = []
    if decision in ["revise","approve_with_notes"]:
        print("\n  Masukkan perubahan (ketik 'done' untuk selesai):")
        while True:
            ct = prompt("change_type [replace_value/set_status/append_note/done]")
            if ct == "done" or not ct: break
            fp = prompt("field_path (contoh: program_identity.program_name)")
            if ct == "replace_value":
                nv = prompt("new_value")
                re = prompt("reason (opsional)")
                changes.append({"change_type":ct,"field_path":fp,"new_value":nv,"reason":re})
            elif ct == "set_status":
                ns = prompt("new_status [proxy/pending/under_confirmation/final]")
                changes.append({"change_type":ct,"field_path":fp,"new_status":ns})
            elif ct == "append_note":
                note = prompt("note")
                changes.append({"change_type":ct,"field_path":fp,"note":note})

    return {
        "review_id":          uuid.uuid4().hex[:8],
        "review_target_type": "canonical",
        "review_target_id":   view.get("program_code","?"),
        "program_code":       view.get("program_code","?"),
        "decision":           decision,
        "pipeline_gate":      "review_point_a",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              notes,
        "changes":            changes,
        "review_state":       "approved" if decision.startswith("approve") else "revision_requested",
    }


# ══════════════════════════════════════════════════════════════
# GAP REVIEW
# ══════════════════════════════════════════════════════════════
def review_gap(view: dict) -> dict:
    header("GAP MATRIX REVIEW")

    section(f"Gap items: {view.get('total_gaps',0)}")
    for item in view.get("gap_items",[]):
        info(f"  [{item['chapter_id']}] {item['chapter_title']}")
        info(f"    status: {item['status']} | recommendation: {item.get('recommendation','?')}")
        if item.get("note"):
            info(f"    note: {item['note']}")

    section("Review Prompts")
    for q in view.get("review_prompts",[]):
        info(f"  • {q}")

    print()
    decision = prompt("Decision [approve/approve_with_notes/revise/defer]") or "approve"
    notes    = prompt("Notes (kosong = skip)") or ""

    changes = []
    for item in view.get("gap_items",[]):
        cid = item["chapter_id"]
        print(f"\n  Gap [{cid}] — tindakan:")
        print(f"    1. accepted (terima apa adanya)")
        print(f"    2. ignorable (abaikan — tidak material)")
        print(f"    3. must_render_as_gap (harus muncul eksplisit)")
        print(f"    4. skip")
        act = prompt(f"Pilih tindakan untuk {cid} [1/2/3/4]") or "4"
        if act == "1":
            changes.append({"change_type":"approve_without_change","field_path":cid})
        elif act == "2":
            changes.append({"change_type":"set_status","field_path":cid,"new_status":"ignorable"})
        elif act == "3":
            note = prompt("Catatan gap (opsional)")
            changes.append({"change_type":"mark_as_gap","field_path":cid,
                            "gap_type":"data_unavailable","note":note})

    return {
        "review_id":          uuid.uuid4().hex[:8],
        "review_target_type": "gap_matrix",
        "review_target_id":   "all_babs",
        "decision":           decision,
        "pipeline_gate":      "review_point_a",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              notes,
        "changes":            changes,
        "review_state":       "approved" if decision.startswith("approve") else "revision_requested",
    }


# ══════════════════════════════════════════════════════════════
# OUTLINE REVIEW
# ══════════════════════════════════════════════════════════════
def review_outline(view: dict) -> dict:
    cid = view.get("chapter_id","?")
    header(f"OUTLINE REVIEW — {cid.upper()}")

    info(f"Chapter  : {view.get('chapter_title','?')}")
    info(f"Purpose  : {view.get('purpose','?')}")

    section("Core Claim")
    info(f"  {view.get('core_claim',{}).get('text','?')[:100]}...")

    section(f"Argument Points ({view.get('argument_points_summary',{}).get('total',0)} total)")
    for p in view.get("argument_points_summary",{}).get("points",[])[:8]:
        proxy = " [PROXY]" if p.get("is_proxy") else ""
        info(f"  {p['label']}: {p['point'][:60]}...{proxy}")
    if view.get("argument_points_summary",{}).get("total",0) > 8:
        info(f"  ... dan {view['argument_points_summary']['total']-8} point lainnya")

    section("Known Gaps")
    gaps = view.get("known_gaps",[])
    if gaps:
        for g in gaps:
            info(f"  • {g.get('field','')} [{g.get('gap_type','?')}]")
    else:
        info("  (tidak ada known gaps)")

    section("Review Prompts")
    for q in view.get("review_prompts",[]):
        info(f"  • {q}")

    print()
    decision = prompt("Decision [approve/approve_with_notes/revise/defer]") or "approve"
    notes    = prompt("Notes (kosong = skip)") or ""

    changes = []
    if decision in ["revise","approve_with_notes"]:
        revise_cc = prompt("Revisi core_claim? [y/N]")
        if revise_cc.lower() == "y":
            new_cc = prompt("Core claim baru")
            old_cc = view.get("core_claim",{}).get("text","")
            changes.append({
                "change_type": "replace_value",
                "field_path":  "core_claim",
                "old_value":   old_cc[:60],
                "new_value":   new_cc,
                "reason":      "User revision",
            })

        point_revise = prompt("Revisi status argument point? [y/N]")
        if point_revise.lower() == "y":
            label = prompt("Label point (contoh: 7.5.3)")
            status = prompt("Status baru [partial/unsupported]")
            reason = prompt("Alasan")
            changes.append({
                "change_type": "set_status",
                "field_path":  f"argument_points.{label}",
                "new_status":  status,
                "reason":      reason,
            })

        add_gap = prompt("Tambah known_gap baru? [y/N]")
        if add_gap.lower() == "y":
            fp   = prompt("field_path gap")
            gt   = prompt("gap_type [data_unavailable/evidence_insufficient/pending_field_validation]")
            note = prompt("note")
            changes.append({
                "change_type": "mark_as_gap",
                "field_path":  fp,
                "gap_type":    gt,
                "note":        note,
            })

    return {
        "review_id":          uuid.uuid4().hex[:8],
        "review_target_type": "outline",
        "review_target_id":   cid,
        "program_code":       "ESL",
        "decision":           decision,
        "pipeline_gate":      "review_point_b",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              notes,
        "changes":            changes,
        "review_state":       "approved" if decision.startswith("approve") else "revision_requested",
    }


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if not args.input:
    # Default paths
    defaults = {
        "canonical": SCRIPT_DIR / "canonical_review_view.json",
        "gap":       SCRIPT_DIR / "gap_review_view.json",
        "outline":   SCRIPT_DIR / f"outline_review_view_bab_7.json",
    }
    args.input = str(defaults.get(args.type, ""))

if not args.input or not Path(args.input).exists():
    print(f"FAIL: input view file tidak ditemukan: {args.input}")
    print(f"Jalankan handler terlebih dahulu:")
    print(f"  python {args.type}_review_handler.py --mode view --output {SCRIPT_DIR}")
    sys.exit(1)

view = json.load(open(args.input))

# Jika --auto → auto-approve tanpa interaksi
if args.auto:
    decisions = auto_approve_session(view, args.type)
    ok(f"Auto-approved: {args.type}")
elif args.decisions and Path(args.decisions).exists() and not args.apply:
    # Load existing decisions
    decisions = json.load(open(args.decisions))
    print(f"Loaded existing decisions: {decisions.get('decision','?')}")
else:
    # Interactive review
    try:
        HANDLERS = {
            "canonical": review_canonical,
            "gap":       review_gap,
            "outline":   review_outline,
        }
        decisions = HANDLERS[args.type](view)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Review dibatalkan.")
        sys.exit(0)

# Simpan decisions
dec_filename = {
    "canonical": "canonical_review_decisions.json",
    "gap":       "gap_review_decisions.json",
    "outline":   f"outline_review_decisions_{view.get('chapter_id','bab_7')}.json",
}
dec_path = OUTPUT_DIR / dec_filename.get(args.type, "review_decisions.json")
json.dump(decisions, open(dec_path,"w"), indent=2, ensure_ascii=False)
ok(f"Decisions saved: {dec_path}")

# Jika --apply → langsung apply
if args.apply or args.auto:
    import subprocess
    handler_map = {
        "canonical": "canonical_review_handler.py",
        "gap":       "gap_review_handler.py",
        "outline":   "outline_review_handler.py",
    }
    handler = str(SCRIPT_DIR / handler_map[args.type])

    # Determine canonical/gap/outline source
    sources = {
        "canonical": str(SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"),
        "gap":       str(SCRIPT_DIR.parent / "sprint2/gap_matrix.json"),
        "outline":   str(SCRIPT_DIR.parent / "sprint3/chapter_outline_bab7.json"),
    }
    flag_map = {"canonical":"--canonical","gap":"--gap","outline":"--outline"}

    cmd = [sys.executable, handler, "--mode","apply",
           flag_map[args.type], sources[args.type],
           "--decisions", str(dec_path),
           "--output", str(OUTPUT_DIR)]
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        ok(f"Reviewed {args.type} generated")
    else:
        print(f"FAIL: apply step exited {result.returncode}")

print(f"\n  Review {args.type}: {decisions.get('decision','?')} [{decisions.get('review_state','?')}]")
