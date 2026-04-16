"""
outline_review_handler.py — Sprint 11D
Handler untuk review chapter outline (titik paling penting).

Usage:
  python outline_review_handler.py --mode view \
      --outline /path/chapter_outline_bab7.json --output /path/

  python outline_review_handler.py --mode apply \
      --outline /path/ --decisions /path/ --output /path/
"""

import json, sys, os, argparse, uuid, copy
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--mode",      choices=["view","apply"], default="view")
parser.add_argument("--outline",   default=None)
parser.add_argument("--decisions", default=None)
parser.add_argument("--output",    default=None)
parser.add_argument("--chapter",   default="bab_7", help="chapter_id untuk filter")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
OUTLINE_FILE = Path(args.outline) if args.outline \
    else Path(os.environ.get("OUTLINE_FILE",
              SCRIPT_DIR.parent / "sprint3/chapter_outline_bab7.json"))
OUTPUT_DIR   = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))
CHAPTER_ID   = args.chapter

if not OUTLINE_FILE.exists():
    print(f"FAIL: {OUTLINE_FILE} tidak ditemukan"); sys.exit(1)

raw    = json.load(open(OUTLINE_FILE))
outlines = raw if isinstance(raw, list) else [raw]
chapter  = next((o for o in outlines if o.get("chapter_id") == CHAPTER_ID), None)
if not chapter:
    # Fallback: ambil chapter pertama
    chapter = outlines[0] if outlines else {}
    print(f"  Warning: {CHAPTER_ID} tidak ditemukan, pakai {chapter.get('chapter_id','?')}")


def generate_outline_view(chapter: dict) -> dict:
    points = chapter.get("argument_points", [])
    gaps   = chapter.get("known_gaps", [])
    fin_refs = chapter.get("financial_refs", [])

    # Summarize per point
    point_views = []
    for p in points:
        point_views.append({
            "label":      p.get("label","?"),
            "point":      p.get("point","")[:100] + "..." if len(p.get("point","")) > 100 else p.get("point",""),
            "is_proxy":   p.get("is_proxy", False),
            "status":     p.get("status","supported"),
            "fin_ref":    p.get("fin_ref",""),
            "available_actions": [
                "approve",
                "set_status_partial",
                "set_status_unsupported",
                "revise_text",
                "add_note",
                "remove",
            ],
            "current_review": None,
        })

    return {
        "view_type":    "outline_review",
        "chapter_id":   chapter.get("chapter_id","?"),
        "chapter_title":chapter.get("chapter_title",""),
        "generated_at": datetime.now().isoformat(),
        "review_state": "pending_review",

        "core_claim": {
            "text":    chapter.get("core_claim",""),
            "ref":     chapter.get("core_claim_ref",""),
            "current_review": None,
            "available_actions": ["approve","revise_text"],
        },

        "purpose": chapter.get("purpose",""),

        "argument_points_summary": {
            "total":         len(points),
            "proxy_points":  sum(1 for p in points if p.get("is_proxy")),
            "points":        point_views,
        },

        "known_gaps": gaps,

        "financial_refs_count": len(fin_refs),

        "review_prompts": [
            "Apakah core_claim sudah mencerminkan SROI final yang disepakati?",
            "Apakah ada argument point yang terlalu kuat klaimnya dan perlu diturunkan?",
            "Apakah known_gaps sudah lengkap atau ada gap yang belum tercatat?",
            "Apakah point proxy (REINT, CONF) sudah diberi tanda is_proxy = True?",
            "Apakah urutan argument_points sudah logis dari input → output → outcome → dampak?",
        ],

        "available_decisions":["approve","approve_with_notes","revise","defer"],
    }


def apply_outline_decisions(chapter: dict, decisions: dict) -> dict:
    reviewed = copy.deepcopy(chapter)
    changes  = decisions.get("changes", [])
    log      = []

    for change in changes:
        ct = change.get("change_type","")
        fp = change.get("field_path","")

        if ct == "replace_value":
            # Handle special paths: core_claim, argument_points.label.point, dll
            if fp == "core_claim":
                old = reviewed.get("core_claim","")
                reviewed["core_claim"] = change.get("new_value","")
                log.append(f"replace core_claim: '{old[:40]}...' → '{reviewed['core_claim'][:40]}...'")

            elif fp.startswith("argument_points."):
                # Format: argument_points.7.1.status
                parts = fp.split(".")
                if len(parts) >= 3:
                    label = parts[1] + "." + parts[2]  # e.g. "7.1"
                    field = parts[3] if len(parts) > 3 else "status"
                    for p in reviewed.get("argument_points",[]):
                        if p.get("label") == label:
                            old = p.get(field)
                            p[field] = change.get("new_value", change.get("new_status"))
                            log.append(f"replace {fp}: {old!r} → {p[field]!r}")

            else:
                # Generic path
                try:
                    keys = fp.split(".")
                    obj = reviewed
                    for k in keys[:-1]:
                        obj = obj[k]
                    old = obj.get(keys[-1])
                    obj[keys[-1]] = change.get("new_value")
                    log.append(f"replace {fp}: {old!r} → {obj[keys[-1]]!r}")
                except Exception as e:
                    log.append(f"replace FAILED: {fp} — {e}")

        elif ct == "set_status":
            label = change.get("field_path","").replace("argument_points.","")
            for p in reviewed.get("argument_points",[]):
                if p.get("label") == label or fp == f"argument_points.{p.get('label','')}":
                    old_status = p.get("status","supported")
                    p["status"] = change.get("new_status","partial")
                    log.append(f"set_status point {p['label']}: {old_status} → {p['status']}")

        elif ct == "append_note":
            label = fp.replace("argument_points.","")
            for p in reviewed.get("argument_points",[]):
                if p.get("label") == label:
                    p["_review_note"] = change.get("note","")
                    log.append(f"append_note: {p['label']} += {change.get('note','')[:40]}")

        elif ct == "mark_as_gap":
            # Tambah ke known_gaps
            gap_entry = {
                "gap_id":    f"gap_review_{uuid.uuid4().hex[:4]}",
                "field":     fp,
                "gap_type":  change.get("gap_type","data_unavailable"),
                "note":      change.get("note",""),
                "_from_review": True,
            }
            reviewed.setdefault("known_gaps",[]).append(gap_entry)
            log.append(f"mark_as_gap: {fp} added to known_gaps")

        elif ct == "approve_without_change":
            log.append(f"approve_without_change: {fp}")

        elif ct == "request_regeneration":
            reviewed["_regen_request"] = {
                "target":      change.get("target_id",""),
                "instruction": change.get("instruction",""),
                "timestamp":   datetime.now().isoformat(),
            }
            log.append(f"request_regeneration: {change.get('target_id','?')}")

    # Tambah metadata review
    reviewed["_review_metadata"] = {
        "reviewed_at":      datetime.now().isoformat(),
        "reviewer":         decisions.get("reviewer","user"),
        "decision":         decisions.get("decision","approve"),
        "changes_count":    len(changes),
        "applied_log":      log,
        "source_review_id": decisions.get("review_id",""),
        "review_state":     "approved" if decisions.get("decision","").startswith("approve") else "revision_requested",
    }

    return reviewed, log


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if args.mode == "view":
    view = generate_outline_view(chapter)
    cid  = chapter.get("chapter_id","bab_x")
    view_path = OUTPUT_DIR / f"outline_review_view_{cid}.json"
    json.dump(view, open(view_path,"w"), indent=2, ensure_ascii=False)
    print(f"View: {view_path}")

    # Sample decisions — perubahan konkret pada core_claim dan satu argument point
    sample = {
        "review_id":          str(uuid.uuid4())[:8],
        "review_target_type": "outline",
        "review_target_id":   cid,
        "program_code":       "ESL",
        "decision":           "approve_with_notes",
        "pipeline_gate":      "review_point_b",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              "Outline bab_7 disetujui — core_claim disesuaikan ke SROI 1:1.03 (pipeline value), point REINT/CONF ditandai partial",
        "changes": [
            {
                "change_type": "replace_value",
                "field_path":  "core_claim",
                "old_value":   chapter.get("core_claim","")[:60],
                "new_value":   "Program ESL menghasilkan SROI blended 1 : 1.03 (evaluatif, DDAT-adjusted, ORI-compounded) selama periode 2023–2025 — setiap Rp 1 investasi menghasilkan Rp 1.03 nilai sosial-ekonomi terukur.",
                "reason":      "Sesuaikan ke angka pipeline final, bukan nilai manual awal"
            },
            {
                "change_type": "set_status",
                "field_path":  "argument_points.7.5.3",
                "new_status":  "partial",
                "reason":      "REINT masih proxy — belum diverifikasi survei peserta"
            },
            {
                "change_type": "mark_as_gap",
                "field_path":  "participant_verification",
                "gap_type":    "pending_field_validation",
                "note":        "Jumlah peserta 70/70/80 belum dikonfirmasi dari data absensi"
            }
        ]
    }
    dec_path = OUTPUT_DIR / f"outline_review_decisions_{cid}.json"
    json.dump(sample, open(dec_path,"w"), indent=2, ensure_ascii=False)
    print(f"Sample decisions: {dec_path}")

    points = chapter.get("argument_points",[])
    print(f"\nOutline {cid}: {len(points)} points")
    print(f"Core claim: {chapter.get('core_claim','')[:60]}...")

elif args.mode == "apply":
    if not args.decisions:
        print("FAIL: --decisions wajib untuk mode apply"); sys.exit(1)
    dec_path = Path(args.decisions)
    if not dec_path.exists():
        print(f"FAIL: {dec_path} tidak ditemukan"); sys.exit(1)

    decisions = json.load(open(dec_path))
    reviewed, log = apply_outline_decisions(chapter, decisions)

    cid      = chapter.get("chapter_id","bab_x")
    out_path = OUTPUT_DIR / f"chapter_outline_reviewed_{cid}.json"
    json.dump([reviewed], open(out_path,"w"), indent=2, ensure_ascii=False)
    print(f"Reviewed outline: {out_path}")
    print(f"Changes applied: {len(log)}")
    for entry in log:
        print(f"  → {entry}")

print("\noutline_review_handler: OK")
