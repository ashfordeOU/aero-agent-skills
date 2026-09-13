#!/usr/bin/env python3
"""Multipactor-free declaration up to the drive level actually applied.

Anchor: ECSS-E-ST-20-01C clause 8.5.2 (conditions under which equipment may
be declared free of multipactor up to the level reached during the run).
Paraphrased into an implementable procedure; no standard text is reproduced.

Deterministic, offline, Python standard library only.
"""

import math

# Vacuum condition that must be held for a multipactor run to demonstrate
# anything about secondary-electron-multiplication (Pa).
VACUUM_LIMIT_PA = 1.0e-4

# Detection-method families. A run must be watched by at least one of each.
GLOBAL_METHODS = frozenset(
    {"forward-reflected-comparison", "harmonic-detection", "nulling-detection"}
)
LOCAL_METHODS = frozenset(
    {"electron-probe", "optical-detection", "charged-particle-collection"}
)
MIN_DETECTION_METHODS = 2

# Recognised electron-seeding sources.
SEEDING_SOURCES = frozenset(
    {"radioactive-source", "electron-gun", "ultraviolet-illumination"}
)

# Fraction of the lowest recorded onset that the declaration may name when an
# observation exists: strictly below the onset, by a defined step-back.
ONSET_STEP_BACK = 0.99

# Representation tolerance. It absorbs floating-point error at an inclusive
# limit; it never relaxes the engineering margin itself.
REL_TOL = 1e-12
ABS_TOL = 1e-15


def _positive_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _finite_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _at_or_above(value, limit):
    """Inclusive comparison that absorbs floating-point representation error."""
    return value > limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def db_to_ratio(margin_db):
    """Convert a decibel margin on a power quantity to a linear ratio."""
    margin = _finite_float(margin_db, "margin_db")
    if margin < 0.0:
        raise ValueError("margin_db must be >= 0, got %r" % (margin_db,))
    return 10.0 ** (margin / 10.0)


def ratio_to_db(ratio):
    """Convert a linear power ratio to decibels."""
    value = _positive_float(ratio, "ratio")
    return 10.0 * math.log10(value)


def required_drive_level_w(max_operating_power_w, margin_db):
    """Drive level the run must reach: operating level raised by the margin."""
    base = _positive_float(max_operating_power_w, "max_operating_power_w")
    return base * db_to_ratio(margin_db)


def qualified_operating_level_w(declared_free_level_w, margin_db):
    """Operating level the declaration supports once the margin is released."""
    declared = _positive_float(declared_free_level_w, "declared_free_level_w")
    return declared / db_to_ratio(margin_db)


def scan_run_log(run_log):
    """Return the highest quiet drive level and the lowest recorded onset."""
    if not isinstance(run_log, (list, tuple)) or not run_log:
        raise ValueError("run_log must be a non-empty list of drive-level entries")
    highest_quiet = None
    lowest_onset = None
    for i, entry in enumerate(run_log):
        if not isinstance(entry, dict):
            raise ValueError("run_log[%d] must be a mapping, got %r" % (i, entry))
        level = _positive_float(entry.get("level_w"), "run_log[%d].level_w" % i)
        observed = entry.get("multipactor_observed")
        if not isinstance(observed, bool):
            raise ValueError(
                "run_log[%d].multipactor_observed must be a boolean, got %r"
                % (i, observed)
            )
        if observed:
            if lowest_onset is None or level < lowest_onset:
                lowest_onset = level
        else:
            if highest_quiet is None or level > highest_quiet:
                highest_quiet = level
    return {"highest_quiet_level_w": highest_quiet, "lowest_onset_level_w": lowest_onset}


def check_detection_capability(methods):
    """Findings against the detection-capability prerequisite."""
    if not isinstance(methods, (list, tuple)):
        raise ValueError("detection methods must be a list")
    findings = []
    if len(methods) < MIN_DETECTION_METHODS:
        findings.append(
            "detection-capability carries %d method(s); at least %d are required"
            % (len(methods), MIN_DETECTION_METHODS)
        )
    families = set()
    for i, method in enumerate(methods):
        if not isinstance(method, dict):
            raise ValueError("detection method[%d] must be a mapping" % i)
        name = method.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("detection method[%d] needs a non-empty name" % i)
        if name in GLOBAL_METHODS:
            families.add("global")
        elif name in LOCAL_METHODS:
            families.add("local")
        else:
            raise ValueError("detection method %r is not a recognised method" % (name,))
        for flag in ("sensitivity_verified", "calibration_in_date"):
            value = method.get(flag)
            if not isinstance(value, bool):
                raise ValueError(
                    "detection method %s: %s must be a boolean, got %r"
                    % (name, flag, value)
                )
            if not value:
                findings.append("detection method %s: %s is not satisfied" % (name, flag))
    if "global" not in families:
        findings.append("no global-detection-method in the detection-capability")
    if "local" not in families:
        findings.append("no local-detection-method in the detection-capability")
    return findings


def check_seeding(seeding):
    """Findings against the electron-seeding prerequisite."""
    if not isinstance(seeding, dict):
        raise ValueError("seeding must be a mapping")
    source = seeding.get("source")
    if not isinstance(source, str) or source not in SEEDING_SOURCES:
        raise ValueError(
            "seeding source %r is not a recognised source; expected one of %s"
            % (source, ", ".join(sorted(SEEDING_SOURCES)))
        )
    findings = []
    for flag in ("active", "effectiveness_verified"):
        value = seeding.get(flag)
        if not isinstance(value, bool):
            raise ValueError("seeding %s must be a boolean, got %r" % (flag, value))
        if not value:
            findings.append("electron-seeding: %s is not satisfied" % flag)
    return findings


def check_environment(environment):
    """Findings against the vacuum-condition and temperature-envelope."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    pressure = _positive_float(environment.get("pressure_pa"), "environment.pressure_pa")
    run_min = _finite_float(environment.get("run_temp_min_c"), "run_temp_min_c")
    run_max = _finite_float(environment.get("run_temp_max_c"), "run_temp_max_c")
    op_min = _finite_float(environment.get("operating_temp_min_c"), "operating_temp_min_c")
    op_max = _finite_float(environment.get("operating_temp_max_c"), "operating_temp_max_c")
    if run_min > run_max:
        raise ValueError("run_temp_min_c must not exceed run_temp_max_c")
    if op_min > op_max:
        raise ValueError("operating_temp_min_c must not exceed operating_temp_max_c")
    findings = []
    if not (
        pressure < VACUUM_LIMIT_PA
        or math.isclose(pressure, VACUUM_LIMIT_PA, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    ):
        findings.append(
            "vacuum-condition %.3e Pa is above the declared limit %.3e Pa"
            % (pressure, VACUUM_LIMIT_PA)
        )
    if run_min > op_min and not math.isclose(
        run_min, op_min, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        findings.append(
            "temperature-envelope does not reach the operational cold corner "
            "(%.2f C vs %.2f C)" % (run_min, op_min)
        )
    if run_max < op_max and not math.isclose(
        run_max, op_max, rel_tol=REL_TOL, abs_tol=ABS_TOL
    ):
        findings.append(
            "temperature-envelope does not reach the operational hot corner "
            "(%.2f C vs %.2f C)" % (run_max, op_max)
        )
    return findings


def declared_free_level_w(scan):
    """Level the declaration may name, capped strictly below any onset."""
    if not isinstance(scan, dict):
        raise ValueError("scan must be the mapping returned by scan_run_log")
    quiet = scan.get("highest_quiet_level_w")
    onset = scan.get("lowest_onset_level_w")
    if quiet is None:
        return None
    quiet = _positive_float(quiet, "highest_quiet_level_w")
    if onset is None:
        return quiet
    onset = _positive_float(onset, "lowest_onset_level_w")
    capped = onset * ONSET_STEP_BACK
    return min(quiet, capped)


def evaluate_declaration(record):
    """Decide whether the clause 8.5.2 declaration is supported, and at what level."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    margin_db = _finite_float(record.get("margin_db"), "margin_db")
    required = required_drive_level_w(record.get("max_operating_power_w"), margin_db)
    scan = scan_run_log(record.get("run_log"))
    findings = []
    findings.extend(check_detection_capability(record.get("detection_methods")))
    findings.extend(check_seeding(record.get("seeding")))
    findings.extend(check_environment(record.get("environment")))
    declared = declared_free_level_w(scan)
    if declared is None:
        findings.append("no quiet drive level on record; nothing can be declared")
    elif not _at_or_above(declared, required):
        findings.append(
            "declarable level %.4f W does not reach the required %.4f W "
            "(maximum-operating-power plus %.2f dB)" % (declared, required, margin_db)
        )
    if scan["lowest_onset_level_w"] is not None:
        findings.append(
            "multipactor onset recorded at %.4f W; declaration capped below it"
            % scan["lowest_onset_level_w"]
        )
    qualified = (
        qualified_operating_level_w(declared, margin_db) if declared is not None else None
    )
    return {
        "required_drive_level_w": required,
        "highest_quiet_level_w": scan["highest_quiet_level_w"],
        "lowest_onset_level_w": scan["lowest_onset_level_w"],
        "declared_free_level_w": declared,
        "qualified_operating_level_w": qualified,
        "findings": findings,
        "declarable": not findings,
    }
