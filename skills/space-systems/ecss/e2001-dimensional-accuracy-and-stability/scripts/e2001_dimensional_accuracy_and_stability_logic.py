#!/usr/bin/env python3
"""Worst case gap dimension from manufacturing accuracy and in-service stability.

Anchor: ECSS-E-ST-20-01C clause 5.3.3.2. The procedure below is a paraphrased,
implementable restatement -- no verbatim standard text. Offline, deterministic,
Python standard library only.

The multipactor-critical dimension of a radio-frequency gap is not its drawing
nominal: it is the band the gap actually occupies in orbit once manufacturing
accuracy and in-service dimensional stability are both stacked onto the
nominal. This module derives that band, converts it into a frequency-gap-product
interval, and decides whether the interval reaches the susceptibility band.
"""

import math

__all__ = [
    "categorize_mechanism",
    "validate_contribution",
    "combine_contributions",
    "derive_worst_case_gap",
    "excursion_within_allowance",
    "frequency_gap_product_interval",
    "interval_reaches_band",
    "contributions_missing_evidence",
    "assess_gap_dimension",
    "assess_gap_set",
]

# Absolute floor below which a derived dimension is representation noise, and
# the relative tolerance that absorbs the float error of a tolerance stack-up
# that is exactly on its allowance. Neither widens an engineering limit: they
# only stop a sum of decimal terms from reading a few ULPs over its own bound.
DIM_ABS_TOL_MM = 1e-12
STACK_REL_TOL = 1e-9

MANUFACTURING_MECHANISMS = (
    "machining-tolerance",
    "assembly-tolerance",
    "plating-thickness-variation",
    "braze-gap-variation",
    "dimensional-measurement-uncertainty",
)

STABILITY_MECHANISMS = (
    "thermo-elastic-expansion",
    "launch-induced-permanent-set",
    "material-creep",
    "moisture-release-shrinkage",
    "radiation-induced-swelling",
    "joint-settling",
)

DISTRIBUTIONS = ("systematic", "random")
EVIDENCE_KINDS = ("measured", "analysis", "specification")
STACK_METHODS = ("arithmetic", "statistical")


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def categorize_mechanism(mechanism):
    """Return the family a dimensional mechanism belongs to.

    Clause 5.3.3.2 stacks two distinct families onto the nominal: the accuracy
    the part is built to, and the movement it undergoes once in service. A
    mechanism that belongs to neither family is not a gap contributor and is
    rejected rather than silently dropped.
    """
    if not isinstance(mechanism, str) or not mechanism.strip():
        raise ValueError("mechanism must be a non-empty string")
    key = mechanism.strip().lower()
    if key in MANUFACTURING_MECHANISMS:
        return "manufacturing-accuracy"
    if key in STABILITY_MECHANISMS:
        return "in-service-stability"
    raise ValueError("unrecognized dimensional mechanism: %r" % (mechanism,))


def validate_contribution(contribution):
    """Normalize one dimensional contribution, raising on an unusable entry.

    A contribution carries a closing excursion (minus_mm, shrinking the gap)
    and an opening excursion (plus_mm, widening it); both are magnitudes, so
    both are non-negative, and a contribution that moves the gap in neither
    direction is a bookkeeping artefact, not a tolerance.
    """
    if not isinstance(contribution, dict):
        raise ValueError("contribution must be a mapping, got %r" % type(contribution))
    family = categorize_mechanism(contribution.get("mechanism"))
    minus_mm = _finite_number(contribution.get("minus_mm", 0.0), "minus_mm")
    plus_mm = _finite_number(contribution.get("plus_mm", 0.0), "plus_mm")
    if minus_mm < 0.0 or plus_mm < 0.0:
        raise ValueError("excursions are magnitudes and cannot be negative")
    if minus_mm == 0.0 and plus_mm == 0.0:
        raise ValueError(
            "contribution %r moves the gap in neither direction"
            % (contribution.get("mechanism"),)
        )
    distribution = contribution.get("distribution", "systematic")
    if distribution not in DISTRIBUTIONS:
        raise ValueError(
            "distribution must be one of %s, got %r" % (DISTRIBUTIONS, distribution)
        )
    evidence = contribution.get("evidence")
    if evidence is not None and evidence not in EVIDENCE_KINDS:
        raise ValueError(
            "evidence must be one of %s or absent, got %r" % (EVIDENCE_KINDS, evidence)
        )
    return {
        "mechanism": contribution["mechanism"].strip().lower(),
        "family": family,
        "minus_mm": minus_mm,
        "plus_mm": plus_mm,
        "distribution": distribution,
        "evidence": evidence,
    }


def combine_contributions(contributions, method="arithmetic"):
    """Stack the contributions into a single closing and opening excursion.

    arithmetic  -- every term summed linearly; the true worst case, and the
                   only defensible stack when the terms are few or correlated.
    statistical -- systematic terms still summed linearly (a bias does not
                   cancel), independent random terms combined root-sum-square.
    """
    if method not in STACK_METHODS:
        raise ValueError("method must be one of %s, got %r" % (STACK_METHODS, method))
    if not isinstance(contributions, (list, tuple)) or not contributions:
        raise ValueError("at least one dimensional contribution is required")
    entries = [validate_contribution(item) for item in contributions]
    systematic_minus = 0.0
    systematic_plus = 0.0
    random_minus_sq = 0.0
    random_plus_sq = 0.0
    for entry in entries:
        if method == "arithmetic" or entry["distribution"] == "systematic":
            systematic_minus += entry["minus_mm"]
            systematic_plus += entry["plus_mm"]
        else:
            random_minus_sq += entry["minus_mm"] ** 2
            random_plus_sq += entry["plus_mm"] ** 2
    random_minus = math.sqrt(random_minus_sq)
    random_plus = math.sqrt(random_plus_sq)
    return {
        "method": method,
        "entries": entries,
        "systematic_minus_mm": systematic_minus,
        "systematic_plus_mm": systematic_plus,
        "random_minus_mm": random_minus,
        "random_plus_mm": random_plus,
        "minus_mm": systematic_minus + random_minus,
        "plus_mm": systematic_plus + random_plus,
    }


def derive_worst_case_gap(nominal_mm, contributions, method="arithmetic"):
    """Bound the gap between its smallest and largest in-service value.

    The smallest value drives the multipactor assessment for a gap sitting
    above the susceptibility band and the largest drives it for a gap sitting
    below, so both bounds are carried forward rather than one.
    """
    nominal = _finite_number(nominal_mm, "nominal_mm")
    if nominal <= 0.0:
        raise ValueError("nominal gap must be strictly positive, got %r" % (nominal_mm,))
    stack = combine_contributions(contributions, method=method)
    minimum = nominal - stack["minus_mm"]
    maximum = nominal + stack["plus_mm"]
    if minimum <= DIM_ABS_TOL_MM:
        raise ValueError(
            "stack-up closes the gap (minimum %.6g mm); the electrodes touch and "
            "the dimension is not a multipactor gap" % (minimum,)
        )
    families = {"manufacturing-accuracy": 0, "in-service-stability": 0}
    for entry in stack["entries"]:
        families[entry["family"]] += 1
    return {
        "nominal_mm": nominal,
        "method": stack["method"],
        "minus_mm": stack["minus_mm"],
        "plus_mm": stack["plus_mm"],
        "minimum_mm": minimum,
        "maximum_mm": maximum,
        "excursion_mm": maximum - minimum,
        "families": families,
        "entries": stack["entries"],
    }


def excursion_within_allowance(worst_case, allowance_mm):
    """True when the derived band fits the allowance held for the gap.

    math.isclose absorbs the representation error of a decimal stack-up that
    lands exactly on its allowance; the allowance itself is never widened.
    """
    allowance = _finite_number(allowance_mm, "allowance_mm")
    if allowance < 0.0:
        raise ValueError("allowance cannot be negative, got %r" % (allowance_mm,))
    excursion = _finite_number(worst_case["excursion_mm"], "excursion_mm")
    if excursion <= allowance:
        return True
    return math.isclose(excursion, allowance, rel_tol=STACK_REL_TOL,
                        abs_tol=DIM_ABS_TOL_MM)


def frequency_gap_product_interval(worst_case, frequency_ghz):
    """Map the gap band onto the frequency-gap-product axis, in GHz*mm."""
    frequency = _finite_number(frequency_ghz, "frequency_ghz")
    if frequency <= 0.0:
        raise ValueError("frequency must be strictly positive, got %r" % (frequency_ghz,))
    low = _finite_number(worst_case["minimum_mm"], "minimum_mm") * frequency
    high = _finite_number(worst_case["maximum_mm"], "maximum_mm") * frequency
    if high < low:
        raise ValueError("maximum gap is smaller than the minimum gap")
    return (low, high)


def interval_reaches_band(interval, band):
    """True when the derived interval reaches the susceptibility band.

    A touch counts as a reach: an interval whose edge coincides with the band
    edge is inside the susceptible region for assessment purposes, which is
    also the direction that keeps float error on the conservative side.
    """
    low, high = interval
    band_low, band_high = band
    for label, value in (("interval low", low), ("interval high", high),
                         ("band low", band_low), ("band high", band_high)):
        _finite_number(value, label)
    if high < low:
        raise ValueError("interval is inverted")
    if band_high < band_low:
        raise ValueError("susceptibility band is inverted")
    if low > band_high and not math.isclose(low, band_high, rel_tol=STACK_REL_TOL):
        return False
    if high < band_low and not math.isclose(high, band_low, rel_tol=STACK_REL_TOL):
        return False
    return True


def contributions_missing_evidence(worst_case):
    """Mechanisms carried in the stack with no evidence kind on record."""
    return sorted(
        entry["mechanism"] for entry in worst_case["entries"] if entry["evidence"] is None
    )


def assess_gap_dimension(gap):
    """Derive and grade the worst case dimension of one multipactor gap."""
    if not isinstance(gap, dict):
        raise ValueError("gap must be a mapping, got %r" % type(gap))
    name = gap.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("gap requires a non-empty name")
    worst_case = derive_worst_case_gap(
        gap.get("nominal_mm"),
        gap.get("contributions"),
        method=gap.get("method", "arithmetic"),
    )
    interval = frequency_gap_product_interval(worst_case, gap.get("frequency_ghz"))
    findings = []
    if worst_case["families"]["manufacturing-accuracy"] == 0:
        findings.append("manufacturing-accuracy-family-absent")
    if worst_case["families"]["in-service-stability"] == 0:
        findings.append("in-service-stability-family-absent")
    missing = contributions_missing_evidence(worst_case)
    if missing:
        findings.append("evidence-missing:" + ",".join(missing))
    allowance = gap.get("stability_allowance_mm")
    if allowance is not None and not excursion_within_allowance(worst_case, allowance):
        findings.append("stability-allowance-exceeded")
    band = gap.get("susceptibility_band")
    if band is None:
        reaches = True
        findings.append("susceptibility-band-absent")
    else:
        reaches = interval_reaches_band(interval, band)
    verdict = "multipactor-critical" if reaches else "outside-susceptibility-band"
    return {
        "name": name.strip(),
        "worst_case": worst_case,
        "frequency_gap_product_ghz_mm": interval,
        "verdict": verdict,
        "findings": sorted(findings),
        "dimension_accepted": not findings,
    }


def assess_gap_set(gaps):
    """Grade a set of gaps; the set is accepted only when every gap is."""
    if not isinstance(gaps, (list, tuple)) or not gaps:
        raise ValueError("at least one gap is required")
    results = [assess_gap_dimension(gap) for gap in gaps]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("gap names must be unique within a set")
    critical = [item["name"] for item in results if item["verdict"] == "multipactor-critical"]
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "gaps": results,
        "critical_gaps": critical,
        "open_findings": open_findings,
        "set_accepted": not open_findings,
    }
