"""Polhamus leading-edge suction analogy for sharp-edged slender delta wings.

Pure stdlib implementation of the vortex-lift estimate of NASA TN D-3767
(Polhamus 1966, public domain): total lift is the sum of an attached
potential term and a leading-edge-separation vortex term,

    CL = Kp sin(a) cos^2(a) + Kv cos(a) sin^2(a)

with Kp the small-angle lift slope (slender-wing value pi * AR / 2) and Kv
the vortex lift factor growing linearly from 3.14 at AR 0 to about 3.45 at
AR 4. Valid for sharp leading edges, subsonic flow, AR about 0.5 to 2.0,
and alpha up to about 25 degrees. Offline deterministic, no external
dependencies.
"""

import math

PI = math.pi
KV_0 = 3.14  # vortex lift factor at AR = 0 (NASA TN D-3767 text anchor)
KV_4 = 3.45  # vortex lift factor at AR = 4 (NASA TN D-3767 Fig. 9 discussion)
AR_CLAMP = 4.0  # aspect ratio above which Kv stops growing


def delta_aspect_ratio(le_sweep_deg):
    """Aspect ratio of a full delta wing from its leading-edge sweep.

    AR = 4 / tan(Lambda_LE). A 76 deg sweep gives about 1.0 and a 45 deg
    sweep gives 4.0. Raises ValueError for sweeps <= 0 or >= 90 deg.
    """
    if le_sweep_deg <= 0 or le_sweep_deg >= 90:
        raise ValueError(
            "leading-edge sweep must be in (0, 90) degrees, got %r"
            % (le_sweep_deg,)
        )
    return 4.0 / math.tan(math.radians(le_sweep_deg))


def slender_delta_kp(ar):
    """Small-angle potential lift slope Kp of a slender delta, pi * AR / 2.

    Raises ValueError for aspect ratios <= 0.
    """
    if ar <= 0:
        raise ValueError("aspect ratio must be > 0, got %r" % (ar,))
    return PI * ar / 2.0


def delta_kv(ar):
    """Vortex lift factor Kv, linear from KV_0 at AR 0 to KV_4 at AR 4.

    Kv = KV_0 + (KV_4 - KV_0) * min(ar, AR_CLAMP) / AR_CLAMP; ar is
    clamped to [0, 4] and negative values raise ValueError.
    """
    if ar < 0:
        raise ValueError("aspect ratio must be >= 0, got %r" % (ar,))
    return KV_0 + (KV_4 - KV_0) * min(ar, AR_CLAMP) / AR_CLAMP


def polhamus_cl(kp, kv, alpha_deg):
    """Total lift coefficient, Kp sin(a) cos^2(a) + Kv cos(a) sin^2(a)."""
    a = math.radians(alpha_deg)
    return kp * math.sin(a) * math.cos(a) ** 2 + kv * math.cos(a) * math.sin(a) ** 2


def polhamus_cl_potential(kp, alpha_deg):
    """Attached potential-flow term of the suction analogy, Kp sin(a) cos^2(a)."""
    a = math.radians(alpha_deg)
    return kp * math.sin(a) * math.cos(a) ** 2


def polhamus_cl_vortex(kv, alpha_deg):
    """Leading-edge-separation vortex term, Kv cos(a) sin^2(a)."""
    a = math.radians(alpha_deg)
    return kv * math.cos(a) * math.sin(a) ** 2


def cd_due_to_lift(cl, alpha_deg):
    """Drag due to lift, CL * tan(a) (NASA TN D-3767 definition)."""
    if abs(alpha_deg) >= 90:
        raise ValueError(
            "angle of attack must be within (-90, 90) degrees, got %r"
            % (alpha_deg,)
        )
    return cl * math.tan(math.radians(alpha_deg))


def vortex_potential_crossing_deg(kp, kv):
    """Angle where the vortex term equals the potential term, atan(kp / kv).

    tan(alpha) = kp / kv gives the crossing in degrees. Raises ValueError
    when kv <= 0.
    """
    if kv <= 0:
        raise ValueError("vortex factor kv must be > 0, got %r" % (kv,))
    return math.degrees(math.atan(kp / kv))


def delta_lift_summary(ar_or_sweep, alpha_deg, sweep=False):
    """One-call lift breakdown for a delta wing.

    Input convention: by default ar_or_sweep is the aspect ratio used
    directly; pass sweep=True to supply the leading-edge sweep angle in
    degrees instead (converted with delta_aspect_ratio). Returns a dict
    with exactly the keys: aspect_ratio, kp, kv, alpha_deg, cl_potential,
    cl_vortex, cl_total, cd_due_to_lift, vortex_fraction, crossing_deg.
    """
    ar = (
        delta_aspect_ratio(ar_or_sweep)
        if sweep
        else float(ar_or_sweep)
    )
    kp = slender_delta_kp(ar)
    kv = delta_kv(ar)
    cl_potential = polhamus_cl_potential(kp, alpha_deg)
    cl_vortex = polhamus_cl_vortex(kv, alpha_deg)
    cl_total = polhamus_cl(kp, kv, alpha_deg)
    cd_lift = cd_due_to_lift(cl_total, alpha_deg)
    crossing = vortex_potential_crossing_deg(kp, kv)
    vortex_fraction = cl_vortex / cl_total if cl_total != 0 else 0.0
    return {
        "aspect_ratio": ar,
        "kp": kp,
        "kv": kv,
        "alpha_deg": float(alpha_deg),
        "cl_potential": cl_potential,
        "cl_vortex": cl_vortex,
        "cl_total": cl_total,
        "cd_due_to_lift": cd_lift,
        "vortex_fraction": vortex_fraction,
        "crossing_deg": crossing,
    }
