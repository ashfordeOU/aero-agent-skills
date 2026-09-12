#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.3.4 COPV homogeneous non-metallic liner and
all-composite CPV structural assessment (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's pressure-vessel clause covers two composite vessel
families -- COPVs with a homogeneous non-metallic liner (composite overwrap
carries primary load; liner provides the pressure boundary) and all-composite
CPVs (no distinct liner); composite fibers sustain time-dependent stress
rupture failure governed by a power-law relationship between sustained stress
ratio and time-to-rupture; damage fractions from each operating phase are
summed (Miner-rule analogue) and must not exceed the allowable limit; for
COPVs the liner hoop stress from thin-wall theory is checked against the
liner material allowable; and both vessel types require a Verification by
Damage Tolerance (VDT) assessment confirming that an initial flaw bounded by
the NDT threshold does not grow to the critical flaw size within the service
life. This module implements vessel categorization, sustained stress ratio
computation, power-law stress rupture life and damage accumulation, liner hoop
stress, liner integrity violation flagging, VDT flaw-growth compliance, and a
full vessel compliance review.
"""

# Valid liner type identifiers
LINER_TYPE_NONMETALLIC = "nonmetallic_homogeneous"
LINER_TYPE_ALL_COMPOSITE = "all_composite"
LINER_TYPES = frozenset({LINER_TYPE_NONMETALLIC, LINER_TYPE_ALL_COMPOSITE})

# Derived vessel categories
VESSEL_CATEGORY_COPV = "copv"
VESSEL_CATEGORY_CPV = "cpv"

# Default stress rupture power-law exponent for composite fibers (carbon fiber,
# typical value; material-specific characterization overrides this).
DEFAULT_STRESS_RUPTURE_EXPONENT = 50.0


def categorize_vessel(liner_type):
    """Vessel category for the given liner type: "copv" for a homogeneous
    non-metallic liner, "cpv" for an all-composite vessel. Raises ValueError
    for any liner type outside the two recognised families."""
    if liner_type == LINER_TYPE_NONMETALLIC:
        return VESSEL_CATEGORY_COPV
    if liner_type == LINER_TYPE_ALL_COMPOSITE:
        return VESSEL_CATEGORY_CPV
    raise ValueError(
        "unrecognized liner type %r under ECSS-E-ST-32C clause 4.3.4; "
        "expected one of %r" % (liner_type, sorted(LINER_TYPES))
    )


def sustained_stress_ratio(operating_fiber_stress, mean_fiber_strength):
    """Sustained stress ratio (SSR): operating fiber stress divided by mean
    fiber strength. Returns a positive float; values <= 1.0 are physically
    expected for sustained operation below mean strength. Raises ValueError
    for non-positive inputs."""
    if operating_fiber_stress <= 0:
        raise ValueError("operating_fiber_stress must be > 0")
    if mean_fiber_strength <= 0:
        raise ValueError("mean_fiber_strength must be > 0")
    return operating_fiber_stress / mean_fiber_strength


def stress_rupture_life(ssr, reference_life_s, exponent=DEFAULT_STRESS_RUPTURE_EXPONENT):
    """Time-to-rupture (seconds) for a composite overwrap at the given SSR,
    using the power-law model:
        t_rupture = reference_life_s * (1 / ssr) ** exponent
    reference_life_s is the characteristic life at SSR = 1.0 (mean strength
    loading). Raises ValueError for ssr outside (0, 1], non-positive
    reference_life_s, or non-positive exponent."""
    if not (0 < ssr <= 1.0):
        raise ValueError("ssr must be in (0, 1]; got %r" % (ssr,))
    if reference_life_s <= 0:
        raise ValueError("reference_life_s must be > 0")
    if exponent <= 0:
        raise ValueError("exponent must be > 0")
    return reference_life_s * (1.0 / ssr) ** exponent


def stress_rupture_damage(load_cases):
    """Miner-rule-analogue cumulative stress rupture damage for a composite
    overwrap across all sustained-load phases.

    load_cases: iterable of dicts, each with:
      "ssr": float          — sustained stress ratio for this phase
      "duration_s": float   — phase duration in seconds (>= 0)
      "reference_life_s": float — characteristic fiber life at SSR = 1.0
      "exponent": float (optional) — stress rupture slope; default 50.0

    Returns total damage (must be <= 1.0 for compliance). Raises ValueError
    for negative duration or invalid ssr / reference_life_s."""
    total_damage = 0.0
    for case in load_cases:
        duration_s = case["duration_s"]
        if duration_s < 0:
            raise ValueError("duration_s must be >= 0; got %r" % (duration_s,))
        t_rupt = stress_rupture_life(
            case["ssr"],
            case["reference_life_s"],
            case.get("exponent", DEFAULT_STRESS_RUPTURE_EXPONENT),
        )
        total_damage += duration_s / t_rupt
    return total_damage


def liner_hoop_stress(internal_pressure, vessel_radius, liner_thickness):
    """Thin-wall hoop stress in the non-metallic liner:
        sigma = internal_pressure * vessel_radius / (2 * liner_thickness)
    Units are consistent with the caller's choice (e.g. MPa, mm).
    Raises ValueError for non-positive inputs."""
    if internal_pressure <= 0:
        raise ValueError("internal_pressure must be > 0")
    if vessel_radius <= 0:
        raise ValueError("vessel_radius must be > 0")
    if liner_thickness <= 0:
        raise ValueError("liner_thickness must be > 0")
    return internal_pressure * vessel_radius / (2.0 * liner_thickness)


def liner_integrity_violations(vessel_id, vessel):
    """Violation list (empty if compliant) for non-metallic liner integrity.
    Requires vessel keys "liner_pressure", "liner_radius", "liner_thickness",
    and "allowable_liner_stress". Any None value triggers a
    "missing_liner_parameters" finding. When all are present and the computed
    hoop stress exceeds the allowable, a "liner_stress_exceeded" finding is
    returned."""
    required = ["liner_pressure", "liner_radius", "liner_thickness", "allowable_liner_stress"]
    missing = [k for k in required if vessel.get(k) is None]
    if missing:
        return [{"issue": "missing_liner_parameters", "vessel": vessel_id, "missing": missing}]
    hoop = liner_hoop_stress(
        vessel["liner_pressure"],
        vessel["liner_radius"],
        vessel["liner_thickness"],
    )
    allowable = vessel["allowable_liner_stress"]
    if hoop > allowable:
        return [
            {
                "issue": "liner_stress_exceeded",
                "vessel": vessel_id,
                "hoop_stress": hoop,
                "allowable": allowable,
            }
        ]
    return []


def vdt_compliance(vessel_id, initial_flaw_mm, ndt_threshold_mm,
                   critical_flaw_mm, growth_per_cycle_mm, service_cycles):
    """Verification by Damage Tolerance (VDT) result for one vessel.

    Projects end-of-life flaw size using a linear growth model:
        final_flaw = initial_flaw + growth_per_cycle * service_cycles
    The initial flaw must be >= ndt_threshold_mm (NDT bounds the initial
    flaw from below; a smaller value is non-conservative). Compliance requires
    final_flaw < critical_flaw_mm.

    Returns a dict with keys: vessel, compliant (bool), initial_flaw_mm,
    final_flaw_mm, critical_flaw_mm, margin ((critical - final) / critical),
    and "issue" when non-compliant.

    Raises ValueError for non-positive size/threshold inputs, negative
    growth or cycle count, initial flaw below the NDT threshold, or a
    critical flaw not greater than the initial flaw."""
    if initial_flaw_mm <= 0:
        raise ValueError("initial_flaw_mm must be > 0")
    if ndt_threshold_mm <= 0:
        raise ValueError("ndt_threshold_mm must be > 0")
    if critical_flaw_mm <= 0:
        raise ValueError("critical_flaw_mm must be > 0")
    if growth_per_cycle_mm < 0:
        raise ValueError("growth_per_cycle_mm must be >= 0")
    if service_cycles < 0:
        raise ValueError("service_cycles must be >= 0")
    if initial_flaw_mm < ndt_threshold_mm:
        raise ValueError(
            "initial_flaw_mm (%r) must be >= ndt_threshold_mm (%r); "
            "NDT bounds the initial flaw from below" % (initial_flaw_mm, ndt_threshold_mm)
        )
    if critical_flaw_mm <= initial_flaw_mm:
        raise ValueError(
            "critical_flaw_mm must be > initial_flaw_mm"
        )

    final_flaw_mm = initial_flaw_mm + growth_per_cycle_mm * service_cycles
    margin = (critical_flaw_mm - final_flaw_mm) / critical_flaw_mm

    if final_flaw_mm >= critical_flaw_mm:
        return {
            "vessel": vessel_id,
            "compliant": False,
            "initial_flaw_mm": initial_flaw_mm,
            "final_flaw_mm": final_flaw_mm,
            "critical_flaw_mm": critical_flaw_mm,
            "margin": margin,
            "issue": "flaw_reaches_critical_size",
        }
    return {
        "vessel": vessel_id,
        "compliant": True,
        "initial_flaw_mm": initial_flaw_mm,
        "final_flaw_mm": final_flaw_mm,
        "critical_flaw_mm": critical_flaw_mm,
        "margin": margin,
    }


def copv_review(vessel):
    """Full ECSS-E-ST-32C clause 4.3.4 review for a COPV or CPV.

    vessel dict keys:
      "vessel_id": str
      "liner_type": str — "nonmetallic_homogeneous" or "all_composite"
      "load_cases": list[dict] — phases for stress_rupture_damage
      "stress_rupture_limit": float (optional, default 1.0) — max damage sum
      For COPV only:
        "liner_pressure", "liner_radius", "liner_thickness",
        "allowable_liner_stress" (None triggers a missing-parameter finding)
      "vdt": dict | None — keys: initial_flaw_mm, ndt_threshold_mm,
        critical_flaw_mm, growth_per_cycle_mm, service_cycles

    Returns:
      {
        "vessel_category": str,
        "stress_rupture": [violation dicts],
        "liner_integrity": [violation dicts],  # empty list for CPV
        "vdt": result dict | None,
      }
    Raises ValueError for an unrecognized liner type."""
    vessel_id = vessel["vessel_id"]
    vessel_category = categorize_vessel(vessel["liner_type"])

    # Stress rupture
    load_cases = vessel.get("load_cases", [])
    sr_limit = vessel.get("stress_rupture_limit", 1.0)
    total_sr_damage = stress_rupture_damage(load_cases)
    sr_violations = []
    if total_sr_damage > sr_limit:
        sr_violations.append(
            {
                "issue": "stress_rupture_limit_exceeded",
                "vessel": vessel_id,
                "total_damage": total_sr_damage,
                "limit": sr_limit,
            }
        )

    # Liner integrity (COPV only)
    liner_violations = []
    if vessel_category == VESSEL_CATEGORY_COPV:
        liner_violations = liner_integrity_violations(vessel_id, vessel)

    # VDT
    vdt_result = None
    vdt_params = vessel.get("vdt")
    if vdt_params is not None:
        vdt_result = vdt_compliance(
            vessel_id,
            vdt_params["initial_flaw_mm"],
            vdt_params["ndt_threshold_mm"],
            vdt_params["critical_flaw_mm"],
            vdt_params["growth_per_cycle_mm"],
            vdt_params["service_cycles"],
        )

    return {
        "vessel_category": vessel_category,
        "stress_rupture": sr_violations,
        "liner_integrity": liner_violations,
        "vdt": vdt_result,
    }


def is_vessel_compliant(review):
    """True when the copv_review result is fully clear of violations and the
    VDT (when present) is compliant -- the vessel satisfies clause 4.3.4 for
    this assessment."""
    if review["stress_rupture"]:
        return False
    if review["liner_integrity"]:
        return False
    vdt = review.get("vdt")
    if vdt is not None and not vdt["compliant"]:
        return False
    return True
