"""Contract tests for the clause 4.2 flight-model die lot procurement logic."""

import unittest

from q6012_flight_model_die_lot_procurement_logic import (
    CEIL_TOLERANCE,
    STEP_KEYS,
    assess_flight_lot_procurement,
    ceil_units,
    chain_yield,
    delivered_dies_required,
    die_starts_required,
    good_dies_required,
    lot_identity_findings,
    procurement_steps,
    qualification_status,
    validate_count,
    validate_date,
    validate_yield,
    validate_yield_stages,
    wafers_to_start,
)

STAGES = [("process-control", 0.5), ("visual-and-rf", 0.5)]


def base_spec(**overrides):
    spec = {
        "flight_die_count": 100,
        "assembly_yield": 0.5,
        "destructive_sample_count": 5,
        "validation_sample_count": 5,
        "yield_stages": STAGES,
        "dies_per_wafer": 100,
        "max_wafers_per_lot": 12,
        "qualification_expiry": "2027-06-30",
        "wafer_start_date": "2026-10-01",
        "delivery_date": "2027-02-01",
        "wafer_lot_ids": ["LOT-A7"],
        "mask_set_ids": ["MASK-311"],
        "radiation_required": True,
    }
    spec.update(overrides)
    return spec


class CeilUnitTests(unittest.TestCase):
    def test_exact_whole_number_is_not_rounded_up(self):
        self.assertEqual(ceil_units(125.0), 125)

    def test_ulp_noise_above_a_whole_number_does_not_buy_a_spare_die(self):
        self.assertEqual(ceil_units(125.0 + 1e-11), 125)

    def test_a_real_fraction_still_rounds_up(self):
        self.assertEqual(ceil_units(125.2), 126)

    def test_half_rounds_up(self):
        self.assertEqual(ceil_units(125.5), 126)

    def test_zero_is_allowed(self):
        self.assertEqual(ceil_units(0.0), 0)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            ceil_units(-1.0)

    def test_non_finite_value_rejected(self):
        with self.assertRaises(ValueError):
            ceil_units(float("inf"))

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            ceil_units(True)

    def test_tolerance_is_relative_and_small(self):
        self.assertLess(CEIL_TOLERANCE, 1e-6)


class ValidationTests(unittest.TestCase):
    def test_yield_of_one_is_accepted(self):
        self.assertAlmostEqual(validate_yield(1.0), 1.0, places=9)

    def test_zero_yield_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield(0.0)

    def test_yield_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield(1.05)

    def test_non_numeric_yield_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield("0.9")

    def test_count_minimum_is_enforced(self):
        with self.assertRaises(ValueError):
            validate_count(0, "flight_die_count", minimum=1)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(True, "count")

    def test_iso_date_parsed(self):
        self.assertEqual(validate_date("2026-10-01").year, 2026)

    def test_free_text_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_date("1 October 2026")

    def test_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_date(20261001)

    def test_stage_names_are_normalised_and_unique(self):
        stages = validate_yield_stages([("Process-Control", 0.9), ("Visual", 0.8)])
        self.assertEqual([s[0] for s in stages], ["process-control", "visual"])

    def test_duplicate_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_stages([("visual", 0.9), ("Visual", 0.8)])

    def test_empty_stage_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_stages([])

    def test_malformed_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_stages([("visual",)])

    def test_unnamed_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_yield_stages([("  ", 0.9)])

    def test_chain_yield_is_the_product(self):
        self.assertAlmostEqual(chain_yield(STAGES), 0.25, places=9)


class QualificationTests(unittest.TestCase):
    def test_valid_qualification_reports_positive_margin(self):
        record = qualification_status("2027-06-30", "2026-10-01")
        self.assertTrue(record["valid_at_wafer_start"])
        self.assertGreater(record["margin_days"], 0)

    def test_expired_qualification_is_graded_at_wafer_start(self):
        record = qualification_status("2026-09-01", "2026-10-01")
        self.assertFalse(record["valid_at_wafer_start"])
        self.assertEqual(record["margin_days"], -30)

    def test_expiry_on_the_start_day_is_still_valid(self):
        record = qualification_status("2026-10-01", "2026-10-01")
        self.assertTrue(record["valid_at_wafer_start"])
        self.assertEqual(record["margin_days"], 0)

    def test_lapse_between_start_and_delivery_is_reported(self):
        record = qualification_status("2026-11-01", "2026-10-01", "2027-02-01")
        self.assertTrue(record["valid_at_wafer_start"])
        self.assertTrue(record["lapses_before_delivery"])

    def test_delivery_before_wafer_start_rejected(self):
        with self.assertRaises(ValueError):
            qualification_status("2027-06-30", "2026-10-01", "2026-09-01")

    def test_no_delivery_date_leaves_the_lapse_flag_clear(self):
        record = qualification_status("2027-06-30", "2026-10-01")
        self.assertFalse(record["lapses_before_delivery"])
        self.assertIsNone(record["delivery_date"])


class CascadeTests(unittest.TestCase):
    def test_assembly_attrition_raises_the_delivered_need(self):
        self.assertEqual(delivered_dies_required(100, 0.5), 200)

    def test_perfect_assembly_yield_delivers_the_flight_count(self):
        self.assertEqual(delivered_dies_required(100, 1.0), 100)

    def test_zero_flight_count_rejected(self):
        with self.assertRaises(ValueError):
            delivered_dies_required(0, 0.5)

    def test_samples_are_consumed_on_top_of_the_delivered_need(self):
        self.assertEqual(good_dies_required(200, 5, 5), 210)

    def test_negative_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            good_dies_required(200, -1, 5)

    def test_reverse_cascade_reaches_the_die_starts(self):
        starts, cascade = die_starts_required(210, STAGES)
        self.assertEqual(starts, 840)
        self.assertEqual(len(cascade), 2)

    def test_cascade_is_reported_in_process_order(self):
        _starts, cascade = die_starts_required(210, STAGES)
        self.assertEqual(cascade[0]["stage"], "process-control")
        self.assertEqual(cascade[-1]["stage"], "visual-and-rf")

    def test_each_cascade_stage_balances(self):
        _starts, cascade = die_starts_required(210, STAGES)
        for record in cascade:
            self.assertEqual(record["dies_in"] - record["dies_out"], record["dies_lost"])

    def test_cascade_stages_chain_end_to_end(self):
        _starts, cascade = die_starts_required(210, STAGES)
        self.assertEqual(cascade[0]["dies_out"], cascade[1]["dies_in"])

    def test_unit_yield_stage_loses_nothing(self):
        starts, _cascade = die_starts_required(210, [("visual", 1.0)])
        self.assertEqual(starts, 210)

    def test_wafers_round_up_to_whole_wafers(self):
        self.assertEqual(wafers_to_start(840, 100), 9)

    def test_exact_wafer_fit_does_not_buy_a_spare_wafer(self):
        self.assertEqual(wafers_to_start(800, 100), 8)

    def test_zero_dies_per_wafer_rejected(self):
        with self.assertRaises(ValueError):
            wafers_to_start(840, 0)


class LotIdentityTests(unittest.TestCase):
    def test_single_lot_and_mask_set_is_clean(self):
        self.assertEqual(lot_identity_findings(["LOT-A7"], ["MASK-311"]), [])

    def test_repeated_identifier_is_one_identity(self):
        self.assertEqual(lot_identity_findings(["LOT-A7", "lot-a7"], ["MASK-311"]), [])

    def test_two_wafer_lots_are_flagged(self):
        findings = lot_identity_findings(["LOT-A7", "LOT-B2"], ["MASK-311"])
        self.assertEqual(len(findings), 1)
        self.assertIn("wafer lot", findings[0])

    def test_two_mask_sets_are_flagged(self):
        findings = lot_identity_findings(["LOT-A7"], ["MASK-311", "MASK-312"])
        self.assertIn("mask set", findings[0])

    def test_empty_identifier_list_rejected(self):
        with self.assertRaises(ValueError):
            lot_identity_findings([], ["MASK-311"])

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            lot_identity_findings(["  "], ["MASK-311"])


class StepTests(unittest.TestCase):
    def test_steps_are_positioned_from_one(self):
        steps = procurement_steps({"destructive_sample_count": 5,
                                   "validation_sample_count": 5,
                                   "radiation_required": True})
        self.assertEqual([s["position"] for s in steps], list(range(1, len(steps) + 1)))

    def test_no_radiation_requirement_drops_the_radiation_step(self):
        steps = procurement_steps({"destructive_sample_count": 5,
                                   "validation_sample_count": 5,
                                   "radiation_required": False})
        self.assertNotIn("radiation-lot-acceptance", [s["key"] for s in steps])

    def test_no_destructive_sample_drops_that_step(self):
        steps = procurement_steps({"destructive_sample_count": 0,
                                   "validation_sample_count": 5})
        self.assertNotIn("destructive-sample-drawn", [s["key"] for s in steps])

    def test_wafer_lot_start_always_present(self):
        steps = procurement_steps({})
        self.assertIn("wafer-lot-started", [s["key"] for s in steps])

    def test_screening_precedes_the_destructive_draw(self):
        steps = procurement_steps({"destructive_sample_count": 5,
                                   "validation_sample_count": 5})
        keys = [s["key"] for s in steps]
        self.assertLess(keys.index("visual-and-rf-screening"),
                        keys.index("destructive-sample-drawn"))

    def test_every_step_key_is_in_the_registry(self):
        for step in procurement_steps({"destructive_sample_count": 1,
                                       "validation_sample_count": 1,
                                       "radiation_required": True}):
            self.assertIn(step["key"], STEP_KEYS)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            procurement_steps(["radiation_required"])


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_releasable(self):
        result = assess_flight_lot_procurement(base_spec())
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])

    def test_headline_numbers_are_the_cascade_result(self):
        result = assess_flight_lot_procurement(base_spec())
        self.assertEqual(result["delivered_dies_required"], 200)
        self.assertEqual(result["good_dies_required"], 210)
        self.assertEqual(result["die_starts_required"], 840)
        self.assertEqual(result["wafers_to_start"], 9)

    def test_spare_dies_are_the_wafer_rounding(self):
        result = assess_flight_lot_procurement(base_spec())
        self.assertEqual(result["dies_available"], 900)
        self.assertEqual(result["spare_dies"], 60)

    def test_chain_yield_is_reported(self):
        result = assess_flight_lot_procurement(base_spec())
        self.assertAlmostEqual(result["chain_yield"], 0.25, places=9)

    def test_expired_qualification_blocks_release(self):
        result = assess_flight_lot_procurement(base_spec(qualification_expiry="2026-09-01"))
        self.assertFalse(result["releasable"])
        self.assertTrue(any("expired" in f for f in result["findings"]))

    def test_qualification_lapse_before_delivery_is_flagged(self):
        result = assess_flight_lot_procurement(base_spec(qualification_expiry="2026-11-01"))
        self.assertTrue(any("lapses" in f for f in result["findings"]))

    def test_split_wafer_lot_blocks_release(self):
        result = assess_flight_lot_procurement(base_spec(wafer_lot_ids=["LOT-A7", "LOT-B2"]))
        self.assertFalse(result["releasable"])

    def test_missing_destructive_sample_is_flagged(self):
        result = assess_flight_lot_procurement(base_spec(destructive_sample_count=0))
        self.assertTrue(any("destructive analysis sample" in f for f in result["findings"]))

    def test_missing_validation_sample_is_flagged(self):
        result = assess_flight_lot_procurement(base_spec(validation_sample_count=0))
        self.assertTrue(any("lot validation sample" in f for f in result["findings"]))

    def test_need_beyond_one_lot_is_flagged_not_split_silently(self):
        result = assess_flight_lot_procurement(base_spec(max_wafers_per_lot=4))
        self.assertFalse(result["releasable"])
        self.assertTrue(any("one flight batch cannot cover it" in f for f in result["findings"]))

    def test_lower_yield_raises_the_wafer_count(self):
        low = assess_flight_lot_procurement(
            base_spec(yield_stages=[("process-control", 0.25), ("visual-and-rf", 0.5)],
                      max_wafers_per_lot=40)
        )
        high = assess_flight_lot_procurement(base_spec())
        self.assertGreater(low["wafers_to_start"], high["wafers_to_start"])

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["dies_per_wafer"]
        with self.assertRaises(ValueError):
            assess_flight_lot_procurement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_flight_lot_procurement(["flight_die_count"])

    def test_bad_yield_in_the_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_flight_lot_procurement(base_spec(assembly_yield=0.0))

    def test_steps_carry_through_to_the_result(self):
        result = assess_flight_lot_procurement(base_spec(radiation_required=False))
        self.assertNotIn("radiation-lot-acceptance", [s["key"] for s in result["steps"]])


if __name__ == "__main__":
    unittest.main()
