"""ECSS-E-ST-20-07C clause 5.2.3.3 -- composite test-plane surface resistivity.

Deterministic, offline, python3 standard library only.

The clause anchor requires a composite mounting plane used beneath a unit on
electromagnetic-compatibility test to reproduce the surface resistivity of
the real installation. This module turns that into a checkable procedure:

1. reduce a probe measurement to surface resistivity in ohms per square,
   from a two-probe bar geometry, a collinear four-point probe, or a
   volume-resistivity value over a laminate thickness;
2. categorize a panel as conductive, static-dissipative or insulating;
3. require the test panel and the flight panel to share that regime and to
   agree within a declared decade-deviation;
4. require the fibre-direction anisotropy of the flight laminate to be
   reproduced by the test laminate;
5. check the panel-to-facility bonding path and flag a flight value that was
   never characterized.

Every threshold is a module constant so a programme override is explicit.
"""

import math

__all__ = [
    "FOUR_POINT_GEOMETRY_FACTOR",
    "CONDUCTIVE_CEILING_OHM_PER_SQUARE",
    "DISSIPATIVE_CEILING_OHM_PER_SQUARE",
    "MAX_DECADE_DEVIATION",
    "MAX_ANISOTROPY_DEVIATION",
    "MAX_PANEL_BOND_RESISTANCE_MOHM",
    "PROBE_METHODS",
    "surface_resistivity_two_probe",
    "surface_resistivity_four_point",
    "surface_resistivity_from_volume",
    "surface_resistivity",
    "categorize_resistivity_regime",
    "decade_deviation",
    "anisotropy_ratio",
    "check_flight_characterization",
    "check_regime_match",
    "check_decade_match",
    "check_anisotropy_match",
    "check_panel_bonding",
    "assess_composite_ground_plane",
]

# --- house verification defaults --------------------------------------------

# Collinear four-point probe on a thin sheet much wider than the probe span.
FOUR_POINT_GEOMETRY_FACTOR = math.pi / math.log(2.0)

# Regime boundaries in ohms per square; the lower bound of each band is
# inclusive, so a panel sitting exactly on a boundary falls in the upper band.
CONDUCTIVE_CEILING_OHM_PER_SQUARE = 1.0e4
DISSIPATIVE_CEILING_OHM_PER_SQUARE = 1.0e11

# The test panel has to sit within a factor of two of the flight panel.
MAX_DECADE_DEVIATION = math.log10(2.0)
MAX_ANISOTROPY_DEVIATION = 0.25
MAX_PANEL_BOND_RESISTANCE_MOHM = 10.0

PROBE_METHODS = ("two-probe", "four-point", "volume")

# Representation tolerance: absorbs floating-point representation error on an
# exact-boundary comparison. It never widens the engineering limit.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12

_SEVERITIES = ("major", "minor")


# --- input guards -----------------------------------------------------------


def _as_float(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _as_float(value, label)
    if out <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _as_float(value, label)
    if out < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return out


def _mapping(obj, label):
    if not isinstance(obj, dict):
        raise ValueError("%s must be a mapping, got %s" % (label, type(obj).__name__))
    return obj


def _at_most(value, limit):
    return value <= limit or math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _finding(code, severity, detail):
    if severity not in _SEVERITIES:
        raise ValueError("severity must be one of %s, got %r" % (", ".join(_SEVERITIES), severity))
    return {"code": code, "severity": severity, "detail": detail}


# --- measurement reduction --------------------------------------------------


def surface_resistivity_two_probe(resistance_ohm, bar_width_mm, electrode_spacing_mm):
    """Ohms per square from a two-electrode bar measurement."""
    resistance = _positive(resistance_ohm, "measured resistance")
    width = _positive(bar_width_mm, "bar width")
    spacing = _positive(electrode_spacing_mm, "electrode spacing")
    return resistance * width / spacing


def surface_resistivity_four_point(voltage_v, current_a,
                                   geometry_factor=FOUR_POINT_GEOMETRY_FACTOR):
    """Ohms per square from a collinear four-point probe on a thin sheet."""
    voltage = _non_negative(voltage_v, "probe voltage")
    current = _positive(current_a, "probe current")
    factor = _positive(geometry_factor, "geometry factor")
    return factor * voltage / current


def surface_resistivity_from_volume(volume_resistivity_ohm_m, thickness_mm):
    """Ohms per square from a bulk volume resistivity over a laminate thickness."""
    rho = _positive(volume_resistivity_ohm_m, "volume resistivity")
    thickness = _positive(thickness_mm, "laminate thickness")
    return rho / (thickness / 1000.0)


def surface_resistivity(measurement):
    """Reduce any accepted measurement record to ohms per square."""
    spec = _mapping(measurement, "measurement")
    method = spec.get("method")
    if not isinstance(method, str) or not method.strip():
        raise ValueError("measurement needs a method, got %r" % (method,))
    key = method.strip().lower()
    if key not in PROBE_METHODS:
        raise ValueError(
            "uncategorized measurement method %r; expected one of %s"
            % (method, ", ".join(PROBE_METHODS))
        )
    if key == "two-probe":
        return surface_resistivity_two_probe(
            spec.get("resistance_ohm"),
            spec.get("bar_width_mm"),
            spec.get("electrode_spacing_mm"),
        )
    if key == "four-point":
        return surface_resistivity_four_point(
            spec.get("voltage_v"),
            spec.get("current_a"),
            spec.get("geometry_factor", FOUR_POINT_GEOMETRY_FACTOR),
        )
    return surface_resistivity_from_volume(
        spec.get("volume_resistivity_ohm_m"), spec.get("thickness_mm")
    )


# --- categorization and comparison ------------------------------------------


def categorize_resistivity_regime(ohm_per_square):
    """Place a panel in the conductive, dissipative or insulating band."""
    value = _positive(ohm_per_square, "surface resistivity")
    if value < CONDUCTIVE_CEILING_OHM_PER_SQUARE:
        return "conductive"
    if value < DISSIPATIVE_CEILING_OHM_PER_SQUARE:
        return "static-dissipative"
    return "insulating"


def decade_deviation(test_ohm_per_square, flight_ohm_per_square):
    """Absolute difference in decades between a test and a flight panel."""
    test = _positive(test_ohm_per_square, "test surface resistivity")
    flight = _positive(flight_ohm_per_square, "flight surface resistivity")
    return abs(math.log10(test) - math.log10(flight))


def anisotropy_ratio(warp_ohm_per_square, fill_ohm_per_square):
    """Ratio of the more resistive fibre direction to the less resistive one."""
    warp = _positive(warp_ohm_per_square, "warp-direction surface resistivity")
    fill = _positive(fill_ohm_per_square, "fill-direction surface resistivity")
    return max(warp, fill) / min(warp, fill)


# --- checks -----------------------------------------------------------------


def check_flight_characterization(flight_panel):
    """The real installation has to carry a characterized resistivity."""
    flight = _mapping(flight_panel, "flight panel")
    if flight.get("surface_resistivity_ohm_per_square") is None and \
            flight.get("measurement") is None:
        return [
            _finding(
                "CP-FLIGHT-VALUE-MISSING",
                "major",
                "the real installation carries no characterized surface resistivity, "
                "so the test panel cannot be shown to reproduce it",
            )
        ]
    return []


def _panel_resistivity(panel, label):
    spec = _mapping(panel, label)
    direct = spec.get("surface_resistivity_ohm_per_square")
    if direct is not None:
        return _positive(direct, "%s surface resistivity" % label)
    measurement = spec.get("measurement")
    if measurement is None:
        raise ValueError("%s carries neither a resistivity nor a measurement" % label)
    return surface_resistivity(measurement)


def check_regime_match(flight_panel, test_panel):
    """Both panels have to sit in the same conduction band."""
    flight = categorize_resistivity_regime(_panel_resistivity(flight_panel, "flight panel"))
    test = categorize_resistivity_regime(_panel_resistivity(test_panel, "test panel"))
    if flight == test:
        return []
    return [
        _finding(
            "CP-REGIME-MISMATCH",
            "major",
            "flight panel is %s while the test panel is %s" % (flight, test),
        )
    ]


def check_decade_match(flight_panel, test_panel, max_decades=MAX_DECADE_DEVIATION):
    """The test panel has to agree with the flight panel within the tolerance."""
    limit = _positive(max_decades, "decade tolerance")
    flight = _panel_resistivity(flight_panel, "flight panel")
    test = _panel_resistivity(test_panel, "test panel")
    deviation = decade_deviation(test, flight)
    if _at_most(deviation, limit):
        return []
    return [
        _finding(
            "CP-DECADE-DEVIATION",
            "major",
            "test panel %.4g ohm/square deviates %.4f decades from the flight "
            "panel %.4g ohm/square, beyond the %.4f decade tolerance"
            % (test, deviation, flight, limit),
        )
    ]


def check_anisotropy_match(flight_panel, test_panel):
    """Fibre-direction anisotropy of the flight laminate has to be reproduced."""
    flight = _mapping(flight_panel, "flight panel")
    test = _mapping(test_panel, "test panel")
    flight_pair = flight.get("directional_ohm_per_square")
    test_pair = test.get("directional_ohm_per_square")
    if flight_pair is None and test_pair is None:
        return []
    if flight_pair is None or test_pair is None:
        return [
            _finding(
                "CP-ANISOTROPY-UNCHARACTERIZED",
                "minor",
                "one panel carries directional data and the other does not, so "
                "fibre-direction anisotropy cannot be compared",
            )
        ]
    for pair, label in ((flight_pair, "flight panel"), (test_pair, "test panel")):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError(
                "%s directional data must be a two-element sequence, got %r" % (label, pair)
            )
    flight_ratio = anisotropy_ratio(flight_pair[0], flight_pair[1])
    test_ratio = anisotropy_ratio(test_pair[0], test_pair[1])
    deviation = abs(test_ratio - flight_ratio) / flight_ratio
    if _at_most(deviation, MAX_ANISOTROPY_DEVIATION):
        return []
    return [
        _finding(
            "CP-ANISOTROPY",
            "minor",
            "test laminate anisotropy %.3f deviates %.1f%% from the flight "
            "laminate %.3f" % (test_ratio, deviation * 100.0, flight_ratio),
        )
    ]


def check_panel_bonding(test_panel):
    """The test panel still needs a low-resistance path to the facility."""
    test = _mapping(test_panel, "test panel")
    resistance = test.get("bond_resistance_mohm")
    if resistance is None:
        return [
            _finding(
                "CP-BOND-UNRECORDED",
                "minor",
                "no panel-to-facility bond resistance is on record for the test panel",
            )
        ]
    value = _non_negative(resistance, "panel bond resistance")
    if _at_most(value, MAX_PANEL_BOND_RESISTANCE_MOHM):
        return []
    return [
        _finding(
            "CP-BOND-RESISTANCE",
            "major",
            "panel-to-facility bond %.3f mohm exceeds the %.1f mohm cap"
            % (value, MAX_PANEL_BOND_RESISTANCE_MOHM),
        )
    ]


def check_measurement_method(flight_panel, test_panel):
    """Both panels should be reduced through the same probe geometry."""
    flight = _mapping(flight_panel, "flight panel").get("measurement")
    test = _mapping(test_panel, "test panel").get("measurement")
    if not isinstance(flight, dict) or not isinstance(test, dict):
        return []
    flight_method = str(flight.get("method", "")).strip().lower()
    test_method = str(test.get("method", "")).strip().lower()
    if flight_method and test_method and flight_method != test_method:
        return [
            _finding(
                "CP-METHOD-DEVIATION",
                "minor",
                "flight panel was reduced through a %s measurement and the test "
                "panel through a %s one" % (flight_method, test_method),
            )
        ]
    return []


# --- aggregation ------------------------------------------------------------


def assess_composite_ground_plane(flight_panel, test_panel):
    """Full clause 5.2.3.3 assessment of a composite test mounting plane."""
    flight = _mapping(flight_panel, "flight panel")
    test = _mapping(test_panel, "test panel")
    findings = list(check_flight_characterization(flight))
    if any(item["code"] == "CP-FLIGHT-VALUE-MISSING" for item in findings):
        test_value = _panel_resistivity(test, "test panel")
        return {
            "findings": findings,
            "codes": [item["code"] for item in findings],
            "counts": {"major": 1, "minor": 0},
            "test_ohm_per_square": test_value,
            "flight_ohm_per_square": None,
            "test_regime": categorize_resistivity_regime(test_value),
            "flight_regime": None,
            "decade_deviation": None,
            "compliant": False,
            "clean": False,
        }
    flight_value = _panel_resistivity(flight, "flight panel")
    test_value = _panel_resistivity(test, "test panel")
    findings.extend(check_regime_match(flight, test))
    findings.extend(check_decade_match(flight, test))
    findings.extend(check_anisotropy_match(flight, test))
    findings.extend(check_panel_bonding(test))
    findings.extend(check_measurement_method(flight, test))
    majors = sum(1 for item in findings if item["severity"] == "major")
    minors = len(findings) - majors
    return {
        "findings": findings,
        "codes": [item["code"] for item in findings],
        "counts": {"major": majors, "minor": minors},
        "test_ohm_per_square": test_value,
        "flight_ohm_per_square": flight_value,
        "test_regime": categorize_resistivity_regime(test_value),
        "flight_regime": categorize_resistivity_regime(flight_value),
        "decade_deviation": decade_deviation(test_value, flight_value),
        "compliant": majors == 0,
        "clean": len(findings) == 0,
    }
