"""
copv_metallic_liner_logic.py — ECSS-E-ST-32-02C §4.3.3 COPV with metallic liner.

Deterministic engineering checks for a Composite Overwrapped Pressure Vessel
with metallic liner: liner hoop stress, proof/burst pressure verification,
composite overwrap fiber stress (netting theory), metallic liner fatigue life
(Basquin power-law), and consolidated compliance.

References: ECSS-E-ST-32-02C §4.3.3 (paraphrased; no verbatim text copied).
stdlib only — no third-party dependencies.
"""

PROOF_FACTOR_MIN = 1.25   # minimum proof factor relative to MEOP
BURST_FACTOR_MIN = 2.0    # minimum burst factor relative to MEOP (flight COPV)
FATIGUE_SCATTER = 4.0     # default scatter factor applied to design cycle count


def compute_hoop_stress(
    pressure_pa: float,
    inner_radius_m: float,
    wall_thickness_m: float,
) -> float:
    """
    Compute thin-wall hoop (circumferential) stress using Barlow's formula.

    σ_hoop = p * r / t.  Valid for t/r < 0.1 (thin-wall assumption).

    Returns:
        Hoop stress (Pa).

    Raises:
        ValueError: If any argument is non-positive.
    """
    if pressure_pa <= 0:
        raise ValueError(f"pressure_pa must be positive, got {pressure_pa}")
    if inner_radius_m <= 0:
        raise ValueError(f"inner_radius_m must be positive, got {inner_radius_m}")
    if wall_thickness_m <= 0:
        raise ValueError(f"wall_thickness_m must be positive, got {wall_thickness_m}")
    return (pressure_pa * inner_radius_m) / wall_thickness_m


def compute_margin_of_safety(allowable: float, actual: float) -> float:
    """
    Compute margin of safety: MOS = allowable / actual - 1.

    Positive MOS indicates compliance; zero or negative indicates failure.

    Raises:
        ValueError: If actual or allowable is non-positive.
    """
    if actual <= 0:
        raise ValueError(f"actual must be positive, got {actual}")
    if allowable <= 0:
        raise ValueError(f"allowable must be positive, got {allowable}")
    return (allowable / actual) - 1.0


def compute_proof_pressure(meop_pa: float, proof_factor: float) -> float:
    """
    Compute required proof test pressure.

    Args:
        meop_pa: Maximum Expected Operating Pressure (Pa).
        proof_factor: Multiplier on MEOP (must be >= PROOF_FACTOR_MIN).

    Returns:
        Proof pressure (Pa).

    Raises:
        ValueError: If meop_pa <= 0 or proof_factor < PROOF_FACTOR_MIN.
    """
    if meop_pa <= 0:
        raise ValueError(f"meop_pa must be positive, got {meop_pa}")
    if proof_factor < PROOF_FACTOR_MIN:
        raise ValueError(
            f"proof_factor {proof_factor} is below minimum {PROOF_FACTOR_MIN}"
        )
    return meop_pa * proof_factor


def compute_burst_pressure(meop_pa: float, burst_factor: float) -> float:
    """
    Compute required burst (qualification) pressure.

    Args:
        meop_pa: Maximum Expected Operating Pressure (Pa).
        burst_factor: Multiplier on MEOP (must be >= BURST_FACTOR_MIN).

    Returns:
        Burst pressure (Pa).

    Raises:
        ValueError: If meop_pa <= 0 or burst_factor < BURST_FACTOR_MIN.
    """
    if meop_pa <= 0:
        raise ValueError(f"meop_pa must be positive, got {meop_pa}")
    if burst_factor < BURST_FACTOR_MIN:
        raise ValueError(
            f"burst_factor {burst_factor} is below minimum {BURST_FACTOR_MIN}"
        )
    return meop_pa * burst_factor


def check_proof_factor(proof_factor: float) -> bool:
    """Return True if proof_factor meets the ECSS-E-ST-32-02C minimum."""
    return proof_factor >= PROOF_FACTOR_MIN


def check_burst_factor(burst_factor: float) -> bool:
    """Return True if burst_factor meets the ECSS-E-ST-32-02C minimum."""
    return burst_factor >= BURST_FACTOR_MIN


def compute_fiber_hoop_stress(
    pressure_pa: float,
    inner_radius_m: float,
    overwrap_thickness_m: float,
    fiber_volume_fraction: float,
) -> float:
    """
    Estimate effective hoop fiber stress in the composite overwrap.

    Uses a simplified netting-theory approach for the cylindrical (equatorial)
    section: σ_fiber = p * r / (t_ow * Vf).  Fiber volume fraction scales the
    gross overwrap cross-section down to the net fiber load-bearing area.

    Args:
        pressure_pa: Applied internal pressure (Pa).
        inner_radius_m: Vessel inner radius (m).
        overwrap_thickness_m: Total composite overwrap thickness (m).
        fiber_volume_fraction: Volume fraction of fiber in overwrap (0 < Vf <= 1).

    Returns:
        Effective hoop fiber stress (Pa).

    Raises:
        ValueError: If any argument is out of valid range.
    """
    if pressure_pa <= 0:
        raise ValueError(f"pressure_pa must be positive, got {pressure_pa}")
    if inner_radius_m <= 0:
        raise ValueError(f"inner_radius_m must be positive, got {inner_radius_m}")
    if overwrap_thickness_m <= 0:
        raise ValueError(
            f"overwrap_thickness_m must be positive, got {overwrap_thickness_m}"
        )
    if not (0.0 < fiber_volume_fraction <= 1.0):
        raise ValueError(
            f"fiber_volume_fraction must be in (0, 1], got {fiber_volume_fraction}"
        )
    return (pressure_pa * inner_radius_m) / (overwrap_thickness_m * fiber_volume_fraction)


def compute_fatigue_life_cycles(
    stress_amplitude_pa: float,
    fatigue_strength_reference_pa: float,
    slope_exponent: float,
) -> float:
    """
    Estimate fatigue life using a Basquin-type power-law S-N model.

    Nf = (sigma_f / sigma_a) ** m

    where sigma_f is the fatigue strength reference (stress that causes failure
    at one reversal, extrapolated from the S-N curve) and m is the inverse of
    the Basquin fatigue strength exponent (m = -1/b, typically 3–10 for metals).

    Args:
        stress_amplitude_pa: Half-range stress amplitude in the liner (Pa).
        fatigue_strength_reference_pa: Fatigue strength coefficient sigma_f (Pa).
        slope_exponent: Power-law exponent m (> 0).

    Returns:
        Estimated fatigue life in cycles (float).

    Raises:
        ValueError: If any argument is non-positive.
    """
    if stress_amplitude_pa <= 0:
        raise ValueError(
            f"stress_amplitude_pa must be positive, got {stress_amplitude_pa}"
        )
    if fatigue_strength_reference_pa <= 0:
        raise ValueError(
            f"fatigue_strength_reference_pa must be positive, "
            f"got {fatigue_strength_reference_pa}"
        )
    if slope_exponent <= 0:
        raise ValueError(f"slope_exponent must be positive, got {slope_exponent}")
    return (fatigue_strength_reference_pa / stress_amplitude_pa) ** slope_exponent


def check_fatigue_adequacy(
    computed_life_cycles: float,
    design_cycles: int,
    scatter_factor: float = FATIGUE_SCATTER,
) -> dict:
    """
    Check whether computed fatigue life satisfies the scatter-factored requirement.

    Required life = design_cycles * scatter_factor.
    Passes when computed_life_cycles >= required_life.

    Returns:
        dict with:
            required_life (float): design_cycles * scatter_factor
            margin (float): computed_life / required_life - 1
            compliant (bool): True if margin >= 0

    Raises:
        ValueError: If any argument is non-positive.
    """
    if computed_life_cycles <= 0:
        raise ValueError(
            f"computed_life_cycles must be positive, got {computed_life_cycles}"
        )
    if design_cycles <= 0:
        raise ValueError(f"design_cycles must be positive, got {design_cycles}")
    if scatter_factor <= 0:
        raise ValueError(f"scatter_factor must be positive, got {scatter_factor}")

    required = design_cycles * scatter_factor
    margin = (computed_life_cycles / required) - 1.0
    return {
        "required_life": required,
        "margin": margin,
        "compliant": margin >= 0.0,
    }


def check_liner_yield_at_proof(
    liner_stress_at_proof_pa: float,
    liner_yield_strength_pa: float,
) -> dict:
    """
    Check liner behaviour at proof pressure.

    For a non-autofrettage design the liner must not yield at proof.  For an
    autofrettage design the liner intentionally yields; this function flags which
    regime applies via the 'yielded' key and computes the margin of safety.

    Returns:
        dict with:
            stress_pa (float)
            yield_strength_pa (float)
            mos (float): (yield / stress) - 1
            yielded (bool): True if stress >= yield (autofrettage territory)
            compliant (bool): True if stress < yield (non-autofrettage check)

    Raises:
        ValueError: If either argument is non-positive.
    """
    if liner_stress_at_proof_pa <= 0:
        raise ValueError(
            f"liner_stress_at_proof_pa must be positive, got {liner_stress_at_proof_pa}"
        )
    if liner_yield_strength_pa <= 0:
        raise ValueError(
            f"liner_yield_strength_pa must be positive, got {liner_yield_strength_pa}"
        )

    mos = (liner_yield_strength_pa / liner_stress_at_proof_pa) - 1.0
    yielded = liner_stress_at_proof_pa >= liner_yield_strength_pa
    return {
        "stress_pa": liner_stress_at_proof_pa,
        "yield_strength_pa": liner_yield_strength_pa,
        "mos": mos,
        "yielded": yielded,
        "compliant": not yielded,
    }


def validate_copv_metallic_liner(params: dict) -> dict:
    """
    Run consolidated ECSS-E-ST-32-02C §4.3.3 compliance checks for a COPV
    with metallic liner.

    Required keys in params:
        meop_pa (float): Maximum Expected Operating Pressure (Pa).
        proof_factor (float): Proof factor (>= PROOF_FACTOR_MIN = 1.25).
        burst_factor (float): Burst factor (>= BURST_FACTOR_MIN = 2.0).
        inner_radius_m (float): Vessel inner radius (m).
        liner_thickness_m (float): Metallic liner wall thickness (m).
        liner_yield_pa (float): Liner material tensile yield strength (Pa).
        overwrap_thickness_m (float): Composite overwrap thickness (m).
        fiber_volume_fraction (float): Fiber volume fraction (0, 1].
        fiber_tensile_strength_pa (float): Fiber tensile allowable (Pa).
        liner_stress_amplitude_pa (float): Liner hoop stress amplitude per cycle (Pa).
        fatigue_strength_ref_pa (float): Basquin fatigue strength coefficient (Pa).
        fatigue_slope_exponent (float): Basquin slope exponent m (> 0).
        design_cycles (int): Total pressurisation cycles in mission.
        fatigue_scatter_factor (float, optional): Life scatter factor (default 4.0).

    Returns:
        dict with:
            liner_meop_mos (float)
            liner_proof_check (dict)
            fiber_burst_mos (float)
            fatigue_check (dict)
            proof_factor_ok (bool)
            burst_factor_ok (bool)
            compliant (bool): True only if ALL checks produce no findings.
            findings (list[str]): Human-readable failure descriptions.

    Raises:
        ValueError: If any required key is missing, or if geometry/material
            inputs are invalid.
    """
    required_keys = [
        "meop_pa", "proof_factor", "burst_factor",
        "inner_radius_m", "liner_thickness_m", "liner_yield_pa",
        "overwrap_thickness_m", "fiber_volume_fraction", "fiber_tensile_strength_pa",
        "liner_stress_amplitude_pa", "fatigue_strength_ref_pa",
        "fatigue_slope_exponent", "design_cycles",
    ]
    for k in required_keys:
        if k not in params:
            raise ValueError(f"Missing required parameter: '{k}'")

    findings = []

    meop = params["meop_pa"]
    pf = params["proof_factor"]
    bf = params["burst_factor"]
    r = params["inner_radius_m"]
    t_l = params["liner_thickness_m"]
    sigma_y = params["liner_yield_pa"]
    t_ow = params["overwrap_thickness_m"]
    vf = params["fiber_volume_fraction"]
    f_ult = params["fiber_tensile_strength_pa"]
    sa = params["liner_stress_amplitude_pa"]
    sf_ref = params["fatigue_strength_ref_pa"]
    m_exp = params["fatigue_slope_exponent"]
    n_des = params["design_cycles"]
    scatter = params.get("fatigue_scatter_factor", FATIGUE_SCATTER)

    # Liner hoop stress at MEOP
    liner_meop_stress = compute_hoop_stress(meop, r, t_l)
    liner_meop_mos = compute_margin_of_safety(sigma_y, liner_meop_stress)
    if liner_meop_mos < 0:
        findings.append(
            f"Liner hoop stress at MEOP exceeds yield: "
            f"stress={liner_meop_stress:.3e} Pa, yield={sigma_y:.3e} Pa, "
            f"MOS={liner_meop_mos:.4f}"
        )

    # Proof factor check
    pf_ok = check_proof_factor(pf)
    if not pf_ok:
        findings.append(f"Proof factor {pf} < minimum {PROOF_FACTOR_MIN}")

    # Liner stress at proof — bypass raising helper if factor already flagged
    proof_p = compute_proof_pressure(meop, pf) if pf_ok else meop * pf
    liner_proof_stress = compute_hoop_stress(proof_p, r, t_l)
    liner_proof_check = check_liner_yield_at_proof(liner_proof_stress, sigma_y)
    if not liner_proof_check["compliant"]:
        findings.append(
            f"Liner yields at proof (non-autofrettage design): "
            f"stress={liner_proof_stress:.3e} Pa, yield={sigma_y:.3e} Pa, "
            f"MOS={liner_proof_check['mos']:.4f}"
        )

    # Burst factor check
    bf_ok = check_burst_factor(bf)
    if not bf_ok:
        findings.append(f"Burst factor {bf} < minimum {BURST_FACTOR_MIN}")

    # Fiber hoop stress at burst — bypass raising helper if factor already flagged
    burst_p = compute_burst_pressure(meop, bf) if bf_ok else meop * bf
    fiber_burst_stress = compute_fiber_hoop_stress(burst_p, r, t_ow, vf)
    fiber_burst_mos = compute_margin_of_safety(f_ult, fiber_burst_stress)
    if fiber_burst_mos < 0:
        findings.append(
            f"Fiber hoop stress at burst exceeds allowable: "
            f"stress={fiber_burst_stress:.3e} Pa, allowable={f_ult:.3e} Pa, "
            f"MOS={fiber_burst_mos:.4f}"
        )

    # Fatigue adequacy
    nf = compute_fatigue_life_cycles(sa, sf_ref, m_exp)
    fatigue_check = check_fatigue_adequacy(nf, n_des, scatter)
    if not fatigue_check["compliant"]:
        findings.append(
            f"Fatigue life insufficient: Nf={nf:.2f} cycles, "
            f"required={fatigue_check['required_life']:.2f} cycles, "
            f"margin={fatigue_check['margin']:.4f}"
        )

    return {
        "liner_meop_mos": liner_meop_mos,
        "liner_proof_check": liner_proof_check,
        "fiber_burst_mos": fiber_burst_mos,
        "fatigue_check": fatigue_check,
        "proof_factor_ok": pf_ok,
        "burst_factor_ok": bf_ok,
        "compliant": len(findings) == 0,
        "findings": findings,
    }
