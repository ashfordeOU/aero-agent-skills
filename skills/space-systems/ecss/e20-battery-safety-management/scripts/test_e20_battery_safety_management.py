#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-safety-management (stdlib, offline)."""

import unittest

from e20_battery_safety_management_logic import (
    assess_battery_safety,
    assess_hazard,
    categorize_likelihood,
    categorize_severity,
    compute_risk_index,
    evaluate_inhibit_chain,
    propagation_barrier_margin,
    required_controls,
    validate_battery,
    validate_hazard,
)


def battery(**overrides):
    base = {
        "battery_id": "BAT-A",
        "cell_runaway_onset_c": 130.0,
        "max_predicted_cell_temp_c": 45.0,
        "required_thermal_margin_k": 40.0,
        "cell_to_cell_barrier": True,
        "safety_standard_ref": "product-assurance-space-safety",
    }
    base.update(overrides)
    return base


def inhibits(n, independent=True, verifiable=True):
    return [
        {"inhibit_id": "I%d" % i, "independent": independent, "verifiable": verifiable}
        for i in range(1, n + 1)
    ]


def hazard(**overrides):
    base = {
        "hazard_id": "HZ-01",
        "hazard_type": "overcharge",
        "severity": "catastrophic",
        "likelihood": "improbable",
        "inhibits": inhibits(3),
        "verification_method": "test",
        "containment_provision": False,
        "safety_requirement_ref": "SAF-014",
    }
    base.update(overrides)
    return base


class ScaleTests(unittest.TestCase):
    def test_severity_scale_is_ordered(self):
        self.assertEqual(categorize_severity("negligible"), 0)
        self.assertEqual(categorize_severity("catastrophic"), 3)

    def test_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_severity("very-bad")

    def test_likelihood_scale_is_ordered(self):
        self.assertEqual(categorize_likelihood("improbable"), 0)
        self.assertEqual(categorize_likelihood("frequent"), 4)

    def test_unknown_likelihood_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_likelihood("sometimes")


class BatteryValidationTests(unittest.TestCase):
    def test_nominal_battery_validates(self):
        rec = validate_battery(battery())
        self.assertEqual(rec["battery_id"], "BAT-A")
        self.assertAlmostEqual(rec["cell_runaway_onset_c"], 130.0)

    def test_non_mapping_battery_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_battery("BAT-A")

    def test_missing_battery_field_is_rejected(self):
        bad = battery()
        del bad["cell_to_cell_barrier"]
        with self.assertRaises(ValueError):
            validate_battery(bad)

    def test_blank_safety_standard_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_battery(battery(safety_standard_ref="  "))

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_battery(battery(required_thermal_margin_k=-5.0))

    def test_non_boolean_barrier_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_battery(battery(cell_to_cell_barrier="yes"))


class HazardValidationTests(unittest.TestCase):
    def test_nominal_hazard_validates(self):
        rec = validate_hazard(hazard())
        self.assertEqual(rec["hazard_id"], "HZ-01")
        self.assertEqual(rec["safety_requirement_ref"], "SAF-014")

    def test_unknown_hazard_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(hazard_type="gremlins"))

    def test_unknown_verification_method_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(verification_method="vibes"))

    def test_non_boolean_containment_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(containment_provision=1))

    def test_empty_safety_requirement_reference_normalizes_to_none(self):
        rec = validate_hazard(hazard(safety_requirement_ref=""))
        self.assertIsNone(rec["safety_requirement_ref"])

    def test_non_string_safety_requirement_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_hazard(hazard(safety_requirement_ref=42))


class ControlSizingTests(unittest.TestCase):
    def test_catastrophic_electrical_hazard_demands_three_inhibits(self):
        controls = required_controls("catastrophic", "overcharge")
        self.assertEqual(controls["inhibits"], 3)
        self.assertFalse(controls["containment_required"])
        self.assertFalse(controls["propagation_barrier_required"])

    def test_critical_hazard_demands_two_inhibits(self):
        self.assertEqual(required_controls("critical", "overdischarge")["inhibits"], 2)

    def test_negligible_hazard_demands_no_inhibit(self):
        self.assertEqual(required_controls("negligible", "cell-venting")["inhibits"], 0)

    def test_containment_hazard_trades_one_inhibit_for_containment(self):
        controls = required_controls("critical", "electrolyte-leakage")
        self.assertEqual(controls["inhibits"], 1)
        self.assertTrue(controls["containment_required"])

    def test_propagation_hazard_at_critical_demands_a_barrier(self):
        controls = required_controls("critical", "thermal-runaway")
        self.assertTrue(controls["propagation_barrier_required"])

    def test_propagation_hazard_below_critical_needs_no_barrier(self):
        controls = required_controls("marginal", "thermal-runaway")
        self.assertFalse(controls["propagation_barrier_required"])

    def test_unknown_hazard_type_in_control_sizing_is_rejected(self):
        with self.assertRaises(ValueError):
            required_controls("critical", "ion-storm")


class InhibitChainTests(unittest.TestCase):
    def test_three_sound_inhibits_give_dual_failure_tolerance(self):
        chain = evaluate_inhibit_chain(inhibits(3))
        self.assertEqual(chain["effective"], 3)
        self.assertEqual(chain["fault_tolerance"], 2)
        self.assertEqual(chain["findings"], [])

    def test_empty_chain_has_zero_tolerance(self):
        chain = evaluate_inhibit_chain([])
        self.assertEqual(chain["effective"], 0)
        self.assertEqual(chain["fault_tolerance"], 0)

    def test_dependent_inhibits_do_not_count(self):
        chain = evaluate_inhibit_chain(inhibits(2, independent=False))
        self.assertEqual(chain["effective"], 0)
        self.assertEqual(len(chain["findings"]), 2)

    def test_unverifiable_inhibit_is_flagged_and_discounted(self):
        chain = evaluate_inhibit_chain(inhibits(1, verifiable=False))
        self.assertEqual(chain["effective"], 0)
        self.assertIn("inhibit-not-verifiable:I1", chain["findings"])

    def test_duplicate_inhibit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inhibit_chain(inhibits(1) + inhibits(1))

    def test_non_list_chain_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inhibit_chain("I1,I2,I3")

    def test_non_mapping_chain_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inhibit_chain(["I1"])

    def test_chain_entry_missing_a_field_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inhibit_chain([{"inhibit_id": "I1", "independent": True}])

    def test_blank_inhibit_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_inhibit_chain(
                [{"inhibit_id": " ", "independent": True, "verifiable": True}]
            )


class RiskTests(unittest.TestCase):
    def test_worst_case_pair_is_unacceptable(self):
        index, band = compute_risk_index("catastrophic", "frequent")
        self.assertEqual(index, 20)
        self.assertEqual(band, "unacceptable")

    def test_best_case_pair_is_acceptable(self):
        index, band = compute_risk_index("negligible", "improbable")
        self.assertEqual(index, 1)
        self.assertEqual(band, "acceptable")

    def test_mid_band_pair_is_undesirable(self):
        index, band = compute_risk_index("critical", "occasional")
        self.assertEqual(index, 9)
        self.assertEqual(band, "undesirable")

    def test_rare_catastrophic_pair_needs_review(self):
        index, band = compute_risk_index("catastrophic", "improbable")
        self.assertEqual(index, 4)
        self.assertEqual(band, "acceptable-with-review")

    def test_risk_index_rejects_an_off_scale_severity(self):
        with self.assertRaises(ValueError):
            compute_risk_index("apocalyptic", "remote")


class PropagationTests(unittest.TestCase):
    def test_margin_is_the_gap_to_runaway_onset(self):
        out = propagation_barrier_margin(battery())
        self.assertAlmostEqual(out["margin_k"], 85.0)
        self.assertTrue(out["adequate"])

    def test_margin_exactly_at_the_requirement_is_adequate(self):
        out = propagation_barrier_margin(battery(required_thermal_margin_k=85.0))
        self.assertTrue(out["adequate"])

    def test_margin_below_the_requirement_is_inadequate(self):
        out = propagation_barrier_margin(battery(required_thermal_margin_k=90.0))
        self.assertFalse(out["adequate"])

    def test_absent_barrier_is_inadequate_however_large_the_margin(self):
        out = propagation_barrier_margin(battery(cell_to_cell_barrier=False))
        self.assertAlmostEqual(out["margin_k"], 85.0)
        self.assertFalse(out["adequate"])


class HazardAssessmentTests(unittest.TestCase):
    def test_fully_controlled_hazard_raises_no_finding(self):
        out = assess_hazard(hazard(), battery())
        self.assertTrue(out["controlled"])
        self.assertEqual(out["required_inhibits"], 3)
        self.assertEqual(out["fault_tolerance"], 2)

    def test_short_inhibit_chain_is_flagged(self):
        out = assess_hazard(hazard(inhibits=inhibits(2)), battery())
        self.assertFalse(out["controlled"])
        self.assertIn("insufficient-independent-inhibits:2-of-3", out["findings"])

    def test_missing_product_assurance_link_is_flagged(self):
        out = assess_hazard(hazard(safety_requirement_ref=None), battery())
        self.assertIn("product-assurance-safety-link-missing", out["findings"])

    def test_missing_containment_provision_is_flagged(self):
        out = assess_hazard(
            hazard(
                hazard_type="electrolyte-leakage",
                severity="critical",
                inhibits=inhibits(1),
                containment_provision=False,
            ),
            battery(),
        )
        self.assertIn("containment-provision-missing", out["findings"])

    def test_inadequate_propagation_barrier_is_flagged(self):
        out = assess_hazard(
            hazard(hazard_type="thermal-runaway"),
            battery(cell_to_cell_barrier=False),
        )
        self.assertIn("propagation-barrier-inadequate", out["findings"])
        self.assertIsNotNone(out["propagation_margin"])

    def test_unacceptable_residual_risk_is_flagged(self):
        out = assess_hazard(hazard(likelihood="frequent"), battery())
        self.assertEqual(out["risk_band"], "unacceptable")
        self.assertIn("residual-risk-unacceptable", out["findings"])


class SafetyCaseTests(unittest.TestCase):
    def test_single_controlled_hazard_closes_the_safety_case(self):
        out = assess_battery_safety(battery(), [hazard()])
        self.assertTrue(out["safety_case_closed"])
        self.assertEqual(out["hazard_count"], 1)
        self.assertEqual(out["worst_risk_index"], 4)

    def test_worst_band_is_carried_up_from_the_hazard_list(self):
        out = assess_battery_safety(
            battery(),
            [hazard(), hazard(hazard_id="HZ-02", likelihood="occasional")],
        )
        self.assertEqual(out["worst_risk_index"], 12)
        self.assertEqual(out["worst_risk_band"], "unacceptable")
        self.assertFalse(out["safety_case_closed"])

    def test_empty_hazard_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_battery_safety(battery(), [])

    def test_duplicate_hazard_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_battery_safety(battery(), [hazard(), hazard()])

    def test_findings_are_reported_with_their_hazard_identifier(self):
        out = assess_battery_safety(battery(), [hazard(inhibits=inhibits(1))])
        self.assertTrue(all(f.startswith("HZ-01/") for f in out["open_findings"]))


if __name__ == "__main__":
    unittest.main()
