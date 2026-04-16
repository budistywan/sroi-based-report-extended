"""
Report Architect — Sprint 2 (v1.1 — scoring fix)
SROI Report System

Input : canonical_esl_v1.json + handoff_b.json
Output: report_blueprint.json + gap_matrix.json + handoff_c.json

Usage:
  python report_architect.py
  python report_architect.py --canonical /path/c.json --handoff /path/h.json --output /path/
  CANONICAL_FILE=... HANDOFF_FILE=... OUTPUT_DIR=... python report_architect.py
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

ARCHITECT_VERSION = "1.1.0"

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="Report Architect")
parser.add_argument("--canonical", default=None)
parser.add_argument("--handoff",   default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
HANDOFF_B_FILE = Path(args.handoff)   if args.handoff \
    else Path(os.environ.get("HANDOFF_FILE",   SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
OUTPUT_DIR     = Path(args.output)    if args.output \
    else Path(os.environ.get("OUTPUT_DIR",     SCRIPT_DIR))

print(f"Canonical : {CANONICAL_FILE.resolve()}")
print(f"Handoff B : {HANDOFF_B_FILE.resolve()}")
print(f"Output dir: {OUTPUT_DIR.resolve()}")

for f in [CANONICAL_FILE, HANDOFF_B_FILE]:
    if not f.exists():
        print(f"\nFAIL: File tidak ditemukan — {f}")
        sys.exit(1)

canonical = json.load(open(CANONICAL_FILE))
handoff_b = json.load(open(HANDOFF_B_FILE))
calc      = handoff_b["sroi_metrics"]["calculated"]


# ══════════════════════════════════════════════════════════
# BAGIAN 1 — FIELD STRENGTH EVALUATOR (v1.1)
# ══════════════════════════════════════════════════════════

def has_content(val):
    if val is None:                   return False
    if isinstance(val, str):          return val.strip() != ""
    if isinstance(val, (list, dict)): return len(val) > 0
    return True

# Status epistemic → score
DATA_STATUS_SCORE = {
    "final":              "strong",
    "observed":           "strong",
    "derived":            "partial",
    "proxy":              "partial",
    "under_confirmation": "partial",  # ada tapi belum dikonfirmasi → partial bukan weak
    "pending":            "weak",
}

def eval_field(canonical, field_name, calc):
    """
    Evaluasi kekuatan satu field canonical.
    Return: 'strong' | 'partial' | 'weak' | 'missing'
    """
    # sroi_metrics dinilai dari calc (Handoff B), bukan dari canonical
    if field_name == "sroi_metrics":
        if has_content(calc) and calc.get("sroi_blended", 0) > 0:
            return "strong"
        return "missing"

    val = canonical.get(field_name)
    if not has_content(val):
        return "missing"

    # Dict tanpa data_status — cek apakah isinya substantif
    if isinstance(val, dict):
        if "data_status" in val:
            return DATA_STATUS_SCORE.get(val["data_status"], "partial")
        # Dict tanpa data_status: kuat jika punya ≥ 2 key berisi
        filled = sum(1 for v in val.values() if has_content(v))
        if filled >= 3:  return "strong"
        if filled >= 1:  return "partial"
        return "missing"

    # List: evaluasi berdasarkan data_status mayoritas item
    if isinstance(val, list):
        if len(val) == 0:
            return "missing"
        statuses = [item.get("data_status","") for item in val if isinstance(item, dict)]
        statuses = [s for s in statuses if s]  # hapus kosong
        if not statuses:
            return "partial"  # list berisi tapi tidak punya data_status → partial
        strong_count  = sum(1 for s in statuses if s in ["final","observed"])
        partial_count = sum(1 for s in statuses if s in ["derived","proxy","under_confirmation"])
        if strong_count / len(statuses) >= 0.6:   return "strong"
        if (strong_count + partial_count) / len(statuses) >= 0.5: return "partial"
        return "weak"

    # Nilai primitif (string, number) yang tidak kosong → partial
    return "partial"

STRENGTH_SCORE = {"strong": 3, "partial": 2, "weak": 1, "missing": 0}


# ══════════════════════════════════════════════════════════
# BAGIAN 2 — BAB DEFINITIONS
# ══════════════════════════════════════════════════════════

BAB_DEFINITIONS = [
    {
        "chapter_id":    "bab_1",
        "chapter_title": "Pendahuluan",
        "builder_mode":  "framing",
        "canonical_inputs":  ["program_identity","program_positioning","source_registry"],
        "required_inputs":   ["program_identity"],
        "description": "Latar belakang, tujuan, ruang lingkup, konsiderasi hukum, dan konteks PROPER/SROI.",
        "notes": "Narasi latar belakang hukum PROPER dan SROI diinferensi dari program_positioning. Data program sudah cukup kuat."
    },
    {
        "chapter_id":    "bab_2",
        "chapter_title": "Profil Perusahaan",
        "builder_mode":  "framing",
        "canonical_inputs":  ["program_identity","program_positioning"],
        "required_inputs":   ["program_identity"],
        "description": "Lingkup usaha, visi misi, prinsip TJSL, dan jenis program pemberdayaan.",
        "notes": "Profil detail PT Pertamina Lubricants tidak ada di canonical — builder inferensi dari program_positioning dan pengetahuan umum."
    },
    {
        "chapter_id":    "bab_3",
        "chapter_title": "Metodologi SROI dan Triple Loop Learning",
        "builder_mode":  "framing",
        "canonical_inputs":  ["source_registry","ddat_params","ori_rates"],
        "required_inputs":   ["ddat_params","ori_rates"],
        "description": "Kerangka SROI, metode pengumpulan data, LFA, exit strategy, dan loop learning.",
        "notes": "Narasi metodologis perlu dikembangkan dari prinsip umum SROI — data aktual terbatas pada parameter kalkulasi."
    },
    {
        "chapter_id":    "bab_4",
        "chapter_title": "Identifikasi Kondisi Awal",
        "builder_mode":  "context",
        "canonical_inputs":  ["context_baseline","problem_framing","beneficiaries"],
        "required_inputs":   ["problem_framing"],
        "description": "Profil wilayah, permasalahan ESG, dan potensi sasaran program.",
        "notes": "Data baseline wilayah (statistik BPS, peta) tidak ada. Problem framing tersedia secara derived. Builder tulis placeholder terstruktur untuk data wilayah."
    },
    {
        "chapter_id":    "bab_5",
        "chapter_title": "Identifikasi Kondisi Ideal",
        "builder_mode":  "context",
        "canonical_inputs":  ["ideal_conditions","problem_framing","program_positioning"],
        "required_inputs":   ["ideal_conditions"],
        "description": "Tujuan utama, tujuan spesifik LSEW, dan kesesuaian masalah–intervensi–tujuan.",
        "notes": "Kondisi ideal tersedia sebagai derived. Kualitas cukup untuk bab partial."
    },
    {
        "chapter_id":    "bab_6",
        "chapter_title": "Strategi untuk Mencapai Kondisi Ideal",
        "builder_mode":  "context",
        "canonical_inputs":  ["strategy_design","program_identity","program_positioning"],
        "required_inputs":   ["strategy_design"],
        "description": "Nama dan filosofi program, relevansi visi misi, roadmap, value chain, kelembagaan.",
        "notes": "Strategy design cukup kuat — roadmap, value chain, dan kelembagaan tersedia."
    },
    {
        "chapter_id":    "bab_7",
        "chapter_title": "Implementasi / PDIS dengan SROI",
        "builder_mode":  "sroi",
        "canonical_inputs":  [
            "activities","outputs","stakeholders",
            "investment","outcomes","monetization",
            "ddat_params","ori_rates","sroi_metrics"
        ],
        "required_inputs":   [
            "activities","investment","outcomes",
            "monetization","ddat_params","sroi_metrics"
        ],
        "description": "Kegiatan, stakeholder, investasi, output, outcome, fiksasi, monetisasi, LFA, nilai SROI.",
        "notes": "Bab terkuat. Angka dari sroi_metrics.calculated — tidak boleh ditulis ulang oleh builder."
    },
    {
        "chapter_id":    "bab_8",
        "chapter_title": "Aspek Pembelajaran dengan Triple Loop Learning",
        "builder_mode":  "learning",
        "canonical_inputs":  ["learning_signals","activities","strategy_design"],
        "required_inputs":   ["learning_signals"],
        "description": "Identifikasi masalah, LFA refleksi, L1/L2/L3, keunikan, efisiensi, keberlanjutan.",
        "notes": "Learning signals partial/derived. Refleksi triple loop mendalam perlu data wawancara — builder beri label inferred."
    },
    {
        "chapter_id":    "bab_9",
        "chapter_title": "Penutup",
        "builder_mode":  "learning",
        "canonical_inputs":  ["sroi_metrics","learning_signals","ideal_conditions"],
        "required_inputs":   ["sroi_metrics"],
        "description": "Kesimpulan evaluatif dan rekomendasi tindak lanjut.",
        "notes": "Diturunkan dari SROI + learning signals. Kualitas tergantung kedalaman Bab 7 dan 8."
    },
]


# ══════════════════════════════════════════════════════════
# BAGIAN 3 — SCORING PER BAB
# ══════════════════════════════════════════════════════════

def score_chapter(bab_def, canonical, calc):
    scores         = []
    missing_fields = []
    weak_fields    = []
    field_detail   = {}

    for field in bab_def["canonical_inputs"]:
        strength = eval_field(canonical, field, calc)
        score    = STRENGTH_SCORE[strength]
        scores.append(score)
        field_detail[field] = strength
        is_required = field in bab_def.get("required_inputs", [])

        if strength == "missing":
            missing_fields.append(field)
        elif strength == "weak" and is_required:
            weak_fields.append(field)

    avg = sum(scores) / len(scores) if scores else 0
    required_missing = [f for f in bab_def.get("required_inputs",[]) if f in missing_fields]

    if required_missing:
        status, risk = "missing", "skeleton_only"
    elif avg >= 2.6 or (not required_missing and all(s != "missing" for s in field_detail.values()) and STRENGTH_SCORE.get(field_detail.get("sroi_metrics","missing"),0) == 3):
        status, risk = "strong",  "reliable"
    elif avg >= 2.0:
        risk   = "reliable" if not weak_fields else "thin"
        status = "partial"
    elif avg >= 1.0:
        status, risk = "weak",    "thin"
    else:
        status, risk = "missing", "skeleton_only"

    return {
        "score":            round(avg, 2),
        "status":           status,
        "risk":             risk,
        "missing_fields":   missing_fields,
        "weak_fields":      weak_fields,
        "required_missing": required_missing,
        "field_detail":     field_detail,
    }


# ══════════════════════════════════════════════════════════
# BAGIAN 4 — MODE SELECTION
# ══════════════════════════════════════════════════════════

def select_mode(chapter_scores):
    statuses    = {c["chapter_id"]: c["status"] for c in chapter_scores}
    bab7_status = statuses.get("bab_7", "missing")

    if bab7_status != "strong":
        return "skeleton", "Bab 7 tidak strong — data inti SROI tidak mencukupi"

    missing_count = sum(1 for s in statuses.values() if s == "missing")
    weak_count    = sum(1 for s in statuses.values() if s in ["weak","missing"])

    partial_count = sum(1 for s in statuses.values() if s == "partial")

    if weak_count == 0 and partial_count == 0:
        return "full",    "Semua bab strong"
    elif weak_count == 0 and missing_count == 0:
        return "partial", f"Bab 7 strong · {partial_count} bab partial · tidak ada yang missing/weak"
    elif missing_count <= 2:
        return "partial", f"Bab 7 strong · {missing_count} bab missing · {weak_count} bab weak/missing"
    else:
        return "skeleton", f"Bab 7 strong tapi {missing_count} bab missing — terlalu banyak gap"


# ══════════════════════════════════════════════════════════
# BAGIAN 5 — EKSEKUSI
# ══════════════════════════════════════════════════════════

print("\n--- Scanning coverage per bab ---")
chapter_results = []

for bab in BAB_DEFINITIONS:
    result = score_chapter(bab, canonical, calc)
    chapter_results.append({
        "chapter_id":    bab["chapter_id"],
        "chapter_title": bab["chapter_title"],
        "builder_mode":  bab["builder_mode"],
        **result,
        "canonical_inputs": bab["canonical_inputs"],
        "description":   bab["description"],
        "notes":         bab["notes"],
    })
    bar  = "█" * int(result["score"] / 3 * 20)
    flag = " ⚠" if result["missing_fields"] or result["weak_fields"] else ""
    print(f"  {bab['chapter_id']} [{result['status']:8}] {result['risk']:12} "
          f"score={result['score']:.1f}  {bar}{flag}")
    # detail per field
    for field, strength in result["field_detail"].items():
        marker = {"strong":"✓","partial":"~","weak":"✗","missing":"✕"}.get(strength,"?")
        print(f"           {marker} {field} [{strength}]")

report_mode, mode_reason = select_mode(chapter_results)
print(f"\n  Mode terpilih : {report_mode.upper()}")
print(f"  Alasan        : {mode_reason}")


# ── Report Blueprint ─────────────────────────────────────
report_blueprint = {
    "blueprint_version": "1.0",
    "case_id":           canonical["case_id"],
    "program_code":      canonical["program_identity"]["program_code"],
    "report_mode":       report_mode,
    "mode_reason":       mode_reason,
    "generated_at":      datetime.now().isoformat(),
    "architect_version": ARCHITECT_VERSION,
    "chapters": [
        {
            "chapter_id":       r["chapter_id"],
            "chapter_title":    r["chapter_title"],
            "builder_mode":     r["builder_mode"],
            "coverage_status":  r["status"],
            "risk":             r["risk"],
            "score":            r["score"],
            "canonical_inputs": r["canonical_inputs"],
            "field_detail":     r["field_detail"],
            "notes":            r["notes"],
        }
        for r in chapter_results
    ]
}

# ── Gap Matrix ────────────────────────────────────────────
gap_matrix = []
for r in chapter_results:
    # Masukkan ke gap matrix jika: ada missing/weak field ATAU status partial/weak/missing
    if r["missing_fields"] or r["weak_fields"] or r["status"] in ["weak","missing","partial"]:
        if r["required_missing"]:
            rec = "placeholder"
        elif r["status"] in ["weak","missing"]:
            rec = "placeholder"
        elif r["status"] == "partial":
            rec = "full"  # bisa ditulis, tapi perlu catatan gap
        else:
            rec = "full"

        gap_matrix.append({
            "chapter_id":       r["chapter_id"],
            "chapter_title":    r["chapter_title"],
            "status":           r["status"],
            "missing_fields":   r["missing_fields"],
            "weak_fields":      r["weak_fields"],
            "required_missing": r["required_missing"],
            "recommendation":   rec,
            "note":             r["notes"],
        })

# ── Handoff C ─────────────────────────────────────────────
handoff_c = {
    "report_blueprint_json": report_blueprint,
    "gap_matrix":            gap_matrix,
    "program_canonical_ref": str(CANONICAL_FILE.resolve()),
    "financial_handoff_ref": str(HANDOFF_B_FILE.resolve()),
    "generated_at":          datetime.now().isoformat(),
}

# ── Tulis output ──────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
blueprint_path  = OUTPUT_DIR / "report_blueprint.json"
gap_matrix_path = OUTPUT_DIR / "gap_matrix.json"
handoff_c_path  = OUTPUT_DIR / "handoff_c.json"

json.dump(report_blueprint, open(blueprint_path,  "w"), indent=2, ensure_ascii=False)
json.dump(gap_matrix,       open(gap_matrix_path, "w"), indent=2, ensure_ascii=False)
json.dump(handoff_c,        open(handoff_c_path,  "w"), indent=2, ensure_ascii=False)

# ── Summary table ─────────────────────────────────────────
print("\n" + "="*65)
print(f"REPORT BLUEPRINT — {canonical['program_identity']['program_code']}")
print(f"Mode : {report_mode.upper()}  |  {mode_reason}")
print("="*65)
print(f"{'BAB':<8} {'JUDUL':<38} {'STATUS':<10} {'RISK':<14} SCORE")
print("-"*65)
for r in chapter_results:
    flag = " ⚠" if r["missing_fields"] or r["weak_fields"] else ""
    print(f"{r['chapter_id']:<8} {r['chapter_title'][:37]:<38} "
          f"{r['status']:<10} {r['risk']:<14} {r['score']:.1f}{flag}")

if gap_matrix:
    print(f"\nGAP MATRIX — {len(gap_matrix)} bab perlu perhatian")
    print("-"*65)
    for g in gap_matrix:
        print(f"  {g['chapter_id']} [{g['recommendation']:12}] {g['status']}")
        if g["missing_fields"]: print(f"    Missing : {', '.join(g['missing_fields'])}")
        if g["weak_fields"]:    print(f"    Weak    : {', '.join(g['weak_fields'])}")

print("="*65)
print(f"\nOutput:")
print(f"  {blueprint_path}")
print(f"  {gap_matrix_path}")
print(f"  {handoff_c_path}")
