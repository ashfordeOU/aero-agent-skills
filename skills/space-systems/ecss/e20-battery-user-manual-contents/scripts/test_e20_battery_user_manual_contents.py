#!/usr/bin/env python3
"""Gate 3 contract test for e20-battery-user-manual-contents.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e20_battery_user_manual_contents.py
"""

import unittest

import e20_battery_user_manual_contents_logic as logic


def envelope(**over):
    rec = {
        "cells_in_series": 8,
        "min_cell_voltage_v": 3.00,
        "max_cell_voltage_v": 4.10,
        "charge_termination_voltage_v": 4.10,
        "min_temperature_c": -5.0,
        "max_temperature_c": 40.0,
    }
    rec.update(over)
    return rec


def storage(**over):
    rec = {
        "state_of_charge_pct": 40.0,
        "temperature_c": 10.0,
        "recharge_interval_days": 90.0,
    }
    rec.update(over)
    return rec


def charge_control(**over):
    rec = {
        "mode": "constant-current-constant-voltage",
        "charge_rate_c": 0.30,
        "max_charge_rate_c": 0.50,
        "termination_criterion": "voltage-and-taper-current",
        "cell_balancing_procedure": "dissipative top-of-charge balancing",
    }
    rec.update(over)
    return rec


def life(**over):
    rec = {
        "cycle_life_cycles": 30000.0,
        "cycle_life_dod_pct": 25.0,
        "calendar_life_years": 8.0,
    }
    rec.update(over)
    return rec


def duty_profile(**over):
    rec = {
        "orbits_per_day": 15.0,
        "mission_years": 5.0,
        "eclipse_fraction": 0.60,
        "operating_dod_pct": 20.0,
        "storage_years": 1.0,
    }
    rec.update(over)
    return rec


def manual(**over):
    rec = {
        "chapters": list(logic.REQUIRED_CHAPTERS),
        "chemistry": "lithium-ion",
        "operating_envelope": envelope(),
        "storage": storage(),
        "charge_control": charge_control(),
        "life": life(),
        "duty_profile": duty_profile(),
        "safety_topics": list(logic.REQUIRED_SAFETY_TOPICS),
    }
    rec.update(over)
    return rec


class TestChapterCoverage(unittest.TestCase):
    def test_full_chapter_list_has_no_gap(self):
        out = logic.check_chapter_coverage(list(logic.REQUIRED_CHAPTERS))
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["duplicates"], [])

    def test_optional_chapter_is_allowed(self):
        out = logic.check_chapter_coverage(
            list(logic.REQUIRED_CHAPTERS) + ["monitoring-and-telemetry"]
        )
        self.assertEqual(out["missing"], [])

    def test_absent_mandated_chapter_is_reported(self):
        chapters = [c for c in logic.REQUIRED_CHAPTERS if c != "transport-and-shipping"]
        out = logic.check_chapter_coverage(chapters)
        self.assertEqual(out["missing"], ["transport-and-shipping"])

    def test_duplicated_chapter_is_reported(self):
        chapters = list(logic.REQUIRED_CHAPTERS) + ["operating-envelope"]
        out = logic.check_chapter_coverage(chapters)
        self.assertEqual(out["duplicates"], ["operating-envelope"])

    def test_free_form_heading_is_normalized(self):
        out = logic.check_chapter_coverage(
            ["Operating Envelope", "Safety_and_Hazard_Precautions"]
        )
        self.assertNotIn("operating-envelope", out["missing"])
        self.assertNotIn("safety-and-hazard-precautions", out["missing"])

    def test_uncategorized_chapter_raises(self):
        with self.assertRaises(ValueError):
            logic.check_chapter_coverage(["operating-envelope", "marketing-overview"])

    def test_blank_chapter_name_raises(self):
        with self.assertRaises(ValueError):
            logic.check_chapter_coverage(["  "])

    def test_non_list_chapters_raises(self):
        with self.assertRaises(ValueError):
            logic.check_chapter_coverage("operating-envelope")


class TestChemistry(unittest.TestCase):
    def test_lithium_ion_window_resolves(self):
        data = logic.chemistry_data("lithium-ion")
        self.assertAlmostEqual(data["cell_max_v"], 4.20)

    def test_chemistry_label_is_normalized(self):
        data = logic.chemistry_data("Lithium Ion")
        self.assertEqual(data["chemistry"], "lithium-ion")

    def test_nickel_chemistry_stores_near_flat(self):
        data = logic.chemistry_data("nickel-hydrogen")
        self.assertAlmostEqual(data["storage_soc_pct"][1], 20.0)

    def test_uncategorized_chemistry_raises(self):
        with self.assertRaises(ValueError):
            logic.chemistry_data("sodium-sulphur")

    def test_non_string_chemistry_raises(self):
        with self.assertRaises(ValueError):
            logic.chemistry_data(None)


class TestOperatingEnvelope(unittest.TestCase):
    def test_consistent_envelope_has_no_finding(self):
        out = logic.validate_operating_envelope(envelope(), "lithium-ion")
        self.assertEqual(out["findings"], [])

    def test_envelope_is_scaled_by_the_series_count(self):
        out = logic.validate_operating_envelope(envelope(), "lithium-ion")
        self.assertAlmostEqual(out["assembly_max_voltage_v"], 32.8)
        self.assertAlmostEqual(out["assembly_min_voltage_v"], 24.0)

    def test_termination_exactly_at_the_envelope_maximum_is_the_design_point(self):
        out = logic.validate_operating_envelope(
            envelope(charge_termination_voltage_v=4.10), "lithium-ion"
        )
        self.assertEqual(out["findings"], [])

    def test_termination_a_few_ulps_over_by_representation_is_absorbed(self):
        # 0.9 + 3.2 lands a few ULPs above 4.1; the physical case is the
        # declared envelope maximum and must not be read as an exceedance.
        v_term = 0.9 + 3.2
        self.assertGreater(v_term, 4.10)
        out = logic.validate_operating_envelope(
            envelope(charge_termination_voltage_v=v_term), "lithium-ion"
        )
        self.assertEqual(out["findings"], [])

    def test_termination_above_the_envelope_is_a_finding(self):
        out = logic.validate_operating_envelope(
            envelope(charge_termination_voltage_v=4.25, max_cell_voltage_v=4.2),
            "lithium-ion",
        )
        self.assertIn(
            "charge-termination-voltage outside the declared envelope", out["findings"]
        )

    def test_cell_voltage_outside_the_chemistry_window_is_a_finding(self):
        out = logic.validate_operating_envelope(
            envelope(max_cell_voltage_v=4.30, charge_termination_voltage_v=4.30),
            "lithium-ion",
        )
        self.assertIn("max_cell_voltage_v outside the chemistry window", out["findings"])

    def test_high_voltage_chemistry_accepts_the_same_envelope(self):
        out = logic.validate_operating_envelope(
            envelope(max_cell_voltage_v=4.30, charge_termination_voltage_v=4.30),
            "lithium-ion-high-voltage",
        )
        self.assertEqual(out["findings"], [])

    def test_inverted_voltage_envelope_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope(
                envelope(min_cell_voltage_v=4.2, max_cell_voltage_v=3.0), "lithium-ion"
            )

    def test_inverted_temperature_envelope_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope(
                envelope(min_temperature_c=40.0, max_temperature_c=-5.0), "lithium-ion"
            )

    def test_zero_series_count_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope(envelope(cells_in_series=0), "lithium-ion")

    def test_non_integer_series_count_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope(envelope(cells_in_series=8.5), "lithium-ion")

    def test_missing_envelope_key_raises(self):
        rec = envelope()
        del rec["charge_termination_voltage_v"]
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope(rec, "lithium-ion")

    def test_non_mapping_envelope_raises(self):
        with self.assertRaises(ValueError):
            logic.validate_operating_envelope([3.0, 4.1], "lithium-ion")


class TestStorageRegime(unittest.TestCase):
    def test_regime_inside_the_band_has_no_finding(self):
        self.assertEqual(logic.check_storage_regime(storage(), "lithium-ion")["findings"], [])

    def test_state_of_charge_on_the_band_edge_is_accepted(self):
        out = logic.check_storage_regime(storage(state_of_charge_pct=30.0), "lithium-ion")
        self.assertEqual(out["findings"], [])

    def test_full_state_of_charge_storage_is_a_finding(self):
        out = logic.check_storage_regime(storage(state_of_charge_pct=100.0), "lithium-ion")
        self.assertIn("storage state-of-charge outside the chemistry band", out["findings"])

    def test_warm_storage_is_a_finding(self):
        out = logic.check_storage_regime(storage(temperature_c=35.0), "lithium-ion")
        self.assertIn("storage temperature outside the chemistry band", out["findings"])

    def test_recharge_interval_beyond_dormancy_is_a_finding(self):
        out = logic.check_storage_regime(
            storage(recharge_interval_days=400.0), "lithium-ion"
        )
        self.assertIn("recharge interval exceeds the tolerated dormancy", out["findings"])

    def test_nickel_chemistry_accepts_a_flat_storage_state(self):
        out = logic.check_storage_regime(
            storage(state_of_charge_pct=5.0, temperature_c=0.0, recharge_interval_days=60.0),
            "nickel-cadmium",
        )
        self.assertEqual(out["findings"], [])

    def test_state_of_charge_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            logic.check_storage_regime(storage(state_of_charge_pct=120.0), "lithium-ion")

    def test_negative_state_of_charge_raises(self):
        with self.assertRaises(ValueError):
            logic.check_storage_regime(storage(state_of_charge_pct=-1.0), "lithium-ion")

    def test_zero_recharge_interval_raises(self):
        with self.assertRaises(ValueError):
            logic.check_storage_regime(storage(recharge_interval_days=0.0), "lithium-ion")

    def test_missing_storage_key_raises(self):
        rec = storage()
        del rec["temperature_c"]
        with self.assertRaises(ValueError):
            logic.check_storage_regime(rec, "lithium-ion")


class TestChargeControl(unittest.TestCase):
    def test_valid_control_chapter_has_no_finding(self):
        self.assertEqual(logic.check_charge_control(charge_control(), 8)["findings"], [])

    def test_rate_equal_to_the_maximum_is_accepted(self):
        out = logic.check_charge_control(charge_control(charge_rate_c=0.50), 8)
        self.assertEqual(out["findings"], [])

    def test_rate_above_the_maximum_is_a_finding(self):
        out = logic.check_charge_control(charge_control(charge_rate_c=0.90), 8)
        self.assertIn("declared charge rate exceeds the declared maximum", out["findings"])

    def test_series_stack_without_balancing_is_a_finding(self):
        rec = charge_control()
        del rec["cell_balancing_procedure"]
        out = logic.check_charge_control(rec, 8)
        self.assertIn("cell-balancing-procedure absent for a series stack", out["findings"])

    def test_single_cell_needs_no_balancing(self):
        rec = charge_control()
        del rec["cell_balancing_procedure"]
        out = logic.check_charge_control(rec, 1)
        self.assertEqual(out["findings"], [])

    def test_uncategorized_charge_mode_raises(self):
        with self.assertRaises(ValueError):
            logic.check_charge_control(charge_control(mode="fast-charge"), 8)

    def test_zero_charge_rate_raises(self):
        with self.assertRaises(ValueError):
            logic.check_charge_control(charge_control(charge_rate_c=0.0), 8)

    def test_blank_termination_criterion_raises(self):
        with self.assertRaises(ValueError):
            logic.check_charge_control(charge_control(termination_criterion="  "), 8)


class TestDutyProfileAndLife(unittest.TestCase):
    def test_cycle_demand_follows_the_duty_profile(self):
        self.assertAlmostEqual(
            logic.required_cycle_count(15.0, 5.0, 0.60), 15.0 * 365.25 * 5.0 * 0.60
        )

    def test_full_eclipse_fraction_is_allowed(self):
        self.assertAlmostEqual(
            logic.required_cycle_count(15.0, 1.0, 1.0), 15.0 * 365.25
        )

    def test_zero_orbits_per_day_raises(self):
        with self.assertRaises(ValueError):
            logic.required_cycle_count(0.0, 5.0, 0.6)

    def test_eclipse_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.required_cycle_count(15.0, 5.0, 1.4)

    def test_negative_mission_duration_raises(self):
        with self.assertRaises(ValueError):
            logic.required_cycle_count(15.0, -2.0, 0.6)

    def test_sufficient_life_data_has_no_finding(self):
        out = logic.check_life_data(life(), duty_profile())
        self.assertEqual(out["findings"], [])
        self.assertAlmostEqual(out["demanded_cycles"], 16436.25)

    def test_short_cycle_life_is_a_finding(self):
        out = logic.check_life_data(life(cycle_life_cycles=9000.0), duty_profile())
        self.assertIn("declared cycle-life short of the duty-profile demand", out["findings"])

    def test_shallow_declared_depth_is_a_finding(self):
        out = logic.check_life_data(life(cycle_life_dod_pct=10.0), duty_profile())
        self.assertIn(
            "cycle-life declared at a shallower depth-of-discharge-limit", out["findings"]
        )

    def test_short_calendar_life_is_a_finding(self):
        out = logic.check_life_data(life(calendar_life_years=4.0), duty_profile())
        self.assertIn("declared calendar-life short of mission plus storage", out["findings"])

    def test_calendar_life_exactly_covering_mission_plus_storage_is_accepted(self):
        out = logic.check_life_data(
            life(calendar_life_years=6.0), duty_profile(mission_years=5.0, storage_years=1.0)
        )
        self.assertNotIn(
            "declared calendar-life short of mission plus storage", out["findings"]
        )

    def test_summed_years_a_few_ulps_over_by_representation_are_absorbed(self):
        # mission 0.1 y + storage 0.2 y sums a few ULPs above 0.3; a
        # calendar-life declared at exactly 0.3 y is compliant.
        out = logic.check_life_data(
            life(calendar_life_years=0.3),
            duty_profile(mission_years=0.1, storage_years=0.2),
        )
        self.assertGreater(out["total_years"], 0.3)
        self.assertNotIn(
            "declared calendar-life short of mission plus storage", out["findings"]
        )

    def test_zero_cycle_life_raises(self):
        with self.assertRaises(ValueError):
            logic.check_life_data(life(cycle_life_cycles=0.0), duty_profile())

    def test_depth_above_one_hundred_percent_raises(self):
        with self.assertRaises(ValueError):
            logic.check_life_data(life(cycle_life_dod_pct=140.0), duty_profile())

    def test_negative_storage_years_raises(self):
        with self.assertRaises(ValueError):
            logic.check_life_data(life(), duty_profile(storage_years=-1.0))

    def test_missing_duty_profile_key_raises(self):
        rec = duty_profile()
        del rec["operating_dod_pct"]
        with self.assertRaises(ValueError):
            logic.check_life_data(life(), rec)


class TestSafetyTopics(unittest.TestCase):
    def test_full_topic_list_has_no_gap(self):
        self.assertEqual(logic.check_safety_topics(list(logic.REQUIRED_SAFETY_TOPICS)), [])

    def test_absent_topic_is_reported(self):
        topics = [t for t in logic.REQUIRED_SAFETY_TOPICS if t != "thermal-runaway"]
        self.assertEqual(logic.check_safety_topics(topics), ["thermal-runaway"])

    def test_topics_are_normalized(self):
        topics = ["Thermal Runaway"] + [
            t for t in logic.REQUIRED_SAFETY_TOPICS if t != "thermal-runaway"
        ]
        self.assertEqual(logic.check_safety_topics(topics), [])

    def test_non_list_topics_raises(self):
        with self.assertRaises(ValueError):
            logic.check_safety_topics("thermal-runaway")


class TestManualAssessment(unittest.TestCase):
    def test_complete_manual_is_compliant(self):
        out = logic.assess_manual(manual())
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_missing_chapter_blocks_compliance(self):
        chapters = [c for c in logic.REQUIRED_CHAPTERS if c != "life-and-degradation-data"]
        out = logic.assess_manual(manual(chapters=chapters))
        self.assertFalse(out["compliant"])
        self.assertTrue(any(f.startswith("missing-chapters") for f in out["findings"]))

    def test_storage_finding_propagates_to_the_verdict(self):
        out = logic.assess_manual(manual(storage=storage(state_of_charge_pct=95.0)))
        self.assertFalse(out["compliant"])

    def test_life_finding_propagates_to_the_verdict(self):
        out = logic.assess_manual(manual(life=life(cycle_life_cycles=100.0)))
        self.assertFalse(out["compliant"])

    def test_missing_safety_topic_propagates_to_the_verdict(self):
        topics = [t for t in logic.REQUIRED_SAFETY_TOPICS if t != "external-short-circuit"]
        out = logic.assess_manual(manual(safety_topics=topics))
        self.assertFalse(out["compliant"])
        self.assertEqual(out["missing_safety_topics"], ["external-short-circuit"])

    def test_manual_missing_a_top_level_key_raises(self):
        rec = manual()
        del rec["duty_profile"]
        with self.assertRaises(ValueError):
            logic.assess_manual(rec)

    def test_non_mapping_manual_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_manual(["operating-envelope"])


if __name__ == "__main__":
    unittest.main()
