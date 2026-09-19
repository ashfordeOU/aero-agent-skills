"""Contract tests for the clause 4.7.7.1-4.7.7.3 / 4.7.7.5 electrical design logic."""

import math
import unittest

from e3301_electrical_design_connectors_insulation_logic import (
    CIRCUIT_CLASSES,
    CURRENT_TOLERANCE,
    DEFAULT_DIELECTRIC_FACTOR,
    DEFAULT_DIELECTRIC_OFFSET_V,
    assess_electrical_design,
    bundle_derating_factor,
    contact_current_margin,
    contact_findings,
    cross_mating_findings,
    dielectric_findings,
    function_separation_findings,
    insulation_findings,
    required_dielectric_voltage,
    validate_connector,
)


def power_connector(**overrides):
    connector = {
        "id": "J1",
        "shell": "size-11",
        "insert": "13-pin",
        "keying": "normal",
        "total_contacts": 13,
        "circuits": [
            {"id": "MOTOR-A", "circuit_class": "power", "current_a": 1.2,
             "contact_rating_a": 5.0, "operating_v": 28.0, "contacts_used": 2},
            {"id": "MOTOR-B", "circuit_class": "power", "current_a": 1.2,
             "contact_rating_a": 5.0, "operating_v": 28.0, "contacts_used": 2},
        ],
    }
    connector.update(overrides)
    return connector


def signal_connector(**overrides):
    connector = {
        "id": "J2",
        "shell": "size-9",
        "insert": "9-pin",
        "keying": "position-b",
        "total_contacts": 9,
        "circuits": [
            {"id": "RESOLVER", "circuit_class": "signal", "current_a": 0.05,
             "contact_rating_a": 3.0, "operating_v": 5.0, "contacts_used": 4},
        ],
    }
    connector.update(overrides)
    return connector


IR_MEASUREMENTS = [
    {"id": "MOTOR-A-CASE", "measured_ohm": 5.0e8, "test_voltage_v": 500.0},
    {"id": "RESOLVER-CASE", "measured_ohm": 2.0e9, "test_voltage_v": 500.0},
]

HV_TESTS = [
    {"id": "MOTOR-A-CASE", "operating_v": 28.0, "applied_v": 1200.0, "leakage_a": 1.0e-5},
]


class ValidateConnectorTests(unittest.TestCase):
    def test_normalises_identifiers_and_counts(self):
        record = validate_connector(power_connector())
        self.assertEqual(record["id"], "J1")
        self.assertEqual(record["contacts_used"], 4)

    def test_every_recognised_class_validates(self):
        for family in CIRCUIT_CLASSES:
            connector = signal_connector(
                circuits=[{"id": "C", "circuit_class": family, "current_a": 0.1,
                           "contact_rating_a": 3.0, "operating_v": 5.0}]
            )
            self.assertEqual(validate_connector(connector)["circuits"][0]["circuit_class"],
                             family)

    def test_unknown_circuit_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(signal_connector(
                circuits=[{"id": "C", "circuit_class": "telepathy", "current_a": 0.1,
                           "contact_rating_a": 3.0, "operating_v": 5.0}]))

    def test_overallocated_shell_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(power_connector(total_contacts=3))

    def test_connector_without_circuits_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(power_connector(circuits=[]))

    def test_missing_key_rejected(self):
        connector = power_connector()
        del connector["keying"]
        with self.assertRaises(ValueError):
            validate_connector(connector)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector("J1")

    def test_zero_contact_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(signal_connector(
                circuits=[{"id": "C", "circuit_class": "signal", "current_a": 0.1,
                           "contact_rating_a": 0.0, "operating_v": 5.0}]))

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(signal_connector(
                circuits=[{"id": "C", "circuit_class": "signal", "current_a": -0.1,
                           "contact_rating_a": 3.0, "operating_v": 5.0}]))

    def test_zero_contacts_used_rejected(self):
        with self.assertRaises(ValueError):
            validate_connector(signal_connector(
                circuits=[{"id": "C", "circuit_class": "signal", "current_a": 0.1,
                           "contact_rating_a": 3.0, "operating_v": 5.0,
                           "contacts_used": 0}]))


class DeratingTests(unittest.TestCase):
    def test_empty_shell_keeps_the_full_rating(self):
        self.assertAlmostEqual(bundle_derating_factor(0, 10), 1.0, places=9)

    def test_full_shell_halves_the_rating(self):
        self.assertAlmostEqual(bundle_derating_factor(10, 10), 0.5, places=9)

    def test_half_full_shell_is_three_quarters(self):
        self.assertAlmostEqual(bundle_derating_factor(5, 10), 0.75, places=9)

    def test_occupancy_above_the_shell_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(11, 10)

    def test_zero_contact_shell_rejected(self):
        with self.assertRaises(ValueError):
            bundle_derating_factor(0, 0)

    def test_margin_is_the_fractional_headroom(self):
        self.assertAlmostEqual(contact_current_margin(2.0, 5.0, 0.8), 1.0, places=9)

    def test_unused_circuit_has_unbounded_margin(self):
        self.assertTrue(math.isinf(contact_current_margin(0.0, 5.0, 1.0)))

    def test_derating_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            contact_current_margin(1.0, 5.0, 1.2)

    def test_exact_boundary_margin_is_compliant(self):
        result = contact_findings(
            power_connector(
                total_contacts=16,
                circuits=[{"id": "M", "circuit_class": "power", "current_a": 3.0,
                           "contact_rating_a": 4.0, "operating_v": 28.0,
                           "contacts_used": 8}],
            ),
            0.0,
        )
        self.assertAlmostEqual(result["records"][0]["margin"], 0.0, places=9)
        self.assertTrue(result["records"][0]["compliant"])
        self.assertAlmostEqual(result["records"][0]["margin"], 0.0, places=12)
        self.assertAlmostEqual(CURRENT_TOLERANCE, 1e-12, places=15)

    def test_overloaded_contact_is_flagged(self):
        connector = power_connector(
            circuits=[{"id": "M", "circuit_class": "power", "current_a": 4.5,
                       "contact_rating_a": 5.0, "operating_v": 28.0, "contacts_used": 2}]
        )
        result = contact_findings(connector, 0.25)
        self.assertFalse(result["records"][0]["compliant"])
        self.assertTrue(any("contact current margin" in f for f in result["findings"]))

    def test_insufficient_spares_are_flagged(self):
        connector = power_connector(total_contacts=5)
        result = contact_findings(connector, 0.25)
        self.assertEqual(result["spare_contacts"], 1)
        self.assertTrue(any("spare contact" in f for f in result["findings"]))


class SeparationTests(unittest.TestCase):
    def test_distinct_connectors_do_not_cross_mate(self):
        self.assertEqual(cross_mating_findings([power_connector(), signal_connector()]), [])

    def test_identical_shell_insert_keying_is_flagged(self):
        twin = signal_connector(id="J3", shell="size-11", insert="13-pin", keying="normal")
        findings = cross_mating_findings([power_connector(), twin])
        self.assertEqual(len(findings), 1)

    def test_keying_difference_clears_the_hazard(self):
        twin = signal_connector(id="J3", shell="size-11", insert="13-pin", keying="position-c")
        self.assertEqual(cross_mating_findings([power_connector(), twin]), [])

    def test_duplicate_connector_id_rejected(self):
        with self.assertRaises(ValueError):
            cross_mating_findings([power_connector(), power_connector()])

    def test_empty_connector_set_rejected(self):
        with self.assertRaises(ValueError):
            cross_mating_findings([])

    def test_power_and_signal_in_one_shell_is_flagged(self):
        mixed = power_connector(
            circuits=[
                {"id": "M", "circuit_class": "power", "current_a": 1.0,
                 "contact_rating_a": 5.0, "operating_v": 28.0},
                {"id": "S", "circuit_class": "signal", "current_a": 0.01,
                 "contact_rating_a": 3.0, "operating_v": 5.0},
            ]
        )
        self.assertEqual(len(function_separation_findings([mixed])), 1)

    def test_pyrotechnic_with_signal_is_flagged(self):
        mixed = power_connector(
            circuits=[
                {"id": "P", "circuit_class": "pyrotechnic", "current_a": 5.0,
                 "contact_rating_a": 10.0, "operating_v": 28.0},
                {"id": "S", "circuit_class": "signal", "current_a": 0.01,
                 "contact_rating_a": 3.0, "operating_v": 5.0},
            ]
        )
        self.assertEqual(len(function_separation_findings([mixed])), 1)

    def test_screen_return_may_share_with_signal(self):
        shared = signal_connector(
            circuits=[
                {"id": "S", "circuit_class": "signal", "current_a": 0.01,
                 "contact_rating_a": 3.0, "operating_v": 5.0},
                {"id": "SCR", "circuit_class": "screen-return", "current_a": 0.0,
                 "contact_rating_a": 3.0, "operating_v": 0.0},
            ]
        )
        self.assertEqual(function_separation_findings([shared]), [])


class InsulationTests(unittest.TestCase):
    def test_healthy_measurements_are_clean(self):
        result = insulation_findings(IR_MEASUREMENTS, 1.0e8)
        self.assertEqual(result["findings"], [])
        self.assertTrue(all(r["compliant"] for r in result["records"]))

    def test_low_resistance_is_flagged(self):
        low = [{"id": "X", "measured_ohm": 1.0e6, "test_voltage_v": 500.0}]
        result = insulation_findings(low, 1.0e8)
        self.assertEqual(len(result["findings"]), 1)

    def test_exact_requirement_is_accepted_at_the_limit(self):
        at_limit = [{"id": "X", "measured_ohm": 1.0e8, "test_voltage_v": 500.0}]
        result = insulation_findings(at_limit, 1.0e8)
        self.assertAlmostEqual(result["records"][0]["ratio"], 1.0, places=9)
        self.assertTrue(result["records"][0]["compliant"])

    def test_undervoltage_measurement_is_flagged(self):
        weak = [{"id": "X", "measured_ohm": 5.0e8, "test_voltage_v": 100.0,
                 "required_test_voltage_v": 500.0}]
        result = insulation_findings(weak, 1.0e8)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("lower stress", result["findings"][0])

    def test_zero_measured_resistance_rejected(self):
        with self.assertRaises(ValueError):
            insulation_findings([{"id": "X", "measured_ohm": 0.0, "test_voltage_v": 500.0}], 1.0e8)

    def test_missing_measurement_key_rejected(self):
        with self.assertRaises(ValueError):
            insulation_findings([{"id": "X", "measured_ohm": 1.0e9}], 1.0e8)

    def test_empty_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            insulation_findings([], 1.0e8)


class DielectricTests(unittest.TestCase):
    def test_default_rule_is_twice_plus_a_kilovolt(self):
        self.assertAlmostEqual(required_dielectric_voltage(28.0), 1056.0, places=9)

    def test_factor_and_offset_are_configurable(self):
        self.assertAlmostEqual(
            required_dielectric_voltage(100.0, factor=1.5, offset_v=500.0), 650.0, places=9
        )

    def test_default_constants_are_the_documented_ones(self):
        self.assertAlmostEqual(DEFAULT_DIELECTRIC_FACTOR, 2.0, places=9)
        self.assertAlmostEqual(DEFAULT_DIELECTRIC_OFFSET_V, 1000.0, places=9)

    def test_negative_operating_voltage_rejected(self):
        with self.assertRaises(ValueError):
            required_dielectric_voltage(-5.0)

    def test_healthy_withstand_test_is_clean(self):
        result = dielectric_findings(HV_TESTS, 1.0e-4)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["records"][0]["compliant"])

    def test_undervoltage_withstand_is_flagged(self):
        weak = [{"id": "X", "operating_v": 28.0, "applied_v": 500.0, "leakage_a": 1.0e-6}]
        result = dielectric_findings(weak, 1.0e-4)
        self.assertFalse(result["records"][0]["voltage_ok"])
        self.assertEqual(len(result["findings"]), 1)

    def test_excess_leakage_is_flagged(self):
        leaky = [{"id": "X", "operating_v": 28.0, "applied_v": 1200.0, "leakage_a": 1.0e-3}]
        result = dielectric_findings(leaky, 1.0e-4)
        self.assertFalse(result["records"][0]["leakage_ok"])

    def test_exact_required_voltage_is_accepted(self):
        exact = [{"id": "X", "operating_v": 28.0, "applied_v": 1056.0, "leakage_a": 1.0e-6}]
        result = dielectric_findings(exact, 1.0e-4)
        self.assertAlmostEqual(result["records"][0]["applied_v"],
                               result["records"][0]["required_v"], places=9)
        self.assertTrue(result["records"][0]["voltage_ok"])

    def test_missing_test_key_rejected(self):
        with self.assertRaises(ValueError):
            dielectric_findings([{"id": "X", "operating_v": 28.0}], 1.0e-4)

    def test_empty_test_set_rejected(self):
        with self.assertRaises(ValueError):
            dielectric_findings([], 1.0e-4)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "connectors": [power_connector(total_contacts=13), signal_connector()],
            "insulation_measurements": IR_MEASUREMENTS,
            "insulation_required_ohm": 1.0e8,
            "dielectric_tests": HV_TESTS,
            "leakage_limit_a": 1.0e-4,
            "required_current_margin": 0.25,
        }
        spec.update(overrides)
        return spec

    def test_healthy_design_reports_no_findings(self):
        result = assess_electrical_design(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_report_carries_one_record_per_connector(self):
        result = assess_electrical_design(self._spec())
        self.assertEqual(len(result["connectors"]), 2)

    def test_mixed_shell_fails_the_design(self):
        mixed = power_connector(
            circuits=[
                {"id": "M", "circuit_class": "power", "current_a": 1.0,
                 "contact_rating_a": 5.0, "operating_v": 28.0, "contacts_used": 2},
                {"id": "S", "circuit_class": "signal", "current_a": 0.01,
                 "contact_rating_a": 3.0, "operating_v": 5.0, "contacts_used": 2},
            ]
        )
        result = assess_electrical_design(self._spec(connectors=[mixed, signal_connector()]))
        self.assertFalse(result["compliant"])

    def test_low_insulation_fails_the_design(self):
        result = assess_electrical_design(self._spec(insulation_required_ohm=1.0e12))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["leakage_limit_a"]
        with self.assertRaises(ValueError):
            assess_electrical_design(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_electrical_design(["connectors"])

    def test_dielectric_rule_override_reaches_the_report(self):
        result = assess_electrical_design(
            self._spec(dielectric_factor=4.0, dielectric_offset_v=2000.0)
        )
        self.assertAlmostEqual(result["dielectric"][0]["required_v"], 2112.0, places=9)
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()
