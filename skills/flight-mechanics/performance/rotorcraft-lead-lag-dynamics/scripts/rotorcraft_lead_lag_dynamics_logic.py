"""Rotorcraft lead-lag dynamics: lag frequency ratio, multiblade lag modes, ground-resonance clearance.

Pure stdlib, deterministic, no RNG. SI units throughout. Implements the
standard articulated-rotor lead-lag model (Johnson Helicopter Theory,
Leishman Principles of Helicopter Aerodynamics, paraphrased): the rotating
lead-lag frequency ratio of an idealized uniform blade from the lag-hinge
offset, the fixed-frame multiblade lag mode frequencies (collective,
regressing, advancing) for a rotor with three or more blades, and the
Coleman-diagram frequency-coincidence rotor speed where the regressing lag
mode meets the airframe lateral frequency, returning a ground-resonance
clearance verdict against the operating rotor speed.

This leaf provides the deterministic frequency-coincidence and clearance
layer only. Damping and coupled eigenvalue stability analysis, blade
flapping and coning, and control-theory lead-lag compensation are out of
scope here.
"""

import math

# Module constants
PI = math.pi


def lag_frequency_ratio_hinge_offset(hinge_offset_fraction):
    """Rotating lead-lag frequency ratio nu_zeta = sqrt(1.5 * e / (1 - e)).

    e = hinge_offset_fraction in [0, 1), the lag-hinge offset as a fraction
    of rotor radius. Idealized uniform blade, centrifugal-potential
    derivation: the in-plane analog of the flap frequency formula. At e = 0
    the rotating lag frequency is exactly zero (no 1/rev term, unlike flap,
    where nu = 1 at e = 0). Published articulated lag frequencies run about
    0.2-0.4 per rev. Raises ValueError if e < 0 or e >= 1.
    """
    if hinge_offset_fraction < 0:
        raise ValueError("hinge_offset_fraction must be non-negative")
    if hinge_offset_fraction >= 1:
        raise ValueError("hinge_offset_fraction must be below 1")
    return math.sqrt(1.5 * hinge_offset_fraction / (1.0 - hinge_offset_fraction))


def _hz(omega_rad_s, factor):
    """Fixed-frame frequency in Hz for a per-rev factor at rotor speed omega_rad_s."""
    return factor * omega_rad_s / (2.0 * PI)


def _check_nu_omega(nu, omega_rad_s):
    """Shared physical-input checks for the mode and coincidence functions."""
    if nu < 0:
        raise ValueError("nu must be non-negative")
    if omega_rad_s <= 0:
        raise ValueError("omega_rad_s must be positive")


def fixed_frame_lag_modes(nu, omega_rad_s):
    """Fixed-frame multiblade lag mode frequencies for a 3+ bladed rotor.

    Returns {collective_hz: nu * Omega / 2pi, regressing_hz: |1 - nu| *
    Omega / 2pi, advancing_hz: (1 + nu) * Omega / 2pi} with Omega =
    omega_rad_s. The collective mode carries the lag frequency ratio at
    rotor speed, the regressing and advancing modes are the multiblade
    split around 1/rev. Raises ValueError if nu < 0 or omega_rad_s <= 0.
    """
    _check_nu_omega(nu, omega_rad_s)
    return {
        "collective_hz": _hz(omega_rad_s, nu),
        "regressing_hz": _hz(omega_rad_s, abs(1.0 - nu)),
        "advancing_hz": _hz(omega_rad_s, 1.0 + nu),
    }


def regressing_lag_frequency(nu, omega_rad_s):
    """Regressing lag mode frequency |1 - nu| * Omega / 2pi in Hz.

    The fixed-frame regressing lag mode is the one that sweeps downward
    through the airframe frequencies as the rotor slows, which is what
    makes ground resonance a low-rotor-speed phenomenon. Raises ValueError
    if nu < 0 or omega_rad_s <= 0.
    """
    _check_nu_omega(nu, omega_rad_s)
    return _hz(omega_rad_s, abs(1.0 - nu))


def coincidence_rotor_speed(nu, airframe_frequency_hz):
    """Coincidence rotor speed Omega* = 2 pi omega_F / |1 - nu| in rad/s.

    The rotor speed at which the regressing lag mode frequency equals the
    airframe lateral frequency omega_F (Coleman-diagram frequency
    coincidence), the geometric exposure condition for ground resonance.
    Raises ValueError if nu < 0, airframe_frequency_hz <= 0, or |1 - nu| is
    zero (nu = 1 is not physical for lag: nu stays below 1 for realistic
    hinge offsets, and the division would blow up).
    """
    if nu < 0:
        raise ValueError("nu must be non-negative")
    if airframe_frequency_hz <= 0:
        raise ValueError("airframe_frequency_hz must be positive")
    if abs(1.0 - nu) == 0.0:
        raise ValueError("|1 - nu| must be non-zero (nu = 1 is not physical for lag)")
    return 2.0 * PI * airframe_frequency_hz / abs(1.0 - nu)


def ground_resonance_clearance(nu, operating_omega_rad_s,
                               airframe_frequency_hz, margin=0.20):
    """Ground-resonance clearance verdict for a rotor at its operating speed.

    Returns {coincidence_omega: Omega* rad/s, operating_omega:
    operating_omega_rad_s, clearance_fraction: (Omega* - Omega_op)/Omega_op,
    verdict: "clear" if the coincidence speed is more than margin away from
    the operating speed, else "resonance-adjacent"}. ValueErrors from the
    underlying checks propagate; operating_omega_rad_s and margin must be
    positive and non-negative respectively.
    """
    coincidence = coincidence_rotor_speed(nu, airframe_frequency_hz)
    if operating_omega_rad_s <= 0:
        raise ValueError("operating_omega_rad_s must be positive")
    if margin < 0:
        raise ValueError("margin must be non-negative")
    clearance = (coincidence - operating_omega_rad_s) / operating_omega_rad_s
    verdict = "clear" if abs(clearance) > margin else "resonance-adjacent"
    return {
        "coincidence_omega": coincidence,
        "operating_omega": operating_omega_rad_s,
        "clearance_fraction": clearance,
        "verdict": verdict,
    }


def _resolve_lag_frequency_ratio(hinge_offset_or_nu):
    """Resolve the lead_lag_summary first argument to a lag frequency ratio.

    Input convention (documented in the SKILL): values below 1 are the
    lag-hinge offset fraction e in [0, 1) and are converted with
    lag_frequency_ratio_hinge_offset; values of 1 or more are taken as nu
    directly. This matches design practice: articulated rotors are
    specified by hinge offset (lag nu below 1/rev), stiff-inplane rotors by
    a measured or target nu at or above 1/rev. A hinge offset can never
    reach 1, so the two domains do not collide.
    """
    if hinge_offset_or_nu < 0:
        raise ValueError("hinge_offset_or_nu must be non-negative")
    if hinge_offset_or_nu < 1.0:
        return lag_frequency_ratio_hinge_offset(hinge_offset_or_nu)
    return hinge_offset_or_nu


def lead_lag_summary(hinge_offset_or_nu, omega_rad_s, airframe_frequency_hz,
                     margin=0.20):
    """One-call lead-lag assessment dict for a helicopter main rotor.

    First argument is either the lag-hinge offset fraction e in [0, 1) or
    the rotating lag frequency ratio nu directly; _resolve_lag_frequency_ratio
    applies the documented convention (below 1 is a hinge offset, 1 or more
    is nu). Returns {lag_frequency_ratio, collective_hz, regressing_hz,
    advancing_hz, coincidence_omega, operating_omega, clearance_fraction,
    verdict}. ValueErrors propagate from the underlying checks.
    """
    nu = _resolve_lag_frequency_ratio(hinge_offset_or_nu)
    modes = fixed_frame_lag_modes(nu, omega_rad_s)
    clearance = ground_resonance_clearance(nu, omega_rad_s,
                                           airframe_frequency_hz, margin)
    summary = {"lag_frequency_ratio": nu}
    summary.update(modes)
    summary.update(clearance)
    return summary
