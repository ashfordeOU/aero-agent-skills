#!/usr/bin/env python3
"""ECSS-E-ST-20C clause 4.2.1.2.1 reliable-insulation underlying
assumptions (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
electrical engineering standard's reliable-insulation concept, once
termed double insulation, protects an exposed part from a hazardous
net by ensuring that no single insulation defect can bridge them. The
concept is admissible only as one basic plus one independent
supplementary layer, or as a single reinforced layer qualified to the
whole stress. This module tests the assumptions that carry that
argument -- layer categorization, set admissibility, layer
independence and common-cause exclusion, the surviving layer's
withstand margin, the applied environment against the qualification
envelope (including the low-pressure corona band), and the absence of
a conductive bypass. It does not qualify insulation materials, derive
withstand voltages, or compute Paschen curves.
"""

# Declared layer type -> role in the reliable-insulation argument.
# "functional" insulation exists for circuit operation and never
# counts toward the protective layer set.
INSULATION_LAYER_TYPES = {
    "basic_insulation": "basic",
    "supplementary_insulation": "supplementary",
    "reinforced_insulation": "reinforced",
    "functional_insulation": "functional",
}

# Assumptions the clause 4.2.1.2.1 argument rests on, in check order.
REQUIRED_ASSUMPTIONS = (
    "admissible_layer_set",
    "independent_layers",
    "surviving_layer_withstand",
    "environment_within_envelope",
    "no_conductive_bypass",
)

# The surviving layer alone carries the full applied stress.
MIN_WITHSTAND_FACTOR = 2.0

# Low-pressure band (Pa) where corona onset is lowest; a layer with no
# qualification evidence inside it has an uncovered environment.
CORONA_BAND_PA = (1.0e-1, 1.0e4)


def categorize_layer(layer_type):
    """Role of a declared insulation layer type: "basic",
    "supplementary", "reinforced" or "functional". Raises ValueError
    for a layer type outside the recognised set."""
    try:
        return INSULATION_LAYER_TYPES[layer_type]
    except (KeyError, TypeError):
        raise ValueError(
            "unrecognized insulation layer type %r under E-ST-20C "
            "clause 4.2.1.2.1" % (layer_type,)
        )


def layer_set_admissible(layers):
    """Admissibility of a declared layer set.

    layers: iterable of dicts each carrying "layer_type" (and, for a
    reinforced layer, "qualified_full_stress": bool). Returns
    {"admissible": bool, "shape": str, "reason": str | None} where
    shape is "reinforced_single_layer", "basic_plus_supplementary" or
    "inadmissible". Raises ValueError for an empty set, a missing
    "layer_type" key, or an unrecognised layer type."""
    layers = list(layers)
    if not layers:
        raise ValueError("layer set must contain at least one declared layer")
    roles = []
    for layer in layers:
        if "layer_type" not in layer:
            raise ValueError("every layer must carry a 'layer_type' key")
        roles.append(categorize_layer(layer["layer_type"]))
    protective = [role for role in roles if role != "functional"]
    if roles.count("reinforced") == 1 and len(protective) == 1:
        reinforced = layers[roles.index("reinforced")]
        if not reinforced.get("qualified_full_stress", False):
            return {
                "admissible": False,
                "shape": "inadmissible",
                "reason": "reinforced_layer_not_qualified_to_full_stress",
            }
        return {
            "admissible": True,
            "shape": "reinforced_single_layer",
            "reason": None,
        }
    if roles.count("basic") == 1 and roles.count("supplementary") == 1 and len(
        protective
    ) == 2:
        return {
            "admissible": True,
            "shape": "basic_plus_supplementary",
            "reason": None,
        }
    return {
        "admissible": False,
        "shape": "inadmissible",
        "reason": "layer_set_is_not_two_independent_layers_or_one_reinforced",
    }


def layers_independent(layer_a, layer_b):
    """Independence of two protective layers.

    Each layer must carry "part_id", "material" and "process".
    Independence requires distinct part identifiers plus a difference
    in material or in process. Returns {"independent": bool,
    "common_cause": [str]} listing the shared attributes. Raises
    ValueError when a required key is absent."""
    required = ("part_id", "material", "process")
    for label, layer in (("layer_a", layer_a), ("layer_b", layer_b)):
        for key in required:
            if key not in layer:
                raise ValueError("%s is missing required key %r" % (label, key))
    common_cause = []
    if layer_a["part_id"] == layer_b["part_id"]:
        common_cause.append("shared_part")
    if layer_a["material"] == layer_b["material"]:
        common_cause.append("shared_material")
    if layer_a["process"] == layer_b["process"]:
        common_cause.append("shared_process")
    independent = "shared_part" not in common_cause and not (
        "shared_material" in common_cause and "shared_process" in common_cause
    )
    return {"independent": independent, "common_cause": common_cause}


def withstand_margin(layer_withstand_v, applied_stress_v, required_factor=MIN_WITHSTAND_FACTOR):
    """Margin of the surviving layer alone against the full applied
    stress. Returns {"margin": withstand/applied, "required": factor,
    "adequate": bool}. Raises ValueError for a non-positive withstand
    or applied stress, or a required factor below 1."""
    if layer_withstand_v <= 0:
        raise ValueError(
            "layer_withstand_v must be > 0 (got %r)" % (layer_withstand_v,)
        )
    if applied_stress_v <= 0:
        raise ValueError(
            "applied_stress_v must be > 0 (got %r)" % (applied_stress_v,)
        )
    if required_factor < 1.0:
        raise ValueError(
            "required_factor must be >= 1.0 (got %r)" % (required_factor,)
        )
    margin = layer_withstand_v / applied_stress_v
    return {
        "margin": margin,
        "required": required_factor,
        "adequate": margin >= required_factor,
    }


def environment_findings(applied, qualified):
    """Exceedances of the qualification envelope.

    applied: {"voltage_v", "temperature_c", "pressure_pa"}.
    qualified: {"max_voltage_v", "min_temperature_c",
    "max_temperature_c", "corona_band_qualified": bool}. Returns a
    list of finding strings (empty when the applied environment is
    covered). Raises ValueError for a missing key, a negative voltage
    or pressure, or an inverted qualified temperature range."""
    for key in ("voltage_v", "temperature_c", "pressure_pa"):
        if key not in applied:
            raise ValueError("applied environment is missing %r" % (key,))
    for key in (
        "max_voltage_v",
        "min_temperature_c",
        "max_temperature_c",
        "corona_band_qualified",
    ):
        if key not in qualified:
            raise ValueError("qualification envelope is missing %r" % (key,))
    if applied["voltage_v"] < 0:
        raise ValueError("applied voltage_v must be >= 0")
    if applied["pressure_pa"] < 0:
        raise ValueError("applied pressure_pa must be >= 0")
    if qualified["min_temperature_c"] > qualified["max_temperature_c"]:
        raise ValueError("qualified temperature range is inverted")
    findings = []
    if applied["voltage_v"] > qualified["max_voltage_v"]:
        findings.append("applied_voltage_above_qualified_ceiling")
    if (
        applied["temperature_c"] < qualified["min_temperature_c"]
        or applied["temperature_c"] > qualified["max_temperature_c"]
    ):
        findings.append("applied_temperature_outside_qualified_range")
    low, high = CORONA_BAND_PA
    if low <= applied["pressure_pa"] <= high and not qualified["corona_band_qualified"]:
        findings.append("low_pressure_corona_band_not_qualified")
    return findings


def assumption_findings(case):
    """Unmet assumptions for one reliable-insulation case.

    case: {"layers": [...], "applied_stress_v": float, "applied": {...},
    "qualified": {...}, "conductive_bypass": bool,
    "required_factor": float (optional)}. Each protective layer also
    carries "withstand_v" for the margin check. Returns a list of
    finding dicts. Raises ValueError through the helpers for any
    malformed input. Does not mutate `case`."""
    findings = []
    layers = list(case.get("layers", []))
    admissibility = layer_set_admissible(layers)
    if not admissibility["admissible"]:
        findings.append(
            {
                "assumption": "admissible_layer_set",
                "issue": admissibility["reason"],
            }
        )
    protective = [
        layer
        for layer in layers
        if categorize_layer(layer["layer_type"]) != "functional"
    ]
    if len(protective) == 2:
        independence = layers_independent(protective[0], protective[1])
        if not independence["independent"]:
            findings.append(
                {
                    "assumption": "independent_layers",
                    "issue": "common_cause_between_layers",
                    "common_cause": independence["common_cause"],
                }
            )
    required_factor = case.get("required_factor", MIN_WITHSTAND_FACTOR)
    for layer in protective:
        result = withstand_margin(
            layer["withstand_v"], case["applied_stress_v"], required_factor
        )
        if not result["adequate"]:
            findings.append(
                {
                    "assumption": "surviving_layer_withstand",
                    "issue": "surviving_layer_margin_below_required_factor",
                    "part_id": layer.get("part_id"),
                    "margin": result["margin"],
                }
            )
    for issue in environment_findings(case["applied"], case["qualified"]):
        findings.append(
            {"assumption": "environment_within_envelope", "issue": issue}
        )
    if case.get("conductive_bypass", False):
        findings.append(
            {
                "assumption": "no_conductive_bypass",
                "issue": "conductive_path_bypasses_both_layers",
            }
        )
    return findings


def reliable_insulation_assumptions_review(case):
    """Full clause 4.2.1.2.1 assumption review for one case. Returns a
    mapping from each name in REQUIRED_ASSUMPTIONS to its finding list
    (empty list = that assumption holds)."""
    review = dict((name, []) for name in REQUIRED_ASSUMPTIONS)
    for finding in assumption_findings(case):
        review[finding["assumption"]].append(finding)
    return review


def assumptions_hold(review):
    """True when every assumption list in a
    reliable_insulation_assumptions_review result is empty -- the
    reliable-insulation argument is admissible on its assumptions."""
    return all(len(findings) == 0 for findings in review.values())
