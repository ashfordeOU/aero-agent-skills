#!/usr/bin/env python3
"""Flutter speed prediction logic for the binary bending-torsion typical
section (classical wing flutter, V-g method).

Common-knowledge summary (public-domain textbook methodology, e.g.
Bisplinghoff/Ashley/Halfman, Aeroelasticity; Hodges and Pierce,
Introduction to Structural Dynamics and Aeroelasticity; Theodorsen 1935,
NACA Report 496): a two-degree-of-freedom wing section with plunge h
(positive down) and pitch theta (positive nose-up) about an elastic axis
at x = a*b from the mid-chord (positive aft, so a = -0.2 is the elastic
axis at 40 percent chord) is modeled with the unsteady Theodorsen
aerodynamics evaluated at harmonic motion. The complex lift-deficiency
function C(k) = H1^(2)(k) / (H1^(2)(k) + i H0^(2)(k)) is built from
Bessel J and Y series (Abramowitz and Stegun 9.1.10-9.1.11); the series
are accurate to double precision for reduced frequencies k up to about
10, and the sweep ranges in this leaf stay within k in [0.05, 4].

The V-g method adds an artificial structural damping g to the stiffness
(K(1 + i g)) and, for each reduced frequency k = omega*b/V, solves
det[K(1 + i g) - lambda E(k)] = 0 for real lambda = omega^2 and real g.
g < 0 means the aerodynamic damping stabilizes the mode (negative
artificial damping would be required to sustain harmonic motion), g = 0
is the neutral condition, and g > 0 means the mode is unstable. The
flutter speed is the lowest speed where a mode's g crosses zero from
negative to positive as V increases; the classic picture shows the two
modal frequencies coalescing just above the flutter speed, and the
section has a static divergence limit at higher speed where the torsion
frequency collapses to zero. Quasi-steady (C = 1) aerodynamics is known
to give erroneous pitch damping and is not used here.

The FAR 25.629 context enters only as a name-level reference: flutter
clearance of transport category airplanes is demonstrated against the
design dive speed, with margin practice at 1.15 x V_D; the regulation
text is referenced, never reproduced (standards-map.yaml far-25,
reference-only).
"""

import cmath
import math

ISA_SEA_LEVEL_DENSITY = 1.225  # kg/m^3, ISA standard atmosphere at sea level
FLUTTER_MARGIN_REQUIRED = 1.15  # clearance practice at 1.15 x V_D (FAR 25.629 context)
EULER_GAMMA = 0.57721566490153286060651209
PI = math.pi


def _require_positive(name, value):
    if not (isinstance(value, (int, float)) and value > 0.0):
        raise ValueError("%s must be positive, got %r" % (name, value))


def bessel_j0(x):
    """Bessel J0 via the alternating power series (A&S 9.1.10)."""
    s, term, n, xh = 0.0, 1.0, 0, x / 2.0
    while True:
        s += term
        n += 1
        term *= -(xh * xh) / (n * n)
        if abs(term) < 1e-17 * abs(s) or n > 300:
            break
    return s


def bessel_j1(x):
    """Bessel J1 via the alternating power series (A&S 9.1.10)."""
    xh = x / 2.0
    s, term, n = 0.0, xh, 0
    while True:
        s += term
        n += 1
        term *= -(xh * xh) / (n * (n + 1))
        if abs(term) < 1e-17 * abs(s) or n > 300:
            break
    return s


def bessel_y0(x):
    """Bessel Y0 via the log-power series (A&S 9.1.11)."""
    xh = x / 2.0
    s, term, h, n = 0.0, xh * xh, 0.0, 0
    while True:
        n += 1
        h += 1.0 / n
        s += term * h
        term *= -(xh * xh) / ((n + 1) * (n + 1))
        if abs(term * h) < 1e-17 * abs(s) or n > 300:
            break
    return (2.0 / PI) * ((math.log(xh) + EULER_GAMMA) * bessel_j0(x) + s)


def bessel_y1(x):
    """Bessel Y1 = -dY0/dx, from the Y0 series differentiated termwise."""
    xh = x / 2.0
    j0 = bessel_j0(x)
    j1 = bessel_j1(x)
    s = 0.0
    h = 0.0
    t = xh  # (x/2)^1 / (1!)^2 for n = 1
    n = 1
    while True:
        h += 1.0 / n
        s += ((-1) ** (n + 1)) * h * n * t
        n += 1
        t *= (xh * xh) / (n * n)
        if abs(((-1) ** (n + 1)) * h * n * t) < 1e-17 * abs(s) or n > 300:
            break
    return (2.0 / PI) * ((math.log(xh) + EULER_GAMMA) * j1 - j0 / x - s)


def theodorsen_c(k):
    """Complex lift-deficiency function C(k) = F + iG (k > 0).

    C = H1^(2) / (H1^(2) + i H0^(2)) with Hn^(2) = Jn - iYn, i.e.
    C = (J1 - iY1) / ((J1 + Y0) + i(J0 - Y1)). Limits: C -> 1 as
    k -> 0 (steady flow) and C -> 1/2 as k -> infinity (high reduced
    frequency lift deficiency), with |C| <= 1 for all k. The series
    implementation is accurate for k up to about 10.
    """
    _require_positive("reduced frequency k", k)
    j0, j1 = bessel_j0(k), bessel_j1(k)
    y0, y1 = bessel_y0(k), bessel_y1(k)
    den = (j1 + y0) * (j1 + y0) + (j0 - y1) * (j0 - y1)
    f = (j1 * (j1 + y0) + y1 * (y1 - j0)) / den
    g = (-j1 * j0 - y1 * y0) / den
    return complex(f, g)


def _effective_inertia(mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b, k, rho):
    """Effective complex inertia matrix E(k) and stiffness diagonal K.

    The Theodorsen loads, evaluated at harmonic motion and expressed as
    coefficients of lambda = omega^2 with V = omega*b/k, give
    det[K(1 + i g) - lambda E(k)] = 0 with K diagonal and E complex:
    the real parts are the structural and added inertias plus the
    circulatory stiffness, the imaginary parts are the aerodynamic
    damping. The apparent-mass damping terms (i/k in the lift, the
    -i(1/2 - a)/k in the moment) are included.
    """
    m = PI * rho * b * b * mu                  # mass per unit span
    s_theta = m * x_theta * b                  # static moment about the EA
    i_theta = m * r_theta_sq * b * b           # inertia about the EA
    k_h = m * omega_h * omega_h                # bending stiffness
    k_theta = i_theta * omega_theta * omega_theta  # torsion stiffness
    c = theodorsen_c(k)
    e11 = m + PI * rho * b * b - 2.0j * PI * rho * b * b * c / k
    e12 = s_theta - PI * rho * b * b * b * (a + 2.0 * c / k ** 2
                                            + 1.0j * (1.0 + 2.0 * c * (0.5 - a)) / k)
    e21 = s_theta + PI * rho * b * b * b * (-a + 2.0j * c * (a + 0.5) / k)
    e22 = (i_theta + PI * rho * b ** 4
           * ((0.125 + a * a) + 2.0 * c * (a + 0.5) / k ** 2
              + 1.0j * (0.5 - a) * (2.0 * c * (a + 0.5) - 1.0) / k))
    return e11, e12, e21, e22, k_h, k_theta


def _roots_at_g(e11, e12, e21, e22, k11, k22, g):
    """Complex roots of det[K(1+ig) - lambda E] = 0 at artificial damping g."""
    one = 1.0 + 1.0j * g
    c2 = e11 * e22 - e12 * e21
    c1 = -one * (k11 * e22 + k22 * e11)
    c0 = one * one * k11 * k22
    disc = cmath.sqrt(c1 * c1 - 4.0 * c2 * c0)
    return ((-c1 + disc) / (2.0 * c2), (-c1 - disc) / (2.0 * c2))


def _branch_lambda(g, e11, e12, e21, e22, k11, k22, l0_ref):
    """Continuous branch root: the quadratic root nearest the g=0 root."""
    la, lb = _roots_at_g(e11, e12, e21, e22, k11, k22, g)
    if abs(la - l0_ref) <= abs(lb - l0_ref):
        return la
    return lb


def vg_modes(mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b, k,
             rho=ISA_SEA_LEVEL_DENSITY, g_hi=5.0):
    """V-g solution at one reduced frequency k.

    Returns a list of mode dicts {"omega", "g", "v"} with the real modal
    frequency omega (rad/s), the artificial structural damping g, and the
    airspeed v = omega*b/k (m/s), one per aeroelastic branch with a
    real-frequency neutral solution in the g search window. Branches with
    no solution in [-g_hi, g_hi] are skipped.

    Invalid inputs raise ValueError.
    """
    _require_positive("mass ratio mu", mu)
    _require_positive("radius of gyration squared r_theta_sq", r_theta_sq)
    _require_positive("bending frequency omega_h", omega_h)
    _require_positive("torsion frequency omega_theta", omega_theta)
    _require_positive("semi-chord b", b)
    _require_positive("air density rho", rho)
    _require_positive("reduced frequency k", k)
    if not (isinstance(x_theta, (int, float)) and x_theta >= 0.0):
        raise ValueError(
            "static unbalance x_theta must be >= 0 (CG aft of the EA), got %r"
            % (x_theta,)
        )
    if not isinstance(a, (int, float)):
        raise ValueError("elastic axis location a must be a number, got %r" % (a,))
    e11, e12, e21, e22, k_h, k_theta = _effective_inertia(
        mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b, k, rho)
    l0a, l0b = _roots_at_g(e11, e12, e21, e22, k_h, k_theta, 0.0)
    out = []
    for l0 in (l0a, l0b):
        if l0.real <= 0.0:
            continue
        denom = 2.0 * (e11 * e22 - e12 * e21) * l0 - (k_h * e22 + k_theta * e11)
        if abs(denom) < 1e-30:
            continue
        l1 = (1.0j * (k_h * e22 + k_theta * e11) * l0 - 2.0j * k_h * k_theta) / denom
        g_est = 0.0 if abs(l1.imag) < 1e-30 else -l0.imag / l1.imag

        def branch_im(g):
            return _branch_lambda(g, e11, e12, e21, e22, k_h, k_theta, l0).imag

        g_lo, g_hi2 = -g_hi, g_hi
        g0 = max(min(g_est, g_hi2 - 1e-6), g_lo + 1e-6)
        f0 = branch_im(g0)
        if f0 == 0.0:
            g_final = g0
        else:
            lo, hi = g_lo, g_hi2
            flo, fhi = branch_im(lo), branch_im(hi)
            if flo * f0 < 0.0:
                lo, hi, flo, fhi = lo, g0, flo, f0
            elif f0 * fhi < 0.0:
                lo, hi, flo, fhi = g0, hi, f0, fhi
            else:
                continue  # no real-frequency neutral solution in the window
            for _ in range(300):
                mid = 0.5 * (lo + hi)
                fm = branch_im(mid)
                if flo * fm <= 0.0:
                    hi, fhi = mid, fm
                else:
                    lo, flo = mid, fm
                if abs(fm) < 1e-12 or abs(hi - lo) < 1e-14:
                    break
            g_final = 0.5 * (lo + hi)
        lam = _branch_lambda(g_final, e11, e12, e21, e22, k_h, k_theta, l0)
        if lam.real <= 0.0:
            continue
        omega = math.sqrt(lam.real)
        out.append({"omega": omega, "g": g_final, "v": omega * b / k})
    return out


def vg_damping_crossing(mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b,
                        k_values, rho=ISA_SEA_LEVEL_DENSITY):
    """V-g sweep: for each reduced frequency k in k_values, the modes.

    Returns a list of (k, modes) pairs, modes as in vg_modes. The
    damping crossing (flutter onset) is the lowest speed at which a
    mode's g rises through zero as k decreases (V = omega*b/k grows).
    """
    return [(k, vg_modes(mu, x_theta, r_theta_sq, omega_h, omega_theta,
                         a, b, k, rho))
            for k in k_values]


def _match_modes(prev_modes, cur_modes):
    """Pair modes across consecutive k steps by frequency proximity."""
    pairs = []
    used = set()
    for pm in prev_modes:
        best = None
        for i, cm in enumerate(cur_modes):
            if i in used:
                continue
            d = abs(cm["omega"] - pm["omega"])
            if best is None or d < best[0]:
                best = (d, i)
        if best is not None:
            used.add(best[1])
            pairs.append((pm, cur_modes[best[1]]))
    return pairs


def flutter_speed_binary(mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b,
                         k_lo, k_hi, n_scan=200, rho=ISA_SEA_LEVEL_DENSITY):
    """Flutter speed by bisection on the V-g damping crossing.

    Scans reduced frequencies from k_hi (low speed) down to k_lo (high
    speed), tracks each aeroelastic branch by frequency proximity, and
    locates the lowest speed where a branch's g crosses zero from
    negative to positive (flutter onset). Bisects on k to machine
    precision.

    Returns a dict with flutter_speed (m/s), flutter_frequency (rad/s),
    reduced_frequency, other_frequency (rad/s of the second mode at the
    flutter point), critical_mode ("torsion" when the flutter branch
    carries the higher frequency), and flutter_g (near zero), or None
    when no crossing occurs within the scanned k range.
    """
    if not (isinstance(n_scan, int) and n_scan >= 10):
        raise ValueError("n_scan must be an integer >= 10, got %r" % (n_scan,))
    _require_positive("reduced frequency lower bound k_lo", k_lo)
    _require_positive("reduced frequency upper bound k_hi", k_hi)
    if k_hi <= k_lo:
        raise ValueError("k_hi must exceed k_lo, got %r, %r" % (k_lo, k_hi))
    ks = sorted([k_lo + (k_hi - k_lo) * i / n_scan for i in range(n_scan + 1)],
                reverse=True)
    prev_modes = vg_modes(mu, x_theta, r_theta_sq, omega_h, omega_theta,
                          a, b, ks[0], rho)
    for idx in range(1, len(ks)):
        k = ks[idx]
        cur_modes = vg_modes(mu, x_theta, r_theta_sq, omega_h, omega_theta,
                             a, b, k, rho)
        for pm, cm in _match_modes(prev_modes, cur_modes):
            if pm["g"] < 0.0 < cm["g"]:
                # g rises through zero on this branch between ks[idx-1], ks[idx]
                k_a, k_b = ks[idx - 1], k
                g_a, g_b = pm["g"], cm["g"]
                omega_ref = 0.5 * (pm["omega"] + cm["omega"])
                for _ in range(300):
                    k_m = 0.5 * (k_a + k_b)
                    modes_m = vg_modes(mu, x_theta, r_theta_sq, omega_h,
                                       omega_theta, a, b, k_m, rho)
                    best = None
                    for mm in modes_m:
                        d = abs(mm["omega"] - omega_ref)
                        if best is None or d < best[0]:
                            best = (d, mm)
                    if best is None:
                        break
                    matched = best[1]
                    g_m = matched["g"]
                    omega_ref = matched["omega"]
                    if (g_a < 0.0) == (g_m < 0.0):
                        k_a, g_a = k_m, g_m
                    else:
                        k_b, g_b = k_m, g_m
                    if abs(g_m) < 1e-10 or abs(k_b - k_a) < 1e-13:
                        break
                k_f = 0.5 * (k_a + k_b)
                modes_f = vg_modes(mu, x_theta, r_theta_sq, omega_h,
                                   omega_theta, a, b, k_f, rho)
                crit = None
                other = None
                for mm in modes_f:
                    if abs(mm["omega"] - omega_ref) < 1e-3:
                        crit = mm
                    else:
                        other = mm
                if crit is None and modes_f:
                    crit = modes_f[0]
                    other = modes_f[1] if len(modes_f) > 1 else None
                if crit is None:
                    return None
                return {
                    "flutter_speed": crit["v"],
                    "flutter_frequency": crit["omega"],
                    "reduced_frequency": k_f,
                    "flutter_g": crit["g"],
                    "other_frequency": other["omega"] if other else None,
                    "critical_mode": ("torsion" if other is None
                                      or crit["omega"] > other["omega"]
                                      else "bending"),
                }
        prev_modes = cur_modes
    return None


def _modal_frequencies(mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b,
                       k, rho=ISA_SEA_LEVEL_DENSITY):
    """Real modal frequencies (rad/s) of the two aeroelastic modes at k.

    The frequencies follow from the g=0 (no artificial damping)
    eigenvalues: omega = sqrt(Re(lambda)) for each root, sorted.
    """
    e11, e12, e21, e22, k_h, k_theta = _effective_inertia(
        mu, x_theta, r_theta_sq, omega_h, omega_theta, a, b, k, rho)
    la, lb = _roots_at_g(e11, e12, e21, e22, k_h, k_theta, 0.0)
    omegas = []
    for lam in (la, lb):
        if lam.real > 0.0:
            omegas.append(math.sqrt(lam.real))
    return sorted(omegas)


def frequency_coalescence_check(mu, x_theta, r_theta_sq, omega_h, omega_theta,
                                a, b, k_lo, k_hi, n_scan=400,
                                rho=ISA_SEA_LEVEL_DENSITY):
    """Frequency coalescence check across the V-g sweep.

    Scans the reduced frequency range and measures the gap between the
    two aeroelastic modal frequencies at each k. In the classical
    flutter mechanism the modal frequencies converge strongly as the
    airspeed approaches the flutter boundary; the check reports the
    minimum gap, the speed at which it occurs, and the gap at the high
    end of the range (low speed) for comparison.

    Returns a dict with min_gap (rad/s), coalescence_speed (m/s, the
    mean of the two modal speeds at the minimum-gap station),
    coalescence_frequency (rad/s, the mean modal frequency there),
    low_speed_gap (rad/s), and coalescing (bool, True when the minimum
    gap is at most 40 percent of the low-speed gap), or None when fewer
    than two modes are found across the range.
    """
    if not (isinstance(n_scan, int) and n_scan >= 50):
        raise ValueError("n_scan must be an integer >= 50, got %r" % (n_scan,))
    _require_positive("reduced frequency lower bound k_lo", k_lo)
    _require_positive("reduced frequency upper bound k_hi", k_hi)
    if k_hi <= k_lo:
        raise ValueError("k_hi must exceed k_lo, got %r, %r" % (k_lo, k_hi))
    best = None
    low_speed_gap = None
    for i in range(n_scan + 1):
        k = k_lo + (k_hi - k_lo) * i / n_scan
        omegas = _modal_frequencies(mu, x_theta, r_theta_sq, omega_h,
                                    omega_theta, a, b, k, rho)
        if len(omegas) < 2:
            continue
        gap = omegas[1] - omegas[0]
        if i == n_scan:  # highest k = lowest speed end of the sweep
            low_speed_gap = gap
        if best is None or gap < best[0]:
            v1 = omegas[0] * b / k
            v2 = omegas[1] * b / k
            best = (gap, k, omegas, 0.5 * (v1 + v2))
    if best is None:
        return None
    gap, k_best, omegas, v_coal = best
    omega_coal = 0.5 * (omegas[0] + omegas[1])
    low_gap = low_speed_gap if low_speed_gap is not None else gap
    return {
        "min_gap": gap,
        "coalescence_speed": v_coal,
        "coalescence_frequency": omega_coal,
        "reduced_frequency": k_best,
        "low_speed_gap": low_gap,
        "coalescing": low_gap > 0.0 and gap <= 0.4 * low_gap,
    }


def flutter_margin(v_f, v_design, required=FLUTTER_MARGIN_REQUIRED):
    """Flutter margin against the design dive speed (FAR 25.629 context).

    margin = V_F / V_D. A margin at or above the required value (the
    clearance practice default 1.15, a rule of thumb referenced to the
    airworthiness standard, not a reproduction of it) is acceptable.
    Returns (margin, acceptable).
    """
    _require_positive("flutter speed V_F", v_f)
    _require_positive("design dive speed V_D", v_design)
    if not (required >= 1.0):
        raise ValueError("required margin must be at least 1.0, got %r" % (required,))
    margin = v_f / v_design
    return (margin, margin >= required)
