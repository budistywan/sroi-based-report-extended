"""
Source Extractor — Sprint 7
Sub-parser: deck_script_parser

Input : TJSL_Scripts.md
Output: parsed_source_json[] per program
        canonical_json per program (auto-populated dari script)

Ekstrak dari pptxgenjs script:
  - program_identity (nama, kode, tagline, company, period)
  - investment (total, per tahun jika tersedia)
  - monetization (per aspek per tahun)
  - ddat_params (net_multiplier per aspek)
  - ori_rates (per tahun)
  - sroi_metrics (blended, per tahun)
  - learning_signals (dari slide kesimpulan)

Usage:
  python deck_script_parser.py
  python deck_script_parser.py --input /p/TJSL_Scripts.md --output /p/
  INPUT_FILE=... OUTPUT_DIR=... python deck_script_parser.py
"""

import re
import json
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

PARSER_VERSION = "1.0.0"

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="Deck Script Parser")
parser.add_argument("--input",   default=None)
parser.add_argument("--output",  default=None)
parser.add_argument("--program", default=None, help="Filter program code (ESL/PSN/etc)")
args = parser.parse_args()

SCRIPT_DIR  = Path(__file__).parent
INPUT_FILE  = Path(args.input)  if args.input  \
    else Path(os.environ.get("INPUT_FILE",  "/mnt/user-data/outputs/TJSL_Scripts.md"))
OUTPUT_DIR  = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR",  SCRIPT_DIR))
FILTER_PROG = args.program.upper() if args.program else None

print(f"Input  : {INPUT_FILE.resolve()}")
print(f"Output : {OUTPUT_DIR.resolve()}")
if FILTER_PROG:
    print(f"Filter : {FILTER_PROG} only")

if not INPUT_FILE.exists():
    print(f"FAIL: {INPUT_FILE} tidak ditemukan"); sys.exit(1)

src = open(INPUT_FILE).read()


# ══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════

def clean_idr(s):
    """Konversi string Rp ke integer. Rp 502,46 Jt → 502460000"""
    if not s:
        return 0
    s = s.strip().replace("Rp", "").replace("rp", "").strip()
    s = s.replace(".", "").replace(",", ".")

    multiplier = 1
    if re.search(r'\bjuta\b|\bJuta\b|\bJt\b|\bjt\b', s):
        multiplier = 1_000_000
        s = re.sub(r'\bjuta\b|\bJuta\b|\bJt\b|\bjt\b', '', s, flags=re.IGNORECASE)
    elif re.search(r'\bmiliar\b|\bMiliar\b|\bM\b', s):
        multiplier = 1_000_000_000
        s = re.sub(r'\bmiliar\b|\bMiliar\b|\bM\b', '', s, flags=re.IGNORECASE)

    try:
        return int(float(s.strip()) * multiplier)
    except:
        return 0

def parse_ratio(s):
    """Parse '1 : 1,44' → 1.44"""
    m = re.search(r'1\s*:\s*([\d,\.]+)', str(s))
    if m:
        return float(m.group(1).replace(',', '.'))
    return 0.0

def parse_rate(s):
    """Parse '5,90%' → 0.059"""
    m = re.search(r'([\d,\.]+)\s*%', str(s))
    if m:
        return float(m.group(1).replace(',', '.')) / 100
    return 0.0


# ══════════════════════════════════════════════════════════
# STEP 1: SPLIT SECTIONS PER BATCH
# ══════════════════════════════════════════════════════════

sections = {}
raw_sections = re.split(r'^## ', src, flags=re.MULTILINE)
for section in raw_sections[1:]:
    name = section.split('\n')[0].strip()
    sections[name] = section

print(f"\nDitemukan {len(sections)} sections: {list(sections.keys())}")


# ══════════════════════════════════════════════════════════
# STEP 2: GROUP SECTIONS PER PROGRAM
# ══════════════════════════════════════════════════════════

PROGRAM_MAP = {
    "psn": "PSN", "esd": "ESD", "esl": "ESL",
    "etb": "ETB", "ess": "ESS", "esp": "ESP",
}

program_sections = {}
for sec_name, content in sections.items():
    prefix = sec_name.split('_')[0].lower()
    prog   = PROGRAM_MAP.get(prefix)
    if prog:
        if prog not in program_sections:
            program_sections[prog] = []
        program_sections[prog].append((sec_name, content))

print(f"Program terdeteksi: {sorted(program_sections.keys())}")


# ══════════════════════════════════════════════════════════
# STEP 3: EXTRACTORS
# ══════════════════════════════════════════════════════════

def extract_program_identity(prog_code, all_content):
    """Ekstrak identitas program dari pres.title dan slide cover."""
    identity = {
        "program_code": prog_code,
        "program_name": "",
        "program_tagline": "",
        "company": "PT Pertamina Lubricants",
        "unit": "TJSL CSV",
        "period_start": 2023,
        "period_end": 2025,
    }

    # Nama dari pres.title
    m = re.search(r'pres\.title\s*=\s*"([^"]+)"', all_content)
    if m:
        title = m.group(1)
        # Ambil sebelum " — SROI"
        name_part = re.split(r'\s*[—–-]\s*SROI', title)[0].strip()
        identity["program_name"] = name_part

    # Tagline dari subtitle slide cover
    taglines = re.findall(
        r'addText\("([^"]{30,120})"[^)]*(?:y:2\.[3-9]|y:[3-4])',
        all_content
    )
    # Ambil tagline pertama yang bukan boilerplate
    boilerplate = {"SROI Program Report","PT PERTAMINA LUBRICANTS","PROGRAM TJSL CSV"}
    for tl in taglines:
        if tl not in boilerplate and len(tl) > 30 and "\\" not in tl:
            identity["program_tagline"] = tl.strip()
            break

    return identity


def extract_investment(all_content):
    """Ekstrak data investasi — total dan per tahun jika tersedia."""
    investments = []

    # Per tahun dari object literal: { yr:"2023", inv:128108409, ... }
    yr_pattern = re.findall(
        r'\{\s*yr\s*:\s*"?(202[3-5])"?\s*,\s*inv\s*:\s*([\d]+)',
        all_content
    )
    if yr_pattern:
        for yr, inv in yr_pattern:
            investments.append({
                "year":         int(yr),
                "node":         "total",
                "amount_idr":   int(inv),
                "data_status":  "under_confirmation",
                "display_status": "present_as_pending",
                "source_refs":  ["src_01"],
            })
    else:
        # Fallback: total investasi dari slide cover
        m = re.search(
            r'"Rp\s*([\d,\.]+\s*(?:Jt|M|juta|miliar))"'
            r'[^}]*sub\s*:\s*"total investasi',
            all_content, re.IGNORECASE
        )
        if m:
            total = clean_idr(m.group(1))
            if total > 0:
                per_year = total // 3
                for yr in [2023, 2024, 2025]:
                    investments.append({
                        "year":           yr,
                        "node":           "total",
                        "amount_idr":     per_year,
                        "data_status":    "proxy",
                        "display_status": "present_as_proxy",
                        "source_refs":    ["src_01"],
                        "note":           "Estimasi merata — data per tahun tidak tersedia di script",
                    })

    return investments


def extract_monetization(all_content):
    """Ekstrak monetisasi per aspek per tahun."""
    monetization = []

    # Pola: { id:"LUB", label:"...", vals:{ "2023":"Rp 20,68 Jt", ... } }
    aspect_blocks = re.finditer(
        r'\{\s*id\s*:\s*"([A-Z]+)"[^{]*vals\s*:\s*\{([^}]+)\}',
        all_content
    )

    for m in aspect_blocks:
        asp_code = m.group(1)
        vals_str = m.group(2)
        year_vals = re.findall(r'"(202[3-5])"\s*:\s*"Rp\s*([\d,\.]+\s*(?:Jt|jt|juta|M|miliar)?)"',
                               vals_str, re.IGNORECASE)
        for yr, val in year_vals:
            amount = clean_idr(val)
            if amount > 0:
                is_proxy = asp_code in ["REINT","CONF","JSP","TEFA","OMZ","JOB"]
                monetization.append({
                    "monetization_id": f"MON_{asp_code}_{yr}",
                    "aspect_code":     asp_code,
                    "aspect_name":     asp_code,
                    "year":            int(yr),
                    "gross_idr":       amount,
                    "data_status":     "proxy"   if is_proxy else "observed",
                    "display_status":  "present_as_proxy" if is_proxy else "present_as_final",
                    "source_refs":     ["src_01"],
                })

    # Fallback: cari gross/net dari { yr:"2023", gross:..., net:... }
    if not monetization:
        yr_rows = re.findall(
            r'\{\s*yr\s*:\s*"?(202[3-5])"?\s*,\s*gross\s*:\s*"Rp\s*([\d,\.]+\s*(?:Jt|jt|Juta|juta|M)?)"',
            all_content, re.IGNORECASE
        )
        for yr, gross_str in yr_rows:
            gross = clean_idr(gross_str)
            if gross > 0:
                monetization.append({
                    "monetization_id": f"MON_TOTAL_{yr}",
                    "aspect_code":     "TOTAL",
                    "aspect_name":     "Total (tidak terperinci per aspek)",
                    "year":            int(yr),
                    "gross_idr":       gross,
                    "data_status":     "derived",
                    "display_status":  "present_as_inferred",
                    "source_refs":     ["src_01"],
                })

    return monetization


def extract_ddat(all_content):
    """Ekstrak DDAT params — net multiplier per aspek."""
    ddat = {}

    # Pola: mult:"×0,54" atau netMultiplier:0.54 atau haircut:46
    # Format 1: dari fiksasi table
    mult_patterns = re.findall(
        r'"([A-Z]{2,5})"\s*[,\s]+[^"]*(?:mult|Mult|netMult|net_mult)[^"]*"?×?\s*(0\.[0-9]+)',
        all_content
    )
    for asp, mult in mult_patterns:
        if asp not in ddat:
            ddat[asp] = {"net_multiplier": float(mult), "data_status": "final",
                         "justification": "extracted from script"}

    # Format 2: dari objek fiksasi dengan DW/AT/DO
    fiksasi_blocks = re.finditer(
        r'"([A-Z]{2,5})"\s*:\s*\{[^}]*(?:dw|deadweight|DW)[^}]*?(0\.\d+)[^}]*\}',
        all_content, re.IGNORECASE
    )
    for m in fiksasi_blocks:
        asp = m.group(1)
        if asp not in ddat and len(asp) <= 5:
            ddat[asp] = {"net_multiplier": 0.5, "data_status": "proxy",
                         "justification": "partial extraction — verify manually"}

    # Fallback per aspek yang ditemukan di monetization
    asp_codes = set(re.findall(r'\bid\s*:\s*"([A-Z]{2,5})"', all_content))
    for asp in asp_codes:
        if asp not in ddat and asp not in {"PSN","ESD","ESL","ETB","ESS","ESP"}:
            ddat[asp] = {"net_multiplier": 0.5, "data_status": "pending",
                         "justification": "tidak tersedia di script — default 0.5"}

    return ddat


def extract_ori_rates(all_content):
    """Ekstrak ORI rates per tahun."""
    ori = {}

    # Pola: { yr:"2023", label:"ORI023T3", rate:"5,90%" }
    ori_rows = re.finditer(
        r'\{\s*yr\s*:\s*"?(202[3-5])"?\s*,\s*label\s*:\s*"([^"]+)"\s*,\s*rate\s*:\s*"([^"]+)"',
        all_content
    )
    for m in ori_rows:
        yr    = m.group(1)
        label = m.group(2)
        rate  = parse_rate(m.group(3))
        ori[yr] = {
            "rate":            rate,
            "series":          label,
            "compound_factor": 1.0,   # akan dihitung saat validasi
            "terminal_year":   yr == "2025",
        }

    # Hitung compound factor jika belum ada
    if "2023" in ori and "2024" in ori and "2025" in ori:
        r23 = ori["2023"]["rate"]
        r24 = ori["2024"]["rate"]
        ori["2023"]["compound_factor"] = round((1 + r23) * (1 + r24), 4)
        ori["2024"]["compound_factor"] = round(1 + r24, 4)
        ori["2025"]["compound_factor"] = 1.0

    return ori


def extract_sroi_metrics(all_content):
    """Ekstrak SROI blended dan per tahun."""
    metrics = {"status": "not_calculated", "calculated": {}}

    # SROI blended
    m = re.search(r'1\s*:\s*([\d,]+)\s*\(blended', all_content)
    if m:
        metrics["calculated"]["sroi_blended"] = float(m.group(1).replace(',','.'))
        metrics["status"] = "extracted"

    # Per tahun dari object literal
    per_year = []
    yr_rows = re.finditer(
        r'\{\s*yr\s*:\s*"?(202[3-5])"?\s*,'
        r'[^}]*inv\s*:\s*([\d]+)'
        r'[^}]*gross\s*:\s*([\d]+)'
        r'[^}]*net\s*:\s*([\d]+)'
        r'[^}]*nc\s*:\s*([\d]+)'
        r'[^}]*ratio\s*:\s*"([^"]+)"',
        all_content
    )
    for m in yr_rows:
        per_year.append({
            "year":       int(m.group(1)),
            "investment": int(m.group(2)),
            "gross":      int(m.group(3)),
            "net":        int(m.group(4)),
            "compounded": int(m.group(5)),
            "sroi_ratio": parse_ratio(m.group(6)),
        })

    if per_year:
        metrics["calculated"]["per_year"] = per_year
        # Hitung total
        metrics["calculated"]["total_investment_idr"]     = sum(r["investment"]  for r in per_year)
        metrics["calculated"]["total_gross_idr"]          = sum(r["gross"]       for r in per_year)
        metrics["calculated"]["total_net_idr"]            = sum(r["net"]         for r in per_year)
        metrics["calculated"]["total_net_compounded_idr"] = sum(r["compounded"]  for r in per_year)
        if "sroi_blended" not in metrics["calculated"]:
            inv   = metrics["calculated"]["total_investment_idr"]
            nc    = metrics["calculated"]["total_net_compounded_idr"]
            if inv > 0:
                metrics["calculated"]["sroi_blended"] = round(nc / inv, 4)
        metrics["status"] = "extracted"

    return metrics


def extract_learning_signals(all_content):
    """Ekstrak learning signals dari slide kesimpulan."""
    ls = {"loop_1": [], "loop_2": [], "loop_3": [], "lfa_reflections": [],
          "data_status": "derived"}

    # Cari teks dari slide kesimpulan/pembelajaran
    concl_texts = re.findall(
        r'addText\("([^"]{20,200})"[^)]*(?:y:[3-9]\.|y:5\.|y:4\.)',
        all_content
    )
    for t in concl_texts:
        t = t.strip()
        if any(kw in t.lower() for kw in ["berhasil","terbukti","proof","capaian","sukses"]):
            ls["loop_3"].append(t)
        elif any(kw in t.lower() for kw in ["perlu","butuh","rekomendasi","perbaikan"]):
            ls["loop_2"].append(t)
        elif len(t) > 30:
            ls["loop_1"].append(t)

    # Batasi agar tidak terlalu panjang
    for key in ["loop_1","loop_2","loop_3"]:
        ls[key] = ls[key][:3]

    return ls


# ══════════════════════════════════════════════════════════
# STEP 4: BUILD PARSED SOURCE JSON PER PROGRAM
# ══════════════════════════════════════════════════════════

PALETTE_MAP = {
    "PSN": "C — Midnight Indigo",
    "ESD": "A — Deep Ocean",
    "ESL": "B — Marine Teal",
    "ETB": "F — Crimson Frontier",
    "ESS": "A — Deep Ocean",
    "ESP": "E — Savanna Dusk",
}

all_parsed   = []
all_canonical = []

for prog_code in sorted(program_sections.keys()):
    if FILTER_PROG and prog_code != FILTER_PROG:
        continue

    print(f"\n--- Parsing {prog_code} ---")
    batches     = program_sections[prog_code]
    all_content = "\n".join(content for _, content in batches)

    # Ekstrak semua komponen
    identity    = extract_program_identity(prog_code, all_content)
    investments = extract_investment(all_content)
    monetization= extract_monetization(all_content)
    ddat        = extract_ddat(all_content)
    ori         = extract_ori_rates(all_content)
    sroi        = extract_sroi_metrics(all_content)
    learning    = extract_learning_signals(all_content)

    # Parsed source JSON
    parsed = {
        "source_id":      f"src_{prog_code.lower()}_01",
        "source_type":    "ppt_script",
        "name":           f"TJSL_Scripts.md — {prog_code.lower()} sections",
        "program_code":   prog_code,
        "parsed_at":      datetime.now().isoformat(),
        "parser_version": PARSER_VERSION,
        "parsed_sections": {
            "program_identity":  identity,
            "investment":        investments,
            "monetization":      monetization,
            "ddat_params":       ddat,
            "ori_rates":         ori,
            "sroi_metrics":      sroi,
            "learning_signals":  learning,
        },
        "uncertainty_flags": [],
        "coverage": {
            "investment":   "strong"  if any(i["data_status"]=="under_confirmation" for i in investments) else "proxy",
            "monetization": "strong"  if any(m["aspect_code"] not in ["TOTAL"] for m in monetization) else "partial",
            "ddat":         "strong"  if ddat else "missing",
            "ori":          "strong"  if len(ori) == 3 else "partial",
            "sroi_metrics": "strong"  if sroi["status"] == "extracted" else "missing",
        }
    }

    # Flag data yang tidak lengkap
    if not investments:
        parsed["uncertainty_flags"].append({
            "flag_id": "UF_INV", "field_path": "investment",
            "reason": "Tidak ditemukan data investasi", "severity": "high"
        })
    if not monetization:
        parsed["uncertainty_flags"].append({
            "flag_id": "UF_MON", "field_path": "monetization",
            "reason": "Tidak ditemukan data monetisasi per aspek", "severity": "high"
        })

    # Deduplicate monetization — ambil entri unik per (aspect_code, year)
    seen_mon = {}
    deduped  = []
    for m in monetization:
        key = (m["aspect_code"], m["year"])
        if key not in seen_mon:
            seen_mon[key] = True
            deduped.append(m)
    monetization = deduped

    # Deduplicate investment per (year, node)
    seen_inv = {}
    deduped_inv = []
    for inv in investments:
        key = (inv["year"], inv.get("node",""))
        if key not in seen_inv:
            seen_inv[key] = True
            deduped_inv.append(inv)
    investments = deduped_inv

    all_parsed.append(parsed)

    # Canonical JSON (scaffold)
    canonical_json = {
        "schema_version": "1.0",
        "case_id":        f"{prog_code.lower()}_2023_2025_v1",
        "created_at":     datetime.now().strftime("%Y-%m-%d"),
        "last_updated":   datetime.now().strftime("%Y-%m-%d"),
        "program_identity": {**identity, "palette": PALETTE_MAP.get(prog_code,"")},
        "program_positioning": {
            "tjsl_pillar": "Pemberdayaan Masyarakat",
            "proper_category": "Beyond Compliance — Inovasi Sosial",
            "policy_basis": [
                "UU No. 40 Tahun 2007 tentang Perseroan Terbatas Pasal 74",
                "Peraturan Menteri LHK No. 1 Tahun 2021",
            ]
        },
        "source_registry": [{
            "source_id":   f"src_{prog_code.lower()}_01",
            "source_type": "ppt_script",
            "name":        f"TJSL_Scripts.md — {prog_code.lower()} sections",
            "parsed_at":   datetime.now().strftime("%Y-%m-%d"),
            "reliability": "primary",
        }],
        "context_baseline":  {"data_status": "pending"},
        "problem_framing":   {"problem_tree": [], "data_status": "pending"},
        "ideal_conditions":  {"data_status": "pending"},
        "strategy_design":   {"data_status": "pending"},
        "activities":        [],
        "outputs":           [],
        "stakeholders":      [],
        "beneficiaries":     [],
        "investment":        investments,
        "outcomes":          [],
        "monetization":      monetization,
        "ddat_params":       ddat,
        "ori_rates":         ori,
        "sroi_metrics":      sroi,
        "learning_signals":  learning,
        "evidence_registry": [],
        "uncertainty_flags": parsed["uncertainty_flags"],
        "coverage_status":   {
            f"bab_{i}": {"status": "missing", "inputs": [], "risk": "skeleton_only"}
            for i in range(1, 10)
        }
    }
    # Override bab_7 jika data tersedia
    if sroi["status"] == "extracted" and investments and monetization:
        canonical_json["coverage_status"]["bab_7"] = {
            "status": "partial", "inputs": ["investment","monetization","sroi_metrics"],
            "risk": "reliable", "notes": "Diekstrak dari script — perlu validasi manual"
        }

    all_canonical.append(canonical_json)

    # Coverage summary
    cov = parsed["coverage"]
    print(f"  identity    : {identity['program_name'][:40]}")
    print(f"  investments : {len(investments)} entries [{cov['investment']}]")
    print(f"  monetization: {len(monetization)} entries [{cov['monetization']}]")
    print(f"  ddat_params : {len(ddat)} aspek [{cov['ddat']}]")
    print(f"  ori_rates   : {len(ori)} tahun [{cov['ori']}]")
    print(f"  sroi_metrics: {sroi['status']} [{cov['sroi_metrics']}]")
    sroi_b = sroi["calculated"].get("sroi_blended", "—")
    print(f"  sroi_blended: {sroi_b}")


# ══════════════════════════════════════════════════════════
# STEP 5: WRITE OUTPUT
# ══════════════════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tulis parsed source per program
for parsed in all_parsed:
    pc   = parsed["program_code"]
    path = OUTPUT_DIR / f"parsed_source_{pc.lower()}.json"
    json.dump(parsed, open(path,"w"), indent=2, ensure_ascii=False)
    print(f"\nParsed: {path.name}")

# Tulis canonical JSON per program
for canonical_json in all_canonical:
    pc   = canonical_json["program_identity"]["program_code"]
    path = OUTPUT_DIR / f"canonical_{pc.lower()}_extracted.json"
    json.dump(canonical_json, open(path,"w"), indent=2, ensure_ascii=False)
    print(f"Canonical: {path.name}")

# Tulis registry semua parsed sources
registry = {
    "generated_at": datetime.now().isoformat(),
    "parser_version": PARSER_VERSION,
    "source_file": str(INPUT_FILE.resolve()),
    "programs_parsed": len(all_parsed),
    "programs": [
        {
            "program_code": p["program_code"],
            "source_id":    p["source_id"],
            "coverage":     p["coverage"],
            "sroi_blended": p["parsed_sections"]["sroi_metrics"]["calculated"].get("sroi_blended","—"),
            "flags":        len(p["uncertainty_flags"]),
        }
        for p in all_parsed
    ]
}
reg_path = OUTPUT_DIR / "parsed_registry.json"
json.dump(registry, open(reg_path,"w"), indent=2, ensure_ascii=False)

print(f"\nRegistry: {reg_path.name}")
print("\n" + "="*60)
print("DECK SCRIPT PARSER — selesai")
print(f"  Programs  : {len(all_parsed)}")
print(f"  Output dir: {OUTPUT_DIR.resolve()}")
print("="*60)
