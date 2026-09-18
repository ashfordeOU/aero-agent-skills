#!/usr/bin/env python3
"""Cable injection susceptibility setup, ECSS-E-ST-20-07C clause 5.4.8.3.

Paraphrased procedure, no verbatim standard text. The clause does not
describe a bench from nothing: the coupling arrangement for harness
injection starts from the standard bench layout already used for the other
runs and is modified only where coupling current onto a bundle demands
something different. This module turns that into a deterministic
assessment:

  baseline bands + declared deltas -> the bands this bench is graded on
  realized geometry                -> conforming / deviation / nonconforming
  probe order and separation       -> mutual coupling and phase bounds
  exposed harness length           -> the frequency the layout stops at
  jig against bench impedance      -> the error in a calibrated drive level

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerances. Band edges, wavelengths and decibel errors are
# floats, so a value that exactly meets a bound can land a few units in
# the last place off it. These absorb representation error only; they
# never relax a band.
REL_TOL = 1e-12
ABS_TOL = 1e-12

SPEED_OF_LIGHT_M_S = 299792458.0

# The monitor probe has to clear the injection probe by this multiple of
# the probe aperture before the two stop coupling to each other directly.
APERTURE_MULTIPLE = 1.5

# ...and has to stay inside this fraction of a wavelength at the top of
# the band, or the current it monitors is not the current at the unit.
WAVELENGTH_FRACTION = 0.05

# A calibrated drive level carries this much error in decibels before the
# difference between the jig and the bench has to be acted on.
CALIBRATION_TOLERANCE_DB = 3.0

COUPLING_METHODS = ("capacitive-coupling-clamp", "current-injection-probe")
LEVEL_CONTROLS = ("closed-loop-monitored", "open-loop-calibrated")

GEOMETRY_PARAMETERS = (
    "bond_resistance_ohm",
    "harness_height_m",
    "harness_length_m",
    "injection_probe_to_eut_m",
    "monitor_probe_to_eut_m",
)

CONFORMING = "conforming"
DECLARED_DEVIATION = "declared-deviation"
NONCONFORMING = "nonconforming"

VERDICT_CONFORMING = "setup-conforming"
VERDICT_WITH_DEVIATIONS = "setup-conforming-with-deviations"
VERDICT_NONCONFORMING = "setup-nonconforming"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _word(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_band(band, name):
    """Validate one (minimum, maximum) acceptance band and return it."""
    if not isinstance(band, (tuple, list)) or len(band) != 2:
        raise ValueError("%s: band must be a (minimum, maximum) pair" % name)
    low = _scalar(band[0], "%s.minimum" % name)
    high = _scalar(band[1], "%s.maximum" % name)
    if high <= low:
        raise ValueError(
            "%s: band maximum (%g) must exceed its minimum (%g)" % (name, high, low)
        )
    return (low, high)


def apply_setup_deltas(baseline_bands, deltas):
    """Move the standard layout's bands by the deltas the injection run declares.

    baseline_bands maps a geometry parameter to a (minimum, maximum) pair.
    deltas maps a parameter to {"minimum_delta": x, "maximum_delta": y};
    either key may be omitted. An unknown parameter is refused, and so is a
    delta that collapses or inverts the band it is applied to.
    """
    if not isinstance(baseline_bands, dict) or not baseline_bands:
        raise ValueError("baseline_bands: must be a non-empty mapping")
    if deltas is None:
        deltas = {}
    if not isinstance(deltas, dict):
        raise ValueError("deltas: must be a mapping")

    resolved = {}
    for name, band in baseline_bands.items():
        if name not in GEOMETRY_PARAMETERS:
            raise ValueError(
                "baseline_bands: unknown parameter %r; known: %s"
                % (name, ", ".join(GEOMETRY_PARAMETERS))
            )
        resolved[name] = validate_band(band, name)

    for name, delta in deltas.items():
        if name not in resolved:
            raise ValueError(
                "deltas: %r is not a parameter of this bench; known: %s"
                % (name, ", ".join(sorted(resolved)))
            )
        if not isinstance(delta, dict):
            raise ValueError("deltas[%r]: must be a mapping" % name)
        for key in delta:
            if key not in ("minimum_delta", "maximum_delta"):
                raise ValueError(
                    "deltas[%r]: unknown key %r; use minimum_delta or maximum_delta"
                    % (name, key)
                )
        low, high = resolved[name]
        if "minimum_delta" in delta:
            low = low + _number(delta, "minimum_delta", "deltas[%r]" % name)
        if "maximum_delta" in delta:
            high = high + _number(delta, "maximum_delta", "deltas[%r]" % name)
        if high <= low:
            raise ValueError(
                "deltas[%r]: collapses the band to (%g, %g); a delta may move a "
                "band, not close it" % (name, low, high)
            )
        resolved[name] = (low, high)
    return resolved


def validate_bench(config):
    """Validate a realized harness injection bench and return it normalized."""
    where = "bench"
    if not isinstance(config, dict):
        raise ValueError("%s: record must be a mapping" % where)

    values = {
        "coupling_method": _word(config, "coupling_method", where, COUPLING_METHODS),
        "level_control": _word(config, "level_control", where, LEVEL_CONTROLS),
    }

    positive = (
        "band_high_hz",
        "bench_common_mode_impedance_ohm",
        "calibration_fixture_impedance_ohm",
        "harness_height_m",
        "harness_length_m",
        "injection_probe_to_eut_m",
        "monitor_probe_to_eut_m",
        "probe_aperture_m",
    )
    for key in positive:
        value = _number(config, key, where)
        if value <= 0.0:
            raise ValueError("%s: %s must be > 0, got %g" % (where, key, value))
        values[key] = value

    resistance = _number(config, "bond_resistance_ohm", where)
    if resistance < 0.0:
        raise ValueError(
            "%s: bond_resistance_ohm must be >= 0, got %g" % (where, resistance)
        )
    values["bond_resistance_ohm"] = resistance

    declared = config.get("declared_deviations", ())
    if isinstance(declared, str) or not isinstance(declared, (tuple, list, set)):
        raise ValueError(
            "%s: declared_deviations must be a sequence of parameter names" % where
        )
    names = set()
    for name in declared:
        if name not in GEOMETRY_PARAMETERS:
            raise ValueError(
                "%s: declared deviation %r is not a graded parameter; graded: %s"
                % (where, name, ", ".join(GEOMETRY_PARAMETERS))
            )
        names.add(name)
    values["declared_deviations"] = frozenset(names)
    return values


def categorize_parameter(value, band, declared_deviation=False):
    """Grade one realized parameter against the band that governs it."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    if at_least(measured, low) and at_most(measured, high):
        return CONFORMING
    return DECLARED_DEVIATION if bool(declared_deviation) else NONCONFORMING


def band_margin(value, band):
    """Fractional distance from the nearer band edge, negative when outside."""
    low, high = validate_band(band, "band")
    measured = _scalar(value, "value")
    width = high - low
    return min(measured - low, high - measured) / width


def governing_parameter(realized, bands):
    """The graded parameter sitting closest to, or furthest outside, its band."""
    if not isinstance(bands, dict) or not bands:
        raise ValueError("bands: must be a non-empty mapping")
    ranked = []
    for name in sorted(bands):
        if name not in realized:
            raise ValueError("realized: missing graded parameter %r" % name)
        ranked.append((band_margin(realized[name], bands[name]), name))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][1]


def probe_separation_m(bench):
    """Distance between the injection probe and the monitor probe, signed.

    Positive when the monitor sits between the injection point and the
    unit, which is the only order in which it measures what reaches the
    unit rather than what the injection probe put onto the far side.
    """
    return bench["injection_probe_to_eut_m"] - bench["monitor_probe_to_eut_m"]


def minimum_probe_separation_m(probe_aperture_m, aperture_multiple=APERTURE_MULTIPLE):
    """Separation below which the two probes couple to each other directly."""
    aperture = _scalar(probe_aperture_m, "probe_aperture_m")
    multiple = _scalar(aperture_multiple, "aperture_multiple")
    if aperture <= 0.0:
        raise ValueError("probe_aperture_m must be > 0, got %g" % aperture)
    if multiple < 1.0:
        raise ValueError("aperture_multiple must be >= 1, got %g" % multiple)
    return aperture * multiple


def maximum_probe_separation_m(band_high_hz, wavelength_fraction=WAVELENGTH_FRACTION):
    """Separation above which the monitored current is not the injected current."""
    top = _scalar(band_high_hz, "band_high_hz")
    fraction = _scalar(wavelength_fraction, "wavelength_fraction")
    if top <= 0.0:
        raise ValueError("band_high_hz must be > 0, got %g" % top)
    if not 0.0 < fraction <= 1.0:
        raise ValueError(
            "wavelength_fraction must be in (0, 1], got %g" % fraction
        )
    return fraction * SPEED_OF_LIGHT_M_S / top


def harness_resonance_hz(harness_length_m):
    """Quarter-wave resonance of the exposed harness run on the bench."""
    length = _scalar(harness_length_m, "harness_length_m")
    if length <= 0.0:
        raise ValueError("harness_length_m must be > 0, got %g" % length)
    return SPEED_OF_LIGHT_M_S / (4.0 * length)


def calibration_error_db(fixture_impedance_ohm, bench_impedance_ohm):
    """Decibels by which a jig-calibrated drive misses the current on the bench."""
    fixture = _scalar(fixture_impedance_ohm, "fixture_impedance_ohm")
    bench = _scalar(bench_impedance_ohm, "bench_impedance_ohm")
    if fixture <= 0.0:
        raise ValueError("fixture_impedance_ohm must be > 0, got %g" % fixture)
    if bench <= 0.0:
        raise ValueError("bench_impedance_ohm must be > 0, got %g" % bench)
    return 20.0 * math.log10(fixture / bench)


def assess_injection_setup(
    config,
    baseline_bands,
    deltas=None,
    wavelength_fraction=WAVELENGTH_FRACTION,
    aperture_multiple=APERTURE_MULTIPLE,
    calibration_tolerance_db=CALIBRATION_TOLERANCE_DB,
):
    """Full clause 5.4.8.3 assessment of a harness injection coupling setup."""
    tolerance = _scalar(calibration_tolerance_db, "calibration_tolerance_db")
    if tolerance < 0.0:
        raise ValueError("calibration_tolerance_db must be >= 0, got %g" % tolerance)

    bench = validate_bench(config)
    bands = apply_setup_deltas(baseline_bands, deltas)

    findings = []
    limitations = []

    categories = {}
    for name in sorted(bands):
        category = categorize_parameter(
            bench[name], bands[name], name in bench["declared_deviations"]
        )
        categories[name] = category
        if category == NONCONFORMING:
            low, high = bands[name]
            findings.append(
                "%s is %g, outside its band %g to %g and not declared as a deviation"
                % (name, bench[name], low, high)
            )
        elif category == DECLARED_DEVIATION:
            low, high = bands[name]
            limitations.append(
                "%s is %g, outside its band %g to %g but carried as a declared "
                "deviation" % (name, bench[name], low, high)
            )

    separation = probe_separation_m(bench)
    lower = minimum_probe_separation_m(bench["probe_aperture_m"], aperture_multiple)
    upper = maximum_probe_separation_m(bench["band_high_hz"], wavelength_fraction)
    order_is_right = separation > 0.0
    separation_ok = False
    if not order_is_right:
        findings.append(
            "the monitor probe sits at %g m and the injection probe at %g m, so the "
            "monitor is not between the injection point and the unit and reads a "
            "current the unit never sees"
            % (bench["monitor_probe_to_eut_m"], bench["injection_probe_to_eut_m"])
        )
    elif not at_least(separation, lower):
        findings.append(
            "the probes are %g m apart, inside the %g m at which they couple to "
            "each other rather than to the harness" % (separation, lower)
        )
    elif not at_most(separation, upper):
        findings.append(
            "the probes are %g m apart, past the %g m that keeps the monitored "
            "current equal to the injected current at %g Hz"
            % (separation, upper, bench["band_high_hz"])
        )
    else:
        separation_ok = True

    resonance = harness_resonance_hz(bench["harness_length_m"])
    resonance_ok = at_most(bench["band_high_hz"], resonance)
    if not resonance_ok:
        findings.append(
            "the exposed harness of %g m resonates at %g Hz, under the %g Hz top of "
            "the band; above resonance the injected current depends on where the "
            "probe sits" % (bench["harness_length_m"], resonance, bench["band_high_hz"])
        )

    error = calibration_error_db(
        bench["calibration_fixture_impedance_ohm"],
        bench["bench_common_mode_impedance_ohm"],
    )
    calibration_ok = at_most(abs(error), tolerance)
    if not calibration_ok:
        if bench["level_control"] == "open-loop-calibrated":
            findings.append(
                "the jig and the bench differ by %.2f dB and the level is set open "
                "loop, so the current injected is not the current calibrated" % error
            )
        else:
            limitations.append(
                "the jig and the bench differ by %.2f dB; the monitor closes the "
                "loop, but the amplifier carries that much extra drive" % error
            )

    if bench["coupling_method"] == "capacitive-coupling-clamp":
        limitations.append(
            "a capacitive clamp couples through the harness jacket, so the current "
            "it produces depends on the bundle build and does not transfer to "
            "another harness unchanged"
        )

    if findings:
        verdict = VERDICT_NONCONFORMING
    elif limitations:
        verdict = VERDICT_WITH_DEVIATIONS
    else:
        verdict = VERDICT_CONFORMING

    return {
        "bench": bench,
        "bands": bands,
        "categories": categories,
        "probe_separation_m": separation,
        "minimum_probe_separation_m": lower,
        "maximum_probe_separation_m": upper,
        "probe_order_is_right": order_is_right,
        "probe_separation_is_adequate": separation_ok,
        "harness_resonance_hz": resonance,
        "band_is_below_resonance": resonance_ok,
        "calibration_error_db": error,
        "calibration_is_adequate": calibration_ok,
        "governing_parameter": governing_parameter(bench, bands),
        "findings": findings,
        "limitations": limitations,
        "verdict": verdict,
    }
