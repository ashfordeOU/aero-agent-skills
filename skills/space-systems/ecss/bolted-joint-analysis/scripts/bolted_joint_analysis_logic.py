#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.2.13 bolted-joint analysis
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's bolted-joint clause requires the analyst to determine
the load carried by each fastener (distributing the applied load among
fasteners proportionally to their axial stiffness), compute the bearing
stress at each fastener hole (load divided by diameter times plate
thickness), determine the bypass ratio (fraction of total applied load
that passes through the plate section past the fastener rather than being
transferred), check the linear bearing-bypass interaction criterion
(bearing ratio plus bypass ratio must not exceed 1.0), derive bolt preload
from the installation torque using the simplified nut-factor relationship
(F = T / (K * D)), and assess every governing failure mode: bearing,
net-section tension, shear-out, pull-through, fastener shear, fastener
tension, and fatigue. This module implements joint-type categorization,
fastener load distribution, bearing stress and margin, bypass ratio,
bearing-bypass interaction, preload from torque, per-fastener assessment,
and a consolidated joint-compliance check; it does not supply material
allowables, which come from the approved materials data reference.
"""

JOINT_TYPES = frozenset({"metallic_fastener", "composite_bolted", "lug_joint"})

FAILURE_MODES = frozenset({
    "bearing",
    "net_tension",
    "shear_out",
    "pull_through",
    "fastener_shear",
    "fastener_tension",
    "fatigue",
})


def categorize_joint(joint_type):
    """Joint category for a bolted-joint type. Returns joint_type unchanged
    when it is one of the recognized types. Raises ValueError for any
    unrecognized joint type."""
    if joint_type in JOINT_TYPES:
        return joint_type
    raise ValueError(
        "unrecognized joint type %r under E-ST-32C clause 4.6.2.13; "
        "expected one of %s" % (joint_type, sorted(JOINT_TYPES))
    )


def distribute_fastener_loads(total_load_N, stiffnesses_N_per_m):
    """Distribute total_load_N among fasteners proportionally to their
    axial stiffness values. Returns a list of fastener loads (N) in the
    same order as stiffnesses_N_per_m. Raises ValueError for an empty
    stiffness list, a negative total load, or any non-positive stiffness."""
    if not stiffnesses_N_per_m:
        raise ValueError("stiffnesses_N_per_m must not be empty")
    if total_load_N < 0:
        raise ValueError("total_load_N must be >= 0, got %g" % total_load_N)
    for k in stiffnesses_N_per_m:
        if k <= 0:
            raise ValueError(
                "fastener stiffness must be > 0, got %g" % k
            )
    total_stiffness = sum(stiffnesses_N_per_m)
    return [total_load_N * k / total_stiffness for k in stiffnesses_N_per_m]


def bearing_stress_MPa(load_N, diameter_mm, thickness_mm):
    """Bearing stress (MPa) at a fastener hole: load_N / (diameter_mm *
    thickness_mm). Units: N / (mm * mm) = N/mm^2 = MPa. Raises ValueError
    for a negative load, or non-positive diameter or thickness."""
    if load_N < 0:
        raise ValueError("load_N must be >= 0, got %g" % load_N)
    if diameter_mm <= 0:
        raise ValueError("diameter_mm must be > 0, got %g" % diameter_mm)
    if thickness_mm <= 0:
        raise ValueError("thickness_mm must be > 0, got %g" % thickness_mm)
    return load_N / (diameter_mm * thickness_mm)


def bearing_margin_of_safety(bearing_stress, allowable_bearing_stress):
    """Margin of safety for bearing: (allowable / applied) - 1.
    Positive margin = passing; negative margin = failing. Raises ValueError
    for non-positive bearing_stress or allowable_bearing_stress."""
    if bearing_stress <= 0:
        raise ValueError(
            "bearing_stress must be > 0, got %g" % bearing_stress
        )
    if allowable_bearing_stress <= 0:
        raise ValueError(
            "allowable_bearing_stress must be > 0, got %g"
            % allowable_bearing_stress
        )
    return (allowable_bearing_stress / bearing_stress) - 1.0


def bypass_ratio(fastener_load_N, total_load_N):
    """Fraction of the total load that bypasses the fastener:
    (total_load_N - fastener_load_N) / total_load_N. Returns 0.0 when
    total_load_N is 0.0. Raises ValueError for negative loads or a
    fastener load that exceeds the total load."""
    if total_load_N < 0:
        raise ValueError("total_load_N must be >= 0, got %g" % total_load_N)
    if fastener_load_N < 0:
        raise ValueError(
            "fastener_load_N must be >= 0, got %g" % fastener_load_N
        )
    if fastener_load_N > total_load_N + 1e-9:
        raise ValueError(
            "fastener_load_N (%g) exceeds total_load_N (%g)"
            % (fastener_load_N, total_load_N)
        )
    if total_load_N == 0.0:
        return 0.0
    return (total_load_N - fastener_load_N) / total_load_N


def bearing_bypass_interaction(bearing_ratio_val, bypass_ratio_val):
    """Linear bearing-bypass interaction: bearing_ratio + bypass_ratio.
    A value <= 1.0 satisfies the interaction criterion. Raises ValueError
    for a negative input ratio."""
    if bearing_ratio_val < 0:
        raise ValueError(
            "bearing_ratio_val must be >= 0, got %g" % bearing_ratio_val
        )
    if bypass_ratio_val < 0:
        raise ValueError(
            "bypass_ratio_val must be >= 0, got %g" % bypass_ratio_val
        )
    return bearing_ratio_val + bypass_ratio_val


def preload_from_torque_N(torque_Nm, nut_factor, diameter_mm):
    """Bolt preload (N) from installation torque using the simplified
    nut-factor formula: F = T / (K * D), where T is torque in N·m, K is
    the dimensionless nut factor, and D is diameter in metres. Raises
    ValueError for non-positive torque, nut_factor, or diameter_mm."""
    if torque_Nm <= 0:
        raise ValueError("torque_Nm must be > 0, got %g" % torque_Nm)
    if nut_factor <= 0:
        raise ValueError("nut_factor must be > 0, got %g" % nut_factor)
    if diameter_mm <= 0:
        raise ValueError("diameter_mm must be > 0, got %g" % diameter_mm)
    diameter_m = diameter_mm / 1000.0
    return torque_Nm / (nut_factor * diameter_m)


def _assess_single_fastener(fastener_id, load_N, total_load_N,
                             diameter_mm, plate_thickness_mm,
                             allowable_bearing_MPa):
    """Per-fastener assessment. Returns a dict with computed quantities
    and a violations list. allowable_bearing_MPa=None means the allowable
    has not been provided (itself a finding)."""
    br_stress = bearing_stress_MPa(load_N, diameter_mm, plate_thickness_mm)
    bp_ratio = bypass_ratio(load_N, total_load_N)
    violations = []

    if allowable_bearing_MPa is None:
        ms = None
        br_ratio = None
        interaction = None
        violations.append({
            "issue": "missing_allowable_bearing_stress",
            "fastener": fastener_id,
        })
    elif br_stress == 0.0:
        ms = float("inf")
        br_ratio = 0.0
        interaction = bearing_bypass_interaction(0.0, bp_ratio)
    else:
        ms = bearing_margin_of_safety(br_stress, allowable_bearing_MPa)
        br_ratio = br_stress / allowable_bearing_MPa
        interaction = bearing_bypass_interaction(br_ratio, bp_ratio)
        if ms < 0:
            violations.append({
                "issue": "bearing_overstress",
                "fastener": fastener_id,
                "margin_of_safety": ms,
            })
        if interaction > 1.0:
            violations.append({
                "issue": "bearing_bypass_interaction_exceeded",
                "fastener": fastener_id,
                "interaction": interaction,
            })

    return {
        "id": fastener_id,
        "load_N": load_N,
        "bearing_stress_MPa": br_stress,
        "bypass_ratio": bp_ratio,
        "margin_of_safety": ms,
        "bearing_ratio": br_ratio,
        "interaction": interaction,
        "violations": violations,
    }


def assess_joint(joint):
    """Full bolted-joint assessment per E-ST-32C clause 4.6.2.13.

    joint: {
        "joint_type": str,          # "metallic_fastener" | "composite_bolted" | "lug_joint"
        "total_load_N": float,
        "fasteners": [
            {
                "id": str,
                "stiffness_N_per_m": float,
                "diameter_mm": float,
                "plate_thickness_mm": float,
                "allowable_bearing_MPa": float | None,
            },
            ...
        ]
    }

    Returns {
        "joint_type": str,
        "fastener_results": [...],
        "violations": [...],
        "compliant": bool,
    }.

    Raises ValueError for an unrecognized joint_type or invalid fastener
    geometry. Does not mutate the input dict."""
    categorize_joint(joint["joint_type"])
    total_load = joint["total_load_N"]
    fasteners = joint["fasteners"]
    stiffnesses = [f["stiffness_N_per_m"] for f in fasteners]
    loads = distribute_fastener_loads(total_load, stiffnesses)

    fastener_results = []
    all_violations = []
    for f, load in zip(fasteners, loads):
        result = _assess_single_fastener(
            f["id"],
            load,
            total_load,
            f["diameter_mm"],
            f["plate_thickness_mm"],
            f.get("allowable_bearing_MPa"),
        )
        fastener_results.append(result)
        all_violations.extend(result["violations"])

    return {
        "joint_type": joint["joint_type"],
        "fastener_results": fastener_results,
        "violations": all_violations,
        "compliant": len(all_violations) == 0,
    }


def is_joint_compliant(assessment):
    """True when the assess_joint result carries no violations."""
    return assessment["compliant"]
