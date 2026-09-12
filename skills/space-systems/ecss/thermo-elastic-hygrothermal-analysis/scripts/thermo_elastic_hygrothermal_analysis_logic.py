"""
Thermo-elastic and hygrothermal stress/strain verification logic.
Paraphrased procedure anchored to ECSS-E-ST-32C clause 4.6.2.11.
stdlib only — no external dependencies.
"""


class ThermoElasticError(ValueError):
    pass


class HygrothermalError(ValueError):
    pass


def compute_thermal_strain(alpha, delta_T):
    """Return free thermal strain: alpha * delta_T."""
    if not isinstance(alpha, (int, float)):
        raise ThermoElasticError("alpha must be numeric")
    if not isinstance(delta_T, (int, float)):
        raise ThermoElasticError("delta_T must be numeric")
    if alpha < 0:
        raise ThermoElasticError("CTE alpha must be non-negative")
    return alpha * delta_T


def compute_thermal_stress(E, alpha, delta_T, restraint_factor=1.0):
    """
    Induced thermal stress in a member with given restraint factor R.
    sigma = -R * E * alpha * delta_T
    restraint_factor: 0.0 = free, 1.0 = fully constrained.
    """
    if not isinstance(E, (int, float)) or E <= 0:
        raise ThermoElasticError("Elastic modulus E must be a positive number")
    if not isinstance(alpha, (int, float)) or alpha < 0:
        raise ThermoElasticError("CTE alpha must be a non-negative number")
    if not isinstance(restraint_factor, (int, float)):
        raise ThermoElasticError("restraint_factor must be numeric")
    if not 0.0 <= restraint_factor <= 1.0:
        raise ThermoElasticError("restraint_factor must be in [0, 1]")
    return -restraint_factor * E * alpha * delta_T


def compute_hygral_strain(beta, delta_M):
    """
    Return free hygral (moisture expansion) strain: beta * delta_M.
    beta: coefficient of moisture expansion (CME), non-negative.
    delta_M: absorbed moisture content change (mass fraction), non-negative.
    """
    if not isinstance(beta, (int, float)) or beta < 0:
        raise HygrothermalError("CME beta must be a non-negative number")
    if not isinstance(delta_M, (int, float)) or delta_M < 0:
        raise HygrothermalError("Moisture content change delta_M must be non-negative")
    return beta * delta_M


def compute_combined_hygrothermal_strain(alpha, delta_T, beta, delta_M):
    """
    Combined thermo-hygral free strain: alpha*delta_T + beta*delta_M.
    """
    e_th = compute_thermal_strain(alpha, delta_T)
    e_h = compute_hygral_strain(beta, delta_M)
    return e_th + e_h


def categorize_load_case(delta_T, delta_M):
    """
    Categorize the hygrothermal load case for a structural element.
    Returns one of: 'thermal-only', 'hygral-only', 'combined', 'none'.
    """
    if not isinstance(delta_T, (int, float)):
        raise ThermoElasticError("delta_T must be numeric")
    if not isinstance(delta_M, (int, float)):
        raise HygrothermalError("delta_M must be numeric")
    has_thermal = delta_T != 0.0
    has_hygral = delta_M != 0.0
    if has_thermal and has_hygral:
        return "combined"
    elif has_thermal:
        return "thermal-only"
    elif has_hygral:
        return "hygral-only"
    else:
        return "none"


def compute_margin_of_safety(allowable, demand):
    """
    Compute margin of safety = (allowable / |demand|) - 1.
    Returns float('inf') when demand is exactly zero.
    Positive MoS = PASS; negative = FAIL.
    """
    if not isinstance(allowable, (int, float)) or allowable <= 0:
        raise ThermoElasticError("allowable must be a positive number")
    if not isinstance(demand, (int, float)):
        raise ThermoElasticError("demand must be numeric")
    if demand == 0.0:
        return float("inf")
    return (allowable / abs(demand)) - 1.0


def check_stress_limit(stress, allowable_stress):
    """
    Check whether |stress| is within allowable_stress.
    Returns dict: stress, allowable, margin_of_safety, status ('PASS'/'FAIL').
    """
    mos = compute_margin_of_safety(allowable_stress, stress)
    return {
        "stress": stress,
        "allowable": allowable_stress,
        "margin_of_safety": mos,
        "status": "PASS" if mos >= 0.0 else "FAIL",
    }


def check_strain_limit(strain, allowable_strain):
    """
    Check whether |strain| is within allowable_strain.
    Returns dict: strain, allowable, margin_of_safety, status ('PASS'/'FAIL').
    """
    if not isinstance(allowable_strain, (int, float)) or allowable_strain <= 0:
        raise ThermoElasticError("allowable_strain must be a positive number")
    mos = compute_margin_of_safety(allowable_strain, strain)
    return {
        "strain": strain,
        "allowable": allowable_strain,
        "margin_of_safety": mos,
        "status": "PASS" if mos >= 0.0 else "FAIL",
    }


def compute_laminate_hygrothermal_resultants(plies, delta_T, delta_M):
    """
    Compute in-plane hygrothermal force resultant N and moment resultant M
    per unit width for a composite laminate.

    N = sum_k  Q11_k * (alpha_k * dT + beta_k * dM) * t_k
    M = sum_k  Q11_k * (alpha_k * dT + beta_k * dM) * t_k * z_mid_k

    plies: list of dicts, each containing:
        'Q11'       — reduced in-plane stiffness (Pa)
        'alpha'     — CTE in the dominant direction (1/K)
        'beta'      — CME in the dominant direction (dimensionless)
        'thickness' — ply thickness (m), positive
        'z_mid'     — distance from laminate mid-plane to ply centre (m)

    Returns dict: N_hygrothermal (N/m), M_hygrothermal (N).
    """
    if not plies:
        raise HygrothermalError("plies list must not be empty")
    required_keys = ("Q11", "alpha", "beta", "thickness", "z_mid")
    N_total = 0.0
    M_total = 0.0
    for i, ply in enumerate(plies):
        for k in required_keys:
            if k not in ply:
                raise HygrothermalError(f"Ply {i} missing required key '{k}'")
        Q11 = ply["Q11"]
        alpha = ply["alpha"]
        beta = ply["beta"]
        t = ply["thickness"]
        z_mid = ply["z_mid"]
        if not isinstance(Q11, (int, float)) or Q11 <= 0:
            raise HygrothermalError(f"Ply {i}: Q11 must be a positive number")
        if not isinstance(t, (int, float)) or t <= 0:
            raise HygrothermalError(f"Ply {i}: thickness must be a positive number")
        if not isinstance(alpha, (int, float)) or alpha < 0:
            raise HygrothermalError(f"Ply {i}: alpha must be non-negative")
        if not isinstance(beta, (int, float)) or beta < 0:
            raise HygrothermalError(f"Ply {i}: beta must be non-negative")
        eps_ht = alpha * delta_T + beta * delta_M
        N_ply = Q11 * eps_ht * t
        M_ply = Q11 * eps_ht * t * z_mid
        N_total += N_ply
        M_total += M_ply
    return {
        "N_hygrothermal": N_total,
        "M_hygrothermal": M_total,
    }


def verify_thermo_elastic_case(E, alpha, delta_T, restraint_factor, allowable_stress):
    """
    End-to-end single-member thermo-elastic verification.
    Returns dict: thermal_strain, thermal_stress, margin_of_safety, status.
    """
    strain = compute_thermal_strain(alpha, delta_T)
    stress = compute_thermal_stress(E, alpha, delta_T, restraint_factor)
    check = check_stress_limit(stress, allowable_stress)
    return {
        "thermal_strain": strain,
        "thermal_stress": stress,
        "margin_of_safety": check["margin_of_safety"],
        "status": check["status"],
    }


def verify_hygrothermal_laminate(plies, delta_T, delta_M, allowable_N, allowable_M):
    """
    End-to-end hygrothermal laminate verification.
    Checks force resultant N and moment resultant M against their allowables.
    Returns dict: N, M, MoS_N, MoS_M, status_N, status_M, overall_status.
    """
    if not isinstance(allowable_N, (int, float)) or allowable_N <= 0:
        raise HygrothermalError("allowable_N must be a positive number")
    if not isinstance(allowable_M, (int, float)) or allowable_M <= 0:
        raise HygrothermalError("allowable_M must be a positive number")
    resultants = compute_laminate_hygrothermal_resultants(plies, delta_T, delta_M)
    N = resultants["N_hygrothermal"]
    M = resultants["M_hygrothermal"]
    mos_N = compute_margin_of_safety(allowable_N, N)
    mos_M = compute_margin_of_safety(allowable_M, M)
    status_N = "PASS" if mos_N >= 0.0 else "FAIL"
    status_M = "PASS" if mos_M >= 0.0 else "FAIL"
    return {
        "N_hygrothermal": N,
        "M_hygrothermal": M,
        "MoS_N": mos_N,
        "MoS_M": mos_M,
        "status_N": status_N,
        "status_M": status_M,
        "overall_status": "PASS" if (status_N == "PASS" and status_M == "PASS") else "FAIL",
    }
