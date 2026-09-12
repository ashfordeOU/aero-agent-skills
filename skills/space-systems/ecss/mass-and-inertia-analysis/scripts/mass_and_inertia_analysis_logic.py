"""
Deterministic mass and inertia property computation per ECSS-E-ST-32C §4.6.2.18.

A component is a dict with keys:
    name     : str
    mass     : float  (kg, must be > 0)
    centroid : [x, y, z]  (m, 3-element list)
    inertia  : [[Ixx, Ixy, Ixz],   (kg m², self-inertia about the component centroid)
                [Iyx, Iyy, Iyz],
                [Izx, Izy, Izz]]
"""

REQUIRED_KEYS = {"name", "mass", "centroid", "inertia"}


class MassInertiaError(Exception):
    pass


def _validate_component(comp):
    missing = REQUIRED_KEYS - set(comp.keys())
    if missing:
        raise MassInertiaError(
            f"Component '{comp.get('name', '?')}' missing fields: {sorted(missing)}"
        )
    if comp["mass"] <= 0:
        raise MassInertiaError(
            f"Component '{comp['name']}' has non-positive mass: {comp['mass']}"
        )
    if len(comp["centroid"]) != 3:
        raise MassInertiaError(
            f"Component '{comp['name']}' centroid must have exactly 3 elements."
        )
    if len(comp["inertia"]) != 3 or any(len(row) != 3 for row in comp["inertia"]):
        raise MassInertiaError(
            f"Component '{comp['name']}' inertia must be a 3x3 matrix."
        )


def compute_total_mass(components):
    """Sum of all component masses (kg)."""
    if not components:
        raise MassInertiaError("Component list is empty.")
    for c in components:
        _validate_component(c)
    return sum(c["mass"] for c in components)


def compute_center_of_mass(components):
    """
    Mass-weighted centroid of the component set.
    Returns [x, y, z] in the same coordinate frame as the component centroids.
    """
    total = compute_total_mass(components)
    cx = sum(c["mass"] * c["centroid"][0] for c in components) / total
    cy = sum(c["mass"] * c["centroid"][1] for c in components) / total
    cz = sum(c["mass"] * c["centroid"][2] for c in components) / total
    return [cx, cy, cz]


def _dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _parallel_axis_correction(m, d):
    """
    Parallel-axis correction tensor for mass m displaced by vector d from the
    reference point: C_ij = m * (|d|^2 * delta_ij - d_i * d_j).
    Returns 3x3 list-of-lists.
    """
    d2 = _dot3(d, d)
    result = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            delta_ij = 1.0 if i == j else 0.0
            result[i][j] = m * (delta_ij * d2 - d[i] * d[j])
    return result


def compute_inertia_tensor(components, ref_point=None):
    """
    System inertia tensor about ref_point using the parallel-axis theorem.
    ref_point defaults to the system center of mass when not provided.
    Returns a 3x3 list-of-lists in kg m².
    """
    for c in components:
        _validate_component(c)

    if ref_point is None:
        ref_point = compute_center_of_mass(components)

    I_sys = [[0.0] * 3 for _ in range(3)]

    for c in components:
        d = [c["centroid"][k] - ref_point[k] for k in range(3)]
        correction = _parallel_axis_correction(c["mass"], d)
        for i in range(3):
            for j in range(3):
                I_sys[i][j] += c["inertia"][i][j] + correction[i][j]

    return I_sys


def check_mass_budget(total_mass, budget):
    """
    Compare total_mass (kg) against the allocated mass budget (kg).
    Returns a dict with:
        compliant : bool  — True when total_mass <= budget
        margin    : float — budget - total_mass (positive means under budget)
    Raises MassInertiaError if budget is not positive.
    """
    if budget <= 0:
        raise MassInertiaError(f"Mass budget must be positive, got {budget}.")
    margin = budget - total_mass
    return {"compliant": margin >= 0.0, "margin": margin}


def mass_fraction(component_mass, total_mass):
    """Fraction of system mass attributable to a single component (dimensionless)."""
    if total_mass <= 0:
        raise MassInertiaError("Total mass must be positive.")
    return component_mass / total_mass
