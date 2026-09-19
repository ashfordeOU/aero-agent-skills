"""Contract test for the fastener coating and finish leaf (stdlib unittest)."""

import unittest

from q7046_coating_and_finish_control_logic import (
    ACCEPTED,
    ACCEPTED_WITH_CONTROLS,
    CVCM_LIMIT_PERCENT,
    PITCH_DIAMETER_FACTOR,
    REJECTED,
    TML_LIMIT_PERCENT,
    assess_finish_application,
    assess_finish_schedule,
    finish_record,
    lubricant_record,
    lubricant_temperature_coverage,
    max_external_thickness_um,
    outgassing_check,
    pitch_diameter_consumption_um,
    preload_band_n,
    screen_finish,
    substitutes_for,
    thread_fit_check,
    validate_finish_application,
)


def application(**kw):
    record = {
        "part_number": "fs-2001",
        "finish": "zinc-nickel-plate",
        "alloy_fraction": 0.0,
        "lubricant": "molybdenum-disulphide-dry-film",
        "allowance_um": 40.0,
        "external_thickness_um": 5.0,
        "internal_thickness_um": 0.0,
        "mission_min_c": -50.0,
        "mission_max_c": 80.0,
        "nut_factor_min": 0.15,
        "nut_factor_max": 0.22,
        "torque_nm": 20.0,
        "diameter_mm": 8.0,
        "assumed_scatter_fraction": 0.25,
    }
    record.update(kw)
    return record


class TestFinishRegister(unittest.TestCase):
    def test_a_registered_finish_returns_its_entry(self):
        self.assertEqual(finish_record("zinc-nickel-plate")["status"], "permitted")

    def test_an_unknown_finish_raises(self):
        with self.assertRaises(ValueError):
            finish_record("gold-leaf-by-hand")

    def test_the_register_returns_a_copy(self):
        entry = finish_record("cadmium-plate")
        entry["status"] = "permitted"
        self.assertEqual(finish_record("cadmium-plate")["status"], "barred")

    def test_a_barred_finish_offers_substitutes(self):
        self.assertIn("zinc-nickel-plate", substitutes_for("cadmium-plate"))


class TestScreenFinish(unittest.TestCase):
    def test_cadmium_is_barred_whatever_the_alloying(self):
        screen = screen_finish("cadmium-plate", 0.9)
        self.assertFalse(screen["admissible"])
        self.assertEqual(screen["reason"], "cadmium-deposit-barred-for-flight")

    def test_a_barred_screen_names_the_permitted_substitutes(self):
        screen = screen_finish("cadmium-plate")
        self.assertIn("aluminium-ion-vapour-deposit", screen["substitutes"])

    def test_pure_tin_below_the_suppression_floor_is_screened_out(self):
        screen = screen_finish("pure-tin-plate", 0.02)
        self.assertFalse(screen["admissible"])
        self.assertEqual(screen["reason"], "tin-whisker-risk")

    def test_pure_tin_exactly_on_the_floor_is_admissible(self):
        floor = finish_record("pure-tin-plate")["min_alloy_fraction"]
        screen = screen_finish("pure-tin-plate", floor)
        self.assertTrue(screen["admissible"])

    def test_a_permitted_finish_needs_no_alloying(self):
        screen = screen_finish("passivation-only")
        self.assertTrue(screen["admissible"])
        self.assertEqual(screen["substitutes"], [])

    def test_an_alloy_fraction_above_unity_raises(self):
        with self.assertRaises(ValueError):
            screen_finish("pure-zinc-plate", 1.4)


class TestThreadFit(unittest.TestCase):
    def test_a_deposit_moves_the_pitch_diameter_by_four_thicknesses(self):
        self.assertAlmostEqual(
            pitch_diameter_consumption_um(5.0), PITCH_DIAMETER_FACTOR * 5.0, places=9
        )

    def test_both_mating_threads_consume_the_same_allowance(self):
        self.assertAlmostEqual(
            pitch_diameter_consumption_um(5.0, 3.0), 32.0, places=9
        )

    def test_an_allowance_exactly_consumed_still_fits(self):
        fit = thread_fit_check(40.0, 10.0)
        self.assertAlmostEqual(fit["consumed_um"], 40.0, places=9)
        self.assertTrue(fit["fits"])

    def test_one_micrometre_more_does_not_fit(self):
        self.assertFalse(thread_fit_check(40.0, 11.0)["fits"])

    def test_the_thickest_admissible_deposit_is_a_quarter_of_the_allowance(self):
        self.assertAlmostEqual(max_external_thickness_um(40.0), 10.0, places=9)

    def test_an_internal_deposit_eats_the_external_budget(self):
        self.assertAlmostEqual(max_external_thickness_um(40.0, 4.0), 6.0, places=9)

    def test_an_internal_deposit_can_leave_no_budget_at_all(self):
        self.assertAlmostEqual(max_external_thickness_um(40.0, 12.0), 0.0, places=9)

    def test_a_zero_allowance_raises(self):
        with self.assertRaises(ValueError):
            thread_fit_check(0.0, 5.0)

    def test_a_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            pitch_diameter_consumption_um(-1.0)


class TestLubricant(unittest.TestCase):
    def test_a_registered_lubricant_returns_its_entry(self):
        self.assertAlmostEqual(
            lubricant_record("ptfe-dry-film")["tml_percent"], 0.50, places=9
        )

    def test_an_unknown_lubricant_raises(self):
        with self.assertRaises(ValueError):
            lubricant_record("chip-fat")

    def test_a_dry_film_passes_the_outgassing_limits(self):
        result = outgassing_check("molybdenum-disulphide-dry-film")
        self.assertTrue(result["acceptable"])

    def test_a_grease_fails_both_outgassing_limits(self):
        result = outgassing_check("hydrocarbon-grease")
        self.assertFalse(result["tml_within_limit"])
        self.assertFalse(result["cvcm_within_limit"])

    def test_the_limits_are_the_ones_the_screen_uses(self):
        self.assertAlmostEqual(TML_LIMIT_PERCENT, 1.00, places=9)
        self.assertAlmostEqual(CVCM_LIMIT_PERCENT, 0.10, places=9)

    def test_a_lubricant_band_can_miss_the_cold_end_alone(self):
        coverage = lubricant_temperature_coverage("hydrocarbon-grease", -60.0, 100.0)
        self.assertFalse(coverage["cold_end_covered"])
        self.assertTrue(coverage["hot_end_covered"])

    def test_a_mission_exactly_on_the_hot_end_is_covered(self):
        coverage = lubricant_temperature_coverage("ptfe-dry-film", -100.0, 250.0)
        self.assertTrue(coverage["hot_end_covered"])

    def test_an_inverted_mission_band_raises(self):
        with self.assertRaises(ValueError):
            lubricant_temperature_coverage("silver-film", 100.0, -100.0)


class TestPreloadBand(unittest.TestCase):
    def test_the_scatter_depends_only_on_the_nut_factor_band(self):
        band = preload_band_n(20.0, 8.0, 0.15, 0.22)
        self.assertAlmostEqual(
            band["scatter_fraction"], (0.22 - 0.15) / (0.22 + 0.15), places=9
        )

    def test_a_single_valued_nut_factor_has_no_scatter(self):
        band = preload_band_n(20.0, 8.0, 0.20, 0.20)
        self.assertAlmostEqual(band["scatter_fraction"], 0.0, places=9)

    def test_the_high_nut_factor_gives_the_low_preload(self):
        band = preload_band_n(20.0, 8.0, 0.15, 0.22)
        self.assertAlmostEqual(band["preload_min_n"], 20.0 / (0.22 * 0.008), places=6)
        self.assertLess(band["preload_min_n"], band["preload_max_n"])

    def test_an_inverted_nut_factor_band_raises(self):
        with self.assertRaises(ValueError):
            preload_band_n(20.0, 8.0, 0.25, 0.15)

    def test_a_zero_torque_raises(self):
        with self.assertRaises(ValueError):
            preload_band_n(0.0, 8.0, 0.15, 0.22)

    def test_a_zero_diameter_raises(self):
        with self.assertRaises(ValueError):
            preload_band_n(20.0, 0.0, 0.15, 0.22)


class TestValidateApplication(unittest.TestCase):
    def test_a_well_formed_application_normalizes(self):
        norm = validate_finish_application(application())
        self.assertEqual(norm["part_number"], "fs-2001")
        self.assertAlmostEqual(norm["allowance_um"], 40.0, places=9)

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_finish_application("zinc-nickel-plate")

    def test_a_missing_part_number_raises(self):
        with self.assertRaises(ValueError):
            validate_finish_application(application(part_number=" "))

    def test_an_unknown_finish_raises(self):
        with self.assertRaises(ValueError):
            validate_finish_application(application(finish="hot-dip-anything"))


class TestAssessApplication(unittest.TestCase):
    def test_a_clean_application_is_accepted(self):
        result = assess_finish_application(application())
        self.assertEqual(result["disposition"], ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_barred_deposit_is_rejected_and_offers_a_way_out(self):
        result = assess_finish_application(application(finish="cadmium-plate"))
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("zinc-nickel-plate", result["screen"]["substitutes"])

    def test_an_alloyed_restricted_deposit_carries_a_batch_control(self):
        result = assess_finish_application(
            application(finish="pure-tin-plate", alloy_fraction=0.05)
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTROLS)
        self.assertIn(
            "verify-the-alloying-addition-on-every-batch", result["controls"]
        )

    def test_a_deposit_too_thick_for_the_class_is_rejected(self):
        result = assess_finish_application(
            application(external_thickness_um=15.0)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "deposit-consumes-more-than-the-thread-allowance", result["findings"]
        )

    def test_a_grease_is_rejected_on_outgassing(self):
        result = assess_finish_application(
            application(lubricant="hydrocarbon-grease", mission_min_c=0.0,
                        mission_max_c=100.0)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("lubricant-above-the-outgassing-limits", result["findings"])

    def test_an_unqualified_cold_end_is_its_own_finding(self):
        result = assess_finish_application(
            application(lubricant="ptfe-dry-film", mission_min_c=-220.0)
        )
        self.assertIn("lubricant-cold-end-not-qualified", result["findings"])

    def test_a_wider_nut_factor_band_than_assumed_raises_a_control(self):
        result = assess_finish_application(
            application(nut_factor_min=0.10, nut_factor_max=0.30,
                        assumed_scatter_fraction=0.20)
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_CONTROLS)
        self.assertIn(
            "re-run-the-preload-window-on-the-measured-nut-factor",
            result["controls"],
        )


class TestAssessSchedule(unittest.TestCase):
    def test_a_clean_schedule_is_accepted(self):
        report = assess_finish_schedule(
            [application(), application(part_number="fs-2002")]
        )
        self.assertEqual(report["schedule_disposition"], ACCEPTED)
        self.assertEqual(report["rejected_parts"], [])

    def test_the_worst_application_sets_the_schedule_disposition(self):
        report = assess_finish_schedule(
            [application(), application(part_number="fs-2003",
                                        finish="cadmium-plate")]
        )
        self.assertEqual(report["schedule_disposition"], REJECTED)
        self.assertEqual(report["rejected_parts"], ["fs-2003"])

    def test_substitutions_are_collected_per_part(self):
        report = assess_finish_schedule(
            [application(part_number="fs-2004", finish="cadmium-plate")]
        )
        self.assertIn("fs-2004", report["substitutions_offered"])

    def test_a_duplicate_part_raises(self):
        with self.assertRaises(ValueError):
            assess_finish_schedule([application(), application()])

    def test_an_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            assess_finish_schedule([])


if __name__ == "__main__":
    unittest.main()
