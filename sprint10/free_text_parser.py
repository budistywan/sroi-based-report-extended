"""
free_text_parser.py — Sprint 10B
Parser untuk catatan bebas → structured parsed items.

Bedakan:
  - fact_candidate   : angka, rasio, klaim terukur
  - instruction      : perintah/arahan dari user
  - interpretation_candidate : penilaian evaluatif
  - limitation_note  : catatan keterbatasan/caveat

Usage:
  python free_text_parser.py --input /path/notes.txt --output /path/parsed.json
  echo "teks..." | python free_text_parser.py --stdin --output /path/parsed.json
"""

import json, re, sys, os, argparse
from pathlib import Path
from datetime import datetime

PARSER_VERSION = "1.0.0"

parser = argparse.ArgumentParser()
parser.add_argument("--input",  default=None)
parser.add_argument("--output", default=None)
parser.add_argument("--stdin",  action="store_true")
args = parser.parse_args()

SCRIPT_DIR   = Path(__file__).parent
OUTPUT_FILE  = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_FILE", SCRIPT_DIR / "parsed_free_text_example.json"))

# ── SAMPLE INPUT jika tidak ada file ─────────────────────────
SAMPLE_TEXT = """
Sprint 9.3 Review Notes — ESL SROI Report

Beberapa hal yang perlu dirapikan sebelum laporan final:

1. Gunakan hanya dua istilah resmi:
   - Observed direct return
   - Blended SROI
   Jangan campur dengan "observed blended direct return" atau istilah tidak konsisten.

2. Fakta terukur yang sudah dikonfirmasi:
   - Blended SROI 1 : 1,03 (evaluatif, 2023-2025)
   - Total investasi Rp 502.460.181
   - Net benefit compounded Rp 519.625.266
   - Observed direct return 1 : 0,29 (hanya transaksi tercatat)

3. Keterbatasan yang harus diakui:
   - Data investasi 2023 dan 2024 berstatus under_confirmation
   - Proxy REINT dan CONF belum diverifikasi dari survei peserta
   - Bab IV masih menggunakan baseline programatik, bukan data BPS

4. Instruksi tambahan:
   - Hapus semua kalimat "SROI final belum dihitung"
   - Tambahkan definisi tegas perbedaan Observed direct return vs Blended SROI
   - Bab VIII jangan lagi memunculkan angka yang bertentangan dengan Bab VII

5. Penilaian evaluatif:
   - Pipeline orkestrasi sudah sehat end-to-end
   - Narasi Bab VII kuat, Bab IV masih lemah
   - QA 0 error, renderer_ready = True
"""

if args.stdin:
    text = sys.stdin.read()
elif args.input and Path(args.input).exists():
    text = open(args.input).read()
    print(f"Input: {args.input}")
else:
    text = SAMPLE_TEXT
    print("Input: [sample text — no file provided]")

print(f"Output: {OUTPUT_FILE}")

# ══════════════════════════════════════════════════════════════
# DETECTION PATTERNS
# ══════════════════════════════════════════════════════════════

# Rasio SROI / Return
RATIO_PATTERNS = [
    r'(?:SROI|sroi|return|ratio)\s*[=:]*\s*1\s*[:\-]\s*([\d,\.]+)',
    r'1\s*[:\-]\s*([\d,\.]+)\s*(?:\(|$|\s)',
]

# Angka rupiah
IDR_PATTERN = r'Rp\.?\s*([\d\.]+(?:[\.,]\d+)*)\s*(?:juta|ribu|miliar|M|Jt|jt)?'

# Persentase
PCT_PATTERN  = r'([\d,\.]+)\s*%'

# Instruksi keywords
INSTRUCTION_MARKERS = [
    r'^(?:gunakan|pakai|hapus|tambahkan|ganti|ubah|jangan|harus|wajib|perlu|perbaiki|sesuaikan)',
    r'^(?:use|remove|add|replace|change|do not|must|should|fix|update|ensure)',
    r'\btolong\b|\bplease\b|\bpastikan\b|\bsebaiknya\b',
]

# Limitation markers
LIMITATION_MARKERS = [
    r'belum\s+(?:tersedia|diverifikasi|dikonfirmasi|lengkap|final)',
    r'(?:masih|sedang)\s+(?:pending|under_confirmation|proxy|menunggu)',
    r'keterbatasan|limitation|caveat|catatan|perlu\s+dikonfirmasi',
    r'data\s+(?:tidak|belum)\s+',
    r'berstatus\s+(?:under_confirmation|proxy|pending|partial)',
]

# Evaluatif
EVALUATIVE_MARKERS = [
    r'(?:sudah|masih|belum|cukup|sangat|terlihat|tampak|menunjukkan)',
    r'(?:kuat|lemah|sehat|baik|buruk|bersih|solid|tipis)',
    r'(?:berhasil|gagal|lolos|pass|fail)',
    r'(?:pipeline|narasi|validator|laporan)\s+(?:sudah|masih|belum)',
]

# Terminology SROI yang harus dikenali
SROI_TERMS = {
    "Observed direct return": "observed_direct_return",
    "observed direct return":  "observed_direct_return",
    "Blended SROI":            "blended_sroi",
    "blended SROI":            "blended_sroi",
    "blended sroi":            "blended_sroi",
    "SROI blended":            "blended_sroi",
    "under_confirmation":      "status_under_confirmation",
    "proxy":                   "status_proxy",
    "pending":                 "status_pending",
    "partial":                 "status_partial",
}

# ══════════════════════════════════════════════════════════════
# ITEM CLASSIFIERS
# ══════════════════════════════════════════════════════════════

def classify_line(line: str) -> str:
    """Klasifikasi satu baris teks."""
    l = line.strip().lower()
    if not l:
        return "empty"
    if any(re.search(p, l, re.IGNORECASE) for p in INSTRUCTION_MARKERS):
        return "instruction"
    if any(re.search(p, l, re.IGNORECASE) for p in LIMITATION_MARKERS):
        return "limitation_note"
    if any(re.search(p, l, re.IGNORECASE) for p in EVALUATIVE_MARKERS):
        return "interpretation_candidate"
    return "fact_candidate"

def extract_numbers(line: str) -> list:
    """Ekstrak semua angka signifikan dari satu baris."""
    found = []

    # Rasio SROI
    for pat in RATIO_PATTERNS:
        for m in re.finditer(pat, line, re.IGNORECASE):
            try:
                val = float(m.group(1).replace(',','.'))
                found.append({"value_type":"ratio","value":val,"raw":m.group(0).strip()})
            except: pass

    # Rupiah
    for m in re.finditer(IDR_PATTERN, line, re.IGNORECASE):
        raw_num = m.group(1).replace('.','').replace(',','.')
        try:
            val = float(raw_num)
            found.append({"value_type":"currency_idr","value":val,"raw":m.group(0).strip()})
        except: pass

    # Persentase
    for m in re.finditer(PCT_PATTERN, line):
        try:
            val = float(m.group(1).replace(',','.'))
            found.append({"value_type":"percentage","value":val,"raw":m.group(0).strip()})
        except: pass

    return found

def detect_terminology(line: str) -> list:
    """Deteksi istilah SROI khusus."""
    found = []
    for term, tag in SROI_TERMS.items():
        if term in line:
            found.append({"term": term, "semantic_tag": tag})
    return found

def compute_confidence(item_type: str, line: str, numbers: list) -> float:
    """Hitung confidence berdasarkan konteks."""
    if item_type == "instruction":
        return 0.95
    if item_type == "limitation_note":
        return 0.90
    if item_type == "fact_candidate" and numbers:
        return 0.85
    if item_type == "fact_candidate" and not numbers:
        return 0.60
    if item_type == "interpretation_candidate":
        return 0.70
    return 0.50

# ══════════════════════════════════════════════════════════════
# MAIN PARSING
# ══════════════════════════════════════════════════════════════

lines  = text.split('\n')
items  = []
seen   = set()  # dedup

for raw_line in lines:
    line = raw_line.strip()
    if not line or len(line) < 4:
        continue
    # Dedup
    if line in seen:
        continue
    seen.add(line)

    item_type  = classify_line(line)
    if item_type == "empty":
        continue

    numbers    = extract_numbers(line)
    terms      = detect_terminology(line)
    confidence = compute_confidence(item_type, line, numbers)

    item = {
        "item_type":  item_type,
        "text":       line,
        "confidence": round(confidence, 2),
    }

    if numbers:
        item["numbers"] = numbers

    if terms:
        item["terminology"] = terms

    # Tambah semantic tag jika ada terminology match
    if terms:
        item["semantic_tag"] = terms[0]["semantic_tag"]
    elif item_type == "instruction":
        item["semantic_tag"] = "instruction"
    elif item_type == "limitation_note":
        item["semantic_tag"] = "data_limitation"

    items.append(item)

# ── SUMMARY ───────────────────────────────────────────────────
type_counts = {}
for it in items:
    t = it["item_type"]
    type_counts[t] = type_counts.get(t,0) + 1

# ── COMPOSE OUTPUT ────────────────────────────────────────────
output = {
    "source_type":    "free_text",
    "parsed_at":      datetime.now().isoformat(),
    "parser_version": PARSER_VERSION,
    "stats": {
        "total_lines":   len([l for l in lines if l.strip()]),
        "items_extracted": len(items),
        "by_type":       type_counts,
    },
    "items": items,
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
json.dump(output, open(OUTPUT_FILE,"w"), indent=2, ensure_ascii=False)

print(f"\n{'='*55}")
print("FREE TEXT PARSER COMPLETE")
print(f"  Items extracted: {len(items)}")
for t,n in sorted(type_counts.items(), key=lambda x:-x[1]):
    print(f"    {t:<30} × {n}")
print("="*55)
