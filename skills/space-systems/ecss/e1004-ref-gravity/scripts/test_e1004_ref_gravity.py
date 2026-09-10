

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

import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

from e1004_ref_gravity_logic import (
    EARTH_RADIUS_KM,
    GM_EARTH_KM3_S2,
    GM_MOON_KM3_S2,
    GM_SUN_KM3_S2,
    circular_orbit_velocity_km_s,
    escape_velocity_km_s,
    gm_for_body,
    is_gravity_model_compliant,
    j2_perturbation_acceleration_km_s2,
    missing_gravity_model_terms,
    point_mass_gravity_accel_km_s2,
    significant_gravity_terms,
    tidal_acceleration_km_s2,
)

LEO_RADIUS_KM = EARTH_RADIUS_KM + 400.0
MOON_DISTANCE_KM = 384400.0
SUN_DISTANCE_KM = 1.496e8


def test_gm_for_body_known_bodies_case_insensitive():
    assert gm_for_body("earth") == GM_EARTH_KM3_S2
    assert gm_for_body("EARTH") == GM_EARTH_KM3_S2
    assert gm_for_body("Moon") == GM_MOON_KM3_S2
    assert gm_for_body("sun") == GM_SUN_KM3_S2


def test_gm_for_body_unknown_raises():
    with _raises(ValueError):
        gm_for_body("mars")


def test_point_mass_gravity_accel_matches_known_surface_gravity():
    surface_accel_m_s2 = (
        point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, EARTH_RADIUS_KM) * 1000.0
    )
    assert surface_accel_m_s2 == _approx(9.80665, rel=0.02)


def test_point_mass_gravity_accel_rejects_non_positive_inputs():
    with _raises(ValueError):
        point_mass_gravity_accel_km_s2(0.0, EARTH_RADIUS_KM)
    with _raises(ValueError):
        point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, 0.0)
    with _raises(ValueError):
        point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, -1.0)


def test_point_mass_gravity_decreases_with_radius():
    near = point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, EARTH_RADIUS_KM)
    far = point_mass_gravity_accel_km_s2(GM_EARTH_KM3_S2, LEO_RADIUS_KM)
    assert near > far > 0


def test_escape_velocity_equals_sqrt2_times_circular_velocity():
    circular = circular_orbit_velocity_km_s(GM_EARTH_KM3_S2, LEO_RADIUS_KM)
    escape = escape_velocity_km_s(GM_EARTH_KM3_S2, LEO_RADIUS_KM)
    assert escape == _approx(circular * (2.0**0.5))


def test_circular_and_escape_velocity_reject_non_positive_inputs():
    with _raises(ValueError):
        circular_orbit_velocity_km_s(-1.0, LEO_RADIUS_KM)
    with _raises(ValueError):
        circular_orbit_velocity_km_s(GM_EARTH_KM3_S2, 0.0)
    with _raises(ValueError):
        escape_velocity_km_s(-1.0, LEO_RADIUS_KM)
    with _raises(ValueError):
        escape_velocity_km_s(GM_EARTH_KM3_S2, 0.0)


def test_j2_perturbation_larger_at_pole_than_equator():
    equator = j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM, 0.0)
    pole = j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM, 90.0)
    assert pole > equator > 0


def test_j2_perturbation_decreases_with_radius():
    low = j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM, 30.0)
    high = j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM * 4.0, 30.0)
    assert low > high > 0


def test_j2_perturbation_rejects_below_surface_radius():
    with _raises(ValueError):
        j2_perturbation_acceleration_km_s2(EARTH_RADIUS_KM - 1.0, 0.0)


def test_j2_perturbation_rejects_out_of_range_latitude():
    with _raises(ValueError):
        j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM, 90.1)
    with _raises(ValueError):
        j2_perturbation_acceleration_km_s2(LEO_RADIUS_KM, -90.1)


def test_tidal_acceleration_scales_with_orbit_radius():
    inner = tidal_acceleration_km_s2(GM_MOON_KM3_S2, LEO_RADIUS_KM, MOON_DISTANCE_KM)
    outer = tidal_acceleration_km_s2(
        GM_MOON_KM3_S2, LEO_RADIUS_KM * 2.0, MOON_DISTANCE_KM
    )
    assert outer == _approx(inner * 2.0)


def test_tidal_acceleration_rejects_third_body_no_farther_than_orbit():
    with _raises(ValueError):
        tidal_acceleration_km_s2(GM_MOON_KM3_S2, MOON_DISTANCE_KM, LEO_RADIUS_KM)


def test_tidal_acceleration_rejects_non_positive_inputs():
    with _raises(ValueError):
        tidal_acceleration_km_s2(-1.0, LEO_RADIUS_KM, MOON_DISTANCE_KM)
    with _raises(ValueError):
        tidal_acceleration_km_s2(GM_MOON_KM3_S2, 0.0, MOON_DISTANCE_KM)


def test_significant_gravity_terms_flags_j2_required_at_leo():
    assessment = significant_gravity_terms(
        LEO_RADIUS_KM, 0.0, MOON_DISTANCE_KM, SUN_DISTANCE_KM
    )
    assert assessment["point_mass_km_s2"] > 0
    assert assessment["terms"]["j2"]["required"] is True


def test_significant_gravity_terms_does_not_flag_third_body_at_leo():
    assessment = significant_gravity_terms(
        LEO_RADIUS_KM, 0.0, MOON_DISTANCE_KM, SUN_DISTANCE_KM
    )
    assert assessment["terms"]["lunar_third_body"]["required"] is False
    assert assessment["terms"]["solar_third_body"]["required"] is False


def test_missing_gravity_model_terms_empty_when_j2_modeled():
    assessment = significant_gravity_terms(
        LEO_RADIUS_KM, 0.0, MOON_DISTANCE_KM, SUN_DISTANCE_KM
    )
    missing = missing_gravity_model_terms(assessment, modeled_terms={"j2"})
    assert missing == []
    assert is_gravity_model_compliant(missing) is True


def test_missing_gravity_model_terms_flags_missing_j2():
    assessment = significant_gravity_terms(
        LEO_RADIUS_KM, 0.0, MOON_DISTANCE_KM, SUN_DISTANCE_KM
    )
    missing = missing_gravity_model_terms(assessment, modeled_terms=set())
    assert missing == ["j2"]
    assert is_gravity_model_compliant(missing) is False


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
