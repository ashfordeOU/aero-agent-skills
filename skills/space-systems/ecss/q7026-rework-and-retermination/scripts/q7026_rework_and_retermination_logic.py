"""Rework and re-termination limits for crimped connections.

Anchor: ECSS-Q-ST-70-26C, the rework clause of the crimping practice --
how many times a wire end may be cut back and crimped again, what each
remake costs the wire, and which defects have no rework path at all
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. A remake is bought with wire. Every re-termination cuts the failed
   barrel off and strips again, so the wire gets shorter by a fixed
   amount each time. The limit that bites first is usually length, not
   the count.
2. The count limit exists anyway. Repeated stripping work-hardens and
   nicks the conductor in ways an inspection does not see, so a wire
   end carries a maximum number of re-terminations independent of how
   much length is left.
3. A crimped contact is consumed by its crimp. The barrel is plastically
   deformed, so removing it ends its life; the remake needs a new
   contact, and a rule that lets one be re-crimped is rejected rather
   than obeyed.
4. Some defects have no rework path. Conductor damage inside the
   insulation, or damage to the connector housing, is not cured by
   cutting the barrel off, so those categories scrap rather than
   remake.
5. Length is judged after the cut, not before. The test is whether the
   wire still reaches its routed length with the declared slack once
   the next remake has taken its share.
6. A wire that lands exactly on its required length still reaches. The
   comparison absorbs representation error from the length arithmetic;
   the required slack is never trimmed to make a remake fit.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

REMAKE = "remake-permitted-with-a-new-contact"
REPLACE_WIRE = "replace-the-wire"
NO_REWORK = "no-rework-path-scrap-the-termination"

_DISPOSITIONS = (REMAKE, REPLACE_WIRE, NO_REWORK)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _count(label, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_rules(rules):
    """Validate the declared rework rule set."""
    if not isinstance(rules, dict):
        raise ValueError("rules must be a mapping")

    per_remake = _numeric(
        "length_per_retermination_mm", rules.get("length_per_retermination_mm"), 0.0
    )
    if per_remake <= 0.0:
        raise ValueError("length_per_retermination_mm must be greater than zero")

    reworkable = rules.get("reworkable_defects")
    scrap_only = rules.get("scrap_only_defects")
    if not isinstance(reworkable, list) or not reworkable:
        raise ValueError("reworkable_defects must be a non-empty list")
    if not isinstance(scrap_only, list):
        raise ValueError("scrap_only_defects must be a list")
    reworkable = [_text("reworkable_defect", d).lower() for d in reworkable]
    scrap_only = [_text("scrap_only_defect", d).lower() for d in scrap_only]
    overlap = sorted(set(reworkable) & set(scrap_only))
    if overlap:
        raise ValueError(
            "defect categories are both reworkable and scrap-only: %s"
            % ", ".join(overlap)
        )

    reusable = rules.get("reusable_contact_types", [])
    if not isinstance(reusable, list):
        raise ValueError("reusable_contact_types must be a list")
    reusable = [_text("reusable_contact_type", c).lower() for c in reusable]
    if "crimp" in reusable:
        raise ValueError(
            "a crimp contact is consumed by its crimp and cannot be declared "
            "reusable"
        )

    return {
        "max_reterminations_per_wire_end": _count(
            "max_reterminations_per_wire_end",
            rules.get("max_reterminations_per_wire_end"),
            1,
        ),
        "length_per_retermination_mm": per_remake,
        "required_slack_mm": _numeric(
            "required_slack_mm", rules.get("required_slack_mm", 0.0), 0.0
        ),
        "reworkable_defects": reworkable,
        "scrap_only_defects": scrap_only,
        "reusable_contact_types": reusable,
    }


def validate_wire_end(wire):
    """Validate one wire end presented for re-termination."""
    if not isinstance(wire, dict):
        raise ValueError("wire must be a mapping")
    present = _numeric("present_length_mm", wire.get("present_length_mm"), 0.0)
    routed = _numeric("routed_length_mm", wire.get("routed_length_mm"), 0.0)
    if present <= 0.0:
        raise ValueError("present_length_mm must be greater than zero")
    if routed <= 0.0:
        raise ValueError("routed_length_mm must be greater than zero")
    if present + TOLERANCE < routed:
        raise ValueError(
            "present_length_mm is already shorter than routed_length_mm"
        )
    return {
        "wire_id": _text("wire_id", wire.get("wire_id")),
        "contact_type": _text("contact_type", wire.get("contact_type")).lower(),
        "present_length_mm": present,
        "routed_length_mm": routed,
        "reterminations_taken": _count(
            "reterminations_taken", wire.get("reterminations_taken", 0), 0
        ),
    }


def contact_may_be_reused(contact_type, rules):
    """Is a contact of this type reusable after it is removed?"""
    checked = validate_rules(rules)
    return _text("contact_type", contact_type).lower() in checked[
        "reusable_contact_types"
    ]


def defect_allows_rework(defect_code, rules):
    """Does this defect category have a rework path at all?"""
    checked = validate_rules(rules)
    code = _text("defect_code", defect_code).lower()
    if code in checked["reworkable_defects"]:
        return True
    if code in checked["scrap_only_defects"]:
        return False
    raise ValueError(
        "defect category %r is in neither the reworkable nor the scrap-only "
        "list" % code
    )


def reterminations_remaining(wire, rules):
    """How many re-terminations the count limit still allows."""
    checked_wire = validate_wire_end(wire)
    checked_rules = validate_rules(rules)
    remaining = (
        checked_rules["max_reterminations_per_wire_end"]
        - checked_wire["reterminations_taken"]
    )
    return max(0, remaining)


def length_after_remake(wire, rules):
    """The wire length left once the next remake has taken its share."""
    checked_wire = validate_wire_end(wire)
    checked_rules = validate_rules(rules)
    return (
        checked_wire["present_length_mm"]
        - checked_rules["length_per_retermination_mm"]
    )


def length_budget_allows_remake(wire, rules):
    """Does the wire still reach its routed length after the next remake?"""
    checked_wire = validate_wire_end(wire)
    checked_rules = validate_rules(rules)
    needed = checked_wire["routed_length_mm"] + checked_rules["required_slack_mm"]
    return length_after_remake(wire, rules) >= needed - TOLERANCE


def assess_retermination(wire, defect_code, rules):
    """Decide whether this wire end may be re-terminated."""
    checked_wire = validate_wire_end(wire)
    checked_rules = validate_rules(rules)
    reasons = []

    if not defect_allows_rework(defect_code, rules):
        return {
            "wire_id": checked_wire["wire_id"],
            "disposition": NO_REWORK,
            "reasons": ["defect-category-has-no-rework-path"],
            "reterminations_remaining": reterminations_remaining(wire, rules),
            "length_after_remake_mm": length_after_remake(wire, rules),
            "new_contact_required": True,
            "permitted": False,
        }

    if reterminations_remaining(wire, rules) <= 0:
        reasons.append("re-termination-count-limit-reached")
    if not length_budget_allows_remake(wire, rules):
        reasons.append("wire-too-short-after-the-next-remake")

    disposition = REPLACE_WIRE if reasons else REMAKE
    return {
        "wire_id": checked_wire["wire_id"],
        "disposition": disposition,
        "reasons": reasons,
        "reterminations_remaining": reterminations_remaining(wire, rules),
        "length_after_remake_mm": length_after_remake(wire, rules),
        "new_contact_required": not contact_may_be_reused(
            checked_wire["contact_type"], checked_rules
        ),
        "permitted": disposition == REMAKE,
    }


def assess_rework_batch(items, rules):
    """Roll a set of re-termination decisions up for a harness."""
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    results = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each item must be a mapping")
        results.append(
            assess_retermination(item.get("wire"), item.get("defect_code"), rules)
        )
    return {
        "results": results,
        "remake": [r["wire_id"] for r in results if r["disposition"] == REMAKE],
        "replace_wire": [
            r["wire_id"] for r in results if r["disposition"] == REPLACE_WIRE
        ],
        "scrap": [r["wire_id"] for r in results if r["disposition"] == NO_REWORK],
        "new_contacts_needed": sum(
            1 for r in results if r["new_contact_required"]
        ),
        "all_reworkable": all(r["permitted"] for r in results),
    }
