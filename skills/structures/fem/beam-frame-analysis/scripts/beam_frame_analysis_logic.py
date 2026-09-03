"""Two-dimensional rigid-jointed frame analysis with the Euler-Bernoulli beam element.

Pure Python standard library implementation (no numpy). Units are SI
throughout: coordinates and lengths in m, E in Pa, A in m^2, I in m^4,
forces in N, moments in N m, displacements in m, rotations in rad.

Model
-----
Each node has three degrees of freedom (u, v, theta) with the global
dof index of node n given by 3*n + 0 for u, 3*n + 1 for v and
3*n + 2 for theta.  A rigid-jointed frame member carries axial force,
shear and bending moment: the 6x6 local element stiffness over
(u1, v1, theta1, u2, v2, theta2) is the sum of the axial bar terms
E*A/L on (u1, u2) and the Euler-Bernoulli beam block on
(v1, theta1, v2, theta2),

    k = (E*I/L^3) * [[ 12, -6L, -12, -6L],
                     [-6L,  4L^2,  6L,  2L^2],
                     [-12,  6L,  12,  6L],
                     [-6L,  2L^2,  6L,  4L^2]],

the standard symmetric beam element matrix of the textbook fixed-end
action convention in which a cantilever with a downward tip load P
returns end actions (V1, M1) = (+P, -P*L) at the fixed end.  The
convention keeps the element end action vector q = k * d_local equal to
the forces and moments the joints apply to the element ends: shear is
positive along the local +y axis and end moments are positive in the
rotation scalar convention below (clockwise positive, equivalently the
beam sign convention of M = E*I*v'' with v positive up).  Under it the
cantilever tip values come out v2 = -P*L^3/(3*E*I) and
theta2 = +P*L^2/(2*E*I), and the fixed-end reactions are
(R_v0, R_m0) = (+P, -P*L), which reproduces the wave-28 spec anchors
exactly (tip deflection magnitude 0.0095238 m, rotation magnitude
0.0071429 rad, vertical reaction +1000 N, end moment -2000 N m for
P = 1000 N on E = 70 GPa, I = 4e-6 m^4, L = 2 m).  The scalar rotation
dof is invariant under the proper rotations used to orient members, so
the same transformation matrix is used for every member.

Orientation
-----------
For a member from node i (xi, yi) to node j (xj, yj) the member axis
angle is alpha = atan2(yj - yi, xj - xi) from the global +x axis, with
c = cos(alpha), s = sin(alpha).  The 6x6 block transformation
T = diag(lambda, lambda) with lambda = [[c, s, 0], [-s, c, 0],
[0, 0, 1]] maps global to local displacements (d_local = T d_global)
and the global element stiffness is k_global = T^T k_local T.

Support conditions
------------------
Fixed degrees of freedom are eliminated from the global system and the
reduced system is solved with a compact Gaussian elimination with
partial pivoting.  Support reactions at a fixed dof d are
R_d = sum_j K[d][j] * u[j] - applied_load[d], the action the support
exerts on the structure.  Member end actions are recovered per element
as q_local = k_local * d_local and reported in the local frame as
(n1, v1, m1, n2, v2, m2).

Every function raises ValueError on non-physical input (non-positive E,
A, I, L, unknown node indices, zero-length members, singular reduced
systems).
"""

import math

#: Local degree of freedom offset of each dof name within a node.
DOF_INDEX = {"u": 0, "v": 1, "theta": 2}

#: Relative pivot floor for the elimination solver.
PIVOT_TOL = 1e-12

#: Absolute tolerance (N) for the global force equilibrium check.
EQ_TOL = 1e-6


def element_stiffness_local(E, A, I, L):
    """Return the 6x6 local beam element stiffness over (u1, v1, theta1, u2, v2, theta2).

    The axial block is E*A/L on (u1, u2); the bending block is the
    standard Euler-Bernoulli matrix documented in the module docstring.
    Raises ValueError when E, A, I or L is not positive.
    """
    if E <= 0.0:
        raise ValueError("E must be positive")
    if A <= 0.0:
        raise ValueError("A must be positive")
    if I <= 0.0:
        raise ValueError("I must be positive")
    if L <= 0.0:
        raise ValueError("L must be positive")
    ka = E * A / L
    a = 12.0 * E * I / L ** 3
    b = 6.0 * E * I / L ** 2
    c4 = 4.0 * E * I / L
    c2 = 2.0 * E * I / L
    k = [[0.0] * 6 for _ in range(6)]
    # Axial block on (u1, u2).
    k[0][0] = ka
    k[0][3] = -ka
    k[3][0] = -ka
    k[3][3] = ka
    # Bending block on local dofs 1, 2, 4, 5 -> (v1, theta1, v2, theta2).
    block = (
        (a, -b, -a, -b),
        (-b, c4, b, c2),
        (-a, b, a, b),
        (-b, c2, b, c4),
    )
    local = (1, 2, 4, 5)
    for r, row in enumerate(block):
        for col, value in enumerate(row):
            k[local[r]][local[col]] = value
    return k


def rotation_matrix(angle_rad):
    """Return the 6x6 block transformation T = diag(lambda, lambda).

    lambda = [[c, s, 0], [-s, c, 0], [0, 0, 1]] with c = cos(angle) and
    s = sin(angle) maps global to local displacements, so
    k_global = T^T k_local T.  T is orthogonal: T T^T = T^T T = I.
    """
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    lam = ((c, s, 0.0), (-s, c, 0.0), (0.0, 0.0, 1.0))
    t = [[0.0] * 6 for _ in range(6)]
    for r in range(3):
        for col in range(3):
            t[r][col] = lam[r][col]
            t[r + 3][col + 3] = lam[r][col]
    return t


def element_stiffness_global(E, A, I, L, angle_rad):
    """Return the 6x6 element stiffness rotated into the global frame.

    k_global = T(angle)^T * k_local * T(angle).  Raises ValueError when
    E, A, I or L is not positive.
    """
    k_local = element_stiffness_local(E, A, I, L)
    t = rotation_matrix(angle_rad)
    # k_global = T^T k_local T, built with explicit matrix products.
    ndof = 6
    temp = [[0.0] * ndof for _ in range(ndof)]
    for r in range(ndof):
        for col in range(ndof):
            acc = 0.0
            for m in range(ndof):
                acc += t[m][r] * k_local[m][col]
            temp[r][col] = acc
    kg = [[0.0] * ndof for _ in range(ndof)]
    for r in range(ndof):
        for col in range(ndof):
            acc = 0.0
            for m in range(ndof):
                acc += temp[r][m] * t[m][col]
            kg[r][col] = acc
    return kg


def _member_geometry(nodes, element):
    """Return (L, angle_rad) of an element from the node coordinates.

    Raises ValueError for an unknown node index or a zero-length member.
    """
    i = element["i"]
    j = element["j"]
    if i < 0 or i >= len(nodes) or j < 0 or j >= len(nodes):
        raise ValueError("unknown node index in element")
    dx = nodes[j][0] - nodes[i][0]
    dy = nodes[j][1] - nodes[i][1]
    length = math.hypot(dx, dy)
    if length <= 0.0:
        raise ValueError("zero length member")
    return length, math.atan2(dy, dx)


def _default_dof_map(node_count):
    """Return {(node_index, dof_name): global dof index} for node_count nodes."""
    dof_map = {}
    for node in range(node_count):
        for name, offset in DOF_INDEX.items():
            dof_map[(node, name)] = 3 * node + offset
    return dof_map


def assemble(nodes, elements, dof_map=None):
    """Assemble the global stiffness matrix from nodes and elements.

    nodes is a list of (x, y); elements is a list of dicts {i, j, E, A,
    I} with 0-based node indices.  When dof_map is None the standard map
    {(node, name): 3*node + offset} is built and returned.  Returns
    {"K": K, "dof_map": dof_map}.  Raises ValueError for an unknown node
    index, a zero-length member, or a duplicate dof assignment in a
    caller-supplied dof_map.
    """
    if dof_map is None:
        dof_map = _default_dof_map(len(nodes))
    assigned = {}
    for key, value in dof_map.items():
        if value in assigned and assigned[value] != key:
            raise ValueError("duplicate dof in dof_map")
        assigned[value] = key
    ndof = 3 * len(nodes)
    k_full = [[0.0] * ndof for _ in range(ndof)]
    for element in elements:
        length, angle = _member_geometry(nodes, element)
        i = element["i"]
        j = element["j"]
        kg = element_stiffness_global(
            element["E"], element["A"], element["I"], length, angle
        )
        dofs = (
            dof_map[(i, "u")],
            dof_map[(i, "v")],
            dof_map[(i, "theta")],
            dof_map[(j, "u")],
            dof_map[(j, "v")],
            dof_map[(j, "theta")],
        )
        for r in range(6):
            for col in range(6):
                k_full[dofs[r]][dofs[col]] += kg[r][col]
    return {"K": k_full, "dof_map": dof_map}


def gaussian_elimination(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting.

    A is a square list of lists and b a list of the same length.  Rows
    are swapped so the pivot is the largest-magnitude entry in the
    current column; a pivot below PIVOT_TOL times the largest matrix
    entry raises ValueError("singular matrix").  Returns x as a list.
    """
    n = len(A)
    if n == 0:
        raise ValueError("empty system")
    if len(b) != n or any(len(row) != n for row in A):
        raise ValueError("non-square system")
    scale = 0.0
    for row in A:
        for value in row:
            scale = max(scale, abs(value))
    if scale <= 0.0:
        raise ValueError("singular matrix")
    aug = [list(A[r]) + [b[r]] for r in range(n)]
    for col in range(n):
        pivot = col
        for r in range(col + 1, n):
            if abs(aug[r][col]) > abs(aug[pivot][col]):
                pivot = r
        if abs(aug[pivot][col]) <= PIVOT_TOL * scale:
            raise ValueError("singular matrix")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pv
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        acc = aug[r][n]
        for c in range(r + 1, n):
            acc -= aug[r][c] * x[c]
        x[r] = acc / aug[r][r]
    return x


def solve_free(K_full, free_dofs, loads):
    """Solve the reduced system for the free degrees of freedom.

    free_dofs is a list of global dof indices and loads a dict of
    {global dof index: applied value}.  Extracts the reduced matrix,
    solves with gaussian_elimination, and maps the result back to the
    full displacement vector (fixed dofs stay 0).  Returns
    {"u_full": u_full, "x_free": x}.  Raises ValueError("singular
    structure") when the reduced matrix is singular.
    """
    ndof = len(K_full)
    free = list(free_dofs)
    b = [loads.get(d, 0.0) for d in free]
    u_full = [0.0] * ndof
    if free:
        reduced = [[K_full[r][col] for col in free] for r in free]
        try:
            x = gaussian_elimination(reduced, b)
        except ValueError:
            raise ValueError("singular structure") from None
        for dof, value in zip(free, x):
            u_full[dof] = value
        return {"u_full": u_full, "x_free": x}
    return {"u_full": u_full, "x_free": []}


def reactions(K_full, u_full, fixed_dofs, loads):
    """Return {dof index: reaction} for every fixed dof.

    R_d = sum_j K[d][j] * u[j] - applied_load[d], the action the
    support exerts on the structure at the fixed dof d.  loads is a
    dict of {global dof index: applied value}.
    """
    result = {}
    for d in fixed_dofs:
        acc = 0.0
        for j, uj in enumerate(u_full):
            acc += K_full[d][j] * uj
        result[d] = acc - loads.get(d, 0.0)
    return result


def recover_member_actions(element, u_full, dof_map):
    """Return the local end actions {n1, v1, m1, n2, v2, m2} of an element.

    The element dict must carry the geometry keys "L" and "angle"
    (added by solve_frame) in addition to i, j, E, A, I.  The local
    displacement vector is d_local = T * d_global at both ends and the
    end actions are q = k_local * d_local, the forces and moments the
    joints apply to the element ends in the local frame.  Raises
    ValueError when the member geometry is missing or non-physical.
    """
    if "L" not in element or "angle" not in element:
        raise ValueError("member geometry missing: pass L and angle")
    i = element["i"]
    j = element["j"]
    local = (
        dof_map[(i, "u")],
        dof_map[(i, "v")],
        dof_map[(i, "theta")],
        dof_map[(j, "u")],
        dof_map[(j, "v")],
        dof_map[(j, "theta")],
    )
    d_global = [u_full[d] for d in local]
    t = rotation_matrix(element["angle"])
    d_local = [0.0] * 6
    for r in range(6):
        acc = 0.0
        for col in range(6):
            acc += t[r][col] * d_global[col]
        d_local[r] = acc
    k_local = element_stiffness_local(
        element["E"], element["A"], element["I"], element["L"]
    )
    q = [0.0] * 6
    for r in range(6):
        acc = 0.0
        for col in range(6):
            acc += k_local[r][col] * d_local[col]
        q[r] = acc
    return {
        "n1": q[0],
        "v1": q[1],
        "m1": q[2],
        "n2": q[3],
        "v2": q[4],
        "m2": q[5],
    }


def solve_frame(nodes, elements, supports, loads):
    """Solve a rigid-jointed 2D frame in one call.

    nodes is a list of (x, y).  elements is a list of dicts {i, j, E,
    A, I}.  supports is a list of (node_index, dof_names) where
    dof_names lists the fixed dofs, e.g. ("u", "v", "theta").  loads is
    a dict {(node_index, dof_name): value} of point loads on any dof.
    Returns {"displacements", "reactions", "member_actions",
    "equilibrium_ok"}: displacements and reactions are dicts keyed by
    (node_index, dof_name), member_actions is one end-action dict per
    element in element order, and equilibrium_ok is True when the sum
    of the support reactions balances the applied load resultant in
    both the u and v directions within EQ_TOL = 1e-6 N.  Raises
    ValueError for unknown node indices or dof names, non-physical
    member data, and singular (unstably supported) structures.
    """
    dof_map = _default_dof_map(len(nodes))
    for node, names in supports:
        if node < 0 or node >= len(nodes):
            raise ValueError("unknown support node index")
        for name in names:
            if name not in DOF_INDEX:
                raise ValueError("unknown dof name: %r" % (name,))
    for key in loads:
        node, name = key
        if node < 0 or node >= len(nodes):
            raise ValueError("unknown load node index")
        if name not in DOF_INDEX:
            raise ValueError("unknown dof name: %r" % (name,))
    fixed = set()
    for node, names in supports:
        for name in names:
            fixed.add(dof_map[(node, name)])
    free = [d for d in range(3 * len(nodes)) if d not in fixed]
    fixed = sorted(fixed)
    assembled = assemble(nodes, elements, dof_map)
    k_full = assembled["K"]
    loads_by_dof = {dof_map[key]: value for key, value in loads.items()}
    solved = solve_free(k_full, free, loads_by_dof)
    u_full = solved["u_full"]
    reaction_map = reactions(k_full, u_full, fixed, loads_by_dof)
    displacements = {
        (node, name): u_full[dof_map[(node, name)]]
        for node in range(len(nodes))
        for name in DOF_INDEX
    }
    reverse_map = {index: key for key, index in dof_map.items()}
    reactions_out = {reverse_map[d]: reaction_map[d] for d in reaction_map}
    member_actions = []
    for element in elements:
        length, angle = _member_geometry(nodes, element)
        working = dict(element)
        working["L"] = length
        working["angle"] = angle
        member_actions.append(recover_member_actions(working, u_full, dof_map))
    equilibrium_ok = True
    for direction in ("u", "v"):
        total = 0.0
        for (node, name), value in loads.items():
            if name == direction:
                total += value
        for dof, value in reaction_map.items():
            if dof % 3 == DOF_INDEX[direction]:
                total += value
        if abs(total) > EQ_TOL:
            equilibrium_ok = False
    return {
        "displacements": displacements,
        "reactions": reactions_out,
        "member_actions": member_actions,
        "equilibrium_ok": equilibrium_ok,
    }
