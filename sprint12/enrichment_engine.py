"""
enrichment_engine.py — Sprint 12C
Ontology/NLP Enrichment Engine untuk SROI pipeline.

Membaca:
  - canonical JSON
  - reviewed gap matrix
  - reviewed outline
  - ontology_v1.json
  - domain_lexicon_v1.json
  - enrichment_rules.json

Menghasilkan:
  - canonical_enriched.json (canonical + enrichment metadata, TIDAK menimpa facts)
  - outline_enrichment_suggestions.json (suggestions per bab dari outline)
  - gap_aware_suggestions.json (suggestions dari gap matrix)

Prinsip:
  - enrichment TIDAK menimpa observed facts
  - semua suggestions berlabel: suggestion_type + confidence + source
  - field canonical asli dipertahankan 100%

Usage:
  python enrichment_engine.py
  python enrichment_engine.py --canonical /p/ --gap /p/ --outline /p/ --output /p/
"""

import json, re, sys, os, argparse
from pathlib import Path
from datetime import datetime

ENRICHMENT_VERSION = "1.0.0"

parser = argparse.ArgumentParser()
parser.add_argument("--canonical", default=None)
parser.add_argument("--gap",       default=None)
parser.add_argument("--outline",   default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE",
              SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
GAP_FILE       = Path(args.gap)       if args.gap       \
    else Path(os.environ.get("GAP_FILE",
              SCRIPT_DIR.parent / "sprint11/gap_matrix_reviewed.json"))
OUTLINE_FILE   = Path(args.outline)   if args.outline   \
    else Path(os.environ.get("OUTLINE_FILE",
              SCRIPT_DIR.parent / "sprint11/chapter_outline_reviewed_bab_7.json"))
OUTPUT_DIR     = Path(args.output)    if args.output    \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

ONTOLOGY_FILE  = SCRIPT_DIR / "ontology_v1.json"
LEXICON_FILE   = SCRIPT_DIR / "domain_lexicon_v1.json"
RULES_FILE     = SCRIPT_DIR / "enrichment_rules.json"

print(f"Canonical : {CANONICAL_FILE.resolve()}")
print(f"Gap       : {GAP_FILE.resolve()}")
print(f"Outline   : {OUTLINE_FILE.resolve()}")
print(f"Ontology  : {ONTOLOGY_FILE.resolve()}")

for f in [CANONICAL_FILE, ONTOLOGY_FILE, LEXICON_FILE, RULES_FILE]:
    if not f.exists():
        print(f"FAIL: {f} tidak ditemukan"); sys.exit(1)

canonical = json.load(open(CANONICAL_FILE))
ontology  = json.load(open(ONTOLOGY_FILE))
lexicon   = json.load(open(LEXICON_FILE))
rules     = json.load(open(RULES_FILE))

gap_items = []
if GAP_FILE.exists():
    gap_raw = json.load(open(GAP_FILE))
    gap_items = gap_raw.get("gap_items", []) if isinstance(gap_raw, dict) else gap_raw

outline_data = []
if OUTLINE_FILE.exists():
    raw = json.load(open(OUTLINE_FILE))
    outline_data = raw if isinstance(raw, list) else [raw]

# Shortcuts
pi         = canonical.get("program_identity", {})
sm         = canonical.get("sroi_metrics", {}).get("calculated", {})
investment = canonical.get("investment", [])
monetization = canonical.get("monetization", [])
outcomes   = canonical.get("outcomes", [])
activities = canonical.get("activities", [])
ddat       = canonical.get("ddat_params", {})


# ══════════════════════════════════════════════════════════════
# SUGGESTION BUILDER
# ══════════════════════════════════════════════════════════════

def make_suggestion(rule_id, suggestion_type, text, confidence, source,
                    target="general", category="general"):
    return {
        "suggestion_id":   f"sugg_{rule_id.lower()}_{datetime.now().strftime('%H%M%S')}",
        "rule_id":         rule_id,
        "suggestion_type": suggestion_type,
        "text":            text,
        "confidence":      round(confidence, 2),
        "source":          source,
        "target":          target,
        "category":        category,
        "generated_at":    datetime.now().isoformat(),
        "status":          "pending",   # pending | accepted | rejected | revised
    }


# ══════════════════════════════════════════════════════════════
# RULE EVALUATORS
# ══════════════════════════════════════════════════════════════

suggestions_all = []

# ── ER_PROXY_CAUTION ─────────────────────────────────────────
proxy_items = [m for m in monetization if m.get("data_status") in ["proxy","pending"]]
if proxy_items:
    n = len(proxy_items)
    aspects = list({m["aspect_code"] for m in proxy_items})
    s = make_suggestion(
        "ER_PROXY_CAUTION", "caution_note",
        f"Ada {n} aspek monetisasi menggunakan proxy ({', '.join(aspects)}) — pastikan proxy reference terdokumentasi dan berlabel present_as_proxy di laporan.",
        0.95, "ontology_rule SR_02 + monetization", "bab_7", "caution"
    )
    suggestions_all.append(s)
    print(f"  [ER_PROXY_CAUTION] {n} proxy aspects detected")

# ── ER_BASELINE_FRAMING ───────────────────────────────────────
baseline_gap_babs = [g for g in gap_items
                     if g.get("chapter_id") in ["bab_4","bab_5"]
                     and g.get("status") in ["partial","missing","weak"]]
if baseline_gap_babs:
    bab_ids = [g["chapter_id"] for g in baseline_gap_babs]
    s = make_suggestion(
        "ER_BASELINE_FRAMING", "framing_note",
        f"Bab {'dan '.join(bab_ids)} memiliki gap data baseline. Gunakan framing 'baseline programatik' — nyatakan keterbatasan ini secara eksplisit, jangan overclaim kelengkapan data wilayah.",
        0.94, "ontology_rule SR_01 + gap_matrix", "bab_4", "framing"
    )
    suggestions_all.append(s)
    print(f"  [ER_BASELINE_FRAMING] Baseline gap di: {bab_ids}")

# ── ER_INVESTMENT_PENDING ─────────────────────────────────────
pending_inv = [i for i in investment if i.get("data_status") in ["under_confirmation","pending"]]
if pending_inv:
    years = sorted({str(i.get("year","?")) for i in pending_inv})
    s = make_suggestion(
        "ER_INVESTMENT_PENDING", "status_note",
        f"Investasi tahun {', '.join(years)} berstatus under_confirmation. Tampilkan sebagai pending di laporan — jangan gunakan sebagai final dalam klaim evaluatif.",
        0.97, "ontology_rule SR_03 + investment", "bab_7", "status"
    )
    suggestions_all.append(s)
    print(f"  [ER_INVESTMENT_PENDING] Years: {years}")

# ── ER_TERMINOLOGY_BLENDED ────────────────────────────────────
sroi_val = sm.get("sroi_blended")
if sroi_val:
    s = make_suggestion(
        "ER_TERMINOLOGY_BLENDED", "terminology_note",
        f"Gunakan istilah 'Blended SROI' secara konsisten untuk rasio evaluatif total (1 : {sroi_val:.2f}). Bedakan secara eksplisit dari 'Observed direct return' jika keduanya disebut.",
        0.98, "domain_lexicon + ontology_rule SR_08", "bab_7", "terminology"
    )
    suggestions_all.append(s)
    print(f"  [ER_TERMINOLOGY_BLENDED] SROI: {sroi_val:.4f}")

# ── ER_REINTEGRATION_PROXY ────────────────────────────────────
reint_outcomes = [o for o in outcomes
                  if "reintegrasi" in o.get("name","").lower()
                  or o.get("indicator","") and "reintegrasi" in o.get("indicator","").lower()]
reint_mon = [m for m in monetization if m.get("aspect_code") == "REINT"]
if reint_outcomes or reint_mon:
    s = make_suggestion(
        "ER_REINTEGRATION_PROXY", "proxy_recommendation",
        "Outcome reintegrasi sosial-ekonomi membutuhkan proxy yang defensible. Proxy yang direkomendasikan: nilai pelatihan Kartu Prakerja (Rp 3.500.000/peserta) atau replacement cost program pemerintah sejenis. Dokumentasikan sumber proxy.",
        0.88, "ontology entity + domain_lexicon", "bab_7", "proxy_recommendation"
    )
    suggestions_all.append(s)
    print("  [ER_REINTEGRATION_PROXY] Reintegrasi outcome/monetization detected")

# ── ER_LFA_TRACE ──────────────────────────────────────────────
if activities:
    n_act = len(activities)
    # Cek apakah ada signal LFA di canonical
    has_lfa = any("lfa" in str(canonical).lower() for _ in [1])
    if not has_lfa:
        s = make_suggestion(
            "ER_LFA_TRACE", "methodology_note",
            f"Program memiliki {n_act} aktivitas tercatat. Pastikan ada LFA atau Theory of Change yang memetakan jalur aktivitas → output → outcome — ini memperkuat defensibility klaim SROI.",
            0.82, "ontology_rule SR_06", "bab_3", "methodology"
        )
        suggestions_all.append(s)
        print(f"  [ER_LFA_TRACE] {n_act} activities, no LFA signal detected")

# ── ER_GAP_EXPLICIT ───────────────────────────────────────────
must_gap_items = [g for g in gap_items if g.get("_review_decision") == "must_render_as_gap"]
if must_gap_items:
    chapters = [g["chapter_id"] for g in must_gap_items]
    s = make_suggestion(
        "ER_GAP_EXPLICIT", "gap_rendering_note",
        f"Gap di {', '.join(chapters)} ditandai 'must_render_as_gap' dalam review. Gunakan callout_gap eksplisit dengan gap_type yang sesuai — jangan biarkan bab ini terlihat seolah lengkap.",
        0.99, "gap_matrix review decision", "bab_4", "gap_acknowledgement"
    )
    suggestions_all.append(s)
    print(f"  [ER_GAP_EXPLICIT] must_render_as_gap: {chapters}")

# ── ER_CONF_PROXY ─────────────────────────────────────────────
conf_mon = [m for m in monetization if m.get("aspect_code") == "CONF"]
if conf_mon:
    s = make_suggestion(
        "ER_CONF_PROXY", "proxy_validation",
        "Outcome kepercayaan diri (CONF) menggunakan proxy replacement cost layanan psikologi. Proxy yang direkomendasikan: tarif psikologi publik (6 sesi × Rp 50.000 = Rp 300.000/peserta). Pastikan sumber proxy terdokumentasi.",
        0.87, "domain_lexicon + ontology entity", "bab_7", "proxy_recommendation"
    )
    suggestions_all.append(s)
    print("  [ER_CONF_PROXY] CONF monetization detected")

# ── ER_SROI_BELOW_PAR ─────────────────────────────────────────
if sroi_val and sroi_val < 1.0:
    s = make_suggestion(
        "ER_SROI_BELOW_PAR", "interpretation_note",
        f"Blended SROI = {sroi_val:.2f} < 1.0 — nilai sosial lebih kecil dari investasi. Ini bukan kegagalan otomatis: horizon evaluasi mungkin belum penuh atau ada outcome jangka panjang yang belum dapat dimonetisasi. Jelaskan konteks ini di laporan.",
        0.85, "ontology_rule SR_05", "bab_9", "interpretation"
    )
    suggestions_all.append(s)
    print(f"  [ER_SROI_BELOW_PAR] SROI below 1.0: {sroi_val:.4f}")

# ── TERMINOLOGY SCAN dari Lexicon ─────────────────────────────
# Cek apakah ada istilah penting yang mungkin dipakai tidak konsisten
canonical_text = json.dumps(canonical).lower()
lexicon_terms  = lexicon.get("terms", [])
term_issues = []
for term in lexicon_terms:
    aliases = term.get("aliases", [])
    canonical_term = term["term"].lower()
    # Cari alias yang dipakai tapi berbeda dari term canonical
    for alias in aliases:
        if alias.lower() in canonical_text and canonical_term not in canonical_text:
            term_issues.append(f"'{alias}' → sebaiknya '{term['term']}'")

if term_issues:
    s = make_suggestion(
        "ER_TERMINOLOGY_CONSISTENCY", "terminology_note",
        f"Ditemukan {len(term_issues)} potensi inkonsistensi istilah: " + " | ".join(term_issues[:3]),
        0.75, "domain_lexicon scan", "general", "terminology"
    )
    suggestions_all.append(s)
    print(f"  [ER_TERMINOLOGY_CONSISTENCY] {len(term_issues)} potential issues")

print(f"\nTotal suggestions generated: {len(suggestions_all)}")


# ══════════════════════════════════════════════════════════════
# OUTLINE ENRICHMENT SUGGESTIONS
# ══════════════════════════════════════════════════════════════

outline_suggestions = []
for chapter in outline_data:
    cid    = chapter.get("chapter_id","?")
    points = chapter.get("argument_points",[])
    claim  = chapter.get("core_claim","")

    # Cek terminologi di core_claim
    claim_lower = claim.lower()
    if "1 :" in claim_lower or "sroi" in claim_lower:
        if "blended sroi" not in claim_lower and "blended" not in claim_lower:
            outline_suggestions.append(make_suggestion(
                "ER_OUTLINE_CLAIM_TERMINOLOGY",
                "terminology_note",
                f"Core claim bab {cid} menyebut rasio SROI tapi tidak menggunakan istilah 'Blended SROI' secara eksplisit. Pertimbangkan: 'Program menghasilkan Blended SROI ...'",
                0.80, "domain_lexicon", cid, "terminology"
            ))

    # Cek proxy points
    proxy_points = [p for p in points if p.get("is_proxy")]
    if proxy_points:
        outline_suggestions.append(make_suggestion(
            "ER_OUTLINE_PROXY_POINTS",
            "caution_note",
            f"Bab {cid} memiliki {len(proxy_points)} argument point dengan data proxy. Pastikan setiap point proxy diberi tanda [PROXY] dan dilengkapi sumber proxy di narasi.",
            0.88, "ontology_rule SR_02", cid, "caution"
        ))

    # Cek known gaps
    known_gaps = chapter.get("known_gaps", [])
    new_gaps   = [g for g in known_gaps if g.get("_from_review")]
    if new_gaps:
        outline_suggestions.append(make_suggestion(
            "ER_OUTLINE_NEW_GAPS",
            "gap_note",
            f"Bab {cid} memiliki {len(new_gaps)} gap baru dari hasil review. Pastikan gap ini muncul sebagai callout_gap di narasi.",
            0.92, "review decisions", cid, "gap_acknowledgement"
        ))

print(f"Outline suggestions: {len(outline_suggestions)}")


# ══════════════════════════════════════════════════════════════
# GAP-AWARE SUGGESTIONS (per bab)
# ══════════════════════════════════════════════════════════════

gap_suggestions = []
for g in gap_items:
    cid      = g.get("chapter_id","?")
    decision = g.get("_review_decision","unreviewed")
    status   = g.get("status","?")
    note     = g.get("note","")

    if decision == "must_render_as_gap":
        gap_suggestions.append(make_suggestion(
            f"ER_GAP_{cid.upper()}_RENDER",
            "gap_rendering_note",
            f"Bab {cid} harus menampilkan gap secara eksplisit (keputusan review: must_render_as_gap). {note[:80] if note else ''}. Gunakan callout_gap dengan gap_type: data_unavailable.",
            0.99, "review decision + gap_matrix", cid, "gap_acknowledgement"
        ))
    elif decision == "ignorable":
        gap_suggestions.append(make_suggestion(
            f"ER_GAP_{cid.upper()}_IGNORE",
            "gap_note",
            f"Bab {cid} gap ditandai ignorable oleh reviewer. Boleh tidak ditampilkan sebagai gap eksplisit, tetapi tetap jangan overclaim kelengkapan konten.",
            0.90, "review decision", cid, "status"
        ))

print(f"Gap-aware suggestions: {len(gap_suggestions)}")


# ══════════════════════════════════════════════════════════════
# COMPOSE OUTPUTS
# ══════════════════════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. canonical_enriched.json — TIDAK menimpa canonical, hanya menambah layer
import copy
canonical_enriched = copy.deepcopy(canonical)
canonical_enriched["_enrichment_metadata"] = {
    "enrichment_version":  ENRICHMENT_VERSION,
    "enriched_at":         datetime.now().isoformat(),
    "enrichment_source":   ["ontology_v1","domain_lexicon_v1","enrichment_rules"],
    "total_suggestions":   len(suggestions_all),
    "note":                "Field asli canonical tidak diubah. Enrichment tersimpan di _enrichment_suggestions.",
    "facts_preserved":     True,
}
canonical_enriched["_enrichment_suggestions"] = suggestions_all

can_path = OUTPUT_DIR / "canonical_enriched.json"
json.dump(canonical_enriched, open(can_path,"w"), indent=2, ensure_ascii=False)
print(f"\nOutput: {can_path}")

# 2. outline_enrichment_suggestions.json
out_sugg = {
    "generated_at":  datetime.now().isoformat(),
    "source_outline": str(OUTLINE_FILE.name),
    "suggestions":   outline_suggestions,
}
os_path = OUTPUT_DIR / "outline_enrichment_suggestions.json"
json.dump(out_sugg, open(os_path,"w"), indent=2, ensure_ascii=False)
print(f"Output: {os_path}")

# 3. gap_aware_suggestions.json
gap_sugg = {
    "generated_at": datetime.now().isoformat(),
    "source_gap":   str(GAP_FILE.name),
    "suggestions":  gap_suggestions,
}
gs_path = OUTPUT_DIR / "gap_aware_suggestions.json"
json.dump(gap_sugg, open(gs_path,"w"), indent=2, ensure_ascii=False)
print(f"Output: {gs_path}")

print(f"\n{'='*55}")
print("ENRICHMENT ENGINE COMPLETE")
print(f"  Suggestions (canonical) : {len(suggestions_all)}")
print(f"  Suggestions (outline)   : {len(outline_suggestions)}")
print(f"  Suggestions (gap-aware) : {len(gap_suggestions)}")
print(f"  Facts preserved         : True")
print("="*55)
