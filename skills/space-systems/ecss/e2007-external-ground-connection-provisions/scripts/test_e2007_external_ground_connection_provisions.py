#!/usr/bin/env python3
"""Gate 3 contract test for e2007-external-ground-connection-provisions.

Offline, deterministic, stdlib unittest. Exercises provision qualification and
its error paths, the resistance-capacitance time constant, residual-potential
decay, required dwell, peak equalization current, the bleed-resistance window,
per-operation evaluation and the aggregate clause 4.2.11.3 verdict.
"""

import math
import unittest

import e2007_external_ground_connection_provisions_logic as logic


def nominal_provisions():
    return [
        {
            "id": "gnd-stud-forward-ring",
            "style": "grounding-stud",
            "bond_to_structure_mohm": 3.0,
            "bleed_resistance_ohm": 1.0e6,
            "marking_present": True,
            "reachable_configurations": [
                "transport-container-open",
                "hoist-and-mate",
            ],
        },
        {
            "id": "jack-aft-bulkhead",
            "style": "banana-jack-receptacle",
            "bond_to_structure_mohm": 6.5,
            "bleed_resistance_ohm": 1.0e6,
            "marking_present": True,
            "reachable_configurations": ["hoist-and-mate"],
        },
    ]


def nominal_operations():
    return [
        {
            "id": "op-array-panel-handling",
            "provision_id": "gnd-stud-forward-ring",
            "configuration": "transport-container-open",
            "initial_potential_v": 1500.0,
            "item_capacitance_f": 1.0e-7,
            "dwell_s": 5.0,
            "susceptibility_category": "category-1b",
        },
        {
            "id": "op-payload-connector-mating",
            "provision_id": "jack-aft-bulkhead",
            "configuration": "hoist-and-mate",
            "initial_potential_v": 800.0,
            "item_capacitance_f": 5.0e-8,
            "dwell_s": 2.0,
            "susceptibility_category": "category-1a",
        },
    ]


def nominal_catalogue():
    return logic.build_provision_catalogue(nominal_provisions())


class TestThresholds(unittest.TestCase):
    def test_residual_threshold_derates_the_withstand(self):
        self.assertAlmostEqual(logic.residual_threshold_v("category-0"), 25.0)
        self.assertAlmostEqual(logic.residual_threshold_v("category-1a"), 50.0)
        self.assertAlmostEqual(logic.residual_threshold_v("category-1b"), 100.0)
        self.assertAlmostEqual(logic.residual_threshold_v("category-2"), 200.0)

    def test_residual_threshold_canonicalizes_case(self):
        self.assertAlmostEqual(logic.residual_threshold_v(" Category-1A "), 50.0)

    def test_residual_threshold_rejects_an_uncategorized_item(self):
        with self.assertRaises(ValueError):
            logic.residual_threshold_v("category-9")

    def test_normalize_token_rejects_non_string(self):
        with self.assertRaises(ValueError):
            logic.normalize_token(3, logic.PROVISION_STYLES, "provision style")


class TestTimeConstant(unittest.TestCase):
    def test_time_constant_is_the_resistance_capacitance_product(self):
        self.assertAlmostEqual(logic.time_constant_s(1.0e6, 1.0e-7), 0.1)

    def test_rejects_zero_resistance(self):
        with self.assertRaises(ValueError):
            logic.time_constant_s(0.0, 1.0e-7)

    def test_rejects_zero_capacitance(self):
        with self.assertRaises(ValueError):
            logic.time_constant_s(1.0e6, 0.0)

    def test_rejects_non_numeric_resistance(self):
        with self.assertRaises(ValueError):
            logic.time_constant_s("1 megaohm", 1.0e-7)


class TestDecay(unittest.TestCase):
    def test_one_time_constant_leaves_the_reciprocal_of_e(self):
        residual = logic.residual_potential_v(1000.0, 1.0e6, 1.0e-7, 0.1)
        self.assertAlmostEqual(residual, 1000.0 / math.e, places=9)

    def test_zero_dwell_leaves_the_initial_potential(self):
        self.assertAlmostEqual(
            logic.residual_potential_v(1500.0, 1.0e6, 1.0e-7, 0.0), 1500.0
        )

    def test_residual_falls_as_the_dwell_grows(self):
        short = logic.residual_potential_v(1500.0, 1.0e6, 1.0e-7, 0.2)
        long_dwell = logic.residual_potential_v(1500.0, 1.0e6, 1.0e-7, 0.6)
        self.assertLess(long_dwell, short)

    def test_rejects_a_negative_dwell(self):
        with self.assertRaises(ValueError):
            logic.residual_potential_v(1500.0, 1.0e6, 1.0e-7, -1.0)

    def test_rejects_a_negative_initial_potential(self):
        with self.assertRaises(ValueError):
            logic.residual_potential_v(-10.0, 1.0e6, 1.0e-7, 1.0)


class TestRequiredDwell(unittest.TestCase):
    def test_decade_of_decay_takes_one_time_constant_times_log_ten(self):
        dwell = logic.required_dwell_s(1000.0, 100.0, 1.0e6, 1.0e-7)
        self.assertAlmostEqual(dwell, 0.1 * math.log(10.0))

    def test_required_dwell_returns_the_target_potential(self):
        dwell = logic.required_dwell_s(1500.0, 100.0, 1.0e6, 1.0e-7)
        residual = logic.residual_potential_v(1500.0, 1.0e6, 1.0e-7, dwell)
        self.assertAlmostEqual(residual, 100.0, places=6)

    def test_rejects_a_target_at_or_above_the_initial_potential(self):
        with self.assertRaises(ValueError):
            logic.required_dwell_s(500.0, 500.0, 1.0e6, 1.0e-7)

    def test_rejects_a_zero_target(self):
        with self.assertRaises(ValueError):
            logic.required_dwell_s(500.0, 0.0, 1.0e6, 1.0e-7)


class TestPeakCurrent(unittest.TestCase):
    def test_peak_current_is_potential_over_bleed_resistance(self):
        self.assertAlmostEqual(
            logic.peak_equalization_current_a(1500.0, 1.0e6), 1.5e-3
        )

    def test_hard_short_is_rejected_rather_than_reported_as_infinite(self):
        with self.assertRaises(ValueError):
            logic.peak_equalization_current_a(1500.0, 0.0)


class TestResistanceWindow(unittest.TestCase):
    def test_nominal_window_is_feasible_and_bracketed(self):
        window = logic.bleed_resistance_window_ohm(1500.0, 1.0e-7, 5.0, 100.0)
        self.assertTrue(window["feasible"])
        self.assertAlmostEqual(window["minimum_ohm"], 3.0e5)
        self.assertLess(window["minimum_ohm"], window["maximum_ohm"])

    def test_lower_bound_follows_the_current_limit(self):
        tight = logic.bleed_resistance_window_ohm(
            1500.0, 1.0e-7, 5.0, 100.0, current_limit_a=1.0e-3
        )
        self.assertAlmostEqual(tight["minimum_ohm"], 1.5e6)

    def test_upper_bound_follows_the_available_dwell(self):
        slow = logic.bleed_resistance_window_ohm(1500.0, 1.0e-7, 10.0, 100.0)
        quick = logic.bleed_resistance_window_ohm(1500.0, 1.0e-7, 5.0, 100.0)
        self.assertAlmostEqual(slow["maximum_ohm"] / quick["maximum_ohm"], 2.0)

    def test_a_dwell_too_short_for_any_resistor_is_infeasible(self):
        window = logic.bleed_resistance_window_ohm(1500.0, 1.0e-7, 0.001, 100.0)
        self.assertFalse(window["feasible"])
        self.assertGreater(window["minimum_ohm"], window["maximum_ohm"])

    def test_rejects_a_target_at_or_above_the_initial_potential(self):
        with self.assertRaises(ValueError):
            logic.bleed_resistance_window_ohm(100.0, 1.0e-7, 5.0, 100.0)

    def test_rejects_a_zero_current_limit(self):
        with self.assertRaises(ValueError):
            logic.bleed_resistance_window_ohm(
                1500.0, 1.0e-7, 5.0, 100.0, current_limit_a=0.0
            )


class TestProvisionQualification(unittest.TestCase):
    def test_nominal_provision_qualifies(self):
        verdict = logic.qualify_provision(nominal_provisions()[0])
        self.assertTrue(verdict["qualified"])
        self.assertEqual(verdict["findings"], [])
        self.assertEqual(verdict["style"], "grounding-stud")

    def test_flags_a_bond_above_the_allowance(self):
        record = nominal_provisions()[0]
        record["bond_to_structure_mohm"] = 14.0
        verdict = logic.qualify_provision(record)
        self.assertIn(
            "provision-bond-to-structure-exceeds-allowance", verdict["findings"]
        )

    def test_bond_exactly_on_the_allowance_is_accepted(self):
        record = nominal_provisions()[0]
        record["bond_to_structure_mohm"] = logic.PROVISION_BOND_ALLOWANCE_MOHM
        verdict = logic.qualify_provision(record)
        self.assertEqual(verdict["findings"], [])

    def test_flags_a_lead_with_no_current_limiting_resistance(self):
        record = nominal_provisions()[0]
        record["bleed_resistance_ohm"] = 0.0
        verdict = logic.qualify_provision(record)
        self.assertIn(
            "provision-lacks-current-limiting-bleed-resistance", verdict["findings"]
        )

    def test_flags_an_unmarked_provision(self):
        record = nominal_provisions()[1]
        record["marking_present"] = False
        verdict = logic.qualify_provision(record)
        self.assertIn("provision-not-marked-for-the-operator", verdict["findings"])

    def test_flags_a_provision_reachable_in_no_configuration(self):
        record = nominal_provisions()[1]
        record["reachable_configurations"] = []
        verdict = logic.qualify_provision(record)
        self.assertIn("provision-has-no-reachable-configuration", verdict["findings"])

    def test_rejects_an_uncategorized_attachment_style(self):
        record = nominal_provisions()[0]
        record["style"] = "crocodile-clip"
        with self.assertRaises(ValueError):
            logic.qualify_provision(record)

    def test_rejects_a_negative_bond_resistance(self):
        record = nominal_provisions()[0]
        record["bond_to_structure_mohm"] = -1.0
        with self.assertRaises(ValueError):
            logic.qualify_provision(record)

    def test_rejects_a_non_boolean_marking_flag(self):
        record = nominal_provisions()[0]
        record["marking_present"] = "yes"
        with self.assertRaises(ValueError):
            logic.qualify_provision(record)

    def test_rejects_a_non_sequence_configuration_set(self):
        record = nominal_provisions()[0]
        record["reachable_configurations"] = "hoist-and-mate"
        with self.assertRaises(ValueError):
            logic.qualify_provision(record)

    def test_rejects_a_record_without_id(self):
        record = nominal_provisions()[0]
        del record["id"]
        with self.assertRaises(ValueError):
            logic.qualify_provision(record)

    def test_rejects_a_non_mapping_record(self):
        with self.assertRaises(ValueError):
            logic.qualify_provision("gnd-stud-forward-ring")


class TestCatalogue(unittest.TestCase):
    def test_catalogue_is_indexed_by_identifier(self):
        catalogue = nominal_catalogue()
        self.assertEqual(sorted(catalogue), ["gnd-stud-forward-ring", "jack-aft-bulkhead"])

    def test_rejects_a_duplicate_provision_id(self):
        records = nominal_provisions()
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            logic.build_provision_catalogue(records)

    def test_rejects_an_empty_provision_set(self):
        with self.assertRaises(ValueError):
            logic.build_provision_catalogue([])


class TestOperationEvaluation(unittest.TestCase):
    def test_nominal_operation_is_compliant(self):
        verdict = logic.evaluate_operation(nominal_operations()[0], nominal_catalogue())
        self.assertTrue(verdict["compliant"])
        self.assertAlmostEqual(verdict["time_constant_s"], 0.1)
        self.assertAlmostEqual(verdict["residual_threshold_v"], 100.0)
        self.assertAlmostEqual(verdict["peak_current_a"], 1.5e-3)
        self.assertLess(verdict["residual_potential_v"], 100.0)

    def test_required_dwell_is_reported_for_a_charged_item(self):
        verdict = logic.evaluate_operation(nominal_operations()[0], nominal_catalogue())
        self.assertAlmostEqual(verdict["required_dwell_s"], 0.1 * math.log(15.0))
        self.assertTrue(verdict["bleed_resistance_window_ohm"]["feasible"])

    def test_flags_a_provision_unreachable_in_the_configuration(self):
        record = nominal_operations()[1]
        record["configuration"] = "transport-container-open"
        verdict = logic.evaluate_operation(record, nominal_catalogue())
        self.assertIn(
            "provision-not-reachable-in-operation-configuration", verdict["findings"]
        )

    def test_flags_a_dwell_too_short_for_the_residual_threshold(self):
        record = nominal_operations()[0]
        record["dwell_s"] = 0.05
        verdict = logic.evaluate_operation(record, nominal_catalogue())
        self.assertIn(
            "equalization-dwell-too-short-for-residual-threshold", verdict["findings"]
        )
        self.assertGreater(verdict["residual_potential_v"], 100.0)

    def test_flags_a_peak_current_above_the_soft_ground_limit(self):
        provisions = nominal_provisions()
        provisions[0]["bleed_resistance_ohm"] = logic.MIN_BLEED_RESISTANCE_OHM
        catalogue = logic.build_provision_catalogue(provisions)
        verdict = logic.evaluate_operation(nominal_operations()[0], catalogue)
        self.assertIn("peak-equalization-current-above-limit", verdict["findings"])
        self.assertAlmostEqual(verdict["peak_current_a"], 1.5e-2)

    def test_flags_an_operation_with_no_feasible_resistance_window(self):
        record = nominal_operations()[0]
        record["dwell_s"] = 0.001
        verdict = logic.evaluate_operation(record, nominal_catalogue())
        self.assertIn("no-feasible-bleed-resistance-window", verdict["findings"])
        self.assertFalse(verdict["bleed_resistance_window_ohm"]["feasible"])

    def test_dwell_exactly_at_the_required_value_is_compliant(self):
        provisions = nominal_provisions()
        catalogue = logic.build_provision_catalogue(provisions)
        initial = 2000.0
        capacitance = 5.0e-8
        resistance = provisions[0]["bleed_resistance_ohm"]
        threshold = logic.residual_threshold_v("category-1b")
        dwell = logic.required_dwell_s(initial, threshold, resistance, capacitance)
        # The decay evaluated at this logarithm-derived dwell lands a few units
        # in the last place above the threshold although it physically sits on
        # it; the comparison tolerance absorbs that without moving the
        # threshold or lengthening the required dwell.
        self.assertGreater(
            logic.residual_potential_v(initial, resistance, capacitance, dwell),
            threshold,
        )
        record = {
            "id": "op-boundary-equalization",
            "provision_id": "gnd-stud-forward-ring",
            "configuration": "hoist-and-mate",
            "initial_potential_v": initial,
            "item_capacitance_f": capacitance,
            "dwell_s": dwell,
            "susceptibility_category": "category-1b",
        }
        verdict = logic.evaluate_operation(record, catalogue)
        self.assertEqual(verdict["findings"], [])
        self.assertTrue(verdict["compliant"])

    def test_tolerance_does_not_widen_the_residual_threshold(self):
        self.assertTrue(logic._within(100.0, 100.0))
        self.assertFalse(logic._within(100.001, 100.0))
        self.assertFalse(logic._within(5.1e-3, logic.MAX_EQUALIZATION_CURRENT_A))

    def test_rejects_an_operation_naming_an_unknown_provision(self):
        record = nominal_operations()[0]
        record["provision_id"] = "stud-that-is-not-there"
        with self.assertRaises(ValueError):
            logic.evaluate_operation(record, nominal_catalogue())

    def test_rejects_an_operation_without_a_configuration(self):
        record = nominal_operations()[0]
        del record["configuration"]
        with self.assertRaises(ValueError):
            logic.evaluate_operation(record, nominal_catalogue())

    def test_rejects_an_operation_with_zero_item_capacitance(self):
        record = nominal_operations()[0]
        record["item_capacitance_f"] = 0.0
        with self.assertRaises(ValueError):
            logic.evaluate_operation(record, nominal_catalogue())

    def test_rejects_an_empty_catalogue(self):
        with self.assertRaises(ValueError):
            logic.evaluate_operation(nominal_operations()[0], {})

    def test_rejects_a_non_mapping_operation(self):
        with self.assertRaises(ValueError):
            logic.evaluate_operation("op-array-panel-handling", nominal_catalogue())


class TestAssessment(unittest.TestCase):
    def test_nominal_provision_set_is_compliant(self):
        report = logic.assess_ground_connection_provisions(
            nominal_provisions(), nominal_operations()
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["operation_count"], 2)
        self.assertLess(report["worst_residual_v"], 100.0)

    def test_provision_findings_are_prefixed_with_the_provision_id(self):
        provisions = nominal_provisions()
        provisions[1]["marking_present"] = False
        report = logic.assess_ground_connection_provisions(
            provisions, nominal_operations()
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "jack-aft-bulkhead: provision-not-marked-for-the-operator",
            report["findings"],
        )

    def test_operation_findings_are_prefixed_with_the_operation_id(self):
        operations = nominal_operations()
        operations[0]["dwell_s"] = 0.05
        report = logic.assess_ground_connection_provisions(
            nominal_provisions(), operations
        )
        self.assertFalse(report["compliant"])
        self.assertIn(
            "op-array-panel-handling: "
            "equalization-dwell-too-short-for-residual-threshold",
            report["findings"],
        )

    def test_provision_set_with_no_operation_reports_no_residual(self):
        report = logic.assess_ground_connection_provisions(nominal_provisions(), [])
        self.assertIsNone(report["worst_residual_v"])
        self.assertTrue(report["compliant"])

    def test_rejects_a_non_sequence_operation_set(self):
        with self.assertRaises(ValueError):
            logic.assess_ground_connection_provisions(
                nominal_provisions(), "op-array-panel-handling"
            )


class TestSummary(unittest.TestCase):
    def test_summary_reports_verdict_and_counts(self):
        report = logic.assess_ground_connection_provisions(
            nominal_provisions(), nominal_operations()
        )
        text = logic.summarize_assessment(report)
        self.assertIn("COMPLIANT", text)
        self.assertIn("2 provision(s)", text)
        self.assertIn("2 operation(s)", text)

    def test_summary_rejects_a_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_assessment({"operations": []})


if __name__ == "__main__":
    unittest.main()
