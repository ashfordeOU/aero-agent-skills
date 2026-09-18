#!/usr/bin/env python3
"""Non-destructive testing of additively manufactured parts.

Anchor: ECSS-Q-ST-70-80C, Inspection, taken together with the
non-destructive inspection requirements of ECSS-Q-ST-70-15C. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

An additively manufactured part carries defect populations a wrought
part does not: lack-of-fusion between tracks or layers, gas porosity
from the feedstock, entrapped unfused powder in an internal channel,
and cracking driven by the thermal gradient of the build. Those defects
are the reason a volumetric method is demanded at all, and they also
decide which method can find them:

    computed-tomography   volumetric, reaches internal channels, but
                          the achievable voxel grows with the longest
                          radiographic path through the part
    ultrasonic            volumetric and sensitive to planar flaws, but
                          it needs a coupled, machined surface and a
                          clear back-wall path
    radiographic          volumetric and fast, but a planar flaw is
                          only seen when the beam runs close to its
                          plane

The decision this module makes is not "which method is nicest". It is
whether the smallest flaw the declared setup can resolve is smaller
than the flaw the fracture-control assessment says is critical, on a
coverage that the part criticality category demands.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

CRITICALITY_CATEGORIES = ("catastrophic", "critical", "major", "minor")
NDT_METHODS = ("computed-tomography", "ultrasonic", "radiographic")

FULL_VOLUMETRIC = "full-volumetric"
SAMPLED_VOLUMETRIC = "sampled-volumetric"
SURFACE_ONLY = "surface-only"

DEFAULT_NDT_POLICY = {
    "coverage": {
        "catastrophic": FULL_VOLUMETRIC,
        "critical": FULL_VOLUMETRIC,
        "major": SAMPLED_VOLUMETRIC,
        "minor": SURFACE_ONLY,
    },
    "sample_fraction": {
        FULL_VOLUMETRIC: 1.0,
        SAMPLED_VOLUMETRIC: 0.1,
        SURFACE_ONLY: 0.0,
    },
    "voxels_per_flaw": 3.0,
    "ultrasonic_flaw_wavelengths": 0.5,
    "radiographic_sensitivity_fraction": 0.02,
    "ultrasonic_max_roughness_um": 6.3,
    "detectability_margin": 1.0,
}

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


def _require_non_negative(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return float(value)


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A detectable flaw size is built from divisions and a cosine, so a
    setup meant to sit exactly on the critical flaw size can land a few
    units in the last place above it. The limit is never relaxed; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_ndt_policy(policy):
    """Check an inspection policy covers every category with sane numbers."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    coverage = policy.get("coverage")
    if not isinstance(coverage, dict):
        raise ValueError("policy coverage must be a mapping")
    missing = set(CRITICALITY_CATEGORIES) - set(coverage)
    if missing:
        raise ValueError(
            "policy coverage is missing categories: %s" % ", ".join(sorted(missing))
        )
    allowed_coverage = (FULL_VOLUMETRIC, SAMPLED_VOLUMETRIC, SURFACE_ONLY)
    for category in CRITICALITY_CATEGORIES:
        _require_choice(
            "policy coverage[%s]" % category, coverage[category], allowed_coverage
        )
    fractions = policy.get("sample_fraction")
    if not isinstance(fractions, dict):
        raise ValueError("policy sample_fraction must be a mapping")
    for level in allowed_coverage:
        if level not in fractions:
            raise ValueError("policy sample_fraction is missing %s" % level)
        value = _require_non_negative("policy sample_fraction[%s]" % level, fractions[level])
        if value > 1.0:
            raise ValueError("policy sample_fraction[%s] exceeds one" % level)
    voxels = _require_positive("voxels_per_flaw", policy.get("voxels_per_flaw"))
    if voxels < 1.0:
        raise ValueError("voxels_per_flaw below one claims sub-voxel detection")
    _require_positive(
        "ultrasonic_flaw_wavelengths", policy.get("ultrasonic_flaw_wavelengths")
    )
    sensitivity = _require_positive(
        "radiographic_sensitivity_fraction",
        policy.get("radiographic_sensitivity_fraction"),
    )
    if sensitivity >= 1.0:
        raise ValueError("radiographic_sensitivity_fraction must be a fraction below one")
    _require_positive(
        "ultrasonic_max_roughness_um", policy.get("ultrasonic_max_roughness_um")
    )
    _require_positive("detectability_margin", policy.get("detectability_margin"))
    return policy


def ct_voxel_size_mm(pixel_pitch_mm, source_to_object_mm, source_to_detector_mm):
    """Reconstructed voxel edge for a cone-beam tomography setup.

    Geometric magnification is the detector distance over the object
    distance, and the voxel is the detector pixel divided back down by
    it. A bulky part cannot be brought close to the source, so a large
    part buys resolution with nothing but standoff.
    """
    pitch = _require_positive("pixel_pitch_mm", pixel_pitch_mm)
    sod = _require_positive("source_to_object_mm", source_to_object_mm)
    sdd = _require_positive("source_to_detector_mm", source_to_detector_mm)
    if sdd < sod:
        raise ValueError(
            "source_to_detector_mm %g is nearer than source_to_object_mm %g; "
            "the detector cannot sit in front of the part" % (sdd, sod)
        )
    magnification = sdd / sod
    return pitch / magnification


def ct_detectable_flaw_mm(voxel_size_mm, voxels_per_flaw=None, policy=None):
    """Smallest flaw a tomography reconstruction can be trusted to show."""
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    voxel = _require_positive("voxel_size_mm", voxel_size_mm)
    count = policy["voxels_per_flaw"] if voxels_per_flaw is None else voxels_per_flaw
    count = _require_positive("voxels_per_flaw", count)
    if count < 1.0:
        raise ValueError("voxels_per_flaw below one claims sub-voxel detection")
    return voxel * count


def ultrasonic_wavelength_mm(velocity_m_s, frequency_mhz):
    """Wavelength of the interrogating pulse in the parent material."""
    velocity = _require_positive("velocity_m_s", velocity_m_s)
    frequency = _require_positive("frequency_mhz", frequency_mhz)
    return velocity / (frequency * 1000.0)


def ultrasonic_detectable_flaw_mm(
    velocity_m_s, frequency_mhz, wavelength_fraction=None, policy=None
):
    """Smallest flaw an ultrasonic setup resolves, as a wavelength share."""
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    share = (
        policy["ultrasonic_flaw_wavelengths"]
        if wavelength_fraction is None
        else wavelength_fraction
    )
    share = _require_positive("wavelength_fraction", share)
    return ultrasonic_wavelength_mm(velocity_m_s, frequency_mhz) * share


def radiographic_detectable_flaw_mm(
    section_thickness_mm, flaw_tilt_deg=0.0, sensitivity_fraction=None, policy=None
):
    """Smallest planar flaw a radiograph resolves at a given beam tilt.

    Contrast comes from the material the flaw removes along the beam, so
    a planar lack-of-fusion flaw lying square to the beam is nearly
    invisible. The through-beam extent falls with the cosine of the
    tilt between the beam and the flaw plane, and the flaw that can
    still be seen grows by the same factor.
    """
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    thickness = _require_positive("section_thickness_mm", section_thickness_mm)
    tilt = _require_non_negative("flaw_tilt_deg", flaw_tilt_deg)
    if tilt >= 90.0:
        raise ValueError(
            "flaw_tilt_deg %g puts the flaw plane square to the beam; "
            "radiography cannot be credited at all" % tilt
        )
    sensitivity = (
        policy["radiographic_sensitivity_fraction"]
        if sensitivity_fraction is None
        else sensitivity_fraction
    )
    sensitivity = _require_positive("sensitivity_fraction", sensitivity)
    return (thickness * sensitivity) / math.cos(math.radians(tilt))


def required_coverage(criticality, policy=None):
    """Volumetric coverage the part criticality category demands."""
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    _require_choice("criticality", criticality, CRITICALITY_CATEGORIES)
    level = policy["coverage"][criticality]
    return {
        "coverage": level,
        "sample_fraction": policy["sample_fraction"][level],
        "volumetric_required": level != SURFACE_ONLY,
    }


def method_applicability(method, part):
    """Whether a method can be credited on this part, and why not."""
    _require_choice("method", method, NDT_METHODS)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    findings = []
    applicable = True
    if method == "computed-tomography":
        path = _require_positive(
            "max_radiographic_path_mm", part.get("max_radiographic_path_mm")
        )
        capability = _require_positive(
            "ct_max_path_mm", part.get("ct_max_path_mm")
        )
        if path > capability and not math.isclose(
            path, capability, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            applicable = False
            findings.append(
                "longest radiographic path %.1f mm exceeds the %.1f mm the "
                "source can penetrate; the reconstruction starves in the core"
                % (path, capability)
            )
    elif method == "ultrasonic":
        roughness = _require_non_negative(
            "surface_roughness_um", part.get("surface_roughness_um")
        )
        limit = _require_positive(
            "ultrasonic_max_roughness_um",
            part.get("ultrasonic_max_roughness_um", DEFAULT_NDT_POLICY["ultrasonic_max_roughness_um"]),
        )
        if roughness > limit and not math.isclose(
            roughness, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ):
            applicable = False
            findings.append(
                "as-built roughness %.2f um is above the %.2f um that couples; "
                "machine the scan surface or drop the method" % (roughness, limit)
            )
        if bool(part.get("has_enclosed_channels", False)):
            applicable = False
            findings.append(
                "enclosed internal channels break the back-wall path; the "
                "channel walls cannot be swept from outside"
            )
    else:
        if bool(part.get("has_enclosed_channels", False)):
            findings.append(
                "enclosed channels superimpose on the projection; unfused "
                "powder inside one reads as parent material"
            )
    return {"method": method, "applicable": applicable, "findings": findings}


def method_detectability_mm(method, part, policy=None):
    """Smallest flaw the declared setup resolves with the given method."""
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    _require_choice("method", method, NDT_METHODS)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    if method == "computed-tomography":
        voxel = ct_voxel_size_mm(
            part.get("pixel_pitch_mm"),
            part.get("source_to_object_mm"),
            part.get("source_to_detector_mm"),
        )
        return ct_detectable_flaw_mm(voxel, policy=policy)
    if method == "ultrasonic":
        return ultrasonic_detectable_flaw_mm(
            part.get("sound_velocity_m_s"), part.get("probe_frequency_mhz"), policy=policy
        )
    return radiographic_detectable_flaw_mm(
        part.get("section_thickness_mm"),
        part.get("flaw_tilt_deg", 0.0),
        policy=policy,
    )


def assess_ndt_plan(case, policy=None):
    """Full inspection verdict for one additively manufactured part."""
    policy = DEFAULT_NDT_POLICY if policy is None else policy
    validate_ndt_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITY_CATEGORIES
    )
    methods = case.get("methods")
    if not isinstance(methods, (list, tuple)) or not methods:
        raise ValueError("case methods must be a non-empty sequence")
    for method in methods:
        _require_choice("method", method, NDT_METHODS)
    critical_flaw = _require_positive(
        "critical_flaw_size_mm", case.get("critical_flaw_size_mm")
    )
    coverage = required_coverage(criticality, policy)
    findings = []
    evaluated = []
    credited = []
    for method in methods:
        applicability = method_applicability(method, case)
        detectable = method_detectability_mm(method, case, policy)
        allowed = critical_flaw / policy["detectability_margin"]
        resolves = _at_most(detectable, allowed)
        entry = {
            "method": method,
            "detectable_flaw_mm": detectable,
            "resolves_critical_flaw": resolves,
            "applicable": applicability["applicable"],
            "credited": bool(applicability["applicable"] and resolves),
            "findings": list(applicability["findings"]),
        }
        if not resolves:
            entry["findings"].append(
                "%s resolves %.4f mm against a %.4f mm critical flaw"
                % (method, detectable, allowed)
            )
        findings.extend(entry["findings"])
        evaluated.append(entry)
        if entry["credited"]:
            credited.append(method)
    volumetric_needed = coverage["volumetric_required"]
    if not volumetric_needed:
        verdict = "surface-inspection-sufficient"
        compliant = True
    elif credited:
        verdict = "volumetric-coverage-demonstrated"
        compliant = True
    else:
        verdict = "volumetric-coverage-not-demonstrated"
        compliant = False
        findings.append(
            "a %s part demands %s coverage and no declared method is credited"
            % (criticality, coverage["coverage"])
        )
    best = min((e["detectable_flaw_mm"] for e in evaluated if e["credited"]), default=None)
    return {
        "criticality": criticality,
        "coverage": coverage["coverage"],
        "sample_fraction": coverage["sample_fraction"],
        "methods": evaluated,
        "credited_methods": credited,
        "best_detectable_flaw_mm": best,
        "detectability_ratio": None if best is None else critical_flaw / best,
        "compliant": compliant,
        "verdict": verdict,
        "findings": findings,
    }
