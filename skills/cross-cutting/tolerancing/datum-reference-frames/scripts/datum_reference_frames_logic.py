#!/usr/bin/env python3
"""Datum reference frame logic (paraphrase, common GD&T knowledge).

Common-knowledge summary (standards-map.yaml, asme-y14-5: proprietary,
reference-only): a datum reference frame is the coordinate system
established from the datum features of a part, taken in precedence
order. The primary datum is the datum feature that establishes the
frame first, the secondary datum locates the frame in the next
direction, and the tertiary datum finishes the location. Each datum
feature has a simulator: a planar surface is simulated by a plane, a
cylindrical surface (hole, pin, shaft) by its axis, and a spherical
surface by a point. Six degrees of freedom exist: three translations
(tx, ty, tz) and three rotations (rx, ry, rz). A plane constrains one
translation (along its normal) and two rotations (tilting about the
in-plane axes); an axis constrains two translations (perpendicular to
the axis) and two rotations; a point constrains three translations.
In a frame, each datum constrains only the degrees of freedom not
already constrained by the earlier datums, so the precedence order
changes the constraint table. Material condition modifiers on datum
feature references set the simulator boundary: RMB (regardless of
material boundary) fixes the simulator with zero datum shift, MMB
(maximum material boundary) permits datum shift equal to the
departure of the actual mating size from the MMB size, and LMB (least
material boundary) permits datum shift equal to the departure from
the LMB size. The feature control frame is the drawing callout:
geometric characteristic symbol, tolerance value with optional
diameter symbol and material condition modifier, then the datum
feature references with their modifiers. Units: any consistent length
unit (mm, inch).

Module is pure stdlib, deterministic, offline.
"""

import math

# Canonical degree-of-freedom order and labels.
DOF_ORDER = ("tx", "ty", "tz", "rx", "ry", "rz")
DOF_LABELS = {
    "tx": "translation x",
    "ty": "translation y",
    "tz": "translation z",
    "rx": "rotation x",
    "ry": "rotation y",
    "rz": "rotation z",
}

DATUM_FEATURE_TYPES = ("plane", "axis", "point")
ORIENTATIONS = ("x", "y", "z")
PRECEDENCE_NAMES = ("primary", "secondary", "tertiary")
MATERIAL_MODIFIERS = ("rmb", "mmb", "lmb")
FEATURE_KINDS = ("hole", "pin")
TOLERANCE_MODIFIERS = ("mmc", "lmc", "rfs")

# Simulator produced by each datum feature type.
SIMULATORS = {
    "plane": "plane",
    "axis": "axis",
    "point": "point",
}

# Degrees of freedom constrained by a plane whose normal aligns with
# the given orientation axis: one translation plus two rotations.
_PLANE_DOF = {
    "x": frozenset(("tx", "ry", "rz")),
    "y": frozenset(("ty", "rx", "rz")),
    "z": frozenset(("tz", "rx", "ry")),
}

# Degrees of freedom constrained by an axis (cylinder centerline)
# aligned with the given orientation axis: two translations
# perpendicular to the axis plus two rotations about axes
# perpendicular to it.
_AXIS_DOF = {
    "x": frozenset(("ty", "tz", "ry", "rz")),
    "y": frozenset(("tx", "tz", "rx", "rz")),
    "z": frozenset(("tx", "ty", "rx", "ry")),
}

# A point (spherical datum feature) constrains all three translations.
_POINT_DOF = frozenset(("tx", "ty", "tz"))

# Feature control frame symbols for the supported characteristics.
CHARACTERISTIC_SYMBOLS = {
    "position": "\u2316",
    "flatness": "\u2313",
    "straightness": "\u23e4",
    "circularity": "\u25cb",
    "cylindricity": "\u232d",
    "perpendicularity": "\u22a5",
    "parallelism": "\u2225",
    "angularity": "\u2220",
    "concentricity": "\u25ce",
    "symmetry": "\u232f",
    "circular-runout": "\u2197",
    "total-runout": "\u2330",
}

# Characteristics whose tolerance zone is a cylinder: the tolerance
# value carries the diameter symbol.
_DIAMETER_CHARACTERISTICS = frozenset(
    ("position", "concentricity", "symmetry", "cylindricity")
)

# Material condition modifier suffixes on the tolerance value.
_TOLERANCE_MODIFIER_SUFFIX = {
    "mmc": "\u24c2",
    "lmc": "\u24c1",
    "rfs": "\u24c8",
}

# Material condition modifier suffixes on datum feature references.
_DATUM_MODIFIER_SUFFIX = {
    "rmb": "",
    "mmb": "\u24c2",
    "lmb": "\u24c1",
}


def _finite(value, label):
    """Require a finite real number; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(float(value)):
        raise ValueError("%s must be finite, got %r" % (label, value))


def _validate_orientation(orientation):
    """Require an orientation in ('x', 'y', 'z'); raise otherwise."""
    if orientation not in ORIENTATIONS:
        raise ValueError(
            "orientation must be one of %s, got %r"
            % (", ".join(ORIENTATIONS), orientation)
        )
    return orientation


def _validate_feature_type(feature_type):
    """Require a datum feature type in ('plane', 'axis', 'point')."""
    if feature_type not in DATUM_FEATURE_TYPES:
        raise ValueError(
            "feature_type must be one of %s, got %r"
            % (", ".join(DATUM_FEATURE_TYPES), feature_type)
        )
    return feature_type


def _validate_modifier(modifier):
    """Require a material condition modifier in ('rmb', 'mmb', 'lmb')."""
    if modifier not in MATERIAL_MODIFIERS:
        raise ValueError(
            "modifier must be one of %s, got %r"
            % (", ".join(MATERIAL_MODIFIERS), modifier)
        )
    return modifier


def _validate_letter(letter):
    """Require a single uppercase letter datum identifier."""
    if not isinstance(letter, str) or len(letter) != 1 or not letter.isalpha():
        raise ValueError("datum letter must be a single letter, got %r" % (letter,))
    if not letter.isupper():
        raise ValueError("datum letter must be uppercase, got %r" % (letter,))
    return letter


def _sort_dof(dof):
    """Sort a set of DOF names into the canonical order."""
    return [name for name in DOF_ORDER if name in dof]


def dof_set(feature_type, orientation):
    """Degrees of freedom constrained by a datum feature simulator.

    A plane constrains one translation and two rotations; an axis
    constrains two translations and two rotations; a point constrains
    three translations. Raises ValueError on an unknown feature type
    or orientation.
    """
    _validate_feature_type(feature_type)
    _validate_orientation(orientation)
    if feature_type == "plane":
        return frozenset(_PLANE_DOF[orientation])
    if feature_type == "axis":
        return frozenset(_AXIS_DOF[orientation])
    return frozenset(_POINT_DOF)


def dof_label(dof):
    """Human-readable label for a DOF name, e.g. 'tx' -> 'translation x'."""
    if dof not in DOF_LABELS:
        raise ValueError("unknown DOF name %r" % (dof,))
    return DOF_LABELS[dof]


def _normalize_datum(datum, default_letter):
    """Validate one datum feature reference and fill defaults.

    Accepts a dict with keys feature_type, orientation, modifier
    (default 'rmb') and letter (default from precedence). Returns the
    normalized dict.
    """
    if not isinstance(datum, dict):
        raise ValueError("datum must be a dict, got %r" % (datum,))
    feature_type = datum.get("feature_type")
    orientation = datum.get("orientation")
    modifier = datum.get("modifier", "rmb")
    letter = datum.get("letter", default_letter)
    feature_type = _validate_feature_type(feature_type)
    orientation = _validate_orientation(orientation)
    modifier = _validate_modifier(modifier)
    letter = _validate_letter(letter)
    return {
        "letter": letter,
        "feature_type": feature_type,
        "orientation": orientation,
        "modifier": modifier,
        "simulator": SIMULATORS[feature_type],
    }


def parse_datum_precedence(primary, secondary=None, tertiary=None):
    """Parse and validate the datum precedence into normalized references.

    The primary datum is required; secondary and tertiary are
    optional. Letters default to A, B, C in precedence order when a
    datum dict does not carry its own letter. Returns a list of
    normalized datum dicts in precedence order. Raises ValueError on
    an invalid datum or a duplicated letter.
    """
    datums = []
    for rank, raw in ((0, primary), (1, secondary), (2, tertiary)):
        if raw is None:
            continue
        normalized = _normalize_datum(raw, "ABC"[rank])
        letters = [d["letter"] for d in datums]
        if normalized["letter"] in letters:
            raise ValueError(
                "duplicate datum letter %r in precedence" % (normalized["letter"],)
            )
        datums.append(normalized)
    return datums


def datum_reference_frame(primary, secondary=None, tertiary=None):
    """Establish the datum reference frame from the datum precedence.

    Builds the frame definition: the normalized datum references with
    their simulators, the degrees of freedom each datum constrains in
    the frame (its own DOF set minus everything already constrained by
    earlier datums), the constrained and unconstrained DOF lists, and
    the constrained count. Raises ValueError on invalid input.
    """
    datums = parse_datum_precedence(primary, secondary, tertiary)
    constrained = set()
    dof_table = []
    for rank, datum in enumerate(datums):
        own = set(dof_set(datum["feature_type"], datum["orientation"]))
        remaining = own - constrained
        constrained |= own
        dof_table.append(
            {
                "letter": datum["letter"],
                "precedence": PRECEDENCE_NAMES[rank],
                "feature_type": datum["feature_type"],
                "orientation": datum["orientation"],
                "simulator": datum["simulator"],
                "modifier": datum["modifier"],
                "dof": _sort_dof(remaining),
                "count": len(remaining),
            }
        )
    unconstrained = [name for name in DOF_ORDER if name not in constrained]
    return {
        "datums": datums,
        "dof_table": dof_table,
        "constrained": _sort_dof(constrained),
        "unconstrained": unconstrained,
        "total": len(DOF_ORDER),
        "constrained_count": len(constrained),
    }


def datum_shift(modifier, feature_kind, boundary_size, actual_mating_size):
    """Datum shift available from the modifier on a datum reference.

    RMB: the simulator is fixed, shift is 0. MMB: shift equals the
    departure of the actual mating size from the MMB size (for a hole
    the MMB size is the smallest hole, so shift = actual - MMB; for a
    pin the MMB size is the largest pin, so shift = MMB - actual).
    LMB: shift equals the departure from the LMB size (for a hole the
    LMB size is the largest hole, so shift = LMB - actual; for a pin
    the LMB size is the smallest pin, so shift = actual - LMB).
    Raises ValueError on an invalid modifier, an invalid feature kind,
    a non-positive or non-finite boundary size, a non-finite actual
    size, or an actual size that violates the boundary side.
    """
    _validate_modifier(modifier)
    if feature_kind not in FEATURE_KINDS:
        raise ValueError(
            "feature_kind must be one of %s, got %r"
            % (", ".join(FEATURE_KINDS), feature_kind)
        )
    _finite(boundary_size, "boundary_size")
    _finite(actual_mating_size, "actual_mating_size")
    if boundary_size <= 0:
        raise ValueError("boundary_size must be > 0, got %r" % (boundary_size,))
    if modifier == "rmb":
        return 0.0
    if modifier == "mmb":
        if feature_kind == "hole":
            if actual_mating_size < boundary_size:
                raise ValueError(
                    "hole actual mating size below MMB size %r, got %r"
                    % (boundary_size, actual_mating_size)
                )
            return actual_mating_size - boundary_size
        if actual_mating_size > boundary_size:
            raise ValueError(
                "pin actual mating size above MMB size %r, got %r"
                % (boundary_size, actual_mating_size)
            )
        return boundary_size - actual_mating_size
    # LMB
    if feature_kind == "hole":
        if actual_mating_size > boundary_size:
            raise ValueError(
                "hole actual mating size above LMB size %r, got %r"
                % (boundary_size, actual_mating_size)
            )
        return boundary_size - actual_mating_size
    if actual_mating_size < boundary_size:
        raise ValueError(
            "pin actual mating size below LMB size %r, got %r"
            % (boundary_size, actual_mating_size)
        )
    return actual_mating_size - boundary_size


def _fmt_tolerance(value):
    """Format a tolerance value without trailing zeros, e.g. 0.5 -> '0.5'."""
    return ("%.6f" % value).rstrip("0").rstrip(".")


def _normalize_datum_refs(datums):
    """Normalize FCF datum references to (letter, modifier suffix) pairs.

    Each reference is either a single uppercase letter string or a
    dict with keys letter and modifier ('rmb', 'mmb', 'lmb').
    """
    refs = []
    for ref in datums:
        if isinstance(ref, str):
            letter, modifier = ref, "rmb"
        elif isinstance(ref, dict):
            letter = ref.get("letter")
            modifier = ref.get("modifier", "rmb")
        else:
            raise ValueError(
                "datum reference must be a letter or a dict, got %r" % (ref,)
            )
        letter = _validate_letter(letter)
        modifier = _validate_modifier(modifier)
        refs.append((letter, _DATUM_MODIFIER_SUFFIX[modifier]))
    return refs


def feature_control_frame(
    characteristic, tolerance, datums=(), tolerance_modifier=None, diameter=None
):
    """Build the feature control frame string.

    Format: {symbol}|{tolerance segment}|{datum refs joined by '|'}.
    The tolerance segment is an optional diameter symbol, the
    tolerance value, and an optional material condition modifier
    suffix (mmc -> M, lmc -> L, rfs -> S). The diameter symbol is
    automatic for the cylindrical-zone characteristics (position,
    concentricity, symmetry, cylindricity) unless overridden. Datum
    references are uppercase letters with an optional MMB/LMB suffix,
    e.g. 'A|BM|C'. A frame without datums ends after the tolerance
    segment. Raises ValueError on an unknown characteristic, a
    negative or non-finite tolerance, an invalid tolerance modifier,
    or an invalid datum reference.
    """
    if characteristic not in CHARACTERISTIC_SYMBOLS:
        raise ValueError(
            "unknown characteristic %r; supported: %s"
            % (characteristic, ", ".join(sorted(CHARACTERISTIC_SYMBOLS)))
        )
    _finite(tolerance, "tolerance")
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0, got %r" % (tolerance,))
    if tolerance_modifier is not None and tolerance_modifier not in TOLERANCE_MODIFIERS:
        raise ValueError(
            "tolerance_modifier must be one of %s, got %r"
            % (", ".join(TOLERANCE_MODIFIERS), tolerance_modifier)
        )
    if diameter is None:
        diameter = characteristic in _DIAMETER_CHARACTERISTICS
    if not isinstance(diameter, bool):
        raise ValueError("diameter must be a bool or None, got %r" % (diameter,))

    symbol = CHARACTERISTIC_SYMBOLS[characteristic]
    tolerance_segment = ""
    if diameter:
        tolerance_segment += "\u2300"
    tolerance_segment += _fmt_tolerance(tolerance)
    if tolerance_modifier is not None:
        tolerance_segment += _TOLERANCE_MODIFIER_SUFFIX[tolerance_modifier]

    refs = _normalize_datum_refs(datums)
    parts = [symbol, tolerance_segment]
    for letter, suffix in refs:
        parts.append(letter + suffix)
    return "|".join(parts)
