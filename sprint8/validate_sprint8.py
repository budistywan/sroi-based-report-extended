"""
Sprint 8 Gate Validator — Full Assembly
Gate: ESL_SROI_Report_Full.docx harus valid sebagai laporan utuh 9 bab.

Usage:
  python validate_sprint8.py
  python validate_sprint8.py --docx /p/ESL_SROI_Report_Full.docx \
                              --canonical /p/canonical_snapshot.json
  DOCX_FILE=... CANONICAL_FILE=... python validate_sprint8.py
"""
import sys, os, re, json, argparse, zipfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--docx",      default=None)
parser.add_argument("--canonical", default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
DOCX_FILE     = Path(args.docx)      if args.docx      \
    else Path(os.environ.get("DOCX_FILE",
              SCRIPT_DIR / "ESL_SROI_Report_Full.docx"))
CANONICAL_FILE= Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE",
              SCRIPT_DIR / "canonical_snapshot.json"))

print(f"Docx     : {DOCX_FILE.resolve()}")
print(f"Canonical: {CANONICAL_FILE.resolve()}")

for f in [DOCX_FILE, CANONICAL_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

canonical = json.load(open(CANONICAL_FILE))
pi  = canonical["program_identity"]
sm  = canonical["sroi_metrics"]["calculated"]

# Load XML
with zipfile.ZipFile(DOCX_FILE) as z:
    doc_xml = z.read("word/document.xml").decode("utf-8")
    names   = z.namelist()

plain = re.sub(r"<[^>]+>", " ", doc_xml)

# ── GATE 1: File valid ────────────────────────────────────
print("\n=== GATE 1: File valid ===")
check(DOCX_FILE.exists(),                      "File .docx ada")
check(DOCX_FILE.stat().st_size > 20_000,       f"Ukuran > 20KB ({DOCX_FILE.stat().st_size:,} bytes)")
check("word/document.xml" in names,            "word/document.xml ada")
check("word/styles.xml"   in names,            "word/styles.xml ada")

import subprocess
r = subprocess.run(["unzip","-t",str(DOCX_FILE)], capture_output=True, text=True)
check(r.returncode == 0,                       "ZIP structure valid")

# ── GATE 2: Halaman count ─────────────────────────────────
print("\n=== GATE 2: Halaman dan paragraf ===")
para_count  = len(re.findall(r"<w:p[ >]", doc_xml))
table_count = len(re.findall(r"<w:tbl[ >]", doc_xml))
check(para_count  >= 500,  f"Paragraf ≥ 500 (dapat: {para_count})")
check(para_count  <= 1500, f"Paragraf ≤ 1500 (dapat: {para_count})")
check(table_count >= 10,   f"Tabel ≥ 10 (dapat: {table_count})")

# ── GATE 3: Halaman front-matter ─────────────────────────
print("\n=== GATE 3: Front-matter hadir ===")
check("LEMBAR VERIFIKASI"   in plain, "Lembar Verifikasi ada")
check("KATA PENGANTAR"      in plain, "Kata Pengantar ada")
check("RINGKASAN EKSEKUTIF" in plain, "Ringkasan Eksekutif ada")
check("DAFTAR ISI"          in plain, "Daftar Isi ada")

# ── GATE 4: Semua 9 bab ada ──────────────────────────────
print("\n=== GATE 4: Semua 9 bab ada ===")
BAB_TITLES = [
    ("BAB I",   "PENDAHULUAN"),
    ("BAB II",  "PROFIL"),
    ("BAB III", "METODOLOGI"),
    ("BAB IV",  "KONDISI AWAL"),
    ("BAB V",   "KONDISI IDEAL"),
    ("BAB VI",  "STRATEGI"),
    ("BAB VII", "IMPLEMENTASI"),
    ("BAB VIII","PEMBELAJARAN"),
    ("BAB IX",  "PENUTUP"),
]
for bab, keyword in BAB_TITLES:
    check(bab in plain and keyword in plain,
          f"{bab} ({keyword}) ada di dokumen")

# ── GATE 5: Konten kunci ada ──────────────────────────────
print("\n=== GATE 5: Konten kunci ===")
program_name = pi["program_name"].split()[0]  # "Enduro"
sroi_str     = f"1 : {float(sm['sroi_blended']):.2f}"

for needle, label in [
    (program_name,               f"Nama program '{program_name}'"),
    ("502",                      "Angka investasi ~502jt"),
    ("570",                      "Net compounded ~570jt"),
    (sroi_str,                   f"SROI blended {sroi_str}"),
    ("Lapas Palembang",          "Node Lapas Palembang"),
    ("Milenial Motor",           "Milenial Motor"),
    ("Deadweight",               "Metodologi Deadweight"),
    ("ORI",                      "ORI reference rate"),
    ("REINT",                    "Aspek REINT"),
    ("proxy",                    "Label proxy"),
    ("Dipa Konsultan",           "PT Dipa Konsultan Utama"),
]:
    check(needle in plain, label)

# ── GATE 6: Header + footer ───────────────────────────────
print("\n=== GATE 6: Header & footer ===")
has_header = any("header" in n for n in names)
has_footer = any("footer" in n for n in names)
check(has_header, "Header file ada")
check(has_footer, "Footer file ada")

# Cek isi header
try:
    with zipfile.ZipFile(DOCX_FILE) as z:
        hdr_files = [n for n in names if "header" in n and n.endswith(".xml")]
        if hdr_files:
            hdr_xml = z.read(hdr_files[0]).decode("utf-8")
            hdr_plain = re.sub(r"<[^>]+>", " ", hdr_xml)
            check("Laporan SROI" in hdr_plain or "Enduro" in hdr_plain,
                  "Header berisi nama program")
except: pass

# ── GATE 7: Page size A4 ─────────────────────────────────
print("\n=== GATE 7: Page size A4 ===")
check("11906" in doc_xml, "Page width = 11906 DXA (A4)")
check("16838" in doc_xml, "Page height = 16838 DXA (A4)")

# ── GATE 8: TOC entries ada ───────────────────────────────
print("\n=== GATE 8: TOC entries ===")
check("DAFTAR ISI"   in plain, "DAFTAR ISI heading ada")
# Cek bahwa nomor halaman TOC ada (ii, iii, iv, 1, 28, dll)
check("ii"  in plain, "TOC entry halaman roman ada")
check("28"  in plain, "TOC entry Bab VII (hal 28) ada")

# ── GATE 9: Heading structure ────────────────────────────
print("\n=== GATE 9: Heading structure ===")
pstyles   = re.findall(r'<w:pStyle w:val="([^"]+)"', doc_xml)
h1_count  = pstyles.count("Heading1")
h2_count  = pstyles.count("Heading2")
check(h1_count >= 9,   f"Minimal 9 Heading1 (9 bab + front matter) dapat: {h1_count}")
check(h2_count >= 20,  f"Minimal 20 Heading2 (sub-bab) dapat: {h2_count}")

# ── GATE 10: Canonical snapshot ada ──────────────────────
print("\n=== GATE 10: Self-contained ===")
snapshot = SCRIPT_DIR / "canonical_snapshot.json"
check(snapshot.exists(), "canonical_snapshot.json ada di sprint8 folder")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 8 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("SPRINT 8 GATE: ALL PASS")
    print(f"  {para_count} paragraf · {table_count} tabel")
    print(f"  {DOCX_FILE.stat().st_size:,} bytes · A4 · 9 bab")
    print("Sprint 9 — Orchestrator boleh dimulai.")
    sys.exit(0)
