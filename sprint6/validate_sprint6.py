"""
Sprint 6 Gate Validator — Narrative Builder (framing + context + learning)

Usage:
  python validate_sprint6.py
  python validate_sprint6.py --rest /p/chapters_semantic_rest.json --contract /p/
  REST_FILE=... CONTRACT_FILE=... python validate_sprint6.py
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--rest",     default=None)
parser.add_argument("--contract", default=None)
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
REST_FILE     = Path(args.rest)     if args.rest     \
    else Path(os.environ.get("REST_FILE",     SCRIPT_DIR / "chapters_semantic_rest.json"))
CONTRACT_FILE = Path(args.contract) if args.contract \
    else Path(os.environ.get("CONTRACT_FILE", SCRIPT_DIR.parent / "sprint0/render_contract_v1.json"))

print(f"Rest      : {REST_FILE.resolve()}")
print(f"Contract  : {CONTRACT_FILE.resolve()}")

for f in [REST_FILE, CONTRACT_FILE]:
    if not f.exists():
        print(f"\nFAIL: {f} tidak ditemukan"); sys.exit(1)

chapters  = json.load(open(REST_FILE))
contract  = json.load(open(CONTRACT_FILE))
VALID_TYPES = set(contract["supported_block_types"])

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

# ── GATE 1: Semua bab ada ────────────────────────────────
print("\n=== GATE 1: Semua bab ada ===")
expected = {"bab_1","bab_2","bab_3","bab_4","bab_5","bab_6","bab_8","bab_9"}
found    = {c["chapter_id"] for c in chapters}
check(found == expected, f"8 bab lengkap: {sorted(found)}")
check("bab_7" not in found, "bab_7 tidak ada (sudah di Sprint 3B)")

# ── GATE 2: Setiap bab punya minimal 8 blocks ────────────
print("\n=== GATE 2: Minimal blocks per bab ===")
for ch in chapters:
    nb = len(ch.get("blocks",[]))
    check(nb >= 8, f"{ch['chapter_id']}: {nb} blocks (min 8)")

# ── GATE 3: Block types valid ────────────────────────────
print("\n=== GATE 3: Block types valid per bab ===")
for ch in chapters:
    bad = [b["type"] for b in ch["blocks"] if b.get("type") not in VALID_TYPES]
    check(len(bad)==0, f"{ch['chapter_id']}: semua block types valid (invalid: {bad})")

# ── GATE 4: Heading_1 tepat 1 per bab ────────────────────
print("\n=== GATE 4: heading_1 tepat 1 per bab ===")
for ch in chapters:
    h1s = [b for b in ch["blocks"] if b.get("type")=="heading_1"]
    check(len(h1s)==1, f"{ch['chapter_id']}: tepat 1 heading_1 (dapat: {len(h1s)})")

# ── GATE 5: Bab partial punya callout_gap ────────────────
print("\n=== GATE 5: Bab partial punya callout_gap ===")
PARTIAL_BABS = {"bab_4","bab_5"}
for ch in chapters:
    cid = ch["chapter_id"]
    if cid in PARTIAL_BABS:
        has_gap = any(b.get("type")=="callout_gap" for b in ch["blocks"])
        check(has_gap, f"{cid} (partial) punya callout_gap")

# ── GATE 6: callout_gap punya gap_type ───────────────────
print("\n=== GATE 6: callout_gap punya gap_type ===")
VALID_GAPS = set(contract.get("field_schemas",{}).get("gap_type_enum",[]))
for ch in chapters:
    for b in ch["blocks"]:
        if b.get("type") == "callout_gap":
            check("gap_type" in b,
                  f"{ch['chapter_id']} callout_gap punya gap_type")
            if "gap_type" in b:
                check(b["gap_type"] in VALID_GAPS,
                      f"{ch['chapter_id']} gap_type '{b['gap_type']}' valid")

# ── GATE 7: Column widths tabel ───────────────────────────
print("\n=== GATE 7: Column widths tabel = 9638 DXA ===")
for ch in chapters:
    for b in ch["blocks"]:
        if b.get("type") in ["table","table_borderless","table_accent_col"]:
            cw    = b.get("column_widths",[])
            total = sum(cw)
            if total != 9638:
                ERRORS.append(f"  FAIL: {ch['chapter_id']} table column_widths={total} (harus 9638)")
            else:
                print(f"  PASS: {ch['chapter_id']} table column_widths=9638")

# ── GATE 8: Proxy/inferred punya source_refs ─────────────
# callout_gap dikecualikan — ia adalah deklarasi kekosongan, bukan klaim data
print("\n=== GATE 8: Proxy/inferred punya source_refs ===")
for ch in chapters:
    for b in ch["blocks"]:
        ds = b.get("display_status","")
        bt = b.get("type","")
        if ds in ["present_as_proxy","present_as_inferred"] and bt != "callout_gap":
            check(bool(b.get("source_refs",[])),
                  f"{ch['chapter_id']} [{bt}] {ds} punya source_refs")

# ── GATE 9: Konten kunci ada di bab yang benar ───────────
print("\n=== GATE 9: Konten kunci ada ===")
ch_map = {c["chapter_id"]: " ".join(
    str(b.get("text",""))+str(b.get("rows",""))+str(b.get("items",""))
    for b in c["blocks"]
) for c in chapters}

checks = [
    ("bab_1", "SROI",              "bab_1 menyebut SROI"),
    ("bab_1", "PROPER",            "bab_1 menyebut PROPER"),
    ("bab_2", "Pertamina",         "bab_2 menyebut Pertamina"),
    ("bab_3", "Deadweight",        "bab_3 menyebut Deadweight"),
    ("bab_3", "ORI",               "bab_3 menyebut ORI"),
    ("bab_4", "WBP",               "bab_4 menyebut WBP"),
    ("bab_5", "reintegrasi",       "bab_5 menyebut reintegrasi"),
    ("bab_6", "Milenial Motor",    "bab_6 menyebut Milenial Motor"),
    ("bab_6", "roadmap",           "bab_6 menyebut roadmap"),
    ("bab_8", "Loop",              "bab_8 menyebut Loop"),
    ("bab_9", "1 : 1.14",          "bab_9 mencantumkan SROI 1:1,14"),
    ("bab_9", "rekomendasi",       "bab_9 menyebut rekomendasi"),
]
for cid, needle, label in checks:
    check(needle.lower() in ch_map.get(cid,"").lower(), label)

# ── GATE 10: builder_mode konsisten ──────────────────────
print("\n=== GATE 10: builder_mode assignment ===")
EXPECTED_MODES = {
    "bab_1":"framing","bab_2":"framing","bab_3":"framing",
    "bab_4":"context","bab_5":"context","bab_6":"context",
    "bab_8":"learning","bab_9":"learning",
}
for ch in chapters:
    cid = ch["chapter_id"]
    check(ch.get("builder_mode") == EXPECTED_MODES.get(cid),
          f"{cid} builder_mode = {ch.get('builder_mode')}")

# ── HASIL ────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"SPRINT 6 GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    total = sum(len(c["blocks"]) for c in chapters)
    print("SPRINT 6 GATE: ALL PASS")
    print(f"  {len(chapters)} bab · {total} blocks total")
    for c in chapters:
        print(f"    {c['chapter_id']}: {len(c['blocks'])} blocks [{c['builder_mode']}]")
    print("Sprint 7 — Source Extractor boleh dimulai.")
    sys.exit(0)
