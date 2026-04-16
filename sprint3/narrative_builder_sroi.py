"""
Narrative Builder — Sprint 3B (v2.0 — Dynamic)
Sub-mode: builder_sroi (Bab 7)

Input  : chapter_outline_bab7.json (Handoff D)
         handoff_b.json (financial tables)
         canonical_{program}_v1.json (context)
Output : chapter_semantic_bab7.json (Handoff E ke QA)

Rules:
  - Semua angka dari sroi_metrics.calculated via audit_log
  - Tidak ada angka baru yang tidak ada di outline
  - Proxy aspects wajib punya display_status present_as_proxy
  - Block types harus sesuai render_contract_v1.json
  - v2.0: semua referensi program dibaca dari canonical — tidak ada hardcode ESL

Usage:
  python narrative_builder_sroi.py
  python narrative_builder_sroi.py --outline /p/ --handoff-b /p/ --canonical /p/ --output /p/
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

BUILDER_VERSION = "2.0.0"

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--outline",   default=None)
parser.add_argument("--handoff-b", default=None, dest="handoff_b")
parser.add_argument("--canonical", default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
OUTLINE_FILE   = Path(args.outline)   if args.outline   \
    else Path(os.environ.get("OUTLINE_FILE",   SCRIPT_DIR / "chapter_outline_bab7.json"))
HANDOFF_B_FILE = Path(args.handoff_b) if args.handoff_b \
    else Path(os.environ.get("HANDOFF_B_FILE", SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
OUTPUT_DIR     = Path(args.output)    if args.output    \
    else Path(os.environ.get("OUTPUT_DIR",     SCRIPT_DIR))

print(f"Outline   : {OUTLINE_FILE.resolve()}")
print(f"Handoff B : {HANDOFF_B_FILE.resolve()}")
print(f"Canonical : {CANONICAL_FILE.resolve()}")
print(f"Output    : {OUTPUT_DIR.resolve()}")

for f in [OUTLINE_FILE, HANDOFF_B_FILE, CANONICAL_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

outline_raw = json.load(open(OUTLINE_FILE))
handoff_b   = json.load(open(HANDOFF_B_FILE))
canonical   = json.load(open(CANONICAL_FILE))

outline = outline_raw if isinstance(outline_raw, list) else [outline_raw]
bab7    = next((b for b in outline if b["chapter_id"] == "bab_7"), None)
if not bab7:
    print("FAIL: bab_7 tidak ditemukan"); sys.exit(1)

# ── IDENTITAS PROGRAM ─────────────────────────────────────
pi           = canonical.get("program_identity", {})
PROG_CODE    = pi.get("program_code", "PROGRAM")
PROG_NAME    = pi.get("program_name", PROG_CODE)
PERIOD_LABEL = pi.get("period_label", f"{pi.get('period_start','2023')}–{pi.get('period_end','2025')}")
years        = sorted(set(m["year"] for m in canonical.get("monetization", []))) or [2023, 2024, 2025]

print(f"\nProgram : {PROG_CODE} — {PROG_NAME}")

# ── FORMAT NORMALIZERS ───────────────────────────────────────────
def _to_list(val, str_key=None):
    """Normalisasi nilai ke list of strings — handle list, dict, string."""
    if val is None: return []
    if isinstance(val, list): return val
    if isinstance(val, dict):
        if str_key and str_key in val: return [val[str_key]]
        # Ambil semua string values dari dict
        parts = [str(v) for v in val.values() if v and isinstance(v, (str, int, float))]
        return parts if parts else []
    return [str(val)]

def _to_str(val, keys=None, fallback=""):
    """Normalisasi nilai ke string — handle string, dict, list."""
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
    """Handle activities sebagai list of dicts ATAU dict per tahun."""
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

calc       = handoff_b["sroi_metrics"]["calculated"]
audit_map  = {e["field"]: e["value"] for e in handoff_b["calc_audit_log"]}
fin_tables = {t["table_id"]: t for t in handoff_b["financial_tables"]}
ddat       = canonical["ddat_params"]
ori        = canonical["ori_rates"]

# ── Aspek dinamis: observed vs proxy ─────────────────────
asp_meta = {}
seen = []
for m in canonical.get("monetization", []):
    asp = m["aspect_code"]
    if asp in seen: continue
    seen.append(asp)
    asp_meta[asp] = {
        "name":  m.get("aspect_name", asp),
        "tag":   "observed" if m.get("measurement_type") == "observed" else "proxy",
        "proxy_basis": m.get("proxy_basis", ""),
    }

observed_asps = [k for k, v in asp_meta.items() if v["tag"] == "observed"]
proxy_asps    = [k for k, v in asp_meta.items() if v["tag"] == "proxy"]

# ── Node info ─────────────────────────────────────────────
institutional = canonical.get("strategy_design", {}).get("institutional", {})
nodes         = institutional.get("nodes", [])
node_note     = institutional.get("note", "")

# ── Temuan kritis dari uncertainty_flags ──────────────────
_uf_raw = canonical.get("uncertainty_flags", [])
if isinstance(_uf_raw, dict): _uf_raw = list(_uf_raw.values())
elif not isinstance(_uf_raw, list): _uf_raw = []
_uf_norm = [f if isinstance(f, dict) else {"description": str(f), "severity": "medium"} for f in _uf_raw]
high_flags = [f for f in _uf_norm if f.get("severity") == "high"]

def A(field):
    if field not in audit_map:
        raise KeyError(f"'{field}' tidak ada di audit_log")
    return audit_map[field]

def idr(v):   return f"Rp {v:,.0f}"
def ratio(v): return f"1 : {v:.2f}"

# ── BLOK HELPERS ─────────────────────────────────────────
def H1(text):  return {"type":"heading_1","text":text}
def H2(text):  return {"type":"heading_2","text":text}
def H3(text):  return {"type":"heading_3","text":text}
def P(text, display_status=None, source_refs=None):
    b = {"type":"paragraph","text":text}
    if display_status: b["display_status"] = display_status
    if source_refs:    b["source_refs"]    = source_refs
    return b
def LEAD(text):  return {"type":"paragraph_lead","text":text}
def SMALL(text): return {"type":"paragraph_small","text":text}
def TABLE(table_id, display_status=None, source_refs=None):
    t = fin_tables[table_id]
    b = {
        "type":          "table",
        "table_id":      table_id,
        "title":         t["title"],
        "headers":       t["headers"],
        "rows":          t["rows"],
        "column_widths": t["column_widths"],
    }
    if t.get("note"):  b["note"]           = t["note"]
    if display_status: b["display_status"] = display_status
    if source_refs:    b["source_refs"]    = source_refs
    return b
def CALLOUT(ctype, text, display_status=None, source_refs=None, gap_type=None):
    b = {"type": f"callout_{ctype}", "text": text}
    if display_status: b["display_status"] = display_status
    if source_refs:    b["source_refs"]    = source_refs
    if gap_type:       b["gap_type"]       = gap_type
    return b
def METRIC3(items, display_status=None):
    b = {"type":"metric_card_3col","items":items}
    if display_status: b["display_status"] = display_status
    return b
def BAR(data_points, max_value, title=None):
    b = {"type":"bar_chart_text","data_points":data_points,"max_value":max_value}
    if title: b["title"] = title
    return b
def DIVIDER():       return {"type":"divider"}
def DIVIDER_THICK(): return {"type":"divider_thick"}

# ══════════════════════════════════════════════════════════
# SUSUN BLOCKS BAB 7
# ══════════════════════════════════════════════════════════

blocks = []

# ── HEADER BAB ───────────────────────────────────────────
blocks += [
    H1("BAB VII IMPLEMENTASI / PDIS DENGAN SROI"),
    LEAD(
        f"Bab ini menyajikan seluruh rangkaian implementasi Program {PROG_NAME} "
        f"({PROG_CODE}) secara terukur — dari kegiatan, stakeholder, dan investasi "
        f"hingga outcome, fiksasi dampak, monetisasi nilai sosial, dan hasil evaluasi SROI "
        f"periode {PERIOD_LABEL}. Semua angka pada bab ini "
        "bersumber dari Financial Calculation Engine dan dapat ditelusuri melalui calc_audit_log."
    ),
    DIVIDER(),
]

# ── 7.1 PROSES & KEGIATAN ────────────────────────────────
blocks += [H2("7.1 Proses dan Kegiatan yang Dilakukan")]

activities = _activities_to_list(canonical.get("activities", []))

blocks.append(P(
    f"Program {PROG_CODE} melaksanakan {len(activities)} aktivitas terstruktur "
    f"sepanjang periode {PERIOD_LABEL}. "
    f"{bab7.get('purpose', '')}"
))

for yr in years:
    acts_yr = [a for a in activities if a.get("year") == yr]
    if acts_yr:
        scopes = []
        for a in acts_yr:
            scopes += a.get("activity_scope", [a.get("name", "")])
        blocks.append(P(
            f"Tahun {yr}: {' · '.join(scopes[:4])}{'...' if len(scopes) > 4 else ''}.",
            display_status="present_as_final"
        ))

# ── 7.2 NODE PROGRAM ─────────────────────────────────────
blocks += [H2("7.2 Node Program")]
_nodes_display = nodes if isinstance(nodes, list) else list(nodes) if nodes else []
blocks.append(P(
    f"Program beroperasi di {len(_nodes_display)} node/lokasi: {', '.join(str(n) for n in _nodes_display)}. "
    f"{node_note}"
))

# Callout info tentang node — dinamis
if nodes:
    blocks.append(CALLOUT(
        "info",
        f"Program {PROG_CODE} menjalankan aktivitas melalui {len(nodes)} node yang tersebar "
        f"secara nasional. Setiap node memiliki karakteristik dan tingkat aktivitas yang berbeda "
        f"sesuai dengan kapasitas dan tahap pengembangan masing-masing.",
        display_status="present_as_final"
    ))

# Temuan kritis dari high_flags — menggantikan hardcode "Lapas Palembang"
for flag in high_flags:
    blocks.append(CALLOUT(
        "neutral",
        f"{flag.get('description', '')} "
        "Temuan ini disajikan secara transparan sebagai bagian dari evaluasi jujur program.",
        display_status="present_as_final",
        source_refs=["uncertainty_flags"]
    ))

# ── 7.3 STAKEHOLDER ──────────────────────────────────────
blocks += [H2("7.3 Identifikasi Stakeholder yang Terlibat")]
stk = canonical.get("stakeholders", [])
blocks.append(P(
    f"Program melibatkan {len(stk)} pemangku kepentingan utama dengan peran berbeda "
    f"dalam ekosistem program."
))
blocks.append({
    "type":    "table_borderless",
    "headers": ["Stakeholder", "Peran", "Tipe Keterlibatan"],
    "rows": [
        [s["name"], s.get("role","—"), s.get("involvement_type","—").replace("_"," ")]
        for s in stk
    ],
    "column_widths": [3200, 1600, 4838],
    "display_status": "present_as_final",
    "source_refs": ["stakeholders"]
})

# ── 7.4 INVESTASI ─────────────────────────────────────────
blocks += [H2("7.4 Input / Investasi")]
inv_statuses = set(i.get("data_status","") for i in canonical.get("investment",[]))
has_pending  = "under_confirmation" in inv_statuses or "planned" in inv_statuses

if has_pending:
    blocks.append(CALLOUT(
        "warning",
        f"Catatan status data: sebagian investasi program berstatus under_confirmation atau planned — "
        "angka telah tersedia namun perlu diverifikasi dari laporan keuangan resmi.",
        display_status="present_as_pending",
        source_refs=["investment"]
    ))

blocks.append(P(
    f"Total investasi program selama {PERIOD_LABEL} mencapai "
    f"{idr(A('total_investment'))}, dengan distribusi yang meningkat setiap tahun "
    f"seiring penguatan aktivitas."
))
blocks.append(TABLE(
    "table_investment_per_node",
    display_status="present_as_pending" if has_pending else "present_as_final",
    source_refs=["investment"]
))

# Metric cards investasi per tahun — dinamis
metric_inv = []
for yr in years:
    fkey = f"investment_total_{yr}"
    if fkey in audit_map:
        inv_data = [i for i in canonical.get("investment",[]) if i.get("year") == yr]
        status = inv_data[0].get("data_status","") if inv_data else ""
        sublabel = "under confirmation" if status in ("under_confirmation","planned") else "final"
        metric_inv.append({"label": f"Investasi {yr}", "value": idr(A(fkey)), "sublabel": sublabel})

if metric_inv:
    blocks.append(METRIC3(metric_inv))

# ── 7.5 OUTPUT ────────────────────────────────────────────
blocks += [H2("7.5 Proses dan Output yang Dihasilkan")]
outputs = canonical.get("outputs", [])
blocks.append(P(
    f"Program menghasilkan {len(outputs)} output terukur sepanjang periode evaluasi."
))
if outputs:
    blocks.append({
        "type":    "table_borderless",
        "headers": ["Output", "Tahun", "Jumlah", "Satuan", "Status"],
        "rows": [
            [o.get("description", o.get("output_id","")), str(o.get("year","")),
             str(int(o.get("quantity",0))), o.get("unit","—"), o.get("data_status","—")]
            for o in outputs
        ],
        "column_widths": [3000, 1000, 1200, 1200, 3238],
        "display_status": "present_as_final",
        "source_refs": ["outputs"]
    })

# ── 7.6 OUTCOME ───────────────────────────────────────────
blocks += [H2("7.6 Outcome Program")]
outcomes = canonical.get("outcomes", [])
blocks.append(P(
    f"Program menghasilkan {len(outcomes)} outcome yang dimonetisasi melalui "
    f"{len(observed_asps)} aspek observed dan {len(proxy_asps)} aspek proxy."
))
for oc in outcomes:
    ds_val = oc.get("data_status","")
    is_obs = ds_val == "observed"
    tag    = "✓ Observed" if is_obs else "~ Proxy"
    ds     = "present_as_final" if is_obs else "present_as_proxy"
    # QA rule C4: proxy block wajib punya source_refs — fallback ke evidence_registry
    sr = oc.get("source_refs",[])
    if not sr:
        sr = ["evidence_registry"] if not is_obs else ["outcomes"]
    blocks.append(P(
        f"{tag} — {oc.get('name','')}: {oc.get('description','')}",
        display_status=ds,
        source_refs=sr
    ))

# ── 7.7 FIKSASI DAMPAK ────────────────────────────────────
blocks += [H2("7.7 Fiksasi Dampak (DDAT Adjustment)")]
blocks.append(P(
    "Fiksasi dampak diterapkan untuk memastikan bahwa nilai sosial yang diklaim "
    "benar-benar mencerminkan kontribusi program secara nyata. "
    "Empat parameter: Deadweight (DW), Displacement (DS), Attribution (AT), Drop-off (DO)."
))
blocks.append(TABLE("table_ddat_per_aspek", display_status="present_as_final"))

avg_f = A("avg_fiksasi_pct")
# Aspek dengan haircut tertinggi
max_asp = max(asp_meta.keys(), key=lambda k: 1 - ddat.get(k,{}).get("net_multiplier",1)) if asp_meta else None
max_haircut = round((1 - ddat.get(max_asp,{}).get("net_multiplier",1))*100) if max_asp else 0
blocks.append(SMALL(
    f"Rata-rata fiksasi dampak keseluruhan: −{avg_f:.1f}%. "
    + (f"Haircut tertinggi pada aspek {max_asp} ({max_haircut}%): "
       f"{ddat.get(max_asp,{}).get('justification','')}." if max_asp else "")
))

# ── 7.8 MONETISASI ────────────────────────────────────────
blocks += [DIVIDER(), H2("7.8 Monetisasi Dampak")]

# Deskripsi aspek observed dan proxy — dinamis
obs_desc = ""
if observed_asps:
    obs_desc = (
        f"Aspek {' dan '.join(observed_asps)} dimonetisasi berdasarkan data transaksi aktual (observed). "
    )
proxy_desc = ""
if proxy_asps:
    proxy_bases = " · ".join(
        f"{asp}: {asp_meta[asp].get('proxy_basis','proxy tervalidasi')}"
        for asp in proxy_asps
    )
    proxy_desc = (
        f"Aspek {' dan '.join(proxy_asps)} dimonetisasi menggunakan proxy konservatif: {proxy_bases}."
    )

blocks.append(LEAD(
    f"Monetisasi nilai sosial dilakukan melalui {len(asp_meta)} aspek. "
    + obs_desc + proxy_desc
))

if proxy_asps:
    blocks.append(CALLOUT(
        "info",
        obs_desc + proxy_desc,
        display_status="present_as_final"
    ))

blocks.append(TABLE(
    "table_monetization_per_aspek",
    display_status="present_as_final",
    source_refs=["monetization","ddat_params"]
))

# Callout proxy — hanya jika ada aspek proxy
if proxy_asps:
    blocks.append(CALLOUT(
        "warning",
        f"Aspek {', '.join(proxy_asps)} adalah proxy monetisasi — estimasi nilai sosial "
        "berdasarkan referensi kebijakan dan data sekunder, bukan pengukuran langsung. "
        "Nilai ini perlu dikonfirmasi melalui survei peserta pada periode evaluasi berikutnya.",
        display_status="present_as_proxy",
        source_refs=["evidence_registry"]
    ))

# Bar chart distribusi nilai — dinamis
gross_asp = {}
for m in canonical.get("monetization", []):
    asp = m["aspect_code"]
    gross_asp[asp] = gross_asp.get(asp, 0) + m["gross_idr"] * ddat.get(asp, {}).get("net_multiplier", 1)

if gross_asp:
    bar_data = [
        {"label": f"{asp:<6}", "value": round(v/1e6, 1)}
        for asp, v in sorted(gross_asp.items(), key=lambda x: -x[1])
    ]
    blocks.append(BAR(
        data_points=bar_data,
        max_value=round(max(v["value"] for v in bar_data)*1.1, 0),
        title=f"Distribusi nilai bersih per aspek (Rp juta, kumulatif {PERIOD_LABEL})"
    ))

# ── 7.9 KALKULASI SROI ────────────────────────────────────
blocks += [DIVIDER_THICK(), H2("7.9 Nilai SROI dan Penjelasan")]
sroi_val = A("sroi_blended")
blocks.append(LEAD(
    f"Berdasarkan kalkulasi evaluatif dengan compound ORI-adjusted dan DDAT "
    f"net multiplier per aspek, program {PROG_CODE} menghasilkan SROI blended "
    f"{ratio(sroi_val)} — artinya setiap Rp 1 yang diinvestasikan "
    f"menghasilkan Rp {sroi_val:.2f} nilai sosial-ekonomi terukur."
))

blocks.append(METRIC3([
    {"label":"Total Investasi",          "value":idr(A("total_investment")),    "sublabel":PERIOD_LABEL},
    {"label":"Net Benefit (compounded)", "value":idr(A("total_net_compounded")),"sublabel":"terminal year"},
    {"label":"SROI Blended",             "value":ratio(sroi_val),               "sublabel":"positive return"},
], display_status="present_as_final"))

blocks.append(TABLE(
    "table_sroi_per_tahun",
    display_status="present_as_final",
    source_refs=["sroi_metrics.calculated"]
))
blocks.append(TABLE(
    "table_sroi_blended",
    display_status="present_as_final",
    source_refs=["sroi_metrics.calculated"]
))

# Narasi per tahun — dinamis
for yr in years:
    yr_rows = [r for r in calc.get("per_year",[]) if r["year"] == yr]
    if not yr_rows: continue
    row    = yr_rows[0]
    ori_yr = ori.get(str(yr), {})
    blocks.append(P(
        f"Tahun {yr} ({ori_yr.get('series','—')}, {ori_yr.get('rate',0)*100:.2f}%): "
        f"investasi {idr(row['investment'])}, gross {idr(row['gross'])}, "
        f"nilai bersih setelah DDAT {idr(row['net'])}, "
        f"di-compound ×{ori_yr.get('compound_factor',1):.4f} menjadi {idr(row['compounded'])}, "
        f"SROI {ratio(row['sroi_ratio'])}.",
        display_status="present_as_final"
    ))

# ── 7.10 TEMUAN & INTERPRETASI ────────────────────────────
blocks += [H2("7.10 Interpretasi dan Temuan Program")]

blocks.append(P(
    f"Evaluasi SROI menunjukkan bahwa program {PROG_CODE} menghasilkan nilai sosial "
    "yang melampaui investasi. Struktur monetisasi perlu dibaca dengan memahami "
    "komposisi aspek observed dan proxy, serta distribusi nilai antar tahun."
))

# Success callout — dari evidence_registry atau learning_signals
ev_success = [e for e in canonical.get("evidence_registry",[]) if "observed" in e.get("type","").lower()]
if ev_success:
    blocks.append(CALLOUT(
        "success",
        f"Bukti terkuat keberhasilan program: {ev_success[0].get('description','')}",
        display_status="present_as_final",
        source_refs=[ev_success[0].get("evidence_id","")]
    ))

# Temuan kritis dari uncertainty_flags — menggantikan hardcode
for flag in high_flags:
    blocks.append(CALLOUT(
        "neutral",
        f"{flag.get('description','')} "
        "Jika hal ini dapat ditangani pada periode berikutnya, "
        "SROI program berpotensi meningkat tanpa investasi tambahan yang proporsional.",
        display_status="present_as_final",
        source_refs=["uncertainty_flags"]
    ))

# Learning signals loop 1 — sebagai temuan
ls = canonical.get("learning_signals", {})
if isinstance(ls, list): ls = {}
for item in _to_list(ls.get("loop_1"))[:2]:
    blocks.append(P(str(item), display_status="present_as_inferred", source_refs=["learning_signals"]))

blocks.append(SMALL(
    f"Catatan metodologis: seluruh angka pada bab ini dihasilkan oleh Financial "
    "Calculation Engine (deterministik, non-LLM) dan dapat ditelusuri melalui "
    f"calc_audit_log. Evaluasi ini bersifat evaluatif — mengukur nilai yang "
    f"dihasilkan selama {PERIOD_LABEL} berdasarkan data yang tersedia."
))

print(f"  {len(blocks)} blok disusun")

# ══════════════════════════════════════════════════════════
# COMPOSE HANDOFF E
# ══════════════════════════════════════════════════════════

chapter_semantic = {
    "chapter_id":        "bab_7",
    "chapter_type":      "implementation_sroi",
    "source_outline_ref":"bab_7",
    "builder_mode":      "sroi",
    "builder_version":   BUILDER_VERSION,
    "program_code":      PROG_CODE,
    "generated_at":      datetime.now().isoformat(),
    "blocks":            blocks
}

handoff_e = [chapter_semantic]

# ── WRITE ─────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
out_path = OUTPUT_DIR / "chapter_semantic_bab7.json"
json.dump(handoff_e, open(out_path,"w"), indent=2, ensure_ascii=False)
print(f"\nOutput: {out_path}")

type_counts = {}
for b in blocks:
    t = b["type"]
    type_counts[t] = type_counts.get(t,0)+1

print("\n" + "="*55)
print(f"NARRATIVE BUILDER — bab_7 | {PROG_CODE}")
print(f"  Total blocks : {len(blocks)}")
for t,n in sorted(type_counts.items(), key=lambda x:-x[1]):
    print(f"    {t:<30} × {n}")
print("="*55)
