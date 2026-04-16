"""
canonical_review_handler.py — Sprint 11B
Handler untuk review canonical JSON.

Input : canonical_esl_v1.json
Output: canonical_review_view.json (ringkasan human-readable)
        canonical_review_decisions.json (keputusan review)
        canonical_reviewed.json (canonical setelah perubahan diterapkan)

Usage:
  # Generate view
  python canonical_review_handler.py --mode view \
      --canonical /path/canonical.json --output /path/

  # Apply decisions
  python canonical_review_handler.py --mode apply \
      --canonical /path/canonical.json \
      --decisions /path/decisions.json \
      --output /path/
"""

import json, sys, os, argparse, uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from review_state_handler import get_initial_state, transition, save_state

parser = argparse.ArgumentParser()
parser.add_argument("--mode",      choices=["view","apply"], default="view")
parser.add_argument("--canonical", default=None)
parser.add_argument("--decisions", default=None)
parser.add_argument("--output",    default=None)
args = parser.parse_args()

SCRIPT_DIR     = Path(__file__).parent
CANONICAL_FILE = Path(args.canonical) if args.canonical \
    else Path(os.environ.get("CANONICAL_FILE",
              SCRIPT_DIR.parent / "sprint0/canonical_esl_v1.json"))
OUTPUT_DIR     = Path(args.output) if args.output \
    else Path(os.environ.get("OUTPUT_DIR", SCRIPT_DIR))

if not CANONICAL_FILE.exists():
    print(f"FAIL: {CANONICAL_FILE} tidak ditemukan"); sys.exit(1)

canonical = json.load(open(CANONICAL_FILE))


def idr(v):
    try: return f"Rp {int(v):,}"
    except: return str(v)


# ══════════════════════════════════════════════════════════════
# MODE: VIEW — generate ringkasan review-friendly
# ══════════════════════════════════════════════════════════════
def generate_view(canonical: dict) -> dict:
    pi   = canonical.get("program_identity", {})
    pp   = canonical.get("program_positioning", {})
    sm   = canonical.get("sroi_metrics", {}).get("calculated", {})
    inv  = canonical.get("investment", [])
    mon  = canonical.get("monetization", [])
    cov  = canonical.get("coverage_status", {})
    flags= canonical.get("uncertainty_flags", [])

    # Investment summary
    total_inv = sum(i.get("amount_idr",0) for i in inv)
    inv_statuses = list({i.get("data_status","?") for i in inv})

    # Monetization summary
    aspects = {}
    for m in mon:
        asp = m["aspect_code"]
        if asp not in aspects:
            aspects[asp] = {"gross": 0, "status": m.get("data_status","?")}
        aspects[asp]["gross"] += m.get("gross_idr", 0)

    # Coverage summary
    cov_summary = {}
    for bab, cv in cov.items():
        cov_summary[bab] = {
            "status": cv.get("status","?"),
            "risk":   cv.get("risk","?"),
        }

    view = {
        "view_type":       "canonical_review",
        "program_code":    pi.get("program_code","?"),
        "generated_at":    datetime.now().isoformat(),
        "review_state":    "pending_review",

        "program_identity_summary": {
            "program_name":    pi.get("program_name",""),
            "program_tagline": pi.get("program_tagline","")[:80] + "..." if len(pi.get("program_tagline","")) > 80 else pi.get("program_tagline",""),
            "company":         pi.get("company",""),
            "period":          f"{pi.get('period_start','')}–{pi.get('period_end','')}",
            "review_fields":   ["program_name","program_tagline","company","period_start","period_end"],
        },

        "key_metrics": {
            "sroi_blended":         sm.get("sroi_blended"),
            "sroi_blended_status":  "final" if sm.get("sroi_blended") else "pending",
            "total_investment_idr": sm.get("total_investment_idr") or total_inv,
            "net_compounded_idr":   sm.get("total_net_compounded_idr"),
            "avg_fiksasi_pct":      sm.get("avg_fiksasi_pct"),
        },

        "investment_summary": {
            "total_idr":   total_inv,
            "items":       len(inv),
            "statuses":    inv_statuses,
            "reviewable":  True,
            "note":        "Investasi 2023-2024 under_confirmation — perlu verifikasi" if "under_confirmation" in inv_statuses else "",
        },

        "monetization_summary": {
            "aspects":  {
                asp: {
                    "gross_idr": data["gross"],
                    "status":    data["status"],
                    "is_proxy":  data["status"] in ["proxy","inferred"],
                }
                for asp, data in aspects.items()
            },
        },

        "coverage_status": cov_summary,

        "uncertainty_flags": [
            {"flag_id": f.get("flag_id"), "reason": f.get("reason","")[:80]}
            for f in flags
        ],

        "review_prompts": [
            "Apakah program_name sudah benar?",
            "Apakah SROI blended sudah sesuai metodologi yang disepakati?",
            "Apakah status investasi 2023-2024 sudah dikonfirmasi atau masih under_confirmation?",
            "Apakah aspek proxy (REINT, CONF) perlu catatan tambahan?",
            "Apakah ada bab yang coverage-nya perlu dinaikkan atau diturunkan?",
        ],

        "available_decisions": ["approve","approve_with_notes","revise","defer"],
        "available_changes":   ["replace_value","append_note","set_status","mark_as_gap",
                                "approve_without_change","downgrade_confidence"],
    }
    return view


# ══════════════════════════════════════════════════════════════
# MODE: APPLY — terapkan decisions ke canonical
# ══════════════════════════════════════════════════════════════
def set_nested(obj: dict, path: str, value) -> None:
    """Set nilai di nested path, e.g. 'program_identity.program_name'."""
    keys = path.split(".")
    for k in keys[:-1]:
        if k.isdigit():
            obj = obj[int(k)]
        else:
            obj = obj.setdefault(k, {})
    last = keys[-1]
    if last.isdigit():
        obj[int(last)] = value
    else:
        obj[last] = value


def get_nested(obj: dict, path: str):
    """Get nilai di nested path."""
    keys = path.split(".")
    for k in keys:
        try:
            if isinstance(obj, list):
                obj = obj[int(k)]
            else:
                obj = obj[k]
        except (KeyError, IndexError, TypeError):
            return None
    return obj


def apply_decisions(canonical: dict, decisions: dict) -> tuple[dict, list]:
    """Terapkan review decisions ke canonical. Return (reviewed_canonical, applied_log)."""
    import copy
    reviewed = copy.deepcopy(canonical)
    log = []

    changes = decisions.get("changes", [])

    for change in changes:
        ct = change.get("change_type","")
        fp = change.get("field_path","")

        if ct == "replace_value":
            old = get_nested(reviewed, fp)
            new = change.get("new_value")
            set_nested(reviewed, fp, new)
            log.append(f"replace_value: {fp} = {old!r} → {new!r}")

        elif ct == "set_status":
            # Cari field dan tambahkan _status suffix atau ubah data_status
            new_status = change.get("new_status")
            # Coba set data_status di path yang relevan
            status_path = fp + ".data_status" if not fp.endswith("data_status") else fp
            try:
                set_nested(reviewed, status_path, new_status)
                log.append(f"set_status: {status_path} = {new_status!r}")
            except Exception as e:
                log.append(f"set_status FAILED: {fp} — {e}")

        elif ct == "append_note":
            note = change.get("note","")
            note_path = fp + "._review_note"
            set_nested(reviewed, note_path, note)
            log.append(f"append_note: {fp} += {note!r}")

        elif ct == "mark_as_gap":
            gap_type = change.get("gap_type","data_unavailable")
            note     = change.get("note","")
            existing = get_nested(reviewed, fp) or {}
            if isinstance(existing, dict):
                existing["_gap_type"]  = gap_type
                existing["_gap_note"]  = note
                existing["data_status"]= "pending"
                set_nested(reviewed, fp, existing)
            log.append(f"mark_as_gap: {fp} [{gap_type}]")

        elif ct == "downgrade_confidence":
            new_status = change.get("new_status","proxy")
            try:
                # Untuk scalar field, set di parent dengan key _status
                parts = fp.rsplit(".", 1)
                if len(parts) == 2:
                    parent_path, field_key = parts
                    parent = get_nested(reviewed, parent_path) or {}
                    if isinstance(parent, dict):
                        parent[f"{field_key}_data_status"] = new_status
                        set_nested(reviewed, parent_path, parent)
                    else:
                        set_nested(reviewed, fp + "_status", new_status)
                else:
                    reviewed[fp + "_status"] = new_status
                log.append(f"downgrade_confidence: {fp} → {new_status!r}")
            except Exception as e:
                log.append(f"downgrade_confidence FAILED: {fp} — {e}")

        elif ct == "approve_without_change":
            log.append(f"approve_without_change: {fp}")

        elif ct == "request_regeneration":
            target = change.get("target_id","")
            log.append(f"request_regeneration: {target} — {change.get('instruction','')}")

    # Tambah metadata review
    reviewed["_review_metadata"] = {
        "reviewed_at":   datetime.now().isoformat(),
        "reviewer":      decisions.get("reviewer","user"),
        "decision":      decisions.get("decision","approve"),
        "changes_count": len(changes),
        "applied_log":   log,
        "source_review_id": decisions.get("review_id",""),
    }

    return reviewed, log


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if args.mode == "view":
    view = generate_view(canonical)
    view_path = OUTPUT_DIR / "canonical_review_view.json"
    json.dump(view, open(view_path,"w"), indent=2, ensure_ascii=False)
    print(f"View: {view_path}")

    # Juga generate sample decisions file sebagai template
    sample_decisions = {
        "review_id":          str(uuid.uuid4())[:8],
        "review_target_type": "canonical",
        "review_target_id":   canonical.get("program_identity",{}).get("program_code",""),
        "program_code":       canonical.get("program_identity",{}).get("program_code",""),
        "decision":           "approve_with_notes",
        "pipeline_gate":      "review_point_a",
        "reviewer":           "user",
        "timestamp":          datetime.now().isoformat(),
        "notes":              "Canonical approved — investasi 2023-2024 masih under_confirmation, perlu follow-up",
        "changes": [
            {
                "change_type": "approve_without_change",
                "field_path":  "program_identity.program_name",
                "note":        "Sudah benar"
            },
            {
                "change_type": "append_note",
                "field_path":  "investment",
                "note":        "Investasi 2023-2024 perlu dikonfirmasi dari laporan keuangan resmi sebelum evaluasi berikutnya"
            },
            {
                "change_type": "downgrade_confidence",
                "field_path":  "monetization",
                "new_status":  "proxy",
                "reason":      "REINT dan CONF masih estimasi konservatif — belum diverifikasi survei"
            }
        ]
    }
    dec_path = OUTPUT_DIR / "canonical_review_decisions.json"
    json.dump(sample_decisions, open(dec_path,"w"), indent=2, ensure_ascii=False)
    print(f"Sample decisions: {dec_path}")

    print(f"\nCanonical: {canonical.get('program_identity',{}).get('program_name','?')}")
    print(f"SROI blended: {canonical.get('sroi_metrics',{}).get('calculated',{}).get('sroi_blended','?')}")
    print(f"Coverage babs: {list(canonical.get('coverage_status',{}).keys())}")

elif args.mode == "apply":
    if not args.decisions:
        print("FAIL: --decisions wajib untuk mode apply"); sys.exit(1)
    dec_path = Path(args.decisions)
    if not dec_path.exists():
        print(f"FAIL: {dec_path} tidak ditemukan"); sys.exit(1)

    decisions = json.load(open(dec_path))
    reviewed, log = apply_decisions(canonical, decisions)

    out_path = OUTPUT_DIR / "canonical_reviewed.json"
    json.dump(reviewed, open(out_path,"w"), indent=2, ensure_ascii=False)
    print(f"Reviewed canonical: {out_path}")
    print(f"Changes applied: {len(log)}")
    for entry in log:
        print(f"  → {entry}")

print("\ncanonical_review_handler: OK")
