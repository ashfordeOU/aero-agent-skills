"""Contract tests for the clause 4.1.5 ground support equipment component logic."""

import unittest

from q6013_class_1_gse_components_logic import (
    BARRIER_ATTENUATION,
    CONTROL_CATEGORIES,
    MARGIN_TOLERANCE,
    assess_gse_commercial_parts,
    control_category,
    credited_attenuation,
    effective_injection_w,
    evaluate_gse_part,
    interface_margin,
    validate_identifier,
    worst_case_injection_w,
)

INTERFACES = {"UMB-PWR": 50.0, "UMB-TM": 0.5}


def part(**overrides):
    """Return a connected ground support part with optional overrides."""
    base = {
        "part_id": "GSE-001",
        "flight_connected": True,
        "interface_id": "UMB-PWR",
        "supply_voltage_v": 28.0,
        "current_limit_a": 0.5,
        "barrier_type": "series-resistor",
        "barrier_qualified": True,
    }
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_space(self):
        self.assertEqual(validate_identifier(" UMB-PWR ", "interface_id"), "UMB-PWR")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("  ", "interface_id")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(None, "part_id")


class WorstCaseInjectionTests(unittest.TestCase):
    def test_power_is_voltage_times_current_limit(self):
        self.assertAlmostEqual(worst_case_injection_w(28.0, 0.5), 14.0, places=9)

    def test_raising_the_current_limit_raises_the_injection(self):
        low = worst_case_injection_w(28.0, 0.5)
        high = worst_case_injection_w(28.0, 2.0)
        self.assertAlmostEqual(high / low, 4.0, places=9)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_injection_w(28.0, 0.0)

    def test_negative_voltage_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_injection_w(-28.0, 0.5)

    def test_boolean_voltage_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_injection_w(True, 0.5)


class CreditedAttenuationTests(unittest.TestCase):
    def test_qualified_barrier_is_credited(self):
        self.assertAlmostEqual(credited_attenuation("opto-isolator", True), 1000.0, places=9)

    def test_unqualified_barrier_is_credited_nothing(self):
        self.assertAlmostEqual(credited_attenuation("opto-isolator", False), 1.0, places=9)

    def test_absent_barrier_is_unity_whatever_the_flag(self):
        self.assertAlmostEqual(credited_attenuation("none", True), 1.0, places=9)

    def test_lookup_is_case_insensitive(self):
        self.assertAlmostEqual(credited_attenuation("Series-Resistor", True), 20.0, places=9)

    def test_unknown_barrier_rejected(self):
        with self.assertRaises(ValueError):
            credited_attenuation("gaffer-tape", True)

    def test_non_boolean_qualification_rejected(self):
        with self.assertRaises(ValueError):
            credited_attenuation("opto-isolator", "yes")

    def test_every_known_barrier_is_at_least_unity(self):
        for value in BARRIER_ATTENUATION.values():
            self.assertGreaterEqual(value, 1.0)


class EffectiveInjectionTests(unittest.TestCase):
    def test_attenuation_divides_the_injection(self):
        self.assertAlmostEqual(effective_injection_w(20.0, 20.0), 1.0, places=9)

    def test_unity_attenuation_passes_everything(self):
        self.assertAlmostEqual(effective_injection_w(14.0, 1.0), 14.0, places=9)

    def test_attenuation_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            effective_injection_w(14.0, 0.5)


class InterfaceMarginTests(unittest.TestCase):
    def test_margin_is_limit_over_arriving_power(self):
        self.assertAlmostEqual(interface_margin(50.0, 10.0), 5.0, places=9)

    def test_margin_below_unity_when_injection_exceeds_the_limit(self):
        self.assertAlmostEqual(interface_margin(0.5, 1.0), 0.5, places=9)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            interface_margin(0.0, 1.0)


class ControlCategoryTests(unittest.TestCase):
    def test_unconnected_part_keeps_ordinary_ground_control(self):
        self.assertEqual(control_category(False, 0.01, 2.0), "gse-standard-control")

    def test_sufficient_margin_is_declared_with_protection(self):
        self.assertEqual(control_category(True, 5.0, 2.0), "declared-with-protection")

    def test_insufficient_margin_demands_flight_equivalent_control(self):
        self.assertEqual(control_category(True, 1.2, 2.0), "flight-equivalent-control")

    def test_exactly_met_margin_is_met(self):
        self.assertEqual(control_category(True, 2.0, 2.0), "declared-with-protection")

    def test_non_boolean_connection_rejected(self):
        with self.assertRaises(ValueError):
            control_category("yes", 5.0, 2.0)

    def test_categories_are_the_declared_set(self):
        self.assertEqual(len(CONTROL_CATEGORIES), 3)


class EvaluateGsePartTests(unittest.TestCase):
    def test_protected_part_clears_the_power_interface(self):
        record = evaluate_gse_part(part(), INTERFACES, 2.0)
        self.assertAlmostEqual(record["worst_case_injection_w"], 14.0, places=9)
        self.assertAlmostEqual(record["effective_injection_w"], 0.7, places=9)
        self.assertAlmostEqual(record["margin"], 50.0 / 0.7, places=9)
        self.assertEqual(record["category"], "declared-with-protection")

    def test_same_part_fails_the_sensitive_telemetry_interface(self):
        record = evaluate_gse_part(part(interface_id="UMB-TM"), INTERFACES, 2.0)
        self.assertEqual(record["category"], "flight-equivalent-control")

    def test_unqualified_barrier_loses_its_credit_and_is_noted(self):
        record = evaluate_gse_part(part(barrier_qualified=False), INTERFACES, 2.0)
        self.assertAlmostEqual(record["credited_attenuation"], 1.0, places=9)
        self.assertAlmostEqual(record["effective_injection_w"], 14.0, places=9)
        self.assertTrue(any("not qualified" in note for note in record["notes"]))

    def test_unconnected_part_needs_no_electrical_data(self):
        record = evaluate_gse_part(
            {"part_id": "GSE-009", "flight_connected": False}, INTERFACES, 2.0
        )
        self.assertEqual(record["category"], "gse-standard-control")
        self.assertIsNone(record["margin"])

    def test_bare_part_is_noted_as_sitting_on_the_interface(self):
        record = evaluate_gse_part(
            part(barrier_type="none", barrier_qualified=False), INTERFACES, 2.0
        )
        self.assertTrue(any("no barrier" in note for note in record["notes"]))

    def test_undeclared_interface_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(part(interface_id="UMB-XX"), INTERFACES, 2.0)

    def test_missing_part_id_rejected(self):
        broken = part()
        del broken["part_id"]
        with self.assertRaises(ValueError):
            evaluate_gse_part(broken, INTERFACES, 2.0)

    def test_missing_connection_flag_rejected(self):
        broken = part()
        del broken["flight_connected"]
        with self.assertRaises(ValueError):
            evaluate_gse_part(broken, INTERFACES, 2.0)

    def test_empty_interface_map_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(part(), {}, 2.0)


class AssessGseCommercialPartsTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "parts": [part(), {"part_id": "GSE-002", "flight_connected": False}],
            "interfaces": INTERFACES,
        }
        base.update(overrides)
        return base

    def test_protected_bench_is_accepted(self):
        result = assess_gse_commercial_parts(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["category_counts"]["gse-standard-control"], 1)

    def test_one_exposed_part_escalates_the_whole_bench(self):
        spec = self._spec(
            parts=[part(), part(part_id="GSE-003", interface_id="UMB-TM")]
        )
        result = assess_gse_commercial_parts(spec)
        self.assertEqual(result["verdict"], "escalate")
        self.assertEqual(result["category_counts"]["flight-equivalent-control"], 1)

    def test_governing_part_is_the_lowest_margin(self):
        spec = self._spec(
            parts=[part(), part(part_id="GSE-003", interface_id="UMB-TM")]
        )
        result = assess_gse_commercial_parts(spec)
        self.assertEqual(result["governing_part"]["part_id"], "GSE-003")

    def test_governing_tie_breaks_on_the_part_identifier(self):
        spec = self._spec(parts=[part(part_id="GSE-050"), part(part_id="GSE-004")])
        result = assess_gse_commercial_parts(spec)
        self.assertEqual(result["governing_part"]["part_id"], "GSE-004")

    def test_no_connected_part_leaves_no_governing_part(self):
        spec = self._spec(parts=[{"part_id": "GSE-002", "flight_connected": False}])
        result = assess_gse_commercial_parts(spec)
        self.assertIsNone(result["governing_part"])
        self.assertEqual(result["verdict"], "accept")

    def test_findings_rank_the_exposed_part_first(self):
        spec = self._spec(
            parts=[
                part(part_id="GSE-001", barrier_type="none", barrier_qualified=False),
                part(part_id="GSE-003", interface_id="UMB-TM"),
            ]
        )
        result = assess_gse_commercial_parts(spec)
        self.assertEqual(result["findings"][0]["severity"], 0)
        self.assertEqual(result["findings"][0]["part_id"], "GSE-003")

    def test_raising_the_required_margin_can_flip_the_verdict(self):
        loose = assess_gse_commercial_parts(self._spec(required_margin=2.0))
        tight = assess_gse_commercial_parts(self._spec(required_margin=1000.0))
        self.assertEqual(loose["verdict"], "accept")
        self.assertEqual(tight["verdict"], "escalate")

    def test_missing_interfaces_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_commercial_parts({"parts": [part()]})

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_commercial_parts(self._spec(parts=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_commercial_parts(["parts"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
