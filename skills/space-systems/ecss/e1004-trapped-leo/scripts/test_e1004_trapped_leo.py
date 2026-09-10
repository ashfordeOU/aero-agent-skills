

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

"""Tests for the trapped LEO electron environment logic (ECSS-E-ST-10-04C 9.2.1.2)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import e1004_trapped_leo_logic as logic  # noqa: E402


def test_geodetic_to_bl_equator_l_matches_altitude_radius():
    bl = logic.geodetic_to_bl(altitude_km=500.0, geomagnetic_latitude_deg=0.0)
    expected_r_re = 1.0 + 500.0 / logic.EARTH_RADIUS_KM
    assert math.isclose(bl.l_shell, expected_r_re, rel_tol=1e-9)
    assert math.isclose(bl.b_over_b0, 1.0, rel_tol=1e-9)


def test_geodetic_to_bl_l_increases_with_latitude():
    equator = logic.geodetic_to_bl(altitude_km=500.0, geomagnetic_latitude_deg=0.0)
    mid_lat = logic.geodetic_to_bl(altitude_km=500.0, geomagnetic_latitude_deg=40.0)
    assert mid_lat.l_shell > equator.l_shell


def test_geodetic_to_bl_rejects_negative_altitude():
    try:
        logic.geodetic_to_bl(altitude_km=-1.0, geomagnetic_latitude_deg=0.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for negative altitude")


def test_flux_differential_decreases_with_energy():
    low_e = logic.flux_differential(energy_mev=0.1, l_shell=4.0)
    high_e = logic.flux_differential(energy_mev=1.0, l_shell=4.0)
    assert low_e > high_e > 0


def test_flux_integral_decreases_with_energy():
    low_e = logic.flux_integral(energy_mev=0.1, l_shell=4.0)
    high_e = logic.flux_integral(energy_mev=1.0, l_shell=4.0)
    assert low_e > high_e > 0


def test_flux_integral_rejects_non_positive_energy():
    try:
        logic.flux_integral(energy_mev=0.0, l_shell=4.0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for non-positive energy")


def test_outer_belt_peak_exceeds_inner_belt_and_far_tail():
    inner = logic.flux_integral(energy_mev=0.5, l_shell=1.5)
    peak = logic.flux_integral(energy_mev=0.5, l_shell=4.0)
    tail = logic.flux_integral(energy_mev=0.5, l_shell=7.0)
    assert peak > inner
    assert peak > tail


def test_l_shell_table_lookup_clamps_outside_grid():
    below_grid = logic.flux_integral(energy_mev=0.5, l_shell=0.5)
    at_min = logic.flux_integral(energy_mev=0.5, l_shell=logic.MIN_L)
    above_grid = logic.flux_integral(energy_mev=0.5, l_shell=20.0)
    at_max = logic.flux_integral(energy_mev=0.5, l_shell=logic.MAX_L)
    assert math.isclose(below_grid, at_min, rel_tol=1e-9)
    assert math.isclose(above_grid, at_max, rel_tol=1e-9)


def test_b_attenuation_reduces_off_equator_flux():
    equatorial = logic.flux_integral(energy_mev=0.5, l_shell=4.0, b_over_b0=1.0)
    off_equator = logic.flux_integral(energy_mev=0.5, l_shell=4.0, b_over_b0=2.0)
    assert off_equator < equatorial


def test_orbit_average_flux_flags_saa_dominance_for_low_inclination_leo():
    orbit = logic.OrbitDefinition(altitude_km=500.0, inclination_deg=51.6, n_samples=180)
    result = logic.orbit_average_flux(orbit, energy_mev=0.5, saa_l_threshold=2.0)

    assert result["n_samples"] == 180
    assert 0.0 <= result["saa_time_fraction"] <= 1.0
    assert result["mean_flux_cm2_s"] >= 0.0
    assert result["saa_mean_flux_cm2_s"] >= 0.0


def test_orbit_average_flux_rejects_zero_samples():
    orbit = logic.OrbitDefinition(altitude_km=500.0, inclination_deg=51.6, n_samples=0)
    try:
        logic.orbit_average_flux(orbit, energy_mev=0.5)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for zero samples")


def test_skill_md_description_has_bare_action_verb_and_no_forbidden_word():
    skill_md_path = os.path.join(os.path.dirname(__file__), os.pardir, "SKILL.md")
    with open(skill_md_path, encoding="utf-8") as handle:
        content = handle.read()

    forbidden = "class" + "ified"
    assert forbidden not in content.lower()

    description_line = next(
        line for line in content.splitlines() if line.startswith("description:")
    )
    first_word = description_line.split(":", 1)[1].strip().split()[0].strip("\"'")
    assert first_word.lower() in ("use", "compute", "define", "apply", "select", "run", "verify", "prepare", "determine", "assess", "produce", "perform", "support", "guide", "structure", "coordinate", "identify", "classify", "execute", "optimize", "calibrate", "maintain", "derive", "allocate", "estimate", "check", "validate")


def load_tests(loader, standard_tests, pattern):
    import sys as _sys
    g = _sys.modules[__name__].__dict__
    names = [n for n in g if n.startswith("test_") and callable(g[n])]
    tc = type("TestLeaf", (_unittest.TestCase,), {n: (lambda self, _n=n, _f=g[n]: _f()) for n in names})
    return _unittest.TestLoader().loadTestsFromTestCase(tc)

if __name__ == "__main__":
    _unittest.main()
