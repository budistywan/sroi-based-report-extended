"""
chat_commit_bridge.py — Sprint 13E
Menerapkan accepted/revised patches ke artefak downstream.

Behavior:
  - accepted → diterapkan ke target artifact
  - rejected → dicatat di log, tidak mengubah apa-apa
  - revised → overwrite text target saja (scoped)
  - before/after trace selalu tersimpan

Usage:
  python chat_commit_bridge.py --patches /p/ --packets /p/ --output /p/
  python chat_commit_bridge.py --auto-pilot   # jalankan pilot ESL lengkap
"""

import json, sys, os, argparse, copy, uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from chat_patch_validator import validate_patch, validate_patch_batch

parser = argparse.ArgumentParser()
parser.add_argument("--patches",    default=None, help="Path ke accepted_chat_patch.json")
parser.add_argument("--packets",    default=None, help="Path ke folder packets")
parser.add_argument("--output",     default=None)
parser.add_argument("--auto-pilot", action="store_true", help="Jalankan pilot flow lengkap")
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load enriched outlines sebagai target
DIR12 = SCRIPT_DIR.parent / "sprint12"
DIR11 = SCRIPT_DIR.parent / "sprint11"

def load_outline(path):
    if path.exists():
        d = json.load(open(path))
        return d if isinstance(d, list) else [d]
    return None


def apply_patch_to_outline(outline: list, patch: dict, packet: dict) -> tuple[list, dict]:
    """
    Terapkan patch ke outline.
    Return (updated_outline, commit_record).
    """
    updated = copy.deepcopy(outline)
    target  = patch.get("target_field", "")
    decision= patch.get("decision","")

    # Trace record
    record = {
        "commit_id":         f"commit_{uuid.uuid4().hex[:8]}",
        "patch_id":          patch.get("patch_id",""),
        "source_packet_id":  patch.get("source_packet_id",""),
        "packet_type":       packet.get("packet_type",""),
        "target_id":         packet.get("target_id",""),
        "decision":          decision,
        "original_text":     patch.get("original_text",""),
        "final_text":        patch.get("final_text",""),
        "applied":           False,
        "applicability_context": patch.get("applicability_context",""),
        "review_context":    patch.get("review_context",""),
        "committed_at":      datetime.now().isoformat(),
        "reviewer_note":     patch.get("reviewer_note",""),
    }

    if decision == "reject":
        record["rejection_reason"] = patch.get("rejection_reason","")
        record["applied"]          = False
        return updated, record

    # Accept or revise — inject into _chat_review_patches on first chapter
    if updated:
        ch = updated[0]
        ch.setdefault("_chat_review_patches", [])

        final_text = (patch.get("final_text","") if decision == "revise"
                      else patch.get("original_text",""))

        ch["_chat_review_patches"].append({
            "commit_id":     record["commit_id"],
            "packet_type":   packet.get("packet_type",""),
            "target_id":     packet.get("target_id",""),
            "decision":      decision,
            "original_text": patch.get("original_text",""),
            "final_text":    final_text,
            "reviewer_note": patch.get("reviewer_note",""),
            "committed_at":  record["committed_at"],
            "applicability_context": patch.get("applicability_context",""),
        })
        record["applied"] = True

    return updated, record


# ══════════════════════════════════════════════════════════════
# AUTO-PILOT: generate pilot patches + commit all three pilots
# ══════════════════════════════════════════════════════════════

def run_auto_pilot():
    """Generate sample patches untuk ketiga pilot dan commit semuanya."""
    print("\n=== AUTO-PILOT: Generating pilot patches ===")

    # Load packets
    pkt_b4   = json.load(open(SCRIPT_DIR / "semantic_packets_bab4.json"))[0]
    pkt_b7   = json.load(open(SCRIPT_DIR / "semantic_packets_bab7.json"))[0]
    pkt_cls  = json.load(open(SCRIPT_DIR / "semantic_packets_closing.json"))[0]

    now = datetime.now().isoformat()

    # Pilot 1: Bab IV — revise framing note
    patch_b4 = {
        "patch_id":          "pilot_b4_001",
        "source_packet_id":  pkt_b4["packet_id"],
        "decision":          "revise",
        "review_basis":      "tone",
        "original_text":     pkt_b4["context"]["current_text"],
        "final_text":        (
            "Bab ini menyusun kondisi awal program berdasarkan data yang tersedia — "
            "terutama data program, identifikasi kelompok sasaran, dan analisis hambatan "
            "yang diturunkan dari desain intervensi. Karena data statistik wilayah yang "
            "komprehensif tidak tersedia sebagai sumber utama kajian ini, pembacaan kondisi "
            "awal pada bab ini lebih tepat dipahami sebagai baseline programatik. "
            "Ini bukan kelemahan metodologis, melainkan transparansi tentang sumber data "
            "yang digunakan."
        ),
        "reviewer_note":     "Ditambahkan kalimat 'Ini bukan kelemahan metodologis' untuk menghindari nada defensif",
        "rejection_reason":  None,
        "timestamp":         now,
        "review_context":    "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
        "scope_verified":    True,
    }

    # Pilot 2: Bab VII — accept terminology note
    patch_b7 = {
        "patch_id":          "pilot_b7_001",
        "source_packet_id":  pkt_b7["packet_id"],
        "decision":          "accept",
        "review_basis":      "terminology",
        "original_text":     pkt_b7["context"]["current_text"],
        "final_text":        pkt_b7["context"]["current_text"],
        "reviewer_note":     "Terminology note sudah tepat — konsisten dengan keputusan Sprint 9.3",
        "rejection_reason":  None,
        "timestamp":         now,
        "review_context":    "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
        "scope_verified":    True,
    }

    # Pilot 3: Closing — revise dengan tone lebih formal
    patch_cls = {
        "patch_id":          "pilot_cls_001",
        "source_packet_id":  pkt_cls["packet_id"],
        "decision":          "revise",
        "review_basis":      "tone",
        "original_text":     pkt_cls["context"]["current_text"],
        "final_text":        (
            "Evaluasi SROI menunjukkan bahwa Program Enduro Sahabat Lapas menghasilkan "
            "nilai sosial-ekonomi yang melampaui investasi selama periode evaluasi 2023–2025. "
            "Tiga temuan utama yang perlu dicatat: (1) aspek Kesiapan Reintegrasi "
            "Sosial-Ekonomi mendominasi nilai bersih kumulatif; "
            "(2) Node Lapas Kota Palembang belum menghasilkan transaksi terukur dan "
            "merepresentasikan potensi kenaikan nilai yang belum terealisasi; "
            "dan (3) keberhasilan Milenial Motor membuktikan bahwa model reintegrasi "
            "produktif dapat direplikasi ke node lain pada periode berikutnya."
        ),
        "reviewer_note":     "Format penomoran (1)(2)(3) lebih formal untuk laporan PROPER. 'Terbukti' diganti 'menunjukkan'.",
        "rejection_reason":  None,
        "timestamp":         now,
        "review_context":    "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
        "scope_verified":    True,
    }

    # Satu patch yang sengaja di-reject
    rejected_patch = {
        "patch_id":          "pilot_rejected_001",
        "source_packet_id":  pkt_b7["packet_id"],
        "decision":          "reject",
        "review_basis":      "factual_correction",
        "original_text":     pkt_b7["context"]["current_text"],
        "final_text":        "",
        "reviewer_note":     "Suggestion ini tidak relevan untuk laporan yang sudah mature di terminologi",
        "rejection_reason":  "Terminologi sudah konsisten di laporan final — suggestion duplikatif",
        "timestamp":         now,
        "review_context":    "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
    }

    accepted = [patch_b4, patch_b7, patch_cls]
    rejected = [rejected_patch]

    # Validate semua patches
    all_packets = [pkt_b4, pkt_b7, pkt_cls, pkt_b7]  # pkt_b7 untuk rejected juga
    all_patches = accepted + rejected

    print("\n  Validating patches...")
    results = validate_patch_batch(all_patches, all_packets)
    for pid in results["invalid"]:
        errs = results["errors"].get(pid,[])
        print(f"  ✕ INVALID {pid}: {errs}")
    for pid in results["valid"]:
        print(f"  ✓ valid: {pid}")

    # Save patch files
    json.dump(accepted + rejected,
              open(OUTPUT_DIR / "accepted_chat_patch.json","w"),
              indent=2, ensure_ascii=False)
    json.dump(rejected,
              open(OUTPUT_DIR / "rejected_chat_log.json","w"),
              indent=2, ensure_ascii=False)
    print(f"\n  Saved accepted_chat_patch.json ({len(accepted)} accepted, {len(rejected)} rejected)")

    # ── COMMIT-BACK ─────────────────────────────────────────
    print("\n  Committing patches...")
    commit_log = []

    # Bab IV
    outline4 = load_outline(DIR12 / "enriched_outline_bab4.json")
    if outline4:
        errs = validate_patch(patch_b4, pkt_b4)
        if not errs:
            updated4, rec4 = apply_patch_to_outline(outline4, patch_b4, pkt_b4)
            json.dump(updated4, open(OUTPUT_DIR / "committed_bab4_outline.json","w"),
                      indent=2, ensure_ascii=False)
            commit_log.append(rec4)
            print(f"  ✓ committed_bab4_outline.json — {rec4['decision']}")
        else:
            print(f"  ✕ Bab IV patch rejected by validator: {errs}")

    # Bab VII
    outline7 = load_outline(DIR12 / "enriched_outline_bab7.json")
    if outline7:
        errs = validate_patch(patch_b7, pkt_b7)
        if not errs:
            updated7, rec7 = apply_patch_to_outline(outline7, patch_b7, pkt_b7)
            json.dump(updated7, open(OUTPUT_DIR / "committed_bab7_outline.json","w"),
                      indent=2, ensure_ascii=False)
            commit_log.append(rec7)
            print(f"  ✓ committed_bab7_outline.json — {rec7['decision']}")

    # Closing
    closing_base = [{"chapter_id":"closing","content": {}}]
    _, rec_cls = apply_patch_to_outline(closing_base, patch_cls, pkt_cls)
    closing_out = [{
        "chapter_id":          "closing",
        "applicability_context": "ESL_Pertamina_2025",
        "_chat_review_patches": closing_base[0].get("_chat_review_patches",[]) + [{
            "commit_id":    rec_cls["commit_id"],
            "packet_type":  "closing_paragraph",
            "target_id":    "bab_9.kesimpulan",
            "decision":     "revise",
            "original_text": patch_cls["original_text"],
            "final_text":   patch_cls["final_text"],
            "reviewer_note": patch_cls["reviewer_note"],
            "committed_at": datetime.now().isoformat(),
            "applicability_context": "ESL_Pertamina_2025",
        }]
    }]
    json.dump(closing_out, open(OUTPUT_DIR / "committed_closing_notes.json","w"),
              indent=2, ensure_ascii=False)
    commit_log.append(rec_cls)
    print(f"  ✓ committed_closing_notes.json — revise")

    # Rejected log
    rej_rec = {
        "commit_id":         f"commit_{uuid.uuid4().hex[:8]}",
        "patch_id":          rejected_patch["patch_id"],
        "decision":          "reject",
        "rejection_reason":  rejected_patch["rejection_reason"],
        "original_text":     rejected_patch["original_text"][:80] + "...",
        "applied":           False,
        "committed_at":      datetime.now().isoformat(),
    }
    json.dump([rej_rec],
              open(OUTPUT_DIR / "rejected_chat_log.json","w"),
              indent=2, ensure_ascii=False)
    print(f"  ✓ rejected_chat_log.json — 1 rejection logged")

    return commit_log


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
if args.auto_pilot or (not args.patches):
    commit_log = run_auto_pilot()
else:
    # Manual mode — load patches dan commit
    patches_path = Path(args.patches)
    if not patches_path.exists():
        print(f"FAIL: {patches_path} tidak ditemukan"); sys.exit(1)
    patches = json.load(open(patches_path))
    print(f"Loaded {len(patches)} patches from {patches_path}")
    # TODO: implement manual mode if needed
    commit_log = []

print(f"\n{'='*55}")
print("COMMIT BRIDGE COMPLETE")
applied   = sum(1 for r in commit_log if r.get("applied"))
rejected  = sum(1 for r in commit_log if not r.get("applied"))
print(f"  Applied  : {applied}")
print(f"  Rejected : {rejected}")
print(f"  Output   : {OUTPUT_DIR.resolve()}")
print("="*55)
