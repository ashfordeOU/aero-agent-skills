#!/usr/bin/env python3
"""Vehicle mass properties (inertia estimation) logic (paraphrase,
common knowledge).

Common-knowledge summary (standards-map.yaml, far-25: public domain
regulation context): mass properties estimation supports weight and
balance and loads analyses. Moment of inertia follows from the
radius of gyration, I = m * k^2, and the parallel-axis theorem
moves inertia between axes, I = I_cg + m * d^2. A gyration radius
must fall inside the component dimension. Bands are project-defined
sanity checks.
"""


def moi_gyration(mass, radius_of_gyration):
    """Moment of inertia (kg m2) from mass and radius of gyration (m)."""
    if mass < 0:
        raise ValueError("mass must be >= 0, got %r" % (mass,))
    if radius_of_gyration <= 0:
        raise ValueError("radius of gyration must be > 0, got %r"
                         % (radius_of_gyration,))
    return mass * radius_of_gyration ** 2


def parallel_axis(i_cg, mass, offset):
    """Moment of inertia about a parallel axis offset d from the CG."""
    if i_cg < 0:
        raise ValueError("i_cg must be >= 0, got %r" % (i_cg,))
    if mass < 0:
        raise ValueError("mass must be >= 0, got %r" % (mass,))
    if offset < 0:
        raise ValueError("offset must be >= 0, got %r" % (offset,))
    return i_cg + mass * offset ** 2


def gyration_sane(radius_of_gyration, dimension):
    """True when the gyration radius lies inside the dimension."""
    if radius_of_gyration <= 0:
        raise ValueError("radius of gyration must be > 0")
    if dimension <= 0:
        raise ValueError("dimension must be > 0")
    return radius_of_gyration < dimension
