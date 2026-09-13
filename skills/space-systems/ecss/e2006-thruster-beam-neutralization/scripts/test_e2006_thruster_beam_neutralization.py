#!/usr/bin/env python3
"""Gate 3 contract test for e2006-thruster-beam-neutralization.

Offline, deterministic, stdlib unittest. Exercises the categorization,
current-balance, floating-potential, coupling-voltage, ignition-sequence,
emitter-redundancy and aggregation paths of the clause 11.2.2 logic,
including every ValueError path and the at-the-limit boundary cases.
"""

import unittest

from e2006_thruster_beam_neutralization_logic import (
    DEFAULT_COUPLING_VOLTAGE_ALLOWANCE_V,
    assess_propulsion_neutralization,
    assess_thruster_neutralization,
    categorize_neutralization_architecture,
    check_coupling_voltage,
    check_emitter_redundancy,
    check_ignition_sequence,
    check_potential_allowance,
    floating_potential_v,
    neutralizer_current_balance,
)


def compliant_thruster(**overrides):
    """Build a thruster record that satisfies every clause 11.2.2 check."""
    record = {
        "id": "EPT-1",
        "architecture": "dedicated-neutralizer",
        "beam_current_a": 0.9,
        "neutralizer_current_a": 0.92,
        "backflow_current_a": 0.01,
        "plasma_contact_conductance_s": 2.0e-3,
        "allowable_potential_v": 25.0,
        "coupling_voltage_v": -12.0,
        "allowable_coupling_voltage_v": 20.0,
        "emitter_ignition_s": 0.0,
        "beam_on_s": 5.0,
        "required_lead_s": 3.0,
        "emitter_count": 2,
    }
    record.update(overrides)
    return record


class ArchitectureCategorizationTests(unittest.TestCase):
    def test_dedicated_alias_normalizes(self):
        self.assertEqual(
            categorize_neutralization_architecture("dedicated"),
            "dedicated-neutralizer",
        )

    def test_shared_alias_normalizes(self):
        self.assertEqual(
            categorize_neutralization_architecture("cluster-neutralizer"),
            "shared-neutralizer",
        )

    def test_self_neutralizing_alias_normalizes(self):
        self.assertEqual(
            categorize_neutralization_architecture("integrated-emitter"),
            "self-neutralizing",
        )

    def test_case_and_separators_are_normalized(self):
        self.assertEqual(
            categorize_neutralization_architecture("  Shared_Neutralizer "),
            "shared-neutralizer",
        )

    def test_unknown_architecture_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_neutralization_architecture("magnetic-nozzle")

    def test_empty_architecture_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_neutralization_architecture("   ")

    def test_non_string_architecture_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_neutralization_architecture(7)


class CurrentBalanceTests(unittest.TestCase):
    def test_matched_currents_are_electron_rich(self):
        balance = neutralizer_current_balance(1.0, 1.05)
        self.assertTrue(balance["electron_rich"])
        self.assertAlmostEqual(balance["neutralization_ratio"], 1.05)
        self.assertAlmostEqual(balance["net_emitted_current_a"], -0.05)

    def test_under_neutralized_beam_is_not_electron_rich(self):
        balance = neutralizer_current_balance(1.0, 0.8)
        self.assertFalse(balance["electron_rich"])
        self.assertAlmostEqual(balance["net_emitted_current_a"], 0.2)

    def test_backflow_reduces_net_emitted_current(self):
        without = neutralizer_current_balance(1.0, 0.8)
        with_backflow = neutralizer_current_balance(1.0, 0.8, 0.05)
        self.assertAlmostEqual(
            with_backflow["net_emitted_current_a"],
            without["net_emitted_current_a"] - 0.05,
        )

    def test_ratio_at_unity_within_representation_is_electron_rich(self):
        # 0.1 + 0.2 lands a few ULPs above 0.3, so the ratio computes just
        # below unity while the design is physically balanced.
        balance = neutralizer_current_balance(0.1 + 0.2, 0.3)
        self.assertLess(balance["neutralization_ratio"], 1.0)
        self.assertTrue(balance["electron_rich"])

    def test_zero_beam_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(0.0, 1.0)

    def test_negative_beam_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(-0.5, 1.0)

    def test_negative_neutralizer_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(1.0, -0.1)

    def test_negative_backflow_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(1.0, 1.0, -0.01)

    def test_backflow_above_beam_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(1.0, 1.0, 1.5)

    def test_non_numeric_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance("1.0", 1.0)

    def test_boolean_current_is_rejected(self):
        with self.assertRaises(ValueError):
            neutralizer_current_balance(True, 1.0)


class FloatingPotentialTests(unittest.TestCase):
    def test_positive_net_emission_drives_negative_potential(self):
        self.assertAlmostEqual(floating_potential_v(1.0e-3, 1.0e-4), -10.0)

    def test_electron_rich_emission_drives_positive_potential(self):
        self.assertAlmostEqual(floating_potential_v(-2.0e-3, 1.0e-4), 20.0)

    def test_larger_conductance_lowers_the_potential(self):
        low = abs(floating_potential_v(1.0e-3, 1.0e-4))
        high = abs(floating_potential_v(1.0e-3, 1.0e-3))
        self.assertLess(high, low)

    def test_zero_conductance_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_potential_v(1.0e-3, 0.0)

    def test_negative_conductance_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_potential_v(1.0e-3, -1.0e-4)

    def test_non_finite_current_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_potential_v(float("inf"), 1.0e-4)


class PotentialAllowanceTests(unittest.TestCase):
    def test_margin_is_allowance_minus_magnitude(self):
        check = check_potential_allowance(-12.0, 25.0)
        self.assertAlmostEqual(check["margin_v"], 13.0)
        self.assertTrue(check["compliant"])

    def test_potential_exactly_at_allowance_passes(self):
        check = check_potential_allowance(-25.0, 25.0)
        self.assertTrue(check["compliant"])
        self.assertAlmostEqual(check["margin_v"], 0.0)

    def test_representation_error_at_the_limit_is_absorbed(self):
        # (0.1 + 0.2) / 0.03 evaluates a few ULPs above 10.0.
        magnitude = (0.1 + 0.2) / 0.03
        self.assertGreater(magnitude, 10.0)
        check = check_potential_allowance(-magnitude, 10.0)
        self.assertTrue(check["compliant"])

    def test_potential_above_allowance_fails(self):
        check = check_potential_allowance(-40.0, 25.0)
        self.assertFalse(check["compliant"])
        self.assertLess(check["margin_v"], 0.0)

    def test_non_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_potential_allowance(-10.0, 0.0)


class CouplingVoltageTests(unittest.TestCase):
    def test_voltage_within_allowance_passes(self):
        check = check_coupling_voltage(-14.0, 20.0)
        self.assertTrue(check["compliant"])
        self.assertAlmostEqual(check["magnitude_v"], 14.0)

    def test_default_allowance_is_applied(self):
        check = check_coupling_voltage(-19.0)
        self.assertAlmostEqual(
            check["allowable_magnitude_v"], DEFAULT_COUPLING_VOLTAGE_ALLOWANCE_V
        )
        self.assertTrue(check["compliant"])

    def test_degraded_emitter_voltage_fails(self):
        check = check_coupling_voltage(-31.5, 20.0)
        self.assertFalse(check["compliant"])

    def test_zero_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            check_coupling_voltage(-5.0, 0.0)

    def test_non_numeric_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            check_coupling_voltage(None, 20.0)


class IgnitionSequenceTests(unittest.TestCase):
    def test_emitter_leading_the_beam_passes(self):
        check = check_ignition_sequence(0.0, 5.0, 3.0)
        self.assertTrue(check["compliant"])
        self.assertAlmostEqual(check["lead_s"], 5.0)

    def test_lead_equal_to_requirement_within_representation_passes(self):
        # 0.3 - 0.1 evaluates a few ULPs below 0.2.
        check = check_ignition_sequence(0.1, 0.3, 0.2)
        self.assertLess(check["lead_s"], 0.2)
        self.assertTrue(check["compliant"])

    def test_beam_opening_before_ignition_fails(self):
        check = check_ignition_sequence(4.0, 1.0, 0.0)
        self.assertFalse(check["compliant"])
        self.assertAlmostEqual(check["lead_s"], -3.0)

    def test_insufficient_lead_fails(self):
        check = check_ignition_sequence(0.0, 1.0, 3.0)
        self.assertFalse(check["compliant"])

    def test_negative_required_lead_is_rejected(self):
        with self.assertRaises(ValueError):
            check_ignition_sequence(0.0, 5.0, -1.0)


class EmitterRedundancyTests(unittest.TestCase):
    def test_two_emitters_raise_no_finding(self):
        check = check_emitter_redundancy("dedicated-neutralizer", 2)
        self.assertEqual(check["findings"], [])
        self.assertEqual(check["observations"], [])

    def test_single_emitter_is_an_observation(self):
        check = check_emitter_redundancy("dedicated-neutralizer", 1)
        self.assertEqual(check["findings"], [])
        self.assertEqual(check["observations"], ["single-string-electron-emitter"])

    def test_missing_emitter_is_a_finding(self):
        check = check_emitter_redundancy("shared-neutralizer", 0)
        self.assertEqual(check["findings"], ["no-electron-emitter-declared"])

    def test_self_neutralizing_needs_no_separate_emitter(self):
        check = check_emitter_redundancy("self-neutralizing", 0)
        self.assertFalse(check["emitter_required"])
        self.assertEqual(check["findings"], [])

    def test_negative_emitter_count_is_rejected(self):
        with self.assertRaises(ValueError):
            check_emitter_redundancy("dedicated-neutralizer", -1)

    def test_non_integer_emitter_count_is_rejected(self):
        with self.assertRaises(ValueError):
            check_emitter_redundancy("dedicated-neutralizer", 1.5)

    def test_boolean_emitter_count_is_rejected(self):
        with self.assertRaises(ValueError):
            check_emitter_redundancy("dedicated-neutralizer", True)


class ThrusterAssessmentTests(unittest.TestCase):
    def test_compliant_thruster_has_no_findings(self):
        result = assess_thruster_neutralization(compliant_thruster())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["floating_potential_v"], 15.0)

    def test_under_neutralized_beam_is_flagged(self):
        result = assess_thruster_neutralization(
            compliant_thruster(neutralizer_current_a=0.5)
        )
        self.assertIn("beam-not-electron-rich", result["findings"])
        self.assertFalse(result["compliant"])

    def test_potential_exceedance_is_flagged(self):
        result = assess_thruster_neutralization(
            compliant_thruster(allowable_potential_v=5.0)
        )
        self.assertIn("floating-potential-exceeds-allowance", result["findings"])

    def test_missing_coupling_voltage_is_a_finding(self):
        result = assess_thruster_neutralization(
            compliant_thruster(coupling_voltage_v=None)
        )
        self.assertIn("neutralizer-coupling-voltage-not-recorded", result["findings"])
        self.assertIsNone(result["coupling_check"])

    def test_excessive_coupling_voltage_is_a_finding(self):
        result = assess_thruster_neutralization(
            compliant_thruster(coupling_voltage_v=-28.0)
        )
        self.assertIn(
            "neutralizer-coupling-voltage-exceeds-allowance", result["findings"]
        )

    def test_missing_sequence_data_is_a_finding(self):
        result = assess_thruster_neutralization(compliant_thruster(beam_on_s=None))
        self.assertIn("ignition-sequence-not-recorded", result["findings"])
        self.assertIsNone(result["sequence_check"])

    def test_beam_ahead_of_ignition_is_a_finding(self):
        result = assess_thruster_neutralization(
            compliant_thruster(emitter_ignition_s=6.0, required_lead_s=0.0)
        )
        self.assertIn("beam-precedes-neutralizer-ignition", result["findings"])

    def test_single_string_emitter_is_an_observation_only(self):
        result = assess_thruster_neutralization(compliant_thruster(emitter_count=1))
        self.assertTrue(result["compliant"])
        self.assertIn("single-string-electron-emitter", result["observations"])

    def test_missing_required_key_is_rejected(self):
        record = compliant_thruster()
        del record["allowable_potential_v"]
        with self.assertRaises(ValueError):
            assess_thruster_neutralization(record)

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thruster_neutralization(["EPT-1"])

    def test_blank_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_thruster_neutralization(compliant_thruster(id="  "))


class PropulsionSetTests(unittest.TestCase):
    def test_all_compliant_set_is_compliant(self):
        summary = assess_propulsion_neutralization(
            [compliant_thruster(), compliant_thruster(id="EPT-2")]
        )
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["compliant_count"], 2)
        self.assertEqual(summary["noncompliant_ids"], [])

    def test_noncompliant_thruster_is_named(self):
        summary = assess_propulsion_neutralization(
            [
                compliant_thruster(),
                compliant_thruster(id="EPT-2", neutralizer_current_a=0.2),
            ]
        )
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["noncompliant_ids"], ["EPT-2"])
        self.assertIn(
            "beam-not-electron-rich", summary["findings_by_thruster"]["EPT-2"]
        )

    def test_empty_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_neutralization([])

    def test_non_list_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_neutralization(compliant_thruster())

    def test_duplicate_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_propulsion_neutralization(
                [compliant_thruster(), compliant_thruster()]
            )


if __name__ == "__main__":
    unittest.main()
