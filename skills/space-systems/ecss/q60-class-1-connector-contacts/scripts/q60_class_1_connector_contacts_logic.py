#!/usr/bin/env python3
"""Sourcing removable contacts for a class 1 connector.

Anchor: ECSS-Q-ST-60C clause 4.6.6 (removable contacts fitted to connectors in
class 1 equipment are obtained from approved manufacturers only). Paraphrased
into an implementable procedure; no standard text is reproduced.

A removable contact is the one part of a connector that is bought separately,
fitted by hand, and invisible once the backshell is on. It is also the part
that carries the current and makes the only metal-to-metal interface in the
mated pair. The clause closes that gap the simplest way there is: the contact
comes from an approved manufacturer, and a contact whose source cannot be shown
is not fitted, whatever it measures on the bench.

Procedure implemented here
--------------------------
1. Check the contact manufacturer against the approved manufacturer list, on a
   normalized name so spacing and capitalization cannot hide a match or invent
   one.
2. Check the traceability record actually ties the contacts in hand back to
   that manufacturer and to a detail specification.
3. Check a contact from one manufacturer fitted into another manufacturer's
   connector carries qualification evidence for the pair.
4. Check the application: the wire gauge sits inside the range the contact
   size accommodates, and the applied current sits inside the derated rating.
5. Check the crimp tooling and its acceptance record.
6. Return a verdict in precedence order together with every finding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "CONTACT_SIZES",
    "CONTACT_FINISHES",
    "TRACEABILITY_ITEMS",
    "TOOLING_ITEMS",
    "DEFAULT_CONTACT_POLICY",
    "SOURCE_NOT_APPROVED",
    "TRACEABILITY_INCOMPLETE",
    "INTERMIX_NOT_QUALIFIED",
    "APPLICATION_MISMATCH",
    "TOOLING_NOT_QUALIFIED",
    "CONTACT_ACCEPTED",
    "validate_contact_policy",
    "normalize_manufacturer",
    "manufacturer_is_approved",
    "missing_traceability",
    "missing_tooling_controls",
    "accommodated_gauge_range",
    "wire_gauge_is_accommodated",
    "rated_contact_current_a",
    "derated_contact_current_a",
    "contact_current_margin_a",
    "intermix_findings",
    "validate_contact_case",
    "assess_contact_sourcing",
]

# Removable contact sizes, the current each is rated to carry, and the wire
# gauge range each accommodates. American wire gauge counts downwards, so the
# smallest number in the range is the largest conductor the barrel takes.
CONTACT_SIZES = {
    "22d": {"rated_current_a": 5.0, "largest_awg": 22, "smallest_awg": 28},
    "20": {"rated_current_a": 7.5, "largest_awg": 20, "smallest_awg": 24},
    "16": {"rated_current_a": 13.0, "largest_awg": 16, "smallest_awg": 20},
    "12": {"rated_current_a": 23.0, "largest_awg": 12, "smallest_awg": 14},
    "8": {"rated_current_a": 46.0, "largest_awg": 8, "smallest_awg": 10},
}

CONTACT_FINISHES = ("gold-over-nickel", "gold-over-copper", "silver")

# What ties the contacts in the bag back to the approved source.
TRACEABILITY_ITEMS = (
    "manufacturer_lot_code",
    "date_code",
    "certificate_of_conformance",
    "detail_specification_reference",
)

# What makes a crimp a controlled process rather than a hand operation.
TOOLING_ITEMS = (
    "crimp_tool_identifier",
    "positioner_identifier",
    "tool_calibration_record",
    "crimp_acceptance_record",
)

DEFAULT_CONTACT_POLICY = {
    # Share of the rated current a class 1 harness is allowed to apply.
    "current_derating_factor": 0.5,
    # Whether a contact and shell from different makers need pair evidence.
    "require_intermix_qualification": True,
    # Whether the crimp tooling record is mandatory.
    "require_tooling_qualification": True,
    # There is no waiver route for an unapproved source at class 1.
    "allow_unapproved_source_waiver": False,
}

SOURCE_NOT_APPROVED = "contact-source-not-approved"
TRACEABILITY_INCOMPLETE = "contact-traceability-incomplete"
INTERMIX_NOT_QUALIFIED = "contact-intermix-not-qualified"
APPLICATION_MISMATCH = "contact-application-mismatch"
TOOLING_NOT_QUALIFIED = "contact-tooling-not-qualified"
CONTACT_ACCEPTED = "contact-accepted-for-class-1"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A derated current is a rating multiplied by a policy share, so a circuit
    sitting exactly on its allowance can land a few units in the last place
    above it. The allowance is never raised; only the comparison tolerates the
    representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_contact_policy(policy=None):
    """Return a complete sourcing policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CONTACT_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("contact policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CONTACT_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CONTACT_POLICY:
            raise ValueError("unknown contact policy key %r" % (key,))
        merged[key] = value
    factor = _require_positive(
        "current_derating_factor", merged["current_derating_factor"]
    )
    if factor > 1.0:
        raise ValueError(
            "current_derating_factor must not exceed 1.0, got %r" % (factor,)
        )
    for key in (
        "require_intermix_qualification",
        "require_tooling_qualification",
        "allow_unapproved_source_waiver",
    ):
        if not isinstance(merged[key], bool):
            raise ValueError("%s must be a boolean" % key)
    return merged


def normalize_manufacturer(name):
    """Fold a manufacturer name so spacing and case cannot hide a match."""
    if not isinstance(name, str):
        raise ValueError("manufacturer name must be a string, got %r" % (name,))
    folded = " ".join(name.split()).casefold()
    if not folded:
        raise ValueError("manufacturer name is blank; the source cannot be checked")
    return folded


def manufacturer_is_approved(manufacturer, approved_manufacturers):
    """Whether the contact manufacturer appears on the approved source list."""
    if isinstance(approved_manufacturers, str) or not hasattr(
        approved_manufacturers, "__iter__"
    ):
        raise ValueError(
            "approved_manufacturers must be an iterable of names, got %r"
            % (approved_manufacturers,)
        )
    approved = {normalize_manufacturer(name) for name in approved_manufacturers}
    if not approved:
        raise ValueError(
            "the approved manufacturer list is empty; no contact can be sourced "
            "against it"
        )
    return normalize_manufacturer(manufacturer) in approved


def missing_traceability(record):
    """Traceability items the delivery does not carry."""
    if not isinstance(record, dict):
        raise ValueError("traceability record must be a mapping, got %r" % (record,))
    unknown = set(record) - set(TRACEABILITY_ITEMS)
    if unknown:
        raise ValueError("unknown traceability items: %s" % ", ".join(sorted(unknown)))
    missing = []
    for item in TRACEABILITY_ITEMS:
        value = record.get(item)
        if value is None:
            missing.append(item)
        elif isinstance(value, str) and not value.strip():
            missing.append(item)
        elif isinstance(value, bool) and not value:
            missing.append(item)
    return tuple(missing)


def missing_tooling_controls(record):
    """Crimp tooling items the process record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("tooling record must be a mapping, got %r" % (record,))
    unknown = set(record) - set(TOOLING_ITEMS)
    if unknown:
        raise ValueError("unknown tooling items: %s" % ", ".join(sorted(unknown)))
    missing = []
    for item in TOOLING_ITEMS:
        value = record.get(item)
        if value is None:
            missing.append(item)
        elif isinstance(value, str) and not value.strip():
            missing.append(item)
        elif isinstance(value, bool) and not value:
            missing.append(item)
    return tuple(missing)


def _require_size(size):
    if not isinstance(size, str):
        raise ValueError("contact size must be a string, got %r" % (size,))
    key = size.strip().casefold()
    if key not in CONTACT_SIZES:
        raise ValueError(
            "unknown contact size %r; known sizes are %s"
            % (size, ", ".join(sorted(CONTACT_SIZES)))
        )
    return key


def accommodated_gauge_range(size):
    """Largest and smallest wire gauge the contact barrel accommodates."""
    key = _require_size(size)
    entry = CONTACT_SIZES[key]
    return (entry["largest_awg"], entry["smallest_awg"])


def wire_gauge_is_accommodated(size, wire_awg):
    """Whether the conductor fits the barrel of that contact size."""
    largest, smallest = accommodated_gauge_range(size)
    if not _is_int(wire_awg):
        raise ValueError("wire_awg must be an integer gauge, got %r" % (wire_awg,))
    if wire_awg <= 0:
        raise ValueError("wire_awg must be a positive gauge, got %r" % (wire_awg,))
    return largest <= wire_awg <= smallest


def rated_contact_current_a(size):
    """Current the contact size is rated to carry before derating."""
    return CONTACT_SIZES[_require_size(size)]["rated_current_a"]


def derated_contact_current_a(size, derating_factor=None, policy=None):
    """Current the class 1 derating policy allows through that contact."""
    rated = rated_contact_current_a(size)
    if derating_factor is None:
        derating_factor = validate_contact_policy(policy)["current_derating_factor"]
    factor = _require_positive("derating_factor", derating_factor)
    if factor > 1.0:
        raise ValueError("derating_factor must not exceed 1.0, got %r" % (factor,))
    return rated * factor


def contact_current_margin_a(size, applied_current_a, derating_factor=None, policy=None):
    """Headroom between the derated allowance and the applied current."""
    allowance = derated_contact_current_a(size, derating_factor, policy)
    applied = _require_non_negative("applied_current_a", applied_current_a)
    return allowance - applied


def intermix_findings(case, policy=None):
    """Findings raised by fitting one maker's contact into another's shell."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    resolved = validate_contact_policy(policy)
    contact_maker = normalize_manufacturer(case.get("contact_manufacturer"))
    shell_maker = normalize_manufacturer(case.get("connector_manufacturer"))
    if contact_maker == shell_maker:
        return {"intermixed": False, "qualified": True, "findings": []}
    reference = case.get("intermix_qualification_reference")
    has_reference = isinstance(reference, str) and bool(reference.strip())
    if not resolved["require_intermix_qualification"]:
        return {"intermixed": True, "qualified": True, "findings": []}
    if has_reference:
        return {"intermixed": True, "qualified": True, "findings": []}
    return {
        "intermixed": True,
        "qualified": False,
        "findings": [
            "the contact and the connector shell come from different "
            "manufacturers and no qualification of the pair is referenced"
        ],
    }


def validate_contact_case(case):
    """Check a sourcing case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for field in (
        "contact_manufacturer",
        "connector_manufacturer",
        "contact_size",
        "wire_awg",
        "applied_current_a",
        "approved_manufacturers",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    _require_size(case["contact_size"])
    finish = case.get("contact_finish")
    if finish is not None and finish not in CONTACT_FINISHES:
        raise ValueError(
            "contact_finish must be one of %s, got %r"
            % (", ".join(CONTACT_FINISHES), finish)
        )
    return case


def assess_contact_sourcing(case, policy=None):
    """Full clause 4.6.6 sourcing decision with a verdict and every finding."""
    validate_contact_case(case)
    resolved = validate_contact_policy(policy)
    findings = []

    approved = manufacturer_is_approved(
        case["contact_manufacturer"], case["approved_manufacturers"]
    )
    if not approved:
        findings.append(
            "the contact manufacturer is not on the approved source list and "
            "class 1 admits no other source"
        )

    traceability_gaps = missing_traceability(case.get("traceability", {}))
    if traceability_gaps:
        findings.append(
            "the delivery does not carry %s" % ", ".join(sorted(traceability_gaps))
        )

    intermix = intermix_findings(case, resolved)
    findings.extend(intermix["findings"])

    size = _require_size(case["contact_size"])
    gauge_ok = wire_gauge_is_accommodated(size, case["wire_awg"])
    largest, smallest = accommodated_gauge_range(size)
    if not gauge_ok:
        findings.append(
            "a %d gauge conductor is outside the %d to %d range that a size %s "
            "contact accommodates" % (case["wire_awg"], largest, smallest, size)
        )

    allowance = derated_contact_current_a(size, None, resolved)
    margin = contact_current_margin_a(
        size, case["applied_current_a"], None, resolved
    )
    current_ok = _at_most(float(case["applied_current_a"]), allowance)
    if not current_ok:
        findings.append(
            "the circuit draws %.3f A against a %.3f A derated allowance for a "
            "size %s contact" % (float(case["applied_current_a"]), allowance, size)
        )

    tooling_gaps = missing_tooling_controls(case.get("tooling", {}))
    tooling_ok = not (resolved["require_tooling_qualification"] and tooling_gaps)
    if not tooling_ok:
        findings.append(
            "the crimp process record does not carry %s"
            % ", ".join(sorted(tooling_gaps))
        )

    if not approved and not resolved["allow_unapproved_source_waiver"]:
        verdict = SOURCE_NOT_APPROVED
    elif traceability_gaps:
        verdict = TRACEABILITY_INCOMPLETE
    elif not intermix["qualified"]:
        verdict = INTERMIX_NOT_QUALIFIED
    elif not (gauge_ok and current_ok):
        verdict = APPLICATION_MISMATCH
    elif not tooling_ok:
        verdict = TOOLING_NOT_QUALIFIED
    else:
        verdict = CONTACT_ACCEPTED

    return {
        "verdict": verdict,
        "accepted": verdict == CONTACT_ACCEPTED,
        "source_approved": approved,
        "traceability_gaps": traceability_gaps,
        "intermixed": intermix["intermixed"],
        "intermix_qualified": intermix["qualified"],
        "contact_size": size,
        "accommodated_gauge_range": (largest, smallest),
        "wire_gauge_accommodated": gauge_ok,
        "derated_current_allowance_a": allowance,
        "current_margin_a": margin,
        "current_within_allowance": current_ok,
        "tooling_gaps": tooling_gaps,
        "findings": findings,
    }
