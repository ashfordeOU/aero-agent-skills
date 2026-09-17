"""Lot acceptance of retinned electronic parts.

Anchor: ECSS-Q-ST-60C clause 8 (evaluating parts whose terminations have been
re-tinned, the sample the evaluation is drawn on, and the criteria the lot is
accepted against). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Size the inspection sample from the lot size. A very small lot is
   inspected in full because a fractional sample of it carries no confidence;
   everything larger takes a fraction with a floor and a ceiling.
2. Set an accept number per attribute. Critical and destructive attributes
   accept on zero — one reject is the lot. Cosmetic attributes take a small
   accept number scaled to the sample actually drawn.
3. Bound the thermal exposure the retinning put through the part: the dip
   temperature against the part's own declared limit, the dwell of a single
   dip, the number of dips and the total time at temperature.
4. Confirm the finish left behind is genuinely lead bearing. A retin that
   does not move the composition past the pure tin threshold has not removed
   the whisker hazard it was performed to remove.
5. Require the retinning process itself to be qualified. An unqualified
   process makes every measurement above an observation rather than evidence.
6. Combine the attribute outcomes and the process findings into one verdict:
   the lot is accepted, the lot can be recovered by screening every part, or
   the lot is rejected.

Sample sizing is done in whole numbers throughout. A percentage applied as a
float lands on either side of a round sample count depending on the host, so
the fraction is carried as an integer percent and rounded up exactly.
"""

import math

__all__ = [
    "FULL_INSPECTION_LOT_SIZE",
    "SAMPLE_PERCENT",
    "MIN_SAMPLE_SIZE",
    "MAX_SAMPLE_SIZE",
    "COSMETIC_ACCEPT_PERCENT",
    "ATTRIBUTES",
    "MAX_DIP_DWELL_S",
    "MAX_DIP_COUNT",
    "MAX_TOTAL_DWELL_S",
    "MIN_RESIDUAL_LEAD_PERCENT",
    "PROCESS_TOLERANCE",
    "VERDICTS",
    "normalize_token",
    "validate_attribute",
    "retin_sample_size",
    "accept_number",
    "evaluate_attribute_result",
    "evaluate_attribute_results",
    "total_dwell_seconds",
    "thermal_exposure_findings",
    "residual_finish_is_lead_bearing",
    "validate_process",
    "assess_retinned_lot",
]

# A lot no larger than this is inspected part by part; a fraction of it would
# be one or two pieces and carries no confidence.
FULL_INSPECTION_LOT_SIZE = 8

# The sample fraction, carried as an integer percent so the rounding is exact
# on every host rather than landing either side of a round count.
SAMPLE_PERCENT = 10

# Floor and ceiling on the drawn sample.
MIN_SAMPLE_SIZE = 5
MAX_SAMPLE_SIZE = 50

# Accept number for a cosmetic attribute, as an integer percent of the sample.
COSMETIC_ACCEPT_PERCENT = 4

# The attributes a retinned lot is evaluated on. An attribute that is
# critical or destructive accepts on zero.
ATTRIBUTES = {
    "retinned-lead-solderability": {"critical": True, "destructive": False},
    "retinned-lead-terminal-strength": {"critical": True, "destructive": True},
    "retinned-part-hermeticity": {"critical": True, "destructive": False},
    "retinned-part-electrical-verification": {"critical": True, "destructive": False},
    "retinned-part-internal-visual-examination": {
        "critical": True,
        "destructive": True,
    },
    "retinned-finish-visual-inspection": {"critical": False, "destructive": False},
    "retinned-lead-coplanarity-check": {"critical": False, "destructive": False},
    "retinned-lead-dimensional-check": {"critical": False, "destructive": False},
}

# Thermal exposure bounds on the retinning operation itself.
MAX_DIP_DWELL_S = 5.0
MAX_DIP_COUNT = 2
MAX_TOTAL_DWELL_S = 8.0

# The finish left behind has to carry at least this much lead by mass, or the
# retin has not taken the part out of pure tin.
MIN_RESIDUAL_LEAD_PERCENT = 3.0

# Temperatures and dwells are compared as floats; a process sitting exactly
# on a limit must not be rejected on representation alone.
PROCESS_TOLERANCE = 1e-9

VERDICTS = ("lot-accepted", "screening-required", "lot-rejected")


def _require_text(value, label):
    """Return a non-blank text field, raising on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _positive_int(value, label):
    """Return a strictly positive whole count."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return value


def _non_negative_int(value, label):
    """Return a whole count that may be zero but never negative."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _positive_number(value, label):
    """Return a strictly positive real quantity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _percent(value, label):
    """Return a percentage by mass in the closed range zero to one hundred."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0 or number > 100.0:
        raise ValueError(
            "%s must lie between zero and one hundred, got %r" % (label, value)
        )
    return number


def _flag(value, label):
    """Return a strict boolean flag."""
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def normalize_token(value, label="token"):
    """Return a normalized lower-case hyphenated token."""
    text = _require_text(value, label)
    return "-".join(text.lower().replace("_", " ").replace("-", " ").split())


def validate_attribute(value):
    """Return a recognized evaluation attribute token."""
    token = normalize_token(value, "attribute")
    if token not in ATTRIBUTES:
        raise ValueError(
            "attribute '%s' is not a retinning evaluation attribute; expected "
            "one of %s" % (token, ", ".join(sorted(ATTRIBUTES)))
        )
    return token


def _at_or_below(value, limit):
    """Return whether a value meets a limit, tolerant at the boundary."""
    return value < limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=PROCESS_TOLERANCE
    )


def _at_or_above(value, floor):
    """Return whether a value meets a floor, tolerant at the boundary."""
    return value > floor or math.isclose(
        value, floor, rel_tol=0.0, abs_tol=PROCESS_TOLERANCE
    )


def retin_sample_size(lot_size):
    """Return the sample drawn from a retinned lot for evaluation.

    Whole-number arithmetic throughout: the fraction is an integer percent
    rounded up, so the answer cannot move between hosts.
    """
    size = _positive_int(lot_size, "lot_size")
    if size <= FULL_INSPECTION_LOT_SIZE:
        return size
    fractional = -(-size * SAMPLE_PERCENT // 100)
    sample = max(MIN_SAMPLE_SIZE, fractional)
    sample = min(sample, MAX_SAMPLE_SIZE)
    return min(sample, size)


def accept_number(attribute, sample_size):
    """Return the number of rejects an attribute tolerates in the sample.

    Critical and destructive attributes accept on zero; one reject is the lot.
    """
    token = validate_attribute(attribute)
    sample = _positive_int(sample_size, "sample_size")
    spec = ATTRIBUTES[token]
    if spec["critical"] or spec["destructive"]:
        return 0
    return sample * COSMETIC_ACCEPT_PERCENT // 100


def evaluate_attribute_result(attribute, rejects, sample_size):
    """Return the outcome of one attribute against its accept number."""
    token = validate_attribute(attribute)
    sample = _positive_int(sample_size, "sample_size")
    count = _non_negative_int(rejects, "rejects")
    if count > sample:
        raise ValueError(
            "rejects (%d) cannot exceed the sample drawn (%d)" % (count, sample)
        )
    allowed = accept_number(token, sample)
    spec = ATTRIBUTES[token]
    return {
        "attribute": token,
        "rejects": count,
        "accept_number": allowed,
        "sample_size": sample,
        "critical": spec["critical"],
        "destructive": spec["destructive"],
        "accepted": count <= allowed,
    }


def evaluate_attribute_results(results, sample_size):
    """Return the outcome of every submitted attribute, rejecting duplicates."""
    if not isinstance(results, (list, tuple)):
        raise ValueError("results must be a list")
    if not results:
        raise ValueError("results must name at least one attribute")
    evaluated = {}
    for entry in results:
        if not isinstance(entry, dict):
            raise ValueError("each result must be a mapping")
        for key in ("attribute", "rejects"):
            if key not in entry:
                raise ValueError("result missing required key '%s'" % key)
        item = evaluate_attribute_result(
            entry["attribute"], entry["rejects"], sample_size
        )
        if item["attribute"] in evaluated:
            raise ValueError(
                "attribute '%s' reported more than once" % item["attribute"]
            )
        evaluated[item["attribute"]] = item
    return evaluated


def total_dwell_seconds(dwell_seconds, dip_count):
    """Return the total time the part spent at solder temperature."""
    dwell = _positive_number(dwell_seconds, "dwell_seconds")
    dips = _positive_int(dip_count, "dip_count")
    return dwell * dips


def validate_process(process):
    """Return one validated description of the retinning operation."""
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping")
    for key in (
        "dip_temperature_c",
        "dwell_seconds",
        "dip_count",
        "part_max_process_temperature_c",
        "resulting_lead_mass_percent",
    ):
        if key not in process:
            raise ValueError("process missing required key '%s'" % key)
    return {
        "dip_temperature_c": _positive_number(
            process["dip_temperature_c"], "dip_temperature_c"
        ),
        "dwell_seconds": _positive_number(process["dwell_seconds"], "dwell_seconds"),
        "dip_count": _positive_int(process["dip_count"], "dip_count"),
        "part_max_process_temperature_c": _positive_number(
            process["part_max_process_temperature_c"],
            "part_max_process_temperature_c",
        ),
        "resulting_lead_mass_percent": _percent(
            process["resulting_lead_mass_percent"], "resulting_lead_mass_percent"
        ),
    }


def thermal_exposure_findings(process):
    """Return every way the retinning operation exceeded its bounds, sorted."""
    entry = process if "dip_temperature_c" in process else {}
    if not entry:
        raise ValueError("process must be a validated process mapping")
    findings = []
    if not _at_or_below(
        entry["dip_temperature_c"], entry["part_max_process_temperature_c"]
    ):
        findings.append("dip-temperature-above-the-part-limit")
    if not _at_or_below(entry["dwell_seconds"], MAX_DIP_DWELL_S):
        findings.append("single-dip-dwell-above-the-limit")
    if entry["dip_count"] > MAX_DIP_COUNT:
        findings.append("more-dips-than-permitted")
    total = total_dwell_seconds(entry["dwell_seconds"], entry["dip_count"])
    if not _at_or_below(total, MAX_TOTAL_DWELL_S):
        findings.append("total-time-at-solder-temperature-above-the-limit")
    return sorted(findings)


def residual_finish_is_lead_bearing(lead_mass_percent):
    """Return whether the finish left behind carries enough lead to count."""
    lead = _percent(lead_mass_percent, "resulting_lead_mass_percent")
    return _at_or_above(lead, MIN_RESIDUAL_LEAD_PERCENT)


def assess_retinned_lot(lot):
    """Judge one retinned lot against the clause 8 acceptance conditions.

    lot keys: lot_id, lot_size, process, results, and optionally
    process_qualified.
    """
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping")
    for key in ("lot_id", "lot_size", "process", "results"):
        if key not in lot:
            raise ValueError("lot missing required key '%s'" % key)

    lot_id = _require_text(lot["lot_id"], "lot_id")
    lot_size = _positive_int(lot["lot_size"], "lot_size")
    qualified = _flag(lot.get("process_qualified", True), "process_qualified")
    process = validate_process(lot["process"])
    sample = retin_sample_size(lot_size)
    evaluated = evaluate_attribute_results(lot["results"], sample)

    thermal = thermal_exposure_findings(process)
    lead_bearing = residual_finish_is_lead_bearing(
        process["resulting_lead_mass_percent"]
    )

    critical_failures = sorted(
        token
        for token, item in evaluated.items()
        if not item["accepted"] and (item["critical"] or item["destructive"])
    )
    cosmetic_failures = sorted(
        token
        for token, item in evaluated.items()
        if not item["accepted"] and not (item["critical"] or item["destructive"])
    )

    blocking = bool(critical_failures) or bool(thermal) or not lead_bearing
    blocking = blocking or not qualified

    if blocking:
        verdict = "lot-rejected"
    elif cosmetic_failures:
        verdict = "screening-required"
    else:
        verdict = "lot-accepted"

    findings = []
    if not qualified:
        findings.append(
            "the retinning process behind lot '%s' is not qualified" % lot_id
        )
    for token in critical_failures:
        item = evaluated[token]
        findings.append(
            "lot '%s' failed the accept-on-zero attribute '%s' with %d reject(s) "
            "in a sample of %d" % (lot_id, token, item["rejects"], sample)
        )
    for token in cosmetic_failures:
        item = evaluated[token]
        findings.append(
            "lot '%s' exceeded the accept number on '%s' with %d reject(s) "
            "against %d permitted" % (lot_id, token, item["rejects"], item["accept_number"])
        )
    for token in thermal:
        findings.append("the retinning of lot '%s' shows %s" % (lot_id, token))
    if not lead_bearing:
        findings.append(
            "the finish on lot '%s' carries %.2f percent lead, below the %.2f "
            "that takes it out of pure tin"
            % (lot_id, process["resulting_lead_mass_percent"], MIN_RESIDUAL_LEAD_PERCENT)
        )

    return {
        "lot_id": lot_id,
        "lot_size": lot_size,
        "sample_size": sample,
        "full_inspection": sample == lot_size,
        "process": process,
        "process_qualified": qualified,
        "attributes": evaluated,
        "critical_failures": critical_failures,
        "cosmetic_failures": cosmetic_failures,
        "thermal_findings": thermal,
        "residual_finish_is_lead_bearing": lead_bearing,
        "total_dwell_seconds": total_dwell_seconds(
            process["dwell_seconds"], process["dip_count"]
        ),
        "verdict": verdict,
        "acceptable_as_evaluated": verdict == "lot-accepted",
        "findings": findings,
    }
