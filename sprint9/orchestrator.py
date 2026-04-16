#!/usr/bin/env python3
"""
Orchestrator — Sprint 9
SROI Report Generation System

Single-command end-to-end pipeline:
  intake → extract → canonical → financial calc → blueprint →
  point builder → narrative → QA → renderer → full assembly

Usage:
  python orchestrator.py --program ESL
  python orchestrator.py --program PSN --scripts /path/TJSL_Scripts.md
  python orchestrator.py --program ESL --skip-extract  # pakai canonical yang sudah ada
  python orchestrator.py --program ESL --dry-run       # print rencana tanpa eksekusi

  PROGRAM=ESL python orchestrator.py
"""

import sys
import os
import json
import argparse
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

ORCH_VERSION = "1.0.0"

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="SROI Report Orchestrator")
parser.add_argument("--program",      required=False, default=None,
                    help="Kode program: ESL / PSN / ESD / ETB / ESP / ESS")
parser.add_argument("--scripts",      default=None,
                    help="Path ke TJSL_Scripts.md")
parser.add_argument("--base-dir",     default=None,
                    help="Base directory pipeline (default: parent dari script ini)")
parser.add_argument("--output-dir",   default=None,
                    help="Output directory final (default: base-dir/output/{program})")
parser.add_argument("--skip-extract", action="store_true",
                    help="Lewati Source Extractor — pakai canonical yang sudah ada")
parser.add_argument("--dry-run",      action="store_true",
                    help="Print rencana eksekusi tanpa menjalankan")
args = parser.parse_args()

PROGRAM = (args.program or os.environ.get("PROGRAM", "")).upper()
if not PROGRAM:
    print("FAIL: --program wajib diisi (contoh: --program ESL)")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
BASE_DIR   = Path(args.base_dir) if args.base_dir \
    else Path(os.environ.get("BASE_DIR", SCRIPT_DIR))

SCRIPTS_FILE = Path(args.scripts) if args.scripts \
    else Path(os.environ.get("SCRIPTS_FILE",
              "/mnt/user-data/outputs/TJSL_Scripts.md"))

OUTPUT_DIR = Path(args.output_dir) if args.output_dir \
    else Path(os.environ.get("OUTPUT_DIR",
              BASE_DIR / f"output/{PROGRAM.lower()}"))

# Sprint directories
S0  = BASE_DIR / "sprint0"
S1  = BASE_DIR / "sprint1"
S2  = BASE_DIR / "sprint2"
S3  = BASE_DIR / "sprint3"
S4  = BASE_DIR / "sprint4"
S5  = BASE_DIR / "sprint5"
S6  = BASE_DIR / "sprint6"
S7  = BASE_DIR / "sprint7"
S8  = BASE_DIR / "sprint8"
S9  = BASE_DIR / "sprint9"

DRY_RUN = args.dry_run

print("=" * 60)
print(f"SROI REPORT ORCHESTRATOR v{ORCH_VERSION}")
print(f"  Program   : {PROGRAM}")
print(f"  Base dir  : {BASE_DIR.resolve()}")
print(f"  Output dir: {OUTPUT_DIR.resolve()}")
print(f"  Dry run   : {DRY_RUN}")
print("=" * 60)


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

steps_log = []

def step(name, cmd_parts, check_output=None, env_extra=None):
    """Jalankan satu step pipeline. Return True jika berhasil."""
    steps_log.append({"step": name, "cmd": " ".join(str(p) for p in cmd_parts)})
    print(f"\n{'─'*55}")
    print(f"STEP: {name}")
    print(f"CMD : {' '.join(str(p) for p in cmd_parts)}")

    if DRY_RUN:
        print("  [DRY RUN — tidak dieksekusi]")
        return True

    env = {**os.environ}
    if env_extra:
        env.update(env_extra)

    result = subprocess.run(
        [str(p) for p in cmd_parts],
        capture_output=False,
        env=env
    )
    if result.returncode != 0:
        print(f"\n✕ STEP FAILED: {name} (exit {result.returncode})")
        return False

    # Cek output file jika diminta
    if check_output:
        for f in (check_output if isinstance(check_output, list) else [check_output]):
            if not Path(f).exists():
                print(f"\n✕ OUTPUT MISSING: {f}")
                return False

    print(f"✓ {name} — OK")
    return True


def require_file(path, label):
    """Hentikan pipeline jika file wajib tidak ada."""
    if not Path(path).exists():
        print(f"\nFAIL: {label} tidak ditemukan — {path}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════
# FALLBACK PARSER — perbaiki field yang kosong setelah extrak
# ══════════════════════════════════════════════════════════

PROGRAM_NAME_FALLBACKS = {
    "ESL": "Enduro Sahabat Lapas",
    "PSN": "Pertamina Sahabat Nelayan",
    "ESD": "Enduro Sahabat Difabel",
    "ETB": "Enduro Tapal Batas",
    "ESS": "Enduro Sahabat Santri",
    "ESP": "Enduro Student Program",
}

PROGRAM_TAGLINE_FALLBACKS = {
    "ESL": "Penguatan Keterampilan Mekanik, Kemandirian Usaha, dan Kesiapan Reintegrasi Sosial-Ekonomi bagi WBP dan Eks-WBP",
    "PSN": "Penguatan Keandalan Aset Kapal dan Kapasitas Bengkel Nelayan melalui Pelatihan Mesin, Literasi Pelumasan, dan Kewirausahaan Perbengkelan",
    "ESD": "Pemberdayaan Kelompok Difabel melalui Pelatihan Vokasional dan Penguatan Kelembagaan",
    "ETB": "Pemberdayaan Masyarakat Wilayah Perbatasan melalui Pelumasan dan Kewirausahaan Bengkel",
    "ESS": "Pemberdayaan Santri melalui Literasi Pelumasan dan Kewirausahaan Bengkel Pesantren",
    "ESP": "Penguatan Kompetensi Teknis dan Kewirausahaan Siswa SMK melalui Program Pendampingan Industri",
}

SDG_MAP = {
    "ESL": ["SDG 8 — Pekerjaan Layak", "SDG 10 — Berkurangnya Ketimpangan", "SDG 16 — Perdamaian & Keadilan"],
    "PSN": ["SDG 8 — Pekerjaan Layak", "SDG 14 — Ekosistem Lautan"],
    "ESD": ["SDG 8 — Pekerjaan Layak", "SDG 10 — Berkurangnya Ketimpangan"],
    "ETB": ["SDG 8 — Pekerjaan Layak", "SDG 10 — Berkurangnya Ketimpangan"],
    "ESS": ["SDG 4 — Pendidikan Berkualitas", "SDG 8 — Pekerjaan Layak"],
    "ESP": ["SDG 4 — Pendidikan Berkualitas", "SDG 8 — Pekerjaan Layak", "SDG 9 — Industri & Inovasi"],
}

def apply_fallbacks(canonical_path):
    """
    Perbaiki field yang kosong/missing di canonical JSON
    menggunakan fallback registry yang dikurasi secara manual.
    Field observed tidak boleh diubah — hanya field kosong.
    """
    with open(canonical_path) as f:
        data = json.load(f)

    pi   = data.get("program_identity", {})
    pp   = data.get("program_positioning", {})
    prog = pi.get("program_code", PROGRAM)
    patched = []

    # program_name
    # DEBUG PATTERN — strings dari draft script yang tidak boleh masuk laporan
    DEBUG_PATTERNS = [
        "MON-REINT & MON-CONF",
        "belum dihitung",
        "SROI final belum",
        "Observed blended direct return",
        "observed direct return dari",
        "total investasi kumulatif",
    ]
    def is_debug(text):
        return any(p in str(text) for p in DEBUG_PATTERNS)

    if not pi.get("program_name"):
        fallback = PROGRAM_NAME_FALLBACKS.get(prog)
        if fallback:
            pi["program_name"] = fallback
            patched.append(f"program_identity.program_name = '{fallback}'")

    # program_tagline — override JUGA jika berisi debug string
    current_tagline = pi.get("program_tagline", "")
    if not current_tagline or is_debug(current_tagline):
        fallback = PROGRAM_TAGLINE_FALLBACKS.get(prog)
        if fallback:
            pi["program_tagline"] = fallback
            patched.append("program_identity.program_tagline (override debug → fallback)")

    # sdg_alignment
    if not pp.get("sdg_alignment"):
        fallback = SDG_MAP.get(prog, [])
        if fallback:
            pp["sdg_alignment"] = fallback
            patched.append("program_positioning.sdg_alignment (fallback)")

    # proper_category default
    if not pp.get("proper_category"):
        pp["proper_category"] = "Beyond Compliance — Inovasi Sosial"
        patched.append("program_positioning.proper_category (default)")

    # tjsl_pillar default
    if not pp.get("tjsl_pillar"):
        pp["tjsl_pillar"] = "Pemberdayaan Masyarakat"
        patched.append("program_positioning.tjsl_pillar (default)")

    # policy_basis default
    if not pp.get("policy_basis"):
        pp["policy_basis"] = [
            "UU No. 40 Tahun 2007 tentang Perseroan Terbatas Pasal 74",
            "Peraturan Menteri LHK No. 1 Tahun 2021",
        ]
        patched.append("program_positioning.policy_basis (default)")

    # learning_signals sanitize — buang entries yang berisi debug string
    ls = data.get("learning_signals", {})
    for loop_key in ["loop_1", "loop_2", "loop_3"]:
        items = ls.get(loop_key, [])
        clean = [item for item in items if not is_debug(item)]
        if len(clean) != len(items):
            ls[loop_key] = clean
            patched.append(f"learning_signals.{loop_key} — {len(items)-len(clean)} debug entries removed")
    data["learning_signals"] = ls

    data["program_identity"]    = pi
    data["program_positioning"] = pp

    if patched:
        print(f"  Fallback applied ({len(patched)} field):")
        for p in patched:
            print(f"    + {p}")
        with open(canonical_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        print("  No fallback needed — all fields populated")

    return patched


# ══════════════════════════════════════════════════════════
# SETUP OUTPUT DIRECTORY
# ══════════════════════════════════════════════════════════

if not DRY_RUN:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Work dir — semua artefak intermediate
    WORK_DIR = OUTPUT_DIR / "work"
    WORK_DIR.mkdir(exist_ok=True)
else:
    WORK_DIR = OUTPUT_DIR / "work"

print(f"\nWork dir  : {WORK_DIR}")


# ══════════════════════════════════════════════════════════
# STEP 0 — PREFLIGHT CHECK
# ══════════════════════════════════════════════════════════
print(f"\n{'━'*60}")
print("PREFLIGHT CHECK")

# Scripts yang wajib ada
required_scripts = [
    (S7  / "deck_script_parser.py",     "Source Extractor"),
    (S1  / "financial_engine.py",       "Financial Engine"),
    (S2  / "report_architect.py",       "Report Architect"),
    (S3  / "point_builder_sroi.py",     "Point Builder"),
    (S3  / "narrative_builder_sroi.py", "Narrative Builder sroi"),
    (S6  / "narrative_builder_rest.py", "Narrative Builder rest"),
    (S5  / "qa_checker.py",             "QA Checker"),
    (S4  / "renderer.js",               "Renderer"),
    (S8  / "full_assembler.js",         "Full Assembler"),
    (S0  / "render_contract_v1.json",   "Render Contract"),
]
preflight_ok = True
for path, label in required_scripts:
    exists = Path(path).exists()
    status = "✓" if exists else "✕"
    print(f"  {status} {label}: {path}")
    if not exists:
        preflight_ok = False

if not preflight_ok and not DRY_RUN:
    print("\nPREFLIGHT FAILED — beberapa script tidak ditemukan")
    sys.exit(1)

if not DRY_RUN:
    print("Preflight: OK")


# ══════════════════════════════════════════════════════════
# STEP 1 — SOURCE EXTRACTION
# ══════════════════════════════════════════════════════════
canonical_path = WORK_DIR / f"canonical_{PROGRAM.lower()}.json"
extracted_path = S7 / f"canonical_{PROGRAM.lower()}_extracted.json"

if args.skip_extract:
    print(f"\n[SKIP] Source Extraction — menggunakan canonical yang sudah ada")
    # Cari canonical — urutan lookup:
    # 1. sprint7/canonical_{program}_extracted.json
    # 2. work/canonical_{program}.json (sudah ada)
    # 3. data/canonical/canonical_{program}_v1.json (dari repo)
    # 4. sprint0/canonical_{program}_v1.json (legacy)
    data_canonical = BASE_DIR / f"data/canonical/canonical_{PROGRAM.lower()}_v1.json"
    sprint0_canonical = S0.parent / f"sprint0/canonical_{PROGRAM.lower()}_v1.json"

    if extracted_path.exists():
        shutil.copy(extracted_path, canonical_path)
        print(f"  Copied: {extracted_path} → {canonical_path}")
    elif canonical_path.exists():
        print(f"  Using existing: {canonical_path}")
    elif data_canonical.exists():
        shutil.copy(data_canonical, canonical_path)
        print(f"  Copied from data/canonical: {data_canonical} → {canonical_path}")
    elif sprint0_canonical.exists():
        shutil.copy(sprint0_canonical, canonical_path)
        print(f"  Copied from sprint0: {sprint0_canonical} → {canonical_path}")
    else:
        print(f"FAIL: Tidak ada canonical untuk {PROGRAM} — jalankan tanpa --skip-extract")
        print(f"  Dicari di:")
        print(f"    {extracted_path}")
        print(f"    {canonical_path}")
        print(f"    {data_canonical}")
        print(f"    {sprint0_canonical}")
        sys.exit(1)
else:
    ok = step(
        f"Source Extraction ({PROGRAM})",
        [sys.executable, S7 / "deck_script_parser.py",
         "--input",   SCRIPTS_FILE,
         "--output",  WORK_DIR,
         "--program", PROGRAM],
        check_output=WORK_DIR / f"canonical_{PROGRAM.lower()}_extracted.json"
    )
    if ok and not DRY_RUN:
        # Rename extracted → canonical
        extracted = WORK_DIR / f"canonical_{PROGRAM.lower()}_extracted.json"
        if extracted.exists():
            shutil.copy(extracted, canonical_path)


# ══════════════════════════════════════════════════════════
# STEP 2 — APPLY FALLBACKS (fix empty fields)
# ══════════════════════════════════════════════════════════
if not DRY_RUN and canonical_path.exists():
    print(f"\n{'─'*55}")
    print("STEP: Apply Fallbacks")
    apply_fallbacks(canonical_path)
elif DRY_RUN:
    print(f"\n[DRY RUN] STEP: Apply Fallbacks for {PROGRAM}")


# ══════════════════════════════════════════════════════════
# STEP 2B — ENRICH CANONICAL (merge dari manual jika tersedia)
# ══════════════════════════════════════════════════════════

MANUAL_CANONICAL_MAP = {
    "ESL": str(S0.parent / "data/canonical/canonical_esl_v1.json") if (S0.parent / "data/canonical/canonical_esl_v1.json").exists() else str(S0.parent / "sprint0/canonical_esl_v1.json"),
}

def enrich_canonical(canonical_path, program):
    """
    Merge field yang kosong di canonical extracted dari manual.
    Hanya mengisi yang kosong — tidak menimpa observed facts.
    """
    manual_path = MANUAL_CANONICAL_MAP.get(program)
    if not manual_path or not Path(manual_path).exists():
        print(f"  No manual canonical for {program} — skip enrichment")
        return

    with open(canonical_path) as f: extracted = json.load(f)
    with open(manual_path)    as f: manual    = json.load(f)

    ENRICH_FIELDS = [
        "activities","outputs","stakeholders","beneficiaries",
        "outcomes","context_baseline","problem_framing",
        "ideal_conditions","strategy_design","learning_signals",
        "evidence_registry","uncertainty_flags",
    ]
    enriched = []
    for field in ENRICH_FIELDS:
        ev = extracted.get(field)
        mv = manual.get(field)
        # Field dianggap perlu enrichment jika:
        # - kosong / None / list kosong / string kosong, ATAU
        # - dict yang hanya punya key "data_status" (belum ada isi substantif)
        is_stub = (
            not ev or ev in [{},[],""] or
            (isinstance(ev, dict) and set(ev.keys()) <= {"data_status"}) or
            (isinstance(ev, list) and len(ev) == 0)
        )
        if is_stub and mv:
            extracted[field] = mv
            enriched.append(field)

    if enriched:
        print(f"  Enriched {len(enriched)} fields from manual: {enriched}")
        with open(canonical_path,"w") as f:
            json.dump(extracted, f, indent=2, ensure_ascii=False)
    else:
        print("  No enrichment needed")

if not DRY_RUN and canonical_path.exists():
    print(f"\n{'─'*55}")
    print("STEP: Enrich Canonical from Manual")
    enrich_canonical(canonical_path, PROGRAM)
elif DRY_RUN:
    print(f"\n[DRY RUN] STEP: Enrich Canonical for {PROGRAM}")


# ══════════════════════════════════════════════════════════
# STEP 3 — FINANCIAL CALCULATION ENGINE
# ══════════════════════════════════════════════════════════
handoff_b_path = WORK_DIR / "handoff_b.json"

ok = step(
    "Financial Calculation Engine",
    [sys.executable, S1 / "financial_engine.py",
     "--input",  canonical_path,
     "--output", handoff_b_path],
    check_output=handoff_b_path
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 4 — REPORT ARCHITECT
# ══════════════════════════════════════════════════════════
handoff_c_path = WORK_DIR / "handoff_c.json"

ok = step(
    "Report Architect",
    [sys.executable, S2 / "report_architect.py",
     "--canonical", canonical_path,
     "--handoff",   handoff_b_path,
     "--output",    WORK_DIR],
    check_output=[WORK_DIR / "report_blueprint.json", WORK_DIR / "gap_matrix.json"]
)
if not ok and not DRY_RUN: sys.exit(1)

if not DRY_RUN:
    handoff_c_path = WORK_DIR / "handoff_c.json"


# ══════════════════════════════════════════════════════════
# STEP 5 — POINT BUILDER (Bab 7)
# ══════════════════════════════════════════════════════════
outline_bab7 = WORK_DIR / "chapter_outline_bab7.json"

ok = step(
    "Point Builder — Bab 7",
    [sys.executable, S3 / "point_builder_sroi.py",
     "--canonical",  canonical_path,
     "--handoff-b",  handoff_b_path,
     "--handoff-c",  handoff_c_path,
     "--output",     WORK_DIR],
    check_output=outline_bab7
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 6 — NARRATIVE BUILDER — Bab 7
# ══════════════════════════════════════════════════════════
semantic_bab7 = WORK_DIR / "chapter_semantic_bab7.json"

ok = step(
    "Narrative Builder — Bab 7",
    [sys.executable, S3 / "narrative_builder_sroi.py",
     "--outline",    outline_bab7,
     "--handoff-b",  handoff_b_path,
     "--canonical",  canonical_path,
     "--output",     WORK_DIR],
    check_output=semantic_bab7
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 7 — NARRATIVE BUILDER — Bab 1-6, 8-9
# ══════════════════════════════════════════════════════════
semantic_rest = WORK_DIR / "chapters_semantic_rest.json"

ok = step(
    "Narrative Builder — Bab 1-6, 8-9",
    [sys.executable, S6 / "narrative_builder_rest.py",
     "--canonical",  canonical_path,
     "--handoff-b",  handoff_b_path,
     "--blueprint",  WORK_DIR / "report_blueprint.json",
     "--output",     WORK_DIR],
    check_output=semantic_rest
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 8 — QA CHECKER
# ══════════════════════════════════════════════════════════
qa_report  = WORK_DIR / "qa_report.json"
handoff_f  = WORK_DIR / "handoff_f.json"

ok = step(
    "QA Checker",
    [sys.executable, S5 / "qa_checker.py",
     "--semantic",   semantic_bab7,
     "--handoff-b",  handoff_b_path,
     "--outline",    outline_bab7,
     "--contract",   S0 / "render_contract_v1.json",
     "--output",     WORK_DIR],
    check_output=[qa_report, handoff_f]
)
if not ok and not DRY_RUN: sys.exit(1)

# Cek renderer_ready
if not DRY_RUN and handoff_f.exists():
    hf_data = json.load(open(handoff_f))
    if not hf_data.get("renderer_ready", False):
        print("\nFAIL: QA menandai renderer_ready=False — pipeline dihentikan")
        sys.exit(1)
    print("  QA: renderer_ready = True ✓")


# ══════════════════════════════════════════════════════════
# STEP 9 — RENDERER — Bab 7
# ══════════════════════════════════════════════════════════
bab7_docx = WORK_DIR / f"{PROGRAM}_Report_Bab7.docx"

ok = step(
    "Renderer — Bab 7",
    ["node", S4 / "renderer.js",
     "--semantic", semantic_bab7,
     "--output",   bab7_docx],
    check_output=bab7_docx
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 10 — FULL ASSEMBLER
# ══════════════════════════════════════════════════════════
full_docx = OUTPUT_DIR / f"{PROGRAM}_SROI_Report_Full.docx"

ok = step(
    "Full Assembler — Bab 1-9",
    ["node", S8 / "full_assembler.js",
     "--semantic-dir",  WORK_DIR,
     "--semantic-dir6", WORK_DIR,
     "--canonical",     canonical_path,
     "--output",        full_docx],
    check_output=full_docx
)
if not ok and not DRY_RUN: sys.exit(1)


# ══════════════════════════════════════════════════════════
# STEP 11 — COPY FINAL ARTIFACTS
# ══════════════════════════════════════════════════════════
if not DRY_RUN:
    print(f"\n{'─'*55}")
    print("STEP: Copy final artifacts")

    # Copy key artifacts ke output root
    to_copy = [
        (canonical_path,              OUTPUT_DIR / f"canonical_{PROGRAM.lower()}.json"),
        (handoff_b_path,              OUTPUT_DIR / "handoff_b.json"),
        (WORK_DIR / "report_blueprint.json", OUTPUT_DIR / "report_blueprint.json"),
        (WORK_DIR / "gap_matrix.json",       OUTPUT_DIR / "gap_matrix.json"),
        (WORK_DIR / "qa_report.json",        OUTPUT_DIR / "qa_report.json"),
        (bab7_docx,                          OUTPUT_DIR / f"{PROGRAM}_Report_Bab7.docx"),
    ]
    for src, dst in to_copy:
        if Path(src).exists():
            shutil.copy(src, dst)
            print(f"  → {dst.name}")

    # Write run manifest
    manifest = {
        "orchestrator_version": ORCH_VERSION,
        "program":    PROGRAM,
        "run_at":     datetime.now().isoformat(),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "steps":      steps_log,
        "output_files": [f.name for f in OUTPUT_DIR.iterdir() if f.is_file()],
    }
    manifest_path = OUTPUT_DIR / "run_manifest.json"
    json.dump(manifest, open(manifest_path,"w"), indent=2, ensure_ascii=False)
    print(f"  → run_manifest.json")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "="*60)
if DRY_RUN:
    print(f"DRY RUN COMPLETE — {len(steps_log)} steps planned")
    print(f"Run tanpa --dry-run untuk eksekusi penuh")
else:
    print(f"ORCHESTRATOR COMPLETE — {PROGRAM}")
    print(f"  Steps run    : {len(steps_log)}")
    if full_docx.exists():
        size = full_docx.stat().st_size
        print(f"  Final report : {full_docx.name} ({size:,} bytes)")
    print(f"  Output dir   : {OUTPUT_DIR.resolve()}")

print("="*60)
