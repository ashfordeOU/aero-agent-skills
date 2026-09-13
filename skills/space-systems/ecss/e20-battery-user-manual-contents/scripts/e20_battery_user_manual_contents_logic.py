#!/usr/bin/env python3
"""Battery user manual content check.

Anchor: ECSS-E-ST-20C Annex D (data-requirement fixing the content of the
battery user manual: operation, charging, storage, safety and life data).
Paraphrased into an implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. normalize and check the chapter list against the mandated set;
2. resolve the cell chemistry to its voltage window and storage band;
3. validate the declared operating envelope for self-consistency and scale
   it to the assembly with the series count;
4. check the ground handling and storage regime against the chemistry band;
5. check the charge and discharge control chapter;
6. convert the mission duty profile into a cycle demand and compare the
   declared cycle life and calendar life against it;
7. check safety topic coverage and aggregate a manual-level verdict.
"""

import math

# A value sitting exactly on a declared bound is the design point; the
# comparison absorbs floating-point representation error instead of moving
# the engineering limit.
BOUND_REL_TOL = 1e-9
BOUND_ABS_TOL = 1e-9

REQUIRED_CHAPTERS = (
    "cell-and-battery-identification",
    "operating-envelope",
    "charge-and-discharge-control",
    "ground-handling-and-storage",
    "safety-and-hazard-precautions",
    "life-and-degradation-data",
    "transport-and-shipping",
)

OPTIONAL_CHAPTERS = (
    "electrical-and-mechanical-interface",
    "monitoring-and-telemetry",
    "reconditioning-procedure",
    "disposal-and-passivation",
)

RECOGNIZED_CHAPTERS = REQUIRED_CHAPTERS + OPTIONAL_CHAPTERS

REQUIRED_SAFETY_TOPICS = (
    "thermal-runaway",
    "over-charge-protection",
    "over-discharge-protection",
    "external-short-circuit",
    "cell-venting-and-gas-release",
    "personal-protective-equipment",
)

# chemistry -> usable cell window, storage band and maximum dormancy
CHEMISTRY_DATA = {
    "lithium-ion": {
        "cell_min_v": 2.50,
        "cell_max_v": 4.20,
        "storage_soc_pct": (30.0, 60.0),
        "storage_temp_c": (-10.0, 25.0),
        "max_dormancy_days": 180.0,
    },
    "lithium-ion-high-voltage": {
        "cell_min_v": 2.50,
        "cell_max_v": 4.35,
        "storage_soc_pct": (30.0, 60.0),
        "storage_temp_c": (-10.0, 25.0),
        "max_dormancy_days": 180.0,
    },
    "lithium-iron-phosphate": {
        "cell_min_v": 2.00,
        "cell_max_v": 3.65,
        "storage_soc_pct": (30.0, 60.0),
        "storage_temp_c": (-20.0, 30.0),
        "max_dormancy_days": 365.0,
    },
    "nickel-hydrogen": {
        "cell_min_v": 0.90,
        "cell_max_v": 1.55,
        "storage_soc_pct": (0.0, 20.0),
        "storage_temp_c": (-20.0, 10.0),
        "max_dormancy_days": 90.0,
    },
    "nickel-cadmium": {
        "cell_min_v": 0.90,
        "cell_max_v": 1.50,
        "storage_soc_pct": (0.0, 20.0),
        "storage_temp_c": (-20.0, 10.0),
        "max_dormancy_days": 90.0,
    },
}

CHARGE_MODES = (
    "constant-current-constant-voltage",
    "taper-charge",
    "trickle-charge",
    "pulse-charge",
)

# Above this series count a balancing procedure has to be documented.
BALANCING_SERIES_THRESHOLD = 4

DAYS_PER_YEAR = 365.25


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _at_least(value, bound):
    """True when value >= bound, absorbing representation error at equality."""
    return value > bound or math.isclose(
        value, bound, rel_tol=BOUND_REL_TOL, abs_tol=BOUND_ABS_TOL
    )


def _within(value, low, high):
    """True when low <= value <= high, inclusive at both ends."""
    return _at_least(value, low) and _at_least(high, value)


def normalize_chapter(name):
    """Normalize a chapter heading to its canonical hyphenated token."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("chapter name must be a non-empty string, got %r" % (name,))
    return "-".join(name.strip().lower().replace("_", " ").replace("-", " ").split())


def check_chapter_coverage(chapters):
    """Return the missing mandated chapters and any duplicated heading.

    Raises ValueError on a heading outside the recognized set: an
    uncategorized chapter usually means a mandated one was renamed.
    """
    if not isinstance(chapters, (list, tuple)):
        raise ValueError("chapters must be a list")
    seen = []
    duplicates = []
    for entry in chapters:
        token = normalize_chapter(entry)
        if token not in RECOGNIZED_CHAPTERS:
            raise ValueError("uncategorized manual chapter %r" % (entry,))
        if token in seen:
            duplicates.append(token)
        seen.append(token)
    missing = [c for c in REQUIRED_CHAPTERS if c not in seen]
    return {"missing": missing, "duplicates": sorted(set(duplicates))}


def chemistry_data(chemistry):
    """Resolve a cell chemistry to its window, storage band and dormancy."""
    if not isinstance(chemistry, str) or not chemistry.strip():
        raise ValueError("chemistry must be a non-empty string, got %r" % (chemistry,))
    key = "-".join(chemistry.strip().lower().replace("_", " ").replace("-", " ").split())
    data = CHEMISTRY_DATA.get(key)
    if data is None:
        raise ValueError("uncategorized cell chemistry %r" % (chemistry,))
    return dict(data, chemistry=key)


def validate_operating_envelope(envelope, chemistry):
    """Validate the declared operating envelope and scale it to the assembly.

    Required keys: cells_in_series, min_cell_voltage_v, max_cell_voltage_v,
    charge_termination_voltage_v, min_temperature_c, max_temperature_c.
    """
    if not isinstance(envelope, dict):
        raise ValueError("envelope must be a mapping")
    required = (
        "cells_in_series",
        "min_cell_voltage_v",
        "max_cell_voltage_v",
        "charge_termination_voltage_v",
        "min_temperature_c",
        "max_temperature_c",
    )
    for key in required:
        if key not in envelope:
            raise ValueError("operating envelope is missing required key %r" % (key,))
    series = envelope["cells_in_series"]
    if isinstance(series, bool) or not isinstance(series, int) or series < 1:
        raise ValueError("cells_in_series must be a positive integer, got %r" % (series,))
    v_min = _as_float(envelope["min_cell_voltage_v"], "min_cell_voltage_v")
    v_max = _as_float(envelope["max_cell_voltage_v"], "max_cell_voltage_v")
    v_term = _as_float(
        envelope["charge_termination_voltage_v"], "charge_termination_voltage_v"
    )
    t_min = _as_float(envelope["min_temperature_c"], "min_temperature_c")
    t_max = _as_float(envelope["max_temperature_c"], "max_temperature_c")
    if not v_min < v_max:
        raise ValueError("min_cell_voltage_v must sit below max_cell_voltage_v")
    if not t_min < t_max:
        raise ValueError("min_temperature_c must sit below max_temperature_c")
    data = chemistry_data(chemistry)
    findings = []
    if not _within(v_term, v_min, v_max):
        findings.append("charge-termination-voltage outside the declared envelope")
    if not _within(v_min, data["cell_min_v"], data["cell_max_v"]):
        findings.append("min_cell_voltage_v outside the chemistry window")
    if not _within(v_max, data["cell_min_v"], data["cell_max_v"]):
        findings.append("max_cell_voltage_v outside the chemistry window")
    return {
        "chemistry": data["chemistry"],
        "cells_in_series": series,
        "assembly_min_voltage_v": v_min * series,
        "assembly_max_voltage_v": v_max * series,
        "assembly_termination_voltage_v": v_term * series,
        "temperature_span_c": t_max - t_min,
        "findings": findings,
    }


def check_storage_regime(storage, chemistry):
    """Check the declared ground storage regime against the chemistry band.

    Required keys: state_of_charge_pct, temperature_c, recharge_interval_days.
    """
    if not isinstance(storage, dict):
        raise ValueError("storage must be a mapping")
    for key in ("state_of_charge_pct", "temperature_c", "recharge_interval_days"):
        if key not in storage:
            raise ValueError("storage regime is missing required key %r" % (key,))
    soc = _as_float(storage["state_of_charge_pct"], "state_of_charge_pct")
    temp = _as_float(storage["temperature_c"], "temperature_c")
    interval = _as_float(storage["recharge_interval_days"], "recharge_interval_days")
    if soc < 0.0 or soc > 100.0:
        raise ValueError("state_of_charge_pct must sit in 0-100, got %r" % (soc,))
    if interval <= 0.0:
        raise ValueError("recharge_interval_days must be positive, got %r" % (interval,))
    data = chemistry_data(chemistry)
    findings = []
    soc_low, soc_high = data["storage_soc_pct"]
    if not _within(soc, soc_low, soc_high):
        findings.append("storage state-of-charge outside the chemistry band")
    t_low, t_high = data["storage_temp_c"]
    if not _within(temp, t_low, t_high):
        findings.append("storage temperature outside the chemistry band")
    if not _at_least(data["max_dormancy_days"], interval):
        findings.append("recharge interval exceeds the tolerated dormancy")
    return {"chemistry": data["chemistry"], "findings": findings}


def check_charge_control(control, cells_in_series):
    """Check the charge and discharge control chapter."""
    if not isinstance(control, dict):
        raise ValueError("charge control must be a mapping")
    for key in ("mode", "charge_rate_c", "max_charge_rate_c", "termination_criterion"):
        if key not in control:
            raise ValueError("charge control is missing required key %r" % (key,))
    if isinstance(cells_in_series, bool) or not isinstance(cells_in_series, int):
        raise ValueError("cells_in_series must be an integer")
    mode = control["mode"]
    if mode not in CHARGE_MODES:
        raise ValueError("uncategorized charge mode %r" % (mode,))
    rate = _as_float(control["charge_rate_c"], "charge_rate_c")
    max_rate = _as_float(control["max_charge_rate_c"], "max_charge_rate_c")
    if rate <= 0.0:
        raise ValueError("charge_rate_c must be positive, got %r" % (rate,))
    if max_rate <= 0.0:
        raise ValueError("max_charge_rate_c must be positive, got %r" % (max_rate,))
    criterion = control["termination_criterion"]
    if not isinstance(criterion, str) or not criterion.strip():
        raise ValueError("termination_criterion must be a non-empty string")
    findings = []
    if not _at_least(max_rate, rate):
        findings.append("declared charge rate exceeds the declared maximum")
    if cells_in_series >= BALANCING_SERIES_THRESHOLD and not control.get(
        "cell_balancing_procedure"
    ):
        findings.append("cell-balancing-procedure absent for a series stack")
    return {"mode": mode, "findings": findings}


def required_cycle_count(orbits_per_day, mission_years, eclipse_fraction):
    """Convert a mission duty profile into the cycle count it demands."""
    orbits = _as_float(orbits_per_day, "orbits_per_day")
    years = _as_float(mission_years, "mission_years")
    fraction = _as_float(eclipse_fraction, "eclipse_fraction")
    if orbits <= 0.0:
        raise ValueError("orbits_per_day must be positive, got %r" % (orbits,))
    if years <= 0.0:
        raise ValueError("mission_years must be positive, got %r" % (years,))
    if fraction <= 0.0 or fraction > 1.0:
        raise ValueError("eclipse_fraction must sit in (0, 1], got %r" % (fraction,))
    return orbits * DAYS_PER_YEAR * years * fraction


def check_life_data(life, duty_profile):
    """Compare declared life data against the mission duty profile.

    life keys: cycle_life_cycles, cycle_life_dod_pct, calendar_life_years.
    duty_profile keys: orbits_per_day, mission_years, eclipse_fraction,
    operating_dod_pct, storage_years (optional).
    """
    if not isinstance(life, dict) or not isinstance(duty_profile, dict):
        raise ValueError("life and duty_profile must both be mappings")
    for key in ("cycle_life_cycles", "cycle_life_dod_pct", "calendar_life_years"):
        if key not in life:
            raise ValueError("life data is missing required key %r" % (key,))
    for key in ("orbits_per_day", "mission_years", "eclipse_fraction", "operating_dod_pct"):
        if key not in duty_profile:
            raise ValueError("duty profile is missing required key %r" % (key,))
    declared_cycles = _as_float(life["cycle_life_cycles"], "cycle_life_cycles")
    declared_dod = _as_float(life["cycle_life_dod_pct"], "cycle_life_dod_pct")
    calendar_years = _as_float(life["calendar_life_years"], "calendar_life_years")
    operating_dod = _as_float(duty_profile["operating_dod_pct"], "operating_dod_pct")
    if declared_cycles <= 0.0:
        raise ValueError("cycle_life_cycles must be positive, got %r" % (declared_cycles,))
    if not 0.0 < declared_dod <= 100.0:
        raise ValueError("cycle_life_dod_pct must sit in (0, 100], got %r" % (declared_dod,))
    if not 0.0 < operating_dod <= 100.0:
        raise ValueError("operating_dod_pct must sit in (0, 100], got %r" % (operating_dod,))
    if calendar_years <= 0.0:
        raise ValueError("calendar_life_years must be positive, got %r" % (calendar_years,))
    demanded = required_cycle_count(
        duty_profile["orbits_per_day"],
        duty_profile["mission_years"],
        duty_profile["eclipse_fraction"],
    )
    storage_years = _as_float(duty_profile.get("storage_years", 0.0), "storage_years")
    if storage_years < 0.0:
        raise ValueError("storage_years must be non-negative, got %r" % (storage_years,))
    total_years = _as_float(duty_profile["mission_years"], "mission_years") + storage_years
    findings = []
    if not _at_least(declared_cycles, demanded):
        findings.append("declared cycle-life short of the duty-profile demand")
    if not _at_least(declared_dod, operating_dod):
        findings.append("cycle-life declared at a shallower depth-of-discharge-limit")
    if not _at_least(calendar_years, total_years):
        findings.append("declared calendar-life short of mission plus storage")
    return {
        "demanded_cycles": demanded,
        "declared_cycles": declared_cycles,
        "total_years": total_years,
        "findings": findings,
    }


def check_safety_topics(topics):
    """Return the mandated safety topics that the chapter never covers."""
    if not isinstance(topics, (list, tuple)):
        raise ValueError("safety topics must be a list")
    seen = {normalize_chapter(t) for t in topics}
    return [t for t in REQUIRED_SAFETY_TOPICS if t not in seen]


def assess_manual(manual):
    """Assess a whole battery user manual against the Annex D content set."""
    if not isinstance(manual, dict):
        raise ValueError("manual must be a mapping")
    for key in (
        "chapters",
        "chemistry",
        "operating_envelope",
        "storage",
        "charge_control",
        "life",
        "duty_profile",
        "safety_topics",
    ):
        if key not in manual:
            raise ValueError("manual is missing required key %r" % (key,))
    chemistry = manual["chemistry"]
    coverage = check_chapter_coverage(manual["chapters"])
    envelope = validate_operating_envelope(manual["operating_envelope"], chemistry)
    storage = check_storage_regime(manual["storage"], chemistry)
    control = check_charge_control(manual["charge_control"], envelope["cells_in_series"])
    life = check_life_data(manual["life"], manual["duty_profile"])
    missing_safety = check_safety_topics(manual["safety_topics"])
    findings = []
    if coverage["missing"]:
        findings.append("missing-chapters: " + ", ".join(coverage["missing"]))
    if coverage["duplicates"]:
        findings.append("duplicated-chapters: " + ", ".join(coverage["duplicates"]))
    findings.extend(envelope["findings"])
    findings.extend(storage["findings"])
    findings.extend(control["findings"])
    findings.extend(life["findings"])
    if missing_safety:
        findings.append("missing-safety-topics: " + ", ".join(missing_safety))
    return {
        "coverage": coverage,
        "envelope": envelope,
        "storage": storage,
        "charge_control": control,
        "life": life,
        "missing_safety_topics": missing_safety,
        "findings": findings,
        "compliant": not findings,
    }
