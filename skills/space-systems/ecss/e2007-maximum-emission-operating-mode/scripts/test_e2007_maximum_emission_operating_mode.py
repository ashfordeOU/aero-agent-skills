#!/usr/bin/env python3
"""Gate 3 contract test for e2007-maximum-emission-operating-mode.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_maximum_emission_operating_mode_logic import (
    DEFAULT_MODE_SPEC,
    EMISSION_EPS,
    bands_needing_additional_run,
    dominant_mode,
    duty_cycle_correction_db,
    emission_mode_readiness,
    evaluate_mode_selection,
    mode_shortfall_db,
    normalize_mode,
    normalize_survey,
    resolve_spec,
    survey_bands,
    worst_mode_per_band,
)


def nominal_modes():
    return [
        {
            "name": "stand-by",
            "levels_dbuv": {"band-a": 30.0, "band-b": 28.0, "band-c": 25.0},
        },
        {
            "name": "converter-full-load",
            "levels_dbuv": {"band-a": 52.0, "band-b": 44.0, "band-c": 31.0},
        },
        {
            "name": "transmit",
            "levels_dbuv": {"band-a": 41.0, "band-b": 40.0, "band-c": 58.0},
        },
    ]


def nominal_config(declared="converter-full-load"):
    return {"modes": nominal_modes(), "declared_mode": declared}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["allowed_shortfall_db"], 2.0, places=9)
        self.assertEqual(set(spec), set(DEFAULT_MODE_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"allowed_shortfall_db": 0.5})
        self.assertAlmostEqual(spec["allowed_shortfall_db"], 0.5, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"allowed_shortfall_db": 0.5})
        self.assertAlmostEqual(DEFAULT_MODE_SPEC["allowed_shortfall_db"], 2.0, places=9)

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"antenna_height_m": 1.0})

    def test_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"allowed_shortfall_db": -1.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("allowed_shortfall_db", 1.0)])


class TestDutyCycleCorrection(unittest.TestCase):
    def test_continuous_emitter_needs_no_correction(self):
        self.assertAlmostEqual(duty_cycle_correction_db(1.0), 0.0, places=9)

    def test_half_duty_cycle_is_about_six_decibels_down(self):
        self.assertAlmostEqual(
            duty_cycle_correction_db(0.5), -6.020599913279624, places=9
        )

    def test_tenth_duty_cycle_is_twenty_decibels_down(self):
        self.assertAlmostEqual(duty_cycle_correction_db(0.1), -20.0, places=9)

    def test_correction_is_never_positive(self):
        for duty in (1.0, 0.75, 0.5, 0.25, 0.01):
            self.assertLessEqual(duty_cycle_correction_db(duty), 0.0)

    def test_zero_duty_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle_correction_db(0.0)

    def test_duty_cycle_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle_correction_db(1.5)

    def test_unresolvably_small_duty_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle_correction_db(1.0e-12)

    def test_non_numeric_duty_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_cycle_correction_db("0.5")


class TestModeNormalization(unittest.TestCase):
    def test_levels_are_carried_through_unchanged_at_full_duty(self):
        mode = normalize_mode(nominal_modes()[1])
        self.assertAlmostEqual(mode["levels_dbuv"]["band-a"], 52.0, places=9)
        self.assertAlmostEqual(mode["correction_db"], 0.0, places=9)

    def test_pulsed_mode_levels_are_corrected_down(self):
        mode = normalize_mode(
            {"name": "pulsed", "levels_dbuv": {"band-a": 60.0}, "duty_cycle": 0.1}
        )
        self.assertAlmostEqual(mode["levels_dbuv"]["band-a"], 40.0, places=9)

    def test_missing_levels_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode({"name": "x"})

    def test_empty_levels_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode({"name": "x", "levels_dbuv": {}})

    def test_blank_mode_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode({"name": "   ", "levels_dbuv": {"band-a": 10.0}})

    def test_non_numeric_level_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode({"name": "x", "levels_dbuv": {"band-a": "10"}})

    def test_empty_survey_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_survey([])

    def test_duplicate_mode_names_are_rejected(self):
        modes = nominal_modes()
        modes[1]["name"] = "stand-by"
        with self.assertRaises(ValueError):
            normalize_survey(modes)

    def test_inconsistent_band_sets_are_rejected(self):
        modes = nominal_modes()
        del modes[2]["levels_dbuv"]["band-c"]
        with self.assertRaises(ValueError):
            normalize_survey(modes)

    def test_survey_bands_are_sorted(self):
        self.assertEqual(survey_bands(nominal_modes()), ["band-a", "band-b", "band-c"])


class TestRanking(unittest.TestCase):
    def test_worst_mode_is_found_band_by_band(self):
        worst = worst_mode_per_band(nominal_modes())
        self.assertEqual(worst["band-a"]["mode"], "converter-full-load")
        self.assertEqual(worst["band-c"]["mode"], "transmit")

    def test_worst_level_is_reported_with_the_mode(self):
        worst = worst_mode_per_band(nominal_modes())
        self.assertAlmostEqual(worst["band-c"]["level_dbuv"], 58.0, places=9)

    def test_a_tie_is_broken_by_mode_name(self):
        modes = [
            {"name": "zulu", "levels_dbuv": {"band-a": 40.0}},
            {"name": "alpha", "levels_dbuv": {"band-a": 40.0}},
        ]
        self.assertEqual(worst_mode_per_band(modes)["band-a"]["mode"], "alpha")

    def test_dominant_mode_leads_the_most_bands(self):
        self.assertEqual(dominant_mode(nominal_modes()), "converter-full-load")

    def test_a_pulsed_transmitter_can_lose_its_lead_after_correction(self):
        modes = nominal_modes()
        modes[2]["duty_cycle"] = 0.01
        worst = worst_mode_per_band(modes)
        self.assertEqual(worst["band-c"]["mode"], "converter-full-load")

    def test_a_single_mode_survey_still_ranks(self):
        worst = worst_mode_per_band([nominal_modes()[0]])
        self.assertEqual(worst["band-a"]["mode"], "stand-by")


class TestShortfall(unittest.TestCase):
    def test_the_worst_mode_has_no_shortfall_in_the_band_it_leads(self):
        shortfalls = mode_shortfall_db(nominal_modes(), "converter-full-load")
        self.assertAlmostEqual(shortfalls["band-a"], 0.0, places=9)

    def test_shortfall_is_the_decibel_gap_to_the_worst_mode(self):
        shortfalls = mode_shortfall_db(nominal_modes(), "converter-full-load")
        self.assertAlmostEqual(shortfalls["band-c"], 27.0, places=9)

    def test_shortfall_is_never_negative(self):
        shortfalls = mode_shortfall_db(nominal_modes(), "stand-by")
        for value in shortfalls.values():
            self.assertGreaterEqual(value, 0.0)

    def test_an_unsurveyed_declared_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            mode_shortfall_db(nominal_modes(), "safe-hold")

    def test_a_blank_declared_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            mode_shortfall_db(nominal_modes(), "  ")

    def test_a_shortfall_exactly_on_the_margin_needs_no_extra_run(self):
        modes = [
            {"name": "quiet", "levels_dbuv": {"band-a": 40.0}},
            {"name": "loud", "levels_dbuv": {"band-a": 42.0}},
        ]
        shortfalls = mode_shortfall_db(modes, "quiet")
        self.assertAlmostEqual(shortfalls["band-a"], 2.0, places=9)
        self.assertEqual(bands_needing_additional_run(modes, "quiet"), [])

    def test_a_shortfall_beyond_the_margin_needs_an_extra_run(self):
        modes = [
            {"name": "quiet", "levels_dbuv": {"band-a": 40.0}},
            {"name": "loud", "levels_dbuv": {"band-a": 46.0}},
        ]
        self.assertEqual(bands_needing_additional_run(modes, "quiet"), ["band-a"])

    def test_a_tighter_margin_pulls_in_more_bands(self):
        modes = [
            {"name": "quiet", "levels_dbuv": {"band-a": 40.0}},
            {"name": "loud", "levels_dbuv": {"band-a": 41.0}},
        ]
        self.assertEqual(bands_needing_additional_run(modes, "quiet"), [])
        self.assertEqual(
            bands_needing_additional_run(modes, "quiet", {"allowed_shortfall_db": 0.5}),
            ["band-a"],
        )


class TestAggregation(unittest.TestCase):
    """End-to-end workflow: every step of the mode review feeds one gate token."""

    def test_the_dominant_mode_still_misses_a_band_it_does_not_lead(self):
        result = evaluate_mode_selection(nominal_config())
        self.assertFalse(result["ready"])
        self.assertEqual(result["bands_needing_additional_run"], ["band-c"])
        self.assertEqual(result["status"], "hold-mode-selection")

    def test_a_mode_leading_every_band_is_ready(self):
        modes = [
            {"name": "quiet", "levels_dbuv": {"band-a": 30.0, "band-b": 31.0}},
            {"name": "loud", "levels_dbuv": {"band-a": 50.0, "band-b": 49.0}},
        ]
        result = evaluate_mode_selection({"modes": modes, "declared_mode": "loud"})
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["status"], "ready-for-emission-run")

    def test_the_finding_names_the_mode_that_should_have_been_run(self):
        result = evaluate_mode_selection(nominal_config())
        self.assertTrue(
            any("transmit" in f for f in result["findings"]), result["findings"]
        )

    def test_max_shortfall_is_reported(self):
        result = evaluate_mode_selection(nominal_config())
        self.assertAlmostEqual(result["max_shortfall_db"], 27.0, places=9)

    def test_a_single_mode_survey_is_held(self):
        modes = [{"name": "only", "levels_dbuv": {"band-a": 40.0}}]
        result = evaluate_mode_selection({"modes": modes, "declared_mode": "only"})
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("fewer operating modes" in f for f in result["findings"]),
            result["findings"],
        )

    def test_dominant_mode_is_reported_alongside_the_declared_one(self):
        result = evaluate_mode_selection(nominal_config("stand-by"))
        self.assertEqual(result["declared_mode"], "stand-by")
        self.assertEqual(result["dominant_mode"], "converter-full-load")

    def test_missing_declared_mode_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mode_selection({"modes": nominal_modes()})

    def test_non_mapping_config_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_mode_selection(["transmit"])

    def test_gate_token_needs_a_sequence(self):
        with self.assertRaises(ValueError):
            emission_mode_readiness("no findings")

    def test_gate_token_reflects_the_finding_list(self):
        self.assertEqual(emission_mode_readiness([]), "ready-for-emission-run")
        self.assertEqual(emission_mode_readiness(["one"]), "hold-mode-selection")

    def test_named_tolerance_is_far_below_any_decibel_margin(self):
        self.assertLess(EMISSION_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
