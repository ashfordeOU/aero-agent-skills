#!/usr/bin/env python3
"""Supplier acceptance criteria for photovoltaic assembly components.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The general criteria a visual inspection judges against are not written
by the standard. The supplier writes them for every component of the
assembly -- solar cell, coverglass, interconnect, adhesive fillet, bus
bar, insulation film -- the customer agrees them, and the agreed set is
documented so that the same coupon gets the same verdict a year later.

That gives two jobs, and they are separable:

    admissibility   does a criteria set exist for every component, is
                    every criterion agreed, and does every agreed
                    criterion carry the document it was agreed in
    adjudication    against that set, what does an observed feature on a
                    real coupon come out as

An unagreed criterion is not a licence to reject. A feature inside a
supplier-only limit is accepted while the agreement is still open, and a
feature outside one is referred to the customer rather than dispositioned
by the supplier alone.

Three criterion kinds cover what a visual inspection can actually
measure: a limit on a single feature, a limit on the cumulative area
those features take up as a fraction of the assembly, and a limit on how
many of them there may be.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ASSEMBLY_COMPONENTS = (
    "solar-cell",
    "coverglass",
    "interconnect",
    "adhesive-fillet",
    "bus-bar",
    "insulation-film",
)

AGREEMENT_STATES = (
    "customer-agreed",
    "submitted-for-agreement",
    "supplier-only",
)

CRITERION_KINDS = (
    "single-feature-limit",
    "cumulative-area-fraction",
    "count-limit",
)

MEASURES = ("length_mm", "width_mm", "major_dimension_mm")

KIND_UNITS = {
    "single-feature-limit": "mm",
    "cumulative-area-fraction": "fraction",
    "count-limit": "count",
}

ACCEPT = "accept"
ACCEPT_PENDING_AGREEMENT = "accept-pending-agreement"
REFER_TO_CUSTOMER = "refer-to-customer"
REJECT = "reject"

DISPOSITION_SEVERITY = {
    ACCEPT: 0,
    ACCEPT_PENDING_AGREEMENT: 1,
    REFER_TO_CUSTOMER: 2,
    REJECT: 3,
}

SET_ADMISSIBLE = "criteria-set-admissible"
SET_NOT_ADMISSIBLE = "criteria-set-not-admissible"

ASSEMBLY_ACCEPTED = "assembly-accepted"
ASSEMBLY_REFERRED = "assembly-referred"
ASSEMBLY_REJECTED = "assembly-rejected"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A cumulative area fraction is a sum of products divided by an area, so
    a coupon that sits exactly on its limit can land a few units in the
    last place above it. The limit is never widened; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def criterion_label(criterion):
    """Stable human-readable name for one criterion, used to break ties."""
    return "%s/%s/%s" % (
        criterion["component"],
        criterion["feature"],
        criterion["kind"],
    )


def validate_criterion(criterion):
    """Check one supplier criterion is complete, consistent and agreed."""
    if not isinstance(criterion, dict):
        raise ValueError("criterion must be a mapping, got %r" % (criterion,))
    component = _require_choice(
        "criterion component", criterion.get("component"), ASSEMBLY_COMPONENTS
    )
    kind = _require_choice("criterion kind", criterion.get("kind"), CRITERION_KINDS)
    feature = _require_text("criterion feature", criterion.get("feature"))
    method = _require_text("criterion method", criterion.get("method"))
    agreement = _require_choice(
        "criterion agreement", criterion.get("agreement"), AGREEMENT_STATES
    )
    unit = _require_text("criterion unit", criterion.get("unit"))
    if unit != KIND_UNITS[kind]:
        raise ValueError(
            "a %s is expressed in %s, got unit %r"
            % (kind, KIND_UNITS[kind], unit)
        )
    limit = _require_positive("criterion limit", criterion.get("limit"))
    if kind == "cumulative-area-fraction" and limit > 1.0:
        raise ValueError(
            "a cumulative area fraction limit cannot exceed unity, got %r" % (limit,)
        )
    if kind == "count-limit" and float(limit) != float(int(limit)):
        raise ValueError("a count limit must be a whole number, got %r" % (limit,))
    measure = criterion.get("measure", "major_dimension_mm")
    if kind == "single-feature-limit":
        measure = _require_choice("criterion measure", measure, MEASURES)
    document_ref = criterion.get("document_ref")
    if agreement == "customer-agreed":
        document_ref = _require_text("criterion document_ref", document_ref)
    elif document_ref is not None:
        document_ref = _require_text("criterion document_ref", document_ref)
    return {
        "component": component,
        "kind": kind,
        "feature": feature,
        "measure": measure,
        "method": method,
        "agreement": agreement,
        "unit": unit,
        "limit": float(limit),
        "document_ref": document_ref,
    }


def validate_criteria_set(criteria, required_components=ASSEMBLY_COMPONENTS):
    """Check the supplier set covers every component and is fully agreed."""
    if not isinstance(criteria, (list, tuple)) or not criteria:
        raise ValueError("criteria must be a non-empty sequence")
    for component in required_components:
        _require_choice("required component", component, ASSEMBLY_COMPONENTS)
    checked = []
    seen = set()
    for criterion in criteria:
        item = validate_criterion(criterion)
        key = criterion_label(item)
        if key in seen:
            raise ValueError("duplicate criterion %s" % key)
        seen.add(key)
        checked.append(item)
    covered = {item["component"] for item in checked}
    missing = sorted(set(required_components) - covered)
    unagreed = sorted(
        criterion_label(item)
        for item in checked
        if item["agreement"] != "customer-agreed"
    )
    undocumented = sorted(
        criterion_label(item) for item in checked if not item["document_ref"]
    )
    findings = []
    if missing:
        findings.append(
            "no supplier criteria written for: %s" % ", ".join(missing)
        )
    if unagreed:
        findings.append(
            "criteria not yet agreed with the customer: %s" % ", ".join(unagreed)
        )
    if undocumented:
        findings.append(
            "criteria carrying no document reference: %s" % ", ".join(undocumented)
        )
    admissible = not missing and not unagreed and not undocumented
    return {
        "criteria": checked,
        "components_covered": sorted(covered),
        "missing_components": missing,
        "unagreed_criteria": unagreed,
        "undocumented_criteria": undocumented,
        "coverage_fraction": len(covered & set(required_components))
        / float(len(required_components)),
        "verdict": SET_ADMISSIBLE if admissible else SET_NOT_ADMISSIBLE,
        "admissible": admissible,
        "findings": findings,
    }


def validate_observation(observation):
    """Check one observed feature carries the geometry a criterion needs."""
    if not isinstance(observation, dict):
        raise ValueError("observation must be a mapping, got %r" % (observation,))
    component = _require_choice(
        "observation component", observation.get("component"), ASSEMBLY_COMPONENTS
    )
    feature = _require_text("observation feature", observation.get("feature"))
    length = _require_positive("observation length_mm", observation.get("length_mm"))
    width = _require_positive("observation width_mm", observation.get("width_mm"))
    return {
        "component": component,
        "feature": feature,
        "length_mm": length,
        "width_mm": width,
        "major_dimension_mm": max(length, width),
        "area_mm2": length * width,
    }


def observed_value(criterion, observations, assembly_area_mm2=None):
    """Reduce the matching observations to the quantity the criterion limits."""
    matching = [
        obs
        for obs in observations
        if obs["component"] == criterion["component"]
        and obs["feature"] == criterion["feature"]
    ]
    if criterion["kind"] == "count-limit":
        return float(len(matching))
    if not matching:
        return 0.0
    if criterion["kind"] == "single-feature-limit":
        return max(obs[criterion["measure"]] for obs in matching)
    area = _require_positive("assembly_area_mm2", assembly_area_mm2)
    return sum(obs["area_mm2"] for obs in matching) / area


def adjudicate_criterion(criterion, value):
    """Disposition one observed quantity against one supplier criterion."""
    limit = _require_positive("criterion limit", criterion.get("limit"))
    observed = _require_non_negative("observed value", value)
    utilisation = observed / limit
    within = _at_most(observed, limit)
    agreed = criterion.get("agreement") == "customer-agreed"
    if within:
        disposition = ACCEPT if agreed else ACCEPT_PENDING_AGREEMENT
    else:
        disposition = REJECT if agreed else REFER_TO_CUSTOMER
    findings = []
    if not within:
        findings.append(
            "%s reads %.4f against a limit of %.4f %s"
            % (criterion_label(criterion), observed, limit, criterion["unit"])
        )
    if not agreed:
        findings.append(
            "%s is dispositioned on a criterion the customer has not agreed"
            % criterion_label(criterion)
        )
    return {
        "criterion": criterion_label(criterion),
        "observed": observed,
        "limit": limit,
        "utilisation": utilisation,
        "within_limit": within,
        "disposition": disposition,
        "findings": findings,
    }


def screen_assembly(criteria, observations, assembly_area_mm2=None,
                    required_components=ASSEMBLY_COMPONENTS):
    """Full clause 5.5.3.2.3 screening of a coupon against the agreed set."""
    review = validate_criteria_set(criteria, required_components)
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations must be a sequence")
    checked = [validate_observation(obs) for obs in observations]
    results = []
    for criterion in review["criteria"]:
        value = observed_value(criterion, checked, assembly_area_mm2)
        results.append(adjudicate_criterion(criterion, value))
    findings = list(review["findings"])
    for result in results:
        findings.extend(result["findings"])
    covered_features = {
        (item["component"], item["feature"]) for item in review["criteria"]
    }
    uncovered = sorted(
        "%s/%s" % (obs["component"], obs["feature"])
        for obs in checked
        if (obs["component"], obs["feature"]) not in covered_features
    )
    if uncovered:
        findings.append(
            "observed features no agreed criterion covers: %s" % ", ".join(uncovered)
        )
    dispositions = [result["disposition"] for result in results]
    if uncovered:
        dispositions.append(REFER_TO_CUSTOMER)
    worst = max(dispositions, key=lambda d: DISPOSITION_SEVERITY[d])
    if worst == REJECT:
        verdict = ASSEMBLY_REJECTED
    elif worst == ACCEPT:
        verdict = ASSEMBLY_ACCEPTED
    else:
        verdict = ASSEMBLY_REFERRED
    governing = sorted(
        results, key=lambda r: (-r["utilisation"], r["criterion"])
    )[0]["criterion"]
    return {
        "criteria_review": review,
        "results": results,
        "uncovered_features": uncovered,
        "worst_disposition": worst,
        "governing_criterion": governing,
        "verdict": verdict,
        "findings": findings,
    }
