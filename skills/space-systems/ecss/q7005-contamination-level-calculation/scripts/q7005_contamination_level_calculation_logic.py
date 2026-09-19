"""Contamination level calculation from measured infrared band signals.

Anchor: ECSS-Q-ST-70-05C, quantification. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the sampling chain: sampled area, dilution factor and recovery.
2. Validate each species record and refuse a reading whose band measure is
   not the measure its calibration was built on.
3. Invert each species signal through its own calibration to a deposit mass,
   then carry the dilution, recovery and sampled area to an areal mass.
4. Bound a species whose signal is at or below its quantification limit: it
   is omitted from the lower-bound total and counted at its limit in the
   upper-bound total.
5. Sum the species into the bounded total and categorize each bound against
   the supplied cleanliness level bands.
"""

import math

__all__ = [
    "BAND_AREA",
    "PEAK_HEIGHT",
    "assess_contamination_level",
    "categorize_level",
    "deposit_mass_ug",
    "net_band_signal",
    "species_areal_mass",
    "total_contamination_level",
    "validate_level_bands",
    "validate_sampling_chain",
    "validate_species",
]

PEAK_HEIGHT = "baseline-corrected-peak-height"
BAND_AREA = "integrated-band-area"
_MEASURES = (PEAK_HEIGHT, BAND_AREA)

_BOUND_TOLERANCE = 1e-12


def _positive(label, value, allow_zero=False):
    """Return value as a finite float, raising on a non-numeric or non-positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _real(label, value):
    """Return value as a finite float of any sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _at_most(value, bound):
    """True when value is below bound or lands on it within tolerance."""
    return value < bound or abs(value - bound) <= _BOUND_TOLERANCE


def validate_sampling_chain(record):
    """Return the normalised sampling chain.

    Keys: sampled_area_cm2, dilution_factor (>= 1), recovery_fraction (0..1].
    """
    if not isinstance(record, dict):
        raise ValueError("sampling chain must be a mapping")
    for key in ("sampled_area_cm2", "dilution_factor", "recovery_fraction"):
        if key not in record:
            raise ValueError("sampling chain missing required key '%s'" % key)
    dilution = _positive("dilution_factor", record["dilution_factor"])
    if dilution < 1.0 and abs(dilution - 1.0) > _BOUND_TOLERANCE:
        raise ValueError(
            "dilution_factor %g is below unity; an aliquot cannot hold more "
            "than the extract it came from" % dilution
        )
    recovery = _positive("recovery_fraction", record["recovery_fraction"])
    if recovery > 1.0 and abs(recovery - 1.0) > _BOUND_TOLERANCE:
        raise ValueError("recovery_fraction must not exceed unity, got %g"
                         % recovery)
    return {
        "sampled_area_cm2": _positive("sampled_area_cm2",
                                      record["sampled_area_cm2"]),
        "dilution_factor": dilution,
        "recovery_fraction": recovery,
    }


def net_band_signal(gross, baseline, blank=0.0):
    """Return the baseline- and blank-corrected band signal."""
    gross_v = _real("gross", gross)
    baseline_v = _real("baseline", baseline)
    blank_v = _positive("blank", blank, allow_zero=True)
    above = gross_v - baseline_v
    if above < 0.0:
        raise ValueError(
            "band signal %g sits below its baseline %g" % (gross_v, baseline_v)
        )
    net = above - blank_v
    return net if net > 0.0 else 0.0


def validate_species(record):
    """Return the normalised species record.

    Keys: name, measure_kind, net_signal, calibration_measure_kind,
    calibration_slope, calibration_intercept, quantification_limit_signal,
    top_standard_signal.
    """
    if not isinstance(record, dict):
        raise ValueError("species record must be a mapping")
    for key in ("name", "measure_kind", "net_signal", "calibration_measure_kind",
                "calibration_slope", "calibration_intercept",
                "quantification_limit_signal", "top_standard_signal"):
        if key not in record:
            raise ValueError("species record missing required key '%s'" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("species name must be a non-empty string")
    for key in ("measure_kind", "calibration_measure_kind"):
        if record[key] not in _MEASURES:
            raise ValueError(
                "%s must be one of %s, got %r"
                % (key, ", ".join(_MEASURES), record[key])
            )
    if record["measure_kind"] != record["calibration_measure_kind"]:
        raise ValueError(
            "species %s was read as %s but its calibration was built on %s; "
            "the two differ by the band shape factor"
            % (name.strip(), record["measure_kind"],
               record["calibration_measure_kind"])
        )
    slope = _positive("calibration_slope", record["calibration_slope"])
    return {
        "name": name.strip(),
        "measure_kind": record["measure_kind"],
        "net_signal": _positive("net_signal", record["net_signal"],
                                allow_zero=True),
        "calibration_slope": slope,
        "calibration_intercept": _real("calibration_intercept",
                                       record["calibration_intercept"]),
        "quantification_limit_signal": _positive(
            "quantification_limit_signal",
            record["quantification_limit_signal"], allow_zero=True
        ),
        "top_standard_signal": _positive("top_standard_signal",
                                         record["top_standard_signal"]),
    }


def deposit_mass_ug(species, signal=None):
    """Return the deposit mass a species signal implies, through its own curve."""
    norm = validate_species(species)
    value = norm["net_signal"] if signal is None else _positive(
        "signal", signal, allow_zero=True
    )
    mass = (value - norm["calibration_intercept"]) / norm["calibration_slope"]
    return mass if mass > 0.0 else 0.0


def species_areal_mass(species, sampling):
    """Return the areal-mass record of one species, bounded when sub-limit."""
    norm = validate_species(species)
    chain = validate_sampling_chain(sampling)
    factor = chain["dilution_factor"] / (
        chain["recovery_fraction"] * chain["sampled_area_cm2"]
    )
    point = deposit_mass_ug(species) * factor
    limit = deposit_mass_ug(species, norm["quantification_limit_signal"]) * factor
    sub_limit = _at_most(norm["net_signal"], norm["quantification_limit_signal"])
    above_top = norm["net_signal"] > norm["top_standard_signal"] and abs(
        norm["net_signal"] - norm["top_standard_signal"]
    ) > _BOUND_TOLERANCE
    return {
        "name": norm["name"],
        "areal_mass_ug_per_cm2": point,
        "quantification_limit_ug_per_cm2": limit,
        "sub_limit": sub_limit,
        "above_top_standard": above_top,
        "lower_bound_ug_per_cm2": 0.0 if sub_limit else point,
        "upper_bound_ug_per_cm2": limit if sub_limit else point,
    }


def total_contamination_level(species_list, sampling):
    """Return the bounded total areal mass over all species."""
    if not isinstance(species_list, (list, tuple)) or not species_list:
        raise ValueError("species_list must be a non-empty sequence")
    records = [species_areal_mass(item, sampling) for item in species_list]
    seen = set()
    for record in records:
        if record["name"] in seen:
            raise ValueError("species %s appears twice" % record["name"])
        seen.add(record["name"])
    return {
        "species": records,
        "lower_bound_ug_per_cm2": sum(r["lower_bound_ug_per_cm2"] for r in records),
        "upper_bound_ug_per_cm2": sum(r["upper_bound_ug_per_cm2"] for r in records),
        "bounded": any(r["sub_limit"] for r in records),
    }


def validate_level_bands(bands):
    """Return the level bands sorted tightest first, as (name, max_areal_mass)."""
    if not isinstance(bands, (list, tuple)) or not bands:
        raise ValueError("level bands must be a non-empty sequence of pairs")
    out = []
    names = set()
    for i, item in enumerate(bands):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("level band %d must be a (name, max) pair" % i)
        name, bound = item
        if not isinstance(name, str) or not name.strip():
            raise ValueError("level band %d name must be a non-empty string" % i)
        if name.strip() in names:
            raise ValueError("level band %r appears twice" % name.strip())
        names.add(name.strip())
        out.append((name.strip(), _positive("level band %d bound" % i, bound)))
    out.sort(key=lambda pair: pair[1])
    return out


def categorize_level(areal_mass, bands):
    """Return the tightest level band whose bound the areal mass satisfies."""
    value = _positive("areal_mass", areal_mass, allow_zero=True)
    ordered = validate_level_bands(bands)
    for name, bound in ordered:
        if _at_most(value, bound):
            return name
    return None


def assess_contamination_level(spec):
    """Run the full contamination-level calculation.

    spec keys: species (sequence of species records), sampling (chain),
    level_bands (sequence of (name, max) pairs).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("species", "sampling", "level_bands"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    totals = total_contamination_level(spec["species"], spec["sampling"])
    bands = validate_level_bands(spec["level_bands"])
    lower_level = categorize_level(totals["lower_bound_ug_per_cm2"], bands)
    upper_level = categorize_level(totals["upper_bound_ug_per_cm2"], bands)
    findings = []
    for record in totals["species"]:
        if record["sub_limit"]:
            findings.append(
                "species %s is at or below its quantification limit; the total "
                "is reported as an interval, not a point" % record["name"]
            )
        if record["above_top_standard"]:
            findings.append(
                "species %s was read above its top calibration standard; the "
                "mass is extrapolated and biased low" % record["name"]
            )
    if upper_level is None:
        findings.append(
            "the upper-bound total %.4f ug/cm2 exceeds every supplied level "
            "band; the result is out of scale, not the loosest level"
            % totals["upper_bound_ug_per_cm2"]
        )
    elif lower_level != upper_level:
        findings.append(
            "the bounded total straddles a level boundary: lower bound is %s "
            "and upper bound is %s" % (lower_level, upper_level)
        )
    return {
        "species": totals["species"],
        "lower_bound_ug_per_cm2": totals["lower_bound_ug_per_cm2"],
        "upper_bound_ug_per_cm2": totals["upper_bound_ug_per_cm2"],
        "bounded": totals["bounded"],
        "lower_bound_level": lower_level,
        "upper_bound_level": upper_level,
        "level": upper_level if lower_level == upper_level else None,
        "findings": findings,
        "unambiguous": not findings,
    }
