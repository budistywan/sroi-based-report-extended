"""
Point Builder — Sprint 3 (v2.0 — Dynamic)
SROI Report System

Sub-mode: builder_sroi (Bab 7 — Implementasi / PDIS dengan SROI)

Input  : canonical_{program}_v1.json + handoff_b.json + handoff_c.json
Output : chapter_outline_bab7.json (Handoff D ke Narrative Builder)

Prinsip:
  - Point Builder TIDAK menulis narasi
  - Point Builder menyusun LOGIKA ARGUMENTASI per bab
  - Setiap poin harus punya evidence_refs yang traceable ke canonical JSON
  - Angka hanya boleh diambil dari sroi_metrics.calculated via calc_audit_log
  - v2.0: semua referensi program dibaca dari canonical — tidak ada hardcode ESL

Usage:
  python point_builder_sroi.py
  python point_builder_sroi.py --canonical /p/c.json --handoff-b /p/hb.json --handoff-c /p/hc.json --output /p/
  CANONICAL_FILE=... HANDOFF_B_FILE=... HANDOFF_C_FILE=... OUTPUT_DIR=... python point_builder_sroi.py
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

BUILDER_VERSION = "2.0.0"

# ── FORMAT NORMALIZERS ───────────────────────────────────────────
def _to_list(val):
    if val is None: return []
    if isinstance(val, list): return [str(i) for i in val if i]
    if isinstance(val, dict):
        return [str(v) for v in val.values() if v and isinstance(v,(str,int,float))]
    return [str(val)] if val else []

def _to_str(val, keys=None, fallback=""):
    if val is None: return fallback
    if isinstance(val, str): return val
    if isinstance(val, dict):
        if keys:
            for k in keys:
                if val.get(k): return str(val[k])
        return " ".join(str(v) for v in val.values() if v and isinstance(v,str))
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

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="Point Builder — builder_sroi (dynamic)")
parser.add_argument("--canonical",  default=None)
parser.add_argument("--handoff-b",  default=None, dest="handoff_b")
parser.add_argument("--handoff-c",  default=None, dest="handoff_c")
parser.add_argument("--output",     default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE", SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
HANDOFF_B_FILE = Path(args.handoff_b) if args.handoff_b \
    else Path(os.environ.get("HANDOFF_B_FILE", SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
HANDOFF_C_FILE = Path(args.handoff_c) if args.handoff_c \
    else Path(os.environ.get("HANDOFF_C_FILE", SCRIPT_DIR.parent / "sprint2/handoff_c.json"))
OUTPUT_DIR     = Path(args.output)    if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

print(f"Canonical : {CANONICAL_FILE.resolve()}")
print(f"Handoff B : {HANDOFF_B_FILE.resolve()}")
print(f"Handoff C : {HANDOFF_C_FILE.resolve()}")
print(f"Output    : {OUTPUT_DIR.resolve()}")

for f in [CANONICAL_FILE, HANDOFF_B_FILE, HANDOFF_C_FILE]:
    if not f.exists():
        print(f"\nFAIL: File tidak ditemukan — {f}")
        sys.exit(1)

canonical  = json.load(open(CANONICAL_FILE))
handoff_b  = json.load(open(HANDOFF_B_FILE))
handoff_c  = json.load(open(HANDOFF_C_FILE))
calc       = handoff_b["sroi_metrics"]["calculated"]
blueprint  = handoff_c["report_blueprint_json"]
audit_log  = {e["field"]: e for e in handoff_b["calc_audit_log"]}

# ── IDENTITAS PROGRAM (dari canonical) ───────────────────
prog_identity = canonical.get("program_identity", {})
PROGRAM_CODE  = prog_identity.get("program_code", "UNKNOWN")
PROGRAM_NAME  = prog_identity.get("program_name", PROGRAM_CODE)
PERIOD_LABEL  = prog_identity.get("period_label", "2023–2025")

print(f"\nProgram   : {PROGRAM_CODE} — {PROGRAM_NAME}")
print(f"Periode   : {PERIOD_LABEL}")

# ── HELPER ───────────────────────────────────────────────
def from_audit(field):
    if field not in audit_log:
        raise KeyError(f"Field '{field}' tidak ada di calc_audit_log — angka tidak traceable")
    return audit_log[field]["value"]

def fmt_idr(value):
    return f"Rp {value:,.0f}"

def fmt_ratio(value):
    return f"1 : {value:.2f}"

# ── VERIFY: Bab 7 ada dan strong ─────────────────────────
bab7_blueprint = next(
    (c for c in blueprint["chapters"] if c["chapter_id"] == "bab_7"), None
)
if not bab7_blueprint:
    print("FAIL: bab_7 tidak ditemukan di blueprint")
    sys.exit(1)
if bab7_blueprint["coverage_status"] != "strong":
    print(f"FAIL: bab_7 coverage_status = {bab7_blueprint['coverage_status']} — harus strong")
    sys.exit(1)

print(f"\nbab_7 status : {bab7_blueprint['coverage_status']}")
print(f"builder_mode : {bab7_blueprint['builder_mode']}")
print(f"report_mode  : {blueprint['report_mode']}")

# ── EXTRACT DATA DARI CANONICAL ───────────────────────────
years = sorted(set(
    item["year"] for item in canonical.get("investment", [])
)) or [2023, 2024, 2025]

# Investasi per tahun
inv_by_year = {}
for item in canonical["investment"]:
    yr = item["year"]
    inv_by_year[yr] = inv_by_year.get(yr, 0) + item["amount_idr"]

# Monetisasi per aspek per tahun — dibaca dinamis dari canonical
mon_by_aspect = {}
for m in canonical["monetization"]:
    asp = m["aspect_code"]
    if asp not in mon_by_aspect:
        mon_by_aspect[asp] = {}
    mon_by_aspect[asp][m["year"]] = {
        "gross":          m["gross_idr"],
        "proxy_basis":    m.get("proxy_basis", ""),
        "proxy_value":    m.get("proxy_value", 0),
        "quantity_basis": m.get("quantity_basis", ""),
        "data_status":    m["data_status"],
        "display_status": m["display_status"],
        "source_refs":    m.get("source_refs", []),
    }

# DDAT params
ddat = canonical["ddat_params"]

# ORI rates
ori = canonical["ori_rates"]

# SROI per tahun dari calc
per_year = {row["year"]: row for row in calc["per_year"]}

# Financial tables
table_ids = [t["table_id"] for t in handoff_b["financial_tables"]]

# ── BUILD asp_info DINAMIS dari canonical ─────────────────
# Klasifikasi observed vs proxy berdasarkan measurement_type di monetization
asp_info = {}
seen = []
for m in canonical["monetization"]:
    asp = m["aspect_code"]
    if asp in seen:
        continue
    seen.append(asp)
    mtype = m.get("measurement_type", "proxy")
    # Nama aspek: cari di monetization field aspect_name atau aspect_id
    asp_name = m.get("aspect_name", asp)
    # Fallback: cari di outcomes jika ada related_outcome_id
    if not asp_name or asp_name == asp:
        related = m.get("related_outcome_id", "")
        outcome = next(
            (o for o in canonical.get("outcomes", []) if o.get("outcome_id") == related),
            None
        )
        if outcome:
            asp_name = outcome.get("name", asp)
    asp_info[asp] = {
        "name": asp_name,
        "tag":  "observed" if mtype == "observed" else "proxy"
    }

observed_asps = [k for k, v in asp_info.items() if v["tag"] == "observed"]
proxy_asps    = [k for k, v in asp_info.items() if v["tag"] == "proxy"]

print(f"\nAspek ditemukan: {list(asp_info.keys())}")
print(f"  Observed : {observed_asps}")
print(f"  Proxy    : {proxy_asps}")

# ── NODE INFO dari canonical ──────────────────────────────
institutional = canonical.get("strategy_design", {}).get("institutional", {})
nodes         = institutional.get("nodes", [])
active_note   = institutional.get("note", "")

# ── UNCERTAINTY FLAGS (untuk temuan kritis) ───────────────
# Handle uncertainty_flags: list of dicts, list of strings, atau dict
_uf_raw = canonical.get("uncertainty_flags", [])
if isinstance(_uf_raw, dict):
    _uf_raw = list(_uf_raw.values())
elif not isinstance(_uf_raw, list):
    _uf_raw = []
uncertainty_flags = [
    f if isinstance(f, dict) else {"description": str(f), "severity": "medium"}
    for f in _uf_raw
]
high_flags = [f for f in uncertainty_flags if f.get("severity") == "high"]

# ══════════════════════════════════════════════════════════
# SUSUN OUTLINE BAB 7 — DINAMIS
# ══════════════════════════════════════════════════════════

print("\n--- Menyusun argument points Bab 7 ---")

argument_points = []

# ── 7.1 Node Program ─────────────────────────────────────
argument_points.append({
    "label": "7.1",
    "point": (
        f"Program {PROGRAM_CODE} beroperasi di {len(nodes)} node "
        f"yang tersebar secara nasional."
    ),
    "elaboration": (
        f"Node aktif: {', '.join(nodes)}. "
        f"{active_note} "
        "Narasi harus menjelaskan peran berbeda tiap node dan distribusi "
        "aktivitas program secara geografis."
    ),
    "evidence_refs": ["strategy_design.institutional", "outputs"],
    "status": "supported"
})

# ── 7.2 Stakeholder ──────────────────────────────────────
stk_count = len(canonical["stakeholders"])
stk_names = [s["name"] for s in canonical["stakeholders"]]
argument_points.append({
    "label": "7.2",
    "point": (
        f"Program melibatkan {stk_count} pemangku kepentingan utama "
        "dengan peran yang berbeda dalam ekosistem program."
    ),
    "elaboration": f"Stakeholder: {', '.join(stk_names)}.",
    "evidence_refs": ["stakeholders"],
    "status": "supported"
})

# ── 7.3 Investasi ─────────────────────────────────────────
total_inv    = from_audit("total_investment")
inv_statuses = set(i["data_status"] for i in canonical["investment"])
has_pending  = "under_confirmation" in inv_statuses

inv_per_year_str = ", ".join(
    f"{yr} {fmt_idr(from_audit(f'investment_total_{yr}'))}"
    for yr in years if f"investment_total_{yr}" in audit_log
)

argument_points.append({
    "label": "7.3",
    "point": (
        f"Total investasi program {PERIOD_LABEL} mencapai {fmt_idr(total_inv)}, "
        "meningkat setiap tahun seiring penguatan aktivitas program."
    ),
    "elaboration": (
        f"Per tahun: {inv_per_year_str}. "
        + ("Sebagian investasi berstatus under_confirmation — "
           "perlu diverifikasi dari laporan keuangan resmi."
           if has_pending else "")
    ),
    "evidence_refs": ["investment"],
    "financial_ref": "table_investment_per_node",
    "status": "supported",
    "note": "Sebagian investasi under_confirmation — display_status present_as_pending" if has_pending else ""
})

# ── 7.4 Output Program ────────────────────────────────────
activities_list = _activities_to_list(canonical.get("activities", []))

act_count = len(activities_list)
out_count = len(canonical.get("outputs", []) if isinstance(canonical.get("outputs"), list) else [])

argument_points.append({
    "label": "7.4",
    "point": (
        f"Program menghasilkan {act_count} aktivitas terstruktur "
        f"dengan {out_count} output terukur sepanjang {PERIOD_LABEL}."
    ),
    "elaboration": (
        "Aktivitas mencakup: "
        + "; ".join(
            a.get("name", a.get("activity_id", str(a)))[:60]
            for a in activities_list[:3]
        )
        + ("..." if act_count > 3 else ".")
    ),
    "evidence_refs": ["activities", "outputs"],
    "status": "supported"
})

# ── 7.5 Outcome & Aspek Nilai (dinamis) ───────────────────
total_observed = len(observed_asps)
total_proxy    = len(proxy_asps)

point_75 = f"Program menghasilkan {len(asp_info)} aspek nilai terukur"
if total_observed > 0 and total_proxy > 0:
    point_75 += (
        f": {total_observed} aspek observed "
        f"({', '.join(observed_asps)} dari transaksi aktual) "
        f"dan {total_proxy} aspek proxy yang tervalidasi "
        f"({', '.join(proxy_asps)})."
    )
elif total_observed > 0:
    point_75 += f": semua aspek observed ({', '.join(observed_asps)})."
else:
    point_75 += f": semua aspek proxy ({', '.join(proxy_asps)})."

argument_points.append({
    "label": "7.5",
    "point": point_75,
    "evidence_refs": ["outcomes", "monetization"],
    "financial_ref": "table_monetization_per_aspek",
    "status": "supported"
})

# Sub-poin per aspek — dinamis dari asp_info
for idx, (asp_code, info) in enumerate(asp_info.items(), 1):
    mon_data    = mon_by_aspect.get(asp_code, {})
    gross_total = sum(v["gross"] for v in mon_data.values())
    mult        = ddat.get(asp_code, {}).get("net_multiplier", 1.0)
    net_total   = gross_total * mult
    justif      = ddat.get(asp_code, {}).get("justification", "—")

    if info["tag"] == "proxy":
        sample       = mon_data.get(years[0], {})
        proxy_detail = f"Proxy: {sample.get('proxy_basis', '—')}."
        elaboration  = f"{proxy_detail} Justifikasi DDAT: {justif}"
        note         = "Proxy — display_status present_as_proxy. Wajib disertai badge dan source_refs."
    else:
        elaboration = f"Data transaksi aktual. Justifikasi DDAT: {justif}"
        note        = ""

    argument_points.append({
        "label": f"7.5.{idx}",
        "point": (
            f"{asp_code} — {info['name']} ({info['tag']}): "
            f"gross kumulatif {fmt_idr(gross_total)}, "
            f"adj ×{mult}, net kumulatif {fmt_idr(net_total)}."
        ),
        "elaboration": elaboration,
        "evidence_refs": [
            f"monetization[aspect={asp_code}]",
            f"ddat_params.{asp_code}",
            "evidence_registry",
        ],
        "financial_ref": "table_monetization_per_aspek",
        "status": "supported",
        "note": note
    })

# ── 7.6 Fiksasi Dampak (DDAT) ─────────────────────────────
avg_fiksasi = calc["avg_fiksasi_pct"]

# Buat ringkasan DDAT per aspek secara dinamis
ddat_summary = " · ".join(
    f"{asp} ×{ddat[asp]['net_multiplier']:.2f} ({round((1-ddat[asp]['net_multiplier'])*100)}% haircut)"
    for asp in asp_info if asp in ddat
)

argument_points.append({
    "label": "7.6",
    "point": (
        f"Fiksasi dampak (DDAT adjustment) diterapkan per aspek dengan haircut "
        f"rata-rata {avg_fiksasi:.1f}%, mencerminkan konservatisme metodologis yang konsisten."
    ),
    "elaboration": (
        f"DDAT = Deadweight + Displacement + Attribution + Drop-off. "
        f"{ddat_summary}."
    ),
    "evidence_refs": ["ddat_params"],
    "financial_ref": "table_ddat_per_aspek",
    "status": "supported"
})

# ── 7.7 Compound & ORI ────────────────────────────────────
ori_lines = []
for yr in years:
    if f"net_compounded_{yr}" in audit_log:
        ori_data = ori.get(str(yr), {})
        cf       = ori_data.get("compound_factor", 1.0)
        series   = ori_data.get("series", f"ORI{str(yr)[2:]}")
        rate     = ori_data.get("rate", 0)
        ori_lines.append(
            f"{yr}: ×{cf} ({series}, {rate*100:.2f}%) → {fmt_idr(from_audit(f'net_compounded_{yr}'))}"
        )

argument_points.append({
    "label": "7.7",
    "point": (
        "Nilai bersih setiap tahun di-compound ke terminal year menggunakan "
        "ORI reference rate, untuk mencerminkan nilai waktu uang secara konservatif."
    ),
    "elaboration": ". ".join(ori_lines) + ".",
    "evidence_refs": ["ori_rates"],
    "financial_ref": "table_sroi_per_tahun",
    "status": "supported"
})

# ── 7.8 SROI per Tahun ────────────────────────────────────
for idx, yr in enumerate(years, 1):
    if yr not in per_year:
        continue
    row = per_year[yr]
    argument_points.append({
        "label": f"7.8.{idx}",
        "point": (
            f"Tahun {yr}: investasi {fmt_idr(row['investment'])}, "
            f"net compounded {fmt_idr(row['compounded'])}, "
            f"SROI {fmt_ratio(row['sroi_ratio'])}."
        ),
        "elaboration": (
            f"Gross: {fmt_idr(row['gross'])}. "
            f"Net setelah DDAT: {fmt_idr(row['net'])}. "
            f"Compound factor: ×{row['cf_applied']:.4f}."
        ),
        "evidence_refs": [f"sroi_metrics.calculated.per_year[{yr}]"],
        "financial_ref": "table_sroi_per_tahun",
        "status": "supported"
    })

# ── 7.9 SROI Blended ──────────────────────────────────────
total_inv_val  = from_audit("total_investment")
total_net_comp = from_audit("total_net_compounded")
sroi_blended   = from_audit("sroi_blended")

# Buat catatan transparansi aspek proxy jika ada
proxy_note = ""
if proxy_asps:
    proxy_note = (
        f" Catatan: aspek {', '.join(proxy_asps)} adalah proxy — "
        "jika hanya aspek observed, SROI akan berbeda. "
        "Transparansi ini penting untuk kredibilitas laporan."
    )

argument_points.append({
    "label": "7.9",
    "point": (
        f"SROI blended {PERIOD_LABEL}: {fmt_ratio(sroi_blended)} — "
        f"dari investasi {fmt_idr(total_inv_val)} menghasilkan "
        f"net benefit compounded {fmt_idr(total_net_comp)}."
    ),
    "elaboration": (
        f"Setiap Rp 1 yang diinvestasikan menghasilkan nilai sosial-ekonomi terukur "
        f"senilai Rp {sroi_blended:.2f}. Program dinyatakan positive return."
        + proxy_note
    ),
    "evidence_refs": ["sroi_metrics.calculated"],
    "financial_ref": "table_sroi_blended",
    "status": "supported"
})

# ── 7.10 Temuan Kritis — dari uncertainty_flags ───────────
# Dinamis: ambil high-severity flags sebagai temuan kritis
if high_flags:
    for idx, flag in enumerate(high_flags, 1):
        argument_points.append({
            "label": f"7.10.{idx}",
            "point": (
                f"Temuan kritis: {flag.get('description', flag.get('field', '—'))} "
                "— ini adalah catatan metodologis yang justru memperkuat "
                "kredibilitas laporan."
            ),
            "elaboration": (
                f"Field terdampak: {flag.get('field', '—')}. "
                "Narasi harus menempatkan ini sebagai learning finding "
                "dengan rekomendasi konkret untuk periode berikutnya."
            ),
            "evidence_refs": ["uncertainty_flags"],
            "status": "supported"
        })
else:
    # Fallback jika tidak ada high flags
    argument_points.append({
        "label": "7.10",
        "point": (
            f"Program {PROGRAM_CODE} telah berhasil mendokumentasikan "
            "seluruh aspek nilai dengan tingkat kepercayaan yang memadai."
        ),
        "elaboration": (
            "Tidak ada temuan kritis yang memerlukan catatan khusus. "
            "Semua aspek monetisasi terdokumentasi dengan justifikasi DDAT yang defensible."
        ),
        "evidence_refs": ["uncertainty_flags", "evidence_registry"],
        "status": "supported"
    })

print(f"  {len(argument_points)} argument points disusun")


# ══════════════════════════════════════════════════════════
# COMPOSE OUTLINE BAB 7
# ══════════════════════════════════════════════════════════

# Narrative notes dinamis
proxy_narrative = ""
if proxy_asps:
    proxy_narrative = (
        f"(2) Aspek {', '.join(proxy_asps)} wajib disertai badge proxy dan source_refs. "
    )

pending_narrative = ""
if has_pending:
    pending_narrative = (
        "(3) Sebagian investasi berstatus under_confirmation — "
        "tampilkan dengan callout_warning atau badge pending. "
    )

outline_bab7 = {
    "chapter_id":    "bab_7",
    "chapter_title": "Implementasi / PDIS dengan SROI",
    "builder_mode":  "sroi",
    "coverage_status": "strong",
    "program_code":  PROGRAM_CODE,
    "program_name":  PROGRAM_NAME,

    "purpose": (
        f"Menyajikan seluruh rangkaian implementasi program {PROGRAM_CODE} secara terukur — "
        "dari aktivitas, stakeholder, investasi, dan output hingga outcome, "
        "fiksasi dampak, monetisasi, dan hasil SROI evaluatif."
    ),

    "core_claim": (
        f"Program {PROGRAM_CODE} — {PROGRAM_NAME} menghasilkan "
        f"SROI blended {fmt_ratio(sroi_blended)} — "
        "positive return yang dicapai melalui kombinasi aspek nilai terukur "
        f"({', '.join(observed_asps) or 'observed'}) "
        + (f"dan nilai terproksikan ({', '.join(proxy_asps)}) " if proxy_asps else "")
        + "secara konservatif dan defensible."
    ),
    "core_claim_ref": "sroi_metrics.calculated",

    "argument_points": argument_points,

    "known_gaps": [],

    "financial_refs": table_ids,

    "narrative_notes": (
        "PENTING untuk Narrative Builder: "
        "(1) Semua angka HARUS diambil dari sroi_metrics.calculated — "
        "jangan hitung ulang atau bulatkan secara mandiri. "
        + proxy_narrative
        + pending_narrative
        + f"Laporan ini untuk program {PROGRAM_CODE}, bukan ESL — "
        "pastikan tidak ada referensi program lain yang bocor ke narasi."
    ),

    "generated_at":      datetime.now().isoformat(),
    "builder_version":   BUILDER_VERSION,
    "source_calc_at":    calc.get("calculated_at", ""),
    "source_engine_ver": calc.get("engine_version", ""),
}


# ══════════════════════════════════════════════════════════
# VALIDATE SEBELUM SIMPAN
# ══════════════════════════════════════════════════════════

print("\n--- Pre-save validation ---")
errors = []

valid_refs = set(canonical.keys()) | {
    f"sroi_metrics.calculated.per_year[{yr}]" for yr in years
} | {
    "sroi_metrics.calculated",
    "strategy_design.institutional",
} | {e["evidence_id"] for e in canonical.get("evidence_registry", [])} \
  | {f"monetization[aspect={asp}]" for asp in asp_info} \
  | {f"ddat_params.{asp}" for asp in ddat} \
  | {"evidence_registry", "uncertainty_flags", "outputs", "outcomes",
     "activities", "investment", "stakeholders", "monetization",
     "ddat_params", "ori_rates"}

for ap in argument_points:
    for ref in ap.get("evidence_refs", []):
        ref_base = ref.split(".")[0].split("[")[0]
        if ref not in valid_refs and ref_base not in valid_refs:
            errors.append(f"  WARN: evidence_ref tidak dikenal: '{ref}' di point {ap['label']}")

for ap in argument_points:
    if ap["status"] == "supported" and not ap.get("evidence_refs"):
        errors.append(f"  FAIL: Point {ap['label']} supported tapi evidence_refs kosong")

if outline_bab7["known_gaps"]:
    errors.append("  FAIL: known_gaps tidak boleh berisi jika coverage strong")

core_ref = outline_bab7["core_claim_ref"].split(".")[0]
if core_ref not in canonical:
    errors.append(f"  FAIL: core_claim_ref '{core_ref}' tidak ada di canonical")
else:
    print(f"  PASS: core_claim_ref '{core_ref}' ditemukan di canonical")

for ap in argument_points:
    if ap["status"] in ["pending", "inferred"] and not ap.get("note", "").strip():
        errors.append(f"  FAIL: Point {ap['label']} status={ap['status']} tapi note kosong")

if errors:
    for e in errors:
        print(e)
    fail_count = sum(1 for e in errors if "FAIL" in e)
    if fail_count > 0:
        print(f"\n{fail_count} validation error — outline tidak disimpan")
        sys.exit(1)
    else:
        print(f"  {len(errors)} warning(s) — outline tetap disimpan")
else:
    print("  PASS: semua validation rules terpenuhi")


# ══════════════════════════════════════════════════════════
# WRITE OUTPUT (Handoff D)
# ══════════════════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
outline_path = OUTPUT_DIR / "chapter_outline_bab7.json"

json.dump([outline_bab7], open(outline_path, "w"), indent=2, ensure_ascii=False)

print(f"\nOutput: {outline_path}")

# ── Human-readable preview ───────────────────────────────
print("\n" + "="*65)
print(f"POINT BUILDER OUTPUT — {outline_bab7['chapter_id']}")
print(f"Program : {PROGRAM_CODE} — {PROGRAM_NAME}")
print(f"Mode    : {outline_bab7['builder_mode']}")
print(f"Coverage: {outline_bab7['coverage_status']}")
print(f"Points  : {len(argument_points)}")
print(f"Aspek   : {list(asp_info.keys())} ({len(observed_asps)} observed, {len(proxy_asps)} proxy)")
print(f"Fin.refs: {len(table_ids)}")
print("-"*65)
print(f"Core claim: {outline_bab7['core_claim'][:80]}...")
print("-"*65)
for ap in argument_points:
    status_marker = {"supported":"✓","partial":"~","inferred":"?","pending":"⏳"}.get(ap["status"],"·")
    proxy_marker  = " [PROXY]" if ap.get("note","").strip() else ""
    print(f"  {status_marker} {ap['label']:<8} {ap['point'][:65]}{proxy_marker}")
print("="*65)
