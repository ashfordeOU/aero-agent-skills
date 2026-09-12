"""
LBB-by-analysis logic: fracture-mechanics and crack-growth checks per
ECSS-E-ST-32C clause 5.3.2 (paraphrased -- no verbatim standard text).
stdlib only -- no third-party dependencies.
"""

import math
from collections import namedtuple


LbbInputs = namedtuple(
    "LbbInputs",
    [
        "wall_thickness",       # t [m]
        "vessel_radius",        # R [m]
        "burst_pressure",       # P_burst [Pa]
        "proof_pressure",       # P_proof [Pa]
        "fracture_toughness",   # K_Ic [Pa*sqrt(m)]
        "yield_strength",       # sigma_y [Pa]
        "geometry_factor",      # Y (dimensionless)
        "initial_crack_depth",  # a_0 [m]
        "initial_half_length",  # c_0 [m]
        "paris_C",              # C in da/dN = C*(delta_K)^m
        "paris_m",              # m exponent
        "delta_stress",         # cyclic stress range [Pa]
        "required_life_cycles", # N_life [cycles]
        "life_safety_factor",   # factor on required life (>= 1.0)
    ],
)

LbbResult = namedtuple(
    "LbbResult",
    [
        "burst_stress",
        "proof_stress",
        "critical_crack_length",        # a_c [m]
        "through_wall_half_length",     # a_tw [m]
        "lbb_size_criterion_pass",
        "growth_cycles_to_through_wall",
        "required_cycles_with_margin",
        "life_criterion_pass",
        "residual_K_at_proof",
        "residual_strength_pass",
        "lbb_demonstrated",
        "findings",
    ],
)


def _validate_inputs(inp):
    if inp.wall_thickness <= 0:
        raise ValueError("wall_thickness must be positive")
    if inp.vessel_radius <= 0:
        raise ValueError("vessel_radius must be positive")
    if inp.burst_pressure <= 0:
        raise ValueError("burst_pressure must be positive")
    if inp.proof_pressure <= 0:
        raise ValueError("proof_pressure must be positive")
    if inp.proof_pressure > inp.burst_pressure:
        raise ValueError("proof_pressure must not exceed burst_pressure")
    if inp.fracture_toughness <= 0:
        raise ValueError("fracture_toughness must be positive")
    if inp.yield_strength <= 0:
        raise ValueError("yield_strength must be positive")
    if inp.geometry_factor <= 0:
        raise ValueError("geometry_factor must be positive")
    if inp.initial_crack_depth <= 0:
        raise ValueError("initial_crack_depth must be positive")
    if inp.initial_crack_depth >= inp.wall_thickness:
        raise ValueError("initial_crack_depth must be less than wall_thickness")
    if inp.initial_half_length <= 0:
        raise ValueError("initial_half_length must be positive")
    if inp.paris_C <= 0:
        raise ValueError("paris_C must be positive")
    if inp.paris_m <= 0:
        raise ValueError("paris_m must be positive")
    if inp.delta_stress <= 0:
        raise ValueError("delta_stress must be positive")
    if inp.required_life_cycles <= 0:
        raise ValueError("required_life_cycles must be positive")
    if inp.life_safety_factor < 1.0:
        raise ValueError("life_safety_factor must be >= 1.0")


def compute_hoop_stress(pressure, radius, thickness):
    """
    Thin-wall hoop stress: sigma = P * R / t.
    Caller is responsible for verifying R/t > 10 applicability.
    """
    if thickness <= 0:
        raise ValueError("thickness must be positive")
    if radius <= 0:
        raise ValueError("radius must be positive")
    if pressure < 0:
        raise ValueError("pressure must be non-negative")
    return pressure * radius / thickness


def compute_stress_intensity(stress, half_crack_length, geometry_factor=1.0):
    """
    Stress intensity factor: K = Y * sigma * sqrt(pi * a).
    a is the characteristic half-crack dimension.
    """
    if stress < 0:
        raise ValueError("stress must be non-negative")
    if half_crack_length <= 0:
        raise ValueError("half_crack_length must be positive")
    if geometry_factor <= 0:
        raise ValueError("geometry_factor must be positive")
    return geometry_factor * stress * math.sqrt(math.pi * half_crack_length)


def compute_critical_crack_length(fracture_toughness, stress, geometry_factor=1.0):
    """
    Critical half-crack length where K = K_Ic:
    a_c = (K_Ic / (Y * sigma))^2 / pi.
    """
    if fracture_toughness <= 0:
        raise ValueError("fracture_toughness must be positive")
    if stress <= 0:
        raise ValueError("stress must be positive")
    if geometry_factor <= 0:
        raise ValueError("geometry_factor must be positive")
    return (fracture_toughness / (geometry_factor * stress)) ** 2 / math.pi


def compute_margin_of_safety(critical, actual):
    """
    Margin of safety: MS = (critical / actual) - 1.
    Positive MS indicates margin available.
    """
    if actual <= 0:
        raise ValueError("actual value must be positive")
    return critical / actual - 1.0


def integrate_paris_growth(
    initial_depth,
    wall_thickness,
    paris_C,
    paris_m,
    delta_stress,
    geometry_factor,
    n_steps=1000,
):
    """
    Numerically integrate Paris law da/dN = C*(delta_K)^m from initial_depth
    to wall_thickness using forward Euler with n_steps increments.
    Assumes constant aspect ratio (conservative).
    Returns (total_cycles, final_depth).
    """
    if initial_depth <= 0 or initial_depth >= wall_thickness:
        raise ValueError("initial_depth must be in (0, wall_thickness)")
    if paris_C <= 0 or paris_m <= 0:
        raise ValueError("Paris constants must be positive")
    if delta_stress <= 0:
        raise ValueError("delta_stress must be positive")
    if n_steps < 10:
        raise ValueError("n_steps must be at least 10")

    a = initial_depth
    step_size = (wall_thickness - initial_depth) / n_steps
    total_cycles = 0.0

    for _ in range(n_steps):
        delta_K = compute_stress_intensity(delta_stress, a, geometry_factor)
        da_dN = paris_C * (delta_K ** paris_m)
        if da_dN <= 0:
            raise ValueError("Paris law produced non-positive da/dN")
        total_cycles += step_size / da_dN
        a += step_size

    return total_cycles, a


def check_lbb_size_criterion(through_wall_half_length, critical_crack_length):
    """
    LBB size criterion: through-wall crack half-length must be strictly less
    than the critical crack length at burst pressure.
    """
    return through_wall_half_length < critical_crack_length


def check_life_criterion(growth_cycles, required_life, safety_factor):
    """
    Life criterion: cycles to through-wall must be at least required_life
    multiplied by safety_factor.
    """
    return growth_cycles >= required_life * safety_factor


def check_residual_strength(K_at_proof, fracture_toughness, proof_stress, yield_strength):
    """
    Residual strength at proof pressure with through-wall crack:
    no fracture (K < K_Ic) and no net-section collapse (sigma < sigma_y).
    """
    no_fracture = K_at_proof < fracture_toughness
    no_net_section_collapse = proof_stress < yield_strength
    return no_fracture and no_net_section_collapse


def assess_lbb(inp):
    """
    Run the complete LBB-by-analysis assessment for a pressurized structure.
    Returns LbbResult with pass/fail flags and computed engineering values.
    """
    _validate_inputs(inp)
    findings = []

    burst_stress = compute_hoop_stress(
        inp.burst_pressure, inp.vessel_radius, inp.wall_thickness
    )
    proof_stress = compute_hoop_stress(
        inp.proof_pressure, inp.vessel_radius, inp.wall_thickness
    )

    a_c = compute_critical_crack_length(
        inp.fracture_toughness, burst_stress, inp.geometry_factor
    )

    cycles, _ = integrate_paris_growth(
        inp.initial_crack_depth,
        inp.wall_thickness,
        inp.paris_C,
        inp.paris_m,
        inp.delta_stress,
        inp.geometry_factor,
    )

    # Through-wall half-length: preserve initial aspect ratio through the wall
    aspect_ratio = inp.initial_half_length / inp.initial_crack_depth
    a_tw = aspect_ratio * inp.wall_thickness

    size_pass = check_lbb_size_criterion(a_tw, a_c)
    if not size_pass:
        findings.append(
            "LBB size criterion FAILED: through-wall half-length {:.4e} m "
            ">= critical crack length {:.4e} m at burst stress".format(a_tw, a_c)
        )

    required_cycles = inp.required_life_cycles * inp.life_safety_factor
    life_pass = check_life_criterion(cycles, inp.required_life_cycles, inp.life_safety_factor)
    if not life_pass:
        findings.append(
            "Crack-growth life FAILED: {:.2e} cycles to through-wall "
            "< required {:.2e} cycles (life x safety factor)".format(
                cycles, required_cycles
            )
        )

    K_proof = compute_stress_intensity(proof_stress, a_tw, inp.geometry_factor)
    res_pass = check_residual_strength(
        K_proof, inp.fracture_toughness, proof_stress, inp.yield_strength
    )
    if not res_pass:
        findings.append(
            "Residual strength FAILED: K_proof={:.4e} Pa*sqrt(m), "
            "K_Ic={:.4e} Pa*sqrt(m), "
            "proof_stress={:.4e} Pa, yield={:.4e} Pa".format(
                K_proof, inp.fracture_toughness, proof_stress, inp.yield_strength
            )
        )

    lbb_demonstrated = size_pass and life_pass and res_pass

    return LbbResult(
        burst_stress=burst_stress,
        proof_stress=proof_stress,
        critical_crack_length=a_c,
        through_wall_half_length=a_tw,
        lbb_size_criterion_pass=size_pass,
        growth_cycles_to_through_wall=cycles,
        required_cycles_with_margin=required_cycles,
        life_criterion_pass=life_pass,
        residual_K_at_proof=K_proof,
        residual_strength_pass=res_pass,
        lbb_demonstrated=lbb_demonstrated,
        findings=findings,
    )
