"""
QA Checker — Sprint 5
SROI Report System

Layer: Consistency & Evidence Checker
Input : chapter_semantic_bab7.json (Handoff E dari Narrative Builder)
        handoff_b.json (Financial Engine — audit log)
        chapter_outline_bab7.json (Point Builder — reference)
        render_contract_v1.json (Renderer constraints)
Output: qa_report.json + renderer_ready_chapter_json (Handoff F)

Pemeriksaan:
  1. Angka di blocks harus ada di calc_audit_log
  2. display_status proxy/pending wajib punya source_refs
  3. Tidak ada angka baru yang lahir di luar audit_log (overclaim detector)
  4. Konsistensi istilah: output vs outcome vs impact tidak tertukar
  5. outline → narrative consistency (semua poin outline terwakili)
  6. Block types sesuai render contract
  7. Semua tabel punya column_widths total 9638 DXA
  8. renderer_ready: true/false per bab

Usage:
  python qa_checker.py
  python qa_checker.py --semantic /p/ --handoff-b /p/ --outline /p/ --contract /p/ --output /p/
  SEMANTIC_FILE=... HANDOFF_B_FILE=... python qa_checker.py
"""

import json
import re
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

QA_VERSION = "1.0.0"

# ── PATH CONFIG ──────────────────────────────────────────
parser = argparse.ArgumentParser(description="QA Checker")
parser.add_argument("--semantic",  default=None)
parser.add_argument("--handoff-b", default=None, dest="handoff_b")
parser.add_argument("--outline",   default=None)
parser.add_argument("--contract",  default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
SEMANTIC_FILE = Path(args.semantic)  if args.semantic  \
    else Path(os.environ.get("SEMANTIC_FILE",  SCRIPT_DIR.parent / "sprint3/chapter_semantic_bab7.json"))
HANDOFF_B     = Path(args.handoff_b) if args.handoff_b \
    else Path(os.environ.get("HANDOFF_B_FILE", SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
OUTLINE_FILE  = Path(args.outline)   if args.outline   \
    else Path(os.environ.get("OUTLINE_FILE",   SCRIPT_DIR.parent / "sprint3/chapter_outline_bab7.json"))
CONTRACT_FILE = Path(args.contract)  if args.contract  \
    else Path(os.environ.get("CONTRACT_FILE",  SCRIPT_DIR.parent / "sprint0/render_contract_v1.json"))
OUTPUT_DIR    = Path(args.output)    if args.output    \
    else Path(os.environ.get("OUTPUT_DIR",     SCRIPT_DIR))

print(f"Semantic  : {SEMANTIC_FILE.resolve()}")
print(f"Handoff B : {HANDOFF_B.resolve()}")
print(f"Outline   : {OUTLINE_FILE.resolve()}")
print(f"Contract  : {CONTRACT_FILE.resolve()}")
print(f"Output    : {OUTPUT_DIR.resolve()}")

for f in [SEMANTIC_FILE, HANDOFF_B, OUTLINE_FILE, CONTRACT_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

semantic_raw = json.load(open(SEMANTIC_FILE))
handoff_b    = json.load(open(HANDOFF_B))
outline_raw  = json.load(open(OUTLINE_FILE))
contract     = json.load(open(CONTRACT_FILE))

semantic = semantic_raw if isinstance(semantic_raw, list) else [semantic_raw]
outline  = outline_raw  if isinstance(outline_raw,  list) else [outline_raw]
bab7     = next((b for b in semantic if b.get("chapter_id") == "bab_7"), None)
bab7_out = next((b for b in outline  if b.get("chapter_id") == "bab_7"), None)

if not bab7:
    print("FAIL: bab_7 tidak ditemukan di semantic"); sys.exit(1)

calc      = handoff_b["sroi_metrics"]["calculated"]
audit_log = handoff_b["calc_audit_log"]
audit_map = {e["field"]: e["value"] for e in audit_log}
fin_tables = {t["table_id"]: t for t in handoff_b["financial_tables"]}
VALID_TYPES = set(contract["supported_block_types"])

blocks = bab7["blocks"]

# ══════════════════════════════════════════════════════════
# QA FINDINGS — struktur temuan
# ══════════════════════════════════════════════════════════

findings = []   # semua temuan
flags    = []   # hanya yang blocking (error)
warnings = []   # non-blocking (warn)

def flag(check_id, block_idx, block_type, message, severity="error"):
    entry = {
        "check_id":   check_id,
        "block_idx":  block_idx,
        "block_type": block_type,
        "message":    message,
        "severity":   severity,
    }
    findings.append(entry)
    if severity == "error":
        flags.append(entry)
        print(f"  ✕ [{check_id}] block[{block_idx}] {block_type}: {message}")
    else:
        warnings.append(entry)
        print(f"  ~ [{check_id}] block[{block_idx}] {block_type}: {message}")

def ok(check_id, msg):
    print(f"  ✓ [{check_id}] {msg}")


# ══════════════════════════════════════════════════════════
# CHECK 1 — Block types sesuai render contract
# ══════════════════════════════════════════════════════════
print("\n--- Check 1: Block types valid ---")
unknown_types = []
for i, b in enumerate(blocks):
    bt = b.get("type", "")
    if bt not in VALID_TYPES:
        flag("C1", i, bt, f"Block type '{bt}' tidak ada di render contract", "error")
        unknown_types.append(bt)

if not unknown_types:
    ok("C1", f"Semua {len(blocks)} block types valid")


# ══════════════════════════════════════════════════════════
# CHECK 2 — Required fields per block type
# ══════════════════════════════════════════════════════════
print("\n--- Check 2: Required fields per block ---")
req_map = contract.get("required_fields_per_block", {})
c2_errors = 0
for i, b in enumerate(blocks):
    bt = b.get("type","")
    required = req_map.get(bt, [])
    for field in required:
        if field not in b:
            flag("C2", i, bt, f"Required field '{field}' tidak ada", "error")
            c2_errors += 1

if c2_errors == 0:
    ok("C2", "Semua required fields terpenuhi di setiap block")


# ══════════════════════════════════════════════════════════
# CHECK 3 — Column widths tabel = 9638 DXA
# ══════════════════════════════════════════════════════════
print("\n--- Check 3: Column widths tabel = 9638 DXA ---")
c3_ok = 0
for i, b in enumerate(blocks):
    if b.get("type") in ["table","table_borderless","table_accent_col","table_total_row"]:
        cw    = b.get("column_widths", [])
        total = sum(cw)
        if total != 9638:
            flag("C3", i, b["type"],
                 f"column_widths total = {total} DXA (harus 9638)", "error")
        else:
            c3_ok += 1

if c3_ok > 0:
    ok("C3", f"{c3_ok} tabel dengan column_widths = 9638 DXA")


# ══════════════════════════════════════════════════════════
# CHECK 4 — display_status proxy/pending wajib source_refs
# ══════════════════════════════════════════════════════════
print("\n--- Check 4: Proxy/pending wajib punya source_refs ---")
c4_ok = 0
for i, b in enumerate(blocks):
    ds = b.get("display_status","")
    if ds in ["present_as_proxy","present_as_pending","present_as_inferred"]:
        refs = b.get("source_refs", [])
        if not refs:
            flag("C4", i, b.get("type",""),
                 f"display_status={ds} tapi source_refs kosong", "error")
        else:
            c4_ok += 1

if c4_ok > 0:
    ok("C4", f"{c4_ok} block proxy/pending memiliki source_refs")


# ══════════════════════════════════════════════════════════
# CHECK 5 — Angka kunci ada di audit_log (overclaim detector)
# ══════════════════════════════════════════════════════════
print("\n--- Check 5: Angka kunci traceable ke audit_log ---")

# Kumpulkan semua angka signifikan dari blocks (> 1 juta)
def extract_numbers(text):
    """Ekstrak angka dari text — cari pola Rp X,XXX,XXX"""
    raw = re.findall(r'[\d,]+', str(text))
    nums = set()
    for r in raw:
        try:
            n = int(r.replace(',',''))
            if n > 1_000_000:   # hanya angka > 1 juta yang signifikan
                nums.add(n)
        except:
            pass
    return nums

# Kumpulkan semua nilai dari audit_log (rounded ke integer)
audit_values = set(int(round(v)) for v in audit_map.values() if isinstance(v, (int,float)))

# Tambahkan nilai dari financial tables rows
for tbl in handoff_b["financial_tables"]:
    for row in tbl.get("rows", []):
        for cell in row:
            for n in extract_numbers(str(cell)):
                audit_values.add(n)

# Cek angka di teks paragraph dan tabel blocks
c5_suspect = []
for i, b in enumerate(blocks):
    bt = b.get("type","")
    # Cek teks
    text_to_check = b.get("text","") if bt.startswith("paragraph") or bt.startswith("callout") else ""
    nums_in_block = extract_numbers(text_to_check)

    for n in nums_in_block:
        # Cari angka ini di audit_values (toleransi ±1 untuk floating point)
        found = any(abs(n - av) <= 1 for av in audit_values)
        if not found:
            # Cek apakah ini mungkin sub-angka yang valid (misal: 128,108,409 → 128108409)
            flag("C5", i, bt,
                 f"Angka {n:,} di teks tidak ditemukan di audit_log — potensi overclaim",
                 "warning")   # warning, bukan error — karena bisa jadi angka deskriptif
            c5_suspect.append((i, bt, n))

if not c5_suspect:
    ok("C5", "Semua angka signifikan di paragraph blocks traceable ke audit_log/tables")
else:
    ok("C5", f"{len(c5_suspect)} angka perlu dikonfirmasi (lihat warning)")


# ══════════════════════════════════════════════════════════
# CHECK 6 — Konsistensi istilah output/outcome/impact
# ══════════════════════════════════════════════════════════
print("\n--- Check 6: Konsistensi istilah ---")

TERM_RULES = {
    # Istilah yang sering tertukar
    "output":  ["output", "hasil langsung", "keluaran"],
    "outcome": ["outcome", "perubahan", "dampak yang dirasakan"],
    "impact":  ["impact", "dampak sistemik", "transformasi"],
}

# Cek apakah "output" dipakai untuk menggambarkan perubahan sosial (seharusnya outcome)
# dan "outcome" dipakai untuk menggambarkan jumlah kegiatan (seharusnya output)
c6_flags = []
for i, b in enumerate(blocks):
    text = b.get("text","").lower()
    # Pola problematik: "output berupa perubahan" atau "outcome berupa jumlah"
    if re.search(r'\boutput\b.{0,30}\bperubahan\b', text):
        flag("C6", i, b.get("type",""),
             "Kemungkinan salah istilah: 'output' dipakai untuk 'perubahan' (seharusnya outcome)",
             "warning")
        c6_flags.append(i)
    if re.search(r'\boutcome\b.{0,30}\bjumlah\b', text):
        flag("C6", i, b.get("type",""),
             "Kemungkinan salah istilah: 'outcome' dipakai untuk 'jumlah' (seharusnya output)",
             "warning")
        c6_flags.append(i)

if not c6_flags:
    ok("C6", "Tidak ada mismatch istilah output/outcome/impact terdeteksi")


# ══════════════════════════════════════════════════════════
# CHECK 7 — Outline → Narrative consistency
# Setiap argument_point di outline harus terwakili di narrative
# ══════════════════════════════════════════════════════════
print("\n--- Check 7: Outline → Narrative consistency ---")

if bab7_out:
    all_block_text = " ".join(
        str(b.get("text","")) + str(b.get("rows","")) + str(b.get("items",""))
        for b in blocks
    ).lower()

    covered     = []
    not_covered = []

    for ap in bab7_out.get("argument_points", []):
        label = ap.get("label","")
        # Cari kata kunci dari poin di teks blocks
        point_words = [w for w in ap.get("point","").lower().split()
                       if len(w) > 5 and w not in
                       {"dengan","untuk","dalam","yang","dari","pada","telah","tidak",
                        "adalah","setiap","dapat","sudah","bahwa","akan","serta","atau"}]

        # Poin dianggap covered jika minimal 2 kata kunci muncul
        matches = sum(1 for w in point_words if w in all_block_text)
        if matches >= 2:
            covered.append(label)
        else:
            not_covered.append((label, ap.get("point","")[:60]))

    ok("C7", f"{len(covered)}/{len(covered)+len(not_covered)} outline points terwakili di narrative")
    for label, snippet in not_covered:
        flag("C7", -1, "outline_point",
             f"Point {label} tidak jelas terwakili: '{snippet}...'",
             "warning")
else:
    flag("C7", -1, "outline", "Outline bab_7 tidak ditemukan", "warning")


# ══════════════════════════════════════════════════════════
# CHECK 8 — Tabel financial berasal dari Handoff B
# ══════════════════════════════════════════════════════════
print("\n--- Check 8: Tabel financial berasal dari Handoff B ---")
c8_ok = 0
for i, b in enumerate(blocks):
    if b.get("type") == "table":
        tid = b.get("table_id","")
        if tid:
            if tid not in fin_tables:
                flag("C8", i, "table",
                     f"table_id '{tid}' tidak ada di financial_tables Handoff B", "error")
            else:
                # Cek bahwa rows-nya identik dengan yang di Handoff B
                expected_rows = fin_tables[tid]["rows"]
                actual_rows   = b.get("rows", [])
                if expected_rows != actual_rows:
                    flag("C8", i, "table",
                         f"Rows tabel '{tid}' berbeda dari Handoff B — possible data drift", "error")
                else:
                    c8_ok += 1

if c8_ok > 0:
    ok("C8", f"{c8_ok} tabel financial identik dengan Handoff B (no data drift)")


# ══════════════════════════════════════════════════════════
# CHECK 9 — Heading structure
# ══════════════════════════════════════════════════════════
print("\n--- Check 9: Heading structure ---")
h1s = [b for b in blocks if b.get("type") == "heading_1"]
h2s = [b for b in blocks if b.get("type") == "heading_2"]

if len(h1s) != 1:
    flag("C9", -1, "heading_1", f"Jumlah heading_1 = {len(h1s)} (harus tepat 1)", "error")
else:
    ok("C9", f"heading_1: tepat 1 — '{h1s[0].get('text','')[:40]}'")

if len(h2s) < 5:
    flag("C9", -1, "heading_2", f"Jumlah heading_2 = {len(h2s)} (minimal 5)", "error")
else:
    ok("C9", f"heading_2: {len(h2s)} sub-bab")


# ══════════════════════════════════════════════════════════
# COMPOSE QA REPORT
# ══════════════════════════════════════════════════════════

n_errors   = len(flags)
n_warnings = len(warnings)
renderer_ready = n_errors == 0

qa_report = {
    "qa_version":      QA_VERSION,
    "chapter_id":      "bab_7",
    "generated_at":    datetime.now().isoformat(),
    "renderer_ready":  renderer_ready,
    "summary": {
        "total_blocks":   len(blocks),
        "errors":         n_errors,
        "warnings":       n_warnings,
        "checks_run":     9,
    },
    "findings":        findings,
    "revision_instructions": (
        [] if renderer_ready else
        [f["message"] for f in flags]
    ),
}


# ══════════════════════════════════════════════════════════
# COMPOSE HANDOFF F (QA → Renderer)
# ══════════════════════════════════════════════════════════

# Deteksi signals dari findings
has_proxy   = any(b.get("display_status") == "present_as_proxy"   for b in blocks)
has_pending = any(b.get("display_status") == "present_as_pending"  for b in blocks)
has_gap     = any(b.get("type") == "callout_gap"                   for b in blocks)
has_inferred= any(b.get("display_status") == "present_as_inferred" for b in blocks)

# Outline alignment
outline_covered_ratio = len(covered) / max(len(covered)+len(not_covered),1) if bab7_out else 0
if outline_covered_ratio >= 0.9:
    alignment_status = "aligned"
elif outline_covered_ratio >= 0.7:
    alignment_status = "partial"
else:
    alignment_status = "diverged"

handoff_f = {
    "renderer_ready":   renderer_ready,
    "chapter_id":       "bab_7",
    "blocks":           blocks,  # sama persis dari semantic — QA tidak mengubah isi
    "reference_outline": {
        "chapter_id":      bab7_out.get("chapter_id","") if bab7_out else "",
        "core_claim":      bab7_out.get("core_claim","")  if bab7_out else "",
        "argument_points": bab7_out.get("argument_points",[]) if bab7_out else [],
        "known_gaps":      bab7_out.get("known_gaps",[])      if bab7_out else [],
    },
    "qa_render_signals": {
        "outline_alignment_status": alignment_status,
        "render_gap_note":          has_gap,
        "render_inference_note":    has_inferred,
    },
    "style_hints": {
        "proxy_badge":     has_proxy,
        "warning_callout": has_pending,
        "pending_note":    has_pending,
        "gap_note":        has_gap,
        "inference_note":  has_inferred,
    },
    "qa_report_ref":    "qa_report.json",
    "generated_at":     datetime.now().isoformat(),
}


# ══════════════════════════════════════════════════════════
# WRITE OUTPUT
# ══════════════════════════════════════════════════════════

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
qa_path = OUTPUT_DIR / "qa_report.json"
hf_path = OUTPUT_DIR / "handoff_f.json"

json.dump(qa_report,  open(qa_path, "w"), indent=2, ensure_ascii=False)
json.dump(handoff_f,  open(hf_path, "w"), indent=2, ensure_ascii=False)

print(f"\nOutput:")
print(f"  {qa_path}")
print(f"  {hf_path}")


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "="*55)
print(f"QA CHECKER — bab_7")
print(f"  Blocks checked   : {len(blocks)}")
print(f"  Checks run       : 9")
print(f"  Errors           : {n_errors}")
print(f"  Warnings         : {n_warnings}")
print(f"  Outline coverage : {outline_covered_ratio*100:.0f}%  [{alignment_status}]")
print(f"  renderer_ready   : {renderer_ready}")
print("-"*55)
if n_errors == 0:
    print("QA PASS — Handoff F siap untuk Renderer")
else:
    print(f"QA FAIL — {n_errors} error harus diperbaiki sebelum render")
print("="*55)

sys.exit(0 if renderer_ready else 1)
