"""Contract test for the complementary soldering leaf (stdlib unittest)."""

import unittest

from q2030_comp_soldering_logic import (
    COARSE_MAGNIFICATION,
    FLUX_ACTIVATED,
    FLUX_MILDLY_ACTIVATED,
    FLUX_NON_ACTIVATED,
    FLUX_WATER_SOLUBLE,
    MAX_HEAT_APPLICATIONS,
    MAX_TIP_TEMPERATURE_C,
    MAX_WETTING_ANGLE_DEG,
    MIN_DWELL_S,
    MIN_INSULATION_CLEARANCE_MM,
    MIN_LEAD_CONTENT_PERCENT,
    MIN_TIP_TEMPERATURE_C,
    OPERATOR_CERTIFICATION_VALIDITY_DAYS,
    allowable_dwell_s,
    alloy_findings,
    assess_solder_termination,
    assess_soldering_lot,
    flux_findings,
    geometry_findings,
    insulation_clearance_window_mm,
    minimum_inspection_magnification,
    thermal_exposure_budget_s,
    thermal_findings,
    total_thermal_exposure_s,
    validate_termination,
    wetting_findings,
    workmanship_findings,
)


def termination(tid="T-1", **kw):
    record = {
        "id": tid,
        "tin_percent": 60.0,
        "lead_percent": 40.0,
        "whisker_mitigation_plan": False,
        "flux_type": FLUX_MILDLY_ACTIVATED,
        "cleaned_after_soldering": True,
        "cross_section_mm2": 0.38,
        "insulation_diameter_mm": 1.2,
        "insulation_clearance_mm": 0.8,
        "tip_temperature_c": 320.0,
        "dwell_s": 1.0,
        "reheats": 0,
        "wetting_angle_deg": 15.0,
        "inspection_magnification": 10.0,
        "days_since_operator_certification": 100,
    }
    record.update(kw)
    return record


class TestValidateTermination(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_termination(
            {
                "id": "T-1",
                "tin_percent": 60.0,
                "lead_percent": 40.0,
                "flux_type": FLUX_NON_ACTIVATED,
                "cross_section_mm2": 0.25,
                "insulation_diameter_mm": 1.0,
                "tip_temperature_c": 300.0,
                "dwell_s": 1.0,
            }
        )
        self.assertEqual(norm["reheats"], 0)
        self.assertFalse(norm["whisker_mitigation_plan"])
        self.assertEqual(norm["days_since_operator_certification"], 0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(["T-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(""))

    def test_composition_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(tin_percent=70.0, lead_percent=40.0))

    def test_empty_composition_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(tin_percent=0.0, lead_percent=0.0))

    def test_unknown_flux_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(flux_type="lard"))

    def test_zero_cross_section_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(cross_section_mm2=0.0))

    def test_zero_insulation_diameter_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(insulation_diameter_mm=0.0))

    def test_negative_reheats_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(reheats=-1))

    def test_boolean_reheats_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(reheats=True))

    def test_non_integer_certification_age_raises(self):
        with self.assertRaises(ValueError):
            validate_termination(termination(days_since_operator_certification=10.5))


class TestAlloy(unittest.TestCase):
    def test_tin_lead_alloy_is_clean(self):
        self.assertEqual(alloy_findings(termination()), [])

    def test_near_pure_tin_without_a_plan_is_a_finding(self):
        bare = termination(tin_percent=99.5, lead_percent=0.0)
        self.assertIn(
            "near-pure-tin-alloy-without-a-whisker-mitigation-plan", alloy_findings(bare)
        )

    def test_near_pure_tin_with_a_plan_is_accepted(self):
        planned = termination(
            tin_percent=99.5, lead_percent=0.0, whisker_mitigation_plan=True
        )
        self.assertEqual(alloy_findings(planned), [])

    def test_lead_exactly_on_the_floor_is_accepted(self):
        on_floor = termination(tin_percent=97.0, lead_percent=MIN_LEAD_CONTENT_PERCENT)
        self.assertEqual(alloy_findings(on_floor), [])


class TestFlux(unittest.TestCase):
    def test_mildly_activated_flux_needs_no_cleaning(self):
        self.assertEqual(
            flux_findings(termination(flux_type=FLUX_MILDLY_ACTIVATED, cleaned_after_soldering=False)),
            [],
        )

    def test_activated_flux_left_uncleaned_is_a_finding(self):
        dirty = termination(flux_type=FLUX_ACTIVATED, cleaned_after_soldering=False)
        self.assertIn("activated-flux-residue-left-on-the-termination", flux_findings(dirty))

    def test_water_soluble_flux_cleaned_is_accepted(self):
        clean = termination(flux_type=FLUX_WATER_SOLUBLE, cleaned_after_soldering=True)
        self.assertEqual(flux_findings(clean), [])


class TestThermal(unittest.TestCase):
    def test_dwell_scales_with_cross_section(self):
        self.assertAlmostEqual(allowable_dwell_s(2.0), 6.0, places=9)

    def test_fine_gauge_dwell_is_floored(self):
        self.assertAlmostEqual(allowable_dwell_s(0.1), MIN_DWELL_S, places=9)

    def test_dwell_rejects_a_zero_cross_section(self):
        with self.assertRaises(ValueError):
            allowable_dwell_s(0.0)

    def test_budget_is_the_dwell_times_the_heat_applications(self):
        self.assertAlmostEqual(
            thermal_exposure_budget_s(2.0), 6.0 * MAX_HEAT_APPLICATIONS, places=9
        )

    def test_exposure_counts_the_original_plus_the_reheats(self):
        self.assertAlmostEqual(total_thermal_exposure_s(2.0, 2), 6.0, places=9)

    def test_exposure_rejects_a_fractional_reheat_count(self):
        with self.assertRaises(ValueError):
            total_thermal_exposure_s(2.0, 1.5)

    def test_cold_tip_is_a_finding(self):
        cold = termination(tip_temperature_c=MIN_TIP_TEMPERATURE_C - 40.0)
        self.assertIn("iron-tip-temperature-below-the-window", thermal_findings(cold))

    def test_hot_tip_is_a_finding(self):
        hot = termination(tip_temperature_c=MAX_TIP_TEMPERATURE_C + 40.0)
        self.assertIn("iron-tip-temperature-above-the-window", thermal_findings(hot))

    def test_tip_exactly_on_the_window_edge_is_accepted(self):
        edge = termination(tip_temperature_c=MAX_TIP_TEMPERATURE_C)
        self.assertEqual(thermal_findings(edge), [])

    def test_too_many_heat_applications_is_a_finding(self):
        many = termination(reheats=MAX_HEAT_APPLICATIONS)
        self.assertIn("heat-applications-above-the-allowance", thermal_findings(many))

    def test_exposure_above_the_budget_is_a_finding(self):
        long_dwell = termination(cross_section_mm2=0.1, dwell_s=10.0, reheats=1)
        self.assertIn("thermal-exposure-above-the-scaled-budget", thermal_findings(long_dwell))

    def test_exposure_exactly_on_the_budget_is_accepted(self):
        budget = thermal_exposure_budget_s(0.38)
        exact = termination(
            cross_section_mm2=0.38,
            dwell_s=budget / MAX_HEAT_APPLICATIONS,
            reheats=MAX_HEAT_APPLICATIONS - 1,
        )
        self.assertAlmostEqual(
            total_thermal_exposure_s(exact["dwell_s"], exact["reheats"]), budget, places=9
        )
        self.assertEqual(thermal_findings(exact), [])


class TestGeometry(unittest.TestCase):
    def test_window_runs_from_the_floor_to_twice_the_diameter(self):
        lower, upper = insulation_clearance_window_mm(1.2)
        self.assertAlmostEqual(lower, MIN_INSULATION_CLEARANCE_MM, places=9)
        self.assertAlmostEqual(upper, 2.4, places=9)

    def test_window_rejects_a_zero_diameter(self):
        with self.assertRaises(ValueError):
            insulation_clearance_window_mm(0.0)

    def test_clearance_inside_the_window_is_clean(self):
        self.assertEqual(geometry_findings(termination()), [])

    def test_clearance_below_the_window_is_a_finding(self):
        tight = termination(insulation_clearance_mm=0.05)
        self.assertIn("insulation-clearance-below-the-window", geometry_findings(tight))

    def test_clearance_above_the_window_is_a_finding(self):
        loose = termination(insulation_clearance_mm=5.0)
        self.assertIn("insulation-clearance-above-the-window", geometry_findings(loose))

    def test_clearance_exactly_on_the_upper_edge_is_accepted(self):
        _, upper = insulation_clearance_window_mm(1.2)
        edge = termination(insulation_clearance_mm=upper)
        self.assertEqual(geometry_findings(edge), [])


class TestWettingAndWorkmanship(unittest.TestCase):
    def test_good_wetting_is_clean(self):
        self.assertEqual(wetting_findings(termination()), [])

    def test_high_wetting_angle_is_a_finding(self):
        dewetted = termination(wetting_angle_deg=MAX_WETTING_ANGLE_DEG + 20.0)
        self.assertIn("wetting-angle-above-the-acceptance-value", wetting_findings(dewetted))

    def test_wetting_angle_exactly_on_the_value_is_accepted(self):
        edge = termination(wetting_angle_deg=MAX_WETTING_ANGLE_DEG)
        self.assertEqual(wetting_findings(edge), [])

    def test_fine_conductor_owes_the_highest_magnification(self):
        self.assertAlmostEqual(minimum_inspection_magnification(0.05), 10.0, places=9)

    def test_coarse_conductor_owes_the_lowest_magnification(self):
        self.assertAlmostEqual(
            minimum_inspection_magnification(2.0), COARSE_MAGNIFICATION, places=9
        )

    def test_magnification_rejects_a_zero_cross_section(self):
        with self.assertRaises(ValueError):
            minimum_inspection_magnification(0.0)

    def test_low_magnification_is_a_finding(self):
        low = termination(cross_section_mm2=0.05, inspection_magnification=4.0)
        self.assertIn(
            "inspection-magnification-below-the-owed-value", workmanship_findings(low)
        )

    def test_expired_certification_is_a_finding(self):
        stale = termination(
            days_since_operator_certification=OPERATOR_CERTIFICATION_VALIDITY_DAYS + 1
        )
        self.assertIn("operator-certification-out-of-currency", workmanship_findings(stale))

    def test_certification_on_its_last_valid_day_is_accepted(self):
        current = termination(
            days_since_operator_certification=OPERATOR_CERTIFICATION_VALIDITY_DAYS
        )
        self.assertEqual(workmanship_findings(current), [])


class TestAssessment(unittest.TestCase):
    def test_a_sound_termination_is_compliant(self):
        result = assess_solder_termination(termination())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["owed_inspection_magnification"], 6.0, places=9)

    def test_a_bad_termination_collects_every_finding(self):
        bad = termination(
            tin_percent=99.5,
            lead_percent=0.0,
            flux_type=FLUX_ACTIVATED,
            cleaned_after_soldering=False,
            tip_temperature_c=200.0,
            insulation_clearance_mm=0.0,
            wetting_angle_deg=70.0,
            inspection_magnification=1.0,
            days_since_operator_certification=5000,
        )
        result = assess_solder_termination(bad)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 6)

    def test_lot_counts_findings_by_type(self):
        report = assess_soldering_lot(
            [
                termination("T-1"),
                termination("T-2", flux_type=FLUX_ACTIVATED, cleaned_after_soldering=False),
            ]
        )
        self.assertEqual(report["non_compliant_ids"], ["T-2"])
        self.assertEqual(
            report["findings_by_type"]["activated-flux-residue-left-on-the-termination"], 1
        )
        self.assertAlmostEqual(report["non_compliant_fraction"], 0.5, places=9)

    def test_duplicate_termination_id_raises(self):
        with self.assertRaises(ValueError):
            assess_soldering_lot([termination("T-1"), termination("T-1")])

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_soldering_lot([])

    def test_non_list_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_soldering_lot(termination())


if __name__ == "__main__":
    unittest.main()
