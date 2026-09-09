"""Wave-49 spec anchor: structures/composites/laminate-progressive-failure.

Ply-discount / last-ply-failure march of a composite laminate under
in-plane load resultants, pure stdlib (math + os + sys only), fully
deterministic, no RNG, no tables.

Conventions (identical identity class to the on-disk sibling
structures/composites/laminate-first-ply-failure):

- Stresses, moduli and allowables in MPa; resultants in N/mm; ply
  thickness in mm; strains dimensionless.
- Plies are listed bottom to top as angles in degrees; the leaf works
  the symmetric balanced in-plane world and the full 3x3 in-plane
  block of A, so a balance-breaking discount (possible in general
  mixed loads) stays well posed.
- Per-ply Tsai-Wu index from the A-inverse mid-plane strain recovery,
  exactly the sibling formula: FI = F1 s1 + F2 s2 + F11 s1^2 +
  F22 s2^2 + F66 t12^2 + 2 F12 s1 s2 with F1 = 1/Xt - 1/Xc,
  F2 = 1/Yt - 1/Yc, F11 = 1/(Xt Xc), F22 = 1/(Yt Yc), F66 = 1/S^2,
  F12 = -0.5 sqrt(F11 F22).
- EVENT convention (this leaf): a ply event occurs at the load scale
  where the ply index actually reaches unity, the positive root of
  FI(lambda) = a lambda^2 + b lambda = 1 (the index is quadratic in
  the load scale because stresses scale linearly). The sibling leaf's
  first-ply-failure scale k* = 1 / max(FI) is its documented
  LINEARIZED reserve convention (its own Pitfalls say so); this leaf
  marches the exact index to unity, which is what a consistent
  multi-event march requires.
- PLY-DISCOUNT convention (receipt, gate d): a matrix-mode failure
  zeroes E2, G12 and nu12 of that ply (E1 retained: the failed ply
  keeps carrying fiber-direction load as a tape, and can later fail
  again in fiber mode); a fiber-mode failure zeroes E1 as well, and
  the ply carries nothing further.
- MODE discrimination: fiber mode iff s1 >= Xt (tension) or
  s1 <= -Xc (compression) at the event stress state, else matrix
  mode. For a retained-E1 tape the index FI = 1 factors exactly as
  (s1 - Xt)(s1 + Xc) = 0, so a tape always re-fails in fiber mode;
  the state guard below makes progress monotone in all cases.

March algorithm (load controlled, proportional from zero):

1. Assemble the in-plane A block (full 6-tuple order A11, A12, A16,
   A22, A26, A66) from the current per-ply degraded constants.
2. If no active stiffness remains or the A block is not positive
   definite, stop: the last recorded event load is the ultimate load
   (reason "last-ply-failure").
3. If a strain limit is set and an active ply fiber strain has
   already reached it, stop at the current load (reason
   "strain-limit").
4. With the current A, stresses are linear in the total load scale
   lambda; per active ply solve the quadratic FI_k(lambda) = 1 for
   its smallest positive root. If a remaining active ply already has
   FI >= 1 at the current load (a load-controlled cascade after a
   discount), fail those plies immediately at the current load.
5. Otherwise the next event sits at the smallest root above the
   current load; group every ply whose root equals it (within 1e-9
   relative), classify each by its mode at the event stress, apply
   the discount, record the event with the degraded A after it, and
   loop. A strain limit, when set and reached before the next event,
   stops the march at the strain-limit load (reason "strain-limit").

Reported quantities (receipt, gate d): the failure sequence (event
loads, failed plies, modes), the degraded laminate stiffness after
each event, the first-ply-failure (FPF) event, the ultimate
(last-ply-failure) load, and the post-FPF reserve factor
ultimate / FPF.

Deterministic closure checks asserted in __main__ (receipt, gate d):

- [0]8 unidirectional reduction: a [0]8 stack under Nx fails in the
  fiber direction with s1 = Nx/t = Xt at Nx = Xt * h, so FPF =
  last-ply = ultimate and the march reduces to the FPF identity.
- Quasi-isotropic magnitude: for the worked high-strength
  carbon/epoxy [0/90/45/-45]s stack the 90-degree matrix event (FPF)
  sits at roughly a third to a fifth of the 0-degree fiber-failure
  ultimate load (asserted band 0.20 to 0.35).
- Sibling-oracle parity: the on-disk laminate-first-ply-failure
  logic module, imported at run time from its repo path, returns a
  max per-ply index of 1.0 at this leaf's first event load, and
  reproduces its own published T300/5208 worked example.
"""

import math
import os
import sys

# --------------------------------------------------------------------------
# Module constants (every fixed number used by the worked examples)
# --------------------------------------------------------------------------

# Worked QI stack [0/90/45/-45]s, ply thickness 0.125 mm, 8 plies, h = 1 mm.
QI_ANGLES = [0.0, 90.0, 45.0, -45.0, -45.0, 45.0, 90.0, 0.0]
PLY_T_MM = 0.125

# High-strength carbon/epoxy (T800H-class design allowables, the leaf
# convention that allowables are given inputs): T300/5208-class
# engineering constants with a high-strength fiber tension allowable.
HC_E1 = 181000.0   # MPa
HC_E2 = 10300.0    # MPa
HC_G12 = 7170.0    # MPa
HC_NU12 = 0.28
HC_XT = 2700.0     # MPa, fiber tension allowable
HC_XC = 2000.0     # MPa, fiber compression allowable
HC_YT = 40.0       # MPa, transverse tension allowable
HC_YC = 246.0      # MPa, transverse compression allowable
HC_S = 68.0        # MPa, in-plane shear allowable

# T300/5208 reprise constants (identical to the sibling leaf's module).
T300_E1 = 181000.0
T300_E2 = 10300.0
T300_G12 = 7170.0
T300_NU12 = 0.28
T300_XT = 1500.0
T300_XC = 1500.0
T300_YT = 40.0
T300_YC = 246.0
T300_S = 68.0

UD8_ANGLES = [0.0] * 8   # [0]8 unidirectional stack for the FPF identity


# --------------------------------------------------------------------------
# Closed-form machinery
# --------------------------------------------------------------------------

def q_matrix_from_constants(e1, e2, nu12, g12):
    """Return (q11, q12, q22, q66) from the engineering constants.

    q11 = E1 / (1 - nu12 nu21), q22 = E2 / (1 - nu12 nu21),
    q12 = nu12 E2 / (1 - nu12 nu21), q66 = G12 with
    nu21 = nu12 E2 / E1 (MPa). ValueError for non-positive constants
    or a singular Poisson product.
    """
    if e1 <= 0.0 or e2 <= 0.0 or g12 <= 0.0 or nu12 <= 0.0:
        raise ValueError(
            "engineering constants E1, E2, G12, nu12 must be positive")
    nu21 = nu12 * e2 / e1
    denominator = 1.0 - nu12 * nu21
    if denominator <= 0.0:
        raise ValueError(
            "nu12 nu21 >= 1 makes the plane-stress stiffness singular")
    q11 = e1 / denominator
    q22 = e2 / denominator
    q12 = nu12 * e2 / denominator
    return (q11, q12, q22, g12)


def _q_unchecked(e1, e2, nu12, g12):
    """Plane-stress stiffness without input checks (degraded states,
    where nu12 = 0 and E2 = 0 are legal, go through here)."""
    nu21 = nu12 * e2 / e1 if e1 > 0.0 else 0.0
    denominator = 1.0 - nu12 * nu21
    if denominator <= 0.0:
        denominator = 1.0
    q11 = e1 / denominator
    q22 = e2 / denominator
    q12 = nu12 * e2 / denominator
    return (q11, q12, q22, g12)


def _rotated_full(q_components, theta_deg):
    """Rotate the ply stiffness to the laminate axes at theta_deg.

    Returns the full in-plane 6-tuple (Qb11, Qb12, Qb16, Qb22, Qb26,
    Qb66), the standard fourth-power closed form of Jones ch. 2 (the
    same arithmetic order the wave-48 laminate-bending-stiffness spec
    pins for Qbar16 and Qbar26).
    """
    q11, q12, q22, q66 = q_components
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2 = c * c
    s2 = s * s
    c4 = c2 * c2
    s4 = s2 * s2
    s2c2 = s2 * c2
    cs = c * s
    qb11 = q11 * c4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * s4
    qb22 = q11 * s4 + 2.0 * (q12 + 2.0 * q66) * s2c2 + q22 * c4
    qb12 = (q11 + q22 - 4.0 * q66) * s2c2 + q12 * (c4 + s4)
    qb66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * s2c2 + q66 * (c4 + s4)
    qb16 = ((q11 - q12 - 2.0 * q66) * c2
            - (q22 - q12 - 2.0 * q66) * s2) * cs
    qb26 = ((q11 - q12 - 2.0 * q66) * s2
            - (q22 - q12 - 2.0 * q66) * c2) * cs
    return (qb11, qb12, qb16, qb22, qb26, qb66)


def _assemble_a(plies_deg, ply_thickness_mm, states):
    """Assemble (A11, A12, A16, A22, A26, A66) in N/mm from per-ply
    degraded engineering-constant states (e1, e2, nu12, g12) each.
    """
    a11 = a12 = a16 = a22 = a26 = a66 = 0.0
    for theta_deg, (e1s, e2s, nu12s, g12s) in zip(plies_deg, states):
        q = _q_unchecked(e1s, e2s, nu12s, g12s)
        qb11, qb12, qb16, qb22, qb26, qb66 = _rotated_full(q, theta_deg)
        a11 += qb11 * ply_thickness_mm
        a12 += qb12 * ply_thickness_mm
        a16 += qb16 * ply_thickness_mm
        a22 += qb22 * ply_thickness_mm
        a26 += qb26 * ply_thickness_mm
        a66 += qb66 * ply_thickness_mm
    return (a11, a12, a16, a22, a26, a66)


def laminate_a_matrix(plies_deg, ply_thickness_mm, e1, e2, nu12, g12):
    """Return the intact-laminate in-plane stiffness block
    (A11, A12, A16, A22, A26, A66) in N/mm (the A matrix the sibling
    first-ply-failure leaf inverts; the 4-tuple (A11, A12, A22, A66)
    is its balanced-symmetric sub-block). ValueErrors: empty ply list,
    non-positive thickness, non-positive constants (see
    q_matrix_from_constants).
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if ply_thickness_mm <= 0.0:
        raise ValueError(
            "ply thickness must be a positive number, got %r"
            % (ply_thickness_mm,))
    q = q_matrix_from_constants(e1, e2, nu12, g12)
    states = [(e1, e2, nu12, g12)] * len(plies_deg)
    return _assemble_a(plies_deg, ply_thickness_mm, states)


def _invert_a_block(a_components):
    """Return the exact closed-form inverse of the symmetric 3x3
    in-plane block plus its determinant, or None if not positive
    definite: (i11, i12, i16, i22, i26, i66, det).
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
    in-plane block inverse: {eps} = [A]^-1 {N}. Resultants in N/mm,
    strains dimensionless. ValueError for a non-positive-definite
    block.
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
    """Strains transformed to the ply material axes (sibling closed
    form): e1 = ex c^2 + ey s^2 + gxy c s, e2 = ex s^2 + ey c^2 -
    gxy c s, g12 = 2 (ey - ex) c s + gxy (c^2 - s^2)."""
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2 = c * c
    s2 = s * s
    cs = c * s
    e1 = ex * c2 + ey * s2 + gxy * cs
    e2 = ex * s2 + ey * c2 - gxy * cs
    g12 = 2.0 * (ey - ex) * cs + gxy * (c2 - s2)
    return (e1, e2, g12)


def _stresses_from_q(e1, e2, g12, q):
    """s1, s2, t12 from material strains and the ply stiffness tuple
    (q11, q12, q22, q66)."""
    q11, q12, q22, q66 = q
    s1 = q11 * e1 + q12 * e2
    s2 = q12 * e1 + q22 * e2
    t12 = q66 * g12
    return (s1, s2, t12)


def tsai_wu_index(s1, s2, t12, allowables):
    """Return the Tsai-Wu failure index for a ply stress state, the
    exact sibling closed form. allowables = (xt, xc, yt, yc, s_uv).
    ValueError for non-positive allowables.
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
    return (f1 * s1 + f2 * s2 + f11 * s1 * s1 + f22 * s2 * s2
            + f66 * t12 * t12 + 2.0 * f12 * s1 * s2)


def per_ply_failure_indices(plies_deg, a_components, e1, e2, nu12, g12,
                            allowables, nx, ny, nxy):
    """Return the per-ply Tsai-Wu failure indices (list order matches
    plies_deg) of the INTACT laminate at the given resultants, the
    sibling-parity surface used for the FPF cross-checks."""
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    q = q_matrix_from_constants(e1, e2, nu12, g12)
    ex, ey, gxy = midplane_strains(a_components, nx, ny, nxy)
    indices = []
    for theta_deg in plies_deg:
        e1p, e2p, g12p = _ply_material_strains(ex, ey, gxy, theta_deg)
        s1, s2, t12 = _stresses_from_q(e1p, e2p, g12p, q)
        indices.append(tsai_wu_index(s1, s2, t12, allowables))
    return indices


def ply_discount_mode(s1, s2, t12, xt, xc):
    """Return the ply-discount failure mode: "fiber" iff s1 >= xt or
    s1 <= -xc at the event stress state (with a 1e-9 relative slack
    so an event exactly on the fiber boundary classifies fiber in
    floating point), else "matrix". Matrix mode zeroes E2, G12 and
    nu12; fiber mode zeroes E1 as well.
    """
    if s1 >= xt * (1.0 - 1e-9) or s1 <= -xc * (1.0 - 1e-9):
        return "fiber"
    return "matrix"


def progressive_failure_march(plies_deg, ply_thickness_mm, e1, e2, nu12,
                              g12, allowables, nx, ny, nxy,
                              strain_limit=None):
    """Run the ply-discount / last-ply-failure march and return the
    report dict (see the module docstring for the algorithm and the
    event convention). ValueErrors: empty ply list, non-positive
    thickness or constants or allowables, an all-zero reference
    resultant, a non-positive strain limit.

    Report dict keys:
    - ply_angles_deg, ply_thickness_mm
    - nx_ref, ny_ref, nxy_ref: the reference resultant (N/mm)
    - a_initial: the intact (A11, A12, A16, A22, A26, A66) in N/mm
    - events: list of dicts, one per ply event, each with keys event
      (1-based), load_nx (the total applied Nx at the event, N/mm),
      load_multiplier (dimensionless), failed_plies (0-based
      indices), failed_angles_deg, modes, a_after (the degraded
      in-plane block after the discount, N/mm)
    - fpf_event_index, fpf_load_nx, fpf_plies, fpf_modes: the first
      event (None when no ply event precedes termination)
    - ultimate_event_index, ultimate_load_nx: the last-ply-failure
      load (or the strain-limit load)
    - post_fpf_reserve_factor: ultimate / FPF (None when no FPF
      event)
    - termination_reason: one of "last-ply-failure", "strain-limit",
      "no-further-ply-failure"
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if ply_thickness_mm <= 0.0:
        raise ValueError(
            "ply thickness must be a positive number, got %r"
            % (ply_thickness_mm,))
    q_matrix_from_constants(e1, e2, nu12, g12)   # validates the constants
    xt, xc, yt, yc, s_uv = allowables
    if xt <= 0.0 or xc <= 0.0 or yt <= 0.0 or yc <= 0.0 or s_uv <= 0.0:
        raise ValueError("allowables Xt, Xc, Yt, Yc, S must be positive")
    if nx == 0.0 and ny == 0.0 and nxy == 0.0:
        raise ValueError("the reference resultant (Nx, Ny, Nxy) must be nonzero")
    if strain_limit is not None and strain_limit <= 0.0:
        raise ValueError(
            "strain limit must be a positive number, got %r" % (strain_limit,))

    states = [(e1, e2, nu12, g12)] * len(plies_deg)
    a0 = _assemble_a(plies_deg, ply_thickness_mm, states)
    if _invert_a_block(a0) is None:
        raise ValueError("the intact laminate A block is not positive definite")

    events = []
    load = 0.0
    reason = "no-further-ply-failure"
    rel_tol = 1e-9

    while True:
        a_now = _assemble_a(plies_deg, ply_thickness_mm, states)
        inv = _invert_a_block(a_now)
        active = [k for k, st in enumerate(states) if st[0] > 0.0
                  or st[1] > 0.0 or st[3] > 0.0]
        if inv is None or not active:
            reason = "last-ply-failure"
            break

        # Per-unit strains and stresses at the reference resultant.
        ex_u, ey_u, gxy_u = midplane_strains(a_now, nx, ny, nxy)
        ply_info = []
        max_abs_e1_u = 0.0
        for k in active:
            theta_deg = plies_deg[k]
            st = states[k]
            q = _q_unchecked(st[0], st[1], st[2], st[3])
            e1p, e2p, g12p = _ply_material_strains(ex_u, ey_u, gxy_u,
                                                   theta_deg)
            s1_u, s2_u, t12_u = _stresses_from_q(e1p, e2p, g12p, q)
            fi_now = tsai_wu_index(s1_u * load, s2_u * load, t12_u * load,
                                   allowables)
            ply_info.append((k, s1_u, s2_u, t12_u, fi_now))
            max_abs_e1_u = max(max_abs_e1_u, abs(e1p))

        # Strain-limit termination: fiber strain of an active ply.
        if strain_limit is not None and max_abs_e1_u > 0.0:
            lam_eps = strain_limit / max_abs_e1_u
            if lam_eps <= load * (1.0 + rel_tol):
                reason = "strain-limit"
                break
        else:
            lam_eps = float("inf")

        # Load-controlled cascade: an active ply already at or past
        # unity at the current load fails immediately (no load rise).
        cascade = [info for info in ply_info if info[4] >= 1.0 - 1e-9]
        if cascade and load > 0.0:
            k_list = [info[0] for info in cascade]
            modes = []
            for k, s1_u, s2_u, t12_u, _fi in cascade:
                modes.append(ply_discount_mode(
                    s1_u * load, s2_u * load, t12_u * load, xt, xc))
            events.append(_record_event(events, load, nx, k_list,
                                        plies_deg, modes))
            _apply_discounts(states, k_list, modes)
            events[-1]["a_after"] = _assemble_a(plies_deg, ply_thickness_mm,
                                                states)
            continue

        # Smallest positive quadratic root of FI_k(lambda) = 1 over
        # active plies, strictly above the current load.
        best = None
        for k, s1_u, s2_u, t12_u, _fi in ply_info:
            aq = (_tw_quadratic_a(s1_u, s2_u, t12_u, allowables))
            bq = (_tw_linear_b(s1_u, s2_u, allowables))
            root = _positive_root(aq, bq)
            if root is None or root <= load * (1.0 + rel_tol):
                continue
            if best is None or root < best[0]:
                best = (root, k, s1_u, s2_u, t12_u)
        if best is None:
            if lam_eps != float("inf"):
                reason = "strain-limit"
                load = lam_eps
            else:
                reason = "no-further-ply-failure"
            break

        lam_event = best[0]
        if lam_eps < lam_event:
            reason = "strain-limit"
            load = lam_eps
            break

        group = [(root, k, s1_u, s2_u, t12_u) for (root, k, s1_u, s2_u,
                 t12_u) in _all_roots(ply_info, allowables)
                 if root is not None and abs(root - lam_event)
                 <= rel_tol * lam_event]
        k_list = [item[1] for item in group]
        modes = []
        for _root, k, s1_u, s2_u, t12_u in group:
            mode = ply_discount_mode(s1_u * lam_event, s2_u * lam_event,
                                     t12_u * lam_event, xt, xc)
            # State guard: a matrix discount must change the ply; a
            # retained-E1 tape reaching unity re-fails in fiber mode
            # (FI = 1 factors as (s1 - Xt)(s1 + Xc) = 0 for a tape).
            if mode == "matrix":
                st = states[k]
                if st[1] == 0.0 and st[3] == 0.0:
                    mode = "fiber"
            modes.append(mode)
        load = lam_event
        events.append(_record_event(events, load, nx, k_list, plies_deg,
                                    modes))
        _apply_discounts(states, k_list, modes)
        events[-1]["a_after"] = _assemble_a(plies_deg, ply_thickness_mm,
                                            states)
        if not any(st[0] > 0.0 or st[1] > 0.0 or st[3] > 0.0
                   for st in states):
            reason = "last-ply-failure"
            break

    report = {
        "ply_angles_deg": list(plies_deg),
        "ply_thickness_mm": ply_thickness_mm,
        "nx_ref": nx,
        "ny_ref": ny,
        "nxy_ref": nxy,
        "a_initial": a0,
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
    else:
        report["fpf_event_index"] = None
        report["fpf_load_nx"] = None
        report["fpf_plies"] = None
        report["fpf_modes"] = None
        report["ultimate_event_index"] = None
        report["ultimate_load_nx"] = load
    if report["fpf_load_nx"] is not None and report["fpf_load_nx"] > 0.0:
        report["post_fpf_reserve_factor"] = (report["ultimate_load_nx"]
                                             / report["fpf_load_nx"])
    else:
        report["post_fpf_reserve_factor"] = None
    return report


def _record_event(events, load, nx, k_list, plies_deg, modes):
    """Build one event dict (a_after is filled by the caller right
    after the discount is applied)."""
    return {
        "event": len(events) + 1,
        "load_multiplier": load,
        "load_nx": load * nx,
        "failed_plies": k_list,
        "failed_angles_deg": [plies_deg[k] for k in k_list],
        "modes": modes,
        "a_after": None,
    }


def _all_roots(ply_info, allowables):
    """Roots of FI_k(lambda) = 1 for every reported active ply."""
    out = []
    for k, s1_u, s2_u, t12_u, _fi in ply_info:
        aq = _tw_quadratic_a(s1_u, s2_u, t12_u, allowables)
        bq = _tw_linear_b(s1_u, s2_u, allowables)
        out.append((_positive_root(aq, bq), k, s1_u, s2_u, t12_u))
    return out


def _tw_quadratic_a(s1_u, s2_u, t12_u, allowables):
    """Quadratic-in-load coefficient of the Tsai-Wu index at unit
    reference resultants."""
    xt, xc, yt, yc, s_uv = allowables
    f11 = 1.0 / (xt * xc)
    f22 = 1.0 / (yt * yc)
    f66 = 1.0 / (s_uv * s_uv)
    f12 = -0.5 * math.sqrt(f11 * f22)
    return (f11 * s1_u * s1_u + f22 * s2_u * s2_u + f66 * t12_u * t12_u
            + 2.0 * f12 * s1_u * s2_u)


def _tw_linear_b(s1_u, s2_u, allowables):
    """Linear-in-load coefficient of the Tsai-Wu index at unit
    reference resultants."""
    xt, xc, yt, yc, _s_uv = allowables
    f1 = 1.0 / xt - 1.0 / xc
    f2 = 1.0 / yt - 1.0 / yc
    return f1 * s1_u + f2 * s2_u


def _positive_root(aq, bq):
    """Smallest positive root of aq lambda^2 + bq lambda - 1 = 0, or
    None when no positive root exists (the ply never fails in this
    segment)."""
    if aq == 0.0:
        if bq > 0.0:
            return 1.0 / bq
        return None
    disc = bq * bq + 4.0 * aq
    if disc < 0.0:
        return None
    sqrt_disc = math.sqrt(disc)
    r1 = (-bq - sqrt_disc) / (2.0 * aq)
    r2 = (-bq + sqrt_disc) / (2.0 * aq)
    candidates = [r for r in (r1, r2) if r > 0.0]
    if not candidates:
        return None
    return min(candidates)


def _apply_discounts(states, k_list, modes):
    """Apply the ply-discount reductions in place: matrix mode zeroes
    E2, G12 and nu12 (E1 retained); fiber mode zeroes E1 as well.
    """
    for k, mode in zip(k_list, modes):
        st = list(states[k])
        if mode == "fiber":
            st[0] = 0.0
        st[1] = 0.0
        st[2] = 0.0
        st[3] = 0.0
        states[k] = tuple(st)


# --------------------------------------------------------------------------
# __main__: run the worked examples, print REAL outputs, assert closures
# --------------------------------------------------------------------------

def _fmt(x):
    return format(x, ".12g")


def main():
    print("anchor_laminate-progressive-failure.py")
    print("python %s" % sys.version.split()[0])
    print("module: pure stdlib (math, os, sys), deterministic, no RNG")
    print("")

    # ---------------- Section 1: intact QI assembly ----------------
    print("== Section 1: intact [0/90/45/-45]s assembly ==")
    a_qi = laminate_a_matrix(QI_ANGLES, PLY_T_MM, HC_E1, HC_E2, HC_NU12,
                             HC_G12)
    print("a_initial = %r N/mm" % (a_qi,))
    q_qi = q_matrix_from_constants(HC_E1, HC_E2, HC_NU12, HC_G12)
    print("q = %r MPa" % (q_qi,))
    ex1, ey1, gxy1 = midplane_strains(a_qi, 100.0, 0.0, 0.0)
    print("midplane strains at Nx = 100 N/mm: ex %.12g ey %.12g gxy %.12g"
          % (ex1, ey1, gxy1))
    assert abs(ex1 - 1.4352e-3) < 1e-6, "strain parity vs sibling failed"
    assert abs(a_qi[2]) < 1e-6 and abs(a_qi[4]) < 1e-6, \
        "QI A16/A26 must vanish"
    print("A16 = %.3g and A26 = %.3g N/mm: balanced symmetric "
          "coupling terms vanish to machine precision"
          % (a_qi[2], a_qi[4]))
    print("")

    # ---------------- Section 2: QI progressive-failure march ----
    print("== Section 2: QI march (high-strength carbon/epoxy, Nx only) ==")
    allow_hc = (HC_XT, HC_XC, HC_YT, HC_YC, HC_S)
    rep = progressive_failure_march(QI_ANGLES, PLY_T_MM, HC_E1, HC_E2,
                                    HC_NU12, HC_G12, allow_hc, 1.0, 0.0,
                                    0.0)
    a_afters = [ev["a_after"] for ev in rep["events"]]
    print("termination_reason = %s" % rep["termination_reason"])
    print("fpf_event_index = %r" % rep["fpf_event_index"])
    print("fpf_load_nx = %.12g N/mm" % rep["fpf_load_nx"])
    print("fpf_plies = %r" % rep["fpf_plies"])
    print("fpf_modes = %r" % rep["fpf_modes"])
    print("ultimate_event_index = %r" % rep["ultimate_event_index"])
    print("ultimate_load_nx = %.12g N/mm" % rep["ultimate_load_nx"])
    print("post_fpf_reserve_factor = %.12g" % rep["post_fpf_reserve_factor"])
    for i, ev in enumerate(rep["events"]):
        print("event %d: load_nx %.12g N/mm, plies %r angles %r modes %r"
              % (ev["event"], ev["load_nx"], ev["failed_plies"],
                 ev["failed_angles_deg"], ev["modes"]))
        print("  a_after = %r N/mm" % (a_afters[i],))
    ratio = rep["fpf_load_nx"] / rep["ultimate_load_nx"]
    print("fpf/ultimate ratio = %.12g" % ratio)
    print("note: events 3 and 4 share the load: once the 0-degree plies "
          "drop out, the retained-E1 tapes (90 and 45 degrees) cascade to "
          "fiber failure at the same applied load (load-controlled "
          "cascade), zeroing the laminate stiffness")
    assert 0.20 <= ratio <= 0.35, "QI magnitude gate out of band"
    assert rep["fpf_modes"] == ["matrix", "matrix"], \
        "FPF must be 90-ply matrix"
    assert rep["fpf_plies"] == [1, 6], "FPF plies must be the two 90s"
    # The 0-ply fiber event (index 3, plies [0, 7]) sets the ultimate;
    # the final same-load event is the tape cascade that zeroes A.
    assert rep["events"][2]["failed_plies"] == [0, 7]
    assert rep["events"][2]["modes"] == ["fiber", "fiber"], \
        "the 0-ply fiber failure is the last-ply event"
    assert abs(rep["events"][3]["load_nx"]
               - rep["events"][2]["load_nx"]) < 1e-6 * \
        rep["events"][2]["load_nx"]
    assert abs(rep["ultimate_load_nx"]
               - rep["events"][2]["load_nx"]) < 1e-6 * \
        rep["events"][2]["load_nx"]
    assert all(v == 0.0 for v in a_afters[-1]), \
        "final cascade must leave zero laminate stiffness"
    assert rep["fpf_load_nx"] < rep["ultimate_load_nx"]
    # Degraded stiffness monotonicity: A11, A22, A66 never increase.
    prev = list(rep["a_initial"])
    for a_after in a_afters:
        for idx in (0, 3, 5):
            assert a_after[idx] <= prev[idx] * (1.0 + 1e-9) + 1e-9, \
                "diagonal A terms must not increase across events"
        prev = a_after
    print("degraded A11/A22/A66 monotone non-increasing across events: ok")
    print("")

    # ---------------- Section 3: [0]8 FPF identity -----------------
    print("== Section 3: [0]8 unidirectional reduction identity ==")
    t_total = 8.0 * PLY_T_MM
    rep0 = progressive_failure_march(UD8_ANGLES, PLY_T_MM, HC_E1, HC_E2,
                                     HC_NU12, HC_G12, allow_hc, 1.0, 0.0,
                                     0.0)
    print("events = %d" % len(rep0["events"]))
    print("event1 load_nx = %.12g N/mm" % rep0["events"][0]["load_nx"])
    print("event1 modes = %r" % rep0["events"][0]["modes"])
    print("event1 failed_plies = %r" % rep0["events"][0]["failed_plies"])
    print("ultimate_load_nx = %.12g N/mm" % rep0["ultimate_load_nx"])
    print("post_fpf_reserve_factor = %.12g" % rep0["post_fpf_reserve_factor"])
    print("termination_reason = %s" % rep0["termination_reason"])
    assert len(rep0["events"]) == 1
    assert rep0["events"][0]["modes"] == ["fiber"] * 8
    assert abs(rep0["ultimate_load_nx"] - HC_XT * t_total) < 1e-6, \
        "[0]8 must fail at s1 = Nx/t = Xt"
    assert abs(rep0["post_fpf_reserve_factor"] - 1.0) < 1e-9
    print("[0]8 identity: FPF = last-ply = ultimate at Nx = Xt*h = "
          "%.12g N/mm: ok" % (HC_XT * t_total,))
    # Strain-limit termination on the [0]8 stack.
    strain_half = 0.5 * HC_XT / HC_E1
    rep_eps = progressive_failure_march(UD8_ANGLES, PLY_T_MM, HC_E1,
                                        HC_E2, HC_NU12, HC_G12, allow_hc,
                                        1.0, 0.0, 0.0,
                                        strain_limit=strain_half)
    print("strain-limit run: limit %.12g, events = %d, ultimate_load_nx = "
          "%.12g N/mm, reason = %s"
          % (strain_half, len(rep_eps["events"]), rep_eps["ultimate_load_nx"],
             rep_eps["termination_reason"]))
    assert rep_eps["termination_reason"] == "strain-limit"
    assert len(rep_eps["events"]) == 0
    assert abs(rep_eps["ultimate_load_nx"] - strain_half * HC_E1
               * t_total) < 1e-6
    print("")

    # ---------------- Section 4: sibling-oracle parity ------------
    print("== Section 4: T300/5208 reprise and sibling-oracle parity ==")
    sibling = None
    try:
        _here = os.path.dirname(os.path.abspath(__file__))
        _root = os.path.abspath(os.path.join(_here, "..", "..", "..",
                                             "..", ".."))
        _sib_dir = os.path.join(_root, "skills", "structures", "composites",
                                "laminate-first-ply-failure", "scripts")
        sys.path.insert(0, _sib_dir)
        import laminate_first_ply_failure_logic as sib
        sibling = sib
    except Exception as exc:  # pragma: no cover - oracle availability
        print("sibling oracle import failed: %s" % (exc,))

    allow_t300 = (T300_XT, T300_XC, T300_YT, T300_YC, T300_S)
    q_t300 = q_matrix_from_constants(T300_E1, T300_E2, T300_NU12, T300_G12)
    a_t300 = laminate_a_matrix(QI_ANGLES, PLY_T_MM, T300_E1, T300_E2,
                               T300_NU12, T300_G12)
    print("T300/5208 QI intact A = %r N/mm" % (a_t300,))
    print("T300/5208 QI A11 = %.12g N/mm A12 = %.12g N/mm A22 = "
          "%.12g N/mm A66 = %.12g N/mm" % (a_t300[0], a_t300[1], a_t300[3],
                                           a_t300[5]))
    idx100 = per_ply_failure_indices(QI_ANGLES, a_t300, T300_E1, T300_E2,
                                     T300_NU12, T300_G12, allow_t300,
                                     100.0, 0.0, 0.0)
    print("per-ply indices at Nx = 100 N/mm (T300/5208) = %r" % (idx100,))
    maxidx = max(idx100)
    print("max index = %.12g at ply %d (%.0f deg)" % (maxidx,
          idx100.index(maxidx), QI_ANGLES[idx100.index(maxidx)]))
    rep_t300 = progressive_failure_march(QI_ANGLES, PLY_T_MM, T300_E1,
                                         T300_E2, T300_NU12, T300_G12,
                                         allow_t300, 1.0, 0.0, 0.0)
    print("T300/5208 QI march: fpf_load_nx = %.12g N/mm, plies %r, "
          "ultimate_load_nx = %.12g N/mm, ratio %.12g"
          % (rep_t300["fpf_load_nx"], rep_t300["fpf_plies"],
             rep_t300["ultimate_load_nx"],
             rep_t300["fpf_load_nx"] / rep_t300["ultimate_load_nx"]))
    if sibling is not None:
        sib_a = sibling.a_matrix_from_plies(QI_ANGLES, q_t300, PLY_T_MM)
        # The sibling's a_components argument is the A-INVERSE
        # compliance tuple in mm/N, not the A matrix itself.
        sib_comp = sibling.a_inverse_compliance(sib_a[0], sib_a[1],
                                                sib_a[2], sib_a[3])
        sib_fpf = sibling.first_ply_failure(QI_ANGLES, q_t300, allow_t300,
                                            100.0, 0.0, 0.0, sib_comp)
        print("sibling oracle: max_fi = %.12g, critical ply %d, "
              "fpf_scale_k = %.12g, fpf_load_nx = %.12g N/mm"
              % (sib_fpf["max_fi"], sib_fpf["critical_ply_index"],
                 sib_fpf["fpf_scale_k"], sib_fpf["fpf_load_nx"]))
        assert abs(sib_fpf["max_fi"] - 0.313007) < 1e-4, \
            "sibling worked example not reproduced"
        assert abs(sib_fpf["fpf_load_nx"] - 319.5) < 0.1, \
            "sibling FPF load not reproduced"
        # Sibling index oracle at THIS leaf's quadratic-exact event.
        sib_at = sibling.ply_failure_indices(QI_ANGLES, q_t300, allow_t300,
                                             rep_t300["fpf_load_nx"], 0.0,
                                             0.0, sib_comp)
        max_at = max(sib_at)
        print("sibling oracle indices at this leaf's FPF load: max = "
              "%.12g" % max_at)
        assert abs(max_at - 1.0) < 1e-6, \
            "sibling index oracle must reach unity at the march FPF load"
        print("sibling-parity: max index reaches 1.0 at the march FPF "
              "load: ok")
        print("convention note: sibling linearized k* load %.12g N/mm vs "
              "this leaf quadratic-exact event %.12g N/mm (ratio %.12g)"
              % (sib_fpf["fpf_load_nx"], rep_t300["fpf_load_nx"],
                 sib_fpf["fpf_load_nx"] / rep_t300["fpf_load_nx"]))
    print("")

    # ---------------- Section 5: ValueError rejection ---------------
    print("== Section 5: ValueError messages (real, quoted) ==")
    cases = [
        ("zero E1",
         lambda: laminate_a_matrix([0.0], PLY_T_MM, 0.0, HC_E2, HC_NU12,
                                   HC_G12)),
        ("negative thickness",
         lambda: laminate_a_matrix([0.0], -0.125, HC_E1, HC_E2, HC_NU12,
                                   HC_G12)),
        ("empty stack",
         lambda: laminate_a_matrix([], PLY_T_MM, HC_E1, HC_E2, HC_NU12,
                                   HC_G12)),
        ("singular Poisson product",
         lambda: q_matrix_from_constants(HC_E1, 1e12, 0.9, HC_G12)),
        ("zero allowable",
         lambda: progressive_failure_march(QI_ANGLES, PLY_T_MM, HC_E1,
                                           HC_E2, HC_NU12, HC_G12,
                                           (HC_XT, HC_XC, 0.0, HC_YC,
                                            HC_S), 1.0, 0.0, 0.0)),
        ("zero reference resultant",
         lambda: progressive_failure_march(QI_ANGLES, PLY_T_MM, HC_E1,
                                           HC_E2, HC_NU12, HC_G12,
                                           allow_hc, 0.0, 0.0, 0.0)),
        ("non-positive strain limit",
         lambda: progressive_failure_march(QI_ANGLES, PLY_T_MM, HC_E1,
                                           HC_E2, HC_NU12, HC_G12,
                                           allow_hc, 1.0, 0.0, 0.0,
                                           strain_limit=0.0)),
    ]
    for label, fn in cases:
        try:
            fn()
            print("%s: NO RAISE (bad)" % label)
        except ValueError as exc:
            print("%s -> ValueError: %s" % (label, exc))
    print("")

    # ---------------- Section 6: determinism -----------------------
    print("== Section 6: determinism and closure summary ==")
    rep_b = progressive_failure_march(QI_ANGLES, PLY_T_MM, HC_E1, HC_E2,
                                      HC_NU12, HC_G12, allow_hc, 1.0, 0.0,
                                      0.0)
    assert rep == rep_b, "march must be deterministic"
    print("two consecutive QI marches identical: ok")
    print("internal asserts all passed; anchor exit 0")


if __name__ == "__main__":
    main()
