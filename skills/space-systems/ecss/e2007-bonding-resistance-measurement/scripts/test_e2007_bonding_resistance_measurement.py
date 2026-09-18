"""Contract test for the bonding-resistance-measurement leaf (stdlib unittest)."""

import unittest

from e2007_bonding_resistance_measurement_logic import (
    EXEMPT,
    MAX_INJECTION_CURRENT_A,
    MIN_INJECTION_CURRENT_A,
    REQUIRED,
    RESISTANCE_TOLERANCE_OHM,
    TYPICAL_LEAD_RESISTANCE_OHM,
    assess_bond,
    assess_bonding_resistance_measurement,
    bond_resistance_limit_ohm,
    check_resistance_limit,
    check_setup,
    measured_resistance_ohm,
    measurement_required,
    resistance_from_four_wire,
    two_wire_reading_error_ohm,
    validate_bond,
)


def bond(bid="B-1", purpose="structural-reference", **kw):
    record = {
        "id": bid,
        "purpose": purpose,
        "method": "four-wire",
        "separate_sense_pair": True,
        "injection_current_a": 1.0,
        "sensed_voltage_v": 1.0e-3,
    }
    record.update(kw)
    return record


def bleed(bid="B-C", **kw):
    record = {
        "id": bid,
        "purpose": "electrostatic-charging-control",
        "method": "none",
        "separate_sense_pair": False,
    }
    record.update(kw)
    return record


class TestValidateBond(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_bond({"id": "B-1", "purpose": "structural-reference"})
        self.assertEqual(norm["method"], "none")
        self.assertEqual(norm["additional_purposes"], [])
        self.assertIsNone(norm["injection_current_a"])
        self.assertIsNone(norm["sensed_voltage_v"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(["B-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond(""))

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", purpose="paint-touch-up"))

    def test_unknown_additional_purpose_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", additional_purposes=["decorative"]))

    def test_non_sequence_additional_purposes_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", additional_purposes="shield-termination"))

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", method="six-wire"))

    def test_non_boolean_sense_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", separate_sense_pair="yes"))

    def test_zero_injection_current_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", injection_current_a=0.0))

    def test_negative_sensed_voltage_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", sensed_voltage_v=-1.0e-3))

    def test_negative_reported_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_bond(bond("B-1", reported_resistance_ohm=-1.0))

    def test_four_wire_method_defaults_the_sense_pair_true(self):
        norm = validate_bond(
            {"id": "B-1", "purpose": "structural-reference", "method": "four-wire"}
        )
        self.assertTrue(norm["separate_sense_pair"])


class TestMeasurementRequired(unittest.TestCase):
    def test_structural_bond_is_required(self):
        status, reason = measurement_required(bond())
        self.assertEqual(status, REQUIRED)
        self.assertEqual(reason, "purpose-carries-a-resistance-target")

    def test_charge_bleed_only_is_exempt(self):
        status, reason = measurement_required(bleed())
        self.assertEqual(status, EXEMPT)
        self.assertEqual(reason, "serves-charging-control-only")

    def test_charge_bleed_with_second_role_is_required(self):
        status, reason = measurement_required(
            bleed(additional_purposes=["shield-termination"])
        )
        self.assertEqual(status, REQUIRED)
        self.assertEqual(reason, "charge-bleed-path-with-a-second-role")

    def test_power_return_bond_is_required(self):
        status, _ = measurement_required(bond("B-2", purpose="power-current-return"))
        self.assertEqual(status, REQUIRED)


class TestResistanceLimit(unittest.TestCase):
    def test_structural_limit(self):
        self.assertAlmostEqual(bond_resistance_limit_ohm(bond()), 2.5e-3, places=9)

    def test_power_return_limit_is_tighter(self):
        limit = bond_resistance_limit_ohm(bond("B-2", purpose="power-current-return"))
        self.assertAlmostEqual(limit, 1.0e-3, places=9)

    def test_second_role_takes_the_tighter_limit(self):
        limit = bond_resistance_limit_ohm(
            bond("B-3", purpose="structural-reference",
                 additional_purposes=["lightning-current-path"])
        )
        self.assertAlmostEqual(limit, 1.0e-3, places=9)

    def test_exempt_bond_has_no_limit(self):
        with self.assertRaises(ValueError):
            bond_resistance_limit_ohm(bleed())

    def test_charge_bleed_with_second_role_takes_that_limit(self):
        limit = bond_resistance_limit_ohm(
            bleed(additional_purposes=["shield-termination"])
        )
        self.assertAlmostEqual(limit, 2.5e-3, places=9)


class TestResistanceFromFourWire(unittest.TestCase):
    def test_quotient_of_voltage_and_current(self):
        self.assertAlmostEqual(
            resistance_from_four_wire(2.5e-3, 1.0), 2.5e-3, places=12
        )

    def test_ten_ampere_injection_scales_down(self):
        self.assertAlmostEqual(
            resistance_from_four_wire(2.5e-2, 10.0), 2.5e-3, places=12
        )

    def test_zero_current_raises(self):
        with self.assertRaises(ValueError):
            resistance_from_four_wire(1.0e-3, 0.0)

    def test_non_numeric_voltage_raises(self):
        with self.assertRaises(ValueError):
            resistance_from_four_wire("1 mV", 1.0)

    def test_two_wire_error_dwarfs_the_tightest_limit(self):
        self.assertGreater(two_wire_reading_error_ohm(), 10.0 * 1.0e-3)
        self.assertAlmostEqual(
            two_wire_reading_error_ohm(), TYPICAL_LEAD_RESISTANCE_OHM, places=12
        )


class TestCheckSetup(unittest.TestCase):
    def test_good_four_wire_setup_is_clean(self):
        self.assertEqual(check_setup(bond()), [])

    def test_exempt_bond_is_not_graded_on_setup(self):
        self.assertEqual(check_setup(bleed()), [])

    def test_missing_measurement_is_flagged(self):
        self.assertEqual(
            check_setup(bond("B-1", method="none")),
            ["no-resistance-measurement-on-record"],
        )

    def test_two_wire_method_is_flagged(self):
        self.assertEqual(
            check_setup(bond("B-1", method="two-wire", separate_sense_pair=False)),
            ["two-wire-reading-includes-lead-and-contact-resistance"],
        )

    def test_shared_sense_pair_is_flagged(self):
        self.assertIn(
            "sense-pair-not-separated-from-injection-pair",
            check_setup(bond("B-1", separate_sense_pair=False)),
        )

    def test_injection_current_below_window_is_flagged(self):
        self.assertIn(
            "injection-current-below-window",
            check_setup(bond("B-1", injection_current_a=0.01)),
        )

    def test_injection_current_above_window_is_flagged(self):
        self.assertIn(
            "injection-current-above-window",
            check_setup(bond("B-1", injection_current_a=25.0)),
        )

    def test_injection_current_on_the_window_floor_is_accepted(self):
        findings = check_setup(
            bond("B-1", injection_current_a=MIN_INJECTION_CURRENT_A,
                 sensed_voltage_v=1.0e-4)
        )
        self.assertEqual(findings, [])

    def test_injection_current_on_the_window_ceiling_is_accepted(self):
        findings = check_setup(
            bond("B-1", injection_current_a=MAX_INJECTION_CURRENT_A,
                 sensed_voltage_v=1.0e-2)
        )
        self.assertEqual(findings, [])

    def test_missing_injection_current_is_flagged(self):
        self.assertIn(
            "injection-current-not-on-record",
            check_setup(bond("B-1", injection_current_a=None)),
        )

    def test_missing_sensed_voltage_is_flagged(self):
        self.assertIn(
            "sensed-voltage-not-on-record",
            check_setup(bond("B-1", sensed_voltage_v=None)),
        )


class TestMeasuredResistance(unittest.TestCase):
    def test_four_wire_value_is_computed(self):
        self.assertAlmostEqual(measured_resistance_ohm(bond()), 1.0e-3, places=12)

    def test_two_wire_value_is_not_usable(self):
        self.assertIsNone(measured_resistance_ohm(bond("B-1", method="two-wire")))

    def test_absent_measurement_is_none(self):
        self.assertIsNone(measured_resistance_ohm(bond("B-1", method="none")))

    def test_incomplete_four_wire_record_is_none(self):
        self.assertIsNone(measured_resistance_ohm(bond("B-1", sensed_voltage_v=None)))


class TestCheckResistanceLimit(unittest.TestCase):
    def test_bond_under_limit_is_clean(self):
        findings, value = check_resistance_limit(bond())
        self.assertEqual(findings, [])
        self.assertAlmostEqual(value, 1.0e-3, places=12)

    def test_bond_exactly_on_limit_is_accepted(self):
        findings, value = check_resistance_limit(
            bond("B-1", sensed_voltage_v=2.5e-3, injection_current_a=1.0)
        )
        self.assertEqual(findings, [])
        self.assertAlmostEqual(value, 2.5e-3, places=12)

    def test_bond_over_limit_is_flagged(self):
        findings, value = check_resistance_limit(
            bond("B-1", sensed_voltage_v=9.0e-3, injection_current_a=1.0)
        )
        self.assertEqual(findings, ["bond-resistance-above-purpose-limit"])
        self.assertAlmostEqual(value, 9.0e-3, places=12)

    def test_tolerance_absorbs_a_last_place_overshoot(self):
        over = 2.5e-3 + RESISTANCE_TOLERANCE_OHM / 2.0
        findings, _ = check_resistance_limit(
            bond("B-1", sensed_voltage_v=over, injection_current_a=1.0)
        )
        self.assertEqual(findings, [])

    def test_exempt_bond_yields_no_value(self):
        findings, value = check_resistance_limit(bleed())
        self.assertEqual(findings, [])
        self.assertIsNone(value)


class TestAssessBond(unittest.TestCase):
    def test_compliant_bond_reports_its_limit(self):
        result = assess_bond(bond())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["status"], REQUIRED)
        self.assertAlmostEqual(result["limit_ohm"], 2.5e-3, places=9)

    def test_exempt_bond_is_compliant_without_a_limit(self):
        result = assess_bond(bleed())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["status"], EXEMPT)
        self.assertIsNone(result["limit_ohm"])

    def test_two_wire_bond_is_not_compliant(self):
        result = assess_bond(bond("B-1", method="two-wire"))
        self.assertFalse(result["compliant"])
        self.assertIn(
            "two-wire-reading-includes-lead-and-contact-resistance",
            result["findings"],
        )

    def test_over_limit_bond_is_not_compliant(self):
        result = assess_bond(
            bond("B-1", purpose="power-current-return", sensed_voltage_v=2.0e-3)
        )
        self.assertFalse(result["compliant"])
        self.assertIn("bond-resistance-above-purpose-limit", result["findings"])


class TestAssessSchedule(unittest.TestCase):
    def test_clean_schedule_is_compliant(self):
        report = assess_bonding_resistance_measurement([bond("B-1"), bleed("B-2")])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["exempt_ids"], ["B-2"])
        self.assertEqual(report["measured_ids"], ["B-1"])

    def test_unmeasured_bond_fails_the_schedule(self):
        report = assess_bonding_resistance_measurement(
            [bond("B-1"), bond("B-2", method="none")]
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["B-2"])

    def test_duplicate_bond_id_raises(self):
        with self.assertRaises(ValueError):
            assess_bonding_resistance_measurement([bond("B-1"), bond("B-1")])

    def test_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            assess_bonding_resistance_measurement([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_bonding_resistance_measurement(bond())


if __name__ == "__main__":
    unittest.main()
