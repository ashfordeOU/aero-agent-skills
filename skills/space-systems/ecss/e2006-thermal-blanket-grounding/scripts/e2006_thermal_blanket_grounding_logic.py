#!/usr/bin/env python3
"""Thermal-blanket layer grounding (ECSS-E-ST-20-06C, 6.3.3.3).

Deterministic, offline, standard-library-only implementation of the grounding
rule for the metallic layers of a multi-layer-insulation blanket: every
metallized layer reaches structure through its own straps, in parallel and
with enough of them, rather than through a chain that runs from layer to
layer before it finds a bond point.

The module resolves each layer's ground path, rejects looped and chained
routes, combines the straps of a layer in parallel, adds the lateral
resistance of the layer itself, grades the total against the bonding limit,
and sizes the number of straps a blanket of a given area needs.

Paraphrased procedure only; the standard is cited as an anchor and no
standard text is reproduced.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Named limits
# ---------------------------------------------------------------------------

#: Node name that stands for the spacecraft structure ground reference.
GROUND_REFERENCE = "structure"

#: Highest acceptable resistance from any point of a metallic layer to
#: structure (ohm).
DEFAULT_MAX_GROUND_PATH_RESISTANCE_OHM = 1.0

#: Smallest number of straps on a metallic layer, so that a single broken or
#: unbonded strap never leaves the layer floating.
MIN_STRAPS_PER_LAYER = 2

#: Blanket area covered by one strap before another one is required (m^2).
DEFAULT_AREA_PER_STRAP_M2 = 2.0

#: Smallest number of straps that must land directly on structure across the
#: whole blanket.
MIN_DIRECT_STRAPS_PER_BLANKET = 2

#: Hop ceiling used to stop a malformed ground path from running away.
MAX_GROUND_PATH_HOPS = 8

#: Tolerances that absorb floating-point representation error at an exactly
#: compliant limit. They never widen the engineering limit itself.
LIMIT_REL_TOL = 1e-9
LIMIT_ABS_TOL = 1e-15

FINDING_UNGROUNDED = "ungrounded-metallic-layer"
FINDING_CHAINED = "chained-layer-to-layer-ground-path"
FINDING_NO_STRAP = "declared-ground-path-without-strap"
FINDING_STRAP_COUNT = "strap-count-below-required"
FINDING_RESISTANCE = "ground-path-resistance-above-limit"
FINDING_BLANKET_REDUNDANCY = "blanket-without-redundant-direct-strap"


def _within_limit(value, limit):
    """True when value does not exceed limit, absorbing representation error."""
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=LIMIT_REL_TOL, abs_tol=LIMIT_ABS_TOL)


def _require_positive(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (field, value))
    return number


def _require_non_negative(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (field, value))
    return number


def normalize_strap(record, layer_id):
    """Validate one grounding-strap record."""
    if not isinstance(record, dict):
        raise ValueError("strap on %s must be a mapping, got %r" % (layer_id, type(record)))
    strap_id = record.get("strap_id")
    if not isinstance(strap_id, str) or not strap_id.strip():
        raise ValueError("strap_id on %s must be a non-empty string" % layer_id)
    return {
        "strap_id": strap_id.strip(),
        "resistance_ohm": _require_positive(
            record.get("resistance_ohm"), "resistance_ohm on %s" % strap_id
        ),
    }


def normalize_layer(record):
    """Validate one blanket-layer record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("layer record must be a mapping, got %r" % (type(record),))
    layer_id = record.get("layer_id")
    if not isinstance(layer_id, str) or not layer_id.strip():
        raise ValueError("layer_id must be a non-empty string")
    layer_id = layer_id.strip()
    if layer_id == GROUND_REFERENCE:
        raise ValueError("layer_id must not shadow the %r node" % GROUND_REFERENCE)
    metallized = record.get("metallized", True)
    if not isinstance(metallized, bool):
        raise ValueError("metallized must be a boolean on %s" % layer_id)
    target = record.get("ground_target", None)
    if target is not None and (not isinstance(target, str) or not target.strip()):
        raise ValueError("ground_target must be a non-empty string or None on %s" % layer_id)
    raw_straps = record.get("straps", [])
    if not isinstance(raw_straps, (list, tuple)):
        raise ValueError("straps must be a list on %s" % layer_id)
    straps = [normalize_strap(item, layer_id) for item in raw_straps]
    seen = set()
    for strap in straps:
        if strap["strap_id"] in seen:
            raise ValueError(
                "duplicate strap_id %r on layer %s" % (strap["strap_id"], layer_id)
            )
        seen.add(strap["strap_id"])
    return {
        "layer_id": layer_id,
        "metallized": metallized,
        "ground_target": target.strip() if isinstance(target, str) else None,
        "straps": straps,
        "lateral_resistance_ohm": _require_non_negative(
            record.get("lateral_resistance_ohm", 0.0), "lateral_resistance_ohm"
        ),
    }


def normalize_blanket(record):
    """Validate one blanket record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("blanket record must be a mapping, got %r" % (type(record),))
    blanket_id = record.get("blanket_id")
    if not isinstance(blanket_id, str) or not blanket_id.strip():
        raise ValueError("blanket_id must be a non-empty string")
    raw_layers = record.get("layers")
    if not isinstance(raw_layers, (list, tuple)) or len(raw_layers) == 0:
        raise ValueError("blanket %s must carry a non-empty layers list" % blanket_id)
    layers = [normalize_layer(item) for item in raw_layers]
    seen = set()
    for layer in layers:
        if layer["layer_id"] in seen:
            raise ValueError(
                "duplicate layer_id %r in blanket %s" % (layer["layer_id"], blanket_id)
            )
        seen.add(layer["layer_id"])
    return {
        "blanket_id": blanket_id.strip(),
        "area_m2": _require_positive(record.get("area_m2"), "area_m2"),
        "layers": layers,
    }


def resolve_ground_path(layer_id, layers_by_id, max_hops=MAX_GROUND_PATH_HOPS):
    """Follow a layer's declared ground target until it reaches structure.

    Returns a mapping with the visited path, the terminal node (structure or
    None when the chain dead-ends) and the hop count. A target that names an
    unknown node, or a route that revisits a layer, is an error rather than a
    finding: the topology itself is undefined.
    """
    if layer_id not in layers_by_id:
        raise ValueError("unknown layer_id %r" % (layer_id,))
    path = [layer_id]
    visited = {layer_id}
    current = layers_by_id[layer_id]
    hops = 0
    while True:
        target = current["ground_target"]
        if target is None:
            return {"path": path, "terminal": None, "hops": hops}
        if target == GROUND_REFERENCE:
            path.append(GROUND_REFERENCE)
            return {"path": path, "terminal": GROUND_REFERENCE, "hops": hops + 1}
        if target not in layers_by_id:
            raise ValueError(
                "layer %r grounds to unknown node %r" % (current["layer_id"], target)
            )
        if target in visited:
            raise ValueError(
                "ground path from %r loops back to %r" % (layer_id, target)
            )
        visited.add(target)
        path.append(target)
        current = layers_by_id[target]
        hops += 1
        if hops > max_hops:
            raise ValueError(
                "ground path from %r exceeds %d hops" % (layer_id, max_hops)
            )


def parallel_resistance(resistances):
    """Resistance of straps in parallel: 1 / sum(1 / R_i) (ohm)."""
    if not isinstance(resistances, (list, tuple)):
        raise ValueError("resistances must be a list or tuple")
    if len(resistances) == 0:
        raise ValueError("resistances must not be empty")
    conductance = 0.0
    for index, value in enumerate(resistances):
        conductance += 1.0 / _require_positive(value, "resistances[%d]" % index)
    return 1.0 / conductance


def layer_ground_resistance(layer):
    """Resistance from the furthest point of a layer to its bond point.

    The straps sit in parallel; the lateral resistance of the layer itself is
    in series ahead of them. A layer with no strap has no bond point, so its
    resistance is infinite rather than zero.
    """
    if len(layer["straps"]) == 0:
        return float("inf")
    strap_resistance = parallel_resistance(
        [strap["resistance_ohm"] for strap in layer["straps"]]
    )
    return layer["lateral_resistance_ohm"] + strap_resistance


def required_strap_count(
    area_m2, area_per_strap_m2=DEFAULT_AREA_PER_STRAP_M2, minimum=MIN_STRAPS_PER_LAYER
):
    """Number of straps a metallic layer of this blanket area needs."""
    area = _require_positive(area_m2, "area_m2")
    per_strap = _require_positive(area_per_strap_m2, "area_per_strap_m2")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 1:
        raise ValueError("minimum must be an integer of at least 1, got %r" % (minimum,))
    return max(minimum, int(math.ceil(area / per_strap)))


def evaluate_layer(
    layer_id,
    layers_by_id,
    area_m2,
    max_resistance_ohm=DEFAULT_MAX_GROUND_PATH_RESISTANCE_OHM,
    area_per_strap_m2=DEFAULT_AREA_PER_STRAP_M2,
    minimum_straps=MIN_STRAPS_PER_LAYER,
):
    """Grade the grounding of one blanket layer."""
    layer = layers_by_id[layer_id]
    limit = _require_positive(max_resistance_ohm, "max_resistance_ohm")
    if not layer["metallized"]:
        return {
            "layer_id": layer_id,
            "applicable": False,
            "findings": [],
            "path": [layer_id],
            "hops": 0,
            "strap_count": len(layer["straps"]),
            "required_strap_count": 0,
            "path_resistance_ohm": None,
            "resistance_limit_ohm": limit,
        }

    resolution = resolve_ground_path(layer_id, layers_by_id)
    findings = []
    required = required_strap_count(
        area_m2, area_per_strap_m2=area_per_strap_m2, minimum=minimum_straps
    )
    strap_count = len(layer["straps"])

    if resolution["terminal"] is None:
        findings.append(FINDING_UNGROUNDED)
        path_resistance = None
    else:
        if resolution["hops"] > 1:
            findings.append(FINDING_CHAINED)
        path_resistance = 0.0
        for node in resolution["path"]:
            if node == GROUND_REFERENCE:
                continue
            path_resistance += layer_ground_resistance(layers_by_id[node])
        if strap_count == 0:
            findings.append(FINDING_NO_STRAP)
        if not _within_limit(path_resistance, limit):
            findings.append(FINDING_RESISTANCE)

    if 0 < strap_count < required:
        findings.append(FINDING_STRAP_COUNT)

    return {
        "layer_id": layer_id,
        "applicable": True,
        "findings": findings,
        "path": resolution["path"],
        "hops": resolution["hops"],
        "strap_count": strap_count,
        "required_strap_count": required,
        "path_resistance_ohm": path_resistance,
        "resistance_limit_ohm": limit,
    }


def evaluate_blanket(
    record,
    max_resistance_ohm=DEFAULT_MAX_GROUND_PATH_RESISTANCE_OHM,
    area_per_strap_m2=DEFAULT_AREA_PER_STRAP_M2,
    minimum_straps=MIN_STRAPS_PER_LAYER,
    minimum_direct_straps=MIN_DIRECT_STRAPS_PER_BLANKET,
):
    """Grade the grounding of one multi-layer-insulation blanket."""
    blanket = normalize_blanket(record)
    layers_by_id = {layer["layer_id"]: layer for layer in blanket["layers"]}
    layer_results = [
        evaluate_layer(
            layer["layer_id"],
            layers_by_id,
            blanket["area_m2"],
            max_resistance_ohm=max_resistance_ohm,
            area_per_strap_m2=area_per_strap_m2,
            minimum_straps=minimum_straps,
        )
        for layer in blanket["layers"]
    ]

    direct_straps = 0
    for layer in blanket["layers"]:
        if layer["metallized"] and layer["ground_target"] == GROUND_REFERENCE:
            direct_straps += len(layer["straps"])

    blanket_findings = []
    metallic_layers = [layer for layer in blanket["layers"] if layer["metallized"]]
    if metallic_layers and direct_straps < minimum_direct_straps:
        blanket_findings.append(FINDING_BLANKET_REDUNDANCY)

    open_findings = [
        (result["layer_id"], finding)
        for result in layer_results
        for finding in result["findings"]
    ]
    return {
        "blanket_id": blanket["blanket_id"],
        "area_m2": blanket["area_m2"],
        "layer_results": layer_results,
        "metallic_layer_count": len(metallic_layers),
        "direct_strap_count": direct_straps,
        "blanket_findings": blanket_findings,
        "open_findings": open_findings,
        "compliant": len(open_findings) == 0 and len(blanket_findings) == 0,
        "anchor": "ECSS-E-ST-20-06C 6.3.3.3",
    }


def assess_blanket_set(records, **limits):
    """Grade a set of blankets and aggregate their findings."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple")
    if len(records) == 0:
        raise ValueError("records must not be empty")
    results = []
    seen = set()
    for record in records:
        result = evaluate_blanket(record, **limits)
        if result["blanket_id"] in seen:
            raise ValueError("duplicate blanket_id %r" % result["blanket_id"])
        seen.add(result["blanket_id"])
        results.append(result)
    return {
        "blankets": results,
        "compliant_count": sum(1 for r in results if r["compliant"]),
        "non_compliant": [r["blanket_id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }


def format_grounding_report(assessment):
    """Render a deterministic plain-text blanket-grounding report."""
    if not isinstance(assessment, dict) or "blankets" not in assessment:
        raise ValueError("assessment must come from assess_blanket_set")
    lines = ["ECSS-E-ST-20-06C 6.3.3.3 thermal-blanket layer grounding"]
    for blanket in assessment["blankets"]:
        lines.append(
            "%s area=%.3g m2 metallic-layers=%d direct-straps=%d"
            % (
                blanket["blanket_id"],
                blanket["area_m2"],
                blanket["metallic_layer_count"],
                blanket["direct_strap_count"],
            )
        )
        for layer_id, finding in blanket["open_findings"]:
            lines.append("    %s: %s" % (layer_id, finding))
        for finding in blanket["blanket_findings"]:
            lines.append("    blanket: %s" % finding)
    lines.append("compliant=%s" % str(assessment["compliant"]).lower())
    return "\n".join(lines)
