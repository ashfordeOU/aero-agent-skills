"""Procurement test matrix evaluation for a lot of commercial microcircuits.

Anchor: ECSS-Q-ST-60-13C Table 8-6 (procurement testing of microcircuits --
test methods, sample sizes and acceptance limits). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate every row of the matrix: a row names a test method, a sample size
   drawn from the lot, an accept number and whether the method consumes the
   devices it is run on. A consuming row is judged accept-on-zero.
2. Compute the burn-in percent defective allowable on the devices that
   entered burn-in, after a bounded exclusion of failures attributed to
   handling rather than to the devices themselves.
3. Count the parameter-drift rejects: a device whose measured delta exceeds
   its declared limit is a reject even when its end points still sit inside
   the datasheet window.
4. Check that the electrical row covered the cold, room and hot points; a run
   at room temperature alone does not stand for the row.
5. Hold a life test that stopped short of its declared duration, and hold the
   lot when any single row rejects rather than averaging rows together.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "MARGINAL_FRACTION",
    "MAX_EXCLUSION_FRACTION",
    "TEMPERATURE_POINTS",
    "validate_row",
    "burn_in_pda",
    "parameter_drift_rejects",
    "temperature_coverage",
    "life_test_verdict",
    "row_verdict",
    "assess_microcircuit_test_matrix",
]

# Limit comparisons are ratios of small integers scaled by 100; an exact
# equality with a limit can land a few ULPs on the wrong side. Absorb the
# representation error here, never by relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9

# An accepted row that has used up this share of its allowance is reported as
# marginal: the lot passes, but the margin is gone.
MARGINAL_FRACTION = 0.8

# Excluding failures from the burn-in population as handling damage is
# admissible but bounded; past this share of the failures the exclusion is
# carrying the result and is reported for challenge.
MAX_EXCLUSION_FRACTION = 0.25

# The electrical row is run at all three points; room alone is not the row.
TEMPERATURE_POINTS = ("cold", "room", "hot")

# Methods that consume the devices they are run on.
DESTRUCTIVE_METHODS = (
    "construction-analysis",
    "life-test",
    "bond-pull",
    "die-shear",
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
    """Return the normalised record for one row of the microcircuit matrix.

    A row whose method consumes its devices is judged accept-on-zero, so an
    accept number above zero on such a row is refused rather than honoured.
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
        raise ValueError("row '%s' must sample at least one device" % method)
    if sample > lot:
        raise ValueError(
            "row '%s' samples %d devices from a lot of %d" % (method, sample, lot)
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
    if destructive and accept_number > 0:
        raise ValueError(
            "row '%s' consumes its devices and is judged accept-on-zero, not on %d"
            % (method, accept_number)
        )
    return {
        "method": method,
        "lot_size": lot,
        "sample_size": sample,
        "accept_number": accept_number,
        "failures": failures,
        "destructive": destructive,
    }


def burn_in_pda(devices_entered, failures, allowable_percent, excluded_failures=0):
    """Return the burn-in percent-defective-allowable record.

    The rate is taken on the devices that entered burn-in, not on the devices
    that survived it, so a lot cannot improve its rate by shedding units.
    """
    entered = _count("devices_entered", devices_entered)
    if entered < 1:
        raise ValueError("devices_entered must be at least 1, got %d" % entered)
    observed_failures = _count("failures", failures)
    if observed_failures > entered:
        raise ValueError(
            "failures %d exceed the %d devices that entered burn-in"
            % (observed_failures, entered)
        )
    excluded = _count("excluded_failures", excluded_failures)
    if excluded > observed_failures:
        raise ValueError(
            "excluded_failures %d exceed the %d failures recorded"
            % (excluded, observed_failures)
        )
    allowance = _real("allowable_percent", allowable_percent)
    if allowance < 0.0 or allowance > 100.0:
        raise ValueError("allowable_percent must lie in 0..100, got %g" % allowance)
    device_failures = observed_failures - excluded
    pda = 100.0 * device_failures / entered
    within = _at_or_below(pda, allowance)
    challenged = observed_failures > 0 and excluded > MAX_EXCLUSION_FRACTION * observed_failures
    return {
        "devices_entered": entered,
        "failures": observed_failures,
        "excluded_failures": excluded,
        "device_failures": device_failures,
        "percent_defective": pda,
        "allowable_percent": allowance,
        "exclusion_challenged": challenged,
        "marginal": within and allowance > 0.0 and pda >= MARGINAL_FRACTION * allowance,
        "accepted": within,
    }


def parameter_drift_rejects(readings, delta_limit_percent):
    """Return the drift-reject record for a set of (initial, final) readings.

    A device is a drift reject when the magnitude of its relative change
    exceeds the declared delta limit; a change landing on the limit is
    admissible, the tolerance being representation error only.
    """
    limit = _real("delta_limit_percent", delta_limit_percent)
    if limit < 0.0:
        raise ValueError("delta_limit_percent must be non-negative, got %g" % limit)
    if not isinstance(readings, (list, tuple)) or not readings:
        raise ValueError("readings must be a non-empty sequence of (initial, final) pairs")
    drifts = []
    rejects = []
    for index, item in enumerate(readings):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("readings[%d] must be an (initial, final) pair" % index)
        initial = _real("readings[%d] initial" % index, item[0])
        final = _real("readings[%d] final" % index, item[1])
        if initial == 0.0:
            raise ValueError(
                "readings[%d] initial value is zero; relative drift is undefined" % index
            )
        drift = 100.0 * abs(final - initial) / abs(initial)
        drifts.append(drift)
        if not _at_or_below(drift, limit):
            rejects.append(index)
    return {
        "count": len(drifts),
        "drift_percent": drifts,
        "reject_indices": rejects,
        "rejects": len(rejects),
        "worst_drift_percent": max(drifts),
        "delta_limit_percent": limit,
        "accepted": not rejects,
    }


def temperature_coverage(points):
    """Return the coverage record for the electrical row's temperature points."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("points must be a non-empty sequence of temperature points")
    seen = []
    for index, item in enumerate(points):
        if not isinstance(item, str) or not item.strip():
            raise ValueError("points[%d] must be a non-empty string" % index)
        name = item.strip().lower()
        if name not in TEMPERATURE_POINTS:
            raise ValueError(
                "points[%d] %r is not one of %s"
                % (index, item, ", ".join(TEMPERATURE_POINTS))
            )
        if name not in seen:
            seen.append(name)
    missing = [name for name in TEMPERATURE_POINTS if name not in seen]
    return {
        "covered": seen,
        "missing": missing,
        "accepted": not missing,
    }


def life_test_verdict(
    hours_completed, hours_required, failures, sample_size, accept_number=0
):
    """Return the life-test record for the sampled devices.

    A run stopped short of its declared duration is held: the hours are the
    stress, and a shorter run is a different test, not a softer pass.
    """
    completed = _real("hours_completed", hours_completed)
    required = _real("hours_required", hours_required)
    if required <= 0.0:
        raise ValueError("hours_required must be positive, got %g" % required)
    if completed < 0.0:
        raise ValueError("hours_completed must be non-negative, got %g" % completed)
    sample = _count("sample_size", sample_size)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    observed = _count("failures", failures)
    if observed > sample:
        raise ValueError("failures %d exceed the sample of %d" % (observed, sample))
    allowed = _count("accept_number", accept_number)
    if allowed > sample:
        raise ValueError(
            "accept_number %d exceeds the sample of %d" % (allowed, sample)
        )
    duration_met = _at_or_above(completed, required)
    within_accept_number = observed <= allowed
    return {
        "hours_completed": completed,
        "hours_required": required,
        "shortfall_hours": max(0.0, required - completed),
        "duration_met": duration_met,
        "sample_size": sample,
        "failures": observed,
        "accept_number": allowed,
        "within_accept_number": within_accept_number,
        "accepted": duration_met and within_accept_number,
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


def assess_microcircuit_test_matrix(spec):
    """Run the Table 8-6 procurement test assessment for one microcircuit lot.

    spec keys: lot_size, rows, allowable_percent, optional burn_in, drift,
    electrical_points and life_test blocks.
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
    burn_in = None
    if "burn_in" in spec:
        block = spec["burn_in"]
        if not isinstance(block, dict):
            raise ValueError("spec['burn_in'] must be a mapping")
        burn_in = burn_in_pda(
            block.get("devices_entered"),
            block.get("failures"),
            block.get("allowable_percent", allowance),
            block.get("excluded_failures", 0),
        )
        if not burn_in["accepted"]:
            findings.append(
                "burn-in rate %.3f%% exceeds the allowable %.3f%% on %d devices entered"
                % (
                    burn_in["percent_defective"],
                    burn_in["allowable_percent"],
                    burn_in["devices_entered"],
                )
            )
        elif burn_in["marginal"]:
            findings.append(
                "burn-in accepted at %.3f%% of an allowable %.3f%%; little margin left"
                % (burn_in["percent_defective"], burn_in["allowable_percent"])
            )
        if burn_in["exclusion_challenged"]:
            findings.append(
                "%d of %d burn-in failures were excluded as handling damage; the exclusion carries the result"
                % (burn_in["excluded_failures"], burn_in["failures"])
            )
    drift = None
    if "drift" in spec:
        block = spec["drift"]
        if not isinstance(block, dict):
            raise ValueError("spec['drift'] must be a mapping")
        drift = parameter_drift_rejects(
            block.get("readings"), block.get("delta_limit_percent")
        )
        if not drift["accepted"]:
            findings.append(
                "%d device(s) drifted past the %.3f%% delta limit, worst %.3f%%"
                % (
                    drift["rejects"],
                    drift["delta_limit_percent"],
                    drift["worst_drift_percent"],
                )
            )
    electrical = None
    if "electrical_points" in spec:
        electrical = temperature_coverage(spec["electrical_points"])
        if not electrical["accepted"]:
            findings.append(
                "electrical row missing the %s point(s)" % ", ".join(electrical["missing"])
            )
    life = None
    if "life_test" in spec:
        block = spec["life_test"]
        if not isinstance(block, dict):
            raise ValueError("spec['life_test'] must be a mapping")
        life = life_test_verdict(
            block.get("hours_completed"),
            block.get("hours_required"),
            block.get("failures", 0),
            block.get("sample_size"),
            block.get("accept_number", 0),
        )
        if not life["duration_met"]:
            findings.append(
                "life test stopped %.1f h short of the declared %.1f h"
                % (life["shortfall_hours"], life["hours_required"])
            )
        if not life["within_accept_number"]:
            findings.append(
                "life test: %d failures exceed the accept number %d"
                % (life["failures"], life["accept_number"])
            )
    rejecting = [item["method"] for item in judged if not item["accepted"]]
    accepted = (
        not rejecting
        and (burn_in is None or burn_in["accepted"])
        and (drift is None or drift["accepted"])
        and (electrical is None or electrical["accepted"])
        and (life is None or life["accepted"])
    )
    return {
        "lot_size": records[0]["lot_size"],
        "rows": judged,
        "burn_in": burn_in,
        "drift": drift,
        "electrical": electrical,
        "life_test": life,
        "rejecting_rows": rejecting,
        "accepted": accepted,
        "disposition": "accept-microcircuit-lot" if accepted else "hold-microcircuit-lot",
        "findings": findings,
    }
