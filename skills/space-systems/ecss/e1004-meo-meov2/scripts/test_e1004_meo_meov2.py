

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

"""Tests for the E-ST-10-04C Annex B.3 MEOv2 trapped-environment logic."""

import math


from e1004_meo_meov2_logic import (
    ENERGY_GRID,
    L_GRID,
    ELECTRON_LOG_FLUX,
    PROTON_LOG_FLUX,
    LShellCrossing,
    categorize_severity,
    integrate_fluence,
    interpolate_flux,
    orbit_averaged_spectrum,
)


# --- interpolate_flux --------------------------------------------------


def test_interpolate_flux_matches_grid_point_exactly():
    # At a tabulated (L, E) node the interpolation should reproduce the
    # stored value exactly (10 ** stored log10 flux).
    l_index, e_index = 4, 2
    expected = 10.0 ** ELECTRON_LOG_FLUX[l_index][e_index]
    actual = interpolate_flux("electron", L_GRID[l_index], ENERGY_GRID[e_index])
    assert actual == _approx(expected, rel=1e-9)


def test_interpolate_flux_proton_matches_grid_point_exactly():
    l_index, e_index = 6, 1
    expected = 10.0 ** PROTON_LOG_FLUX[l_index][e_index]
    actual = interpolate_flux("proton", L_GRID[l_index], ENERGY_GRID[e_index])
    assert actual == _approx(expected, rel=1e-9)


def test_interpolate_flux_midpoint_is_between_neighbors():
    l_lo, l_hi = L_GRID[0], L_GRID[1]
    mid_l = (l_lo + l_hi) / 2
    energy = ENERGY_GRID[0]
    flux_lo = interpolate_flux("electron", l_lo, energy)
    flux_hi = interpolate_flux("electron", l_hi, energy)
    flux_mid = interpolate_flux("electron", mid_l, energy)
    lo, hi = sorted((flux_lo, flux_hi))
    assert lo <= flux_mid <= hi


def test_interpolate_flux_clamps_below_grid_range():
    below_range = L_GRID[0] - 5.0
    at_edge = interpolate_flux("electron", L_GRID[0], ENERGY_GRID[0])
    clamped = interpolate_flux("electron", below_range, ENERGY_GRID[0])
    assert clamped == _approx(at_edge, rel=1e-9)


def test_interpolate_flux_clamps_above_grid_range():
    above_range = L_GRID[-1] + 5.0
    at_edge = interpolate_flux("proton", L_GRID[-1], ENERGY_GRID[-1])
    clamped = interpolate_flux("proton", above_range, ENERGY_GRID[-1] + 500.0)
    assert clamped == _approx(at_edge, rel=1e-9)


def test_interpolate_flux_rejects_unknown_species():
    with _raises(ValueError):
        interpolate_flux("muon", 3.0, 1.0)


def test_interpolate_flux_rejects_nonpositive_energy():
    with _raises(ValueError):
        interpolate_flux("electron", 3.0, 0.0)
    with _raises(ValueError):
        interpolate_flux("electron", 3.0, -1.0)


# --- orbit_averaged_spectrum --------------------------------------------


def test_orbit_averaged_spectrum_matches_single_crossing():
    crossings = [LShellCrossing(l_shell=3.0, dwell_seconds=1000.0)]
    spectrum = orbit_averaged_spectrum("electron", crossings, (1.0,))
    assert spectrum[1.0] == _approx(interpolate_flux("electron", 3.0, 1.0))


def test_orbit_averaged_spectrum_weights_by_dwell_time():
    # Two crossings with equal dwell time should average their fluxes;
    # heavily weighting one crossing should pull the average toward it.
    low_l, high_l = 1.5, 6.0
    energy = 1.0
    equal = orbit_averaged_spectrum(
        "electron",
        [
            LShellCrossing(l_shell=low_l, dwell_seconds=100.0),
            LShellCrossing(l_shell=high_l, dwell_seconds=100.0),
        ],
        (energy,),
    )[energy]
    flux_low = interpolate_flux("electron", low_l, energy)
    flux_high = interpolate_flux("electron", high_l, energy)
    assert equal == _approx((flux_low + flux_high) / 2.0, rel=1e-9)

    weighted_to_high = orbit_averaged_spectrum(
        "electron",
        [
            LShellCrossing(l_shell=low_l, dwell_seconds=1.0),
            LShellCrossing(l_shell=high_l, dwell_seconds=999.0),
        ],
        (energy,),
    )[energy]
    assert abs(weighted_to_high - flux_high) < abs(equal - flux_high)


def test_orbit_averaged_spectrum_rejects_empty_crossings():
    with _raises(ValueError):
        orbit_averaged_spectrum("electron", [])


def test_orbit_averaged_spectrum_rejects_zero_total_dwell():
    crossings = [LShellCrossing(l_shell=3.0, dwell_seconds=0.0)]
    with _raises(ValueError):
        orbit_averaged_spectrum("electron", crossings)


# --- integrate_fluence ---------------------------------------------------


def test_integrate_fluence_scales_linearly_with_mission_duration():
    crossings = [
        LShellCrossing(l_shell=1.3, dwell_seconds=1800.0),
        LShellCrossing(l_shell=5.0, dwell_seconds=3600.0),
    ]
    period = 21600.0
    short = integrate_fluence("proton", crossings, 1.0, period, period)
    long = integrate_fluence("proton", crossings, 1.0, period, period * 10)
    assert long == _approx(short * 10, rel=1e-9)


def test_integrate_fluence_rejects_nonpositive_period():
    crossings = [LShellCrossing(l_shell=3.0, dwell_seconds=100.0)]
    with _raises(ValueError):
        integrate_fluence("electron", crossings, 1.0, 0.0, 100.0)


def test_integrate_fluence_rejects_negative_mission_duration():
    crossings = [LShellCrossing(l_shell=3.0, dwell_seconds=100.0)]
    with _raises(ValueError):
        integrate_fluence("electron", crossings, 1.0, 100.0, -1.0)


# --- categorize_severity --------------------------------------------------


def test_categorize_severity_bands():
    for species, fluence, expected in [
        ("electron", 1.0e8, "benign"),
        ("electron", 1.0e10, "elevated"),
        ("electron", 1.0e12, "severe"),
        ("proton", 1.0e6, "benign"),
        ("proton", 1.0e8, "elevated"),
        ("proton", 1.0e10, "severe"),
    ]:
        assert categorize_severity(species, fluence) == expected


def test_categorize_severity_rejects_negative_fluence():
    with _raises(ValueError):
        categorize_severity("electron", -1.0)


def test_categorize_severity_rejects_unknown_species():
    with _raises(ValueError):
        categorize_severity("muon", 1.0)


def test_categorize_severity_never_returns_forbidden_word():
    # Regression guard: severity labels must be "categorized", never the
    # security-marking word the content-policy gate forbids.
    for species, fluence in (("electron", 1.0e12), ("proton", 1.0e10)):
        label = categorize_severity(species, fluence)
        assert "classif" not in label.lower()


def test_categorize_severity_handles_extreme_fluence():
    assert categorize_severity("electron", math.inf) == "severe"


def load_tests(loader, standard_tests, pattern):
    import sys as _sys
    g = _sys.modules[__name__].__dict__
    names = [n for n in g if n.startswith("test_") and callable(g[n])]
    tc = type("TestLeaf", (_unittest.TestCase,), {n: (lambda self, _n=n, _f=g[n]: _f()) for n in names})
    return _unittest.TestLoader().loadTestsFromTestCase(tc)

if __name__ == "__main__":
    _unittest.main()
