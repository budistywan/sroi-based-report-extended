"""
review_state_handler.py — Sprint 11E
State machine untuk review objects.

Usage (sebagai modul):
  from review_state_handler import ReviewState, apply_decision, is_blocking
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── VALID STATES ──────────────────────────────────────────────
STATES = {
    "draft",
    "pending_review",
    "approved",
    "approved_with_notes",
    "revision_requested",
    "deferred",
}

BLOCKING_STATES = {"pending_review", "revision_requested"}

VALID_TRANSITIONS = {
    "draft":              {"send_to_review": "pending_review"},
    "pending_review":     {
        "approve":        "approved",
        "approve_notes":  "approved_with_notes",
        "revise":         "revision_requested",
        "defer":          "deferred",
    },
    "revision_requested": {"resubmit": "pending_review"},
    "deferred":           {"reopen":   "pending_review"},
    "approved":           {},
    "approved_with_notes":{},
}


def get_initial_state() -> dict:
    """Buat state record awal."""
    return {
        "state":      "draft",
        "history":    [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def transition(state_record: dict, action: str,
               reviewer: str = "user", note: str = "") -> dict:
    """
    Lakukan transisi state.
    Return state_record yang sudah diupdate.
    Raise ValueError jika transisi tidak valid.
    """
    current = state_record.get("state", "draft")
    transitions = VALID_TRANSITIONS.get(current, {})

    if action not in transitions:
        valid = list(transitions.keys())
        raise ValueError(
            f"Transisi '{action}' tidak valid dari state '{current}'. "
            f"Valid actions: {valid}"
        )

    new_state = transitions[action]
    now = datetime.now().isoformat()

    state_record["history"].append({
        "from_state": current,
        "action":     action,
        "to_state":   new_state,
        "reviewer":   reviewer,
        "note":       note,
        "timestamp":  now,
    })
    state_record["state"]      = new_state
    state_record["updated_at"] = now

    return state_record


def is_blocking(state_record: dict, auto_continue: bool = False) -> bool:
    """Apakah state ini memblocking pipeline?"""
    if auto_continue:
        return False
    return state_record.get("state") in BLOCKING_STATES


def auto_approve(state_record: dict) -> dict:
    """Approve otomatis (mode auto_continue)."""
    current = state_record.get("state", "draft")
    if current == "draft":
        state_record = transition(state_record, "send_to_review", reviewer="system")
    if state_record["state"] == "pending_review":
        state_record = transition(state_record, "approve", reviewer="auto",
                                   note="Auto-approved — auto_continue mode")
    return state_record


def load_or_init(state_path: Path) -> dict:
    """Load state dari file, atau buat baru."""
    if state_path.exists():
        return json.load(open(state_path))
    return get_initial_state()


def save_state(state_record: dict, state_path: Path) -> None:
    """Simpan state ke file."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(state_record, open(state_path,"w"), indent=2, ensure_ascii=False)


# ── STANDALONE TEST ───────────────────────────────────────────
if __name__ == "__main__":
    print("=== State Machine Test ===")

    sr = get_initial_state()
    print(f"Initial: {sr['state']}")

    sr = transition(sr, "send_to_review")
    print(f"After send_to_review: {sr['state']}")

    sr = transition(sr, "revise", note="Core claim perlu diperbaiki")
    print(f"After revise: {sr['state']}")

    sr = transition(sr, "resubmit")
    print(f"After resubmit: {sr['state']}")

    sr = transition(sr, "approve_notes", note="Disetujui dengan catatan minor")
    print(f"After approve_notes: {sr['state']}")

    print(f"Blocking (no auto): {is_blocking(sr)}")
    print(f"History: {len(sr['history'])} transitions")
    print("State machine test: PASS")
