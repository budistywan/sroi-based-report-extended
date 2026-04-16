"""
batch_refinement_orchestrator.py — Sprint 14E
Control tower untuk refinement lintas bab.

Modes:
  priority_first    — priority_chapters dulu, lalu sisanya
  register_grouped  — per register family
  full_sequential   — bab_1 → bab_9

Usage:
  python batch_refinement_orchestrator.py
  python batch_refinement_orchestrator.py --config /p/config.json
  python batch_refinement_orchestrator.py --mode priority_first
"""

import json, sys, os, argparse, subprocess
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--config", default=None)
parser.add_argument("--mode",   default=None)
args = parser.parse_args()

SCRIPT_DIR  = Path(__file__).parent
CONFIG_FILE = Path(args.config) if args.config \
    else SCRIPT_DIR / "batch_refinement_config.json"

if not CONFIG_FILE.exists():
    print(f"FAIL: {CONFIG_FILE} tidak ditemukan"); sys.exit(1)

cfg = json.load(open(CONFIG_FILE))
MODE         = args.mode or cfg.get("mode", "priority_first")
CHAPTERS     = cfg.get("chapters", [])
PRIORITY     = cfg.get("priority_chapters", [])
MAX_PACKETS  = cfg.get("max_packets_per_batch", 10)
RUN_ID       = cfg.get("run_id", "batch_run")
CONTEXT      = cfg.get("applicability_context", "ESL_Pertamina_2025")

# Path resolution
BASE         = SCRIPT_DIR
S9W          = (BASE / cfg.get("semantic_dir",  "../sprint9/output/esl/work")).resolve()
S14D         = (BASE / cfg.get("sprint14d_dir", "../sprint14d")).resolve()
S14C         = (BASE / cfg.get("sprint14c_dir", "../sprint14c")).resolve()
WORK_DIR     = SCRIPT_DIR / "work"
WORK_DIR.mkdir(parents=True, exist_ok=True)

EVALUATOR    = S14D / "paragraph_style_evaluator.py"
EXPORTER     = S14D / "paragraph_style_packet_exporter.py"
APPLICATOR   = S14D / "style_patch_applicator.py"

import sys as _sys
PYTHON = _sys.executable

# ── CHAPTER ORDERING ─────────────────────────────────────────
def get_chapter_order(mode: str) -> list:
    REGISTER_GROUPS = {
        "framing_register":    ["bab_1","bab_2","bab_3"],
        "analytic_register":   ["bab_4","bab_5","bab_6"],
        "evaluative_register": ["bab_7"],
        "reflective_register": ["bab_8"],
        "conclusive_register": ["bab_9"],
    }
    if mode == "priority_first":
        remaining = [c for c in CHAPTERS if c not in PRIORITY]
        return PRIORITY + remaining
    elif mode == "register_grouped":
        ordered = []
        for reg_chs in REGISTER_GROUPS.values():
            ordered += [c for c in reg_chs if c in CHAPTERS]
        return ordered
    else:  # full_sequential
        return CHAPTERS

chapter_order = get_chapter_order(MODE)
print(f"Run ID  : {RUN_ID}")
print(f"Mode    : {MODE}")
print(f"Chapters: {chapter_order}")
print(f"Max pkts: {MAX_PACKETS} per batch\n")


# ── SEMANTIC FILE LOOKUP ──────────────────────────────────────
def find_semantic(chapter_id: str) -> Path | None:
    candidates = [
        S9W / f"chapter_semantic_{chapter_id}.json",
        S9W / f"chapter_semantic_{chapter_id.replace('bab_','bab_')}.json",
    ]
    # bab_7 naming quirk
    if chapter_id == "bab_7":
        candidates.insert(0, S9W / "chapter_semantic_bab7.json")
    for c in candidates:
        if c.exists(): return c
    return None


# ── PER-CHAPTER PROCESSING ────────────────────────────────────
chapter_status   = []
all_packets      = []
packet_manifests = {}

for chapter_id in chapter_order:
    sem_file = find_semantic(chapter_id)
    if not sem_file:
        print(f"  SKIP {chapter_id}: semantic file tidak ditemukan")
        chapter_status.append({
            "chapter_id":        chapter_id,
            "status":            "skipped",
            "reason":            "semantic_file_not_found",
            "evaluated_at":      datetime.now().isoformat(),
        })
        continue

    print(f"  Processing {chapter_id} ({sem_file.name})...")

    # Step 1: Evaluator
    eval_output = SCRIPT_DIR / f"work/eval_{chapter_id}.json"
    assign_log  = SCRIPT_DIR / f"work/assign_{chapter_id}.json"

    r1 = subprocess.run([
        PYTHON, str(EVALUATOR),
        "--chapter",  chapter_id,
        "--semantic", str(sem_file),
        "--output",   str(SCRIPT_DIR / "work"),
    ], capture_output=True, text=True)

    # Evaluator writes to work/ with its own naming
    eval_file = SCRIPT_DIR / f"work/style_evaluation_report_{chapter_id}.json"
    if not eval_file.exists():
        # Try alternate name (bab7 quirk)
        alt = SCRIPT_DIR / f"work/style_evaluation_report_bab_7.json" if chapter_id == "bab_7" else None
        if alt and alt.exists(): eval_file = alt

    if not eval_file.exists() or r1.returncode != 0:
        print(f"    WARN: evaluator gagal untuk {chapter_id} — {r1.stderr[:80]}")
        chapter_status.append({
            "chapter_id": chapter_id, "status": "eval_failed",
            "evaluated_at": datetime.now().isoformat(),
        })
        continue

    eval_report = json.load(open(eval_file))
    summary     = eval_report.get("summary", {})
    nr_count    = summary.get("needs_review", 0) + summary.get("flagged", 0)

    print(f"    evaluated: {nr_count} packets needed")

    # Step 2: Packet exporter (only if needs_review/flagged exist)
    chapter_packets = []
    if nr_count > 0:
        r2 = subprocess.run([
            PYTHON, str(EXPORTER),
            "--report", str(eval_file),
            "--output", str(SCRIPT_DIR / "work"),
        ], capture_output=True, text=True)

        pkt_file = SCRIPT_DIR / f"work/paragraph_style_packets_{chapter_id}.json"
        if pkt_file.exists():
            chapter_packets = json.load(open(pkt_file))
            print(f"    packets: {len(chapter_packets)} generated")
        else:
            print(f"    WARN: packet file tidak ditemukan")

    all_packets.extend(chapter_packets)
    packet_manifests[chapter_id] = {
        "packet_count": len(chapter_packets),
        "packet_ids":   [p["packet_id"] for p in chapter_packets],
        "eval_file":    str(eval_file.relative_to(SCRIPT_DIR)),
    }

    chapter_status.append({
        "chapter_id":       chapter_id,
        "status":           "evaluated",
        "register_used":    eval_report.get("register_used",""),
        "register_confidence": 1.0 if chapter_id in
            json.load(open(S14C/"register_style_map.json")).get("lookup",{}) else 0.75,
        "packets_generated":len(chapter_packets),
        "review_status":    "pending",
        "evaluated_at":     datetime.now().isoformat(),
        "semantic_file":    sem_file.name,
    })

    # Respect max_packets_per_batch
    if len(all_packets) >= MAX_PACKETS:
        print(f"  Max packets ({MAX_PACKETS}) reached — pausing batch queue")
        break

# ── WRITE WORK OUTPUTS ────────────────────────────────────────
status_out = {
    "run_id":        RUN_ID,
    "mode":          MODE,
    "generated_at":  datetime.now().isoformat(),
    "chapters":      chapter_status,
}
json.dump(status_out,
          open(WORK_DIR/"chapter_refinement_status.json","w"),
          indent=2, ensure_ascii=False)

manifest_out = {
    "run_id":       RUN_ID,
    "generated_at": datetime.now().isoformat(),
    "chapters":     packet_manifests,
    "total_packets":len(all_packets),
}
json.dump(manifest_out,
          open(WORK_DIR/"chapter_packet_manifests.json","w"),
          indent=2, ensure_ascii=False)

print(f"\nStatus   : {WORK_DIR/'chapter_refinement_status.json'}")
print(f"Manifests: {WORK_DIR/'chapter_packet_manifests.json'}")
print(f"Total packets collected: {len(all_packets)}")
print("="*55)
print("ORCHESTRATOR COMPLETE")
print("="*55)
