"""
enrichment_review_handler.py — Sprint 12D
Suggestion Review Bridge — mengubah enrichment suggestions menjadi reviewable objects.

Usage:
  python enrichment_review_handler.py --mode view --enriched /p/ --output /p/
  python enrichment_review_handler.py --mode apply --enriched /p/ --decisions /p/ --output /p/
  python enrichment_review_handler.py --mode apply --auto --enriched /p/ --output /p/
"""

import json, sys, os, argparse, uuid, copy
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--mode",      choices=["view","apply"], default="view")
parser.add_argument("--enriched",  default=None)
parser.add_argument("--decisions", default=None)
parser.add_argument("--output",    default=None)
parser.add_argument("--auto",      action="store_true", help="Auto-accept all suggestions")
args = parser.parse_args()

SCRIPT_DIR    = Path(__file__).parent
ENRICHED_FILE = Path(args.enriched) if args.enriched \
    else Path(os.environ.get("ENRICHED_FILE", SCRIPT_DIR / "canonical_enriched.json"))
OUTPUT_DIR    = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

if not ENRICHED_FILE.exists():
    print(f"FAIL: {ENRICHED_FILE} tidak ditemukan"); sys.exit(1)

enriched    = json.load(open(ENRICHED_FILE))
suggestions = enriched.get("_enrichment_suggestions", [])


def generate_review_view(suggestions: list) -> dict:
    """Buat view ringkas untuk reviewer."""
    by_category = {}
    for s in suggestions:
        cat = s.get("category","general")
        by_category.setdefault(cat, []).append({
            "suggestion_id":   s["suggestion_id"],
            "suggestion_type": s["suggestion_type"],
            "text":            s["text"][:100] + "..." if len(s["text"]) > 100 else s["text"],
            "confidence":      s["confidence"],
            "target":          s["target"],
            "current_status":  s["status"],
            "available_actions": ["accept","reject","revise","defer"],
        })

    return {
        "view_type":        "enrichment_review",
        "generated_at":     datetime.now().isoformat(),
        "total_suggestions": len(suggestions),
        "by_category":      by_category,
        "review_guidance": [
            "accept → suggestion diterima dan akan dimasukkan ke builder hints",
            "reject → suggestion diabaikan, tidak masuk ke pipeline",
            "revise → teks suggestion diubah reviewer sebelum diterima",
            "defer → tidak diputuskan sekarang, bisa di-review nanti",
        ],
    }


def apply_enrichment_decisions(suggestions: list, decisions: dict) -> list:
    """Terapkan keputusan review ke suggestions."""
    updated   = copy.deepcopy(suggestions)
    changes   = decisions.get("changes", [])
    auto_mode = decisions.get("auto_accept_all", False)

    if auto_mode:
        for s in updated:
            s["status"]      = "accepted"
            s["reviewed_at"] = datetime.now().isoformat()
            s["reviewer"]    = "auto"
        return updated

    for change in changes:
        sid     = change.get("suggestion_id","")
        action  = change.get("action","")
        revised = change.get("revised_text","")

        for s in updated:
            if s["suggestion_id"] == sid:
                if action == "accept":
                    s["status"]      = "accepted"
                    s["reviewed_at"] = datetime.now().isoformat()
                    s["reviewer"]    = decisions.get("reviewer","user")
                elif action == "reject":
                    s["status"]      = "rejected"
                    s["reviewed_at"] = datetime.now().isoformat()
                    s["reviewer"]    = decisions.get("reviewer","user")
                elif action == "revise":
                    s["status"]      = "accepted"
                    s["original_text"] = s["text"]
                    s["text"]        = revised or s["text"]
                    s["reviewed_at"] = datetime.now().isoformat()
                    s["reviewer"]    = decisions.get("reviewer","user")
                elif action == "defer":
                    s["status"]      = "deferred"

    return updated


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if args.mode == "view":
    view = generate_review_view(suggestions)
    view_path = OUTPUT_DIR / "enrichment_review_view.json"
    json.dump(view, open(view_path,"w"), indent=2, ensure_ascii=False)
    print(f"View: {view_path}")

    # Sample decisions — accept beberapa, reject satu
    if suggestions:
        sample_changes = []
        for i, s in enumerate(suggestions):
            action = "accept" if i < len(suggestions) - 1 else "defer"
            sample_changes.append({
                "suggestion_id": s["suggestion_id"],
                "action":        action,
                "note":          "Accepted by reviewer" if action == "accept" else "Deferred",
            })

        sample_dec = {
            "review_id":       uuid.uuid4().hex[:8],
            "reviewer":        "user",
            "timestamp":       datetime.now().isoformat(),
            "auto_accept_all": False,
            "changes":         sample_changes,
        }
        dec_path = OUTPUT_DIR / "enrichment_review_decisions.json"
        json.dump(sample_dec, open(dec_path,"w"), indent=2, ensure_ascii=False)
        print(f"Sample decisions: {dec_path}")

    print(f"\nTotal suggestions: {len(suggestions)}")
    by_cat = {}
    for s in suggestions:
        by_cat[s.get("category","?")] = by_cat.get(s.get("category","?"),0) + 1
    for cat, n in sorted(by_cat.items()):
        print(f"  {cat}: {n}")

elif args.mode == "apply":
    if args.auto:
        decisions = {"auto_accept_all": True, "reviewer": "auto", "changes": []}
    elif args.decisions and Path(args.decisions).exists():
        decisions = json.load(open(args.decisions))
    else:
        print("FAIL: --decisions atau --auto wajib untuk mode apply"); sys.exit(1)

    updated = apply_enrichment_decisions(suggestions, decisions)

    # Update enriched canonical dengan suggestions yang sudah di-review
    enriched_updated = copy.deepcopy(enriched)
    enriched_updated["_enrichment_suggestions"] = updated
    enriched_updated["_enrichment_metadata"]["reviewed_at"] = datetime.now().isoformat()
    enriched_updated["_enrichment_metadata"]["review_completed"] = True

    accepted = [s for s in updated if s["status"] == "accepted"]
    rejected = [s for s in updated if s["status"] == "rejected"]
    deferred = [s for s in updated if s["status"] == "deferred"]

    out_path = OUTPUT_DIR / "canonical_enriched_reviewed.json"
    json.dump(enriched_updated, open(out_path,"w"), indent=2, ensure_ascii=False)
    print(f"Enriched reviewed: {out_path}")
    print(f"  accepted: {len(accepted)} | rejected: {len(rejected)} | deferred: {len(deferred)}")

print("\nenrichment_review_handler: OK")
