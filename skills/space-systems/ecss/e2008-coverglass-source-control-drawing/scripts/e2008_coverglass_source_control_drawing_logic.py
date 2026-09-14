#!/usr/bin/env python3
"""A coated coverglass is bought against a drawing, so the drawing has to say everything.

Anchor: ECSS-E-ST-20-08C Annex D. The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

A source control drawing is the whole of the purchase agreement for a coated
coverglass. Anything the drawing leaves out is a property the supplier is free
to choose, and a coverglass that meets a silent drawing perfectly can still be
the wrong part. This module reads a drawing and answers four questions:

    content      does the drawing carry every heading a coated coverglass is
                 bought against -- substrate, thickness, planar size, the
                 coating stack, the optical window, absorptance, emittance,
                 radiation, surface quality, marking, packaging, acceptance
                 and the source it may be bought from
    tolerance    does every dimension carry a band that brackets its nominal
                 and is narrow enough to control the part it describes
    optics       does the optical window run the right way round, is it wide
                 enough to be a window, and are absorptance and emittance
                 physically possible numbers
    stack        does the coating stack name a face and a function per layer,
                 and does it carry the layers a coverglass exists to provide

The arms are ranked rather than merged. A heading that is absent outranks a
heading that is present but unusable, because an absent heading is a decision
nobody has made yet, while an unusable one is a decision written down wrong.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REQUIRED_SCD_CONTENT = (
    "drawing_identifier",
    "issue_and_date",
    "component_description",
    "substrate_material",
    "thickness",
    "planar_dimensions",
    "coating_stack",
    "optical_window",
    "solar_absorptance",
    "thermal_emittance",
    "radiation_requirement",
    "surface_quality_requirement",
    "marking_and_traceability",
    "packaging_and_handling",
    "acceptance_inspection",
    "approved_source",
)

DIMENSIONAL_CONTENT = ("thickness", "planar_dimensions")

REQUIRED_COATING_FUNCTIONS = ("antireflection", "ultraviolet-reject")
COATING_FACES = ("front", "rear")

DIMENSION_USABLE = "dimension-usable"
DIMENSION_UNTOLERANCED = "dimension-untoleranced"
DIMENSION_UNBRACKETED = "dimension-unbracketed"
DIMENSION_BAND_TOO_WIDE = "dimension-band-too-wide"

WINDOW_USABLE = "optical-window-usable"
WINDOW_INVERTED = "optical-window-inverted"
WINDOW_TOO_NARROW = "optical-window-too-narrow"
WINDOW_TRANSMITTANCE_IMPOSSIBLE = "optical-window-transmittance-impossible"

STACK_USABLE = "coating-stack-usable"
STACK_THIN = "coating-stack-thin"
STACK_FUNCTION_MISSING = "coating-stack-function-missing"

SCD_RELEASABLE = "scd-releasable"
SCD_NOT_RELEASABLE = "scd-not-releasable"

DEFAULT_SCD_POLICY = {
    "max_thickness_band_fraction": 0.10,
    "max_planar_band_fraction": 0.02,
    "min_coating_layers": 2,
    "require_conductive_coating": False,
    "min_optical_window_nm": 100.0,
    "min_content_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _close(value, limit):
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or _close(value, limit)


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or _close(value, limit)


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_positive(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be finite and positive, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def validate_scd_policy(policy):
    """Check a drawing-review policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "max_thickness_band_fraction", policy.get("max_thickness_band_fraction")
    )
    _require_fraction(
        "max_planar_band_fraction", policy.get("max_planar_band_fraction")
    )
    _require_count("min_coating_layers", policy.get("min_coating_layers"))
    _require_flag(
        "require_conductive_coating", policy.get("require_conductive_coating")
    )
    _require_positive("min_optical_window_nm", policy.get("min_optical_window_nm"))
    _require_fraction("min_content_fraction", policy.get("min_content_fraction"))
    return policy


def required_scd_content():
    """The headings a coated coverglass source control drawing is bought against."""
    return tuple(REQUIRED_SCD_CONTENT)


def dimensional_content():
    """The headings that are dimensions and therefore owe a tolerance band."""
    return tuple(DIMENSIONAL_CONTENT)


def audit_scd_content(drawing, policy=DEFAULT_SCD_POLICY):
    """Which required headings the drawing does not actually carry."""
    validate_scd_policy(policy)
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    content = drawing.get("content")
    if not isinstance(content, dict):
        raise ValueError("drawing content must be a mapping, got %r" % (content,))
    missing = []
    for heading in REQUIRED_SCD_CONTENT:
        value = content.get(heading)
        if value is None:
            missing.append(heading)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(heading)
            continue
        if isinstance(value, (list, tuple, dict)) and not value:
            missing.append(heading)
    return sorted(missing)


def assess_dimensional_entry(name, entry, max_band_fraction):
    """Does a dimension on the drawing carry a band that can control the part."""
    name = _require_text("dimension name", name)
    max_band_fraction = _require_fraction("max_band_fraction", max_band_fraction)
    if not isinstance(entry, dict):
        raise ValueError("%s must be a mapping, got %r" % (name, entry))
    nominal = _require_positive("%s nominal" % name, entry.get("nominal"))
    minimum = entry.get("minimum")
    maximum = entry.get("maximum")
    if minimum is None or maximum is None:
        return {
            "dimension": name,
            "nominal": nominal,
            "minimum": None,
            "maximum": None,
            "band_width": None,
            "band_fraction": None,
            "brackets_nominal": False,
            "within_band_limit": False,
            "verdict": DIMENSION_UNTOLERANCED,
            "usable": False,
        }
    minimum = _require_positive("%s minimum" % name, minimum)
    maximum = _require_positive("%s maximum" % name, maximum)
    if not _at_most(minimum, maximum):
        raise ValueError(
            "%s declares a minimum above its maximum (%r > %r)"
            % (name, minimum, maximum)
        )
    band_width = maximum - minimum
    band_fraction = band_width / nominal
    brackets = _at_most(minimum, nominal) and _at_least(maximum, nominal)
    within = _at_most(band_fraction, max_band_fraction)
    if not brackets:
        verdict = DIMENSION_UNBRACKETED
    elif not within:
        verdict = DIMENSION_BAND_TOO_WIDE
    else:
        verdict = DIMENSION_USABLE
    return {
        "dimension": name,
        "nominal": nominal,
        "minimum": minimum,
        "maximum": maximum,
        "band_width": band_width,
        "band_fraction": band_fraction,
        "brackets_nominal": brackets,
        "within_band_limit": within,
        "verdict": verdict,
        "usable": verdict == DIMENSION_USABLE,
    }


def assess_optical_window(entry, policy=DEFAULT_SCD_POLICY):
    """Does the transmission window the drawing states describe a real filter."""
    validate_scd_policy(policy)
    if not isinstance(entry, dict):
        raise ValueError("optical window must be a mapping, got %r" % (entry,))
    cut_on = _require_positive("cut_on_nm", entry.get("cut_on_nm"))
    cut_off = _require_positive("cut_off_nm", entry.get("cut_off_nm"))
    transmittance = entry.get("min_transmittance")
    if transmittance is None:
        raise ValueError("optical window must state a minimum transmittance")
    transmittance = float(_require_fraction("min_transmittance", transmittance))
    width = cut_off - cut_on
    wide_enough = _at_least(width, float(policy["min_optical_window_nm"]))
    if not _at_least(cut_off, cut_on) or _close(cut_off, cut_on):
        verdict = WINDOW_INVERTED
    elif transmittance <= 0.0:
        verdict = WINDOW_TRANSMITTANCE_IMPOSSIBLE
    elif not wide_enough:
        verdict = WINDOW_TOO_NARROW
    else:
        verdict = WINDOW_USABLE
    return {
        "cut_on_nm": cut_on,
        "cut_off_nm": cut_off,
        "window_width_nm": width,
        "min_transmittance": transmittance,
        "wide_enough": wide_enough,
        "verdict": verdict,
        "usable": verdict == WINDOW_USABLE,
    }


def assess_coating_stack(layers, policy=DEFAULT_SCD_POLICY):
    """Does the coating stack name a face and a function for every layer it lists."""
    validate_scd_policy(policy)
    if not isinstance(layers, (list, tuple)) or not layers:
        raise ValueError("coating stack must be a non-empty sequence of layers")
    functions = []
    faces = []
    for layer in layers:
        if not isinstance(layer, dict):
            raise ValueError("coating layer must be a mapping, got %r" % (layer,))
        function = _require_text("layer function", layer.get("function")).lower()
        face = _require_text("layer face", layer.get("face")).lower()
        if face not in COATING_FACES:
            raise ValueError(
                "layer face must be one of %s, got %r"
                % (", ".join(COATING_FACES), face)
            )
        functions.append(function)
        faces.append(face)
    grouped = sorted(set(functions))
    required = list(REQUIRED_COATING_FUNCTIONS)
    if policy["require_conductive_coating"]:
        required.append("conductive")
    absent = sorted(item for item in required if item not in grouped)
    thin = len(layers) < int(policy["min_coating_layers"])
    if absent:
        verdict = STACK_FUNCTION_MISSING
    elif thin:
        verdict = STACK_THIN
    else:
        verdict = STACK_USABLE
    return {
        "layer_count": len(layers),
        "functions": grouped,
        "faces": sorted(set(faces)),
        "absent_functions": absent,
        "verdict": verdict,
        "usable": verdict == STACK_USABLE,
    }


def assess_coverglass_scd(drawing, policy=DEFAULT_SCD_POLICY):
    """Full Annex D sweep over a coated coverglass source control drawing."""
    validate_scd_policy(policy)
    if not isinstance(drawing, dict):
        raise ValueError("drawing must be a mapping, got %r" % (drawing,))
    drawing_id = _require_text("drawing_id", drawing.get("drawing_id"))
    content = drawing.get("content")
    if not isinstance(content, dict) or not content:
        raise ValueError("drawing content must be a non-empty mapping")

    missing = audit_scd_content(drawing, policy)
    findings = [
        "drawing %s states nothing under %s, so the supplier chooses it"
        % (drawing_id, heading)
        for heading in missing
    ]

    dimensions = {}
    for heading in DIMENSIONAL_CONTENT:
        if heading in missing:
            continue
        limit = (
            policy["max_thickness_band_fraction"]
            if heading == "thickness"
            else policy["max_planar_band_fraction"]
        )
        entries = content[heading]
        if not isinstance(entries, dict):
            raise ValueError("%s must be a mapping of dimensions" % heading)
        if "nominal" in entries:
            entries = {heading: entries}
        for label, entry in sorted(entries.items()):
            assessed = assess_dimensional_entry(label, entry, limit)
            dimensions[label] = assessed
            if not assessed["usable"]:
                findings.append(
                    "dimension %s on drawing %s is %s"
                    % (label, drawing_id, assessed["verdict"])
                )

    window = None
    if "optical_window" not in missing:
        window = assess_optical_window(content["optical_window"], policy)
        if not window["usable"]:
            findings.append(
                "the optical window on drawing %s is %s" % (drawing_id, window["verdict"])
            )

    stack = None
    if "coating_stack" not in missing:
        stack = assess_coating_stack(content["coating_stack"], policy)
        if not stack["usable"]:
            findings.append(
                "the coating stack on drawing %s is %s, absent %s"
                % (
                    drawing_id,
                    stack["verdict"],
                    ", ".join(stack["absent_functions"]) or "no function",
                )
            )

    total = len(REQUIRED_SCD_CONTENT)
    stated = total - len(missing)
    content_fraction = stated / float(total)
    minimum = float(policy["min_content_fraction"])
    content_ok = _at_least(content_fraction, minimum)
    if not content_ok:
        findings.append(
            "drawing %s states %d of %d required headings against a required "
            "share of %.3f" % (drawing_id, stated, total, minimum)
        )

    unusable = sorted(
        label for label, entry in dimensions.items() if not entry["usable"]
    )
    releasable = (
        content_ok
        and not missing
        and not unusable
        and (window is None or window["usable"])
        and (stack is None or stack["usable"])
    )
    return {
        "verdict": SCD_RELEASABLE if releasable else SCD_NOT_RELEASABLE,
        "drawing_id": drawing_id,
        "missing_content": missing,
        "stated_content_fraction": content_fraction,
        "required_content_fraction": minimum,
        "dimension_assessments": dimensions,
        "unusable_dimensions": unusable,
        "optical_window": window,
        "coating_stack": stack,
        "every_heading_stated": not missing,
        "findings": findings,
    }
