"""Contract tests for the clause 8.2.2 passive chip bondability logic."""

import unittest

from q6005_passive_chip_bondability_test_logic import (
    FORCE_TOLERANCE_GF,
    INTERFACE_MODES,
    MINIMUM_PULL_TABLES,
    MIN_BONDS_PULLED,
    MIN_CHIPS_SAMPLED,
    assess_bondability,
    evaluate_pull,
    is_interface_failure,
    minimum_pull_force_gf,
    normalize_separation_mode,
    normalize_wire_material,
    pull_statistics,
    required_sample,
)

GOLD_25_MINIMUM = MINIMUM_PULL_TABLES["gold"][1][1]


def readings(count=12, force=6.0, mode="wire-break"):
    return [{"force_gf": force, "mode": mode} for _ in range(count)]


def spec(**overrides):
    record = {
        "lot_size": 500,
        "wire_material": "gold",
        "wire_diameter_um": 25.0,
        "chips_sampled": 4,
        "readings": readings(),
    }
    record.update(overrides)
    return record


class WireMaterialTests(unittest.TestCase):
    def test_canonical_material_passes_through(self):
        self.assertEqual(normalize_wire_material("gold"), "gold")

    def test_symbol_is_resolved(self):
        self.assertEqual(normalize_wire_material("Al"), "aluminium")

    def test_american_spelling_is_resolved(self):
        self.assertEqual(normalize_wire_material("aluminum"), "aluminium")

    def test_unknown_material_rejected(self):
        with self.assertRaises(ValueError):
            normalize_wire_material("copper")

    def test_non_string_material_rejected(self):
        with self.assertRaises(ValueError):
            normalize_wire_material(79)


class MinimumForceTests(unittest.TestCase):
    def test_tabulated_diameter_returns_the_tabulated_force(self):
        self.assertAlmostEqual(minimum_pull_force_gf("gold", 25.0), GOLD_25_MINIMUM, places=9)

    def test_lower_table_edge_is_available(self):
        self.assertAlmostEqual(minimum_pull_force_gf("gold", 18.0), 1.5, places=9)

    def test_upper_table_edge_is_available(self):
        self.assertAlmostEqual(minimum_pull_force_gf("gold", 50.0), 8.0, places=9)

    def test_midpoint_is_interpolated(self):
        self.assertAlmostEqual(minimum_pull_force_gf("gold", 29.0), 3.75, places=9)

    def test_aluminium_sits_below_gold_at_the_same_diameter(self):
        gold = minimum_pull_force_gf("gold", 33.0)
        aluminium = minimum_pull_force_gf("aluminium", 33.0)
        self.assertLess(aluminium, gold)

    def test_thicker_wire_owes_more_force(self):
        self.assertLess(
            minimum_pull_force_gf("gold", 25.0), minimum_pull_force_gf("gold", 33.0)
        )

    def test_diameter_below_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf("gold", 12.0)

    def test_diameter_above_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf("gold", 75.0)

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf("gold", 0.0)

    def test_boolean_diameter_rejected(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf("gold", True)


class SamplePlanTests(unittest.TestCase):
    def test_plan_meets_the_bond_floor(self):
        self.assertEqual(required_sample(500)["bonds"], MIN_BONDS_PULLED)

    def test_plan_meets_the_chip_floor(self):
        self.assertEqual(required_sample(500)["chips"], MIN_CHIPS_SAMPLED)

    def test_tiny_lot_cannot_owe_more_chips_than_it_has(self):
        self.assertEqual(required_sample(2)["chips"], 2)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample(0)

    def test_float_lot_rejected(self):
        with self.assertRaises(ValueError):
            required_sample(500.0)


class SeparationModeTests(unittest.TestCase):
    def test_canonical_mode_passes_through(self):
        self.assertEqual(normalize_separation_mode("wire-break"), "wire-break")

    def test_spaces_and_case_are_normalized(self):
        self.assertEqual(
            normalize_separation_mode("Bond Lift At Termination"), "bond-lift-at-termination"
        )

    def test_wire_break_is_not_an_interface_failure(self):
        self.assertFalse(is_interface_failure("wire-break"))

    def test_heel_break_is_not_an_interface_failure(self):
        self.assertFalse(is_interface_failure("heel-break"))

    def test_bond_lift_is_an_interface_failure(self):
        self.assertTrue(is_interface_failure("bond-lift-at-termination"))

    def test_termination_lift_is_an_interface_failure(self):
        self.assertTrue(is_interface_failure("termination-lift-from-chip"))

    def test_every_interface_mode_is_a_known_mode(self):
        for mode in INTERFACE_MODES:
            self.assertTrue(is_interface_failure(mode))

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_separation_mode("it-just-came-off")


class PullEvaluationTests(unittest.TestCase):
    def test_strong_wire_break_passes(self):
        result = evaluate_pull(6.0, "wire-break", GOLD_25_MINIMUM)
        self.assertTrue(result["passed"])
        self.assertEqual(result["reasons"], ())

    def test_force_exactly_on_the_minimum_passes(self):
        minimum = minimum_pull_force_gf("gold", 29.0)
        result = evaluate_pull(minimum, "wire-break", minimum)
        self.assertAlmostEqual(result["force_gf"], result["minimum_gf"], places=9)
        self.assertTrue(result["passed"])

    def test_weak_pull_fails_on_force(self):
        result = evaluate_pull(1.0, "wire-break", GOLD_25_MINIMUM)
        self.assertFalse(result["passed"])
        self.assertFalse(result["strong_enough"])

    def test_strong_bond_lift_still_fails(self):
        result = evaluate_pull(20.0, "bond-lift-at-termination", GOLD_25_MINIMUM)
        self.assertTrue(result["strong_enough"])
        self.assertFalse(result["passed"])
        self.assertIn("interface failure", result["reasons"][0])

    def test_both_faults_are_reported(self):
        result = evaluate_pull(0.5, "termination-lift-from-chip", GOLD_25_MINIMUM)
        self.assertEqual(len(result["reasons"]), 2)

    def test_zero_force_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pull(0.0, "wire-break", GOLD_25_MINIMUM)

    def test_negative_minimum_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_pull(6.0, "wire-break", -1.0)

    def test_tolerance_stays_far_below_a_gram_force(self):
        self.assertLess(FORCE_TOLERANCE_GF, 1e-6)


class StatisticsTests(unittest.TestCase):
    def test_mean_of_a_symmetric_set(self):
        self.assertAlmostEqual(pull_statistics([3.0, 4.0, 5.0])["mean_gf"], 4.0, places=9)

    def test_sample_standard_deviation(self):
        self.assertAlmostEqual(pull_statistics([3.0, 4.0, 5.0])["std_dev_gf"], 1.0, places=9)

    def test_single_reading_has_no_spread(self):
        self.assertAlmostEqual(pull_statistics([4.0])["std_dev_gf"], 0.0, places=9)

    def test_minimum_and_maximum_are_reported(self):
        statistics = pull_statistics([3.0, 9.0, 5.0])
        self.assertAlmostEqual(statistics["minimum_gf"], 3.0, places=9)
        self.assertAlmostEqual(statistics["maximum_gf"], 9.0, places=9)

    def test_count_matches_the_readings(self):
        self.assertEqual(pull_statistics([3.0, 4.0, 5.0, 6.0])["count"], 4)

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            pull_statistics([])

    def test_non_positive_reading_rejected(self):
        with self.assertRaises(ValueError):
            pull_statistics([3.0, -1.0])


class BondabilityTests(unittest.TestCase):
    def test_clean_sample_is_bondable(self):
        result = assess_bondability(spec())
        self.assertTrue(result["bondable"])
        self.assertEqual(result["findings"], ())

    def test_short_bond_sample_is_flagged(self):
        result = assess_bondability(spec(readings=readings(6)))
        self.assertFalse(result["bondable"])
        self.assertIn("the plan for this lot is 10", result["governing_finding"])

    def test_too_few_chips_is_flagged(self):
        result = assess_bondability(spec(chips_sampled=2))
        self.assertFalse(result["bondable"])
        self.assertIn("2 chips", result["governing_finding"])

    def test_one_interface_failure_condemns_the_lot(self):
        sample = readings(11)
        sample.append({"force_gf": 9.0, "mode": "bond-lift-at-termination"})
        result = assess_bondability(spec(readings=sample))
        self.assertFalse(result["bondable"])
        self.assertEqual(result["interface_indices"], (11,))

    def test_weak_reading_is_indexed(self):
        sample = readings(11)
        sample.append({"force_gf": 1.0, "mode": "wire-break"})
        result = assess_bondability(spec(readings=sample))
        self.assertEqual(result["weak_indices"], (11,))

    def test_minimum_follows_the_wire_actually_used(self):
        thin = assess_bondability(spec(wire_diameter_um=18.0))
        thick = assess_bondability(spec(wire_diameter_um=33.0))
        self.assertLess(thin["minimum_gf"], thick["minimum_gf"])

    def test_statistics_are_reported_with_the_verdict(self):
        result = assess_bondability(spec())
        self.assertEqual(result["statistics"]["count"], 12)
        self.assertAlmostEqual(result["statistics"]["mean_gf"], 6.0, places=9)

    def test_aluminium_wire_lowers_the_bar(self):
        gold = assess_bondability(spec(wire_material="gold"))
        aluminium = assess_bondability(spec(wire_material="aluminium"))
        self.assertLess(aluminium["minimum_gf"], gold["minimum_gf"])

    def test_missing_key_rejected(self):
        record = spec()
        del record["wire_diameter_um"]
        with self.assertRaises(ValueError):
            assess_bondability(record)

    def test_malformed_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_bondability(spec(readings=[{"force_gf": 6.0}]))

    def test_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_bondability(spec(readings=[6.0]))

    def test_empty_reading_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_bondability(spec(readings=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bondability(["gold"])

    def test_zero_chip_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_bondability(spec(chips_sampled=0))


if __name__ == "__main__":
    unittest.main()
