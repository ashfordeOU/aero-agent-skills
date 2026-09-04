"""Rotorcraft autorotative descent estimation logic (pure stdlib).

Empirical energy method for the power-off autorotative descent of a
single-rotor helicopter, following NASA TM 78452 (Talbot and Schroers
1978, "A Simple Method for Estimating Minimum Autorotative Descent Rate
of Single Rotor Helicopters", NTRS 19780012170, public domain).

Scope note: this module never evaluates momentum theory in descent; the
vertical-descent vortex-ring and windmill transition range invalidates
momentum theory there (wave-31 review receipt). Two deterministic,
flight-test-validated estimates are provided instead: the classical
energy balance V = P_min / W, which the paper documents to overestimate
the measured minimum descent rate, and the empirical Talbot-Schoers
least-squares correlation V_est = M1 * OmegaR * (C_PMIN / C_T) + M0,
whose coefficients are pinned to the public-domain NASA values.
"""

M0_TALBOT_MPS = 2.30  # NASA TM 78452 eq. 14 intercept of the empirical correlation (m/s).
M1_TALBOT = 0.66      # NASA TM 78452 eq. 14 slope of the empirical correlation.
G0 = 9.80665          # Standard gravity (m/s^2).
MPS_TO_FT_PER_MIN = 60.0 / 0.3048  # Unit conversion, 196.8504 ft/min per m/s.

VALIDITY_NOTE = (
    "steady minimum-rate autorotative glide of a single main rotor "
    "helicopter; not the vortex-ring vertical-descent regime"
)


def _require_positive(value, name):
    """Raise ValueError unless value is strictly positive."""
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (name, value))


def energy_method_sink_rate(p_min_level_w, weight_n):
    """Return the energy-balance sink rate V = p_min_level_w / weight_n (m/s).

    Classical energy method W * V = P_min for steady power-off descent:
    all the minimum level-flight power would go into the descent rate.
    Documented to overestimate the measured minimum autorotative descent
    rate. Raises ValueError on non-positive power or weight.
    """
    _require_positive(p_min_level_w, "p_min_level_w")
    _require_positive(weight_n, "weight_n")
    return p_min_level_w / weight_n


def talbot_min_descent_rate_mps(cp_min, c_t, tip_speed_mps):
    """Return the empirical minimum descent rate V_est (m/s).

    V_est = M1_TALBOT * tip_speed_mps * (cp_min / c_t) + M0_TALBOT,
    the NASA TM 78452 eq. 14 least-squares fit through measured
    minimum-descent-rate data of multiple single-rotor helicopters.
    Raises ValueError if c_t <= 0, tip_speed_mps <= 0 or cp_min < 0.
    """
    if c_t <= 0:
        raise ValueError("c_t must be positive, got %r" % (c_t,))
    if tip_speed_mps <= 0:
        raise ValueError("tip_speed_mps must be positive, got %r" % (tip_speed_mps,))
    if cp_min < 0:
        raise ValueError("cp_min must be non-negative, got %r" % (cp_min,))
    return M1_TALBOT * tip_speed_mps * (cp_min / c_t) + M0_TALBOT_MPS


def talbot_min_descent_rate_from_power(p_min_level_w, weight_n, tip_speed_mps):
    """Return the empirical minimum descent rate from power entry (m/s).

    In level flight T = W, so OmegaR * C_PMIN / C_T = P_min / T =
    P_min / W and V_est = M1_TALBOT * p_min_level_w / weight_n +
    M0_TALBOT_MPS. The tip speed argument is required for dimensional
    consistency and is validated even though it cancels in level flight.
    Raises ValueError on non-positive power, weight or tip speed.
    """
    _require_positive(p_min_level_w, "p_min_level_w")
    _require_positive(weight_n, "weight_n")
    _require_positive(tip_speed_mps, "tip_speed_mps")
    return M1_TALBOT * (p_min_level_w / weight_n) + M0_TALBOT_MPS


def autorotative_descent_assessment(weight_n, p_min_level_w, tip_speed_mps):
    """Return the autorotative descent assessment dictionary.

    Keys: energy_method_sink_rate_mps, talbot_min_descent_rate_mps,
    talbot_min_descent_rate_ft_per_min, power_to_weight_ratio_mps and
    validity_note. ValueErrors from the underlying functions propagate.
    """
    energy_mps = energy_method_sink_rate(p_min_level_w, weight_n)
    talbot_mps = talbot_min_descent_rate_from_power(
        p_min_level_w, weight_n, tip_speed_mps
    )
    return {
        "energy_method_sink_rate_mps": energy_mps,
        "talbot_min_descent_rate_mps": talbot_mps,
        "talbot_min_descent_rate_ft_per_min": talbot_mps * MPS_TO_FT_PER_MIN,
        "power_to_weight_ratio_mps": p_min_level_w / weight_n,
        "validity_note": VALIDITY_NOTE,
    }
