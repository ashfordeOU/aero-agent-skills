"""Local crippling and inter-rivet analysis of formed compression stiffeners.

Pure stdlib closed-form implementation (math only) of the local crippling
allowable of a formed thin-wall compression section (angle, channel, Z, hat
stringer, bulb angle) by the shape-constant power-law correlation family of
Gerard (NACA-TN-3784 / NACA-TN-3785, paraphrased by name only), the
inter-rivet buckling stress of the fastener-attached flat between rivet
lines after Semonian and Peterson (NACA-TN-3431, paraphrased), and the
Johnson-Euler column interaction that anchors the stiffener column curve on
the local crippling allowable.

All geometry in metres (b, t, d, pitch), stresses in pascals, slenderness
lambda = K*L/r dimensionless. Correlation constants are module-level names
and are calibrated on the aluminum sheet crippling test family, so the
method is stated for 2024-T3 and 7075-T6 only. Corner radii are ignored
(flat widths). Every non-physical input raises ValueError.
"""

import math

# ---------------------------------------------------------------------------
# Module constants: the correlation itself (pin exactly)
# ---------------------------------------------------------------------------

CRIPPLING_EXPONENT = 0.75      # exponent n in the (t/b)**n power law
C_OEF = 0.31                   # one-edge-free flat element (outstanding leg or flange)
C_SEF = 0.55                   # no-edge-free flat element (web or crown between corners)
K_INTER_RIVET = 4.0            # long-plate coefficient, rivet lines as simple supports
MATERIALS = {
    "2024-T3": {"E": 72.4e9, "fcy": 290.0e6, "nu": 0.33},
    "7075-T6": {"E": 71.7e9, "fcy": 462.0e6, "nu": 0.33},
}

_ELEMENT_CLASSES = ("oef", "sef", "bulb")
_FLAT_CLASSES = ("oef", "sef")

# Formed shapes and their required dimensions (all positive, SI).
_SHAPE_DIMS = {
    "angle": ("b1", "b2", "t"),
    "channel": ("bw", "bf", "t"),
    "z": ("bw", "bf", "t"),
    "hat": ("bc", "bl", "t"),
    "bulb-angle": ("b1", "bs", "d", "t"),
}


def _alnum(text):
    """Keep alphanumeric characters only, for case/whitespace-insensitive
    material name matching (the hyphen in 2024-T3 is optional spacing)."""
    return "".join(ch for ch in text if ch.isalnum())


def _require_positive(value, name):
    """Return value coerced to float if strictly positive, else ValueError."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a positive number, got %r" % (name, value))
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return number


def material(name):
    """Resolve a material name to its constants dict.

    Case and whitespace insensitive for "2024-T3" and "7075-T6".
    ValueError on an unknown material.
    """
    if not isinstance(name, str):
        raise ValueError("material name must be a string, got %r" % (name,))
    key = _alnum(name).upper()
    lookup = {_alnum(k).upper(): k for k in MATERIALS}
    if key not in lookup:
        raise ValueError(
            "unknown material %r; registry holds 2024-T3 and 7075-T6 only" % (name,)
        )
    return dict(MATERIALS[lookup[key]])


def element_crippling_stress(b, t, edge_class, mat):
    """Element crippling stress of one flat element, capped at the yield.

    F_cc = min(F_cy, C_s * sqrt(F_cy * E) * (t / b) ** CRIPPLING_EXPONENT)
    with C_s = C_OEF for a one-edge-free flat ("oef") and C_SES = C_SEF for
    a no-edge-free flat ("sef"). ValueError if b or t is non-positive or
    the edge class is not "oef"/"sef".
    """
    width = _require_positive(b, "b")
    thick = _require_positive(t, "t")
    if edge_class not in _FLAT_CLASSES:
        raise ValueError("edge_class must be 'oef' or 'sef', got %r" % (edge_class,))
    constant = C_OEF if edge_class == "oef" else C_SEF
    raw = constant * math.sqrt(mat["fcy"] * mat["E"]) * (
        thick / width
    ) ** CRIPPLING_EXPONENT
    return min(mat["fcy"], raw)


def _flat_element_fcc(element, mat):
    """Crippling stress of a flat element dict carrying b and t."""
    if "b" not in element or "t" not in element:
        raise ValueError(
            "flat element %r needs 'b' and 't' keys" % (element.get("label"),)
        )
    return element_crippling_stress(
        element["b"], element["t"], element["cls"], mat
    )


def section_crippling_stress(elements, mat):
    """Area-weighted section crippling allowable over the flat elements.

    Elements is a list of dicts, each either
    {"label": str, "b": float, "t": float, "cls": "oef"|"sef"} or
    {"label": str, "d": float, "cls": "bulb"}. A bulb element (solid
    cylinder of diameter d) carries at F_cy with area pi*d**2/4 and does
    not cripple locally. Returns {"fcc", "area_total", "elements"} where
    the per-element rows carry their area and fcc. ValueError on an empty
    list or an unknown element key.
    """
    if not isinstance(elements, list) or len(elements) == 0:
        raise ValueError("elements must be a non-empty list of element dicts")
    rows = []
    area_total = 0.0
    load_total = 0.0
    for element in elements:
        if not isinstance(element, dict) or "label" not in element:
            raise ValueError("each element must be a dict with a 'label'")
        cls = element.get("cls")
        if cls not in _ELEMENT_CLASSES:
            raise ValueError(
                "element %r has unknown class %r; use 'oef', 'sef' or 'bulb'"
                % (element["label"], cls)
            )
        if cls in _FLAT_CLASSES:
            area = _require_positive(element.get("b"), "b") * _require_positive(
                element.get("t"), "t"
            )
            fcc = _flat_element_fcc(element, mat)
        else:  # bulb: solid cylinder carrying at yield, no local crippling
            d = _require_positive(element.get("d"), "d")
            area = math.pi * d * d / 4.0
            fcc = mat["fcy"]
        row = dict(element)
        row["area"] = area
        row["fcc"] = fcc
        rows.append(row)
        area_total += area
        load_total += fcc * area
    fcc_section = load_total / area_total
    return {"fcc": fcc_section, "area_total": area_total, "elements": rows}


def inter_rivet_allowable(t_attach, pitch, mat):
    """Inter-rivet buckling allowable of the fastener-attached flat.

    sigma_ir = K_INTER_RIVET * pi**2 * E / (12 * (1 - nu**2)) *
    (t_attach / pitch)**2, the long-plate value with the rivet lines as
    simple supports. Returns {"stress_raw", "allowable"} with
    allowable = min(raw, fcy): above yield the flat yields before it can
    buckle between the fasteners. ValueError if t_attach or pitch is
    non-positive.
    """
    thick = _require_positive(t_attach, "t_attach")
    spacing = _require_positive(pitch, "pitch")
    raw = (
        K_INTER_RIVET
        * math.pi ** 2
        * mat["E"]
        / (12.0 * (1.0 - mat["nu"] ** 2))
        * (thick / spacing) ** 2
    )
    return {"stress_raw": raw, "allowable": min(mat["fcy"], raw)}


def column_interaction_allowable(fcc, lam, mat):
    """Johnson-Euler interaction allowable anchored on the crippling stress.

    The crippling stress is the lambda-tending-to-0 limit of the stiffener
    column curve, so the Johnson parabola is anchored at F_cc (never at
    sigma_y): lambda_t = pi * sqrt(2*E/F_cc); for lambda <= lambda_t,
    F_col = F_cc * (1 - F_cc*lambda**2 / (4*pi**2*E)) (Johnson arm); for
    lambda > lambda_t, F_col = pi**2*E / lambda**2 (Euler arm). At
    lambda_t both arms equal F_cc/2 exactly by construction. Returns
    {"allowable", "lam_t", "regime"} with regime "johnson" or "euler".
    ValueError if fcc or lam is non-positive.
    """
    cripple = _require_positive(fcc, "fcc")
    lamda = _require_positive(lam, "lam")
    lam_t = math.pi * math.sqrt(2.0 * mat["E"] / cripple)
    if lamda <= lam_t:
        allowable = cripple * (
            1.0 - cripple * lamda ** 2 / (4.0 * math.pi ** 2 * mat["E"])
        )
        regime = "johnson"
    else:
        allowable = math.pi ** 2 * mat["E"] / lamda ** 2
        regime = "euler"
    return {"allowable": allowable, "lam_t": lam_t, "regime": regime}


def compression_margin(f_allowable, sigma_applied):
    """Margin of safety against the applied compression stress.

    MS = f_allowable / sigma_applied - 1. ValueError if sigma_applied is
    non-positive.
    """
    applied = _require_positive(sigma_applied, "sigma_applied")
    return float(f_allowable) / applied - 1.0


def formed_shape_elements(shape, **dims):
    """Expand a formed shape into its flat element list.

    Shapes and required dims (all positive): "angle": b1, b2, t (two
    one-edge-free legs); "channel": bw, bf, t and "z": bw, bf, t
    (no-edge-free web plus two one-edge-free flanges); "hat": bc, bl, t
    (no-edge-free crown plus two one-edge-free legs); "bulb-angle": b1,
    bs, d, t (one-edge-free plain leg, one-edge-free stem to the bulb,
    solid bulb of diameter d). ValueError on an unknown shape, a missing
    required dim, or a non-positive dim.
    """
    shape_key = shape.lower() if isinstance(shape, str) else shape
    if shape_key not in _SHAPE_DIMS:
        raise ValueError(
            "unknown formed shape %r; supported: angle, channel, z, hat, "
            "bulb-angle" % (shape,)
        )
    required = _SHAPE_DIMS[shape_key]
    missing = [name for name in required if name not in dims]
    if missing:
        raise ValueError(
            "shape %r requires dims %s, missing %s"
            % (shape, ", ".join(required), ", ".join(missing))
        )
    values = {name: _require_positive(dims[name], name) for name in required}
    t = values["t"] if "t" in values else None

    if shape_key == "angle":
        return [
            {"label": "leg-a", "b": values["b1"], "t": t, "cls": "oef"},
            {"label": "leg-b", "b": values["b2"], "t": t, "cls": "oef"},
        ]
    if shape_key in ("channel", "z"):
        return [
            {"label": "web", "b": values["bw"], "t": t, "cls": "sef"},
            {"label": "flange-a", "b": values["bf"], "t": t, "cls": "oef"},
            {"label": "flange-b", "b": values["bf"], "t": t, "cls": "oef"},
        ]
    if shape_key == "hat":
        return [
            {"label": "crown", "b": values["bc"], "t": t, "cls": "sef"},
            {"label": "leg-a", "b": values["bl"], "t": t, "cls": "oef"},
            {"label": "leg-b", "b": values["bl"], "t": t, "cls": "oef"},
        ]
    # bulb-angle: plain leg, stem to the bulb, solid bulb of diameter d
    return [
        {"label": "plain-leg", "b": values["b1"], "t": t, "cls": "oef"},
        {"label": "stem", "b": values["bs"], "t": t, "cls": "oef"},
        {"label": "bulb", "d": values["d"], "cls": "bulb"},
    ]


def stiffener_compression_check(elements, mat, t_attach, pitch, lam,
                                sigma_applied):
    """Umbrella stiffener compression check against the applied stress.

    Returns {"fcc_section", "area_total", "sigma_ir_raw", "f_ir_allowable",
    "f_col_allowable", "lam_t", "column_regime", "f_compression_allowable",
    "margin", "verdict"} with f_compression_allowable = min(f_col,
    f_ir) and verdict "pass" when the margin of safety is >= 0. The
    ValueError set is inherited from every callee.
    """
    section = section_crippling_stress(elements, mat)
    ir = inter_rivet_allowable(t_attach, pitch, mat)
    column = column_interaction_allowable(section["fcc"], lam, mat)
    f_compression = min(column["allowable"], ir["allowable"])
    margin = compression_margin(f_compression, sigma_applied)
    return {
        "fcc_section": section["fcc"],
        "area_total": section["area_total"],
        "sigma_ir_raw": ir["stress_raw"],
        "f_ir_allowable": ir["allowable"],
        "f_col_allowable": column["allowable"],
        "lam_t": column["lam_t"],
        "column_regime": column["regime"],
        "f_compression_allowable": f_compression,
        "margin": margin,
        "verdict": "pass" if margin >= 0.0 else "fail",
    }
