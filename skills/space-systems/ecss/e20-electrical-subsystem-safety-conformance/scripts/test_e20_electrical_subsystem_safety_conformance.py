#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.9 electrical subsystem
safety conformance.

Exercises scripts/e20_electrical_subsystem_safety_conformance_logic.py
(stdlib unittest, offline). Contract: every hazard kind maps to exactly
one family and an unrecognized kind raises; a credible consequence maps
to exactly one severity band and an unmapped consequence raises; the
failure tolerance is two for catastrophic, one for critical and none
for marginal, and the independent-inhibit count is one more than the
tolerance except for a marginal hazard; an inhibit set is flagged when
it is short of that count, when an inhibit is not independent, or when
an inhibit is not monitored; the residual voltage on a stored-energy
source follows the resistance-capacitance decay, the time to the safe
touch voltage is its exact inverse, and both are checked against the
safe touch voltage, the safe energy limit and the bleed period the
procedure allows; a hazard with no verification record or an open one
is flagged and an unrecognized method raises; and the subsystem is
conformant only when no hazard carries a finding.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electrical_subsystem_safety_conformance_logic as sc  # noqa: E402


def _clean_stored_energy():
    """A bulk capacitor whose bleed path satisfies every clause 5.9
    stored-energy check."""
    return {
        "capacitance_f": 1.0e-3,
        "operating_voltage_v": 100.0,
        "bleed_resistance_ohm": 1.0e4,
        "safe_touch_voltage_v": 30.0,
        "safe_energy_j": 0.1,
        "required_bleed_time_s": 60.0,
    }


def _clean_inhibits():
    return [
        {"inhibit_id": "INH-A", "independent": True, "monitored": True},
        {"inhibit_id": "INH-B", "independent": True, "monitored": True},
    ]


def _clean_verification():
    return {
        "method": "safety_test",
        "closed": True,
        "closure_reference": "SAF-TR-014",
    }


def _clean_hazard():
    return {
        "hazard_id": "HAZ-01",
        "hazard_kind": "bulk_capacitor_residual_charge",
        "consequence": "loss_of_mission",
        "inhibits": _clean_inhibits(),
        "stored_energy": _clean_stored_energy(),
        "verification": _clean_verification(),
    }


class CategorizeElectricalHazardTest(unittest.TestCase):
    def test_exposed_conductor_is_shock_and_touch(self):
        self.assertEqual(
            sc.categorize_electrical_hazard("exposed_live_conductor"),
            "shock_and_touch",
        )

    def test_capacitor_charge_is_stored_energy(self):
        self.assertEqual(
            sc.categorize_electrical_hazard("bulk_capacitor_residual_charge"),
            "stored_energy",
        )

    def test_cell_internal_short_is_thermal_runaway(self):
        self.assertEqual(
            sc.categorize_electrical_hazard("battery_cell_internal_short"),
            "thermal_runaway",
        )

    def test_firing_circuit_is_inadvertent_initiation(self):
        self.assertEqual(
            sc.categorize_electrical_hazard("pyrotechnic_firing_circuit"),
            "inadvertent_initiation",
        )

    def test_transmitter_field_is_radiated_energy(self):
        self.assertEqual(
            sc.categorize_electrical_hazard("rf_transmitter_field_exposure"),
            "radiated_energy",
        )

    def test_every_kind_maps_to_a_known_family(self):
        families = set(sc.HAZARD_FAMILIES.values())
        self.assertEqual(
            families,
            {
                "shock_and_touch",
                "stored_energy",
                "thermal_runaway",
                "inadvertent_initiation",
                "radiated_energy",
            },
        )

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            sc.categorize_electrical_hazard("bad_vibes")

    def test_unhashable_kind_raises_value_error(self):
        with self.assertRaises(ValueError):
            sc.categorize_electrical_hazard(["exposed_live_conductor"])


class SeverityFromConsequenceTest(unittest.TestCase):
    def test_loss_of_vehicle_is_catastrophic(self):
        self.assertEqual(
            sc.severity_from_consequence("loss_of_life_or_vehicle"),
            "catastrophic",
        )

    def test_disabling_injury_is_catastrophic(self):
        self.assertEqual(
            sc.severity_from_consequence("permanent_disabling_injury"),
            "catastrophic",
        )

    def test_loss_of_mission_is_critical(self):
        self.assertEqual(
            sc.severity_from_consequence("loss_of_mission"), "critical"
        )

    def test_redundant_string_loss_is_marginal(self):
        self.assertEqual(
            sc.severity_from_consequence("loss_of_a_redundant_string"),
            "marginal",
        )

    def test_unmapped_consequence_raises(self):
        with self.assertRaises(ValueError):
            sc.severity_from_consequence("probably_fine")

    def test_none_consequence_raises(self):
        with self.assertRaises(ValueError):
            sc.severity_from_consequence(None)


class FailureToleranceTest(unittest.TestCase):
    def test_catastrophic_needs_two_failure_tolerance(self):
        self.assertEqual(sc.required_failure_tolerance("catastrophic"), 2)

    def test_critical_needs_one_failure_tolerance(self):
        self.assertEqual(sc.required_failure_tolerance("critical"), 1)

    def test_marginal_needs_no_failure_tolerance(self):
        self.assertEqual(sc.required_failure_tolerance("marginal"), 0)

    def test_catastrophic_needs_three_independent_inhibits(self):
        self.assertEqual(sc.required_independent_inhibits("catastrophic"), 3)

    def test_critical_needs_two_independent_inhibits(self):
        self.assertEqual(sc.required_independent_inhibits("critical"), 2)

    def test_marginal_needs_no_inhibits(self):
        self.assertEqual(sc.required_independent_inhibits("marginal"), 0)

    def test_inhibit_count_is_tolerance_plus_one_where_tolerance_applies(self):
        for severity in ("catastrophic", "critical"):
            self.assertEqual(
                sc.required_independent_inhibits(severity),
                sc.required_failure_tolerance(severity) + 1,
            )

    def test_unrecognized_severity_raises(self):
        with self.assertRaises(ValueError):
            sc.required_failure_tolerance("annoying")

    def test_unrecognized_severity_raises_in_inhibit_count(self):
        with self.assertRaises(ValueError):
            sc.required_independent_inhibits("annoying")


class InhibitFindingsTest(unittest.TestCase):
    def test_two_independent_monitored_inhibits_satisfy_a_critical_hazard(self):
        self.assertEqual(
            sc.inhibit_findings("HAZ-01", "critical", _clean_inhibits()), []
        )

    def test_two_inhibits_are_short_for_a_catastrophic_hazard(self):
        findings = sc.inhibit_findings(
            "HAZ-01", "catastrophic", _clean_inhibits()
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("independent inhibit", findings[0])

    def test_three_independent_inhibits_satisfy_a_catastrophic_hazard(self):
        inhibits = _clean_inhibits() + [
            {"inhibit_id": "INH-C", "independent": True, "monitored": True}
        ]
        self.assertEqual(
            sc.inhibit_findings("HAZ-01", "catastrophic", inhibits), []
        )

    def test_marginal_hazard_needs_no_inhibits(self):
        self.assertEqual(sc.inhibit_findings("HAZ-02", "marginal", []), [])

    def test_dependent_inhibit_does_not_count(self):
        inhibits = _clean_inhibits()
        inhibits[1]["independent"] = False
        findings = sc.inhibit_findings("HAZ-01", "critical", inhibits)
        self.assertEqual(len(findings), 2)
        self.assertTrue(any("shares a failure cause" in f for f in findings))

    def test_unmonitored_inhibit_is_flagged(self):
        inhibits = _clean_inhibits()
        inhibits[0]["monitored"] = False
        findings = sc.inhibit_findings("HAZ-01", "critical", inhibits)
        self.assertEqual(len(findings), 1)
        self.assertIn("monitoring", findings[0])

    def test_no_inhibits_on_a_critical_hazard_is_flagged(self):
        findings = sc.inhibit_findings("HAZ-01", "critical", [])
        self.assertEqual(len(findings), 1)

    def test_inhibit_missing_a_key_raises(self):
        inhibits = _clean_inhibits()
        del inhibits[0]["monitored"]
        with self.assertRaises(ValueError):
            sc.inhibit_findings("HAZ-01", "critical", inhibits)


class StoredEnergyMathTest(unittest.TestCase):
    def test_stored_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(
            sc.capacitor_stored_energy(1.0e-3, 100.0), 5.0, places=9
        )

    def test_zero_voltage_stores_no_energy(self):
        self.assertAlmostEqual(
            sc.capacitor_stored_energy(1.0e-3, 0.0), 0.0, places=12
        )

    def test_non_positive_capacitance_raises(self):
        with self.assertRaises(ValueError):
            sc.capacitor_stored_energy(0.0, 100.0)

    def test_negative_voltage_raises(self):
        with self.assertRaises(ValueError):
            sc.capacitor_stored_energy(1.0e-3, -1.0)

    def test_one_time_constant_leaves_one_over_e(self):
        self.assertAlmostEqual(
            sc.residual_voltage_after_bleed(100.0, 1.0e-3, 1.0e4, 10.0),
            100.0 / math.e,
            places=9,
        )

    def test_zero_elapsed_time_leaves_the_initial_voltage(self):
        self.assertAlmostEqual(
            sc.residual_voltage_after_bleed(100.0, 1.0e-3, 1.0e4, 0.0),
            100.0,
            places=9,
        )

    def test_negative_elapsed_time_raises(self):
        with self.assertRaises(ValueError):
            sc.residual_voltage_after_bleed(100.0, 1.0e-3, 1.0e4, -1.0)

    def test_non_positive_bleed_resistance_raises(self):
        with self.assertRaises(ValueError):
            sc.residual_voltage_after_bleed(100.0, 1.0e-3, 0.0, 10.0)

    def test_time_to_safe_voltage_inverts_the_decay(self):
        seconds = sc.time_to_safe_voltage(100.0, 30.0, 1.0e-3, 1.0e4)
        self.assertAlmostEqual(
            sc.residual_voltage_after_bleed(100.0, 1.0e-3, 1.0e4, seconds),
            30.0,
            places=9,
        )

    def test_already_safe_source_needs_no_time(self):
        self.assertAlmostEqual(
            sc.time_to_safe_voltage(20.0, 30.0, 1.0e-3, 1.0e4), 0.0, places=12
        )

    def test_non_positive_safe_voltage_raises(self):
        with self.assertRaises(ValueError):
            sc.time_to_safe_voltage(100.0, 0.0, 1.0e-3, 1.0e4)

    def test_negative_initial_voltage_raises_in_time_to_safe(self):
        with self.assertRaises(ValueError):
            sc.time_to_safe_voltage(-1.0, 30.0, 1.0e-3, 1.0e4)


class StoredEnergyFindingsTest(unittest.TestCase):
    def test_clean_source_has_no_findings(self):
        self.assertEqual(
            sc.stored_energy_findings("HAZ-01", _clean_stored_energy()), []
        )

    def test_bleed_period_exactly_at_the_requirement_passes(self):
        source = _clean_stored_energy()
        source["required_bleed_time_s"] = sc.time_to_safe_voltage(
            source["operating_voltage_v"],
            source["safe_touch_voltage_v"],
            source["capacitance_f"],
            source["bleed_resistance_ohm"],
        )
        source["safe_energy_j"] = sc.capacitor_stored_energy(
            source["capacitance_f"], source["safe_touch_voltage_v"]
        )
        self.assertEqual(sc.stored_energy_findings("HAZ-01", source), [])

    def test_short_bleed_period_leaves_voltage_on_the_source(self):
        source = _clean_stored_energy()
        source["required_bleed_time_s"] = 1.0
        findings = sc.stored_energy_findings("HAZ-01", source)
        self.assertTrue(any("safe touch limit" in f for f in findings))

    def test_short_bleed_period_is_flagged_against_the_procedure(self):
        source = _clean_stored_energy()
        source["required_bleed_time_s"] = 1.0
        findings = sc.stored_energy_findings("HAZ-01", source)
        self.assertTrue(any("longer than" in f for f in findings))

    def test_tight_energy_limit_is_flagged(self):
        source = _clean_stored_energy()
        source["safe_energy_j"] = 1.0e-12
        findings = sc.stored_energy_findings("HAZ-01", source)
        self.assertTrue(any("residual stored energy" in f for f in findings))

    def test_missing_stored_energy_key_raises(self):
        source = _clean_stored_energy()
        del source["bleed_resistance_ohm"]
        with self.assertRaises(ValueError):
            sc.stored_energy_findings("HAZ-01", source)

    def test_negative_required_bleed_time_raises(self):
        source = _clean_stored_energy()
        source["required_bleed_time_s"] = -1.0
        with self.assertRaises(ValueError):
            sc.stored_energy_findings("HAZ-01", source)

    def test_non_positive_safe_touch_voltage_raises(self):
        source = _clean_stored_energy()
        source["safe_touch_voltage_v"] = 0.0
        with self.assertRaises(ValueError):
            sc.stored_energy_findings("HAZ-01", source)


class VerificationFindingsTest(unittest.TestCase):
    def test_closed_record_has_no_findings(self):
        self.assertEqual(
            sc.verification_findings("HAZ-01", _clean_verification()), []
        )

    def test_open_record_is_flagged(self):
        verification = _clean_verification()
        verification["closed"] = False
        findings = sc.verification_findings("HAZ-01", verification)
        self.assertEqual(len(findings), 1)
        self.assertIn("still open", findings[0])

    def test_blank_closure_reference_is_flagged(self):
        verification = _clean_verification()
        verification["closure_reference"] = "   "
        findings = sc.verification_findings("HAZ-01", verification)
        self.assertTrue(any("closure reference" in f for f in findings))

    def test_every_recognized_method_is_accepted(self):
        for method in sorted(sc.RECOGNIZED_VERIFICATION_METHODS):
            verification = _clean_verification()
            verification["method"] = method
            self.assertEqual(
                sc.verification_findings("HAZ-01", verification), []
            )

    def test_unrecognized_method_raises(self):
        verification = _clean_verification()
        verification["method"] = "vibes_based_assurance"
        with self.assertRaises(ValueError):
            sc.verification_findings("HAZ-01", verification)

    def test_missing_verification_key_raises(self):
        verification = _clean_verification()
        del verification["closed"]
        with self.assertRaises(ValueError):
            sc.verification_findings("HAZ-01", verification)


class ReviewHazardTest(unittest.TestCase):
    def test_clean_hazard_is_conformant(self):
        review = sc.review_hazard(_clean_hazard())
        self.assertTrue(review["conformant"])
        self.assertEqual(review["family"], "stored_energy")
        self.assertEqual(review["severity"], "critical")

    def test_review_reports_the_required_counts(self):
        review = sc.review_hazard(_clean_hazard())
        self.assertEqual(review["required_failure_tolerance"], 1)
        self.assertEqual(review["required_independent_inhibits"], 2)

    def test_missing_verification_record_is_a_finding(self):
        hazard = _clean_hazard()
        del hazard["verification"]
        review = sc.review_hazard(hazard)
        self.assertFalse(review["conformant"])
        self.assertEqual(len(review["verification_findings"]), 1)

    def test_hazard_without_stored_energy_skips_that_check(self):
        hazard = _clean_hazard()
        del hazard["stored_energy"]
        review = sc.review_hazard(hazard)
        self.assertEqual(review["stored_energy_findings"], [])
        self.assertTrue(review["conformant"])

    def test_catastrophic_consequence_raises_the_inhibit_bar(self):
        hazard = _clean_hazard()
        hazard["consequence"] = "loss_of_life_or_vehicle"
        review = sc.review_hazard(hazard)
        self.assertEqual(review["required_independent_inhibits"], 3)
        self.assertFalse(review["conformant"])

    def test_missing_hazard_key_raises(self):
        hazard = _clean_hazard()
        del hazard["consequence"]
        with self.assertRaises(ValueError):
            sc.review_hazard(hazard)


class AggregateSafetyConformanceTest(unittest.TestCase):
    def _clean_subsystem(self):
        second = _clean_hazard()
        second["hazard_id"] = "HAZ-02"
        second["hazard_kind"] = "exposed_live_conductor"
        del second["stored_energy"]
        return {
            "subsystem_id": "EPS-PAYLOAD-A",
            "hazards": [_clean_hazard(), second],
        }

    def test_clean_subsystem_is_conformant(self):
        review = sc.aggregate_safety_conformance_review(self._clean_subsystem())
        self.assertTrue(review["conformant"])
        self.assertEqual(review["findings"], [])
        self.assertEqual(len(review["hazard_reviews"]), 2)

    def test_subsystem_without_hazards_is_conformant(self):
        review = sc.aggregate_safety_conformance_review(
            {"subsystem_id": "EPS-B"}
        )
        self.assertTrue(review["conformant"])

    def test_one_open_verification_breaks_conformance(self):
        subsystem = self._clean_subsystem()
        subsystem["hazards"][1]["verification"]["closed"] = False
        review = sc.aggregate_safety_conformance_review(subsystem)
        self.assertFalse(review["conformant"])
        self.assertEqual(len(review["findings"]), 1)

    def test_one_short_inhibit_set_breaks_conformance(self):
        subsystem = self._clean_subsystem()
        subsystem["hazards"][0]["inhibits"] = []
        review = sc.aggregate_safety_conformance_review(subsystem)
        self.assertFalse(review["conformant"])
        self.assertTrue(review["findings"])

    def test_findings_are_flattened_across_hazards(self):
        subsystem = self._clean_subsystem()
        subsystem["hazards"][0]["inhibits"] = []
        subsystem["hazards"][1]["verification"]["closed"] = False
        review = sc.aggregate_safety_conformance_review(subsystem)
        self.assertEqual(len(review["findings"]), 2)

    def test_missing_subsystem_id_raises(self):
        with self.assertRaises(ValueError):
            sc.aggregate_safety_conformance_review({"hazards": []})

    def test_subsystem_id_is_echoed(self):
        review = sc.aggregate_safety_conformance_review(self._clean_subsystem())
        self.assertEqual(review["subsystem_id"], "EPS-PAYLOAD-A")


if __name__ == "__main__":
    unittest.main()
