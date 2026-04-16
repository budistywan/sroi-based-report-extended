"""
Financial Calculation Engine — Sprint 1
SROI Report System

Komponen DETERMINISTIK. Tidak ada LLM di sini.
Input : canonical_esl_v1.json (via Handoff A)
Output: sroi_metrics.calculated + financial_tables + calc_audit_log (via Handoff B)

Usage:
  python financial_engine.py                              # default paths
  python financial_engine.py --input canonical_esl_v1.json --output handoff_b.json
  INPUT_FILE=... OUTPUT_FILE=... python financial_engine.py
"""

import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from copy import deepcopy

ENGINE_VERSION = "1.0.0"

# ── CLI / ENV CONFIG ─────────────────────────────────────
parser = argparse.ArgumentParser(description="Financial Calculation Engine")
parser.add_argument("--input",  type=str, default=None, help="Path ke canonical JSON (Handoff A input)")
parser.add_argument("--output", type=str, default=None, help="Path output Handoff B JSON")
parser.add_argument("--base",   type=str, default=None, help="Base directory (fallback jika --input/--output tidak diset)")
args = parser.parse_args()

BASE = Path(args.base or os.environ.get("BASE_DIR", Path(__file__).parent))

INPUT_FILE  = Path(args.input)  if args.input  else Path(os.environ.get("INPUT_FILE",  BASE / "canonical_esl_v1.json"))
OUTPUT_FILE = Path(args.output) if args.output else Path(os.environ.get("OUTPUT_FILE", BASE / "handoff_b.json"))

print(f"Input : {INPUT_FILE.resolve()}")
print(f"Output: {OUTPUT_FILE.resolve()}")


# ── AUDIT LOG HELPER ─────────────────────────────────────
audit_log = []

def log(field, value, formula, inputs_used):
    audit_log.append({
        "field":       field,
        "value":       round(value, 2),
        "formula":     formula,
        "inputs_used": inputs_used,
        "timestamp":   datetime.utcnow().isoformat() + "Z"
    })
    return value


# ── LOAD CANONICAL JSON ──────────────────────────────────
with open(INPUT_FILE) as f:
    canonical = json.load(f)

program_code = canonical["program_identity"]["program_code"]
print(f"\nProgram: {program_code}")
print(f"Status : {canonical['sroi_metrics']['status']}")

if canonical["sroi_metrics"]["status"] == "validated":
    print("WARN: sroi_metrics sudah validated — engine tidak akan overwrite.")
    sys.exit(0)


# ── LOAD POLICY (dari Handoff A atau default) ────────────
policy = {
    "allow_compound":    True,
    "allow_sensitivity": True,
    "allow_payback":     True,
    "terminal_year":     2025,
    "compound_basis":    "ORI"
}


# ── STEP 1: AGGREGATE INVESTMENT PER TAHUN ───────────────
print("\n--- Step 1: Investment per tahun ---")
inv_by_year = {}
for item in canonical["investment"]:
    yr = item["year"]
    inv_by_year[yr] = inv_by_year.get(yr, 0) + item["amount_idr"]

for yr, total in sorted(inv_by_year.items()):
    log(f"investment_total_{yr}", total,
        f"SUM(investment[year={yr}].amount_idr)", [f"investment[year={yr}]"])
    print(f"  {yr}: Rp {total:,.0f}")

total_investment = sum(inv_by_year.values())
log("total_investment", total_investment, "SUM(investment_total_*)", list(inv_by_year.keys()))
print(f"  TOTAL: Rp {total_investment:,.0f}")


# ── STEP 2: GROSS PER ASPEK PER TAHUN ───────────────────
print("\n--- Step 2: Gross per aspek per tahun ---")
gross_by_aspect_year = {}  # {(aspect_code, year): gross_idr}

for mon in canonical["monetization"]:
    key = (mon["aspect_code"], mon["year"])
    gross_by_aspect_year[key] = mon["gross_idr"]
    log(f"gross_{mon['aspect_code']}_{mon['year']}",
        mon["gross_idr"],
        f"monetization[{mon['monetization_id']}].gross_idr",
        [mon["monetization_id"]])
    print(f"  {mon['aspect_code']} {mon['year']}: Rp {mon['gross_idr']:,.0f}")


# ── STEP 3: NET PER ASPEK PER TAHUN (apply DDAT) ────────
print("\n--- Step 3: Net per aspek per tahun (after DDAT) ---")
net_by_aspect_year = {}

for (aspect_code, year), gross in gross_by_aspect_year.items():
    ddat = canonical["ddat_params"][aspect_code]
    multiplier = ddat["net_multiplier"]
    net = gross * multiplier
    net_by_aspect_year[(aspect_code, year)] = net
    log(f"net_{aspect_code}_{year}",
        net,
        f"gross_{aspect_code}_{year} × net_multiplier({multiplier})",
        [f"gross_{aspect_code}_{year}", f"ddat_params.{aspect_code}.net_multiplier"])
    print(f"  {aspect_code} {year}: Rp {gross:,.0f} × {multiplier} = Rp {net:,.0f}")


# ── STEP 4: GROSS TOTAL + NET TOTAL PER TAHUN ───────────
print("\n--- Step 4: Gross total & net total per tahun ---")
years = sorted(set(yr for (_, yr) in gross_by_aspect_year.keys()))

gross_by_year = {}
net_by_year   = {}

for yr in years:
    g = sum(v for (asp, y), v in gross_by_aspect_year.items() if y == yr)
    n = sum(v for (asp, y), v in net_by_aspect_year.items()   if y == yr)
    gross_by_year[yr] = g
    net_by_year[yr]   = n

    fiksasi_pct = (1 - n / g) * 100 if g > 0 else 0
    log(f"gross_total_{yr}", g, f"SUM(gross_*_{yr})", [f"gross_*_{yr}"])
    log(f"net_total_{yr}",   n, f"SUM(net_*_{yr})",   [f"net_*_{yr}"])
    log(f"fiksasi_pct_{yr}", fiksasi_pct,
        f"(1 - net_total_{yr} / gross_total_{yr}) × 100",
        [f"gross_total_{yr}", f"net_total_{yr}"])
    print(f"  {yr}: gross Rp {g:,.0f}  net Rp {n:,.0f}  fiksasi {fiksasi_pct:.1f}%")


# ── STEP 5: COMPOUND KE TERMINAL YEAR ───────────────────
print("\n--- Step 5: Compound ke terminal year ---")
terminal_year = policy["terminal_year"]
net_compounded_by_year = {}

for yr in years:
    if not policy["allow_compound"]:
        cf = 1.0
    else:
        ori = canonical["ori_rates"].get(str(yr), {})
        cf  = ori.get("compound_factor", 1.0)

    net_comp = net_by_year[yr] * cf
    net_compounded_by_year[yr] = net_comp
    log(f"net_compounded_{yr}",
        net_comp,
        f"net_total_{yr} × compound_factor({cf}) [{canonical['ori_rates'].get(str(yr), {}).get('series','N/A')}]",
        [f"net_total_{yr}", f"ori_rates.{yr}.compound_factor"])
    print(f"  {yr}: Rp {net_by_year[yr]:,.0f} × {cf:.4f} = Rp {net_comp:,.0f}")


# ── STEP 6: SROI PER TAHUN ───────────────────────────────
print("\n--- Step 6: SROI per tahun ---")
sroi_per_year = []

for yr in years:
    inv  = inv_by_year[yr]
    nc   = net_compounded_by_year[yr]
    sroi = nc / inv if inv > 0 else 0
    sroi_per_year.append({
        "year":       yr,
        "investment": round(inv, 2),
        "gross":      round(gross_by_year[yr], 2),
        "net":        round(net_by_year[yr], 2),
        "compounded": round(nc, 2),
        "sroi_ratio": round(sroi, 4),
        "cf_applied": canonical["ori_rates"].get(str(yr), {}).get("compound_factor", 1.0)
    })
    log(f"sroi_ratio_{yr}", sroi,
        f"net_compounded_{yr} / investment_total_{yr}",
        [f"net_compounded_{yr}", f"investment_total_{yr}"])
    print(f"  {yr}: 1 : {sroi:.2f}")


# ── STEP 7: SROI BLENDED ─────────────────────────────────
print("\n--- Step 7: SROI blended ---")
total_net_compounded = sum(net_compounded_by_year.values())
sroi_blended = total_net_compounded / total_investment if total_investment > 0 else 0
avg_fiksasi  = sum((1 - net_by_year[yr] / gross_by_year[yr]) for yr in years
                   if gross_by_year[yr] > 0) / len(years) * 100

log("total_net_compounded", total_net_compounded,
    "SUM(net_compounded_*)", [f"net_compounded_{yr}" for yr in years])
log("sroi_blended", sroi_blended,
    "total_net_compounded / total_investment",
    ["total_net_compounded", "total_investment"])
log("avg_fiksasi_pct", avg_fiksasi,
    "AVG(fiksasi_pct_*)", [f"fiksasi_pct_{yr}" for yr in years])

print(f"  Total investasi       : Rp {total_investment:,.0f}")
print(f"  Total net compounded  : Rp {total_net_compounded:,.0f}")
print(f"  Avg fiksasi           : {avg_fiksasi:.1f}%")
print(f"  SROI blended          : 1 : {sroi_blended:.2f}")


# ── STEP 8: SENSITIVITY (opsional) ──────────────────────
sensitivity = {}
if policy["allow_sensitivity"]:
    print("\n--- Step 8: Sensitivity analysis ---")
    for aspect_code in canonical["ddat_params"].keys():
        base_nc    = total_net_compounded
        base_sroi  = sroi_blended
        delta_pct  = 0.01  # 1 percentage point

        # Hitung ulang dengan net_multiplier +1pp
        new_total = 0
        for yr in years:
            new_net_yr = 0
            for (asp, y), gross in gross_by_aspect_year.items():
                mult = canonical["ddat_params"][asp]["net_multiplier"]
                if asp == aspect_code and y == yr:
                    mult = mult + delta_pct
                new_net_yr += gross * mult
            cf = canonical["ori_rates"].get(str(yr), {}).get("compound_factor", 1.0)
            new_total += new_net_yr * cf

        delta_sroi = (new_total / total_investment) - base_sroi
        sensitivity[aspect_code] = {
            "delta_per_1pp_multiplier": round(delta_sroi, 4),
            "description": f"Kenaikan 1pp net_multiplier {aspect_code} → SROI naik {delta_sroi:.4f}"
        }
        print(f"  {aspect_code}: +1pp multiplier → SROI +{delta_sroi:.4f} (total {sroi_blended + delta_sroi:.4f})")


# ── STEP 9: BUILD FINANCIAL TABLES ──────────────────────
print("\n--- Step 9: Build financial tables ---")

CW = 9638  # content width DXA (A4 minus margins)

# Table 1: Investasi per node per tahun
rows_inv = []
node_totals = {}
for item in canonical["investment"]:
    node = item.get("node", "—")
    yr   = item["year"]
    amt  = item["amount_idr"]
    node_totals[node] = node_totals.get(node, 0) + amt
    rows_inv.append([node, str(yr), f"Rp {amt:,.0f}", item["data_status"]])

rows_inv.append(["TOTAL", "—",
                 f"Rp {total_investment:,.0f}",
                 "final"])

table_investment = {
    "table_id":      "table_investment_per_node",
    "title":         "Investasi Program per Node per Tahun",
    "headers":       ["Node Program", "Tahun", "Investasi (Rp)", "Status"],
    "rows":          rows_inv,
    "column_widths": [3200, 1200, 3000, 2238],   # sum = 9638
    "note":          "2023–2024 under_confirmation — ditampilkan dengan badge pending"
}

# Table 2: Monetisasi per aspek per tahun
rows_mon = []
aspect_totals = {}
for (asp, yr), gross in sorted(gross_by_aspect_year.items()):
    net    = net_by_aspect_year[(asp, yr)]
    mult   = canonical["ddat_params"][asp]["net_multiplier"]
    d_stat = next((m["display_status"] for m in canonical["monetization"]
                   if m["aspect_code"] == asp and m["year"] == yr), "present_as_final")
    rows_mon.append([asp, str(yr),
                     f"Rp {gross:,.0f}",
                     f"×{mult}",
                     f"Rp {net:,.0f}",
                     d_stat.replace("present_as_","")])
    aspect_totals[asp] = aspect_totals.get(asp, 0) + net

rows_mon.append(["TOTAL", "—", f"Rp {sum(gross_by_year.values()):,.0f}",
                 "—", f"Rp {sum(net_by_year.values()):,.0f}", "—"])

table_monetization = {
    "table_id":      "table_monetization_per_aspek",
    "title":         "Monetisasi Nilai Sosial per Aspek per Tahun",
    "headers":       ["Aspek", "Tahun", "Gross (Rp)", "Adj DDAT", "Net (Rp)", "Status"],
    "rows":          rows_mon,
    "column_widths": [900, 800, 2100, 900, 2100, 2838],   # sum = 9638
    "note":          "LUB & SVC = observed. REINT & CONF = proxy S10."
}

# Table 3: DDAT per aspek
rows_ddat = []
for asp, params in canonical["ddat_params"].items():
    rows_ddat.append([
        asp,
        f"{params.get('deadweight',0)*100:.0f}%",
        f"{params.get('displacement',0)*100:.0f}%",
        f"{params.get('attribution',0)*100:.0f}%",
        f"{params.get('dropoff',0)*100:.0f}%",
        f"×{params['net_multiplier']}",
        f"{(1-params['net_multiplier'])*100:.0f}%"
    ])

table_ddat = {
    "table_id":      "table_ddat_per_aspek",
    "title":         "DDAT Adjustment per Aspek",
    "headers":       ["Aspek", "DW", "DS", "AT", "DO", "Net ×", "Haircut"],
    "rows":          rows_ddat,
    "column_widths": [1200, 1100, 1100, 1100, 1100, 1100, 2938],   # sum = 9638
    "note":          "DW=Deadweight DS=Displacement AT=Attribution DO=Drop-off"
}

# Table 4: SROI per tahun
rows_sroi = []
for row in sroi_per_year:
    yr = row["year"]
    ori_series = canonical["ori_rates"].get(str(yr), {}).get("series", "—")
    rows_sroi.append([
        str(yr),
        f"Rp {row['investment']:,.0f}",
        f"Rp {row['gross']:,.0f}",
        f"Rp {row['net']:,.0f}",
        f"×{row['cf_applied']:.4f} ({ori_series})",
        f"Rp {row['compounded']:,.0f}",
        f"1 : {row['sroi_ratio']:.2f}"
    ])

rows_sroi.append([
    "TOTAL",
    f"Rp {total_investment:,.0f}",
    f"Rp {sum(gross_by_year.values()):,.0f}",
    f"Rp {sum(net_by_year.values()):,.0f}",
    "—",
    f"Rp {total_net_compounded:,.0f}",
    f"1 : {sroi_blended:.2f}"
])

table_sroi = {
    "table_id":      "table_sroi_per_tahun",
    "title":         "Kalkulasi SROI per Tahun Program",
    "headers":       ["Tahun", "Investasi", "Gross", "Net", "Compound", "Net Compounded", "SROI"],
    "rows":          rows_sroi,
    "column_widths": [800, 1500, 1400, 1400, 1700, 1638, 1200],   # sum = 9638
    "note":          "Net compounded = nilai bersih yang di-compound ke terminal year 2025"
}

# Table 5: SROI blended summary (metric card data)
table_blended = {
    "table_id": "table_sroi_blended",
    "title":    "Ringkasan SROI Evaluatif 2023–2025",
    "headers":  ["Metrik", "Nilai"],
    "rows": [
        ["Total Investasi",           f"Rp {total_investment:,.0f}"],
        ["Total Gross Kumulatif",     f"Rp {sum(gross_by_year.values()):,.0f}"],
        ["Total Net Kumulatif",       f"Rp {sum(net_by_year.values()):,.0f}"],
        ["Total Net Compounded",      f"Rp {total_net_compounded:,.0f}"],
        ["Avg Fiksasi",               f"−{avg_fiksasi:.1f}%"],
        ["SROI Blended",              f"1 : {sroi_blended:.2f}"],
    ],
    "column_widths": [4819, 4819],   # sum = 9638
    "note": "Evaluatif · Compound ORI-adjusted · DDAT net multiplier per aspek · Terminal year 2025"
}

financial_tables = [
    table_investment,
    table_monetization,
    table_ddat,
    table_sroi,
    table_blended
]
print(f"  {len(financial_tables)} tabel dihasilkan")


# ── STEP 10: COMPOSE HANDOFF B ───────────────────────────
sroi_metrics_calculated = {
    "total_investment_idr":     round(total_investment, 2),
    "total_gross_idr":          round(sum(gross_by_year.values()), 2),
    "total_net_idr":            round(sum(net_by_year.values()), 2),
    "total_net_compounded_idr": round(total_net_compounded, 2),
    "sroi_blended":             round(sroi_blended, 4),
    "avg_fiksasi_pct":          round(avg_fiksasi, 2),
    "per_year":                 sroi_per_year,
    "financial_tables":         financial_tables,
    "calc_audit_log":           audit_log,
    "sensitivity":              sensitivity,
    "calculated_at":            datetime.utcnow().isoformat() + "Z",
    "engine_version":           ENGINE_VERSION
}

handoff_b = {
    "sroi_metrics": {
        "calculated": sroi_metrics_calculated,
        "status":     "calculated"
    },
    "financial_tables": financial_tables,
    "calc_audit_log":   audit_log
}


# ── WRITE HANDOFF B ──────────────────────────────────────
with open(OUTPUT_FILE, "w") as f:
    json.dump(handoff_b, f, indent=2, ensure_ascii=False)
print(f"\nHandoff B written → {OUTPUT_FILE}")


# ── UPDATE CANONICAL JSON ────────────────────────────────
# Engine menulis hasil kembali ke canonical JSON
canonical_updated = deepcopy(canonical)
canonical_updated["sroi_metrics"]["calculated"] = sroi_metrics_calculated
canonical_updated["sroi_metrics"]["status"]     = "calculated"

with open(INPUT_FILE, "w") as f:
    json.dump(canonical_updated, f, indent=2, ensure_ascii=False)
print(f"Canonical JSON updated → {INPUT_FILE}")


# ── SUMMARY ──────────────────────────────────────────────
print("\n" + "="*55)
print(f"FINANCIAL ENGINE COMPLETE")
print(f"  Program      : {program_code}")
print(f"  Investasi    : Rp {total_investment:,.0f}")
print(f"  Net compound : Rp {total_net_compounded:,.0f}")
print(f"  Avg fiksasi  : −{avg_fiksasi:.1f}%")
print(f"  SROI blended : 1 : {sroi_blended:.2f}")
print(f"  Audit log    : {len(audit_log)} entri")
print(f"  Tabel        : {len(financial_tables)}")
print("="*55)
