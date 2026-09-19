"""Contract tests for the clause 10.2.5 die packaging and storage assessment."""

import unittest

from q6012_die_packaging_and_storage_logic import (
    ADEQUATE_INDEX,
    BARRIERS,
    CARRIER_TYPES,
    CONDITIONAL_INDEX,
    DEFAULT_HUMIDITY_LIMIT_PERCENT,
    DEFAULT_TEMPERATURE_LIMITS_C,
    SEAL_TYPES,
    TEMPERATURE_ALLOWANCE_C,
    assess_die_storage,
    bake_required,
    barrier_scores,
    carrier_profile,
    governing_barrier,
    humidity_score,
    protection_index,
    remaining_floor_life,
    required_actions,
    seal_profile,
    storage_findings,
    temperature_score,
    validate_arrangement,
)


def base_spec(**overrides):
    spec = {
        "batch_id": "DIE-BATCH-08",
        "carrier": "waffle-pack",
        "seal": "dry-nitrogen-bag",
        "storage_temperature_c": 22.0,
        "storage_humidity_percent": 35.0,
        "days_since_seal_opened": 3,
        "floor_life_days": 30,
        "desiccant_present": True,
        "humidity_indicator_present": True,
        "moisture_sensitive": True,
        "die_count": 250,
    }
    spec.update(overrides)
    return spec


class RegistryTests(unittest.TestCase):
    def test_carrier_and_seal_tokens_are_unique(self):
        self.assertEqual(len(CARRIER_TYPES), len(set(CARRIER_TYPES)))
        self.assertEqual(len(SEAL_TYPES), len(set(SEAL_TYPES)))

    def test_every_carrier_has_a_profile(self):
        for key in CARRIER_TYPES:
            profile = carrier_profile(key)
            self.assertIn("mechanical", profile)
            self.assertIsInstance(profile["dissipative"], bool)

    def test_every_seal_has_a_profile(self):
        for key in SEAL_TYPES:
            profile = seal_profile(key)
            self.assertIn("moisture", profile)
            self.assertIsInstance(profile["desiccant_expected"], bool)

    def test_unknown_carrier_rejected(self):
        with self.assertRaises(ValueError):
            carrier_profile("cardboard-box")

    def test_unknown_seal_rejected(self):
        with self.assertRaises(ValueError):
            seal_profile("cling-film")

    def test_barrier_names_and_thresholds_are_coherent(self):
        self.assertEqual(len(BARRIERS), len(set(BARRIERS)))
        self.assertGreater(ADEQUATE_INDEX, CONDITIONAL_INDEX)

    def test_unsealed_offers_no_moisture_barrier(self):
        self.assertAlmostEqual(seal_profile("unsealed")["moisture"], 0.0, places=9)


class ValidateArrangementTests(unittest.TestCase):
    def test_tokens_are_normalised_to_lower_case(self):
        arrangement = validate_arrangement(base_spec(carrier="Waffle-Pack"))
        self.assertEqual(arrangement["carrier"], "waffle-pack")

    def test_optional_flags_default(self):
        spec = base_spec()
        for key in ("desiccant_present", "humidity_indicator_present",
                    "moisture_sensitive", "die_count"):
            del spec[key]
        arrangement = validate_arrangement(spec)
        self.assertFalse(arrangement["desiccant_present"])
        self.assertTrue(arrangement["moisture_sensitive"])
        self.assertEqual(arrangement["die_count"], 1)

    def test_default_limits_are_applied(self):
        arrangement = validate_arrangement(base_spec())
        self.assertEqual(
            arrangement["temperature_limits_c"], tuple(DEFAULT_TEMPERATURE_LIMITS_C)
        )
        self.assertAlmostEqual(
            arrangement["humidity_limit_percent"],
            DEFAULT_HUMIDITY_LIMIT_PERCENT,
            places=9,
        )

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(["batch_id"])

    def test_missing_required_key_rejected(self):
        spec = base_spec()
        del spec["floor_life_days"]
        with self.assertRaises(ValueError):
            validate_arrangement(spec)

    def test_unknown_key_rejected_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(dessicant_present=True))

    def test_unknown_carrier_token_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(carrier="shoebox"))

    def test_fractional_day_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(days_since_seal_opened=3.5))

    def test_negative_day_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(days_since_seal_opened=-1))

    def test_zero_floor_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(floor_life_days=0))

    def test_humidity_outside_zero_to_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(storage_humidity_percent=140.0))

    def test_inverted_temperature_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(temperature_limits_c=[30.0, 15.0]))

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrangement(base_spec(desiccant_present="yes"))


class EnvironmentScoreTests(unittest.TestCase):
    def test_temperature_inside_the_band_scores_one(self):
        self.assertAlmostEqual(temperature_score(22.0, (15.0, 30.0)), 1.0, places=9)

    def test_temperature_on_the_band_edge_scores_one(self):
        self.assertAlmostEqual(temperature_score(30.0, (15.0, 30.0)), 1.0, places=9)

    def test_temperature_just_outside_loses_score_linearly(self):
        expected = 1.0 - 10.0 / TEMPERATURE_ALLOWANCE_C
        self.assertAlmostEqual(temperature_score(40.0, (15.0, 30.0)), expected, places=9)

    def test_temperature_far_outside_is_floored_at_zero(self):
        self.assertAlmostEqual(temperature_score(90.0, (15.0, 30.0)), 0.0, places=9)

    def test_temperature_score_rejects_inverted_limits(self):
        with self.assertRaises(ValueError):
            temperature_score(22.0, (30.0, 15.0))

    def test_humidity_at_the_ceiling_scores_one(self):
        self.assertAlmostEqual(humidity_score(60.0, 60.0), 1.0, places=9)

    def test_humidity_above_the_ceiling_loses_score(self):
        self.assertAlmostEqual(humidity_score(80.0, 60.0), 0.5, places=9)

    def test_saturated_store_scores_zero(self):
        self.assertAlmostEqual(humidity_score(100.0, 60.0), 0.0, places=9)

    def test_humidity_score_rejects_an_impossible_ceiling(self):
        with self.assertRaises(ValueError):
            humidity_score(50.0, 100.0)


class BarrierTests(unittest.TestCase):
    def test_good_arrangement_scores_every_barrier_well(self):
        scores = barrier_scores(validate_arrangement(base_spec()))
        for name in BARRIERS:
            self.assertGreaterEqual(scores[name], ADEQUATE_INDEX)

    def test_non_dissipative_carrier_zeroes_the_electrostatic_barrier(self):
        arrangement = validate_arrangement(base_spec(carrier="loose-tray"))
        self.assertAlmostEqual(
            barrier_scores(arrangement)["electrostatic"], 0.0, places=9
        )
        self.assertEqual(governing_barrier(arrangement), "electrostatic")

    def test_missing_desiccant_halves_the_moisture_barrier(self):
        arrangement = validate_arrangement(base_spec(desiccant_present=False))
        full = seal_profile("dry-nitrogen-bag")["moisture"]
        self.assertAlmostEqual(
            barrier_scores(arrangement)["moisture"], full / 2.0, places=9
        )

    def test_unsealed_moisture_sensitive_batch_governs_on_moisture(self):
        arrangement = validate_arrangement(
            base_spec(seal="unsealed", desiccant_present=False,
                      humidity_indicator_present=False)
        )
        self.assertEqual(governing_barrier(arrangement), "moisture")
        self.assertAlmostEqual(protection_index(arrangement), 0.0, places=9)

    def test_non_moisture_sensitive_batch_is_not_penalised_for_the_seal(self):
        arrangement = validate_arrangement(
            base_spec(seal="unsealed", moisture_sensitive=False,
                      desiccant_present=False, humidity_indicator_present=False)
        )
        self.assertAlmostEqual(
            barrier_scores(arrangement)["moisture"], ADEQUATE_INDEX, places=9
        )

    def test_barrier_scores_reject_a_raw_spec(self):
        with self.assertRaises(ValueError):
            barrier_scores(base_spec())


class FloorLifeTests(unittest.TestCase):
    def test_unspent_floor_life_is_reported_in_whole_days(self):
        arrangement = validate_arrangement(base_spec())
        self.assertEqual(remaining_floor_life(arrangement), 27)
        self.assertFalse(bake_required(arrangement))

    def test_exactly_spent_floor_life_requires_a_bake(self):
        arrangement = validate_arrangement(
            base_spec(days_since_seal_opened=30, floor_life_days=30)
        )
        self.assertEqual(remaining_floor_life(arrangement), 0)
        self.assertTrue(bake_required(arrangement))

    def test_overspent_floor_life_is_reported_negative(self):
        arrangement = validate_arrangement(
            base_spec(days_since_seal_opened=45, floor_life_days=30)
        )
        self.assertEqual(remaining_floor_life(arrangement), -15)
        self.assertTrue(bake_required(arrangement))


class FindingsAndVerdictTests(unittest.TestCase):
    def test_good_arrangement_is_adequate_and_released(self):
        result = assess_die_storage(base_spec())
        self.assertEqual(result["verdict"], "adequate")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["required_actions"], [])
        self.assertTrue(result["release_to_assembly"])

    def test_loose_tray_is_inadequate_and_names_the_transfer(self):
        result = assess_die_storage(base_spec(carrier="loose-tray"))
        self.assertEqual(result["verdict"], "inadequate")
        self.assertFalse(result["release_to_assembly"])
        self.assertIn(
            "transfer the dies into an electrostatic dissipative carrier",
            result["required_actions"],
        )

    def test_missing_desiccant_is_recoverable_not_fatal(self):
        result = assess_die_storage(base_spec(desiccant_present=False))
        self.assertEqual(result["verdict"], "conditionally-adequate")
        self.assertIn("re-seal the bag with fresh desiccant", result["required_actions"])

    def test_hot_store_is_flagged_and_routed_back(self):
        result = assess_die_storage(base_spec(storage_temperature_c=48.0))
        self.assertTrue(any("outside the" in f for f in result["findings"]))
        self.assertIn(
            "return the batch to a store inside the declared conditions",
            result["required_actions"],
        )

    def test_spent_floor_life_orders_a_bake(self):
        result = assess_die_storage(
            base_spec(days_since_seal_opened=30, floor_life_days=30)
        )
        self.assertTrue(result["bake_required"])
        self.assertIn(
            "bake the dies before they are released to assembly",
            result["required_actions"],
        )

    def test_missing_indicator_is_reported_as_an_unreadable_bag(self):
        findings = storage_findings(
            validate_arrangement(base_spec(humidity_indicator_present=False))
        )
        self.assertTrue(any("humidity indicator" in f for f in findings))

    def test_actions_are_empty_for_a_clean_arrangement(self):
        self.assertEqual(required_actions(validate_arrangement(base_spec())), [])

    def test_governing_barrier_is_one_of_the_declared_barriers(self):
        self.assertIn(assess_die_storage(base_spec())["governing_barrier"], BARRIERS)

    def test_assessment_rejects_a_bad_spec(self):
        with self.assertRaises(ValueError):
            assess_die_storage(base_spec(seal="cling-film"))


if __name__ == "__main__":
    unittest.main()
