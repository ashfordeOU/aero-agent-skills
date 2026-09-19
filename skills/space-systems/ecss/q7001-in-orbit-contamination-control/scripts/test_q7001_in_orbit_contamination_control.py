"""Contract tests for the in-orbit self-contamination budget logic."""

import math
import unittest

from q7001_in_orbit_contamination_control_logic import (
    DEFAULT_DEPOSIT_DENSITY_KG_PER_M3,
    SECONDS_PER_DAY,
    assess_in_orbit_contamination,
    film_thickness_nm,
    outgassed_mass_kg,
    particle_obscuration_ppm,
    source_deposit_kg_per_m2,
    sticking_coefficient,
    thruster_deposit_kg_per_m2,
    validate_source,
)


def _source(**overrides):
    source = {
        "name": "mli-blanket",
        "area_m2": 12.0,
        "initial_rate_kg_per_m2_s": 2.0e-13,
        "decay_time_constant_days": 30.0,
        "view_factor": 0.02,
    }
    source.update(overrides)
    return source


def _budget(**overrides):
    budget = {
        "sources": [
            _source(),
            _source(
                name="harness-potting",
                area_m2=0.8,
                initial_rate_kg_per_m2_s=6.0e-13,
                decay_time_constant_days=10.0,
                view_factor=0.05,
            ),
        ],
        "mission_days": 365.0,
        "surface_area_m2": 0.5,
        "surface_temperature_k": 200.0,
        "allocation_nm": 100.0,
    }
    budget.update(overrides)
    return budget


class SourceValidationTests(unittest.TestCase):
    def test_valid_source_normalizes(self):
        normalized = validate_source(_source())
        self.assertAlmostEqual(normalized["view_factor"], 0.02)

    def test_missing_key_rejected(self):
        broken = _source()
        del broken["view_factor"]
        with self.assertRaises(ValueError):
            validate_source(broken)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source(area_m2=0.0))

    def test_zero_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source(decay_time_constant_days=0.0))

    def test_view_factor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source(view_factor=1.4))

    def test_negative_view_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(_source(view_factor=-0.01))

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_source("mli-blanket")


class OutgassingTests(unittest.TestCase):
    def test_mass_matches_the_analytic_integral(self):
        source = _source()
        tau_s = 30.0 * SECONDS_PER_DAY
        window_s = 90.0 * SECONDS_PER_DAY
        expected = 2.0e-13 * 12.0 * tau_s * (1.0 - math.exp(-window_s / tau_s))
        self.assertAlmostEqual(outgassed_mass_kg(source, 90.0), expected, places=15)

    def test_zero_mission_emits_nothing(self):
        self.assertAlmostEqual(outgassed_mass_kg(_source(), 0.0), 0.0, places=18)

    def test_emission_saturates_at_long_mission(self):
        one_year = outgassed_mass_kg(_source(), 365.0)
        ten_years = outgassed_mass_kg(_source(), 3650.0)
        ceiling = 2.0e-13 * 12.0 * (30.0 * SECONDS_PER_DAY)
        # Ten years is 121 time constants: exp(-121) is about 1e-53, below the
        # last bit of one, so (1 - exp) is exactly 1.0 and the integral lands
        # ON the ceiling rather than asymptotically near it.
        self.assertEqual(ten_years, ceiling)
        # One year is 12 time constants, still measurably short of it.
        self.assertLess(one_year, ceiling)
        self.assertGreater(ten_years, one_year)

    def test_longer_time_constant_emits_more_over_the_same_window(self):
        quick = outgassed_mass_kg(_source(decay_time_constant_days=5.0), 30.0)
        slow = outgassed_mass_kg(_source(decay_time_constant_days=100.0), 30.0)
        self.assertGreater(slow, quick)

    def test_negative_mission_rejected(self):
        with self.assertRaises(ValueError):
            outgassed_mass_kg(_source(), -1.0)

    def test_non_numeric_mission_rejected(self):
        with self.assertRaises(ValueError):
            outgassed_mass_kg(_source(), "365")


class StickingTests(unittest.TestCase):
    def test_cold_surface_keeps_everything(self):
        self.assertAlmostEqual(sticking_coefficient(100.0), 1.0, places=12)

    def test_warm_surface_keeps_nothing(self):
        self.assertAlmostEqual(sticking_coefficient(400.0), 0.0, places=12)

    def test_midpoint_keeps_half(self):
        self.assertAlmostEqual(sticking_coefficient(250.0), 0.5, places=12)

    def test_taper_is_monotone(self):
        values = [sticking_coefficient(t) for t in (160.0, 200.0, 250.0, 300.0, 340.0)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            sticking_coefficient(0.0)


class DepositTests(unittest.TestCase):
    def test_deposit_scales_with_the_view_factor(self):
        low = source_deposit_kg_per_m2(_source(view_factor=0.01), 100.0, 200.0, 0.5)
        high = source_deposit_kg_per_m2(_source(view_factor=0.02), 100.0, 200.0, 0.5)
        self.assertAlmostEqual(high, 2.0 * low, places=18)

    def test_deposit_scales_inversely_with_receiving_area(self):
        small = source_deposit_kg_per_m2(_source(), 100.0, 200.0, 0.5)
        large = source_deposit_kg_per_m2(_source(), 100.0, 200.0, 1.0)
        self.assertAlmostEqual(small, 2.0 * large, places=18)

    def test_warm_surface_collects_nothing(self):
        value = source_deposit_kg_per_m2(_source(), 100.0, 400.0, 0.5)
        self.assertAlmostEqual(value, 0.0, places=18)

    def test_zero_receiving_area_rejected(self):
        with self.assertRaises(ValueError):
            source_deposit_kg_per_m2(_source(), 100.0, 200.0, 0.0)


class ThrusterTests(unittest.TestCase):
    def test_no_firings_deposit_nothing(self):
        self.assertAlmostEqual(thruster_deposit_kg_per_m2([], 200.0, 0.5), 0.0)

    def test_backflow_matches_the_closed_form(self):
        firings = [{"propellant_kg": 4.0, "backflow_fraction": 0.01, "view_factor": 0.25}]
        expected = 4.0 * 0.01 * 0.25 * sticking_coefficient(200.0) / 0.5
        self.assertAlmostEqual(
            thruster_deposit_kg_per_m2(firings, 200.0, 0.5), expected, places=15
        )

    def test_firings_accumulate(self):
        one = [{"propellant_kg": 4.0, "backflow_fraction": 0.01, "view_factor": 0.25}]
        two = one * 2
        self.assertAlmostEqual(
            thruster_deposit_kg_per_m2(two, 200.0, 0.5),
            2.0 * thruster_deposit_kg_per_m2(one, 200.0, 0.5),
            places=15,
        )

    def test_a_thruster_with_no_view_deposits_nothing(self):
        firings = [{"propellant_kg": 40.0, "backflow_fraction": 0.05, "view_factor": 0.0}]
        self.assertAlmostEqual(thruster_deposit_kg_per_m2(firings, 200.0, 0.5), 0.0)

    def test_backflow_fraction_above_one_rejected(self):
        firings = [{"propellant_kg": 4.0, "backflow_fraction": 1.2, "view_factor": 0.2}]
        with self.assertRaises(ValueError):
            thruster_deposit_kg_per_m2(firings, 200.0, 0.5)

    def test_missing_firing_key_rejected(self):
        with self.assertRaises(ValueError):
            thruster_deposit_kg_per_m2([{"propellant_kg": 4.0}], 200.0, 0.5)


class ParticleTests(unittest.TestCase):
    def test_no_particles_give_no_obscuration(self):
        self.assertAlmostEqual(particle_obscuration_ppm([], 0.5), 0.0)

    def test_obscuration_matches_the_projected_area(self):
        released = [{"diameter_micron": 100.0, "count": 50, "capture_fraction": 1.0}]
        expected = 1.0e6 * 50 * math.pi * (0.5 * 100.0e-6) ** 2 / 0.5
        self.assertAlmostEqual(particle_obscuration_ppm(released, 0.5), expected, places=12)

    def test_capture_fraction_scales_the_obscuration(self):
        full = [{"diameter_micron": 100.0, "count": 50, "capture_fraction": 1.0}]
        half = [{"diameter_micron": 100.0, "count": 50, "capture_fraction": 0.5}]
        self.assertAlmostEqual(
            particle_obscuration_ppm(half, 0.5),
            0.5 * particle_obscuration_ppm(full, 0.5),
            places=12,
        )

    def test_negative_count_rejected(self):
        released = [{"diameter_micron": 100.0, "count": -1, "capture_fraction": 1.0}]
        with self.assertRaises(ValueError):
            particle_obscuration_ppm(released, 0.5)

    def test_capture_fraction_above_one_rejected(self):
        released = [{"diameter_micron": 100.0, "count": 5, "capture_fraction": 1.5}]
        with self.assertRaises(ValueError):
            particle_obscuration_ppm(released, 0.5)


class ThicknessTests(unittest.TestCase):
    def test_thickness_matches_mass_over_density(self):
        value = film_thickness_nm(1.1e-6)
        self.assertAlmostEqual(value, 1.1e-6 / DEFAULT_DEPOSIT_DENSITY_KG_PER_M3 * 1e9,
                               places=9)

    def test_zero_deposit_is_zero_thickness(self):
        self.assertAlmostEqual(film_thickness_nm(0.0), 0.0)

    def test_denser_deposit_is_thinner(self):
        light = film_thickness_nm(1.0e-6, 900.0)
        heavy = film_thickness_nm(1.0e-6, 1800.0)
        self.assertAlmostEqual(heavy, light / 2.0, places=9)

    def test_negative_deposit_rejected(self):
        with self.assertRaises(ValueError):
            film_thickness_nm(-1.0e-6)

    def test_zero_density_rejected(self):
        with self.assertRaises(ValueError):
            film_thickness_nm(1.0e-6, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_generous_allocation_is_held(self):
        result = assess_in_orbit_contamination(_budget())
        self.assertTrue(result["within_allocation"])
        self.assertEqual(result["findings"], [])

    def test_total_is_the_sum_of_contributions(self):
        result = assess_in_orbit_contamination(_budget())
        total = sum(entry["deposit_kg_per_m2"] for entry in result["contributions"])
        self.assertAlmostEqual(result["total_deposit_kg_per_m2"], total, places=18)

    def test_tight_allocation_is_broken(self):
        result = assess_in_orbit_contamination(_budget(allocation_nm=0.001))
        self.assertFalse(result["within_allocation"])
        self.assertTrue(any("deposited film" in note for note in result["findings"]))

    def test_dominant_source_is_named(self):
        result = assess_in_orbit_contamination(_budget())
        names = [entry["name"] for entry in result["contributions"]]
        self.assertIn(result["dominant_source"], names)

    def test_thruster_firings_appear_as_their_own_contribution(self):
        budget = _budget(
            firings=[{"propellant_kg": 20.0, "backflow_fraction": 0.02, "view_factor": 0.3}]
        )
        result = assess_in_orbit_contamination(budget)
        names = [entry["name"] for entry in result["contributions"]]
        self.assertIn("thruster-plume-backflow", names)

    def test_thruster_backflow_can_dominate_the_budget(self):
        budget = _budget(
            allocation_nm=1.0e6,
            firings=[{"propellant_kg": 40.0, "backflow_fraction": 0.05, "view_factor": 0.4}],
        )
        result = assess_in_orbit_contamination(budget)
        self.assertEqual(result["dominant_source"], "thruster-plume-backflow")

    def test_particles_are_reported_separately_from_the_film(self):
        budget = _budget(
            released_particles=[
                {"diameter_micron": 200.0, "count": 30, "capture_fraction": 0.5}
            ]
        )
        result = assess_in_orbit_contamination(budget)
        self.assertGreater(result["particle_obscuration_ppm"], 0.0)
        self.assertTrue(result["within_allocation"])

    def test_particle_allocation_can_fail_on_its_own(self):
        budget = _budget(
            released_particles=[
                {"diameter_micron": 500.0, "count": 400, "capture_fraction": 1.0}
            ],
            obscuration_allocation_ppm=1.0,
        )
        result = assess_in_orbit_contamination(budget)
        self.assertFalse(result["within_allocation"])
        self.assertTrue(any("obscuration" in note for note in result["findings"]))

    def test_a_warm_surface_is_flagged_rather_than_silently_clean(self):
        result = assess_in_orbit_contamination(_budget(surface_temperature_k=400.0))
        self.assertFalse(result["within_allocation"])
        self.assertTrue(any("warm enough" in note for note in result["findings"]))

    def test_margin_is_allocation_less_total(self):
        result = assess_in_orbit_contamination(_budget())
        self.assertAlmostEqual(
            result["thickness_margin_nm"],
            100.0 - result["total_thickness_nm"],
            places=9,
        )

    def test_duplicate_source_name_rejected(self):
        budget = _budget()
        budget["sources"] = list(budget["sources"]) + [_source()]
        with self.assertRaises(ValueError):
            assess_in_orbit_contamination(budget)

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_in_orbit_contamination(_budget(sources=[]))

    def test_missing_budget_key_rejected(self):
        budget = _budget()
        del budget["allocation_nm"]
        with self.assertRaises(ValueError):
            assess_in_orbit_contamination(budget)

    def test_non_mapping_budget_rejected(self):
        with self.assertRaises(ValueError):
            assess_in_orbit_contamination(["sources"])


if __name__ == "__main__":
    unittest.main()
