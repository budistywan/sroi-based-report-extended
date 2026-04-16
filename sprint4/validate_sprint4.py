"""
Sprint 4 Gate Validator — Renderer
Gate: .docx yang dihasilkan pipeline harus valid dan materially identical
      dengan struktur Bab 7 yang diharapkan.

Usage:
  python validate_sprint4.py
  python validate_sprint4.py --docx /path/ESL_Report_Bab7.docx --semantic /path/chapter_semantic_bab7.json
  DOCX_FILE=... SEMANTIC_FILE=... python validate_sprint4.py
"""
import sys
import os
import json
import argparse
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--docx",     default=None)
parser.add_argument("--semantic", default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
DOCX_FILE     = Path(args.docx)     if args.docx     \
    else Path(os.environ.get("DOCX_FILE",     SCRIPT_DIR / "ESL_Report_Bab7.docx"))
# Default: cari snapshot lokal di sprint4 — cross-sprint sebagai fallback
_semantic_local    = SCRIPT_DIR / "chapter_semantic_bab7.json"
_semantic_fallback = SCRIPT_DIR.parent / "sprint3/chapter_semantic_bab7.json"
SEMANTIC_FILE = Path(args.semantic) if args.semantic \
    else Path(os.environ.get("SEMANTIC_FILE",
              str(_semantic_local) if _semantic_local.exists() else str(_semantic_fallback)))

print(f"Docx     : {DOCX_FILE.resolve()}")
print(f"Semantic : {SEMANTIC_FILE.resolve()}")

for f in [DOCX_FILE, SEMANTIC_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

semantic_raw = json.load(open(SEMANTIC_FILE))
semantic     = semantic_raw if isinstance(semantic_raw, list) else [semantic_raw]
bab7         = next((b for b in semantic if b.get("chapter_id")=="bab_7"), None)

# ── GATE 1: File valid ────────────────────────────────────
print("\n=== GATE 1: Docx file valid ===")
check(DOCX_FILE.exists(),                       "File .docx ada")
check(DOCX_FILE.stat().st_size > 10_000,        f"Ukuran file > 10KB ({DOCX_FILE.stat().st_size:,} bytes)")

# Validasi via unzip (cek ZIP structure)
result = subprocess.run(["unzip", "-t", str(DOCX_FILE)],
                        capture_output=True, text=True)
check(result.returncode == 0,                   "ZIP structure valid")
check("word/document.xml" in result.stdout,     "word/document.xml ada di dalam .docx")
check("word/styles.xml" in result.stdout,       "word/styles.xml ada")

# ── GATE 2: Paragraph count ───────────────────────────────
print("\n=== GATE 2: Paragraph count ===")
import zipfile, re
with zipfile.ZipFile(DOCX_FILE) as z:
    doc_xml = z.read("word/document.xml").decode("utf-8")

para_count = len(re.findall(r"<w:p[ >]", doc_xml))
check(para_count >= 100,   f"Paragraf ≥ 100 (dapat: {para_count})")
check(para_count <= 600,   f"Paragraf ≤ 600 (dapat: {para_count}) — tidak overflow")

# ── GATE 3: Konten kunci ada di XML ──────────────────────
print("\n=== GATE 3: Konten kunci ada di dokumen ===")
plain = re.sub(r"<[^>]+>", " ", doc_xml)  # strip tags

for needle, label in [
    ("BAB VII",               "Judul bab BAB VII"),
    ("502",                   "Angka investasi ~502jt"),
    ("570",                   "Angka net compounded ~570jt"),
    ("1 : 1.14",              "SROI blended 1:1,14"),
    ("Lapas Palembang",       "Node Lapas Palembang"),
    ("Milenial Motor",        "Node Milenial Motor"),
    ("REINT",                 "Aspek REINT"),
    ("CONF",                  "Aspek CONF"),
    ("under_confirmation",    "Status under_confirmation (badge pending)"),
    ("proxy",                 "Label proxy"),
    ("ORI023T3",              "ORI series 2023"),
    ("Pertamina Lubricants",  "Footer PT Pertamina Lubricants"),
]:
    check(needle in plain or needle in doc_xml, label)

# ── GATE 4: Tabel ada ─────────────────────────────────────
print("\n=== GATE 4: Tabel ada ===")
table_count = len(re.findall(r"<w:tbl[ >]", doc_xml))
check(table_count >= 6,    f"Minimal 6 tabel (dapat: {table_count})")

# ── GATE 5: Heading structure ─────────────────────────────
print("\n=== GATE 5: Heading structure ===")
h1_count = doc_xml.count('"Heading1"') + doc_xml.count("'Heading1'") + \
           doc_xml.count('Heading 1') + doc_xml.count("HEADING_1")
# Lebih reliabel: cek styleId
h_refs = re.findall(r'w:styleId="([^"]+)"', doc_xml)
# Alternatif: cek via pStyle
pstyles = re.findall(r'<w:pStyle w:val="([^"]+)"', doc_xml)
h1s = [s for s in pstyles if '1' in s and 'ead' in s.lower() or s == 'Heading1']
h2s = [s for s in pstyles if '2' in s and 'ead' in s.lower() or s == 'Heading2']
# Simpler: just count occurrences of heading style in pStyle
h1_count = pstyles.count('Heading1')
h2_count = pstyles.count('Heading2')
check(h1_count >= 1,       f"Heading 1 ada (dapat: {h1_count})")
check(h2_count >= 5,       f"Minimal 5 Heading 2 — sub-bab (dapat: {h2_count})")

# ── GATE 6: Block count vs semantic ──────────────────────
print("\n=== GATE 6: Block count vs semantic input ===")
if bab7:
    n_blocks = len(bab7.get("blocks", []))
    # Setiap block menghasilkan minimal 1 docx element
    # Beberapa block (callout, table) menghasilkan lebih dari 1
    check(para_count >= n_blocks,
          f"Para count ({para_count}) ≥ input blocks ({n_blocks})")

# ── GATE 7: Header & footer ───────────────────────────────
print("\n=== GATE 7: Header & footer ada ===")
try:
    with zipfile.ZipFile(DOCX_FILE) as z:
        names = z.namelist()
    has_header = any("header" in n for n in names)
    has_footer = any("footer" in n for n in names)
    check(has_header, "Header file ada")
    check(has_footer, "Footer file ada")
except Exception as e:
    ERRORS.append(f"  FAIL: Tidak bisa cek header/footer — {e}")

# ── GATE 8: Page size A4 ─────────────────────────────────
print("\n=== GATE 8: Page size A4 ===")
try:
    with zipfile.ZipFile(DOCX_FILE) as z:
        doc_xml2 = z.read("word/document.xml").decode("utf-8")
    # A4: width=11906, height=16838 DXA
    check("11906" in doc_xml2, "Page width = 11906 DXA (A4)")
    check("16838" in doc_xml2, "Page height = 16838 DXA (A4)")
except Exception as e:
    ERRORS.append(f"  FAIL: {e}")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 4 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 4 GATE: ALL PASS")
    print(f"  {para_count} paragraf · {table_count} tabel · {DOCX_FILE.stat().st_size:,} bytes")
    print("Sprint 5 — QA Layer boleh dimulai.")
    sys.exit(0)
