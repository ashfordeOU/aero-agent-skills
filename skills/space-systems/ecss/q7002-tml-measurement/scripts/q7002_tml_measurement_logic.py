"""Total mass loss of specimens taken through an outgassing screening run.

Anchor: ECSS-Q-ST-70-02C, measurement clause -- the mass a specimen lost over
the vacuum exposure, expressed as a percentage of the mass it went in with,
and the part of that loss which was only water coming back out of the
laboratory air. Paraphrased into an implementable procedure; no standard text
is reproduced.

What this module computes and decides
-------------------------------------
1. Total mass loss. The difference between the initial and final specimen
   masses, referred to the initial mass. It is a ratio, so the same absolute
   loss on a light and a heavy coupon are different results.
2. Water vapour regained. The mass a specimen takes back on after the run,
   referred to the same initial mass, so it can be subtracted from the total
   on equal terms.
3. Recovered mass loss. Total loss less the regained water -- the part that
   did not come back, and therefore the part that describes the material
   rather than the laboratory.
4. Resolution. A loss smaller than the balance can see is not a small loss; it
   is a result the run cannot report, and saying so is the honest outcome.
5. The replicate set. Each coupon is graded against the limits, the set mean
   and spread are reported, and a spread beyond the scatter allowance is a
   finding about the run rather than about any single coupon.
"""

import math

__all__ = [
    "DEFAULT_TML_LIMIT_PCT",
    "DEFAULT_RML_LIMIT_PCT",
    "DEFAULT_SCATTER_ALLOWANCE_PCT",
    "validate_mass",
    "total_mass_loss_percent",
    "water_vapour_regained_percent",
    "recovered_mass_loss_percent",
    "resolution_floor_percent",
    "within_limit",
    "specimen_record",
    "set_statistics",
    "assess_tml_measurement",
]

# Screening limits, in percent of the initial specimen mass.
DEFAULT_TML_LIMIT_PCT = 1.00
DEFAULT_RML_LIMIT_PCT = 1.00

# Largest accepted spread of total mass loss across the replicate set, in
# percentage points.
DEFAULT_SCATTER_ALLOWANCE_PCT = 0.10

# Limit comparisons are inclusive; absorb representation error at the edge
# rather than relaxing the screening limit itself.
LIMIT_TOLERANCE = 1e-9


def validate_mass(value, label):
    """Return a specimen mass as a strictly positive finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def total_mass_loss_percent(initial_mg, final_mg):
    """Return the total mass loss as a percentage of the initial mass."""
    initial = validate_mass(initial_mg, "initial_mg")
    final = validate_mass(final_mg, "final_mg")
    if final > initial:
        raise ValueError(
            "final mass %g mg exceeds the initial %g mg; a specimen heavier after the "
            "exposure is a weighing or handling error, not a negative loss"
            % (final, initial)
        )
    return (initial - final) / initial * 100.0


def water_vapour_regained_percent(initial_mg, final_mg, recovered_mg):
    """Return the mass taken back on after the run, on the initial-mass basis."""
    initial = validate_mass(initial_mg, "initial_mg")
    final = validate_mass(final_mg, "final_mg")
    recovered = validate_mass(recovered_mg, "recovered_mg")
    if final > initial:
        raise ValueError(
            "final mass %g mg exceeds the initial %g mg" % (final, initial)
        )
    if recovered < final:
        raise ValueError(
            "recovered mass %g mg is below the final mass %g mg; reconditioning "
            "cannot remove mass" % (recovered, final)
        )
    if recovered > initial:
        raise ValueError(
            "recovered mass %g mg exceeds the initial %g mg; the specimen cannot "
            "regain more than it started with" % (recovered, initial)
        )
    return (recovered - final) / initial * 100.0


def recovered_mass_loss_percent(total_pct, regained_pct):
    """Return the loss that did not come back, in percent of the initial mass."""
    for label, value in (("total_pct", total_pct), ("regained_pct", regained_pct)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite, got %r" % (label, value))
        if float(value) < 0.0:
            raise ValueError("%s must not be negative, got %r" % (label, value))
    total = float(total_pct)
    regained = float(regained_pct)
    if regained > total + LIMIT_TOLERANCE:
        raise ValueError(
            "regained %g %% exceeds the total loss %g %%; the specimen cannot take "
            "back more than it lost" % (regained, total)
        )
    return total - regained


def resolution_floor_percent(readability_mg, initial_mg):
    """Return the smallest loss the balance can distinguish, as a percentage."""
    readability = validate_mass(readability_mg, "readability_mg")
    initial = validate_mass(initial_mg, "initial_mg")
    return readability / initial * 100.0


def within_limit(value_pct, limit_pct):
    """Return True when a percentage result satisfies its screening limit."""
    if not isinstance(value_pct, (int, float)) or isinstance(value_pct, bool):
        raise ValueError("value_pct must be a real number, got %r" % (value_pct,))
    if not math.isfinite(float(value_pct)):
        raise ValueError("value_pct must be finite")
    limit = validate_mass(limit_pct, "limit_pct")
    return float(value_pct) <= limit + LIMIT_TOLERANCE


def specimen_record(specimen, options=None):
    """Return the graded result of one coupon.

    specimen keys: id, initial_mg, final_mg; optional recovered_mg and
    readability_mg.
    """
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    settings = dict(options or {})
    for key in ("id", "initial_mg", "final_mg"):
        if key not in specimen:
            raise ValueError("specimen is missing '%s'" % key)
    identifier = specimen["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("specimen id must be a non-blank string")
    total = total_mass_loss_percent(specimen["initial_mg"], specimen["final_mg"])
    tml_limit = settings.get("tml_limit_pct", DEFAULT_TML_LIMIT_PCT)
    rml_limit = settings.get("rml_limit_pct", DEFAULT_RML_LIMIT_PCT)
    findings = []
    regained = None
    recovered = None
    if "recovered_mg" in specimen and specimen["recovered_mg"] is not None:
        regained = water_vapour_regained_percent(
            specimen["initial_mg"], specimen["final_mg"], specimen["recovered_mg"]
        )
        recovered = recovered_mass_loss_percent(total, regained)
    floor = None
    if "readability_mg" in specimen and specimen["readability_mg"] is not None:
        floor = resolution_floor_percent(
            specimen["readability_mg"], specimen["initial_mg"]
        )
        if total < floor - LIMIT_TOLERANCE:
            findings.append(
                "specimen '%s' lost %.4f %%, below the %.4f %% the balance can "
                "distinguish" % (identifier.strip(), total, floor)
            )
    if not within_limit(total, tml_limit):
        findings.append(
            "specimen '%s' total mass loss %.4f %% exceeds the %.4f %% limit"
            % (identifier.strip(), total, tml_limit)
        )
    if recovered is not None and not within_limit(recovered, rml_limit):
        findings.append(
            "specimen '%s' recovered mass loss %.4f %% exceeds the %.4f %% limit"
            % (identifier.strip(), recovered, rml_limit)
        )
    return {
        "id": identifier.strip(),
        "total_mass_loss_pct": total,
        "water_vapour_regained_pct": regained,
        "recovered_mass_loss_pct": recovered,
        "resolution_floor_pct": floor,
        "findings": findings,
        "compliant": not findings,
    }


def set_statistics(values):
    """Return the mean and spread of a replicate set of percentage results."""
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    numbers = []
    for i, value in enumerate(values):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("value %d must be a real number, got %r" % (i, value))
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("value %d must be finite" % i)
        numbers.append(number)
    return {
        "count": len(numbers),
        "mean": sum(numbers) / len(numbers),
        "spread": max(numbers) - min(numbers),
        "minimum": min(numbers),
        "maximum": max(numbers),
    }


def assess_tml_measurement(spec):
    """Run the full total-mass-loss measurement assessment for one material.

    spec keys: specimens (sequence of coupon records); optional options
    mapping carrying tml_limit_pct, rml_limit_pct and scatter_allowance_pct.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "specimens" not in spec:
        raise ValueError("spec missing required key 'specimens'")
    specimens = spec["specimens"]
    if not isinstance(specimens, (list, tuple)) or not specimens:
        raise ValueError("spec['specimens'] must be a non-empty sequence")
    options = dict(spec.get("options") or {})
    records = [specimen_record(item, options) for item in specimens]
    seen = set()
    for record in records:
        if record["id"] in seen:
            raise ValueError("specimen identifier '%s' is used twice" % record["id"])
        seen.add(record["id"])
    totals = set_statistics([record["total_mass_loss_pct"] for record in records])
    findings = []
    for record in records:
        findings.extend(record["findings"])
    allowance = validate_mass(
        options.get("scatter_allowance_pct", DEFAULT_SCATTER_ALLOWANCE_PCT),
        "scatter_allowance_pct",
    )
    if len(records) > 1 and totals["spread"] > allowance + LIMIT_TOLERANCE:
        findings.append(
            "replicate total mass loss spans %.4f percentage points, beyond the "
            "%.4f allowed; the set does not agree with itself"
            % (totals["spread"], allowance)
        )
    recovered_values = [
        record["recovered_mass_loss_pct"]
        for record in records
        if record["recovered_mass_loss_pct"] is not None
    ]
    recovered_stats = set_statistics(recovered_values) if recovered_values else None
    return {
        "records": records,
        "total_mass_loss": totals,
        "recovered_mass_loss": recovered_stats,
        "findings": findings,
        "screened_pass": not findings,
    }
