"""
builder_enrichment_adapter.py — Sprint 12E
Adapter yang mengambil accepted enrichment suggestions dan mengintegrasikannya
ke chapter outline sebagai enrichment hints untuk builder.

Input:
  - canonical_enriched_reviewed.json (atau canonical_enriched.json)
  - chapter_outline bab7 dan bab4

Output:
  - enriched_outline_bab7.json
  - enriched_outline_bab4.json

Prinsip:
  - adapter TIDAK mengubah argument_points
  - adapter HANYA menambahkan _enrichment_hints ke outline
  - builder bisa memilih memakai hints atau mengabaikannya

Usage:
  python builder_enrichment_adapter.py
  python builder_enrichment_adapter.py --enriched /p/ --outline-bab7 /p/ --output /p/
"""

import json, sys, os, argparse, copy
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--enriched",     default=None)
parser.add_argument("--outline-bab7", default=None, dest="outline7")
parser.add_argument("--outline-bab4", default=None, dest="outline4")
parser.add_argument("--output",       default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
ENRICHED_FILE  = Path(args.enriched)  if args.enriched \
    else Path(os.environ.get("ENRICHED_FILE",
              SCRIPT_DIR / "canonical_enriched_reviewed.json"))
# Fallback ke non-reviewed jika reviewed belum ada
if not ENRICHED_FILE.exists():
    ENRICHED_FILE = SCRIPT_DIR / "canonical_enriched.json"

OUTLINE7_FILE  = Path(args.outline7)  if args.outline7 \
    else Path(os.environ.get("OUTLINE7_FILE",
              SCRIPT_DIR.parent / "sprint11/chapter_outline_reviewed_bab_7.json"))
OUTLINE4_FILE  = Path(args.outline4)  if args.outline4 \
    else Path(os.environ.get("OUTLINE4_FILE",
              SCRIPT_DIR.parent / "sprint3/chapter_outline_bab7.json"))   # fallback

OUTPUT_DIR     = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

if not ENRICHED_FILE.exists():
    print(f"FAIL: {ENRICHED_FILE} tidak ditemukan"); sys.exit(1)

print(f"Enriched  : {ENRICHED_FILE.resolve()}")
print(f"Outline7  : {OUTLINE7_FILE.resolve()}")

enriched    = json.load(open(ENRICHED_FILE))
suggestions = enriched.get("_enrichment_suggestions", [])
accepted    = [s for s in suggestions if s.get("status") in ["accepted","pending"]]

print(f"Accepted suggestions: {len(accepted)} / {len(suggestions)}")


def build_hint_map(suggestions: list) -> dict:
    """Buat map: target → hints yang relevan."""
    hint_map = {}
    for s in suggestions:
        target = s.get("target","general")
        hint_map.setdefault(target, []).append({
            "hint_type":  s["suggestion_type"],
            "text":       s["text"],
            "confidence": s["confidence"],
            "category":   s["category"],
            "source":     s["source"],
            "rule_id":    s["rule_id"],
        })
    # 'general' hints masuk ke semua bab
    return hint_map


def enrich_outline(outline_data: list, hint_map: dict, chapter_id: str) -> list:
    """Tambahkan enrichment hints ke outline. Tidak mengubah structure asli."""
    enriched_outlines = []
    for chapter in outline_data:
        cid = chapter.get("chapter_id","?")
        ch  = copy.deepcopy(chapter)

        # Hints spesifik untuk bab ini
        specific_hints = hint_map.get(cid, [])
        # Hints general
        general_hints  = hint_map.get("general", [])

        all_hints = specific_hints + general_hints

        if all_hints:
            ch["_enrichment_hints"] = {
                "generated_at":  datetime.now().isoformat(),
                "total_hints":   len(all_hints),
                "hints":         all_hints,
                "usage_note":    "Hints ini dari enrichment engine — builder boleh memakai atau mengabaikan. Tidak mengubah argument_points.",
            }

            # Tambah per-category summary
            by_cat = {}
            for h in all_hints:
                by_cat[h["category"]] = by_cat.get(h["category"],0) + 1
            ch["_enrichment_hints"]["by_category"] = by_cat

        enriched_outlines.append(ch)
    return enriched_outlines


hint_map = build_hint_map(accepted)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Enrich Bab 7 ─────────────────────────────────────────────
if OUTLINE7_FILE.exists():
    raw7 = json.load(open(OUTLINE7_FILE))
    ol7  = raw7 if isinstance(raw7, list) else [raw7]
    enriched7 = enrich_outline(ol7, hint_map, "bab_7")

    out7 = OUTPUT_DIR / "enriched_outline_bab7.json"
    json.dump(enriched7, open(out7,"w"), indent=2, ensure_ascii=False)
    hints7 = enriched7[0].get("_enrichment_hints",{}).get("total_hints",0)
    print(f"Enriched bab7: {out7} ({hints7} hints)")
else:
    print(f"  WARN: Outline bab7 tidak ditemukan — {OUTLINE7_FILE}")

# ── Enrich Bab 4 (buat dari bab7 outline sebagai skeleton) ────
# Bab 4 tidak punya outline tersendiri — buat skeleton dengan enrichment hints
bab4_skeleton = [{
    "chapter_id":      "bab_4",
    "chapter_title":   "Identifikasi Kondisi Awal",
    "builder_mode":    "context",
    "coverage_status": "weak",
    "purpose":         "Memetakan kondisi awal yang menjadi dasar intervensi program",
    "core_claim":      "Kondisi awal program diidentifikasi secara programatik — baseline wilayah rinci tidak tersedia",
    "argument_points": [],
    "known_gaps": [
        {
            "gap_id":   "gap_bab4_baseline",
            "field":    "context_baseline",
            "gap_type": "data_unavailable",
            "note":     "Data baseline wilayah (BPS, peta administrasi) tidak tersedia dalam sumber utama"
        }
    ],
    "generated_at":    datetime.now().isoformat(),
}]

enriched4 = enrich_outline(bab4_skeleton, hint_map, "bab_4")
out4 = OUTPUT_DIR / "enriched_outline_bab4.json"
json.dump(enriched4, open(out4,"w"), indent=2, ensure_ascii=False)
hints4 = enriched4[0].get("_enrichment_hints",{}).get("total_hints",0)
print(f"Enriched bab4: {out4} ({hints4} hints)")

print(f"\n{'='*55}")
print("BUILDER ENRICHMENT ADAPTER COMPLETE")
print(f"  bab_7 hints: {hints7 if OUTLINE7_FILE.exists() else 'N/A'}")
print(f"  bab_4 hints: {hints4}")
print(f"  Hint categories: {list(hint_map.keys())}")
print("="*55)
