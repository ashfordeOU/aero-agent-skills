#!/usr/bin/env python3
"""Allowable defect levels for a photovoltaic assembly.

Anchor: ECSS-E-ST-20-08C clause 5.4.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An assembly is never defect-free, so an allowable defect level is agreed
per defect type before hardware is presented. A level only counts as
established when three things line up: the level is written down, the
writing down is an agreement rather than a supplier preference, and
qualification actually carried hardware at or above that level.

Agreement basis, strongest to weakest
    customer-agreed      the level sits in an agreed record, cited by id
    supplier-proposed    the level is documented but not yet agreed
    undocumented         the level exists only as practice

Qualification basis, strongest to weakest
    qualification-demonstrated  a qualification article carried the level
    analysis-supported          the level is argued, not demonstrated
    none                        no confirmation of any kind

An agreed fraction becomes an allowable count only against a declared
population, and the observed population of a defect type is then judged
against that count. The two questions stay separate: whether the
criterion is established, and whether this article meets it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

AGREEMENT_BASES = ("customer-agreed", "supplier-proposed", "undocumented")
QUALIFICATION_BASES = ("qualification-demonstrated", "analysis-supported", "none")

ACCEPTABILITY_ESTABLISHED = "acceptability-established"
ACCEPTABILITY_PROVISIONAL = "acceptability-provisional"
ACCEPTABILITY_NOT_ESTABLISHED = "acceptability-not-established"

VERDICT_RANK = {
    ACCEPTABILITY_NOT_ESTABLISHED: 0,
    ACCEPTABILITY_PROVISIONAL: 1,
    ACCEPTABILITY_ESTABLISHED: 2,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_fraction(name, value):
    """A defect fraction: finite, greater than zero, at most one."""
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    if value > 1.0 and not math.isclose(value, 1.0, rel_tol=_REL_TOL):
        raise ValueError("%s must not exceed one, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_population(name, value):
    count = _require_count(name, value)
    if count == 0:
        raise ValueError("%s must be greater than zero" % name)
    return count


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_label(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A coverage ratio is a quotient of two declared fractions, so a
    qualification article that carried exactly the agreed level can land
    a few units in the last place below one. The agreed level is never
    lowered; only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _tolerant_floor(value):
    """Floor of a product that should have landed on a whole number.

    population * fraction is a float product, so a pairing that is
    exactly three defects can evaluate a hair above or below three.
    Snap to the nearest integer first when the product is within
    representation error of it, then floor.
    """
    nearest = round(value)
    if math.isclose(value, nearest, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return int(nearest)
    return int(math.floor(value))


def allowable_defect_count(population, allowable_fraction):
    """Whole defects an agreed fraction permits over a declared population."""
    size = _require_population("population", population)
    fraction = _require_fraction("allowable_fraction", allowable_fraction)
    return _tolerant_floor(size * fraction)


def defect_utilisation(observed_count, allowed_count):
    """Share of the allowance this article has already consumed."""
    observed = _require_count("observed_count", observed_count)
    allowed = _require_count("allowed_count", allowed_count)
    if allowed == 0:
        return 0.0 if observed == 0 else math.inf
    return observed / allowed


def qualification_coverage_ratio(demonstrated_fraction, agreed_fraction):
    """How far the qualified defect level reaches past the agreed level."""
    demonstrated = _require_fraction("demonstrated_fraction", demonstrated_fraction)
    agreed = _require_fraction("agreed_fraction", agreed_fraction)
    return demonstrated / agreed


def assess_agreement(agreement_basis, agreement_record=None):
    """Categorize how firmly the allowable level is written down."""
    basis = _require_choice("agreement_basis", agreement_basis, AGREEMENT_BASES)
    findings = []
    if basis == "customer-agreed":
        record = _require_label("agreement_record", agreement_record)
        return {"basis": basis, "record": record, "agreed": True, "findings": findings}
    if basis == "supplier-proposed":
        record = agreement_record
        if record is not None:
            record = _require_label("agreement_record", record)
        findings.append(
            "the allowable level is proposed but not agreed; it cannot be "
            "presented as an acceptance criterion until the customer signs it"
        )
        return {"basis": basis, "record": record, "agreed": False, "findings": findings}
    if agreement_record is not None:
        raise ValueError(
            "an undocumented basis cannot cite an agreement record; either "
            "declare the record or keep the basis undocumented"
        )
    findings.append(
        "no written allowable level exists for this defect type; the level in "
        "use is shop practice and has no acceptance standing"
    )
    return {"basis": basis, "record": None, "agreed": False, "findings": findings}


def assess_defect_rule(rule, population):
    """Judge one defect type: is the level established, does the article meet it."""
    if not isinstance(rule, dict):
        raise ValueError("rule must be a mapping, got %r" % (rule,))
    defect_type = _require_label("defect_type", rule.get("defect_type"))
    agreed_fraction = _require_fraction(
        "allowable_fraction", rule.get("allowable_fraction")
    )
    observed_count = _require_count("observed_count", rule.get("observed_count"))
    qualification_basis = _require_choice(
        "qualification_basis", rule.get("qualification_basis"), QUALIFICATION_BASES
    )
    agreement = assess_agreement(
        rule.get("agreement_basis"), rule.get("agreement_record")
    )
    findings = list(agreement["findings"])

    allowed_count = allowable_defect_count(population, agreed_fraction)
    utilisation = defect_utilisation(observed_count, allowed_count)
    within_allowance = observed_count <= allowed_count

    coverage = None
    qualification_confirms = False
    if qualification_basis == "qualification-demonstrated":
        coverage = qualification_coverage_ratio(
            rule.get("demonstrated_fraction"), agreed_fraction
        )
        qualification_confirms = _at_least(coverage, 1.0)
        if not qualification_confirms:
            findings.append(
                "qualification carried %.4f against an agreed %.4f for %s; the "
                "agreed level reaches past what was demonstrated"
                % (coverage * agreed_fraction, agreed_fraction, defect_type)
            )
    elif qualification_basis == "analysis-supported":
        findings.append(
            "the allowable level for %s rests on analysis; a qualification "
            "article carrying the level is still outstanding" % defect_type
        )
    else:
        findings.append(
            "nothing confirms the allowable level for %s; neither a "
            "qualification article nor an analysis is on record" % defect_type
        )

    if not agreement["agreed"] and agreement["basis"] == "undocumented":
        verdict = ACCEPTABILITY_NOT_ESTABLISHED
    elif qualification_basis == "none":
        verdict = ACCEPTABILITY_NOT_ESTABLISHED
    elif not agreement["agreed"] or qualification_basis == "analysis-supported":
        verdict = ACCEPTABILITY_PROVISIONAL
    elif not qualification_confirms:
        verdict = ACCEPTABILITY_PROVISIONAL
    else:
        verdict = ACCEPTABILITY_ESTABLISHED

    if not within_allowance:
        findings.append(
            "%d %s defects against an allowance of %d over a population of %d"
            % (observed_count, defect_type, allowed_count, population)
        )

    return {
        "defect_type": defect_type,
        "agreement_basis": agreement["basis"],
        "agreement_record": agreement["record"],
        "qualification_basis": qualification_basis,
        "allowable_fraction": agreed_fraction,
        "allowed_count": allowed_count,
        "observed_count": observed_count,
        "utilisation": utilisation,
        "within_allowance": within_allowance,
        "qualification_coverage": coverage,
        "qualification_confirms": qualification_confirms,
        "verdict": verdict,
        "findings": findings,
    }


def governing_defect(assessments):
    """The defect type that drags the assembly verdict down."""
    if not assessments:
        raise ValueError("no defect assessments to rank")
    return min(
        assessments,
        key=lambda a: (
            VERDICT_RANK[a["verdict"]],
            -a["utilisation"] if math.isfinite(a["utilisation"]) else -math.inf,
            a["defect_type"],
        ),
    )


def assess_assembly_defect_acceptability(case):
    """Full clause 5.4.2 roll-up over every declared defect type."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    population = _require_population("population", case.get("population"))
    rules = case.get("rules")
    if not isinstance(rules, (list, tuple)) or not rules:
        raise ValueError("case must carry a non-empty rules sequence")
    seen = set()
    assessments = []
    findings = []
    for rule in rules:
        assessment = assess_defect_rule(rule, population)
        if assessment["defect_type"] in seen:
            raise ValueError(
                "defect type %r appears twice; one allowable level per type"
                % assessment["defect_type"]
            )
        seen.add(assessment["defect_type"])
        assessments.append(assessment)
        findings.extend(assessment["findings"])

    worst = min(VERDICT_RANK[a["verdict"]] for a in assessments)
    verdict = next(k for k, v in VERDICT_RANK.items() if v == worst)
    governing = governing_defect(assessments)
    article_conforms = all(a["within_allowance"] for a in assessments)
    established = [
        a["defect_type"]
        for a in assessments
        if a["verdict"] == ACCEPTABILITY_ESTABLISHED
    ]
    return {
        "population": population,
        "assessments": assessments,
        "verdict": verdict,
        "governing_defect_type": governing["defect_type"],
        "article_conforms": article_conforms,
        "established_defect_types": established,
        "established_share": len(established) / len(assessments),
        "findings": findings,
    }
