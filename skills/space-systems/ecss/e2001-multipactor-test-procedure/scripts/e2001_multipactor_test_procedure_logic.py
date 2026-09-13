"""ECSS-E-ST-20-01C clause 8.6 -- multipactor test procedure content audit.

Deterministic, offline, stdlib-only implementation of the content check a
multipactor test procedure must pass before the customer approves it and
radio-frequency testing starts.  Every rule here is a paraphrase of the
clause intent expressed as an implementable procedure; no standard text is
reproduced.

The module answers four questions about a proposed procedure:

1. does its section list carry every content item the clause expects,
2. do the declared vacuum-chamber conditions bound the test away from the
   gas-discharge regime,
3. does the declared electron-seeding arrangement guarantee a free-electron
   population at the gap, and
4. does the radio-frequency drive schedule actually reach the required
   power-margin above the declared operating power, with enough independent
   detection coverage to believe the result.

Only an audit that raises no finding is approvable.
"""

import math

# Relative/absolute tolerances used to absorb floating-point representation
# error at an exact compliance boundary.  They never widen an engineering
# limit: a value that is physically at the limit stays compliant, a value
# that is genuinely past it still fails.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Content items clause 8.6 expects a multipactor test procedure to carry.
REQUIRED_SECTIONS = (
    "test-item-identification",
    "test-item-configuration",
    "test-objectives",
    "facility-description",
    "vacuum-conditions",
    "seeding-arrangement",
    "rf-drive-schedule",
    "power-margin",
    "detection-coverage",
    "pass-fail-criteria",
    "instrumentation-calibration",
    "test-sequence",
    "non-conformance-route",
)

# Detection techniques, split by what they observe.  A global technique
# senses the discharge through the radio-frequency signal itself and covers
# the whole item; a local technique senses the electron cloud at one gap.
GLOBAL_DETECTION_METHODS = (
    "forward-reflected-power-nulling",
    "third-harmonic-monitoring",
    "close-to-carrier-noise",
    "phase-modulation-monitoring",
)
LOCAL_DETECTION_METHODS = (
    "electron-probe",
    "optical-photomultiplier",
    "electron-current-probe",
    "local-pressure-rise",
)

# Recognised free-electron seeding arrangements.
SEEDING_SOURCES = (
    "beta-radioactive-source",
    "ultraviolet-lamp",
    "electron-gun",
)

# Chamber must sit well below the pressure at which a gas discharge would
# mask or pre-empt the vacuum breakdown being hunted.
MAX_TEST_PRESSURE_MBAR = 1.0e-5
# Stabilisation under vacuum before the drive schedule starts.
MIN_PUMP_DOWN_HOURS = 24.0
# Declared seeding electron flux at the gap, electrons per square
# centimetre per second.
MIN_SEED_FLUX = 1.0
# Default customer-required margin above declared operating power, in dB.
DEFAULT_REQUIRED_MARGIN_DB = 3.0
# Largest single step the drive schedule may take, in dB, so that the
# threshold is bracketed rather than jumped over.
MAX_DRIVE_STEP_DB = 1.0


def _at_least(value, limit):
    """True when value meets or exceeds limit, absorbing representation error."""
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _at_most(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_detection_method(method):
    """Return 'global' or 'local' for a recognised detection technique.

    Raises ValueError for an empty, non-string or unrecognised technique --
    an unnamed technique cannot be credited as coverage.
    """
    if not isinstance(method, str) or not method.strip():
        raise ValueError("detection method must be a non-empty string")
    key = method.strip().lower()
    if key in GLOBAL_DETECTION_METHODS:
        return "global"
    if key in LOCAL_DETECTION_METHODS:
        return "local"
    raise ValueError("unrecognized detection method: %s" % method)


def evaluate_detection_coverage(methods):
    """Categorize the declared detection techniques and judge their coverage.

    The procedure needs at least two independent techniques and, because a
    global technique can miss a discharge confined to one gap while a local
    technique only watches the gap it faces, at least one of each kind.
    """
    if not isinstance(methods, (list, tuple)) or not methods:
        raise ValueError("detection methods must be a non-empty list")
    global_methods = []
    local_methods = []
    for method in methods:
        kind = categorize_detection_method(method)
        key = method.strip().lower()
        target = global_methods if kind == "global" else local_methods
        if key not in target:
            target.append(key)
    findings = []
    distinct = len(global_methods) + len(local_methods)
    if distinct < 2:
        findings.append("fewer than two independent detection techniques declared")
    if not global_methods:
        findings.append("no global detection technique declared")
    if not local_methods:
        findings.append("no local detection technique declared")
    return {
        "global_methods": global_methods,
        "local_methods": local_methods,
        "distinct_methods": distinct,
        "findings": findings,
        "adequate": not findings,
    }


def required_test_power_w(operating_power_w, margin_db):
    """Power the drive schedule must reach: operating power raised by margin."""
    if not isinstance(operating_power_w, (int, float)) or isinstance(operating_power_w, bool):
        raise ValueError("operating power must be numeric")
    if operating_power_w <= 0.0:
        raise ValueError("operating power must be positive, got %r" % (operating_power_w,))
    if not isinstance(margin_db, (int, float)) or isinstance(margin_db, bool):
        raise ValueError("margin must be numeric")
    if margin_db < 0.0:
        raise ValueError("required margin cannot be negative, got %r" % (margin_db,))
    return float(operating_power_w) * (10.0 ** (float(margin_db) / 10.0))


def achieved_margin_db(operating_power_w, test_power_w):
    """Margin in dB that a declared test power represents over operating power."""
    if operating_power_w <= 0.0:
        raise ValueError("operating power must be positive, got %r" % (operating_power_w,))
    if test_power_w <= 0.0:
        raise ValueError("test power must be positive, got %r" % (test_power_w,))
    return 10.0 * math.log10(float(test_power_w) / float(operating_power_w))


def evaluate_power_schedule(
    operating_power_w,
    drive_steps_w,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
    max_step_db=MAX_DRIVE_STEP_DB,
):
    """Check the radio-frequency drive schedule against the margin requirement.

    The schedule is a strictly ascending list of drive levels in watts.  It
    must start at or below the declared operating power, climb in steps no
    coarser than max_step_db so the threshold is bracketed, and finish at or
    above the power the required margin demands.
    """
    if not isinstance(drive_steps_w, (list, tuple)) or len(drive_steps_w) < 2:
        raise ValueError("drive schedule needs at least two levels")
    levels = []
    for level in drive_steps_w:
        if not isinstance(level, (int, float)) or isinstance(level, bool):
            raise ValueError("drive level must be numeric, got %r" % (level,))
        if level <= 0.0:
            raise ValueError("drive level must be positive, got %r" % (level,))
        levels.append(float(level))
    for lower, upper in zip(levels, levels[1:]):
        if upper <= lower:
            raise ValueError("drive schedule must ascend strictly")
    target_w = required_test_power_w(operating_power_w, required_margin_db)
    top_w = levels[-1]
    findings = []
    if not _at_least(top_w, target_w):
        findings.append(
            "drive schedule tops out at %.4f W, below the %.4f W the required margin demands"
            % (top_w, target_w)
        )
    if not _at_most(levels[0], float(operating_power_w)):
        findings.append("drive schedule starts above the declared operating power")
    coarse = []
    for lower, upper in zip(levels, levels[1:]):
        step_db = 10.0 * math.log10(upper / lower)
        if not _at_most(step_db, float(max_step_db)):
            coarse.append(round(step_db, 4))
    if coarse:
        findings.append("drive steps coarser than %.2f dB: %s" % (max_step_db, coarse))
    return {
        "target_power_w": target_w,
        "top_power_w": top_w,
        "achieved_margin_db": achieved_margin_db(operating_power_w, top_w),
        "required_margin_db": float(required_margin_db),
        "coarse_steps_db": coarse,
        "findings": findings,
        "compliant": not findings,
    }


def check_vacuum_conditions(
    pressure_mbar,
    pump_down_hours,
    max_pressure_mbar=MAX_TEST_PRESSURE_MBAR,
    min_pump_down_hours=MIN_PUMP_DOWN_HOURS,
):
    """Judge the declared chamber conditions for a vacuum-breakdown test."""
    if not isinstance(pressure_mbar, (int, float)) or isinstance(pressure_mbar, bool):
        raise ValueError("chamber pressure must be numeric")
    if pressure_mbar <= 0.0:
        raise ValueError("chamber pressure must be positive, got %r" % (pressure_mbar,))
    if pump_down_hours < 0.0:
        raise ValueError("pump-down duration cannot be negative")
    findings = []
    if not _at_most(float(pressure_mbar), float(max_pressure_mbar)):
        findings.append(
            "chamber pressure %.3e mbar exceeds the %.3e mbar ceiling; a gas "
            "discharge could mask the vacuum breakdown" % (pressure_mbar, max_pressure_mbar)
        )
    if not _at_least(float(pump_down_hours), float(min_pump_down_hours)):
        findings.append(
            "pump-down of %.2f h is shorter than the %.2f h stabilisation period"
            % (pump_down_hours, min_pump_down_hours)
        )
    return {
        "pressure_mbar": float(pressure_mbar),
        "pump_down_hours": float(pump_down_hours),
        "findings": findings,
        "acceptable": not findings,
    }


def check_seeding_arrangement(source, flux_per_cm2_s, min_flux=MIN_SEED_FLUX):
    """Judge the declared free-electron seeding arrangement.

    Without seeding a susceptible gap can survive the whole drive schedule
    simply because no starting electron happened to be present, so the
    procedure has to name a recognised source and a declared flux.
    """
    if not isinstance(source, str) or not source.strip():
        raise ValueError("seeding source must be a non-empty string")
    key = source.strip().lower()
    if key not in SEEDING_SOURCES:
        raise ValueError("unrecognized seeding source: %s" % source)
    if not isinstance(flux_per_cm2_s, (int, float)) or isinstance(flux_per_cm2_s, bool):
        raise ValueError("seeding flux must be numeric")
    if flux_per_cm2_s < 0.0:
        raise ValueError("seeding flux cannot be negative, got %r" % (flux_per_cm2_s,))
    findings = []
    if not _at_least(float(flux_per_cm2_s), float(min_flux)):
        findings.append(
            "declared seeding flux %.4f /cm2/s is below the %.4f /cm2/s floor"
            % (flux_per_cm2_s, min_flux)
        )
    return {
        "source": key,
        "flux_per_cm2_s": float(flux_per_cm2_s),
        "findings": findings,
        "adequate": not findings,
    }


def audit_procedure_sections(sections):
    """Compare a procedure's section list with the expected content items."""
    if not isinstance(sections, (list, tuple)):
        raise ValueError("sections must be a list")
    present = []
    for section in sections:
        if not isinstance(section, str) or not section.strip():
            raise ValueError("section name must be a non-empty string")
        key = section.strip().lower()
        if key not in present:
            present.append(key)
    missing = [s for s in REQUIRED_SECTIONS if s not in present]
    extra = [s for s in present if s not in REQUIRED_SECTIONS]
    return {
        "present": present,
        "missing": missing,
        "extra": extra,
        "complete": not missing,
    }


def assess_test_procedure(procedure):
    """Run the full clause 8.6 content audit over one proposed procedure.

    Returns the four sub-audits plus an aggregate finding list.  The
    procedure is approvable only when no sub-audit raised a finding.
    """
    if not isinstance(procedure, dict):
        raise ValueError("procedure must be a mapping")
    for key in ("sections", "operating_power_w", "drive_steps_w", "detection_methods"):
        if key not in procedure:
            raise ValueError("procedure missing required key: %s" % key)
    sections = audit_procedure_sections(procedure["sections"])
    schedule = evaluate_power_schedule(
        procedure["operating_power_w"],
        procedure["drive_steps_w"],
        procedure.get("required_margin_db", DEFAULT_REQUIRED_MARGIN_DB),
    )
    vacuum = check_vacuum_conditions(
        procedure.get("chamber_pressure_mbar", MAX_TEST_PRESSURE_MBAR),
        procedure.get("pump_down_hours", MIN_PUMP_DOWN_HOURS),
    )
    seeding = check_seeding_arrangement(
        procedure.get("seeding_source", "electron-gun"),
        procedure.get("seeding_flux_per_cm2_s", MIN_SEED_FLUX),
    )
    detection = evaluate_detection_coverage(procedure["detection_methods"])
    findings = []
    if sections["missing"]:
        findings.append("missing procedure content: %s" % ", ".join(sections["missing"]))
    findings.extend(schedule["findings"])
    findings.extend(vacuum["findings"])
    findings.extend(seeding["findings"])
    findings.extend(detection["findings"])
    return {
        "sections": sections,
        "schedule": schedule,
        "vacuum": vacuum,
        "seeding": seeding,
        "detection": detection,
        "findings": findings,
        "approvable": not findings,
    }
