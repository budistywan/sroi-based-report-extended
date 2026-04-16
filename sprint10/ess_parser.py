"""
ess_parser.py — Sprint 10C
Parser khusus ESS (Enduro Sahabat Santri).

Rule khusus karena generic deck_script_parser tidak cukup untuk ESS:
  - Script ESS tidak punya per-year breakdown yang lengkap
  - SROI final belum bisa dihitung dari script saja
  - Parser harus jujur: partial/pending, tidak fabricate

Output: canonical_ess_extracted_v2.json (canonical-schema-valid)

Usage:
  python ess_parser.py
  python ess_parser.py --scripts /path/TJSL_Scripts.md --output /path/canonical_ess_v2.json
"""

import json, re, sys, os, argparse
from pathlib import Path
from datetime import datetime

PARSER_VERSION = "1.0.0"

parser = argparse.ArgumentParser()
parser.add_argument("--scripts", default=None)
parser.add_argument("--output",  default=None)
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
SCRIPTS_FILE = Path(args.scripts) if args.scripts \
    else Path(os.environ.get("SCRIPTS_FILE",
              "/mnt/user-data/outputs/TJSL_Scripts.md"))
OUTPUT_FILE  = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_FILE",
              SCRIPT_DIR / "canonical_ess_extracted_v2.json"))

print(f"Scripts: {SCRIPTS_FILE.resolve()}")
print(f"Output : {OUTPUT_FILE.resolve()}")

if not SCRIPTS_FILE.exists():
    print(f"FAIL: {SCRIPTS_FILE} tidak ditemukan"); sys.exit(1)

src = open(SCRIPTS_FILE).read()

# ── EXTRACT ESS SECTIONS ──────────────────────────────────────
sections = {}
raw_sections = re.split(r'^## ', src, flags=re.MULTILINE)
for s in raw_sections[1:]:
    name = s.split('\n')[0].strip()
    if name.startswith('ess'):
        sections[name] = s

print(f"ESS sections found: {list(sections.keys())}")
ess_content = "\n".join(sections.values())

# ── PROGRAM IDENTITY ──────────────────────────────────────────
identity = {
    "program_code":     "ESS",
    "program_name":     "Enduro Sahabat Santri",
    "program_tagline":  "Pemberdayaan Santri melalui Literasi Pelumasan dan Kewirausahaan Bengkel Pesantren",
    "company":          "PT Pertamina Lubricants",
    "unit":             "TJSL CSV",
    "period_start":     2023,
    "period_end":       2025,
    "palette":          "A — Deep Ocean",
    "data_status":      "final",
}

# ── EXTRACT INVESTMENT (total saja, per tahun tidak ada) ──────
investments = []
inv_match = re.search(
    r'"Rp\s*([\d,\.]+\s*(?:Jt|jt|M|miliar|juta))"[^}]*sub\s*:\s*"total investasi',
    ess_content, re.IGNORECASE
)
if inv_match:
    raw = inv_match.group(1).strip()
    # Parse: 402,37 Jt
    num_match = re.match(r'([\d,\.]+)\s*(Jt|jt|M|miliar|juta)?', raw, re.IGNORECASE)
    if num_match:
        val = float(num_match.group(1).replace(',','.'))
        unit = (num_match.group(2) or '').lower()
        if 'jt' in unit or 'juta' in unit:
            val *= 1_000_000
        elif 'm' in unit or 'miliar' in unit:
            val *= 1_000_000_000
        investments.append({
            "year":           "2023-2025",
            "node":           "total",
            "amount_idr":     int(val),
            "data_status":    "under_confirmation",
            "display_status": "present_as_pending",
            "source_refs":    ["src_ess_01"],
            "note":           "Total investasi 3 tahun — per-tahun breakdown tidak tersedia di script",
        })
    print(f"  Investment total: {raw}")
else:
    print("  Investment: tidak ditemukan di script")

# ── EXTRACT MONETIZATION (aspek yang tersedia) ────────────────
monetization = []
aspect_blocks = re.finditer(
    r'\{\s*id\s*:\s*"([A-Z]+)"[^{]*vals\s*:\s*\{([^}]+)\}',
    ess_content
)
seen_mon = {}
for m in aspect_blocks:
    asp_code = m.group(1)
    vals_str = m.group(2)
    year_vals = re.findall(
        r'"(202[3-5])"\s*:\s*"Rp\s*([\d,\.]+\s*(?:Jt|jt|juta|M|miliar)?)"',
        vals_str, re.IGNORECASE
    )
    for yr, val in year_vals:
        key = (asp_code, yr)
        if key in seen_mon: continue
        seen_mon[key] = True
        # Parse amount
        num_m = re.match(r'([\d,\.]+)\s*(Jt|jt|M|miliar|juta)?', val.strip(), re.IGNORECASE)
        if num_m:
            v = float(num_m.group(1).replace(',','.'))
            u = (num_m.group(2) or '').lower()
            if 'jt' in u or 'juta' in u: v *= 1_000_000
            elif 'm' in u or 'miliar' in u: v *= 1_000_000_000
            is_proxy = asp_code in ["REINT","CONF","JSP","TEFA","OMZ","JOB","SMK","TEFA"]
            monetization.append({
                "monetization_id": f"MON_{asp_code}_{yr}",
                "aspect_code":     asp_code,
                "year":            int(yr),
                "gross_idr":       int(v),
                "data_status":     "proxy" if is_proxy else "observed",
                "display_status":  "present_as_proxy" if is_proxy else "present_as_final",
                "source_refs":     ["src_ess_01"],
            })

print(f"  Monetization: {len(monetization)} entries")

# ── DDAT PARAMS (default pending — ESS spesifik belum tersedia) ──
ddat_params = {}
# Coba ekstrak dari script
mult_search = re.findall(
    r'"([A-Z]{2,5})"\s*[,\s]+[^"]*net[Mm]ult[^"]*"?×?\s*(0\.[0-9]+)',
    ess_content
)
if mult_search:
    for asp, mult in mult_search:
        if asp not in ddat_params and len(asp) <= 5:
            ddat_params[asp] = {
                "net_multiplier": float(mult),
                "data_status":    "extracted",
                "justification":  "extracted from ess script"
            }

# Aspek yang terdeteksi dari monetization tapi belum ada di ddat
for mon in monetization:
    asp = mon["aspect_code"]
    if asp not in ddat_params:
        ddat_params[asp] = {
            "net_multiplier": 0.5,
            "data_status":    "pending",
            "justification":  "default 0.5 — per-aspek ESS belum tersedia di script",
        }

print(f"  DDAT params: {list(ddat_params.keys())}")

# ── ORI RATES ─────────────────────────────────────────────────
ori_rates = {}
ori_rows = re.finditer(
    r'\{\s*yr\s*:\s*"?(202[3-5])"?\s*,\s*label\s*:\s*"([^"]+)"\s*,\s*rate\s*:\s*"([^"]+)"',
    ess_content
)
for m in ori_rows:
    yr    = m.group(1)
    label = m.group(2)
    rate_str = m.group(3).replace(',','.').replace('%','').strip()
    try:
        rate = float(rate_str) / 100
        cf_map = {"2023": round((1+rate)*(1+0.0625),4), "2024": round(1+0.065,4), "2025": 1.0}
        ori_rates[yr] = {
            "rate":            rate,
            "series":          label,
            "compound_factor": cf_map.get(yr, 1.0),
            "terminal_year":   yr == "2025",
        }
    except: pass

# Default jika tidak tersedia
if not ori_rates:
    ori_rates = {
        "2023": {"rate":0.059,"series":"ORI023T3","compound_factor":1.1252,"terminal_year":False,"data_status":"proxy"},
        "2024": {"rate":0.0625,"series":"ORI025T3","compound_factor":1.065,"terminal_year":False,"data_status":"proxy"},
        "2025": {"rate":0.065,"series":"ORI027T3","compound_factor":1.0,"terminal_year":True,"data_status":"proxy"},
    }

# ── SROI METRICS — ESS khusus ─────────────────────────────────
# ESS: angka SROI final tidak tersedia per tahun — hanya gross total
sroi_blended_raw = re.search(r'1\s*:\s*([\d,]+)\s*\(blended', ess_content)

# Cek gross/net jika ada
gross_match = re.search(
    r'Total Nilai (?:Bersih|Kotor)[^:]*:\s*Rp\s*([\d,\.]+\s*(?:Juta|juta|M|miliar|Jt))',
    ess_content
)
inv_total_match = re.search(
    r'dari total investasi Rp\s*([\d,\.]+\s*(?:Jt|M|juta|miliar))',
    ess_content
)

def parse_idr_str(s):
    if not s: return 0
    s = s.strip()
    num_m = re.match(r'([\d,\.]+)\s*(Jt|jt|M|miliar|juta|Juta)?', s, re.IGNORECASE)
    if not num_m: return 0
    v = float(num_m.group(1).replace(',','.'))
    u = (num_m.group(2) or '').lower()
    if 'jt' in u or 'juta' in u: v *= 1_000_000
    elif 'm' in u or 'miliar' in u: v *= 1_000_000_000
    return int(v)

sroi_metrics = {
    "status": "partial",
    "note":   "SROI final ESS tidak dapat dihitung deterministik dari script — per-tahun breakdown tidak tersedia. Angka di bawah bersifat preliminary dari gross total.",
    "calculated": {},
}

if gross_match:
    gross_val = parse_idr_str(gross_match.group(1))
    sroi_metrics["calculated"]["total_gross_idr"] = gross_val
    sroi_metrics["calculated"]["gross_data_status"] = "extracted"

if investments:
    sroi_metrics["calculated"]["total_investment_idr"] = investments[0]["amount_idr"]
    sroi_metrics["calculated"]["investment_data_status"] = "under_confirmation"

if sroi_blended_raw:
    val = float(sroi_blended_raw.group(1).replace(',','.'))
    sroi_metrics["calculated"]["sroi_blended"] = val
    sroi_metrics["calculated"]["sroi_blended_status"] = "preliminary"
    sroi_metrics["status"] = "preliminary"
else:
    sroi_metrics["calculated"]["sroi_blended"] = None
    sroi_metrics["calculated"]["sroi_blended_status"] = "pending"

sroi_metrics["calculated"]["per_year"] = []  # tidak tersedia
sroi_metrics["calculated"]["per_year_status"] = "pending — yearly breakdown tidak tersedia di script ESS"

print(f"  SROI status: {sroi_metrics['status']}")

# ── COVERAGE STATUS ───────────────────────────────────────────
coverage_status = {
    "bab_1": {"status":"strong",  "inputs":["program_identity","program_positioning"], "risk":"reliable"},
    "bab_2": {"status":"strong",  "inputs":["program_identity","program_positioning"], "risk":"reliable"},
    "bab_3": {"status":"partial", "inputs":["ddat_params","ori_rates"],               "risk":"thin"},
    "bab_4": {"status":"missing", "inputs":[],                                         "risk":"skeleton_only"},
    "bab_5": {"status":"missing", "inputs":[],                                         "risk":"skeleton_only"},
    "bab_6": {"status":"missing", "inputs":[],                                         "risk":"skeleton_only"},
    "bab_7": {
        "status":  "partial",
        "inputs":  ["investment","monetization","ddat_params","ori_rates"],
        "risk":    "thin",
        "notes":   "SROI final pending — per-year breakdown tidak tersedia",
    },
    "bab_8": {"status":"missing", "inputs":[],  "risk":"skeleton_only"},
    "bab_9": {"status":"partial", "inputs":["sroi_metrics"], "risk":"thin"},
}

# ── COMPOSE CANONICAL ─────────────────────────────────────────
canonical = {
    "schema_version": "1.0",
    "case_id":        "ess_2023_2025_v2",
    "created_at":     datetime.now().strftime("%Y-%m-%d"),
    "last_updated":   datetime.now().strftime("%Y-%m-%d"),
    "parser_version": PARSER_VERSION,
    "parser_note":    "ESS-specific parser v2 — jujur tentang keterbatasan data per-tahun",
    "program_identity": {**identity},
    "program_positioning": {
        "tjsl_pillar":    "Pemberdayaan Masyarakat",
        "sdg_alignment":  ["SDG 4 — Pendidikan Berkualitas", "SDG 8 — Pekerjaan Layak"],
        "proper_category":"Beyond Compliance — Inovasi Sosial",
        "policy_basis":   [
            "UU No. 40 Tahun 2007 tentang Perseroan Terbatas Pasal 74",
            "Peraturan Menteri LHK No. 1 Tahun 2021",
        ],
    },
    "source_registry": [{
        "source_id":   "src_ess_01",
        "source_type": "ppt_script",
        "name":        "TJSL_Scripts.md — ess sections",
        "parsed_at":   datetime.now().strftime("%Y-%m-%d"),
        "reliability": "primary",
        "notes":       "Script ESS tidak memiliki per-tahun investment breakdown",
    }],
    # Fields yang tidak tersedia — eksplisit kosong dengan status
    "context_baseline":  {"data_status":"pending"},
    "problem_framing":   {"problem_tree":[], "data_status":"pending"},
    "ideal_conditions":  {"data_status":"pending"},
    "strategy_design":   {"data_status":"pending"},
    "activities":        [],
    "outputs":           [],
    "stakeholders":      [],
    "beneficiaries":     [],
    "outcomes":          [],
    # Fields yang berhasil diekstrak
    "investment":        investments,
    "monetization":      monetization,
    "ddat_params":       ddat_params,
    "ori_rates":         ori_rates,
    "sroi_metrics":      sroi_metrics,
    "learning_signals":  {"loop_1":[], "loop_2":[], "loop_3":[], "data_status":"pending"},
    "evidence_registry": [],
    "uncertainty_flags": [
        {
            "flag_id":   "UF_ESS_YEARLY",
            "field_path":"sroi_metrics.calculated.per_year",
            "reason":    "Per-year investment breakdown tidak tersedia di script ESS — SROI evaluatif tidak dapat dihitung deterministik",
            "severity":  "high",
        },
        {
            "flag_id":   "UF_ESS_INV",
            "field_path":"investment",
            "reason":    "Total investasi tersedia tapi berstatus under_confirmation",
            "severity":  "medium",
        },
    ],
    "coverage_status": coverage_status,
}

# ── WRITE ─────────────────────────────────────────────────────
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
json.dump(canonical, open(OUTPUT_FILE,"w"), indent=2, ensure_ascii=False)

print(f"\nOutput: {OUTPUT_FILE}")
print(f"\n{'='*55}")
print("ESS PARSER COMPLETE")
print(f"  Investments : {len(investments)} entries")
print(f"  Monetization: {len(monetization)} entries")
print(f"  DDAT params : {len(ddat_params)} aspek")
print(f"  ORI rates   : {len(ori_rates)} tahun")
print(f"  SROI status : {sroi_metrics['status']}")
print(f"  Flags       : {len(canonical['uncertainty_flags'])}")
print("="*55)
