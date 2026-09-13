"""ECSS-E-ST-20-07C clause 5.2.3.2 -- metallic test ground-plane resistance.

Deterministic, offline, python3 standard library only.

The clause anchor caps the direct-current surface resistance of a metallic
plane used beneath a unit on electromagnetic-compatibility test. This module
turns that cap into a checkable computation:

1. resolve the bulk resistivity of the plane material at the plane's working
   temperature from its twenty-degree value and temperature coefficient;
2. derive the sheet resistance in milliohms per square from resistivity and
   conductive thickness;
3. count the squares along the current path and derive the end-to-end path
   resistance, adding the resistance of every riveted, bolted or welded
   joint and every bond strap in the chain;
4. reject a mating face whose surface finish is not conductive;
5. derive the minimum conductive thickness that still meets the cap, and
   reconcile a measured sheet resistance against the computed one.

Every threshold is a module constant so a programme override is explicit.
"""

import math

__all__ = [
    "MATERIALS",
    "FINISH_CONTACT_MOHM",
    "NON_CONDUCTIVE_FINISHES",
    "JOINT_KINDS",
    "MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE",
    "MAX_PATH_RESISTANCE_MOHM",
    "MAX_JOINT_RESISTANCE_MOHM",
    "MEASURED_DEVIATION_FRACTION",
    "THICKNESS_MARGIN_FACTOR",
    "ABSOLUTE_ZERO_C",
    "resistivity_at_temperature",
    "sheet_resistance_mohm_per_square",
    "squares_along_path",
    "path_resistance_mohm",
    "joint_resistance_mohm",
    "chain_resistance_mohm",
    "minimum_conductive_thickness_mm",
    "finish_contact_resistance_mohm",
    "check_sheet_resistance",
    "assess_metallic_ground_plane",
]

# --- clause caps and house defaults -----------------------------------------

MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE = 0.1
MAX_PATH_RESISTANCE_MOHM = 2.5
MAX_JOINT_RESISTANCE_MOHM = 1.0
MEASURED_DEVIATION_FRACTION = 0.30
THICKNESS_MARGIN_FACTOR = 1.2
ABSOLUTE_ZERO_C = -273.15

# Representation tolerance: absorbs floating-point representation error on an
# exact-boundary comparison. It never widens the engineering cap.
_REL_TOL = 1e-9
_ABS_TOL = 1e-15

# Bulk resistivity at 20 degrees Celsius (ohm metre) and the linear
# temperature coefficient (per kelvin) of each accepted plane material.
MATERIALS = {
    "aluminium": {"rho20_ohm_m": 2.65e-8, "alpha_per_k": 0.00429},
    "aluminum": {"rho20_ohm_m": 2.65e-8, "alpha_per_k": 0.00429},
    "copper": {"rho20_ohm_m": 1.68e-8, "alpha_per_k": 0.00393},
    "brass": {"rho20_ohm_m": 7.00e-8, "alpha_per_k": 0.00150},
    "magnesium": {"rho20_ohm_m": 4.39e-8, "alpha_per_k": 0.00400},
    "stainless-steel": {"rho20_ohm_m": 7.20e-7, "alpha_per_k": 0.00094},
    "silver": {"rho20_ohm_m": 1.59e-8, "alpha_per_k": 0.00380},
}

# Added contact resistance of a mating face finish, in milliohms.
FINISH_CONTACT_MOHM = {
    "bare": 0.00,
    "chemical-conversion": 0.10,
    "alodine": 0.10,
    "tin-plated": 0.05,
    "gold-plated": 0.02,
    "silver-plated": 0.02,
}

NON_CONDUCTIVE_FINISHES = ("anodized", "hard-anodized", "painted", "primed")

JOINT_KINDS = {
    "welded": 0.05,
    "bolted": 0.30,
    "riveted": 0.50,
    "bond-strap": 0.80,
}

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


def _material(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("plane material must be a non-empty string, got %r" % (name,))
    key = name.strip().lower()
    if key not in MATERIALS:
        raise ValueError(
            "uncategorized plane material %r; add it to MATERIALS before use" % (name,)
        )
    return MATERIALS[key]


# --- primitives -------------------------------------------------------------


def resistivity_at_temperature(material, temperature_c=20.0):
    """Bulk resistivity in ohm metre, corrected to the working temperature."""
    entry = _material(material)
    temperature = _as_float(temperature_c, "plane temperature")
    if temperature <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "plane temperature %.2f C is at or below absolute zero" % (temperature,)
        )
    rho = entry["rho20_ohm_m"] * (1.0 + entry["alpha_per_k"] * (temperature - 20.0))
    if rho <= 0.0:
        raise ValueError(
            "temperature %.2f C drives %r to a non-physical resistivity" % (temperature, material)
        )
    return rho


def sheet_resistance_mohm_per_square(material, thickness_mm, temperature_c=20.0):
    """Sheet resistance in milliohms per square from resistivity over thickness."""
    thickness = _positive(thickness_mm, "conductive thickness")
    rho = resistivity_at_temperature(material, temperature_c)
    return (rho / (thickness / 1000.0)) * 1000.0


def squares_along_path(length_mm, width_mm):
    """Number of squares along the current path (length over width)."""
    length = _positive(length_mm, "current-path length")
    width = _positive(width_mm, "current-path width")
    return length / width


def path_resistance_mohm(material, thickness_mm, length_mm, width_mm, temperature_c=20.0):
    """End-to-end sheet contribution of one plane run, in milliohms."""
    sheet = sheet_resistance_mohm_per_square(material, thickness_mm, temperature_c)
    return sheet * squares_along_path(length_mm, width_mm)


def joint_resistance_mohm(joint):
    """Resistance of one joint: the measured value, else the kind default."""
    spec = _mapping(joint, "joint")
    if "resistance_mohm" in spec and spec["resistance_mohm"] is not None:
        return _non_negative(spec["resistance_mohm"], "joint resistance")
    kind = spec.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("joint needs a measured resistance or a kind, got %r" % (spec,))
    key = kind.strip().lower()
    if key not in JOINT_KINDS:
        raise ValueError(
            "uncategorized joint kind %r; expected one of %s"
            % (kind, ", ".join(sorted(JOINT_KINDS)))
        )
    return JOINT_KINDS[key]


def chain_resistance_mohm(segments, joints=()):
    """Series resistance of plane runs plus the joints that link them."""
    if not isinstance(segments, (list, tuple)):
        raise ValueError("segments must be a list or tuple, got %s" % type(segments).__name__)
    if not segments:
        raise ValueError("segments must not be empty")
    if not isinstance(joints, (list, tuple)):
        raise ValueError("joints must be a list or tuple, got %s" % type(joints).__name__)
    total = 0.0
    for index, segment in enumerate(segments):
        spec = _mapping(segment, "segment %d" % index)
        total += path_resistance_mohm(
            spec.get("material"),
            spec.get("thickness_mm"),
            spec.get("length_mm"),
            spec.get("width_mm"),
            spec.get("temperature_c", 20.0),
        )
    for joint in joints:
        total += joint_resistance_mohm(joint)
    return total


def minimum_conductive_thickness_mm(material, temperature_c=20.0,
                                    cap_mohm_per_square=MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE):
    """Thinnest plane of this material that still meets the sheet-resistance cap."""
    cap = _positive(cap_mohm_per_square, "sheet-resistance cap")
    rho = resistivity_at_temperature(material, temperature_c)
    return (rho / (cap / 1000.0)) * 1000.0


def finish_contact_resistance_mohm(finish):
    """Contact resistance added by a mating-face finish, in milliohms."""
    if not isinstance(finish, str) or not finish.strip():
        raise ValueError("surface finish must be a non-empty string, got %r" % (finish,))
    key = finish.strip().lower()
    if key in NON_CONDUCTIVE_FINISHES:
        return None
    if key not in FINISH_CONTACT_MOHM:
        raise ValueError(
            "uncategorized surface finish %r; add it to FINISH_CONTACT_MOHM or "
            "NON_CONDUCTIVE_FINISHES before use" % (finish,)
        )
    return FINISH_CONTACT_MOHM[key]


# --- checks -----------------------------------------------------------------


def check_sheet_resistance(material, thickness_mm, temperature_c=20.0):
    """Compare the computed sheet resistance against the clause cap."""
    sheet = sheet_resistance_mohm_per_square(material, thickness_mm, temperature_c)
    within = _at_most(sheet, MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE)
    return {
        "sheet_resistance_mohm_per_square": sheet,
        "cap_mohm_per_square": MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE,
        "margin_mohm_per_square": MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE - sheet,
        "within_cap": within,
        "minimum_thickness_mm": minimum_conductive_thickness_mm(material, temperature_c),
    }


def assess_metallic_ground_plane(plane):
    """Full clause 5.2.3.2 assessment of a metallic test ground plane."""
    spec = _mapping(plane, "plane")
    material = spec.get("material")
    thickness = _positive(spec.get("thickness_mm"), "conductive thickness")
    temperature = _as_float(spec.get("temperature_c", 20.0), "plane temperature")
    length = _positive(spec.get("current_path_length_mm"), "current-path length")
    width = _positive(spec.get("current_path_width_mm"), "current-path width")
    joints = spec.get("joints", ())
    if not isinstance(joints, (list, tuple)):
        raise ValueError("joints must be a list or tuple, got %s" % type(joints).__name__)

    findings = []
    sheet_report = check_sheet_resistance(material, thickness, temperature)
    if not sheet_report["within_cap"]:
        findings.append(
            _finding(
                "MG-SHEET-CAP",
                "major",
                "sheet resistance %.6f mohm/square exceeds the %.3f mohm/square cap; "
                "at least %.4f mm of conductive thickness is needed"
                % (
                    sheet_report["sheet_resistance_mohm_per_square"],
                    MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE,
                    sheet_report["minimum_thickness_mm"],
                ),
            )
        )
    elif thickness < sheet_report["minimum_thickness_mm"] * THICKNESS_MARGIN_FACTOR:
        findings.append(
            _finding(
                "MG-THICKNESS-MARGIN",
                "minor",
                "thickness %.4f mm meets the cap but sits under the %.2fx margin "
                "over the %.4f mm minimum"
                % (thickness, THICKNESS_MARGIN_FACTOR, sheet_report["minimum_thickness_mm"]),
            )
        )

    contact = 0.0
    finish = spec.get("mating_face_finish", "bare")
    finish_penalty = finish_contact_resistance_mohm(finish)
    if finish_penalty is None:
        findings.append(
            _finding(
                "MG-FINISH-NON-CONDUCTIVE",
                "major",
                "mating face finish %r is not conductive and breaks the "
                "direct-current path into the plane" % (finish,),
            )
        )
    else:
        contact = finish_penalty

    joint_total = 0.0
    for index, joint in enumerate(joints):
        value = joint_resistance_mohm(joint)
        joint_total += value
        if not _at_most(value, MAX_JOINT_RESISTANCE_MOHM):
            findings.append(
                _finding(
                    "MG-JOINT-CAP",
                    "major",
                    "joint %d at %.4f mohm exceeds the %.2f mohm per-joint cap"
                    % (index, value, MAX_JOINT_RESISTANCE_MOHM),
                )
            )

    squares = squares_along_path(length, width)
    sheet_contribution = sheet_report["sheet_resistance_mohm_per_square"] * squares
    path_total = sheet_contribution + joint_total + contact
    if not _at_most(path_total, MAX_PATH_RESISTANCE_MOHM):
        findings.append(
            _finding(
                "MG-PATH-CAP",
                "major",
                "end-to-end path %.4f mohm exceeds the %.2f mohm cap"
                % (path_total, MAX_PATH_RESISTANCE_MOHM),
            )
        )

    measured = spec.get("measured_sheet_resistance_mohm_per_square")
    if measured is not None:
        measured = _non_negative(measured, "measured sheet resistance")
        computed = sheet_report["sheet_resistance_mohm_per_square"]
        deviation = abs(measured - computed) / computed
        if not _at_most(deviation, MEASURED_DEVIATION_FRACTION):
            findings.append(
                _finding(
                    "MG-MEASURED-DEVIATION",
                    "minor",
                    "measured %.6f mohm/square deviates %.1f%% from the computed "
                    "%.6f mohm/square" % (measured, deviation * 100.0, computed),
                )
            )
        if not _at_most(measured, MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE):
            findings.append(
                _finding(
                    "MG-MEASURED-CAP",
                    "major",
                    "measured sheet resistance %.6f mohm/square exceeds the "
                    "%.3f mohm/square cap"
                    % (measured, MAX_SHEET_RESISTANCE_MOHM_PER_SQUARE),
                )
            )

    majors = sum(1 for item in findings if item["severity"] == "major")
    minors = len(findings) - majors
    return {
        "findings": findings,
        "codes": [item["code"] for item in findings],
        "counts": {"major": majors, "minor": minors},
        "sheet_resistance_mohm_per_square": sheet_report["sheet_resistance_mohm_per_square"],
        "minimum_thickness_mm": sheet_report["minimum_thickness_mm"],
        "squares": squares,
        "joint_resistance_mohm": joint_total,
        "contact_resistance_mohm": contact,
        "path_resistance_mohm": path_total,
        "compliant": majors == 0,
        "clean": len(findings) == 0,
    }
