#!/usr/bin/env python3
"""2D truss analysis by the direct stiffness method (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25 and mmpsd:
gated false, reference-only): a pin-jointed truss is a set of axial
bar elements connected at frictionless pins. Each bar of Young's
modulus E, area A and length L has a 4x4 element stiffness matrix in
global coordinates. The element matrices are assembled into a global
stiffness matrix K over the 2*N nodal degrees of freedom
[u_x0, u_y0, u_x1, u_y1, ...]. Support conditions fix some degrees of
freedom; the remaining free system K_red u_free = F_red is solved for
the nodal displacements, then member axial forces and support
reactions are recovered. Only the Python standard library is used;
the linear solve is a dense Gaussian elimination with partial
pivoting implemented here (no numpy).

Worked anchor (verified by running this module): the symmetric
three-bar truss with nodes (0,0), (4,3), (8,0) m, bars 0-1, 1-2 and
0-2 of E = 200 GPa, A = 1e-3 m^2, a downward load of 100 kN at the
apex node 1, pin at node 0 (x and y fixed) and a vertical roller at
node 2 (y fixed) gives displacements [0, 0, 1.3333e-3, -5.25e-3,
2.6667e-3, 0] m, member forces [-83.333e3, -83.333e3, +66.667e3] N
(the two inclined bars compress, the bottom bar carries tension) and
reactions R_0y = +50e3 N, R_2y = +50e3 N with R_0x = 0.

Units: SI throughout. Coordinates in m, E in Pa, A in m^2, forces in
N, displacements in m. One unit convention, no mixing.
"""

import math

_EPS = 1e-13


def _check_finite(value, name):
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return float(value)


def _axis_index(axis):
    if axis == "x":
        return 0
    if axis == "y":
        return 1
    raise ValueError("axis must be 'x' or 'y', got %r" % (axis,))


def _dof(node, axis):
    """Global degree-of-freedom index for node (0-based) and axis."""
    return 2 * node + _axis_index(axis)


def gaussian_elimination(A, b):
    """Solve the dense linear system A x = b by Gaussian elimination.

    Uses partial pivoting on the augmented matrix; returns x as a
    list of floats. A must be a square list of lists of numbers and b
    a list of the same length. Raises ValueError when A is singular
    (or numerically rank-deficient), including systems with no unique
    solution such as an unrestrained mechanism.

    Anchor: A = [[2, 1, 1], [1, 3, 2], [1, 0, 0]], b = [7, 13, 1]
    gives x = [1, 2, 3].
    """
    if not isinstance(A, list) or not A:
        raise ValueError("A must be a non-empty square matrix (list of lists)")
    n = len(A)
    if any(not isinstance(row, list) or len(row) != n for row in A):
        raise ValueError("A must be a square matrix (got %d rows)" % n)
    if not isinstance(b, list) or len(b) != n:
        raise ValueError("b must be a list of length %d matching A" % n)
    scale = 1.0
    for row in A:
        for v in row:
            scale = max(scale, abs(_check_finite(v, "matrix entry")))
    for v in b:
        scale = max(scale, abs(_check_finite(v, "right-hand side entry")))
    M = [row[:] for row in A]
    rhs = b[:]
    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[pivot_row][col]) <= _EPS * scale:
            raise ValueError(
                "singular or rank-deficient matrix: no unique solution"
            )
        if pivot_row != col:
            M[col], M[pivot_row] = M[pivot_row], M[col]
            rhs[col], rhs[pivot_row] = rhs[pivot_row], rhs[col]
        pivot = M[col][col]
        for r in range(col + 1, n):
            factor = M[r][col] / pivot
            if factor == 0.0:
                continue
            for c in range(col, n):
                M[r][c] -= factor * M[col][c]
            rhs[r] -= factor * rhs[col]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        acc = rhs[r]
        for c in range(r + 1, n):
            acc -= M[r][c] * x[c]
        x[r] = acc / M[r][r]
    return x


def element_stiffness_matrix(E, A, L, theta_deg):
    """Element stiffness matrix (4x4, global coordinates) of one bar.

    Bar of modulus E (Pa), area A (m^2), length L (m) at orientation
    theta_deg measured counterclockwise from the global +x axis, with
    local axis pointing from its first node to its second. With
    c = cos(theta), s = sin(theta):

        k = (E A / L) * [[ c^2,  c s, -c^2, -c s],
                         [ c s,  s^2, -c s, -s^2],
                         [-c^2, -c s,  c^2,  c s],
                         [-c s, -s^2,  c s,  s^2]]

    Returns a 4x4 list of lists. E and A must be positive, L must be
    positive; anything else raises ValueError.

    Anchor: E = 200 GPa, A = 1e-3 m^2, L = 1 m, theta = 0 deg gives
    k = 2e8 * [[1, 0, -1, 0], [0, 0, 0, 0], [-1, 0, 1, 0], [0, 0, 0, 0]].
    """
    E = _check_finite(E, "E")
    A = _check_finite(A, "A")
    L = _check_finite(L, "L")
    theta_deg = _check_finite(theta_deg, "theta_deg")
    if E <= 0.0:
        raise ValueError("Young's modulus E must be positive (Pa), got %r" % (E,))
    if A <= 0.0:
        raise ValueError("cross-section area A must be positive (m^2), got %r" % (A,))
    if L <= 0.0:
        raise ValueError("bar length L must be positive (m), got %r" % (L,))
    theta = math.radians(theta_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    scale = E * A / L
    return [
        [scale * c * c, scale * c * s, -scale * c * c, -scale * c * s],
        [scale * c * s, scale * s * s, -scale * c * s, -scale * s * s],
        [-scale * c * c, -scale * c * s, scale * c * c, scale * c * s],
        [-scale * c * s, -scale * s * s, scale * c * s, scale * s * s],
    ]


def _check_model(nodes, elements):
    """Validate node and element geometry; returns (n_nodes, K-scale hint)."""
    if not isinstance(nodes, list) or len(nodes) < 2:
        raise ValueError("nodes must be a list of at least 2 (x, y) coordinates")
    coords = []
    for idx, pt in enumerate(nodes):
        if not isinstance(pt, (tuple, list)) or len(pt) != 2:
            raise ValueError("node %d must be an (x, y) pair, got %r" % (idx, pt))
        x = _check_finite(pt[0], "node %d x" % idx)
        y = _check_finite(pt[1], "node %d y" % idx)
        coords.append((x, y))
    if not isinstance(elements, list) or not elements:
        raise ValueError("elements must be a non-empty list of (i, j, E, A)")
    n = len(coords)
    for idx, el in enumerate(elements):
        if not isinstance(el, (tuple, list)) or len(el) != 4:
            raise ValueError(
                "element %d must be (i, j, E, A), got %r" % (idx, el)
            )
        i, j, E, A = el
        if not isinstance(i, int) or not isinstance(j, int):
            raise ValueError(
                "element %d node indices must be integers, got %r" % (idx, (i, j))
            )
        if not (0 <= i < n and 0 <= j < n):
            raise ValueError(
                "element %d node indices %r out of range 0..%d" % (idx, (i, j), n - 1)
            )
        if i == j:
            raise ValueError("element %d joins a node to itself (i == j == %d)" % (idx, i))
        E = _check_finite(E, "element %d E" % idx)
        A = _check_finite(A, "element %d A" % idx)
        if E <= 0.0:
            raise ValueError("element %d E must be positive (Pa), got %r" % (idx, E))
        if A <= 0.0:
            raise ValueError("element %d A must be positive (m^2), got %r" % (idx, A))
        dx = coords[j][0] - coords[i][0]
        dy = coords[j][1] - coords[i][1]
        L = math.hypot(dx, dy)
        if L <= 0.0:
            raise ValueError(
                "element %d nodes %d and %d share the same coordinates"
                % (idx, i, j)
            )
    return n, coords


def assemble_global_stiffness(nodes, elements):
    """Assemble the 2N x 2N global stiffness matrix.

    nodes is a list of (x, y) coordinates in m (node index = list
    position, 0-based); elements is a list of (i, j, E, A) bars with
    0-based node indices, E in Pa and A in m^2. Degrees of freedom are
    ordered [u_x0, u_y0, u_x1, u_y1, ...]. Returns K as a 2N x 2N
    list of lists. Invalid geometry or material data raises ValueError.
    """
    n, _ = _check_model(nodes, elements)
    size = 2 * n
    K = [[0.0] * size for _ in range(size)]
    for i, j, E, A in elements:
        xi, yi = nodes[i]
        xj, yj = nodes[j]
        theta = math.degrees(math.atan2(yj - yi, xj - xi))
        L = math.hypot(xj - xi, yj - yi)
        k4 = element_stiffness_matrix(E, A, L, theta)
        dofs = [2 * i, 2 * i + 1, 2 * j, 2 * j + 1]
        for r in range(4):
            for c in range(4):
                K[dofs[r]][dofs[c]] += k4[r][c]
    return K


def solve_displacements(K, F, constraints):
    """Solve for the nodal displacements after applying support conditions.

    K is the assembled 2N x 2N global stiffness matrix (list of
    lists), F is the nodal load vector of length 2N ordered
    [F_x0, F_y0, F_x1, F_y1, ...], and constraints is a list of
    (node, axis) pairs with axis 'x' or 'y' that are fixed to zero
    displacement. The constrained degrees of freedom are removed, the
    reduced system is solved by gaussian_elimination, and the full
    displacement vector (constrained entries 0.0) is returned.

    Raises ValueError for inconsistent sizes, invalid axes, out-of-range
    nodes, and singular reduced systems (mechanisms, e.g. a structure
    that is not sufficiently restrained).
    """
    if not isinstance(K, list) or not K:
        raise ValueError("K must be a non-empty square matrix (list of lists)")
    size = len(K)
    if any(not isinstance(row, list) or len(row) != size for row in K):
        raise ValueError("K must be a square matrix (got %d rows)" % size)
    if not isinstance(F, list) or len(F) != size:
        raise ValueError("F must be a list of length %d matching K" % size)
    for v in F:
        _check_finite(v, "load entry")
    n_nodes = size // 2
    fixed = set()
    for item in constraints:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(
                "each constraint must be a (node, axis) pair, got %r" % (item,)
            )
        node, axis = item
        if not isinstance(node, int) or not (0 <= node < n_nodes):
            raise ValueError(
                "constraint node %r out of range 0..%d" % (node, n_nodes - 1)
            )
        fixed.add(_dof(node, axis))
    free = [d for d in range(size) if d not in fixed]
    u = [0.0] * size
    if not free:
        return u  # every degree of freedom constrained: trivial solution
    K_red = [[K[r][c] for c in free] for r in free]
    F_red = [F[r] for r in free]
    u_free = gaussian_elimination(K_red, F_red)
    for dof, value in zip(free, u_free):
        u[dof] = value
    return u


def member_forces(nodes, elements, displacements):
    """Axial force in every bar, tension positive.

    For element (i, j, E, A) with direction cosines c, s the axial
    force is F = (E A / L) * ((u_xj - u_xi) c + (u_yj - u_yi) s), the
    bar extension times its axial stiffness. Positive values are
    tension, negative values compression. displacements is the full
    length-2N vector from solve_displacements. Returns a list of
    forces (N), one per element, in element order.
    """
    n, _ = _check_model(nodes, elements)
    if not isinstance(displacements, list) or len(displacements) != 2 * n:
        raise ValueError(
            "displacements must be a list of length %d (2 per node)" % (2 * n,)
        )
    for v in displacements:
        _check_finite(v, "displacement entry")
    forces = []
    for i, j, E, A in elements:
        xi, yi = nodes[i]
        xj, yj = nodes[j]
        L = math.hypot(xj - xi, yj - yi)
        c = (xj - xi) / L
        s = (yj - yi) / L
        elongation = (
            (displacements[2 * j] - displacements[2 * i]) * c
            + (displacements[2 * j + 1] - displacements[2 * i + 1]) * s
        )
        forces.append(E * A / L * elongation)
    return forces


def reaction_forces(nodes, elements, displacements, constraints):
    """Support reactions at the constrained degrees of freedom.

    With the full displacement vector known, the reaction at a
    constrained degree of freedom d is R_d = sum_c K[d][c] u_c, the
    force the support exerts on the structure (positive in the +x or
    +y direction). Returns a dict mapping (node, axis) to the reaction
    force in N for every constraint.
    """
    n, _ = _check_model(nodes, elements)
    if not isinstance(displacements, list) or len(displacements) != 2 * n:
        raise ValueError(
            "displacements must be a list of length %d (2 per node)" % (2 * n,)
        )
    K = assemble_global_stiffness(nodes, elements)
    reactions = {}
    for item in constraints:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(
                "each constraint must be a (node, axis) pair, got %r" % (item,)
            )
        node, axis = item
        if not isinstance(node, int) or not (0 <= node < n):
            raise ValueError("constraint node %r out of range 0..%d" % (node, n - 1))
        d = _dof(node, axis)
        reactions[(node, axis)] = sum(K[d][c] * displacements[c] for c in range(2 * n))
    return reactions


def truss_analysis(nodes, elements, loads, constraints):
    """Full 2D truss solve: displacements, member forces, reactions.

    Convenience wrapper over assemble_global_stiffness,
    solve_displacements, member_forces and reaction_forces. loads is a
    dict mapping (node, axis) to a force in N (positive along +x/+y),
    constraints a list of (node, axis) fixed supports. Returns a dict
    with keys "displacements" (length-2N list), "member_forces" (list
    per element, tension positive) and "reactions" (dict keyed by
    (node, axis)). Invalid input raises ValueError.

    Anchor: nodes [(0,0), (4,3), (8,0)], elements
    [(0,1,200e9,1e-3), (1,2,200e9,1e-3), (0,2,200e9,1e-3)], loads
    {(1, 'y'): -100e3}, constraints [(0, 'x'), (0, 'y'), (2, 'y')]
    gives displacements [0, 0, 1.3333e-3, -5.25e-3, 2.6667e-3, 0] m,
    member forces [-83.333e3, -83.333e3, +66.667e3] N and reactions
    {(0,'x'): 0.0, (0,'y'): 50e3, (2,'y'): 50e3} N.
    """
    n, _ = _check_model(nodes, elements)
    if not isinstance(loads, dict):
        raise ValueError("loads must be a dict mapping (node, axis) to force (N)")
    F = [0.0] * (2 * n)
    for key, value in loads.items():
        if not isinstance(key, (tuple, list)) or len(key) != 2:
            raise ValueError("each load key must be a (node, axis) pair, got %r" % (key,))
        node, axis = key
        if not isinstance(node, int) or not (0 <= node < n):
            raise ValueError("load node %r out of range 0..%d" % (node, n - 1))
        F[_dof(node, axis)] = _check_finite(value, "load force")
    if not isinstance(constraints, list) or not constraints:
        raise ValueError(
            "constraints must be a non-empty list of (node, axis) fixed supports"
        )
    K = assemble_global_stiffness(nodes, elements)
    u = solve_displacements(K, F, constraints)
    return {
        "displacements": u,
        "member_forces": member_forces(nodes, elements, u),
        "reactions": reaction_forces(nodes, elements, u, constraints),
    }
