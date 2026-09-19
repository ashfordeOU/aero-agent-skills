"""Operational constraints and thermo-mechanical interfaces of a mechanism.

Anchor: ECSS-E-ST-33-01C clauses 4.5.3 (operational constraints imposed on the
mechanism by its context -- contamination, magnetic cleanliness, grounding) and
4.6 (thermo-mechanical interface requirements). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Accumulate every declared contamination source over the operational life and
   compare the deposition it produces on the sensitive surface with the
   allowance the mechanism was given, applying the geometric view factor rather
   than assuming every emitted molecule lands.
2. Sum the static residual dipole of the mechanism with the moment its moving
   parts add, convert the worst-case aligned total into the field seen at the
   declared separation, and compare with the magnetic-cleanliness allowance.
3. Walk every grounding path, separating the ones that cross a rotating or
   sliding joint -- those are the paths that degrade with wear and need a
   dedicated bonding element rather than the bearing itself.
4. Convert the expansion mismatch across the mounting interface into an
   interface displacement, then into the load that displacement drives through
   the interface stiffness, and compare both with their budgets.
5. Report the interface conducted heat flux alongside the mechanical findings,
   because the same interface carries both and a stiffening fix usually moves
   the thermal answer too.
"""

import math

__all__ = [
    "BUDGET_TOLERANCE",
    "MU0_OVER_FOUR_PI",
    "validate_positive",
    "validate_non_negative",
    "within_budget",
    "deposition_over_life",
    "assess_contamination",
    "total_dipole_moment",
    "field_at_distance_nt",
    "assess_magnetic_cleanliness",
    "assess_grounding",
    "differential_expansion_mm",
    "interface_induced_load_n",
    "interface_heat_flux_w",
    "assess_thermo_mechanical_interface",
    "assess_operational_constraints",
]

# Budget comparisons are sums of products; a value that is physically exactly on
# its budget can land a few ULPs above it. Absorb the representation error here
# instead of relaxing the engineering allowance.
BUDGET_TOLERANCE = 1e-9

# mu0 / (4 * pi) in T*m/A, exact in SI-2019 to the precision used here.
MU0_OVER_FOUR_PI = 1e-7


def validate_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def within_budget(value, budget):
    """Return True when value sits at or below budget within the tolerance."""
    value = float(value)
    budget = float(budget)
    if value <= budget:
        return True
    return math.isclose(value, budget, rel_tol=BUDGET_TOLERANCE, abs_tol=0.0)


def deposition_over_life(sources, life_years, view_factor=1.0):
    """Return deposition in ng/cm2 on the sensitive surface over the life.

    Each source is a mapping with 'name' and 'rate_ng_cm2_year'; an optional
    per-source 'view_factor' overrides the assembly-level one, which is how a
    source behind a baffle is credited without moving the global geometry.
    """
    if not isinstance(sources, (list, tuple)):
        raise ValueError("sources must be a sequence of source mappings")
    life = validate_positive("life_years", life_years)
    assembly_view = validate_non_negative("view_factor", view_factor)
    if assembly_view > 1.0:
        raise ValueError("view_factor must not exceed 1.0, got %r" % (view_factor,))
    total = 0.0
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError("sources[%d] must be a mapping" % index)
        if "rate_ng_cm2_year" not in source:
            raise ValueError("sources[%d] missing 'rate_ng_cm2_year'" % index)
        rate = validate_non_negative(
            "sources[%d].rate_ng_cm2_year" % index, source["rate_ng_cm2_year"]
        )
        local_view = assembly_view
        if "view_factor" in source:
            local_view = validate_non_negative(
                "sources[%d].view_factor" % index, source["view_factor"]
            )
            if local_view > 1.0:
                raise ValueError("sources[%d].view_factor must not exceed 1.0" % index)
        total += rate * life * local_view
    return total


def assess_contamination(sources, life_years, allowance_ng_cm2, view_factor=1.0):
    """Compare accumulated deposition with the contamination allowance."""
    allowance = validate_positive("allowance_ng_cm2", allowance_ng_cm2)
    deposited = deposition_over_life(sources, life_years, view_factor)
    compliant = within_budget(deposited, allowance)
    findings = []
    if not compliant:
        findings.append(
            "accumulated deposition %.3f ng/cm2 exceeds the allowance %.3f ng/cm2"
            % (deposited, allowance)
        )
    return {
        "deposited_ng_cm2": deposited,
        "allowance_ng_cm2": allowance,
        "utilisation": deposited / allowance,
        "compliant": compliant,
        "findings": findings,
    }


def total_dipole_moment(static_moment_am2, moving_part_moments=None):
    """Return the worst-case aligned residual dipole moment in A*m2.

    Moving parts change their orientation during operation, so the bounding
    assumption is that every contribution lines up at some point in the motion
    envelope; the moments add as magnitudes rather than as fixed vectors.
    """
    total = validate_non_negative("static_moment_am2", static_moment_am2)
    for index, moment in enumerate(moving_part_moments or []):
        total += validate_non_negative("moving_part_moments[%d]" % index, moment)
    return total


def field_at_distance_nt(moment_am2, distance_m):
    """Return the on-axis dipole field in nT at the declared separation."""
    moment = validate_non_negative("moment_am2", moment_am2)
    distance = validate_positive("distance_m", distance_m)
    tesla = MU0_OVER_FOUR_PI * 2.0 * moment / (distance ** 3)
    return tesla * 1.0e9


def assess_magnetic_cleanliness(spec):
    """Compare the mechanism dipole field with the cleanliness allowance."""
    if not isinstance(spec, dict):
        raise ValueError("magnetic spec must be a mapping")
    for key in ("static_moment_am2", "distance_m", "allowance_nt"):
        if key not in spec:
            raise ValueError("magnetic spec missing required key '%s'" % key)
    moment = total_dipole_moment(
        spec["static_moment_am2"], spec.get("moving_part_moments")
    )
    distance = validate_positive("distance_m", spec["distance_m"])
    allowance = validate_positive("allowance_nt", spec["allowance_nt"])
    field = field_at_distance_nt(moment, distance)
    compliant = within_budget(field, allowance)
    findings = []
    if not compliant:
        findings.append(
            "dipole field %.4f nT at %.3f m exceeds the allowance %.4f nT"
            % (field, distance, allowance)
        )
    return {
        "total_moment_am2": moment,
        "field_nt": field,
        "allowance_nt": allowance,
        "compliant": compliant,
        "findings": findings,
    }


def assess_grounding(paths, limit_milliohm):
    """Evaluate the grounding continuity of the mechanism.

    Each path is a mapping with 'name', 'resistance_milliohm' and the boolean
    'crosses_moving_interface'. A path that crosses a rotating or sliding joint
    and has no dedicated bonding element is a finding even when its measured
    resistance passes, because the measurement is of a wear surface.
    """
    if not isinstance(paths, (list, tuple)) or not paths:
        raise ValueError("paths must be a non-empty sequence of path mappings")
    limit = validate_positive("limit_milliohm", limit_milliohm)
    findings = []
    evaluated = []
    for index, path in enumerate(paths):
        if not isinstance(path, dict):
            raise ValueError("paths[%d] must be a mapping" % index)
        if "resistance_milliohm" not in path:
            raise ValueError("paths[%d] missing 'resistance_milliohm'" % index)
        name = path.get("name", "path-%d" % index)
        resistance = validate_non_negative(
            "paths[%d].resistance_milliohm" % index, path["resistance_milliohm"]
        )
        crosses = bool(path.get("crosses_moving_interface", False))
        bonded = bool(path.get("dedicated_bonding_element", False))
        ok = within_budget(resistance, limit)
        if not ok:
            findings.append(
                "grounding path %s measures %.3f mOhm against a %.3f mOhm limit"
                % (name, resistance, limit)
            )
        if crosses and not bonded:
            findings.append(
                "grounding path %s crosses a moving interface with no dedicated "
                "bonding element; continuity relies on a wear surface" % name
            )
            ok = False
        evaluated.append(
            {
                "name": name,
                "resistance_milliohm": resistance,
                "crosses_moving_interface": crosses,
                "dedicated_bonding_element": bonded,
                "compliant": ok,
            }
        )
    return {
        "paths": evaluated,
        "limit_milliohm": limit,
        "compliant": not findings,
        "findings": findings,
    }


def differential_expansion_mm(length_mm, cte_a_ppm_per_k, cte_b_ppm_per_k, delta_t_k):
    """Return the unrestrained expansion mismatch across the interface in mm.

    CTE values are given in ppm/K (1e-6 per kelvin), the units mechanism
    interface control drawings normally carry.
    """
    length = validate_positive("length_mm", length_mm)
    for label, value in (
        ("cte_a_ppm_per_k", cte_a_ppm_per_k),
        ("cte_b_ppm_per_k", cte_b_ppm_per_k),
        ("delta_t_k", delta_t_k),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    mismatch = (float(cte_a_ppm_per_k) - float(cte_b_ppm_per_k)) * 1.0e-6
    return length * mismatch * float(delta_t_k)


def interface_induced_load_n(displacement_mm, stiffness_n_per_mm):
    """Return the load a restrained interface displacement drives, in N."""
    if not isinstance(displacement_mm, (int, float)) or isinstance(displacement_mm, bool):
        raise ValueError("displacement_mm must be a real number")
    if not math.isfinite(float(displacement_mm)):
        raise ValueError("displacement_mm must be finite")
    stiffness = validate_positive("stiffness_n_per_mm", stiffness_n_per_mm)
    return abs(float(displacement_mm)) * stiffness


def interface_heat_flux_w(conductance_w_per_k, delta_t_k):
    """Return the conducted heat crossing the mounting interface, in W."""
    conductance = validate_positive("conductance_w_per_k", conductance_w_per_k)
    if not isinstance(delta_t_k, (int, float)) or isinstance(delta_t_k, bool):
        raise ValueError("delta_t_k must be a real number")
    if not math.isfinite(float(delta_t_k)):
        raise ValueError("delta_t_k must be finite")
    return conductance * abs(float(delta_t_k))


def assess_thermo_mechanical_interface(spec):
    """Evaluate the clause 4.6 thermo-mechanical interface of the mechanism."""
    if not isinstance(spec, dict):
        raise ValueError("interface spec must be a mapping")
    required = (
        "length_mm",
        "cte_mechanism_ppm_per_k",
        "cte_structure_ppm_per_k",
        "delta_t_k",
        "stiffness_n_per_mm",
        "allowed_displacement_mm",
        "allowed_load_n",
    )
    for key in required:
        if key not in spec:
            raise ValueError("interface spec missing required key '%s'" % key)
    displacement = differential_expansion_mm(
        spec["length_mm"],
        spec["cte_mechanism_ppm_per_k"],
        spec["cte_structure_ppm_per_k"],
        spec["delta_t_k"],
    )
    magnitude = abs(displacement)
    allowed_displacement = validate_positive(
        "allowed_displacement_mm", spec["allowed_displacement_mm"]
    )
    allowed_load = validate_positive("allowed_load_n", spec["allowed_load_n"])
    load = interface_induced_load_n(displacement, spec["stiffness_n_per_mm"])
    findings = []
    displacement_ok = within_budget(magnitude, allowed_displacement)
    if not displacement_ok:
        findings.append(
            "interface displacement %.6f mm exceeds the allowed %.6f mm"
            % (magnitude, allowed_displacement)
        )
    load_ok = within_budget(load, allowed_load)
    if not load_ok:
        findings.append(
            "thermally induced interface load %.3f N exceeds the allowed %.3f N"
            % (load, allowed_load)
        )
    heat_flux = None
    if "conductance_w_per_k" in spec:
        heat_flux = interface_heat_flux_w(spec["conductance_w_per_k"], spec["delta_t_k"])
        if "allowed_heat_flux_w" in spec:
            allowed_flux = validate_positive(
                "allowed_heat_flux_w", spec["allowed_heat_flux_w"]
            )
            if not within_budget(heat_flux, allowed_flux):
                findings.append(
                    "interface conducted heat %.3f W exceeds the allowed %.3f W"
                    % (heat_flux, allowed_flux)
                )
    return {
        "displacement_mm": displacement,
        "displacement_magnitude_mm": magnitude,
        "induced_load_n": load,
        "heat_flux_w": heat_flux,
        "compliant": not findings,
        "findings": findings,
    }


def assess_operational_constraints(spec):
    """Run the combined clause 4.5.3 and 4.6 assessment for a mechanism.

    spec keys: contamination (sources, life_years, allowance_ng_cm2, optional
    view_factor), magnetic (see assess_magnetic_cleanliness), grounding (paths,
    limit_milliohm) and interface (see assess_thermo_mechanical_interface).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("contamination", "magnetic", "grounding", "interface"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    contamination_spec = spec["contamination"]
    if not isinstance(contamination_spec, dict):
        raise ValueError("spec['contamination'] must be a mapping")
    for key in ("sources", "life_years", "allowance_ng_cm2"):
        if key not in contamination_spec:
            raise ValueError("contamination spec missing required key '%s'" % key)
    grounding_spec = spec["grounding"]
    if not isinstance(grounding_spec, dict):
        raise ValueError("spec['grounding'] must be a mapping")
    for key in ("paths", "limit_milliohm"):
        if key not in grounding_spec:
            raise ValueError("grounding spec missing required key '%s'" % key)
    contamination = assess_contamination(
        contamination_spec["sources"],
        contamination_spec["life_years"],
        contamination_spec["allowance_ng_cm2"],
        contamination_spec.get("view_factor", 1.0),
    )
    magnetic = assess_magnetic_cleanliness(spec["magnetic"])
    grounding = assess_grounding(
        grounding_spec["paths"], grounding_spec["limit_milliohm"]
    )
    interface = assess_thermo_mechanical_interface(spec["interface"])
    findings = (
        list(contamination["findings"])
        + list(magnetic["findings"])
        + list(grounding["findings"])
        + list(interface["findings"])
    )
    return {
        "contamination": contamination,
        "magnetic": magnetic,
        "grounding": grounding,
        "interface": interface,
        "compliant": not findings,
        "findings": findings,
    }
