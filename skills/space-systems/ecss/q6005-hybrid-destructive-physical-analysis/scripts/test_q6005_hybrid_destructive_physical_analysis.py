#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 14 hybrid DPA leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_hybrid_destructive_physical_analysis.py
"""

import math
import unittest

from q6005_hybrid_destructive_physical_analysis_logic import (
    BOND_PULL_ACCEPTANCE_FRACTION,
    DIE_SHEAR_FLOOR_N,
    DIE_SHEAR_STRENGTH_MPA,
    DPA_SAMPLE_PLAN,
    DPA_SAMPLE_PLAN_TOP,
    DPA_STEPS,
    DPA_TOLERANCE,
    MANDATORY_STEPS,
    MAX_FAILED_SAMPLES,
    MEASURED_ATTRIBUTES,
    STEP_ORDER,
    VERDICTS,
    WIRE_ALLOY_STRENGTH_MPA,
    assess_destructive_physical_analysis,
    assess_sample,
    dpa_sample_size,
    lot_disposition,
    minimum_bond_pull_force_n,
    minimum_die_shear_force_n,
    sample_minimums,
    step_is_destructive,
    validate_sequence,
)

CANONICAL = [name for name, _d, _m in DPA_STEPS]


def build(**overrides):
    """A gold-wire hybrid with a moderate die."""
    record = {
        "wire_diameter_um": 25.0,
        "wire_alloy": "aluminium-1-percent-silicon",
        "die_area_mm2": 2.0,
    }
    record.update(overrides)
    return record


def sample(serial="SN0001", **overrides):
    """An opened unit whose measurements clear the acceptance forces."""
    record = {
        "serial": serial,
        "bond_pull_force_n": 0.06,
        "die_shear_force_n": 40.0,
        "visual_anomalies": [],
    }
    record.update(overrides)
    return record


def run(**overrides):
    """Grade one destructive physical analysis."""
    case = {
        "lot_id": "HYB-1234-LOT-07",
        "lot_size": 40,
        "build": build(),
        "sequence": list(CANONICAL),
        "samples": [sample("SN0001"), sample("SN0002")],
    }
    case.update(overrides)
    return assess_destructive_physical_analysis(**case)


class SamplePlanTests(unittest.TestCase):
    def test_a_small_lot_gives_up_one_unit(self):
        self.assertEqual(dpa_sample_size(10), 1)

    def test_a_larger_lot_gives_up_more_units(self):
        self.assertGreater(dpa_sample_size(250), dpa_sample_size(40))

    def test_a_lot_on_a_band_edge_stays_in_that_band(self):
        edge, expected = DPA_SAMPLE_PLAN[1]
        self.assertEqual(dpa_sample_size(edge), expected)

    def test_a_very_large_lot_reaches_the_top_of_the_plan(self):
        self.assertEqual(dpa_sample_size(5000), DPA_SAMPLE_PLAN_TOP)

    def test_the_sample_never_exceeds_the_lot(self):
        self.assertEqual(dpa_sample_size(1), 1)

    def test_a_zero_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(0)

    def test_a_fractional_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            dpa_sample_size(12.5)

    def test_the_plan_bands_rise_and_their_samples_rise_with_them(self):
        for earlier, later in zip(DPA_SAMPLE_PLAN, DPA_SAMPLE_PLAN[1:]):
            self.assertLess(earlier[0], later[0])
            self.assertLess(earlier[1], later[1])


class SequenceTests(unittest.TestCase):
    def test_the_canonical_order_is_valid(self):
        result = validate_sequence(CANONICAL)
        self.assertTrue(result["sequence_valid"])
        self.assertEqual(result["findings"], [])

    def test_every_non_destructive_step_precedes_every_destructive_one(self):
        last_open = max(
            STEP_ORDER[name] for name, destructive, _m in DPA_STEPS if not destructive
        )
        first_destructive = min(
            STEP_ORDER[name] for name, destructive, _m in DPA_STEPS if destructive
        )
        self.assertLess(last_open, first_destructive)

    def test_opening_before_the_hermeticity_result_is_reported(self):
        sequence = [
            "external-visual-inspection",
            "internal-visual-inspection",
            "fine-leak-hermeticity",
            "gross-leak-hermeticity",
            "radiographic-inspection",
            "particle-impact-noise-detection",
            "bond-pull-test",
            "die-shear-test",
        ]
        result = validate_sequence(sequence)
        self.assertIn("sealed-package-evidence-taken-after-the-unit-was-opened", result["findings"])
        self.assertIn("fine-leak-hermeticity", result["steps_after_opening"])

    def test_a_reordered_destructive_step_is_reported(self):
        sequence = list(CANONICAL)
        sequence.remove("bond-pull-test")
        sequence.append("bond-pull-test")
        result = validate_sequence(sequence)
        self.assertIn("analysis-step-performed-out-of-the-canonical-order", result["findings"])

    def test_a_missing_mandatory_step_is_named(self):
        sequence = [step for step in CANONICAL if step != "die-shear-test"]
        result = validate_sequence(sequence)
        self.assertEqual(result["missing_mandatory_steps"], ["die-shear-test"])

    def test_dropping_an_optional_step_is_not_a_finding(self):
        sequence = [step for step in CANONICAL if step != "residual-gas-analysis"]
        self.assertTrue(validate_sequence(sequence)["sequence_valid"])

    def test_an_unknown_analysis_step_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(CANONICAL + ["shake-it-and-listen"])

    def test_a_repeated_analysis_step_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(CANONICAL + ["die-shear-test"])

    def test_an_empty_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])

    def test_the_opening_index_names_the_first_destructive_step(self):
        result = validate_sequence(CANONICAL)
        self.assertEqual(CANONICAL[result["opened_at_index"]], "residual-gas-analysis")

    def test_every_mandatory_step_is_a_published_step(self):
        for step in MANDATORY_STEPS:
            self.assertIn(step, STEP_ORDER)

    def test_an_unknown_step_has_no_destructiveness(self):
        with self.assertRaises(ValueError):
            step_is_destructive("polish-and-admire")


class AcceptanceForceTests(unittest.TestCase):
    def test_the_bond_pull_minimum_follows_the_published_wire_relation(self):
        radius_m = 25.0 * 0.5e-6
        expected = (
            BOND_PULL_ACCEPTANCE_FRACTION
            * WIRE_ALLOY_STRENGTH_MPA["aluminium-1-percent-silicon"]
            * 1.0e6
            * math.pi
            * radius_m
            * radius_m
        )
        self.assertAlmostEqual(
            minimum_bond_pull_force_n(25.0, "aluminium-1-percent-silicon"), expected, places=12
        )

    def test_thicker_wire_has_to_hold_more(self):
        self.assertGreater(
            minimum_bond_pull_force_n(33.0, "gold-99-99"),
            minimum_bond_pull_force_n(25.0, "gold-99-99"),
        )

    def test_a_stronger_alloy_has_to_hold_more_at_the_same_diameter(self):
        self.assertGreater(
            minimum_bond_pull_force_n(25.0, "aluminium-1-percent-magnesium"),
            minimum_bond_pull_force_n(25.0, "aluminium-1-percent-silicon"),
        )

    def test_an_unknown_wire_alloy_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_bond_pull_force_n(25.0, "copper-clad-mystery")

    def test_a_zero_wire_diameter_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_bond_pull_force_n(0.0, "gold-99-99")

    def test_the_die_shear_minimum_follows_the_area_rule_above_the_floor(self):
        self.assertAlmostEqual(
            minimum_die_shear_force_n(4.0), DIE_SHEAR_STRENGTH_MPA * 4.0, places=9
        )

    def test_a_very_small_die_is_held_to_the_floor(self):
        self.assertAlmostEqual(minimum_die_shear_force_n(0.05), DIE_SHEAR_FLOOR_N, places=9)

    def test_an_area_landing_exactly_on_the_floor_returns_the_floor(self):
        area = DIE_SHEAR_FLOOR_N / DIE_SHEAR_STRENGTH_MPA
        self.assertAlmostEqual(minimum_die_shear_force_n(area), DIE_SHEAR_FLOOR_N, places=9)

    def test_a_negative_die_area_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_die_shear_force_n(-1.0)

    def test_the_build_yields_a_minimum_for_every_measured_attribute(self):
        minimums = sample_minimums(build())
        for attribute in MEASURED_ATTRIBUTES:
            self.assertIn(attribute, minimums)

    def test_a_build_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            sample_minimums("25um aluminium")


class SampleTests(unittest.TestCase):
    def test_a_sound_unit_passes(self):
        record = assess_sample(sample(), sample_minimums(build()))
        self.assertTrue(record["sample_passed"])
        self.assertEqual(record["failures"], [])

    def test_a_weak_bond_is_reported(self):
        record = assess_sample(sample(bond_pull_force_n=0.005), sample_minimums(build()))
        self.assertIn("bond-pull-force-n-below-the-acceptance-force", record["failures"])

    def test_a_weak_die_attachment_is_reported(self):
        record = assess_sample(sample(die_shear_force_n=1.0), sample_minimums(build()))
        self.assertIn("die-shear-force-n-below-the-acceptance-force", record["failures"])

    def test_a_measurement_exactly_on_the_acceptance_force_passes(self):
        minimums = sample_minimums(build())
        record = assess_sample(
            sample(
                bond_pull_force_n=minimums["bond_pull_force_n"],
                die_shear_force_n=minimums["die_shear_force_n"],
            ),
            minimums,
        )
        self.assertTrue(record["sample_passed"])

    def test_a_visual_anomaly_is_kept_as_an_observation(self):
        record = assess_sample(
            sample(visual_anomalies=["substrate-metallization-void"]), sample_minimums(build())
        )
        self.assertEqual(record["observations"], ["substrate-metallization-void"])
        self.assertTrue(record["sample_passed"])

    def test_a_unit_with_no_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_sample(sample(serial="  "), sample_minimums(build()))

    def test_a_missing_measurement_is_rejected(self):
        broken = sample()
        del broken["die_shear_force_n"]
        with self.assertRaises(ValueError):
            assess_sample(broken, sample_minimums(build()))

    def test_a_blank_visual_anomaly_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_sample(sample(visual_anomalies=[" "]), sample_minimums(build()))


class DispositionTests(unittest.TestCase):
    def test_a_full_sound_sample_leaves_the_lot_acceptable(self):
        minimums = sample_minimums(build())
        records = [assess_sample(sample("SN0001"), minimums), assess_sample(sample("SN0002"), minimums)]
        result = lot_disposition(records, 2)
        self.assertTrue(result["lot_acceptable"])

    def test_a_short_sample_is_reported(self):
        minimums = sample_minimums(build())
        result = lot_disposition([assess_sample(sample(), minimums)], 3)
        self.assertFalse(result["sample_complete"])
        self.assertIn("fewer-units-analysed-than-the-sample-plan-demands", result["findings"])

    def test_one_failed_unit_refuses_the_lot(self):
        minimums = sample_minimums(build())
        records = [
            assess_sample(sample("SN0001"), minimums),
            assess_sample(sample("SN0002", die_shear_force_n=1.0), minimums),
        ]
        result = lot_disposition(records, 2)
        self.assertEqual(result["failed_serials"], ["SN0002"])
        self.assertFalse(result["lot_acceptable"])

    def test_the_published_allowance_admits_no_failed_unit(self):
        self.assertEqual(MAX_FAILED_SAMPLES, 0)

    def test_a_zero_required_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_disposition([], 0)


class WholeAnalysisTests(unittest.TestCase):
    def test_a_sound_analysis_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "dpa-passed")
        self.assertTrue(result["lot_released"])
        self.assertEqual(result["findings"], [])

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_the_sample_plan_drives_the_number_of_units_demanded(self):
        self.assertEqual(run(lot_size=200, samples=[sample("SN%04d" % n) for n in range(4)])[
            "sample_size_required"
        ], 4)

    def test_a_missing_mandatory_step_leaves_the_analysis_incomplete(self):
        sequence = [step for step in CANONICAL if step != "bond-pull-test"]
        self.assertEqual(run(sequence=sequence)["verdict"], "dpa-incomplete")

    def test_too_few_analysed_units_leave_the_analysis_incomplete(self):
        self.assertEqual(run(samples=[sample("SN0001")])["verdict"], "dpa-incomplete")

    def test_a_weak_bond_fails_the_lot(self):
        result = run(samples=[sample("SN0001"), sample("SN0002", bond_pull_force_n=0.004)])
        self.assertEqual(result["verdict"], "dpa-failed")
        self.assertFalse(result["lot_released"])

    def test_an_out_of_order_teardown_fails_the_analysis(self):
        sequence = list(CANONICAL)
        sequence.remove("fine-leak-hermeticity")
        sequence.append("fine-leak-hermeticity")
        self.assertEqual(run(sequence=sequence)["verdict"], "dpa-failed")

    def test_a_visual_anomaly_alone_leaves_the_lot_released_with_observations(self):
        result = run(
            samples=[
                sample("SN0001"),
                sample("SN0002", visual_anomalies=["bond-tail-longer-than-drawn"]),
            ]
        )
        self.assertEqual(result["verdict"], "dpa-passed-with-observations")
        self.assertTrue(result["lot_released"])

    def test_a_unit_analysed_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            run(samples=[sample("SN0001"), sample("SN0001")])

    def test_a_blank_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(lot_id="   ")

    def test_a_sample_set_that_is_not_a_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            run(samples=sample())

    def test_the_acceptance_forces_are_reported_with_the_result(self):
        forces = run()["acceptance_forces"]
        self.assertAlmostEqual(
            forces["die_shear_force_n"], DIE_SHEAR_STRENGTH_MPA * 2.0, places=9
        )


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(DPA_TOLERANCE, 1e-6)

    def test_the_acceptance_fraction_sits_below_the_breaking_force(self):
        self.assertLess(BOND_PULL_ACCEPTANCE_FRACTION, 1.0)

    def test_every_step_has_a_distinct_position(self):
        self.assertEqual(len(STEP_ORDER), len(DPA_STEPS))

    def test_the_die_shear_floor_is_positive(self):
        self.assertGreater(DIE_SHEAR_FLOOR_N, 0.0)


if __name__ == "__main__":
    unittest.main()
