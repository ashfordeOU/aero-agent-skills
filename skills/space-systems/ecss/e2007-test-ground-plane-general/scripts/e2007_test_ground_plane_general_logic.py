"""ECSS-E-ST-20-07C clause 5.2.3.1 -- general test ground-plane arrangement.

Deterministic, offline, python3 standard library only.

The clause anchor requires the unit under electromagnetic-compatibility test
to sit on a ground plane that reproduces the known flight installation
arrangement. This module turns that requirement into a checkable procedure:

1. establish whether the flight installation arrangement is known at all
   (an unknown arrangement is a finding, not a silent pass);
2. resolve the conduction family of the flight mounting panel and of the
   proposed test plane and require them to agree;
3. check the geometry of the test plane against the unit footprint
   (plane area, shortest edge, front set-back, lateral extension);
4. check the plane-to-facility bonding path (bond-point count and the
   direct-current resistance of the strap chain);
5. check that a flight mounting isolator or stand-off is reproduced rather
   than replaced by a hard-mounted interface.

All limits below are the house verification defaults used by this leaf; a
programme may tighten them, and every threshold is exposed as a module
constant so a caller can override it explicitly rather than by accident.
"""

import math

__all__ = [
    "MATERIAL_FAMILY",
    "INTERFACE_KINDS",
    "MIN_PLANE_AREA_M2",
    "MIN_PLANE_EDGE_MM",
    "NOMINAL_FRONT_SETBACK_MM",
    "FRONT_SETBACK_TOLERANCE_MM",
    "MIN_SIDE_EXTENSION_MM",
    "MIN_PLANE_BOND_POINTS",
    "MAX_PLANE_BOND_RESISTANCE_MOHM",
    "resolve_plane_family",
    "normalize_interface_kind",
    "plane_area_m2",
    "side_extension_mm",
    "series_bond_resistance_mohm",
    "check_installation_knowledge",
    "check_plane_geometry",
    "check_material_representativeness",
    "check_bond_representativeness",
    "check_isolator_representation",
    "summarize_findings",
    "assess_test_ground_plane",
]

# --- house verification defaults -------------------------------------------

MIN_PLANE_AREA_M2 = 2.25
MIN_PLANE_EDGE_MM = 760.0
NOMINAL_FRONT_SETBACK_MM = 100.0
FRONT_SETBACK_TOLERANCE_MM = 20.0
MIN_SIDE_EXTENSION_MM = 500.0
MIN_PLANE_BOND_POINTS = 2
MAX_PLANE_BOND_RESISTANCE_MOHM = 2.5

# Representation tolerance: absorbs floating-point representation error on an
# exact-boundary comparison. It never widens the engineering limit.
_REL_TOL = 1e-9
_ABS_TOL = 1e-12

MATERIAL_FAMILY = {
    "aluminium": "metallic",
    "aluminum": "metallic",
    "copper": "metallic",
    "brass": "metallic",
    "stainless-steel": "metallic",
    "magnesium": "metallic",
    "cfrp": "composite",
    "cfrp-honeycomb": "composite",
    "carbon-fibre-skin": "composite",
    "gfrp": "dielectric",
    "glass-fibre-skin": "dielectric",
    "polyimide-film": "dielectric",
}

INTERFACE_KINDS = ("hard-mounted", "isolator-mounted", "stand-off-mounted")

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


def _as_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _mapping(obj, label):
    if not isinstance(obj, dict):
        raise ValueError("%s must be a mapping, got %s" % (label, type(obj).__name__))
    return obj


def _at_least(value, limit):
    return value >= limit or math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_most(value, limit):
    return value <= limit or math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _finding(code, severity, detail):
    if severity not in _SEVERITIES:
        raise ValueError("severity must be one of %s, got %r" % (", ".join(_SEVERITIES), severity))
    return {"code": code, "severity": severity, "detail": detail}


# --- primitives -------------------------------------------------------------


def resolve_plane_family(material):
    """Map a plane or mounting-panel material onto its conduction family."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("plane material must be a non-empty string, got %r" % (material,))
    key = material.strip().lower()
    if key not in MATERIAL_FAMILY:
        raise ValueError(
            "uncategorized plane material %r; add it to MATERIAL_FAMILY before use" % (material,)
        )
    return MATERIAL_FAMILY[key]


def normalize_interface_kind(kind):
    """Normalize the mounting-interface kind of a unit onto the plane."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("interface kind must be a non-empty string, got %r" % (kind,))
    key = kind.strip().lower()
    if key not in INTERFACE_KINDS:
        raise ValueError(
            "uncategorized interface kind %r; expected one of %s"
            % (kind, ", ".join(INTERFACE_KINDS))
        )
    return key


def plane_area_m2(length_mm, width_mm):
    """Plane area in square metres from millimetre edge dimensions."""
    length = _positive(length_mm, "plane length")
    width = _positive(width_mm, "plane width")
    return (length / 1000.0) * (width / 1000.0)


def side_extension_mm(plane_dim_mm, unit_dim_mm):
    """Symmetric extension of the plane beyond the unit footprint, per side."""
    plane = _positive(plane_dim_mm, "plane dimension")
    unit = _positive(unit_dim_mm, "unit footprint dimension")
    if unit > plane:
        raise ValueError(
            "unit footprint %.1f mm exceeds plane dimension %.1f mm" % (unit, plane)
        )
    return (plane - unit) / 2.0


def series_bond_resistance_mohm(segments):
    """Direct-current resistance of a series strap chain, in milliohms."""
    if not isinstance(segments, (list, tuple)):
        raise ValueError("bond segments must be a list or tuple, got %s" % type(segments).__name__)
    if not segments:
        raise ValueError("bond segments must not be empty")
    total = 0.0
    for index, segment in enumerate(segments):
        total += _non_negative(segment, "bond segment %d resistance" % index)
    return total


# --- individual checks ------------------------------------------------------


def check_installation_knowledge(flight_installation):
    """Clause gate: the flight arrangement has to be known or bounded."""
    flight = _mapping(flight_installation, "flight installation")
    known = flight.get("arrangement_known", False)
    if not isinstance(known, bool):
        raise ValueError("arrangement_known must be a boolean, got %r" % (known,))
    if known:
        return []
    bounded = flight.get("worst_case_declared", False)
    if not isinstance(bounded, bool):
        raise ValueError("worst_case_declared must be a boolean, got %r" % (bounded,))
    if bounded:
        return [
            _finding(
                "GP-ARRANGEMENT-BOUNDED",
                "minor",
                "flight arrangement unknown; a declared worst-case stands in for it "
                "and has to be recorded in the verification report",
            )
        ]
    return [
        _finding(
            "GP-ARRANGEMENT-UNKNOWN",
            "major",
            "flight installation arrangement is neither known nor bounded by a "
            "declared worst-case, so the test plane cannot be shown representative",
        )
    ]


def check_plane_geometry(test_setup):
    """Plane area, shortest edge, unit set-back and lateral extension."""
    setup = _mapping(test_setup, "test setup")
    length = _positive(setup.get("plane_length_mm"), "plane length")
    width = _positive(setup.get("plane_width_mm"), "plane width")
    unit_length = _positive(setup.get("unit_length_mm"), "unit footprint length")
    unit_width = _positive(setup.get("unit_width_mm"), "unit footprint width")
    setback = _non_negative(setup.get("front_setback_mm", NOMINAL_FRONT_SETBACK_MM), "front set-back")

    findings = []
    area = plane_area_m2(length, width)
    if not _at_least(area, MIN_PLANE_AREA_M2):
        findings.append(
            _finding(
                "GP-AREA",
                "major",
                "plane area %.3f m2 is below the %.2f m2 floor" % (area, MIN_PLANE_AREA_M2),
            )
        )
    shortest_edge = min(length, width)
    if not _at_least(shortest_edge, MIN_PLANE_EDGE_MM):
        findings.append(
            _finding(
                "GP-EDGE",
                "major",
                "shortest plane edge %.1f mm is below the %.1f mm floor"
                % (shortest_edge, MIN_PLANE_EDGE_MM),
            )
        )
    lateral = side_extension_mm(width, unit_width)
    if not _at_least(lateral, MIN_SIDE_EXTENSION_MM):
        findings.append(
            _finding(
                "GP-EXTENT",
                "major",
                "lateral extension %.1f mm beyond the unit footprint is below the "
                "%.1f mm floor" % (lateral, MIN_SIDE_EXTENSION_MM),
            )
        )
    deviation = abs(setback - NOMINAL_FRONT_SETBACK_MM)
    if not _at_most(deviation, FRONT_SETBACK_TOLERANCE_MM):
        findings.append(
            _finding(
                "GP-SETBACK",
                "minor",
                "front set-back %.1f mm deviates %.1f mm from the %.1f mm nominal"
                % (setback, deviation, NOMINAL_FRONT_SETBACK_MM),
            )
        )
    return findings


def check_material_representativeness(flight_installation, test_setup):
    """The test plane has to share the flight panel's conduction family."""
    flight = _mapping(flight_installation, "flight installation")
    setup = _mapping(test_setup, "test setup")
    flight_material = flight.get("panel_material")
    test_material = setup.get("plane_material")
    flight_family = resolve_plane_family(flight_material)
    test_family = resolve_plane_family(test_material)
    if flight_family != test_family:
        return [
            _finding(
                "GP-MATERIAL-FAMILY",
                "major",
                "flight panel family %r is not reproduced by test plane family %r"
                % (flight_family, test_family),
            )
        ]
    if flight_material.strip().lower() != test_material.strip().lower():
        return [
            _finding(
                "GP-MATERIAL-GRADE",
                "minor",
                "same %s family but the test plane is %r against a flight panel of %r"
                % (flight_family, test_material, flight_material),
            )
        ]
    return []


def check_bond_representativeness(flight_installation, test_setup):
    """Bond-point count and strap-chain resistance of the plane interface."""
    flight = _mapping(flight_installation, "flight installation")
    setup = _mapping(test_setup, "test setup")
    test_points = _as_int(setup.get("bond_points", 0), "test bond-point count")
    flight_points = _as_int(flight.get("bond_points", 0), "flight bond-point count")
    segments = setup.get("bond_segments_mohm")
    if segments is None:
        resistance = _non_negative(
            setup.get("bond_resistance_mohm", 0.0), "test bond resistance"
        )
    else:
        resistance = series_bond_resistance_mohm(segments)

    findings = []
    if test_points < MIN_PLANE_BOND_POINTS:
        findings.append(
            _finding(
                "GP-BOND-POINTS",
                "major",
                "test plane carries %d bond points against a floor of %d"
                % (test_points, MIN_PLANE_BOND_POINTS),
            )
        )
    if not _at_most(resistance, MAX_PLANE_BOND_RESISTANCE_MOHM):
        findings.append(
            _finding(
                "GP-BOND-RESISTANCE",
                "major",
                "plane-to-facility bond chain %.4f mohm exceeds the %.2f mohm cap"
                % (resistance, MAX_PLANE_BOND_RESISTANCE_MOHM),
            )
        )
    if test_points >= MIN_PLANE_BOND_POINTS and test_points < flight_points:
        findings.append(
            _finding(
                "GP-BOND-UNDER-REPRESENTED",
                "minor",
                "test plane carries %d bond points against %d in the flight "
                "installation" % (test_points, flight_points),
            )
        )
    return findings


def check_isolator_representation(flight_installation, test_setup):
    """A flight isolator or stand-off has to be reproduced, not removed."""
    flight = _mapping(flight_installation, "flight installation")
    setup = _mapping(test_setup, "test setup")
    flight_kind = normalize_interface_kind(flight.get("interface_kind"))
    test_kind = normalize_interface_kind(setup.get("interface_kind"))
    if flight_kind == test_kind:
        return []
    if flight_kind == "isolator-mounted":
        return [
            _finding(
                "GP-ISOLATOR-MISSING",
                "major",
                "flight unit is isolator-mounted but the test setup is %s, which "
                "short-circuits the flight return path" % test_kind,
            )
        ]
    if test_kind == "isolator-mounted":
        return [
            _finding(
                "GP-ISOLATOR-ADDED",
                "major",
                "test setup adds an isolator absent from the %s flight interface"
                % flight_kind,
            )
        ]
    return [
        _finding(
            "GP-INTERFACE-DEVIATION",
            "minor",
            "flight interface %s is reproduced as %s" % (flight_kind, test_kind),
        )
    ]


# --- aggregation ------------------------------------------------------------


def summarize_findings(findings):
    """Count findings by severity."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a list or tuple, got %s" % type(findings).__name__)
    counts = {"major": 0, "minor": 0}
    for item in findings:
        severity = _mapping(item, "finding").get("severity")
        if severity not in counts:
            raise ValueError("finding carries an unknown severity %r" % (severity,))
        counts[severity] += 1
    return counts


def assess_test_ground_plane(flight_installation, test_setup):
    """Full clause 5.2.3.1 representativeness assessment of a test plane."""
    flight = _mapping(flight_installation, "flight installation")
    setup = _mapping(test_setup, "test setup")
    findings = []
    findings.extend(check_installation_knowledge(flight))
    findings.extend(check_plane_geometry(setup))
    findings.extend(check_material_representativeness(flight, setup))
    findings.extend(check_bond_representativeness(flight, setup))
    findings.extend(check_isolator_representation(flight, setup))
    counts = summarize_findings(findings)
    return {
        "findings": findings,
        "codes": [item["code"] for item in findings],
        "counts": counts,
        "plane_area_m2": plane_area_m2(setup["plane_length_mm"], setup["plane_width_mm"]),
        "lateral_extension_mm": side_extension_mm(
            setup["plane_width_mm"], setup["unit_width_mm"]
        ),
        "compliant": counts["major"] == 0,
        "fully_representative": counts["major"] == 0 and counts["minor"] == 0,
    }
