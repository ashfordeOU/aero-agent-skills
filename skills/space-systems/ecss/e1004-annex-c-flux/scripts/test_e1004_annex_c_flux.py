

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

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from e1004_annex_c_flux_logic import (
    METEOROID_STREAMS,
    earth_shielding_factor,
    grun_cumulative_flux,
    grun_differential_flux,
    gravitational_focusing_factor,
    near_earth_flux,
    stream_enhancement_factor,
    total_cumulative_flux,
)


def test_grun_flux_positive_across_range():
    for mass_g in (1e-18, 1e-12, 1e-6, 1e-3, 1.0, 10.0, 100.0):
        assert grun_cumulative_flux(mass_g) > 0


def test_grun_flux_strictly_decreasing_with_mass():
    masses = (1e-18, 1e-15, 1e-10, 1e-6, 1e-3, 1.0, 10.0, 100.0)
    fluxes = [grun_cumulative_flux(m) for m in masses]
    assert all(fluxes[i] > fluxes[i + 1] for i in range(len(fluxes) - 1))


def test_grun_flux_rejects_out_of_range_mass():
    with _raises(ValueError):
        grun_cumulative_flux(1e-19)
    with _raises(ValueError):
        grun_cumulative_flux(1e3)


def test_grun_flux_rejects_non_positive_mass():
    with _raises(ValueError):
        grun_cumulative_flux(0)
    with _raises(ValueError):
        grun_cumulative_flux(-1e-6)


def test_grun_differential_flux_is_positive():
    for mass_g in (1e-12, 1e-6, 1e-3, 1.0):
        assert grun_differential_flux(mass_g) > 0


def test_stream_enhancement_factor_known_stream_is_case_insensitive():
    assert stream_enhancement_factor("perseids") == METEOROID_STREAMS["perseids"]["enhancement_factor"]
    assert stream_enhancement_factor("PERSEIDS") == stream_enhancement_factor("perseids")


def test_stream_enhancement_factor_unknown_stream_raises():
    with _raises(ValueError):
        stream_enhancement_factor("not-a-real-stream")


def test_total_cumulative_flux_without_stream_equals_background():
    mass_g = 1e-6
    result = total_cumulative_flux(mass_g)
    assert result["enhancement_factor"] == 1.0
    assert result["total_m2_s"] == _approx(result["background_m2_s"])


def test_total_cumulative_flux_with_stream_scales_background():
    mass_g = 1e-6
    result = total_cumulative_flux(mass_g, stream_name="leonids")
    expected_factor = METEOROID_STREAMS["leonids"]["enhancement_factor"]
    assert result["enhancement_factor"] == expected_factor
    assert result["total_m2_s"] == _approx(result["background_m2_s"] * expected_factor)


def test_earth_shielding_factor_bounds_and_monotonicity():
    surface = earth_shielding_factor(0.0)
    leo = earth_shielding_factor(400.0)
    high = earth_shielding_factor(36000.0)
    assert surface == _approx(0.5)
    assert 0.5 <= surface < leo < high < 1.0


def test_earth_shielding_factor_rejects_negative_altitude():
    with _raises(ValueError):
        earth_shielding_factor(-1.0)


def test_gravitational_focusing_factor_bounds_and_monotonicity():
    surface = gravitational_focusing_factor(0.0)
    leo = gravitational_focusing_factor(400.0)
    high = gravitational_focusing_factor(36000.0)
    assert surface == _approx(2.0)
    assert 1.0 < high < leo < surface <= 2.0


def test_gravitational_focusing_factor_rejects_negative_altitude():
    with _raises(ValueError):
        gravitational_focusing_factor(-1.0)


def test_shielding_and_focusing_factors_exactly_cancel_at_surface():
    shielding = earth_shielding_factor(0.0)
    focusing = gravitational_focusing_factor(0.0)
    assert shielding * focusing == _approx(1.0)


def test_near_earth_flux_combines_all_factors():
    mass_g = 1e-6
    altitude_km = 400.0
    result = near_earth_flux(mass_g, altitude_km, stream_name="geminids")
    shielding = earth_shielding_factor(altitude_km)
    focusing = gravitational_focusing_factor(altitude_km)
    expected = result["total_m2_s"] * shielding * focusing
    assert result["near_earth_m2_s"] == _approx(expected)
    assert result["shielding_factor"] == _approx(shielding)
    assert result["focusing_factor"] == _approx(focusing)


def test_near_earth_flux_leo_shielding_and_focusing_partially_cancel():
    mass_g = 1e-6
    background = grun_cumulative_flux(mass_g)
    result = near_earth_flux(mass_g, altitude_km=400.0)
    ratio = result["near_earth_m2_s"] / background
    assert 0.9 < ratio < 1.5


def load_tests(loader, standard_tests, pattern):
    import sys as _sys
    g = _sys.modules[__name__].__dict__
    names = [n for n in g if n.startswith("test_") and callable(g[n])]
    tc = type("TestLeaf", (_unittest.TestCase,), {n: (lambda self, _n=n, _f=g[n]: _f()) for n in names})
    return _unittest.TestLoader().loadTestsFromTestCase(tc)

if __name__ == "__main__":
    _unittest.main()
