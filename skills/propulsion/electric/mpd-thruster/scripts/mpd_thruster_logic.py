"""Self-field magnetoplasmadynamic (MPD) thruster operating-point logic.

Pure stdlib, math only, deterministic, no RNG. Computes the steady
operating point of a self-field electromagnetic MPD thruster from the
discharge current and the coaxial geometry alone (Jahn, "Physics of
Electric Propulsion", McGraw-Hill 1968; reported in Sutton's Rocket
Propulsion Elements electric-propulsion chapter).

The discharge current drives its own azimuthal magnetic field and the
JxB body force on the arc is the sole acceleration mechanism: the
electromagnetic thrust T = (mu0/(4 pi)) * J^2 * ln(r_a/r_c). Electrode
falls, ionization and thermal-pressure contributions are neglected
(the recorded idealization of the anchor). There is no voltage input,
no applied magnetic field and no electrode-fall or arc-resistance
term: propellant is carried as a mass-flow label only.

The module chains thrust, exhaust velocity v_e = T/m_dot, specific
impulse Isp = v_e/g0, jet kinetic power P_j = T^2/(2 m_dot),
thrust-to-power on the jet-power basis and a reference-only class-band
verdict (Isp 1000-4000 s, thrust-to-power 10-40 mN/kW for the steady
self-field MPD class) that reports position and never enforces it.
"""

import math

MU0 = 4.0 * math.pi * 1e-7  # vacuum permeability, N/A^2 (exact SI value)
MU0_OVER_4PI = MU0 / (4.0 * math.pi)  # law coefficient, about 1e-7 N/A^2
G0 = 9.80665  # standard gravity, m/s^2
MN_PER_KW = 1e6  # N/W to mN/kW scale

# Reference-only class bands for the steady self-field MPD class,
# reported by the verdict, never enforced.
ISP_BAND_S = (1000.0, 4000.0)
TP_BAND_MN_PER_KW = (10.0, 40.0)


def _check_finite(*values):
    """Raise ValueError if any value is not finite."""
    for value in values:
        if not math.isfinite(value):
            raise ValueError("inputs must be finite, got %r" % (value,))


def _position(value, band):
    """Return 'below', 'inside' or 'above' for value against band."""
    if value < band[0]:
        return "below"
    if value > band[1]:
        return "above"
    return "inside"


def self_field_thrust(current_j, radius_ratio):
    """Electromagnetic thrust T (N) from the self-field current-squared law.

    T = MU0_OVER_4PI * J^2 * ln(r_a/r_c), with J the total discharge
    current (A) and r_a/r_c the anode-to-cathode radius ratio of the
    coaxial electrode pair. Raises ValueError if inputs are non-finite,
    current_j < 0 or radius_ratio <= 1 (a coaxial pair needs r_a > r_c).
    current_j = 0 is allowed and returns 0.0 exactly.
    """
    _check_finite(current_j, radius_ratio)
    if current_j < 0.0:
        raise ValueError("discharge current must be >= 0, got %r" % (current_j,))
    if radius_ratio <= 1.0:
        raise ValueError("radius ratio must be > 1, got %r" % (radius_ratio,))
    return MU0_OVER_4PI * current_j * current_j * math.log(radius_ratio)


def exhaust_velocity(thrust, mass_flow):
    """Effective exhaust velocity v_e (m/s) = thrust / mass_flow.

    Definition, not a nozzle expansion: the propellant mass flow
    carries the momentum of the electromagnetic thrust. Raises
    ValueError if inputs are non-finite, thrust < 0 or mass_flow <= 0.
    """
    _check_finite(thrust, mass_flow)
    if thrust < 0.0:
        raise ValueError("thrust must be >= 0, got %r" % (thrust,))
    if mass_flow <= 0.0:
        raise ValueError("mass flow must be > 0, got %r" % (mass_flow,))
    return thrust / mass_flow


def specific_impulse(v_e):
    """Specific impulse Isp (s) = v_e / G0.

    Raises ValueError if v_e is non-finite or negative.
    """
    _check_finite(v_e)
    if v_e < 0.0:
        raise ValueError("exhaust velocity must be >= 0, got %r" % (v_e,))
    return v_e / G0


def jet_power(thrust, mass_flow):
    """Jet kinetic power P_j (W) = thrust^2 / (2 * mass_flow).

    Raises ValueError if inputs are non-finite, thrust < 0 or
    mass_flow <= 0.
    """
    _check_finite(thrust, mass_flow)
    if thrust < 0.0:
        raise ValueError("thrust must be >= 0, got %r" % (thrust,))
    if mass_flow <= 0.0:
        raise ValueError("mass flow must be > 0, got %r" % (mass_flow,))
    return thrust * thrust / (2.0 * mass_flow)


def thrust_to_power(thrust, p_j):
    """Thrust-to-power ratio (N/W) = thrust / p_j on the jet-power basis.

    Raises ValueError if inputs are non-finite, thrust < 0 or p_j <= 0.
    """
    _check_finite(thrust, p_j)
    if thrust < 0.0:
        raise ValueError("thrust must be >= 0, got %r" % (thrust,))
    if p_j <= 0.0:
        raise ValueError("jet power must be > 0, got %r" % (p_j,))
    return thrust / p_j


def mpd_band_verdict(isp, thrust_to_power_mn_per_kw):
    """Reference-only class-band verdict dict for the MPD operating point.

    Reports the position ('below', 'inside' or 'above') of the specific
    impulse against ISP_BAND_S and of the thrust-to-power (mN/kW)
    against TP_BAND_MN_PER_KW, with enforced: False. The bands are
    published ranges for the steady self-field MPD class, reported and
    never enforced: an out-of-band point never raises. Raises ValueError
    only for negative or non-finite inputs.
    """
    _check_finite(isp, thrust_to_power_mn_per_kw)
    if isp < 0.0:
        raise ValueError("specific impulse must be >= 0, got %r" % (isp,))
    if thrust_to_power_mn_per_kw < 0.0:
        raise ValueError(
            "thrust-to-power must be >= 0, got %r" % (thrust_to_power_mn_per_kw,)
        )
    return {
        "isp_band_s": ISP_BAND_S,
        "isp_position": _position(isp, ISP_BAND_S),
        "thrust_to_power_band_mn_per_kw": TP_BAND_MN_PER_KW,
        "thrust_to_power_position": _position(
            thrust_to_power_mn_per_kw, TP_BAND_MN_PER_KW
        ),
        "enforced": False,
    }


def mpd_operating_point(current_j, radius_ratio, mass_flow):
    """Single-point summary dict for the steady self-field MPD thruster.

    Chains the current-squared thrust law, the exhaust-velocity and
    specific-impulse definitions, the jet kinetic power, the
    thrust-to-power ratio (N/W and mN/kW) and the reference-only band
    verdict. ValueErrors propagate from the chained functions.
    """
    thrust = self_field_thrust(current_j, radius_ratio)
    v_e = exhaust_velocity(thrust, mass_flow)
    isp = specific_impulse(v_e)
    p_j = jet_power(thrust, mass_flow)
    ttp_n_per_w = thrust_to_power(thrust, p_j)
    ttp_mn_per_kw = ttp_n_per_w * MN_PER_KW
    return {
        "current_j": current_j,
        "radius_ratio": radius_ratio,
        "mass_flow": mass_flow,
        "thrust": thrust,
        "exhaust_velocity": v_e,
        "specific_impulse": isp,
        "jet_power": p_j,
        "thrust_to_power_n_per_w": ttp_n_per_w,
        "thrust_to_power_mn_per_kw": ttp_mn_per_kw,
        "band_verdict": mpd_band_verdict(isp, ttp_mn_per_kw),
    }
