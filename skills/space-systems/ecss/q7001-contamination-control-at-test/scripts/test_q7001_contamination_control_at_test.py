"""Contract tests for the test-campaign contamination budget logic."""

import unittest

from q7001_contamination_control_at_test_logic import (
    BUDGET_TOLERANCE,
    CLEANROOM_FALLOUT_PPM_PER_HOUR,
    PROTECTION_TRANSMISSION,
    accumulate_campaign,
    assess_test_campaign,
    fallout_rate_ppm_per_hour,
    first_reclean_phase,
    phase_molecular_mg_per_m2,
    phase_particulate_ppm,
    protection_transmission,
    validate_phase,
)


def _phase(**overrides):
    phase = {
        "name": "vibration-x",
        "kind": "vibration",
        "cleanroom_class": "ISO-8",
        "exposure_hours": 10.0,
        "protection": "open",
    }
    phase.update(overrides)
    return phase


def _campaign(**overrides):
    campaign = {
        "phases": [
            _phase(name="incoming-handling", kind="handling", cleanroom_class="ISO-7",
                   exposure_hours=6.0, protection="open"),
            _phase(name="vibration-x", kind="vibration", cleanroom_class="ISO-8",
                   exposure_hours=8.0, protection="covered"),
            _phase(
                name="thermal-vacuum",
                kind="thermal-vacuum",
                cleanroom_class="ISO-7",
                exposure_hours=200.0,
                protection="open",
                shroud_delta_k=100.0,
                chamber_loading_factor=1.0,
            ),
            _phase(name="post-test-storage", kind="storage", cleanroom_class="ISO-6",
                   exposure_hours=300.0, protection="double-bagged"),
        ],
        "campaign_particulate_ppm": 3.0,
        "campaign_molecular_mg_per_m2": 5.0,
    }
    campaign.update(overrides)
    return campaign


class EnvironmentTests(unittest.TestCase):
    def test_cleaner_room_has_a_lower_fallout_rate(self):
        self.assertLess(
            fallout_rate_ppm_per_hour("ISO-5"), fallout_rate_ppm_per_hour("ISO-8")
        )

    def test_uncontrolled_is_the_worst_environment(self):
        worst = max(CLEANROOM_FALLOUT_PPM_PER_HOUR.values())
        self.assertAlmostEqual(fallout_rate_ppm_per_hour("uncontrolled"), worst)

    def test_unknown_cleanroom_class_rejected(self):
        with self.assertRaises(ValueError):
            fallout_rate_ppm_per_hour("ISO-9")

    def test_open_hardware_sees_the_whole_environment(self):
        self.assertAlmostEqual(protection_transmission("open"), 1.0)

    def test_no_protection_state_is_a_perfect_seal(self):
        for value in PROTECTION_TRANSMISSION.values():
            self.assertGreater(value, 0.0)

    def test_unknown_protection_rejected(self):
        with self.assertRaises(ValueError):
            protection_transmission("cling-film")


class PhaseValidationTests(unittest.TestCase):
    def test_valid_phase_normalizes_with_defaults(self):
        normalized = validate_phase(_phase())
        self.assertAlmostEqual(normalized["shroud_delta_k"], 0.0)
        self.assertIsNone(normalized["particulate_allocation_ppm"])

    def test_missing_key_rejected(self):
        broken = _phase()
        del broken["protection"]
        with self.assertRaises(ValueError):
            validate_phase(broken)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase(kind="shock"))

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase(exposure_hours=-1.0))

    def test_shroud_delta_on_a_non_vacuum_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase(shroud_delta_k=40.0))

    def test_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase(particulate_allocation_ppm=-0.1))

    def test_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase("vibration-x")


class PhaseContributionTests(unittest.TestCase):
    def test_particulate_is_rate_times_hours(self):
        value = phase_particulate_ppm(_phase(exposure_hours=10.0, protection="open"))
        self.assertAlmostEqual(value, 0.025 * 10.0, places=12)

    def test_protection_scales_the_particulate_pickup(self):
        openly = phase_particulate_ppm(_phase(protection="open"))
        bagged = phase_particulate_ppm(_phase(protection="double-bagged"))
        self.assertAlmostEqual(bagged, openly * 0.03, places=12)

    def test_zero_exposure_adds_nothing(self):
        self.assertAlmostEqual(phase_particulate_ppm(_phase(exposure_hours=0.0)), 0.0)

    def test_only_a_vacuum_phase_deposits_molecules(self):
        self.assertAlmostEqual(phase_molecular_mg_per_m2(_phase()), 0.0)

    def test_vacuum_deposition_scales_with_the_shroud_difference(self):
        warm = phase_molecular_mg_per_m2(
            _phase(name="tv", kind="thermal-vacuum", shroud_delta_k=50.0)
        )
        cold = phase_molecular_mg_per_m2(
            _phase(name="tv", kind="thermal-vacuum", shroud_delta_k=100.0)
        )
        self.assertAlmostEqual(cold, 2.0 * warm, places=12)

    def test_vacuum_deposition_scales_with_chamber_loading(self):
        light = phase_molecular_mg_per_m2(
            _phase(name="tv", kind="thermal-vacuum", shroud_delta_k=50.0,
                   chamber_loading_factor=1.0)
        )
        heavy = phase_molecular_mg_per_m2(
            _phase(name="tv", kind="thermal-vacuum", shroud_delta_k=50.0,
                   chamber_loading_factor=3.0)
        )
        self.assertAlmostEqual(heavy, 3.0 * light, places=12)

    def test_a_shroud_at_article_temperature_deposits_nothing(self):
        value = phase_molecular_mg_per_m2(
            _phase(name="tv", kind="thermal-vacuum", shroud_delta_k=0.0)
        )
        self.assertAlmostEqual(value, 0.0, places=12)


class AccumulationTests(unittest.TestCase):
    def test_one_row_per_phase(self):
        rows = accumulate_campaign(_campaign()["phases"])
        self.assertEqual(len(rows), 4)

    def test_cumulative_total_is_the_sum_of_the_additions(self):
        rows = accumulate_campaign(_campaign()["phases"])
        total = sum(row["added_particulate_ppm"] for row in rows)
        self.assertAlmostEqual(rows[-1]["cumulative_particulate_ppm"], total, places=12)

    def test_cumulative_never_decreases(self):
        rows = accumulate_campaign(_campaign()["phases"])
        values = [row["cumulative_particulate_ppm"] for row in rows]
        self.assertEqual(values, sorted(values))

    def test_duplicate_phase_name_rejected(self):
        phases = _campaign()["phases"] + [_phase(name="vibration-x")]
        with self.assertRaises(ValueError):
            accumulate_campaign(phases)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_campaign([])

    def test_no_allocation_means_no_reclean_point(self):
        rows = accumulate_campaign(_campaign()["phases"])
        self.assertIsNone(first_reclean_phase(rows))

    def test_first_breaching_phase_is_the_reclean_point(self):
        phases = [
            _phase(name="a", exposure_hours=1.0, particulate_allocation_ppm=1.0),
            _phase(name="b", exposure_hours=100.0, particulate_allocation_ppm=0.5),
            _phase(name="c", exposure_hours=100.0, particulate_allocation_ppm=0.1),
        ]
        rows = accumulate_campaign(phases)
        self.assertEqual(first_reclean_phase(rows), "b")

    def test_phase_exactly_on_its_allocation_is_not_a_breach(self):
        phases = [_phase(name="a", exposure_hours=10.0, particulate_allocation_ppm=0.25)]
        rows = accumulate_campaign(phases)
        self.assertIsNone(first_reclean_phase(rows))
        self.assertLessEqual(
            abs(rows[0]["added_particulate_ppm"] - 0.25), BUDGET_TOLERANCE
        )

    def test_malformed_row_rejected(self):
        with self.assertRaises(ValueError):
            first_reclean_phase([{"added_particulate_ppm": 1.0}])


class CampaignAssessmentTests(unittest.TestCase):
    def test_generous_budget_is_held(self):
        result = assess_test_campaign(_campaign())
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["findings"], [])

    def test_tight_budget_is_broken(self):
        result = assess_test_campaign(_campaign(campaign_particulate_ppm=0.01))
        self.assertFalse(result["within_budget"])
        self.assertTrue(any("campaign obscuration" in note for note in result["findings"]))

    def test_margin_is_allocation_less_total(self):
        result = assess_test_campaign(_campaign())
        self.assertAlmostEqual(
            result["particulate_margin_ppm"],
            3.0 - result["total_particulate_ppm"],
            places=12,
        )

    def test_dominant_phase_is_named(self):
        result = assess_test_campaign(_campaign())
        self.assertEqual(result["dominant_particulate_phase"], "thermal-vacuum")

    def test_starting_contamination_is_carried_in(self):
        clean = assess_test_campaign(_campaign())
        dirty = assess_test_campaign(_campaign(start_particulate_ppm=0.2))
        self.assertAlmostEqual(
            dirty["total_particulate_ppm"] - clean["total_particulate_ppm"],
            0.2,
            places=12,
        )

    def test_molecular_budget_is_tracked_separately(self):
        result = assess_test_campaign(_campaign(campaign_molecular_mg_per_m2=0.5))
        self.assertFalse(result["within_budget"])
        self.assertTrue(any("deposition" in note for note in result["findings"]))

    def test_phase_allocation_breach_names_a_reclean_point(self):
        campaign = _campaign()
        campaign["phases"] = list(campaign["phases"])
        campaign["phases"][0] = _phase(
            name="incoming-handling",
            kind="handling",
            cleanroom_class="uncontrolled",
            exposure_hours=40.0,
            protection="open",
            particulate_allocation_ppm=0.1,
        )
        result = assess_test_campaign(campaign)
        self.assertEqual(result["reclean_after_phase"], "incoming-handling")

    def test_missing_campaign_key_rejected(self):
        campaign = _campaign()
        del campaign["campaign_molecular_mg_per_m2"]
        with self.assertRaises(ValueError):
            assess_test_campaign(campaign)

    def test_negative_campaign_allocation_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_campaign(_campaign(campaign_particulate_ppm=-1.0))

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_campaign(["phases"])

    def test_bagging_a_long_storage_phase_saves_budget(self):
        campaign = _campaign()
        exposed = list(campaign["phases"])
        exposed[3] = _phase(
            name="post-test-storage",
            kind="storage",
            cleanroom_class="ISO-6",
            exposure_hours=300.0,
            protection="open",
        )
        bagged_total = assess_test_campaign(campaign)["total_particulate_ppm"]
        open_total = assess_test_campaign(_campaign(phases=exposed))["total_particulate_ppm"]
        self.assertLess(bagged_total, open_total)


if __name__ == "__main__":
    unittest.main()
