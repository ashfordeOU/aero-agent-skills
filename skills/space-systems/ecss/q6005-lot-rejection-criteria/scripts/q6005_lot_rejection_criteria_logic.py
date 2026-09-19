"""Quantitative limits beyond which a hybrid lot is refused.

Anchor: ECSS-Q-ST-60-05C clause 10.4.2 (the limits on observed failures past
which the whole batch is refused). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the per-stage screening record: units entering the stage, and the
   failures charged to the lot at that stage. The flow has to be consistent --
   a stage cannot start with more units than the previous stage passed on.
2. Compute the percentage defective at each stage and compare it with the
   percentage allowed for that stage. A value sitting exactly on the limit is
   within the limit: the comparison absorbs representation error with a named
   tolerance instead of picking a side of an equality that libm rounds
   differently on different hosts.
3. Apply the accept-number path to a small lot. Below a stated population a
   percentage says more about the sample size than about the process, so the
   criterion becomes an absolute number of failures -- and a stage that allows
   no percentage allows no failures either.
4. Compute the cumulative percentage over the whole screening sequence
   against the units that entered it, because a lot can stay inside every
   stage limit and still shed an unacceptable fraction overall.
5. Return the per-stage verdicts, the cumulative verdict and the overall
   accept or reject, naming every limit that was exceeded.
"""

import math

__all__ = [
    "CUMULATIVE_LIMIT_PERCENT",
    "DEFAULT_STAGE_LIMITS",
    "LIMIT_TOLERANCE",
    "SMALL_LOT_ACCEPT_NUMBER",
    "SMALL_LOT_THRESHOLD",
    "accept_number",
    "assess_lot_rejection_criteria",
    "cumulative_percent_defective",
    "evaluate_stage",
    "exceeds_limit",
    "percent_defective",
    "resolve_limits",
    "validate_stage_records",
]

# Percentage defective allowed at each screening or acceptance stage.
DEFAULT_STAGE_LIMITS = {
    "internal-visual": 10.0,
    "temperature-cycling": 5.0,
    "constant-acceleration": 5.0,
    "burn-in": 5.0,
    "final-electrical": 10.0,
    "seal-fine-leak": 5.0,
    "seal-gross-leak": 5.0,
    "external-visual": 5.0,
    "lot-acceptance-tests": 0.0,
}

# Allowed across the whole screening sequence, against the units that entered it.
CUMULATIVE_LIMIT_PERCENT = 10.0

# Below this population a percentage criterion is replaced by an absolute
# accept number, because one failure out of a handful of units is a sample-size
# artefact rather than a statement about the process.
SMALL_LOT_THRESHOLD = 20
SMALL_LOT_ACCEPT_NUMBER = 1

# Percentages are quotients that land exactly on a stated limit for the cases
# that matter most. Comparisons absorb representation error here rather than by
# relaxing the limit itself.
LIMIT_TOLERANCE = 1e-9


def _clean_token(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = value.strip().lower().replace("_", "-").replace(" ", "-")
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _require_int(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _require_percent(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value < 0.0 or value > 100.0:
        raise ValueError("%s must lie between 0 and 100, got %r" % (label, value))
    return value


def percent_defective(failures, units_entering):
    """Return the percentage of units entering a stage that failed it."""
    units = _require_int(units_entering, "units_entering", minimum=1)
    failed = _require_int(failures, "failures", minimum=0)
    if failed > units:
        raise ValueError(
            "failures (%d) cannot exceed units entering the stage (%d)" % (failed, units)
        )
    return 100.0 * failed / units


def accept_number(units_entering, limit_percent):
    """Return the largest failure count that stays inside the stage limit.

    A limit of zero allows no failures whatever the population, and a small lot
    is graded on the absolute accept number rather than on a percentage.
    """
    units = _require_int(units_entering, "units_entering", minimum=1)
    limit = _require_percent(limit_percent, "limit_percent")
    if math.isclose(limit, 0.0, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE):
        return 0
    if units < SMALL_LOT_THRESHOLD:
        return SMALL_LOT_ACCEPT_NUMBER
    return int(math.floor((units * limit) / 100.0 + LIMIT_TOLERANCE))


def exceeds_limit(observed_percent, limit_percent):
    """Return whether an observed percentage is past its limit.

    A value sitting on the limit is inside it. The equality is settled with a
    tolerance rather than by a strict comparison, because the two sides are
    computed differently and need not land on the same float on every host.
    """
    observed = _require_percent(observed_percent, "observed_percent")
    limit = _require_percent(limit_percent, "limit_percent")
    if math.isclose(observed, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE):
        return False
    return observed > limit


def resolve_limits(overrides=None):
    """Return the stage limit table, with any validated procurement overrides."""
    limits = dict(DEFAULT_STAGE_LIMITS)
    if overrides is None:
        return limits
    if not isinstance(overrides, dict):
        raise ValueError("stage_limits must be a mapping of stage to percentage")
    for stage, value in overrides.items():
        token = _clean_token(stage, "stage_limits key")
        limits[token] = _require_percent(value, "stage_limits[%r]" % stage)
    return limits


def validate_stage_records(records):
    """Return the normalised per-stage screening record of a lot.

    Each record names the stage, the units that entered it and the failures
    charged to the lot there. A stage that starts with more units than the
    previous stage passed on is refused: the record does not describe one flow
    of hardware, so nothing computed from it can be trusted.
    """
    if isinstance(records, dict) or not isinstance(records, (list, tuple)):
        raise ValueError("stage records must be a sequence of records")
    if not records:
        raise ValueError("no stage records supplied for the lot")
    normalised = []
    previous_survivors = None
    seen = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("stage records[%d] must be a mapping" % index)
        for key in ("stage", "units_entering", "chargeable_failures"):
            if key not in record:
                raise ValueError("stage records[%d] needs a '%s'" % (index, key))
        stage = _clean_token(record["stage"], "stage records[%d]['stage']" % index)
        if stage in seen:
            raise ValueError("stage %s appears twice in the screening record" % stage)
        seen.add(stage)
        units = _require_int(
            record["units_entering"], "stage records[%d]['units_entering']" % index, minimum=1
        )
        failures = _require_int(
            record["chargeable_failures"],
            "stage records[%d]['chargeable_failures']" % index,
            minimum=0,
        )
        if failures > units:
            raise ValueError(
                "stage %s charges %d failures against %d units entering" % (stage, failures, units)
            )
        if previous_survivors is not None and units > previous_survivors:
            raise ValueError(
                "stage %s starts with %d units but the previous stage passed on %d"
                % (stage, units, previous_survivors)
            )
        previous_survivors = units - failures
        normalised.append(
            {"stage": stage, "units_entering": units, "chargeable_failures": failures}
        )
    return normalised


def cumulative_percent_defective(records):
    """Return the failures charged across the sequence over the units entering it."""
    normalised = validate_stage_records(records)
    entered = normalised[0]["units_entering"]
    charged = sum(item["chargeable_failures"] for item in normalised)
    return 100.0 * charged / entered


def evaluate_stage(record, limits=None):
    """Grade one screening stage against its percentage or accept-number limit."""
    normalised = validate_stage_records([record])[0]
    table = resolve_limits(limits) if isinstance(limits, dict) else dict(DEFAULT_STAGE_LIMITS)
    stage = normalised["stage"]
    if stage not in table:
        raise ValueError("no rejection limit stated for stage %r" % stage)
    limit = table[stage]
    units = normalised["units_entering"]
    failures = normalised["chargeable_failures"]
    observed = percent_defective(failures, units)
    allowed = accept_number(units, limit)
    small_lot = units < SMALL_LOT_THRESHOLD
    if small_lot:
        exceeded = failures > allowed
        criterion = "accept-number"
    else:
        exceeded = exceeds_limit(observed, limit)
        criterion = "percentage"
    return {
        "stage": stage,
        "units_entering": units,
        "chargeable_failures": failures,
        "percent_defective": observed,
        "limit_percent": limit,
        "accept_number": allowed,
        "criterion": criterion,
        "small_lot": small_lot,
        "exceeded": exceeded,
    }


def assess_lot_rejection_criteria(spec):
    """Run the full clause 10.4.2 quantitative rejection assessment.

    spec keys: stage_records, optional stage_limits overrides and optional
    cumulative_limit_percent.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "stage_records" not in spec:
        raise ValueError("spec missing required key 'stage_records'")
    records = validate_stage_records(spec["stage_records"])
    limits = resolve_limits(spec.get("stage_limits"))
    cumulative_limit = _require_percent(
        spec.get("cumulative_limit_percent", CUMULATIVE_LIMIT_PERCENT),
        "cumulative_limit_percent",
    )
    stages = [evaluate_stage(record, limits) for record in records]
    cumulative = cumulative_percent_defective(spec["stage_records"])
    cumulative_exceeded = exceeds_limit(cumulative, cumulative_limit)

    exceeded = []
    for item in stages:
        if item["exceeded"]:
            if item["criterion"] == "accept-number":
                exceeded.append(
                    "%s: %d failures against an accept number of %d on a lot of %d"
                    % (
                        item["stage"],
                        item["chargeable_failures"],
                        item["accept_number"],
                        item["units_entering"],
                    )
                )
            else:
                exceeded.append(
                    "%s: %.4f%% defective against a limit of %.4f%%"
                    % (item["stage"], item["percent_defective"], item["limit_percent"])
                )
    if cumulative_exceeded:
        exceeded.append(
            "cumulative: %.4f%% defective against a limit of %.4f%%"
            % (cumulative, cumulative_limit)
        )
    small_lot_stages = [item["stage"] for item in stages if item["small_lot"]]
    findings = []
    if small_lot_stages:
        findings.append(
            "accept-number criterion applied below %d units at: %s"
            % (SMALL_LOT_THRESHOLD, ", ".join(small_lot_stages))
        )
    return {
        "stages": stages,
        "units_entering_screening": records[0]["units_entering"],
        "total_chargeable_failures": sum(r["chargeable_failures"] for r in records),
        "cumulative_percent_defective": cumulative,
        "cumulative_limit_percent": cumulative_limit,
        "cumulative_exceeded": cumulative_exceeded,
        "exceeded_limits": exceeded,
        "findings": findings,
        "verdict": "reject" if exceeded else "accept",
        "rejected": bool(exceeded),
    }
