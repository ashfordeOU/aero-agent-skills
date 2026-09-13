#!/usr/bin/env python3
"""Emission-yield sample handling and storage (ECSS-E-ST-20-01C clause 9.4.1.1).

Deterministic, offline, stdlib-only logic that audits the custody chain of a
secondary-electron-emission-yield coupon - containment, storage environment,
weighted ambient-air exposure, handling steps and the transport leg - and
returns a three-valued admissibility verdict for the measurement run.

Paraphrased procedure only; the standard and clause are cited as the anchor.
"""

from datetime import date

import math

# --- Containment -----------------------------------------------------------
# Each container carries its own storage-life limit and says whether it needs
# an active purge-gas and whether it stops ambient air reaching the surface.
CONTAINERS = {
    "vacuum-desiccator": {"storage_life_days": 365, "needs_purge_gas": False,
                          "stops_ambient_air": True, "relies_on_seal": True},
    "purge-gas-container": {"storage_life_days": 180, "needs_purge_gas": True,
                            "stops_ambient_air": True, "relies_on_seal": True},
    "sealed-double-bag": {"storage_life_days": 90, "needs_purge_gas": False,
                          "stops_ambient_air": False, "relies_on_seal": True},
    "vented-transit-case": {"storage_life_days": 7, "needs_purge_gas": False,
                            "stops_ambient_air": False, "relies_on_seal": False},
}

# Weighting applied to time spent in each custody environment.
ENVIRONMENT_WEIGHTS = {
    "vacuum-chamber": 0.0,
    "purge-gas": 0.0,
    "cleanroom-air": 1.0,
    "uncontrolled-air": 3.0,
}

APPROVED_GLOVES = ("powder-free-nitrile", "cleanroom-vinyl", "lint-free-cotton-liner")
APPROVED_TOOL_MATERIALS = ("ptfe-tipped-tweezers", "stainless-tweezers",
                           "anodised-aluminium-fixture")

# --- Allowances ------------------------------------------------------------
MAX_WEIGHTED_EXPOSURE_HOURS = 24.0
MAX_RELATIVE_HUMIDITY_PCT = 45.0
STORAGE_TEMPERATURE_BAND_C = (15.0, 30.0)
MAX_TRANSIT_HOURS = 72.0

REL_TOL = 1e-9
ABS_TOL = 1e-9

VERDICT_ADMISSIBLE = "admissible"
VERDICT_RECLEAN = "re-cleaning-required"
VERDICT_WITHDRAWN = "withdrawn"

SEVERITY_NOTE = "note"
SEVERITY_RECLEAN = "re-clean"
SEVERITY_WITHDRAW = "withdraw"


def _close(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def within_limit(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or _close(value, limit)


def meets_or_exceeds(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or _close(value, limit)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _finding(severity, message):
    return {"severity": severity, "message": message}


def parse_iso_date(text, label="date"):
    """Parse a YYYY-MM-DD date without touching the network or the clock."""
    if isinstance(text, date):
        return text
    if not isinstance(text, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, text))
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("%s must be formatted YYYY-MM-DD, got %r" % (label, text))
    try:
        year, month, day = (int(p) for p in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError("%s is not a valid calendar date (%r): %s" % (label, text, exc))


def storage_age_days(prepared_on, run_on):
    """Whole days between surface preparation and the measurement run."""
    prepared = parse_iso_date(prepared_on, "prepared_on")
    run = parse_iso_date(run_on, "run_on")
    age = (run - prepared).days
    if age < 0:
        raise ValueError("preparation date %s is after the run date %s"
                         % (prepared.isoformat(), run.isoformat()))
    return age


# --- Coupon record ---------------------------------------------------------
def validate_coupon_record(record):
    """Validate the coupon identity block and return a normalised copy."""
    if not isinstance(record, dict):
        raise ValueError("coupon record must be a mapping")
    normalised = {}
    for key in ("coupon_id", "material", "cleanliness_level", "container",
                "prepared_on"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("coupon record needs a non-empty %r" % (key,))
        normalised[key] = value.strip()
    if normalised["container"] not in CONTAINERS:
        raise ValueError("unrecognised container %r; expected one of %s"
                         % (normalised["container"], ", ".join(sorted(CONTAINERS))))
    parse_iso_date(normalised["prepared_on"], "prepared_on")
    dielectric = record.get("dielectric", False)
    if not isinstance(dielectric, bool):
        raise ValueError("dielectric must be a boolean")
    normalised["dielectric"] = dielectric
    return normalised


def container_profile(container):
    """Return the containment profile for a container type."""
    if container not in CONTAINERS:
        raise ValueError("unrecognised container %r" % (container,))
    return dict(CONTAINERS[container])


# --- Storage environment ---------------------------------------------------
def check_storage_environment(container, environment, storage_days):
    """Check purge-gas, humidity, temperature and storage life against limits."""
    profile = container_profile(container)
    if not isinstance(environment, dict):
        raise ValueError("storage environment must be a mapping")
    days = _require_number(storage_days, "storage_days")
    if days < 0.0:
        raise ValueError("storage_days must not be negative")
    findings = []
    purge = environment.get("purge_gas")
    if profile["needs_purge_gas"]:
        if not isinstance(purge, str) or not purge.strip():
            findings.append(_finding(SEVERITY_WITHDRAW,
                                     "container %s requires an active purge-gas and "
                                     "none is recorded" % container))
    humidity = _require_number(environment.get("relative_humidity_pct"),
                               "relative_humidity_pct")
    if humidity < 0.0 or humidity > 100.0:
        raise ValueError("relative_humidity_pct must lie between 0 and 100")
    if not within_limit(humidity, MAX_RELATIVE_HUMIDITY_PCT):
        findings.append(_finding(SEVERITY_RECLEAN,
                                 "relative-humidity %.3g%% exceeds the %.3g%% "
                                 "allowance" % (humidity, MAX_RELATIVE_HUMIDITY_PCT)))
    temperature = _require_number(environment.get("temperature_c"), "temperature_c")
    low, high = STORAGE_TEMPERATURE_BAND_C
    if not meets_or_exceeds(temperature, low) or not within_limit(temperature, high):
        findings.append(_finding(SEVERITY_RECLEAN,
                                 "storage temperature %.3g C outside the %.3g-%.3g C "
                                 "band" % (temperature, low, high)))
    if not within_limit(days, float(profile["storage_life_days"])):
        findings.append(_finding(SEVERITY_RECLEAN,
                                 "storage age %.4g days exceeds the %d day "
                                 "storage-life of %s"
                                 % (days, profile["storage_life_days"], container)))
    return findings


# --- Weighted ambient-air exposure ----------------------------------------
def environment_weight(environment_name):
    """Weighting applied to one hour spent in a custody environment."""
    if environment_name not in ENVIRONMENT_WEIGHTS:
        raise ValueError("unrecognised custody environment %r; expected one of %s"
                         % (environment_name, ", ".join(sorted(ENVIRONMENT_WEIGHTS))))
    return ENVIRONMENT_WEIGHTS[environment_name]


def weighted_air_exposure(events):
    """Accumulate weighted ambient-air exposure across the custody events."""
    if not isinstance(events, (list, tuple)):
        raise ValueError("custody events must be a list")
    total = 0.0
    breakdown = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError("custody event %d must be a mapping" % index)
        activity = event.get("activity")
        if not isinstance(activity, str) or not activity.strip():
            raise ValueError("custody event %d needs a non-empty activity" % index)
        hours = _require_number(event.get("duration_hours"),
                                "custody event %d duration_hours" % index)
        if hours < 0.0:
            raise ValueError("custody event %d duration_hours must not be negative"
                             % index)
        weight = environment_weight(event.get("environment"))
        contribution = hours * weight
        total += contribution
        breakdown.append({"activity": activity.strip(),
                          "environment": event["environment"],
                          "duration_hours": hours,
                          "weighted_hours": contribution})
    return {"weighted_hours": total, "breakdown": breakdown}


def check_exposure(total_weighted_hours, allowance=MAX_WEIGHTED_EXPOSURE_HOURS):
    """Compare the weighted exposure total against its allowance."""
    total = _require_number(total_weighted_hours, "total_weighted_hours")
    limit = _require_number(allowance, "allowance")
    if total < 0.0:
        raise ValueError("total_weighted_hours must not be negative")
    if limit <= 0.0:
        raise ValueError("allowance must be positive")
    if within_limit(total, limit):
        return []
    return [_finding(SEVERITY_RECLEAN,
                     "weighted ambient-air exposure %.4g h exceeds the %.4g h "
                     "allowance" % (total, limit))]


# --- Handling steps --------------------------------------------------------
def audit_handling_steps(steps, dielectric=False):
    """Audit glove-type, tool-material and electrostatic-discharge control."""
    if not isinstance(steps, (list, tuple)) or not steps:
        raise ValueError("at least one handling step is required")
    if not isinstance(dielectric, bool):
        raise ValueError("dielectric must be a boolean")
    findings = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("handling step %d must be a mapping" % index)
        name = step.get("step")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("handling step %d needs a non-empty step name" % index)
        name = name.strip()
        gloves = step.get("gloves")
        if gloves is None:
            raise ValueError("handling step %r does not record a glove-type" % name)
        if gloves == "bare-hand":
            findings.append(_finding(SEVERITY_WITHDRAW,
                                     "bare-hand contact during %s" % name))
        elif gloves not in APPROVED_GLOVES:
            findings.append(_finding(SEVERITY_RECLEAN,
                                     "unapproved glove-type %r during %s"
                                     % (gloves, name)))
        tool = step.get("tool_material")
        if tool is not None and tool not in APPROVED_TOOL_MATERIALS:
            findings.append(_finding(SEVERITY_RECLEAN,
                                     "unapproved tool-material %r during %s"
                                     % (tool, name)))
        esd = step.get("esd_control", False)
        if not isinstance(esd, bool):
            raise ValueError("handling step %r: esd_control must be a boolean" % name)
        if dielectric and not esd:
            findings.append(_finding(SEVERITY_WITHDRAW,
                                     "no electrostatic-discharge control during %s on "
                                     "a dielectric coupon" % name))
    return findings


# --- Transport leg ---------------------------------------------------------
def audit_transport(leg, container):
    """Audit seal integrity, transit duration and shock monitoring."""
    profile = container_profile(container)
    if not isinstance(leg, dict):
        raise ValueError("transport leg must be a mapping")
    findings = []
    seal_intact = leg.get("seal_intact")
    if not isinstance(seal_intact, bool):
        raise ValueError("transport leg needs a boolean seal_intact")
    if profile["relies_on_seal"] and not seal_intact:
        findings.append(_finding(SEVERITY_WITHDRAW,
                                 "seal of %s broken on arrival; the containment "
                                 "argument is void" % container))
    hours = _require_number(leg.get("transit_hours"), "transit_hours")
    if hours < 0.0:
        raise ValueError("transit_hours must not be negative")
    if not within_limit(hours, MAX_TRANSIT_HOURS):
        findings.append(_finding(SEVERITY_RECLEAN,
                                 "transit duration %.4g h exceeds the %.4g h limit"
                                 % (hours, MAX_TRANSIT_HOURS)))
    shock_monitored = leg.get("shock_monitored", False)
    if not isinstance(shock_monitored, bool):
        raise ValueError("shock_monitored must be a boolean")
    if not profile["stops_ambient_air"] and not shock_monitored:
        findings.append(_finding(SEVERITY_NOTE,
                                 "transit in %s was not shock-monitored" % container))
    return findings


# --- Verdict ---------------------------------------------------------------
def verdict_from_findings(findings):
    """Collapse a finding list into the three-valued custody verdict."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a list")
    severities = set()
    for finding in findings:
        if not isinstance(finding, dict) or "severity" not in finding:
            raise ValueError("each finding must be a mapping carrying 'severity'")
        severity = finding["severity"]
        if severity not in (SEVERITY_NOTE, SEVERITY_RECLEAN, SEVERITY_WITHDRAW):
            raise ValueError("unrecognised finding severity %r" % (severity,))
        severities.add(severity)
    if SEVERITY_WITHDRAW in severities:
        return VERDICT_WITHDRAWN
    if SEVERITY_RECLEAN in severities:
        return VERDICT_RECLEAN
    return VERDICT_ADMISSIBLE


def assess_sample_custody(coupon, environment, events, handling_steps, transport_leg,
                          run_on, exposure_allowance=MAX_WEIGHTED_EXPOSURE_HOURS):
    """Run the full clause 9.4.1.1 custody audit for one coupon."""
    record = validate_coupon_record(coupon)
    age_days = storage_age_days(record["prepared_on"], run_on)
    exposure = weighted_air_exposure(events)
    findings = []
    findings.extend(check_storage_environment(record["container"], environment,
                                              float(age_days)))
    findings.extend(check_exposure(exposure["weighted_hours"], exposure_allowance))
    findings.extend(audit_handling_steps(handling_steps, record["dielectric"]))
    findings.extend(audit_transport(transport_leg, record["container"]))
    return {"verdict": verdict_from_findings(findings),
            "coupon_id": record["coupon_id"],
            "container": record["container"],
            "storage_age_days": age_days,
            "weighted_exposure_hours": exposure["weighted_hours"],
            "exposure_breakdown": exposure["breakdown"],
            "findings": findings}


def format_custody_report(result):
    """Render a custody audit as reviewable text lines."""
    if not isinstance(result, dict) or "verdict" not in result:
        raise ValueError("result must be a custody audit mapping")
    lines = ["ECSS-E-ST-20-01C clause 9.4.1.1 emission-yield coupon custody audit",
             "coupon %s in %s" % (result["coupon_id"], result["container"]),
             "storage age %d days, weighted ambient-air exposure %.4g h"
             % (result["storage_age_days"], result["weighted_exposure_hours"]),
             "verdict: %s" % result["verdict"]]
    for finding in result["findings"]:
        lines.append("  [%s] %s" % (finding["severity"], finding["message"]))
    if not result["findings"]:
        lines.append("  no custody defect recorded")
    return lines
