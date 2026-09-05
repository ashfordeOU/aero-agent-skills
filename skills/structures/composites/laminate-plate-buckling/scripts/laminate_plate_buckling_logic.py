"""laminate_plate_buckling_logic.py: elastic buckling of orthotropic and
laminated flat plates under uniaxial in-plane compression.

Implements the classical energy-method critical load for a simply
supported orthotropic plate of length a (load direction) and width b
with laminate bending stiffnesses D11, D22, D12, D66 in N m:

    N_x_cr(m, n) = pi^2 * ( D11 * (m / a)^2
                            + 2 * (D12 + 2 * D66) * (n / b)^2
                            + D22 * n^4 * a^2 / (m^2 * b^4) )

for integer half-wave counts m and n, plus the mode-count sweep that
minimizes the critical load over the modes and the stability margin
against an applied in-plane compression load. Pure stdlib, deterministic,
offline, no randomness.

AeroSkills leaf: structures/composites/laminate-plate-buckling (wave-39).
Standards context: CMH-17 (reference only). The relations above are
standard engineering methodology, summary-only.
"""

import math

DEFAULT_M_MAX = 20
DEFAULT_N_MAX = 20


def _require_positive_float(name, value):
    """Raise ValueError unless value is a positive finite real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be a number, got " + repr(value))
    if value <= 0.0:
        raise ValueError(name + " must be positive, got " + repr(value))


def _require_positive_int(name, value):
    """Raise ValueError unless value is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(name + " must be a positive integer, got " + repr(value))


def critical_load(d11, d22, d12, d66, a, b, m, n):
    """Return the critical load N_x_cr per unit width (N/m) for mode (m, n).

    Energy-method result for a simply supported orthotropic plate of
    length a in the load direction and width b, with bending stiffnesses
    D11, D22, D12, D66 in N m and integer half-wave counts m, n.
    Raises ValueError on non-positive stiffnesses or dimensions or on m,
    n outside the positive integers.
    """
    _require_positive_float("d11", d11)
    _require_positive_float("d22", d22)
    _require_positive_float("d12", d12)
    _require_positive_float("d66", d66)
    _require_positive_float("a", a)
    _require_positive_float("b", b)
    _require_positive_int("m", m)
    _require_positive_int("n", n)
    term_m = d11 * (m / a) ** 2
    term_n = 2.0 * (d12 + 2.0 * d66) * (n / b) ** 2
    term_mn = d22 * n ** 4 * a ** 2 / (m ** 2 * b ** 4)
    return math.pi ** 2 * (term_m + term_n + term_mn)


def buckling_mode(d11, d22, d12, d66, a, b, m_max=DEFAULT_M_MAX,
                  n_max=DEFAULT_N_MAX):
    """Return (N_x_cr_min, m, n): the minimized critical load and the mode.

    Sweeps every half-wave count m in 1..m_max and n in 1..n_max through
    critical_load and keeps the smallest value. Ties resolve to the
    smallest (m, n) lexicographically (m outer loop, ascending), so the
    result is deterministic.
    """
    _require_positive_int("m_max", m_max)
    _require_positive_int("n_max", n_max)
    best = None
    best_m = 0
    best_n = 0
    for m in range(1, m_max + 1):
        for n in range(1, n_max + 1):
            value = critical_load(d11, d22, d12, d66, a, b, m, n)
            if best is None or value < best:
                best = value
                best_m = m
                best_n = n
    return (best, best_m, best_n)


def buckling_margin(d11, d22, d12, d66, a, b, applied_load,
                    m_max=DEFAULT_M_MAX, n_max=DEFAULT_N_MAX):
    """Return the buckling margin N_x_cr_min / applied_load.

    The minimized critical load comes from buckling_mode over the half-
    wave sweep; the margin is that load divided by the applied in-plane
    compression load per unit width. A margin below 1.0 means the panel
    buckles under the applied load. Raises ValueError when applied_load
    is not positive.
    """
    _require_positive_float("applied_load", applied_load)
    n_min, _, _ = buckling_mode(d11, d22, d12, d66, a, b, m_max, n_max)
    return n_min / applied_load
