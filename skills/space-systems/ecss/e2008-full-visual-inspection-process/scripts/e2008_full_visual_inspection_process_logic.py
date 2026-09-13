#!/usr/bin/env python3
"""How a visual examination of a photovoltaic assembly coupon is carried out.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A visual inspection requirement names a feature the examination has to be
able to find: an edge chip on a coverglass, a lifted interconnect foot, a
void in an adhesive fillet. Whether the examination as actually carried
out can find it is not a matter of opinion -- it follows from three
things that are all recorded on the inspection sheet:

    magnification   sets the smallest detail that can be resolved at all
    illumination    sets whether the contrast is there to see it
    viewing aspect  sets whether the feature was ever in the field of view

plus a fourth that is easy to lose: the point in the build flow at which
the examination happened. A rear-face interconnect that is only visible
before the coupon is bonded down cannot be examined after bonding, so a
requirement written against a stage that the process never performed is
not satisfied by an otherwise perfect inspection.

Resolution model
    A trained unaided eye resolves roughly a tenth of a millimetre at the
    reference viewing distance. Under magnification M the resolvable
    detail is that reference divided by M. A feature is only reliably
    found when several resolution elements fall across it, so the
    magnification the requirement demands is

        M_req = resolution_unaided * elements / smallest_feature

    with the element count a declared inspection policy rather than a
    physical constant.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

REFERENCE_UNAIDED_RESOLUTION_MM = 0.10
DEFAULT_DETECTION_ELEMENTS = 3.0

VIEWING_ASPECTS = (
    "front-face",
    "rear-face",
    "cell-edge",
    "coverglass-edge",
    "interconnect-loop",
)

INSPECTION_STAGES = (
    "incoming",
    "pre-bond",
    "post-bond",
    "post-cure",
    "final",
)

ILLUMINATION_WITHIN = "illumination-within-band"
ILLUMINATION_BELOW = "illumination-below-band"
ILLUMINATION_ABOVE = "illumination-above-band"

EXAMINATION_ADEQUATE = "examination-adequate"
EXAMINATION_INADEQUATE = "examination-inadequate"
PROCESS_ADEQUATE = "process-adequate"
PROCESS_INADEQUATE = "process-inadequate"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error.

    A magnification ratio is a quotient of two computed quantities, so a
    case that sits exactly on the demanded magnification can land a few
    units in the last place below it. The demand itself is never lowered;
    only the comparison tolerates the representation error.
    """
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def resolvable_feature_size_mm(
    magnification, unaided_resolution_mm=REFERENCE_UNAIDED_RESOLUTION_MM
):
    """Smallest detail the examination can resolve at this magnification."""
    factor = _require_positive("magnification", magnification)
    if factor < 1.0:
        raise ValueError(
            "magnification must be at least unity (unaided), got %r" % (magnification,)
        )
    reference = _require_positive("unaided_resolution_mm", unaided_resolution_mm)
    return reference / factor


def required_magnification(
    smallest_feature_mm,
    detection_elements=DEFAULT_DETECTION_ELEMENTS,
    unaided_resolution_mm=REFERENCE_UNAIDED_RESOLUTION_MM,
):
    """Magnification the requirement demands to find its smallest feature.

    A value below unity means the feature is large enough to be found with
    the unaided eye; it is returned as computed rather than clamped, so the
    head-room a requirement carries stays visible.
    """
    feature = _require_positive("smallest_feature_mm", smallest_feature_mm)
    elements = _require_positive("detection_elements", detection_elements)
    reference = _require_positive("unaided_resolution_mm", unaided_resolution_mm)
    return reference * elements / feature


def illumination_verdict(applied_lux, min_lux, max_lux):
    """Place the applied illuminance against the band the requirement sets."""
    applied = _require_positive("applied_lux", applied_lux)
    low = _require_positive("min_lux", min_lux)
    high = _require_positive("max_lux", max_lux)
    if not low < high:
        raise ValueError(
            "illumination band is inverted: min %g lx is not below max %g lx"
            % (low, high)
        )
    if applied < low and not math.isclose(
        applied, low, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return ILLUMINATION_BELOW
    if applied > high and not math.isclose(
        applied, high, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        return ILLUMINATION_ABOVE
    return ILLUMINATION_WITHIN


def aspect_gap(required_aspects, viewed_aspects):
    """Viewing aspects a requirement needs that the examination never took."""
    if not isinstance(required_aspects, (list, tuple)) or not required_aspects:
        raise ValueError("required_aspects must be a non-empty sequence")
    if not isinstance(viewed_aspects, (list, tuple)):
        raise ValueError("viewed_aspects must be a sequence")
    for aspect in required_aspects:
        _require_choice("required aspect", aspect, VIEWING_ASPECTS)
    for aspect in viewed_aspects:
        _require_choice("viewed aspect", aspect, VIEWING_ASPECTS)
    return sorted(set(required_aspects) - set(viewed_aspects))


def _validate_process(process):
    if not isinstance(process, dict):
        raise ValueError("process must be a mapping, got %r" % (process,))
    magnification = _require_positive("process magnification", process.get("magnification"))
    if magnification < 1.0:
        raise ValueError(
            "process magnification must be at least unity, got %r" % (magnification,)
        )
    illumination = _require_positive(
        "process illumination_lux", process.get("illumination_lux")
    )
    elements = process.get("detection_elements", DEFAULT_DETECTION_ELEMENTS)
    elements = _require_positive("process detection_elements", elements)
    viewed = process.get("viewed_aspects")
    if not isinstance(viewed, (list, tuple)) or not viewed:
        raise ValueError("process viewed_aspects must be a non-empty sequence")
    for aspect in viewed:
        _require_choice("viewed aspect", aspect, VIEWING_ASPECTS)
    stages = process.get("stages_performed")
    if not isinstance(stages, (list, tuple)) or not stages:
        raise ValueError("process stages_performed must be a non-empty sequence")
    for stage in stages:
        _require_choice("performed stage", stage, INSPECTION_STAGES)
    return {
        "magnification": magnification,
        "illumination_lux": illumination,
        "detection_elements": elements,
        "viewed_aspects": tuple(viewed),
        "stages_performed": tuple(stages),
    }


def _validate_requirement(requirement):
    if not isinstance(requirement, dict):
        raise ValueError("requirement must be a mapping, got %r" % (requirement,))
    ident = requirement.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("requirement id must be a non-empty string")
    feature_mm = _require_positive(
        "%s smallest_feature_mm" % ident, requirement.get("smallest_feature_mm")
    )
    stage = _require_choice("%s stage" % ident, requirement.get("stage"), INSPECTION_STAGES)
    aspects = requirement.get("aspects")
    if not isinstance(aspects, (list, tuple)) or not aspects:
        raise ValueError("requirement %s needs a non-empty aspects sequence" % ident)
    for aspect in aspects:
        _require_choice("%s aspect" % ident, aspect, VIEWING_ASPECTS)
    band = requirement.get("illumination_band_lux")
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError(
            "requirement %s needs illumination_band_lux as a two-value sequence" % ident
        )
    return {
        "id": ident,
        "smallest_feature_mm": feature_mm,
        "stage": stage,
        "aspects": tuple(aspects),
        "illumination_band_lux": (float(band[0]), float(band[1])),
    }


def evaluate_inspection_requirement(requirement, process):
    """Decide whether the examination as carried out satisfies one requirement."""
    req = _validate_requirement(requirement)
    proc = _validate_process(process)
    demanded = required_magnification(
        req["smallest_feature_mm"],
        proc["detection_elements"],
    )
    resolvable = resolvable_feature_size_mm(proc["magnification"])
    ratio = proc["magnification"] / demanded
    magnification_ok = _at_least(proc["magnification"], demanded)
    lighting = illumination_verdict(
        proc["illumination_lux"], *req["illumination_band_lux"]
    )
    missing_aspects = aspect_gap(req["aspects"], proc["viewed_aspects"])
    stage_covered = req["stage"] in proc["stages_performed"]
    findings = []
    if not magnification_ok:
        findings.append(
            "%s needs %.1fx to resolve a %.3f mm feature; the examination used %.1fx"
            % (req["id"], demanded, req["smallest_feature_mm"], proc["magnification"])
        )
    if lighting != ILLUMINATION_WITHIN:
        findings.append(
            "%s was examined at %.0f lx, outside its %.0f-%.0f lx band"
            % (
                req["id"],
                proc["illumination_lux"],
                req["illumination_band_lux"][0],
                req["illumination_band_lux"][1],
            )
        )
    if missing_aspects:
        findings.append(
            "%s was never viewed from: %s" % (req["id"], ", ".join(missing_aspects))
        )
    if not stage_covered:
        findings.append(
            "%s is written against the %s stage, which the process never performed"
            % (req["id"], req["stage"])
        )
    adequate = (
        magnification_ok
        and lighting == ILLUMINATION_WITHIN
        and not missing_aspects
        and stage_covered
    )
    return {
        "id": req["id"],
        "smallest_feature_mm": req["smallest_feature_mm"],
        "required_magnification": demanded,
        "applied_magnification": proc["magnification"],
        "magnification_ratio": ratio,
        "resolvable_feature_size_mm": resolvable,
        "magnification_adequate": magnification_ok,
        "illumination": lighting,
        "missing_aspects": missing_aspects,
        "stage": req["stage"],
        "stage_covered": stage_covered,
        "verdict": EXAMINATION_ADEQUATE if adequate else EXAMINATION_INADEQUATE,
        "findings": findings,
    }


def governing_requirement(results):
    """The requirement that drives the magnification: the smallest ratio.

    Ties break on the requirement id so the answer is reproducible.
    """
    if not isinstance(results, (list, tuple)) or not results:
        raise ValueError("results must be a non-empty sequence")
    return min(results, key=lambda r: (r["magnification_ratio"], r["id"]))["id"]


def run_visual_inspection_process(requirements, process):
    """Full clause 5.5.3.2.2 examination against every detailed requirement."""
    if not isinstance(requirements, (list, tuple)) or not requirements:
        raise ValueError("requirements must be a non-empty sequence")
    seen = set()
    results = []
    for requirement in requirements:
        result = evaluate_inspection_requirement(requirement, process)
        if result["id"] in seen:
            raise ValueError("duplicate requirement id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    adequate = [r for r in results if r["verdict"] == EXAMINATION_ADEQUATE]
    findings = []
    for result in results:
        findings.extend(result["findings"])
    proc = _validate_process(process)
    unused = sorted(set(proc["viewed_aspects"]) - {
        aspect for requirement in requirements for aspect in requirement["aspects"]
    })
    if unused:
        findings.append(
            "the examination viewed aspects no requirement asks for: %s"
            % ", ".join(unused)
        )
    return {
        "results": results,
        "requirement_count": len(results),
        "adequate_count": len(adequate),
        "coverage_fraction": len(adequate) / float(len(results)),
        "governing_requirement": governing_requirement(results),
        "unused_aspects": unused,
        "verdict": PROCESS_ADEQUATE
        if len(adequate) == len(results)
        else PROCESS_INADEQUATE,
        "findings": findings,
    }
