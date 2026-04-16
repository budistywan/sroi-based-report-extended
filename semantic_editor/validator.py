"""
validator.py — Semantic Editor
Memvalidasi chapter semantic JSON yang sudah diedit user
sebelum diimport kembali ke pipeline.

Checks:
  1. JSON valid dan parseable
  2. Struktur chapter-level terjaga (chapter_id, blocks)
  3. block_type tidak berubah dari original
  4. Field finansial tidak berubah (substance lock)
  5. Protected blocks tidak dihapus
  6. Block baru yang ditambahkan punya struktur valid
  7. source_refs tidak dihilangkan dari block yang memilikinya

Usage:
  python validator.py edited.json
  python validator.py edited.json --original original.json
  python validator.py edited.json --original original.json --strict
"""

import json, re, sys, argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

parser = argparse.ArgumentParser(description="Semantic JSON Validator")
parser.add_argument("edited",             help="Path ke file hasil edit user")
parser.add_argument("--original", "-o",   default=None,
                    help="Path ke original semantic JSON (untuk diff checks)")
parser.add_argument("--strict",           action="store_true",
                    help="Gagal jika ada warning, bukan hanya error")
parser.add_argument("--quiet",            action="store_true",
                    help="Hanya tampilkan summary")
args = parser.parse_args()

# ── VALID BLOCK TYPES ─────────────────────────────────────────
VALID_BLOCK_TYPES = {
    "heading_1", "heading_2", "heading_3",
    "paragraph", "paragraph_lead", "paragraph_small",
    "table", "table_borderless",
    "callout_info", "callout_warning", "callout_success",
    "callout_neutral", "callout_gap",
    "metric_card_3col", "bar_chart_text",
    "bullet_list", "numbered_list",
    "divider", "divider_thick",
}

# Block types yang punya data finansial — jangan ubah values-nya
FINANCIAL_BLOCK_TYPES = {"table", "table_borderless", "metric_card_3col", "bar_chart_text"}

# Field di setiap block yang tidak boleh diubah user
PROTECTED_BLOCK_FIELDS = {
    "type", "table_id", "column_widths", "source_refs",
    "display_status", "gap_type", "data_points", "max_value",
}

# Regex untuk deteksi angka finansial signifikan
NUM_PAT = re.compile(
    r'Rp\s*[\d.,]+|'       # Rp 502.460.181
    r'1\s*:\s*[\d.,]+|'    # 1 : 1.14
    r'\d{6,}|'             # angka >= 6 digit
    r'\d+[.,]\d{2,}'       # desimal bermakna
)


@dataclass
class ValidationResult:
    errors:   list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    infos:    list = field(default_factory=list)

    def error(self, msg):   self.errors.append(msg)
    def warning(self, msg): self.warnings.append(msg)
    def info(self, msg):    self.infos.append(msg)

    @property
    def valid(self): return len(self.errors) == 0

    @property
    def clean(self): return len(self.errors) == 0 and len(self.warnings) == 0


def load_json(path: str, label: str) -> Optional[dict]:
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data[0] if isinstance(data, list) else data
    except json.JSONDecodeError as e:
        print(f"FAIL: {label} bukan JSON yang valid — {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"FAIL: {label} tidak ditemukan: {path}")
        sys.exit(1)


def extract_numbers(text: str) -> set:
    """Ekstrak angka finansial dari string."""
    if not isinstance(text, str):
        return set()
    return set(NUM_PAT.findall(text))


def validate_chapter_structure(ch: dict, r: ValidationResult):
    """Check 1: Struktur chapter-level."""
    if "chapter_id" not in ch:
        r.error("chapter_id hilang dari chapter")
    if "blocks" not in ch:
        r.error("blocks hilang dari chapter")
        return False
    if not isinstance(ch["blocks"], list):
        r.error("blocks harus berupa array")
        return False
    if len(ch["blocks"]) == 0:
        r.warning("blocks kosong — chapter tidak punya konten")
    return True


def validate_blocks(blocks: list, r: ValidationResult):
    """Check 2+3: Setiap block valid."""
    for i, block in enumerate(blocks):
        btype = block.get("type", "MISSING")

        # type wajib ada
        if btype == "MISSING":
            r.error(f"block[{i}]: field 'type' tidak ada")
            continue

        # type harus dari daftar valid
        if btype not in VALID_BLOCK_TYPES:
            r.error(f"block[{i}]: block_type '{btype}' tidak dikenal — "
                    f"cek EDITING_RULES_GLOBAL.md")

        # Block dengan text: harus string
        if "text" in block and not isinstance(block["text"], str):
            r.error(f"block[{i}] ({btype}): field 'text' harus string")

        # heading tidak boleh kosong
        if btype in ("heading_1", "heading_2", "heading_3"):
            if not block.get("text", "").strip():
                r.warning(f"block[{i}] ({btype}): heading kosong")

        # paragraph tidak boleh sangat pendek (mungkin lupa isi)
        if btype == "paragraph":
            txt = block.get("text", "")
            if len(txt.strip()) < 10 and txt.strip():
                r.warning(f"block[{i}] (paragraph): teks sangat pendek "
                          f"({len(txt)} chars) — mungkin belum selesai diedit")

        # table: wajib punya headers dan rows
        if btype in ("table", "table_borderless"):
            if "headers" not in block:
                r.error(f"block[{i}] ({btype}): 'headers' wajib ada")
            if "rows" not in block:
                r.error(f"block[{i}] ({btype}): 'rows' wajib ada")

        # bullet_list: wajib punya items
        if btype == "bullet_list":
            if "items" not in block:
                r.error(f"block[{i}] ({btype}): 'items' wajib ada")
            elif not isinstance(block["items"], list):
                r.error(f"block[{i}] ({btype}): 'items' harus array")


def validate_against_original(edited: dict, original: dict, r: ValidationResult):
    """Check 4+5+6: Diff terhadap original."""
    orig_blocks = original.get("blocks", [])
    edit_blocks = edited.get("blocks", [])

    # chapter_id tidak boleh berubah
    if edited.get("chapter_id") != original.get("chapter_id"):
        r.error(f"chapter_id berubah: "
                f"'{original.get('chapter_id')}' → '{edited.get('chapter_id')}'")

    # Buat map original blocks berdasarkan posisi
    orig_by_type = {}
    for i, b in enumerate(orig_blocks):
        bt = b.get("type","")
        orig_by_type.setdefault(bt, []).append((i, b))

    # Cek setiap block original — apakah masih ada dan tidak berubah di bagian kritis
    orig_protected = [(i, b) for i, b in enumerate(orig_blocks)
                      if b.get("protected") or b.get("type") in FINANCIAL_BLOCK_TYPES
                      or b.get("source_refs")]

    for orig_idx, orig_block in orig_protected:
        btype   = orig_block.get("type", "")
        tbl_id  = orig_block.get("table_id","")

        # Cari block yang cocok di edited
        match = None
        for edit_block in edit_blocks:
            if edit_block.get("type") == btype:
                if tbl_id and edit_block.get("table_id") == tbl_id:
                    match = edit_block
                    break
                elif not tbl_id:
                    match = edit_block
                    break

        if match is None:
            if orig_block.get("protected"):
                r.error(f"Block protected dihapus: block[{orig_idx}] type='{btype}' "
                        f"— block ini tidak boleh dihapus")
            elif btype in FINANCIAL_BLOCK_TYPES:
                r.warning(f"Block finansial tidak ditemukan: block[{orig_idx}] "
                          f"type='{btype}' table_id='{tbl_id}'")
            continue

        # Check 4: Substance lock — angka finansial di block finansial
        if btype in FINANCIAL_BLOCK_TYPES:
            orig_nums = set()
            edit_nums = set()

            # Ekstrak dari rows
            for row in orig_block.get("rows", []):
                for cell in row:
                    orig_nums |= extract_numbers(str(cell))
            for row in match.get("rows", []):
                for cell in row:
                    edit_nums |= extract_numbers(str(cell))

            # Ekstrak dari items (metric_card, bar_chart)
            for item in orig_block.get("items", []):
                orig_nums |= extract_numbers(str(item))
            for item in match.get("items", []):
                edit_nums |= extract_numbers(str(item))

            added   = edit_nums - orig_nums
            removed = orig_nums - edit_nums
            if added or removed:
                r.error(f"Substance lock violation di block[{orig_idx}] "
                        f"({btype} '{tbl_id}'): "
                        f"angka berubah — ditambah: {added}, dihapus: {removed}. "
                        f"Angka finansial tidak boleh diubah secara langsung.")

        # Check 6: source_refs tidak boleh dihilangkan
        if orig_block.get("source_refs") and not match.get("source_refs"):
            r.warning(f"block[{orig_idx}] ({btype}): source_refs dihilangkan — "
                      f"sebaiknya pertahankan untuk auditability")

    # Cek block_type di posisi yang sama tidak berubah
    min_len = min(len(orig_blocks), len(edit_blocks))
    for i in range(min_len):
        ot = orig_blocks[i].get("type", "")
        et = edit_blocks[i].get("type", "")
        if ot != et and ot in FINANCIAL_BLOCK_TYPES:
            r.error(f"block[{i}]: block_type finansial berubah dari "
                    f"'{ot}' → '{et}' — tidak diizinkan")

    # Info: blok baru yang ditambahkan
    added_count = len(edit_blocks) - len(orig_blocks)
    if added_count > 0:
        r.info(f"{added_count} block baru ditambahkan")
    elif added_count < 0:
        r.info(f"{abs(added_count)} block dihapus")


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

edited   = load_json(args.edited,   "File hasil edit")
original = load_json(args.original, "File original") if args.original else None

r = ValidationResult()

# Run checks
ok = validate_chapter_structure(edited, r)
if ok:
    validate_blocks(edited.get("blocks", []), r)

if original:
    validate_against_original(edited, original, r)
else:
    r.info("--original tidak diberikan — substance lock dan diff checks dilewati")

# ── OUTPUT ────────────────────────────────────────────────────
if not args.quiet:
    chapter_id = edited.get("chapter_id", "?")
    print(f"\nValidasi: {Path(args.edited).name} (chapter_id: {chapter_id})")
    print(f"Blocks  : {len(edited.get('blocks', []))}")

    if r.infos:
        for msg in r.infos:
            print(f"  ℹ  {msg}")

    if r.warnings:
        print(f"\nWarnings ({len(r.warnings)}):")
        for msg in r.warnings:
            print(f"  ⚠  {msg}")

    if r.errors:
        print(f"\nErrors ({len(r.errors)}):")
        for msg in r.errors:
            print(f"  ✗  {msg}")

    print()

verdict = r.valid and (r.clean if args.strict else True)
print("VALID — aman untuk diimport ke pipeline."
      if verdict else
      "INVALID — perbaiki error di atas sebelum import.")

sys.exit(0 if verdict else 1)
