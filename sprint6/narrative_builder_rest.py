"""
Narrative Builder — Sprint 6 (v2.0 — Dynamic)
Sub-modes: builder_framing (Bab 1-3), builder_context (Bab 4-6), builder_learning (Bab 8-9)

Input  : canonical_{program}_v1.json + handoff_b.json + report_blueprint.json
Output : chapter_semantic_bab[1-6,8-9].json (Handoff E ke QA)

Rules:
  - Bab partial → tulis konten + callout_gap untuk bagian yang tipis
  - Bab strong  → tulis penuh
  - Tidak ada angka baru — semua dari sroi_metrics.calculated
  - v2.0: semua referensi program dibaca dari canonical — tidak ada hardcode ESL

Usage:
  python narrative_builder_rest.py
  python narrative_builder_rest.py --canonical /p/ --handoff-b /p/ --blueprint /p/ --output /p/
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

BUILDER_VERSION = "2.0.0"

# ── FORMAT NORMALIZERS ───────────────────────────────────────────
def _to_list(val, str_key=None):
    """Normalisasi ke list of strings — handle list, dict, string."""
    if val is None: return []
    if isinstance(val, list): return [str(i) for i in val if i]
    if isinstance(val, dict):
        if str_key and str_key in val: return [str(val[str_key])]
        parts = [str(v) for v in val.values() if v and isinstance(v, (str,int,float))]
        return parts if parts else []
    return [str(val)] if val else []

def _to_str(val, keys=None, fallback=""):
    """Normalisasi ke string."""
    if val is None: return fallback
    if isinstance(val, str): return val
    if isinstance(val, dict):
        if keys:
            for k in keys:
                if val.get(k): return str(val[k])
        return " ".join(str(v) for v in val.values() if v and isinstance(v, str))
    if isinstance(val, list):
        return "; ".join(str(i) for i in val[:3] if i)
    return str(val)

def _activities_to_list(acts_raw):
    if isinstance(acts_raw, dict):
        flat = []
        for yr_key, act_list in acts_raw.items():
            if isinstance(act_list, list):
                for a in act_list:
                    if isinstance(a, str):
                        flat.append({"year": int(yr_key), "name": a, "activity_scope": [a]})
                    elif isinstance(a, dict):
                        flat.append({**a, "year": int(yr_key)})
        return flat
    return acts_raw if isinstance(acts_raw, list) else []

def _ls_to_list(val):
    """Normalisasi learning_signals loop ke list."""
    if not val: return ["—"]
    if isinstance(val, list): return [str(i) for i in val] if val else ["—"]
    if isinstance(val, dict):
        parts = []
        for k in ("signal", "implication", "lesson", "finding"):
            if val.get(k): parts.append(str(val[k]))
        return parts if parts else ["—"]
    return [str(val)] if val else ["—"]

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--canonical",  default=None)
parser.add_argument("--handoff-b",  default=None, dest="handoff_b")
parser.add_argument("--blueprint",  default=None)
parser.add_argument("--output",     default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
HANDOFF_B_FILE = Path(args.handoff_b) if args.handoff_b \
    else Path(os.environ.get("HANDOFF_B_FILE", SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
BLUEPRINT_FILE = Path(args.blueprint) if args.blueprint \
    else Path(os.environ.get("BLUEPRINT_FILE", SCRIPT_DIR.parent / "sprint2/report_blueprint.json"))
OUTPUT_DIR     = Path(args.output)    if args.output    \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

for f in [CANONICAL_FILE, HANDOFF_B_FILE, BLUEPRINT_FILE]:
    if not f.exists():
        print(f"FAIL: {f} tidak ditemukan"); sys.exit(1)

canonical  = json.load(open(CANONICAL_FILE))
handoff_b  = json.load(open(HANDOFF_B_FILE))
blueprint  = json.load(open(BLUEPRINT_FILE))

# ── IDENTITAS PROGRAM ─────────────────────────────────────
pi   = canonical["program_identity"]
pp   = canonical.get("program_positioning", {})
sd   = canonical.get("strategy_design", {})
pf   = canonical.get("problem_framing", {})
ic   = canonical.get("ideal_conditions", {})
ls   = canonical.get("learning_signals", {})
cb   = canonical.get("context_baseline", {})

PROG_CODE    = pi.get("program_code", "PROGRAM")
PROG_NAME    = pi.get("program_name", PROG_CODE)
PERIOD_LABEL = pi.get("period_label", f"{pi.get('period_start')}–{pi.get('period_end')}")
TARGET_GROUP = pi.get("target_group", "kelompok penerima manfaat")

calc      = handoff_b["sroi_metrics"]["calculated"]
audit_map = {e["field"]: e["value"] for e in handoff_b["calc_audit_log"]}

years = sorted(set(
    item["year"] for item in canonical.get("investment", [])
)) or [2023, 2024, 2025]

# ── Aspek dinamis ─────────────────────────────────────────
asp_meta = {}
seen = []
for m in canonical.get("monetization", []):
    asp = m["aspect_code"]
    if asp in seen: continue
    seen.append(asp)
    asp_meta[asp] = {
        "name": m.get("aspect_name", asp),
        "tag":  "observed" if m.get("measurement_type") == "observed" else "proxy",
        "proxy_basis": m.get("proxy_basis", ""),
    }

observed_asps = [k for k, v in asp_meta.items() if v["tag"] == "observed"]
proxy_asps    = [k for k, v in asp_meta.items() if v["tag"] == "proxy"]

# has_pending — didefinisikan di sini agar bisa dipakai di semua bab
has_pending = any(
    i.get("data_status","") in ("under_confirmation","planned")
    for i in canonical.get("investment",[])
)

# ── Node info ─────────────────────────────────────────────
institutional = sd.get("institutional", {})
nodes         = institutional.get("nodes", [])
node_note     = institutional.get("note", "")

# ── Evidence & flags ──────────────────────────────────────
_uf_raw = canonical.get("uncertainty_flags", [])
if isinstance(_uf_raw, dict): _uf_raw = list(_uf_raw.values())
elif not isinstance(_uf_raw, list): _uf_raw = []
_uf_norm = [f if isinstance(f, dict) else {"description": str(f), "severity": "medium"} for f in _uf_raw]
high_flags   = [f for f in _uf_norm if f.get("severity") == "high"]
ev_success   = [e for e in canonical.get("evidence_registry",[]) if "observed" in e.get("type","").lower()]
sroi_val     = calc.get("sroi_blended", 0)

def A(f): return audit_map[f]
def idr(v): return f"Rp {v:,.0f}"
def ratio(v): return f"1 : {v:.2f}"

# ── BLOCK HELPERS ─────────────────────────────────────────
def H1(t): return {"type":"heading_1","text":t}
def H2(t): return {"type":"heading_2","text":t}
def H3(t): return {"type":"heading_3","text":t}
def P(t, ds=None, sr=None):
    b = {"type":"paragraph","text":t}
    if ds: b["display_status"]=ds
    if sr: b["source_refs"]=sr
    return b
def LEAD(t): return {"type":"paragraph_lead","text":t}
def SMALL(t): return {"type":"paragraph_small","text":t}
def DIV():   return {"type":"divider"}
def BREAK(): return {"type":"page_break"}
def GAP(t, gt="data_unavailable"):
    return {"type":"callout_gap","text":t,"gap_type":gt,"display_status":"present_as_inferred"}
def INFO(t, sr=None):
    b = {"type":"callout_info","text":t}
    if sr: b["source_refs"]=sr
    return b
def WARN(t, sr=None):
    b = {"type":"callout_warning","text":t}
    if sr: b["source_refs"]=sr
    return b
def NEUTRAL(t): return {"type":"callout_neutral","text":t}
def SUCCESS(t, sr=None):
    b = {"type":"callout_success","text":t}
    if sr: b["source_refs"]=sr
    return b
def BULLET(items):
    return {"type":"bullet_list","items":[{"text":i} for i in items]}
def NUMBERED(items):
    return {"type":"numbered_list","items":[{"text":i} for i in items]}
def METRIC3(items): return {"type":"metric_card_3col","items":items}
def TBL_BL(headers, rows, cw, sr=None):
    b = {"type":"table_borderless","headers":headers,"rows":rows,"column_widths":cw}
    if sr: b["source_refs"]=sr
    return b

def chapter_semantic(cid, ctype, bmode, blocks):
    return {
        "chapter_id":        cid,
        "chapter_type":      ctype,
        "source_outline_ref":cid,
        "builder_mode":      bmode,
        "builder_version":   BUILDER_VERSION,
        "program_code":      PROG_CODE,
        "generated_at":      datetime.now().isoformat(),
        "blocks":            blocks,
    }


# ══════════════════════════════════════════════════════════
# BAB 1 — PENDAHULUAN
# ══════════════════════════════════════════════════════════
print(f"Building Bab 1 — Pendahuluan ({PROG_CODE})...")
b1 = []
b1 += [
    H1("BAB I PENDAHULUAN"),
    LEAD(
        f"Bab ini menyajikan latar belakang, tujuan, ruang lingkup, dan konsiderasi "
        f"hukum penyusunan Laporan Evaluasi Social Return on Investment (SROI) "
        f"Program {PROG_NAME} ({PROG_CODE}) periode {PERIOD_LABEL}."
    ),
    DIV(),
    H2("1.1 Latar Belakang Penulisan Laporan SROI"),
    P(
        f"Tanggung Jawab Sosial dan Lingkungan (TJSL) merupakan kewajiban strategis "
        f"yang tidak hanya bersifat normatif, tetapi juga menjadi instrumen pengukuran "
        f"dampak sosial yang terukur. {pi.get('company','PT Pertamina Lubricants')} sebagai "
        f"bagian dari ekosistem BUMN, melaksanakan TJSL dalam kerangka "
        f"{pp.get('proper_category','Beyond Compliance — Inovasi Sosial')} — melampaui "
        f"kepatuhan minimum dan mengarah pada penciptaan nilai sosial yang berkelanjutan."
    ),
    P(
        "Social Return on Investment (SROI) adalah kerangka analisis yang mengukur "
        "nilai sosial, ekonomi, dan lingkungan dari suatu program intervensi secara "
        "holistik. Berbeda dengan evaluasi konvensional yang hanya mengukur output, "
        "SROI menelusuri perubahan yang dirasakan oleh pemangku kepentingan — dari "
        "individu penerima manfaat hingga komunitas yang lebih luas."
    ),
    INFO(
        f"Program {PROG_NAME} masuk dalam kategori "
        f"{pp.get('proper_category','Beyond Compliance')} "
        f"sesuai regulasi PROPER yang mewajibkan perusahaan peserta untuk mengusulkan "
        f"program inovasi sosial unggulan dengan pengukuran dampak berbasis SROI.",
        sr=["program_positioning"]
    ),
    H2("1.2 Tujuan dan Luaran"),
    P("Penyusunan laporan ini bertujuan untuk:"),
    NUMBERED([
        "Mengidentifikasi dan mendokumentasikan seluruh aktivitas program secara terstruktur",
        "Menghitung rasio nilai sosial yang dihasilkan terhadap investasi yang dikeluarkan",
        "Menyajikan temuan secara transparan — termasuk keterbatasan data dan area yang perlu diperkuat",
        "Memberikan rekomendasi berbasis bukti untuk pengembangan program pada periode berikutnya",
        "Memenuhi kewajiban pelaporan PROPER beyond compliance kepada KLHK",
    ]),
    H2("1.3 Ruang Lingkup Kajian"),
    P(
        f"Kajian ini mencakup seluruh aktivitas Program {PROG_NAME} "
        f"selama periode {PERIOD_LABEL}, "
        f"meliputi {len(nodes)} node program yang tersebar di wilayah operasional."
    ),
    TBL_BL(
        ["Dimensi", "Cakupan"],
        [
            ["Program",        PROG_NAME],
            ["Kode Program",   PROG_CODE],
            ["Periode",        PERIOD_LABEL],
            ["Perusahaan",     pi.get("company","—")],
            ["Pilar TJSL",     pp.get("tjsl_pillar","—")],
            ["Kategori PROPER",pp.get("proper_category","—")],
            ["Node Program",   f"{len(nodes)} node"],
            ["Kelompok Sasaran", TARGET_GROUP],
        ],
        [3200, 6438],
        sr=["program_identity","program_positioning"]
    ),
    H2("1.4 Konsiderasi Hukum"),
    P("Penyusunan laporan ini berlandaskan pada regulasi berikut:"),
    BULLET(_to_list(pp.get("policy_basis"))),
    SMALL(
        "Regulasi di atas membentuk kerangka kewajiban dan metodologi "
        "yang menjadi dasar pelaksanaan kajian SROI ini."
    ),
]

# ══════════════════════════════════════════════════════════
# BAB 2 — PROFIL PERUSAHAAN
# ══════════════════════════════════════════════════════════
print(f"Building Bab 2 — Profil Perusahaan ({PROG_CODE})...")
b2 = []
company = pi.get("company", "PT Pertamina Lubricants")
b2 += [
    H1("BAB II PROFIL PERUSAHAAN"),
    LEAD(
        f"Bab ini menyajikan profil {company} sebagai pemrakarsa program, "
        f"mencakup lingkup usaha, arah kebijakan TJSL, dan posisi program "
        f"{PROG_NAME} dalam portofolio pemberdayaan perusahaan."
    ),
    DIV(),
    H2("2.1 Lingkup Usaha"),
    P(
        f"{company} merupakan anak perusahaan PT Pertamina (Persero) yang "
        f"bergerak di bidang produksi dan distribusi pelumas untuk kendaraan bermotor "
        f"dan industri. Produk unggulan perusahaan mencakup merek Enduro yang ditujukan "
        f"untuk segmen kendaraan bermotor, menjadikan perusahaan ini memiliki kedekatan "
        f"langsung dengan ekosistem perbengkelan otomotif di seluruh Indonesia."
    ),
    GAP(
        "Data lengkap profil perusahaan (kapasitas produksi, jumlah karyawan, sebaran "
        "distribusi) tidak tersedia dalam canonical JSON kajian ini. Untuk laporan final, "
        "bagian ini perlu dilengkapi dari dokumen profil korporat resmi.",
        "data_unavailable"
    ),
    H2("2.2 Arah Kebijakan, Visi Misi, dan Tujuan Perusahaan"),
    P(
        f"Komitmen {company} terhadap pembangunan sosial diwujudkan melalui "
        f"pilar TJSL '{pp.get('tjsl_pillar','—')}' yang selaras dengan agenda SDGs global. "
        f"Program {PROG_NAME} secara langsung berkontribusi pada:"
    ),
    BULLET(_to_list(pp.get("sdg_alignment"))),
    H2("2.3 Prinsip dan Strategi Pengelolaan Pemberdayaan"),
    P(
        f"Pengelolaan program TJSL {company} menganut pendekatan "
        f"{pp.get('proper_category','Beyond Compliance')} — sebuah paradigma yang "
        f"menempatkan program sosial bukan sebagai kewajiban semata, melainkan sebagai "
        f"investasi strategis yang menghasilkan nilai bersama bagi perusahaan dan masyarakat."
    ),
    INFO(
        "Pendekatan beyond compliance mengharuskan perusahaan untuk mengukur dampak "
        "program secara kuantitatif melalui SROI, membuktikan bahwa setiap rupiah "
        "yang diinvestasikan menghasilkan nilai sosial yang terukur.",
        sr=["program_positioning"]
    ),
    H2("2.4 Jenis dan Lingkup Program Pemberdayaan Masyarakat"),
    P(
        f"Program {PROG_NAME} merupakan salah satu program unggulan TJSL "
        f"{company} yang difokuskan pada {TARGET_GROUP}. "
        f"{sd.get('program_philosophy','')}"
    ),
]

# ══════════════════════════════════════════════════════════
# BAB 3 — METODOLOGI
# ══════════════════════════════════════════════════════════
print(f"Building Bab 3 — Metodologi ({PROG_CODE})...")
b3 = []

# Sumber data dari evidence_registry
data_sources = []
for e in canonical.get("evidence_registry", []):
    ds_str = f"{e.get('description','—')} ({e.get('data_status','—')})"
    data_sources.append(ds_str)

# Proxy descriptions dari asp_meta
proxy_desc_list = [
    f"{asp}: {asp_meta[asp].get('proxy_basis','proxy tervalidasi')}"
    for asp in proxy_asps
]

b3 += [
    H1("BAB III METODOLOGI SROI DAN TRIPLE LOOP LEARNING"),
    LEAD(
        "Bab ini menjelaskan kerangka metodologi yang digunakan dalam kajian SROI "
        "program, mencakup prinsip-prinsip SROI, metode pengumpulan data, pendekatan "
        "LFA, parameter fiksasi dampak, dan kerangka pembelajaran triple loop."
    ),
    DIV(),
    H2("3.1 Perhitungan Dampak Investasi Sosial / Social Return on Investment"),
    P(
        "SROI adalah kerangka pengukuran yang mengkuantifikasi nilai sosial, ekonomi, "
        "dan lingkungan dari suatu investasi. Berbeda dengan ROI finansial konvensional, "
        "SROI memasukkan nilai-nilai yang tidak selalu tercermin dalam transaksi pasar."
    ),
    P(
        f"Formula dasar SROI dalam kajian ini: "
        "SROI = Total Net Benefit (compounded) ÷ Total Investasi. "
        "Nilai bersih dihitung setelah menerapkan DDAT adjustment per aspek monetisasi, "
        "kemudian di-compound ke terminal year menggunakan ORI reference rate."
    ),
    H2("3.2 Metode Pengumpulan Data, Analisis Data, dan Rumus SROI"),
    P("Pengumpulan data menggunakan pendekatan triangulasi:"),
    BULLET(
        data_sources[:5] if data_sources else [
            f"Data observed: transaksi aktual aspek {', '.join(observed_asps)}" if observed_asps else "Data primer program",
            f"Data proxy: {'; '.join(proxy_desc_list)}" if proxy_desc_list else "Data sekunder tervalidasi",
            "Data program: laporan kegiatan, dokumentasi investasi, catatan pendampingan",
        ]
    ),
    H2("3.3 Parameter Fiksasi Dampak (DDAT)"),
    P(
        "Empat parameter fiksasi diterapkan untuk memastikan nilai sosial yang diklaim "
        "benar-benar mencerminkan kontribusi program:"
    ),
    TBL_BL(
        ["Parameter", "Definisi", "Fungsi"],
        [
            ["Deadweight (DW)",  "Manfaat yang terjadi tanpa intervensi program",     "Menghindari klaim berlebihan"],
            ["Displacement (DS)","Manfaat yang menggeser pihak lain",                 "Mencegah double-counting"],
            ["Attribution (AT)", "Kontribusi pihak lain terhadap outcome",            "Proporsionalitas klaim"],
            ["Drop-off (DO)",    "Penurunan manfaat dari waktu ke waktu",             "Realisme jangka menengah"],
        ],
        [2400, 4000, 3238],
        sr=["ddat_params"]
    ),
    H2("3.4 ORI Reference Rate sebagai Discount Rate"),
    P(
        "Nilai bersih setiap tahun di-compound ke terminal year menggunakan "
        "suku bunga ORI (Obligasi Ritel Indonesia) sebagai proxy biaya modal sosial "
        "yang konservatif dan terverifikasi:"
    ),
    TBL_BL(
        ["Tahun", "Seri ORI", "Rate", "Compound Factor"],
        [
            [str(yr),
             canonical["ori_rates"].get(str(yr),{}).get("series","—"),
             f"{canonical['ori_rates'].get(str(yr),{}).get('rate',0)*100:.2f}%",
             str(canonical["ori_rates"].get(str(yr),{}).get("compound_factor","—"))]
            for yr in years
        ],
        [1500, 3000, 2000, 3138],
        sr=["ori_rates"]
    ),
    H2("3.5 Prinsip SROI"),
    BULLET([
        "Involve stakeholders — pemangku kepentingan dilibatkan dalam identifikasi outcome",
        "Understand what changes — fokus pada perubahan nyata yang dirasakan",
        "Value the things that matter — monetisasi nilai yang tidak selalu terwakili pasar",
        "Only include what is material — excludes minor outcomes",
        "Do not over-claim — DDAT adjustment diterapkan secara konsisten",
        "Be transparent — status data (observed/proxy/pending) ditampilkan eksplisit",
        "Verify the result — audit trail tersedia melalui calc_audit_log",
    ]),
    H2("3.6 Logical Framework Approach (LFA)"),
    P(
        "LFA digunakan untuk memetakan rantai kausalitas program: dari input dan "
        "aktivitas menuju output, outcome, dan dampak jangka panjang."
    ),
    GAP(
        "Tabel LFA utuh lintas program belum tersedia dalam canonical JSON — "
        "memerlukan data dari laporan kegiatan detail per aktivitas per node.",
        "data_unavailable"
    ),
    H2("3.7 Triple Loop Learning"),
    P(
        "Kajian ini mengadopsi kerangka triple loop learning untuk mengevaluasi "
        "bukan hanya apa yang terjadi (loop 1), tetapi juga mengapa program "
        "merespons seperti yang dilakukan (loop 2), dan nilai serta asumsi apa "
        "yang berubah dalam proses tersebut (loop 3)."
    ),
    BULLET([
        "Loop 1 (Single): pembelajaran dari hasil langsung — apa yang berhasil dan tidak",
        "Loop 2 (Double): refleksi atas strategi — mengapa cara tertentu dipilih",
        "Loop 3 (Triple): transformasi nilai dan asumsi mendasar program",
    ]),
]

# ══════════════════════════════════════════════════════════
# BAB 4 — KONDISI AWAL
# ══════════════════════════════════════════════════════════
print(f"Building Bab 4 — Kondisi Awal ({PROG_CODE})...")
b4 = []
baseline_econ = cb.get("socioeconomic", {})
b4 += [
    H1("BAB IV IDENTIFIKASI KONDISI AWAL"),
    LEAD(
        "Bab ini mengidentifikasi kondisi awal yang menjadi dasar intervensi program — "
        "mencakup karakteristik kelompok sasaran, hambatan yang dihadapi, dan potensi "
        "yang dapat dimobilisasi melalui program."
    ),
    DIV(),
    WARN(
        "Catatan keterbatasan: pemetaan kondisi awal dalam laporan ini disusun terutama "
        "dari data program dan problem framing yang diturunkan dari desain intervensi. "
        "Pembacaan kondisi awal pada bab ini perlu dipahami sebagai baseline programatik, "
        "bukan potret statistik wilayah yang lengkap.",
        sr=["context_baseline","problem_framing"]
    ),
    H2("4.1 Profil dan Kondisi Kelompok Sasaran"),
    P(
        f"Kelompok sasaran program adalah {TARGET_GROUP}. "
        f"{_to_str(baseline_econ.get('baseline_economic') or cb.get('main_problem',''))}"
    ),
    P(
        " ".join(filter(None, [
            _to_str(baseline_econ.get('baseline_social')),
            _to_str(baseline_econ.get('baseline_wellbeing')),
            "; ".join(_to_list(cb.get('key_indicators')))[:200] if cb.get('key_indicators') else ""
        ])),
        ds="present_as_inferred",
        sr=["context_baseline"]
    ),
    H2("4.2 Permasalahan"),
    P(
        f"Berdasarkan analisis program, terdapat hambatan utama yang menjadi tantangan "
        f"bagi {TARGET_GROUP} dalam mencapai penghidupan yang berkelanjutan:"
    ),
]

# Problem tree — dinamis
problem_tree = pf.get("problem_tree", [])
# Handle problem_framing.narrative (PSN format) atau problem_tree (EHS format)
pf_narrative = _to_str(pf.get("narrative"), fallback="")
pf_barrier   = _to_str(pf.get("core_barrier"), fallback="")
if pf_narrative:
    b4.append(P(pf_narrative, ds="present_as_inferred", sr=["problem_framing"]))
if pf_barrier:
    b4.append(P(f"Hambatan inti: {pf_barrier}", ds="present_as_inferred", sr=["problem_framing"]))
if isinstance(problem_tree, list) and len(problem_tree) > 0:
    if isinstance(problem_tree[0], str):
        for pt in problem_tree:
            b4.append(P(f"• {pt}", ds="present_as_inferred", sr=["problem_framing"]))
    elif isinstance(problem_tree[0], dict):
        for pt in problem_tree:
            b4.append(H3(f"{pt.get('problem_id','')}. {pt.get('label','')}"))
            b4.append(P(pt.get("description",""), ds="present_as_inferred", sr=["problem_framing"]))
            if pt.get("root_causes"):
                b4.append(BULLET(_to_list(pt["root_causes"])))

b4 += [
    WARN(
        "Data di atas bersumber dari problem framing yang disusun berdasarkan "
        "inferensi dari desain program. Untuk laporan defensible, setiap poin "
        "perlu didukung data primer atau data sekunder terverifikasi.",
        sr=["problem_framing"]
    ),
    H2("4.3 Potensi"),
    P("Program mengidentifikasi potensi yang dapat dimobilisasi melalui intervensi yang tepat:"),
]

# Potensi dari ideal_conditions
potentials = _to_list(ic.get("key_improvements"))
if potentials:
    b4.append(BULLET(potentials))
else:
    b4.append(GAP("Data potensi kelompok sasaran belum tersedia dalam canonical JSON.","data_unavailable"))

# ══════════════════════════════════════════════════════════
# BAB 5 — KONDISI IDEAL
# ══════════════════════════════════════════════════════════
print(f"Building Bab 5 — Kondisi Ideal ({PROG_CODE})...")
b5 = []
b5 += [
    H1("BAB V IDENTIFIKASI KONDISI IDEAL YANG DIHARAPKAN"),
    LEAD(ic.get("vision_statement","Kondisi ideal yang ingin dicapai program.")),
    DIV(),
    H2("5.1 Tujuan Utama"),
    P(
        f"Program {PROG_NAME} bertujuan menciptakan ekosistem produktif "
        f"yang memungkinkan {TARGET_GROUP} mencapai kemandirian ekonomi "
        f"dan kondisi kehidupan yang lebih baik secara berkelanjutan."
    ),
    BULLET(_to_list(ic.get("target_outcomes", []))),
    H2("5.2 Tujuan Spesifik: Key Areas of Improvement"),
    P("Area perbaikan kunci yang menjadi fokus intervensi program:"),
]

for area in _to_list(ic.get("key_improvements")):
    b5.append(P(f"• {area}", ds="present_as_inferred", sr=["ideal_conditions"]))

b5 += [
    H2("5.3 Kesesuaian Masalah / Intervensi / Tujuan"),
    P(
        "Setiap hambatan yang diidentifikasi di Bab IV dijawab secara "
        "langsung oleh komponen program:"
    ),
]

# Value chain dari strategy_design
vc = sd.get("value_chain", "")
if vc:
    b5.append(P(f"Rantai nilai program: {vc}", ds="present_as_final", sr=["strategy_design"]))

# SDG alignment
sdg = pp.get("sdg_alignment", [])
if sdg:
    b5.append(INFO(
        f"Kondisi ideal program selaras dengan: {', '.join(sdg)}.",
        sr=["program_positioning"]
    ))

# ══════════════════════════════════════════════════════════
# BAB 6 — STRATEGI
# ══════════════════════════════════════════════════════════
print(f"Building Bab 6 — Strategi ({PROG_CODE})...")
b6 = []
b6 += [
    H1("BAB VI STRATEGI UNTUK MENCAPAI KONDISI IDEAL YANG DIHARAPKAN"),
    LEAD(
        f"Bab ini menyajikan desain strategis Program {PROG_NAME} — "
        f"mencakup filosofi program, roadmap, value chain, dan kelembagaan yang terbentuk."
    ),
    DIV(),
    H2("6.1 Nama dan Filosofi Program"),
    P(
        f"Program '{PROG_NAME}' ({PROG_CODE}) dirancang dengan filosofi: "
        f"{sd.get('program_philosophy','')} "
        f"Tagline program: \"{pi.get('program_tagline','')}\"."
    ),
    H2("6.2 Relevansi Program dengan Visi Misi Perusahaan dan Program Pemerintah"),
    P(
        f"Program ini selaras dengan pilar '{pp.get('tjsl_pillar','—')}' dan kategori "
        f"'{pp.get('proper_category','—')}' yang ditetapkan dalam regulasi PROPER. "
        f"Dasar kebijakan: {', '.join(pp.get('policy_basis',[])[:2])}."
    ),
    H2("6.3 Roadmap Program"),
    P(
        f"Program dirancang dalam {len(sd.get('roadmap',[]))} tahap "
        f"yang mencerminkan evolusi dari pembentukan kapasitas menuju stabilisasi:"
    ),
]

for stage in sd.get("roadmap", []):
    if isinstance(stage, dict):
        yr   = stage.get("year", stage.get("stage_id","—"))
        lbl  = stage.get("phase", stage.get("label",""))
        fcs  = stage.get("focus","")
        loop = stage.get("loop_type","")
        b6.append(H3(f"Tahap {yr}: {lbl}"))
        b6.append(P(
            f"Fokus: {fcs}. " + (f"Tipe pembelajaran: {loop}-loop learning." if loop else ""),
            ds="present_as_final", sr=["strategy_design"]
        ))

b6 += [
    H2("6.4 Value Chain"),
    P("Rantai nilai program mengalir secara sekuensial dari kapasitas teknis menuju dampak sosial:"),
    P(_to_str(sd.get("value_chain"),"—"), ds="present_as_final", sr=["strategy_design"]),
    H2("6.5 Kelembagaan"),
    P(
        f"Program membentuk dan menguatkan {len(nodes)} node kelembagaan "
        f"yang menjadi unit operasional program: {', '.join(nodes)}."
    ),
]

# Tabel node — dinamis dari canonical
if nodes:
    node_type_note = institutional.get("note","")
    rows_node = [[n, "Node aktif"] for n in nodes]
    b6.append(TBL_BL(
        ["Node", "Status"],
        rows_node,
        [4200, 5438],
        sr=["strategy_design"]
    ))

# Success callout dari evidence
if ev_success:
    b6.append(SUCCESS(
        f"{ev_success[0].get('description','')}",
        sr=[ev_success[0].get("evidence_id","")]
    ))

b6.append(METRIC3([
    {"label":"Node Program",       "value":str(len(nodes)), "sublabel":"total"},
    {"label":"Stakeholder Utama",  "value":str(len(canonical.get("stakeholders",[]))),"sublabel":"pihak"},
    {"label":"Aspek Monetisasi",   "value":str(len(asp_meta)), "sublabel":"aspek"},
]))

# Helper: normalize learning_signals loop (list or dict)
def _ls_to_list(val):
    if not val: return ["—"]
    if isinstance(val, list): return val if val else ["—"]
    if isinstance(val, dict):
        parts = []
        if val.get("signal"):     parts.append(val["signal"])
        if val.get("implication"):parts.append(val["implication"])
        if val.get("lesson"):     parts.append(val["lesson"])
        return parts if parts else ["—"]
    return [str(val)]

# ══════════════════════════════════════════════════════════
# BAB 8 — TRIPLE LOOP LEARNING
# ══════════════════════════════════════════════════════════
print(f"Building Bab 8 — Triple Loop Learning ({PROG_CODE})...")
b8 = []
b8 += [
    H1("BAB VIII ASPEK PEMBELAJARAN DENGAN TRIPLE LOOP LEARNING"),
    LEAD(
        "Bab ini menyajikan refleksi pembelajaran program melalui kerangka "
        "triple loop learning — menganalisis tidak hanya apa yang terjadi, "
        "tetapi juga mengapa program merespons seperti yang dilakukan, "
        "dan perubahan mendasar apa yang muncul dari proses implementasi."
    ),
    DIV(),
    H2("8.1 Identifikasi Masalah dan Keterkaitan LFA"),
    P(
        f"Selama implementasi {PERIOD_LABEL}, program menghadapi beberapa "
        "tantangan yang menjadi sumber pembelajaran:"
    ),
]

# LFA reflections
lfa_refs = ls.get("lfa_reflections", [])
if isinstance(lfa_refs, list):
    for ref in lfa_refs:
        if isinstance(ref, dict):
            b8.append(H3(f"Refleksi: {ref.get('activity_ref', ref.get('signal','')[:50] if ref.get('signal') else '')}"))
            gap = ref.get('lfa_gap', ref.get('signal',''))
            lesson = ref.get('lesson_learned', ref.get('implication',''))
            if gap:    b8.append(P(f"Temuan: {gap}",       ds="present_as_inferred", sr=["learning_signals"]))
            if lesson: b8.append(P(f"Implikasi: {lesson}", ds="present_as_inferred", sr=["learning_signals"]))
        elif isinstance(ref, str):
            b8.append(P(f"• {ref}", ds="present_as_inferred", sr=["learning_signals"]))

b8 += [
    H2("8.2 L1, L2, L3 — Analisis Triple Loop"),
    INFO(
        f"SROI blended program {PROG_CODE} adalah {ratio(sroi_val)}. "
        "Angka ini mencerminkan nilai sosial-ekonomi total setelah monetisasi outcome, "
        "compound ORI, dan penyesuaian DDAT per aspek diperhitungkan.",
        sr=["sroi_metrics.calculated","monetization","ddat_params"]
    ),
    H3("Loop 1 — Single Loop Learning (Apa yang terjadi?)"),
    P("Pembelajaran level pertama berfokus pada hasil langsung dari implementasi aktivitas:"),
    BULLET(_ls_to_list(ls.get("loop_1"))),
    H3("Loop 2 — Double Loop Learning (Mengapa respons itu dipilih?)"),
    P("Pembelajaran level kedua merefleksikan penyesuaian strategi berdasarkan temuan implementasi:"),
    BULLET(_ls_to_list(ls.get("loop_2"))),
    H3("Loop 3 — Triple Loop Learning (Apa yang berubah secara fundamental?)"),
    P("Pembelajaran level ketiga menandai transformasi nilai dan asumsi mendasar:"),
    BULLET(_ls_to_list(ls.get("loop_3"))),
    WARN(
        "Analisis triple loop di atas bersumber dari learning signals yang tersedia. "
        "Untuk laporan final, refleksi ini perlu diperkaya dengan wawancara mendalam.",
        sr=["learning_signals"]
    ),
    H2("8.3 Identifikasi Keunikan Program"),
    P("Program memiliki karakteristik unik yang membedakannya dari program konvensional:"),
    BULLET([
        f"Sasaran spesifik: {TARGET_GROUP}",
        f"Model CSV (Creating Shared Value): {sd.get('program_philosophy','')}",
        f"Cakupan {len(nodes)} node yang tersebar secara nasional",
        f"Monetisasi {len(asp_meta)} aspek nilai ({len(observed_asps)} observed, {len(proxy_asps)} proxy)",
    ]),
    H2("8.4 Kontribusi Efisiensi, Efektivitas, dan Keberlanjutan Sosial"),
    P(
        f"Dari sisi efisiensi, program menghasilkan SROI blended "
        f"{ratio(sroi_val)} — setiap Rp 1 investasi menghasilkan nilai sosial Rp {sroi_val:.2f}. "
        f"Dari sisi efektivitas, program mencakup {len(nodes)} node aktif "
        f"selama {PERIOD_LABEL}.",
        ds="present_as_final",
        sr=["sroi_metrics.calculated","strategy_design"]
    ),
]

# ══════════════════════════════════════════════════════════
# BAB 9 — PENUTUP
# ══════════════════════════════════════════════════════════
print(f"Building Bab 9 — Penutup ({PROG_CODE})...")
b9 = []

# Temuan utama dari outline bab7 atau uncertainty_flags
high_flags_desc = [f.get("description","") for f in high_flags[:3]]

b9 += [
    H1("BAB IX PENUTUP"),
    DIV(),
    H2("9.1 Kesimpulan"),
    LEAD(
        f"Program {PROG_NAME} ({PROG_CODE}) terbukti menghasilkan nilai sosial-ekonomi "
        f"yang melampaui investasi, dengan SROI blended "
        f"{ratio(sroi_val)} selama periode {PERIOD_LABEL}."
    ),
    P(
        f"Dari total investasi {idr(A('total_investment'))}, program menghasilkan "
        f"net benefit compounded sebesar {idr(A('total_net_compounded'))} — "
        f"mencerminkan positive return yang konsisten di seluruh tahun evaluasi.",
        ds="present_as_final",
        sr=["sroi_metrics.calculated"]
    ),
    METRIC3([
        {"label":"SROI Blended",          "value":ratio(sroi_val),              "sublabel":PERIOD_LABEL},
        {"label":"Total Investasi",        "value":idr(A("total_investment")),   "sublabel":"kumulatif"},
        {"label":"Net Benefit Compounded", "value":idr(A("total_net_compounded")),"sublabel":"terminal year"},
    ]),
    H2("9.2 Temuan Utama"),
]

# Temuan dari high_flags + learning signals
if high_flags_desc:
    for i, desc in enumerate(high_flags_desc, 1):
        b9.append(P(f"({i}) {desc}"))
else:
    b9.append(P(
        f"Program {PROG_CODE} berhasil mendokumentasikan seluruh aspek nilai "
        f"dengan tingkat kepercayaan yang memadai selama {PERIOD_LABEL}."
    ))

b9 += [
    H2("9.3 Rekomendasi / Usulan Tindak Lanjut"),
]

# Rekomendasi dari learning_signals loop_2 atau flags
recos = []
for flag in high_flags:
    recos.append(
        f"Tindak lanjuti: {flag.get('field','—')} — {flag.get('description','')}"
    )
for item in _ls_to_list(ls.get("loop_2"))[:3]:
    if item != "—": recos.append(item)

if recos:
    b9.append(NUMBERED(recos[:5]))
else:
    b9.append(GAP("Rekomendasi spesifik belum tersedia dalam canonical JSON — perlu dilengkapi dari hasil evaluasi lapangan.","data_unavailable"))

b9.append(SMALL(
    f"Laporan ini disusun berdasarkan data yang tersedia per {pi.get('period_end','2025')} "
    f"dan mencerminkan status evaluatif. Angka investasi berstatus "
    f"{'under_confirmation dan perlu diverifikasi dari dokumen keuangan resmi' if has_pending else 'final'}."
))

# ══════════════════════════════════════════════════════════
# COMPOSE & WRITE
# ══════════════════════════════════════════════════════════
chapters = [
    chapter_semantic("bab_1","pendahuluan",   "framing",  b1),
    chapter_semantic("bab_2","profil",        "framing",  b2),
    chapter_semantic("bab_3","metodologi",    "framing",  b3),
    chapter_semantic("bab_4","kondisi_awal",  "context",  b4),
    chapter_semantic("bab_5","kondisi_ideal", "context",  b5),
    chapter_semantic("bab_6","strategi",      "context",  b6),
    chapter_semantic("bab_8","learning",      "learning", b8),
    chapter_semantic("bab_9","penutup",       "learning", b9),
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)



all_chapters = []
for ch in chapters:
    cid  = ch["chapter_id"]
    path = OUTPUT_DIR / f"chapter_semantic_{cid}.json"
    json.dump([ch], open(path,"w"), indent=2, ensure_ascii=False)
    all_chapters.append(ch)
    print(f"  {cid}: {len(ch['blocks'])} blocks → {path.name}")

all_path = OUTPUT_DIR / "chapters_semantic_rest.json"
json.dump(all_chapters, open(all_path,"w"), indent=2, ensure_ascii=False)

print(f"\nGabungan: {all_path.name} ({len(all_chapters)} bab)")
print("\n" + "="*55)
print(f"NARRATIVE BUILDER REST — {PROG_CODE} — selesai")
total_blocks = sum(len(c["blocks"]) for c in all_chapters)
print(f"  Bab dihasilkan : {len(all_chapters)}")
print(f"  Total blocks   : {total_blocks}")
for ch in all_chapters:
    print(f"    {ch['chapter_id']}: {len(ch['blocks'])} blocks ({ch['builder_mode']})")
print("="*55)
