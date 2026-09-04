"""First-ply-failure of a symmetric balanced composite laminate.

Pure stdlib implementation of the laminate-level strength chain:

    {N} -> [A]^-1 {N} -> per-ply material strains -> per-ply stresses
    -> per-ply Tsai-Wu failure index -> first-ply-failure scale factor.

Conventions: balanced symmetric laminate under in-plane load resultants
{Nx, Ny, Nxy} in N/mm. Mid-plane strains from {eps} = [A]^-1 {N};
balanced symmetric laminates decouple shear, so gamma_xy = a66 * Nxy.
Ply k at angle theta_k has material-axis strains transformed from the
laminate strains and material-axis stresses {s1, s2, t12} = [Q]
{e1, e2, g12}. The Tsai-Wu index is evaluated in every ply and the
first-ply-failure scale factor is k* = 1 / max(FI_k).

Tuple orders used throughout (documented once, here):

- q_components: (q11, q12, q22, q66), in-plane 2D stiffness of the ply
  material, MPa.
- allowables: (xt, xc, yt, yc, s_uv), tensile and compressive allowables
  in the fiber and transverse directions plus the in-plane shear
  allowable, MPa.
- a_components: (a11, a12, a22, a66), the A-matrix inverse compliance
  entries of the laminate, mm/N (the [A]^-1 of classical lamination
  theory for the in-plane block; a66 = 1/A66 for balanced symmetric
  stacks).

Units: stresses and allowables in MPa, strains dimensionless, resultants
in N/mm, thickness in mm. Non-physical inputs raise ValueError.
"""

import math

# Worked-example material (T300/5208) in MPa, used by the contract test
# and shown in the SKILL.md worked example.
T300_E1 = 181000.0
T300_E2 = 10300.0
T300_G12 = 7170.0
T300_NU12 = 0.28
T300_XT = 1500.0
T300_XC = 1500.0
T300_YT = 40.0
T300_YC = 246.0
T300_S = 68.0


def q_matrix_from_constants(e1, e2, nu12, g12):
    """Return (q11, q12, q22, q66) from the engineering constants.

    q11 = E1 / (1 - nu12 nu21), q22 = E2 / (1 - nu12 nu21),
    q12 = nu12 E2 / (1 - nu12 nu21), q66 = G12, with
    nu21 = nu12 E2 / E1. Stresses and constants in consistent units
    (MPa). Raises ValueError for non-positive constants or a
    non-positive denominator 1 - nu12 nu21.
    """
    if e1 <= 0.0 or e2 <= 0.0 or g12 <= 0.0 or nu12 <= 0.0:
        raise ValueError("engineering constants E1, E2, G12, nu12 must be positive")
    nu21 = nu12 * e2 / e1
    denominator = 1.0 - nu12 * nu21
    if denominator <= 0.0:
        raise ValueError("nu12 nu21 >= 1 makes the plane-stress stiffness singular")
    q11 = e1 / denominator
    q22 = e2 / denominator
    q12 = nu12 * e2 / denominator
    return (q11, q12, q22, g12)


def rotated_ply_stiffness(q_components, theta_deg):
    """Return (qb11, qb12, qb22, qb66), the ply stiffness rotated to the
    laminate axes at theta_deg (standard fourth-power rotation of the
    in-plane 2D stiffness).
    """
    q11, q12, q22, q66 = q_components
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2, s2 = c * c, s * s
    c4, s4 = c2 * c2, s2 * s2
    cs2 = c2 * s2
    qb11 = q11 * c4 + 2.0 * (q12 + 2.0 * q66) * cs2 + q22 * s4
    qb12 = (q11 + q22 - 4.0 * q66) * cs2 + q12 * (c4 + s4)
    qb22 = q11 * s4 + 2.0 * (q12 + 2.0 * q66) * cs2 + q22 * c4
    qb66 = (q11 + q22 - 2.0 * q12 - 2.0 * q66) * cs2 + q66 * (c4 + s4)
    return (qb11, qb12, qb22, qb66)


def a_matrix_from_plies(plies_deg, q_components, ply_thickness):
    """Assemble (A11, A12, A22, A66) for a balanced symmetric laminate.

    A_ij = sum over plies of Qbar_ij(theta_k) * t_k. The in-plane block
    of the A matrix is returned; A16 and A26 vanish for balanced
    symmetric stacks and are not returned. Ply angles in degrees, q
    components in MPa, ply_thickness in mm, so the A terms come out in
    N/mm. Raises ValueError for an empty ply list, malformed q
    components, or non-positive ply thickness.
    """
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if len(q_components) != 4:
        raise ValueError("q_components must be (q11, q12, q22, q66)")
    q11, q12, q22, q66 = q_components
    if q11 <= 0.0 or q22 <= 0.0 or q66 <= 0.0:
        raise ValueError("q11, q22, q66 must be positive")
    if ply_thickness <= 0.0:
        raise ValueError("ply_thickness must be positive")
    a11 = a12 = a22 = a66 = 0.0
    for theta_deg in plies_deg:
        qb11, qb12, qb22, qb66 = rotated_ply_stiffness(
            (q11, q12, q22, q66), theta_deg
        )
        a11 += qb11 * ply_thickness
        a12 += qb12 * ply_thickness
        a22 += qb22 * ply_thickness
        a66 += qb66 * ply_thickness
    return (a11, a12, a22, a66)


def a_inverse_compliance(a11_m, a12_m, a22_m, a66_m):
    """Return (a11, a12, a22, a66), the A-inverse compliance entries.

    For the balanced symmetric in-plane block the inverse decouples:
    the 2x2 normal block inverts by determinant and a66 = 1/A66.
    A terms in N/mm, compliance terms in mm/N. Raises ValueError for
    non-positive diagonal terms or a non-positive determinant.
    """
    if a11_m <= 0.0 or a22_m <= 0.0 or a66_m <= 0.0:
        raise ValueError("A11, A22, A66 must be positive")
    determinant = a11_m * a22_m - a12_m * a12_m
    if determinant <= 0.0:
        raise ValueError("A11 A22 - A12^2 must be positive")
    a11 = a22_m / determinant
    a12 = -a12_m / determinant
    a22 = a11_m / determinant
    a66 = 1.0 / a66_m
    return (a11, a12, a22, a66)


def midplane_strains(a11, a12, a22, a66, nx, ny, nxy):
    """Return (ex, ey, gxy), the laminate mid-plane strains.

    ex = a11 nx + a12 ny, ey = a12 nx + a22 ny, gxy = a66 nxy with
    a_ij the A-inverse compliance entries (mm/N) and resultants in
    N/mm. Raises ValueError when the diagonal compliance terms are not
    positive (a12 carries the Poisson cross-coupling sign and may be
    negative for a real laminate).
    """
    if a11 <= 0.0 or a22 <= 0.0 or a66 <= 0.0:
        raise ValueError("a11, a22, a66 compliance entries must be positive")
    ex = a11 * nx + a12 * ny
    ey = a12 * nx + a22 * ny
    gxy = a66 * nxy
    return (ex, ey, gxy)


def ply_material_strains(ex, ey, gxy, theta_deg):
    """Return (e1, e2, g12), laminate strains transformed to the ply
    material axes at theta_deg (c = cos, s = sin):

    e1 = ex c^2 + ey s^2 + gxy c s
    e2 = ex s^2 + ey c^2 - gxy c s
    g12 = 2 (ey - ex) c s + gxy (c^2 - s^2)
    """
    c = math.cos(math.radians(theta_deg))
    s = math.sin(math.radians(theta_deg))
    c2, s2 = c * c, s * s
    cs = c * s
    e1 = ex * c2 + ey * s2 + gxy * cs
    e2 = ex * s2 + ey * c2 - gxy * cs
    g12 = 2.0 * (ey - ex) * cs + gxy * (c2 - s2)
    return (e1, e2, g12)


def ply_material_stresses(e1, e2, g12, q11, q12, q22, q66):
    """Return (s1, s2, t12), the ply stresses from its material strains:

    s1 = q11 e1 + q12 e2, s2 = q12 e1 + q22 e2, t12 = q66 g12.
    """
    s1 = q11 * e1 + q12 * e2
    s2 = q12 * e1 + q22 * e2
    t12 = q66 * g12
    return (s1, s2, t12)


def tsai_wu_index(s1, s2, t12, xt, xc, yt, yc, s_uv):
    """Return the Tsai-Wu failure index for a ply stress state.

    FI = F1 s1 + F2 s2 + F11 s1^2 + F22 s2^2 + F66 t12^2 + 2 F12 s1 s2
    with F1 = 1/Xt - 1/Xc, F2 = 1/Yt - 1/Yc, F11 = 1/(Xt Xc),
    F22 = 1/(Yt Yc), F66 = 1/S^2 and F12 = -0.5 sqrt(F11 F22).
    FI >= 1.0 marks failure. Raises ValueError for non-positive
    allowables.
    """
    if xt <= 0.0 or xc <= 0.0 or yt <= 0.0 or yc <= 0.0 or s_uv <= 0.0:
        raise ValueError("allowables Xt, Xc, Yt, Yc, S must be positive")
    f1 = 1.0 / xt - 1.0 / xc
    f2 = 1.0 / yt - 1.0 / yc
    f11 = 1.0 / (xt * xc)
    f22 = 1.0 / (yt * yc)
    f66 = 1.0 / (s_uv * s_uv)
    f12 = -0.5 * math.sqrt(f11 * f22)
    return (
        f1 * s1
        + f2 * s2
        + f11 * s1 * s1
        + f22 * s2 * s2
        + f66 * t12 * t12
        + 2.0 * f12 * s1 * s2
    )


def _validate_inputs(plies_deg, q_components, allowables, a_components):
    """Shared shape and positivity checks for the laminate entry points."""
    if not plies_deg:
        raise ValueError("plies_deg must contain at least one ply angle")
    if len(q_components) != 4:
        raise ValueError("q_components must be (q11, q12, q22, q66)")
    if len(allowables) != 5:
        raise ValueError("allowables must be (xt, xc, yt, yc, s_uv)")
    if len(a_components) != 4:
        raise ValueError("a_components must be (a11, a12, a22, a66)")
    q11, q12, q22, q66 = q_components
    if q11 <= 0.0 or q22 <= 0.0 or q66 <= 0.0:
        raise ValueError("q11, q22, q66 must be positive")
    xt, xc, yt, yc, s_uv = allowables
    if xt <= 0.0 or xc <= 0.0 or yt <= 0.0 or yc <= 0.0 or s_uv <= 0.0:
        raise ValueError("allowables Xt, Xc, Yt, Yc, S must be positive")
    a11, a12, a22, a66 = a_components
    if a11 <= 0.0 or a22 <= 0.0 or a66 <= 0.0:
        raise ValueError("a11, a22, a66 compliance entries must be positive")


def ply_failure_indices(plies_deg, q_components, allowables, nx, ny, nxy,
                        a_components):
    """Return the per-ply Tsai-Wu failure indices, list order matching
    plies_deg. Internally calls midplane_strains, the per-ply strain
    transforms, ply_material_stresses and tsai_wu_index. Raises
    ValueError for non-physical inputs (see _validate_inputs).
    """
    _validate_inputs(plies_deg, q_components, allowables, a_components)
    q11, q12, q22, q66 = q_components
    xt, xc, yt, yc, s_uv = allowables
    a11, a12, a22, a66 = a_components
    ex, ey, gxy = midplane_strains(a11, a12, a22, a66, nx, ny, nxy)
    indices = []
    for theta_deg in plies_deg:
        e1, e2, g12 = ply_material_strains(ex, ey, gxy, theta_deg)
        s1, s2, t12 = ply_material_stresses(e1, e2, g12, q11, q12, q22, q66)
        indices.append(tsai_wu_index(s1, s2, t12, xt, xc, yt, yc, s_uv))
    return indices


def first_ply_failure(plies_deg, q_components, allowables, nx, ny, nxy,
                      a_components):
    """Return the first-ply-failure summary dict.

    Evaluates the Tsai-Wu index in every ply and scales the loads to
    the first ply failure: k* = 1 / max(FI). Dict keys:

    - max_fi: highest per-ply Tsai-Wu index
    - critical_ply_index: index into plies_deg of that ply
    - critical_ply_deg: angle of that ply
    - fpf_scale_k: load scale factor k* to first ply failure
    - fpf_load_nx: k* * nx, the FPF resultant for the uniaxial case
    - reserve_factor: k* (alias of fpf_scale_k)

    Raises ValueError for non-physical inputs.
    """
    indices = ply_failure_indices(plies_deg, q_components, allowables,
                                  nx, ny, nxy, a_components)
    max_fi = max(indices)
    critical_ply_index = indices.index(max_fi)
    scale_k = 1.0 / max_fi
    return {
        "max_fi": max_fi,
        "critical_ply_index": critical_ply_index,
        "critical_ply_deg": plies_deg[critical_ply_index],
        "fpf_scale_k": scale_k,
        "fpf_load_nx": scale_k * nx,
        "reserve_factor": scale_k,
    }


def first_ply_failure_load(plies_deg, q_components, allowables, nx, ny,
                           nxy, a_components):
    """Alias of first_ply_failure kept for discoverability. Returns the
    same summary dict.
    """
    return first_ply_failure(plies_deg, q_components, allowables,
                             nx, ny, nxy, a_components)
