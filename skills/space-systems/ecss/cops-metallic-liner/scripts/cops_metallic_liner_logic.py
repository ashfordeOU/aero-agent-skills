"""
COPS with metallic liner structural analysis.
Stiffened shell + liner-composite interaction per ECSS-E-ST-32C §4.4.3.
Stdlib only. Deterministic, offline.
"""


def compute_hoop_strain(pressure, radius, liner_thickness, liner_modulus,
                        composite_thickness, composite_hoop_modulus):
    """
    Compute the common hoop strain at the liner-composite interface via
    the compatibility condition: ε_h = P·r / (E_l·t_l + E_c·t_c).

    Both layers are bonded and share the same circumferential strain;
    the internal pressure load is apportioned by stiffness ratio.

    Parameters
    ----------
    pressure               : float — internal design pressure [Pa]
    radius                 : float — inner radius of liner [m]
    liner_thickness        : float — liner wall thickness [m]
    liner_modulus          : float — liner Young's modulus [Pa]
    composite_thickness    : float — composite overwrap thickness [m]
    composite_hoop_modulus : float — composite hoop Young's modulus [Pa]

    Returns
    -------
    float — hoop strain [dimensionless]
    """
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    if liner_thickness <= 0:
        raise ValueError(f"liner_thickness must be positive, got {liner_thickness}")
    if composite_thickness <= 0:
        raise ValueError(f"composite_thickness must be positive, got {composite_thickness}")
    if liner_modulus <= 0:
        raise ValueError(f"liner_modulus must be positive, got {liner_modulus}")
    if composite_hoop_modulus <= 0:
        raise ValueError(f"composite_hoop_modulus must be positive, got {composite_hoop_modulus}")
    combined_stiffness = liner_modulus * liner_thickness + composite_hoop_modulus * composite_thickness
    return pressure * radius / combined_stiffness


def compute_liner_hoop_stress(hoop_strain, liner_modulus):
    """
    Hoop stress in the metallic liner: σ_l = E_l · ε_h.

    Parameters
    ----------
    hoop_strain   : float — common hoop strain from compute_hoop_strain
    liner_modulus : float — liner Young's modulus [Pa]

    Returns
    -------
    float — liner hoop stress [Pa]
    """
    if liner_modulus < 0:
        raise ValueError(f"liner_modulus must be non-negative, got {liner_modulus}")
    return liner_modulus * hoop_strain


def compute_composite_hoop_stress(hoop_strain, composite_hoop_modulus):
    """
    Hoop stress in the composite overwrap: σ_c = E_c · ε_h.

    Parameters
    ----------
    hoop_strain            : float — common hoop strain from compute_hoop_strain
    composite_hoop_modulus : float — composite hoop Young's modulus [Pa]

    Returns
    -------
    float — composite hoop stress [Pa]
    """
    if composite_hoop_modulus < 0:
        raise ValueError(f"composite_hoop_modulus must be non-negative, got {composite_hoop_modulus}")
    return composite_hoop_modulus * hoop_strain


def check_liner_yield(liner_hoop_stress, liner_yield_stress):
    """
    Determine whether the metallic liner has yielded under the computed
    hoop stress.

    Margin of safety = σ_yield / σ_liner − 1.
    Positive margin means the liner remains elastic; negative means it
    has yielded.

    Parameters
    ----------
    liner_hoop_stress  : float — computed liner hoop stress [Pa]
    liner_yield_stress : float — liner material yield stress [Pa]

    Returns
    -------
    (yielded: bool, margin: float)
    """
    if liner_yield_stress <= 0:
        raise ValueError(f"liner_yield_stress must be positive, got {liner_yield_stress}")
    if liner_hoop_stress <= 0:
        raise ValueError(f"liner_hoop_stress must be positive, got {liner_hoop_stress}")
    margin = liner_yield_stress / liner_hoop_stress - 1.0
    return margin < 0.0, margin


def compute_stiffener_smeared_stiffness(stiffener_area, stiffener_modulus,
                                        stiffener_spacing):
    """
    Compute the smeared axial stiffness contribution of ring stiffeners
    per unit length of shell: K_s = E_s · A_s / spacing [N/m].

    This contribution feeds into stability and dynamic response checks
    that use an effective shell stiffness.

    Parameters
    ----------
    stiffener_area    : float — ring stiffener cross-section area [m²]
    stiffener_modulus : float — stiffener material Young's modulus [Pa]
    stiffener_spacing : float — centre-to-centre stiffener spacing [m]

    Returns
    -------
    float — smeared stiffness per unit length [N/m]
    """
    if stiffener_spacing <= 0:
        raise ValueError(f"stiffener_spacing must be positive, got {stiffener_spacing}")
    if stiffener_area < 0:
        raise ValueError(f"stiffener_area must be non-negative, got {stiffener_area}")
    if stiffener_modulus < 0:
        raise ValueError(f"stiffener_modulus must be non-negative, got {stiffener_modulus}")
    return stiffener_modulus * stiffener_area / stiffener_spacing


def compute_burst_pressure(liner_yield_stress, liner_thickness,
                            composite_hoop_allowable, composite_thickness,
                            radius):
    """
    Estimate the burst pressure from the combined hoop capacity of liner
    and composite: P_burst = (σ_yl·t_l + σ_allow_c·t_c) / r.

    The liner contribution is taken at its yield stress (the liner is
    assumed to have yielded before burst); the composite contribution is
    taken at its hoop allowable.

    Parameters
    ----------
    liner_yield_stress       : float — liner material yield stress [Pa]
    liner_thickness          : float — liner wall thickness [m]
    composite_hoop_allowable : float — composite hoop allowable stress [Pa]
    composite_thickness      : float — composite overwrap thickness [m]
    radius                   : float — inner radius of liner [m]

    Returns
    -------
    float — estimated burst pressure [Pa]
    """
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    if liner_thickness <= 0:
        raise ValueError(f"liner_thickness must be positive, got {liner_thickness}")
    if composite_thickness <= 0:
        raise ValueError(f"composite_thickness must be positive, got {composite_thickness}")
    return (liner_yield_stress * liner_thickness +
            composite_hoop_allowable * composite_thickness) / radius


def check_burst_margin(burst_pressure, design_pressure, required_fos):
    """
    Verify the burst margin of safety:
    MoS = P_burst / (P_design · FoS) − 1.

    Positive margin means compliant with the required burst factor of
    safety; negative margin is a critical structural finding.

    Parameters
    ----------
    burst_pressure  : float — estimated burst pressure [Pa]
    design_pressure : float — maximum design pressure [Pa]
    required_fos    : float — required burst factor of safety (≥ 1.0)

    Returns
    -------
    (compliant: bool, margin: float)
    """
    if required_fos <= 0:
        raise ValueError(f"required_fos must be positive, got {required_fos}")
    if design_pressure <= 0:
        raise ValueError(f"design_pressure must be positive, got {design_pressure}")
    if burst_pressure < 0:
        raise ValueError(f"burst_pressure must be non-negative, got {burst_pressure}")
    limit = design_pressure * required_fos
    margin = burst_pressure / limit - 1.0
    return margin >= 0.0, margin


def assess_cops_metallic_liner(
    radius, liner_thickness, liner_modulus, liner_yield_stress,
    composite_thickness, composite_hoop_modulus, composite_hoop_allowable,
    stiffener_area, stiffener_modulus, stiffener_spacing,
    design_pressure, burst_fos
):
    """
    Full COPS metallic liner compliance assessment per ECSS-E-ST-32C §4.4.3.

    Executes the eight-step workflow: hoop-strain compatibility, liner and
    composite stress, liner yield check, composite allowable check, stiffener
    smearing, burst pressure, and burst margin.

    Parameters
    ----------
    radius                   : float — inner radius [m]
    liner_thickness          : float — liner wall thickness [m]
    liner_modulus            : float — liner Young's modulus [Pa]
    liner_yield_stress       : float — liner yield stress [Pa]
    composite_thickness      : float — composite overwrap thickness [m]
    composite_hoop_modulus   : float — composite hoop Young's modulus [Pa]
    composite_hoop_allowable : float — composite hoop allowable stress [Pa]
    stiffener_area           : float — ring stiffener cross-section area [m²];
                               pass 0.0 when no stiffeners are present
    stiffener_modulus        : float — stiffener material Young's modulus [Pa]
    stiffener_spacing        : float — stiffener centre-to-centre spacing [m]
    design_pressure          : float — maximum design pressure [Pa]
    burst_fos                : float — required burst factor of safety

    Returns
    -------
    dict with keys:
      hoop_strain, liner_hoop_stress, composite_hoop_stress,
      liner_yielded, liner_yield_margin,
      composite_stress_ok, composite_margin,
      stiffener_smeared_stiffness,
      burst_pressure, burst_margin, burst_ok,
      compliant
    """
    for name, val in [
        ("radius", radius),
        ("liner_thickness", liner_thickness),
        ("liner_modulus", liner_modulus),
        ("liner_yield_stress", liner_yield_stress),
        ("composite_thickness", composite_thickness),
        ("composite_hoop_modulus", composite_hoop_modulus),
        ("composite_hoop_allowable", composite_hoop_allowable),
        ("design_pressure", design_pressure),
        ("burst_fos", burst_fos),
    ]:
        if val <= 0:
            raise ValueError(f"{name} must be positive, got {val}")

    # Step 1 — hoop strain via compatibility condition
    hoop_strain = compute_hoop_strain(
        design_pressure, radius, liner_thickness, liner_modulus,
        composite_thickness, composite_hoop_modulus
    )

    # Step 2 — stress in each component
    liner_stress = compute_liner_hoop_stress(hoop_strain, liner_modulus)
    comp_stress = compute_composite_hoop_stress(hoop_strain, composite_hoop_modulus)

    # Step 3 — liner yield
    liner_yielded, liner_yield_margin = check_liner_yield(liner_stress, liner_yield_stress)

    # Step 4 — composite allowable
    comp_stress_ok = comp_stress <= composite_hoop_allowable
    comp_margin = (composite_hoop_allowable / comp_stress - 1.0) if comp_stress > 0 else float("inf")

    # Step 5 — stiffener smeared stiffness (zero when no stiffeners)
    stiffener_smeared = 0.0
    if stiffener_area > 0:
        stiffener_smeared = compute_stiffener_smeared_stiffness(
            stiffener_area, stiffener_modulus, stiffener_spacing
        )

    # Step 6 — burst pressure and margin
    burst_pressure = compute_burst_pressure(
        liner_yield_stress, liner_thickness,
        composite_hoop_allowable, composite_thickness, radius
    )
    burst_ok, burst_margin = check_burst_margin(burst_pressure, design_pressure, burst_fos)

    # Overall compliance: composite margin non-negative AND burst margin non-negative
    compliant = comp_stress_ok and burst_ok

    return {
        "hoop_strain": hoop_strain,
        "liner_hoop_stress": liner_stress,
        "composite_hoop_stress": comp_stress,
        "liner_yielded": liner_yielded,
        "liner_yield_margin": liner_yield_margin,
        "composite_stress_ok": comp_stress_ok,
        "composite_margin": comp_margin,
        "stiffener_smeared_stiffness": stiffener_smeared,
        "burst_pressure": burst_pressure,
        "burst_margin": burst_margin,
        "burst_ok": burst_ok,
        "compliant": compliant,
    }
