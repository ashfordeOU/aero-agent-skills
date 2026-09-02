#!/usr/bin/env python3
"""NACA airfoil geometry logic (paraphrase, public-domain formulas).

Common-knowledge summary (standards-map.yaml, naca-tr-824: public
domain): NACA Report 824 (Abbott, von Doenhoff, Stivers) is the classic
airfoil section data reference. The NACA 4-digit series (Report 460)
defines the thickness half-ordinate
  y_t = (t / 0.2) * (0.29690 * sqrt(x) - 0.12600 * x - 0.35160 * x^2
                     + 0.28430 * x^3 - 0.10150 * x^4)
with maximum half-thickness t / 2 at x = 0.3, and the mean camber line
  x <= p: y_c = (m / p^2) * (2 * p * x - x^2)
  x >= p: y_c = (m / (1 - p)^2) * (1 - 2 * p + 2 * p * x - x^2)
with slope dy_c / dx = (2 * m / p^2) * (p - x) on x <= p and
(2 * m / (1 - p)^2) * (p - x) on x >= p, zero at x = p. The
leading-edge radius is r_le = 1.1019 * t^2 and the enclosed section
area per unit span is A = 2 * integral(y_t dx) = 0.68508 * t in
chord^2. NACA 5-digit decode: design cl = first digit * 0.15, camber
position = second digit * 5 percent chord, thickness = last two
digits percent. NACA 6-series decode: 65-218 reads series 6,
min-pressure position 0.5 chord, design cl 0.2, thickness 0.18.
"""

import math
import re

# Mean-line constant k1 for the simple (third digit 0) 5-digit mean
# lines, tabulated by camber position (Abbott and von Doenhoff,
# section 6.3).
K1_TABLE = {
    0.05: 361.4,
    0.10: 51.64,
    0.15: 15.957,
    0.20: 6.643,
    0.25: 3.230,
}

# Integral of the thickness polynomial over [0, 1], closed form.
_THICKNESS_INTEGRAL = 0.0685083


def _check_t(t):
    if not (0.0 < t < 1.0):
        raise ValueError("thickness ratio must be in (0, 1), got %r" % (t,))


def _check_x(x):
    if not (0.0 <= x <= 1.0):
        raise ValueError("chordwise station x must be in [0, 1], got %r" % (x,))


def _check_m(m):
    if not (0.0 <= m < 1.0):
        raise ValueError("max camber m must be in [0, 1), got %r" % (m,))


def _check_p(p):
    if not (0.0 < p < 1.0):
        raise ValueError("camber position p must be in (0, 1), got %r" % (p,))


def thickness_ord(t, x):
    """NACA 4-digit thickness half-ordinate y_t at station x.

    t is the thickness ratio (e.g. 0.12), x the chordwise station in
    [0, 1]. Returns the half-thickness in fraction of chord; y_t peaks
    at t / 2 on x = 0.3.
    """
    _check_t(t)
    _check_x(x)
    s = math.sqrt(x)
    poly = (
        0.29690 * s
        - 0.12600 * x
        - 0.35160 * x * x
        + 0.28430 * x * x * x
        - 0.10150 * x * x * x * x
    )
    return (t / 0.2) * poly


def camber_ord(m, p, x):
    """NACA 4-digit mean line ordinate y_c at station x.

    m is the max camber (e.g. 0.02), p the camber position (e.g. 0.4).
    Both branches return m at x = p.
    """
    _check_m(m)
    _check_p(p)
    _check_x(x)
    if x <= p:
        return (m / (p * p)) * (2.0 * p * x - x * x)
    return (m / ((1.0 - p) * (1.0 - p))) * (
        1.0 - 2.0 * p + 2.0 * p * x - x * x
    )


def camber_slope(m, p, x):
    """NACA 4-digit mean line slope dy_c / dx at station x.

    Zero at x = p on both branches (continuous mean line).
    """
    _check_m(m)
    _check_p(p)
    _check_x(x)
    if x <= p:
        return (2.0 * m / (p * p)) * (p - x)
    return (2.0 * m / ((1.0 - p) * (1.0 - p))) * (p - x)


def surface_ords(m, p, t, x):
    """Upper and lower surface ordinates y_c + y_t and y_c - y_t."""
    yc = camber_ord(m, p, x)
    yt = thickness_ord(t, x)
    return (yc + yt, yc - yt)


def leading_edge_radius(t):
    """NACA 4-digit leading-edge radius in fraction of chord: 1.1019 t^2."""
    _check_t(t)
    return 1.1019 * t * t


def section_area(t):
    """Enclosed section area per unit span in chord^2: 2 * integral(y_t dx).

    Independent of camber: the camber cancels in upper minus lower.
    """
    _check_t(t)
    return 2.0 * (t / 0.2) * _THICKNESS_INTEGRAL


def _clean(name):
    return str(name).upper().replace("NACA", "").strip()


def decode_4digit(name):
    """Decode a NACA 4-digit designation.

    NACA 2412 -> camber 0.02 at p = 0.4, thickness 0.12. Returns a
    dict with camber, camber_pos, thickness.
    """
    n = _clean(name)
    if len(n) != 4 or not n.isdigit():
        raise ValueError("4-digit NACA name expected, got %r" % (name,))
    thickness = int(n[2:]) / 100.0
    if thickness <= 0.0:
        raise ValueError("thickness must be positive, got %r" % (name,))
    return {
        "camber": int(n[0]) / 100.0,
        "camber_pos": int(n[1]) / 10.0,
        "thickness": thickness,
    }


def decode_5digit(name):
    """Decode a NACA 5-digit designation.

    NACA 23012 -> design cl 0.3, camber position 0.15, thickness 0.12;
    mean line m = 0.15 with k1 = 15.957. Returns a dict with design_cl,
    camber_pos, thickness, m, k1, reflexed.
    """
    n = _clean(name)
    if len(n) != 5 or not n.isdigit():
        raise ValueError("5-digit NACA name expected, got %r" % (name,))
    thickness = int(n[3:]) / 100.0
    if thickness <= 0.0:
        raise ValueError("thickness must be positive, got %r" % (name,))
    camber_pos = int(n[1]) * 0.05
    return {
        "design_cl": int(n[0]) * 0.15,
        "camber_pos": camber_pos,
        "thickness": thickness,
        "m": camber_pos,
        "k1": K1_TABLE.get(round(camber_pos, 3)),
        "reflexed": n[2] == "1",
    }


def decode_6series(name):
    """Decode a plain NACA 6-series designation.

    NACA 65-218 -> series 6, min-pressure position 0.5 chord, design
    cl 0.2, thickness 0.18. Modified mean lines (parenthetical digit,
    e.g. 65(3)-218) and A-series thickness variants (e.g. 64A-212)
    are rejected: their decode depends on variant conventions not
    covered here.
    """
    n = _clean(name)
    m = re.match(r"^6(\d)-(\d)(\d{2})$", n)
    if not m:
        raise ValueError("plain 6-series NACA name expected, got %r" % (name,))
    return {
        "series": 6,
        "min_pressure_pos": int(m.group(1)) / 10.0,
        "design_cl": int(m.group(2)) / 10.0,
        "thickness": int(m.group(3)) / 100.0,
    }
