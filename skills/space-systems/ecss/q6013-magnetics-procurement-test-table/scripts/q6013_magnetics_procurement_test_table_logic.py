"""Procurement test matrix evaluation for a lot of commercial magnetic parts.

Anchor: ECSS-Q-ST-60-13C Table 8-5 (procurement testing of magnetic parts --
test methods, sample sizes and acceptance limits). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every row of the matrix: a row names a test method, a sample size
   drawn from the lot, an accept number and the shape of the limit its
   readings are judged against.
2. Correct each winding-resistance reading from the temperature it was taken
   at back to the reference temperature before it meets its limit. A copper
   winding measured warm reads high, and an uncorrected reading fails a part
   the table would have accepted.
3. Judge each measured quantity against the shape of its own limit: a maximum
   for resistance, a minimum for insulation resistance, a two-sided band for
   inductance and turns ratio.
4. Refuse a dielectric-withstanding run carried out below the declared test
   voltage, and reject the sample when its leakage exceeded the declared
   current.
5. Convert row failures into a percent defective, compare it with the
   allowance as well as the accept number, and hold the lot when any single
   row rejects.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MARGINAL_FRACTION",
    "COPPER_INFERRED_ZERO_C",
    "REFERENCE_TEMPERATURE_C",
    "LIMIT_KINDS",
    "corrected_winding_resistance",
    "winding_resistance_verdict",
    "limit_verdict",
    "dielectric_withstanding_verdict",
    "validate_row",
    "row_verdict",
    "assess_magnetics_test_matrix",
]

# Limit comparisons are ratios of small decimals; an exact equality with a
# limit can land a few ULPs on the wrong side. Absorb the representation error
# here, never by relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9

# An accepted row that has used up this share of its allowance is reported as
# marginal: the lot passes, but the margin is gone.
MARGINAL_FRACTION = 0.8

# Inferred zero-resistance temperature of annealed copper, in degrees Celsius.
# The winding-resistance correction is a ratio about this constant.
COPPER_INFERRED_ZERO_C = 234.5

# Winding-resistance limits are quoted at this reference temperature.
REFERENCE_TEMPERATURE_C = 20.0

# The three limit shapes a row of the table can carry.
LIMIT_KINDS = ("maximum", "minimum", "band")


def _real(label, value):
    """Return value as a finite float, raising on anything that is not one."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _at_or_below(value, limit):
    """Return True when value is at or below limit within the tolerance."""
    return value < limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def _at_or_above(value, limit):
    """Return True when value is at or above limit within the tolerance."""
    return value > limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def corrected_winding_resistance(
    resistance_ohm,
    measured_temperature_c,
    reference_temperature_c=REFERENCE_TEMPERATURE_C,
    inferred_zero_c=COPPER_INFERRED_ZERO_C,
):
    """Return a winding resistance corrected to the reference temperature."""
    resistance = _real("resistance_ohm", resistance_ohm)
    if resistance <= 0.0:
        raise ValueError("resistance_ohm must be positive, got %g" % resistance)
    measured = _real("measured_temperature_c", measured_temperature_c)
    reference = _real("reference_temperature_c", reference_temperature_c)
    zero_point = _real("inferred_zero_c", inferred_zero_c)
    if zero_point <= 0.0:
        raise ValueError("inferred_zero_c must be positive, got %g" % zero_point)
    if measured <= -zero_point:
        raise ValueError(
            "measured_temperature_c %g sits at or below the inferred zero -%g"
            % (measured, zero_point)
        )
    if reference <= -zero_point:
        raise ValueError(
            "reference_temperature_c %g sits at or below the inferred zero -%g"
            % (reference, zero_point)
        )
    return resistance * (zero_point + reference) / (zero_point + measured)


def winding_resistance_verdict(
    readings, limit_ohm, reference_temperature_c=REFERENCE_TEMPERATURE_C
):
    """Return the winding-resistance record for a set of (ohm, degC) readings.

    Every reading is corrected to the reference temperature first; the limit
    is a maximum, and a corrected value landing on it is admissible.
    """
    limit = _real("limit_ohm", limit_ohm)
    if limit <= 0.0:
        raise ValueError("limit_ohm must be positive, got %g" % limit)
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of (ohm, degC) pairs")
    corrected = []
    over = []
    for index, item in enumerate(readings):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("readings[%d] must be an (ohm, degC) pair" % index)
        value = corrected_winding_resistance(
            item[0], item[1], reference_temperature_c
        )
        corrected.append(value)
        if not _at_or_below(value, limit):
            over.append(index)
    worst = max(corrected)
    return {
        "count": len(corrected),
        "corrected_ohm": corrected,
        "limit_ohm": limit,
        "reference_temperature_c": _real(
            "reference_temperature_c", reference_temperature_c
        ),
        "over_limit_indices": over,
        "failures": len(over),
        "worst_ohm": worst,
        "used_fraction": worst / limit,
        "accepted": not over,
    }


def limit_verdict(values, kind, lower=None, upper=None):
    """Return the record for a measured quantity judged against its limit.

    kind is one of 'maximum' (upper bound only), 'minimum' (lower bound only)
    or 'band' (both). A value landing on a bound is admissible.
    """
    if kind not in LIMIT_KINDS:
        raise ValueError("kind must be one of %s, got %r" % (", ".join(LIMIT_KINDS), kind))
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("values must be a non-empty sequence")
    low = None if lower is None else _real("lower", lower)
    high = None if upper is None else _real("upper", upper)
    if kind in ("maximum", "band") and high is None:
        raise ValueError("kind '%s' needs an upper bound" % kind)
    if kind in ("minimum", "band") and low is None:
        raise ValueError("kind '%s' needs a lower bound" % kind)
    if kind == "band" and high <= low:
        raise ValueError("band upper %g must exceed lower %g" % (high, low))
    readings = []
    under = []
    over = []
    for index, item in enumerate(values):
        value = _real("values[%d]" % index, item)
        readings.append(value)
        if low is not None and not _at_or_above(value, low):
            under.append(index)
        elif high is not None and not _at_or_below(value, high):
            over.append(index)
    return {
        "count": len(readings),
        "values": readings,
        "kind": kind,
        "lower": low,
        "upper": high,
        "under_indices": under,
        "over_indices": over,
        "failures": len(under) + len(over),
        "lowest": min(readings),
        "highest": max(readings),
        "accepted": not under and not over,
    }


def dielectric_withstanding_verdict(
    leakage_ua, limit_ua, applied_volts, required_volts
):
    """Return the dielectric-withstanding record for one sampled unit set.

    A run carried out below the declared test voltage is not a weaker pass; it
    is not a result, and it is refused rather than graded.
    """
    leakage = _real("leakage_ua", leakage_ua)
    limit = _real("limit_ua", limit_ua)
    applied = _real("applied_volts", applied_volts)
    required = _real("required_volts", required_volts)
    if leakage < 0.0:
        raise ValueError("leakage_ua must be non-negative, got %g" % leakage)
    if limit <= 0.0:
        raise ValueError("limit_ua must be positive, got %g" % limit)
    if required <= 0.0:
        raise ValueError("required_volts must be positive, got %g" % required)
    if applied <= 0.0:
        raise ValueError("applied_volts must be positive, got %g" % applied)
    if not _at_or_above(applied, required):
        raise ValueError(
            "dielectric run applied %g V against a required %g V; the result cannot be graded"
            % (applied, required)
        )
    return {
        "leakage_ua": leakage,
        "limit_ua": limit,
        "applied_volts": applied,
        "required_volts": required,
        "used_fraction": leakage / limit,
        "accepted": _at_or_below(leakage, limit),
    }


def validate_row(row, lot_size):
    """Return the normalised record for one row of the magnetics test matrix."""
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping")
    for key in ("method", "sample_size"):
        if key not in row:
            raise ValueError("row missing required key '%s'" % key)
    method = row["method"]
    if not isinstance(method, str) or not method.strip():
        raise ValueError("row method must be a non-empty string")
    method = method.strip()
    lot = _count("lot_size", lot_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    sample = _count("sample_size", row["sample_size"])
    if sample < 1:
        raise ValueError("row '%s' must sample at least one unit" % method)
    if sample > lot:
        raise ValueError(
            "row '%s' samples %d units from a lot of %d" % (method, sample, lot)
        )
    accept_number = _count("accept_number", row.get("accept_number", 0))
    if accept_number > sample:
        raise ValueError(
            "row '%s' accept number %d exceeds its sample of %d"
            % (method, accept_number, sample)
        )
    failures = _count("failures", row.get("failures", 0))
    if failures > sample:
        raise ValueError(
            "row '%s' reports %d failures in a sample of %d" % (method, failures, sample)
        )
    kind = row.get("limit_kind", "maximum")
    if kind not in LIMIT_KINDS:
        raise ValueError(
            "row '%s' limit_kind must be one of %s, got %r"
            % (method, ", ".join(LIMIT_KINDS), kind)
        )
    return {
        "method": method,
        "lot_size": lot,
        "sample_size": sample,
        "accept_number": accept_number,
        "failures": failures,
        "limit_kind": kind,
    }


def row_verdict(record, allowable_percent):
    """Return the accept/reject judgement for one validated matrix row."""
    if not isinstance(record, dict) or "method" not in record:
        raise ValueError("record must be a validated row mapping")
    allowance = _real("allowable_percent", allowable_percent)
    if allowance < 0.0 or allowance > 100.0:
        raise ValueError("allowable_percent must lie in 0..100, got %g" % allowance)
    sample = record["sample_size"]
    failures = record["failures"]
    observed = 100.0 * failures / sample
    within_accept_number = failures <= record["accept_number"]
    within_allowance = _at_or_below(observed, allowance)
    accepted = within_accept_number and within_allowance
    marginal = (
        accepted and allowance > 0.0 and observed >= MARGINAL_FRACTION * allowance
    )
    out = dict(record)
    out.update(
        {
            "percent_defective": observed,
            "allowable_percent": allowance,
            "within_accept_number": within_accept_number,
            "within_allowance": within_allowance,
            "accepted": accepted,
            "marginal": marginal,
        }
    )
    return out


def assess_magnetics_test_matrix(spec):
    """Run the Table 8-5 procurement test assessment for one magnetics lot.

    spec keys: lot_size, rows, allowable_percent, optional winding_resistance,
    measurements and dielectric blocks.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "rows", "allowable_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    rows = spec["rows"]
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("spec['rows'] must be a non-empty sequence")
    records = [validate_row(item, spec["lot_size"]) for item in rows]
    names = [item["method"] for item in records]
    if len(set(names)) != len(names):
        raise ValueError("matrix repeats a test method; each row is judged once")
    allowance = _real("allowable_percent", spec["allowable_percent"])
    judged = [row_verdict(item, allowance) for item in records]
    findings = []
    for item in judged:
        if not item["within_accept_number"]:
            findings.append(
                "row '%s': %d failures exceed the accept number %d"
                % (item["method"], item["failures"], item["accept_number"])
            )
        elif not item["within_allowance"]:
            findings.append(
                "row '%s': %.3f%% defective exceeds the allowable %.3f%%"
                % (item["method"], item["percent_defective"], item["allowable_percent"])
            )
        elif item["marginal"]:
            findings.append(
                "row '%s' accepted at %.3f%% of an allowable %.3f%%; little margin left"
                % (item["method"], item["percent_defective"], item["allowable_percent"])
            )
    winding = None
    if "winding_resistance" in spec:
        block = spec["winding_resistance"]
        if not isinstance(block, dict):
            raise ValueError("spec['winding_resistance'] must be a mapping")
        winding = winding_resistance_verdict(
            block.get("readings"),
            block.get("limit_ohm"),
            block.get("reference_temperature_c", REFERENCE_TEMPERATURE_C),
        )
        if not winding["accepted"]:
            findings.append(
                "%d winding(s) exceed the %.4f ohm limit once corrected to %.1f degC, worst %.4f ohm"
                % (
                    winding["failures"],
                    winding["limit_ohm"],
                    winding["reference_temperature_c"],
                    winding["worst_ohm"],
                )
            )
    measurements = []
    for index, block in enumerate(spec.get("measurements", [])):
        if not isinstance(block, dict):
            raise ValueError("measurements[%d] must be a mapping" % index)
        name = block.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("measurements[%d] needs a non-empty name" % index)
        record = limit_verdict(
            block.get("values"),
            block.get("kind", "band"),
            block.get("lower"),
            block.get("upper"),
        )
        record["name"] = name.strip()
        measurements.append(record)
        if record["under_indices"]:
            findings.append(
                "%s: %d reading(s) below the lower bound %.4f, lowest %.4f"
                % (record["name"], len(record["under_indices"]), record["lower"], record["lowest"])
            )
        if record["over_indices"]:
            findings.append(
                "%s: %d reading(s) above the upper bound %.4f, highest %.4f"
                % (record["name"], len(record["over_indices"]), record["upper"], record["highest"])
            )
    dielectric = None
    if "dielectric" in spec:
        block = spec["dielectric"]
        if not isinstance(block, dict):
            raise ValueError("spec['dielectric'] must be a mapping")
        dielectric = dielectric_withstanding_verdict(
            block.get("leakage_ua"),
            block.get("limit_ua"),
            block.get("applied_volts"),
            block.get("required_volts"),
        )
        if not dielectric["accepted"]:
            findings.append(
                "dielectric leakage %.4f uA exceeds the %.4f uA limit at %.1f V"
                % (
                    dielectric["leakage_ua"],
                    dielectric["limit_ua"],
                    dielectric["applied_volts"],
                )
            )
    rejecting = [item["method"] for item in judged if not item["accepted"]]
    accepted = (
        not rejecting
        and (winding is None or winding["accepted"])
        and (dielectric is None or dielectric["accepted"])
        and all(item["accepted"] for item in measurements)
    )
    return {
        "lot_size": records[0]["lot_size"],
        "rows": judged,
        "winding_resistance": winding,
        "measurements": measurements,
        "dielectric": dielectric,
        "rejecting_rows": rejecting,
        "accepted": accepted,
        "disposition": "accept-magnetics-lot" if accepted else "hold-magnetics-lot",
        "findings": findings,
    }
