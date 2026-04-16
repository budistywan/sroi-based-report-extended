"""
paragraph_style_packet_exporter.py — Sprint 14D Komponen 2
Mengubah paragraf needs_review/flagged dari evaluation report
menjadi style packets (Sprint 13 schema compatible).

Usage:
  python paragraph_style_packet_exporter.py --report style_evaluation_report_bab_7.json
  python paragraph_style_packet_exporter.py --report /p/ --output /p/
"""

import json, sys, os, argparse, uuid
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--report",  default=None)
parser.add_argument("--output",  default=None)
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
REPORT_FILE  = Path(args.report) if args.report \
    else SCRIPT_DIR / "style_evaluation_report_bab_7.json"
OUTPUT_DIR   = Path(args.output) if args.output else SCRIPT_DIR

if not REPORT_FILE.exists():
    print(f"FAIL: {REPORT_FILE} tidak ditemukan"); sys.exit(1)

report      = json.load(open(REPORT_FILE))
chapter_id  = report["chapter_id"]
register    = report["register_used"]
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

APPLICABILITY = "ESL_Pertamina_2025"
NOW           = datetime.now().isoformat()

# Map gap dimensions ke refinement_type labels
REFINEMENT_TYPE_MAP = {
    "opening_pattern":   "opening_refine",
    "hedging_violation": "hedging_adjustment",
    "closing_pattern":   "closing_lock",
    "disliked_pattern":  "pattern_removal",
    "sentence_rhythm":   "rhythm_adjustment",
}

def gaps_to_refinement_types(gaps: list) -> list:
    types = set()
    for g in gaps:
        dim = g.get("dimension","")
        if dim in REFINEMENT_TYPE_MAP:
            types.add(REFINEMENT_TYPE_MAP[dim])
        # Infer transition if multiple gaps
    if len(gaps) >= 2:
        types.add("transition_smooth")
    return sorted(types)

def build_decision_prompt(gaps: list, register: str, text_preview: str) -> str:
    gap_descs = [g.get("note","") for g in gaps if g.get("severity") in ["high","medium"]]
    issues    = "; ".join(gap_descs[:2]) if gap_descs else "beberapa aspek gaya perlu peninjauan"
    return (
        f"Paragraf ini dievaluasi menggunakan {register}. "
        f"Gap terdeteksi: {issues}. "
        f"Apakah teks perlu disesuaikan, atau pola ini disengaja dalam konteks ini?"
    )

def build_packet(block: dict, register: str, chapter_id: str) -> dict:
    gaps         = block.get("gaps",[])
    # Gunakan full text jika tersedia — text_preview bisa terpotong
    text         = block.get("full_text") or block.get("text_preview","")
    candidate    = block.get("candidate_revision")
    cand_conf    = block.get("candidate_confidence", 0.0)
    diagnosis    = block.get("stylistic_diagnosis","")
    ref_types    = gaps_to_refinement_types(gaps)
    has_high     = any(g["severity"] == "high" for g in gaps)

    return {
        "packet_id":        f"sp14d_{uuid.uuid4().hex[:8]}",
        "packet_type":      "style_review",
        "target_id":        f"{chapter_id}.block_{block['block_index']}",
        "scope": {
            "allowed_changes":  ["text_only","wording","tone","opening","closing","transition"],
            "forbidden_changes":["numeric_values","sroi_values","financial_fields",
                                 "argument_structure","data_status","proxy_labels",
                                 "evidence_refs","claim_scope"],
        },
        "decision_prompt":  build_decision_prompt(gaps, register, text),
        "context": {
            "current_text":            text,
            "candidate_revision":      candidate,
            "candidate_confidence":    cand_conf,
            "stylistic_diagnosis":     diagnosis,
            "gaps_detected":           gaps,
            "register":                register,
            "source":                  "paragraph_style_evaluator",
            "confidence":              round(1.0 - (0.1 * len(gaps)), 2),
            "relevant_history":        "Sprint 14A–C: style profile + signature reviewed",
            "applicability_context":   APPLICABILITY,
        },
        "refinement_type":   ref_types,
        "priority":          "high" if has_high else "medium",
        "decision_options":  ["accept_candidate","keep_original","revise_with_text"],
        "decision":          None,
        "revised_text":      None,
        "reviewer_note":     None,
        "reviewed_at":       None,
    }

# Build packets from needs_review and flagged
exportable = [b for b in report["paragraphs"]
              if b["status"] in ["needs_review","flagged"]]
packets    = [build_packet(b, register, chapter_id) for b in exportable]

out_path = OUTPUT_DIR / f"paragraph_style_packets_{chapter_id}.json"
json.dump(packets, open(out_path,"w"), indent=2, ensure_ascii=False)

print(f"Packets: {len(packets)}")
for p in packets:
    print(f"  {p['packet_id']}: {p['target_id']} [{p['priority']}] types={p['refinement_type']}")
print(f"Output: {out_path}")
print("PACKET EXPORTER COMPLETE")
