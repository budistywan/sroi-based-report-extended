"""
chat_patch_validator.py — Sprint 13D
Memvalidasi patch terhadap scope packet aslinya.

Rules:
  - Patch TIDAK BOLEH mengubah forbidden fields
  - Patch WAJIB punya applicability_context yang valid
  - Patch text_only TIDAK BOLEH mengandung perubahan angka signifikan
  - Rejected patches WAJIB punya rejection_reason
  - Semua patches WAJIB punya context label

Usage:
  from chat_patch_validator import validate_patch, validate_patch_against_packet
"""

import json, re, sys
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent

# Load registry
REGISTRY_FILE = SCRIPT_DIR / "review_context_registry.json"
registry = json.load(open(REGISTRY_FILE)) if REGISTRY_FILE.exists() else {"contexts": []}
VALID_CONTEXTS = {c["context_id"] for c in registry.get("contexts", []) if c.get("active")}


class PatchValidationError(Exception):
    pass


def _contains_numeric_change(original: str, revised: str) -> bool:
    """Deteksi apakah ada perubahan angka antara dua teks."""
    def extract_numbers(text):
        # Ekstrak pola angka signifikan: 1:1,03 | 502.460.181 | 50% | Rp 300.000
        # Minimal 2 digit berturut-turut untuk menghindari false positive
        patterns = re.findall(
            r'1\s*:\s*[\d,\.]+|(?:Rp\s*)?\d{2,}(?:[\.,]\d+)*(?:\s*(?:juta|miliar|Jt|M|jt|%))?|\d+(?:[\.,]\d{2,})',
            text
        )
        return set(p.strip() for p in patterns if len(p.strip()) >= 2)

    orig_nums = extract_numbers(original)
    rev_nums  = extract_numbers(revised)
    added   = rev_nums - orig_nums
    removed = orig_nums - rev_nums
    # Hanya flag jika ada angka yang berbeda (bukan hanya tambahan angka baru)
    return bool(added or removed)


def validate_patch(patch: dict, packet: dict) -> list:
    """
    Validasi satu patch terhadap packet aslinya.
    Return list of error strings. Empty = valid.
    """
    errors = []

    # ── 1. applicability_context wajib ada ─────────────────
    ctx = patch.get("applicability_context","")
    if not ctx:
        errors.append("MISSING_CONTEXT: applicability_context wajib ada")
    elif ctx not in VALID_CONTEXTS:
        errors.append(f"INVALID_CONTEXT: '{ctx}' tidak terdaftar di context registry (valid: {VALID_CONTEXTS})")

    # ── 2. source_packet_id harus match ────────────────────
    if patch.get("source_packet_id") != packet.get("packet_id"):
        errors.append(
            f"PACKET_MISMATCH: source_packet_id '{patch.get('source_packet_id')}' "
            f"!= packet_id '{packet.get('packet_id')}'"
        )

    # ── 3. decision enum valid ──────────────────────────────
    decision = patch.get("decision","")
    if decision not in ["accept","reject","revise"]:
        errors.append(f"INVALID_DECISION: '{decision}' bukan accept|reject|revise")

    # ── 4. rejected patches wajib punya rejection_reason ───
    if decision == "reject" and not patch.get("rejection_reason"):
        errors.append("MISSING_REJECTION_REASON: patch rejected wajib punya rejection_reason")

    # ── 5. revised patches wajib punya final_text berbeda ──
    if decision == "revise":
        orig = patch.get("original_text","")
        final = patch.get("final_text","")
        if not final:
            errors.append("MISSING_FINAL_TEXT: patch revise wajib punya final_text")
        elif orig == final:
            errors.append("IDENTICAL_REVISION: final_text sama dengan original_text — gunakan 'accept' bukan 'revise'")

    # ── 6. Scope: text_only → tidak boleh ubah angka ───────
    scope      = packet.get("scope", {})
    allowed    = scope.get("allowed_changes", [])
    forbidden  = scope.get("forbidden_changes", [])

    if "text_only" in allowed or "wording" in allowed:
        # Cek apakah ada perubahan angka
        if decision == "revise":
            orig  = patch.get("original_text","")
            final = patch.get("final_text","")
            if "numeric_values" in forbidden and _contains_numeric_change(orig, final):
                errors.append(
                    f"SCOPE_VIOLATION: packet scope melarang perubahan 'numeric_values', "
                    f"tetapi ada perubahan angka antara original dan final text"
                )

    # ── 7. forbidden_changes tidak boleh disentuh ──────────
    # Ini cek berbasis keyword di teks patch — heuristik
    if decision == "revise" and forbidden:
        final = patch.get("final_text","").lower()
        for forbidden_field in forbidden:
            if forbidden_field == "sroi_values":
                # Cek apakah ada ratio baru di final text yang tidak ada di original
                orig = patch.get("original_text","").lower()
                orig_ratios = set(re.findall(r'1\s*:\s*[\d,\.]+', orig))
                final_ratios = set(re.findall(r'1\s*:\s*[\d,\.]+', final))
                if final_ratios - orig_ratios:
                    errors.append(
                        f"SCOPE_VIOLATION: forbidden 'sroi_values' — "
                        f"ada rasio SROI baru di final text: {final_ratios - orig_ratios}"
                    )

    # ── 8. original_text wajib ada (audit trail) ───────────
    if not patch.get("original_text"):
        errors.append("MISSING_ORIGINAL_TEXT: original_text wajib ada untuk audit trail")

    # ── 9. review_context wajib ada ────────────────────────
    if not patch.get("review_context"):
        errors.append("MISSING_REVIEW_CONTEXT: review_context (label sesi) wajib ada")

    return errors


def validate_patch_batch(patches: list, packets: list) -> dict:
    """Validasi batch patches terhadap packets yang sesuai."""
    packet_map = {p["packet_id"]: p for p in packets}
    results    = {"valid": [], "invalid": [], "errors": {}}

    for patch in patches:
        pid    = patch.get("source_packet_id","")
        packet = packet_map.get(pid)

        if not packet:
            results["invalid"].append(patch.get("patch_id","?"))
            results["errors"][patch.get("patch_id","?")] = [
                f"PACKET_NOT_FOUND: source_packet_id '{pid}' tidak ditemukan"
            ]
            continue

        errs = validate_patch(patch, packet)
        if errs:
            results["invalid"].append(patch.get("patch_id","?"))
            results["errors"][patch.get("patch_id","?")] = errs
        else:
            results["valid"].append(patch.get("patch_id","?"))

    return results


# ── Standalone test ────────────────────────────────────────────
if __name__ == "__main__":
    import uuid
    from datetime import datetime

    print("=== Patch Validator Self-Test ===\n")

    # Load sample packet
    sample_packet_path = SCRIPT_DIR / "semantic_packets_bab7.json"
    if not sample_packet_path.exists():
        print("SKIP: semantic_packets_bab7.json tidak ditemukan")
        sys.exit(0)

    packets = json.load(open(sample_packet_path))
    pkt     = packets[0]

    # Test 1: VALID patch
    valid_patch = {
        "patch_id":            "test_valid_001",
        "source_packet_id":    pkt["packet_id"],
        "decision":            "revise",
        "review_basis":        "terminology",
        "original_text":       pkt["context"]["current_text"],
        "final_text":          "Gunakan istilah 'Blended SROI' secara konsisten untuk rasio evaluatif total. Bedakan secara eksplisit dari 'Observed direct return' di setiap penyebutan pertama.",
        "reviewer_note":       "Diperjelas dengan instruksi 'penyebutan pertama'",
        "rejection_reason":    None,
        "timestamp":           datetime.now().isoformat(),
        "review_context":      "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
        "scope_verified":      True,
    }
    errs1 = validate_patch(valid_patch, pkt)
    print(f"Test 1 (valid patch): {'PASS ✓' if not errs1 else f'FAIL ✗ {errs1}'}")

    # Test 2: INVALID — mengubah angka di text_only packet
    invalid_numeric_patch = {
        "patch_id":            "test_invalid_numeric",
        "source_packet_id":    pkt["packet_id"],
        "decision":            "revise",
        "review_basis":        "terminology",
        "original_text":       pkt["context"]["current_text"],
        "final_text":          "SROI adalah 1 : 1,10 bukan 1 : 1,03",  # perubahan angka
        "reviewer_note":       "Mengubah angka",
        "rejection_reason":    None,
        "timestamp":           datetime.now().isoformat(),
        "review_context":      "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
    }
    errs2 = validate_patch(invalid_numeric_patch, pkt)
    has_numeric_err = any("numeric" in e.lower() or "scope" in e.lower() for e in errs2)
    print(f"Test 2 (numeric change in text_only): {'PASS ✓' if has_numeric_err else 'FAIL ✗ (should detect numeric change)'}")

    # Test 3: INVALID — missing context
    invalid_context_patch = {
        "patch_id":            "test_invalid_ctx",
        "source_packet_id":    pkt["packet_id"],
        "decision":            "accept",
        "review_basis":        "terminology",
        "original_text":       pkt["context"]["current_text"],
        "final_text":          pkt["context"]["current_text"],
        "reviewer_note":       "",
        "timestamp":           datetime.now().isoformat(),
        "review_context":      "Sprint13_ESL_Pilot",
        "applicability_context": "",   # missing!
    }
    errs3 = validate_patch(invalid_context_patch, pkt)
    has_ctx_err = any("context" in e.lower() for e in errs3)
    print(f"Test 3 (missing context): {'PASS ✓' if has_ctx_err else 'FAIL ✗ (should detect missing context)'}")

    # Test 4: INVALID — reject without reason
    invalid_reject = {
        "patch_id":            "test_invalid_reject",
        "source_packet_id":    pkt["packet_id"],
        "decision":            "reject",
        "review_basis":        "tone",
        "original_text":       pkt["context"]["current_text"],
        "final_text":          "",
        "reviewer_note":       "",
        "rejection_reason":    None,  # missing!
        "timestamp":           datetime.now().isoformat(),
        "review_context":      "Sprint13_ESL_Pilot",
        "applicability_context": "ESL_Pertamina_2025",
    }
    errs4 = validate_patch(invalid_reject, pkt)
    has_rej_err = any("rejection_reason" in e.lower() for e in errs4)
    print(f"Test 4 (reject without reason): {'PASS ✓' if has_rej_err else 'FAIL ✗ (should detect missing rejection_reason)'}")

    all_pass = not errs1 and has_numeric_err and has_ctx_err and has_rej_err
    print(f"\nValidator self-test: {'ALL PASS ✓' if all_pass else 'SOME TESTS FAILED'}")
