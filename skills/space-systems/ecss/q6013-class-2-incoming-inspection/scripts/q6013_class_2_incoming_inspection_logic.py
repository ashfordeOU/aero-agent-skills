"""Receiving inspection of an intermediate assurance commercial EEE delivery.

Anchor: ECSS-Q-ST-60-13C clause 5.3.7 (the checks carried out when a delivery
of parts of the intermediate assurance class arrives on site). Paraphrased
into an implementable procedure; no standard text is reproduced.

What the intermediate class changes
-----------------------------------
The depth of the receiving inspection is allowed to follow the confidence the
receiving organisation has earned in the supplier, so the first output of this
module is not a verdict but an inspection level. A supplier with a long clean
record is inspected less; a delivery routed through an unfranchised source is
inspected more, whatever that record says, because the risk it carries is
substitution rather than workmanship.

Procedure implemented here
--------------------------
1. Set the inspection level from the delivery history, then let the source
   type override it upward. The override is one-way: history can never earn a
   reduction out of an unfranchised source.
2. Size the sample for that level from the quantity actually received, in
   integer arithmetic, floored for small lots, capped for large ones and
   clamped to the lot.
3. Reconcile part number, date code and quantity against the order as three
   separate comparisons.
4. Judge the visual defects found against the level's accept number.
5. Check the documents that must travel with the parts.
6. Release to store or quarantine, and set the level the next delivery from
   this supplier will be inspected at.
"""

import math

__all__ = [
    "INSPECTION_LEVELS",
    "SOURCE_TYPES",
    "REQUIRED_DOCUMENTS",
    "DEFAULT_ACCEPT_NUMBER",
    "REDUCED_AFTER_CLEAN",
    "SKIP_AFTER_CLEAN",
    "SAMPLE_FLOOR",
    "SAMPLE_CAP",
    "determine_level",
    "sample_size",
    "accept_number_for",
    "reconcile_part_number",
    "reconcile_date_code",
    "quantity_discrepancy",
    "missing_documents",
    "next_inspection_level",
    "assess_class_2_receipt",
]

# Ordered from the lightest inspection to the heaviest; the index is the
# escalation order.
INSPECTION_LEVELS = ("skip-lot", "reduced", "normal", "tightened")

# Where the delivery came from. Only the first two can ever earn a reduction.
SOURCE_TYPES = ("manufacturer", "franchised-distributor", "unfranchised-broker")

# The paperwork an intermediate assurance delivery cannot be received without.
REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "manufacturer-traceability",
    "packaging-declaration",
)

# Consecutive accepted deliveries needed before the level is eased.
REDUCED_AFTER_CLEAN = 5
SKIP_AFTER_CLEAN = 20

# Sample bounds applied after the level multiplier, before clamping to the lot.
SAMPLE_FLOOR = 3
SAMPLE_CAP = 50

# Accept-on-zero is the default. A receiving organisation may declare a larger
# allowance for cosmetic defects, but a tightened inspection never honours it.
DEFAULT_ACCEPT_NUMBER = 0


def _clean_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _whole_number(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def determine_level(history, source_type, traceability_evidenced=True):
    """Return the inspection level this delivery is received at, with reasons.

    history keys: consecutive_accepted (whole number of clean deliveries since
    the last rejection) and last_delivery_rejected.
    """
    if not isinstance(history, dict):
        raise ValueError("history must be a mapping")
    for key in ("consecutive_accepted", "last_delivery_rejected"):
        if key not in history:
            raise ValueError("history missing required key '%s'" % key)
    clean = _whole_number(history["consecutive_accepted"], "consecutive_accepted")
    rejected = history["last_delivery_rejected"]
    if not isinstance(rejected, bool):
        raise ValueError("last_delivery_rejected must be True or False")
    if not isinstance(traceability_evidenced, bool):
        raise ValueError("traceability_evidenced must be True or False")
    source = _clean_text(source_type, "source_type").lower()
    if source not in SOURCE_TYPES:
        raise ValueError("source_type must be one of %s, got %r" % (SOURCE_TYPES, source_type))

    reasons = []
    if clean >= SKIP_AFTER_CLEAN and traceability_evidenced:
        level = "skip-lot"
        reasons.append("%d consecutive accepted deliveries with traceability evidenced" % clean)
    elif clean >= REDUCED_AFTER_CLEAN:
        level = "reduced"
        reasons.append("%d consecutive accepted deliveries" % clean)
    else:
        level = "normal"
        reasons.append("delivery history has not yet earned a reduction")
    if clean >= SKIP_AFTER_CLEAN and not traceability_evidenced:
        reasons.append("reduction limited: traceability to the manufacturer is not evidenced")
    if rejected:
        level = "tightened"
        reasons.append("the previous delivery from this supplier was rejected")
    if source == "unfranchised-broker":
        level = "tightened"
        reasons.append("unfranchised source: substitution risk overrides the delivery history")
    return {"level": level, "source_type": source, "reasons": reasons}


def sample_size(level, received_quantity, floor=SAMPLE_FLOOR, cap=SAMPLE_CAP):
    """Return the external visual sample for a level, in integer arithmetic only."""
    level_key = _clean_text(level, "level").lower()
    if level_key not in INSPECTION_LEVELS:
        raise ValueError("level must be one of %s, got %r" % (INSPECTION_LEVELS, level))
    quantity = _whole_number(received_quantity, "received_quantity", minimum=1)
    _whole_number(floor, "floor", minimum=0)
    _whole_number(cap, "cap", minimum=1)
    if cap < floor:
        raise ValueError("cap must be at or above floor")
    if level_key == "skip-lot":
        return 0
    base = math.isqrt(quantity)
    if level_key == "tightened":
        sized = base * 2
    elif level_key == "reduced":
        sized = (base + 1) // 2
    else:
        sized = base
    sized = max(sized, floor)
    sized = min(sized, cap)
    return min(sized, quantity)


def accept_number_for(level, declared=DEFAULT_ACCEPT_NUMBER):
    """Return the sample defects tolerated at this level.

    Accept-on-zero is the default and a declared allowance is honoured at every
    level except tightened, where the reason the level was raised is the reason
    the allowance is withdrawn.
    """
    level_key = _clean_text(level, "level").lower()
    if level_key not in INSPECTION_LEVELS:
        raise ValueError("level must be one of %s, got %r" % (INSPECTION_LEVELS, level))
    _whole_number(declared, "declared accept number")
    if level_key == "tightened":
        return 0
    return declared


def reconcile_part_number(ordered, received):
    """Compare the ordered and received part numbers, ignoring case and spacing."""
    left = _clean_text(ordered, "ordered_part_number").lower()
    right = _clean_text(received, "received_part_number").lower()
    return {"ordered": left, "received": right, "matches": left == right}


def reconcile_date_code(ordered, received):
    """Compare the ordered and received date codes.

    An order placed without a date code constraint matches anything; a stated
    date code that does not match is a different lot with different evidence
    behind it.
    """
    if ordered is None:
        right = _clean_text(received, "received_date_code").lower()
        return {"ordered": None, "received": right, "matches": True, "constrained": False}
    left = _clean_text(ordered, "ordered_date_code").lower()
    right = _clean_text(received, "received_date_code").lower()
    return {"ordered": left, "received": right, "matches": left == right, "constrained": True}


def quantity_discrepancy(ordered, received):
    """Return the shortfall and overage as separate non-negative numbers."""
    want = _whole_number(ordered, "ordered_quantity", minimum=1)
    got = _whole_number(received, "received_quantity", minimum=1)
    return {
        "ordered": want,
        "received": got,
        "shortfall": max(want - got, 0),
        "overage": max(got - want, 0),
    }


def missing_documents(documents, required=REQUIRED_DOCUMENTS):
    """Return the required delivery documents absent or marked not received."""
    if not isinstance(required, (list, tuple)) or not required:
        raise ValueError("required must be a non-empty sequence of document names")
    if isinstance(documents, (list, tuple, set, frozenset)):
        documents = {str(item): True for item in documents}
    if not isinstance(documents, dict):
        raise ValueError("documents must be a mapping or a sequence of document names")
    present = {}
    for key, value in documents.items():
        name = _clean_text(key, "document name").lower()
        if not isinstance(value, bool):
            raise ValueError("documents['%s'] must be True or False, got %r" % (name, value))
        present[name] = value
    absent = []
    for item in required:
        name = _clean_text(item, "required document name").lower()
        if not present.get(name, False):
            absent.append(name)
    return absent


def next_inspection_level(current_level, accepted, defects_found):
    """Return the level the next delivery from this supplier is received at."""
    level_key = _clean_text(current_level, "current_level").lower()
    if level_key not in INSPECTION_LEVELS:
        raise ValueError("current_level must be one of %s, got %r" % (INSPECTION_LEVELS, current_level))
    if not isinstance(accepted, bool):
        raise ValueError("accepted must be True or False")
    _whole_number(defects_found, "defects_found")
    if not accepted:
        return "tightened"
    if defects_found > 0 and level_key in ("skip-lot", "reduced"):
        return "normal"
    return level_key


def assess_class_2_receipt(spec):
    """Run the full clause 5.3.7 receiving assessment for one delivery.

    spec keys: delivery_id, ordered_part_number, received_part_number,
    ordered_quantity, received_quantity, source_type, history, documents and
    visual_defects, plus optional ordered_date_code, received_date_code,
    traceability_evidenced and declared_accept_number.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "delivery_id",
        "ordered_part_number",
        "received_part_number",
        "ordered_quantity",
        "received_quantity",
        "source_type",
        "history",
        "documents",
        "visual_defects",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    delivery_id = _clean_text(spec["delivery_id"], "delivery_id")
    traceability = spec.get("traceability_evidenced", True)
    level_result = determine_level(spec["history"], spec["source_type"], traceability)
    level = level_result["level"]
    quantity = quantity_discrepancy(spec["ordered_quantity"], spec["received_quantity"])
    drawn = sample_size(level, quantity["received"])
    accept = accept_number_for(level, spec.get("declared_accept_number", DEFAULT_ACCEPT_NUMBER))
    defects = _whole_number(spec["visual_defects"], "visual_defects")
    if defects > drawn:
        raise ValueError(
            "visual_defects %d exceeds the sample of %d actually inspected" % (defects, drawn)
        )
    part = reconcile_part_number(spec["ordered_part_number"], spec["received_part_number"])
    date_code = reconcile_date_code(
        spec.get("ordered_date_code"), spec.get("received_date_code", "unmarked")
    )
    absent_documents = missing_documents(spec["documents"])

    findings = []
    if not part["matches"]:
        findings.append(
            "part number '%s' received against '%s' ordered" % (part["received"], part["ordered"])
        )
    if not date_code["matches"]:
        findings.append(
            "date code '%s' received against '%s' ordered" % (date_code["received"], date_code["ordered"])
        )
    if quantity["shortfall"]:
        findings.append("%d part(s) short of the ordered quantity" % quantity["shortfall"])
    if absent_documents:
        findings.append("delivery documents not received: %s" % ", ".join(absent_documents))
    if defects > accept:
        findings.append(
            "%d visual defect(s) in a sample of %d against an accept number of %d"
            % (defects, drawn, accept)
        )

    advisories = []
    if quantity["overage"]:
        advisories.append("%d part(s) over the ordered quantity" % quantity["overage"])
    if level == "skip-lot":
        advisories.append("received under a skip-lot level: identity and documents only")
    for reason in level_result["reasons"]:
        if reason.startswith("unfranchised source") or reason.startswith("reduction limited"):
            advisories.append(reason)

    accepted = not findings
    return {
        "delivery_id": delivery_id,
        "level": level,
        "level_reasons": level_result["reasons"],
        "sample_size": drawn,
        "accept_number": accept,
        "visual_defects": defects,
        "part_number": part,
        "date_code": date_code,
        "quantity": quantity,
        "missing_documents": absent_documents,
        "findings": findings,
        "advisories": advisories,
        "accepted": accepted,
        "disposition": "accept-to-store" if accepted else "quarantine",
        "next_level": next_inspection_level(level, accepted, defects),
    }
