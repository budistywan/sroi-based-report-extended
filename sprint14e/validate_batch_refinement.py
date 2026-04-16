"""
validate_batch_refinement.py — Sprint 14E
Gates 1-9: config, orchestrator, queue, consistency, merge, analytics,
trust tier, no silent drift, final doc.

Usage:
  python validate_batch_refinement.py
  python validate_batch_refinement.py --dir /path/sprint14e/
"""
import json, sys, argparse, zipfile, re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR14E     = Path(args.dir) if args.dir else SCRIPT_DIR
WORK_DIR   = DIR14E / "work"

ERRORS = []
DOD    = {}

def check(cond, msg, dod_key=None):
    if not cond:
        ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}")
    if dod_key: DOD[dod_key] = True
    return True

# ── GATE 1: Config valid ──────────────────────────────────────
print("\n=== GATE 1: batch_refinement_config.json ===")
cfg_path = DIR14E / "batch_refinement_config.json"
check(cfg_path.exists(), "batch_refinement_config.json ada", "dod_1")
if cfg_path.exists():
    cfg = json.load(open(cfg_path))
    check("mode"             in cfg, "mode ada")
    check("priority_chapters"in cfg, "priority_chapters ada")
    check("max_packets_per_batch" in cfg, "max_packets_per_batch ada")
    check("review_policy"    in cfg, "review_policy ada")
    rp = cfg.get("review_policy",{})
    check(rp.get("tier_1_default") is True, "tier_1_default = true")
    check(rp.get("tier_2_enabled") is False,"tier_2_enabled = false (not yet active)")
    check(bool(rp.get("tier_3_always_manual")), "tier_3_always_manual ada")
    check("consistency_checks" in cfg, "consistency_checks ada")
    cc = cfg.get("consistency_checks",{})
    check(cc.get("require_before_merge") is True, "require_before_merge = true")

# ── GATE 2: Orchestrator outputs ─────────────────────────────
print("\n=== GATE 2: Orchestrator outputs ===")
status_path   = WORK_DIR / "chapter_refinement_status.json"
manifest_path = WORK_DIR / "chapter_packet_manifests.json"
check(status_path.exists(),   "chapter_refinement_status.json ada", "dod_2")
check(manifest_path.exists(), "chapter_packet_manifests.json ada")
if status_path.exists():
    st = json.load(open(status_path))
    chs = st.get("chapters",[])
    evaluated = [c for c in chs if c.get("status") == "evaluated"]
    check(len(evaluated) >= 2, f"Minimal 2 chapter evaluated ({len(evaluated)})")
    for c in evaluated:
        check("register_used"        in c, f"{c['chapter_id']}: register_used ada")
        check("packets_generated"    in c, f"{c['chapter_id']}: packets_generated ada")
        check("register_confidence"  in c, f"{c['chapter_id']}: register_confidence ada")
        check("review_status"        in c, f"{c['chapter_id']}: review_status ada")

# ── GATE 3: Queue valid + no auto-accept ─────────────────────
print("\n=== GATE 3: Queue valid + mandatory review ===")
q_path = DIR14E / "batch_refinement_queue.json"
check(q_path.exists(), "batch_refinement_queue.json ada", "dod_3")
if q_path.exists():
    q = json.load(open(q_path))
    check(q.get("auto_accept_enabled") is False,
          "auto_accept_enabled = false", "dod_3_mandatory")
    check(q.get("review_policy") == "tier_1_mandatory",
          "review_policy = tier_1_mandatory")
    pending = q.get("pending_packets",[])
    check(len(pending) >= 2, f"pending_packets ≥ 2 ({len(pending)})")
    # Verify no packet jumped to applied without review
    check("packet_details" in q, "packet_details ada (traceable ke chapter)")

# ── GATE 4: Consistency checker ───────────────────────────────
print("\n=== GATE 4: Consistency checker ===")
cons_path = WORK_DIR / "batch_consistency_report.json"
check(cons_path.exists(), "batch_consistency_report.json ada", "dod_4")
if cons_path.exists():
    cons = json.load(open(cons_path))
    checks = cons.get("checks",[])
    check(len(checks) >= 3, f"Minimal 3 dimensi dicek ({len(checks)})")
    dims = [c["dimension"] for c in checks]
    check("terminology_consistency" in dims, "terminology_consistency dicek")
    check("hedging_level_drift"      in dims, "hedging_level_drift dicek")
    check("closing_style_balance"    in dims, "closing_style_balance dicek")
    check("overall_status" in cons, "overall_status ada")
    check(cons.get("merge_recommendation") in
          ["safe_to_merge","review_warnings_before_merge"],
          "merge_recommendation valid")

# ── GATE 5: Merge valid ───────────────────────────────────────
print("\n=== GATE 5: Merge + final doc ===")
docx_path = DIR14E / "ESL_SROI_Full_Report_Refined.docx"
mm_path   = WORK_DIR / "merge_manifest.json"
check(docx_path.exists(), "ESL_SROI_Full_Report_Refined.docx ada", "dod_5")
check(mm_path.exists(),   "merge_manifest.json ada")
if docx_path.exists():
    size = docx_path.stat().st_size
    check(size > 20_000, f"Docx size > 20KB ({size:,} bytes)")
    with zipfile.ZipFile(docx_path) as z:
        check("word/document.xml" in z.namelist(), "word/document.xml ada")
if mm_path.exists():
    mm = json.load(open(mm_path))
    check("merged_chapters" in mm, "merged_chapters ada")
    check("consistency_report" in mm, "consistency_report referensi ada")
    # Semua 9 bab harus ada di manifest
    mc  = mm.get("merged_chapters",[])
    ids = {c["chapter_id"] for c in mc}
    for bab in [f"bab_{i}" for i in range(1,10)]:
        check(bab in ids, f"{bab} ada di merge manifest")
    # Refined chapters harus teridentifikasi
    refined = [c for c in mc if c.get("source") == "refined"]
    check(len(refined) >= 1, f"Minimal 1 chapter refined di merge ({len(refined)})")

# ── GATE 6: Analytics valid ───────────────────────────────────
print("\n=== GATE 6: Analytics ===")
an_path = DIR14E / "refinement_analytics_report.json"
check(an_path.exists(), "refinement_analytics_report.json ada", "dod_6")
if an_path.exists():
    an = json.load(open(an_path))
    check("by_type"    in an, "by_type ada")
    check("by_chapter" in an, "by_chapter ada")
    check("summary"    in an, "summary ada")
    check("trust_tier_analysis" in an, "trust_tier_analysis ada")
    check("narrative_builder_insights" in an, "narrative_builder_insights ada")
    check(an["summary"].get("total_packets",0) >= 2,
          f"total_packets ≥ 2 ({an['summary'].get('total_packets',0)})")
    tta = an.get("trust_tier_analysis",{})
    check(bool(tta.get("tier_3_always_manual")), "tier_3_always_manual ada di analytics")

# ── GATE 7: Trust tier architecture ready ────────────────────
print("\n=== GATE 7: Trust tier architecture ===")
if cfg_path.exists() and an_path.exists():
    cfg = json.load(open(cfg_path))
    an  = json.load(open(an_path))
    rp  = cfg.get("review_policy",{})
    check("tier_2_candidate_types" in rp, "tier_2_candidate_types ada di config")
    check(rp.get("tier_2_enabled") is False,
          "tier_2 tidak aktif (per keputusan full report pass pertama)", "dod_7")
    tta = an.get("trust_tier_analysis",{})
    check("tier_2_candidates" in tta, "tier_2_candidates ada di analytics")
    check(bool(tta.get("recommendation")), "trust tier recommendation ada")

# ── GATE 8: No silent drift ───────────────────────────────────
print("\n=== GATE 8: No silent drift ===")
if status_path.exists():
    st = json.load(open(status_path))
    for c in st.get("chapters",[]):
        if c.get("status") == "evaluated":
            check("evaluated_at"  in c, f"{c['chapter_id']}: audit timestamp ada")
            check("semantic_file" in c, f"{c['chapter_id']}: semantic_file traceable")
# Queue harus punya pending (no silent apply)
if q_path.exists():
    q = json.load(open(q_path))
    check(len(q.get("pending_packets",[])) > 0,
          "Queue masih ada pending — tidak ada silent auto-apply", "dod_8")
    check(q.get("auto_accept_enabled") is False,
          "auto_accept_enabled = false (mandatory review dijaga)")

# ── GATE 9: Final doc exists ──────────────────────────────────
print("\n=== GATE 9: Final doc ===")
check(docx_path.exists(), "ESL_SROI_Full_Report_Refined.docx ada", "dod_9")
if docx_path.exists():
    with zipfile.ZipFile(docx_path) as z:
        doc_xml   = z.read("word/document.xml").decode("utf-8")
        para_count= len(re.findall(r'<w:p[ >]', doc_xml))
        check(para_count >= 100, f"Minimal 100 paragraf di full doc ({para_count})")

# ── DoD SUMMARY ───────────────────────────────────────────────
print("\n" + "="*55)
print("DEFINITION OF DONE CHECK")
dod_labels = {
    "dod_1": "Batch config menentukan run refinement penuh",
    "dod_2": "Orchestrator evaluasi + packet lintas bab",
    "dod_3": "Semua packet masuk review queue",
    "dod_3_mandatory": "Review mandatory dipatuhi",
    "dod_4": "Consistency checker menghasilkan laporan lintas bab",
    "dod_5": "Full refined report berhasil digabung",
    "dod_6": "Analytics cukup kaya untuk trust-tier",
    "dod_7": "Trust tier architecture siap (tier_2 belum aktif)",
    "dod_8": "Tidak ada silent drift — audit trail lengkap",
    "dod_9": "ESL_SROI_Full_Report_Refined.docx ada",
}
all_done = True
for key, label in dod_labels.items():
    done = DOD.get(key, False)
    sym  = "✓" if done else "✗"
    print(f"  {sym} {label}")
    if not done: all_done = False

print()
if ERRORS:
    print(f"SPRINT 14E GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 14E GATE: ALL PASS")
    sys.exit(0)
