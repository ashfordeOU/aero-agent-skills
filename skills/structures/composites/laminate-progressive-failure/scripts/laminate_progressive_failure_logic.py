"""Progressive failure of a symmetric balanced composite laminate.

Pure stdlib ply-discount / last-ply-failure march past first-ply
failure. Reuses the sibling laminate-first-ply-failure closed forms
(plane-stress ply stiffness, rotation to laminate axes, A-inverse
strain recovery, per-ply Tsai-Wu index) and extends them with the
stiffness-evolution march: at each ply event the failed ply's
stiffness is discounted, the laminate A block is reassembled from the
degraded plies, and the load resultant is reapplied until no
load-bearing stiffness remains (last-ply-failure).

Event convention (the fence against the sibling leaf's linearized
first-ply-failure scale k* = 1 / max(FI)): within a load segment every
active ply's Tsai-Wu index is quadratic in the load scale lambda,
FI_k(lambda) = a_k lambda^2 + b_k lambda. A ply event is the smallest
positive root of FI_k(lambda) = 1, the closed-form quadratic root, not
a linearized reserve factor.

Ply-discount convention: a matrix-mode failure zeroes E2, G12 and
nu12 of the failed ply (E1 retained, so the ply keeps carrying
fiber-direction load as a unidirectional tape and can later fail
again in fiber mode); a fiber-mode failure zeroes E1 as well. Mode
discrimination: fiber mode iff the fiber-direction stress s1 >= Xt or
s1 <= -Xc at the event stress state, else matrix mode.

Units follow the sibling first-ply-failure convention: stresses,
moduli and allowables in MPa, load resultants in N/mm, ply thickness
in mm, strains dimensionless, A-block entries in N/mm. Non-physical
inputs raise ValueError. No RNG, no tables, no imports beyond math.
"""

import math

# Worked-example QI stack [0/90/45/-45]s, 8 plies at 0.125 mm, h = 1 mm.
QI_ANGLES = [0.0, 90.0, 45.0, -45.0, -45.0, 45.0, 90.0, 0.0]
PLY_T_MM = 0.125

# High-strength carbon/epoxy: T300/5208-class engineering constants
# with a T800H-class fiber tension allowable (the worked-example
# material of this leaf).
HC_E1 = 181000.0
HC_E2 = 10300.0
HC_G12 = 7170.0
HC_NU12 = 0.28
HC_XT = 2700.0
HC_XC = 2000.0
HC_YT = 40.0
HC_YC = 246.0
HC_S = 68.0

# [0]8 unidirectional stack for the fiber-direction reduction identity.
UD8_ANGLES = [0.0] * 8

# T300/5208 reprise constants (the sibling leaf's own module constants,
# used for the oracle cross-check in the worked example).
T300_E1 = 181000.0
T300_E2 = 10300.0
T300_G12 = 7170.0
T300_NU12 = 0.28
T300_XT = 1500.0
T300_XC = 1500.0
T300_YT = 40.0
T300_YC = 246.0
T300_S = 68.0

_ROOT_TOL = 1e-9
_FIBER_SLACK = 1e-9


def q_matrix_from_constants(e1, e2, nu12, g12):
    """Return (q11, q12, q22, q66), the plane-stress ply stiffness.

    q11 = E1 / (1 - nu12 nu21), q22 = E2 / (1 - nu12 nu21),
    q12 = nu12 E2 / (1 - nu12 nu21), q66 = G12, with
    nu21 = nu12 E2 / E1. Raises ValueError for a non-positive
    engineering constant or a singular Poisson product.
    """
    if e1 <= 0.0 or e2 <= 0.0 or g12 <= 0.0 or nu12 <= 0.0:
        raise ValueError("engineering constants E1, E2, G12, nu12 must be positive")
    nu21 = nu12 * e2 / e1
    denom = 1.0 - nu12 * nu21
    if denom <= 0.0:
        raise ValueError("nu12 nu21 >= 1 makes the plane-stress stiffness singular")
    q11 = e1 / denom
    q22 = e2 / denom
    q12 = nu12 * e2 / denom
    return (q11, q12, q22, g12)


def _plane_stress_stiffness(e1, e2, nu12, g12):
    """Plane-stress stiffness for a possibly-degraded ply state (a
    zeroed E1, E2, nu12 or G12 is legal here, unlike the validated
    q_matrix_from_constants): same closed form, denom clamped to 1.0
    when it would be non-positive (a zeroed-E1 tape has nu21 = 0).
    """
    nu21 = nu12 * e2 / e1 if e1 > 0.0 else 0.0
    denom = 1.0 - nu12 * nu21
    if denom <= 0.0:
        denom = 1.0
    q11 = e1 / denom
    q22 = e2 / denom
    q12 = nu12 * e2 / denom
    return (q11, q12, q22, g12)


def _rotated_ply_stiffness(q_components, theta_deg):
    """Return the full in-plane 6-tuple (Qb11, Qb12, Qb16, Qb22, Qb26,
    Qb66), the ply stiffness rotated to the laminate axes at theta_deg
    (standard fourth-power rotation of the 2D plane-stress stiffness).
    """
    q11, q12, q22, q66 = q_components
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2, s2 = c * c, s * s
    c4, s4 = c2 * c2, s2 * s2
    s2c2 = s2 * c2
    cs = c * s
    qb11 = q11 * c4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * s4
    qb22 = q11 * s4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * c4
    qb12 = (q11 + q22 - 4.0 * q66) * s2c2 + q12 * (c4 + s4)
    qb66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * s2c2 + q66 * (c4 + s4)
    qb16 = ((q11 - q12 - 2.0 * q66) * c2 - (q22 - q12 - 2.0 * q66) * s2) * cs
    qb26 = ((q11 - q12 - 2.0 * q66) * s2 - (q22 - q12 - 2.0 * q66) * c2) * cs
    return (qb11, qb12, qb16, qb22, qb26, qb66)


def _assemble_a_block(plies_deg, ply_thickness_mm, states):
    """Assemble (A11, A12, A16, A22, A26, A66) in N/mm from the current
    per-ply (e1, e2, nu12, g12) states (intact or degraded).
    """
    a11 = a12 = a16 = a22 = a26 = a66 = 0.0
    for theta_deg, (e1s, e2s, nu12s, g12s) in zip(plies_deg, states):
        q = _plane_stress_stiffness(e1s, e2s, nu12s, g12s)
        qb11, qb12, qb16, qb22, qb26, qb66 = _rotated_ply_stiffness(q, theta_deg)
        a11 += qb11 * ply_thickness_mm
        a12 += qb12 * ply_thickness_mm
        a16 += qb16 * ply_thickness_mm
        a22 += qb22 * ply_thickness_mm
        a26 += qb26 * ply_thickness_mm
        a66 += qb66 * ply_thickness_mm
    return (a11, a12, a16, a22, a26, a66)


def laminate_a_matrix(plies_deg, ply_thickness_mm, e1, e2, nu12, g12):
    """Return the intact-laminate in-plane block (A11, A12, A16, A22,
    A26, A66) in N/mm. Raises ValueError for an empty ply list, a
    non-positive ply thickness, or a non-physical engineering constant
    (see q_matrix_from_constants).
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if ply_thickness_mm <= 0.0:
        raise ValueError(
            "ply thickness must be a positive number, got %r" % (ply_thickness_mm,)
        )
    q_matrix_from_constants(e1, e2, nu12, g12)
    states = [(e1, e2, nu12, g12)] * len(plies_deg)
    return _assemble_a_block(plies_deg, ply_thickness_mm, states)


def _invert_a_block(a_components):
    """Return (i11, i12, i16, i22, i26, i66, det), the exact closed-form
    inverse of the symmetric 3x3 in-plane block, or None when the block
    is not positive definite (det <= 0).
    """
    a11, a12, a16, a22, a26, a66 = a_components
    d1 = a22 * a66 - a26 * a26
    d2 = a12 * a66 - a26 * a16
    d3 = a12 * a26 - a22 * a16
    det = a11 * d1 - a12 * d2 + a16 * d3
    if det <= 0.0:
        return None
    i11 = d1 / det
    i12 = -d2 / det
    i16 = d3 / det
    i22 = (a11 * a66 - a16 * a16) / det
    i26 = -(a11 * a26 - a12 * a16) / det
    i66 = (a11 * a22 - a12 * a12) / det
    return (i11, i12, i16, i22, i26, i66, det)


def midplane_strains(a_components, nx, ny, nxy):
    """Return (ex, ey, gxy), the laminate mid-plane strains from the
    full 3x3 in-plane block inverse: {eps} = [A]^-1 {N}. Raises
    ValueError when the block is not positive definite.
    """
    inv = _invert_a_block(a_components)
    if inv is None:
        raise ValueError("the laminate A block is not positive definite")
    i11, i12, i16, i22, i26, i66, _det = inv
    ex = i11 * nx + i12 * ny + i16 * nxy
    ey = i12 * nx + i22 * ny + i26 * nxy
    gxy = i16 * nx + i26 * ny + i66 * nxy
    return (ex, ey, gxy)


def _ply_material_strains(ex, ey, gxy, theta_deg):
    """Laminate strains transformed to the ply material axes:
    e1 = ex c^2 + ey s^2 + gxy c s, e2 = ex s^2 + ey c^2 - gxy c s,
    g12 = 2 (ey - ex) c s + gxy (c^2 - s^2).
    """
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2, s2 = c * c, s * s
    cs = c * s
    e1 = ex * c2 + ey * s2 + gxy * cs
    e2 = ex * s2 + ey * c2 - gxy * cs
    g12 = 2.0 * (ey - ex) * cs + gxy * (c2 - s2)
    return (e1, e2, g12)


def _ply_material_stresses(e1, e2, g12, q_components):
    """Material-axis stresses from material-axis strains:
    s1 = q11 e1 + q12 e2, s2 = q12 e1 + q22 e2, t12 = q66 g12.
    """
    q11, q12, q22, q66 = q_components
    s1 = q11 * e1 + q12 * e2
    s2 = q12 * e1 + q22 * e2
    t12 = q66 * g12
    return (s1, s2, t12)


def _tsai_wu_coeffs(allowables):
    """Return (f1, f2, f11, f22, f66, f12), the Tsai-Wu allowable terms
    from (xt, xc, yt, yc, s_uv). Raises ValueError for a non-positive
    allowable.
    """
    xt, xc, yt, yc, s_uv = allowables
    if xt <= 0.0 or xc <= 0.0 or yt <= 0.0 or yc <= 0.0 or s_uv <= 0.0:
        raise ValueError("allowables Xt, Xc, Yt, Yc, S must be positive")
    f1 = 1.0 / xt - 1.0 / xc
    f2 = 1.0 / yt - 1.0 / yc
    f11 = 1.0 / (xt * xc)
    f22 = 1.0 / (yt * yc)
    f66 = 1.0 / (s_uv * s_uv)
    f12 = -0.5 * math.sqrt(f11 * f22)
    return (f1, f2, f11, f22, f66, f12)


def _tsai_wu_index(s1, s2, t12, allowables):
    """Tsai-Wu failure index: FI = F1 s1 + F2 s2 + F11 s1^2 + F22 s2^2
    + F66 t12^2 + 2 F12 s1 s2. FI >= 1.0 marks failure.
    """
    f1, f2, f11, f22, f66, f12 = _tsai_wu_coeffs(allowables)
    return (
        f1 * s1
        + f2 * s2
        + f11 * s1 * s1
        + f22 * s2 * s2
        + f66 * t12 * t12
        + 2.0 * f12 * s1 * s2
    )


def per_ply_failure_indices(plies_deg, a_components, e1, e2, nu12, g12,
                             allowables, nx, ny, nxy):
    """Return the per-ply Tsai-Wu failure indices (list order matches
    plies_deg) of the INTACT laminate at the given resultants: recover
    the mid-plane strains, transform to each ply axis, recover the
    ply stresses and evaluate the Tsai-Wu index. Raises ValueError for
    an empty ply list or non-physical constants/allowables.
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    q_components = q_matrix_from_constants(e1, e2, nu12, g12)
    ex, ey, gxy = midplane_strains(a_components, nx, ny, nxy)
    indices = []
    for theta_deg in plies_deg:
        e1p, e2p, g12p = _ply_material_strains(ex, ey, gxy, theta_deg)
        s1, s2, t12 = _ply_material_stresses(e1p, e2p, g12p, q_components)
        indices.append(_tsai_wu_index(s1, s2, t12, allowables))
    return indices


def ply_discount_mode(s1, s2, t12, xt, xc):
    """Return "fiber" iff the fiber-direction stress s1 >= xt or
    s1 <= -xc at the event stress state (1e-9 relative slack so an
    event exactly on the fiber boundary classifies fiber in floating
    point), else "matrix". s2 and t12 are accepted for the caller's
    convenience but do not affect the mode.
    """
    del s2, t12
    if s1 >= xt * (1.0 - _FIBER_SLACK) or s1 <= -xc * (1.0 - _FIBER_SLACK):
        return "fiber"
    return "matrix"


def _discount_ply_state(state, mode):
    """Return the new (e1, e2, nu12, g12) state after a ply-discount
    event: matrix mode zeroes E2, G12 and nu12 (E1 retained, the ply
    becomes a unidirectional tape); fiber mode zeroes E1 as well.
    """
    e1, _e2, _nu12, _g12 = state
    return (0.0 if mode == "fiber" else e1, 0.0, 0.0, 0.0)


def _apply_discounts(states, k_list, modes):
    """Return a new states list with the discount applied at each
    index in k_list (immutable update, other plies unchanged).
    """
    new_states = list(states)
    for k, mode in zip(k_list, modes):
        new_states[k] = _discount_ply_state(states[k], mode)
    return new_states


def _positive_root(aq, bq):
    """Smallest positive root of aq lambda^2 + bq lambda - 1 = 0, or
    None when no positive root exists.
    """
    if aq == 0.0:
        return 1.0 / bq if bq > 0.0 else None
    disc = bq * bq + 4.0 * aq
    if disc < 0.0:
        return None
    sqrt_disc = math.sqrt(disc)
    candidates = [r for r in ((-bq - sqrt_disc) / (2.0 * aq),
                              (-bq + sqrt_disc) / (2.0 * aq)) if r > 0.0]
    return min(candidates) if candidates else None


def _unit_ply_response(plies_deg, states, a_now, nx, ny, nxy):
    """Return a list of (k, s1_u, s2_u, t12_u) for every active ply
    (nonzero E1, E2 or nu12): the material-axis stresses at unit load
    scale (the reference resultant), used to build each ply's
    quadratic Tsai-Wu-in-lambda coefficients.
    """
    ex_u, ey_u, gxy_u = midplane_strains(a_now, nx, ny, nxy)
    response = []
    for k, theta_deg in enumerate(plies_deg):
        e1s, e2s, nu12s, g12s = states[k]
        if e1s <= 0.0 and e2s <= 0.0 and nu12s <= 0.0:
            continue
        q = _plane_stress_stiffness(e1s, e2s, nu12s, g12s)
        e1p, e2p, g12p = _ply_material_strains(ex_u, ey_u, gxy_u, theta_deg)
        s1_u, s2_u, t12_u = _ply_material_stresses(e1p, e2p, g12p, q)
        response.append((k, s1_u, s2_u, t12_u))
    return response


def _event_root(s1_u, s2_u, t12_u, coeffs):
    """Quadratic root in lambda of FI_k(lambda) = 1 at unit-load
    stresses (s1_u, s2_u, t12_u), from the pre-computed Tsai-Wu
    coefficients (f1, f2, f11, f22, f66, f12).
    """
    f1, f2, f11, f22, f66, f12 = coeffs
    aq = f11 * s1_u * s1_u + f22 * s2_u * s2_u + f66 * t12_u * t12_u \
        + 2.0 * f12 * s1_u * s2_u
    bq = f1 * s1_u + f2 * s2_u
    return _positive_root(aq, bq)


def _fiber_strain_limit_load(plies_deg, states, a_now, nx, ny, nxy, strain_limit):
    """Return the load scale at which the largest active-ply fiber
    strain magnitude reaches strain_limit, or None when no active ply
    carries fiber strain (an all-failed laminate).
    """
    ex_u, ey_u, gxy_u = midplane_strains(a_now, nx, ny, nxy)
    max_abs_e1_u = 0.0
    for k, theta_deg in enumerate(plies_deg):
        if states[k][0] <= 0.0:
            continue
        e1p, _e2p, _g12p = _ply_material_strains(ex_u, ey_u, gxy_u, theta_deg)
        max_abs_e1_u = max(max_abs_e1_u, abs(e1p))
    return strain_limit / max_abs_e1_u if max_abs_e1_u > 0.0 else None


def _record_event(event_number, load, nx, k_list, plies_deg, modes, a_after):
    """Build one event dict."""
    return {
        "event": event_number,
        "load_multiplier": load,
        "load_nx": load * nx,
        "failed_plies": k_list,
        "failed_angles_deg": [plies_deg[k] for k in k_list],
        "modes": modes,
        "a_after": a_after,
    }


def _classify_event_modes(group, load, allowables):
    """Classify the mode of every (k, s1_u, s2_u, t12_u) tuple in group
    at the event load; a matrix-mode call on a ply already reduced to
    a tape (E2 = G12 = 0) is forced to fiber mode (the state guard: a
    tape's index factors exactly at the fiber boundary).
    """
    xt, xc = allowables[0], allowables[1]
    modes = []
    for _k, s1_u, s2_u, t12_u in group:
        mode = ply_discount_mode(s1_u * load, s2_u * load, t12_u * load, xt, xc)
        modes.append(mode)
    return modes


def progressive_failure_march(plies_deg, ply_thickness_mm, e1, e2, nu12,
                               g12, allowables, nx, ny, nxy,
                               strain_limit=None):
    """Run the ply-discount / last-ply-failure march at proportional
    load and return the report dict (see the module docstring for the
    algorithm). The march is load controlled: at each segment the
    smallest positive root of every active ply's quadratic
    Tsai-Wu-in-lambda equation gives the next event load; ties within
    1e-9 relative fail together (a grouped event). A discount that
    leaves another active ply already at or past unity at the current
    load fails that ply immediately in a same-load cascade event.

    Raises ValueError for an empty ply list, a non-positive ply
    thickness, a non-physical engineering constant, a non-positive
    allowable, an all-zero reference resultant, or a non-positive
    strain limit.
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if ply_thickness_mm <= 0.0:
        raise ValueError(
            "ply thickness must be a positive number, got %r" % (ply_thickness_mm,)
        )
    q_matrix_from_constants(e1, e2, nu12, g12)
    _tsai_wu_coeffs(allowables)
    if nx == 0.0 and ny == 0.0 and nxy == 0.0:
        raise ValueError("the reference resultant (Nx, Ny, Nxy) must be nonzero")
    if strain_limit is not None and strain_limit <= 0.0:
        raise ValueError(
            "strain limit must be a positive number, got %r" % (strain_limit,)
        )

    states = [(e1, e2, nu12, g12)] * len(plies_deg)
    a_initial = _assemble_a_block(plies_deg, ply_thickness_mm, states)
    if _invert_a_block(a_initial) is None:
        raise ValueError("the laminate A block is not positive definite")

    events = []
    load = 0.0
    reason = "no-further-ply-failure"

    while True:
        a_now = _assemble_a_block(plies_deg, ply_thickness_mm, states)
        if _invert_a_block(a_now) is None:
            reason = "last-ply-failure"
            break
        response = _unit_ply_response(plies_deg, states, a_now, nx, ny, nxy)
        if not response:
            reason = "last-ply-failure"
            break

        coeffs = _tsai_wu_coeffs(allowables)
        lam_eps = None
        if strain_limit is not None:
            lam_eps = _fiber_strain_limit_load(
                plies_deg, states, a_now, nx, ny, nxy, strain_limit
            )
            if lam_eps is not None and lam_eps <= load * (1.0 + _ROOT_TOL):
                reason = "strain-limit"
                break

        cascade = [
            item for item in response
            if _tsai_wu_index(item[1] * load, item[2] * load, item[3] * load,
                              allowables) >= 1.0 - _ROOT_TOL
        ]
        if cascade and load > 0.0:
            k_list = [item[0] for item in cascade]
            modes = _classify_event_modes(cascade, load, allowables)
            states = _apply_discounts(states, k_list, modes)
            a_after = _assemble_a_block(plies_deg, ply_thickness_mm, states)
            events.append(_record_event(len(events) + 1, load, nx, k_list,
                                        plies_deg, modes, a_after))
            continue

        roots = [(k, s1_u, s2_u, t12_u, _event_root(s1_u, s2_u, t12_u, coeffs))
                 for k, s1_u, s2_u, t12_u in response]
        candidates = [item for item in roots
                     if item[4] is not None and item[4] > load * (1.0 + _ROOT_TOL)]
        if not candidates:
            if lam_eps is not None:
                reason = "strain-limit"
                load = lam_eps
            else:
                reason = "no-further-ply-failure"
            break

        lam_event = min(item[4] for item in candidates)
        if lam_eps is not None and lam_eps < lam_event:
            reason = "strain-limit"
            load = lam_eps
            break

        group = [item for item in candidates
                 if abs(item[4] - lam_event) <= _ROOT_TOL * lam_event]
        load = lam_event
        k_list = [item[0] for item in group]
        modes = _classify_event_modes(
            [(item[0], item[1], item[2], item[3]) for item in group],
            load, allowables
        )
        modes = [
            "fiber" if (mode == "matrix" and states[k][1] == 0.0 and states[k][2] == 0.0)
            else mode
            for k, mode in zip(k_list, modes)
        ]
        states = _apply_discounts(states, k_list, modes)
        a_after = _assemble_a_block(plies_deg, ply_thickness_mm, states)
        events.append(_record_event(len(events) + 1, load, nx, k_list,
                                    plies_deg, modes, a_after))
        if not any(st[0] > 0.0 or st[1] > 0.0 or st[2] > 0.0 for st in states):
            reason = "last-ply-failure"
            break

    return _build_report(plies_deg, ply_thickness_mm, nx, ny, nxy,
                         a_initial, events, reason, load)


def _build_report(plies_deg, ply_thickness_mm, nx, ny, nxy, a_initial,
                   events, reason, load):
    """Assemble the final report dict from the march's events."""
    report = {
        "ply_angles_deg": list(plies_deg),
        "ply_thickness_mm": ply_thickness_mm,
        "nx_ref": nx,
        "ny_ref": ny,
        "nxy_ref": nxy,
        "a_initial": a_initial,
        "events": events,
        "termination_reason": reason,
    }
    if events:
        fpf = events[0]
        report["fpf_event_index"] = fpf["event"]
        report["fpf_load_nx"] = fpf["load_nx"]
        report["fpf_plies"] = fpf["failed_plies"]
        report["fpf_modes"] = fpf["modes"]
        report["ultimate_event_index"] = events[-1]["event"]
        report["ultimate_load_nx"] = events[-1]["load_nx"]
        report["post_fpf_reserve_factor"] = (
            report["ultimate_load_nx"] / report["fpf_load_nx"]
            if report["fpf_load_nx"] > 0.0 else None
        )
    else:
        report["fpf_event_index"] = None
        report["fpf_load_nx"] = None
        report["fpf_plies"] = None
        report["fpf_modes"] = None
        report["ultimate_event_index"] = None
        report["ultimate_load_nx"] = load
        report["post_fpf_reserve_factor"] = None
    return report
