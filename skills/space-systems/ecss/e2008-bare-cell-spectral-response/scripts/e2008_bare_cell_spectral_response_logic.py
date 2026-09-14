"""Bare solar cell spectral response behind sun simulator verification.

Anchor: ECSS-E-ST-20-08C clause 7.5.5. The procedure below is a paraphrase of
the clause intent and reproduces none of its text: the spectral response of the
bare cells is measured because it is what makes a sun simulator measurement
defensible. Without it the simulator cannot be verified against the reference
spectrum and the error the spectral difference contributes cannot be bounded.

Procedure implemented here
--------------------------
1. Validate each curve as a curve: wavelengths strictly increasing, responses
   non-negative, a sampling step fine enough to integrate over, and coverage of
   the band the cell actually responds in.
2. Convert absolute spectral response in amperes per watt into external quantum
   efficiency, and refuse any point above unity. More carriers out than photons
   in is not a remarkable cell, it is a calibration fault.
3. Integrate each response against each spectrum by the trapezoidal rule on a
   common wavelength grid built by linear interpolation, since the four curves
   arrive on four different grids.
4. Form the spectral mismatch factor from the four integrals: the test device
   and the reference device, each against the simulator spectrum and against
   the reference spectrum. A factor of one means the simulator spectrum is, for
   this pair of devices, indistinguishable from the reference.
5. Express the departure from unity as the measurement error the spectral
   difference contributes and hold it against the declared error budget.
"""

import math

__all__ = [
    "TOLERANCE",
    "PLANCK_CHARGE_CONSTANT_NM_V",
    "MAX_QUANTUM_EFFICIENCY",
    "MAX_WAVELENGTH_STEP_NM",
    "DEFAULT_REQUIRED_BAND_NM",
    "DEFAULT_MISMATCH_ERROR_BUDGET_PERCENT",
    "validate_curve",
    "quantum_efficiency",
    "curve_quantum_efficiencies",
    "wavelength_coverage_nm",
    "max_wavelength_step_nm",
    "covers_band",
    "interpolate_at",
    "common_grid",
    "trapezoidal_integral",
    "weighted_integral",
    "spectral_mismatch_factor",
    "mismatch_error_percent",
    "assess_bare_cell_spectral_response",
]

# Integrals, interpolations and their quotients are sums of products of floats,
# so a pair of identical spectra can land a few units in the last place off a
# mismatch factor of exactly one. Absorb that here, not by widening a budget.
TOLERANCE = 1e-9

# hc/q in volt nanometres: quantum efficiency is response times this over the
# wavelength in nanometres.
PLANCK_CHARGE_CONSTANT_NM_V = 1239.841984

# A device cannot deliver more carriers than the photons it received.
MAX_QUANTUM_EFFICIENCY = 1.0

# Coarser than this the trapezoidal rule is guessing at the shape of the curve.
MAX_WAVELENGTH_STEP_NM = 25.0

# The band a response curve has to cover before an integral over it is honest.
DEFAULT_REQUIRED_BAND_NM = (400.0, 1000.0)

# How far the mismatch factor may sit from unity before the measurement carries
# an error the campaign has not accounted for, in percent.
DEFAULT_MISMATCH_ERROR_BUDGET_PERCENT = 2.0


def _real(label, value, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if not allow_negative:
        if allow_zero and number < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
        if not allow_zero and number <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _mapping(label, value, required_keys=()):
    """Return value as a mapping carrying every required key."""
    if not isinstance(value, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in required_keys:
        if key not in value:
            raise ValueError("%s is missing required key '%s'" % (label, key))
    return value


def _not_above(value, limit):
    """Return True when value sits at or below limit, edge included."""
    return value < limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TOLERANCE)


def _not_below(value, limit):
    """Return True when value sits at or above limit, edge included."""
    return value > limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=TOLERANCE)


def validate_curve(label, curve):
    """Return a curve as a validated list of (wavelength_nm, value) pairs."""
    if not isinstance(curve, (list, tuple)) or len(curve) < 2:
        raise ValueError("%s must hold at least two (wavelength, value) pairs" % label)
    points = []
    previous = None
    for entry in curve:
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            raise ValueError("%s entries must be (wavelength_nm, value) pairs" % label)
        wavelength = _real("%s wavelength_nm" % label, entry[0])
        value = _real("%s value" % label, entry[1], allow_zero=True)
        if previous is not None and not wavelength > previous:
            raise ValueError(
                "%s wavelengths must strictly increase; %g follows %g"
                % (label, wavelength, previous)
            )
        previous = wavelength
        points.append((wavelength, value))
    return points


def quantum_efficiency(response_a_per_w, wavelength_nm):
    """Return the external quantum efficiency of one spectral response point."""
    response = _real("response_a_per_w", response_a_per_w, allow_zero=True)
    wavelength = _real("wavelength_nm", wavelength_nm)
    return response * PLANCK_CHARGE_CONSTANT_NM_V / wavelength


def curve_quantum_efficiencies(curve):
    """Return the quantum efficiency of every point of a response curve."""
    points = validate_curve("curve", curve)
    return [
        (wavelength, quantum_efficiency(value, wavelength))
        for wavelength, value in points
    ]


def wavelength_coverage_nm(curve):
    """Return the (first, last) wavelength a curve covers."""
    points = validate_curve("curve", curve)
    return points[0][0], points[-1][0]


def max_wavelength_step_nm(curve):
    """Return the widest gap between neighbouring wavelengths of a curve."""
    points = validate_curve("curve", curve)
    return max(
        points[index + 1][0] - points[index][0] for index in range(len(points) - 1)
    )


def covers_band(curve, band=DEFAULT_REQUIRED_BAND_NM):
    """Return True when a curve spans the whole band the cell responds in."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("band must be a (low_nm, high_nm) pair")
    low = _real("band low_nm", band[0])
    high = _real("band high_nm", band[1])
    if not high > low:
        raise ValueError("band is inverted: %g is not above %g" % (high, low))
    first, last = wavelength_coverage_nm(curve)
    return _not_above(first, low) and _not_below(last, high)


def interpolate_at(points, wavelength_nm):
    """Return a curve value at one wavelength by linear interpolation."""
    target = _real("wavelength_nm", wavelength_nm)
    if not isinstance(points, (list, tuple)) or len(points) < 2:
        raise ValueError("points must hold at least two (wavelength, value) pairs")
    if target < points[0][0] or target > points[-1][0]:
        return 0.0
    for index in range(len(points) - 1):
        low_x, low_y = points[index]
        high_x, high_y = points[index + 1]
        if target <= high_x:
            width = high_x - low_x
            if math.isclose(width, 0.0, rel_tol=0.0, abs_tol=TOLERANCE):
                return low_y
            return low_y + (high_y - low_y) * (target - low_x) / width
    return points[-1][1]


def common_grid(*curves):
    """Return the sorted union of the wavelengths of every supplied curve."""
    if not curves:
        raise ValueError("at least one curve is needed to build a grid")
    grid = set()
    for index, curve in enumerate(curves):
        for wavelength, _ in validate_curve("curve %d" % index, curve):
            grid.add(wavelength)
    return sorted(grid)


def trapezoidal_integral(xs, ys):
    """Return the trapezoidal integral of ys over xs."""
    if not isinstance(xs, (list, tuple)) or not isinstance(ys, (list, tuple)):
        raise ValueError("xs and ys must be sequences")
    if len(xs) != len(ys):
        raise ValueError(
            "xs holds %d points and ys holds %d; an integral needs pairs"
            % (len(xs), len(ys))
        )
    if len(xs) < 2:
        raise ValueError("an integral needs at least two points")
    total = 0.0
    for index in range(len(xs) - 1):
        width = xs[index + 1] - xs[index]
        if width < 0.0:
            raise ValueError("xs must not decrease across the integration range")
        total += width * (ys[index] + ys[index + 1]) / 2.0
    return total


def weighted_integral(response_curve, spectrum_curve, grid=None):
    """Return the integral of a response curve weighted by a spectrum."""
    response = validate_curve("response_curve", response_curve)
    spectrum = validate_curve("spectrum_curve", spectrum_curve)
    xs = list(grid) if grid is not None else common_grid(response_curve, spectrum_curve)
    if len(xs) < 2:
        raise ValueError("the integration grid needs at least two wavelengths")
    ys = [
        interpolate_at(response, x) * interpolate_at(spectrum, x) for x in xs
    ]
    return trapezoidal_integral(xs, ys)


def spectral_mismatch_factor(
    test_response, reference_response, simulator_spectrum, reference_spectrum
):
    """Return the spectral mismatch factor of a simulator for one device pair."""
    grid = common_grid(
        test_response, reference_response, simulator_spectrum, reference_spectrum
    )
    test_under_reference = weighted_integral(test_response, reference_spectrum, grid)
    reference_under_simulator = weighted_integral(
        reference_response, simulator_spectrum, grid
    )
    test_under_simulator = weighted_integral(test_response, simulator_spectrum, grid)
    reference_under_reference = weighted_integral(
        reference_response, reference_spectrum, grid
    )
    denominator = test_under_reference * reference_under_simulator
    if math.isclose(denominator, 0.0, rel_tol=0.0, abs_tol=TOLERANCE):
        raise ValueError(
            "the reference device and the test device share no wavelengths with "
            "the spectra, so the mismatch factor is not defined"
        )
    return (test_under_simulator * reference_under_reference) / denominator


def mismatch_error_percent(factor):
    """Return how far a mismatch factor sits from unity, in percent."""
    value = _real("factor", factor)
    return abs(value - 1.0) * 100.0


def assess_bare_cell_spectral_response(spec):
    """Run the full clause 7.5.5 spectral response assessment.

    spec keys: test_response and reference_response (absolute spectral response
    curves in amperes per watt), simulator_spectrum and reference_spectrum
    (irradiance curves), plus optional required_band, max_step_nm and
    error_budget_percent.
    """
    data = _mapping(
        "spec",
        spec,
        ("test_response", "reference_response", "simulator_spectrum",
         "reference_spectrum"),
    )
    band = data.get("required_band", DEFAULT_REQUIRED_BAND_NM)
    max_step = _real(
        "spec['max_step_nm']", data.get("max_step_nm", MAX_WAVELENGTH_STEP_NM)
    )
    budget = _real(
        "spec['error_budget_percent']",
        data.get("error_budget_percent", DEFAULT_MISMATCH_ERROR_BUDGET_PERCENT),
    )

    findings = []
    curve_reports = {}
    for name in ("test_response", "reference_response"):
        points = validate_curve("spec['%s']" % name, data[name])
        step = max_wavelength_step_nm(points)
        coverage = wavelength_coverage_nm(points)
        spans_band = covers_band(points, band)
        efficiencies = curve_quantum_efficiencies(points)
        peak_efficiency = max(value for _, value in efficiencies)
        efficiency_ok = _not_above(peak_efficiency, MAX_QUANTUM_EFFICIENCY)
        if not _not_above(step, max_step):
            findings.append(
                "%s is sampled at up to %.4g nm, coarser than the %.4g nm an "
                "integral over it can be trusted at" % (name, step, max_step)
            )
        if not spans_band:
            findings.append(
                "%s covers %.4g to %.4g nm and leaves part of the %.4g to %.4g "
                "nm response band unmeasured"
                % (name, coverage[0], coverage[1], band[0], band[1])
            )
        if not efficiency_ok:
            findings.append(
                "%s peaks at a quantum efficiency of %.4f, above the one carrier "
                "per photon a device can deliver" % (name, peak_efficiency)
            )
        curve_reports[name] = {
            "point_count": len(points),
            "coverage_nm": coverage,
            "max_step_nm": step,
            "covers_band": spans_band,
            "peak_quantum_efficiency": peak_efficiency,
            "quantum_efficiency_plausible": efficiency_ok,
        }

    for name in ("simulator_spectrum", "reference_spectrum"):
        points = validate_curve("spec['%s']" % name, data[name])
        curve_reports[name] = {
            "point_count": len(points),
            "coverage_nm": wavelength_coverage_nm(points),
            "max_step_nm": max_wavelength_step_nm(points),
        }

    factor = spectral_mismatch_factor(
        data["test_response"],
        data["reference_response"],
        data["simulator_spectrum"],
        data["reference_spectrum"],
    )
    error_percent = mismatch_error_percent(factor)
    within_budget = _not_above(error_percent, budget)
    if not within_budget:
        findings.append(
            "the simulator contributes %.4f percent of spectral mismatch error, "
            "above the declared %.4f percent budget" % (error_percent, budget)
        )
    return {
        "curve_reports": curve_reports,
        "spectral_mismatch_factor": factor,
        "mismatch_error_percent": error_percent,
        "error_budget_percent": budget,
        "within_error_budget": within_budget,
        "findings": findings,
        "valid": not findings,
    }
