#!/usr/bin/env python3
"""Sourcing removable contacts for Class 3 connectors from approved makers.

Anchor: ECSS-Q-ST-60C clause 6.6.6 (removable contacts fitted into Class 3
connectors are taken from approved manufacturers only). Paraphrased into an
implementable procedure; no standard text is reproduced.

A removable contact is the one piece of a connector bought separately, fitted
by hand and invisible once the backshell is on. It also carries the current and
forms the only metal-to-metal interface in the mated pair. Class 3 widens who
may be an approved source -- a project may add one itself -- but it does not
remove the list. A source the project added without writing down why, and
without a qualification reference behind it, is not an approved source.

Procedure implemented here
--------------------------
1. Fold the offered manufacturer name and every candidate source onto a
   comparable key, and decide by which route, if any, the offered name reaches
   an approved source: the list itself, a recorded alias, or a project-approved
   addition that carries both a justification and a qualification reference.
2. Name the traceability records the delivery does not carry.
3. Decide whether contact and shell come from different makers and so owe
   intermateability evidence.
4. Grade the plating pair: a near-pure tin finish is refused outright, and a
   dissimilar noble-to-solderable pair is a design finding.
5. Test the conductor cross-section against the crimp range the contact size
   accommodates, and the applied current against the Class 3 allowance derated
   for the size and the number of energised contacts.
6. Return one disposition in precedence order, with every finding.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "LEGAL_SUFFIX_TOKENS",
    "CONTACT_SIZES",
    "BUNDLE_DERATING_BANDS",
    "REQUIRED_TRACEABILITY_RECORDS",
    "PLATING_FINISHES",
    "PROJECT_ADDITION_RECORDS",
    "DEFAULT_CLASS3_CONTACT_POLICY",
    "CONTACT_ADMISSIBLE",
    "CONTACT_EVIDENCE_OUTSTANDING",
    "CONTACT_APPLICATION_NONCONFORMING",
    "CONTACT_SOURCE_NOT_APPROVED",
    "fold_manufacturer_name",
    "validate_class3_contact_policy",
    "approved_source_route",
    "traceability_gaps",
    "plating_pair_assessment",
    "crimp_range_fit",
    "bundle_derating_factor",
    "derated_current_allowance_a",
    "current_utilisation",
    "intermix_evidence_required",
    "validate_contact_case",
    "assess_class3_contact_sourcing",
]

# Tokens that change a company's legal wrapper without changing the company.
# The fold removes them and removes nothing else: a fold that is too loose maps
# two different makers onto one key and admits a source nobody approved.
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

# Contact size -> conductor cross-section the crimp barrel accommodates, in
# square millimetres, and the rated current of the size before any derating.
CONTACT_SIZES = {
    "22d": {"min_mm2": 0.20, "max_mm2": 0.38, "rated_current_a": 5.0},
    "20": {"min_mm2": 0.38, "max_mm2": 0.62, "rated_current_a": 7.5},
    "16": {"min_mm2": 0.62, "max_mm2": 1.65, "rated_current_a": 13.0},
    "12": {"min_mm2": 1.65, "max_mm2": 3.31, "rated_current_a": 23.0},
    "8": {"min_mm2": 3.31, "max_mm2": 8.37, "rated_current_a": 46.0},
}

# A contact in a crowded insert cannot shed its own heat. Ascending energised
# contact counts; the first band the count falls at or below names the factor.
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

# Contact plating finishes. "noble" finishes mate with each other; a
# solderable finish mated to a noble one wears through and frets. A near-pure
# tin finish grows whiskers and is refused whatever it is mated to.
PLATING_FINISHES = {
    "gold-over-nickel": {"family": "noble", "restricted": False},
    "palladium-nickel": {"family": "noble", "restricted": False},
    "silver": {"family": "solderable", "restricted": False},
    "tin-lead": {"family": "solderable", "restricted": False},
    "pure-tin": {"family": "solderable", "restricted": True},
}

# What a project must have written down before a source it added itself counts
# as approved. Class 3 lets the project add the source; it does not let the
# project add it silently.
PROJECT_ADDITION_RECORDS = ("justification", "qualification-reference")

DEFAULT_CLASS3_CONTACT_POLICY = {
    # Share of the derated allowance the application may draw.
    "max_current_utilisation": 1.0,
    # Class 3 derating applied to the rated current of the contact size.
    "contact_current_derating_factor": 0.6,
    # Whether a contact and shell from different makers owe pair evidence.
    "require_intermix_qualification": True,
    # Whether an alias recorded against an approved source counts as a match.
    "accept_recorded_aliases": True,
    # Whether a project-approved addition to the list counts as a match.
    "accept_project_additions": True,
    # Whether a dissimilar plating pair is a design finding.
    "require_matched_plating_family": True,
}

CONTACT_ADMISSIBLE = "q60-c3-contact-admissible"
CONTACT_EVIDENCE_OUTSTANDING = "q60-c3-contact-evidence-outstanding"
CONTACT_APPLICATION_NONCONFORMING = "q60-c3-contact-application-nonconforming"
CONTACT_SOURCE_NOT_APPROVED = "q60-c3-contact-source-not-approved"

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
    """Fold a manufacturer name onto the key the source list is matched on.

    Case, punctuation, separator runs and a trailing legal wrapper all change
    the string without changing the company, so all four are folded away. A
    distinguishing word is never dropped: two makers that differ by a real word
    must still fold to two different keys.
    """
    if not isinstance(name, str):
        raise ValueError("manufacturer name must be a string, got %r" % (name,))
    cleaned = []
    for character in name.lower():
        cleaned.append(character if character.isalnum() else " ")
    tokens = "".join(cleaned).split()
    while tokens and tokens[-1] in LEGAL_SUFFIX_TOKENS:
        tokens.pop()
    if not tokens:
        raise ValueError("manufacturer name has no distinguishing word: %r" % (name,))
    return "-".join(tokens)


def validate_class3_contact_policy(policy=None):
    """Return a complete Class 3 contact policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_CLASS3_CONTACT_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("contact policy must be a mapping, got %r" % (policy,))
    merged = dict(DEFAULT_CLASS3_CONTACT_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS3_CONTACT_POLICY:
            raise ValueError("unknown contact policy key %r" % (key,))
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
    for flag in (
        "require_intermix_qualification",
        "accept_recorded_aliases",
        "accept_project_additions",
        "require_matched_plating_family",
    ):
        if not isinstance(merged[flag], bool):
            raise ValueError("%s must be a boolean" % flag)
    return merged


def _project_addition_gaps(entry):
    """Records a project-added source entry does not carry."""
    if not isinstance(entry, dict):
        raise ValueError("project addition entry must be a mapping, got %r" % (entry,))
    missing = []
    for record in PROJECT_ADDITION_RECORDS:
        value = entry.get(record)
        if not isinstance(value, str) or not value.strip():
            missing.append(record)
    return tuple(missing)


def approved_source_route(
    offered_name,
    approved_sources,
    aliases=None,
    project_additions=None,
    policy=None,
):
    """Decide by which route, if any, an offered maker reaches an approved source.

    Routes, in the order they are tried: the approved source list itself, a
    recorded alias onto a listed source, and a project-approved addition that
    carries both a justification and a qualification reference. A project
    addition missing either record does not reach an approved source, and the
    missing records are reported so the finding names what to go and write.
    """
    resolved = validate_class3_contact_policy(policy)
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
            "route": "approved-source-list",
            "folded_name": folded,
            "approved_source": approved_keys[folded],
            "addition_record_gaps": (),
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
                    "route": "recorded-alias",
                    "folded_name": folded,
                    "approved_source": approved_keys[target_key],
                    "addition_record_gaps": (),
                }
    if project_additions and resolved["accept_project_additions"]:
        if not isinstance(project_additions, dict):
            raise ValueError(
                "project_additions must be a mapping, got %r" % (project_additions,)
            )
        for added, entry in project_additions.items():
            if fold_manufacturer_name(added) != folded:
                continue
            gaps = _project_addition_gaps(entry)
            if gaps:
                return {
                    "matched": False,
                    "route": "project-addition-incomplete",
                    "folded_name": folded,
                    "approved_source": None,
                    "addition_record_gaps": gaps,
                }
            return {
                "matched": True,
                "route": "project-approved-addition",
                "folded_name": folded,
                "approved_source": added,
                "addition_record_gaps": (),
            }
    return {
        "matched": False,
        "route": "no-route",
        "folded_name": folded,
        "approved_source": None,
        "addition_record_gaps": (),
    }


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


def _require_finish(label, finish):
    if finish not in PLATING_FINISHES:
        raise ValueError(
            "%s must be one of %s, got %r"
            % (label, ", ".join(sorted(PLATING_FINISHES)), finish)
        )
    return PLATING_FINISHES[finish]


def plating_pair_assessment(contact_plating, mating_plating, policy=None):
    """Grade the plating of a contact against the plating it mates with."""
    resolved = validate_class3_contact_policy(policy)
    contact = _require_finish("contact_plating", contact_plating)
    mating = _require_finish("mating_plating", mating_plating)
    restricted = []
    if contact["restricted"]:
        restricted.append(contact_plating)
    if mating["restricted"] and mating_plating not in restricted:
        restricted.append(mating_plating)
    dissimilar = contact["family"] != mating["family"]
    acceptable = not restricted and not (
        dissimilar and resolved["require_matched_plating_family"]
    )
    return {
        "acceptable": acceptable,
        "restricted_finishes": tuple(restricted),
        "dissimilar_family": dissimilar,
        "contact_family": contact["family"],
        "mating_family": mating["family"],
    }


def _require_size(contact_size):
    if contact_size not in CONTACT_SIZES:
        raise ValueError(
            "contact_size must be one of %s, got %r"
            % (", ".join(sorted(CONTACT_SIZES)), contact_size)
        )
    return CONTACT_SIZES[contact_size]


def crimp_range_fit(contact_size, conductor_mm2):
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
    if isinstance(energised_contacts, bool) or not isinstance(energised_contacts, int):
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
    resolved = validate_class3_contact_policy(policy)
    factor = bundle_derating_factor(energised_contacts)
    return size["rated_current_a"] * resolved["contact_current_derating_factor"] * factor


def current_utilisation(applied_current_a, allowance_a):
    """Applied current as a share of the derated allowance."""
    applied = _require_non_negative("applied_current_a", applied_current_a)
    allowance = _require_positive("allowance_a", allowance_a)
    return applied / allowance


def intermix_evidence_required(contact_manufacturer, shell_manufacturer, policy=None):
    """Whether contact and shell from different makers owe pair evidence."""
    resolved = validate_class3_contact_policy(policy)
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
        "contact_plating",
        "mating_plating",
        "approved_sources",
        "traceability_records",
    ):
        if case.get(field) is None:
            raise ValueError("case is missing %s" % field)
    _require_size(case["contact_size"])
    _require_finish("contact_plating", case["contact_plating"])
    _require_finish("mating_plating", case["mating_plating"])
    return case


def assess_class3_contact_sourcing(case, policy=None):
    """Full clause 6.6.6 Class 3 contact sourcing decision with a disposition."""
    validate_contact_case(case)
    resolved = validate_class3_contact_policy(policy)
    findings = []

    route = approved_source_route(
        case["contact_manufacturer"],
        case["approved_sources"],
        case.get("manufacturer_aliases"),
        case.get("project_additions"),
        resolved,
    )
    if not route["matched"]:
        if route["addition_record_gaps"]:
            findings.append(
                "the project addition %s carries no %s"
                % (route["folded_name"], ", no ".join(route["addition_record_gaps"]))
            )
        else:
            findings.append(
                "the contact maker %s is not an approved source" % route["folded_name"]
            )

    gaps = traceability_gaps(case["traceability_records"])
    if gaps:
        findings.append("the delivery carries no %s" % ", no ".join(gaps))

    intermix = intermix_evidence_required(
        case["contact_manufacturer"], case["shell_manufacturer"], resolved
    )
    intermix_held = bool(case.get("intermateability_evidence"))
    if intermix and not intermix_held:
        findings.append(
            "contact and shell come from different makers with no pair evidence"
        )

    plating = plating_pair_assessment(
        case["contact_plating"], case["mating_plating"], resolved
    )
    if plating["restricted_finishes"]:
        findings.append(
            "the %s finish is restricted for flight use"
            % " and ".join(plating["restricted_finishes"])
        )
    elif not plating["acceptable"]:
        findings.append(
            "a %s contact mated to a %s interface is a dissimilar plating pair"
            % (plating["contact_family"], plating["mating_family"])
        )

    fit = crimp_range_fit(case["contact_size"], case["conductor_mm2"])
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

    application_ok = fit["fits"] and current_ok and plating["acceptable"]

    if not route["matched"]:
        disposition = CONTACT_SOURCE_NOT_APPROVED
    elif not application_ok:
        disposition = CONTACT_APPLICATION_NONCONFORMING
    elif evidence_outstanding:
        disposition = CONTACT_EVIDENCE_OUTSTANDING
    else:
        disposition = CONTACT_ADMISSIBLE

    return {
        "disposition": disposition,
        "admissible": disposition == CONTACT_ADMISSIBLE,
        "source_matched": route["matched"],
        "source_route": route["route"],
        "folded_manufacturer": route["folded_name"],
        "approved_source": route["approved_source"],
        "addition_record_gaps": route["addition_record_gaps"],
        "traceability_gaps": gaps,
        "intermix_evidence_required": intermix,
        "plating_acceptable": plating["acceptable"],
        "restricted_finishes": plating["restricted_finishes"],
        "dissimilar_plating_family": plating["dissimilar_family"],
        "conductor_fits": fit["fits"],
        "bundle_derating_factor": bundle_derating_factor(case["energised_contacts"]),
        "derated_allowance_a": allowance,
        "current_utilisation": utilisation,
        "current_ok": current_ok,
        "evidence_outstanding": tuple(evidence_outstanding),
        "findings": findings,
    }
