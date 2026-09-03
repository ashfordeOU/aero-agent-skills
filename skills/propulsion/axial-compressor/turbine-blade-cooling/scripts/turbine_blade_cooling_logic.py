"""Turbine blade cooling effectiveness logic for AeroSkills.

Estimates the cooling flow required to protect a gas turbine blade row:
cooling effectiveness from the hot gas, allowable blade metal and coolant
supply temperatures, conversion into a required coolant-to-gas mass flow
ratio with a simplified energy balance, a verdict against a practical
bleed limit, and the achievable metal temperature with an optional film
cooling improvement. Pure stdlib, deterministic, SI units (K).

Module constants are documented typicals for conceptual design:
- CP_RATIO: coolant-to-gas specific heat ratio, taken as 1.0.
- BLEED_LIMIT: practical coolant-to-gas flow limit for a blade row, 0.20.
- FILM_IMPROVEMENT: effectiveness gain available from leading-edge film
  cooling over the internal-convection baseline, 0.15.
"""

CP_RATIO = 1.0
BLEED_LIMIT = 0.20
FILM_IMPROVEMENT = 0.15
PHI_CAP = 0.95


def effectiveness(t_gas_k, t_metal_allow_k, t_coolant_k):
    """Return the cooling effectiveness phi = (Tg - Tm) / (Tg - Tc).

    phi is the fraction of the gas-to-coolant temperature difference
    that the blade metal temperature drops from the gas temperature.
    Raises ValueError for non-physical inputs: non-positive gas
    temperature, gas at or below coolant temperature, metal temperature
    at or above the gas temperature, or metal at or below the coolant.
    """
    if t_gas_k <= 0:
        raise ValueError("t_gas_k must be positive")
    if t_gas_k <= t_coolant_k:
        raise ValueError("t_gas_k must exceed t_coolant_k")
    if t_metal_allow_k >= t_gas_k:
        raise ValueError("t_metal_allow_k must be below t_gas_k")
    if t_metal_allow_k <= t_coolant_k:
        raise ValueError("t_metal_allow_k must exceed t_coolant_k")
    return (t_gas_k - t_metal_allow_k) / (t_gas_k - t_coolant_k)


def coolant_fraction(phi):
    """Return the required coolant-to-gas mass flow ratio for phi.

    Simplified energy balance: the coolant heat capacity rate must
    offset the blade heat load implied by the effectiveness, so the
    fraction is phi / (1 - phi) times CP_RATIO.
    """
    if not 0 < phi < 1:
        raise ValueError("phi must lie strictly between 0 and 1")
    return phi / (1.0 - phi) * CP_RATIO


def bleed_verdict(fraction):
    """Return the bleed-limit verdict for a coolant fraction.

    Returns "within bleed limit" when the fraction does not exceed
    BLEED_LIMIT and "exceeds bleed limit" otherwise.
    """
    if fraction < 0:
        raise ValueError("fraction must be non-negative")
    if fraction <= BLEED_LIMIT:
        return "within bleed limit"
    return "exceeds bleed limit"


def metal_temp_with_film(t_gas_k, t_coolant_k, phi_base, film_cooling):
    """Return the achievable blade metal temperature, K.

    With film cooling the effective effectiveness is phi_base plus
    FILM_IMPROVEMENT, capped at PHI_CAP; without film it stays at
    phi_base. Tm = Tg - phi_eff * (Tg - Tc).
    """
    if t_gas_k <= 0:
        raise ValueError("t_gas_k must be positive")
    if t_gas_k <= t_coolant_k:
        raise ValueError("t_gas_k must exceed t_coolant_k")
    if not 0 < phi_base < 1:
        raise ValueError("phi_base must lie strictly between 0 and 1")
    phi_eff = phi_base
    if film_cooling:
        phi_eff = min(PHI_CAP, phi_base + FILM_IMPROVEMENT)
    return t_gas_k - phi_eff * (t_gas_k - t_coolant_k)


def analyze(t_gas_k, t_metal_allow_k, t_coolant_k, film_cooling=False):
    """Return the full cooling estimate dict for a blade row.

    Keys: effectiveness, coolant_fraction, verdict, metal_temp_k (with
    the requested film setting) and margin_k = t_metal_allow - metal_temp.
    """
    phi = effectiveness(t_gas_k, t_metal_allow_k, t_coolant_k)
    fraction = coolant_fraction(phi)
    verdict = bleed_verdict(fraction)
    metal_temp = metal_temp_with_film(
        t_gas_k, t_coolant_k, phi, film_cooling
    )
    return {
        "effectiveness": phi,
        "coolant_fraction": fraction,
        "verdict": verdict,
        "metal_temp_k": metal_temp,
        "margin_k": t_metal_allow_k - metal_temp,
    }
