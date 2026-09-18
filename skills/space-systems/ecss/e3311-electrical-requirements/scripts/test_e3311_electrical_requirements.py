"""Contract test for the e3311 electrical-requirements leaf (stdlib unittest)."""

import math
import unittest

from e3311_electrical_requirements_logic import (
    DEFAULT_ELECTRICAL_POLICY,
    ESD_PATHS,
    VERDICT_MET,
    VERDICT_NOT_MET,
    WIRING_CONTROLS,
    assess_electrical_requirements,
    assess_electrostatic_immunity,
    assess_nuclear_pulse_immunity,
    assess_radio_frequency_immunity,
    assess_stray_current,
    assess_wiring_integrity,
    current_margin_db,
    delivered_power_w,
    esd_stored_energy_j,
    induced_open_circuit_voltage_v,
    power_margin_db,
    validate_electrical_policy,
)


def wiring(**kw):
    controls = {name: True for name in WIRING_CONTROLS}
    controls.update(kw)
    return controls


def esd_case(**kw):
    case = {
        "source_capacitance_f": 500.0e-12,
        "source_voltage_v": 25000.0,
        "withstand_energy_j": {"pin-to-pin": 1.0, "pin-to-case": 1.0},
    }
    case.update(kw)
    return case


def rf_case(**kw):
    case = {
        "no_fire_power_w": 1.0,
        "field_strength_v_per_m": 0.2,
        "effective_length_m": 0.05,
        "bridgewire_resistance_ohm": 1.05,
    }
    case.update(kw)
    return case


def pulse_case(**kw):
    case = {
        "immunity_demonstrated": True,
        "no_fire_power_w": 1.0,
        "coupled_power_w": 1.0e-3,
    }
    case.update(kw)
    return case


def full_case(**kw):
    case = {
        "no_fire_current_a": 1.0,
        "no_fire_power_w": 1.0,
        "stray_current_a": 0.02,
        "radio_frequency": rf_case(),
        "electrostatic": esd_case(),
        "nuclear_pulse": pulse_case(),
        "wiring_controls": wiring(),
    }
    case.update(kw)
    return case


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_electrical_policy(DEFAULT_ELECTRICAL_POLICY),
            DEFAULT_ELECTRICAL_POLICY,
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_electrical_policy(["no_fire_power_margin_db", 20.0])

    def test_stray_fraction_at_or_above_unity_raises(self):
        policy = dict(DEFAULT_ELECTRICAL_POLICY, stray_current_fraction=1.0)
        with self.assertRaises(ValueError):
            validate_electrical_policy(policy)

    def test_negative_margin_raises(self):
        policy = dict(DEFAULT_ELECTRICAL_POLICY, no_fire_power_margin_db=-1.0)
        with self.assertRaises(ValueError):
            validate_electrical_policy(policy)

    def test_unknown_wiring_control_in_policy_raises(self):
        policy = dict(DEFAULT_ELECTRICAL_POLICY, required_wiring_controls=("gold-paint",))
        with self.assertRaises(ValueError):
            validate_electrical_policy(policy)

    def test_empty_wiring_control_list_raises(self):
        policy = dict(DEFAULT_ELECTRICAL_POLICY, required_wiring_controls=())
        with self.assertRaises(ValueError):
            validate_electrical_policy(policy)


class TestMarginArithmetic(unittest.TestCase):
    def test_power_margin_of_a_hundredfold_ratio(self):
        self.assertAlmostEqual(power_margin_db(1.0, 0.01), 20.0, places=9)

    def test_power_margin_is_zero_on_equality(self):
        self.assertAlmostEqual(power_margin_db(0.4, 0.4), 0.0, places=9)

    def test_power_margin_is_negative_when_applied_exceeds_no_fire(self):
        self.assertLess(power_margin_db(1.0, 10.0), -9.0)

    def test_current_margin_uses_the_voltage_decade(self):
        self.assertAlmostEqual(current_margin_db(1.0, 0.1), 20.0, places=9)

    def test_power_margin_rejects_zero_applied_power(self):
        with self.assertRaises(ValueError):
            power_margin_db(1.0, 0.0)

    def test_current_margin_rejects_a_boolean(self):
        with self.assertRaises(ValueError):
            current_margin_db(True, 0.1)

    def test_esd_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(
            esd_stored_energy_j(500.0e-12, 25000.0), 0.15625, places=12
        )

    def test_esd_energy_is_zero_at_zero_volts(self):
        self.assertAlmostEqual(esd_stored_energy_j(1.0e-9, 0.0), 0.0, places=12)

    def test_esd_energy_rejects_negative_voltage(self):
        with self.assertRaises(ValueError):
            esd_stored_energy_j(1.0e-9, -10.0)

    def test_induced_voltage_is_field_times_length(self):
        self.assertAlmostEqual(
            induced_open_circuit_voltage_v(20.0, 0.05), 1.0, places=12
        )

    def test_induced_voltage_rejects_zero_length(self):
        with self.assertRaises(ValueError):
            induced_open_circuit_voltage_v(20.0, 0.0)

    def test_delivered_power_uses_the_matched_quarter(self):
        self.assertAlmostEqual(delivered_power_w(2.0, 1.0), 1.0, places=12)

    def test_delivered_power_rejects_zero_resistance(self):
        with self.assertRaises(ValueError):
            delivered_power_w(1.0, 0.0)


class TestStrayCurrent(unittest.TestCase):
    def test_a_low_stray_current_passes(self):
        result = assess_stray_current(1.0, 0.02)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["allowed_current_a"], 0.1, places=12)

    def test_a_stray_current_exactly_on_the_allowance_passes(self):
        result = assess_stray_current(1.0, 0.1)
        self.assertTrue(result["compliant"])

    def test_a_stray_current_above_the_allowance_fails_with_a_finding(self):
        result = assess_stray_current(1.0, 0.5)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_zero_stray_current_reports_an_infinite_margin(self):
        result = assess_stray_current(1.0, 0.0)
        self.assertTrue(math.isinf(result["margin_db"]))
        self.assertTrue(result["compliant"])

    def test_negative_stray_current_raises(self):
        with self.assertRaises(ValueError):
            assess_stray_current(1.0, -0.01)

    def test_zero_no_fire_current_raises(self):
        with self.assertRaises(ValueError):
            assess_stray_current(0.0, 0.01)


class TestRadioFrequencyImmunity(unittest.TestCase):
    def test_a_weak_field_leaves_the_required_margin(self):
        result = assess_radio_frequency_immunity(rf_case(field_strength_v_per_m=2.0))
        self.assertTrue(result["compliant"])

    def test_a_strong_field_breaks_the_margin(self):
        result = assess_radio_frequency_immunity(rf_case(field_strength_v_per_m=200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_a_case_exactly_on_the_required_margin_passes(self):
        # Pickup set so the no-fire power sits exactly 20 dB above it.
        case = rf_case(
            no_fire_power_w=1.0,
            field_strength_v_per_m=0.02,
            effective_length_m=1.0,
            bridgewire_resistance_ohm=0.01,
        )
        result = assess_radio_frequency_immunity(case)
        self.assertAlmostEqual(result["pickup_power_w"], 0.01, places=12)
        self.assertAlmostEqual(result["margin_db"], 20.0, places=9)
        self.assertTrue(result["compliant"])

    def test_zero_field_reports_an_infinite_margin(self):
        result = assess_radio_frequency_immunity(rf_case(field_strength_v_per_m=0.0))
        self.assertTrue(math.isinf(result["margin_db"]))

    def test_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_radio_frequency_immunity(["field", 20.0])

    def test_missing_bridgewire_resistance_raises(self):
        case = rf_case()
        del case["bridgewire_resistance_ohm"]
        with self.assertRaises(ValueError):
            assess_radio_frequency_immunity(case)


class TestElectrostaticImmunity(unittest.TestCase):
    def test_both_paths_are_graded(self):
        result = assess_electrostatic_immunity(esd_case())
        self.assertEqual(sorted(result["paths"]), sorted(ESD_PATHS))

    def test_a_generous_withstand_passes(self):
        result = assess_electrostatic_immunity(esd_case())
        self.assertTrue(result["compliant"])

    def test_a_ratio_exactly_on_the_requirement_passes(self):
        case = esd_case(
            source_capacitance_f=2.0e-9,
            source_voltage_v=1000.0,
            withstand_energy_j={"pin-to-pin": 2.0e-3, "pin-to-case": 2.0e-3},
        )
        result = assess_electrostatic_immunity(case)
        self.assertAlmostEqual(result["discharge_energy_j"], 1.0e-3, places=12)
        self.assertAlmostEqual(
            result["paths"]["pin-to-pin"]["energy_ratio"], 2.0, places=9
        )
        self.assertTrue(result["compliant"])

    def test_a_weak_pin_to_case_path_fails_alone(self):
        case = esd_case(withstand_energy_j={"pin-to-pin": 1.0, "pin-to-case": 0.01})
        result = assess_electrostatic_immunity(case)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["paths"]["pin-to-pin"]["compliant"])
        self.assertFalse(result["paths"]["pin-to-case"]["compliant"])

    def test_a_missing_path_raises(self):
        case = esd_case(withstand_energy_j={"pin-to-pin": 1.0})
        with self.assertRaises(ValueError):
            assess_electrostatic_immunity(case)

    def test_a_non_mapping_withstand_raises(self):
        case = esd_case(withstand_energy_j=1.0)
        with self.assertRaises(ValueError):
            assess_electrostatic_immunity(case)


class TestNuclearPulseImmunity(unittest.TestCase):
    def test_a_demonstrated_low_coupling_passes(self):
        result = assess_nuclear_pulse_immunity(pulse_case())
        self.assertTrue(result["compliant"])

    def test_an_undemonstrated_case_carries_a_finding_even_with_margin(self):
        result = assess_nuclear_pulse_immunity(
            pulse_case(immunity_demonstrated=False)
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_high_coupled_power_fails(self):
        result = assess_nuclear_pulse_immunity(pulse_case(coupled_power_w=0.5))
        self.assertFalse(result["compliant"])

    def test_a_case_exactly_on_the_margin_passes(self):
        result = assess_nuclear_pulse_immunity(
            pulse_case(no_fire_power_w=1.0, coupled_power_w=0.01)
        )
        self.assertAlmostEqual(result["margin_db"], 20.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_non_boolean_demonstration_flag_raises(self):
        with self.assertRaises(ValueError):
            assess_nuclear_pulse_immunity(pulse_case(immunity_demonstrated="yes"))


class TestWiringIntegrity(unittest.TestCase):
    def test_a_complete_control_set_passes(self):
        result = assess_wiring_integrity(wiring())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["controls_absent"], [])

    def test_a_missing_control_is_named(self):
        result = assess_wiring_integrity(wiring(**{"firing-line-shorted-until-arm": False}))
        self.assertFalse(result["compliant"])
        self.assertIn("firing-line-shorted-until-arm", result["controls_absent"])

    def test_an_undeclared_control_raises(self):
        controls = wiring()
        del controls["shielded-twisted-pair"]
        with self.assertRaises(ValueError):
            assess_wiring_integrity(controls)

    def test_an_unknown_control_key_raises(self):
        with self.assertRaises(ValueError):
            assess_wiring_integrity(wiring(**{"gold-paint": True}))

    def test_a_non_boolean_control_state_raises(self):
        controls = wiring()
        controls["shielded-twisted-pair"] = 1
        with self.assertRaises(ValueError):
            assess_wiring_integrity(controls)


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_design_is_met(self):
        report = assess_electrical_requirements(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_paths"], [])
        self.assertEqual(report["findings"], [])

    def test_one_broken_path_names_only_itself(self):
        report = assess_electrical_requirements(full_case(stray_current_a=0.9))
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_paths"], ["stray-current"])

    def test_several_broken_paths_are_all_named(self):
        case = full_case(
            stray_current_a=0.9,
            wiring_controls=wiring(**{"firing-line-routed-apart": False}),
        )
        report = assess_electrical_requirements(case)
        self.assertEqual(
            report["failed_paths"], ["stray-current", "wiring-integrity"]
        )
        self.assertGreaterEqual(len(report["findings"]), 2)

    def test_the_no_fire_power_flows_into_the_subcases(self):
        case = full_case(no_fire_power_w=4.0)
        case["radio_frequency"] = {
            "field_strength_v_per_m": 0.2,
            "effective_length_m": 0.05,
            "bridgewire_resistance_ohm": 1.05,
        }
        case["nuclear_pulse"] = {
            "immunity_demonstrated": True,
            "coupled_power_w": 1.0e-3,
        }
        report = assess_electrical_requirements(case)
        self.assertAlmostEqual(report["no_fire_power_w"], 4.0, places=12)
        self.assertTrue(report["compliant"])

    def test_every_coupling_path_appears_in_the_report(self):
        report = assess_electrical_requirements(full_case())
        for name in (
            "stray-current",
            "radio-frequency",
            "electrostatic",
            "nuclear-pulse",
            "wiring-integrity",
        ):
            self.assertIn(name, report["paths"])

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_electrical_requirements("no-fire 1 A")

    def test_a_missing_no_fire_current_raises(self):
        case = full_case()
        del case["no_fire_current_a"]
        with self.assertRaises(ValueError):
            assess_electrical_requirements(case)


if __name__ == "__main__":
    unittest.main()
