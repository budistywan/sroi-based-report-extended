"""
Sprint 3B Gate Validator — Narrative Builder (builder_sroi)
Memverifikasi chapter_semantic_bab7.json sebelum masuk QA Layer.

Usage:
  python validate_sprint3b.py
  python validate_sprint3b.py --semantic /p/ --handoff-b /p/ --contract /p/
  SEMANTIC_FILE=... HANDOFF_B_FILE=... CONTRACT_FILE=... python validate_sprint3b.py
"""
import json
import sys
import os
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--semantic",  default=None)
parser.add_argument("--handoff-b", default=None, dest="handoff_b")
parser.add_argument("--contract",  default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
SEMANTIC_FILE = Path(args.semantic)  if args.semantic  \
    else Path(os.environ.get("SEMANTIC_FILE",  SCRIPT_DIR / "chapter_semantic_bab7.json"))
HANDOFF_B     = Path(args.handoff_b) if args.handoff_b \
    else Path(os.environ.get("HANDOFF_B_FILE", SCRIPT_DIR.parent / "sprint1/handoff_b.json"))
CONTRACT_FILE = Path(args.contract)  if args.contract  \
    else Path(os.environ.get("CONTRACT_FILE",  SCRIPT_DIR.parent / "sprint0/render_contract_v1.json"))

print(f"Semantic  : {SEMANTIC_FILE.resolve()}")
print(f"Handoff B : {HANDOFF_B.resolve()}")
print(f"Contract  : {CONTRACT_FILE.resolve()}")

for f in [SEMANTIC_FILE, HANDOFF_B, CONTRACT_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

raw       = json.load(open(SEMANTIC_FILE))
hb        = json.load(open(HANDOFF_B))
contract  = json.load(open(CONTRACT_FILE))

semantic = raw if isinstance(raw, list) else [raw]
bab7     = next((b for b in semantic if b.get("chapter_id")=="bab_7"), None)

ERRORS = []
def check(cond, msg):
    if not cond:
        ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

calc       = hb["sroi_metrics"]["calculated"]
audit_vals = {e["field"]: e["value"] for e in hb["calc_audit_log"]}
VALID_TYPES = set(contract["supported_block_types"])
VALID_GAPS  = set(contract.get("field_schemas",{}).get("gap_type_enum",[]))
fin_table_ids = {t["table_id"] for t in hb["financial_tables"]}

# ── GATE 1: Struktur ─────────────────────────────────────
print("\n=== GATE 1: Struktur chapter_semantic ===")
check(bab7 is not None,                         "bab_7 ditemukan")
if not bab7: sys.exit(1)
check(bab7.get("chapter_type")=="implementation_sroi", "chapter_type = implementation_sroi")
check(bab7.get("builder_mode")=="sroi",         "builder_mode = sroi")
check(isinstance(bab7.get("blocks",[]), list),  "blocks adalah array")
check(len(bab7.get("blocks",[])) >= 30,         f"minimal 30 blok (dapat: {len(bab7.get('blocks',[]))})")

# ── GATE 2: Block types valid ─────────────────────────────
print("\n=== GATE 2: Block types sesuai render contract ===")
invalid_types = []
for b in bab7["blocks"]:
    bt = b.get("type","")
    if bt not in VALID_TYPES:
        invalid_types.append(bt)
check(len(invalid_types)==0,
      f"Semua block types valid (invalid: {invalid_types})" if invalid_types
      else "Semua block types valid sesuai render contract")

# ── GATE 3: Required fields per block type ───────────────
print("\n=== GATE 3: Required fields per block ===")
req = contract.get("required_fields_per_block", {})
for b in bab7["blocks"]:
    bt = b.get("type","")
    required = req.get(bt, [])
    for field in required:
        check(field in b,
              f"Block [{bt}] memiliki required field '{field}'")

# ── GATE 4: Angka dari audit_log ─────────────────────────
print("\n=== GATE 4: Angka kunci ada di blocks ===")
all_text = " ".join(
    str(b.get("text","")) + str(b.get("rows","")) + str(b.get("items",""))
    for b in bab7["blocks"]
)
for key, label in [
    ("sroi_blended",         "SROI blended"),
    ("total_investment",     "Total investasi"),
    ("total_net_compounded", "Net compounded"),
]:
    val = audit_vals.get(key, 0)
    # Cari angka dalam teks (tanpa desimal untuk investasi besar)
    needle = f"{val:,.0f}"
    check(needle in all_text,
          f"{label} {needle} ada di blocks")

# ── GATE 5: Proxy wajib punya display_status ─────────────
print("\n=== GATE 5: Proxy blocks punya display_status present_as_proxy ===")
for b in bab7["blocks"]:
    ds = b.get("display_status","")
    if ds == "present_as_proxy":
        check(bool(b.get("source_refs",[])),
              f"Block [{b['type']}] proxy punya source_refs")

# ── GATE 6: Callout_gap punya gap_type ───────────────────
print("\n=== GATE 6: callout_gap wajib punya gap_type ===")
for b in bab7["blocks"]:
    if b.get("type") == "callout_gap":
        check("gap_type" in b,            "callout_gap punya field gap_type")
        check(b.get("gap_type") in ["data_unavailable","evidence_insufficient",
                                     "pending_field_validation","out_of_scope"],
              f"gap_type valid: {b.get('gap_type')}")

# ── GATE 7: Tabel financial valid ────────────────────────
print("\n=== GATE 7: Tabel financial berasal dari Handoff B ===")
for b in bab7["blocks"]:
    if b.get("type") in ["table","table_borderless","table_accent_col","table_total_row"]:
        tid = b.get("table_id")
        if tid:
            check(tid in fin_table_ids,
                  f"table_id '{tid}' ada di financial tables Handoff B")
        # Column widths harus total 9638
        cw = b.get("column_widths",[])
        if cw:
            check(sum(cw)==9638,
                  f"Table [{tid or 'inline'}] column_widths total = {sum(cw)} DXA")

# ── GATE 8: Heading 1 ada tepat 1 ────────────────────────
print("\n=== GATE 8: Heading struktur ===")
h1_blocks = [b for b in bab7["blocks"] if b.get("type")=="heading_1"]
h2_blocks = [b for b in bab7["blocks"] if b.get("type")=="heading_2"]
check(len(h1_blocks)==1,            f"Tepat 1 heading_1 (dapat: {len(h1_blocks)})")
check(len(h2_blocks)>=5,            f"Minimal 5 heading_2 — sub-bab (dapat: {len(h2_blocks)})")
check("BAB VII" in h1_blocks[0].get("text",""),
      "heading_1 berisi 'BAB VII'")

# ── GATE 9: Callout wajib ada untuk proxy & Lapas ────────
print("\n=== GATE 9: Callout wajib ada ===")
callout_texts = " ".join(
    b.get("text","") for b in bab7["blocks"]
    if b.get("type","").startswith("callout_")
)
check("proxy" in callout_texts.lower() or "REINT" in callout_texts,
      "Ada callout yang menyebut proxy")
check("Palembang" in callout_texts or "belum menghasilkan" in callout_texts,
      "Ada callout yang menyebut Lapas Palembang / temuan jujur")
check("Milenial Motor" in callout_texts or "eks-WBP" in callout_texts,
      "Ada callout yang menyebut Milenial Motor / proof-of-concept")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 3B GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    nb = len(bab7["blocks"])
    print("SPRINT 3B GATE: ALL PASS")
    print(f"  {nb} blok tervalidasi — siap ke QA Layer")
    print("Sprint 4 — Renderer boleh dimulai.")
    sys.exit(0)
