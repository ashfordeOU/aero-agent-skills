"""Contract tests for the clause 4.17 dependability and AIT logic."""

import unittest

from e3311_product_assurance_dependability_ait_logic import (
    MAX_STAGES,
    RELIABILITY_TOLERANCE,
    apportion_stage_target,
    assess_product_assurance,
    critical_items_findings,
    single_point_stages,
    stage_reliability,
    train_reliability,
    validate_ait_flow,
    validate_reliability,
    validate_stage,
)


def stage(stage_id="S1", elements=(0.999,), criticality=1):
    return {"stage_id": stage_id, "elements": list(elements), "criticality": criticality}


def operation(operation_id="OP", **overrides):
    base = {
        "operation_id": operation_id,
        "installs_live_device": False,
        "requires_inert_vehicle": False,
        "powered": False,
        "inhibit_fitted": False,
        "esd_controlled_area": False,
    }
    base.update(overrides)
    return base


def flow():
    return [
        operation("OP1", requires_inert_vehicle=True),
        operation("OP2", requires_inert_vehicle=True, powered=True),
        operation("OP3", installs_live_device=True, esd_controlled_area=True),
        operation("OP4", powered=True, inhibit_fitted=True),
    ]


def good_spec(**overrides):
    spec = {
        "stages": [
            stage("initiator", (0.999, 0.999), 1),
            stage("transfer-line", (0.9999,), 1),
            stage("separation-nut", (0.9995,), 1),
        ],
        "system_target": 0.995,
        "critical_items": ["transfer-line", "separation-nut"],
        "ait_flow": flow(),
    }
    spec.update(overrides)
    return spec


class ReliabilityGuardTests(unittest.TestCase):
    def test_reliability_of_one_is_allowed(self):
        self.assertEqual(validate_reliability("r", 1.0), 1.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability("r", 0.0)

    def test_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability("r", 1.2)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_reliability("r", True)

    def test_stage_needs_elements(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage_id": "S", "elements": [], "criticality": 1})

    def test_criticality_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage_id": "S", "elements": [0.9], "criticality": 7})

    def test_blank_stage_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage({"stage_id": "  ", "elements": [0.9], "criticality": 1})


class StageReliabilityTests(unittest.TestCase):
    def test_single_element_stage_is_its_element(self):
        self.assertAlmostEqual(stage_reliability([0.99]), 0.99, places=9)

    def test_two_parallel_elements_multiply_the_failure_probabilities(self):
        self.assertAlmostEqual(stage_reliability([0.9, 0.9]), 0.99, places=9)

    def test_redundancy_never_reduces_reliability(self):
        single = stage_reliability([0.9])
        double = stage_reliability([0.9, 0.9])
        self.assertGreater(double, single)

    def test_a_perfect_element_makes_the_stage_certain(self):
        self.assertAlmostEqual(stage_reliability([1.0, 0.5]), 1.0, places=9)

    def test_empty_stage_rejected(self):
        with self.assertRaises(ValueError):
            stage_reliability([])


class TrainTests(unittest.TestCase):
    def test_series_stages_multiply(self):
        result = train_reliability([stage("A", (0.9,), 1), stage("B", (0.8,), 1)])
        self.assertAlmostEqual(result["reliability"], 0.72, places=9)

    def test_breakdown_reports_each_stage(self):
        result = train_reliability([stage("A", (0.9,), 1), stage("B", (0.8, 0.8), 2)])
        self.assertEqual([s["stage_id"] for s in result["stages"]], ["A", "B"])
        self.assertEqual(result["stages"][1]["element_count"], 2)

    def test_duplicate_stage_id_rejected(self):
        with self.assertRaises(ValueError):
            train_reliability([stage("A"), stage("A")])

    def test_empty_train_rejected(self):
        with self.assertRaises(ValueError):
            train_reliability([])

    def test_train_longer_than_the_model_rejected(self):
        long_train = [stage("S%d" % i, (0.999,), 1) for i in range(MAX_STAGES + 1)]
        with self.assertRaises(ValueError):
            train_reliability(long_train)


class ApportionmentTests(unittest.TestCase):
    def test_single_stage_owns_the_whole_target(self):
        self.assertAlmostEqual(apportion_stage_target(0.99, 1), 0.99, places=9)

    def test_two_stages_each_own_the_square_root(self):
        share = apportion_stage_target(0.81, 2)
        self.assertAlmostEqual(share, 0.9, places=9)

    def test_apportioned_shares_multiply_back_to_the_target(self):
        share = apportion_stage_target(0.995, 4)
        self.assertAlmostEqual(share ** 4, 0.995, places=9)

    def test_zero_stages_rejected(self):
        with self.assertRaises(ValueError):
            apportion_stage_target(0.99, 0)

    def test_non_integer_stage_count_rejected(self):
        with self.assertRaises(ValueError):
            apportion_stage_target(0.99, 2.0)


class CriticalItemTests(unittest.TestCase):
    def test_single_element_stages_are_single_point_failures(self):
        found = single_point_stages([stage("A", (0.9,), 1), stage("B", (0.9, 0.9), 1)])
        self.assertEqual([s["stage_id"] for s in found], ["A"])

    def test_declared_single_point_stage_is_complete(self):
        result = critical_items_findings([stage("A", (0.9,), 1)], ["A"])
        self.assertTrue(result["complete"])

    def test_undeclared_single_point_stage_is_a_finding(self):
        result = critical_items_findings([stage("A", (0.9,), 1)], [])
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_from_list"], ["A"])

    def test_low_criticality_stage_need_not_be_listed(self):
        result = critical_items_findings([stage("A", (0.9,), 4)], [])
        self.assertTrue(result["complete"])

    def test_declared_list_must_hold_strings(self):
        with self.assertRaises(ValueError):
            critical_items_findings([stage("A", (0.9,), 1)], [7])


class AitFlowTests(unittest.TestCase):
    def test_late_installation_flow_is_valid(self):
        result = validate_ait_flow(flow())
        self.assertTrue(result["valid"])
        self.assertEqual(result["operations_after_install"], 1)

    def test_inert_operation_after_installation_is_a_finding(self):
        steps = flow()
        steps.append(operation("OP5", requires_inert_vehicle=True))
        result = validate_ait_flow(steps)
        self.assertFalse(result["valid"])
        self.assertTrue(any("inert vehicle" in f for f in result["findings"]))

    def test_powered_operation_without_the_inhibit_is_a_finding(self):
        steps = flow()
        steps[3] = operation("OP4", powered=True, inhibit_fitted=False)
        result = validate_ait_flow(steps)
        self.assertFalse(result["valid"])
        self.assertTrue(any("inhibit" in f for f in result["findings"]))

    def test_installation_outside_a_controlled_area_is_a_finding(self):
        steps = flow()
        steps[2] = operation("OP3", installs_live_device=True, esd_controlled_area=False)
        result = validate_ait_flow(steps)
        self.assertFalse(result["valid"])

    def test_a_flow_that_never_installs_the_device_is_invalid(self):
        result = validate_ait_flow([operation("OP1")])
        self.assertFalse(result["valid"])
        self.assertIsNone(result["install_position"])

    def test_two_installations_are_a_finding(self):
        steps = flow()
        steps.append(operation("OP5", installs_live_device=True, esd_controlled_area=True))
        result = validate_ait_flow(steps)
        self.assertFalse(result["valid"])

    def test_duplicate_operation_id_rejected(self):
        steps = flow()
        steps[1] = dict(steps[1], operation_id="OP1")
        with self.assertRaises(ValueError):
            validate_ait_flow(steps)

    def test_non_boolean_field_rejected(self):
        steps = flow()
        steps[0] = dict(steps[0], powered="no")
        with self.assertRaises(ValueError):
            validate_ait_flow(steps)


class AssessmentTests(unittest.TestCase):
    def test_clean_design_is_acceptable(self):
        result = assess_product_assurance(good_spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_target_shortfall_is_a_finding(self):
        result = assess_product_assurance(good_spec(system_target=0.99999))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("falls short" in f for f in result["findings"]))

    def test_a_target_the_train_meets_exactly_is_accepted(self):
        spec = good_spec(
            stages=[stage("A", (0.9,), 3), stage("B", (0.8,), 3)],
            critical_items=[],
            system_target=0.9 * 0.8,
        )
        del spec["ait_flow"]
        result = assess_product_assurance(spec)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["achieved_reliability"], 0.72, places=9)

    def test_undeclared_single_point_stage_sinks_the_assessment(self):
        result = assess_product_assurance(good_spec(critical_items=[]))
        self.assertFalse(result["acceptable"])

    def test_weak_stages_are_named_against_the_apportionment(self):
        spec = good_spec(
            stages=[stage("A", (0.5,), 3), stage("B", (0.999,), 3)],
            critical_items=[],
            system_target=0.9,
        )
        del spec["ait_flow"]
        result = assess_product_assurance(spec)
        self.assertIn("A", result["stages_below_apportionment"])

    def test_bad_flow_sinks_the_assessment(self):
        spec = good_spec()
        spec["ait_flow"] = flow() + [operation("OP9", requires_inert_vehicle=True)]
        self.assertFalse(assess_product_assurance(spec)["acceptable"])

    def test_missing_key_rejected(self):
        spec = good_spec()
        del spec["system_target"]
        with self.assertRaises(ValueError):
            assess_product_assurance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_product_assurance(["stages"])

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(RELIABILITY_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
