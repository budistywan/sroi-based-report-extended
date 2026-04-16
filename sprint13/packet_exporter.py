"""
packet_exporter.py — Sprint 13B
Mengubah enrichment suggestions + enriched outlines menjadi semantic packets
yang bisa direview manusia di room chat.

Input:
  - canonical_enriched_reviewed.json (Sprint 12)
  - enriched_outline_bab4.json (Sprint 12)
  - enriched_outline_bab7.json (Sprint 12)
  - gap_aware_suggestions.json (Sprint 12)
  - outline_enrichment_suggestions.json (Sprint 12)

Output:
  - semantic_packets_bab4.json
  - semantic_packets_bab7.json
  - semantic_packets_closing.json

Rules:
  - Packet harus bisa dipahami tanpa membuka file lain
  - TIDAK mengekspor: financial tables, canonical core facts, validator outputs
  - Setiap packet punya scope yang jelas

Usage:
  python packet_exporter.py
  python packet_exporter.py --sprint12-dir /p/ --output /p/
"""

import json, sys, os, argparse, uuid
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--sprint12-dir", default=None, dest="dir12")
parser.add_argument("--output",       default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR12      = Path(args.dir12) if args.dir12 \
    else Path(os.environ.get("SPRINT12_DIR", SCRIPT_DIR.parent / "sprint12"))
OUTPUT_DIR = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

CONTEXT_REGISTRY = SCRIPT_DIR / "review_context_registry.json"
APPLICABILITY    = "ESL_Pertamina_2025"   # default context

print(f"Sprint12 dir: {DIR12.resolve()}")
print(f"Output dir  : {OUTPUT_DIR.resolve()}")

# Load inputs
def load_if_exists(path, default=None):
    if Path(path).exists():
        return json.load(open(path))
    print(f"  WARN: {path} tidak ditemukan")
    return default

enriched_can = load_if_exists(DIR12 / "canonical_enriched_reviewed.json") or \
               load_if_exists(DIR12 / "canonical_enriched.json", {})
enriched_b7  = load_if_exists(DIR12 / "enriched_outline_bab7.json", [{}])
enriched_b4  = load_if_exists(DIR12 / "enriched_outline_bab4.json", [{}])
gap_sugg     = load_if_exists(DIR12 / "gap_aware_suggestions.json", {})
out_sugg     = load_if_exists(DIR12 / "outline_enrichment_suggestions.json", {})

# Sprint 0 canonical untuk mendapatkan closing/recommendation teks
canonical_esl = load_if_exists(
    SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json", {}
)
sm   = canonical_esl.get("sroi_metrics", {}).get("calculated", {})
ls   = canonical_esl.get("learning_signals", {})
pi   = canonical_esl.get("program_identity", {})

PACKET_ID_PREFIX = f"pkt_{datetime.now().strftime('%Y%m%d%H%M')}"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── HELPERS ───────────────────────────────────────────────────
def make_packet(packet_type: str, target_id: str, decision_prompt: str,
                current_text: str, source: str, confidence: float,
                allowed: list, forbidden: list,
                relevant_history: str = "",
                program_code: str = "ESL") -> dict:
    return {
        "packet_id":         f"{PACKET_ID_PREFIX}_{uuid.uuid4().hex[:6]}",
        "packet_type":       packet_type,
        "target_id":         target_id,
        "scope": {
            "allowed_changes":  allowed,
            "forbidden_changes": forbidden,
        },
        "decision_prompt":   decision_prompt,
        "context": {
            "current_text":         current_text,
            "source":               source,
            "confidence":           round(confidence, 2),
            "relevant_history":     relevant_history,
            "applicability_context": APPLICABILITY,
            "program_code":         program_code,
        },
        "decision_options":  ["accept", "reject", "revise_with_text"],
        "decision":          None,
        "revised_text":      None,
        "reviewer_note":     None,
        "reviewed_at":       None,
    }


# ══════════════════════════════════════════════════════════════
# BAB IV PACKETS
# ══════════════════════════════════════════════════════════════
print("\nGenerating Bab IV packets...")
packets_bab4 = []

# Bab IV hints dari enriched outline
ch4 = (enriched_b4[0] if isinstance(enriched_b4, list) else enriched_b4) or {}
hints4 = ch4.get("_enrichment_hints", {}).get("hints", [])

for hint in hints4:
    if hint.get("category") in ["framing", "gap_acknowledgement"]:
        packets_bab4.append(make_packet(
            packet_type   = "framing_note",
            target_id     = "bab_4",
            decision_prompt = (
                "Apakah framing tentang keterbatasan baseline ini sudah tepat untuk "
                "konteks laporan? Apakah perlu dipertegas, diperlunak, atau diubah agar "
                "lebih sesuai dengan gaya penulisan yang diharapkan?"
            ),
            current_text  = hint["text"],
            source        = hint.get("source", "enrichment_engine"),
            confidence    = hint.get("confidence", 0.9),
            allowed       = ["text_only", "wording"],
            forbidden     = ["numeric_values", "data_status", "gap_type", "financial_fields", "argument_points"],
            relevant_history = "Sprint 9.3: reviewer memutuskan bahwa keterbatasan baseline harus dinyatakan eksplisit dengan framing 'baseline programatik'",
        ))

# Gap-aware suggestion untuk bab 4
gap_suggestions = gap_sugg.get("suggestions", [])
for s in gap_suggestions:
    if s.get("target") == "bab_4":
        packets_bab4.append(make_packet(
            packet_type   = "gap_acknowledgement",
            target_id     = "bab_4.gap_note",
            decision_prompt = (
                "Apakah catatan gap ini perlu muncul eksplisit di laporan? "
                "Apakah formulasi yang ada sudah cukup jujur dan tidak terkesan defensif? "
                "Revisi jika perlu disesuaikan dengan tone laporan."
            ),
            current_text  = s["text"],
            source        = s.get("source", "gap_matrix_review"),
            confidence    = s.get("confidence", 0.95),
            allowed       = ["text_only", "wording", "tone"],
            forbidden     = ["gap_type", "numeric_values", "data_status", "chapter_structure"],
            relevant_history = "Gap bab_4 ditandai must_render_as_gap dalam Sprint 11 review",
        ))

# Fallback jika tidak ada hint dari enrichment
if not packets_bab4:
    packets_bab4.append(make_packet(
        packet_type   = "framing_note",
        target_id     = "bab_4",
        decision_prompt = (
            "Bab IV menggunakan framing 'baseline programatik' karena data wilayah rinci "
            "tidak tersedia. Apakah paragraf pembuka Bab IV sudah cukup jelas menyatakan "
            "keterbatasan ini tanpa terkesan melemahkan keseluruhan laporan?"
        ),
        current_text  = (
            "Pemetaan kondisi awal dalam laporan ini disusun terutama dari data program, "
            "identifikasi kelompok sasaran, dan problem framing yang diturunkan dari desain "
            "intervensi. Karena data baseline wilayah yang sepenuhnya komprehensif tidak "
            "tersedia, pembacaan kondisi awal pada bab ini perlu dipahami sebagai baseline "
            "programatik, bukan potret statistik wilayah yang lengkap."
        ),
        source        = "narrative_builder_rest.py — callout_warning bab_4",
        confidence    = 0.94,
        allowed       = ["text_only", "wording", "tone"],
        forbidden     = ["numeric_values", "data_status", "gap_type", "financial_fields"],
        relevant_history = "Sprint 9.3: framing baseline programatik ditetapkan sebagai posisi resmi",
    ))

json.dump(packets_bab4, open(OUTPUT_DIR / "semantic_packets_bab4.json","w"),
          indent=2, ensure_ascii=False)
print(f"  Bab IV packets: {len(packets_bab4)}")


# ══════════════════════════════════════════════════════════════
# BAB VII PACKETS
# ══════════════════════════════════════════════════════════════
print("Generating Bab VII packets...")
packets_bab7 = []

# Hints dari enriched outline bab7
ch7 = (enriched_b7[0] if isinstance(enriched_b7, list) else enriched_b7) or {}
hints7 = ch7.get("_enrichment_hints", {}).get("hints", [])

for hint in hints7:
    cat = hint.get("category","")

    if cat == "terminology":
        packets_bab7.append(make_packet(
            packet_type   = "terminology_note",
            target_id     = "bab_7.terminology",
            decision_prompt = (
                "Apakah istilah 'Blended SROI' dan 'Observed direct return' sudah dipakai "
                "secara konsisten di Bab VII? Apakah definisi pembedanya sudah cukup jelas "
                "untuk pembaca laporan yang tidak familiar dengan metodologi SROI?"
            ),
            current_text  = hint["text"],
            source        = hint.get("source", "domain_lexicon + enrichment_engine"),
            confidence    = hint.get("confidence", 0.98),
            allowed       = ["text_only", "wording", "phrasing"],
            forbidden     = ["numeric_values", "sroi_values", "financial_fields", "data_status", "argument_points"],
            relevant_history = "Sprint 9.3: kontradiksi 'SROI final belum dihitung' vs 'Blended SROI 1:1.03' diselesaikan — terminologi dibersihkan",
        ))

    elif cat == "caution":
        packets_bab7.append(make_packet(
            packet_type   = "caution_note",
            target_id     = "bab_7.proxy_caution",
            decision_prompt = (
                "Catatan ini memperingatkan bahwa aspek REINT dan CONF menggunakan proxy. "
                "Apakah formulasi peringatannya sudah tepat? Tidak terlalu melemahkan klaim "
                "tapi tetap jujur tentang sifat estimatif angka-angka tersebut?"
            ),
            current_text  = hint["text"],
            source        = hint.get("source", "enrichment_engine"),
            confidence    = hint.get("confidence", 0.95),
            allowed       = ["text_only", "wording", "tone"],
            forbidden     = ["numeric_values", "proxy_references", "financial_fields", "ddat_values"],
            relevant_history = "Proxy REINT dan CONF adalah estimasi konservatif Skenario S10 — belum diverifikasi survei peserta",
        ))

    elif cat == "proxy_recommendation":
        packets_bab7.append(make_packet(
            packet_type   = "proxy_recommendation",
            target_id     = "bab_7.proxy_documentation",
            decision_prompt = (
                "Rekomendasi proxy ini menyarankan dokumentasi sumber proxy untuk REINT/CONF. "
                "Apakah rekomendasi ini perlu ditambahkan ke narasi Bab VII sebagai catatan "
                "metodologis, atau cukup sebagai catatan kaki?"
            ),
            current_text  = hint["text"],
            source        = hint.get("source", "enrichment_engine + domain_lexicon"),
            confidence    = hint.get("confidence", 0.88),
            allowed       = ["text_only", "placement_decision"],
            forbidden     = ["numeric_values", "proxy_values", "financial_fields"],
        ))

# Outline enrichment suggestions untuk bab7
out_suggestions = out_sugg.get("suggestions", [])
for s in out_suggestions:
    if s.get("target") in ["bab_7", "bab_7.terminology"]:
        packets_bab7.append(make_packet(
            packet_type   = "caution_note",
            target_id     = "bab_7.proxy_points",
            decision_prompt = (
                "Beberapa argument point di Bab VII menggunakan data proxy. "
                "Apakah setiap point proxy sudah cukup diberi tanda dan konteks yang jelas "
                "di narasi? Apakah ada yang perlu penguatan?"
            ),
            current_text  = s["text"],
            source        = s.get("source", "outline_enrichment"),
            confidence    = s.get("confidence", 0.88),
            allowed       = ["text_only", "wording"],
            forbidden     = ["argument_points_structure", "numeric_values", "financial_fields"],
        ))

json.dump(packets_bab7, open(OUTPUT_DIR / "semantic_packets_bab7.json","w"),
          indent=2, ensure_ascii=False)
print(f"  Bab VII packets: {len(packets_bab7)}")


# ══════════════════════════════════════════════════════════════
# CLOSING PACKETS
# ══════════════════════════════════════════════════════════════
print("Generating closing packets...")
packets_closing = []

sroi_val   = sm.get("sroi_blended", 1.14)
inv_total  = sm.get("total_investment_idr", 502460181)
loop3      = ls.get("loop_3", [])

# Candidate closing paragraph
closing_candidate = (
    f"Program {pi.get('program_name','Enduro Sahabat Lapas')} terbukti menghasilkan "
    f"nilai sosial-ekonomi yang melampaui investasi, dengan Blended SROI "
    f"1 : {sroi_val:.2f} selama periode {pi.get('period_start',2023)}–{pi.get('period_end',2025)}. "
    f"Tiga temuan utama: aspek REINT mendominasi nilai — menunjukkan bahwa nilai reintegrasi "
    f"adalah dampak paling signifikan; Node Lapas Palembang belum menghasilkan transaksi "
    f"aktif; dan Milenial Motor membuktikan bahwa model reintegrasi produktif bukan sekadar "
    f"aspirasi melainkan template yang dapat direplikasi."
)

packets_closing.append(make_packet(
    packet_type   = "closing_paragraph",
    target_id     = "bab_9.kesimpulan",
    decision_prompt = (
        "Ini adalah kandidat paragraf penutup Bab IX. Apakah tone-nya sudah tepat — "
        "cukup kuat untuk menyatakan keberhasilan, tapi tidak overclaim? "
        "Apakah tiga temuan yang disebut sudah merepresentasikan inti laporan dengan benar? "
        "Revisi jika perlu disesuaikan dengan gaya dan postur metodologis yang disepakati."
    ),
    current_text  = closing_candidate,
    source        = "narrative_builder_rest.py — bab_9 kesimpulan",
    confidence    = 0.80,
    allowed       = ["text_only", "tone", "wording", "phrasing"],
    forbidden     = ["numeric_values", "sroi_values", "financial_fields", "data_status"],
    relevant_history = (
        "Sprint 9.3: kontradiksi narasi sudah diselesaikan. "
        "Posisi final: Blended SROI adalah angka evaluatif final yang dipakai. "
        "Observed direct return sebagai metrik pembanding."
    ),
))

# Executive framing
if loop3:
    exec_candidate = (
        "Kajian SROI ini menunjukkan bahwa investasi dalam pemberdayaan vokasional "
        "berbasis reintegrasi — meskipun mengandung komponen proxy yang perlu penguatan "
        "verifikasi — menghasilkan nilai sosial yang terukur dan defensible. "
        "Model Milenial Motor adalah bukti hidup bahwa jalur Lapas → pelatihan → "
        "usaha mandiri bukan sekadar teori."
    )
    packets_closing.append(make_packet(
        packet_type   = "executive_framing",
        target_id     = "ringkasan_eksekutif.framing",
        decision_prompt = (
            "Ini adalah kandidat kalimat framing untuk Ringkasan Eksekutif. "
            "Apakah nada dan posisinya tepat untuk pembaca eksekutif (klien, KLHK)? "
            "Apakah perlu lebih formal, lebih ringkas, atau ada istilah yang perlu disesuaikan?"
        ),
        current_text  = exec_candidate,
        source        = "learning_signals.loop_3 + narrative synthesis",
        confidence    = 0.78,
        allowed       = ["text_only", "tone", "register", "wording"],
        forbidden     = ["numeric_values", "financial_fields", "data_status", "methodology_claims"],
        relevant_history = "Milenial Motor dikonfirmasi sebagai proof-of-concept di Sprint 3B",
    ))

json.dump(packets_closing, open(OUTPUT_DIR / "semantic_packets_closing.json","w"),
          indent=2, ensure_ascii=False)
print(f"  Closing packets: {len(packets_closing)}")


# ══════════════════════════════════════════════════════════════
# PACKET EXAMPLES (untuk dokumentasi + validator testing)
# ══════════════════════════════════════════════════════════════
all_packets = packets_bab4 + packets_bab7 + packets_closing
examples = {
    "description": "Sample packets dari ketiga pilot (bab4, bab7, closing)",
    "total":       len(all_packets),
    "by_type":     {},
    "sample":      all_packets[:3] if len(all_packets) >= 3 else all_packets,
}
for p in all_packets:
    t = p["packet_type"]
    examples["by_type"][t] = examples["by_type"].get(t,0) + 1

json.dump(examples, open(OUTPUT_DIR / "packet_examples.json","w"),
          indent=2, ensure_ascii=False)

print(f"\nTotal packets: {len(all_packets)}")
print(f"{'='*55}")
print("PACKET EXPORTER COMPLETE")
for t, n in examples["by_type"].items():
    print(f"  {t:<30} × {n}")
print("="*55)
