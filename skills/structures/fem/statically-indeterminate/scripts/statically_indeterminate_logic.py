"""Elastic redundancy analysis of statically indeterminate beams, continuous
beams and one symmetric no-sway fixed-base portal frame by the classical hand
methods: fixed-end moments of the standard load cases, three-moment
(Clapeyron) interior support moments, moment distribution (Hardy-Cross) with
distribution factors and the 1/2 carry-over factor, slope-deflection member
end moments and joint rotations, and consistent-deformation (force method)
redundant reactions with flexibility coefficients.

Sign conventions (pinned by the leaf spec):
- Beam internal moment M(x) is SAGGING POSITIVE across each span, so hogging
  support moments are negative floats.
- Member end moments in moment distribution and slope-deflection are CLOCKWISE
  POSITIVE on the member end.  For a downward transverse load on a
  both-ends-fixed member the fixed-end moment is hogging at both ends:
  FEM_left = -|M_FE| and FEM_right = +|M_FE|.
- Joint rotations theta are CLOCKWISE POSITIVE.
- The sagging-positive interior support moment M_j equals -end_moments[j-1][1]
  of the span to its left and end_moments[j][0] of the span to its right;
  joint equilibrium makes the two member-end moments at a joint sum to zero.

Pure stdlib, deterministic, no RNG, SI units (m, N, N/m, N m, rad, Pa).
"""


def fixed_end_moment_uniform(w, L):
    """Hogging fixed-end moment magnitude w*L**2/12 at each end of a
    both-ends-fixed prismatic member under a uniform load w over the full
    span.  ValueError on nonpositive w or L."""
    if w <= 0.0:
        raise ValueError("uniform load w must be positive")
    if L <= 0.0:
        raise ValueError("span length L must be positive")
    return w * L ** 2 / 12.0


def fixed_end_moment_central(P, L):
    """Hogging fixed-end moment magnitude P*L/8 at each end of a
    both-ends-fixed prismatic member under a central point load P.
    ValueError on nonpositive P or L."""
    if P <= 0.0:
        raise ValueError("central load P must be positive")
    if L <= 0.0:
        raise ValueError("span length L must be positive")
    return P * L / 8.0


def clapeyron_term_uniform(w, L):
    """Clapeyron load term t = A*xbar/L = w*L**3/24 of the simple-span free
    bending moment diagram under a uniform load w (A = w*L**3/12, xbar = L/2).
    ValueError on nonpositive w or L."""
    if w <= 0.0:
        raise ValueError("uniform load w must be positive")
    if L <= 0.0:
        raise ValueError("span length L must be positive")
    return w * L ** 3 / 24.0


def clapeyron_term_central(P, L):
    """Clapeyron load term t = A*xbar/L = P*L**2/16 of the simple-span free
    bending moment diagram under a central load P (A = P*L**2/8, xbar = L/2).
    ValueError on nonpositive P or L."""
    if P <= 0.0:
        raise ValueError("central load P must be positive")
    if L <= 0.0:
        raise ValueError("span length L must be positive")
    return P * L ** 2 / 16.0


def _load_fem_magnitude(kind, magnitude, length):
    """Both-ends-fixed end moment magnitude of the standard load case:
    uniform w*L**2/12 or central P*L/8.  ValueError on unknown kind,
    nonpositive magnitude or length."""
    if magnitude <= 0.0:
        raise ValueError("load magnitude must be positive")
    if length <= 0.0:
        raise ValueError("span length must be positive")
    if kind == "uniform":
        return fixed_end_moment_uniform(magnitude, length)
    if kind == "central":
        return fixed_end_moment_central(magnitude, length)
    raise ValueError("unknown load kind %r (use 'uniform' or 'central')" % (kind,))


def _clapeyron_term(kind, magnitude, length):
    """Clapeyron load term of the standard load case: uniform w*L**3/24 or
    central P*L**2/16.  ValueError on unknown kind or nonpositive input."""
    if kind == "uniform":
        return clapeyron_term_uniform(magnitude, length)
    if kind == "central":
        return clapeyron_term_central(magnitude, length)
    raise ValueError("unknown load kind %r (use 'uniform' or 'central')" % (kind,))


def _solve_small_system(a, b):
    """Solve the small dense simultaneous set a*x = b by plain elimination
    without pivoting (diagonally dominant in this catalog).  Incidental
    arithmetic of the classical hand methods, never a claimed method."""
    n = len(b)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = m[col][col]
        for r in range(col + 1, n):
            factor = m[r][col] / pivot
            for c in range(col, n + 1):
                m[r][c] -= factor * m[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = m[r][n]
        for c in range(r + 1, n):
            s -= m[r][c] * x[c]
        x[r] = s / m[r][r]
    return x


def three_moment_support_moments(lengths, terms):
    """Interior support moments (sagging positive, hogging negative) of a
    continuous beam on simple end supports from the three-moment (Clapeyron)
    equation M_{j-1}*L_j + 2*M_j*(L_j + L_{j+1}) + M_{j+1}*L_{j+1} =
    -6*(t_j + t_{j+1}) with M_0 = M_n = 0, one load term per span.
    Returns the n - 1 interior support moments of n spans (n >= 2).
    ValueErrors: fewer than two spans; len(terms) != len(lengths); any
    length or term <= 0."""
    n = len(lengths)
    if n < 2:
        raise ValueError("the three-moment equation needs at least two spans")
    if len(terms) != n:
        raise ValueError("one Clapeyron load term per span is required")
    for L in lengths:
        if L <= 0.0:
            raise ValueError("span length must be positive")
    for t in terms:
        if t <= 0.0:
            raise ValueError("Clapeyron load term must be positive")
    k = n - 1
    a = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    for r in range(k):
        j = r + 1
        L_j = lengths[j - 1]
        L_j1 = lengths[j]
        if j >= 2:
            a[r][r - 1] = L_j
        a[r][r] = 2.0 * (L_j + L_j1)
        if j <= n - 2:
            a[r][r + 1] = L_j1
        b[r] = -6.0 * (terms[j - 1] + terms[j])
    return _solve_small_system(a, b)


def support_reactions_continuous(lengths, loads, moments):
    """Upward support reactions (n + 1 of them) of a continuous beam from the
    span rule R_left = R0 + (M_right_end - M_left_end)/L with R0 the
    simple-span reaction (w*L/2 uniform, P/2 central).  loads is one
    (kind, magnitude) pair per span; moments are the interior support
    moments in the sagging-positive convention (0.0 at the simple ends).
    ValueErrors: len(loads) != len(lengths); len(moments) != n - 1; unknown
    kind; magnitude <= 0."""
    n = len(lengths)
    if len(loads) != n:
        raise ValueError("one load pair per span is required")
    if len(moments) != n - 1:
        raise ValueError("one interior support moment per interior support is required")
    full = [0.0] + list(moments) + [0.0]
    reactions = [0.0] * (n + 1)
    for j in range(n):
        kind, magnitude = loads[j]
        L = lengths[j]
        if magnitude <= 0.0:
            raise ValueError("load magnitude must be positive")
        if kind == "uniform":
            r0 = magnitude * L / 2.0
        elif kind == "central":
            r0 = magnitude / 2.0
        else:
            raise ValueError("unknown load kind %r (use 'uniform' or 'central')" % (kind,))
        m_left = full[j]
        m_right = full[j + 1]
        reactions[j] += r0 + (m_right - m_left) / L
        reactions[j + 1] += r0 + (m_left - m_right) / L
    return reactions


def hardycross_beam(lengths, loads, tol=1e-9, max_iter=50000):
    """Member end moments of a continuous beam on simple end supports by the
    moment distribution (Hardy-Cross) method: each member end starts at its
    fixed-end moment, every joint in turn is released by adding the negative
    of its unbalanced sum split by the distribution factors DF_e = k_e/sum(k)
    with k = 4*E*I/L (common E*I, so DFs proportional to 1/L), carrying one
    half of each balancing moment to the far end of the same member; simple
    end supports have DF = 1.  Returns dict with keys 'end_moments' (per span
    the clockwise-positive (M_left, M_right) pair), 'support_moments'
    (sagging-positive interior support moments, -end_moments[j-1][1] for each
    interior support j) and 'iterations'.  ValueErrors: unknown load kind;
    magnitude <= 0.  RuntimeError if max_iter is exhausted without reaching
    tol."""
    n = len(lengths)
    if len(loads) != n:
        raise ValueError("one load pair per span is required")
    end_moments = []
    for i in range(n):
        fem = _load_fem_magnitude(loads[i][0], loads[i][1], lengths[i])
        end_moments.append([-fem, fem])
    iteration = 0
    while True:
        iteration += 1
        if iteration > max_iter:
            raise RuntimeError("moment distribution did not converge within %d iterations" % max_iter)
        largest = 0.0
        for j in range(n + 1):
            if j == 0:
                balance = -end_moments[0][0]
                end_moments[0][0] = 0.0
                end_moments[0][1] += 0.5 * balance
                largest = max(largest, abs(balance))
            elif j == n:
                balance = -end_moments[n - 1][1]
                end_moments[n - 1][1] = 0.0
                end_moments[n - 1][0] += 0.5 * balance
                largest = max(largest, abs(balance))
            else:
                k_left = 1.0 / lengths[j - 1]
                k_right = 1.0 / lengths[j]
                total_k = k_left + k_right
                unbalanced = end_moments[j - 1][1] + end_moments[j][0]
                bal_left = -unbalanced * k_left / total_k
                bal_right = -unbalanced * k_right / total_k
                end_moments[j - 1][1] += bal_left
                end_moments[j][0] += bal_right
                end_moments[j - 1][0] += 0.5 * bal_left
                end_moments[j][1] += 0.5 * bal_right
                largest = max(largest, abs(unbalanced))
        if largest < tol:
            break
    support_moments = [-end_moments[s][1] for s in range(n - 1)]
    return {
        "end_moments": end_moments,
        "support_moments": support_moments,
        "iterations": iteration,
    }


def slope_deflection_member(ei, length, theta_left, theta_right, fem_left, fem_right):
    """Clockwise-positive member end moments (M_left, M_right) from the
    slope-deflection equations M_ab = (2*E*I/L)*(2*theta_a + theta_b) +
    FEM_ab, no sway term and no settlement.  ValueError if ei <= 0 or
    length <= 0."""
    if ei <= 0.0:
        raise ValueError("bending stiffness ei must be positive")
    if length <= 0.0:
        raise ValueError("member length must be positive")
    k = 2.0 * ei / length
    m_left = k * (2.0 * theta_left + theta_right) + fem_left
    m_right = k * (2.0 * theta_right + theta_left) + fem_right
    return (m_left, m_right)


def propped_cantilever(config, q, length, ei):
    """Consistent-deformation (force method) solution of the propped
    cantilever: release the prop B, close the released-cantilever tip
    deflection delta_B against the unit-load flexibility f_BB = L**3/(3*E*I),
    R_B*f_BB = delta_B.  config 'uniform' (q = w in N/m) or 'central'
    (q = P in N at midspan).  Returns dict with keys 'config',
    'fixed_reaction', 'prop_reaction', 'fixed_end_moment' (hogging magnitude
    at the fixed end A), 'prop_rotation' (theta_B, clockwise positive, a
    negative value), 'flexibility', 'released_deflection', 'consistency_
    residual' (R_B*f_BB - delta_B), 'peak_sagging_moment', 'peak_sagging_
    location', 'hardycross_fixed_end_moment' (FEM + the 1/2 carry-over of the
    released end), 'sd_fixed_end_moment' and 'sd_prop_end_moment' (0.0 by the
    roller condition).  ValueErrors: config not in ('uniform', 'central');
    q <= 0; length <= 0; ei <= 0."""
    if config not in ("uniform", "central"):
        raise ValueError("config must be 'uniform' or 'central'")
    if q <= 0.0:
        raise ValueError("load q must be positive")
    if length <= 0.0:
        raise ValueError("span length must be positive")
    if ei <= 0.0:
        raise ValueError("bending stiffness ei must be positive")
    if config == "uniform":
        fem = fixed_end_moment_uniform(q, length)
        prop = 3.0 * q * length / 8.0
        fixed_r = 5.0 * q * length / 8.0
        released = q * length ** 4 / (8.0 * ei)
        peak = 9.0 * q * length ** 2 / 128.0
        peak_x = 5.0 * length / 8.0
    else:
        fem = fixed_end_moment_central(q, length)
        prop = 5.0 * q / 16.0
        fixed_r = 11.0 * q / 16.0
        released = 5.0 * q * length ** 3 / (48.0 * ei)
        peak = 5.0 * q * length / 32.0
        peak_x = length / 2.0
    moment = fem + fem / 2.0
    theta_b = -fem * length / (4.0 * ei)
    flexibility = length ** 3 / (3.0 * ei)
    residual = prop * flexibility - released
    return {
        "config": config,
        "fixed_reaction": fixed_r,
        "prop_reaction": prop,
        "fixed_end_moment": moment,
        "prop_rotation": theta_b,
        "flexibility": flexibility,
        "released_deflection": released,
        "consistency_residual": residual,
        "peak_sagging_moment": peak,
        "peak_sagging_location": peak_x,
        "hardycross_fixed_end_moment": moment,
        "sd_fixed_end_moment": moment,
        "sd_prop_end_moment": 0.0,
    }


def _frame_sd_moments(ei, span, height, theta_b, theta_c, fem_mag):
    """Closed-form member end moments of the symmetric fixed-base frame from
    the slope-deflection member equations evaluated at the given joint
    rotations: m_ab/m_ba on the left column (A fixed base to B top), m_bc/m_cb
    on the beam (B to C) and m_cd/m_dc on the right column (C top to D fixed
    base), all clockwise positive."""
    col_left = slope_deflection_member(ei, height, 0.0, theta_b, 0.0, 0.0)
    beam = slope_deflection_member(ei, span, theta_b, theta_c, -fem_mag, fem_mag)
    col_right = slope_deflection_member(ei, height, theta_c, 0.0, 0.0, 0.0)
    return {
        "m_ab": col_left[0],
        "m_ba": col_left[1],
        "m_bc": beam[0],
        "m_cb": beam[1],
        "m_cd": col_right[0],
        "m_dc": col_right[1],
    }


def portal_frame_fixed_base(total_load, span, height, ei, tol=1e-9):
    """Symmetric fixed-base portal frame under a central beam load W
    (total_load), no sidesway by symmetry: moment distribution (Hardy-Cross)
    over the two top joints B and C with the fixed bases A and D never
    released, column and beam stiffnesses 4*E*I/h and 4*E*I/Lb, carry-over
    1/2.  Returns dict with keys 'beam_end_moment_magnitude',
    'column_top_moment_magnitude', 'column_base_moment_magnitude' (the
    carry-over half of the top moment), 'beam_midspan_sagging_moment',
    'theta_B', 'theta_C', 'reaction_vertical_each_base',
    'reaction_horizontal_each_base', 'hardycross' (member end moments keyed
    ('col1', 'a'/'b'), ('beam', 'a'/'b'), ('col2', 'a'/'b'), clockwise
    positive), 'sd' (closed-form member end moments m_ab, m_ba, m_bc, m_cb,
    m_cd, m_dc) and 'iterations'.  ValueError if any of total_load, span,
    height, ei <= 0.  RuntimeError if the cycle does not converge."""
    if total_load <= 0.0:
        raise ValueError("central beam load must be positive")
    if span <= 0.0:
        raise ValueError("beam span must be positive")
    if height <= 0.0:
        raise ValueError("column height must be positive")
    if ei <= 0.0:
        raise ValueError("bending stiffness ei must be positive")
    fem_mag = fixed_end_moment_central(total_load, span)
    k_col = 4.0 * ei / height
    k_beam = 4.0 * ei / span
    df_col = k_col / (k_col + k_beam)
    df_beam = k_beam / (k_col + k_beam)
    moments = {
        ("col1", "a"): 0.0,
        ("col1", "b"): 0.0,
        ("beam", "a"): -fem_mag,
        ("beam", "b"): fem_mag,
        ("col2", "a"): 0.0,
        ("col2", "b"): 0.0,
    }
    max_iter = 50000
    iteration = 0
    while True:
        iteration += 1
        if iteration > max_iter:
            raise RuntimeError("frame moment distribution did not converge")
        largest = 0.0
        unbalanced = moments[("col1", "b")] + moments[("beam", "a")]
        bal_col = -unbalanced * df_col
        bal_beam = -unbalanced * df_beam
        moments[("col1", "b")] += bal_col
        moments[("beam", "a")] += bal_beam
        moments[("col1", "a")] += 0.5 * bal_col
        moments[("beam", "b")] += 0.5 * bal_beam
        largest = max(largest, abs(unbalanced))
        unbalanced = moments[("beam", "b")] + moments[("col2", "a")]
        bal_beam = -unbalanced * df_beam
        bal_col = -unbalanced * df_col
        moments[("beam", "b")] += bal_beam
        moments[("col2", "a")] += bal_col
        moments[("beam", "a")] += 0.5 * bal_beam
        moments[("col2", "b")] += 0.5 * bal_col
        largest = max(largest, abs(unbalanced))
        if largest < tol:
            break
    beam_end = abs(moments[("beam", "a")])
    theta_b = fem_mag / (4.0 * ei / height + 2.0 * ei / span)
    theta_c = -theta_b
    return {
        "beam_end_moment_magnitude": beam_end,
        "column_top_moment_magnitude": abs(moments[("col1", "b")]),
        "column_base_moment_magnitude": abs(moments[("col1", "a")]),
        "beam_midspan_sagging_moment": total_load * span / 4.0 - beam_end,
        "theta_B": theta_b,
        "theta_C": theta_c,
        "reaction_vertical_each_base": total_load / 2.0,
        "reaction_horizontal_each_base": 0.0,
        "hardycross": moments,
        "sd": _frame_sd_moments(ei, span, height, theta_b, theta_c, fem_mag),
        "iterations": iteration,
    }


def slope_deflection_frame_solve(total_load, span, height, ei):
    """Direct cross-check of the symmetric fixed-base frame: solve the two
    joint-equilibrium slope-deflection equations
    (4*E*I/Lb + 4*E*I/h)*theta_B + (2*E*I/Lb)*theta_C = +W*Lb/8 and
    (2*E*I/Lb)*theta_B + (4*E*I/Lb + 4*E*I/h)*theta_C = -W*Lb/8 for the joint
    rotations, then evaluate the member end moments.  Returns dict with keys
    'theta_B', 'theta_C', 'det' and 'moments' (m_ab, m_ba, m_bc, m_cb, m_cd,
    m_dc).  Verification cross-check only, never a claimed method of the
    leaf.  ValueError if any of total_load, span, height, ei <= 0."""
    if total_load <= 0.0:
        raise ValueError("central beam load must be positive")
    if span <= 0.0:
        raise ValueError("beam span must be positive")
    if height <= 0.0:
        raise ValueError("column height must be positive")
    if ei <= 0.0:
        raise ValueError("bending stiffness ei must be positive")
    fem_mag = fixed_end_moment_central(total_load, span)
    diag = 4.0 * ei / span + 4.0 * ei / height
    off = 2.0 * ei / span
    theta_b, theta_c = _solve_small_system([[diag, off], [off, diag]], [fem_mag, -fem_mag])
    return {
        "theta_B": theta_b,
        "theta_C": theta_c,
        "det": diag * diag - off * off,
        "moments": _frame_sd_moments(ei, span, height, theta_b, theta_c, fem_mag),
    }
