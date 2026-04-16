"""
batch_patch_merge.py — Sprint 14E
Menggabungkan refined chapter outputs menjadi full report.
Menghasilkan ESL_SROI_Full_Report_Refined.docx + merge_manifest.json

Usage:
  python batch_patch_merge.py
  python batch_patch_merge.py --apply-patches  # apply patches dulu sebelum merge
"""

import json, sys, os, argparse, subprocess, copy
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--apply-patches", action="store_true")
parser.add_argument("--output",        default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(args.output) if args.output else SCRIPT_DIR
WORK_DIR   = SCRIPT_DIR / "work"

# Look in sprint9 output (primary), output/esl/work, OR data/semantic
S9W        = next((p for p in [
    SCRIPT_DIR.parent / "sprint9/output/esl/work",
    SCRIPT_DIR.parent / "output/esl/work",
    SCRIPT_DIR.parent / "data/semantic",
] if p.exists()), SCRIPT_DIR.parent / "sprint9/output/esl/work")
S14D       = SCRIPT_DIR.parent / "sprint14d"
S8         = SCRIPT_DIR.parent / "sprint8"
S4         = SCRIPT_DIR.parent / "sprint4"
PYTHON     = sys.executable

# Guard: consistency check harus sudah ada
cons_report = WORK_DIR / "batch_consistency_report.json"
if not cons_report.exists():
    print("FAIL: batch_consistency_report.json tidak ditemukan — jalankan consistency checker dulu")
    sys.exit(1)

cons = json.load(open(cons_report))
if cons.get("merge_recommendation") == "review_warnings_before_merge":
    print(f"WARN: Consistency status '{cons['overall_status']}' — merge dilanjutkan dengan catatan")

# Load chapter status
status_file = WORK_DIR / "chapter_refinement_status.json"
status_data = json.load(open(status_file)) if status_file.exists() else {"chapters":[]}
evaluated   = {c["chapter_id"]: c for c in status_data.get("chapters",[])
               if c.get("status") == "evaluated"}

# ── APPLY PATCHES PER CHAPTER (auto-pilot mode) ──────────────
if args.apply_patches:
    print("Applying patches per chapter (auto-pilot)...")
    applicator = S14D / "style_patch_applicator.py"
    for ch_id in evaluated:
        pkt_file = WORK_DIR / f"paragraph_style_packets_{ch_id}.json"
        sem_file_candidates = [
            S9W / f"chapter_semantic_{ch_id}.json",
            S9W / "chapter_semantic_bab7.json" if ch_id == "bab_7" else None,
        ]
        sem_file = next((f for f in sem_file_candidates if f and Path(f).exists()), None)
        if not pkt_file.exists() or not sem_file:
            continue
        r = subprocess.run([
            PYTHON, str(applicator),
            "--packets",  str(pkt_file),
            "--semantic", str(sem_file),
            "--output",   str(WORK_DIR),
        ], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ✓ {ch_id} patches applied")


# ── COLLECT CHAPTER SEMANTICS ─────────────────────────────────
ALL_CHAPTERS = ["bab_1","bab_2","bab_3","bab_4","bab_5",
                "bab_6","bab_7","bab_8","bab_9"]

def find_chapter_semantic(ch_id: str) -> tuple[Path, str]:
    """Return (path, source) — refined jika ada, else original."""
    refined_candidates = [
        WORK_DIR   / f"chapter_semantic_{ch_id}_refined.json",
        S14D       / f"chapter_semantic_{ch_id}_refined.json",
    ]
    for f in refined_candidates:
        if f.exists(): return f, "refined"
    original_candidates = [
        S9W / f"chapter_semantic_{ch_id}.json",
        S9W / "chapter_semantic_bab7.json" if ch_id == "bab_7" else None,
    ]
    for f in original_candidates:
        if f and Path(f).exists(): return Path(f), "original"
    return None, "not_found"

# Build merged semantic list
merged_blocks_all = []
merge_manifest_chapters = []

for ch_id in ALL_CHAPTERS:
    sem_path, source = find_chapter_semantic(ch_id)
    merge_manifest_chapters.append({
        "chapter_id": ch_id,
        "source":     source,
        "file":       str(sem_path) if sem_path else None,
    })
    if sem_path:
        data = json.load(open(sem_path))
        ch   = data[0] if isinstance(data, list) else data
        merged_blocks_all.append(ch)
        print(f"  {ch_id}: {source} ({len(ch.get('blocks',[]))} blocks)")
    else:
        print(f"  {ch_id}: NOT FOUND — skipping")

# ── WRITE MERGED SEMANTIC ─────────────────────────────────────
merged_semantic_path = WORK_DIR / "merged_full_report_semantic.json"
json.dump(merged_blocks_all, open(merged_semantic_path,"w"),
          indent=2, ensure_ascii=False)

# ── RENDER VIA ASSEMBLER ──────────────────────────────────────
assembler  = S8 / "full_assembler.js"
docx_out   = OUTPUT_DIR / "ESL_SROI_Full_Report_Refined.docx"

if assembler.exists():
    r = subprocess.run([
        "node", str(assembler),
        "--semantic", str(merged_semantic_path),
        "--output",   str(docx_out),
    ], capture_output=True, text=True)
    if r.returncode == 0 and docx_out.exists():
        print(f"\nRefined docx: {docx_out} ({docx_out.stat().st_size:,} bytes)")
    else:
        print(f"WARN: assembler failed — {r.stderr[:100]}")
        # Fallback: use renderer on merged
        renderer = S4 / "renderer.js"
        if renderer.exists():
            r2 = subprocess.run([
                "node", str(renderer),
                "--semantic", str(merged_semantic_path),
                "--output",   str(docx_out),
            ], capture_output=True, text=True)
            if r2.returncode == 0 and docx_out.exists():
                print(f"\nRefined docx (renderer): {docx_out} ({docx_out.stat().st_size:,} bytes)")
else:
    print("WARN: assembler tidak ditemukan — skip docx render")

# ── MERGE MANIFEST ────────────────────────────────────────────
manifest = {
    "run_id":             "batch_refine_esl_v1",
    "merged_at":          datetime.now().isoformat(),
    "total_chapters":     len(ALL_CHAPTERS),
    "chapters_included":  sum(1 for c in merge_manifest_chapters if c["source"] != "not_found"),
    "merged_chapters":    merge_manifest_chapters,
    "consistency_report": "batch_consistency_report.json",
    "consistency_status": cons.get("overall_status","unknown"),
    "output_docx":        str(docx_out),
}
json.dump(manifest, open(WORK_DIR/"merge_manifest.json","w"),
          indent=2, ensure_ascii=False)

refined_count  = sum(1 for c in merge_manifest_chapters if c["source"] == "refined")
original_count = sum(1 for c in merge_manifest_chapters if c["source"] == "original")

print(f"\nMerge: {refined_count} refined + {original_count} original")
print(f"Manifest: {WORK_DIR/'merge_manifest.json'}")
print("="*55)
print("BATCH MERGE COMPLETE")
print("="*55)
