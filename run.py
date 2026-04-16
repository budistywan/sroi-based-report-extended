#!/usr/bin/env python3
"""
run.py — SROI Report Generation System
Single-command production runner (Jalur A)

Usage:
  # Produksi laporan ESL (pakai canonical yang sudah ada)
  python run.py --program ESL

  # Produksi laporan ESL dari input scripts baru
  python run.py --program ESL --scripts /path/TJSL_Scripts.md

  # Hanya style refinement batch (skip core pipeline)
  python run.py --program ESL --only-refine

  # Dry run — print rencana tanpa eksekusi
  python run.py --program ESL --dry-run

  # Lihat semua opsi
  python run.py --help
"""

import sys, os, subprocess, argparse
from pathlib import Path
from datetime import datetime

BASE   = Path(__file__).parent
PYTHON = sys.executable

parser = argparse.ArgumentParser(
    description="SROI Report Generation System — Production Runner",
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--program",     required=True,
                    help="Kode program: ESL / PSN / ESD / dll.")
parser.add_argument("--scripts",     default=None,
                    help="Path ke TJSL_Scripts.md (opsional jika skip-extract)")
parser.add_argument("--skip-extract",action="store_true",
                    help="Pakai canonical JSON yang sudah ada di data/canonical/")
parser.add_argument("--only-refine", action="store_true",
                    help="Hanya jalankan batch refinement (14E), skip core pipeline")
parser.add_argument("--dry-run",     action="store_true",
                    help="Print rencana tanpa eksekusi")
args = parser.parse_args()

PROGRAM = args.program.upper()
NOW     = datetime.now().strftime("%Y%m%d_%H%M%S")

print("=" * 60)
print(f"SROI REPORT SYSTEM — Production Run")
print(f"  Program   : {PROGRAM}")
print(f"  Mode      : {'dry-run' if args.dry_run else 'LIVE'}")
print(f"  Timestamp : {NOW}")
print("=" * 60)

def run(cmd, label):
    print(f"\n▶ {label}")
    if args.dry_run:
        print(f"  [DRY RUN] {' '.join(str(c) for c in cmd)}")
        return True
    r = subprocess.run(cmd, cwd=str(BASE))
    if r.returncode != 0:
        print(f"  ✗ FAILED: {label}")
        sys.exit(1)
    print(f"  ✓ Done: {label}")
    return True


# ── STEP 1: CORE PIPELINE (Sprint 9 Orchestrator) ─────────────
if not args.only_refine:
    cmd = [PYTHON, str(BASE / "sprint9/orchestrator.py"),
           "--program",  PROGRAM,
           "--base-dir", str(BASE)]

    # Canonical lookup
    canonical = BASE / f"data/canonical/canonical_{PROGRAM.lower()}_v1.json"
    if canonical.exists() or args.skip_extract:
        cmd.append("--skip-extract")
        print(f"\n  Using canonical: {canonical}")
    elif args.scripts:
        cmd += ["--scripts", args.scripts]
    else:
        print(f"\n  WARN: No canonical found at {canonical}")
        print(f"  Provide --scripts or ensure canonical exists.")
        print(f"  Falling back to skip-extract mode.")
        cmd.append("--skip-extract")

    run(cmd, "Core Pipeline (intake → canonical → narrative → render)")


# ── STEP 2: PERSONALIZATION LAYER ─────────────────────────────
style_profile = BASE / "sprint14a/style_profile_reviewed.json"
if style_profile.exists():
    run([PYTHON, str(BASE / "sprint14a/style_profile_importer.py"), "--demo"],
        "Personalization Layer (14A — style profile)")
else:
    print("\n  [SKIP] Sprint 14A: style_profile_reviewed.json tidak ditemukan")


# ── STEP 3: BATCH REFINEMENT (Sprint 14E) ─────────────────────
refine_config = BASE / "sprint14e/batch_refinement_config.json"
if refine_config.exists():
    # Update config program if needed
    run([PYTHON, str(BASE / "sprint14e/batch_refinement_orchestrator.py"),
         "--config", str(refine_config)],
        "Batch Refinement Orchestration (14E)")

    run([PYTHON, str(BASE / "sprint14e/cross_chapter_consistency_checker.py")],
        "Cross-chapter Consistency Check")

    run([PYTHON, str(BASE / "sprint14e/batch_patch_merge.py")],
        "Final Report Merge")
else:
    print("\n  [SKIP] Sprint 14E: batch_refinement_config.json tidak ditemukan")


# ── DONE ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
if args.dry_run:
    print("DRY RUN COMPLETE — tidak ada file yang dibuat")
else:
    output_dir = BASE / f"output"
    docx_candidates = list(output_dir.rglob("*.docx")) + \
                      list((BASE / "sprint14e").glob("*.docx"))
    if docx_candidates:
        for d in docx_candidates:
            print(f"  OUTPUT: {d} ({d.stat().st_size:,} bytes)")
    print("PRODUCTION RUN COMPLETE")
print("=" * 60)
