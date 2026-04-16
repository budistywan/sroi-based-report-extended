"""
cross_chapter_consistency_checker.py — Sprint 14E
Memeriksa konsistensi gaya lintas bab setelah refinement.
Menghasilkan batch_consistency_report.json

Usage:
  python cross_chapter_consistency_checker.py
  python cross_chapter_consistency_checker.py --work /p/work/
"""

import json, re, argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--work",   default=None)
parser.add_argument("--output", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
WORK_DIR   = Path(args.work)   if args.work   else SCRIPT_DIR / "work"
OUTPUT_DIR = Path(args.output) if args.output else SCRIPT_DIR

S9W  = next((p for p in [
    SCRIPT_DIR.parent / "output/esl/work",
    SCRIPT_DIR.parent / "data/semantic",
    SCRIPT_DIR.parent / "sprint9/output/esl/work",
] if p.exists()), SCRIPT_DIR.parent / "data/semantic")
S14A = SCRIPT_DIR.parent / "sprint14a"
S14C = SCRIPT_DIR.parent / "sprint14c"

profile  = json.load(open(S14A/"style_profile_reviewed.json")) if (S14A/"style_profile_reviewed.json").exists() else {}
pref_markers  = profile.get("hedging_profile",{}).get("preferred_markers",[])
avoid_markers = profile.get("hedging_profile",{}).get("avoided_markers",[])
pref_conn     = profile.get("preferred_connectors",{})

style_map = json.load(open(S14C/"register_style_map.json")) if (S14C/"register_style_map.json").exists() else {}
lookup    = style_map.get("lookup",{})


def load_chapter_text(chapter_id: str) -> str:
    """Load refined jika ada, fallback ke original."""
    refined = SCRIPT_DIR / f"work/chapter_semantic_{chapter_id}_refined.json"
    # bab_7 naming
    if chapter_id == "bab_7" and not refined.exists():
        refined = SCRIPT_DIR.parent / "sprint14d/chapter_semantic_bab_7_refined.json"

    cands = [refined,
             S9W / f"chapter_semantic_{chapter_id}.json",
             S9W / "chapter_semantic_bab7.json" if chapter_id == "bab_7" else None]

    for f in cands:
        if f and Path(f).exists():
            data = json.load(open(f))
            ch   = data[0] if isinstance(data,list) else data
            blocks = ch.get("blocks",[])
            paras  = [b.get("text","") for b in blocks
                      if b.get("type","") in {"paragraph","paragraph_lead","paragraph_small"}
                      and len(b.get("text","")) > 40]
            return "\n".join(paras)
    return ""


# Load all chapter texts
status_file = WORK_DIR / "chapter_refinement_status.json"
if not status_file.exists():
    print("FAIL: chapter_refinement_status.json tidak ditemukan"); exit(1)

status = json.load(open(status_file))
evaluated_chapters = [c["chapter_id"] for c in status["chapters"]
                      if c.get("status") == "evaluated"]

chapter_texts = {}
for ch_id in evaluated_chapters:
    txt = load_chapter_text(ch_id)
    if txt:
        chapter_texts[ch_id] = txt

print(f"Checking consistency across {len(chapter_texts)} chapters: {list(chapter_texts.keys())}")


# ── DIMENSION CHECKS ─────────────────────────────────────────

def check_terminology(texts: dict) -> dict:
    """Terminologi kritis harus konsisten lintas bab."""
    CRITICAL_TERMS = {
        "blended_sroi": ["blended sroi","blended SROI"],
        "observed_return": ["observed direct return","Observed direct return"],
        "proxy": ["proxy","nilai proxy"],
        "reintegrasi": ["reintegrasi","Reintegrasi"],
    }
    term_presence = {}
    for term, variants in CRITICAL_TERMS.items():
        presence = {}
        for ch_id, txt in texts.items():
            found = any(v.lower() in txt.lower() for v in variants)
            if found:
                presence[ch_id] = True
        term_presence[term] = presence

    issues = []
    # Kalau term muncul di bab_7 (evaluative) tapi hilang di bab_9 (conclusive) = masalah
    for term, presence in term_presence.items():
        if "bab_7" in presence and "bab_9" in texts and "bab_9" not in presence:
            issues.append(f"'{term}' ada di bab_7 tapi tidak di bab_9")

    return {
        "dimension":    "terminology_consistency",
        "status":       "warning" if issues else "pass",
        "issues":       issues,
        "term_coverage":term_presence,
    }


def check_hedging_drift(texts: dict) -> dict:
    """Hedging level tidak boleh drift drastis antar bab."""
    hedging_scores = {}
    for ch_id, txt in texts.items():
        pref_count  = sum(1 for m in pref_markers if m.lower() in txt.lower())
        avoid_count = sum(1 for m in avoid_markers if m.lower() in txt.lower())
        # Score: lebih tinggi = lebih firm-but-guarded
        score = pref_count / max(1, pref_count + avoid_count + 1)
        hedging_scores[ch_id] = round(score, 2)

    scores = list(hedging_scores.values())
    drift  = max(scores) - min(scores) if len(scores) >= 2 else 0
    status = "warning" if drift > 0.4 else "pass"
    note   = f"Hedging drift {drift:.2f} — " + \
             ("terlalu besar" if drift > 0.4 else "dalam batas wajar")

    return {
        "dimension":      "hedging_level_drift",
        "status":         status,
        "scores":         hedging_scores,
        "drift":          round(drift, 2),
        "note":           note,
    }


def check_closing_balance(texts: dict) -> dict:
    """Pola penutup tidak boleh terlalu timpang antar bab."""
    LOCKED = ["Dengan demikian","Hal tersebut menegaskan","Pada titik inilah",
              "Di sinilah","Inilah","Dalam kerangka","Hal ini menegaskan"]
    closing_scores = {}
    for ch_id, txt in texts.items():
        paras    = [p.strip() for p in txt.split('\n') if len(p.strip()) > 40]
        if not paras: continue
        locked_n = sum(1 for p in paras
                       if any(m.lower() in p.split('.')[-1].lower() for m in LOCKED))
        closing_scores[ch_id] = round(locked_n / max(1,len(paras)), 2)

    scores = list(closing_scores.values())
    if len(scores) >= 2:
        gap    = max(scores) - min(scores)
        status = "warning" if gap > 0.5 else "pass"
        note   = (f"Closing balance gap {gap:.2f} — "
                  + ("satu bab jauh lebih assertive" if gap > 0.5 else "seimbang"))
    else:
        status = "pass"; note = "tidak cukup bab untuk dibandingkan"

    return {
        "dimension": "closing_style_balance",
        "status":    status,
        "scores":    closing_scores,
        "note":      note,
    }


def check_connector_drift(texts: dict) -> dict:
    """Preferred connectors harus dipakai secara merata."""
    ALL_CONN = (pref_conn.get("intra_paragraph",[]) +
                pref_conn.get("inter_paragraph",[]))
    conn_counts = {}
    for ch_id, txt in texts.items():
        count = sum(1 for c in ALL_CONN if c.lower() in txt.lower())
        conn_counts[ch_id] = count

    counts  = list(conn_counts.values())
    drift   = max(counts) - min(counts) if len(counts) >= 2 else 0
    status  = "warning" if drift > 8 else "pass"
    return {
        "dimension":    "connector_drift",
        "status":       status,
        "counts":       conn_counts,
        "drift":        drift,
        "note":         f"Connector usage drift: {drift} (max-min)",
    }


def check_tone_drift(texts: dict) -> dict:
    """Cek apakah ada bab yang jauh lebih 'academic' atau 'flat'."""
    ACADEMIC_MARKERS = ["menunjukkan bahwa","dapat dipahami","mengindikasikan",
                        "dalam konteks","memperlihatkan","mencerminkan"]
    FLAT_MARKERS     = ["adalah","merupakan","terdiri dari","terdapat","dilakukan"]

    tone_scores = {}
    for ch_id, txt in texts.items():
        words    = len(txt.split())
        academic = sum(txt.lower().count(m) for m in ACADEMIC_MARKERS)
        flat     = sum(txt.lower().count(m) for m in FLAT_MARKERS)
        # Ratio academic per 100 words
        score = round((academic / max(1,words)) * 100, 2)
        tone_scores[ch_id] = {"academic_density": score, "flat_count": flat}

    scores  = [v["academic_density"] for v in tone_scores.values()]
    drift   = round(max(scores) - min(scores), 2) if len(scores) >= 2 else 0
    status  = "warning" if drift > 1.5 else "pass"
    return {
        "dimension": "tone_drift",
        "status":    status,
        "scores":    tone_scores,
        "drift":     drift,
        "note":      f"Academic density drift: {drift} per 100 words",
    }


# ── RUN ALL CHECKS ────────────────────────────────────────────
checks = [
    check_terminology(chapter_texts),
    check_hedging_drift(chapter_texts),
    check_closing_balance(chapter_texts),
    check_connector_drift(chapter_texts),
    check_tone_drift(chapter_texts),
]

warnings = [c for c in checks if c["status"] == "warning"]
passes   = [c for c in checks if c["status"] == "pass"]

overall = "pass" if not warnings else \
          "pass_with_notes" if len(warnings) <= 2 else "warning"

report = {
    "report_id":         f"batch_consistency_esl_v1",
    "run_id":            "batch_refine_esl_v1",
    "generated_at":      datetime.now().isoformat(),
    "chapters_checked":  list(chapter_texts.keys()),
    "overall_status":    overall,
    "summary": {
        "total_checks":  len(checks),
        "passed":        len(passes),
        "warnings":      len(warnings),
    },
    "checks": checks,
    "merge_recommendation":
        "safe_to_merge" if overall != "warning" else
        "review_warnings_before_merge",
}

out = WORK_DIR / "batch_consistency_report.json"
json.dump(report, open(out,"w"), indent=2, ensure_ascii=False)

print(f"\nConsistency: {overall.upper()}")
for c in checks:
    sym = "✓" if c["status"] == "pass" else "⚠"
    print(f"  {sym} {c['dimension']}: {c['status']}")
print(f"\nReport: {out}")
print("CONSISTENCY CHECK COMPLETE")
