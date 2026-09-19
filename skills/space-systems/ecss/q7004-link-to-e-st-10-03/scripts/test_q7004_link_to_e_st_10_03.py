#!/usr/bin/env python3
"""Contract test for the equipment-level test interface logic (offline)."""

import copy
import unittest

from q7004_link_to_e_st_10_03_logic import (
    DEFAULT_INTERFACE_POLICY,
    EQUIPMENT_STANDARD,
    HIGHER_IS_SEVERE,
    LOWER_IS_SEVERE,
    MATERIAL_STANDARD,
    PARAMETER_SENSE,
    coordinate_with_equipment_standard,
    credited_cycles,
    envelope_gaps,
    envelopes_material,
    more_severe,
    qualification_margin_k,
    reconcile_parameters,
    severity_sense,
    validate_interface_policy,
)

MATERIAL = {
    "hot_limit_k": 333.15,
    "cold_limit_k": 233.15,
    "cycle_count": 8,
    "dwell_s": 3600.0,
}

EQUIPMENT = {
    "hot_limit_k": 343.15,
    "cold_limit_k": 223.15,
    "cycle_count": 12,
    "dwell_s": 5400.0,
}

BASE_CASE = {
    "material_requirements": MATERIAL,
    "equipment_requirements": EQUIPMENT,
    "equipment_cycles_run": 4,
}


def _merge(base, **overrides):
    merged = copy.deepcopy(base)
    merged.update(overrides)
    return merged


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_interface_policy(DEFAULT_INTERFACE_POLICY),
            DEFAULT_INTERFACE_POLICY,
        )

    def test_a_credit_efficiency_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["credit_efficiency"] = 1.5
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_a_credit_cap_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["credit_cap_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_a_policy_naming_an_unknown_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_INTERFACE_POLICY)
        broken["required_parameters"] = ("hot_limit_k", "humidity_pct")
        with self.assertRaises(ValueError):
            validate_interface_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_interface_policy(("credit", 0.5))


class SeverityTests(unittest.TestCase):
    def test_a_hot_limit_is_more_severe_when_higher(self):
        self.assertEqual(severity_sense("hot_limit_k"), HIGHER_IS_SEVERE)

    def test_a_cold_limit_is_more_severe_when_lower(self):
        self.assertEqual(severity_sense("cold_limit_k"), LOWER_IS_SEVERE)

    def test_a_pressure_is_more_severe_when_lower(self):
        self.assertEqual(severity_sense("chamber_pressure_pa"), LOWER_IS_SEVERE)

    def test_every_declared_parameter_has_a_known_sense(self):
        for parameter, sense in PARAMETER_SENSE.items():
            self.assertIn(sense, (HIGHER_IS_SEVERE, LOWER_IS_SEVERE), parameter)

    def test_an_undeclared_parameter_is_refused_rather_than_guessed(self):
        with self.assertRaises(ValueError):
            severity_sense("relative_humidity_pct")

    def test_the_equipment_standard_governs_a_hotter_hot_limit(self):
        record = more_severe("hot_limit_k", 333.15, 343.15)
        self.assertEqual(record["governing_standard"], EQUIPMENT_STANDARD)
        self.assertAlmostEqual(record["governing_value"], 343.15, places=9)

    def test_the_material_standard_governs_a_colder_cold_limit(self):
        record = more_severe("cold_limit_k", 213.15, 233.15)
        self.assertEqual(record["governing_standard"], MATERIAL_STANDARD)
        self.assertAlmostEqual(record["governing_value"], 213.15, places=9)

    def test_equal_values_are_attributed_to_both(self):
        record = more_severe("dwell_s", 3600.0, 3600.0)
        self.assertEqual(record["governing_standard"], "both")

    def test_values_a_hair_apart_are_attributed_to_both(self):
        record = more_severe("dwell_s", 3600.0, 3600.0 + 1e-12)
        self.assertEqual(record["governing_standard"], "both")

    def test_a_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            more_severe("hot_limit_k", "sixty C", 343.15)


class ReconciliationTests(unittest.TestCase):
    def test_every_required_parameter_is_reconciled(self):
        reconciled = reconcile_parameters(MATERIAL, EQUIPMENT)
        for parameter in DEFAULT_INTERFACE_POLICY["required_parameters"]:
            self.assertIn(parameter, reconciled)

    def test_an_enveloping_equipment_set_leaves_no_gaps(self):
        reconciled = reconcile_parameters(MATERIAL, EQUIPMENT)
        self.assertEqual(envelope_gaps(reconciled), ())
        self.assertTrue(envelopes_material(reconciled))

    def test_one_weaker_parameter_breaks_the_envelope(self):
        weak = _merge(EQUIPMENT, dwell_s=1800.0)
        reconciled = reconcile_parameters(MATERIAL, weak)
        self.assertEqual(envelope_gaps(reconciled), ("dwell_s",))
        self.assertFalse(envelopes_material(reconciled))

    def test_gaps_are_reported_in_a_stable_order(self):
        weak = _merge(EQUIPMENT, dwell_s=1800.0, cycle_count=2)
        reconciled = reconcile_parameters(MATERIAL, weak)
        self.assertEqual(list(envelope_gaps(reconciled)), sorted(envelope_gaps(reconciled)))

    def test_a_missing_material_parameter_rejected(self):
        partial = copy.deepcopy(MATERIAL)
        del partial["dwell_s"]
        with self.assertRaises(ValueError):
            reconcile_parameters(partial, EQUIPMENT)

    def test_a_missing_equipment_parameter_rejected(self):
        partial = copy.deepcopy(EQUIPMENT)
        del partial["cycle_count"]
        with self.assertRaises(ValueError):
            reconcile_parameters(MATERIAL, partial)

    def test_a_non_mapping_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_parameters("see the spec", EQUIPMENT)


class CreditTests(unittest.TestCase):
    def test_credit_is_the_run_count_at_the_declared_efficiency(self):
        credit = credited_cycles(4, 12)
        self.assertEqual(credit["earned_before_cap"], 2)
        self.assertEqual(credit["credited_cycles"], 2)
        self.assertEqual(credit["remaining_cycles"], 10)

    def test_the_cap_bites_on_a_long_equipment_run(self):
        credit = credited_cycles(40, 12)
        self.assertTrue(credit["capped"])
        self.assertEqual(credit["credited_cycles"], 6)
        self.assertEqual(credit["remaining_cycles"], 6)

    def test_a_run_of_zero_cycles_earns_nothing(self):
        credit = credited_cycles(0, 12)
        self.assertEqual(credit["credited_cycles"], 0)
        self.assertEqual(credit["remaining_cycles"], 12)

    def test_credit_never_clears_the_whole_requirement(self):
        credit = credited_cycles(10000, 12)
        self.assertGreater(credit["remaining_cycles"], 0)

    def test_a_fractional_earned_credit_is_floored(self):
        credit = credited_cycles(5, 12)
        self.assertEqual(credit["earned_before_cap"], 2)

    def test_a_non_integer_run_count_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(4.5, 12)

    def test_a_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            credited_cycles(4, 0)


class MarginTests(unittest.TestCase):
    def test_a_hot_margin_is_the_qualification_limit_above_acceptance(self):
        self.assertAlmostEqual(
            qualification_margin_k(333.15, 343.15, HIGHER_IS_SEVERE), 10.0, places=9
        )

    def test_a_cold_margin_is_the_qualification_limit_below_acceptance(self):
        self.assertAlmostEqual(
            qualification_margin_k(233.15, 223.15, LOWER_IS_SEVERE), 10.0, places=9
        )

    def test_an_equal_pair_of_limits_holds_no_margin(self):
        self.assertAlmostEqual(
            qualification_margin_k(333.15, 333.15, HIGHER_IS_SEVERE), 0.0, places=9
        )

    def test_an_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            qualification_margin_k(333.15, 343.15, "whichever")

    def test_a_non_absolute_limit_rejected(self):
        with self.assertRaises(ValueError):
            qualification_margin_k(-60.0, 70.0, HIGHER_IS_SEVERE)


class CoordinationTests(unittest.TestCase):
    def test_the_base_case_interface_is_clean(self):
        result = coordinate_with_equipment_standard(BASE_CASE)
        self.assertTrue(result["interface_clean"])
        self.assertEqual(result["findings"], [])

    def test_the_base_case_equipment_set_envelopes_the_material_one(self):
        result = coordinate_with_equipment_standard(BASE_CASE)
        self.assertTrue(result["equipment_envelopes_material"])

    def test_a_coverage_gap_is_a_finding(self):
        case = _merge(
            BASE_CASE, equipment_requirements=_merge(EQUIPMENT, dwell_s=1800.0)
        )
        result = coordinate_with_equipment_standard(case)
        self.assertFalse(result["interface_clean"])
        self.assertTrue(any("does not envelope" in f for f in result["findings"]))

    def test_a_capped_credit_is_a_finding(self):
        result = coordinate_with_equipment_standard(
            _merge(BASE_CASE, equipment_cycles_run=40)
        )
        self.assertTrue(any("cap allows" in f for f in result["findings"]))

    def test_a_thin_hot_margin_is_a_finding(self):
        case = _merge(
            BASE_CASE, equipment_requirements=_merge(EQUIPMENT, hot_limit_k=334.15)
        )
        result = coordinate_with_equipment_standard(case)
        self.assertTrue(any("governing hot limit" in f for f in result["findings"]))

    def test_a_hot_margin_exactly_on_the_minimum_is_accepted(self):
        minimum = DEFAULT_INTERFACE_POLICY["min_hot_margin_k"]
        case = _merge(
            BASE_CASE,
            equipment_requirements=_merge(
                EQUIPMENT, hot_limit_k=MATERIAL["hot_limit_k"] + minimum
            ),
        )
        result = coordinate_with_equipment_standard(case)
        self.assertFalse(any("governing hot limit" in f for f in result["findings"]))

    def test_the_governing_cycle_count_drives_the_remaining_count(self):
        result = coordinate_with_equipment_standard(BASE_CASE)
        self.assertEqual(result["credit"]["required_cycles"], 12)
        self.assertEqual(
            result["credit"]["remaining_cycles"],
            12 - result["credit"]["credited_cycles"],
        )

    def test_every_result_carries_the_traceability_duty(self):
        result = coordinate_with_equipment_standard(BASE_CASE)
        self.assertTrue(any("governing document" in d for d in result["duties"]))

    def test_every_result_carries_the_credit_recording_duty(self):
        result = coordinate_with_equipment_standard(BASE_CASE)
        self.assertTrue(any("credit efficiency" in d for d in result["duties"]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            coordinate_with_equipment_standard("use the equipment test")

    def test_a_case_without_requirement_sets_rejected(self):
        with self.assertRaises(ValueError):
            coordinate_with_equipment_standard({"equipment_cycles_run": 4})


if __name__ == "__main__":
    unittest.main()
