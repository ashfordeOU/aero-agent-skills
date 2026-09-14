"""Derating limits on stress applied to Class 3 commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 6.2.2.5 (the derating limits placed on the
electrical and thermal stress a commercial EEE part is worked at when it is
selected at the lowest assurance class). Paraphrased into an implementable
procedure; no standard text is reproduced.

Offline, deterministic, python3 standard library only.

Procedure implemented here
--------------------------
* A commercial part is rated by its maker for a commercial life in a
  commercial environment. The rating is never used directly: a derating
  factor is applied to every electrical stress and a step down to the
  temperature ceiling, so the part spends its life inside the envelope the
  datasheet draws.
* Electrical stress is kept as a ratio of applied to rated. Thermal stress is
  kept as an absolute ceiling, expressed as a step down from the rated
  maximum junction temperature.
* Each part family carries its own row, because the mechanism the derating
  protects against differs -- dielectric wear-out on a ceramic capacitor,
  electromigration on a die interconnect, contact erosion on a relay. One
  blanket factor across a board is an average of unrelated mechanisms.
* The table at this class is the loosest of the three: more of the maker's
  rating is left available, because the class carries the lowest assurance
  target.
* Two things are bought back for that. First, an applied value that came from
  a nominal analysis instead of a worst-case one is uplifted before it is
  graded, because at this class a worst-case circuit analysis is often not
  run and the uplift stands in for the spread it would have found. Second,
  the bounded relaxation band the middle class opens is available here too:
  one electrical stress may be carried past its limit by no more than a fixed
  fraction where a relaxation record has been raised and approved for that
  stress on that part.
* The thermal ceiling takes no relaxation and no uplift relief at any class.
  The step down is the whole of the margin against a wear-out mechanism.
* A junction temperature that was never predicted directly can still be had
  from the measured case temperature, the junction-to-case thermal resistance
  and the dissipation. A result with no junction figure at all is half a
  result and is reported as not demonstrated rather than quietly passed.
"""

from __future__ import annotations

import math

# Derating rows at the lowest assurance class: the largest fraction of each
# maker rating the build may work the part at, plus the step down applied to
# the rated maximum junction temperature, in kelvin.
CLASS_3_DERATING_TABLE = {
    "ceramic-capacitor": {
        "voltage": 0.70,
        "current": 0.80,
        "power": 0.75,
        "junction_step_down_k": 10.0,
    },
    "film-capacitor": {
        "voltage": 0.75,
        "current": 0.80,
        "power": 0.75,
        "junction_step_down_k": 10.0,
    },
    "fixed-resistor": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.70,
        "junction_step_down_k": 15.0,
    },
    "signal-diode": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.75,
        "junction_step_down_k": 15.0,
    },
    "bipolar-transistor": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.75,
        "junction_step_down_k": 15.0,
    },
    "digital-integrated-circuit": {
        "voltage": 0.85,
        "current": 0.85,
        "power": 0.80,
        "junction_step_down_k": 10.0,
    },
    "linear-integrated-circuit": {
        "voltage": 0.80,
        "current": 0.80,
        "power": 0.75,
        "junction_step_down_k": 10.0,
    },
    "electromechanical-relay": {
        "voltage": 0.75,
        "current": 0.60,
        "power": 0.70,
        "junction_step_down_k": 15.0,
    },
}

STRESS_KINDS = ("voltage", "current", "power")

# How far past its derated limit one electrical stress may be carried where a
# relaxation record names that stress on that part, as a fraction of the
# allowable value.
RELAXATION_BAND = 0.10

# Where the applied value came from a nominal analysis rather than a
# worst-case one, it is uplifted by this factor before grading.
NOMINAL_ONLY_UPLIFT = 1.10

ANALYSIS_BASES = ("worst-case-analysis", "nominal-analysis-only")

STRESS_DISPOSITIONS = (
    "stress-within-limit",
    "stress-on-limit",
    "stress-inside-approved-relaxation",
    "stress-breach",
)

JUNCTION_DISPOSITIONS = (
    "junction-within-ceiling",
    "junction-on-ceiling",
    "junction-over-ceiling",
    "junction-not-demonstrated",
)

VERDICTS = (
    "derating-compliant",
    "derating-compliant-on-approved-relaxation",
    "derating-open-junction-not-demonstrated",
    "derating-breach",
)

# Every allowable value is a product of decimal figures and every ratio is a
# quotient, so a stress built to sit exactly on its limit or on the band edge
# can land a few units in the last place above it. Absorb that representation
# error here; the limit itself stays untouched.
RATIO_TOLERANCE = 1e-9


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a finite, strictly positive float."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return number


def _non_negative(value, label):
    """Return ``value`` as a finite, non-negative float."""
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def derating_limits(family):
    """Derating row of one part family; an uncategorized family is rejected."""
    if family not in CLASS_3_DERATING_TABLE:
        raise ValueError(
            "unknown part family %r (known: %s)"
            % (family, ", ".join(sorted(CLASS_3_DERATING_TABLE)))
        )
    return dict(CLASS_3_DERATING_TABLE[family])


def derating_ratio(family, kind):
    """Derating factor one family owes on one kind of electrical stress."""
    if kind not in STRESS_KINDS:
        raise ValueError(
            "unknown stress kind %r (known: %s)" % (kind, ", ".join(STRESS_KINDS))
        )
    return derating_limits(family)[kind]


def allowable_applied(rating, ratio):
    """Largest applied value the derating rule leaves against a maker rating."""
    rated = _positive(rating, "rating")
    factor = _real(ratio, "ratio")
    if factor <= 0.0 or factor > 1.0:
        raise ValueError("ratio must sit in (0, 1], got %r" % (ratio,))
    return rated * factor


def effective_applied(applied, analysis_basis):
    """Applied value carried into grading, uplifted where only nominal."""
    value = _non_negative(applied, "applied")
    if analysis_basis not in ANALYSIS_BASES:
        raise ValueError(
            "unknown analysis basis %r (known: %s)"
            % (analysis_basis, ", ".join(ANALYSIS_BASES))
        )
    if analysis_basis == "nominal-analysis-only":
        return value * NOMINAL_ONLY_UPLIFT
    return value


def stress_ratio(applied, rating):
    """Ratio of an applied stress to the maker rating it works against."""
    return _non_negative(applied, "applied") / _positive(rating, "rating")


def grade_stress(
    family,
    kind,
    applied,
    rating,
    analysis_basis="worst-case-analysis",
    relaxation_approved=False,
):
    """Grade one applied electrical stress against its derated allowable."""
    if not isinstance(relaxation_approved, bool):
        raise ValueError(
            "relaxation_approved must be a boolean, got %r" % (relaxation_approved,)
        )
    ratio = derating_ratio(family, kind)
    rated = _positive(rating, "rating")
    allowable = allowable_applied(rated, ratio)
    effective = effective_applied(applied, analysis_basis)
    band_top = allowable * (1.0 + RELAXATION_BAND)
    if effective <= allowable * (1.0 - RATIO_TOLERANCE):
        disposition = "stress-within-limit"
    elif effective <= allowable * (1.0 + RATIO_TOLERANCE):
        disposition = "stress-on-limit"
    elif relaxation_approved and effective <= band_top * (1.0 + RATIO_TOLERANCE):
        disposition = "stress-inside-approved-relaxation"
    else:
        disposition = "stress-breach"
    return {
        "kind": kind,
        "family": family,
        "rating": rated,
        "derating_ratio": ratio,
        "allowable_applied": allowable,
        "declared_applied": _non_negative(applied, "applied"),
        "effective_applied": effective,
        "analysis_basis": analysis_basis,
        "applied_over_rated": effective / rated,
        "headroom_fraction": (allowable - effective) / allowable,
        "relaxation_approved": relaxation_approved,
        "disposition": disposition,
    }


def junction_temperature_c(case_temperature_c, thermal_resistance_k_per_w, dissipation_w):
    """Junction temperature derived from a measured case temperature."""
    case = _real(case_temperature_c, "case_temperature_c")
    resistance = _non_negative(thermal_resistance_k_per_w, "thermal_resistance_k_per_w")
    power = _non_negative(dissipation_w, "dissipation_w")
    return case + resistance * power


def derated_junction_ceiling_c(rated_junction_max_c, step_down_k):
    """Junction ceiling the build may work the part up to."""
    rated = _real(rated_junction_max_c, "rated_junction_max_c")
    step = _non_negative(step_down_k, "step_down_k")
    return rated - step


def resolve_junction_temperature(part):
    """Junction temperature of a part declaration, derived if not predicted."""
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    predicted = part.get("junction_temperature_c")
    if predicted is not None:
        return _real(predicted, "junction_temperature_c")
    case = part.get("case_temperature_c")
    resistance = part.get("thermal_resistance_k_per_w")
    power = part.get("dissipation_w")
    if case is None or resistance is None or power is None:
        return None
    return junction_temperature_c(case, resistance, power)


def grade_junction(junction_temperature, rated_junction_max_c, step_down_k):
    """Grade a junction temperature against the derated ceiling."""
    ceiling = derated_junction_ceiling_c(rated_junction_max_c, step_down_k)
    if junction_temperature is None:
        return {
            "junction_temperature_c": None,
            "ceiling_c": ceiling,
            "headroom_k": None,
            "disposition": "junction-not-demonstrated",
        }
    value = _real(junction_temperature, "junction_temperature")
    headroom = ceiling - value
    if headroom > RATIO_TOLERANCE:
        disposition = "junction-within-ceiling"
    elif headroom >= -RATIO_TOLERANCE:
        disposition = "junction-on-ceiling"
    else:
        disposition = "junction-over-ceiling"
    return {
        "junction_temperature_c": value,
        "ceiling_c": ceiling,
        "headroom_k": headroom,
        "disposition": disposition,
    }


def tightest_electrical_margin(graded):
    """Graded stress sitting closest to its limit; ties broken by stress kind."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("graded must be a non-empty sequence of stress records")
    tightest = None
    for record in graded:
        if not isinstance(record, dict) or "headroom_fraction" not in record:
            raise ValueError("each record must be a mapping carrying 'headroom_fraction'")
        if tightest is None:
            tightest = record
            continue
        here = record["headroom_fraction"]
        best = tightest["headroom_fraction"]
        if math.isclose(here, best, rel_tol=1e-12, abs_tol=1e-15):
            if record["kind"] < tightest["kind"]:
                tightest = record
        elif here < best:
            tightest = record
    return tightest


def assess_derating(part_id, part):
    """Run the clause 6.2.2.5 derating assessment for one commercial part.

    part keys: family, stresses (mapping of stress kind to a mapping carrying
    applied, rating, optional analysis_basis and relaxation_approved),
    rated_junction_max_c, and either junction_temperature_c or the
    case_temperature_c, thermal_resistance_k_per_w and dissipation_w that
    derive one.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        raise ValueError("part_id must be a non-empty string, got %r" % (part_id,))
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (type(part).__name__,))
    family = part.get("family")
    limits = derating_limits(family)
    stresses = part.get("stresses")
    if not isinstance(stresses, dict) or not stresses:
        raise ValueError("part must declare a non-empty 'stresses' mapping")

    graded = []
    findings = []
    for kind in STRESS_KINDS:
        if kind not in stresses:
            continue
        entry = stresses[kind]
        if not isinstance(entry, dict):
            raise ValueError("stress %r must be a mapping, got %r" % (kind, entry))
        for key in ("applied", "rating"):
            if key not in entry:
                raise ValueError("stress %r missing required key %r" % (kind, key))
        record = grade_stress(
            family,
            kind,
            entry["applied"],
            entry["rating"],
            entry.get("analysis_basis", "worst-case-analysis"),
            entry.get("relaxation_approved", False),
        )
        graded.append(record)
        if record["analysis_basis"] == "nominal-analysis-only":
            findings.append("%s-stress-uplifted-from-nominal-analysis" % kind)
        if record["disposition"] == "stress-breach":
            findings.append("%s-stress-past-its-derated-limit" % kind)
        elif record["disposition"] == "stress-inside-approved-relaxation":
            findings.append("%s-stress-carried-on-approved-relaxation" % kind)

    unknown = sorted(set(stresses) - set(STRESS_KINDS))
    if unknown:
        raise ValueError(
            "unknown stress kinds %s (known: %s)"
            % (", ".join(unknown), ", ".join(STRESS_KINDS))
        )
    if not graded:
        raise ValueError("no gradeable stress declared for part %s" % (part_id,))

    if "rated_junction_max_c" not in part:
        raise ValueError("part missing required key 'rated_junction_max_c'")
    junction = grade_junction(
        resolve_junction_temperature(part),
        part["rated_junction_max_c"],
        limits["junction_step_down_k"],
    )
    if junction["disposition"] == "junction-not-demonstrated":
        findings.append("junction-temperature-neither-predicted-nor-derivable")
    elif junction["disposition"] == "junction-over-ceiling":
        findings.append("junction-temperature-past-its-derated-ceiling")

    dispositions = [record["disposition"] for record in graded]
    if "stress-breach" in dispositions or junction["disposition"] == "junction-over-ceiling":
        verdict = "derating-breach"
    elif junction["disposition"] == "junction-not-demonstrated":
        verdict = "derating-open-junction-not-demonstrated"
    elif "stress-inside-approved-relaxation" in dispositions:
        verdict = "derating-compliant-on-approved-relaxation"
    else:
        verdict = "derating-compliant"

    return {
        "part_id": part_id,
        "family": family,
        "limits": limits,
        "stresses": graded,
        "junction": junction,
        "tightest_margin": tightest_electrical_margin(graded),
        "findings": findings,
        "verdict": verdict,
    }
