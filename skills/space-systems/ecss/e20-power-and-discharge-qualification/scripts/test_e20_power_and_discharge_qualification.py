#!/usr/bin/env python3
"""Gate 3 contract test for e20-power-and-discharge-qualification.

Offline, deterministic, stdlib unittest only.
"""

import unittest

from e20_power_and_discharge_qualification_logic import (
    AXES,
    CHANGE_IMPACT,
    COMPARISON_TOLERANCE,
    QUALIFICATION_EVIDENCE,
    assess_qualification_programme,
    categorize_qualification_evidence,
    cross_axis_configuration_check,
    delta_qualification_required,
    evaluate_gas_discharge_axis,
    evaluate_power_handling_axis,
    evidence_profile,
    qualification_power_level_w,
    qualified_operating_envelope_w,
    required_dwell_s,
)


def power_record(**overrides):
    record = {
        "evidence": "dedicated-qualification-model",
        "hardware_standard": "QM-01",
        "demonstrated_level_w": 320.0,
        "dwell_s": 3600.0,
        "thermal_time_constant_s": 600.0,
        "hot_case_temperature_c": 75.0,
        "required_hot_case_temperature_c": 70.0,
    }
    record.update(overrides)
    return record


def discharge_record(**overrides):
    record = {
        "evidence": "dedicated-qualification-model",
        "hardware_standard": "QM-01",
        "demonstrated_level_w": 320.0,
        "swept_band_pa": (0.5, 5000.0),
        "critical_band_pa": (10.0, 2000.0),
        "dwell_per_step_s": 120.0,
        "minimum_step_dwell_s": 60.0,
    }
    record.update(overrides)
    return record


def programme(**overrides):
    prog = {
        "id": "ka-band-output-stage",
        "max_operating_power_w": 250.0,
        "overstress_db": 1.0,
        "axes": {
            "power-handling-capability": power_record(),
            "gas-discharge-behaviour": discharge_record(),
        },
        "changes": [],
    }
    prog.update(overrides)
    return prog


class EvidenceCategoryTests(unittest.TestCase):
    def test_canonical_evidence_resolves_to_itself(self):
        self.assertEqual(
            categorize_qualification_evidence("protoflight-campaign"),
            "protoflight-campaign",
        )

    def test_qualification_model_alias_resolves(self):
        self.assertEqual(
            categorize_qualification_evidence("qualification-model"),
            "dedicated-qualification-model",
        )

    def test_heritage_alias_resolves(self):
        self.assertEqual(
            categorize_qualification_evidence("heritage"), "heritage-similarity"
        )

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(
            categorize_qualification_evidence(" Validated-Analysis "),
            "validated-analysis",
        )

    def test_unrecognized_evidence_raises(self):
        with self.assertRaises(ValueError):
            categorize_qualification_evidence("vendor-assurance")

    def test_non_string_evidence_raises(self):
        with self.assertRaises(ValueError):
            categorize_qualification_evidence(42)

    def test_dedicated_model_is_the_strongest_standalone_route(self):
        profile = evidence_profile("dedicated-qualification-model")
        self.assertTrue(profile["standalone"])
        self.assertEqual(
            profile["strength"],
            max(entry["strength"] for entry in QUALIFICATION_EVIDENCE.values()),
        )

    def test_weak_routes_are_not_standalone(self):
        for kind in ("validated-analysis", "heritage-similarity"):
            self.assertFalse(evidence_profile(kind)["standalone"])

    def test_evidence_profile_is_a_copy(self):
        profile = evidence_profile("protoflight-campaign")
        profile["standalone"] = False
        self.assertTrue(evidence_profile("protoflight-campaign")["standalone"])


class LevelAndDwellTests(unittest.TestCase):
    def test_zero_overstress_leaves_the_level_unchanged(self):
        self.assertAlmostEqual(qualification_power_level_w(250.0, 0.0), 250.0)

    def test_three_decibel_overstress_roughly_doubles_the_level(self):
        self.assertAlmostEqual(
            qualification_power_level_w(100.0, 3.0103), 200.0, places=3
        )

    def test_envelope_inverts_the_overstress(self):
        level = qualification_power_level_w(250.0, 1.0)
        self.assertAlmostEqual(qualified_operating_envelope_w(level, 1.0), 250.0)

    def test_non_positive_operating_power_raises(self):
        with self.assertRaises(ValueError):
            qualification_power_level_w(0.0, 1.0)

    def test_negative_overstress_raises(self):
        with self.assertRaises(ValueError):
            qualification_power_level_w(250.0, -1.0)

    def test_non_positive_demonstrated_level_raises_in_envelope(self):
        with self.assertRaises(ValueError):
            qualified_operating_envelope_w(0.0, 1.0)

    def test_negative_overstress_raises_in_envelope(self):
        with self.assertRaises(ValueError):
            qualified_operating_envelope_w(320.0, -1.0)

    def test_dwell_follows_the_thermal_time_constant(self):
        self.assertAlmostEqual(required_dwell_s(600.0), 3000.0)

    def test_dwell_is_floored_for_a_fast_item(self):
        self.assertAlmostEqual(required_dwell_s(10.0), 300.0)

    def test_settling_multiple_is_configurable(self):
        self.assertAlmostEqual(required_dwell_s(600.0, settling_multiple=3.0), 1800.0)

    def test_non_positive_time_constant_raises(self):
        with self.assertRaises(ValueError):
            required_dwell_s(0.0)

    def test_non_positive_settling_multiple_raises(self):
        with self.assertRaises(ValueError):
            required_dwell_s(600.0, settling_multiple=0.0)

    def test_negative_floor_dwell_raises(self):
        with self.assertRaises(ValueError):
            required_dwell_s(600.0, minimum_dwell_s=-1.0)


class PowerHandlingAxisTests(unittest.TestCase):
    def test_sound_campaign_closes_the_axis(self):
        result = evaluate_power_handling_axis(power_record(), 314.9)
        self.assertTrue(result["closed"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["required_dwell_s"], 3000.0)

    def test_level_shortfall_keeps_the_axis_open(self):
        result = evaluate_power_handling_axis(
            power_record(demonstrated_level_w=300.0), 314.9
        )
        self.assertFalse(result["closed"])

    def test_level_exactly_at_the_requirement_closes_the_axis(self):
        required = qualification_power_level_w(250.0, 1.0)
        result = evaluate_power_handling_axis(
            power_record(demonstrated_level_w=required), required
        )
        self.assertTrue(result["closed"])

    def test_short_dwell_keeps_the_axis_open(self):
        result = evaluate_power_handling_axis(power_record(dwell_s=600.0), 314.9)
        self.assertFalse(result["closed"])
        self.assertTrue(any("steady state" in text for text in result["findings"]))

    def test_dwell_exactly_at_the_requirement_closes_the_axis(self):
        result = evaluate_power_handling_axis(power_record(dwell_s=3000.0), 314.9)
        self.assertTrue(result["closed"])

    def test_cold_run_below_the_hot_case_keeps_the_axis_open(self):
        result = evaluate_power_handling_axis(
            power_record(hot_case_temperature_c=55.0), 314.9
        )
        self.assertFalse(result["closed"])

    def test_missing_hot_case_result_is_a_finding(self):
        record = power_record()
        del record["hot_case_temperature_c"]
        result = evaluate_power_handling_axis(record, 314.9)
        self.assertFalse(result["closed"])

    def test_missing_thermal_time_constant_is_a_finding(self):
        record = power_record()
        del record["thermal_time_constant_s"]
        result = evaluate_power_handling_axis(record, 314.9)
        self.assertFalse(result["closed"])
        self.assertTrue(
            any("thermal time constant" in text for text in result["findings"])
        )

    def test_analysis_route_without_support_cannot_close_the_axis(self):
        result = evaluate_power_handling_axis(
            power_record(evidence="validated-analysis"), 314.9
        )
        self.assertFalse(result["closed"])

    def test_analysis_route_with_a_correlation_reference_closes_the_axis(self):
        result = evaluate_power_handling_axis(
            power_record(
                evidence="validated-analysis", supporting_reference="TN-0091"
            ),
            314.9,
        )
        self.assertTrue(result["closed"])

    def test_missing_key_raises(self):
        record = power_record()
        del record["dwell_s"]
        with self.assertRaises(ValueError):
            evaluate_power_handling_axis(record, 314.9)

    def test_non_positive_demonstrated_level_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_handling_axis(
                power_record(demonstrated_level_w=0.0), 314.9
            )

    def test_non_positive_dwell_raises(self):
        with self.assertRaises(ValueError):
            evaluate_power_handling_axis(power_record(dwell_s=0.0), 314.9)


class GasDischargeAxisTests(unittest.TestCase):
    def test_sound_sweep_closes_the_axis(self):
        result = evaluate_gas_discharge_axis(discharge_record(), 314.9)
        self.assertTrue(result["closed"])
        self.assertEqual(result["uncovered_bands"], [])

    def test_vacuum_only_sweep_keeps_the_axis_open(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(swept_band_pa=(1.0e-6, 1.0e-3)), 314.9
        )
        self.assertFalse(result["closed"])
        self.assertTrue(result["uncovered_bands"])

    def test_sweep_stopping_short_of_the_high_edge_keeps_the_axis_open(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(swept_band_pa=(0.5, 500.0)), 314.9
        )
        self.assertEqual(len(result["uncovered_bands"]), 1)

    def test_sweep_inside_the_critical_band_leaves_two_gaps(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(swept_band_pa=(100.0, 500.0)), 314.9
        )
        self.assertEqual(len(result["uncovered_bands"]), 2)

    def test_level_shortfall_keeps_the_axis_open(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(demonstrated_level_w=280.0), 314.9
        )
        self.assertFalse(result["closed"])

    def test_short_step_dwell_keeps_the_axis_open(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(dwell_per_step_s=10.0), 314.9
        )
        self.assertFalse(result["closed"])
        self.assertTrue(any("pressure step" in text for text in result["findings"]))

    def test_step_dwell_exactly_at_the_minimum_closes_the_axis(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(dwell_per_step_s=60.0), 314.9
        )
        self.assertTrue(result["closed"])

    def test_missing_step_dwell_against_a_stated_minimum_is_a_finding(self):
        record = discharge_record()
        del record["dwell_per_step_s"]
        result = evaluate_gas_discharge_axis(record, 314.9)
        self.assertFalse(result["closed"])

    def test_heritage_route_without_support_cannot_close_the_axis(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(evidence="heritage-similarity"), 314.9
        )
        self.assertFalse(result["closed"])

    def test_heritage_route_with_a_delta_record_closes_the_axis(self):
        result = evaluate_gas_discharge_axis(
            discharge_record(
                evidence="heritage-similarity", supporting_reference="HERITAGE-DELTA-4"
            ),
            314.9,
        )
        self.assertTrue(result["closed"])

    def test_missing_key_raises(self):
        record = discharge_record()
        del record["critical_band_pa"]
        with self.assertRaises(ValueError):
            evaluate_gas_discharge_axis(record, 314.9)

    def test_malformed_band_raises(self):
        with self.assertRaises(ValueError):
            evaluate_gas_discharge_axis(
                discharge_record(swept_band_pa=(5000.0,)), 314.9
            )

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            evaluate_gas_discharge_axis(
                discharge_record(critical_band_pa=(2000.0, 10.0)), 314.9
            )

    def test_non_positive_level_raises(self):
        with self.assertRaises(ValueError):
            evaluate_gas_discharge_axis(
                discharge_record(demonstrated_level_w=-1.0), 314.9
            )


class CrossAxisTests(unittest.TestCase):
    def test_one_hardware_standard_needs_no_link(self):
        power = evaluate_power_handling_axis(power_record(), 314.9)
        discharge = evaluate_gas_discharge_axis(discharge_record(), 314.9)
        check = cross_axis_configuration_check(power, discharge)
        self.assertTrue(check["single_standard"])
        self.assertEqual(check["findings"], [])

    def test_two_standards_without_a_link_is_a_finding(self):
        power = evaluate_power_handling_axis(power_record(), 314.9)
        discharge = evaluate_gas_discharge_axis(
            discharge_record(hardware_standard="EM-03"), 314.9
        )
        check = cross_axis_configuration_check(power, discharge)
        self.assertFalse(check["single_standard"])
        self.assertEqual(len(check["findings"]), 1)

    def test_two_standards_with_a_recorded_link_clears(self):
        power = evaluate_power_handling_axis(power_record(), 314.9)
        discharge = evaluate_gas_discharge_axis(
            discharge_record(hardware_standard="EM-03"), 314.9
        )
        check = cross_axis_configuration_check(power, discharge, "CONFIG-LINK-7")
        self.assertEqual(check["findings"], [])


class DeltaQualificationTests(unittest.TestCase):
    def test_no_change_needs_no_delta(self):
        delta = delta_qualification_required([])
        self.assertFalse(delta["required"])
        self.assertEqual(delta["axes"], [])

    def test_gap_geometry_change_reopens_only_the_discharge_axis(self):
        delta = delta_qualification_required(["discharge-gap-geometry"])
        self.assertTrue(delta["required"])
        self.assertEqual(delta["axes"], ["gas-discharge-behaviour"])

    def test_thermal_interface_change_reopens_only_the_power_axis(self):
        delta = delta_qualification_required(["thermal-interface"])
        self.assertEqual(delta["axes"], ["power-handling-capability"])

    def test_power_increase_reopens_both_axes(self):
        delta = delta_qualification_required(["operating-power-increase"])
        self.assertEqual(list(delta["axes"]), list(AXES))

    def test_cosmetic_change_reopens_nothing(self):
        delta = delta_qualification_required(["external-marking", "documentation-only"])
        self.assertFalse(delta["required"])

    def test_axes_are_reported_in_canonical_order_without_duplicates(self):
        delta = delta_qualification_required(
            ["surface-treatment", "venting-path", "conductor-plating"]
        )
        self.assertEqual(list(delta["axes"]), list(AXES))

    def test_every_catalogued_change_maps_to_known_axes(self):
        for change, axes in CHANGE_IMPACT.items():
            for axis in axes:
                self.assertIn(axis, AXES)

    def test_unrecognized_change_raises(self):
        with self.assertRaises(ValueError):
            delta_qualification_required(["repaint-the-label"])

    def test_non_sequence_changes_raise(self):
        with self.assertRaises(ValueError):
            delta_qualification_required("thermal-interface")

    def test_empty_change_string_raises(self):
        with self.assertRaises(ValueError):
            delta_qualification_required([""])


class ProgrammeAssessmentTests(unittest.TestCase):
    def test_sound_programme_is_qualified(self):
        report = assess_qualification_programme(programme())
        self.assertTrue(report["qualified"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["required_level_w"], 250.0 * 10.0 ** 0.1)

    def test_qualified_envelope_follows_the_weaker_axis(self):
        prog = programme()
        prog["axes"]["gas-discharge-behaviour"]["demonstrated_level_w"] = 400.0
        report = assess_qualification_programme(prog)
        self.assertAlmostEqual(
            report["qualified_operating_envelope_w"],
            qualified_operating_envelope_w(320.0, 1.0),
        )

    def test_missing_discharge_axis_is_a_finding(self):
        prog = programme()
        del prog["axes"]["gas-discharge-behaviour"]
        report = assess_qualification_programme(prog)
        self.assertFalse(report["qualified"])
        self.assertTrue(
            any("not addressed" in text for text in report["findings"])
        )
        self.assertIsNone(report["configuration"])

    def test_missing_power_axis_is_a_finding(self):
        prog = programme()
        del prog["axes"]["power-handling-capability"]
        report = assess_qualification_programme(prog)
        self.assertFalse(report["qualified"])

    def test_split_hardware_standards_reach_the_programme_findings(self):
        prog = programme()
        prog["axes"]["gas-discharge-behaviour"]["hardware_standard"] = "EM-03"
        report = assess_qualification_programme(prog)
        self.assertFalse(report["qualified"])
        self.assertFalse(report["configuration"]["single_standard"])

    def test_recorded_configuration_link_clears_split_standards(self):
        prog = programme(configuration_link="CONFIG-LINK-7")
        prog["axes"]["gas-discharge-behaviour"]["hardware_standard"] = "EM-03"
        report = assess_qualification_programme(prog)
        self.assertTrue(report["qualified"])

    def test_open_change_forces_a_delta_finding(self):
        report = assess_qualification_programme(
            programme(changes=["discharge-gap-geometry"])
        )
        self.assertFalse(report["qualified"])
        self.assertTrue(report["delta"]["required"])

    def test_higher_overstress_raises_the_required_level_and_can_open_an_axis(self):
        report = assess_qualification_programme(programme(overstress_db=3.0))
        self.assertFalse(report["qualified"])
        self.assertGreater(report["required_level_w"], 320.0)

    def test_programme_identifier_is_carried_through(self):
        report = assess_qualification_programme(programme())
        self.assertEqual(report["id"], "ka-band-output-stage")

    def test_missing_programme_key_raises(self):
        prog = programme()
        del prog["overstress_db"]
        with self.assertRaises(ValueError):
            assess_qualification_programme(prog)

    def test_unrecognized_axis_raises(self):
        prog = programme()
        prog["axes"]["thermal-vacuum-behaviour"] = power_record()
        with self.assertRaises(ValueError):
            assess_qualification_programme(prog)

    def test_axes_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_qualification_programme(programme(axes=[power_record()]))

    def test_tolerance_constant_is_representation_scale_only(self):
        self.assertLess(COMPARISON_TOLERANCE, 1.0e-6)


if __name__ == "__main__":
    unittest.main()
