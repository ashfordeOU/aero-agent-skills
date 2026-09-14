"""Procurement test matrix evaluation for a lot of commercial fuses.

Anchor: ECSS-Q-ST-60-13C Table 8-4 (procurement testing of fuses -- test
methods, sample sizes and acceptance limits). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every row of the matrix: a row names a test method, a sample size
   drawn from the lot, an accept number and whether the method consumes the
   units it is run on.
2. Size the destructive sample budget. Fusing-characteristic and
   breaking-capacity runs end with an open element, so those units are bought
   on top of the flight quantity and never delivered.
3. Judge voltage-drop and cold-resistance readings against their maximum
   limits, a reading landing on the limit being admissible.
4. Check each fusing time against the time-current window declared for the
   overload multiple the sample was run at; a fuse that opens too early is a
   reject just as much as one that opens too late.
5. Treat any unit that opens during the rated-current endurance run as an
   outright reject of the lot, whatever the row accept numbers allow.
6. Convert row failures into a percent defective, compare it with the
   allowance, and hold the lot when any single row rejects.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MARGINAL_FRACTION",
    "validate_row",
    "sample_budget",
    "voltage_drop_verdict",
    "fusing_time_verdict",
    "endurance_verdict",
    "row_verdict",
    "assess_fuse_test_matrix",
]

# Limit comparisons are ratios of small decimals; an exact equality with a
# limit can land a few ULPs on the wrong side. Absorb the representation error
# here, never by relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9

# An accepted row that has used up this share of its allowance is reported as
# marginal: the lot passes, but the next delivery of the same build is the one
# that will cross.
MARGINAL_FRACTION = 0.8

# Methods that end with a consumed unit. A fuse run to its fusing point or to
# its breaking capacity cannot be delivered afterwards.
DESTRUCTIVE_METHODS = (
    "fusing-time-current",
    "breaking-capacity",
    "overload-endurance",
    "construction-analysis",
)


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


def validate_row(row, lot_size):
    """Return the normalised record for one row of the fuse test matrix.

    row keys: method, sample_size, optional accept_number (defaults to
    accept-on-zero), optional failures, optional destructive override.
    """
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
    destructive = row.get("destructive")
    if destructive is None:
        destructive = method in DESTRUCTIVE_METHODS
    if not isinstance(destructive, bool):
        raise ValueError("row '%s' destructive flag must be a boolean" % method)
    return {
        "method": method,
        "lot_size": lot,
        "sample_size": sample,
        "accept_number": accept_number,
        "failures": failures,
        "destructive": destructive,
    }


def sample_budget(rows, lot_size, flight_quantity):
    """Return the purchase quantity the matrix forces for a flight need.

    Units consumed by destructive rows are bought on top of the flight
    quantity; a purchase order sized on the flight need alone cannot deliver
    the flight quantity once the matrix has been run.
    """
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("rows must be a non-empty sequence")
    flight = _count("flight_quantity", flight_quantity)
    if flight < 1:
        raise ValueError("flight_quantity must be at least 1, got %d" % flight)
    records = [validate_row(item, lot_size) for item in rows]
    consumed = sum(item["sample_size"] for item in records if item["destructive"])
    minimum = flight + consumed
    lot = records[0]["lot_size"]
    return {
        "flight_quantity": flight,
        "destructive_units": consumed,
        "minimum_purchase_quantity": minimum,
        "lot_size": lot,
        "lot_covers_budget": lot >= minimum,
        "shortfall": max(0, minimum - lot),
    }


def voltage_drop_verdict(readings_mv, limit_mv):
    """Return the voltage-drop record for a sampled set of readings."""
    limit = _real("limit_mv", limit_mv)
    if limit <= 0.0:
        raise ValueError("limit_mv must be positive, got %g" % limit)
    if not isinstance(readings_mv, (list, tuple)) or not readings_mv:
        raise ValueError("readings_mv must be a non-empty sequence")
    values = []
    over = []
    for index, item in enumerate(readings_mv):
        value = _real("readings_mv[%d]" % index, item)
        if value <= 0.0:
            raise ValueError("readings_mv[%d] must be positive, got %g" % (index, value))
        values.append(value)
        if not _at_or_below(value, limit):
            over.append(index)
    worst = max(values)
    return {
        "count": len(values),
        "readings_mv": values,
        "limit_mv": limit,
        "over_limit_indices": over,
        "failures": len(over),
        "worst_mv": worst,
        "used_fraction": worst / limit,
        "accepted": not over,
    }


def fusing_time_verdict(times_s, min_s, max_s, overload_multiple):
    """Return the time-current record for a sampled set of fusing times.

    A unit opening before the window is as much a reject as one opening after
    it: an early fuse nuisance-trips on inrush, a late one stops protecting.
    """
    low = _real("min_s", min_s)
    high = _real("max_s", max_s)
    multiple = _real("overload_multiple", overload_multiple)
    if low <= 0.0:
        raise ValueError("min_s must be positive, got %g" % low)
    if high <= low:
        raise ValueError("max_s %g must exceed min_s %g" % (high, low))
    if multiple <= 1.0:
        raise ValueError(
            "overload_multiple must exceed 1.0 to open a fuse, got %g" % multiple
        )
    if not isinstance(times_s, (list, tuple)) or not times_s:
        raise ValueError("times_s must be a non-empty sequence")
    values = []
    early = []
    late = []
    for index, item in enumerate(times_s):
        value = _real("times_s[%d]" % index, item)
        if value <= 0.0:
            raise ValueError("times_s[%d] must be positive, got %g" % (index, value))
        values.append(value)
        if not _at_or_above(value, low):
            early.append(index)
        elif not _at_or_below(value, high):
            late.append(index)
    return {
        "count": len(values),
        "times_s": values,
        "min_s": low,
        "max_s": high,
        "overload_multiple": multiple,
        "early_indices": early,
        "late_indices": late,
        "failures": len(early) + len(late),
        "fastest_s": min(values),
        "slowest_s": max(values),
        "accepted": not early and not late,
    }


def endurance_verdict(opened_units, sample_size, hours):
    """Return the rated-current endurance record.

    A fuse that opens while carrying its rated current has failed the lot
    outright; no row accept number covers it.
    """
    sample = _count("sample_size", sample_size)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    opened = _count("opened_units", opened_units)
    if opened > sample:
        raise ValueError(
            "opened_units %d exceeds the endurance sample of %d" % (opened, sample)
        )
    duration = _real("hours", hours)
    if duration <= 0.0:
        raise ValueError("hours must be positive, got %g" % duration)
    return {
        "sample_size": sample,
        "opened_units": opened,
        "hours": duration,
        "accepted": opened == 0,
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


def assess_fuse_test_matrix(spec):
    """Run the Table 8-4 procurement test assessment for one fuse lot.

    spec keys: lot_size, flight_quantity, rows, allowable_percent, optional
    voltage_drop, fusing_time and endurance blocks.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "flight_quantity", "rows", "allowable_percent"):
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
    budget = sample_budget(rows, spec["lot_size"], spec["flight_quantity"])
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
    if not budget["lot_covers_budget"]:
        findings.append(
            "lot of %d cannot cover %d flight units plus %d destroyed by the matrix"
            % (budget["lot_size"], budget["flight_quantity"], budget["destructive_units"])
        )
    drop = None
    if "voltage_drop" in spec:
        block = spec["voltage_drop"]
        if not isinstance(block, dict):
            raise ValueError("spec['voltage_drop'] must be a mapping")
        drop = voltage_drop_verdict(block.get("readings_mv"), block.get("limit_mv"))
        if not drop["accepted"]:
            findings.append(
                "%d unit(s) exceed the %.3f mV voltage-drop limit, worst %.3f mV"
                % (drop["failures"], drop["limit_mv"], drop["worst_mv"])
            )
    timing = None
    if "fusing_time" in spec:
        block = spec["fusing_time"]
        if not isinstance(block, dict):
            raise ValueError("spec['fusing_time'] must be a mapping")
        timing = fusing_time_verdict(
            block.get("times_s"),
            block.get("min_s"),
            block.get("max_s"),
            block.get("overload_multiple"),
        )
        if timing["early_indices"]:
            findings.append(
                "%d unit(s) opened before the %.3f s window at %.2f times rated current"
                % (len(timing["early_indices"]), timing["min_s"], timing["overload_multiple"])
            )
        if timing["late_indices"]:
            findings.append(
                "%d unit(s) opened after the %.3f s window at %.2f times rated current"
                % (len(timing["late_indices"]), timing["max_s"], timing["overload_multiple"])
            )
    endurance = None
    if "endurance" in spec:
        block = spec["endurance"]
        if not isinstance(block, dict):
            raise ValueError("spec['endurance'] must be a mapping")
        endurance = endurance_verdict(
            block.get("opened_units"), block.get("sample_size"), block.get("hours")
        )
        if not endurance["accepted"]:
            findings.append(
                "%d unit(s) opened while carrying rated current for %.1f h"
                % (endurance["opened_units"], endurance["hours"])
            )
    rejecting = [item["method"] for item in judged if not item["accepted"]]
    accepted = (
        not rejecting
        and (drop is None or drop["accepted"])
        and (timing is None or timing["accepted"])
        and (endurance is None or endurance["accepted"])
        and budget["lot_covers_budget"]
    )
    return {
        "lot_size": budget["lot_size"],
        "rows": judged,
        "budget": budget,
        "voltage_drop": drop,
        "fusing_time": timing,
        "endurance": endurance,
        "rejecting_rows": rejecting,
        "accepted": accepted,
        "disposition": "accept-fuse-lot" if accepted else "hold-fuse-lot",
        "findings": findings,
    }
