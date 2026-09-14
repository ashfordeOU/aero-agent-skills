"""Lot acceptance decision for one date-code lot of a commercial EEE part.

Anchor: ECSS-Q-ST-60-13C clause 4.3.5 (lot acceptance testing for the highest
assurance category of commercial parts). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the date code (YYWW) the lot is offered under, and refuse a
   delivery whose units carry more than one date code -- the acceptance
   verdict is a statement about a single homogeneous lot.
2. Validate each test subgroup: the sample must be drawn from the lot, so a
   sample larger than the lot, a zero sample or a negative failure count is an
   input error rather than a degenerate case to be clamped.
3. Take each subgroup's failures against its accept number, convert them into
   a percent defective, and compare that with the allowable percent defective
   declared for the lot.
4. Count the parameter-drift rejects: a unit whose measured delta exceeds the
   declared drift limit is a reject even when it still meets the end-point
   limits, because drift is what the burn-in subgroup is there to expose.
5. Hold the lot when ANY subgroup rejects. Subgroups are not averaged, and an
   accepted lot sitting close to its allowance is reported as a marginal-lot
   advisory instead of a bare pass.
"""

import math

__all__ = [
    "ACCEPTANCE_TOLERANCE",
    "MARGINAL_FRACTION",
    "validate_date_code",
    "lot_date_code",
    "validate_sample",
    "percent_defective",
    "subgroup_verdict",
    "parameter_drift_rejects",
    "assess_lot_acceptance",
]

# Percent-defective comparisons are a ratio of small integers scaled by 100; an
# exact equality with the allowance can land a few ULPs on the wrong side.
# Absorb the representation error here, never by relaxing the allowance.
ACCEPTANCE_TOLERANCE = 1e-9

# An accepted subgroup that has used up this share of its allowance is
# reported as marginal: the lot passes, but it carries no room for the next
# date code of the same build.
MARGINAL_FRACTION = 0.8


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


def validate_date_code(date_code):
    """Return the (year, week) pair parsed from a four-digit YYWW date code."""
    if not isinstance(date_code, str):
        raise ValueError("date_code must be a four-digit YYWW string, got %r" % (date_code,))
    code = date_code.strip()
    if len(code) != 4 or not code.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (date_code,))
    year = int(code[:2])
    week = int(code[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (date_code,))
    return (year, week)


def lot_date_code(date_codes):
    """Return the single date code a lot is offered under.

    A delivery carrying more than one date code is not one lot and cannot take
    one acceptance verdict, so it is refused rather than merged.
    """
    if isinstance(date_codes, str):
        date_codes = [date_codes]
    if not isinstance(date_codes, (list, tuple)) or not date_codes:
        raise ValueError("date_codes must be a non-empty sequence of date codes")
    seen = []
    for item in date_codes:
        validate_date_code(item)
        code = item.strip()
        if code not in seen:
            seen.append(code)
    if len(seen) > 1:
        raise ValueError(
            "lot carries %d date codes (%s); one acceptance verdict covers one date code"
            % (len(seen), ", ".join(sorted(seen)))
        )
    return seen[0]


def validate_sample(lot_size, sample_size):
    """Return the validated (lot_size, sample_size) pair for one subgroup."""
    lot = _count("lot_size", lot_size)
    sample = _count("sample_size", sample_size)
    if lot < 1:
        raise ValueError("lot_size must be at least 1, got %d" % lot)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    if sample > lot:
        raise ValueError(
            "sample_size %d exceeds lot_size %d; the sample is drawn from the lot" % (sample, lot)
        )
    return (lot, sample)


def percent_defective(failures, sample_size):
    """Return the percent defective of a subgroup sample."""
    fails = _count("failures", failures)
    sample = _count("sample_size", sample_size)
    if sample < 1:
        raise ValueError("sample_size must be at least 1, got %d" % sample)
    if fails > sample:
        raise ValueError("failures %d exceed sample_size %d" % (fails, sample))
    return 100.0 * fails / sample


def subgroup_verdict(subgroup, lot_size, allowable_percent):
    """Return the accept/reject record for one lot acceptance test subgroup.

    subgroup keys: name, sample_size, failures, optional accept_number
    (defaults to accept-on-zero) and optional allowable_percent overriding the
    lot-level allowance.
    """
    if not isinstance(subgroup, dict):
        raise ValueError("subgroup must be a mapping")
    for key in ("name", "sample_size", "failures"):
        if key not in subgroup:
            raise ValueError("subgroup missing required key '%s'" % key)
    name = subgroup["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("subgroup name must be a non-empty string")
    lot, sample = validate_sample(lot_size, subgroup["sample_size"])
    fails = _count("failures", subgroup["failures"])
    if fails > sample:
        raise ValueError("subgroup '%s' reports %d failures in a sample of %d" % (name, fails, sample))
    accept_number = _count("accept_number", subgroup.get("accept_number", 0))
    allowance = _real("allowable_percent", subgroup.get("allowable_percent", allowable_percent))
    if allowance < 0.0 or allowance > 100.0:
        raise ValueError("allowable_percent must lie in 0..100, got %g" % allowance)
    observed = percent_defective(fails, sample)
    within_accept_number = fails <= accept_number
    within_allowance = observed < allowance or math.isclose(
        observed, allowance, rel_tol=0.0, abs_tol=ACCEPTANCE_TOLERANCE
    )
    accepted = within_accept_number and within_allowance
    marginal = accepted and allowance > 0.0 and observed >= MARGINAL_FRACTION * allowance
    return {
        "name": name.strip(),
        "lot_size": lot,
        "sample_size": sample,
        "failures": fails,
        "accept_number": accept_number,
        "percent_defective": observed,
        "allowable_percent": allowance,
        "within_accept_number": within_accept_number,
        "within_allowance": within_allowance,
        "accepted": accepted,
        "marginal": marginal,
    }


def parameter_drift_rejects(readings, drift_limit_percent):
    """Return the drift-reject record for a set of (initial, final) readings.

    A unit is a drift reject when the magnitude of its relative parameter
    change exceeds the declared limit; a change landing exactly on the limit is
    admissible, the tolerance being representation error only.
    """
    limit = _real("drift_limit_percent", drift_limit_percent)
    if limit < 0.0:
        raise ValueError("drift_limit_percent must be non-negative, got %g" % limit)
    if not isinstance(readings, (list, tuple)):
        raise ValueError("readings must be a sequence of (initial, final) pairs")
    rejects = []
    drifts = []
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
        over = drift > limit and not math.isclose(
            drift, limit, rel_tol=0.0, abs_tol=ACCEPTANCE_TOLERANCE
        )
        if over:
            rejects.append(index)
    worst = max(drifts) if drifts else 0.0
    return {
        "count": len(drifts),
        "drift_percent": drifts,
        "reject_indices": rejects,
        "rejects": len(rejects),
        "worst_drift_percent": worst,
        "drift_limit_percent": limit,
        "accepted": not rejects,
    }


def assess_lot_acceptance(spec):
    """Run the full clause 4.3.5 lot acceptance assessment for one date code.

    spec keys: date_codes (or date_code), lot_size, subgroups,
    allowable_percent, optional drift_readings and drift_limit_percent.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("lot_size", "subgroups", "allowable_percent"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if "date_codes" in spec:
        code = lot_date_code(spec["date_codes"])
    elif "date_code" in spec:
        code = lot_date_code(spec["date_code"])
    else:
        raise ValueError("spec missing required key 'date_code' or 'date_codes'")
    subgroups = spec["subgroups"]
    if not isinstance(subgroups, (list, tuple)) or not subgroups:
        raise ValueError("spec['subgroups'] must be a non-empty sequence")
    allowance = _real("allowable_percent", spec["allowable_percent"])
    records = [
        subgroup_verdict(item, spec["lot_size"], allowance) for item in subgroups
    ]
    findings = []
    for record in records:
        if not record["within_accept_number"]:
            findings.append(
                "subgroup '%s': %d failures exceed the accept number %d"
                % (record["name"], record["failures"], record["accept_number"])
            )
        elif not record["within_allowance"]:
            findings.append(
                "subgroup '%s': %.3f%% defective exceeds the allowable %.3f%%"
                % (record["name"], record["percent_defective"], record["allowable_percent"])
            )
        elif record["marginal"]:
            findings.append(
                "subgroup '%s' accepted at %.3f%% of an allowable %.3f%%; little margin left"
                % (record["name"], record["percent_defective"], record["allowable_percent"])
            )
    drift = None
    if "drift_readings" in spec:
        if "drift_limit_percent" not in spec:
            raise ValueError("drift_readings supplied without 'drift_limit_percent'")
        drift = parameter_drift_rejects(spec["drift_readings"], spec["drift_limit_percent"])
        if not drift["accepted"]:
            findings.append(
                "%d unit(s) drifted past the %.3f%% limit, worst %.3f%%"
                % (drift["rejects"], drift["drift_limit_percent"], drift["worst_drift_percent"])
            )
    rejecting = [record["name"] for record in records if not record["accepted"]]
    accepted = not rejecting and (drift is None or drift["accepted"])
    return {
        "date_code": code,
        "lot_size": records[0]["lot_size"],
        "subgroups": records,
        "drift": drift,
        "rejecting_subgroups": rejecting,
        "accepted": accepted,
        "disposition": "release-for-flight" if accepted else "hold-lot",
        "findings": findings,
    }
