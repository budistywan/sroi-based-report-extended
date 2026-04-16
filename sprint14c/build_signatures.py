"""
build_signatures.py — Sprint 14C helper
Generates five register signature files from register_tagged_exemplars.json
"""
import json
from pathlib import Path
from datetime import datetime

DIR = Path(__file__).parent
reg_data = json.load(open(DIR / "register_tagged_exemplars.json"))

# Load 14B global signature as parent
sig14b_path = DIR.parent / "sprint14b/style_signature_reviewed.json"
parent_sig  = json.load(open(sig14b_path)) if sig14b_path.exists() else {}

def sig(register_id, bab_list, function_desc, opening, hedging_level,
        hedging_preferred, hedging_avoid, transition_style, preferred_connectors,
        closing_pattern, closing_note, rhythm, firmness,
        variation_rules, special_emphasis, guard_rails):
    return {
        "signature_id":          f"style_signature_{register_id}",
        "register":              f"{register_id}_register",
        "bab_coverage":          bab_list,
        "function":              function_desc,
        "parent_global_signature": "style_signature_reviewed",
        "parent_style_profile":    "style_profile_reviewed",
        "created_at":            datetime.now().isoformat(),
        "dimensions": {
            "opening_style": {
                "pattern":     opening["pattern"],
                "description": opening["description"],
                "examples":    opening["examples"],
                "variation_note": opening.get("variation_note",""),
            },
            "hedging_degree": {
                "level":             hedging_level,
                "preferred_markers": hedging_preferred,
                "avoided_markers":   hedging_avoid,
                "firmness":          firmness,
            },
            "transition_style": {
                "style":               transition_style,
                "preferred_connectors": preferred_connectors,
            },
            "closing_style": {
                "pattern":     closing_pattern,
                "description": closing_note,
            },
            "sentence_rhythm": {
                "style": rhythm,
            },
        },
        "variation_rules":  variation_rules,
        "special_emphasis": special_emphasis,
        "guard_rails":      guard_rails,
    }

# ── 1. FRAMING ────────────────────────────────────────────────
framing = sig(
    "framing", ["bab_1","bab_2","bab_3"],
    "Metodologis, orientasi, penjelasan kerangka kajian",
    opening={
        "pattern":      "context_to_framework",
        "description":  "Paragraf membuka dengan posisi/konteks lalu bergerak ke kerangka metodologis atau tujuan",
        "examples":     ["Kajian ini menggunakan pendekatan...", "Program TJSL berdiri pada persimpangan..."],
        "variation_note": "Boleh dimulai dengan konteks regulatoris, konteks program, atau posisi kajian",
    },
    hedging_level="moderate",
    hedging_preferred=["menggunakan", "dipilih karena", "memberikan kerangka", "berdiri pada"],
    hedging_avoid=["terbukti", "pasti", "tidak diragukan"],
    transition_style="soft_methodological",
    preferred_connectors=["Dalam konteks ini", "Dengan demikian", "Di sinilah", "Dalam kerangka ini"],
    closing_pattern="orientative",
    closing_note="Penutup bersifat orientatif — membuka ke arah berikutnya, bukan menutup secara final",
    rhythm="mixed_medium_long",
    firmness="moderate",
    variation_rules={"opening_diversity": True, "connector_rotation": True, "closing_variation": True},
    special_emphasis=["framework_positioning", "methodological_clarity", "stakeholder_orientation"],
    guard_rails={"anti_bombastic": True, "anti_ai_generic": True, "anti_mechanical": True},
)

# ── 2. ANALYTIC ───────────────────────────────────────────────
analytic = sig(
    "analytic", ["bab_4","bab_5","bab_6"],
    "Diagnosis, baseline, problematisasi, pemetaan kondisi",
    opening={
        "pattern":      "investigative_frame",
        "description":  "Paragraf membuka dengan posisi investigatif — menelaah, mengidentifikasi, atau mendialog dengan kondisi yang ada",
        "examples":     ["Bab ini menyusun kondisi awal...", "Jika ditelaah lebih jauh, hambatan terbesar..."],
        "variation_note": "Boleh dimulai dengan 'Jika ditelaah', 'Dalam pengamatan', 'Kondisi yang ada menunjukkan'",
    },
    hedging_level="moderate_high",
    hedging_preferred=["menunjukkan", "mengindikasikan", "dapat dipahami", "lebih tepat dipahami sebagai",
                       "bukan kelemahan melainkan", "tidak otomatis menjadi"],
    hedging_avoid=["terbukti bahwa", "sudah pasti", "jelas bahwa"],
    transition_style="diagnostic_logical",
    preferred_connectors=["Kondisi inilah yang", "Di sinilah", "Jika ditelaah lebih jauh",
                          "Bukan hanya", "melainkan juga", "Hal ini menunjukkan bahwa"],
    closing_pattern="problem_anchored",
    closing_note="Penutup mengikat ke akar masalah atau kondisi yang akan ditangani — bukan menutup dengan klaim besar",
    rhythm="mixed_medium_long",
    firmness="moderate_high",
    variation_rules={"opening_diversity": True, "connector_rotation": True, "avoid_early_conclusion": True},
    special_emphasis=["baseline_honesty", "problem_framing_depth", "anti_overclaim", "investigative_tone"],
    guard_rails={"anti_bombastic": True, "anti_ai_generic": True, "anti_mechanical": True,
                 "no_fake_completeness": True},
)

# ── 3. EVALUATIVE ─────────────────────────────────────────────
evaluative = sig(
    "evaluative", ["bab_7"],
    "Terukur, data-grounded, firm but guarded, membedakan observed/proxy/final",
    opening={
        "pattern":      "evaluative_frame",
        "description":  "Paragraf membuka dengan posisi evaluatif yang tegas — kajian sebagai instrumen, data sebagai dasar",
        "examples":     ["Kajian SROI ini menjadi instrumen evaluasi...", "Dua dari empat aspek monetisasi..."],
        "variation_note": "Boleh dimulai dengan jumlah/proporsi data, posisi kajian, atau aspek yang dievaluasi",
    },
    hedging_level="moderate_high",
    hedging_preferred=["menunjukkan bahwa", "mengindikasikan", "dapat diestimasikan", "bersifat konservatif",
                       "hal ini bukan anomali", "lazim dalam kajian"],
    hedging_avoid=["terbukti mutlak", "tidak diragukan", "sangat jelas"],
    transition_style="evaluative_logical",
    preferred_connectors=["Dalam konteks ini", "Hal ini bukan anomali melainkan", "Dengan demikian",
                          "Di sisi lain", "Nilai ini mencerminkan"],
    closing_pattern="evaluative_locked",
    closing_note="Penutup mengunci posisi evaluatif — jelas tentang apa yang terukur, apa yang diestimasi",
    rhythm="mixed_medium_long",
    firmness="high",
    variation_rules={"terminology_consistency": True, "proxy_label_discipline": True, "connector_rotation": True},
    special_emphasis=["data_grounded_claims", "proxy_transparency", "observed_vs_blended_distinction",
                      "caution_note_compatible", "clarity_over_flourish"],
    guard_rails={"anti_bombastic": True, "anti_ai_generic": True, "anti_mechanical": True,
                 "no_mixing_observed_proxy": True},
)

# ── 4. REFLECTIVE ─────────────────────────────────────────────
reflective = sig(
    "reflective", ["bab_8"],
    "Pembelajaran, refleksi, integrasi makna, menjembatani hasil ke implikasi",
    opening={
        "pattern":      "conceptual_contrast_or_question",
        "description":  "Paragraf membuka dengan kontras konseptual atau pertanyaan yang mengundang refleksi",
        "examples":     ["Perbedaan antara observed direct return dan blended SROI bukan sekadar...",
                         "Node Lapas Palembang yang belum menghasilkan transaksi bukan semata-mata..."],
        "variation_note": "Boleh dimulai dengan 'Perbedaan antara', 'Bukan sekadar', 'Di balik angka ini'",
    },
    hedging_level="moderate",
    hedging_preferred=["mencerminkan", "menjadi sinyal bahwa", "mengundang pertanyaan",
                       "justru menjadi", "bukan pada ... tetapi pada"],
    hedging_avoid=["terbukti", "sudah pasti berhasil", "membuktikan secara mutlak"],
    transition_style="dialogic_gentle",
    preferred_connectors=["Di sinilah pembelajaran terpenting", "Dalam kerangka ini",
                          "Bukan ... tetapi", "Kondisi ini justru", "Yang perlu dicatat adalah"],
    closing_pattern="learning_forward",
    closing_note="Penutup membuka ruang refleksi atau pertanyaan lanjutan — bukan menutup dengan kepastian angka",
    rhythm="mixed_short_medium",
    firmness="moderate",
    variation_rules={"opening_diversity": True, "sentence_length_mix": True, "allow_shorter_closing": True},
    special_emphasis=["learning_orientation", "meaning_integration", "gentle_transition",
                      "reflective_not_vague", "no_number_destabilization"],
    guard_rails={"anti_bombastic": True, "anti_ai_generic": True, "no_contradicting_evaluative_numbers": True},
)

# ── 5. CONCLUSIVE ─────────────────────────────────────────────
conclusive = sig(
    "conclusive", ["bab_9"],
    "Pengunci, implikatif, forward-looking, ringkas namun kuat",
    opening={
        "pattern":      "evaluative_summary_frame",
        "description":  "Paragraf membuka dengan ringkasan evaluatif yang langsung dan tegas — posisi jelas sejak kalimat pertama",
        "examples":     ["Evaluasi SROI menunjukkan bahwa Program...", "Ke depan, penguatan program perlu diarahkan..."],
        "variation_note": "Boleh dimulai dengan pernyataan temuan, pernyataan rekomendasi, atau pernyataan implikasi",
    },
    hedging_level="moderate",
    hedging_preferred=["menunjukkan bahwa", "membuktikan bahwa model", "perlu diarahkan pada",
                       "dengan demikian nilai sosial"],
    hedging_avoid=["sangat luar biasa", "tidak dapat disangkal", "sempurna", "mutlak berhasil"],
    transition_style="concise_forward",
    preferred_connectors=["Dengan demikian", "Ke depan", "Hal ini menunjukkan bahwa",
                          "Dalam jangka berikutnya", "Tiga prioritas yang saling melengkapi"],
    closing_pattern="forward_locked",
    closing_note="Penutup mengunci ke arah ke depan — bukan retrospektif, melainkan implikatif dan actionable",
    rhythm="mixed_short_medium",
    firmness="high",
    variation_rules={"structured_enumeration_allowed": True, "connector_rotation": True, "concise_sentences_preferred": True},
    special_emphasis=["strong_closing", "implication_forward", "concise_firmness", "three_point_structure_ok",
                      "no_hyperbole"],
    guard_rails={"anti_bombastic": True, "anti_ai_generic": True, "anti_mechanical": True},
)

# Write all five
for name, data in [
    ("framing", framing), ("analytic", analytic), ("evaluative", evaluative),
    ("reflective", reflective), ("conclusive", conclusive)
]:
    path = DIR / f"style_signature_{name}.json"
    json.dump(data, open(path,"w"), indent=2, ensure_ascii=False)
    print(f"  ✓ {path.name}")

print("All five register signatures generated.")
