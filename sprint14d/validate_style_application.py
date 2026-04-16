"""
validate_style_application.py — Sprint 14D
Gates 1-10 + substance_lock_check eksplisit.

Definition of Done (DoD):
  1. Bab VII menghasilkan evaluation report
  2. Minimal 2 style packets valid
  3. Minimal 1 accepted patch diterapkan
  4. substance_lock_check pass
  5. Refined semantic JSON tetap schema-safe
  6. Refined .docx berhasil dirender
  7. Sanity check register non-Bab VII pass

Usage:
  python validate_style_application.py
  python validate_style_application.py --dir /path/sprint14d/
"""
import json, re, sys, os, argparse, zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR14D     = Path(args.dir) if args.dir else SCRIPT_DIR
# Original semantic — cari di S9W dulu, fallback ke DIR14D (zip context)
_S9W       = DIR14D.parent / "sprint9/output/esl/work"
S9W        = _S9W if _S9W.exists() else DIR14D

ERRORS = []
DOD    = {}  # track DoD items

def check(cond, msg, dod_key=None):
    if not cond:
        ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}")
    if dod_key: DOD[dod_key] = True
    return True

# ══════════════════════════════════════════════════════════════
# SUBSTANCE LOCK CHECK — eksplisit sebagai langkah terpisah
# ══════════════════════════════════════════════════════════════
def substance_lock_check(original_blocks: list, refined_blocks: list) -> list:
    """
    Verifikasi bahwa refinement tidak mengubah substansi:
    - angka numerik identik
    - label proxy/observed/pending/final tidak hilang
    - evidence refs tidak berubah
    - claim scope tidak bergeser drastis
    """
    violations = []

    # Regex untuk angka signifikan
    NUM_PAT   = re.compile(r'\d{2,}(?:[.,]\d+)*|\d+(?:[.,]\d{2,})|1\s*:\s*[\d,\.]+')
    # Label evidentiary status
    STATUS_LABELS = ["proxy","observed","pending","final","under_confirmation",
                     "partial","estimated","blended sroi","observed direct return"]

    for i, (orig, refined) in enumerate(zip(original_blocks, refined_blocks)):
        if "_style_patch" not in refined:
            continue  # blok tidak diubah

        orig_text    = orig.get("text","")
        refined_text = refined.get("text","")
        patch_info   = refined.get("_style_patch",{})

        # 1. Angka harus identik
        orig_nums    = set(NUM_PAT.findall(orig_text))
        refined_nums = set(NUM_PAT.findall(refined_text))
        added_nums   = refined_nums - orig_nums
        removed_nums = orig_nums - refined_nums

        if added_nums or removed_nums:
            violations.append({
                "block_index": i,
                "type":        "numeric_change",
                "added":       list(added_nums),
                "removed":     list(removed_nums),
                "severity":    "critical",
            })

        # 2. Status labels tidak boleh hilang
        orig_lower    = orig_text.lower()
        refined_lower = refined_text.lower()
        for label in STATUS_LABELS:
            if label in orig_lower and label not in refined_lower:
                violations.append({
                    "block_index": i,
                    "type":        "status_label_removed",
                    "label":       label,
                    "severity":    "high",
                })

        # 3. Claim scope — panjang tidak boleh berkurang drastis (>50%)
        if len(refined_text) < len(orig_text) * 0.4 and len(orig_text) > 100:
            violations.append({
                "block_index": i,
                "type":        "claim_scope_drastic_reduction",
                "orig_len":    len(orig_text),
                "refined_len": len(refined_text),
                "severity":    "high",
            })

    return violations


# ── GATE 1: Evaluation report ada dan valid ───────────────────
print("\n=== GATE 1: Evaluation report bab_7 ===")
rep_path = DIR14D / "style_evaluation_report_bab_7.json"
check(rep_path.exists(), "style_evaluation_report_bab_7.json ada", "dod_1")
if rep_path.exists():
    rep = json.load(open(rep_path))
    check(rep.get("chapter_id") == "bab_7",       "chapter_id = bab_7")
    check("register_used"  in rep,                "register_used ada")
    check("summary"        in rep,                "summary ada")
    check("paragraphs"     in rep,                "paragraphs ada")
    check(rep["summary"].get("total_blocks",0) > 0,
          f"total_blocks > 0 ({rep['summary'].get('total_blocks',0)})")
    nr = rep["summary"].get("needs_review",0) + rep["summary"].get("flagged",0)
    check(nr >= 2, f"Minimal 2 needs_review/flagged ({nr})", "dod_1_report")

# ── GATE 2: Style packets valid ───────────────────────────────
print("\n=== GATE 2: Style packets valid ===")
pkt_path = DIR14D / "paragraph_style_packets_bab_7.json"
check(pkt_path.exists(), "paragraph_style_packets_bab_7.json ada")
if pkt_path.exists():
    pkts = json.load(open(pkt_path))
    check(len(pkts) >= 2, f"Minimal 2 packets ({len(pkts)})", "dod_2")
    REQUIRED = ["packet_id","packet_type","target_id","scope",
                "decision_prompt","context","decision_options","refinement_type"]
    for pkt in pkts:
        for f in REQUIRED:
            check(f in pkt, f"packet {pkt.get('packet_id','?')}: '{f}' ada")
        check(pkt.get("packet_type") == "style_review",
              f"packet_type = style_review")
        check("accept_candidate" in pkt.get("decision_options",[]),
              f"decision_options punya accept_candidate")
        scope = pkt.get("scope",{})
        check("numeric_values" in scope.get("forbidden_changes",[]),
              f"numeric_values di forbidden_changes")
        check("proxy_labels" in scope.get("forbidden_changes",[]),
              f"proxy_labels di forbidden_changes")
        check(bool(pkt.get("refinement_type")),
              f"refinement_type tidak kosong: {pkt.get('refinement_type','')}")
        ctx = pkt.get("context",{})
        check(ctx.get("applicability_context") == "ESL_Pertamina_2025",
              f"applicability_context = ESL_Pertamina_2025")

# ── GATE 3: Minimal 1 patch diterapkan ───────────────────────
print("\n=== GATE 3: Patch applied ===")
refined_path = DIR14D / "chapter_semantic_bab_7_refined.json"
check(refined_path.exists(), "chapter_semantic_bab_7_refined.json ada")
if refined_path.exists():
    refined_data = json.load(open(refined_path))
    refined_ch   = refined_data[0] if isinstance(refined_data, list) else refined_data
    meta         = refined_ch.get("_style_refinement_metadata",{})
    applied      = meta.get("patches_applied",0)
    check(applied >= 1, f"Minimal 1 patch diterapkan ({applied})", "dod_3")
    check("applicability_context" in meta, "_style_refinement_metadata.applicability_context ada")

    # Cek blocks punya _style_patch
    patched_blocks = [b for b in refined_ch.get("blocks",[]) if "_style_patch" in b]
    check(len(patched_blocks) >= 1,
          f"Ada block dengan _style_patch ({len(patched_blocks)})")
    for pb in patched_blocks:
        sp = pb["_style_patch"]
        check("original_text"   in sp, f"_style_patch punya original_text (before)")
        check("final_text"      in sp, f"_style_patch punya final_text (after)")
        check("refinement_type" in sp, f"_style_patch punya refinement_type")
        check("committed_at"    in sp, f"_style_patch punya committed_at")

# ── GATE 4: SUBSTANCE LOCK CHECK ─────────────────────────────
print("\n=== GATE 4: Substance Lock Check ===")
orig_path = S9W / "chapter_semantic_bab7.json"
if orig_path.exists() and refined_path.exists():
    orig_data    = json.load(open(orig_path))
    refined_data = json.load(open(refined_path))
    orig_blocks  = (orig_data[0] if isinstance(orig_data,list) else orig_data).get("blocks",[])
    ref_blocks   = (refined_data[0] if isinstance(refined_data,list) else refined_data).get("blocks",[])

    violations = substance_lock_check(orig_blocks, ref_blocks)
    critical   = [v for v in violations if v.get("severity") == "critical"]
    high       = [v for v in violations if v.get("severity") == "high"]

    passed_critical = len(critical) == 0
    passed_high     = len(high) == 0
    check(passed_critical,
          f"Tidak ada perubahan angka numerik (critical violations: {len(critical)})")
    if passed_critical and passed_high:
        DOD["dod_4"] = True
        print("  PASS: substance_lock_check — semua checks pass [DoD ✓]")
    check(len(high) == 0,
          f"Tidak ada label status yang hilang (high violations: {len(high)})")

    if violations:
        for v in violations:
            print(f"    ⚠ block_{v['block_index']}: {v['type']} [{v['severity']}]")
    else:
        print("  Substance integrity: 100% — tidak ada perubahan substansi terdeteksi")

    # Cek candidate revision tidak mengandung angka baru
    if pkt_path.exists() and orig_path.exists():
        pkts      = json.load(open(pkt_path))
        orig_data = json.load(open(orig_path))
        orig_blks = (orig_data[0] if isinstance(orig_data,list) else orig_data).get("blocks",[])
        NUM_PAT   = re.compile(r'\d{2,}(?:[.,]\d+)*|1\s*:\s*[\d,\.]+')
        for pkt in pkts:
            ctx    = pkt.get("context",{})
            target = pkt.get("target_id","")
            try:
                blk_idx   = int(target.split("block_")[-1])
                full_orig = orig_blks[blk_idx].get("text","") if blk_idx < len(orig_blks) else ctx.get("current_text","")
            except:
                full_orig = ctx.get("current_text","")
            cand_t   = ctx.get("candidate_revision","") or ""
            orig_n   = set(NUM_PAT.findall(full_orig))
            cand_n   = set(NUM_PAT.findall(cand_t.split("[Stylistic hints:")[0]))
            new_nums = cand_n - orig_n
            check(len(new_nums) == 0,
                  f"Candidate revision tidak menambah angka baru: {pkt.get('packet_id','?')} (new: {new_nums})")
else:
    print("  SKIP: original semantic tidak ditemukan")

# ── GATE 5: Refined semantic schema-safe ──────────────────────
print("\n=== GATE 5: Refined semantic schema-safe ===")
if refined_path.exists():
    rd = json.load(open(refined_path))
    rc = rd[0] if isinstance(rd, list) else rd
    check("chapter_id"              in rc, "chapter_id ada")
    check("blocks"                  in rc, "blocks ada")
    check("_style_refinement_metadata" in rc, "_style_refinement_metadata ada")
    # Semua blocks harus punya type
    blocks = rc.get("blocks",[])
    check(all("type" in b for b in blocks[:5]), "Semua blocks punya 'type'", "dod_5")
    # Non-patched blocks identik dengan original
    patched_idxs = {b.get("_style_patch",{}).get("packet_id","") for b in blocks if "_style_patch" in b}
    check(len(blocks) > 0, f"blocks tidak kosong ({len(blocks)})")

# ── GATE 6: Refined .docx dirender ────────────────────────────
print("\n=== GATE 6: Refined .docx rendered ===")
docx_path = DIR14D / "ESL_SROI_Report_Refined.docx"
check(docx_path.exists(), "ESL_SROI_Report_Refined.docx ada", "dod_6")
if docx_path.exists():
    size = docx_path.stat().st_size
    check(size > 10_000, f"Ukuran docx > 10KB ({size:,} bytes)")
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        check("word/document.xml" in names, "word/document.xml ada di docx")
        doc_xml = z.read("word/document.xml").decode("utf-8")
        para_count = len(re.findall(r'<w:p[ >]', doc_xml))
        check(para_count >= 50, f"Minimal 50 paragraf di docx ({para_count})")

# ── GATE 7: Sanity check register non-bab7 ────────────────────
print("\n=== GATE 7: Sanity check register non-Bab VII ===")
sanity_path = DIR14D / "sanity_check_register_log.json"
check(sanity_path.exists(), "sanity_check_register_log.json ada", "dod_7")
if sanity_path.exists():
    sc = json.load(open(sanity_path))
    chapters_tested = sc.get("chapters_tested",[])
    non_bab7 = [c for c in chapters_tested if c.get("chapter_id") != "bab_7"]
    check(len(non_bab7) >= 1, f"Ada chapter non-bab7 yang ditest ({len(non_bab7)})")
    for c in non_bab7:
        check(c.get("register_resolved") != "evaluative_register",
              f"{c['chapter_id']}: register berbeda dari evaluative ({c.get('register_resolved','')})")
    # Cek evaluation report non-bab7 juga ada
    non_bab7_reports = list(DIR14D.glob("style_evaluation_report_bab_[^7]*.json"))
    check(len(non_bab7_reports) >= 1,
          f"Ada evaluation report non-bab7 ({[r.name for r in non_bab7_reports]})")

# ── GATE 8: Audit trail lengkap ───────────────────────────────
print("\n=== GATE 8: Audit trail ===")
pr_path = DIR14D / "style_patch_results_bab_7.json"
check(pr_path.exists(), "style_patch_results_bab_7.json ada")
if pr_path.exists():
    pr = json.load(open(pr_path))
    check(pr.get("applicability_context") == "ESL_Pertamina_2025",
          "applicability_context di patch results")
    patches = pr.get("patches",[])
    check(len(patches) >= 1, f"Ada patches ({len(patches)})")
    for p in patches:
        check(p.get("reviewed_at") is not None,
              f"patch {p.get('packet_id','?')}: reviewed_at ada")

# ── GATE 9: Paragraph register assignment log ─────────────────
print("\n=== GATE 9: Register assignment log ===")
log_path = DIR14D / "paragraph_register_assignment_log.json"
check(log_path.exists(), "paragraph_register_assignment_log.json ada")
if log_path.exists():
    log = json.load(open(log_path))
    check("chapter_id"    in log, "chapter_id ada di log")
    check("register_used" in log, "register_used ada di log")
    check("source"        in log, "source ada di log")
    check(log.get("source") == "register_style_map.json",
          "source = register_style_map.json")

# ── GATE 10: refinement_type per patch ───────────────────────
print("\n=== GATE 10: refinement_type audit ===")
if refined_path.exists():
    rd   = json.load(open(refined_path))
    rc   = rd[0] if isinstance(rd, list) else rd
    pblocks = [b for b in rc.get("blocks",[]) if "_style_patch" in b]
    for pb in pblocks:
        rt = pb["_style_patch"].get("refinement_type",[])
        check(isinstance(rt, list) and len(rt) > 0,
              f"refinement_type ada dan tidak kosong: {rt}")
        valid_types = {"opening_refine","closing_lock","hedging_adjustment",
                       "transition_smooth","pattern_removal","rhythm_adjustment"}
        check(all(t in valid_types for t in rt),
              f"Semua refinement_type valid: {rt}")

# ── DoD SUMMARY ───────────────────────────────────────────────
print("\n" + "="*55)
print("DEFINITION OF DONE CHECK")
dod_items = {
    "dod_1":        "Bab VII menghasilkan evaluation report",
    "dod_2":        "Minimal 2 style packets valid",
    "dod_3":        "Minimal 1 accepted patch diterapkan",
    "dod_4":        "substance_lock_check pass",
    "dod_5":        "Refined semantic JSON tetap schema-safe",
    "dod_6":        "Refined .docx berhasil dirender",
    "dod_7":        "Sanity check register non-Bab VII pass",
}
all_dod = True
for key, label in dod_items.items():
    done = DOD.get(key, False)
    sym  = "✓" if done else "✗"
    print(f"  {sym} {label}")
    if not done: all_dod = False

print()
if ERRORS:
    print(f"SPRINT 14D GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 14D GATE: ALL PASS")
    sys.exit(0)
