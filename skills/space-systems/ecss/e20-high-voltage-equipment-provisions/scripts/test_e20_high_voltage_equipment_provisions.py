#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 5.10 high voltage
equipment provisions.

Exercises scripts/e20_high_voltage_equipment_provisions_logic.py
(stdlib unittest, offline). Contract: every operating state maps to
exactly one ambient regime and an unrecognized state raises; the
provision bites only on hardware that is neither encapsulated nor
sealed and pressurised; the Paschen model returns the analytic minimum
where the curve says it should, rises on both sides of it and goes to
infinity on the low-pressure branch; the critical pressure window is
the band whose edges reproduce the applied voltage exactly, is None
when the applied voltage never reaches the minimum, and scales
inversely with the gap; an ambient pressure at either edge counts as
inside; the venting profile decays exponentially and the time to a
target pressure is its exact inverse; an item is flagged when it
operates inside the window, when no energisation inhibit is on record,
when the inhibit releases above the lower edge, when the breakdown
margin is short, or when energisation is released before the enclosure
falls clear; and the equipment is compliant only when no item carries
a finding.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_high_voltage_equipment_provisions_logic as hv  # noqa: E402

GAP_M = 0.001
APPLIED_V = 1500.0


def _window():
    return hv.critical_pressure_window(GAP_M, APPLIED_V)


def _clean_profile():
    return {
        "initial_pressure_pa": hv.SEA_LEVEL_PRESSURE_PA,
        "time_constant_s": 60.0,
        "inhibit_release_time_s": 600.0,
    }


def _clean_item():
    """An unpotted, unpressurised item that satisfies every clause 5.10
    check."""
    return {
        "item_id": "HV-EPC-01",
        "operating_state": "on_orbit_vacuum",
        "applied_voltage_v": APPLIED_V,
        "gap_m": GAP_M,
        "potted": False,
        "pressurised": False,
        "operating_pressure_pa": 1.0e-4,
        "energisation_inhibit_pressure_pa": 10.0,
        "required_voltage_margin": 2.0,
        "precautions": [
            "energisation_inhibit_below_critical_range",
            "corona_free_clearance_margin",
        ],
    }


class CategorizeHvOperatingStateTest(unittest.TestCase):
    def test_ground_ambient_is_dense_gas(self):
        self.assertEqual(
            hv.categorize_hv_operating_state("ground_ambient"), "dense_gas"
        )

    def test_ascent_is_transitional(self):
        self.assertEqual(
            hv.categorize_hv_operating_state("launch_ascent_depressurisation"),
            "transitional_pressure",
        )

    def test_outgassing_phase_is_transitional(self):
        self.assertEqual(
            hv.categorize_hv_operating_state("early_orbit_outgassing"),
            "transitional_pressure",
        )

    def test_on_orbit_is_vacuum(self):
        self.assertEqual(
            hv.categorize_hv_operating_state("on_orbit_vacuum"), "vacuum"
        )

    def test_every_state_maps_to_a_known_regime(self):
        self.assertEqual(
            set(hv.OPERATING_STATE_REGIMES.values()),
            {"dense_gas", "transitional_pressure", "vacuum"},
        )

    def test_unrecognized_state_raises(self):
        with self.assertRaises(ValueError):
            hv.categorize_hv_operating_state("somewhere_out_there")

    def test_unhashable_state_raises_value_error(self):
        with self.assertRaises(ValueError):
            hv.categorize_hv_operating_state(["on_orbit_vacuum"])


class ClauseAppliesTest(unittest.TestCase):
    def test_unpotted_unpressurised_hardware_is_in_scope(self):
        self.assertTrue(hv.clause_applies(False, False))

    def test_potted_hardware_is_out_of_scope(self):
        self.assertFalse(hv.clause_applies(True, False))

    def test_pressurised_hardware_is_out_of_scope(self):
        self.assertFalse(hv.clause_applies(False, True))

    def test_potted_and_pressurised_hardware_is_out_of_scope(self):
        self.assertFalse(hv.clause_applies(True, True))


class PaschenModelTest(unittest.TestCase):
    def test_minimum_voltage_is_coefficient_b_times_the_product(self):
        product_min, voltage_min = hv.paschen_minimum()
        self.assertAlmostEqual(
            voltage_min, hv.PASCHEN_B_V_PER_PA_M * product_min, places=9
        )

    def test_minimum_product_follows_the_analytic_relation(self):
        product_min, _ = hv.paschen_minimum()
        expected = (
            math.e
            * math.log(1.0 + 1.0 / hv.SECONDARY_EMISSION_COEFFICIENT)
            / hv.PASCHEN_A_PER_PA_M
        )
        self.assertAlmostEqual(product_min, expected, places=12)

    def test_breakdown_at_the_minimum_matches_the_minimum_voltage(self):
        product_min, voltage_min = hv.paschen_minimum()
        self.assertAlmostEqual(
            hv.paschen_breakdown_voltage(product_min / GAP_M, GAP_M),
            voltage_min,
            places=6,
        )

    def test_breakdown_rises_above_the_minimum_on_the_dense_side(self):
        product_min, voltage_min = hv.paschen_minimum()
        self.assertGreater(
            hv.paschen_breakdown_voltage(10.0 * product_min / GAP_M, GAP_M),
            voltage_min,
        )

    def test_breakdown_rises_above_the_minimum_on_the_rarefied_side(self):
        product_min, voltage_min = hv.paschen_minimum()
        self.assertGreater(
            hv.paschen_breakdown_voltage(0.5 * product_min / GAP_M, GAP_M),
            voltage_min,
        )

    def test_low_pressure_branch_is_unbreakable(self):
        self.assertEqual(
            hv.paschen_breakdown_voltage(1.0e-6, GAP_M), math.inf
        )

    def test_a_larger_secondary_emission_lowers_the_minimum(self):
        _, base = hv.paschen_minimum()
        _, easier = hv.paschen_minimum(secondary_emission=0.1)
        self.assertLess(easier, base)

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            hv.paschen_breakdown_voltage(0.0, GAP_M)

    def test_non_positive_gap_raises(self):
        with self.assertRaises(ValueError):
            hv.paschen_breakdown_voltage(100.0, 0.0)

    def test_non_positive_coefficient_a_raises(self):
        with self.assertRaises(ValueError):
            hv.paschen_breakdown_voltage(100.0, GAP_M, coefficient_a=0.0)

    def test_non_positive_coefficient_b_raises(self):
        with self.assertRaises(ValueError):
            hv.paschen_breakdown_voltage(100.0, GAP_M, coefficient_b=-1.0)

    def test_non_positive_secondary_emission_raises(self):
        with self.assertRaises(ValueError):
            hv.paschen_breakdown_voltage(100.0, GAP_M, secondary_emission=0.0)

    def test_minimum_raises_on_a_bad_coefficient(self):
        with self.assertRaises(ValueError):
            hv.paschen_minimum(coefficient_a=0.0)


class CriticalWindowTest(unittest.TestCase):
    def test_window_is_an_ordered_pair(self):
        low, high = _window()
        self.assertGreater(low, 0.0)
        self.assertGreater(high, low)

    def test_lower_edge_reproduces_the_applied_voltage(self):
        low, _high = _window()
        self.assertAlmostEqual(
            hv.paschen_breakdown_voltage(low, GAP_M), APPLIED_V, places=6
        )

    def test_upper_edge_reproduces_the_applied_voltage(self):
        _low, high = _window()
        self.assertAlmostEqual(
            hv.paschen_breakdown_voltage(high, GAP_M), APPLIED_V, places=6
        )

    def test_the_minimum_sits_inside_the_window(self):
        low, high = _window()
        product_min, _ = hv.paschen_minimum()
        self.assertGreater(product_min / GAP_M, low)
        self.assertLess(product_min / GAP_M, high)

    def test_no_window_below_the_curve_minimum(self):
        _, voltage_min = hv.paschen_minimum()
        self.assertIsNone(
            hv.critical_pressure_window(GAP_M, 0.999 * voltage_min)
        )

    def test_window_collapses_to_a_point_at_the_minimum(self):
        _, voltage_min = hv.paschen_minimum()
        window = hv.critical_pressure_window(GAP_M, voltage_min)
        self.assertIsNotNone(window)
        product_min, _ = hv.paschen_minimum()
        self.assertAlmostEqual(window[0], product_min / GAP_M, places=6)
        self.assertAlmostEqual(window[1], product_min / GAP_M, places=6)

    def test_window_scales_inversely_with_the_gap(self):
        low_one, high_one = hv.critical_pressure_window(GAP_M, APPLIED_V)
        low_two, high_two = hv.critical_pressure_window(2.0 * GAP_M, APPLIED_V)
        self.assertAlmostEqual(low_two, 0.5 * low_one, places=9)
        self.assertAlmostEqual(high_two, 0.5 * high_one, places=9)

    def test_non_positive_gap_raises(self):
        with self.assertRaises(ValueError):
            hv.critical_pressure_window(0.0, APPLIED_V)

    def test_non_positive_applied_voltage_raises(self):
        with self.assertRaises(ValueError):
            hv.critical_pressure_window(GAP_M, 0.0)

    def test_voltage_above_the_low_pressure_branch_raises(self):
        with self.assertRaises(ValueError):
            hv.critical_pressure_window(GAP_M, 1.0e12)


class WithinCriticalRangeTest(unittest.TestCase):
    def test_pressure_inside_the_window_is_inside(self):
        self.assertTrue(hv.is_within_critical_pressure_range(500.0, _window()))

    def test_lower_edge_counts_as_inside(self):
        window = _window()
        self.assertTrue(
            hv.is_within_critical_pressure_range(window[0], window)
        )

    def test_upper_edge_counts_as_inside(self):
        window = _window()
        self.assertTrue(
            hv.is_within_critical_pressure_range(window[1], window)
        )

    def test_pressure_below_the_window_is_outside(self):
        window = _window()
        self.assertFalse(
            hv.is_within_critical_pressure_range(0.5 * window[0], window)
        )

    def test_pressure_above_the_window_is_outside(self):
        window = _window()
        self.assertFalse(
            hv.is_within_critical_pressure_range(2.0 * window[1], window)
        )

    def test_a_window_of_none_is_never_entered(self):
        self.assertFalse(hv.is_within_critical_pressure_range(500.0, None))

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            hv.is_within_critical_pressure_range(0.0, _window())

    def test_malformed_window_raises(self):
        with self.assertRaises(ValueError):
            hv.is_within_critical_pressure_range(500.0, (2000.0, 40.0))


class DepressurisationMathTest(unittest.TestCase):
    def test_no_venting_leaves_the_initial_pressure(self):
        self.assertAlmostEqual(
            hv.depressurisation_pressure(hv.SEA_LEVEL_PRESSURE_PA, 60.0, 0.0),
            hv.SEA_LEVEL_PRESSURE_PA,
            places=6,
        )

    def test_one_time_constant_leaves_one_over_e(self):
        self.assertAlmostEqual(
            hv.depressurisation_pressure(hv.SEA_LEVEL_PRESSURE_PA, 60.0, 60.0),
            hv.SEA_LEVEL_PRESSURE_PA / math.e,
            places=6,
        )

    def test_negative_elapsed_time_raises(self):
        with self.assertRaises(ValueError):
            hv.depressurisation_pressure(hv.SEA_LEVEL_PRESSURE_PA, 60.0, -1.0)

    def test_non_positive_time_constant_raises(self):
        with self.assertRaises(ValueError):
            hv.depressurisation_pressure(hv.SEA_LEVEL_PRESSURE_PA, 0.0, 10.0)

    def test_non_positive_initial_pressure_raises(self):
        with self.assertRaises(ValueError):
            hv.depressurisation_pressure(0.0, 60.0, 10.0)

    def test_time_to_pressure_inverts_the_decay(self):
        seconds = hv.time_to_pressure(hv.SEA_LEVEL_PRESSURE_PA, 50.0, 60.0)
        self.assertAlmostEqual(
            hv.depressurisation_pressure(
                hv.SEA_LEVEL_PRESSURE_PA, 60.0, seconds
            ),
            50.0,
            places=9,
        )

    def test_already_low_enough_needs_no_time(self):
        self.assertAlmostEqual(
            hv.time_to_pressure(10.0, 50.0, 60.0), 0.0, places=12
        )

    def test_non_positive_target_raises(self):
        with self.assertRaises(ValueError):
            hv.time_to_pressure(hv.SEA_LEVEL_PRESSURE_PA, 0.0, 60.0)

    def test_non_positive_time_constant_raises_in_time_to_pressure(self):
        with self.assertRaises(ValueError):
            hv.time_to_pressure(hv.SEA_LEVEL_PRESSURE_PA, 50.0, 0.0)


class DepressurisationFindingsTest(unittest.TestCase):
    def test_generous_release_time_has_no_findings(self):
        self.assertEqual(
            hv.depressurisation_findings("HV-1", _clean_profile(), _window()),
            [],
        )

    def test_release_exactly_at_the_clearing_time_passes(self):
        window = _window()
        profile = _clean_profile()
        profile["inhibit_release_time_s"] = hv.time_to_pressure(
            profile["initial_pressure_pa"],
            window[0],
            profile["time_constant_s"],
        )
        self.assertEqual(
            hv.depressurisation_findings("HV-1", profile, window), []
        )

    def test_early_release_is_flagged_twice(self):
        profile = _clean_profile()
        profile["inhibit_release_time_s"] = 100.0
        findings = hv.depressurisation_findings("HV-1", profile, _window())
        self.assertEqual(len(findings), 2)
        self.assertTrue(any("before the" in f for f in findings))
        self.assertTrue(any("lower edge" in f for f in findings))

    def test_no_window_means_no_profile_finding(self):
        profile = _clean_profile()
        profile["inhibit_release_time_s"] = 0.0
        self.assertEqual(hv.depressurisation_findings("HV-1", profile, None), [])

    def test_missing_profile_key_raises(self):
        profile = _clean_profile()
        del profile["time_constant_s"]
        with self.assertRaises(ValueError):
            hv.depressurisation_findings("HV-1", profile, _window())

    def test_negative_release_time_raises(self):
        profile = _clean_profile()
        profile["inhibit_release_time_s"] = -1.0
        with self.assertRaises(ValueError):
            hv.depressurisation_findings("HV-1", profile, _window())


class HvItemFindingsTest(unittest.TestCase):
    def test_clean_item_has_no_findings(self):
        self.assertEqual(hv.hv_item_findings(_clean_item()), [])

    def test_potted_item_is_out_of_scope(self):
        item = _clean_item()
        item["potted"] = True
        item["operating_pressure_pa"] = 500.0
        item["energisation_inhibit_pressure_pa"] = None
        self.assertEqual(hv.hv_item_findings(item), [])

    def test_pressurised_item_is_out_of_scope(self):
        item = _clean_item()
        item["pressurised"] = True
        item["operating_pressure_pa"] = 500.0
        self.assertEqual(hv.hv_item_findings(item), [])

    def test_operating_inside_the_window_is_flagged(self):
        item = _clean_item()
        item["operating_state"] = "planetary_low_pressure_atmosphere"
        item["operating_pressure_pa"] = 500.0
        findings = hv.hv_item_findings(item)
        self.assertTrue(any("critical" in f for f in findings))

    def test_missing_inhibit_is_flagged(self):
        item = _clean_item()
        item["energisation_inhibit_pressure_pa"] = None
        findings = hv.hv_item_findings(item)
        self.assertEqual(len(findings), 1)
        self.assertIn("no energisation inhibit", findings[0])

    def test_inhibit_above_the_lower_edge_is_flagged(self):
        item = _clean_item()
        item["energisation_inhibit_pressure_pa"] = 1000.0
        findings = hv.hv_item_findings(item)
        self.assertEqual(len(findings), 1)
        self.assertIn("lower edge", findings[0])

    def test_inhibit_exactly_at_the_lower_edge_passes(self):
        item = _clean_item()
        item["energisation_inhibit_pressure_pa"] = _window()[0]
        self.assertEqual(hv.hv_item_findings(item), [])

    def test_short_breakdown_margin_is_flagged(self):
        item = _clean_item()
        item["operating_state"] = "planetary_low_pressure_atmosphere"
        item["operating_pressure_pa"] = 3000.0
        findings = hv.hv_item_findings(item)
        self.assertEqual(len(findings), 1)
        self.assertIn("breakdown margin", findings[0])

    def test_a_margin_of_one_accepts_the_same_point(self):
        item = _clean_item()
        item["operating_state"] = "planetary_low_pressure_atmosphere"
        item["operating_pressure_pa"] = 3000.0
        item["required_voltage_margin"] = 1.0
        self.assertEqual(hv.hv_item_findings(item), [])

    def test_attached_profile_is_checked(self):
        item = _clean_item()
        profile = _clean_profile()
        profile["inhibit_release_time_s"] = 100.0
        item["depressurisation_profile"] = profile
        findings = hv.hv_item_findings(item)
        self.assertEqual(len(findings), 2)

    def test_unrecognized_operating_state_raises(self):
        item = _clean_item()
        item["operating_state"] = "under_the_sea"
        with self.assertRaises(ValueError):
            hv.hv_item_findings(item)

    def test_missing_item_key_raises(self):
        item = _clean_item()
        del item["gap_m"]
        with self.assertRaises(ValueError):
            hv.hv_item_findings(item)

    def test_margin_below_one_raises(self):
        item = _clean_item()
        item["required_voltage_margin"] = 0.5
        with self.assertRaises(ValueError):
            hv.hv_item_findings(item)

    def test_non_positive_operating_pressure_raises(self):
        item = _clean_item()
        item["operating_pressure_pa"] = 0.0
        with self.assertRaises(ValueError):
            hv.hv_item_findings(item)

    def test_non_positive_inhibit_pressure_raises(self):
        item = _clean_item()
        item["energisation_inhibit_pressure_pa"] = -1.0
        with self.assertRaises(ValueError):
            hv.hv_item_findings(item)


class DeclaredPrecautionsTest(unittest.TestCase):
    def test_a_declared_precaution_is_enough(self):
        self.assertEqual(
            hv.declared_precaution_findings(
                "HV-1", ["encapsulation_potting"]
            ),
            [],
        )

    def test_every_recognized_precaution_is_accepted(self):
        for precaution in sorted(hv.RECOGNIZED_HV_PRECAUTIONS):
            self.assertEqual(
                hv.declared_precaution_findings("HV-1", [precaution]), []
            )

    def test_no_precaution_is_flagged(self):
        findings = hv.declared_precaution_findings("HV-1", [])
        self.assertEqual(len(findings), 1)
        self.assertIn("no high voltage design precaution", findings[0])

    def test_unrecognized_precaution_raises(self):
        with self.assertRaises(ValueError):
            hv.declared_precaution_findings("HV-1", ["cross_fingers"])


class AggregateHvProvisionsTest(unittest.TestCase):
    def _clean_equipment(self):
        second = _clean_item()
        second["item_id"] = "HV-EPC-02"
        second["potted"] = True
        return {
            "equipment_id": "TWTA-HV-SET",
            "items": [_clean_item(), second],
        }

    def test_clean_equipment_is_compliant(self):
        review = hv.aggregate_hv_provisions_review(self._clean_equipment())
        self.assertTrue(review["compliant"])
        self.assertEqual(review["findings"], [])

    def test_equipment_without_items_is_compliant(self):
        review = hv.aggregate_hv_provisions_review({"equipment_id": "EMPTY"})
        self.assertTrue(review["compliant"])

    def test_findings_are_keyed_by_item(self):
        equipment = self._clean_equipment()
        equipment["items"][0]["energisation_inhibit_pressure_pa"] = None
        review = hv.aggregate_hv_provisions_review(equipment)
        self.assertFalse(review["compliant"])
        self.assertEqual(len(review["item_findings"]["HV-EPC-01"]), 1)
        self.assertEqual(review["item_findings"]["HV-EPC-02"], [])

    def test_missing_precautions_break_compliance(self):
        equipment = self._clean_equipment()
        equipment["items"][1]["precautions"] = []
        review = hv.aggregate_hv_provisions_review(equipment)
        self.assertFalse(review["compliant"])
        self.assertEqual(len(review["findings"]), 1)

    def test_equipment_id_is_echoed(self):
        review = hv.aggregate_hv_provisions_review(self._clean_equipment())
        self.assertEqual(review["equipment_id"], "TWTA-HV-SET")

    def test_missing_equipment_id_raises(self):
        with self.assertRaises(ValueError):
            hv.aggregate_hv_provisions_review({"items": []})

    def test_missing_item_id_raises(self):
        equipment = self._clean_equipment()
        del equipment["items"][0]["item_id"]
        with self.assertRaises(ValueError):
            hv.aggregate_hv_provisions_review(equipment)


if __name__ == "__main__":
    unittest.main()
