#!/usr/bin/env python3
"""Gate 3 contract test for e2001-discharge-and-event-definitions.

Offline, deterministic, stdlib unittest. Run:
python3 test_e2001_discharge_and_event_definitions.py
"""

import unittest

import e2001_discharge_and_event_definitions_logic as L


def base_observation(**over):
    obs = {
        "id": "obs-1",
        "channels": {
            "forward-power-monitor": {"reading": 0.9, "threshold": 1.0},
            "electron-probe": {"reading": 0.2, "threshold": 1.0},
        },
        "chamber_pressure_pa": 1.0e-5,
        "frequency_hz": 12.0e9,
        "gap_m": 1.0e-3,
        "extinguishes_below_onset": True,
        "reproducible_onset": True,
        "pressure_sensitive": False,
        "seeding_active": True,
    }
    obs.update(over)
    return obs


def tripped(**over):
    obs = base_observation(**over)
    obs["channels"] = dict(obs["channels"])
    obs["channels"]["electron-probe"] = {"reading": 3.0, "threshold": 1.0}
    return obs


class TermDefinitionTests(unittest.TestCase):
    def test_three_terms_are_defined(self):
        for term in ("event", "discharge", "multipactor"):
            self.assertTrue(len(L.term_definition(term)) > 40)

    def test_term_lookup_is_case_insensitive(self):
        self.assertEqual(L.term_definition("Multipactor"), L.term_definition("multipactor"))

    def test_unknown_term_raises(self):
        with self.assertRaises(ValueError):
            L.term_definition("breakdown")

    def test_non_string_term_raises(self):
        with self.assertRaises(ValueError):
            L.term_definition(7)


class ValidationTests(unittest.TestCase):
    def test_valid_observation_normalises(self):
        rec = L.validate_observation(base_observation())
        self.assertEqual(rec["id"], "obs-1")
        self.assertAlmostEqual(rec["chamber_pressure_pa"], 1.0e-5)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(["obs-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(id="   "))

    def test_empty_channel_map_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(channels={}))

    def test_channel_entry_not_mapping_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(channels={"probe": 3.0}))

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(
                base_observation(channels={"probe": {"reading": 1.0, "threshold": 0.0}})
            )

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(chamber_pressure_pa=0.0))

    def test_non_finite_pressure_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(chamber_pressure_pa=float("inf")))

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(gap_m=-1.0e-3))

    def test_non_boolean_flag_raises(self):
        with self.assertRaises(ValueError):
            L.validate_observation(base_observation(reproducible_onset="yes"))

    def test_missing_flag_raises(self):
        obs = base_observation()
        del obs["pressure_sensitive"]
        with self.assertRaises(ValueError):
            L.validate_observation(obs)


class ThresholdCrossingTests(unittest.TestCase):
    def test_no_crossing_when_below_threshold(self):
        self.assertEqual(L.crossed_channels(base_observation()), [])

    def test_crossing_listed_and_sorted(self):
        obs = tripped()
        obs["channels"]["arc-detector"] = {"reading": 5.0, "threshold": 1.0}
        self.assertEqual(L.crossed_channels(obs), ["arc-detector", "electron-probe"])

    def test_reading_exactly_at_threshold_is_a_crossing(self):
        obs = base_observation(
            channels={"probe": {"reading": 1.0, "threshold": 1.0}}
        )
        self.assertEqual(L.crossed_channels(obs), ["probe"])

    def test_summed_reading_at_threshold_absorbs_representation_error(self):
        # A reading summed from three sensor terms lands a few ULPs off 0.3.
        summed = 0.1 + 0.1 + 0.1
        self.assertNotEqual(summed, 0.3)
        obs = base_observation(
            channels={"probe": {"reading": summed, "threshold": 0.3}}
        )
        self.assertEqual(L.crossed_channels(obs), ["probe"])


class PressureRegimeTests(unittest.TestCase):
    def test_deep_vacuum_is_high_vacuum_regime(self):
        self.assertEqual(L.pressure_regime(1.0e-6), L.REGIME_HIGH_VACUUM)

    def test_exact_high_vacuum_limit_is_high_vacuum_regime(self):
        self.assertEqual(L.pressure_regime(L.HIGH_VACUUM_LIMIT_PA), L.REGIME_HIGH_VACUUM)

    def test_between_limits_is_transition_regime(self):
        self.assertEqual(L.pressure_regime(5.0e-4), L.REGIME_TRANSITION)

    def test_at_residual_gas_limit_is_residual_gas_regime(self):
        self.assertEqual(L.pressure_regime(L.RESIDUAL_GAS_LIMIT_PA), L.REGIME_RESIDUAL_GAS)

    def test_above_residual_gas_limit_is_residual_gas_regime(self):
        self.assertEqual(L.pressure_regime(2.0e-2), L.REGIME_RESIDUAL_GAS)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            L.pressure_regime(0.0)

    def test_boolean_pressure_raises(self):
        with self.assertRaises(ValueError):
            L.pressure_regime(True)


class FrequencyGapProductTests(unittest.TestCase):
    def test_product_in_ghz_mm(self):
        self.assertAlmostEqual(
            L.frequency_gap_product_ghz_mm(12.0e9, 1.0e-3), 12.0, places=9
        )

    def test_small_gap_product(self):
        self.assertAlmostEqual(
            L.frequency_gap_product_ghz_mm(1.0e9, 0.2e-3), 0.2, places=9
        )

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product_ghz_mm(0.0, 1.0e-3)

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product_ghz_mm(12.0e9, 0.0)

    def test_inside_band(self):
        self.assertTrue(L.in_susceptibility_band(12.0))

    def test_below_band_is_outside(self):
        self.assertFalse(L.in_susceptibility_band(0.01))

    def test_above_band_is_outside(self):
        self.assertFalse(L.in_susceptibility_band(250.0))

    def test_lower_band_edge_is_inside(self):
        self.assertTrue(L.in_susceptibility_band(L.FD_BAND_MIN_GHZ_MM))

    def test_upper_band_edge_is_inside(self):
        self.assertTrue(L.in_susceptibility_band(L.FD_BAND_MAX_GHZ_MM))

    def test_band_edge_reached_by_computation_is_inside(self):
        fd = L.frequency_gap_product_ghz_mm(100.0e9, 1.0e-3)
        self.assertTrue(L.in_susceptibility_band(fd))

    def test_negative_product_raises(self):
        with self.assertRaises(ValueError):
            L.in_susceptibility_band(-1.0)


class CategorizationTests(unittest.TestCase):
    def test_no_crossing_gives_no_event(self):
        out = L.categorize_observation(base_observation())
        self.assertEqual(out["category"], L.CATEGORY_NO_EVENT)
        self.assertEqual(out["crossed_channels"], [])

    def test_power_threshold_signature_in_vacuum_gives_multipactor(self):
        out = L.categorize_observation(tripped())
        self.assertEqual(out["category"], L.CATEGORY_MULTIPACTOR)
        self.assertAlmostEqual(out["fd_ghz_mm"], 12.0, places=9)

    def test_pressure_sensitive_excursion_in_residual_gas_gives_discharge(self):
        out = L.categorize_observation(
            tripped(
                chamber_pressure_pa=5.0e-3,
                pressure_sensitive=True,
                extinguishes_below_onset=False,
                reproducible_onset=False,
            )
        )
        self.assertEqual(out["category"], L.CATEGORY_GAS_DISCHARGE)

    def test_pressure_sensitive_excursion_in_transition_band_gives_discharge(self):
        out = L.categorize_observation(
            tripped(
                chamber_pressure_pa=4.0e-4,
                pressure_sensitive=True,
                extinguishes_below_onset=False,
                reproducible_onset=False,
            )
        )
        self.assertEqual(out["category"], L.CATEGORY_GAS_DISCHARGE)

    def test_no_extinction_in_vacuum_is_undetermined(self):
        out = L.categorize_observation(tripped(extinguishes_below_onset=False))
        self.assertEqual(out["category"], L.CATEGORY_UNDETERMINED)
        self.assertTrue(
            any("extinction" in r for r in out["reasons"]),
            out["reasons"],
        )

    def test_non_repeatable_onset_is_undetermined(self):
        out = L.categorize_observation(tripped(reproducible_onset=False))
        self.assertEqual(out["category"], L.CATEGORY_UNDETERMINED)

    def test_geometry_outside_band_is_undetermined(self):
        out = L.categorize_observation(tripped(frequency_hz=400.0e9, gap_m=5.0e-3))
        self.assertEqual(out["category"], L.CATEGORY_UNDETERMINED)
        self.assertFalse(out["in_susceptibility_band"])

    def test_both_signatures_at_once_is_undetermined(self):
        # Transition-band pressure with a pressure-sensitive excursion that also
        # shows power-threshold behaviour: the mechanism is not resolved.
        out = L.categorize_observation(
            tripped(chamber_pressure_pa=5.0e-4, pressure_sensitive=True)
        )
        self.assertEqual(out["category"], L.CATEGORY_UNDETERMINED)

    def test_high_vacuum_pressure_sensitive_flag_does_not_make_a_discharge(self):
        out = L.categorize_observation(tripped(pressure_sensitive=True))
        self.assertEqual(out["category"], L.CATEGORY_MULTIPACTOR)

    def test_reasons_name_the_crossed_channel(self):
        out = L.categorize_observation(tripped())
        self.assertTrue(any("electron-probe" in r for r in out["reasons"]))

    def test_invalid_observation_propagates_value_error(self):
        with self.assertRaises(ValueError):
            L.categorize_observation(base_observation(frequency_hz=0.0))


class ReportabilityTests(unittest.TestCase):
    def test_no_event_is_not_reportable(self):
        self.assertFalse(L.is_reportable(L.CATEGORY_NO_EVENT))

    def test_undetermined_event_is_reportable(self):
        self.assertTrue(L.is_reportable(L.CATEGORY_UNDETERMINED))

    def test_multipactor_is_reportable(self):
        self.assertTrue(L.is_reportable(L.CATEGORY_MULTIPACTOR))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            L.is_reportable("anomaly")

    def test_non_string_category_raises(self):
        with self.assertRaises(ValueError):
            L.is_reportable(None)


class RunSummaryTests(unittest.TestCase):
    def test_clean_run_is_judgeable_without_multipactor_evidence(self):
        summary = L.summarize_run([base_observation(), base_observation(id="obs-2")])
        self.assertTrue(summary["judgeable"])
        self.assertFalse(summary["multipactor_evidence"])
        self.assertEqual(summary["counts"][L.CATEGORY_NO_EVENT], 2)

    def test_run_with_multipactor_reports_evidence(self):
        summary = L.summarize_run([base_observation(), tripped(id="obs-2")])
        self.assertTrue(summary["multipactor_evidence"])
        self.assertEqual(summary["reportable_events"], ["obs-2"])

    def test_undetermined_event_blocks_judgement(self):
        summary = L.summarize_run(
            [tripped(id="obs-3", extinguishes_below_onset=False)]
        )
        self.assertFalse(summary["judgeable"])
        self.assertEqual(summary["undetermined_events"], ["obs-3"])

    def test_counts_cover_every_category(self):
        summary = L.summarize_run(
            [
                base_observation(id="a"),
                tripped(id="b"),
                tripped(
                    id="c",
                    chamber_pressure_pa=5.0e-3,
                    pressure_sensitive=True,
                    extinguishes_below_onset=False,
                    reproducible_onset=False,
                ),
                tripped(id="d", reproducible_onset=False),
            ]
        )
        self.assertEqual(summary["counts"][L.CATEGORY_NO_EVENT], 1)
        self.assertEqual(summary["counts"][L.CATEGORY_MULTIPACTOR], 1)
        self.assertEqual(summary["counts"][L.CATEGORY_GAS_DISCHARGE], 1)
        self.assertEqual(summary["counts"][L.CATEGORY_UNDETERMINED], 1)
        self.assertEqual(len(summary["reportable_events"]), 3)

    def test_empty_run_log_raises(self):
        with self.assertRaises(ValueError):
            L.summarize_run([])

    def test_non_list_run_log_raises(self):
        with self.assertRaises(ValueError):
            L.summarize_run({"id": "obs-1"})


if __name__ == "__main__":
    unittest.main()
