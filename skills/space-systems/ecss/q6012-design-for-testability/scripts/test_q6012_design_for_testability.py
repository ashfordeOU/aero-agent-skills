#!/usr/bin/env python3
"""Contract test for the MMIC design-for-testability assessment (offline)."""

import copy
import unittest

from q6012_design_for_testability_logic import (
    ADEQUATE,
    ASSEMBLY_LEVEL,
    CONDITIONAL,
    INADEQUATE,
    ON_WAFER,
    UNOBSERVABLE,
    assess_testability,
    coverage_report,
    minimum_landing_side_um,
    probe_landing_check,
    resolve_observability,
    pad_area_overhead,
    touchdown_budget,
    validate_access_point,
    validate_parameter,
)

PROBE_CARD = {
    "pitch_um": 100.0,
    "pitch_tolerance_um": 2.0,
    "tip_diameter_um": 12.0,
    "alignment_tolerance_um": 5.0,
}

RF_PADS = {
    "id": "rf-in-gsg",
    "kind": "rf-probe-pad",
    "pitch_um": 100.0,
    "width_um": 60.0,
    "height_um": 60.0,
    "count": 6,
}

DC_PADS = {
    "id": "drain-bias",
    "kind": "dc-probe-pad",
    "pitch_um": 100.0,
    "width_um": 80.0,
    "height_um": 80.0,
    "count": 4,
}

SENSE_TAP = {"id": "gate-current-sense", "kind": "bias-sense-tap"}
PCM = {"id": "scribe-lane-pcm", "kind": "process-control-monitor"}
FIXTURE = {"id": "carrier-fixture", "kind": "assembled-fixture-only"}

GOOD_CASE = {
    "parameters": [
        {"name": "small-signal-gain", "role": "screening-critical", "requires": "rf-probe-pad"},
        {"name": "input-return-loss", "role": "screening-critical", "requires": "rf-probe-pad"},
        {"name": "quiescent-drain-current", "role": "screening-critical", "requires": "dc-probe-pad"},
        {"name": "gate-leakage", "role": "screening-critical", "requires": "bias-sense-tap"},
        {"name": "pinch-off-voltage", "role": "characterisation-only", "requires": "process-control-monitor"},
        {"name": "saturated-output-power", "role": "characterisation-only", "requires": "rf-probe-pad"},
    ],
    "access_points": [RF_PADS, DC_PADS, SENSE_TAP, PCM],
    "probe_card": PROBE_CARD,
    "die_area_um2": 4.0e6,
    "pad_area_budget_fraction": 0.08,
    "test_steps": 4,
    "retest_allowance": 0.5,
    "rated_touchdowns": 10,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class AccessPointValidationTests(unittest.TestCase):
    def test_a_probe_pad_normalises_with_its_geometry(self):
        point = validate_access_point(RF_PADS)
        self.assertEqual(point["kind"], "rf-probe-pad")
        self.assertAlmostEqual(point["pitch_um"], 100.0, places=9)
        self.assertEqual(point["count"], 6)

    def test_a_non_probe_access_point_needs_no_geometry(self):
        self.assertEqual(validate_access_point(SENSE_TAP)["kind"], "bias-sense-tap")

    def test_unknown_access_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_access_point({"id": "guess", "kind": "x-ray-window"})

    def test_access_point_without_an_id_rejected(self):
        bad = dict(RF_PADS)
        del bad["id"]
        with self.assertRaises(ValueError):
            validate_access_point(bad)

    def test_probe_pad_with_a_zero_pitch_rejected(self):
        with self.assertRaises(ValueError):
            validate_access_point(dict(RF_PADS, pitch_um=0.0))

    def test_probe_pad_with_a_fractional_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_access_point(dict(RF_PADS, count=2.5))

    def test_non_mapping_access_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_access_point("rf-probe-pad")


class ProbeLandingTests(unittest.TestCase):
    def test_minimum_landing_side_covers_tip_and_alignment_both_ways(self):
        self.assertAlmostEqual(minimum_landing_side_um(PROBE_CARD), 22.0, places=9)

    def test_a_matched_pad_is_compatible(self):
        result = probe_landing_check(RF_PADS, PROBE_CARD)
        self.assertTrue(result["compatible"])
        self.assertEqual(result["findings"], [])

    def test_a_pad_exactly_on_the_pitch_tolerance_is_compatible(self):
        result = probe_landing_check(dict(RF_PADS, pitch_um=102.0), PROBE_CARD)
        self.assertAlmostEqual(result["pitch_error_um"], 2.0, places=9)
        self.assertTrue(result["compatible"])

    def test_a_pad_beyond_the_pitch_tolerance_is_not_compatible(self):
        result = probe_landing_check(dict(RF_PADS, pitch_um=120.0), PROBE_CARD)
        self.assertFalse(result["compatible"])
        self.assertTrue(any("pitch" in f for f in result["findings"]))

    def test_a_pad_exactly_on_the_minimum_landing_side_is_compatible(self):
        result = probe_landing_check(
            dict(RF_PADS, width_um=22.0, height_um=22.0), PROBE_CARD
        )
        self.assertAlmostEqual(result["minimum_landing_side_um"], 22.0, places=9)
        self.assertTrue(result["compatible"])

    def test_a_pad_below_the_minimum_landing_side_is_not_compatible(self):
        result = probe_landing_check(
            dict(RF_PADS, width_um=15.0, height_um=60.0), PROBE_CARD
        )
        self.assertFalse(result["compatible"])
        self.assertTrue(any("overhang" in f for f in result["findings"]))

    def test_landing_check_refuses_a_non_probe_access_point(self):
        with self.assertRaises(ValueError):
            probe_landing_check(SENSE_TAP, PROBE_CARD)

    def test_probe_card_without_a_tip_diameter_rejected(self):
        card = dict(PROBE_CARD)
        del card["tip_diameter_um"]
        with self.assertRaises(ValueError):
            probe_landing_check(RF_PADS, card)


class ParameterAndObservabilityTests(unittest.TestCase):
    def test_a_parameter_normalises_with_its_role(self):
        parameter = validate_parameter(GOOD_CASE["parameters"][0])
        self.assertEqual(parameter["role"], "screening-critical")
        self.assertFalse(parameter["assembly_fallback"])

    def test_unknown_parameter_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "gain", "role": "nice-to-have", "requires": "rf-probe-pad"})

    def test_parameter_requiring_an_unknown_access_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter({"name": "gain", "role": "screening-critical", "requires": "telepathy"})

    def test_parameter_with_a_non_boolean_fallback_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(
                {
                    "name": "gain",
                    "role": "screening-critical",
                    "requires": "rf-probe-pad",
                    "assembly_fallback": "yes",
                }
            )

    def test_a_present_on_wafer_access_gives_on_wafer_observability(self):
        self.assertEqual(
            resolve_observability(GOOD_CASE["parameters"][0], {"rf-probe-pad"}), ON_WAFER
        )

    def test_a_fixture_only_access_gives_assembly_level_observability(self):
        self.assertEqual(
            resolve_observability(
                {"name": "thermal-resistance", "role": "characterisation-only",
                 "requires": "assembled-fixture-only"},
                {"assembled-fixture-only"},
            ),
            ASSEMBLY_LEVEL,
        )

    def test_a_missing_access_leaves_the_parameter_unobservable(self):
        self.assertEqual(
            resolve_observability(GOOD_CASE["parameters"][0], {"dc-probe-pad"}),
            UNOBSERVABLE,
        )

    def test_an_assembly_fallback_rescues_a_missing_access(self):
        parameter = dict(GOOD_CASE["parameters"][0], assembly_fallback=True)
        self.assertEqual(
            resolve_observability(parameter, {"assembled-fixture-only"}), ASSEMBLY_LEVEL
        )

    def test_unknown_available_kind_rejected(self):
        with self.assertRaises(ValueError):
            resolve_observability(GOOD_CASE["parameters"][0], {"microscope"})


class CoverageTests(unittest.TestCase):
    def test_full_access_puts_every_parameter_on_wafer(self):
        report = coverage_report(GOOD_CASE["parameters"], GOOD_CASE["access_points"])
        self.assertAlmostEqual(report["on_wafer_fraction"], 1.0, places=9)
        self.assertEqual(report["screening_gaps"], [])

    def test_removing_the_sense_tap_opens_a_screening_gap(self):
        points = [RF_PADS, DC_PADS, PCM]
        report = coverage_report(GOOD_CASE["parameters"], points)
        self.assertEqual(len(report["screening_gaps"]), 1)
        self.assertEqual(report["screening_gaps"][0]["name"], "gate-leakage")
        self.assertEqual(report["screening_gaps"][0]["observability"], UNOBSERVABLE)

    def test_coverage_fraction_falls_with_the_lost_access(self):
        report = coverage_report(GOOD_CASE["parameters"], [RF_PADS, DC_PADS, PCM])
        self.assertAlmostEqual(report["on_wafer_fraction"], 5.0 / 6.0, places=9)

    def test_coverage_groups_every_parameter_exactly_once(self):
        report = coverage_report(GOOD_CASE["parameters"], [RF_PADS])
        grouped_total = sum(len(v) for v in report["grouped"].values())
        self.assertEqual(grouped_total, report["total"])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_report([], GOOD_CASE["access_points"])

    def test_non_sequence_access_points_rejected(self):
        with self.assertRaises(ValueError):
            coverage_report(GOOD_CASE["parameters"], "rf pads")


class TouchdownTests(unittest.TestCase):
    def test_planned_touchdowns_include_the_retest_allowance(self):
        budget = touchdown_budget(4, 0.5, 10)
        self.assertAlmostEqual(budget["planned_touchdowns"], 6.0, places=9)
        self.assertTrue(budget["within_budget"])

    def test_a_flow_exactly_on_the_rating_is_within_budget(self):
        budget = touchdown_budget(8, 0.25, 10)
        self.assertAlmostEqual(budget["planned_touchdowns"], 10.0, places=9)
        self.assertTrue(budget["within_budget"])
        self.assertAlmostEqual(budget["headroom"], 0.0, places=9)

    def test_a_flow_over_the_rating_is_not_within_budget(self):
        self.assertFalse(touchdown_budget(12, 0.0, 10)["within_budget"])

    def test_zero_test_steps_rejected(self):
        with self.assertRaises(ValueError):
            touchdown_budget(0, 0.0, 10)

    def test_negative_retest_allowance_rejected(self):
        with self.assertRaises(ValueError):
            touchdown_budget(4, -0.5, 10)


class AreaTests(unittest.TestCase):
    def test_pad_area_sums_only_the_probe_pads(self):
        area = pad_area_overhead(GOOD_CASE["access_points"], 4.0e6)
        expected = 6 * 60.0 * 60.0 + 4 * 80.0 * 80.0
        self.assertAlmostEqual(area["pad_area_um2"], expected, places=6)

    def test_area_fraction_is_the_pad_area_over_the_die(self):
        area = pad_area_overhead(GOOD_CASE["access_points"], 4.0e6)
        self.assertAlmostEqual(
            area["area_fraction"], area["pad_area_um2"] / 4.0e6, places=12
        )

    def test_a_die_smaller_than_its_pads_rejected(self):
        with self.assertRaises(ValueError):
            pad_area_overhead(GOOD_CASE["access_points"], 1.0e3)

    def test_zero_die_area_rejected(self):
        with self.assertRaises(ValueError):
            pad_area_overhead(GOOD_CASE["access_points"], 0.0)


class AssessTests(unittest.TestCase):
    def test_the_good_case_is_adequate(self):
        result = assess_testability(GOOD_CASE)
        self.assertEqual(result["verdict"], ADEQUATE)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_a_screening_critical_parameter_with_no_access_is_inadequate(self):
        case = _case(GOOD_CASE, access_points=[RF_PADS, DC_PADS, PCM])
        result = assess_testability(case)
        self.assertEqual(result["verdict"], INADEQUATE)
        self.assertTrue(any("no measurement access" in f for f in result["findings"]))

    def test_an_unlandable_pad_is_inadequate(self):
        case = _case(
            GOOD_CASE,
            access_points=[dict(RF_PADS, pitch_um=150.0), DC_PADS, SENSE_TAP, PCM],
        )
        result = assess_testability(case)
        self.assertEqual(result["verdict"], INADEQUATE)
        self.assertFalse(result["probes_compatible"])

    def test_a_screening_parameter_reachable_only_after_assembly_is_conditional(self):
        parameters = copy.deepcopy(GOOD_CASE["parameters"])
        parameters[3] = {
            "name": "gate-leakage",
            "role": "screening-critical",
            "requires": "bias-sense-tap",
            "assembly_fallback": True,
        }
        case = _case(
            GOOD_CASE,
            parameters=parameters,
            access_points=[RF_PADS, DC_PADS, PCM, FIXTURE],
        )
        result = assess_testability(case)
        self.assertEqual(result["verdict"], CONDITIONAL)
        self.assertTrue(any("only after assembly" in f for f in result["findings"]))

    def test_an_over_budget_pad_area_is_conditional(self):
        result = assess_testability(_case(GOOD_CASE, pad_area_budget_fraction=0.001))
        self.assertEqual(result["verdict"], CONDITIONAL)
        self.assertFalse(result["pad_area_within_budget"])

    def test_an_over_spent_touchdown_budget_is_conditional(self):
        result = assess_testability(_case(GOOD_CASE, test_steps=20))
        self.assertEqual(result["verdict"], CONDITIONAL)
        self.assertFalse(result["touchdowns"]["within_budget"])

    def test_probe_pads_without_a_declared_probe_card_are_conditional(self):
        case = _case(GOOD_CASE)
        del case["probe_card"]
        result = assess_testability(case)
        self.assertEqual(result["verdict"], CONDITIONAL)
        self.assertTrue(result["probe_card_undeclared"])

    def test_the_good_case_reports_a_full_on_wafer_fraction(self):
        self.assertAlmostEqual(
            assess_testability(GOOD_CASE)["on_wafer_fraction"], 1.0, places=9
        )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_testability("probe everything")

    def test_case_without_a_die_area_rejected(self):
        case = _case(GOOD_CASE)
        del case["die_area_um2"]
        with self.assertRaises(ValueError):
            assess_testability(case)

    def test_losing_access_never_raises_the_coverage_fraction(self):
        full = assess_testability(GOOD_CASE)["on_wafer_fraction"]
        reduced = assess_testability(
            _case(GOOD_CASE, access_points=[RF_PADS, DC_PADS, SENSE_TAP])
        )["on_wafer_fraction"]
        self.assertGreater(full, reduced)


if __name__ == "__main__":
    unittest.main()
