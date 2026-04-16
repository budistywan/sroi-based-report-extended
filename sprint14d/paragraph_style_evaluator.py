"""
paragraph_style_evaluator.py — Sprint 14D Komponen 1
Membaca chapter_semantic_bab_X.json, menentukan register,
mengevaluasi tiap paragraf terhadap signature, menghasilkan:
  - paragraph_register_assignment_log.json
  - style_evaluation_report_{bab}.json

Usage:
  python paragraph_style_evaluator.py --chapter bab_7
  python paragraph_style_evaluator.py --chapter bab_4 --semantic /p/bab_4.json
"""

import json, re, sys, os, argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--chapter",  default="bab_7")
parser.add_argument("--semantic", default=None)
parser.add_argument("--output",   default=None)
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
CHAPTER_ID   = args.chapter
OUTPUT_DIR   = Path(args.output) if args.output else SCRIPT_DIR

# Path resolution
S14A = SCRIPT_DIR.parent / "sprint14a"
S14C = SCRIPT_DIR.parent / "sprint14c"
S9W  = SCRIPT_DIR.parent / "sprint9/output/esl/work"

SEMANTIC_FILE = Path(args.semantic) if args.semantic \
    else S9W / f"chapter_semantic_{CHAPTER_ID.replace('bab_','bab_')}.json"
# Handle naming convention differences
if not SEMANTIC_FILE.exists():
    alt = S9W / f"chapter_semantic_{CHAPTER_ID}.json"
    if alt.exists(): SEMANTIC_FILE = alt

MAP_FILE      = S14C / "register_style_map.json"
PROFILE_FILE  = S14A / "style_profile_reviewed.json"
DP_FILE       = S14A / "disliked_patterns.json"

for f in [SEMANTIC_FILE, MAP_FILE, S14C]:
    if not Path(f).exists():
        print(f"FAIL: {f} tidak ditemukan"); sys.exit(1)

print(f"Chapter  : {CHAPTER_ID}")
print(f"Semantic : {SEMANTIC_FILE.resolve()}")

# ── LOAD INPUTS ───────────────────────────────────────────────
style_map  = json.load(open(MAP_FILE))
lookup     = style_map.get("lookup", {})
dp_data    = json.load(open(DP_FILE)) if DP_FILE.exists() else {}
disliked   = dp_data.get("patterns", [])

raw = json.load(open(SEMANTIC_FILE))
chapter_data = raw[0] if isinstance(raw, list) else raw
blocks = chapter_data.get("blocks", [])

# ── RESOLVE REGISTER ──────────────────────────────────────────
register_name = lookup.get(CHAPTER_ID, style_map.get("default_register","framing_register"))
reg_key       = register_name.replace("_register","")
sig_file      = S14C / f"style_signature_{reg_key}.json"

if not sig_file.exists():
    print(f"FAIL: Signature file {sig_file} tidak ditemukan"); sys.exit(1)

signature = json.load(open(sig_file))
dims      = signature.get("dimensions", {})

# Write assignment log
assignment_log = {
    "chapter_id":    CHAPTER_ID,
    "register_used": register_name,
    "signature_file": sig_file.name,
    "source":        "register_style_map.json",
    "resolved_at":   datetime.now().isoformat(),
    "default_used":  CHAPTER_ID not in lookup,
}
log_path = OUTPUT_DIR / "paragraph_register_assignment_log.json"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
json.dump(assignment_log, open(log_path,"w"), indent=2, ensure_ascii=False)
print(f"Register : {register_name}")
print(f"Signature: {sig_file.name}")

# ── PATTERN DETECTORS ─────────────────────────────────────────
NARASI_TYPES = {"paragraph","paragraph_lead","paragraph_small"}

# Opening patterns dari signature
OPENING_PAT = dims.get("opening_style",{}).get("pattern","")
OPENING_EXAMPLES = dims.get("opening_style",{}).get("examples",[])

CONTEXT_FIRST = [r"^(Bab|Dalam|Pada|Secara|Di|Kondisi|Berangkat|Jika|Hal ini)"]
EVALUATIVE    = [r"^(Kajian|Evaluasi|Penilaian|Analisis|Dua|Tiga|Perbedaan antara)"]
INVESTIGATIVE = [r"^(Jika ditelaah|Kondisi yang ada|Dalam pengamatan|Bab ini menyusun)"]
SUMMARY_FRAME = [r"^(Evaluasi SROI menunjukkan|Ke depan|Tiga temuan|Dalam jangka)"]
CLAIM_FIRST   = [r"^Program (ini|ESL|Enduro)", r"^Hal ini\b", r"^SROI\b"]

def detect_opening(text: str) -> tuple[str, float]:
    first = text.split('.')[0].strip()
    for pat in CONTEXT_FIRST:
        if re.match(pat, first): return "context_first", 0.85
    for pat in EVALUATIVE:
        if re.match(pat, first): return "evaluative_frame", 0.85
    for pat in INVESTIGATIVE:
        if re.match(pat, first): return "investigative_frame", 0.85
    for pat in SUMMARY_FRAME:
        if re.match(pat, first): return "evaluative_summary_frame", 0.85
    for pat in CLAIM_FIRST:
        if re.match(pat, first): return "claim_first", 0.80
    return "subject_first", 0.60

PREFERRED_MARKERS = dims.get("hedging_degree",{}).get("preferred_markers",[])
AVOIDED_MARKERS   = dims.get("hedging_degree",{}).get("avoided_markers",[])
FIRMNESS          = dims.get("hedging_degree",{}).get("firmness","moderate")

def detect_hedging(text: str) -> tuple[str, list, list]:
    tl = text.lower()
    found_pref   = [m for m in PREFERRED_MARKERS if m.lower() in tl]
    found_avoid  = [m for m in AVOIDED_MARKERS   if m.lower() in tl]
    if found_avoid:
        return "violation", found_pref, found_avoid
    elif found_pref:
        return "ok", found_pref, []
    return "neutral", [], []

LOCKED_PATTERNS = ["Dengan demikian", "Hal tersebut menegaskan", "Pada titik inilah",
                   "Di sinilah", "Inilah", "Dalam kerangka evaluatif"]
LEARNING_FWD    = ["Di sinilah pembelajaran", "bukan pada ... tetapi", "justru menjadi"]
FWD_LOCKED      = ["Ke depan", "Dengan demikian", "nilai sosial program"]
ORIENTATIVE     = ["Di sinilah kajian", "mengambil peran", "menjembatani"]

def detect_closing(text: str, register: str) -> tuple[str, float]:
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    last = sentences[-1] if sentences else ""
    ll   = last.lower()
    if register == "evaluative_register":
        for p in LOCKED_PATTERNS:
            if p.lower() in ll: return "evaluative_locked", 0.9
        if len(last.split()) < 12: return "short_affirmation", 0.75
        return "open_elaboration", 0.5
    elif register == "reflective_register":
        for p in LEARNING_FWD:
            if p.lower() in ll: return "learning_forward", 0.9
        return "open_reflection", 0.6
    elif register == "conclusive_register":
        for p in FWD_LOCKED:
            if p.lower() in ll: return "forward_locked", 0.9
        return "open_elaboration", 0.5
    else:  # framing, analytic
        for p in LOCKED_PATTERNS + ORIENTATIVE:
            if p.lower() in ll: return "anchored_close", 0.8
        return "open_elaboration", 0.5

def detect_disliked(text: str) -> list:
    found = []
    for dp in disliked:
        pid     = dp["pattern_id"]
        severity= dp["severity"]
        examples= dp.get("examples",[])
        if pid == "DP_AI_GENERIC":
            if any(ex[:30].lower() in text.lower() for ex in examples):
                found.append({"pattern_id": pid, "severity": severity})
        elif pid == "DP_BOMBASTIC":
            avoided = ["terbukti mutlak","tidak diragukan lagi","sudah pasti","sangat luar biasa"]
            if any(a in text.lower() for a in avoided):
                found.append({"pattern_id": pid, "severity": severity})
        elif pid == "DP_MECHANICAL_EXPANSION":
            sentences = [s.strip() for s in text.split('.') if s.strip()]
            if len(sentences) >= 3:
                lens = [len(s.split()) for s in sentences]
                avg  = sum(lens)/len(lens)
                if max(lens) - min(lens) < 5 and avg < 15:
                    found.append({"pattern_id": pid, "severity": severity})
        elif pid == "DP_FLAT_PARAGRAPH":
            has_interp = any(m in text.lower() for m in
                ["menunjukkan bahwa","mengindikasikan","dapat dipahami","hal ini mencerminkan",
                 "memperlihatkan","mencerminkan","mengindikasikan","hal ini","dengan demikian"])
            # Hanya flag jika paragraf panjang AND tidak ada interpretasi sama sekali
            if not has_interp and len(text) > 300:
                found.append({"pattern_id": pid, "severity": "low"})
        elif pid == "DP_REPETITIVE_OPENING":
            pass  # handled at report level
    return found

def detect_rhythm(text: str) -> tuple[str, float]:
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 5]
    if len(sentences) < 2: return "too_short", 0.5
    lens = [len(s.split()) for s in sentences]
    has_short  = any(l < 10 for l in lens)
    has_medium = any(10 <= l <= 22 for l in lens)
    has_long   = any(l > 22 for l in lens)
    if (has_short or has_medium) and has_long:
        return "mixed", 0.9
    elif all(l > 20 for l in lens):
        return "uniformly_long", 0.6
    elif all(l < 12 for l in lens):
        return "uniformly_short", 0.7
    return "mixed", 0.8

def compute_candidate_revision(text: str, gaps: list, signature: dict) -> tuple[str | None, float]:
    """
    Candidate revision opsional — hanya jika confidence cukup tinggi.
    TIDAK mengubah angka, label proxy/observed, atau klaim metodologis.
    """
    gap_types = [g["dimension"] for g in gaps]
    confidence = 0.0

    # Hanya generate jika gap jelas dan terbatas
    if len(gaps) > 3:
        return None, 0.0  # terlalu banyak gap — biarkan reviewer yang putuskan

    hints = []
    if "opening_pattern" in gap_types:
        expected = signature.get("dimensions",{}).get("opening_style",{}).get("pattern","")
        if expected == "evaluative_frame":
            hints.append("Pertimbangkan membuka dengan framing evaluatif sebelum klaim inti.")
            confidence += 0.3
        elif expected == "investigative_frame":
            hints.append("Pertimbangkan membuka dengan telaah kondisi sebelum menyatakan temuan.")
            confidence += 0.3

    if "closing_pattern" in gap_types:
        hints.append("Pertimbangkan menambahkan kalimat penutup yang mengunci makna paragraf.")
        confidence += 0.3

    if "hedging_violation" in gap_types:
        hints.append("Periksa marker evaluatif — pastikan tidak ada klaim yang overclaim.")
        confidence += 0.2

    if not hints or confidence < 0.4:
        return None, confidence

    candidate = text + f"\n\n[Stylistic hints: {' | '.join(hints)}]"
    return candidate, round(confidence, 2)


# ── EVALUATE ALL BLOCKS ───────────────────────────────────────
print(f"\nEvaluating {len(blocks)} blocks in {CHAPTER_ID}...")
results = []
opening_patterns_seen = []

for i, block in enumerate(blocks):
    btype = block.get("type","")
    text  = block.get("text","")

    if btype not in NARASI_TYPES or len(text.strip()) < 40:
        results.append({
            "block_index": i,
            "block_type":  btype,
            "text_preview": text[:50] if text else "(non-text block)",
            "status":      "skip",
            "gaps":        [],
        })
        continue

    # Evaluate
    gaps = []
    opening_detected, opening_conf = detect_opening(text)
    opening_patterns_seen.append(opening_detected)

    # Check opening against register expected
    expected_opening = dims.get("opening_style",{}).get("pattern","")
    # Untuk evaluative register: subject_first dengan "Program" adalah acceptable
    # (ciri khas laporan SROI — tidak semua paragraf harus dimulai evaluative_frame)
    is_acceptable_variant = (
        register_name == "evaluative_register" and
        opening_detected in ["subject_first","evaluative_frame","evaluative_summary_frame"]
    )
    if not is_acceptable_variant and opening_detected != expected_opening and opening_conf < 0.85:
        gaps.append({
            "dimension":  "opening_pattern",
            "expected":   expected_opening,
            "detected":   opening_detected,
            "severity":   "medium",
            "note":       f"Pembuka '{opening_detected}' — register {register_name} mengharapkan '{expected_opening}'",
        })

    # Check hedging
    hedge_status, found_pref, found_avoid = detect_hedging(text)
    if hedge_status == "violation":
        gaps.append({
            "dimension":      "hedging_violation",
            "avoided_found":  found_avoid,
            "severity":       "high",
            "note":           f"Ditemukan marker yang harus dihindari: {found_avoid}",
        })

    # Check disliked patterns
    dp_found = detect_disliked(text)
    for dp in dp_found:
        gaps.append({
            "dimension":   "disliked_pattern",
            "pattern_id":  dp["pattern_id"],
            "severity":    dp["severity"],
            "note":        f"Disliked pattern terdeteksi: {dp['pattern_id']}",
        })

    # Check closing
    closing_detected, closing_conf = detect_closing(text, register_name)
    expected_closing = dims.get("closing_style",{}).get("pattern","")
    if closing_conf < 0.7 or (expected_closing and closing_detected != expected_closing and closing_conf < 0.8):
        gaps.append({
            "dimension":  "closing_pattern",
            "expected":   expected_closing,
            "detected":   closing_detected,
            "severity":   "low",
            "note":       "Penutup paragraf mungkin perlu pengunci yang lebih kuat",
        })

    # Check rhythm
    rhythm_detected, rhythm_conf = detect_rhythm(text)
    if rhythm_detected == "uniformly_long" and rhythm_conf < 0.8:
        gaps.append({
            "dimension": "sentence_rhythm",
            "detected":  rhythm_detected,
            "severity":  "low",
            "note":      "Semua kalimat panjang — pertimbangkan variasi ritme",
        })

    # Determine status
    # Low-only gaps tidak trigger needs_review — hanya dicatat
    has_high   = any(g["severity"] == "high"   for g in gaps)
    has_medium = any(g["severity"] == "medium"  for g in gaps)
    has_low_only = gaps and not has_high and not has_medium

    if has_high:
        status = "flagged"
    elif has_medium:
        status = "needs_review"
    elif has_low_only:
        # noted: dicatat — evaluator mungkin mengekspor beberapa untuk advisory review
        # tapi bukan prioritas utama
        n_gaps = len(gaps)
        status = "needs_review" if n_gaps >= 2 else "noted"
    else:
        status = "clean"

    # Candidate revision (opsional)
    candidate, cand_conf = compute_candidate_revision(text, gaps, signature) if gaps else (None, 0.0)

    # Register confidence: seberapa yakin assignment register ini
    # 1.0 jika ada di lookup table, lebih rendah jika pakai default
    reg_confidence = 1.0 if CHAPTER_ID in lookup else 0.75

    result = {
        "block_index":         i,
        "block_type":          btype,
        "full_text":           text,
        "text_preview":        text[:100] + "..." if len(text) > 100 else text,
        "status":              status,
        "register_used":       register_name,
        "register_confidence": reg_confidence,
        "gaps":                gaps,
        "opening_detected":    opening_detected,
        "closing_detected":    closing_detected,
        "rhythm_detected":     rhythm_detected,
    }
    if candidate:
        result["candidate_revision"]    = candidate
        result["candidate_confidence"]  = cand_conf
    else:
        result["candidate_revision"]    = None
        result["candidate_confidence"]  = cand_conf
        if gaps:
            result["stylistic_diagnosis"] = (
                f"Gap terdeteksi: {[g['dimension'] for g in gaps]}. "
                f"Confidence revision rendah ({cand_conf:.2f}) — reviewer disarankan merevisi manual."
            )

    results.append(result)

# Count
status_counts = Counter(r["status"] for r in results)
print(f"  clean:        {status_counts['clean']}")
print(f"  needs_review: {status_counts['needs_review']}")
print(f"  flagged:      {status_counts['flagged']}")
print(f"  skip:         {status_counts['skip']}")

# Compose report
report = {
    "report_id":      f"eval_{CHAPTER_ID}_v1",
    "chapter_id":     CHAPTER_ID,
    "register_used":  register_name,
    "signature_file": sig_file.name,
    "evaluated_at":   datetime.now().isoformat(),
    "summary": {
        "total_blocks":     len(blocks),
        "total_paragraphs": sum(1 for r in results if r["status"] != "skip"),
        "clean":            status_counts["clean"],
        "needs_review":     status_counts["needs_review"],
        "flagged":          status_counts["flagged"],
        "skip":             status_counts["skip"],
    },
    "paragraphs": results,
}

out_path = OUTPUT_DIR / f"style_evaluation_report_{CHAPTER_ID}.json"
json.dump(report, open(out_path,"w"), indent=2, ensure_ascii=False)
print(f"\nReport: {out_path}")
print(f"{'='*55}")
print("EVALUATOR COMPLETE")
print("="*55)
