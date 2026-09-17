#!/usr/bin/env python3
"""Sourcing removable contacts for class 2 connectors from approved makers.

Anchor: ECSS-Q-ST-60C clause 5.6.6 (removable contacts fitted into class 2
connectors are taken from approved manufacturers only). Paraphrased into an
implementable procedure; no standard text is reproduced.

A removable contact is the one piece of a connector bought separately, fitted
by hand and invisible once the backshell is on. It also carries the current and
forms the only metal-to-metal interface in the mated pair. The clause closes
that gap the simplest way available: the contact comes from an approved
manufacturer, and nothing measured on the bench overturns a source that is not
on the list.

Procedure implemented here
--------------------------
1. Fold the offered manufacturer name and the approved source list onto a
   comparable key, and decide whether the offered name names an approved
   source, directly or through a recorded alias.
2. Name the traceability records the delivery is missing.
3. Decide whether the contact and the shell come from different sources and so
   owe intermateability evidence.
4. Test the conductor cross-section against the range the contact size
   accommodates, and the applied current against the class 2 derated allowance
   for the size and the number of energised contacts.
5. Return one disposition in precedence order, with every finding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "LEGAL_SUFFIX_TOKENS",
    "CONTACT_SIZES",
    "BUNDLE_DERATING_BANDS",
    "REQUIRED_TRACEABILITY_RECORDS",
    "DEFAULT_CONTACT_SOURCING_POLICY",
    "CONTACT_ADMISSIBLE",
    "CONTACT_TRACEABILITY_OUTSTANDING",
    "CONTACT_APPLICATION_NONCONFORMING",
    "CONTACT_SOURCE_NOT_APPROVED",
    "fold_manufacturer_name",
    "approved_source_match",
    "validate_contact_sourcing_policy",
    "validate_contact_case",
    "conductor_fit",
    "bundle_derating_factor",
    "derated_current_allowance_a",
    "current_utilisation",
    "traceability_gaps",
    "intermix_evidence_required",
    "assess_class2_contact_sourcing",
]

# Tokens that change a company's legal wrapper without changing the company.
# The fold removes them; it removes nothing else, because a fold that is too
# loose maps two different makers onto one key.
LEGAL_SUFFIX_TOKENS = (
    "gmbh",
    "ag",
    "kg",
    "mbh",
    "ltd",
    "limited",
    "plc",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "sa",
    "sas",
    "sarl",
    "srl",
    "spa",
    "bv",
    "nv",
    "oy",
    "ab",
    "as",
    "aps",
    "ou",
)

# Contact size -> accommodated conductor cross-section in square millimetres
# and the rated current of the size before any derating is applied.
CONTACT_SIZES = {
    "22d": {"min_mm2": 0.20, "max_mm2": 0.38, "rated_current_a": 5.0},
    "20": {"min_mm2": 0.38, "max_mm2": 0.62, "rated_current_a": 7.5},
    "16": {"min_mm2": 0.62, "max_mm2": 1.65, "rated_current_a": 13.0},
    "12": {"min_mm2": 1.65, "max_mm2": 3.31, "rated_current_a": 23.0},
    "8": {"min_mm2": 3.31, "max_mm2": 8.37, "rated_current_a": 46.0},
}

# A contact in a crowded shell cannot shed its own heat. Ascending contact
# counts; the first band the energised count falls at or below names the
# factor.
BUNDLE_DERATING_BANDS = (
    (2, 1.00),
    (8, 0.85),
    (24, 0.70),
    (60, 0.60),
    (float("inf"), 0.50),
)

REQUIRED_TRACEABILITY_RECORDS = (
    "lot-code",
    "date-code",
    "certificate-of-conformance",
    "detail-specification",
)

DEFAULT_CONTACT_SOURCING_POLICY = {
    # Share of the derated allowance the application may draw.
    "max_current_utilisation": 1.0,
    # Class 2 derating applied to the rated current of the contact size.
    "contact_current_derating_factor": 0.5,
    # Whether a contact and shell from different sources owe pair evidence.
    "require_intermix_qualification": True,
    # Whether an alias recorded against an approved source counts as a match.
    "accept_recorded_aliases": True,
}

CONTACT_ADMISSIBLE = "class-2-contact-admissible"
CONTACT_TRACEABILITY_OUTSTANDING = "class-2-contact-traceability-outstanding"
CONTACT_APPLICATION_NONCONFORMING = "class-2-contact-application-nonconforming"
CONTACT_SOURCE_NOT_APPROVED = "class-2-contact-source-not-approved"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def fold_manufacturer_name(name):
    """Fold a manufacturer name onto the key the approved list is matched on.

    Case, punctuation, separator runs and a trailing legal suffix all change
    the string without changing the company, so all four are folded away. A
    distinguishing word is never dropped: two makers that differ by a real word
    must still fold to two different keys.
    """
    if not isinstance(name, str):
        raise ValueError("manufacturer name must be a string, got %r" % (name,))
    cleaned = []
    for character in name.lower():
        if character.isalnum():
            cleaned.append(character)
        else:
            cleaned.append(" ")
    tokens = "".join(cleaned).split()
    while tokens and tokens[-1] in LEGAL_SUFFIX_TOKENS:
        tokens.pop()
    if not tokens:
        raise ValueError("manufacturer name has no distinguishing word: %r" % (name,))
    return "-".join(tokens)


def approved_source_match(offered_name, approved_sources, aliases=None, policy=None):
    """Decide whether an offered maker name reaches an approved source."""
    resolved = validate_contact_sourcing_policy(policy)
    if not isinstance(approved_sources, (list, tuple)):
        raise ValueError(
            "approved_sources must be a list or tuple, got %r" % (approved_sources,)
        )
    if not approved_sources:
        raise ValueError("approved_sources must name at least one source")
    folded = fold_manufacturer_name(offered_name)
    approved_keys = {}
    for source in approved_sources:
        approved_keys[fold_manufacturer_name(source)] = source
    if folded in approved_keys:
        return {
            "matched": True,
            "folded_name": folded,
            "approved_source": approved_keys[folded],
            "matched_through_alias": False,
        }
    if aliases and resolved["accept_recorded_aliases"]:
        if not isinstance(aliases, dict):
            raise ValueError("aliases must be a mapping, got %r" % (aliases,))
        for alias, target in aliases.items():
            if fold_manufacturer_name(alias) != folded:
                continue
            target_key = fold_manufacturer_name(target)
            if target_key in approved_keys:
                return {
                    "matched": True,
                    "folded_name": folded,
                    "approved_source": approved_keys[target_key],
                    "matched_through_alias": True,
                }
    return {
        "matched": False,
        "folded_name": folded,
        "approved_source": None,
        "matched_through_alias": False,
    }


def validate_contact_sourcing_policy(policy=None):
    """Return a complete sourcing policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CONTACT_SOURCING_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("contact sourcing policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CONTACT_SOURCING_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CONTACT_SOURCING_POLICY:
            raise ValueError("unknown contact sourcing policy key %r" % (key,))
        merged[key] = value
    utilisation = _require_positive(
        "max_current_utilisation", merged["max_current_utilisation"]
    )
    if utilisation > 1.0:
        raise ValueError(
            "max_current_utilisation must not exceed 1.0, got %r" % (utilisation,)
        )
    derating = _require_positive(
        "contact_current_derating_factor", merged["contact_current_derating_factor"]
    )
    if derating > 1.0:
        raise ValueError(
            "contact_current_derating_factor must not exceed 1.0, got %r" % (derating,)
        )
    for flag in ("require_intermix_qualification", "accept_recorded_aliases"):
        if not isinstance(merged[flag], bool):
            raise ValueError("%s must be a boolean" % flag)
    return merged


def _require_size(contact_size):
    if contact_size not in CONTACT_SIZES:
        raise ValueError(
            "contact_size must be one of %s, got %r"
            % (", ".join(sorted(CONTACT_SIZES)), contact_size)
        )
    return CONTACT_SIZES[contact_size]


def conductor_fit(contact_size, conductor_mm2):
    """Whether a conductor cross-section sits inside the size's crimp range."""
    size = _require_size(contact_size)
    area = _require_positive("conductor_mm2", conductor_mm2)
    below = not _at_least(area, size["min_mm2"])
    above = not _at_most(area, size["max_mm2"])
    return {
        "fits": not (below or above),
        "below_range": below,
        "above_range": above,
        "min_mm2": size["min_mm2"],
        "max_mm2": size["max_mm2"],
    }


def bundle_derating_factor(energised_contacts):
    """Per-contact current factor set by how many contacts carry current."""
    if isinstance(energised_contacts, bool) or not isinstance(
        energised_contacts, int
    ):
        raise ValueError(
            "energised_contacts must be an integer, got %r" % (energised_contacts,)
        )
    if energised_contacts < 1:
        raise ValueError(
            "energised_contacts must be at least one, got %r" % (energised_contacts,)
        )
    for bound, factor in BUNDLE_DERATING_BANDS:
        if energised_contacts <= bound:
            return factor
    return BUNDLE_DERATING_BANDS[-1][1]


def derated_current_allowance_a(contact_size, energised_contacts, policy=None):
    """Current one contact of this size may carry in this populated shell."""
    size = _require_size(contact_size)
    resolved = validate_contact_sourcing_policy(policy)
    factor = bundle_derating_factor(energised_contacts)
    return (
        size["rated_current_a"] * resolved["contact_current_derating_factor"] * factor
    )


def current_utilisation(applied_current_a, allowance_a):
    """Applied current as a share of the derated allowance."""
    applied = _require_non_negative("applied_current_a", applied_current_a)
    allowance = _require_positive("allowance_a", allowance_a)
    return applied / allowance


def traceability_gaps(records):
    """Traceability records the delivery does not carry."""
    if not isinstance(records, (list, tuple, set, frozenset)):
        raise ValueError("records must be a list, tuple or set, got %r" % (records,))
    held = set()
    for record in records:
        if not isinstance(record, str):
            raise ValueError("every traceability record must be a string")
        held.add(record.strip().lower())
    return tuple(
        record for record in REQUIRED_TRACEABILITY_RECORDS if record not in held
    )


def intermix_evidence_required(
    contact_manufacturer, shell_manufacturer, policy=None
):
    """Whether contact and shell from different makers owe pair evidence."""
    resolved = validate_contact_sourcing_policy(policy)
    if not resolved["require_intermix_qualification"]:
        return False
    return fold_manufacturer_name(contact_manufacturer) != fold_manufacturer_name(
        shell_manufacturer
    )


def validate_contact_case(case):
    """Check a sourcing case names every field the decision needs."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    for field in (
        "contact_manufacturer",
        "shell_manufacturer",
        "contact_size",
        "conductor_mm2",
        "energised_contacts",
        "applied_current_a",
        "approved_sources",
        "traceability_records",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    _require_size(case["contact_size"])
    return case


def assess_class2_contact_sourcing(case, policy=None):
    """Full clause 5.6.6 class 2 contact sourcing decision with a disposition."""
    validate_contact_case(case)
    resolved = validate_contact_sourcing_policy(policy)
    findings = []

    match = approved_source_match(
        case["contact_manufacturer"],
        case["approved_sources"],
        case.get("manufacturer_aliases"),
        resolved,
    )
    if not match["matched"]:
        findings.append(
            "the contact maker %s is not an approved source" % match["folded_name"]
        )

    gaps = traceability_gaps(case["traceability_records"])
    if gaps:
        findings.append(
            "the delivery carries no %s" % ", no ".join(gaps)
        )

    intermix = intermix_evidence_required(
        case["contact_manufacturer"], case["shell_manufacturer"], resolved
    )
    intermix_held = bool(case.get("intermateability_evidence"))
    if intermix and not intermix_held:
        findings.append(
            "contact and shell come from different sources with no pair evidence"
        )

    fit = conductor_fit(case["contact_size"], case["conductor_mm2"])
    if not fit["fits"]:
        edge = "below" if fit["below_range"] else "above"
        findings.append(
            "the %.2f mm2 conductor sits %s the crimp range of size %s"
            % (case["conductor_mm2"], edge, case["contact_size"])
        )

    allowance = derated_current_allowance_a(
        case["contact_size"], case["energised_contacts"], resolved
    )
    utilisation = current_utilisation(case["applied_current_a"], allowance)
    current_ok = _at_most(utilisation, resolved["max_current_utilisation"])
    if not current_ok:
        findings.append(
            "the contact draws %.3f of its %.3f A derated allowance"
            % (utilisation, allowance)
        )

    evidence_outstanding = list(gaps)
    if intermix and not intermix_held:
        evidence_outstanding.append("contact-shell-intermateability-qualification")

    if not match["matched"]:
        disposition = CONTACT_SOURCE_NOT_APPROVED
    elif not fit["fits"] or not current_ok:
        disposition = CONTACT_APPLICATION_NONCONFORMING
    elif evidence_outstanding:
        disposition = CONTACT_TRACEABILITY_OUTSTANDING
    else:
        disposition = CONTACT_ADMISSIBLE

    return {
        "disposition": disposition,
        "admissible": disposition == CONTACT_ADMISSIBLE,
        "source_matched": match["matched"],
        "matched_through_alias": match["matched_through_alias"],
        "folded_manufacturer": match["folded_name"],
        "approved_source": match["approved_source"],
        "traceability_gaps": gaps,
        "intermix_evidence_required": intermix,
        "conductor_fits": fit["fits"],
        "bundle_derating_factor": bundle_derating_factor(case["energised_contacts"]),
        "derated_allowance_a": allowance,
        "current_utilisation": utilisation,
        "current_ok": current_ok,
        "evidence_outstanding": tuple(evidence_outstanding),
        "findings": findings,
    }
