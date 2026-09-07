"""Squire-Young section profile-drag logic.

Pure Python stdlib (math only), closed form, deterministic. Implements the
Squire-Young trailing-edge momentum-state to profile-drag mapping for a
two-dimensional body or airfoil section: c_d,p = 2*(theta_TE/c)*
(U_TE/U_inf)**((H_TE+5)/2), the laminar integral growth of the momentum
thickness to the trailing edge, and the fully laminar one-call chain.
Incompressible clean 2-D attached flow only, one surface of the section.

SI units: x in m, U in m/s, nu in m2/s, theta in m, c_d,p dimensionless.
"""

import math

# Module constants (fixed numbers, family values).
NU_AIR = 1.46e-5            # air kinematic viscosity at standard conditions, m2/s
H_TE = 1.4                  # default trailing-edge shape factor H = delta*/theta
LAMINAR_THETA_C = 0.664     # Blasius momentum-thickness constant, theta = 0.664*x/sqrt(Re_x)
BLASIUS_DRAG_C = 1.328      # 2*0.664, laminar flat-plate drag constant of 1.328/sqrt(Re_c)
GROWTH_C = LAMINAR_THETA_C ** 2.0   # 0.440896, laminar integral-growth constant


def trailing_edge_factor(u_te, u_inf, h_te=H_TE):
    """Edge-velocity wake-transfer factor (U_TE/U_inf)**((H_TE+5)/2).

    Workflow steps 3 and 4: the edge-velocity-ratio exponent that carries
    the trailing-edge momentum state to the far-wake profile-drag level.
    Unity at U_TE = U_inf for any shape factor (flat plate), below unity
    for a decelerated attached TE edge flow.
    """
    if u_te <= 0.0:
        raise ValueError("u_te must be positive, got %r" % (u_te,))
    if u_inf <= 0.0:
        raise ValueError("u_inf must be positive, got %r" % (u_inf,))
    if h_te <= 1.0:
        raise ValueError("h_te must exceed 1.0 (attached layer), got %r" % (h_te,))
    return (u_te / u_inf) ** ((h_te + 5.0) / 2.0)


def squire_young_profile_drag(theta_te, chord, u_te, u_inf, h_te=H_TE):
    """Section profile-drag coefficient 2*(theta_TE/c)*factor, one surface.

    Workflow step 5: maps the trailing-edge momentum state through the
    squire-young-formula to the section profile-drag-coefficient; at
    U_TE = U_inf it reduces to the momentum-integral value 2*theta_TE/c.
    """
    if theta_te <= 0.0:
        raise ValueError("theta_te must be positive, got %r" % (theta_te,))
    if chord <= 0.0:
        raise ValueError("chord must be positive, got %r" % (chord,))
    factor = trailing_edge_factor(u_te, u_inf, h_te)
    return 2.0 * (theta_te / chord) * factor


def momentum_thickness_at_te(xs, ues, nu):
    """Trailing-edge momentum thickness from the laminar integral growth.

    Workflow step 6 (the laminar integral-growth traverse): theta_TE^2 =
    GROWTH_C * nu / U_TE**6 * integral_0^c Ue(x)**5 dx with the cumulative
    trapezoid rule over the supplied stations. The segment from the leading
    edge x = 0 to the first station keeps Ue at its first-station value, so
    a constant-velocity plate closes to the Blasius momentum thickness
    exactly. Returns theta_TE in m, evaluated at the last station.
    """
    n = len(xs)
    if n < 2:
        raise ValueError("at least two stations required, got %d" % n)
    if len(ues) != n:
        raise ValueError("xs and ues lengths differ: %d vs %d" % (n, len(ues)))
    if xs[0] < 0.0:
        raise ValueError("leading station below zero, got %r" % (xs[0],))
    if nu <= 0.0:
        raise ValueError("nu must be positive, got %r" % (nu,))
    for i in range(n):
        if ues[i] <= 0.0:
            raise ValueError("edge velocity must be positive at station %d, got %r" % (i, ues[i]))
        if i > 0 and xs[i] <= xs[i - 1]:
            raise ValueError("stations must be strictly increasing at index %d" % i)
    # Trapezoid integral of Ue^5 over x in [0, xs[-1]], LE-gap segment at
    # the first-station edge velocity so the constant-velocity plate is exact.
    integral = (xs[0] - 0.0) * ues[0] ** 5.0
    for i in range(1, n):
        integral += 0.5 * (ues[i] ** 5.0 + ues[i - 1] ** 5.0) * (xs[i] - xs[i - 1])
    u_te = ues[-1]
    return math.sqrt(GROWTH_C * nu * integral / u_te ** 6.0)


def fully_laminar_profile_drag(xs, ues, nu, chord, u_inf, h_te=H_TE):
    """One-call fully laminar chain: traverse to section profile drag.

    Workflow steps 6 and 7: grows theta to the trailing edge on the
    laminar integral-growth relation (momentum_thickness_at_te), reads
    U_TE as the last-station edge velocity, and applies the squire-young-
    formula mapping with the default or supplied trailing-edge shape
    factor. Returns the section profile-drag coefficient, one surface.
    """
    if chord <= 0.0:
        raise ValueError("chord must be positive, got %r" % (chord,))
    if u_inf <= 0.0:
        raise ValueError("u_inf must be positive, got %r" % (u_inf,))
    theta_te = momentum_thickness_at_te(xs, ues, nu)
    return squire_young_profile_drag(theta_te, chord, ues[-1], u_inf, h_te)
