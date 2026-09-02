#!/usr/bin/env python3
"""Linear-elastic fracture toughness logic (common engineering methodology).

Common-knowledge summary (standards-map.yaml, mmpsd: MMPDS compiles the
statistically based metallic material allowables; ASTM E399 is the test
method context): the applied mode I stress intensity factor of a cracked
body is K = Y * sigma * sqrt(pi * a), where sigma is the remote stress,
a is the crack size (half length of a through-crack or depth of an edge
crack), and Y is the dimensionless geometry factor (1.0 for a crack in
an infinite plate, 1.12 for an edge crack). Fast fracture initiates when
the applied K reaches the plane-strain fracture toughness K_IC. The
critical crack size at the applied stress is a_c = (K_IC / (Y * sigma))^2
/ pi. A valid plane-strain K_IC test requires the specimen thickness B
and the crack size a to both be at least 2.5 * (K_IC / sigma_ys)^2,
where sigma_ys is the 0.2 percent offset yield strength (ASTM E399
validity rule).

Units: stresses in MPa, crack sizes in meters, so K and K_IC are in
MPa sqrt(m). All functions raise ValueError on invalid inputs.
"""

import math


def _check_positive(value, name):
    if value <= 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def stress_intensity(stress_mpa, crack_size_m, geometry_factor=1.0):
    """Applied mode I stress intensity K = Y * sigma * sqrt(pi * a).

    Returns K in MPa sqrt(m) for stress in MPa and crack size in
    meters. geometry_factor defaults to 1.0 (embedded crack); use
    1.12 for an edge crack.
    """
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    _check_positive(crack_size_m, "crack size")
    _check_positive(geometry_factor, "geometry factor")
    return geometry_factor * stress_mpa * math.sqrt(math.pi * crack_size_m)


def is_fracture(stress_mpa, crack_size_m, kic_mpa_sqrtm, geometry_factor=1.0):
    """Failure criterion: True when the applied K >= K_IC.

    Fast fracture initiates when the applied stress intensity reaches
    the plane-strain fracture toughness. Raises ValueError on a
    non-positive K_IC or an invalid crack scenario.
    """
    _check_positive(kic_mpa_sqrtm, "K_IC")
    k_applied = stress_intensity(stress_mpa, crack_size_m, geometry_factor)
    return k_applied >= kic_mpa_sqrtm


def critical_crack_size(stress_mpa, kic_mpa_sqrtm, geometry_factor=1.0):
    """Critical crack size a_c = (K_IC / (Y * sigma))^2 / pi, in meters.

    The largest crack the part tolerates at the applied stress before
    unstable extension. Scales with 1 / sigma^2: doubling the stress
    quarters the tolerable crack size.
    """
    if stress_mpa <= 0:
        raise ValueError("stress must be > 0 MPa for a critical crack size, got %r" % (stress_mpa,))
    _check_positive(kic_mpa_sqrtm, "K_IC")
    _check_positive(geometry_factor, "geometry factor")
    return (kic_mpa_sqrtm / (geometry_factor * stress_mpa)) ** 2 / math.pi


def minimum_plane_strain_dimension(kic_mpa_sqrtm, yield_strength_mpa):
    """ASTM E399 validity dimension 2.5 * (K_IC / sigma_ys)^2, in meters.

    The minimum specimen thickness and crack size for a valid
    plane-strain K_IC test.
    """
    _check_positive(kic_mpa_sqrtm, "K_IC")
    _check_positive(yield_strength_mpa, "yield strength")
    return 2.5 * (kic_mpa_sqrtm / yield_strength_mpa) ** 2


def plane_strain_valid(thickness_m, crack_size_m, kic_mpa_sqrtm, yield_strength_mpa):
    """Plane-strain validity check: thickness and crack size both meet
    2.5 * (K_IC / sigma_ys)^2 (ASTM E399 test context).

    Returns True when the specimen is thick enough and the crack long
    enough for the measured toughness to be a valid plane-strain K_IC;
    False when the constraint is relaxed (plane-stress or transitional
    toughness, geometry dependent). Raises ValueError on a non-positive
    thickness or crack size.
    """
    _check_positive(thickness_m, "specimen thickness")
    _check_positive(crack_size_m, "crack size")
    req = minimum_plane_strain_dimension(kic_mpa_sqrtm, yield_strength_mpa)
    return thickness_m >= req and crack_size_m >= req


def demonstrate():
    """Run the worked anchor and print the results (docstring values)."""
    sigma = 200.0  # MPa
    a = 0.005  # m (5 mm edge crack)
    y = 1.12
    kic = 26.0  # MPa sqrt(m)
    k = stress_intensity(sigma, a, y)
    print("K = Y * sigma * sqrt(pi * a) = %.2f MPa sqrt(m)" % k)
    print("failure at K_IC = %.0f MPa sqrt(m): %s" % (kic, is_fracture(sigma, a, kic, y)))
    kic_30 = 30.0
    ac = critical_crack_size(sigma, kic_30, y)
    print("critical crack at K_IC = %.0f MPa sqrt(m): %.2f mm" % (kic_30, ac * 1000.0))
    ys = 500.0  # MPa
    req = minimum_plane_strain_dimension(kic_30, ys)
    print("plane-strain validity dimension 2.5 * (K_IC/sigma_ys)^2: %.1f mm" % (req * 1000.0))
    print("25 mm thick specimen valid: %s" % plane_strain_valid(0.025, 0.012, kic_30, ys))
    print("5 mm thick specimen valid: %s" % plane_strain_valid(0.005, 0.012, kic_30, ys))


if __name__ == "__main__":
    demonstrate()
