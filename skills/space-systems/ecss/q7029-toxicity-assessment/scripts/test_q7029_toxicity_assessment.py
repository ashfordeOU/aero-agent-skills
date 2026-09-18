"""Contract tests for the ECSS-Q-ST-70-29 SMAC toxicity-assessment logic."""

import unittest

from q7029_toxicity_assessment_logic import (
    T_VALUE_LIMIT,
    T_VALUE_TOLERANCE,
    apply_removal_credit,
    assess_toxicity,
    governing_group,
    group_totals,
    lookup_smac,
    scale_to_cabin,
    t_ratio,
    validate_cabin_model,
)

MODEL = {
    "vessel_volume_m3": 0.002,
    "cabin_volume_m3": 100.0,
    "tested_mass_g": 50.0,
    "flown_mass_g": 5000.0,
    "exposure_duration_h": 180.0,
}

SMACS = {
    "toluene": {24.0: 60.0, 180.0: 16.0, 1000.0: 16.0},
    "benzene": {24.0: 32.0, 180.0: 0.3},
    "hexanal": {180.0: 10.0},
    "acetaldehyde": {180.0: 4.0},
}


def product(compound, conc, group=None, removal=0.0):
    entry = {"compound": compound, "vessel_concentration_mg_m3": conc}
    if group is not None:
        entry["group"] = group
    if removal:
        entry["removal_fraction"] = removal
    return entry


class CabinModelTests(unittest.TestCase):
    def test_valid_model_is_normalised(self):
        m = validate_cabin_model(MODEL)
        self.assertAlmostEqual(m["cabin_volume_m3"], 100.0)
        self.assertAlmostEqual(m["flown_mass_g"], 5000.0)

    def test_missing_key_rejected(self):
        bad = dict(MODEL)
        del bad["cabin_volume_m3"]
        with self.assertRaises(ValueError):
            validate_cabin_model(bad)

    def test_zero_cabin_volume_rejected(self):
        bad = dict(MODEL, cabin_volume_m3=0.0)
        with self.assertRaises(ValueError):
            validate_cabin_model(bad)

    def test_negative_flown_mass_rejected(self):
        bad = dict(MODEL, flown_mass_g=-5.0)
        with self.assertRaises(ValueError):
            validate_cabin_model(bad)

    def test_non_mapping_model_rejected(self):
        with self.assertRaises(ValueError):
            validate_cabin_model(["vessel_volume_m3"])


class ScalingTests(unittest.TestCase):
    def test_scaling_uses_mass_and_volume_ratios(self):
        # 100 mg/m3 * (5000/50) * (0.002/100) = 0.2 mg/m3
        self.assertAlmostEqual(scale_to_cabin(100.0, MODEL), 0.2, places=9)

    def test_scaling_is_linear_in_the_measured_concentration(self):
        self.assertAlmostEqual(
            scale_to_cabin(200.0, MODEL), 2.0 * scale_to_cabin(100.0, MODEL), places=9
        )

    def test_a_larger_cabin_dilutes_the_prediction(self):
        big = dict(MODEL, cabin_volume_m3=200.0)
        self.assertAlmostEqual(scale_to_cabin(100.0, big), 0.1, places=9)

    def test_negative_concentration_rejected(self):
        with self.assertRaises(ValueError):
            scale_to_cabin(-1.0, MODEL)

    def test_removal_credit_reduces_the_concentration(self):
        self.assertAlmostEqual(apply_removal_credit(1.0, 0.75), 0.25, places=9)

    def test_zero_removal_leaves_the_concentration(self):
        self.assertAlmostEqual(apply_removal_credit(1.0, 0.0), 1.0, places=9)

    def test_total_removal_rejected(self):
        with self.assertRaises(ValueError):
            apply_removal_credit(1.0, 1.0)


class SmacLookupTests(unittest.TestCase):
    def test_exact_duration_is_returned(self):
        self.assertAlmostEqual(lookup_smac(SMACS, "benzene", 180.0), 0.3, places=9)

    def test_shorter_exposure_uses_its_own_limit(self):
        self.assertAlmostEqual(lookup_smac(SMACS, "benzene", 24.0), 32.0, places=9)

    def test_uncovered_duration_falls_to_the_next_longer_limit(self):
        self.assertAlmostEqual(lookup_smac(SMACS, "toluene", 100.0), 16.0, places=9)

    def test_duration_beyond_the_table_has_no_limit(self):
        self.assertIsNone(lookup_smac(SMACS, "benzene", 4000.0))

    def test_unknown_compound_has_no_limit(self):
        self.assertIsNone(lookup_smac(SMACS, "unknown-siloxane", 180.0))

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            lookup_smac({}, "benzene", 180.0)


class RatioAndGroupTests(unittest.TestCase):
    def test_ratio_is_concentration_over_limit(self):
        self.assertAlmostEqual(t_ratio(0.15, 0.3), 0.5, places=9)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            t_ratio(0.15, 0.0)

    def test_ratios_add_inside_a_group(self):
        totals = group_totals([
            {"compound": "a", "group": "irritant", "t_ratio": 0.4},
            {"compound": "b", "group": "irritant", "t_ratio": 0.3},
            {"compound": "c", "group": "haematotoxic", "t_ratio": 0.6},
        ])
        self.assertAlmostEqual(totals["irritant"], 0.7, places=9)
        self.assertAlmostEqual(totals["haematotoxic"], 0.6, places=9)

    def test_gap_record_contributes_nothing_to_a_total(self):
        totals = group_totals([
            {"compound": "a", "group": "irritant", "t_ratio": 0.4},
            {"compound": "b", "group": "irritant", "t_ratio": None},
        ])
        self.assertAlmostEqual(totals["irritant"], 0.4, places=9)

    def test_record_without_a_ratio_key_rejected(self):
        with self.assertRaises(ValueError):
            group_totals([{"compound": "a"}])

    def test_governing_group_is_the_largest_total(self):
        group, total = governing_group({"irritant": 0.7, "haematotoxic": 0.9})
        self.assertEqual(group, "haematotoxic")
        self.assertAlmostEqual(total, 0.9, places=9)

    def test_governing_group_tie_is_resolved_by_name(self):
        group, total = governing_group({"beta": 0.5, "alpha": 0.5})
        self.assertEqual(group, "alpha")
        self.assertAlmostEqual(total, 0.5, places=9)

    def test_empty_totals_rejected(self):
        with self.assertRaises(ValueError):
            governing_group({})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "products": [
                product("toluene", 100.0, "irritant"),
                product("hexanal", 100.0, "irritant"),
                product("benzene", 10.0, "haematotoxic"),
            ],
            "cabin_model": MODEL,
            "smac_table": SMACS,
        }
        spec.update(overrides)
        return spec

    def test_compliant_case_is_acceptable(self):
        result = assess_toxicity(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_governing_group_and_total_are_reported(self):
        result = assess_toxicity(self._spec())
        # irritant: 0.2/16 + 0.2/10 = 0.0325; haematotoxic: 0.02/0.3 = 0.0667
        self.assertEqual(result["governing_group"], "haematotoxic")
        self.assertAlmostEqual(result["governing_t_value"], 0.02 / 0.3, places=9)

    def test_driving_compounds_come_from_the_governing_group(self):
        result = assess_toxicity(self._spec())
        self.assertEqual(result["driving_compounds"], ["benzene"])

    def test_group_addition_can_exceed_the_limit_with_every_compound_compliant(self):
        spec = self._spec(products=[
            product("benzene", 100.0, "haematotoxic"),
            product("acetaldehyde", 800.0, "haematotoxic"),
        ])
        result = assess_toxicity(spec)
        for record in result["records"]:
            self.assertAlmostEqual(
                record["cabin_concentration_mg_m3"] / record["smac_mg_m3"],
                record["t_ratio"],
                places=9,
            )
        self.assertFalse(result["acceptable"])

    def test_total_exactly_on_the_unit_boundary_is_acceptable(self):
        # benzene SMAC 0.3 mg/m3; a vessel concentration of 150 mg/m3 scales to
        # 0.3 mg/m3 in the cabin, giving a ratio of exactly one.
        spec = self._spec(products=[product("benzene", 150.0, "haematotoxic")])
        result = assess_toxicity(spec)
        self.assertAlmostEqual(result["governing_t_value"], T_VALUE_LIMIT, places=9)
        self.assertTrue(result["acceptable"])

    def test_missing_smac_is_a_gap_not_a_zero(self):
        spec = self._spec(products=[
            product("benzene", 10.0, "haematotoxic"),
            product("unknown-siloxane", 900.0, "irritant"),
        ])
        result = assess_toxicity(spec)
        self.assertEqual(result["smac_gaps"], ["unknown-siloxane"])
        self.assertFalse(result["acceptable"])

    def test_removal_credit_is_recorded_as_a_dependency(self):
        spec = self._spec(products=[product("benzene", 400.0, "haematotoxic", removal=0.9)])
        result = assess_toxicity(spec)
        self.assertEqual(result["removal_credits"], ["benzene"])
        self.assertEqual(len(result["findings"]), 1)

    def test_duplicate_compound_rejected(self):
        spec = self._spec(products=[
            product("benzene", 10.0, "haematotoxic"),
            product("benzene", 20.0, "haematotoxic"),
        ])
        with self.assertRaises(ValueError):
            assess_toxicity(spec)

    def test_empty_product_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_toxicity(self._spec(products=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["smac_table"]
        with self.assertRaises(ValueError):
            assess_toxicity(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_toxicity(["products"])

    def test_tolerance_is_small_enough_to_be_a_representation_allowance(self):
        self.assertAlmostEqual(T_VALUE_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()
