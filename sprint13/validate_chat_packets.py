"""
validate_chat_packets.py — Sprint 13
Gates 1-3: Schema valid + exporter works + packet examples valid.

Usage:
  python validate_chat_packets.py
  python validate_chat_packets.py --dir /path/sprint13/
"""
import json, sys, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--dir", default=None)
args = parser.parse_args()

SCRIPT_DIR = Path(__file__).parent
DIR13      = Path(args.dir) if args.dir else SCRIPT_DIR

ERRORS = []
def check(cond, msg):
    if not cond: ERRORS.append(f"  FAIL: {msg}"); return False
    print(f"  PASS: {msg}"); return True

REQUIRED_PACKET_FIELDS = [
    "packet_id","packet_type","target_id","scope",
    "decision_prompt","context","decision_options"
]
REQUIRED_CONTEXT_FIELDS = ["current_text","source","confidence","applicability_context"]
VALID_PACKET_TYPES = {
    "framing_note","terminology_note","caution_note",
    "interpretation_paragraph","executive_framing",
    "closing_paragraph","proxy_recommendation","gap_acknowledgement"
}

def validate_single_packet(pkt: dict, label: str) -> list:
    errs = []
    for f in REQUIRED_PACKET_FIELDS:
        if f not in pkt:
            errs.append(f"{label}: required field '{f}' missing")
    ctx = pkt.get("context",{})
    for f in REQUIRED_CONTEXT_FIELDS:
        if f not in ctx:
            errs.append(f"{label}: context.{f} missing")
    if pkt.get("packet_type") not in VALID_PACKET_TYPES:
        errs.append(f"{label}: invalid packet_type '{pkt.get('packet_type')}'")
    scope = pkt.get("scope",{})
    if "allowed_changes" not in scope:
        errs.append(f"{label}: scope.allowed_changes missing")
    if "forbidden_changes" not in scope:
        errs.append(f"{label}: scope.forbidden_changes missing")
    if not ctx.get("applicability_context"):
        errs.append(f"{label}: applicability_context is empty")
    if not pkt.get("decision_prompt","").strip():
        errs.append(f"{label}: decision_prompt is empty")
    return errs

# ── GATE 1: Schema valid ──────────────────────────────────────
print("\n=== GATE 1: Packet schema valid ===")
sch_path = DIR13 / "semantic_packet_schema.json"
check(sch_path.exists(), "semantic_packet_schema.json ada")
if sch_path.exists():
    s = json.load(open(sch_path))
    check("required" in s,                               "schema has required")
    check("packet_id"       in s.get("required",[]),     "packet_id required")
    check("scope"           in s.get("required",[]),     "scope required")
    check("decision_prompt" in s.get("required",[]),     "decision_prompt required")
    check("context"         in s.get("required",[]),     "context required")
    props = s.get("properties",{})
    check("scope"   in props,                            "scope in properties")
    check("context" in props,                            "context in properties")
    scope_props = props.get("scope",{}).get("properties",{})
    check("allowed_changes"  in scope_props,             "scope.allowed_changes in schema")
    check("forbidden_changes" in scope_props,            "scope.forbidden_changes in schema")

patch_sch = DIR13 / "chat_patch_schema.json"
check(patch_sch.exists(), "chat_patch_schema.json ada")
if patch_sch.exists():
    ps = json.load(open(patch_sch))
    for f in ["patch_id","source_packet_id","decision","original_text","applicability_context"]:
        check(f in ps.get("required",[]), f"patch schema requires '{f}'")

# ── GATE 2: Exporter works ────────────────────────────────────
print("\n=== GATE 2: Packet exporter output ===")
for fname, label in [
    ("semantic_packets_bab4.json",    "Bab IV packets"),
    ("semantic_packets_bab7.json",    "Bab VII packets"),
    ("semantic_packets_closing.json", "Closing packets"),
]:
    fpath = DIR13 / fname
    check(fpath.exists(), f"{label} ({fname}) ada")
    if fpath.exists():
        pkts = json.load(open(fpath))
        check(isinstance(pkts, list) and len(pkts) > 0,
              f"{label}: tidak kosong ({len(pkts)} packets)")
        for i, pkt in enumerate(pkts):
            errs = validate_single_packet(pkt, f"{fname}[{i}]")
            for e in errs: ERRORS.append(f"  FAIL: {e}")
            if not errs:
                print(f"  PASS: {fname}[{i}] valid — type={pkt['packet_type']}")

# Cek minimal packet types
all_packets = []
for fname in ["semantic_packets_bab4.json","semantic_packets_bab7.json","semantic_packets_closing.json"]:
    fpath = DIR13 / fname
    if fpath.exists():
        all_packets += json.load(open(fpath))

packet_types = {p["packet_type"] for p in all_packets}
check("framing_note"   in packet_types, "Ada framing_note packet (Bab IV)")
check("terminology_note" in packet_types or "caution_note" in packet_types,
      "Ada terminology_note atau caution_note packet (Bab VII)")
check("closing_paragraph" in packet_types or "executive_framing" in packet_types,
      "Ada closing/executive packet")

# Human readability check
for pkt in all_packets[:3]:
    prompt = pkt.get("decision_prompt","")
    check(len(prompt) >= 30,
          f"decision_prompt cukup informatif ({len(prompt)} chars): {pkt['packet_id']}")
    ctx_text = pkt.get("context",{}).get("current_text","")
    check(len(ctx_text) >= 20,
          f"current_text tidak kosong: {pkt['packet_id']}")

# Non-export discipline: tidak ada financial tables, SROI values mentah di packet
for pkt in all_packets:
    forbidden_exports = ["table_ddat","table_investment","calc_audit_log","validator_output"]
    pt = pkt.get("packet_type","")
    check(pt not in ["financial_table","canonical_core","validator_output"],
          f"Packet type {pt} bukan internal artifact")

# ── GATE 3: Examples valid ────────────────────────────────────
print("\n=== GATE 3: Packet examples valid ===")
ex_path = DIR13 / "packet_examples.json"
check(ex_path.exists(), "packet_examples.json ada")
if ex_path.exists():
    ex = json.load(open(ex_path))
    check("total" in ex,         "examples.total ada")
    check("by_type" in ex,       "examples.by_type ada")
    check(ex.get("total",0) > 0, f"examples total > 0 ({ex.get('total',0)})")
    check("sample" in ex and len(ex.get("sample",[])) > 0, "examples.sample ada")

# ── HASIL ─────────────────────────────────────────────────────
print("\n" + "="*55)
if ERRORS:
    print(f"CHAT PACKETS GATE: FAILED ({len(ERRORS)} error)")
    for e in ERRORS: print(e)
    sys.exit(1)
else:
    print("CHAT PACKETS GATE: ALL PASS")
    print(f"  {len(all_packets)} packets valid across 3 pilots")
    print(f"  Packet types: {sorted(packet_types)}")
    sys.exit(0)
