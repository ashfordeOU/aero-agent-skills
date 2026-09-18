"""Contract tests for the SCC heat-treatment state control logic."""

import unittest

from q7036_heat_treatment_state_control_logic import (
    RESISTANCE_CATEGORIES,
    TEMPER_REGISTRY,
    WINDOW_TOLERANCE,
    acceptance_window,
    assess_state,
    assess_states,
    matching_tempers,
    normalize_state,
    registry_entry,
    resistance_for_state,
    verification_property,
    within_window,
)


def state(sid, alloy="aluminium-7xxx", temper="t73", reading=41.5):
    return {"id": sid, "alloy": alloy, "temper": temper, "reading": reading}


class RegistryTests(unittest.TestCase):
    def test_every_entry_carries_a_known_rating(self):
        for key, entry in TEMPER_REGISTRY.items():
            self.assertIn(entry["resistance"], RESISTANCE_CATEGORIES, key)

    def test_every_window_is_ordered_and_positive(self):
        for key, entry in TEMPER_REGISTRY.items():
            low, high = entry["window"]
            self.assertGreater(low, 0.0, key)
            self.assertLess(low, high, key)

    def test_no_two_tempers_of_one_alloy_share_a_window(self):
        for (alloy_a, temper_a), entry_a in TEMPER_REGISTRY.items():
            for (alloy_b, temper_b), entry_b in TEMPER_REGISTRY.items():
                if alloy_a != alloy_b or temper_a >= temper_b:
                    continue
                low_a, high_a = entry_a["window"]
                low_b, high_b = entry_b["window"]
                self.assertFalse(
                    low_a <= high_b and low_b <= high_a,
                    "%s windows overlap: %s and %s" % (alloy_a, temper_a, temper_b),
                )

    def test_peak_aged_state_is_the_susceptible_one(self):
        self.assertEqual(resistance_for_state("aluminium-7xxx", "t6"), "low")

    def test_overaged_state_is_the_resistant_one(self):
        self.assertEqual(resistance_for_state("aluminium-7xxx", "t73"), "high")

    def test_partially_overaged_state_is_intermediate(self):
        self.assertEqual(resistance_for_state("7xxx", "t76"), "medium")

    def test_steel_state_is_verified_on_hardness(self):
        self.assertEqual(verification_property("low-alloy-steel", "tempered-high"), "hardness")

    def test_aluminium_state_is_verified_on_conductivity(self):
        self.assertEqual(verification_property("al-7xxx", "t651"), "conductivity")


class NormalizationTests(unittest.TestCase):
    def test_alloy_alias_resolved(self):
        self.assertEqual(normalize_state("Al-7xxx", "T73")[0], "aluminium-7xxx")

    def test_temper_alias_resolved(self):
        self.assertEqual(normalize_state("aluminium-7xxx", "T7351")[1], "t73")

    def test_unknown_temper_for_known_alloy_names_the_registered_ones(self):
        with self.assertRaises(ValueError) as caught:
            registry_entry("aluminium-7xxx", "t99")
        self.assertIn("t73", str(caught.exception))

    def test_unknown_alloy_rejected(self):
        with self.assertRaises(ValueError):
            registry_entry("inconel-alloy", "t6")

    def test_blank_temper_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state("aluminium-7xxx", "  ")

    def test_non_string_alloy_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state(7075, "t73")


class WindowTests(unittest.TestCase):
    def test_reading_inside_the_window(self):
        self.assertTrue(within_window(41.5, (40.0, 43.0)))

    def test_reading_exactly_on_the_low_edge_is_inside(self):
        low, high = acceptance_window("aluminium-7xxx", "t73")
        self.assertAlmostEqual(low, 40.0, places=9)
        self.assertTrue(within_window(low, (low, high)))

    def test_reading_exactly_on_the_high_edge_is_inside(self):
        low, high = acceptance_window("aluminium-7xxx", "t73")
        self.assertAlmostEqual(high, 43.0, places=9)
        self.assertTrue(within_window(high, (low, high)))

    def test_reading_just_outside_the_tolerance_is_outside(self):
        self.assertFalse(within_window(43.0 + 1e-3, (40.0, 43.0)))

    def test_tolerance_is_tight(self):
        self.assertLess(WINDOW_TOLERANCE, 1e-6)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            within_window(41.0, (43.0, 40.0))

    def test_malformed_window_rejected(self):
        with self.assertRaises(ValueError):
            within_window(41.0, (40.0,))

    def test_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            within_window("41.0", (40.0, 43.0))

    def test_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            within_window(True, (40.0, 43.0))

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            within_window(-41.0, (40.0, 43.0))


class MatchingTests(unittest.TestCase):
    def test_reading_matches_the_overaged_window(self):
        self.assertEqual(matching_tempers("aluminium-7xxx", 41.5), ["t73"])

    def test_reading_matches_the_peak_aged_window(self):
        self.assertEqual(matching_tempers("aluminium-7xxx", 32.0), ["t6"])

    def test_reading_between_windows_matches_nothing(self):
        self.assertEqual(matching_tempers("aluminium-7xxx", 36.5), [])

    def test_matching_is_scoped_to_one_alloy(self):
        self.assertEqual(matching_tempers("aluminium-2xxx", 41.5), [])


class AssessStateTests(unittest.TestCase):
    def test_reading_in_window_evidences_the_state(self):
        record = assess_state(state("s1"))
        self.assertEqual(record["disposition"], "state-evidenced")
        self.assertTrue(record["within_window"])
        self.assertEqual(record["findings"], [])

    def test_reading_matching_another_temper_is_a_substitution(self):
        record = assess_state(state("s2", temper="t6", reading=41.5))
        self.assertEqual(record["disposition"], "temper-substitution")
        self.assertEqual(record["substituted_tempers"], ["t73"])
        self.assertEqual(len(record["findings"]), 1)

    def test_substitution_finding_names_the_delivered_rating(self):
        record = assess_state(state("s3", temper="t73", reading=32.0))
        self.assertIn("t6", record["findings"][0])
        self.assertIn("rated low", record["findings"][0])

    def test_reading_matching_nothing_is_out_of_window(self):
        record = assess_state(state("s4", reading=36.5))
        self.assertEqual(record["disposition"], "reading-out-of-window")
        self.assertEqual(record["substituted_tempers"], [])

    def test_steel_state_assessed_on_its_hardness_window(self):
        record = assess_state(
            state("s5", alloy="low-alloy-steel", temper="tempered-high", reading=30.0)
        )
        self.assertEqual(record["disposition"], "state-evidenced")
        self.assertEqual(record["property"], "hardness")

    def test_hard_steel_reading_flags_the_susceptible_temper(self):
        record = assess_state(
            state("s6", alloy="low-alloy-steel", temper="tempered-high", reading=46.0)
        )
        self.assertEqual(record["disposition"], "temper-substitution")
        self.assertEqual(record["substituted_tempers"], ["tempered-low"])

    def test_missing_key_rejected(self):
        broken = state("s7")
        del broken["reading"]
        with self.assertRaises(ValueError):
            assess_state(broken)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_state(["s8"])


class AssessStatesTests(unittest.TestCase):
    def test_clean_population_is_compliant(self):
        result = assess_states([state("a"), state("b", temper="t6", reading=32.0)])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["evidenced_count"], 2)

    def test_mixed_population_counts_each_disposition(self):
        result = assess_states(
            [
                state("a"),
                state("b", temper="t6", reading=41.5),
                state("c", reading=36.5),
            ]
        )
        self.assertEqual(result["evidenced_count"], 1)
        self.assertEqual(result["substitution_count"], 1)
        self.assertEqual(result["out_of_window_count"], 1)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_states([state("a"), state("a")])

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            assess_states([])


if __name__ == "__main__":
    unittest.main()
