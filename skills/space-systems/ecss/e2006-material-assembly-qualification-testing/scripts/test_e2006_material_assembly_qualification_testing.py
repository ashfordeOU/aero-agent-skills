#!/usr/bin/env python3
"""Gate 3 contract test for e2006-material-assembly-qualification-testing."""

import unittest

from e2006_material_assembly_qualification_testing_logic import (
    CAMPAIGN_LEVELS,
    DEFAULT_QUALIFICATION_FACTOR,
    INVERTED_GRADIENT,
    NORMAL_GRADIENT,
    NO_GRADIENT,
    REQUIRED_POLARITIES,
    assess_campaign,
    assess_item,
    derive_polarity,
    differential_potential,
    evaluate_run,
    grade_events,
    has_discharge_detection,
    normalize_item,
    normalize_polarity,
    normalize_run,
    polarity_coverage,
    qualification_stress,
)


def item(**over):
    rec = {
        "id": "kapton-blanket",
        "kind": "material",
        "predicted-differential-v": 400.0,
        "qualification-factor": 1.25,
        "required-dwell-min": 30.0,
        "event-allowance": 0,
    }
    rec.update(over)
    return rec


def normal_run(**over):
    rec = {
        "id": "R-normal",
        "item": "kapton-blanket",
        "level": "qualification",
        "surface-potential-v": -600.0,
        "structure-potential-v": 0.0,
        "dwell-min": 45.0,
        "instrumentation": ["current-transient-probe"],
        "events": [],
    }
    rec.update(over)
    return rec


def inverted_run(**over):
    rec = {
        "id": "R-inverted",
        "item": "kapton-blanket",
        "level": "qualification",
        "surface-potential-v": 0.0,
        "structure-potential-v": -600.0,
        "dwell-min": 45.0,
        "instrumentation": ["optical-flash-detector"],
        "events": [],
    }
    rec.update(over)
    return rec


class TestPolarityLabels(unittest.TestCase):
    def test_alias_maps_to_canonical_normal(self):
        self.assertEqual(normalize_polarity("Normal"), NORMAL_GRADIENT)

    def test_alias_maps_to_canonical_inverted(self):
        self.assertEqual(normalize_polarity("inverted_potential gradient"), INVERTED_GRADIENT)

    def test_unknown_label_raises(self):
        with self.assertRaises(ValueError):
            normalize_polarity("reverse-bias")

    def test_blank_label_raises(self):
        with self.assertRaises(ValueError):
            normalize_polarity("")

    def test_two_required_polarities(self):
        self.assertEqual(set(REQUIRED_POLARITIES), {NORMAL_GRADIENT, INVERTED_GRADIENT})


class TestDerivedPolarity(unittest.TestCase):
    def test_surface_below_structure_is_normal(self):
        self.assertEqual(derive_polarity(-500.0, 0.0), NORMAL_GRADIENT)

    def test_surface_above_structure_is_inverted(self):
        self.assertEqual(derive_polarity(0.0, -500.0), INVERTED_GRADIENT)

    def test_equal_potentials_give_no_gradient(self):
        self.assertEqual(derive_polarity(-120.0, -120.0), NO_GRADIENT)

    def test_both_negative_still_resolves_by_sign_of_difference(self):
        self.assertEqual(derive_polarity(-900.0, -100.0), NORMAL_GRADIENT)
        self.assertEqual(derive_polarity(-100.0, -900.0), INVERTED_GRADIENT)

    def test_non_numeric_potential_raises(self):
        with self.assertRaises(ValueError):
            derive_polarity("-500", 0.0)

    def test_differential_is_a_magnitude(self):
        self.assertAlmostEqual(differential_potential(-600.0, 0.0), 600.0)
        self.assertAlmostEqual(differential_potential(0.0, -600.0), 600.0)


class TestQualificationStress(unittest.TestCase):
    def test_default_factor_applies(self):
        self.assertAlmostEqual(qualification_stress(400.0), 400.0 * DEFAULT_QUALIFICATION_FACTOR)

    def test_explicit_factor_applies(self):
        self.assertAlmostEqual(qualification_stress(400.0, 1.5), 600.0)

    def test_unity_factor_is_allowed(self):
        self.assertAlmostEqual(qualification_stress(250.0, 1.0), 250.0)

    def test_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            qualification_stress(400.0, 0.9)

    def test_zero_prediction_raises(self):
        with self.assertRaises(ValueError):
            qualification_stress(0.0)

    def test_negative_prediction_raises(self):
        with self.assertRaises(ValueError):
            qualification_stress(-10.0)

    def test_non_numeric_prediction_raises(self):
        with self.assertRaises(ValueError):
            qualification_stress(None)


class TestItemNormalization(unittest.TestCase):
    def test_stress_is_precomputed(self):
        rec = normalize_item(item())
        self.assertAlmostEqual(rec["qualification-stress-v"], 500.0)
        self.assertEqual(rec["kind"], "material")

    def test_assembly_kind_is_accepted(self):
        self.assertEqual(normalize_item(item(id="mli-stack", kind="Assembly"))["kind"], "assembly")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(item(kind="harness"))

    def test_non_positive_dwell_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(item(**{"required-dwell-min": 0.0}))

    def test_negative_event_allowance_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(item(**{"event-allowance": -1}))

    def test_boolean_event_allowance_raises(self):
        with self.assertRaises(ValueError):
            normalize_item(item(**{"event-allowance": True}))

    def test_missing_id_raises(self):
        rec = item()
        del rec["id"]
        with self.assertRaises(ValueError):
            normalize_item(rec)


class TestRunNormalization(unittest.TestCase):
    def test_polarity_and_differential_are_derived(self):
        rec = normalize_run(normal_run())
        self.assertEqual(rec["polarity"], NORMAL_GRADIENT)
        self.assertAlmostEqual(rec["differential-v"], 600.0)
        self.assertTrue(rec["level-qualifying"])

    def test_development_level_is_not_qualifying(self):
        self.assertFalse(normalize_run(normal_run(level="development"))["level-qualifying"])
        self.assertTrue(CAMPAIGN_LEVELS["protoflight"])

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            normalize_run(normal_run(level="shakedown"))

    def test_negative_dwell_raises(self):
        with self.assertRaises(ValueError):
            normalize_run(normal_run(**{"dwell-min": -1.0}))

    def test_instrumentation_must_be_a_list(self):
        with self.assertRaises(ValueError):
            normalize_run(normal_run(instrumentation="current-transient-probe"))

    def test_event_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_run(normal_run(events=["flash"]))

    def test_negative_event_energy_raises(self):
        with self.assertRaises(ValueError):
            normalize_run(normal_run(events=[{"energy-mj": -0.2}]))

    def test_missing_item_reference_raises(self):
        rec = normal_run()
        del rec["item"]
        with self.assertRaises(ValueError):
            normalize_run(rec)


class TestInstrumentationAndEvents(unittest.TestCase):
    def test_recognized_channel_counts_as_detection(self):
        self.assertTrue(has_discharge_detection({"rf-emission-antenna"}))

    def test_unrelated_channel_is_not_detection(self):
        self.assertFalse(has_discharge_detection({"thermocouple"}))

    def test_empty_event_record_grades_none(self):
        self.assertEqual(grade_events([], 0), "none")

    def test_low_energy_event_inside_allowance(self):
        self.assertEqual(grade_events([{"energy-mj": 0.05}], 2), "within-allowance")

    def test_low_energy_event_over_allowance(self):
        self.assertEqual(grade_events([{"energy-mj": 0.05}, {"energy-mj": 0.05}], 1), "over-allowance")

    def test_high_energy_event_outranks_allowance(self):
        self.assertEqual(grade_events([{"energy-mj": 4.0}], 10), "sustained")


class TestRunEvaluation(unittest.TestCase):
    def test_clean_normal_run_passes(self):
        result = evaluate_run(normal_run(), item())
        self.assertTrue(result["passed"])
        self.assertEqual(result["polarity"], NORMAL_GRADIENT)
        self.assertAlmostEqual(result["stress-margin-v"], 100.0)

    def test_exact_stress_match_passes(self):
        result = evaluate_run(
            normal_run(**{"surface-potential-v": -500.0}), item()
        )
        self.assertTrue(result["passed"])

    def test_stress_limit_float_edge_is_absorbed(self):
        # 400.0 * 1.1 stores as 440.00000000000006; an applied 440.0 V is the
        # physically identical, compliant case and must not read as short.
        spec = item(**{"qualification-factor": 1.1})
        self.assertGreater(normalize_item(spec)["qualification-stress-v"], 440.0)
        result = evaluate_run(normal_run(**{"surface-potential-v": -440.0}), spec)
        self.assertTrue(result["passed"])

    def test_stress_shortfall_is_non_qualifying(self):
        result = evaluate_run(normal_run(**{"surface-potential-v": -300.0}), item())
        self.assertFalse(result["qualifying"])
        self.assertTrue(any("below qualification stress" in f for f in result["findings"]))

    def test_dwell_shortfall_is_non_qualifying(self):
        result = evaluate_run(normal_run(**{"dwell-min": 10.0}), item())
        self.assertFalse(result["passed"])
        self.assertTrue(any("dwell" in f for f in result["findings"]))

    def test_uninstrumented_quiet_run_is_not_a_pass(self):
        result = evaluate_run(normal_run(instrumentation=["thermocouple"]), item())
        self.assertFalse(result["passed"])
        self.assertTrue(any("uninstrumented" in f for f in result["findings"]))

    def test_development_level_run_is_not_a_pass(self):
        result = evaluate_run(normal_run(level="development"), item())
        self.assertFalse(result["qualifying"])

    def test_no_gradient_run_qualifies_neither_polarity(self):
        result = evaluate_run(
            normal_run(**{"surface-potential-v": -600.0, "structure-potential-v": -600.0}), item()
        )
        self.assertEqual(result["polarity"], NO_GRADIENT)
        self.assertFalse(result["qualifying"])

    def test_sustained_event_fails_a_qualifying_run(self):
        result = evaluate_run(normal_run(events=[{"energy-mj": 2.5}]), item())
        self.assertTrue(result["qualifying"])
        self.assertFalse(result["passed"])
        self.assertEqual(result["event-grade"], "sustained")

    def test_event_inside_allowance_still_passes(self):
        result = evaluate_run(
            normal_run(events=[{"energy-mj": 0.1}]), item(**{"event-allowance": 1})
        )
        self.assertTrue(result["passed"])

    def test_run_referencing_another_item_raises(self):
        with self.assertRaises(ValueError):
            evaluate_run(normal_run(item="other-blanket"), item())


class TestPolarityCoverage(unittest.TestCase):
    def test_both_polarities_close_the_item(self):
        report = assess_item(item(), [normal_run(), inverted_run()])
        self.assertTrue(report["qualified"])
        self.assertEqual(report["open-polarities"], [])
        self.assertEqual(report["coverage"][INVERTED_GRADIENT], "R-inverted")

    def test_normal_only_campaign_leaves_inverted_open(self):
        report = assess_item(item(), [normal_run()])
        self.assertFalse(report["qualified"])
        self.assertEqual(report["open-polarities"], [INVERTED_GRADIENT])

    def test_inverted_only_campaign_leaves_normal_open(self):
        report = assess_item(item(), [inverted_run()])
        self.assertEqual(report["open-polarities"], [NORMAL_GRADIENT])

    def test_failed_inverted_run_does_not_close_the_polarity(self):
        report = assess_item(item(), [normal_run(), inverted_run(events=[{"energy-mj": 3.0}])])
        self.assertEqual(report["open-polarities"], [INVERTED_GRADIENT])

    def test_runs_for_other_items_are_ignored(self):
        report = assess_item(item(), [normal_run(), inverted_run(item="mli-stack")])
        self.assertEqual(len(report["evaluations"]), 1)

    def test_runs_must_be_a_list(self):
        with self.assertRaises(ValueError):
            polarity_coverage(item(), normal_run())


class TestCampaignAggregation(unittest.TestCase):
    def test_two_items_both_covered(self):
        assembly = item(id="mli-stack", kind="assembly")
        runs = [
            normal_run(),
            inverted_run(),
            normal_run(id="A-normal", item="mli-stack"),
            inverted_run(id="A-inverted", item="mli-stack"),
        ]
        report = assess_campaign([item(), assembly], runs)
        self.assertTrue(report["complete"])
        self.assertEqual(report["qualified"], ["kapton-blanket", "mli-stack"])

    def test_assembly_coverage_does_not_close_the_material(self):
        assembly = item(id="mli-stack", kind="assembly")
        runs = [
            normal_run(id="A-normal", item="mli-stack"),
            inverted_run(id="A-inverted", item="mli-stack"),
        ]
        report = assess_campaign([item(), assembly], runs)
        self.assertFalse(report["complete"])
        self.assertEqual(
            sorted(report["residual-pairs"]),
            sorted([("kapton-blanket", NORMAL_GRADIENT), ("kapton-blanket", INVERTED_GRADIENT)]),
        )

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_campaign([item(), item()], [normal_run(), inverted_run()])

    def test_empty_item_list_raises(self):
        with self.assertRaises(ValueError):
            assess_campaign([], [normal_run()])

    def test_empty_run_list_leaves_every_pair_open(self):
        report = assess_campaign([item()], [])
        self.assertEqual(len(report["residual-pairs"]), 2)
        self.assertEqual(report["qualified"], [])


if __name__ == "__main__":
    unittest.main()
