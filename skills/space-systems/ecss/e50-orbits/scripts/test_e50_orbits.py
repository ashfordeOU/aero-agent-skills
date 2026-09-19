"""Contract tests for the clause 5.6.5 orbit and link implication logic."""

import unittest

from e50_orbits_logic import (
    COMPLIANT,
    DECLARATION_INCOMPLETE,
    EARTH_RADIUS_KM,
    OUT_OF_ALLOWANCE,
    assess_orbits,
    link_implications,
    max_doppler_shift_hz,
    max_pass_duration_s,
    max_range_rate_km_s,
    normalize_phases,
    one_way_delay_s,
    orbital_period_s,
    orbital_radius_km,
    orbital_speed_km_s,
    orphan_orbit_declarations,
    round_trip_delay_s,
    slant_range_km,
    undeclared_phases,
    validate_altitude_km,
    validate_elevation_deg,
    validate_frequency_hz,
    within_allowance,
)

# Reference values computed independently from the closed-form geometry for a
# 700 km circular orbit seen above a 5 degree mask, and for a 35786 km orbit
# above a 10 degree mask. Tolerances are far wider than libm rounding noise
# and far tighter than any modelling error worth catching.
LEO_H = 700.0
LEO_MASK = 5.0
GEO_H = 35786.0
GEO_MASK = 10.0
X_BAND_HZ = 8.2e9

LEO_SLANT_KM = 2563.148152076
LEO_SPEED_KM_S = 7.504286490
LEO_PERIOD_S = 5926.379071134
LEO_RANGE_RATE_KM_S = 3.253882545
LEO_PASS_S = 696.214130356
LEO_ONE_WAY_S = 0.008549741942
LEO_DOPPLER_HZ = 89001.027747924
GEO_SLANT_KM = 40586.098590898
GEO_ROUND_TRIP_S = 0.270761305082


def _mission(**overrides):
    base = {
        "phases": ("leop", "cruise", "science"),
        "orbits": {
            "leop": {"altitude_km": LEO_H, "min_elevation_deg": LEO_MASK},
            "cruise": {"altitude_km": LEO_H, "min_elevation_deg": LEO_MASK},
            "science": {"altitude_km": LEO_H, "min_elevation_deg": LEO_MASK},
        },
        "carrier_hz": X_BAND_HZ,
        "allowances": {
            "max_round_trip_delay_s": 0.1,
            "max_doppler_shift_hz": 150000.0,
            "min_pass_duration_s": 300.0,
        },
    }
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_zero_altitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_altitude_km(0.0)

    def test_boolean_altitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_altitude_km(True)

    def test_infinite_altitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_altitude_km(float("inf"))

    def test_elevation_at_ninety_rejected(self):
        with self.assertRaises(ValueError):
            validate_elevation_deg(90.0)

    def test_negative_elevation_rejected(self):
        with self.assertRaises(ValueError):
            validate_elevation_deg(-1.0)

    def test_zero_elevation_accepted(self):
        self.assertAlmostEqual(validate_elevation_deg(0.0), 0.0, places=9)

    def test_zero_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz(0.0)

    def test_repeated_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phases(["leop", "leop"])

    def test_blank_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phases([" "])

    def test_bare_string_is_not_a_phase_list(self):
        with self.assertRaises(ValueError):
            normalize_phases("leop")

    def test_iterator_is_taken_once(self):
        phases = iter(["leop", "cruise"])
        taken = normalize_phases(phases)
        self.assertEqual(taken, ("leop", "cruise"))


class GeometryTests(unittest.TestCase):
    def test_orbit_radius_adds_the_earth_radius(self):
        self.assertAlmostEqual(orbital_radius_km(LEO_H), EARTH_RADIUS_KM + LEO_H, places=9)

    def test_leo_speed(self):
        self.assertAlmostEqual(orbital_speed_km_s(LEO_H), LEO_SPEED_KM_S, places=6)

    def test_leo_period(self):
        self.assertAlmostEqual(orbital_period_s(LEO_H), LEO_PERIOD_S, places=6)

    def test_leo_slant_range_at_the_mask(self):
        self.assertAlmostEqual(slant_range_km(LEO_H, LEO_MASK), LEO_SLANT_KM, places=6)

    def test_slant_range_grows_as_the_mask_drops(self):
        low = slant_range_km(LEO_H, 0.0)
        high = slant_range_km(LEO_H, 30.0)
        self.assertGreater(low - high, 1.0)

    def test_geo_slant_range_at_the_mask(self):
        self.assertAlmostEqual(slant_range_km(GEO_H, GEO_MASK), GEO_SLANT_KM, places=6)

    def test_leo_one_way_delay(self):
        self.assertAlmostEqual(one_way_delay_s(LEO_SLANT_KM), LEO_ONE_WAY_S, places=12)

    def test_round_trip_is_twice_the_one_way(self):
        self.assertAlmostEqual(
            round_trip_delay_s(LEO_SLANT_KM), 2.0 * one_way_delay_s(LEO_SLANT_KM), places=12
        )

    def test_geo_round_trip_delay(self):
        self.assertAlmostEqual(
            round_trip_delay_s(GEO_SLANT_KM), GEO_ROUND_TRIP_S, places=9
        )

    def test_negative_range_rejected(self):
        with self.assertRaises(ValueError):
            one_way_delay_s(-1.0)

    def test_leo_range_rate(self):
        self.assertAlmostEqual(max_range_rate_km_s(LEO_H), LEO_RANGE_RATE_KM_S, places=6)

    def test_leo_doppler_at_x_band(self):
        self.assertAlmostEqual(
            max_doppler_shift_hz(X_BAND_HZ, LEO_H), LEO_DOPPLER_HZ, places=4
        )

    def test_doppler_scales_with_the_carrier(self):
        self.assertAlmostEqual(
            max_doppler_shift_hz(2.0 * X_BAND_HZ, LEO_H),
            2.0 * max_doppler_shift_hz(X_BAND_HZ, LEO_H),
            places=4,
        )

    def test_leo_pass_duration(self):
        self.assertAlmostEqual(max_pass_duration_s(LEO_H, LEO_MASK), LEO_PASS_S, places=6)

    def test_pass_shortens_as_the_mask_rises(self):
        self.assertGreater(
            max_pass_duration_s(LEO_H, 0.0) - max_pass_duration_s(LEO_H, 30.0), 1.0
        )


class AllowanceTests(unittest.TestCase):
    def test_value_on_a_maximum_is_inside_it(self):
        self.assertTrue(within_allowance(0.1, 0.1, "max"))

    def test_value_over_a_maximum_is_outside(self):
        self.assertFalse(within_allowance(0.2, 0.1, "max"))

    def test_value_on_a_minimum_is_inside_it(self):
        self.assertTrue(within_allowance(300.0, 300.0, "min"))

    def test_value_under_a_minimum_is_outside(self):
        self.assertFalse(within_allowance(200.0, 300.0, "min"))

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            within_allowance(1.0, 1.0, "either")


class ImplicationTests(unittest.TestCase):
    def test_implications_carry_every_derived_term(self):
        derived = link_implications(
            {"altitude_km": LEO_H, "min_elevation_deg": LEO_MASK}, X_BAND_HZ
        )
        for key in (
            "slant_range_km",
            "one_way_delay_s",
            "round_trip_delay_s",
            "max_doppler_shift_hz",
            "max_pass_duration_s",
        ):
            self.assertIn(key, derived)

    def test_implications_match_the_standalone_terms(self):
        derived = link_implications(
            {"altitude_km": LEO_H, "min_elevation_deg": LEO_MASK}, X_BAND_HZ
        )
        self.assertAlmostEqual(derived["slant_range_km"], LEO_SLANT_KM, places=6)
        self.assertAlmostEqual(derived["max_pass_duration_s"], LEO_PASS_S, places=6)

    def test_orbit_without_an_altitude_rejected(self):
        with self.assertRaises(ValueError):
            link_implications({"min_elevation_deg": LEO_MASK}, X_BAND_HZ)

    def test_non_mapping_orbit_rejected(self):
        with self.assertRaises(ValueError):
            link_implications([LEO_H, LEO_MASK], X_BAND_HZ)


class DeclarationTests(unittest.TestCase):
    def test_every_phase_declared_leaves_no_gap(self):
        mission = _mission()
        self.assertEqual(undeclared_phases(mission["phases"], mission["orbits"]), ())

    def test_missing_orbit_is_reported_in_mission_order(self):
        mission = _mission()
        orbits = {k: v for k, v in mission["orbits"].items() if k != "cruise"}
        self.assertEqual(undeclared_phases(mission["phases"], orbits), ("cruise",))

    def test_orbit_for_an_unknown_phase_is_an_orphan(self):
        mission = _mission()
        orbits = dict(mission["orbits"])
        orbits["disposal"] = {"altitude_km": 300.0, "min_elevation_deg": 5.0}
        self.assertEqual(orphan_orbit_declarations(mission["phases"], orbits), ("disposal",))


class AssessTests(unittest.TestCase):
    def test_declared_and_inside_allowance_is_compliant(self):
        result = assess_orbits(_mission())
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], ())

    def test_undeclared_phase_fails_the_first_item(self):
        mission = _mission()
        orbits = {k: v for k, v in mission["orbits"].items() if k != "science"}
        result = assess_orbits(_mission(orbits=orbits))
        self.assertEqual(result["verdict"], DECLARATION_INCOMPLETE)
        self.assertEqual(result["undeclared_phases"], ("science",))

    def test_orphan_declaration_fails_the_first_item(self):
        mission = _mission()
        orbits = dict(mission["orbits"])
        orbits["disposal"] = {"altitude_km": 300.0, "min_elevation_deg": 5.0}
        result = assess_orbits(_mission(orbits=orbits))
        self.assertEqual(result["verdict"], DECLARATION_INCOMPLETE)

    def test_doppler_beyond_pull_in_fails_the_second_item(self):
        result = assess_orbits(
            _mission(
                allowances={
                    "max_round_trip_delay_s": 0.1,
                    "max_doppler_shift_hz": 50000.0,
                    "min_pass_duration_s": 300.0,
                }
            )
        )
        self.assertEqual(result["verdict"], OUT_OF_ALLOWANCE)
        self.assertTrue(any("Doppler" in f for f in result["findings"]))

    def test_short_pass_fails_the_second_item(self):
        result = assess_orbits(
            _mission(
                allowances={
                    "max_round_trip_delay_s": 0.1,
                    "max_doppler_shift_hz": 150000.0,
                    "min_pass_duration_s": 1200.0,
                }
            )
        )
        self.assertEqual(result["verdict"], OUT_OF_ALLOWANCE)
        self.assertTrue(any("shorter than" in f for f in result["findings"]))

    def test_geo_round_trip_fails_a_leo_delay_allowance(self):
        mission = _mission(
            phases=("relay",),
            orbits={"relay": {"altitude_km": GEO_H, "min_elevation_deg": GEO_MASK}},
        )
        result = assess_orbits(mission)
        self.assertEqual(result["verdict"], OUT_OF_ALLOWANCE)
        self.assertTrue(any("round trip delay" in f for f in result["findings"]))

    def test_absent_allowance_is_not_a_finding(self):
        result = assess_orbits(_mission(allowances={}))
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_declaration_defect_outranks_an_allowance_breach(self):
        mission = _mission()
        orbits = {k: v for k, v in mission["orbits"].items() if k != "science"}
        result = assess_orbits(
            _mission(
                orbits=orbits,
                allowances={"max_doppler_shift_hz": 1.0},
            )
        )
        self.assertEqual(result["verdict"], DECLARATION_INCOMPLETE)

    def test_phase_count_is_reported(self):
        self.assertEqual(assess_orbits(_mission())["phase_count"], 3)

    def test_implications_are_returned_per_phase(self):
        result = assess_orbits(_mission())
        self.assertEqual(sorted(result["implications"]), ["cruise", "leop", "science"])

    def test_mission_without_a_carrier_rejected(self):
        with self.assertRaises(ValueError):
            assess_orbits(_mission(carrier_hz=None))

    def test_non_mapping_mission_rejected(self):
        with self.assertRaises(ValueError):
            assess_orbits(["leop"])


if __name__ == "__main__":
    unittest.main()
