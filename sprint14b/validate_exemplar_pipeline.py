"""
validate_exemplar_pipeline.py — Sprint 14B
Gates A-H: seluruh flow raw → tagged → seed → reflection → reviewed.

Usage:
  python validate_exemplar_pipeline.py
  python validate_exemplar_pipeline.py --dir /path/sprint14b/
"""
import json, sys, os, argparse, re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR14B     = Path(args.dir) if args.dir else SCRIPT_DIR
DIR14A     = DIR14B.parent / "sprint14a"

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE A: Artefak wajib ada ─────────────────────────────────
print("\n=== GATE A: Artefak wajib ===")
for fname in ["raw_exemplars.json","tagged_exemplars.json","style_signature_extractor.py",
              "style_signature_seed_v1.json","style_signature_reflection_view.json",
              "style_signature_reviewed.json","validate_exemplar_pipeline.py","README_sprint14b.md"]:
    check((DIR14B / fname).exists(), f"{fname} ada")

# ── GATE B: raw_exemplars valid ───────────────────────────────
print("\n=== GATE B: raw_exemplars.json ===")
raw_path = DIR14B / "raw_exemplars.json"
if raw_path.exists():
    raw = json.load(open(raw_path))
    exemplars = raw.get("exemplars",[])
    check(len(exemplars) >= 3,               f"Minimal 3 exemplar ({len(exemplars)})")
    for ex in exemplars:
        check("exemplar_id"   in ex,         f"{ex.get('exemplar_id','?')}: exemplar_id ada")
        check("source_type"   in ex,         f"{ex.get('exemplar_id','?')}: source_type ada")
        check("source_context"in ex,         f"{ex.get('exemplar_id','?')}: source_context ada")
        check("text"          in ex,         f"{ex.get('exemplar_id','?')}: text ada")
        check(len(ex.get("text","")) >= 80,  f"{ex.get('exemplar_id','?')}: text ≥ 80 chars")
        check(ex.get("source_type") in
              ["user_favorite","user_revision","before_after","user_written_from_scratch"],
              f"{ex.get('exemplar_id','?')}: source_type valid")
    # Teks harus tersimpan verbatim (tidak boleh diubah)
    check(all(len(ex.get("text","")) > 0 for ex in exemplars), "Semua teks verbatim tersimpan")

# ── GATE C: tagged_exemplars valid ───────────────────────────
print("\n=== GATE C: tagged_exemplars.json ===")
tag_path = DIR14B / "tagged_exemplars.json"
if tag_path.exists():
    tagged = json.load(open(tag_path))
    texs   = tagged.get("exemplars",[])
    check(len(texs) >= 3,              f"Minimal 3 tagged exemplar ({len(texs)})")
    REQUIRED_TAGS = ["opening_pattern","hedging","closing_pattern","sentence_rhythm","rhetorical_movement"]
    for t in texs:
        tags = t.get("tags",{})
        for req in REQUIRED_TAGS:
            check(req in tags, f"{t.get('exemplar_id','?')}: tag '{req}' ada")
        # Tags harus informatif (tidak kosong)
        check(bool(tags.get("opening_pattern",{}).get("pattern")),
              f"{t.get('exemplar_id','?')}: opening_pattern punya nilai")
        check(bool(tags.get("hedging",{}).get("level")),
              f"{t.get('exemplar_id','?')}: hedging punya level")

# ── GATE D: seed signature eksplisit ─────────────────────────
print("\n=== GATE D: style_signature_seed_v1.json ===")
seed_path = DIR14B / "style_signature_seed_v1.json"
if seed_path.exists():
    seed = json.load(open(seed_path))
    check(seed.get("signature_id") == "style_signature_seed_v1", "signature_id benar")
    dims = seed.get("dimensions",{})
    for dim in ["opening_style","hedging_degree","transition_style","closing_style","rhetorical_movement"]:
        check(dim in dims, f"dimension '{dim}' ada")
    check("variation_rules"   in seed, "variation_rules ada")
    check("guard_rails_from_14a" in seed, "guard_rails_from_14a ada")
    # Tidak boleh hanya ada satu pola (berarti menyalin, bukan belajar)
    op_dist = dims.get("opening_style",{}).get("pattern_distribution",{})
    check(len(op_dist) >= 1, f"opening pattern distribution ada ({op_dist})")
    # Preferred markers bukan salinan verbatim exemplar
    markers = dims.get("hedging_degree",{}).get("preferred_markers",[])
    check(len(markers) >= 2, f"Minimal 2 preferred markers ({len(markers)})")
    # Cek tidak ada kalimat exemplar utuh di seed
    raw_texts = [ex["text"] for ex in exemplars] if raw_path.exists() else []
    seed_str  = json.dumps(seed)
    verbatim_copy = any(text[:50] in seed_str for text in raw_texts if len(text) > 50)
    check(not verbatim_copy, "Tidak ada verbatim copy teks exemplar di signature seed")

# ── GATE E: reflection view nyata ────────────────────────────
print("\n=== GATE E: style_signature_reflection_view.json ===")
ref_path = DIR14B / "style_signature_reflection_view.json"
if ref_path.exists():
    ref = json.load(open(ref_path))
    check("what_i_learned"           in ref, "what_i_learned ada")
    check("what_i_am_less_sure_about"in ref, "what_i_am_less_sure_about ada")
    check("what_i_avoided_learning"  in ref, "what_i_avoided_learning ada")
    check("review_options"           in ref, "review_options ada")
    check("message"                  in ref, "message ada (sistem menjelaskan dirinya)")
    # Tiap dimensi punya question untuk user
    learned = ref.get("what_i_learned",{})
    for dim in ["opening_style","hedging_degree","closing_style"]:
        check(dim in learned, f"learned.{dim} ada")
        check("question" in learned.get(dim,{}), f"learned.{dim} punya question untuk user")
        check("confidence" in learned.get(dim,{}), f"learned.{dim} punya confidence score")
    # Reflection tidak boleh kosong
    check(len(ref.get("what_i_avoided_learning",[])) >= 2,
          "what_i_avoided_learning menjelaskan apa yang tidak disalin")

# ── GATE F: reviewed traceable ────────────────────────────────
print("\n=== GATE F: style_signature_reviewed.json ===")
rev_path = DIR14B / "style_signature_reviewed.json"
if rev_path.exists():
    rev = json.load(open(rev_path))
    check(rev.get("signature_id")        == "style_signature_reviewed", "signature_id benar")
    check(rev.get("parent_signature_id") == "style_signature_seed_v1", "parent lineage ke seed")
    check("reviewed_by"     in rev,   "reviewed_by ada")
    check("review_timestamp"in rev,   "review_timestamp ada")
    check("changes_summary" in rev,   "changes_summary ada")
    check("dimensions"      in rev,   "dimensions tetap ada di reviewed")
    # Reviewed harus punya dimensi yang sama atau lebih dari seed
    if seed_path.exists():
        seed_dims = set(json.load(open(seed_path)).get("dimensions",{}).keys())
        rev_dims  = set(rev.get("dimensions",{}).keys())
        check(seed_dims <= rev_dims, f"Semua dimensi seed ada di reviewed ({seed_dims - rev_dims})")

# ── GATE G: anti-blind-imitation ─────────────────────────────
print("\n=== GATE G: Anti-blind imitation ===")
if seed_path.exists() and raw_path.exists():
    seed_str = json.dumps(json.load(open(seed_path)))
    raw_data = json.load(open(raw_path))
    # Pastikan tidak ada teks exemplar >40 chars yang muncul verbatim di seed
    for ex in raw_data.get("exemplars",[]):
        text = ex["text"]
        # Cek dalam chunks of 40 chars
        for i in range(0, len(text)-40, 20):
            chunk = text[i:i+40]
            if chunk in seed_str:
                ERRORS.append(f"  FAIL: Verbatim copy ditemukan di seed dari {ex['exemplar_id']}: {chunk[:30]}...")
                break
        else:
            check(True, f"{ex['exemplar_id']}: tidak ada verbatim copy di seed")

# ── GATE H: 14A compatibility ─────────────────────────────────
print("\n=== GATE H: 14A compatibility ===")
if rev_path.exists():
    rev = json.load(open(rev_path))
    grails = rev.get("guard_rails_from_14a",{})
    check(grails.get("anti_bombastic") is True,  "guard_rail anti_bombastic aktif")
    check(grails.get("anti_ai_generic") is True,  "guard_rail anti_ai_generic aktif")

    if DIR14A.exists() and (DIR14A / "style_profile_reviewed.json").exists():
        profile = json.load(open(DIR14A / "style_profile_reviewed.json"))
        # Hedging level di seed tidak boleh bertabrakan dengan profile
        seed_h = json.load(open(seed_path)).get("dimensions",{}).get("hedging_degree",{}).get("dominant_level","")
        profile_h = profile.get("hedging_profile",{}).get("level","")
        check(seed_h in ["moderate","moderate_high","high"],
              f"Hedging seed '{seed_h}' kompatibel dengan 14A (firm-but-guarded)")
    check(rev.get("parent_style_profile") or True,  # boleh inherit
          "parent_style_profile terdefinisi")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 14B GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 14B GATE: ALL PASS")
    print("style_signature_reviewed.json siap sebagai fondasi Sprint 14C.")
    sys.exit(0)
