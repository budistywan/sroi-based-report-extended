"""
Sprint 10 Gate Validator — doc_parser (Gate B)

Usage:
  python validate_doc_parser.py
  python validate_doc_parser.py --parsed /path/parsed_kresna_doc.json
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--parsed", default=None)
args = parser.parse_args()

SCRIPT_DIR  = Path(__file__).parent
PARSED_FILE = Path(args.parsed) if args.parsed \
    else Path(os.environ.get("PARSED_FILE", SCRIPT_DIR / "parsed_kresna_doc.json"))

print(f"Parsed: {PARSED_FILE.resolve()}")
if not PARSED_FILE.exists():
    print(f"FAIL: {PARSED_FILE} tidak ditemukan"); sys.exit(1)

data   = json.load(open(PARSED_FILE))
ERRORS = []

def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE B1: Struktur output ────────────────────────────────
print("\n=== GATE B1: Struktur output ===")
check(data.get("source_type") == "docx",        "source_type = docx")
check(bool(data.get("document_title")),          "document_title tidak kosong")
check(isinstance(data.get("sections"), list),    "sections adalah list")
check(isinstance(data.get("tables"),   list),    "tables adalah list")
check(isinstance(data.get("signals"),  dict),    "signals adalah dict")
check("stats" in data,                           "stats ada")

# ── GATE B2: Heading hierarchy ──────────────────────────────
print("\n=== GATE B2: Heading hierarchy ===")
sections = data.get("sections", [])
headings = [s for s in sections if s.get("block_type","").startswith("heading")]
check(len(headings) >= 10,
      f"Minimal 10 heading (dapat: {len(headings)})")

# Cek heading_path ada dan berupa list
headings_with_path = [s for s in headings if isinstance(s.get("heading_path"), list) and s["heading_path"]]
check(len(headings_with_path) >= 8,
      f"Minimal 8 heading dengan heading_path (dapat: {len(headings_with_path)})")

# Cek ada hierarchy (path length > 1)
deep_headings = [s for s in sections if len(s.get("heading_path",[])) > 1]
check(len(deep_headings) > 0,
      f"Ada heading dengan path > 1 level (dapat: {len(deep_headings)})")

# ── GATE B3: Preservasi blok ────────────────────────────────
print("\n=== GATE B3: Block preservation ===")
paragraphs = [s for s in sections if s.get("block_type") == "paragraph"]
check(len(paragraphs) >= 50,
      f"Minimal 50 paragraph blocks (dapat: {len(paragraphs)})")

tables = data.get("tables", [])
check(len(tables) >= 5,
      f"Minimal 5 tabel diekstrak (dapat: {len(tables)})")

# Cek tabel punya header dan rows
tables_with_content = [t for t in tables if t.get("header") and t.get("data_rows") is not None]
check(len(tables_with_content) >= 3,
      f"Minimal 3 tabel dengan header dan rows (dapat: {len(tables_with_content)})")

# ── GATE B4: Semantic hints ──────────────────────────────────
print("\n=== GATE B4: Semantic hints ===")
with_hints = [s for s in sections if s.get("semantic_hint")]
check(len(with_hints) > 0,
      f"Ada sections dengan semantic_hint (dapat: {len(with_hints)})")

hint_types = set(s["semantic_hint"] for s in with_hints)
# Jangan overclaim: pastikan hint beragam dan masuk akal
valid_hints = {
    "baseline_or_context","potential","problem_framing","strategy_roadmap",
    "lfa","toc_pathway","ddat_justification","monetization",
    "sroi_result","learning_recommendation",
}
bad_hints = hint_types - valid_hints
check(len(bad_hints) == 0, f"Semua hint valid (bad: {bad_hints})")

# ── GATE B5: Signal detection ────────────────────────────────
print("\n=== GATE B5: Signal detection ===")
signals = data.get("signals", {})
REQUIRED_SIGNALS = ["has_baseline", "has_potential", "has_lfa",
                    "has_toc_narrative", "has_ddat_justification"]
for sig in REQUIRED_SIGNALS:
    check(signals.get(sig) is True,
          f"Signal '{sig}' = True")

# ── GATE B6: Konten kunci terdeteksi ────────────────────────
print("\n=== GATE B6: Konten kunci ada ===")
all_text = " ".join(s.get("text","") for s in sections).lower()
for needle, label in [
    ("kresna",          "Nama program Kresna"),
    ("pertamina",       "Nama perusahaan Pertamina"),
    ("potensi",         "Konten potensi"),
    ("kondisi awal",    "Bab kondisi awal"),
    ("strategi",        "Konten strategi"),
    ("sroi",            "Konten SROI"),
]:
    check(needle in all_text, label)

# ── GATE B7: Tidak ada flattening ────────────────────────────
print("\n=== GATE B7: Tidak ada flattening ===")
# Pastikan tidak semua konten jadi satu blob
max_text_len = max((len(s.get("text","")) for s in sections), default=0)
check(max_text_len < 5000,
      f"Tidak ada blok teks > 5000 chars (max: {max_text_len})")
check(len(sections) >= 100,
      f"Setidaknya 100 sections terpisah (dapat: {len(sections)})")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"DOC PARSER GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("DOC PARSER GATE: ALL PASS")
    print(f"  {len(sections)} sections · {len(tables)} tables")
    print(f"  {len(headings)} headings · {len(with_hints)} with hints")
    print(f"  Signals: {sum(1 for v in signals.values() if v)} active")
    sys.exit(0)
