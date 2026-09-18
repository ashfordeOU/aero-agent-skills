#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 10.1 assembly-control leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_hybrid_manufacturing_control.py
"""

import math
import unittest

from q6005_hybrid_manufacturing_control_logic import (
    ACCEPTANCE_INDEX,
    BAKEOUT_DWELL_AT_MINIMUM_HOURS,
    BAKEOUT_DWELL_FLOOR_HOURS,
    CONTROL_ELEMENT_WEIGHTS,
    CONTROL_STATE_CREDIT,
    CONTROL_TOLERANCE,
    ENVIRONMENT_GRADES,
    MANDATORY_CONTROL_ELEMENTS,
    MANDATORY_OPERATIONS,
    MAXIMUM_BAKEOUT_TEMPERATURE_C,
    MAXIMUM_RELATIVE_HUMIDITY_PERCENT,
    MAXIMUM_SEAL_DELAY_HOURS,
    MINIMUM_BAKEOUT_TEMPERATURE_C,
    MINIMUM_BOND_PULL_SAMPLE,
    MINIMUM_RELATIVE_HUMIDITY_PERCENT,
    OPERATION_ENVIRONMENT_LIMIT,
    REQUIRED_BOND_CAPABILITY,
    SEALING_MOISTURE_LIMIT_PPMV,
    VERDICTS,
    assess_bakeout,
    assess_control_element,
    assess_manufacturing_control,
    assess_seal_atmosphere,
    bond_strength_capability,
    control_element_weight,
    control_state_credit,
    environment_grade_value,
    humidity_within_band,
    manufacturing_control_index,
    missing_operations,
    normalize_control_element,
    normalize_operations,
    operation_environment_is_adequate,
    operation_environment_limit,
    operations_in_wrong_environment,
    required_bakeout_dwell_hours,
)

SPARE_ELEMENT = "rework-authorization-and-record"


def clean_operations():
    """Every assembly operation worked in air at least as clean as it needs."""
    return [
        {"operation": "substrate-preparation", "environment_grade": "grade-7"},
        {"operation": "die-attach", "environment_grade": "grade-6"},
        {"operation": "wire-bonding", "environment_grade": "grade-6"},
        {"operation": "pre-seal-visual-inspection", "environment_grade": "grade-6"},
        {"operation": "pre-seal-bakeout", "environment_grade": "grade-6"},
        {"operation": "package-sealing", "environment_grade": "grade-5"},
        {"operation": "external-lead-attach", "environment_grade": "grade-7"},
        {"operation": "marking-and-packing", "environment_grade": "grade-8"},
    ]


def controlled_elements(**states):
    """Every control element in control, with named exceptions."""
    elements = []
    for name in sorted(CONTROL_ELEMENT_WEIGHTS):
        entry = {"element": name, "state": "in-control"}
        if name in states:
            entry["state"] = states[name]
        elements.append(entry)
    return elements


def good_bakeout(**overrides):
    """A pre-seal bakeout held at the minimum plateau for its full dwell."""
    record = {"temperature_c": 125.0, "dwell_hours": 4.0}
    record.update(overrides)
    return record


def good_seal(**overrides):
    """A dry sealing atmosphere reached inside the allowed stand time."""
    record = {"moisture_ppmv": 1200.0, "delay_after_bakeout_hours": 0.5}
    record.update(overrides)
    return record


def good_pull(**overrides):
    """A bond pull sample whose spread keeps every bond off the floor."""
    record = {"samples_gf": [9.0, 9.0, 11.0, 11.0], "minimum_strength_gf": 7.0}
    record.update(overrides)
    return record


def run(**overrides):
    """Grade one assembly line."""
    case = {
        "line_id": "HYB-LINE-1",
        "operations": clean_operations(),
        "elements": controlled_elements(),
        "bakeout": good_bakeout(),
        "seal_atmosphere": good_seal(),
        "bond_pull": good_pull(),
        "relative_humidity_percent": 45.0,
    }
    case.update(overrides)
    return assess_manufacturing_control(**case)


class EnvironmentTests(unittest.TestCase):
    def test_a_cleaner_grade_carries_the_smaller_rank(self):
        self.assertLess(environment_grade_value("grade-5"), environment_grade_value("grade-8"))

    def test_an_unknown_environment_grade_is_rejected(self):
        with self.assertRaises(ValueError):
            environment_grade_value("fairly-clean")

    def test_every_operation_carries_a_published_environment_limit(self):
        for name in MANDATORY_OPERATIONS:
            self.assertIn(name, OPERATION_ENVIRONMENT_LIMIT)

    def test_sealing_demands_the_cleanest_air_of_all_operations(self):
        self.assertEqual(
            operation_environment_limit("package-sealing"),
            min(OPERATION_ENVIRONMENT_LIMIT.values()),
        )

    def test_an_unknown_assembly_operation_is_rejected(self):
        with self.assertRaises(ValueError):
            operation_environment_limit("shake-and-inspect")

    def test_an_operation_in_cleaner_air_than_required_is_adequate(self):
        self.assertTrue(operation_environment_is_adequate("die-attach", "grade-5"))

    def test_an_operation_on_the_shop_floor_is_not_adequate(self):
        self.assertFalse(
            operation_environment_is_adequate("wire-bonding", "uncontrolled-shop-floor")
        )

    def test_sealing_in_the_bonding_room_is_reported(self):
        operations = clean_operations()
        operations[5]["environment_grade"] = "grade-6"
        self.assertEqual(operations_in_wrong_environment(operations), ["package-sealing"])

    def test_a_repeated_operation_is_rejected(self):
        operations = clean_operations() + [
            {"operation": "die-attach", "environment_grade": "grade-6"}
        ]
        with self.assertRaises(ValueError):
            normalize_operations(operations)

    def test_an_empty_assembly_flow_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_operations([])

    def test_a_flow_that_never_names_sealing_is_reported(self):
        operations = [entry for entry in clean_operations() if entry["operation"] != "package-sealing"]
        self.assertEqual(missing_operations(operations), ["package-sealing"])


class HumidityTests(unittest.TestCase):
    def test_a_mid_band_humidity_is_accepted(self):
        self.assertTrue(humidity_within_band(45.0))

    def test_the_band_is_met_exactly_at_its_lower_edge(self):
        self.assertTrue(humidity_within_band(MINIMUM_RELATIVE_HUMIDITY_PERCENT))

    def test_the_band_is_met_exactly_at_its_upper_edge(self):
        self.assertTrue(humidity_within_band(MAXIMUM_RELATIVE_HUMIDITY_PERCENT))

    def test_a_damp_room_falls_outside_the_band(self):
        self.assertFalse(humidity_within_band(72.0))

    def test_a_humidity_outside_the_physical_range_is_rejected(self):
        with self.assertRaises(ValueError):
            humidity_within_band(140.0)


class BakeoutTests(unittest.TestCase):
    def test_the_minimum_plateau_carries_the_full_dwell(self):
        self.assertAlmostEqual(
            required_bakeout_dwell_hours(MINIMUM_BAKEOUT_TEMPERATURE_C),
            BAKEOUT_DWELL_AT_MINIMUM_HOURS,
            places=9,
        )

    def test_a_hotter_plateau_shortens_the_required_dwell(self):
        self.assertAlmostEqual(required_bakeout_dwell_hours(150.0), 3.0, places=9)

    def test_the_required_dwell_never_falls_below_its_floor(self):
        self.assertAlmostEqual(
            required_bakeout_dwell_hours(190.0), BAKEOUT_DWELL_FLOOR_HOURS, places=9
        )

    def test_a_plateau_under_the_minimum_has_no_published_dwell(self):
        with self.assertRaises(ValueError):
            required_bakeout_dwell_hours(90.0)

    def test_a_bake_meeting_its_dwell_exactly_is_adequate(self):
        record = assess_bakeout(good_bakeout())
        self.assertTrue(record["adequate"])
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(
            record["required_dwell_hours"], BAKEOUT_DWELL_AT_MINIMUM_HOURS, places=9
        )

    def test_a_short_dwell_at_the_minimum_plateau_is_a_finding(self):
        record = assess_bakeout(good_bakeout(dwell_hours=2.0))
        self.assertFalse(record["adequate"])
        self.assertIn("bakeout-dwell-below-required", record["findings"])

    def test_a_cold_bake_is_a_finding_not_a_shorter_dwell(self):
        record = assess_bakeout(good_bakeout(temperature_c=100.0))
        self.assertIn("bakeout-plateau-below-minimum", record["findings"])

    def test_a_bake_above_the_material_limit_is_a_finding_not_extra_credit(self):
        record = assess_bakeout(
            good_bakeout(temperature_c=MAXIMUM_BAKEOUT_TEMPERATURE_C + 25.0, dwell_hours=6.0)
        )
        self.assertIn("bakeout-plateau-above-material-limit", record["findings"])

    def test_a_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bakeout(good_bakeout(dwell_hours=-1.0))

    def test_a_bakeout_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_bakeout([125.0, 4.0])


class SealAtmosphereTests(unittest.TestCase):
    def test_a_dry_atmosphere_sealed_promptly_is_acceptable(self):
        record = assess_seal_atmosphere(good_seal())
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["findings"], [])

    def test_the_moisture_limit_is_met_exactly_at_the_limit(self):
        record = assess_seal_atmosphere(good_seal(moisture_ppmv=SEALING_MOISTURE_LIMIT_PPMV))
        self.assertTrue(record["acceptable"])
        self.assertAlmostEqual(record["moisture_margin_ppmv"], 0.0, places=9)

    def test_a_wet_atmosphere_is_reported(self):
        record = assess_seal_atmosphere(good_seal(moisture_ppmv=8000.0))
        self.assertIn("sealing-atmosphere-moisture-above-limit", record["findings"])

    def test_a_dry_gas_does_not_rescue_a_long_stand_time(self):
        record = assess_seal_atmosphere(
            good_seal(moisture_ppmv=50.0, delay_after_bakeout_hours=MAXIMUM_SEAL_DELAY_HOURS + 4.0)
        )
        self.assertFalse(record["acceptable"])
        self.assertIn("seal-delayed-beyond-allowed-stand-time", record["findings"])

    def test_the_stand_time_is_met_exactly_at_its_bound(self):
        record = assess_seal_atmosphere(
            good_seal(delay_after_bakeout_hours=MAXIMUM_SEAL_DELAY_HOURS)
        )
        self.assertTrue(record["acceptable"])

    def test_a_negative_moisture_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_seal_atmosphere(good_seal(moisture_ppmv=-10.0))


class BondStrengthTests(unittest.TestCase):
    def test_a_sample_meeting_the_capability_exactly_is_capable(self):
        record = bond_strength_capability(**{
            "samples": good_pull()["samples_gf"],
            "minimum_strength_gf": good_pull()["minimum_strength_gf"],
        })
        self.assertAlmostEqual(record["capability"], REQUIRED_BOND_CAPABILITY, places=9)
        self.assertTrue(record["capable"])

    def test_a_wide_spread_is_not_rescued_by_a_comfortable_mean(self):
        record = bond_strength_capability([4.0, 16.0, 4.0, 16.0], 3.0)
        self.assertAlmostEqual(record["mean_strength_gf"], 10.0, places=9)
        self.assertFalse(record["capable"])
        self.assertIn("bond-strength-spread-too-wide", record["findings"])

    def test_a_reading_under_the_floor_is_reported(self):
        record = bond_strength_capability([2.0, 9.0, 10.0, 11.0], 7.0)
        self.assertEqual(record["readings_below_minimum"], 1)
        self.assertIn("pull-reading-below-minimum-strength", record["findings"])

    def test_a_sample_with_no_spread_above_the_floor_is_unbounded(self):
        record = bond_strength_capability([10.0, 10.0, 10.0, 10.0], 7.0)
        self.assertTrue(math.isinf(record["capability"]))
        self.assertTrue(record["capable"])

    def test_a_sample_too_small_to_read_a_spread_from_is_rejected(self):
        with self.assertRaises(ValueError):
            bond_strength_capability([9.0] * (MINIMUM_BOND_PULL_SAMPLE - 1), 7.0)

    def test_a_non_numeric_pull_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            bond_strength_capability([9.0, 9.0, "eleven", 11.0], 7.0)

    def test_a_non_positive_minimum_strength_is_rejected(self):
        with self.assertRaises(ValueError):
            bond_strength_capability([9.0, 9.0, 11.0, 11.0], 0.0)


class ControlElementTests(unittest.TestCase):
    def test_every_mandatory_element_carries_a_published_weight(self):
        for name in MANDATORY_CONTROL_ELEMENTS:
            self.assertIn(name, CONTROL_ELEMENT_WEIGHTS)

    def test_an_unknown_control_element_is_rejected(self):
        with self.assertRaises(ValueError):
            control_element_weight("general-tidiness")

    def test_an_unknown_control_state_is_rejected(self):
        with self.assertRaises(ValueError):
            control_state_credit("probably-fine")

    def test_an_element_nobody_mentioned_defaults_to_not_implemented(self):
        record = normalize_control_element({"element": SPARE_ELEMENT})
        self.assertEqual(record["state"], "not-implemented")

    def test_an_element_in_control_earns_its_full_weight(self):
        record = assess_control_element({"element": SPARE_ELEMENT, "state": "in-control"})
        self.assertAlmostEqual(
            record["weighted_credit"], CONTROL_ELEMENT_WEIGHTS[SPARE_ELEMENT], places=9
        )
        self.assertEqual(record["findings"], [])

    def test_a_missing_mandatory_element_is_marked_missing(self):
        record = assess_control_element({"element": "pre-seal-visual-inspection"})
        self.assertTrue(record["mandatory_missing"])
        self.assertIn("control-element-not-implemented", record["findings"])

    def test_a_missing_optional_element_is_a_finding_but_not_mandatory(self):
        record = assess_control_element({"element": SPARE_ELEMENT})
        self.assertFalse(record["mandatory_missing"])
        self.assertIn("control-element-not-implemented", record["findings"])

    def test_a_mandatory_element_out_of_control_is_flagged_separately(self):
        record = assess_control_element(
            {"element": "electrostatic-discharge-control", "state": "out-of-control"}
        )
        self.assertTrue(record["mandatory_out_of_control"])
        self.assertFalse(record["mandatory_missing"])

    def test_a_fully_controlled_line_reaches_a_full_index(self):
        records = [assess_control_element(entry) for entry in controlled_elements()]
        self.assertAlmostEqual(manufacturing_control_index(records), 1.0, places=9)

    def test_an_empty_element_set_is_rejected(self):
        with self.assertRaises(ValueError):
            manufacturing_control_index([])


class WholeLineTests(unittest.TestCase):
    def test_a_controlled_line_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "assembly-process-under-control")
        self.assertTrue(result["line_under_control"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["manufacturing_control_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_line_with_no_pre_seal_inspection_is_incomplete(self):
        result = run(elements=controlled_elements(**{"pre-seal-visual-inspection": "not-implemented"}))
        self.assertEqual(result["verdict"], "manufacturing-control-assessment-incomplete")

    def test_a_flow_that_never_seals_is_incomplete(self):
        operations = [e for e in clean_operations() if e["operation"] != "package-sealing"]
        result = run(operations=operations)
        self.assertEqual(result["verdict"], "manufacturing-control-assessment-incomplete")
        self.assertEqual(result["missing_operations"], ["package-sealing"])

    def test_bonding_on_the_shop_floor_takes_the_line_out_of_control(self):
        operations = clean_operations()
        operations[2]["environment_grade"] = "uncontrolled-shop-floor"
        result = run(operations=operations)
        self.assertEqual(result["verdict"], "assembly-process-not-under-control")
        self.assertEqual(result["operations_in_wrong_environment"], ["wire-bonding"])

    def test_a_wet_seal_takes_the_line_out_of_control(self):
        result = run(seal_atmosphere=good_seal(moisture_ppmv=9000.0))
        self.assertEqual(result["verdict"], "assembly-process-not-under-control")
        self.assertFalse(result["line_under_control"])

    def test_a_short_bake_takes_the_line_out_of_control(self):
        result = run(bakeout=good_bakeout(dwell_hours=1.0))
        self.assertEqual(result["verdict"], "assembly-process-not-under-control")

    def test_a_wide_bond_spread_takes_the_line_out_of_control(self):
        result = run(bond_pull={"samples_gf": [4.0, 16.0, 4.0, 16.0], "minimum_strength_gf": 3.0})
        self.assertEqual(result["verdict"], "assembly-process-not-under-control")

    def test_an_observation_on_an_optional_element_leaves_open_actions(self):
        result = run(elements=controlled_elements(**{SPARE_ELEMENT: "in-control-with-observation"}))
        self.assertEqual(result["verdict"], "assembly-process-under-control-with-open-actions")
        self.assertTrue(result["line_under_control"])

    def test_a_damp_room_is_reported_without_a_pull_sample_present(self):
        result = run(bond_pull=None, relative_humidity_percent=85.0)
        self.assertFalse(result["humidity_within_band"])
        self.assertIsNone(result["bond_strength"])
        self.assertIn(
            "area-humidity-outside-assembly-band", [f["finding"] for f in result["findings"]]
        )

    def test_an_element_nobody_listed_is_graded_as_not_implemented(self):
        result = run(elements=[{"element": SPARE_ELEMENT, "state": "in-control"}])
        states = {r["element"]: r["state"] for r in result["element_records"]}
        self.assertEqual(states["sealing-atmosphere-control"], "not-implemented")
        self.assertEqual(len(result["element_records"]), len(CONTROL_ELEMENT_WEIGHTS))

    def test_a_repeated_control_element_is_rejected(self):
        elements = controlled_elements() + [{"element": SPARE_ELEMENT, "state": "in-control"}]
        with self.assertRaises(ValueError):
            run(elements=elements)

    def test_a_blank_line_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(line_id="   ")

    def test_a_non_sequence_element_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            run(elements={"element": SPARE_ELEMENT})


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(CONTROL_TOLERANCE, 1e-6)

    def test_the_control_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(CONTROL_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(CONTROL_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_controlled_line(self):
        self.assertLess(ACCEPTANCE_INDEX, 1.0)

    def test_the_humidity_band_is_a_band_and_not_a_point(self):
        self.assertLess(MINIMUM_RELATIVE_HUMIDITY_PERCENT, MAXIMUM_RELATIVE_HUMIDITY_PERCENT)

    def test_the_bakeout_window_runs_from_the_minimum_to_the_material_limit(self):
        self.assertLess(MINIMUM_BAKEOUT_TEMPERATURE_C, MAXIMUM_BAKEOUT_TEMPERATURE_C)

    def test_every_environment_grade_carries_a_whole_rank(self):
        for name, value in ENVIRONMENT_GRADES.items():
            self.assertIsInstance(value, int, name)


if __name__ == "__main__":
    unittest.main()
