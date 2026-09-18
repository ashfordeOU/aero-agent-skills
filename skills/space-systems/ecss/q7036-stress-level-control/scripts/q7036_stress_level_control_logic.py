"""Sustained stress level control against a stress-corrosion threshold.

Anchor: ECSS-Q-ST-70-36C, the selection clauses that hold the sustained
tensile stress in a part below the level at which stress-corrosion cracking
initiates. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Sum every sustained tensile contribution acting on the part at once --
   sustained applied load, assembly fit-up, fastener preload, press fit,
   retained forming residual and a sustained thermal term -- rather than the
   applied load alone.
2. Apply the elastic stress-concentration factor of the feature to the terms
   that see it, and leave the terms that are already local stresses alone.
3. Subtract a beneficial compressive residual, such as a shot-peened surface
   layer, but never below zero: a surface treatment can cancel a tensile
   stress, not reverse the load path.
4. Compare the total with the allowable: a measured threshold stress when one
   exists, otherwise the fraction of yield strength the resistance rating of
   the alloy state permits. Report the margin and, when short, the reductions
   that would close it.
"""

import math

__all__ = [
    "STRESS_TOLERANCE",
    "SUSTAINED_TERMS",
    "LOCAL_TERMS",
    "THRESHOLD_FRACTIONS",
    "normalize_category",
    "validate_stress",
    "concentration_factor",
    "sustained_total_mpa",
    "allowable_stress_mpa",
    "margin_ratio",
    "reduction_options",
    "assess_stress_level",
]

# Total and allowable are both sums and products of floats. A case an engineer
# builds to sit exactly on the allowable must not fail on the last bit.
STRESS_TOLERANCE = 1e-9

# Sustained tensile contributions, in megapascals. Every one of them is held
# for the duration the cracking mechanism needs, which is what puts them in
# the same sum as the applied load.
SUSTAINED_TERMS = (
    "applied_sustained_mpa",
    "assembly_fitup_mpa",
    "preload_mpa",
    "press_fit_mpa",
    "forming_residual_mpa",
    "thermal_sustained_mpa",
)

# The terms already expressed as a local stress at the feature. The elastic
# concentration factor is not applied a second time to these.
LOCAL_TERMS = ("forming_residual_mpa", "press_fit_mpa")

# Fraction of yield strength allowed as sustained tensile stress when no
# measured threshold exists, by the SCC resistance rating of the state.
THRESHOLD_FRACTIONS = {"high": 0.75, "medium": 0.50, "low": 0.25}

_CATEGORY_ALIASES = {
    "high-resistance": "high",
    "resistant": "high",
    "moderate": "medium",
    "medium-resistance": "medium",
    "intermediate": "medium",
    "low-resistance": "low",
    "susceptible": "low",
}


def normalize_category(value):
    """Return the canonical SCC resistance rating token."""
    if not isinstance(value, str):
        raise ValueError("resistance category must be a string")
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("resistance category must not be blank")
    token = _CATEGORY_ALIASES.get(token, token)
    if token not in THRESHOLD_FRACTIONS:
        raise ValueError(
            "resistance category %r is not one of %s"
            % (value, ", ".join(sorted(THRESHOLD_FRACTIONS)))
        )
    return token


def validate_stress(value, label, allow_zero=True):
    """Return a finite, non-negative stress in megapascals."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError(
            "%s must not be negative; a compressive term belongs in "
            "compressive_residual_mpa, got %r" % (label, value)
        )
    if number == 0.0 and not allow_zero:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def concentration_factor(value):
    """Return the elastic stress-concentration factor, at least unity."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("stress_concentration must be a real number")
    factor = float(value)
    if not math.isfinite(factor):
        raise ValueError("stress_concentration must be finite")
    if factor < 1.0:
        raise ValueError(
            "stress_concentration %g is below unity; a feature cannot reduce the "
            "local elastic stress below the nominal" % factor
        )
    return factor


def sustained_total_mpa(terms, stress_concentration=1.0, compressive_residual_mpa=0.0):
    """Return the total sustained tensile stress at the feature.

    Nominal terms are raised by the concentration factor; terms that are
    already local stresses are not. A beneficial compressive residual is
    subtracted last and the total is floored at zero.
    """
    if not isinstance(terms, dict):
        raise ValueError("terms must be a mapping of named stress contributions")
    unknown = sorted(set(terms) - set(SUSTAINED_TERMS))
    if unknown:
        raise ValueError(
            "unknown sustained term(s) %s; expected any of %s"
            % (", ".join(unknown), ", ".join(SUSTAINED_TERMS))
        )
    factor = concentration_factor(stress_concentration)
    relief = validate_stress(compressive_residual_mpa, "compressive_residual_mpa")
    total = 0.0
    for name in SUSTAINED_TERMS:
        if name not in terms:
            continue
        value = validate_stress(terms[name], name)
        total += value if name in LOCAL_TERMS else value * factor
    net = total - relief
    return net if net > 0.0 else 0.0


def allowable_stress_mpa(resistance_category, yield_strength_mpa, measured_threshold_mpa=None):
    """Return the allowable sustained tensile stress.

    A measured threshold for the state supersedes the rating-based fraction of
    yield; it is the direct evidence the fraction stands in for.
    """
    strength = validate_stress(yield_strength_mpa, "yield_strength_mpa", allow_zero=False)
    category = normalize_category(resistance_category)
    if measured_threshold_mpa is not None:
        threshold = validate_stress(
            measured_threshold_mpa, "measured_threshold_mpa", allow_zero=False
        )
        if threshold > strength:
            raise ValueError(
                "measured_threshold_mpa %g exceeds the yield strength %g; a "
                "threshold above yield is not a sustained-stress allowable"
                % (threshold, strength)
            )
        return threshold
    return THRESHOLD_FRACTIONS[category] * strength


def margin_ratio(total_mpa, allowable_mpa):
    """Return allowable/total - 1, the fractional headroom on the allowable."""
    allowable = validate_stress(allowable_mpa, "allowable_mpa", allow_zero=False)
    total = validate_stress(total_mpa, "total_mpa")
    if total == 0.0:
        return float("inf")
    return allowable / total - 1.0


def reduction_options(record):
    """Return the stress reductions available, largest lever first."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    options = []
    contributions = record.get("contributions", {})
    ordered = sorted(contributions.items(), key=lambda item: -item[1])
    labels = {
        "preload_mpa": "reduce the fastener preload or add a preload-limiting feature",
        "assembly_fitup_mpa": "shim or ream the joint so the fit-up stress is not locked in",
        "press_fit_mpa": "relax the interference or split the fit into a clamped joint",
        "forming_residual_mpa": "stress-relieve after forming, or form closer to final shape",
        "applied_sustained_mpa": "increase the section, or re-route the sustained load path",
        "thermal_sustained_mpa": "free a constrained expansion path at the interface",
    }
    for name, value in ordered:
        if value <= 0.0:
            continue
        if name in labels:
            options.append("%s (%.1f MPa)" % (labels[name], value))
    if record.get("stress_concentration", 1.0) > 1.0:
        options.append("open the notch radius to lower the elastic concentration factor")
    options.append("introduce a compressive surface residual by shot peening the feature")
    return options


def assess_stress_level(spec):
    """Grade the sustained stress in a part against its SCC allowable.

    spec keys: id, resistance_category, yield_strength_mpa, terms, optional
    stress_concentration, compressive_residual_mpa, measured_threshold_mpa.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("id", "resistance_category", "yield_strength_mpa", "terms"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    if not isinstance(spec["id"], str) or not spec["id"].strip():
        raise ValueError("spec['id'] must be a non-blank string")
    factor = concentration_factor(spec.get("stress_concentration", 1.0))
    relief = validate_stress(
        spec.get("compressive_residual_mpa", 0.0), "compressive_residual_mpa"
    )
    total = sustained_total_mpa(spec["terms"], factor, relief)
    allowable = allowable_stress_mpa(
        spec["resistance_category"],
        spec["yield_strength_mpa"],
        spec.get("measured_threshold_mpa"),
    )
    compliant = total < allowable or math.isclose(
        total, allowable, rel_tol=0.0, abs_tol=STRESS_TOLERANCE
    )
    contributions = {}
    for name in SUSTAINED_TERMS:
        if name in spec["terms"]:
            value = validate_stress(spec["terms"][name], name)
            contributions[name] = value if name in LOCAL_TERMS else value * factor
    record = {
        "id": spec["id"].strip(),
        "resistance_category": normalize_category(spec["resistance_category"]),
        "stress_concentration": factor,
        "compressive_residual_mpa": relief,
        "contributions": contributions,
        "total_sustained_mpa": total,
        "allowable_mpa": allowable,
        "allowable_source": (
            "measured-threshold" if spec.get("measured_threshold_mpa") is not None
            else "rating-fraction-of-yield"
        ),
        "margin_ratio": margin_ratio(total, allowable),
        "compliant": compliant,
    }
    findings = []
    if not compliant:
        findings.append(
            "sustained tensile stress %.1f MPa on %s exceeds the allowable %.1f MPa "
            "(%s)" % (total, record["id"], allowable, record["allowable_source"])
        )
        record["reductions"] = reduction_options(record)
    else:
        record["reductions"] = []
    if relief > 0.0 and total == 0.0:
        findings.append(
            "the compressive residual cancels the whole sustained tensile stress on "
            "%s; confirm the treated layer covers the loaded feature" % record["id"]
        )
    record["findings"] = findings
    return record
