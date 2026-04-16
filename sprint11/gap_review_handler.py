"""
gap_review_handler.py — Sprint 11C
Handler untuk review gap matrix.

Usage:
  python gap_review_handler.py --mode view --gap /path/gap_matrix.json --output /path/
  python gap_review_handler.py --mode apply --gap /path/ --decisions /path/ --output /path/
"""

import json, sys, os, argparse, uuid
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--mode",      choices=["view","apply"], default="view")
parser.add_argument("--gap",       default=None)
parser.add_argument("--decisions", default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR  = Path(__file__).parent
GAP_FILE    = Path(args.gap) if args.gap \
    else Path(os.environ.get("GAP_FILE",
              SCRIPT_DIR.parent / "sprint2/gap_matrix.json"))
OUTPUT_DIR  = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

if not GAP_FILE.exists():
    print(f"FAIL: {GAP_FILE} tidak ditemukan"); sys.exit(1)

gap_raw = json.load(open(GAP_FILE))
gap_list = gap_raw if isinstance(gap_raw, list) else [gap_raw]


def generate_gap_view(gap_list: list) -> dict:
    items = []
    for g in gap_list:
        cid = g.get("chapter_id","?")
        items.append({
            "chapter_id":    cid,
            "chapter_title": g.get("chapter_title",""),
            "status":        g.get("status","?"),
            "missing_fields":g.get("missing_fields",[]),
            "weak_fields":   g.get("weak_fields",[]),
            "recommendation":g.get("recommendation","?"),
            "note":          g.get("note",""),
            "current_decision": None,  # belum di-review
            "available_decisions": [
                "accepted",           # gap valid, terima apa adanya
                "ignorable",          # gap tidak material, abaikan
                "must_render_as_gap", # gap harus muncul eksplisit di laporan
                "request_regeneration"# minta regenerasi bagian ini
            ],
        })

    return {
        "view_type":    "gap_review",
        "generated_at": datetime.now().isoformat(),
        "review_state": "pending_review",
        "total_gaps":   len(items),
        "gap_items":    items,
        "review_prompts": [
            "Apakah gap di Bab IV (baseline wilayah) perlu diakui eksplisit di laporan?",
            "Apakah gap di Bab V (kondisi ideal) cukup ditangani dengan callout_gap?",
            "Apakah ada gap yang sebenarnya tidak material dan bisa diabaikan?",
            "Apakah ada gap yang perlu memicu regenerasi outline?",
        ],
    }


def apply_gap_decisions(gap_list: list, decisions: dict) -> list:
    import copy
    reviewed = copy.deepcopy(gap_list)
    changes  = decisions.get("changes", [])

    for change in changes:
        ct  = change.get("change_type","")
        cid = change.get("field_path","")  # field_path = chapter_id untuk gap

        # Cari gap yang sesuai
        target = next((g for g in reviewed if g.get("chapter_id") == cid), None)
        if not target:
            continue

        if ct == "set_status":
            target["_review_decision"] = change.get("new_status","accepted")
            target["_review_note"]     = change.get("note","")

        elif ct == "mark_as_gap":
            target["_review_decision"] = "must_render_as_gap"
            target["_gap_type"]        = change.get("gap_type","data_unavailable")
            target["_review_note"]     = change.get("note","")

        elif ct == "approve_without_change":
            target["_review_decision"] = "accepted"
            target["_review_note"]     = change.get("note","")

        elif ct == "request_regeneration":
            target["_review_decision"] = "request_regeneration"
            target["_regen_instruction"]= change.get("instruction","")

    return reviewed


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if args.mode == "view":
    view = generate_gap_view(gap_list)
    view_path = OUTPUT_DIR / "gap_review_view.json"
    json.dump(view, open(view_path,"w"), indent=2, ensure_ascii=False)
    print(f"View: {view_path}")

    # Sample decisions
    sample = {
        "review_id":          str(uuid.uuid4())[:8],
        "review_target_type": "gap_matrix",
        "review_target_id":   "all_babs",
        "decision":           "approve_with_notes",
        "pipeline_gate":      "review_point_a",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              "Gap Bab IV diakui eksplisit; Bab V cukup callout_gap",
        "changes": [
            {
                "change_type": "mark_as_gap",
                "field_path":  "bab_4",
                "gap_type":    "data_unavailable",
                "note":        "Baseline wilayah tidak tersedia — harus diakui eksplisit di laporan"
            },
            {
                "change_type": "set_status",
                "field_path":  "bab_5",
                "new_status":  "ignorable",
                "note":        "Gap kondisi ideal cukup ditangani dengan callout_gap"
            }
        ]
    }
    dec_path = OUTPUT_DIR / "gap_review_decisions.json"
    json.dump(sample, open(dec_path,"w"), indent=2, ensure_ascii=False)
    print(f"Sample decisions: {dec_path}")

    print(f"\nGap items: {len(gap_list)}")
    for g in gap_list:
        print(f"  {g['chapter_id']}: {g.get('status','?')} — {g.get('recommendation','?')}")

elif args.mode == "apply":
    if not args.decisions:
        print("FAIL: --decisions wajib untuk mode apply"); sys.exit(1)
    dec_path = Path(args.decisions)
    if not dec_path.exists():
        print(f"FAIL: {dec_path} tidak ditemukan"); sys.exit(1)

    decisions = json.load(open(dec_path))
    reviewed  = apply_gap_decisions(gap_list, decisions)

    # Tambah metadata
    meta = {
        "reviewed_at": datetime.now().isoformat(),
        "reviewer":    decisions.get("reviewer","user"),
        "decision":    decisions.get("decision",""),
        "source_review_id": decisions.get("review_id",""),
    }

    out = {"_review_metadata": meta, "gap_items": reviewed}
    out_path = OUTPUT_DIR / "gap_matrix_reviewed.json"
    json.dump(out, open(out_path,"w"), indent=2, ensure_ascii=False)
    print(f"Reviewed gap matrix: {out_path}")
    applied = [g for g in reviewed if g.get("_review_decision")]
    print(f"Decisions applied: {len(applied)}")
    for g in applied:
        print(f"  {g['chapter_id']}: {g.get('_review_decision','?')}")

print("\ngap_review_handler: OK")
