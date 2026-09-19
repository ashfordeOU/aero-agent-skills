"""Contract tests for the radiation-test specimen preparation logic."""

import unittest

from q7006_specimen_preparation_logic import (
    MINIMUM_REPLICATES,
    coupon_area_mm2,
    coupons_per_run,
    exposed_coupons_for_property,
    plan_specimens,
    population_findings,
    reference_coupons_for_property,
    run_count,
    validate_property,
)

ABSORPTANCE = {"name": "solar-absorptance", "destructive": False, "in_situ": True}
EMITTANCE = {"name": "infrared-emittance", "destructive": False}
TENSILE = {"name": "tensile-strength", "destructive": True}


def base_spec(**overrides):
    spec = {
        "properties": [dict(ABSORPTANCE), dict(EMITTANCE), dict(TENSILE)],
        "measurement_points": 4,
        "coupon_mm": (25.0, 25.0),
        "uniform_area_mm": (200.0, 100.0),
        "gap_mm": 0.0,
        "edge_keep_out_mm": 0.0,
    }
    spec.update(overrides)
    return spec


class ValidatePropertyTests(unittest.TestCase):
    def test_defaults_to_the_replicate_minimum(self):
        self.assertEqual(validate_property(EMITTANCE)["replicates"], MINIMUM_REPLICATES)

    def test_name_is_stripped(self):
        record = validate_property({"name": "  mass-loss ", "destructive": True})
        self.assertEqual(record["name"], "mass-loss")

    def test_in_situ_defaults_to_false(self):
        self.assertFalse(validate_property(EMITTANCE)["in_situ"])

    def test_destructive_and_in_situ_together_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "x", "destructive": True, "in_situ": True})

    def test_non_boolean_destructive_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "x", "destructive": "yes"})

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "   ", "destructive": False})

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "x"})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_property(["name"])

    def test_zero_replicates_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "x", "destructive": False, "replicates": 0})

    def test_float_replicates_rejected(self):
        with self.assertRaises(ValueError):
            validate_property({"name": "x", "destructive": False, "replicates": 3.0})


class CouponDemandTests(unittest.TestCase):
    def test_destructive_property_consumes_a_set_per_point(self):
        self.assertEqual(exposed_coupons_for_property(TENSILE, 4), 4 * MINIMUM_REPLICATES)

    def test_non_destructive_property_reuses_one_set(self):
        self.assertEqual(exposed_coupons_for_property(EMITTANCE, 4), MINIMUM_REPLICATES)

    def test_replicate_count_scales_the_demand(self):
        prop = dict(TENSILE, replicates=5)
        self.assertEqual(exposed_coupons_for_property(prop, 3), 15)

    def test_destructive_property_needs_matching_references(self):
        self.assertEqual(reference_coupons_for_property(TENSILE, 4), 4 * MINIMUM_REPLICATES)

    def test_in_situ_property_needs_no_reference_coupon(self):
        self.assertEqual(reference_coupons_for_property(ABSORPTANCE, 4), 0)

    def test_ex_situ_non_destructive_property_needs_one_reference_set(self):
        self.assertEqual(reference_coupons_for_property(EMITTANCE, 4), MINIMUM_REPLICATES)

    def test_zero_measurement_points_rejected(self):
        with self.assertRaises(ValueError):
            exposed_coupons_for_property(TENSILE, 0)

    def test_boolean_measurement_points_rejected(self):
        with self.assertRaises(ValueError):
            exposed_coupons_for_property(TENSILE, True)


class GeometryTests(unittest.TestCase):
    def test_area_is_the_product(self):
        self.assertAlmostEqual(coupon_area_mm2((25.0, 20.0)), 500.0, places=9)

    def test_zero_dimension_rejected(self):
        with self.assertRaises(ValueError):
            coupon_area_mm2((25.0, 0.0))

    def test_malformed_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            coupon_area_mm2((25.0,))

    def test_exact_grid_fit(self):
        self.assertEqual(coupons_per_run((25.0, 25.0), (100.0, 50.0)), 8)

    def test_gap_reduces_the_capacity(self):
        packed = coupons_per_run((25.0, 25.0), (100.0, 50.0))
        spaced = coupons_per_run((25.0, 25.0), (100.0, 50.0), gap_mm=5.0)
        self.assertEqual(spaced, 3)
        self.assertLess(spaced, packed)

    def test_rotating_the_coupon_is_allowed(self):
        self.assertEqual(coupons_per_run((40.0, 10.0), (50.0, 40.0)), 5)

    def test_edge_keep_out_shrinks_the_usable_area(self):
        self.assertEqual(
            coupons_per_run((25.0, 25.0), (100.0, 50.0), edge_keep_out_mm=5.0), 3
        )

    def test_oversized_coupon_does_not_fit(self):
        self.assertEqual(coupons_per_run((300.0, 300.0), (100.0, 50.0)), 0)

    def test_keep_out_can_consume_the_whole_area(self):
        self.assertEqual(coupons_per_run((5.0, 5.0), (20.0, 20.0), edge_keep_out_mm=10.0), 0)

    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):
            coupons_per_run((25.0, 25.0), (100.0, 50.0), gap_mm=-1.0)


class RunCountTests(unittest.TestCase):
    def test_exact_multiple_needs_no_extra_run(self):
        self.assertEqual(run_count(16, 8), 2)

    def test_remainder_rounds_up(self):
        self.assertEqual(run_count(17, 8), 3)

    def test_empty_population_needs_no_run(self):
        self.assertEqual(run_count(0, 8), 0)

    def test_zero_capacity_with_coupons_is_refused(self):
        with self.assertRaises(ValueError):
            run_count(4, 0)

    def test_negative_total_rejected(self):
        with self.assertRaises(ValueError):
            run_count(-1, 8)


class PopulationFindingTests(unittest.TestCase):
    def test_no_property_is_a_finding(self):
        notes = population_findings([], (25.0, 25.0), (100.0, 50.0), 8)
        self.assertEqual(len(notes), 1)

    def test_thin_replicate_count_is_a_finding(self):
        record = validate_property({"name": "x", "destructive": True, "replicates": 1})
        notes = population_findings([record], (25.0, 25.0), (100.0, 50.0), 8)
        self.assertTrue(any("below the minimum" in note for note in notes))

    def test_unfittable_coupon_is_a_finding(self):
        record = validate_property(EMITTANCE)
        notes = population_findings([record], (300.0, 300.0), (100.0, 50.0), 0)
        self.assertTrue(any("does not fit" in note for note in notes))

    def test_clean_population_has_no_findings(self):
        record = validate_property(EMITTANCE)
        self.assertEqual(population_findings([record], (25.0, 25.0), (100.0, 50.0), 8), [])


class PlanSpecimensTests(unittest.TestCase):
    def test_exposed_total_sums_the_properties(self):
        result = plan_specimens(base_spec())
        self.assertEqual(result["exposed_coupons"], 3 + 3 + 12)

    def test_reference_total_excludes_in_situ_properties(self):
        result = plan_specimens(base_spec())
        self.assertEqual(result["reference_coupons"], 0 + 3 + 12)

    def test_total_is_exposed_plus_reference(self):
        result = plan_specimens(base_spec())
        self.assertEqual(
            result["total_coupons"], result["exposed_coupons"] + result["reference_coupons"]
        )

    def test_spare_fraction_rounds_up(self):
        result = plan_specimens(base_spec(spare_fraction=0.1))
        self.assertEqual(result["spare_coupons"], 2)

    def test_spare_fraction_of_zero_adds_nothing(self):
        self.assertEqual(plan_specimens(base_spec())["spare_coupons"], 0)

    def test_more_measurement_points_need_more_coupons(self):
        few = plan_specimens(base_spec(measurement_points=2))
        many = plan_specimens(base_spec(measurement_points=6))
        self.assertGreater(many["exposed_coupons"], few["exposed_coupons"])

    def test_run_count_follows_the_capacity(self):
        result = plan_specimens(base_spec())
        self.assertEqual(
            result["exposure_runs"],
            -(-result["exposed_coupons"] // result["coupons_per_run"]),
        )

    def test_small_uniform_area_forces_more_runs(self):
        wide = plan_specimens(base_spec())
        narrow = plan_specimens(base_spec(uniform_area_mm=(50.0, 50.0)))
        self.assertGreater(narrow["exposure_runs"], wide["exposure_runs"])

    def test_clean_plan_is_ready(self):
        result = plan_specimens(base_spec())
        self.assertTrue(result["ready"])
        self.assertEqual(result["findings"], [])

    def test_oversized_coupon_plan_is_not_ready(self):
        result = plan_specimens(base_spec(coupon_mm=(500.0, 500.0)))
        self.assertFalse(result["ready"])
        self.assertEqual(result["exposure_runs"], 0)

    def test_duplicate_property_names_rejected(self):
        spec = base_spec(properties=[dict(EMITTANCE), dict(EMITTANCE)])
        with self.assertRaises(ValueError):
            plan_specimens(spec)

    def test_spare_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            plan_specimens(base_spec(spare_fraction=1.5))

    def test_missing_key_rejected(self):
        spec = base_spec()
        del spec["coupon_mm"]
        with self.assertRaises(ValueError):
            plan_specimens(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            plan_specimens(["properties"])

    def test_coupon_area_is_reported(self):
        self.assertAlmostEqual(plan_specimens(base_spec())["coupon_area_mm2"], 625.0, places=9)


if __name__ == "__main__":
    unittest.main()
