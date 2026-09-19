"""Baseline provisions for a wafer level screening campaign.

Anchor: ECSS-Q-ST-60-12C clause 10.2.1 -- general provisions for wafer level
screening. Paraphrased into an implementable procedure; no standard text is
reproduced.

The baseline the clause asks for has three separable parts, and a campaign can
satisfy any two of them while failing the third:

  coverage    -- every wafer of the procured lot is inside the campaign, and
                 every wafer the campaign reports belongs to that lot;
  conditions  -- the screening is run at declared conditions that meet the
                 agreed baseline, with the stress duration and temperature
                 stated rather than implied;
  records     -- each screened wafer carries a record naming who ran it, on
                 what equipment, when, and where the measured data now lives,
                 retained for at least the agreed period.

Coverage is set arithmetic in two directions. A wafer of the lot that no record
covers is an unscreened wafer that will ship on the strength of its neighbours;
a record naming a wafer the lot never contained is a traceability break, and
the two gaps are reported separately because they have different remedies.

Conditions are compared against the baseline with a relative tolerance, so a
soak written to sit exactly on the agreed minimum is accepted on every machine
instead of on the ones whose rounding happens to favour it.

Stdlib only, offline, deterministic.
"""

import math

__all__ = [
    "COMPLIANT",
    "INCOMPLETE",
    "NON_COMPLIANT",
    "REL_TOL",
    "ABSOLUTE_ZERO_C",
    "BASELINE_CONDITION_KEYS",
    "REQUIRED_RECORD_FIELDS",
    "validate_identifier",
    "validate_temperature_c",
    "validate_duration_hours",
    "validate_retention_years",
    "normalize_wafer_ids",
    "meets_minimum",
    "coverage_gap",
    "untraceable_wafers",
    "coverage_fraction",
    "condition_findings",
    "record_findings",
    "retention_shortfall_years",
    "assess_campaign",
]

COMPLIANT = "compliant"
INCOMPLETE = "incomplete"
NON_COMPLIANT = "non-compliant"

# Relative tolerance for every minimum comparison, so a value written to land
# exactly on the agreed bound is accepted rather than decided by rounding.
REL_TOL = 1e-9

ABSOLUTE_ZERO_C = -273.15

# Conditions the campaign has to state before it can be assessed at all.
BASELINE_CONDITION_KEYS = (
    "soak_temperature_c",
    "soak_duration_h",
    "bias_condition",
    "measurement_temperature_c",
)

# What one wafer's screening record has to name to be a record.
REQUIRED_RECORD_FIELDS = (
    "lot_id",
    "operator",
    "equipment_id",
    "start_timestamp",
    "measured_data_reference",
)


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def validate_identifier(value, name="identifier"):
    """Return a stripped non-empty identifier string."""
    if isinstance(value, bool) or not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    token = value.strip()
    if not token:
        raise ValueError("%s must not be blank" % name)
    return token


def validate_temperature_c(value, name="temperature_c"):
    """Return a physically possible temperature in degrees Celsius."""
    temperature = _validate_number(value, name)
    if temperature < ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must not be below absolute zero, got %r" % (name, value)
        )
    return temperature


def validate_duration_hours(value, name="duration_h"):
    """Return a strictly positive stress duration in hours."""
    duration = _validate_number(value, name)
    if duration <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return duration


def validate_retention_years(value, name="retention_years"):
    """Return a non-negative record retention period in years."""
    years = _validate_number(value, name)
    if years < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return years


def normalize_wafer_ids(values, name="wafer_ids"):
    """Return the wafer identifiers as a tuple, refusing a repeat.

    A repeated wafer identifier is an input defect rather than a screening
    finding: silently collapsing it would make a lot of eight wafers with one
    duplicate look like a fully covered lot of seven.
    """
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise ValueError("%s must be a sequence of identifiers" % name)
    out = []
    seen = set()
    for item in values:
        token = validate_identifier(item, "%s entry" % name)
        if token in seen:
            raise ValueError("%s repeats wafer %r" % (name, token))
        seen.add(token)
        out.append(token)
    return tuple(out)


def meets_minimum(value, minimum):
    """Return True where value reaches the minimum, tolerating the bound."""
    observed = _validate_number(value, "value")
    bound = _validate_number(minimum, "minimum")
    scale = max(abs(observed), abs(bound), 1.0)
    return observed >= bound - REL_TOL * scale


def coverage_gap(lot_wafers, screened_wafers):
    """Return the lot wafers no screening record covers, in lot order."""
    lot = normalize_wafer_ids(lot_wafers, "lot_wafers")
    screened = set(normalize_wafer_ids(screened_wafers, "screened_wafers"))
    return tuple(w for w in lot if w not in screened)


def untraceable_wafers(lot_wafers, screened_wafers):
    """Return screened wafers the procured lot never contained."""
    lot = set(normalize_wafer_ids(lot_wafers, "lot_wafers"))
    screened = normalize_wafer_ids(screened_wafers, "screened_wafers")
    return tuple(w for w in screened if w not in lot)


def coverage_fraction(lot_wafers, screened_wafers):
    """Return the share of the lot the campaign actually covers."""
    lot = normalize_wafer_ids(lot_wafers, "lot_wafers")
    if not lot:
        raise ValueError("lot_wafers must name at least one wafer")
    screened = set(normalize_wafer_ids(screened_wafers, "screened_wafers"))
    covered = sum(1 for w in lot if w in screened)
    return covered / float(len(lot))


def condition_findings(declared, baseline):
    """Return the findings against the declared screening conditions."""
    if not isinstance(declared, dict):
        raise ValueError("declared conditions must be a mapping")
    if not isinstance(baseline, dict):
        raise ValueError("baseline must be a mapping")
    findings = []
    for key in BASELINE_CONDITION_KEYS:
        value = declared.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            findings.append("condition %s is not declared" % key)
    if "soak_temperature_c" in declared and declared["soak_temperature_c"] is not None:
        soak_t = validate_temperature_c(declared["soak_temperature_c"], "soak_temperature_c")
        floor_t = baseline.get("min_soak_temperature_c")
        if floor_t is not None:
            floor_t = validate_temperature_c(floor_t, "min_soak_temperature_c")
            if not meets_minimum(soak_t, floor_t):
                findings.append(
                    "soak temperature %.6g C is below the %.6g C baseline"
                    % (soak_t, floor_t)
                )
    if "soak_duration_h" in declared and declared["soak_duration_h"] is not None:
        soak_h = validate_duration_hours(declared["soak_duration_h"], "soak_duration_h")
        floor_h = baseline.get("min_soak_duration_h")
        if floor_h is not None:
            floor_h = validate_duration_hours(floor_h, "min_soak_duration_h")
            if not meets_minimum(soak_h, floor_h):
                findings.append(
                    "soak duration %.6g h is below the %.6g h baseline"
                    % (soak_h, floor_h)
                )
    return tuple(findings)


def record_findings(record, required_fields=REQUIRED_RECORD_FIELDS):
    """Return the required record fields this wafer record does not carry."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    missing = []
    for field in required_fields:
        value = record.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return tuple(missing)


def retention_shortfall_years(retained, required):
    """Return the retention years still owed; zero once the period is met."""
    held = validate_retention_years(retained, "record_retention_years")
    owed = validate_retention_years(required, "required_retention_years")
    if meets_minimum(held, owed):
        return 0.0
    return owed - held


def assess_campaign(campaign):
    """Grade one wafer level screening campaign against the baseline."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    lot_id = validate_identifier(campaign.get("lot_id"), "lot_id")
    lot = normalize_wafer_ids(campaign.get("lot_wafers"), "lot_wafers")
    if not lot:
        raise ValueError("lot_wafers must name at least one wafer")
    screened = normalize_wafer_ids(campaign.get("screened_wafers", ()), "screened_wafers")
    conditions = campaign.get("conditions") or {}
    baseline = campaign.get("baseline") or {}
    records = campaign.get("records") or {}
    if not isinstance(records, dict):
        raise ValueError("records must be a mapping of wafer id to record")
    uncovered = coverage_gap(lot, screened)
    stray = untraceable_wafers(lot, screened)
    conds = condition_findings(conditions, baseline)
    per_wafer = {}
    for wafer in screened:
        record = records.get(wafer)
        if record is None:
            per_wafer[wafer] = ("record absent",)
            continue
        gaps = record_findings(record)
        if gaps:
            per_wafer[wafer] = gaps
    shortfall = retention_shortfall_years(
        campaign.get("record_retention_years", 0.0),
        campaign.get("required_retention_years", 0.0),
    )
    findings = list(conds)
    if uncovered:
        findings.append(
            "%d wafer(s) of lot %s are outside the campaign: %s"
            % (len(uncovered), lot_id, ", ".join(uncovered))
        )
    if stray:
        findings.append(
            "%d screened wafer(s) do not belong to lot %s: %s"
            % (len(stray), lot_id, ", ".join(stray))
        )
    for wafer in sorted(per_wafer):
        findings.append(
            "wafer %s record is short of %s" % (wafer, ", ".join(per_wafer[wafer]))
        )
    if shortfall > 0.0:
        findings.append(
            "record retention is %.6g year(s) short of the agreed period" % shortfall
        )
    if conds:
        verdict = NON_COMPLIANT
    elif uncovered or stray or per_wafer or shortfall > 0.0:
        verdict = INCOMPLETE
    else:
        verdict = COMPLIANT
    return {
        "lot_id": lot_id,
        "lot_size": len(lot),
        "screened_count": len(screened),
        "coverage_fraction": coverage_fraction(lot, screened),
        "uncovered_wafers": uncovered,
        "untraceable_wafers": stray,
        "condition_findings": conds,
        "record_findings": per_wafer,
        "retention_shortfall_years": shortfall,
        "baseline_met": verdict == COMPLIANT,
        "verdict": verdict,
        "findings": tuple(findings),
    }
