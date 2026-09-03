"""Pitch bandwidth and phase-delay criterion (MIL-STD-1797A style).

Models the pitch attitude response as a short-period mode plus a control
anticipation numerator time constant and an actuator lag:

    G(s) = (1 + T_th2*s) / (s*(s**2 + 2*zeta*wn*s + wn**2)*(1 + s/w_act))

with K normalized to 1.0 because the criterion uses phase and gain ratio
only.  Evaluates the open loop frequency response, finds the bandwidth
frequency omega_BW (lower of the 45 degree phase margin frequency and the
6 dB gain margin frequency), the -180 degree frequency omega_180, the
phase delay tau_p from the phase at twice omega_180, and grades the
result against representative Category A Level 1/2/3 boundaries.

Pure stdlib, deterministic, offline.  No numpy, scipy or network access.
"""

import math

PI = math.pi

# Representative Category A pitch bandwidth / phase delay boundaries from
# MIL-STD-1797A 4.5.1 (class dependent in the standard; verify against the
# current revision before certifying an airframe).
L1_OMEGA = 3.5  # rad/s, Level 1 minimum bandwidth frequency
L2_OMEGA = 2.5  # rad/s, Level 2 minimum bandwidth frequency
L1_TAU = 0.2    # s, Level 1 maximum phase delay
L2_TAU = 0.2    # s, Level 2 maximum phase delay

PHASE_STEP = 0.01      # rad/s sampling step for the dense phase table
PHASE_START = 0.01     # rad/s, first sample of the scanned band
GM_TARGET_DB = -6.0    # dB, 6 dB gain margin level


def _validate(wn, zeta, T_th2, w_act):
    """Raise ValueError on non-physical model parameters."""
    if wn is None or wn <= 0.0:
        raise ValueError("wn must be positive (rad/s)")
    if zeta is None or zeta <= 0.0 or zeta >= 1.0:
        raise ValueError("zeta must be in (0, 1)")
    if T_th2 is None or T_th2 <= 0.0:
        raise ValueError("T_th2 must be positive (s)")
    if w_act is None or w_act <= wn:
        raise ValueError("w_act must exceed wn (rad/s)")


def _validate_w(w):
    """Raise ValueError on a non-positive evaluation frequency."""
    if w is None or w <= 0.0:
        raise ValueError("frequency w must be positive (rad/s)")


def transfer(wn, zeta, T_th2, w_act, w):
    """Return complex G(j*w) for the pitch attitude transfer function.

    w is the evaluation frequency in rad/s.  Raises ValueError for
    non-physical parameters or a non-positive w.
    """
    _validate(wn, zeta, T_th2, w_act)
    _validate_w(w)
    num = complex(1.0, T_th2 * w)
    integrator = complex(0.0, w)
    quadratic = complex(wn * wn - w * w, 2.0 * zeta * wn * w)
    actuator = complex(1.0, w / w_act)
    return num / (integrator * quadratic * actuator)


def _quad_phase_deg(wn, zeta, w):
    """Phase of the quadratic factor in degrees, continuous in (0, 180)."""
    return math.degrees(math.atan2(2.0 * zeta * wn * w, wn * wn - w * w))


def phase_deg(wn, zeta, T_th2, w_act, w):
    """Unwrapped phase of G(j*w) in degrees, starting near -90 at w ~ 0.

    Branch-corrected analytic form: atan2 keeps the quadratic factor phase
    continuous from 0 to 180 degrees, so the total phase

        phase = atan(w*T_th2) - 90 - quad_phase - atan(w/w_act)

    never jumps.  It starts at -90 degrees as w goes to 0, may rise a
    fraction of a degree just above zero where the control anticipation
    lead outruns the mode lag, and then decreases continuously through
    the -135 and -180 degree crossings.  This equals the numeric unwrap
    (unwrap_phase_deg over a fine 0.01 rad/s sample grid) to well below
    0.01 degree everywhere, and is exact at every single w.
    """
    _validate(wn, zeta, T_th2, w_act)
    _validate_w(w)
    num_lead = math.degrees(math.atan(T_th2 * w))
    act_lag = math.degrees(math.atan(w / w_act))
    return num_lead - 90.0 - _quad_phase_deg(wn, zeta, w) - act_lag


def unwrap_phase_deg(phases_deg):
    """Numeric unwrap of a principal-phase series in degrees.

    Adds or subtracts multiples of 360 so every consecutive jump lies in
    (-180, 180], keeping a monotone decreasing phase series continuous.
    Returns a new list; the first entry is kept unchanged.
    """
    if not phases_deg:
        return []
    out = [float(phases_deg[0])]
    for raw in phases_deg[1:]:
        diff = raw - out[-1]
        while diff > 180.0:
            diff -= 360.0
        while diff <= -180.0:
            diff += 360.0
        out.append(out[-1] + diff)
    return out


def _raw_phase_deg(wn, zeta, T_th2, w_act, w):
    """Principal phase of G(j*w) in (-180, 180] from atan2(imag, real)."""
    _validate(wn, zeta, T_th2, w_act)
    _validate_w(w)
    g = transfer(wn, zeta, T_th2, w_act, w)
    return math.degrees(math.atan2(g.imag, g.real))


def _scan_max(w_act):
    """Upper end of the scanned band: max(4*w_act, 200) rad/s."""
    return max(4.0 * w_act, 200.0)


def _phase_table(wn, zeta, T_th2, w_act):
    """Dense (freqs, unwrapped phase deg) sample table over the band.

    Samples the principal phase every PHASE_STEP rad/s from PHASE_START to
    max(4*w_act, 200) rad/s and numerically unwraps the series so it is
    continuous, decreasing from about -90 degrees once the mode lag
    dominates the control anticipation lead.
    """
    _validate(wn, zeta, T_th2, w_act)
    wmax = _scan_max(w_act)
    n = int(round((wmax - PHASE_START) / PHASE_STEP)) + 1
    freqs = [PHASE_START + PHASE_STEP * i for i in range(n)]
    raw = [_raw_phase_deg(wn, zeta, T_th2, w_act, w) for w in freqs]
    return freqs, unwrap_phase_deg(raw)


def _bisect(f, a, b, target, tol=1e-10, max_iter=80):
    """Bisection root finder for a monotone scalar function f.

    Finds x in (a, b) with f(x) = target, given f(a) - target and
    f(b) - target have opposite signs.  Pure float arithmetic, no imports
    beyond math.  Returns the refined root.
    """
    fa = f(a) - target
    fb = f(b) - target
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (a + b)
        fm = f(mid) - target
        if fm == 0.0 or 0.5 * (b - a) < tol:
            return mid
        if fa * fm < 0.0:
            b = mid
            fb = fm
        else:
            a = mid
            fa = fm
    return 0.5 * (a + b)


def find_root_phase(wn, zeta, T_th2, w_act, target_deg):
    """Frequency where the unwrapped phase equals target_deg, or None.

    Locates the bracketing pair on the dense unwrapped table, then refines
    with bisection on phase_deg.  Returns None when the target phase is
    never reached inside the scanned band (0.01 to max(4*w_act, 200) rad/s).
    """
    _validate(wn, zeta, T_th2, w_act)
    freqs, phases = _phase_table(wn, zeta, T_th2, w_act)
    if phases[0] < target_deg or phases[-1] > target_deg:
        return None
    for i in range(len(freqs) - 1):
        if phases[i] >= target_deg >= phases[i + 1]:
            return _bisect(
                lambda w: phase_deg(wn, zeta, T_th2, w_act, w),
                freqs[i], freqs[i + 1], float(target_deg))
    return None


def mag_db(wn, zeta, T_th2, w_act, w):
    """Magnitude of G(j*w) in dB: 20*log10(|G|)."""
    _validate(wn, zeta, T_th2, w_act)
    _validate_w(w)
    num_mag = math.hypot(1.0, T_th2 * w)
    integ_mag = w
    quad_mag = math.hypot(wn * wn - w * w, 2.0 * zeta * wn * w)
    act_mag = math.hypot(1.0, w / w_act)
    return 20.0 * math.log10(num_mag / (integ_mag * quad_mag * act_mag))


def _find_gm6(wn, zeta, T_th2, w_act):
    """Frequency of the stability-relevant -6 dB gain crossing, or None.

    Scans the band from PHASE_START upward for the downward -6 dB gain
    crossing and keeps it only when the unwrapped phase at the crossing is
    at or beyond -180 degrees, the region where gain margin limits the
    loop.  The low frequency crossing of the normalized attitude response
    (phase still near -90 to -135) never limits bandwidth, so it is
    reported as None.  This is the documented gain-margin interpretation
    of the bandwidth criterion for a K = 1 normalized response.
    """
    _validate(wn, zeta, T_th2, w_act)
    wmax = _scan_max(w_act)
    n = int(round((wmax - PHASE_START) / PHASE_STEP)) + 1
    prev_w = PHASE_START
    prev_db = mag_db(wn, zeta, T_th2, w_act, prev_w)
    for i in range(1, n):
        w = PHASE_START + PHASE_STEP * i
        db = mag_db(wn, zeta, T_th2, w_act, w)
        if prev_db >= GM_TARGET_DB > db:
            crossing = _bisect(
                lambda x: mag_db(wn, zeta, T_th2, w_act, x),
                prev_w, w, GM_TARGET_DB)
            if crossing is not None and \
                    phase_deg(wn, zeta, T_th2, w_act, crossing) <= -180.0:
                return crossing
        prev_w = w
        prev_db = db
    return None


def bandwidth(wn, zeta, T_th2, w_act):
    """Evaluate the pitch bandwidth criterion metrics.

    Returns a dict with keys:
      w_135   frequency of the 45 degree phase margin crossing (rad/s) or
              None if never reached in the scanned band,
      w_gm6   6 dB gain margin crossing frequency (rad/s) or None,
      omega_BW  min of the two crossing frequencies that exist,
      w_180   frequency of the -180 degree crossing (rad/s) or None,
      tau_p   phase delay in seconds from the phase at 2*w_180, or None.
    """
    _validate(wn, zeta, T_th2, w_act)
    w_135 = find_root_phase(wn, zeta, T_th2, w_act, -135.0)
    w_gm6 = _find_gm6(wn, zeta, T_th2, w_act)
    present = [w for w in (w_135, w_gm6) if w is not None]
    omega_bw = min(present) if present else None
    w_180 = find_root_phase(wn, zeta, T_th2, w_act, -180.0)
    if w_180 is not None:
        tau_p = -(phase_deg(wn, zeta, T_th2, w_act, 2.0 * w_180) + 180.0) \
            / (2.0 * w_180) * (PI / 180.0)
    else:
        tau_p = None
    return {"w_135": w_135, "w_gm6": w_gm6, "omega_BW": omega_bw,
            "w_180": w_180, "tau_p": tau_p}


def level_verdict(omega_BW, tau_p):
    """Grade the Category A bandwidth and phase delay verdict.

    Returns a dict with:
      level    'Level 1', 'Level 2' or 'Level 3',
      limiting 'bandwidth', 'phase delay' or 'both' (which criterion
               pushed the verdict below the previous level; 'bandwidth'
               when both metrics pass at Level 1),
      missing  list of metrics that were None and so could not be graded.
    Boundaries are the representative MIL-STD-1797A 4.5.1 Category A
    values (class dependent; verify against the current revision).
    """
    missing = []
    if omega_BW is None:
        missing.append("omega_BW")
    if tau_p is None:
        missing.append("tau_p")
    if omega_BW is not None and tau_p is not None:
        if omega_BW >= L1_OMEGA and tau_p <= L1_TAU:
            return {"level": "Level 1", "limiting": "bandwidth",
                    "missing": missing}
        if omega_BW >= L2_OMEGA and tau_p <= L2_TAU:
            return {"level": "Level 2", "limiting": "bandwidth",
                    "missing": missing}
        bw_failed = omega_BW < L2_OMEGA
        tau_failed = tau_p > L2_TAU
        if bw_failed and tau_failed:
            limiting = "both"
        elif tau_failed:
            limiting = "phase delay"
        else:
            limiting = "bandwidth"
        return {"level": "Level 3", "limiting": limiting,
                "missing": missing}
    if omega_BW is not None:
        if omega_BW >= L1_OMEGA:
            return {"level": "Level 1", "limiting": "bandwidth",
                    "missing": missing}
        if omega_BW >= L2_OMEGA:
            return {"level": "Level 2", "limiting": "bandwidth",
                    "missing": missing}
        return {"level": "Level 3", "limiting": "bandwidth",
                "missing": missing}
    if tau_p is not None:
        if tau_p <= L1_TAU:
            return {"level": "Level 1", "limiting": "phase delay",
                    "missing": missing}
        return {"level": "Level 3", "limiting": "phase delay",
                "missing": missing}
    return {"level": "Level 3", "limiting": "both", "missing": missing}


if __name__ == "__main__":
    import sys
    for wn, zeta, t2, wa in [(4.0, 0.7, 0.5, 25.0), (3.0, 0.6, 0.7, 20.0)]:
        res = bandwidth(wn, zeta, t2, wa)
        ver = level_verdict(res["omega_BW"], res["tau_p"])
        sys.stdout.write(
            "wn=%s: w135=%.4f w180=%.4f tau_p=%.4f w_gm6=%s omega_BW=%.4f %s %s\n"
            % (wn, res["w_135"], res["w_180"], res["tau_p"], res["w_gm6"],
               res["omega_BW"], ver["level"], ver["limiting"]))
