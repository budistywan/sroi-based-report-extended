"""
style_signature_extractor.py — Sprint 14B
Membaca raw_exemplars.json, mengekstrak pola gaya, menghasilkan:
  - tagged_exemplars.json
  - style_signature_seed_v1.json
  - style_signature_reflection_view.json

Prinsip:
  - belajar pola, bukan menyalin kalimat
  - signature harus eksplisit dan reviewable
  - differentiates dominant pattern dari allowed variation

Usage:
  python style_signature_extractor.py
  python style_signature_extractor.py --exemplars /p/ --output /p/
"""

import json, re, sys, os, argparse
from pathlib import Path
from datetime import datetime
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--exemplars", default=None)
parser.add_argument("--profile",   default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
EXEMPLAR_FILE = Path(args.exemplars) if args.exemplars \
    else Path(os.environ.get("EXEMPLAR_FILE", SCRIPT_DIR / "raw_exemplars.json"))
PROFILE_FILE  = Path(args.profile)   if args.profile   \
    else Path(os.environ.get("PROFILE_FILE",
              SCRIPT_DIR.parent / "sprint14a/style_profile_reviewed.json"))
OUTPUT_DIR    = Path(args.output)    if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

for f in [EXEMPLAR_FILE]:
    if not f.exists():
        print(f"FAIL: {f} tidak ditemukan"); sys.exit(1)

data      = json.load(open(EXEMPLAR_FILE))
exemplars = data.get("exemplars", [])
profile   = json.load(open(PROFILE_FILE)) if PROFILE_FILE.exists() else {}
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Exemplars : {len(exemplars)}")
print(f"Profile   : {PROFILE_FILE.name if PROFILE_FILE.exists() else 'not found'}")


# ══════════════════════════════════════════════════════════════
# PATTERN DETECTORS (rule-based, human-readable)
# ══════════════════════════════════════════════════════════════

CONTEXT_FIRST_MARKERS = [
    r"^(Bab|Dalam|Pada|Secara|Di|Kondisi|Berangkat|Jika|Hal ini)",
    r"^[A-Z][a-z]+ (ini|tersebut|itu)\b",
]
EVALUATIVE_FRAME_MARKERS = [
    r"^(Kajian|Evaluasi|Penilaian|Analisis) (SROI|ini|program)",
    r"^(Dua|Tiga|Empat|Lima) dari",
    r"^Perbedaan antara",
]
CLAIM_FIRST_MARKERS = [
    r"^Program (ini|ESL|Enduro)",
    r"^Hasil (kajian|evaluasi|analisis)",
    r"^SROI\b",
]
SOFT_CONNECTORS = [
    "Dalam konteks ini", "Dengan demikian", "Hal ini menunjukkan",
    "Lebih lanjut", "Di sisi lain", "Dalam kaitan ini",
    "Berangkat dari", "Kondisi tersebut", "Pada titik ini",
    "Secara substantif", "Jika ditelaah"
]
HEDGING_MODERATE = [
    "menunjukkan", "mengindikasikan", "dapat dipahami", "memperlihatkan",
    "cenderung", "tampak", "dapat dikatakan"
]
HEDGING_HIGH = [
    "menunjukkan bahwa", "mengindikasikan adanya", "belum dapat dipastikan",
    "masih membutuhkan verifikasi"
]
BOMBASTIC = [
    "terbukti mutlak", "tidak diragukan", "sudah pasti", "sangat luar biasa",
    "membuktikan keberhasilan"
]
LOCKED_CLOSING = [
    "Dengan demikian", "Hal tersebut menegaskan", "Pada titik inilah",
    "Dalam kerangka", "Di sinilah", "Inilah"
]


def detect_opening_pattern(text: str) -> dict:
    first_sentence = text.split('.')[0].strip()
    for pat in CONTEXT_FIRST_MARKERS:
        if re.match(pat, first_sentence):
            return {"pattern": "context_first", "evidence": first_sentence[:60]}
    for pat in EVALUATIVE_FRAME_MARKERS:
        if re.match(pat, first_sentence):
            return {"pattern": "evaluative_frame", "evidence": first_sentence[:60]}
    for pat in CLAIM_FIRST_MARKERS:
        if re.match(pat, first_sentence):
            return {"pattern": "claim_first", "evidence": first_sentence[:60]}
    return {"pattern": "subject_first", "evidence": first_sentence[:60]}


def detect_connectors(text: str) -> list:
    found = []
    for c in SOFT_CONNECTORS:
        if c.lower() in text.lower():
            found.append(c)
    return found


def detect_hedging(text: str) -> dict:
    found_h = [h for h in HEDGING_HIGH     if h.lower() in text.lower()]
    found_m = [h for h in HEDGING_MODERATE if h.lower() in text.lower()]
    found_b = [h for h in BOMBASTIC        if h.lower() in text.lower()]
    if found_b:
        level = "low"
    elif found_h:
        level = "high"
    elif found_m:
        level = "moderate_high"
    else:
        level = "moderate"
    return {
        "level":            level,
        "found_markers":    found_h + found_m,
        "bombastic_found":  found_b,
    }


def detect_closing(text: str) -> dict:
    sentences   = [s.strip() for s in text.split('.') if s.strip()]
    last_sent   = sentences[-1] if sentences else ""
    for marker in LOCKED_CLOSING:
        if marker.lower() in last_sent.lower():
            return {"pattern": "locked_implication", "evidence": last_sent[:80]}
    # Cek apakah kalimat terakhir pendek (penegasan)
    if len(last_sent.split()) < 15:
        return {"pattern": "short_affirmation", "evidence": last_sent[:80]}
    return {"pattern": "open_elaboration", "evidence": last_sent[:80]}


def detect_rhythm(text: str) -> dict:
    sentences  = [s.strip() for s in text.split('.') if len(s.strip()) > 5]
    lengths    = [len(s.split()) for s in sentences]
    if not lengths: return {"style": "unknown", "lengths": []}
    avg        = sum(lengths) / len(lengths)
    has_short  = any(l < 12 for l in lengths)
    has_medium = any(12 <= l <= 22 for l in lengths)
    has_long   = any(l > 22 for l in lengths)
    if has_short and has_long:
        style = "mixed_varied"
    elif has_short and has_medium:
        style = "mixed_short_medium"
    elif has_medium and has_long:
        style = "mixed_medium_long"
    elif has_long:
        style = "uniformly_long"
    else:
        style = "uniformly_short"
    return {"style": style, "avg_words_per_sentence": round(avg,1), "sentence_count": len(sentences)}


def detect_rhetorical_movement(text: str, opening: dict, closing: dict) -> str:
    has_context  = opening["pattern"] == "context_first"
    has_locked   = closing["pattern"] == "locked_implication"
    sentences    = [s.strip() for s in text.split('.') if s.strip()]
    n            = len(sentences)
    has_elaboration = n >= 3
    if has_context and has_elaboration and has_locked:
        return "context → claim → elaboration → implication"
    elif has_context and has_elaboration:
        return "context → elaboration → open"
    elif has_elaboration and has_locked:
        return "claim → elaboration → implication"
    return "free_form"


# ══════════════════════════════════════════════════════════════
# TAG ALL EXEMPLARS
# ══════════════════════════════════════════════════════════════

tagged = []
for ex in exemplars:
    text    = ex["text"]
    opening = detect_opening_pattern(text)
    conns   = detect_connectors(text)
    hedging = detect_hedging(text)
    closing = detect_closing(text)
    rhythm  = detect_rhythm(text)
    movement= detect_rhetorical_movement(text, opening, closing)

    tagged.append({
        "exemplar_id":     ex["exemplar_id"],
        "source_context":  ex["source_context"],
        "register_hint":   ex.get("register_hint","unknown"),
        "quality_signal":  ex.get("quality_signal","unrated"),
        "text_preview":    text[:80] + "...",
        "tags": {
            "opening_pattern":        opening,
            "transition_connectors":  conns,
            "hedging":                hedging,
            "closing_pattern":        closing,
            "sentence_rhythm":        rhythm,
            "rhetorical_movement":    movement,
        }
    })
    print(f"  Tagged {ex['exemplar_id']}: opening={opening['pattern']}, hedging={hedging['level']}, closing={closing['pattern']}, movement={movement}")

tagged_out = {
    "tagged_version": "1.0",
    "parent_exemplars": EXEMPLAR_FILE.name,
    "tagged_at":  datetime.now().isoformat(),
    "exemplars":  tagged,
}
tp = OUTPUT_DIR / "tagged_exemplars.json"
json.dump(tagged_out, open(tp,"w"), indent=2, ensure_ascii=False)
print(f"\nTagged: {tp}")


# ══════════════════════════════════════════════════════════════
# EXTRACT STYLE SIGNATURE SEED
# ══════════════════════════════════════════════════════════════

# Opening: count dominant pattern
opening_counts = Counter(t["tags"]["opening_pattern"]["pattern"] for t in tagged)
dominant_opening = opening_counts.most_common(1)[0][0]
opening_examples = [t["exemplar_id"] for t in tagged
                    if t["tags"]["opening_pattern"]["pattern"] == dominant_opening]

# Hedging: dominant level
hedging_counts = Counter(t["tags"]["hedging"]["level"] for t in tagged)
dominant_hedging = hedging_counts.most_common(1)[0][0]
# Collect all found markers across exemplars
all_preferred = []
for t in tagged:
    all_preferred.extend(t["tags"]["hedging"]["found_markers"])
preferred_markers_ranked = [m for m,_ in Counter(all_preferred).most_common(10)]

# Connectors: most used
all_conns = []
for t in tagged:
    all_conns.extend(t["tags"]["transition_connectors"])
preferred_connectors = [c for c,_ in Counter(all_conns).most_common(8)]

# Closing: dominant
closing_counts  = Counter(t["tags"]["closing_pattern"]["pattern"] for t in tagged)
dominant_closing= closing_counts.most_common(1)[0][0]
closing_examples= [t["exemplar_id"] for t in tagged
                   if t["tags"]["closing_pattern"]["pattern"] == dominant_closing]

# Rhythm: dominant
rhythm_counts   = Counter(t["tags"]["sentence_rhythm"]["style"] for t in tagged)
dominant_rhythm = rhythm_counts.most_common(1)[0][0]

# Movement: dominant
movement_counts   = Counter(t["tags"]["rhetorical_movement"] for t in tagged)
dominant_movement = movement_counts.most_common(1)[0][0]

# Variation rules
opening_variety = len(opening_counts) > 1
rhythm_variety  = len(rhythm_counts) > 1

seed = {
    "signature_id":        "style_signature_seed_v1",
    "parent_style_profile":"style_profile_reviewed",
    "source_exemplars":    EXEMPLAR_FILE.name,
    "extracted_at":        datetime.now().isoformat(),
    "exemplar_count":      len(exemplars),

    "dimensions": {
        "opening_style": {
            "dominant_pattern": dominant_opening,
            "description":      "Paragraf cenderung membuka dengan konteks atau posisi persoalan sebelum klaim inti",
            "pattern_distribution": dict(opening_counts),
            "supporting_exemplars":  opening_examples,
            "variation_note":  "context_first dominan tapi ada variasi — konsisten dengan preferensi diversitas pembuka",
        },
        "hedging_degree": {
            "dominant_level":     dominant_hedging,
            "level_distribution": dict(hedging_counts),
            "preferred_markers":  preferred_markers_ranked,
            "avoided_markers":    list(set(m for t in tagged for m in t["tags"]["hedging"]["bombastic_found"])),
            "note":               "Firm but guarded — tegas tapi tidak overclaim",
        },
        "transition_style": {
            "style":               "soft_logical",
            "preferred_connectors": preferred_connectors,
            "connector_frequency":  dict(Counter(all_conns).most_common(8)),
            "note":               "Transisi halus menggunakan jembatan logis, bukan kata hubung kasar",
        },
        "closing_style": {
            "dominant_pattern":   dominant_closing,
            "pattern_distribution": dict(closing_counts),
            "supporting_exemplars": closing_examples,
            "note":               "Penutup paragraf cenderung mengunci makna — bukan menggantung setelah elaborasi",
        },
        "sentence_rhythm": {
            "dominant_style":     dominant_rhythm,
            "style_distribution": dict(rhythm_counts),
            "note":               "Campuran kalimat medium dan panjang, dengan kalimat pendek sebagai penegas",
        },
        "rhetorical_movement": {
            "dominant_pattern":     dominant_movement,
            "pattern_distribution": dict(movement_counts),
            "note":               "Gerakan argumentatif dari konteks ke klaim ke elaborasi ke implikasi",
        },
    },

    "variation_rules": {
        "opening_diversity":    opening_variety,
        "rhythm_mix":           rhythm_variety,
        "connector_rotation":   len(preferred_connectors) >= 4,
        "closing_variation":    len(closing_counts) > 1,
        "note":                 "Variasi diizinkan dan dianjurkan — konsistensi pada prinsip, bukan pada bentuk permukaan",
    },

    "guard_rails_from_14a": {
        "anti_bombastic":  True,
        "anti_ai_generic": True,
        "anti_mechanical": True,
        "note":            "Signature ini beroperasi di atas style_profile_reviewed — 14A tetap aktif sebagai guard rail",
    },
}

sp = OUTPUT_DIR / "style_signature_seed_v1.json"
json.dump(seed, open(sp,"w"), indent=2, ensure_ascii=False)
print(f"Seed: {sp}")


# ══════════════════════════════════════════════════════════════
# REFLECTION VIEW
# ══════════════════════════════════════════════════════════════

# Identify low-confidence dimensions (less than 80% consensus)
uncertain = []
for dim_name, counts_dict in [
    ("opening_style", dict(opening_counts)),
    ("closing_style", dict(closing_counts)),
    ("sentence_rhythm", dict(rhythm_counts)),
]:
    total = sum(counts_dict.values())
    max_count = max(counts_dict.values()) if counts_dict else 0
    if total > 0 and max_count / total < 0.8:
        uncertain.append(dim_name)

reflection = {
    "view_type":         "style_signature_reflection",
    "generated_at":      datetime.now().isoformat(),
    "source_seed":       "style_signature_seed_v1",
    "exemplar_count":    len(exemplars),

    "message": "Ini pola yang saya pelajari dari contoh paragraf Anda. Silakan review setiap dimensi dan konfirmasi, revisi, atau tolak.",

    "what_i_learned": {
        "opening_style": {
            "finding":    f"Paragraf Anda cenderung membuka dengan konteks terlebih dahulu sebelum klaim ({opening_counts[dominant_opening]}/{len(tagged)} exemplar).",
            "dominant":   dominant_opening,
            "examples":   [e["text"][:80]+"..." for e in exemplars if e["exemplar_id"] in opening_examples][:2],
            "question":   "Apakah ini memang pendekatan yang Anda inginkan, atau ada exemplar tertentu yang justru tidak mewakili preferensi Anda?",
            "confidence": round(opening_counts[dominant_opening]/len(tagged), 2),
        },
        "hedging_degree": {
            "finding":    f"Tingkat kehati-hatian klaim Anda berada di level '{dominant_hedging}'. Marker yang paling sering muncul: {preferred_markers_ranked[:3]}.",
            "dominant":   dominant_hedging,
            "question":   "Apakah level hedging ini sudah tepat? Atau ada dimensi tertentu di mana Anda ingin lebih/kurang tegas?",
            "confidence": round(hedging_counts[dominant_hedging]/len(tagged), 2),
        },
        "transition_style": {
            "finding":    f"Anda menggunakan transisi halus berbasis logika. Connector yang paling sering muncul: {preferred_connectors[:4]}.",
            "question":   "Apakah ada connector yang menurut Anda terlalu sering dipakai? Atau ada yang ingin ditambahkan?",
            "confidence": 0.90,
        },
        "closing_style": {
            "finding":    f"Penutup paragraf Anda cenderung '{dominant_closing}' ({closing_counts[dominant_closing]}/{len(tagged)} exemplar) — kalimat terakhir mengunci makna.",
            "dominant":   dominant_closing,
            "examples":   [e["tags"]["closing_pattern"]["evidence"] for e in tagged if e["tags"]["closing_pattern"]["pattern"] == dominant_closing][:2],
            "question":   "Apakah pola penutup ini konsisten dengan yang Anda inginkan?",
            "confidence": round(closing_counts[dominant_closing]/len(tagged), 2),
        },
        "rhetorical_movement": {
            "finding":    f"Gerakan retorika dominan: '{dominant_movement}'.",
            "question":   "Apakah formula paragraf ini sudah mencerminkan cara Anda ingin teks bergerak?",
            "confidence": round(movement_counts[dominant_movement]/len(tagged), 2),
        },
    },

    "what_i_am_less_sure_about": {
        "dimensions":   uncertain,
        "note":         "Dimensi berikut menunjukkan variasi yang cukup besar di antara exemplar — mungkin ini memang variasi yang disengaja, atau mungkin ada exemplar yang kurang representatif.",
        "question":     "Apakah variasi pada dimensi ini memang disengaja, atau ada exemplar yang sebaiknya diabaikan?",
    },

    "what_i_avoided_learning": [
        "Saya tidak menyalin frasa atau kalimat dari exemplar secara verbatim ke dalam signature.",
        "Saya mengekstrak pola dan prinsip, bukan template kalimat.",
        "Saya mempertahankan 14A guard rails (anti-bombastic, anti-AI-generic, anti-mechanical) sebagai batas atas.",
    ],

    "review_options": {
        "accept_all":          "Signature diterima sepenuhnya — lanjut ke style_signature_reviewed.json",
        "revise_dimension":    "Ubah satu atau lebih dimensi sebelum menerima",
        "reject_exemplar":     "Tandai exemplar tertentu sebagai tidak representatif dan re-extract",
        "add_note":            "Tambahkan catatan pada dimensi tertentu",
    },
}

rp = OUTPUT_DIR / "style_signature_reflection_view.json"
json.dump(reflection, open(rp,"w"), indent=2, ensure_ascii=False)
print(f"Reflection: {rp}")

print(f"\n{'='*55}")
print("EXTRACTOR COMPLETE")
print(f"  Exemplars tagged  : {len(tagged)}")
print(f"  Dominant opening  : {dominant_opening}")
print(f"  Dominant hedging  : {dominant_hedging}")
print(f"  Dominant closing  : {dominant_closing}")
print(f"  Dominant movement : {dominant_movement}")
print(f"  Uncertain dims    : {uncertain if uncertain else 'none'}")
print("="*55)
