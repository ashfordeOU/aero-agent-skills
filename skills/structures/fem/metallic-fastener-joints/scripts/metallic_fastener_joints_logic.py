"""Metallic multi-fastener joint analysis (structures/fem/metallic-fastener-joints).

Closed-form stress analysis of a metallic multi-fastener joint (bolt or
rivet pattern) under an applied load: the per-fastener load share of a
symmetric pattern P/n, fastener shear in single or double shear over the
fastener shear area, sheet bearing P/(D*t), net-section tension across
the fastener row P/((w - holes*D)*t) and sheet shear-out P/(2*e*t) at the
edge distance, each with a margin of safety against an MMPDS-style
allowable under the standard 1.5 ultimate factor (FAR 25.303 style),
plus the polar-moment resolution of an eccentric bolt group whose
applied load line misses the pattern centroid. Pure stdlib math only,
deterministic, SI units (loads in N, geometry in mm, stresses in MPa).

The module constants are representative MMPDS-style design values stated
as module parameters, never a reproduced design-value table: BOLT_F_SU
is the fastener shear ultimate of a steel MS-class bolt, and the
SHEET_* constants are 2024-T3 sheet allowables valid at the edge
distance ratio e/D >= 2 used in the worked example.
"""

import math

# Module constants (MMPDS-style design parameters, representative defaults)
BOLT_F_SU = 655.0  # fastener shear ultimate F_su, MPa, steel MS-class bolt
SHEET_F_TU = 427.0  # 2024-T3 sheet tension ultimate F_tu, MPa
SHEET_F_SU = 255.0  # 2024-T3 sheet shear ultimate F_su, MPa
SHEET_F_BRU = 620.0  # 2024-T3 sheet bearing ultimate F_bru, MPa (e/D >= 2)
ULTIMATE_FACTOR = 1.5  # design ultimate factor on limit stresses, FAR 25.303 style

MAX_TIE_TOL = 1e-9  # magnitude tolerance for tying max-loaded fasteners


def fastener_area(D):
    """Fastener shear area pi*D^2/4 (mm^2) for diameter D in mm."""
    if D <= 0:
        raise ValueError("fastener diameter D must be positive")
    return math.pi * D * D / 4.0


def fastener_shear_stress(P_f, D, planes=1):
    """Shear stress on one fastener over `planes` shear planes: P_f/(planes*A).

    planes = 1 is single shear, planes = 2 is double shear.
    """
    if P_f < 0:
        raise ValueError("fastener load P_f must be non-negative")
    if D <= 0:
        raise ValueError("fastener diameter D must be positive")
    if planes not in (1, 2):
        raise ValueError("planes must be 1 (single shear) or 2 (double shear)")
    area = fastener_area(D)
    return P_f / (planes * area)


def bearing_stress(P_f, D, t):
    """Sheet bearing stress under one fastener P_f/(D*t), MPa."""
    if P_f < 0:
        raise ValueError("fastener load P_f must be non-negative")
    if D <= 0:
        raise ValueError("fastener diameter D must be positive")
    if t <= 0:
        raise ValueError("sheet thickness t must be positive")
    return P_f / (D * t)


def net_section_stress(P, w, holes, D, t):
    """Net-section tension at a row of `holes` fasteners: P/((w - holes*D)*t).

    The full row load P acts over the net width w - holes*D, which must
    stay positive (a destroyed net section is rejected).
    """
    if P < 0:
        raise ValueError("row load P must be non-negative")
    if w <= 0:
        raise ValueError("joint width w must be positive")
    if not isinstance(holes, int) or isinstance(holes, bool) or holes < 1:
        raise ValueError("holes must be a positive integer")
    if D <= 0:
        raise ValueError("fastener diameter D must be positive")
    if t <= 0:
        raise ValueError("sheet thickness t must be positive")
    net_width = w - holes * D
    if net_width <= 0:
        raise ValueError("net section destroyed: net width w - holes*D must be positive")
    return P / (net_width * t)


def shear_out_stress(P_f, e, t):
    """Sheet shear-out (tear-out) stress at the edge: P_f/(2*e*t), MPa.

    Two shear planes, each of length e (the edge distance from the hole
    center to the free edge along the load direction) and thickness t.
    """
    if P_f < 0:
        raise ValueError("fastener load P_f must be non-negative")
    if e <= 0:
        raise ValueError("edge distance e must be positive")
    if t <= 0:
        raise ValueError("sheet thickness t must be positive")
    return P_f / (2.0 * e * t)


def margin_of_safety(allowable, applied_limit, factor=ULTIMATE_FACTOR):
    """Margin of safety: allowable/(factor*applied_limit) - 1.

    The design ultimate stress is factor*applied_limit (default ultimate
    factor 1.5 on limit stresses, FAR 25.303 style); a factor of 1.0
    recovers the plain allowable/applied - 1 form, and a margin of zero
    means the factored applied stress equals the allowable.
    """
    if allowable <= 0:
        raise ValueError("allowable must be positive")
    if applied_limit <= 0:
        raise ValueError("applied limit stress must be positive")
    if factor <= 0:
        raise ValueError("factor must be positive")
    return allowable / (factor * applied_limit) - 1.0


def splice_joint_analysis(P, n, D, t, w, e, f_su_fastener, f_bru, f_tu,
                          f_su_sheet, planes=1, factor=ULTIMATE_FACTOR):
    """One-shot symmetric n-fastener single-row shear splice report.

    Splits the row load P into the per-fastener share P/n, checks each
    fastener in shear over `planes` planes, the sheet in bearing, in
    net-section tension across the row and in shear-out at the sheet
    edge, and returns the limit stresses with the per-mode margins of
    safety, the governing (lowest-margin) mode and the pass verdict.

    Returns dict with per_fastener_load_N, fastener_shear_MPa,
    bearing_MPa, net_section_MPa, shear_out_MPa, margins (dict keyed
    fastener_shear, bearing, net_section, shear_out), governing,
    min_margin and passes (min_margin >= 0).
    """
    if P < 0:
        raise ValueError("row load P must be non-negative")
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive integer")
    if f_su_fastener <= 0 or f_bru <= 0 or f_tu <= 0 or f_su_sheet <= 0:
        raise ValueError("all allowables must be positive")
    if planes not in (1, 2):
        raise ValueError("planes must be 1 (single shear) or 2 (double shear)")
    p_f = P / float(n)
    tau_fast = fastener_shear_stress(p_f, D, planes)
    sig_b = bearing_stress(p_f, D, t)
    sig_nt = net_section_stress(P, w, n, D, t)
    tau_so = shear_out_stress(p_f, e, t)
    margins = {
        "fastener_shear": margin_of_safety(f_su_fastener, tau_fast, factor),
        "bearing": margin_of_safety(f_bru, sig_b, factor),
        "net_section": margin_of_safety(f_tu, sig_nt, factor),
        "shear_out": margin_of_safety(f_su_sheet, tau_so, factor),
    }
    governing = min(margins, key=lambda k: margins[k])
    min_margin = margins[governing]
    return {
        "per_fastener_load_N": p_f,
        "fastener_shear_MPa": tau_fast,
        "bearing_MPa": sig_b,
        "net_section_MPa": sig_nt,
        "shear_out_MPa": tau_so,
        "margins": margins,
        "governing": governing,
        "min_margin": min_margin,
        "passes": min_margin >= 0.0,
    }


def bolt_group_properties(bolts):
    """Centroid (x_c, y_c) and polar moment J of a bolt group.

    bolts is a list of (x, y) tuples in mm; J = sum_i((x_i - x_c)^2 +
    (y_i - y_c)^2) in mm^2, the polar moment used by the eccentric
    group resolution.
    """
    if not bolts:
        raise ValueError("bolt group must not be empty")
    n = float(len(bolts))
    x_c = sum(x for x, _ in bolts) / n
    y_c = sum(y for _, y in bolts) / n
    j_polar = sum((x - x_c) ** 2 + (y - y_c) ** 2 for x, y in bolts)
    return x_c, y_c, j_polar


def eccentric_bolt_group_loads(fx, fy, ax, ay, bolts):
    """Polar-moment resolution of an eccentric bolt group.

    Applied force (fx, fy) in N acting at (ax, ay) in mm on the bolt
    group `bolts` (list of (x, y) tuples in mm). The torque about the
    group centroid is M = (ax - x_c)*fy - (ay - y_c)*fx; every bolt
    carries the equal direct share (fx, fy)/n plus the secondary share
    F_sec,i = (M/J)*(-dy_i, dx_i) perpendicular to its radius, so the
    secondary forces sum to zero and their moments sum to M.

    Returns dict with centroid, polar_moment_mm2, torque_Nmm,
    direct_per_fastener_N, fasteners (per-bolt dicts in input order with
    x, y, r_mm, direct_N, secondary_N, total_N and magnitude_N),
    max_magnitude_N, max_indices (all bolts within 1e-9 of the maximum)
    and max_fastener (the first max-loaded bolt dict).
    """
    if not bolts:
        raise ValueError("bolt group must not be empty")
    if fx == 0.0 and fy == 0.0:
        raise ValueError("applied force must not be zero")
    x_c, y_c, j_polar = bolt_group_properties(bolts)
    if j_polar <= 0:
        raise ValueError("all bolts coincident: polar moment J must be positive")
    n = float(len(bolts))
    torque = (ax - x_c) * fy - (ay - y_c) * fx
    direct_x = fx / n
    direct_y = fy / n
    fasteners = []
    for x, y in bolts:
        dx = x - x_c
        dy = y - y_c
        radius = math.hypot(dx, dy)
        sec_x = (torque / j_polar) * (-dy)
        sec_y = (torque / j_polar) * dx
        tot_x = direct_x + sec_x
        tot_y = direct_y + sec_y
        fasteners.append({
            "x": x,
            "y": y,
            "r_mm": radius,
            "direct_N": (direct_x, direct_y),
            "secondary_N": (sec_x, sec_y),
            "total_N": (tot_x, tot_y),
            "magnitude_N": math.hypot(tot_x, tot_y),
        })
    max_magnitude = max(f["magnitude_N"] for f in fasteners)
    max_indices = [i for i, f in enumerate(fasteners)
                   if abs(f["magnitude_N"] - max_magnitude) <= MAX_TIE_TOL]
    return {
        "centroid": (x_c, y_c),
        "polar_moment_mm2": j_polar,
        "torque_Nmm": torque,
        "direct_per_fastener_N": (direct_x, direct_y),
        "fasteners": fasteners,
        "max_magnitude_N": max_magnitude,
        "max_indices": max_indices,
        "max_fastener": fasteners[max_indices[0]],
    }
