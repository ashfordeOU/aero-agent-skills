"""Contract tests for the ECSS-Q-ST-70-21C flammability acceptance logic."""

import unittest

from q7021_acceptance_criteria_logic import (
    APPLICATION_CLASSES,
    LIMIT_TOLERANCE,
    assess_acceptance,
    class_limits,
    evaluate_set,
    evaluate_specimen,
    validate_specimen,
    worst_case_burn_length,
)

BAY = class_limits("vented-equipment-bay")
CABIN = class_limits("habitable-volume")


def specimen(ident="S1", burn=80.0, exposed=300.0, after_flame=2.0,
             drips=0, ignited=False, consumed=False):
    return {
        "specimen_id": ident,
        "burn_length_mm": burn,
        "specimen_length_mm": exposed,
        "after_flame_s": after_flame,
        "flaming_drips": drips,
        "drip_ignited_indicator": ignited,
        "fully_consumed": consumed,
    }


def a_set(count=3, **over):
    return [specimen(ident="S%d" % i, **over) for i in range(1, count + 1)]


class ClassLimitsTests(unittest.TestCase):
    def test_known_class_returns_its_limits(self):
        self.assertAlmostEqual(BAY["burn_length_limit_mm"], 150.0, places=9)
        self.assertEqual(BAY["name"], "vented-equipment-bay")

    def test_limits_tighten_with_the_surroundings(self):
        oxygen = class_limits("oxygen-enriched-volume")
        self.assertLess(oxygen["burn_length_limit_mm"], CABIN["burn_length_limit_mm"])
        self.assertLess(CABIN["burn_length_limit_mm"], BAY["burn_length_limit_mm"])

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            class_limits("somewhere-warm")

    def test_empty_class_name_rejected(self):
        with self.assertRaises(ValueError):
            class_limits("  ")

    def test_every_class_declares_a_minimum_specimen_count(self):
        for limits in APPLICATION_CLASSES.values():
            self.assertGreaterEqual(limits["min_specimens"], 3)


class ValidateSpecimenTests(unittest.TestCase):
    def test_normalises_a_good_record(self):
        record = validate_specimen(specimen())
        self.assertEqual(record["specimen_id"], "S1")
        self.assertAlmostEqual(record["burn_length_mm"], 80.0, places=9)

    def test_burn_longer_than_the_specimen_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(burn=320.0, exposed=300.0))

    def test_burn_exactly_equal_to_the_exposed_length_accepted(self):
        record = validate_specimen(specimen(burn=300.0, exposed=300.0))
        self.assertAlmostEqual(record["burn_length_mm"], 300.0, places=9)

    def test_negative_burn_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(burn=-1.0))

    def test_zero_exposed_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(exposed=0.0))

    def test_non_integer_drip_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(drips=1.5))

    def test_boolean_drip_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(drips=True))

    def test_ignited_indicator_with_no_drips_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(drips=0, ignited=True))

    def test_non_boolean_consumption_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_specimen(specimen(consumed="yes"))

    def test_missing_specimen_id_rejected(self):
        bad = specimen()
        del bad["specimen_id"]
        with self.assertRaises(ValueError):
            validate_specimen(bad)


class EvaluateSpecimenTests(unittest.TestCase):
    def test_short_burn_passes(self):
        self.assertEqual(evaluate_specimen(specimen(burn=80.0), BAY)["status"], "pass")

    def test_burn_past_the_limit_fails(self):
        graded = evaluate_specimen(specimen(burn=180.0), BAY)
        self.assertEqual(graded["status"], "fail")
        self.assertEqual(len(graded["reasons"]), 1)

    def test_burn_exactly_on_the_limit_passes_with_zero_margin(self):
        graded = evaluate_specimen(specimen(burn=150.0), BAY)
        self.assertEqual(graded["status"], "pass")
        self.assertAlmostEqual(graded["burn_length_margin_mm"], 0.0, places=9)

    def test_after_flame_exactly_on_the_limit_passes(self):
        graded = evaluate_specimen(specimen(after_flame=10.0), BAY)
        self.assertEqual(graded["status"], "pass")

    def test_after_flame_past_the_limit_fails(self):
        self.assertEqual(evaluate_specimen(specimen(after_flame=12.0), BAY)["status"],
                         "fail")

    def test_the_same_specimen_passes_one_class_and_fails_a_tighter_one(self):
        self.assertEqual(evaluate_specimen(specimen(burn=120.0), BAY)["status"], "pass")
        self.assertEqual(evaluate_specimen(specimen(burn=120.0), CABIN)["status"], "fail")

    def test_drips_allowed_in_the_bay_class(self):
        self.assertEqual(evaluate_specimen(specimen(drips=2), BAY)["status"], "pass")

    def test_drips_fail_a_class_that_allows_none(self):
        graded = evaluate_specimen(specimen(drips=2), CABIN)
        self.assertEqual(graded["status"], "fail")

    def test_drip_ignition_fails_even_where_drips_are_allowed(self):
        graded = evaluate_specimen(specimen(drips=1, ignited=True), BAY)
        self.assertEqual(graded["status"], "fail")

    def test_full_consumption_fails_even_inside_the_burn_limit(self):
        graded = evaluate_specimen(specimen(burn=140.0, exposed=140.0, consumed=True), BAY)
        self.assertEqual(graded["status"], "fail")

    def test_incomplete_limits_mapping_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen(specimen(), {"burn_length_limit_mm": 150.0})

    def test_tolerance_constant_is_tight(self):
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


class WorstCaseTests(unittest.TestCase):
    def test_returns_the_longest_burn(self):
        records = [specimen("S1", burn=40.0), specimen("S2", burn=95.0),
                   specimen("S3", burn=61.0)]
        self.assertAlmostEqual(worst_case_burn_length(records), 95.0, places=9)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_burn_length([])

    def test_record_without_a_burn_length_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_burn_length([{"specimen_id": "S1"}])


class EvaluateSetTests(unittest.TestCase):
    def test_full_clean_set_passes(self):
        result = evaluate_set(a_set(3), "vented-equipment-bay")
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["margin_mm"], 70.0, places=9)

    def test_one_failing_specimen_fails_the_set(self):
        records = a_set(3)
        records[1]["burn_length_mm"] = 200.0
        result = evaluate_set(records, "vented-equipment-bay")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["failing"], ["S2"])

    def test_short_set_is_inconclusive_not_a_pass(self):
        result = evaluate_set(a_set(3), "habitable-volume")
        self.assertEqual(result["status"], "inconclusive")
        self.assertTrue(result["findings"])

    def test_a_failing_short_set_still_fails(self):
        records = a_set(2)
        records[0]["burn_length_mm"] = 260.0
        self.assertEqual(evaluate_set(records, "habitable-volume")["status"], "fail")

    def test_duplicate_specimen_id_rejected(self):
        records = [specimen("S1"), specimen("S1"), specimen("S3")]
        with self.assertRaises(ValueError):
            evaluate_set(records, "vented-equipment-bay")

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_set([], "vented-equipment-bay")

    def test_worst_case_drives_the_reported_margin(self):
        records = a_set(3)
        records[2]["burn_length_mm"] = 149.0
        result = evaluate_set(records, "vented-equipment-bay")
        self.assertAlmostEqual(result["worst_case_burn_length_mm"], 149.0, places=9)
        self.assertAlmostEqual(result["margin_mm"], 1.0, places=9)


class AssessAcceptanceTests(unittest.TestCase):
    def _spec(self, **over):
        base = {"material": "polyimide-tape-grade-b",
                "application_class": "vented-equipment-bay",
                "specimens": a_set(3)}
        base.update(over)
        return base

    def test_clean_run_screens_the_material_in(self):
        result = assess_acceptance(self._spec())
        self.assertTrue(result["screened_in"])
        self.assertEqual(result["material"], "polyimide-tape-grade-b")

    def test_inconclusive_run_does_not_screen_the_material_in(self):
        result = assess_acceptance(self._spec(application_class="habitable-volume"))
        self.assertFalse(result["screened_in"])
        self.assertEqual(result["status"], "inconclusive")

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance({"material": "x", "specimens": a_set(3)})

    def test_empty_material_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance(self._spec(material="  "))

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_acceptance(a_set(3))


if __name__ == "__main__":
    unittest.main()
