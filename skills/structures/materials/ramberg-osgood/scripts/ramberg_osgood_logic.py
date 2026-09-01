#!/usr/bin/env python3
"""Ramberg-Osgood elastic-plastic stress-strain logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, naca-tn-902: public domain
NACA technical note): the three-parameter Ramberg-Osgood model describes
the elastic-plastic stress-strain curve of a metallic material as
epsilon = sigma / E + 0.002 * (sigma / sigma_0.2) ** n, where E is the
elastic modulus, sigma_0.2 is the 0.2 percent offset yield strength, and
n is the strain hardening exponent (typically 3 to 30 for aerospace
metals). The first term is the elastic strain, the second term is the
plastic strain. The equation is implicit in sigma, so the stress at a
given total strain is found by bisection on the monotonic residual
f(sigma) = sigma / E + 0.002 * (sigma / sigma_0.2) ** n - epsilon,
bracketed on [0, E * epsilon]. The secant modulus is sigma / epsilon;
the tangent modulus is the reciprocal of
d(epsilon)/d(sigma) = 1 / E + 0.002 * n * sigma ** (n - 1) / sigma_0.2 ** n.
Units: stresses and moduli in MPa, strains dimensionless.
"""


def _check_material(e_modulus_mpa, sigma_02_mpa, n):
    """Shared input validation for the material parameters."""
    if e_modulus_mpa <= 0:
        raise ValueError("elastic modulus must be > 0 MPa, got %r" % (e_modulus_mpa,))
    if sigma_02_mpa <= 0:
        raise ValueError("0.2 percent offset yield strength must be > 0 MPa, got %r" % (sigma_02_mpa,))
    if n < 1.0:
        raise ValueError("strain hardening exponent must be >= 1, got %r" % (n,))


def strain(stress_mpa, e_modulus_mpa, sigma_02_mpa, n):
    """Total Ramberg-Osgood strain at a stress: sigma/E + 0.002*(sigma/sigma_0.2)**n.

    Raises ValueError on a negative stress or invalid material
    parameters (modulus or yield strength not positive, exponent < 1).
    """
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    _check_material(e_modulus_mpa, sigma_02_mpa, n)
    elastic = stress_mpa / e_modulus_mpa
    plastic = 0.002 * (stress_mpa / sigma_02_mpa) ** n
    return elastic + plastic


def elastic_strain(stress_mpa, e_modulus_mpa):
    """Elastic strain sigma / E at a stress; the linear part of the model."""
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    if e_modulus_mpa <= 0:
        raise ValueError("elastic modulus must be > 0 MPa, got %r" % (e_modulus_mpa,))
    return stress_mpa / e_modulus_mpa


def plastic_strain(total_strain, stress_mpa, e_modulus_mpa):
    """Plastic strain: total strain minus the elastic part sigma / E.

    Raises ValueError when the elastic part already exceeds the total
    strain (physically impossible input).
    """
    if total_strain < 0:
        raise ValueError("total strain must be >= 0, got %r" % (total_strain,))
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    if e_modulus_mpa <= 0:
        raise ValueError("elastic modulus must be > 0 MPa, got %r" % (e_modulus_mpa,))
    elastic = stress_mpa / e_modulus_mpa
    if elastic > total_strain + 1e-12:
        raise ValueError(
            "elastic strain %r exceeds total strain %r; inconsistent input" % (elastic, total_strain)
        )
    return total_strain - elastic


def stress_for_strain(total_strain, e_modulus_mpa, sigma_02_mpa, n, tol=1e-10):
    """Stress at a total strain by bisection on the implicit model.

    The residual f(sigma) is monotonic increasing and bracketed on
    [0, E * total_strain], since sigma / E never exceeds the total
    strain. Converges to a relative bracket width of tol (default
    1e-10) in at most 200 iterations.
    """
    if total_strain < 0:
        raise ValueError("total strain must be >= 0, got %r" % (total_strain,))
    _check_material(e_modulus_mpa, sigma_02_mpa, n)
    if total_strain == 0.0:
        return 0.0

    def residual(sig):
        return sig / e_modulus_mpa + 0.002 * (sig / sigma_02_mpa) ** n - total_strain

    lo = 0.0
    hi = e_modulus_mpa * total_strain
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if residual(mid) > 0.0:
            hi = mid
        else:
            lo = mid
        if (hi - lo) <= tol * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def secant_modulus(stress_mpa, total_strain):
    """Secant modulus sigma / epsilon, the chord slope from the origin."""
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    if total_strain <= 0:
        raise ValueError("total strain must be > 0 for a secant modulus, got %r" % (total_strain,))
    return stress_mpa / total_strain


def tangent_modulus(stress_mpa, e_modulus_mpa, sigma_02_mpa, n):
    """Tangent modulus d(sigma)/d(epsilon) at a stress along the curve.

    Reciprocal of 1/E + 0.002 * n * sigma ** (n - 1) / sigma_0.2 ** n;
    equals E at sigma = 0 and falls toward the plastic plateau as the
    stress rises.
    """
    if stress_mpa < 0:
        raise ValueError("stress must be >= 0 MPa, got %r" % (stress_mpa,))
    _check_material(e_modulus_mpa, sigma_02_mpa, n)
    deps_dsig = 1.0 / e_modulus_mpa + 0.002 * n * stress_mpa ** (n - 1.0) / sigma_02_mpa ** n
    return 1.0 / deps_dsig
