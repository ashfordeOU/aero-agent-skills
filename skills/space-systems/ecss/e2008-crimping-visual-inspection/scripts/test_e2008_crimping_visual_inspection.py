#!/usr/bin/env python3
"""Contract test for the accepted-standard crimp inspection (offline)."""

import copy
import unittest

from e2008_crimping_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_CRIMPING_ALLOWANCES,
    INSPECTION_INCOMPLETE,
    REJECT,
    REWORK,
    SUPPORT_LOOSE,
    SUPPORT_MISSING,
    assess_crimp,
    crimp_measurements,
    gauge_band,
    inspect_crimping,
    validate_crimping_allowances,
    validate_crimping_standard,
)


def _standard(revision="B", accepted=True, **overrides):
    record = {
        "standard_id": "WS-CRIMP-0042",
        "revision": revision,
        "customer_accepted": accepted,
        "accepted_by": "customer product assurance",
        "gauge_bands": {
            "20": {
                "crimp_height_min_mm": 0.95,
                "crimp_height_max_mm": 1.05,
                "min_pull_out_n": 130.0,
                "nominal_strand_count": 19,
            },
            "24": {
                "crimp_height_min_mm": 0.70,
                "crimp_height_max_mm": 0.78,
                "min_pull_out_n": 60.0,
                "nominal_strand_count": 19,
            },
        },
    }
    record.update(overrides)
    return record


def _crimp(crimp_id="C-001", **overrides):
    record = {
        "crimp_id": crimp_id,
        "gauge": "20",
        "strand_count": 19,
        "strands_in_barrel": 19,
        "nicked_strands": 0,
        "brush_strands": 0,
        "crimp_height_mm": 1.00,
        "insulation_support": "correct",
        "insulation_in_barrel": False,
        "bell_mouth_present": True,
        "conductor_visible_at_window": True,
        "pull_out_n": None,
    }
    record.update(overrides)
    return record


def _clean_harness(how_many, pull_tested=None, declared=None, revision="B"):
    if pull_tested is None:
        pull_tested = max(1, (how_many + 9) // 10)
    crimps = []
    for n in range(1, how_many + 1):
        crimp = _crimp("C-%03d" % n)
        if n <= pull_tested:
            crimp["pull_out_n"] = 180.0
        crimps.append(crimp)
    return {
        "harness_id": "HRN-12",
        "standard_revision": revision,
        "declared_crimp_count": declared if declared is not None else how_many,
        "crimps": crimps,
    }


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_crimping_allowances(DEFAULT_CRIMPING_ALLOWANCES),
            DEFAULT_CRIMPING_ALLOWANCES,
        )

    def test_non_mapping_allowances_refused(self):
        with self.assertRaises(ValueError):
            validate_crimping_allowances(["default"])

    def test_missing_fraction_refused(self):
        broken = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        del broken["max_nicked_strand_fraction"]
        with self.assertRaises(ValueError):
            validate_crimping_allowances(broken)

    def test_fraction_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        broken["max_affected_crimp_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_crimping_allowances(broken)

    def test_negative_brush_strand_allowance_refused(self):
        broken = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        broken["max_brush_strands"] = -1
        with self.assertRaises(ValueError):
            validate_crimping_allowances(broken)

    def test_strand_loss_allowance_above_nicked_allowance_refused(self):
        broken = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        broken["max_strand_loss_fraction"] = 0.5
        with self.assertRaises(ValueError):
            validate_crimping_allowances(broken)

    def test_rework_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        broken["rework_margin_factor"] = 0.9
        with self.assertRaises(ValueError):
            validate_crimping_allowances(broken)


class WorkmanshipStandardTests(unittest.TestCase):
    def test_an_accepted_standard_returns_its_gauge_table(self):
        bands = validate_crimping_standard(_standard())
        self.assertEqual(sorted(bands), ["20", "24"])

    def test_a_standard_without_customer_acceptance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_crimping_standard(_standard(accepted=False))

    def test_a_standard_with_no_acceptance_flag_is_refused(self):
        standard = _standard()
        del standard["customer_accepted"]
        with self.assertRaises(ValueError):
            validate_crimping_standard(standard)

    def test_a_standard_without_an_acceptor_is_refused(self):
        standard = _standard()
        standard["accepted_by"] = "  "
        with self.assertRaises(ValueError):
            validate_crimping_standard(standard)

    def test_a_standard_without_a_revision_is_refused(self):
        standard = _standard()
        del standard["revision"]
        with self.assertRaises(ValueError):
            validate_crimping_standard(standard)

    def test_a_standard_tabulating_no_gauge_is_refused(self):
        with self.assertRaises(ValueError):
            validate_crimping_standard(_standard(gauge_bands={}))

    def test_a_zero_width_height_band_is_refused(self):
        standard = _standard()
        standard["gauge_bands"]["20"]["crimp_height_max_mm"] = 0.95
        with self.assertRaises(ValueError):
            validate_crimping_standard(standard)

    def test_a_gauge_without_a_nominal_strand_count_is_refused(self):
        standard = _standard()
        del standard["gauge_bands"]["24"]["nominal_strand_count"]
        with self.assertRaises(ValueError):
            validate_crimping_standard(standard)

    def test_an_untabulated_gauge_is_refused_not_interpolated(self):
        with self.assertRaises(ValueError):
            gauge_band(_standard(), "22")

    def test_a_tabulated_gauge_returns_its_band(self):
        entry = gauge_band(_standard(), "24")
        self.assertAlmostEqual(entry["crimp_height_min_mm"], 0.70, places=9)


class MeasurementTests(unittest.TestCase):
    def test_a_clean_crimp_sits_inside_its_band(self):
        measured = crimp_measurements(_crimp(), _standard())
        self.assertFalse(measured["over_compressed"])
        self.assertFalse(measured["under_compressed"])
        self.assertAlmostEqual(measured["crimp_height_band_position"], 0.5, places=9)

    def test_a_height_on_the_band_floor_is_not_over_compressed(self):
        measured = crimp_measurements(_crimp(crimp_height_mm=0.95), _standard())
        self.assertFalse(measured["over_compressed"])
        self.assertAlmostEqual(measured["crimp_height_band_position"], 0.0, places=9)

    def test_a_height_on_the_band_top_is_not_under_compressed(self):
        measured = crimp_measurements(_crimp(crimp_height_mm=1.05), _standard())
        self.assertFalse(measured["under_compressed"])
        self.assertAlmostEqual(measured["crimp_height_band_position"], 1.0, places=9)

    def test_strand_loss_is_the_strands_that_never_reached_the_barrel(self):
        measured = crimp_measurements(
            _crimp(strands_in_barrel=17, brush_strands=2), _standard()
        )
        self.assertEqual(measured["strands_lost"], 2)
        self.assertAlmostEqual(
            measured["strand_loss_fraction"], 2.0 / 19.0, places=9
        )

    def test_a_strand_count_the_gauge_does_not_carry_is_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(_crimp(strand_count=7, strands_in_barrel=7), _standard())

    def test_more_strands_in_the_barrel_than_the_conductor_has_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(_crimp(strands_in_barrel=21), _standard())

    def test_more_nicked_strands_than_reached_the_barrel_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(
                _crimp(strands_in_barrel=4, nicked_strands=5), _standard()
            )

    def test_strands_accounted_for_twice_are_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(
                _crimp(strands_in_barrel=19, brush_strands=3), _standard()
            )

    def test_non_positive_crimp_height_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(_crimp(crimp_height_mm=0.0), _standard())

    def test_a_crimp_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            crimp_measurements(_crimp(crimp_id=""), _standard())

    def test_an_untested_crimp_reports_itself_untested(self):
        measured = crimp_measurements(_crimp(), _standard())
        self.assertFalse(measured["pull_tested"])
        self.assertIsNone(measured["pull_out_n"])


class CrimpDispositionTests(unittest.TestCase):
    def test_a_clean_crimp_accepts(self):
        result = assess_crimp(_crimp(), _standard())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_a_slightly_over_compressed_crimp_reworks(self):
        result = assess_crimp(_crimp(crimp_height_mm=0.90), _standard())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_badly_over_compressed_crimp_rejects(self):
        result = assess_crimp(_crimp(crimp_height_mm=0.70), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_slightly_under_compressed_crimp_reworks(self):
        result = assess_crimp(_crimp(crimp_height_mm=1.10), _standard())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_badly_under_compressed_crimp_rejects(self):
        result = assess_crimp(_crimp(crimp_height_mm=1.40), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_missing_strand_rejects_under_the_default_allowance(self):
        result = assess_crimp(
            _crimp(strands_in_barrel=18, brush_strands=1), _standard()
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_an_empty_barrel_names_the_missing_conductor(self):
        result = assess_crimp(_crimp(strands_in_barrel=0), _standard())
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("no conductor" in f for f in result["findings"]))

    def test_one_brushed_strand_reworks(self):
        allowances = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        allowances["max_strand_loss_fraction"] = 1.0 / 19.0
        allowances["max_nicked_strand_fraction"] = 1.0 / 19.0
        result = assess_crimp(
            _crimp(strands_in_barrel=18, brush_strands=1), _standard(), allowances
        )
        self.assertEqual(result["verdict"], REWORK)

    def test_nicked_strands_past_the_allowance_reject(self):
        result = assess_crimp(_crimp(nicked_strands=4), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_single_nicked_strand_stays_inside_the_allowance(self):
        allowances = copy.deepcopy(DEFAULT_CRIMPING_ALLOWANCES)
        allowances["max_nicked_strand_fraction"] = 1.0 / 19.0
        result = assess_crimp(_crimp(nicked_strands=1), _standard(), allowances)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_missing_insulation_support_rejects(self):
        result = assess_crimp(_crimp(insulation_support=SUPPORT_MISSING), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_loose_insulation_support_reworks(self):
        result = assess_crimp(_crimp(insulation_support=SUPPORT_LOOSE), _standard())
        self.assertEqual(result["verdict"], REWORK)

    def test_an_unknown_insulation_support_state_is_refused(self):
        with self.assertRaises(ValueError):
            assess_crimp(_crimp(insulation_support="partial"), _standard())

    def test_insulation_trapped_in_the_barrel_rejects(self):
        result = assess_crimp(_crimp(insulation_in_barrel=True), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_missing_bell_mouth_reworks(self):
        result = assess_crimp(_crimp(bell_mouth_present=False), _standard())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_conductor_not_visible_at_the_window_reworks(self):
        result = assess_crimp(_crimp(conductor_visible_at_window=False), _standard())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_pull_out_below_the_standard_rejects(self):
        result = assess_crimp(_crimp(pull_out_n=90.0), _standard())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_pull_out_exactly_on_the_standard_accepts(self):
        result = assess_crimp(_crimp(pull_out_n=130.0), _standard())
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_non_boolean_feature_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_crimp(_crimp(bell_mouth_present="yes"), _standard())

    def test_a_crimp_graded_against_an_unaccepted_standard_is_refused(self):
        with self.assertRaises(ValueError):
            assess_crimp(_crimp(), _standard(accepted=False))


class HarnessRollupTests(unittest.TestCase):
    def test_a_clean_harness_accepts(self):
        result = inspect_crimping(_clean_harness(40), _standard())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["affected_count"], 0)
        self.assertEqual(result["pull_tested_count"], 4)
        self.assertTrue(result["pull_test_sample_met"])
        self.assertAlmostEqual(result["remaining_affected_allowance"], 2.0, places=9)

    def test_two_affected_terminations_stay_inside_the_harness_allowance(self):
        harness = _clean_harness(40)
        harness["crimps"][10]["bell_mouth_present"] = False
        harness["crimps"][11]["conductor_visible_at_window"] = False
        result = inspect_crimping(harness, _standard())
        self.assertEqual(result["affected_count"], 2)
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 0.0, places=9)

    def test_the_harness_allowance_bites_once_it_is_exceeded(self):
        harness = _clean_harness(40)
        for index in range(5):
            harness["crimps"][index + 10]["bell_mouth_present"] = False
        result = inspect_crimping(harness, _standard())
        self.assertEqual(result["affected_count"], 5)
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("rework margin" in f for f in result["findings"]))

    def test_a_short_pull_test_sample_is_a_finding(self):
        harness = _clean_harness(40, pull_tested=1)
        result = inspect_crimping(harness, _standard())
        self.assertFalse(result["pull_test_sample_met"])
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["pull_test_sample_required"], 4.0, places=9)

    def test_a_short_record_set_leaves_the_harness_open(self):
        harness = _clean_harness(38, declared=40)
        result = inspect_crimping(harness, _standard())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            inspect_crimping(_clean_harness(6, declared=5), _standard())

    def test_a_mismatched_standard_revision_is_refused(self):
        harness = _clean_harness(4)
        harness["standard_revision"] = "A"
        with self.assertRaises(ValueError):
            inspect_crimping(harness, _standard())

    def test_duplicate_crimp_ids_refused(self):
        harness = _clean_harness(4)
        harness["crimps"][3]["crimp_id"] = "C-001"
        with self.assertRaises(ValueError):
            inspect_crimping(harness, _standard())

    def test_a_rejected_termination_names_itself(self):
        harness = _clean_harness(40)
        harness["crimps"][6]["insulation_in_barrel"] = True
        result = inspect_crimping(harness, _standard())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["C-007"])
        self.assertEqual(result["disposition_counts"][REJECT], 1)
        self.assertEqual(result["disposition_counts"][ACCEPT], 39)

    def test_the_report_carries_the_standard_it_answered_to(self):
        result = inspect_crimping(_clean_harness(10), _standard())
        self.assertEqual(result["standard_id"], "WS-CRIMP-0042")
        self.assertEqual(result["standard_revision"], "B")
        self.assertEqual(result["accepted_by"], "customer product assurance")

    def test_a_harness_graded_against_an_unaccepted_standard_is_refused(self):
        with self.assertRaises(ValueError):
            inspect_crimping(_clean_harness(4), _standard(accepted=False))

    def test_non_mapping_harness_refused(self):
        with self.assertRaises(ValueError):
            inspect_crimping("HRN-12", _standard())

    def test_crimps_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            inspect_crimping(
                {
                    "harness_id": "HRN-12",
                    "standard_revision": "B",
                    "declared_crimp_count": 3,
                    "crimps": "three",
                },
                _standard(),
            )

    def test_non_integer_declared_count_refused(self):
        harness = _clean_harness(3)
        harness["declared_crimp_count"] = "three"
        with self.assertRaises(ValueError):
            inspect_crimping(harness, _standard())

    def test_a_mixed_gauge_harness_uses_each_gauge_band(self):
        harness = _clean_harness(20)
        for index in range(10, 20):
            harness["crimps"][index]["gauge"] = "24"
            harness["crimps"][index]["crimp_height_mm"] = 0.74
        result = inspect_crimping(harness, _standard())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["inspected_count"], 20)


if __name__ == "__main__":
    unittest.main()
