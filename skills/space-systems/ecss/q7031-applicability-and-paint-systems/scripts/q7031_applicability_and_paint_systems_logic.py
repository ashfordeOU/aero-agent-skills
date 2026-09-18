"""Paint-system applicability and coating-stack assembly.

Anchor: ECSS-Q-ST-70-31C framework clause -- which finishes on space hardware
the paint rules govern at all, and what a declared paint system has to look
like before any material or process choice is made. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Categorize the declared finish family as a paint system, a bare surface
   treatment outside the paint rules, or an unknown family that cannot be
   dispositioned from the declaration alone.
2. Normalise every declared layer -- role, binder, nominal dry-film thickness
   and its tolerance -- and refuse a layer that is not usable as declared.
3. Order the layers by role and report the structural findings: a repeated or
   inverted stack, a topcoat sitting straight on an unprimed metallic
   substrate, and a stack carrying no organic-binder layer at all.
4. Total the dry-film build across the stack and return its tolerance band,
   because the build the item carries is the sum of the layers, not the
   headline figure of the topcoat.
5. Close with one disposition -- in-scope, out-of-scope or
   incomplete-declaration -- carrying every finding that produced it.
"""

import math

__all__ = [
    "DFT_TOLERANCE_UM",
    "PAINT_FINISH_FAMILIES",
    "SURFACE_TREATMENT_FAMILIES",
    "LAYER_ROLES",
    "METALLIC_SUBSTRATES",
    "NON_METALLIC_SUBSTRATES",
    "ORGANIC_BINDERS",
    "DISPOSITIONS",
    "normalize_key",
    "finish_category",
    "normalize_layer",
    "normalize_stack",
    "stack_findings",
    "total_dft_um",
    "build_within_limit",
    "assess_applicability",
]

# Dry-film sums are differences of floats; an exactly-at-limit build can land a
# few ULPs the wrong side. Absorb the representation error here, leave the
# engineering limit where it is.
DFT_TOLERANCE_UM = 1e-9

# Finish families the paint rules govern.
PAINT_FINISH_FAMILIES = (
    "primer-topcoat-system",
    "single-coat-paint",
    "thermal-control-paint",
    "conductive-paint",
    "anti-static-topcoat",
)

# Finish families that are surface treatments, not paint systems. They may sit
# UNDER a paint system, but on their own they fall outside these rules.
SURFACE_TREATMENT_FAMILIES = (
    "anodising",
    "chemical-conversion-coating",
    "electroplating",
    "vacuum-deposited-metal",
    "bare-machined-surface",
)

LAYER_ROLES = ("primer", "intermediate", "topcoat")

METALLIC_SUBSTRATES = (
    "aluminium-alloy",
    "titanium-alloy",
    "stainless-steel",
    "magnesium-alloy",
    "copper-alloy",
)

NON_METALLIC_SUBSTRATES = (
    "cfrp-laminate",
    "gfrp-laminate",
    "polyimide-film",
    "ceramic",
)

ORGANIC_BINDERS = ("epoxy", "polyurethane", "silicone", "acrylic", "phenolic")

DISPOSITIONS = ("in-scope", "out-of-scope", "incomplete-declaration")


def normalize_key(value, label):
    """Return a trimmed lower-case key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _positive(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _non_negative(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def finish_category(family):
    """Return 'paint-system', 'surface-treatment' or 'unknown' for a family."""
    key = normalize_key(family, "finish family")
    if key in PAINT_FINISH_FAMILIES:
        return "paint-system"
    if key in SURFACE_TREATMENT_FAMILIES:
        return "surface-treatment"
    return "unknown"


def normalize_layer(layer):
    """Return one validated layer record from a declared layer mapping."""
    if not isinstance(layer, dict):
        raise ValueError("layer must be a mapping, got %r" % (layer,))
    for key in ("role", "binder", "nominal_dft_um"):
        if key not in layer:
            raise ValueError("layer missing required key '%s'" % key)
    role = normalize_key(layer["role"], "layer role")
    if role not in LAYER_ROLES:
        raise ValueError("layer role '%s' is not one of %s" % (role, list(LAYER_ROLES)))
    binder = normalize_key(layer["binder"], "layer binder")
    nominal = _positive(layer["nominal_dft_um"], "nominal_dft_um")
    minus = _non_negative(layer.get("minus_tolerance_um", 0.0), "minus_tolerance_um")
    plus = _non_negative(layer.get("plus_tolerance_um", 0.0), "plus_tolerance_um")
    if minus >= nominal:
        raise ValueError(
            "minus tolerance %g um removes the whole %g um layer" % (minus, nominal)
        )
    return {
        "role": role,
        "binder": binder,
        "organic": binder in ORGANIC_BINDERS,
        "nominal_dft_um": nominal,
        "min_dft_um": nominal - minus,
        "max_dft_um": nominal + plus,
    }


def normalize_stack(layers):
    """Return the validated layer records of a declared stack, in declared order."""
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("a paint system needs at least one declared layer")
    return [normalize_layer(entry) for entry in layers]


def stack_findings(layers, substrate):
    """Return the structural findings of a stack applied to a substrate."""
    records = normalize_stack(layers)
    key = normalize_key(substrate, "substrate")
    findings = []
    roles = [rec["role"] for rec in records]
    indices = [LAYER_ROLES.index(r) for r in roles]
    for i in range(1, len(indices)):
        if indices[i] < indices[i - 1]:
            findings.append("layers-out-of-order")
            break
    for role in LAYER_ROLES:
        if roles.count(role) > 1:
            findings.append("repeated-%s-layer" % role)
    if key in METALLIC_SUBSTRATES and "primer" not in roles:
        findings.append("topcoat-on-unprimed-metallic-substrate")
    if key not in METALLIC_SUBSTRATES and key not in NON_METALLIC_SUBSTRATES:
        findings.append("unrecognised-substrate")
    if not any(rec["organic"] for rec in records):
        findings.append("no-organic-binder-layer")
    return findings


def total_dft_um(layers):
    """Return the summed dry-film build of a stack as a tolerance band."""
    records = normalize_stack(layers)
    return {
        "min_um": math.fsum(rec["min_dft_um"] for rec in records),
        "nominal_um": math.fsum(rec["nominal_dft_um"] for rec in records),
        "max_um": math.fsum(rec["max_dft_um"] for rec in records),
    }


def build_within_limit(band, max_build_um):
    """Return True when the worst-case build stays at or under the mass limit."""
    if not isinstance(band, dict) or "max_um" not in band:
        raise ValueError("band must be a mapping carrying 'max_um'")
    worst = _positive(band["max_um"], "band max_um")
    limit = _positive(max_build_um, "max_build_um")
    if worst < limit:
        return True
    return math.isclose(worst, limit, rel_tol=0.0, abs_tol=DFT_TOLERANCE_UM)


def assess_applicability(item):
    """Return the scope disposition for one declared finish on one item."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    for key in ("finish_family", "substrate", "layers"):
        if key not in item:
            raise ValueError("item missing required key '%s'" % key)
    category = finish_category(item["finish_family"])
    result = {
        "finish_category": category,
        "findings": [],
        "disposition": None,
        "build_um": None,
    }
    if category == "surface-treatment":
        result["findings"].append("finish-is-a-surface-treatment")
        result["disposition"] = "out-of-scope"
        return result
    if category == "unknown":
        result["findings"].append("finish-family-not-recognised")
        result["disposition"] = "incomplete-declaration"
        return result
    findings = stack_findings(item["layers"], item["substrate"])
    band = total_dft_um(item["layers"])
    result["findings"] = findings
    result["build_um"] = band
    if "max_build_um" in item and not build_within_limit(band, item["max_build_um"]):
        findings.append("worst-case-build-over-limit")
    # A declaration that cannot be read is not a scope decision: the stack has
    # to be legible before the item can be called in or out of these rules.
    incomplete = [
        f for f in findings
        if f == "unrecognised-substrate" or f == "no-organic-binder-layer"
    ]
    if incomplete:
        result["disposition"] = "incomplete-declaration"
    else:
        result["disposition"] = "in-scope"
    return result
