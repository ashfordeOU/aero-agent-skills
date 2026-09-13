#!/usr/bin/env python3
"""Multipactor verification process for a radio-frequency unit.

Anchor: ECSS-E-ST-20-01C clause 4.1 (overall process demonstrating that
equipment holds the required multipactor margins before flight).
Paraphrased into an implementable procedure; no verbatim standard text.

Stdlib only, offline, deterministic.

Procedure implemented here:

1. derive the frequency-gap-product of every multipactor-critical gap;
2. categorize it against the validated susceptibility-chart band and drop a
   gap that falls outside it, with a stated reason;
3. resolve the electrode material to its chart coefficients and compute the
   parallel-plate breakdown voltage at that product;
4. convert threshold and operating conditions into power at the gap
   impedance and take the margin in decibel;
5. select the verification route in three bands (analysis-only,
   multipactor test, redesign);
6. compute the elevated test level and validate the planned setup
   (seeding source plus two independent detection methods);
7. aggregate into a unit-level verdict.

The chart coefficients below are a documented engineering fit of the
parallel-plate reference geometry, expressed as
    breakdown_voltage = coefficient * (frequency_gap_product ** exponent)
with the frequency-gap-product in gigahertz-millimetre. They are a
project-replaceable default, not a reproduction of any chart.
"""

import math

# A margin landing exactly on a threshold is the design point; the
# comparison absorbs floating-point representation error instead of moving
# the engineering threshold.
MARGIN_REL_TOL = 1e-9
MARGIN_ABS_TOL = 1e-9

# Validated band of the frequency-gap-product, in GHz.mm.
FD_BAND_MIN_GHZ_MM = 0.1
FD_BAND_MAX_GHZ_MM = 100.0

# Default project thresholds, in decibel.
DEFAULT_ANALYSIS_MARGIN_DB = 8.0
DEFAULT_TEST_MARGIN_DB = 3.0

MATERIALS = {
    "silver": {"coefficient": 63.0, "exponent": 1.12, "sey_first_crossover_ev": 30.0},
    "silver-plated-aluminium": {
        "coefficient": 63.0,
        "exponent": 1.12,
        "sey_first_crossover_ev": 30.0,
    },
    "aluminium-alloy": {"coefficient": 70.0, "exponent": 1.10, "sey_first_crossover_ev": 35.0},
    "aluminium-alodine": {"coefficient": 57.0, "exponent": 1.10, "sey_first_crossover_ev": 25.0},
    "copper": {"coefficient": 68.0, "exponent": 1.11, "sey_first_crossover_ev": 33.0},
    "gold": {"coefficient": 80.0, "exponent": 1.08, "sey_first_crossover_ev": 45.0},
    "titanium": {"coefficient": 90.0, "exponent": 1.05, "sey_first_crossover_ev": 55.0},
}

SEEDING_SOURCES = ("strontium-90", "ultraviolet-source", "electron-gun")

GLOBAL_DETECTION_METHODS = ("forward-reverse-power-nulling", "phase-noise")
LOCAL_DETECTION_METHODS = ("third-harmonic", "electron-current-probe", "optical-emission")
DETECTION_METHODS = GLOBAL_DETECTION_METHODS + LOCAL_DETECTION_METHODS

MIN_DETECTION_METHODS = 2

ROUTE_ANALYSIS_ONLY = "analysis-only"
ROUTE_TEST_REQUIRED = "multipactor-test-required"
ROUTE_REDESIGN = "redesign-required"

BAND_BELOW = "below-susceptible-band"
BAND_INSIDE = "inside-susceptible-band"
BAND_ABOVE = "above-susceptible-band"


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
        value, bound, rel_tol=MARGIN_REL_TOL, abs_tol=MARGIN_ABS_TOL
    )


def frequency_gap_product(frequency_hz, gap_m):
    """Return the frequency-gap-product in gigahertz-millimetre."""
    freq = _as_float(frequency_hz, "frequency_hz")
    gap = _as_float(gap_m, "gap_m")
    if freq <= 0.0:
        raise ValueError("frequency_hz must be positive, got %r" % (frequency_hz,))
    if gap <= 0.0:
        raise ValueError("gap_m must be positive, got %r" % (gap_m,))
    return (freq / 1.0e9) * (gap * 1.0e3)


def categorize_gap_band(fd_ghz_mm):
    """Categorize a frequency-gap-product against the validated chart band."""
    fd = _as_float(fd_ghz_mm, "fd_ghz_mm")
    if fd <= 0.0:
        raise ValueError("fd_ghz_mm must be positive, got %r" % (fd_ghz_mm,))
    if not _at_least(fd, FD_BAND_MIN_GHZ_MM):
        return BAND_BELOW
    if not _at_least(FD_BAND_MAX_GHZ_MM, fd):
        return BAND_ABOVE
    return BAND_INSIDE


def material_data(material):
    """Resolve an electrode material to its chart coefficients."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty string, got %r" % (material,))
    key = "-".join(material.strip().lower().replace("_", " ").replace("-", " ").split())
    data = MATERIALS.get(key)
    if data is None:
        raise ValueError("uncategorized electrode material %r" % (material,))
    return dict(data, material=key)


def breakdown_voltage(fd_ghz_mm, material):
    """Parallel-plate multipactor breakdown voltage, in volt.

    Refuses a frequency-gap-product outside the validated band: the fit has
    no physical content there and extrapolating it manufactures a margin.
    """
    band = categorize_gap_band(fd_ghz_mm)
    if band != BAND_INSIDE:
        raise ValueError(
            "frequency-gap-product %r GHz.mm is %s; the chart fit is not valid there"
            % (fd_ghz_mm, band)
        )
    data = material_data(material)
    fd = _as_float(fd_ghz_mm, "fd_ghz_mm")
    return data["coefficient"] * (fd ** data["exponent"])


def power_from_peak_voltage(peak_voltage_v, impedance_ohm):
    """Peak power carried by a peak voltage across a local impedance."""
    volt = _as_float(peak_voltage_v, "peak_voltage_v")
    imp = _as_float(impedance_ohm, "impedance_ohm")
    if volt <= 0.0:
        raise ValueError("peak_voltage_v must be positive, got %r" % (peak_voltage_v,))
    if imp <= 0.0:
        raise ValueError("impedance_ohm must be positive, got %r" % (impedance_ohm,))
    return (volt * volt) / (2.0 * imp)


def peak_voltage_from_power(power_w, impedance_ohm):
    """Peak voltage produced by a peak power across a local impedance."""
    power = _as_float(power_w, "power_w")
    imp = _as_float(impedance_ohm, "impedance_ohm")
    if power <= 0.0:
        raise ValueError("power_w must be positive, got %r" % (power_w,))
    if imp <= 0.0:
        raise ValueError("impedance_ohm must be positive, got %r" % (impedance_ohm,))
    return math.sqrt(2.0 * power * imp)


def multipactor_margin_db(operating_power_w, threshold_power_w):
    """Margin in decibel of a threshold power over an operating power."""
    operating = _as_float(operating_power_w, "operating_power_w")
    threshold = _as_float(threshold_power_w, "threshold_power_w")
    if operating <= 0.0:
        raise ValueError("operating_power_w must be positive, got %r" % (operating_power_w,))
    if threshold <= 0.0:
        raise ValueError("threshold_power_w must be positive, got %r" % (threshold_power_w,))
    return 10.0 * math.log10(threshold / operating)


def voltage_margin_db(operating_voltage_v, threshold_voltage_v):
    """Margin in decibel of a threshold voltage over an operating voltage."""
    operating = _as_float(operating_voltage_v, "operating_voltage_v")
    threshold = _as_float(threshold_voltage_v, "threshold_voltage_v")
    if operating <= 0.0:
        raise ValueError("operating_voltage_v must be positive, got %r" % (operating_voltage_v,))
    if threshold <= 0.0:
        raise ValueError("threshold_voltage_v must be positive, got %r" % (threshold_voltage_v,))
    return 20.0 * math.log10(threshold / operating)


def select_verification_route(
    margin_db,
    analysis_margin_db=DEFAULT_ANALYSIS_MARGIN_DB,
    test_margin_db=DEFAULT_TEST_MARGIN_DB,
):
    """Select the route for one gap from its margin and the project thresholds."""
    margin = _as_float(margin_db, "margin_db")
    analysis = _as_float(analysis_margin_db, "analysis_margin_db")
    tested = _as_float(test_margin_db, "test_margin_db")
    if tested <= 0.0:
        raise ValueError("test_margin_db must be positive, got %r" % (test_margin_db,))
    if not analysis > tested:
        raise ValueError(
            "analysis_margin_db must exceed test_margin_db (%r vs %r)"
            % (analysis_margin_db, test_margin_db)
        )
    if _at_least(margin, analysis):
        return ROUTE_ANALYSIS_ONLY
    if _at_least(margin, tested):
        return ROUTE_TEST_REQUIRED
    return ROUTE_REDESIGN


def required_test_power(operating_power_w, test_margin_db=DEFAULT_TEST_MARGIN_DB):
    """Elevated power level a multipactor test has to reach, in watt."""
    operating = _as_float(operating_power_w, "operating_power_w")
    margin = _as_float(test_margin_db, "test_margin_db")
    if operating <= 0.0:
        raise ValueError("operating_power_w must be positive, got %r" % (operating_power_w,))
    if margin < 0.0:
        raise ValueError("test_margin_db must be non-negative, got %r" % (test_margin_db,))
    return operating * (10.0 ** (margin / 10.0))


def validate_test_setup(setup):
    """Validate a planned multipactor test setup.

    Required keys: seeding_source, detection_methods.
    """
    if not isinstance(setup, dict):
        raise ValueError("test setup must be a mapping")
    for key in ("seeding_source", "detection_methods"):
        if key not in setup:
            raise ValueError("test setup is missing required key %r" % (key,))
    source = setup["seeding_source"]
    if source not in SEEDING_SOURCES:
        raise ValueError("uncategorized electron seeding source %r" % (source,))
    methods = setup["detection_methods"]
    if not isinstance(methods, (list, tuple)):
        raise ValueError("detection_methods must be a list")
    seen = []
    for method in methods:
        if method not in DETECTION_METHODS:
            raise ValueError("uncategorized detection method %r" % (method,))
        if method not in seen:
            seen.append(method)
    findings = []
    if len(seen) < MIN_DETECTION_METHODS:
        findings.append("fewer than two independent detection methods")
    has_global = any(m in GLOBAL_DETECTION_METHODS for m in seen)
    has_local = any(m in LOCAL_DETECTION_METHODS for m in seen)
    if seen and not (has_global and has_local):
        findings.append("detection methods are not a global and local pair")
    return {
        "seeding_source": source,
        "detection_methods": seen,
        "findings": findings,
        "valid": not findings,
    }


def assess_gap(gap, analysis_margin_db=DEFAULT_ANALYSIS_MARGIN_DB,
               test_margin_db=DEFAULT_TEST_MARGIN_DB):
    """Assess one multipactor-critical gap end to end.

    Required keys: id, frequency_hz, gap_m, material, impedance_ohm,
    peak_operating_power_w.
    """
    if not isinstance(gap, dict):
        raise ValueError("gap must be a mapping")
    required = (
        "id",
        "frequency_hz",
        "gap_m",
        "material",
        "impedance_ohm",
        "peak_operating_power_w",
    )
    for key in required:
        if key not in gap:
            raise ValueError("gap is missing required key %r" % (key,))
    identifier = gap["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("gap id must be a non-empty string, got %r" % (identifier,))
    fd = frequency_gap_product(gap["frequency_hz"], gap["gap_m"])
    band = categorize_gap_band(fd)
    if band != BAND_INSIDE:
        return {
            "id": identifier.strip(),
            "fd_ghz_mm": fd,
            "band": band,
            "route": None,
            "margin_db": None,
            "reason": "frequency-gap-product %s; no credible multipactor risk" % band,
        }
    v_threshold = breakdown_voltage(fd, gap["material"])
    impedance = gap["impedance_ohm"]
    p_threshold = power_from_peak_voltage(v_threshold, impedance)
    p_operating = _as_float(gap["peak_operating_power_w"], "peak_operating_power_w")
    if p_operating <= 0.0:
        raise ValueError(
            "peak_operating_power_w must be positive, got %r" % (gap["peak_operating_power_w"],)
        )
    margin = multipactor_margin_db(p_operating, p_threshold)
    route = select_verification_route(margin, analysis_margin_db, test_margin_db)
    result = {
        "id": identifier.strip(),
        "fd_ghz_mm": fd,
        "band": band,
        "material": material_data(gap["material"])["material"],
        "threshold_voltage_v": v_threshold,
        "threshold_power_w": p_threshold,
        "operating_power_w": p_operating,
        "margin_db": margin,
        "route": route,
        "reason": None,
    }
    if route == ROUTE_TEST_REQUIRED:
        result["required_test_power_w"] = required_test_power(p_operating, test_margin_db)
    return result


def run_verification_process(equipment):
    """Run the clause 4.1 process over a whole radio-frequency unit.

    Keys: gaps (non-empty list), test_setup (optional),
    analysis_margin_db / test_margin_db (optional project thresholds).
    """
    if not isinstance(equipment, dict):
        raise ValueError("equipment must be a mapping")
    if "gaps" not in equipment:
        raise ValueError("equipment is missing required key 'gaps'")
    gaps = equipment["gaps"]
    if not isinstance(gaps, (list, tuple)) or not gaps:
        raise ValueError("equipment must carry at least one multipactor-critical gap")
    analysis = equipment.get("analysis_margin_db", DEFAULT_ANALYSIS_MARGIN_DB)
    tested = equipment.get("test_margin_db", DEFAULT_TEST_MARGIN_DB)
    results = [assess_gap(g, analysis, tested) for g in gaps]
    redesign = sorted(r["id"] for r in results if r["route"] == ROUTE_REDESIGN)
    to_test = sorted(r["id"] for r in results if r["route"] == ROUTE_TEST_REQUIRED)
    out_of_band = sorted(r["id"] for r in results if r["band"] != BAND_INSIDE)
    findings = []
    if redesign:
        findings.append("redesign-required: " + ", ".join(redesign))
    setup = None
    if to_test:
        if "test_setup" not in equipment:
            findings.append("gaps routed to test with no test setup on record")
        else:
            setup = validate_test_setup(equipment["test_setup"])
            for item in setup["findings"]:
                findings.append("test-setup: " + item)
    graded = [r["margin_db"] for r in results if r["margin_db"] is not None]
    return {
        "gaps": results,
        "out_of_band": out_of_band,
        "to_test": to_test,
        "redesign": redesign,
        "test_setup": setup,
        "worst_margin_db": min(graded) if graded else None,
        "findings": findings,
        "verified": not findings,
    }
