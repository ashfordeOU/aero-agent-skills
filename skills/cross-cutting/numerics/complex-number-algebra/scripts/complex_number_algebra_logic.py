"""Complex-number algebra kernel over (re, im) float tuples.

Pure Python standard library only (math module). A complex number is a
2-tuple (re, im) of floats. All core arithmetic is implemented directly
over the rectangular coordinates; no cmath calls, so every operation is
transparent, deterministic and assertable to exact float equality on
rational results.

Reference: NACA-TR-824 pack convention (reference-only; no complex-math
standard exists in standards-map.yaml). The relations implemented are
standard engineering methodology.
"""

import math

# Module constants (no magic numbers in the functions).
ROUND_TOL = 1e-12      # near-zero coordinate cleanup threshold.
IS_CLOSE_TOL = 1e-9    # default tolerance for is_close.
TWO_PI = math.tau      # 2*pi, the full-turn angle for roots of unity.


def rect(re, im):
    """Return the complex value (re, im) as a 2-tuple, no normalization."""
    return (re, im)


def modulus(z):
    """Return |z| = math.hypot(re, im), overflow-safe and exact to ulp."""
    re, im = z
    return math.hypot(re, im)


def arg(z):
    """Return the argument of z in radians in (-pi, pi] via atan2."""
    re, im = z
    return math.atan2(im, re)


def conjugate(z):
    """Return the complex conjugate (re, -im)."""
    re, im = z
    return (re, -im)


def complex_add(z1, z2):
    """Return z1 + z2 componentwise."""
    re1, im1 = z1
    re2, im2 = z2
    return (re1 + re2, im1 + im2)


def complex_sub(z1, z2):
    """Return z1 - z2 componentwise."""
    re1, im1 = z1
    re2, im2 = z2
    return (re1 - re2, im1 - im2)


def complex_mul(z1, z2):
    """Return z1 * z2 by the rectangular product rule."""
    re1, im1 = z1
    re2, im2 = z2
    return (re1 * re2 - im1 * im2, re1 * im2 + re2 * im1)


def complex_div(z1, z2):
    """Return z1 / z2 by multiplying by the conjugate over |z2|^2.

    Raises ValueError when the denominator is exactly zero.
    """
    re1, im1 = z1
    re2, im2 = z2
    denom = re2 * re2 + im2 * im2
    if denom == 0:
        raise ValueError("complex division by zero")
    re = (re1 * re2 + im1 * im2) / denom
    im = (im1 * re2 - re1 * im2) / denom
    return (re, im)


def polar(z):
    """Return (modulus, argument) of z as a 2-tuple."""
    return (modulus(z), arg(z))


def from_polar(r, theta):
    """Return (r*cos(theta), r*sin(theta)); ValueError if r < 0."""
    if r < 0:
        raise ValueError("polar radius must be non-negative")
    return (r * math.cos(theta), r * math.sin(theta))


def exp_imag(theta):
    """Return e^(i*theta) = (cos(theta), sin(theta))."""
    return (math.cos(theta), math.sin(theta))


def complex_pow(z, n):
    """Return z**n for integer n >= 0 by De Moivre's formula.

    z**n = r**n * (cos(n*theta) + i*sin(n*theta)) with r = |z| and
    theta = arg(z). Float noise on a real-axis result is cleaned up:
    the imaginary part below ROUND_TOL is rounded to 0.0, and the real
    part within ROUND_TOL of an integer is snapped to it, so (1+i)**8
    returns exactly (16.0, 0.0). Raises ValueError for negative n and
    for 0**0 (n = 0, z = (0, 0)).
    """
    if n < 0:
        raise ValueError("complex_pow exponent must be >= 0")
    if n == 0 and z == (0, 0):
        raise ValueError("0**0 is undefined")
    re, im = from_polar(modulus(z) ** n, n * arg(z))
    if abs(im) < ROUND_TOL:
        im = 0.0
        if abs(re - round(re)) < ROUND_TOL:
            re = float(round(re))
    return (re, im)


def roots_of_unity(n):
    """Return the n-th roots of unity e^(2*pi*i*k/n) for k in 0..n-1.

    Near-zero coordinates are rounded to 0.0 so the 4th roots come out
    exactly (1, 0), (0, 1), (-1, 0), (0, -1). ValueError if n <= 0.
    """
    if n <= 0:
        raise ValueError("roots_of_unity requires n >= 1")
    roots = []
    for k in range(n):
        angle = TWO_PI * k / n
        re = math.cos(angle)
        im = math.sin(angle)
        if abs(re) < ROUND_TOL:
            re = 0.0
        if abs(im) < ROUND_TOL:
            im = 0.0
        roots.append((re, im))
    return roots


def mag_phase(z):
    """Return (modulus, argument); phasor-vocabulary alias of polar."""
    return polar(z)


def is_close(z1, z2, tol=IS_CLOSE_TOL):
    """Return True when both components of z1 and z2 differ by < tol."""
    return max(abs(z1[0] - z2[0]), abs(z1[1] - z2[1])) < tol


def complex_algebra(z1, z2, n=None):
    """Run the full algebra result set on z1 and z2.

    Returns a dict with keys z1, z2, sum, difference, product, quotient,
    conjugate_z1, modulus_z1, argument_z1_deg, polar_z1 and, when n is
    not None, power_z1_n and roots_n. ValueErrors propagate.
    """
    result = {
        "z1": z1,
        "z2": z2,
        "sum": complex_add(z1, z2),
        "difference": complex_sub(z1, z2),
        "product": complex_mul(z1, z2),
        "quotient": complex_div(z1, z2),
        "conjugate_z1": conjugate(z1),
        "modulus_z1": modulus(z1),
        "argument_z1_deg": math.degrees(arg(z1)),
        "polar_z1": polar(z1),
    }
    if n is not None:
        result["power_z1_n"] = complex_pow(z1, n)
        result["roots_n"] = roots_of_unity(n)
    return result


if __name__ == "__main__":
    # Lightweight smoke print; the contract test owns the assertions.
    print("(3,4)*(2,-1) =", complex_mul((3, 4), (2, -1)))
    print("(1,2)/(3,-4) =", complex_div((1, 2), (3, -4)))
    print("(1,1)**8 =", complex_pow((1, 1), 8))
    print("4th roots:", roots_of_unity(4))
