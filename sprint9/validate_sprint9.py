"""
Sprint 9 Gate Validator — Orchestrator
Gate: pipeline `--program ESL` harus menghasilkan semua artefak
      yang dibutuhkan secara end-to-end, termasuk fallback ESL name fix.

Usage:
  python validate_sprint9.py
  python validate_sprint9.py --output-dir /p/sprint9/output/esl
  OUTPUT_DIR=... python validate_sprint9.py
"""
import json, sys, os, argparse, zipfile, re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default=None, dest="output_dir")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(args.output_dir) if args.output_dir \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR / "output/esl"))
WORK_DIR   = OUTPUT_DIR / "work"

print(f"Output dir : {OUTPUT_DIR.resolve()}")
print(f"Work dir   : {WORK_DIR.resolve()}")

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 1: Final report ada ─────────────────────────────
print("\n=== GATE 1: Final report ada ===")
final_docx = OUTPUT_DIR / "ESL_SROI_Report_Full.docx"
check(final_docx.exists(),                        "ESL_SROI_Report_Full.docx ada")
check(final_docx.stat().st_size > 20_000 if final_docx.exists() else False,
      f"Ukuran final report > 20KB")

# ── GATE 2: Semua artefak output ada ─────────────────────
print("\n=== GATE 2: Artefak output ada ===")
expected_outputs = [
    "ESL_SROI_Report_Full.docx",
    "canonical_esl.json",
    "handoff_b.json",
    "report_blueprint.json",
    "gap_matrix.json",
    "qa_report.json",
    "run_manifest.json",
    "canonical_snapshot.json",
]
for fname in expected_outputs:
    check((OUTPUT_DIR / fname).exists(), f"{fname} ada di output dir")

# ── GATE 3: Artefak work dir ada ─────────────────────────
print("\n=== GATE 3: Artefak work dir ada ===")
expected_work = [
    "chapter_outline_bab7.json",
    "chapter_semantic_bab7.json",
    "chapters_semantic_rest.json",
    "handoff_f.json",
    "qa_report.json",
]
for fname in expected_work:
    check((WORK_DIR / fname).exists(), f"work/{fname} ada")

# ── GATE 4: Fallback ESL program_name diterapkan ─────────
print("\n=== GATE 4: Fallback ESL program_name ===")
canonical_path = OUTPUT_DIR / "canonical_esl.json"
if canonical_path.exists():
    c = json.load(open(canonical_path))
    pi = c.get("program_identity", {})
    check(pi.get("program_name") == "Enduro Sahabat Lapas",
          f"program_name = 'Enduro Sahabat Lapas' (dapat: '{pi.get('program_name')}')")
    check(bool(pi.get("program_tagline")),
          "program_tagline tidak kosong")
    check(bool(c.get("program_positioning",{}).get("sdg_alignment")),
          "sdg_alignment tidak kosong")

# ── GATE 5: Enrichment berhasil ──────────────────────────
print("\n=== GATE 5: Canonical enrichment ===")
if canonical_path.exists():
    c = json.load(open(canonical_path))
    check(isinstance(c.get("activities"), list) and len(c["activities"]) > 0,
          "activities tidak kosong (enriched from manual)")
    check(isinstance(c.get("stakeholders"), list) and len(c["stakeholders"]) > 0,
          "stakeholders tidak kosong (enriched from manual)")
    check(isinstance(c.get("outcomes"), list) and len(c["outcomes"]) > 0,
          "outcomes tidak kosong (enriched from manual)")
    sd = c.get("strategy_design", {})
    check(sd.get("institutional", {}).get("nodes"),
          "strategy_design.institutional.nodes ada (enriched)")

# ── GATE 6: Financial Engine benar ───────────────────────
print("\n=== GATE 6: Financial Engine output ===")
hb_path = OUTPUT_DIR / "handoff_b.json"
if hb_path.exists():
    hb = json.load(open(hb_path))
    calc = hb["sroi_metrics"]["calculated"]
    inv  = calc.get("total_investment_idr", 0)
    check(abs(inv - 502460181) < 1,
          f"total_investment = 502,460,181 (dapat: {inv:,})")
    sroi = calc.get("sroi_blended", 0)
    check(0.9 < sroi < 1.5,
          f"sroi_blended dalam range wajar 0.9–1.5 (dapat: {sroi:.4f})")
    check(len(hb.get("calc_audit_log", [])) >= 40,
          f"audit_log ≥ 40 entries (dapat: {len(hb.get('calc_audit_log',[]))})")

# ── GATE 7: QA pass ──────────────────────────────────────
print("\n=== GATE 7: QA result ===")
qa_path = OUTPUT_DIR / "qa_report.json"
if qa_path.exists():
    qa = json.load(open(qa_path))
    check(qa.get("renderer_ready") is True, "qa renderer_ready = True")
    check(qa["summary"].get("errors", 999) == 0,
          f"qa errors = 0 (dapat: {qa['summary'].get('errors')})")
    check(qa["summary"].get("checks_run", 0) >= 9,
          f"qa checks_run ≥ 9 (dapat: {qa['summary'].get('checks_run')})")

# ── GATE 8: Final .docx valid ────────────────────────────
print("\n=== GATE 8: Final .docx structure ===")
if final_docx.exists():
    with zipfile.ZipFile(final_docx) as z:
        names   = z.namelist()
        doc_xml = z.read("word/document.xml").decode("utf-8")
    plain = re.sub(r"<[^>]+>", " ", doc_xml)

    check("word/document.xml" in names,  "word/document.xml ada")
    para_count = len(re.findall(r"<w:p[ >]", doc_xml))
    check(para_count >= 400,             f"paragraf ≥ 400 (dapat: {para_count})")

    for needle, label in [
        ("Enduro Sahabat Lapas", "Program name di docx"),
        ("DAFTAR ISI",           "TOC ada"),
        ("BAB VII",              "Bab 7 ada"),
        ("BAB IX",               "Bab 9 ada"),
        ("502",                  "Angka investasi ada"),
    ]:
        check(needle in plain, label)

# ── GATE 9: run_manifest valid ───────────────────────────
print("\n=== GATE 9: run_manifest ===")
manifest_path = OUTPUT_DIR / "run_manifest.json"
if manifest_path.exists():
    manifest = json.load(open(manifest_path))
    check(manifest.get("program") == "ESL",
          "manifest program = ESL")
    check(len(manifest.get("steps", [])) >= 9,
          f"manifest steps ≥ 9 (dapat: {len(manifest.get('steps',[]))})")
    check(bool(manifest.get("output_files")),
          "manifest output_files tercatat")

# ── GATE 10: Dry run berfungsi ───────────────────────────
print("\n=== GATE 10: Dry run test ===")
import subprocess
r = subprocess.run(
    [sys.executable, str(SCRIPT_DIR / "orchestrator.py"),
     "--program", "ESL",
     "--base-dir", str(SCRIPT_DIR.parent),
     "--dry-run"],
    capture_output=True, text=True
)
check(r.returncode == 0,                    "orchestrator --dry-run exit 0")
check("DRY RUN COMPLETE" in r.stdout,       "DRY RUN COMPLETE ada di output")
check("9 steps planned" in r.stdout,        "9 steps planned di dry run")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*60)
if ERRORS:
    print(f"SPRINT 9 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    size = final_docx.stat().st_size if final_docx.exists() else 0
    print("SPRINT 9 GATE: ALL PASS")
    print(f"  Program      : ESL")
    print(f"  Final report : {final_docx.name} ({size:,} bytes)")
    print(f"  Output dir   : {OUTPUT_DIR.resolve()}")
    print("Sprint 10 — Input Expansion boleh dimulai.")
    sys.exit(0)
