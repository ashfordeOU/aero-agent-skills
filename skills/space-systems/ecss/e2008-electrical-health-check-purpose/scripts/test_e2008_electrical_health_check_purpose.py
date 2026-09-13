#!/usr/bin/env python3
"""Contract test for the electrical health assessment purpose (offline)."""

import copy
import unittest

from e2008_electrical_health_check_purpose_logic import (
    CHECK_KINDS,
    DEFAULT_HEALTH_CRITERIA,
    DEGRADED,
    FAILED,
    HEALTHY,
    INDETERMINATE,
    assess_bypass_diode,
    assess_check,
    assess_continuity,
    assess_grounding_bond,
    assess_insulation,
    assess_polarity,
    discrimination_ratio,
    evaluate_electrical_health,
    validate_health_criteria,
)


def _continuity(**overrides):
    check = {
        "id": "C1",
        "kind": "continuity",
        "target": "P1",
        "expected_resistance_ohm": 1.0,
        "measured_resistance_ohm": 1.05,
        "resolution_ohm": 0.005,
    }
    check.update(overrides)
    return check


def _insulation(**overrides):
    check = {
        "id": "I1",
        "kind": "insulation-resistance",
        "target": "B1",
        "measured_resistance_ohm": 5.0e9,
        "applied_voltage_v": 500.0,
        "rated_voltage_v": 500.0,
    }
    check.update(overrides)
    return check


def _diode(**overrides):
    check = {
        "id": "D1",
        "kind": "bypass-diode-function",
        "target": "P1",
        "forward_drop_v": 0.6,
        "reverse_leakage_a": 1.0e-7,
    }
    check.update(overrides)
    return check


def _bond(**overrides):
    check = {
        "id": "G1",
        "kind": "grounding-bond",
        "target": "P1",
        "measured_resistance_ohm": 0.02,
        "resolution_ohm": 0.002,
    }
    check.update(overrides)
    return check


def _assembly(checks, paths=("P1",), barriers=("B1",), **overrides):
    assembly = {
        "assembly_id": "PVA-01",
        "declared_paths": list(paths),
        "declared_barriers": list(barriers),
        "checks": checks,
    }
    assembly.update(overrides)
    return assembly


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_health_criteria(DEFAULT_HEALTH_CRITERIA), DEFAULT_HEALTH_CRITERIA
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_health_criteria("default")

    def test_missing_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_HEALTH_CRITERIA)
        del broken["min_insulation_resistance_ohm"]
        with self.assertRaises(ValueError):
            validate_health_criteria(broken)

    def test_tolerance_of_one_accepts_an_open_circuit_and_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_HEALTH_CRITERIA)
        broken["continuity_tolerance_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_health_criteria(broken)

    def test_inverted_diode_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_HEALTH_CRITERIA)
        broken["min_diode_forward_drop_v"] = 1.5
        with self.assertRaises(ValueError):
            validate_health_criteria(broken)

    def test_resolution_ratio_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_HEALTH_CRITERIA)
        broken["min_resolution_ratio"] = 0.5
        with self.assertRaises(ValueError):
            validate_health_criteria(broken)


class DiscriminationTests(unittest.TestCase):
    def test_ratio_counts_instrument_steps_inside_the_band(self):
        self.assertAlmostEqual(discrimination_ratio(0.2, 0.01), 20.0, places=9)

    def test_zero_resolution_rejected(self):
        with self.assertRaises(ValueError):
            discrimination_ratio(0.2, 0.0)

    def test_non_numeric_band_rejected(self):
        with self.assertRaises(ValueError):
            discrimination_ratio("0.2", 0.01)


class ContinuityTests(unittest.TestCase):
    def test_path_inside_the_band_is_healthy(self):
        result = assess_continuity(_continuity())
        self.assertEqual(result["outcome"], HEALTHY)
        self.assertTrue(result["discriminating"])

    def test_deviation_exactly_on_the_band_edge_is_healthy(self):
        result = assess_continuity(_continuity(measured_resistance_ohm=1.2))
        self.assertAlmostEqual(
            result["deviation_ohm"], result["accept_band_ohm"], places=9
        )
        self.assertEqual(result["outcome"], HEALTHY)

    def test_a_joint_carrying_extra_resistance_is_degraded(self):
        result = assess_continuity(_continuity(measured_resistance_ohm=1.3))
        self.assertEqual(result["outcome"], DEGRADED)

    def test_an_open_path_fails(self):
        result = assess_continuity(_continuity(measured_resistance_ohm=40.0))
        self.assertEqual(result["outcome"], FAILED)

    def test_a_coarse_instrument_cannot_certify_a_healthy_path(self):
        result = assess_continuity(_continuity(resolution_ohm=0.5))
        self.assertEqual(result["outcome"], INDETERMINATE)
        self.assertFalse(result["discriminating"])
        self.assertTrue(
            any("would not have shown" in reason for reason in result["reasons"])
        )

    def test_a_coarse_instrument_still_reports_a_defect_it_could_see(self):
        result = assess_continuity(
            _continuity(measured_resistance_ohm=40.0, resolution_ohm=0.5)
        )
        self.assertEqual(result["outcome"], FAILED)

    def test_resolution_exactly_at_the_ratio_discriminates(self):
        band = 1.0 * DEFAULT_HEALTH_CRITERIA["continuity_tolerance_fraction"]
        resolution = band / DEFAULT_HEALTH_CRITERIA["min_resolution_ratio"]
        result = assess_continuity(_continuity(resolution_ohm=resolution))
        self.assertAlmostEqual(
            result["discrimination_ratio"],
            DEFAULT_HEALTH_CRITERIA["min_resolution_ratio"],
            places=9,
        )
        self.assertTrue(result["discriminating"])
        self.assertEqual(result["outcome"], HEALTHY)

    def test_negative_measured_resistance_rejected(self):
        with self.assertRaises(ValueError):
            assess_continuity(_continuity(measured_resistance_ohm=-1.0))


class InsulationTests(unittest.TestCase):
    def test_a_sound_barrier_stressed_to_rating_is_healthy(self):
        result = assess_insulation(_insulation())
        self.assertEqual(result["outcome"], HEALTHY)
        self.assertTrue(result["stressed_to_rating"])

    def test_resistance_exactly_on_the_floor_is_healthy(self):
        floor = DEFAULT_HEALTH_CRITERIA["min_insulation_resistance_ohm"]
        result = assess_insulation(_insulation(measured_resistance_ohm=floor))
        self.assertAlmostEqual(result["measured_resistance_ohm"], floor, places=3)
        self.assertEqual(result["outcome"], HEALTHY)

    def test_a_barrier_on_its_way_down_is_degraded(self):
        result = assess_insulation(_insulation(measured_resistance_ohm=5.0e7))
        self.assertEqual(result["outcome"], DEGRADED)

    def test_a_bridged_barrier_fails(self):
        result = assess_insulation(_insulation(measured_resistance_ohm=1.0e3))
        self.assertEqual(result["outcome"], FAILED)

    def test_a_barrier_never_taken_to_its_rating_is_indeterminate(self):
        result = assess_insulation(_insulation(applied_voltage_v=50.0))
        self.assertEqual(result["outcome"], INDETERMINATE)
        self.assertFalse(result["stressed_to_rating"])

    def test_an_understressed_barrier_that_already_failed_still_fails(self):
        result = assess_insulation(
            _insulation(applied_voltage_v=50.0, measured_resistance_ohm=1.0e3)
        )
        self.assertEqual(result["outcome"], FAILED)

    def test_applied_voltage_exactly_at_rating_counts_as_stressed(self):
        result = assess_insulation(
            _insulation(applied_voltage_v=500.0, rated_voltage_v=500.0)
        )
        self.assertTrue(result["stressed_to_rating"])


class PolarityAndDiodeTests(unittest.TestCase):
    def test_matching_polarity_is_healthy(self):
        check = {
            "id": "PL1",
            "kind": "polarity",
            "target": "P1",
            "expected_polarity": "positive",
            "measured_polarity": "positive",
        }
        self.assertEqual(assess_polarity(check)["outcome"], HEALTHY)

    def test_reversed_polarity_fails(self):
        check = {
            "id": "PL1",
            "kind": "polarity",
            "target": "P1",
            "expected_polarity": "positive",
            "measured_polarity": "negative",
        }
        self.assertEqual(assess_polarity(check)["outcome"], FAILED)

    def test_unknown_polarity_token_rejected(self):
        check = {
            "id": "PL1",
            "kind": "polarity",
            "target": "P1",
            "expected_polarity": "positive",
            "measured_polarity": "reversed",
        }
        with self.assertRaises(ValueError):
            assess_polarity(check)

    def test_a_diode_in_its_window_is_healthy(self):
        self.assertEqual(assess_bypass_diode(_diode())["outcome"], HEALTHY)

    def test_a_shorted_diode_fails(self):
        self.assertEqual(
            assess_bypass_diode(_diode(forward_drop_v=0.05))["outcome"], FAILED
        )

    def test_a_diode_that_will_not_take_string_current_fails(self):
        self.assertEqual(
            assess_bypass_diode(_diode(forward_drop_v=2.0))["outcome"], FAILED
        )

    def test_mild_reverse_leakage_is_degraded(self):
        self.assertEqual(
            assess_bypass_diode(_diode(reverse_leakage_a=5.0e-5))["outcome"], DEGRADED
        )

    def test_heavy_reverse_leakage_fails(self):
        self.assertEqual(
            assess_bypass_diode(_diode(reverse_leakage_a=1.0e-2))["outcome"], FAILED
        )


class GroundingBondTests(unittest.TestCase):
    def test_a_low_resistance_bond_is_healthy(self):
        self.assertEqual(assess_grounding_bond(_bond())["outcome"], HEALTHY)

    def test_a_high_resistance_bond_fails(self):
        self.assertEqual(
            assess_grounding_bond(_bond(measured_resistance_ohm=5.0))["outcome"],
            FAILED,
        )

    def test_a_marginal_bond_is_degraded(self):
        self.assertEqual(
            assess_grounding_bond(_bond(measured_resistance_ohm=0.15))["outcome"],
            DEGRADED,
        )

    def test_a_coarse_bond_instrument_gives_an_indeterminate_pass(self):
        result = assess_grounding_bond(_bond(resolution_ohm=0.05))
        self.assertEqual(result["outcome"], INDETERMINATE)
        self.assertFalse(result["discriminating"])


class CheckRoutingTests(unittest.TestCase):
    def test_every_declared_kind_has_an_assessor(self):
        self.assertEqual(len(CHECK_KINDS), 5)

    def test_routing_carries_the_identity_through(self):
        result = assess_check(_continuity())
        self.assertEqual(result["id"], "C1")
        self.assertEqual(result["kind"], "continuity")
        self.assertEqual(result["target"], "P1")

    def test_unknown_check_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_check(_continuity(kind="megger-sweep"))

    def test_missing_required_field_rejected(self):
        check = _continuity()
        del check["resolution_ohm"]
        with self.assertRaises(ValueError):
            assess_check(check)

    def test_check_without_a_target_rejected(self):
        with self.assertRaises(ValueError):
            assess_check(_continuity(target="  "))


class AssemblyTests(unittest.TestCase):
    def test_a_fully_covered_sound_assembly_is_healthy(self):
        result = evaluate_electrical_health(_assembly([_continuity(), _insulation()]))
        self.assertEqual(result["outcome"], HEALTHY)
        self.assertTrue(result["assessment_complete"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_an_unmeasured_path_is_not_a_healthy_path(self):
        result = evaluate_electrical_health(
            _assembly([_continuity(), _insulation()], paths=("P1", "P2"))
        )
        self.assertEqual(result["outcome"], INDETERMINATE)
        self.assertEqual(result["uncovered_paths"], ["P2"])
        self.assertFalse(result["assessment_complete"])
        self.assertAlmostEqual(result["coverage_fraction"], 2.0 / 3.0, places=9)

    def test_an_unmeasured_barrier_is_reported_separately(self):
        result = evaluate_electrical_health(
            _assembly([_continuity(), _insulation()], barriers=("B1", "B2"))
        )
        self.assertEqual(result["uncovered_barriers"], ["B2"])
        self.assertTrue(
            any("current could still go" in finding for finding in result["findings"])
        )

    def test_a_diode_check_does_not_cover_a_path_for_continuity(self):
        result = evaluate_electrical_health(_assembly([_diode(), _insulation()]))
        self.assertEqual(result["uncovered_paths"], ["P1"])
        self.assertEqual(result["outcome"], INDETERMINATE)

    def test_a_failed_check_outranks_an_incomplete_assessment(self):
        checks = [_continuity(measured_resistance_ohm=40.0), _insulation()]
        result = evaluate_electrical_health(_assembly(checks, paths=("P1", "P2")))
        self.assertEqual(result["outcome"], FAILED)
        self.assertEqual(result["unhealthy_check_ids"], ["C1"])

    def test_indeterminate_checks_are_listed_by_identifier(self):
        checks = [_continuity(resolution_ohm=0.5), _insulation()]
        result = evaluate_electrical_health(_assembly(checks))
        self.assertEqual(result["indeterminate_check_ids"], ["C1"])
        self.assertEqual(result["outcome"], INDETERMINATE)

    def test_outcome_counts_add_up_to_the_check_count(self):
        checks = [_continuity(), _insulation(), _bond(), _diode()]
        result = evaluate_electrical_health(_assembly(checks))
        self.assertEqual(sum(result["outcome_counts"].values()), 4)

    def test_a_check_on_an_undeclared_target_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_electrical_health(_assembly([_continuity(target="P9")]))

    def test_duplicate_check_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_electrical_health(_assembly([_continuity(), _continuity()]))

    def test_repeated_declared_path_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_electrical_health(
                _assembly([_continuity()], paths=("P1", "P1"))
            )

    def test_an_assembly_with_nothing_to_cover_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_electrical_health(_assembly([], paths=(), barriers=()))

    def test_non_list_checks_rejected(self):
        assembly = _assembly([])
        assembly["checks"] = "none"
        with self.assertRaises(ValueError):
            evaluate_electrical_health(assembly)

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_electrical_health("PVA-01")


if __name__ == "__main__":
    unittest.main()
