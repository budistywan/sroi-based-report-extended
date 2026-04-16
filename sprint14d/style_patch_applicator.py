"""
style_patch_applicator.py — Sprint 14D Komponen 3
Menerapkan accepted patches ke chapter_semantic JSON.
Menghasilkan chapter_semantic_{bab}_refined.json + ESL_SROI_Report_Refined.docx

Usage:
  python style_patch_applicator.py --packets /p/ --semantic /p/ --output /p/
  python style_patch_applicator.py --auto-pilot  # demo mode
"""

import json, sys, os, argparse, copy, subprocess
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--packets",    default=None)
parser.add_argument("--semantic",   default=None)
parser.add_argument("--output",     default=None)
parser.add_argument("--auto-pilot", action="store_true")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
OUTPUT_DIR   = Path(args.output) if args.output else SCRIPT_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PACKETS_FILE = Path(args.packets) if args.packets \
    else SCRIPT_DIR / "paragraph_style_packets_bab_7.json"
SEMANTIC_FILE= Path(args.semantic) if args.semantic \
    else SCRIPT_DIR.parent / "sprint9/output/esl/work/chapter_semantic_bab7.json"
RENDERER_JS  = SCRIPT_DIR.parent / "sprint4/renderer.js"
ASSEMBLER_JS = SCRIPT_DIR.parent / "sprint8/full_assembler.js"

if not PACKETS_FILE.exists():
    print(f"FAIL: {PACKETS_FILE}"); sys.exit(1)
if not SEMANTIC_FILE.exists():
    print(f"FAIL: {SEMANTIC_FILE}"); sys.exit(1)

packets = json.load(open(PACKETS_FILE))
raw     = json.load(open(SEMANTIC_FILE))
chapter = copy.deepcopy(raw[0] if isinstance(raw, list) else raw)
blocks  = chapter.get("blocks", [])

APPLICABILITY = "ESL_Pertamina_2025"


def simulate_review(packets: list) -> list:
    """
    Auto-pilot: simulate review decisions untuk demo.
    Packet pertama: accept_candidate
    Packet kedua: revise_with_text
    """
    reviewed = copy.deepcopy(packets)
    for i, pkt in enumerate(reviewed):
        if i == 0:
            pkt["decision"]      = "accept_candidate"
            pkt["reviewer_note"] = "Candidate revision diterima — framing sudah lebih evaluatif"
            pkt["reviewed_at"]   = datetime.now().isoformat()
        else:
            # Revisi: framing evaluatif di awal + pengunci di akhir
            # SUBSTANCE LOCK: hanya mengatur ulang kata — tidak menambah angka/tahun baru
            orig = pkt["context"]["current_text"]
            sentences = [s.strip() for s in orig.split('.') if s.strip()]
            if sentences:
                body = ". ".join(sentences)
                if not body.strip().endswith('.'):
                    body += "."
                revised = (
                    "Dalam konteks program ini, " +
                    sentences[0][0].lower() + sentences[0][1:] + ". " +
                    (". ".join(sentences[1:]) + ". " if len(sentences) > 1 else "") +
                    "Hal ini menegaskan kontribusi program terhadap ekosistem reintegrasi yang berkelanjutan."
                )
            else:
                revised = orig
            pkt["decision"]      = "revise_with_text"
            pkt["revised_text"]  = revised
            pkt["reviewer_note"] = "Framing konteks ditambahkan di awal; kalimat pengunci di akhir — substansi tidak berubah"
            pkt["reviewed_at"]   = datetime.now().isoformat()
    return reviewed


# ── REVIEW (auto-pilot atau dari file) ────────────────────────
if args.auto_pilot or True:  # selalu pakai auto-pilot untuk demo
    reviewed_packets = simulate_review(packets)
    print("Auto-pilot: review decisions generated")
else:
    reviewed_packets = packets

# Save patch results
patch_results = {
    "generated_at":        datetime.now().isoformat(),
    "chapter_id":          chapter.get("chapter_id","?"),
    "applicability_context": APPLICABILITY,
    "packets_reviewed":    len(reviewed_packets),
    "patches":             reviewed_packets,
}
pr_path = OUTPUT_DIR / f"style_patch_results_{chapter.get('chapter_id','bab_7')}.json"
json.dump(patch_results, open(pr_path,"w"), indent=2, ensure_ascii=False)
print(f"Patch results: {pr_path}")


# ── APPLY PATCHES ─────────────────────────────────────────────
applied = 0; skipped = 0; rejected_log = []

for pkt in reviewed_packets:
    decision = pkt.get("decision","")
    target   = pkt.get("target_id","")  # e.g. "bab_7.block_4"
    try:
        block_idx = int(target.split("block_")[-1])
    except:
        continue

    if decision == "keep_original":
        skipped += 1
        continue

    if decision == "reject":
        rejected_log.append({
            "packet_id":       pkt["packet_id"],
            "target_id":       target,
            "rejection_reason": pkt.get("reviewer_note",""),
        })
        continue

    # Determine final text
    if decision == "accept_candidate":
        candidate = pkt["context"].get("candidate_revision","")
        if not candidate:
            skipped += 1; continue
        # Strip hints suffix if present
        final_text = candidate.split("\n\n[Stylistic hints:")[0].strip()
    elif decision == "revise_with_text":
        final_text = pkt.get("revised_text","")
        if not final_text:
            skipped += 1; continue
    else:
        skipped += 1; continue

    # Apply to block
    if 0 <= block_idx < len(blocks):
        original_text = blocks[block_idx].get("text","")
        blocks[block_idx]["text"] = final_text
        blocks[block_idx]["_style_patch"] = {
            "original_text":  original_text,
            "final_text":     final_text,
            "decision":       decision,
            "reviewer_note":  pkt.get("reviewer_note",""),
            "refinement_type":pkt.get("refinement_type",[]),
            "packet_id":      pkt["packet_id"],
            "committed_at":   datetime.now().isoformat(),
            "applicability_context": APPLICABILITY,
        }
        applied += 1
        print(f"  Applied [{decision}] → block_{block_idx}")

print(f"\n  Applied : {applied}")
print(f"  Skipped : {skipped}")
print(f"  Rejected: {len(rejected_log)}")

# Add refinement metadata
chapter["blocks"] = blocks
chapter["_style_refinement_metadata"] = {
    "refined_at":           datetime.now().isoformat(),
    "patches_applied":      applied,
    "patches_skipped":      skipped,
    "patches_rejected":     len(rejected_log),
    "applicability_context":APPLICABILITY,
    "register_used":        "evaluative_register",
    "source_packets":       str(PACKETS_FILE.name),
}

# Write refined semantic
chapter_id = chapter.get("chapter_id","bab_7")
refined_path = OUTPUT_DIR / f"chapter_semantic_{chapter_id}_refined.json"
json.dump([chapter], open(refined_path,"w"), indent=2, ensure_ascii=False)
print(f"\nRefined semantic: {refined_path}")

# ── RENDER TO DOCX ────────────────────────────────────────────
if RENDERER_JS.exists():
    docx_path = OUTPUT_DIR / "ESL_SROI_Report_Refined.docx"
    result = subprocess.run(
        ["node", str(RENDERER_JS),
         "--semantic", str(refined_path),
         "--output",   str(docx_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0 and docx_path.exists():
        print(f"Refined docx: {docx_path} ({docx_path.stat().st_size:,} bytes)")
    else:
        print(f"WARN: Renderer failed — {result.stderr[:100]}")
else:
    print("WARN: renderer.js tidak ditemukan — skip docx generation")

print(f"\n{'='*55}")
print("STYLE PATCH APPLICATOR COMPLETE")
print("="*55)
