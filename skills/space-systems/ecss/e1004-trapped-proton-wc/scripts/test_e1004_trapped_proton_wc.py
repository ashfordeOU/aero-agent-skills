

import math as _math
import unittest as _unittest

class _approx:
    def __init__(self, expected, rel=1e-9):
        self.expected = expected
        self.rel = rel
    def __eq__(self, other):
        try:
            return _math.isclose(other, self.expected, rel_tol=self.rel)
        except TypeError:
            return False
    def __repr__(self):
        return f"approx({self.expected!r})"

class _raises:
    def __init__(self, exc):
        self.exc = exc
    def __enter__(self):
        return self
    def __exit__(self, typ, val, tb):
        if typ is None:
            raise AssertionError(f"{self.exc.__name__} not raised")
        if issubclass(typ, self.exc):
            return True
        return False

class _PytestShim:
    approx = staticmethod(lambda *a, **k: _approx(*a, **k))
    raises = staticmethod(lambda *a, **k: _raises(*a, **k))

pytest = _PytestShim()

"""Tests for the ECSS-E-ST-10-04C worst-case trapped proton model."""

import math


from e1004_trapped_proton_wc_logic import (
    TrappedProtonModelError,
    build_worst_case_envelope,
    compute_worst_case_trapped_proton_spectrum,
    integrate_integral_spectrum,
    make_spectrum,
    resample_spectrum,
)


def test_make_spectrum_accepts_valid_data():
    spectrum = make_spectrum([1.0, 10.0, 100.0], [1e6, 1e4, 1e1])
    assert spectrum.energies_mev == (1.0, 10.0, 100.0)
    assert spectrum.flux == (1e6, 1e4, 1e1)


def test_make_spectrum_rejects_mismatched_lengths():
    with _raises(TrappedProtonModelError):
        make_spectrum([1.0, 10.0], [1e6])


def test_make_spectrum_rejects_non_increasing_energy_grid():
    with _raises(TrappedProtonModelError):
        make_spectrum([1.0, 1.0, 10.0], [1e6, 1e5, 1e4])


def test_make_spectrum_rejects_negative_flux():
    with _raises(TrappedProtonModelError):
        make_spectrum([1.0, 10.0], [1e6, -1.0])


def test_make_spectrum_rejects_empty_grid():
    with _raises(TrappedProtonModelError):
        make_spectrum([], [])


def test_make_spectrum_rejects_non_positive_energy():
    with _raises(TrappedProtonModelError):
        make_spectrum([0.0, 10.0], [1e6, 1e4])


def test_resample_spectrum_clamps_outside_range():
    spectrum = make_spectrum([1.0, 10.0, 100.0], [1e6, 1e4, 1e2])
    resampled = resample_spectrum(spectrum, [0.1, 1.0, 1000.0])
    assert resampled.flux[0] == _approx(1e6)
    assert resampled.flux[1] == _approx(1e6)
    assert resampled.flux[2] == _approx(1e2)


def test_resample_spectrum_loglog_interpolates_midpoint():
    spectrum = make_spectrum([1.0, 100.0], [1e6, 1e2])
    resampled = resample_spectrum(spectrum, [10.0])
    assert resampled.flux[0] == _approx(1e4, rel=1e-6)


def test_build_worst_case_envelope_takes_pointwise_max():
    ap8_min = make_spectrum([1.0, 10.0, 100.0], [1e5, 1e4, 1e2])
    ap8_max = make_spectrum([1.0, 10.0, 100.0], [1e4, 5e4, 1e1])

    envelope, dominant_source = build_worst_case_envelope(ap8_min, ap8_max)

    assert envelope.flux == (1e5, 5e4, 1e2)
    assert dominant_source == ("ap8_min", "ap8_max", "ap8_min")


def test_build_worst_case_envelope_includes_ap9_percentile():
    ap8_min = make_spectrum([1.0, 10.0], [1e5, 1e4])
    ap8_max = make_spectrum([1.0, 10.0], [1e4, 1e4])
    ap9_percentile = make_spectrum([1.0, 10.0], [2e5, 1e3])

    envelope, dominant_source = build_worst_case_envelope(ap8_min, ap8_max, ap9_percentile)

    assert envelope.flux[0] == _approx(2e5)
    assert dominant_source[0] == "ap9_percentile"
    assert envelope.flux[1] == _approx(1e4)


def test_build_worst_case_envelope_rejects_non_overlapping_ranges():
    ap8_min = make_spectrum([1.0, 10.0], [1e5, 1e4])
    ap8_max = make_spectrum([100.0, 1000.0], [1e2, 1e1])

    with _raises(TrappedProtonModelError):
        build_worst_case_envelope(ap8_min, ap8_max)


def test_integrate_integral_spectrum_is_non_increasing():
    spectrum = make_spectrum([1.0, 10.0, 100.0], [1e5, 1e4, 1e2])
    integral = integrate_integral_spectrum(spectrum)

    assert integral.flux[-1] == _approx(0.0)
    assert integral.flux[0] > integral.flux[1] > integral.flux[2]


def test_integrate_integral_spectrum_matches_trapezoid_by_hand():
    spectrum = make_spectrum([1.0, 2.0], [10.0, 0.0])
    # Linear segment 1..2 MeV, flux drops from 10 to 0 -> triangle area 0.5*1*10 = 5.
    integral = integrate_integral_spectrum(spectrum)
    assert integral.flux[0] == _approx(5.0)
    assert integral.flux[1] == _approx(0.0)


def test_compute_worst_case_trapped_proton_spectrum_end_to_end():
    ap8_min = make_spectrum([1.0, 10.0, 100.0], [1e5, 1e4, 1e2])
    ap8_max = make_spectrum([1.0, 10.0, 100.0], [1e4, 5e4, 1e1])

    result = compute_worst_case_trapped_proton_spectrum(ap8_min, ap8_max)

    assert result.differential_spectrum.flux == (1e5, 5e4, 1e2)
    assert result.dominant_source == ("ap8_min", "ap8_max", "ap8_min")
    assert result.integral_spectrum.flux[0] > result.integral_spectrum.flux[-1]
    assert result.integral_spectrum.flux[-1] == _approx(0.0)


def test_compute_worst_case_trapped_proton_spectrum_with_ap9():
    ap8_min = make_spectrum([1.0, 10.0], [1e5, 1e4])
    ap8_max = make_spectrum([1.0, 10.0], [1e4, 1e4])
    ap9_percentile = make_spectrum([1.0, 10.0], [2e5, 1e3])

    result = compute_worst_case_trapped_proton_spectrum(ap8_min, ap8_max, ap9_percentile)

    assert result.dominant_source[0] == "ap9_percentile"
    assert math.isfinite(result.integral_spectrum.flux[0])


def load_tests(loader, standard_tests, pattern):
    import sys as _sys
    g = _sys.modules[__name__].__dict__
    names = [n for n in g if n.startswith("test_") and callable(g[n])]
    tc = type("TestLeaf", (_unittest.TestCase,), {n: (lambda self, _n=n, _f=g[n]: _f()) for n in names})
    return _unittest.TestLoader().loadTestsFromTestCase(tc)

if __name__ == "__main__":
    _unittest.main()
