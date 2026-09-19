"""Contract tests for the ECSS-Q-ST-70-29 collection-system logic."""

import unittest

from q7029_collection_system_logic import (
    KIND_COLD_FINGER,
    KIND_SORBENT,
    capture_for_compound,
    cold_finger_captures,
    derated_breakthrough_volume,
    ordering_findings,
    series_capture_fraction,
    size_collection_train,
    sorbent_captures,
    validate_compound,
    validate_sampling,
    validate_stage,
    validate_train,
)

COLD = {
    "name": "cold-finger-1",
    "kind": KIND_COLD_FINGER,
    "efficiency": 0.9,
    "surface_temperature_k": 200.0,
    "required_margin_k": 20.0,
}
BED = {
    "name": "tenax-bed",
    "kind": KIND_SORBENT,
    "efficiency": 0.9,
    "temperature_k": 298.15,
    "reference_temperature_k": 298.15,
}

TOLUENE = {
    "name": "toluene",
    "condensation_temperature_k": 383.0,
    "breakthrough_volume_l": {"tenax-bed": 20.0},
}
METHANE = {
    "name": "methane",
    "condensation_temperature_k": 111.0,
    "breakthrough_volume_l": {"tenax-bed": 0.2},
}


def spec(**over):
    base = {
        "stages": [dict(COLD), dict(BED)],
        "compounds": [dict(TOLUENE)],
        "swept_volume_l": 5.0,
        "duration_h": 24.0,
        "safety_factor": 2.0,
        "minimum_capture_fraction": 0.95,
    }
    base.update(over)
    return base


class StageValidationTests(unittest.TestCase):
    def test_valid_sorbent_stage(self):
        stage = validate_stage(dict(BED), 0)
        self.assertEqual(stage["kind"], KIND_SORBENT)
        self.assertAlmostEqual(stage["efficiency"], 0.9, places=9)

    def test_unknown_stage_kind_rejected(self):
        bad = dict(BED)
        bad["kind"] = "impinger"
        with self.assertRaises(ValueError):
            validate_stage(bad, 0)

    def test_efficiency_above_one_rejected(self):
        bad = dict(BED)
        bad["efficiency"] = 1.4
        with self.assertRaises(ValueError):
            validate_stage(bad, 0)

    def test_zero_efficiency_rejected(self):
        bad = dict(BED)
        bad["efficiency"] = 0.0
        with self.assertRaises(ValueError):
            validate_stage(bad, 0)

    def test_unnamed_stage_rejected(self):
        bad = dict(BED)
        bad["name"] = "  "
        with self.assertRaises(ValueError):
            validate_stage(bad, 0)

    def test_cold_finger_default_margin_is_applied(self):
        bare = {
            "name": "finger",
            "kind": KIND_COLD_FINGER,
            "efficiency": 0.8,
            "surface_temperature_k": 120.0,
        }
        self.assertAlmostEqual(validate_stage(bare, 0)["required_margin_k"], 20.0, places=9)

    def test_empty_train_rejected(self):
        with self.assertRaises(ValueError):
            validate_train([])

    def test_duplicate_stage_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_train([dict(BED), dict(BED)])


class CompoundAndSamplingTests(unittest.TestCase):
    def test_valid_compound(self):
        compound = validate_compound(dict(TOLUENE))
        self.assertEqual(compound["name"], "toluene")
        self.assertAlmostEqual(
            compound["breakthrough_volume_l"]["tenax-bed"], 20.0, places=9
        )

    def test_unnamed_compound_rejected(self):
        bad = dict(TOLUENE)
        bad["name"] = ""
        with self.assertRaises(ValueError):
            validate_compound(bad)

    def test_negative_breakthrough_volume_rejected(self):
        bad = dict(TOLUENE)
        bad["breakthrough_volume_l"] = {"tenax-bed": -1.0}
        with self.assertRaises(ValueError):
            validate_compound(bad)

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling(5.0, 24.0, 0.8)

    def test_safety_factor_exactly_one_is_allowed(self):
        self.assertAlmostEqual(
            validate_sampling(5.0, 24.0, 1.0)["safety_factor"], 1.0, places=9
        )

    def test_zero_swept_volume_rejected(self):
        with self.assertRaises(ValueError):
            validate_sampling(0.0, 24.0, 2.0)


class DeratingTests(unittest.TestCase):
    def test_bed_at_reference_temperature_keeps_its_volume(self):
        self.assertAlmostEqual(
            derated_breakthrough_volume(20.0, 298.15, 298.15), 20.0, places=9
        )

    def test_bed_below_reference_temperature_is_not_uprated(self):
        self.assertAlmostEqual(
            derated_breakthrough_volume(20.0, 280.0, 298.15), 20.0, places=9
        )

    def test_warm_bed_loses_breakthrough_volume(self):
        warm = derated_breakthrough_volume(20.0, 308.15, 298.15)
        self.assertAlmostEqual(warm, 20.0 * 0.8, places=9)

    def test_very_hot_bed_holds_nothing(self):
        self.assertAlmostEqual(
            derated_breakthrough_volume(20.0, 498.15, 298.15), 0.0, places=9
        )

    def test_zero_catalogue_volume_rejected(self):
        with self.assertRaises(ValueError):
            derated_breakthrough_volume(0.0, 298.15, 298.15)


class StageCaptureTests(unittest.TestCase):
    def setUp(self):
        self.sampling = validate_sampling(5.0, 24.0, 2.0)
        self.bed = validate_stage(dict(BED), 1)
        self.cold = validate_stage(dict(COLD), 0)

    def test_bed_holds_a_heavy_compound(self):
        holds, allowed, why = sorbent_captures(
            self.bed, validate_compound(dict(TOLUENE)), self.sampling
        )
        self.assertTrue(holds)
        self.assertAlmostEqual(allowed, 10.0, places=9)
        self.assertIsNone(why)

    def test_bed_breaks_through_on_a_light_compound(self):
        holds, _, why = sorbent_captures(
            self.bed, validate_compound(dict(METHANE)), self.sampling
        )
        self.assertFalse(holds)
        self.assertIn("exceeds", why)

    def test_swept_volume_exactly_on_the_allowance_still_holds(self):
        sampling = validate_sampling(10.0, 24.0, 2.0)
        holds, allowed, _ = sorbent_captures(
            self.bed, validate_compound(dict(TOLUENE)), sampling
        )
        self.assertAlmostEqual(allowed, sampling["swept_volume_l"], places=9)
        self.assertTrue(holds)

    def test_undeclared_breakthrough_volume_means_no_capture(self):
        compound = validate_compound(
            {"name": "argon", "condensation_temperature_k": 87.0}
        )
        holds, _, why = sorbent_captures(self.bed, compound, self.sampling)
        self.assertFalse(holds)
        self.assertIn("no breakthrough volume", why)

    def test_cold_finger_with_margin_captures(self):
        holds, required, why = cold_finger_captures(
            self.cold, validate_compound(dict(TOLUENE))
        )
        self.assertTrue(holds)
        self.assertAlmostEqual(required, 363.0, places=9)
        self.assertIsNone(why)

    def test_cold_finger_exactly_at_the_required_margin_captures(self):
        stage = validate_stage(
            {
                "name": "edge-finger",
                "kind": KIND_COLD_FINGER,
                "efficiency": 0.9,
                "surface_temperature_k": 363.0,
                "required_margin_k": 20.0,
            },
            0,
        )
        holds, required, _ = cold_finger_captures(
            stage, validate_compound(dict(TOLUENE))
        )
        self.assertAlmostEqual(stage["surface_temperature_k"], required, places=9)
        self.assertTrue(holds)

    def test_cold_finger_too_warm_for_a_light_compound(self):
        holds, _, why = cold_finger_captures(
            self.cold, validate_compound(dict(METHANE))
        )
        self.assertFalse(holds)
        self.assertIn("not", why)

    def test_wrong_stage_kind_rejected(self):
        with self.assertRaises(ValueError):
            cold_finger_captures(self.bed, validate_compound(dict(TOLUENE)))


class SeriesTests(unittest.TestCase):
    def test_two_stages_combine_multiplicatively_not_additively(self):
        self.assertAlmostEqual(series_capture_fraction([0.9, 0.9]), 0.99, places=9)

    def test_single_stage_passes_through(self):
        self.assertAlmostEqual(series_capture_fraction([0.75]), 0.75, places=9)

    def test_a_perfect_stage_gives_full_capture(self):
        self.assertAlmostEqual(series_capture_fraction([0.5, 1.0]), 1.0, places=9)

    def test_empty_series_captures_nothing(self):
        self.assertAlmostEqual(series_capture_fraction([]), 0.0, places=9)

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            series_capture_fraction(0.9)


class OrderingTests(unittest.TestCase):
    def test_cold_first_train_has_no_ordering_finding(self):
        self.assertEqual(ordering_findings(validate_train([dict(COLD), dict(BED)])), [])

    def test_sorbent_ahead_of_cold_is_a_finding(self):
        findings = ordering_findings(validate_train([dict(BED), dict(COLD)]))
        self.assertEqual(len(findings), 1)
        self.assertIn("upstream", findings[0])


class TrainSizingTests(unittest.TestCase):
    def test_well_sized_train_is_adequate(self):
        result = size_collection_train(spec())
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["limiting_capture_fraction"], 0.99, places=9)
        self.assertEqual(result["findings"], [])

    def test_light_compound_drives_the_limiting_case(self):
        result = size_collection_train(
            spec(compounds=[dict(TOLUENE), dict(METHANE)])
        )
        self.assertFalse(result["adequate"])
        self.assertEqual(result["limiting_compound"], "methane")

    def test_uncaptured_compound_is_named_not_assumed_absent(self):
        result = size_collection_train(spec(compounds=[dict(METHANE)]))
        self.assertAlmostEqual(result["limiting_capture_fraction"], 0.0, places=9)
        self.assertTrue(any("unmeasured" in f for f in result["findings"]))

    def test_warm_bed_loses_a_stage_and_the_capture_falls(self):
        warm_bed = dict(BED)
        warm_bed["temperature_k"] = 348.15
        result = size_collection_train(spec(stages=[dict(COLD), warm_bed]))
        self.assertAlmostEqual(result["limiting_capture_fraction"], 0.9, places=9)
        self.assertFalse(result["adequate"])

    def test_bad_ordering_is_reported_even_when_capture_is_adequate(self):
        result = size_collection_train(spec(stages=[dict(BED), dict(COLD)]))
        self.assertTrue(result["adequate"])
        self.assertTrue(any("upstream" in f for f in result["findings"]))

    def test_larger_safety_factor_can_break_a_marginal_bed(self):
        loose = size_collection_train(spec(safety_factor=2.0))
        tight = size_collection_train(spec(safety_factor=8.0))
        self.assertGreater(
            loose["limiting_capture_fraction"], tight["limiting_capture_fraction"]
        )

    def test_duplicate_compound_rejected(self):
        with self.assertRaises(ValueError):
            size_collection_train(spec(compounds=[dict(TOLUENE), dict(TOLUENE)]))

    def test_empty_compound_list_rejected(self):
        with self.assertRaises(ValueError):
            size_collection_train(spec(compounds=[]))

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["swept_volume_l"]
        with self.assertRaises(ValueError):
            size_collection_train(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            size_collection_train(["stages"])


if __name__ == "__main__":
    unittest.main()
