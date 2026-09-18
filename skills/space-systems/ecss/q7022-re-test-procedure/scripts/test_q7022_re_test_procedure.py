"""Contract test for the re-test-procedure leaf (stdlib unittest)."""

import unittest

from q7022_re_test_procedure_logic import (
    DEFAULT_RETENTION,
    LARGE_LOT_SAMPLE_SIZE,
    acceptance_threshold,
    assess_re_test,
    build_re_test_plan,
    evaluate_property,
    evaluate_results,
    required_properties,
    sample_size,
)

ORIGINALS = {
    "application-life": 60.0,
    "cure-hardness": 50.0,
    "adhesion-strength": 20.0,
}


def plan(family="sealant", lot_units=10, retention=DEFAULT_RETENTION):
    return build_re_test_plan(family, lot_units, ORIGINALS, retention)


def good_results():
    return {
        "application-life": [58.0, 59.0, 60.0],
        "cure-hardness": [49.0, 50.0, 51.0],
        "adhesion-strength": [19.0, 19.5, 20.0],
    }


def spec(**kw):
    base = {
        "family": "sealant",
        "lot_units": 10,
        "originals": ORIGINALS,
        "results": good_results(),
        "requested_extension_days": 180,
    }
    base.update(kw)
    return base


class TestSampleSize(unittest.TestCase):
    def test_small_lot_owes_two_specimens(self):
        self.assertEqual(sample_size(8), 2)

    def test_the_bracket_boundary_belongs_to_the_lower_bracket(self):
        self.assertEqual(sample_size(25), 3)
        self.assertEqual(sample_size(26), 5)

    def test_a_large_lot_owes_the_top_count(self):
        self.assertEqual(sample_size(500), LARGE_LOT_SAMPLE_SIZE)

    def test_zero_units_raises(self):
        with self.assertRaises(ValueError):
            sample_size(0)

    def test_boolean_lot_size_raises(self):
        with self.assertRaises(ValueError):
            sample_size(True)


class TestRequiredProperties(unittest.TestCase):
    def test_a_known_family_lists_its_properties(self):
        self.assertIn("lap-shear-strength", required_properties("adhesive-paste"))

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(required_properties("Prepreg"), required_properties("prepreg"))

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            required_properties("moon-dust")

    def test_the_returned_list_is_a_copy(self):
        first = required_properties("sealant")
        first.append("invented-property")
        self.assertNotIn("invented-property", required_properties("sealant"))


class TestAcceptanceThreshold(unittest.TestCase):
    def test_a_min_property_only_gets_a_lower_bound(self):
        record = acceptance_threshold("adhesion-strength", 20.0, 0.9)
        self.assertAlmostEqual(record["lower"], 18.0, places=9)
        self.assertIsNone(record["upper"])

    def test_a_max_property_only_gets_an_upper_bound(self):
        record = acceptance_threshold("viscosity", 100.0, 0.9)
        self.assertIsNone(record["lower"])
        self.assertAlmostEqual(record["upper"], 110.0, places=9)

    def test_a_banded_property_gets_both_bounds(self):
        record = acceptance_threshold("gel-time", 100.0, 0.9)
        self.assertAlmostEqual(record["lower"], 90.0, places=9)
        self.assertAlmostEqual(record["upper"], 110.0, places=9)

    def test_a_tighter_retention_narrows_the_band(self):
        record = acceptance_threshold("gel-time", 100.0, 0.95)
        self.assertAlmostEqual(record["lower"], 95.0, places=9)
        self.assertAlmostEqual(record["upper"], 105.0, places=9)

    def test_unknown_property_raises(self):
        with self.assertRaises(ValueError):
            acceptance_threshold("vibes", 10.0)

    def test_retention_outside_the_open_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            acceptance_threshold("gel-time", 100.0, 1.0)

    def test_non_positive_original_raises(self):
        with self.assertRaises(ValueError):
            acceptance_threshold("gel-time", 0.0)


class TestBuildPlan(unittest.TestCase):
    def test_plan_covers_every_required_property(self):
        built = plan()
        self.assertEqual([p["property"] for p in built["properties"]],
                         required_properties("sealant"))

    def test_plan_carries_the_specimen_count(self):
        self.assertEqual(plan(lot_units=200)["specimens_per_property"],
                         LARGE_LOT_SAMPLE_SIZE)

    def test_a_missing_as_manufactured_value_raises(self):
        with self.assertRaises(ValueError):
            build_re_test_plan("sealant", 10, {"application-life": 60.0})

    def test_non_mapping_originals_raises(self):
        with self.assertRaises(ValueError):
            build_re_test_plan("sealant", 10, [60.0, 50.0, 20.0])


class TestEvaluateProperty(unittest.TestCase):
    def test_results_inside_the_band_are_accepted(self):
        record = plan()["properties"][0]
        graded = evaluate_property(record, [58.0, 59.0, 60.0])
        self.assertTrue(graded["accepted"])
        self.assertAlmostEqual(graded["mean"], 59.0, places=9)

    def test_a_value_exactly_on_the_lower_bound_is_accepted(self):
        record = acceptance_threshold("adhesion-strength", 20.0, 0.9)
        record["specimens"] = 1
        self.assertAlmostEqual(record["lower"], 18.0, places=9)
        self.assertTrue(evaluate_property(record, [18.0])["accepted"])

    def test_a_value_exactly_on_the_upper_bound_is_accepted(self):
        record = acceptance_threshold("viscosity", 100.0, 0.9)
        record["specimens"] = 1
        self.assertAlmostEqual(record["upper"], 110.0, places=9)
        self.assertTrue(evaluate_property(record, [110.0])["accepted"])

    def test_one_failing_specimen_fails_the_property(self):
        record = plan()["properties"][2]
        graded = evaluate_property(record, [20.0, 19.0, 12.0])
        self.assertFalse(graded["accepted"])
        self.assertAlmostEqual(graded["first_failing_value"], 12.0, places=9)

    def test_too_few_specimens_is_flagged_and_not_accepted(self):
        record = plan()["properties"][0]
        graded = evaluate_property(record, [59.0])
        self.assertTrue(graded["under_sampled"])
        self.assertFalse(graded["accepted"])

    def test_empty_result_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_property(plan()["properties"][0], [])

    def test_non_numeric_result_raises(self):
        with self.assertRaises(ValueError):
            evaluate_property(plan()["properties"][0], [59.0, "sixty", 60.0])

    def test_bad_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_property({"property": "gel-time"}, [1.0])


class TestEvaluateResults(unittest.TestCase):
    def test_a_complete_result_set_has_nothing_missing(self):
        outcome = evaluate_results(plan(), good_results())
        self.assertEqual(outcome["missing_properties"], [])
        self.assertEqual(outcome["failed_properties"], [])

    def test_an_untested_property_is_missing_not_failing(self):
        results = good_results()
        del results["cure-hardness"]
        outcome = evaluate_results(plan(), results)
        self.assertEqual(outcome["missing_properties"], ["cure-hardness"])
        self.assertEqual(outcome["failed_properties"], [])

    def test_a_property_outside_the_plan_is_reported_separately(self):
        results = good_results()
        results["peel-strength"] = [5.0, 5.0, 5.0]
        outcome = evaluate_results(plan(), results)
        self.assertEqual(outcome["unplanned_properties"], ["peel-strength"])

    def test_non_mapping_results_raises(self):
        with self.assertRaises(ValueError):
            evaluate_results(plan(), [59.0])

    def test_bad_plan_raises(self):
        with self.assertRaises(ValueError):
            evaluate_results({"family": "sealant"}, good_results())


class TestAssessReTest(unittest.TestCase):
    def test_a_complete_passing_re_test_supports_the_extension(self):
        report = assess_re_test(spec())
        self.assertEqual(report["disposition"], "re-test-passed")
        self.assertTrue(report["supports_extension"])
        self.assertEqual(report["extension_days_supported"], 180)
        self.assertEqual(report["findings"], [])

    def test_a_failing_property_fails_the_re_test(self):
        results = good_results()
        results["adhesion-strength"] = [20.0, 19.0, 10.0]
        report = assess_re_test(spec(results=results))
        self.assertEqual(report["disposition"], "re-test-failed")
        self.assertEqual(report["extension_days_supported"], 0)

    def test_an_untested_property_makes_the_re_test_incomplete(self):
        results = good_results()
        del results["application-life"]
        report = assess_re_test(spec(results=results))
        self.assertEqual(report["disposition"], "re-test-incomplete")
        self.assertFalse(report["supports_extension"])

    def test_under_sampling_makes_the_re_test_incomplete_not_failed(self):
        results = good_results()
        results["cure-hardness"] = [50.0]
        report = assess_re_test(spec(results=results))
        self.assertEqual(report["disposition"], "re-test-incomplete")
        self.assertEqual(report["under_sampled_properties"], ["cure-hardness"])

    def test_a_real_failure_outranks_an_incomplete_property(self):
        results = good_results()
        results["adhesion-strength"] = [10.0, 10.0, 10.0]
        del results["application-life"]
        report = assess_re_test(spec(results=results))
        self.assertEqual(report["disposition"], "re-test-failed")

    def test_a_tighter_retention_can_fail_a_previously_passing_set(self):
        results = good_results()
        results["adhesion-strength"] = [18.5, 18.5, 18.5]
        self.assertEqual(assess_re_test(spec(results=results))["disposition"],
                         "re-test-passed")
        self.assertEqual(
            assess_re_test(spec(results=results, retention=0.95))["disposition"],
            "re-test-failed")

    def test_missing_spec_key_raises(self):
        broken = spec()
        del broken["results"]
        with self.assertRaises(ValueError):
            assess_re_test(broken)

    def test_zero_requested_extension_raises(self):
        with self.assertRaises(ValueError):
            assess_re_test(spec(requested_extension_days=0))

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_re_test("sealant")


if __name__ == "__main__":
    unittest.main()
