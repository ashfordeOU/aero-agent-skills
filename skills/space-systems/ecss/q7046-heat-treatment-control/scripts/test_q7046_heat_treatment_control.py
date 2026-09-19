"""Contract test for the fastener heat-treatment leaf (stdlib unittest)."""

import unittest

from q7046_heat_treatment_control_logic import (
    BRINELL_TO_TENSILE_MPA,
    BRINELL_VALID_MAX,
    BRINELL_VALID_MIN,
    CONDITIONAL,
    CONFORMING,
    HARDNESS_TENSILE_AGREEMENT_FRACTION,
    NONCONFORMING,
    PROOF_STRESS_FRACTION_OF_YIELD,
    QUENCH_DELAY_LIMIT_S,
    SOAK_BASE_MINUTES,
    SOAK_RATE_MINUTES_PER_MM,
    assess_charge,
    assess_heat_treatment_log,
    class_strengths,
    hardness_tensile_agreement,
    minimum_temper_temperature_c,
    proof_load_kn,
    quench_delay_finding,
    soak_time_minutes,
    stress_area_mm2,
    tensile_from_brinell_mpa,
    uniformity_survey,
    validate_charge,
)


def charge(**kw):
    record = {
        "charge_id": "ht-5001",
        "property_class": "10.9",
        "section_mm": 10.0,
        "declared_soak_minutes": 60.0,
        "setpoint_c": 860.0,
        "survey_readings_c": [858.0, 861.0, 864.0, 857.0],
        "survey_band_c": 10.0,
        "quench_delay_s": 5.0,
        "temper_temperature_c": 500.0,
        "brinell": 320.0,
        "measured_tensile_mpa": 1050.0,
        "nominal_diameter_mm": 10.0,
        "pitch_mm": 1.5,
    }
    record.update(kw)
    return record


class TestClassStrengths(unittest.TestCase):
    def test_the_first_number_gives_the_tensile_target(self):
        self.assertAlmostEqual(
            class_strengths("10.9")["tensile_mpa"], 1000.0, places=9
        )

    def test_the_second_number_gives_the_yield_fraction(self):
        self.assertAlmostEqual(class_strengths("10.9")["yield_mpa"], 900.0, places=9)

    def test_a_lower_class_reads_the_same_way(self):
        strengths = class_strengths("4.6")
        self.assertAlmostEqual(strengths["tensile_mpa"], 400.0, places=9)
        self.assertAlmostEqual(strengths["yield_mpa"], 240.0, places=9)

    def test_the_proof_stress_follows_the_declared_policy(self):
        strengths = class_strengths("12.9")
        self.assertAlmostEqual(
            strengths["proof_stress_mpa"],
            strengths["yield_mpa"] * PROOF_STRESS_FRACTION_OF_YIELD,
            places=9,
        )

    def test_an_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            class_strengths("14.9")

    def test_the_top_class_tempers_lower_than_its_neighbour(self):
        self.assertLess(
            minimum_temper_temperature_c("12.9"),
            minimum_temper_temperature_c("10.9"),
        )

    def test_an_unknown_class_has_no_temper_floor(self):
        with self.assertRaises(ValueError):
            minimum_temper_temperature_c("14.9")


class TestSoakTime(unittest.TestCase):
    def test_the_soak_is_a_base_plus_a_rate_on_the_section(self):
        self.assertAlmostEqual(
            soak_time_minutes(10.0),
            SOAK_BASE_MINUTES + SOAK_RATE_MINUTES_PER_MM * 10.0,
            places=9,
        )

    def test_a_thicker_section_soaks_longer(self):
        self.assertGreater(soak_time_minutes(40.0), soak_time_minutes(10.0))

    def test_a_zero_section_raises(self):
        with self.assertRaises(ValueError):
            soak_time_minutes(0.0)

    def test_a_non_numeric_section_raises(self):
        with self.assertRaises(ValueError):
            soak_time_minutes("thick")


class TestUniformitySurvey(unittest.TestCase):
    def test_a_tight_survey_is_uniform(self):
        survey = uniformity_survey(860.0, [858.0, 861.0, 864.0], 10.0)
        self.assertTrue(survey["uniform"])
        self.assertEqual(survey["failing_thermocouples"], [])

    def test_a_reading_exactly_on_the_band_is_uniform(self):
        survey = uniformity_survey(860.0, [870.0, 850.0], 10.0)
        self.assertTrue(survey["uniform"])
        self.assertAlmostEqual(survey["max_deviation_c"], 10.0, places=9)

    def test_one_bad_thermocouple_fails_the_survey(self):
        survey = uniformity_survey(860.0, [858.0, 861.0, 880.0], 10.0)
        self.assertFalse(survey["uniform"])
        self.assertEqual(survey["failing_thermocouples"], [2])

    def test_the_survey_is_not_judged_on_the_average(self):
        survey = uniformity_survey(860.0, [840.0, 880.0], 10.0)
        self.assertFalse(survey["uniform"])

    def test_an_empty_survey_raises(self):
        with self.assertRaises(ValueError):
            uniformity_survey(860.0, [], 10.0)

    def test_a_zero_band_raises(self):
        with self.assertRaises(ValueError):
            uniformity_survey(860.0, [860.0], 0.0)


class TestQuenchDelay(unittest.TestCase):
    def test_a_prompt_transfer_is_within_its_clock(self):
        self.assertTrue(quench_delay_finding(4.0)["within_limit"])

    def test_a_transfer_exactly_on_the_clock_is_within_it(self):
        result = quench_delay_finding(QUENCH_DELAY_LIMIT_S)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["overrun_s"], 0.0, places=9)

    def test_a_slow_transfer_reports_its_overrun(self):
        result = quench_delay_finding(18.0)
        self.assertFalse(result["within_limit"])
        self.assertAlmostEqual(result["overrun_s"], 8.0, places=9)

    def test_a_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            quench_delay_finding(1.0, 0.0)


class TestHardnessConversion(unittest.TestCase):
    def test_the_conversion_is_proportional(self):
        self.assertAlmostEqual(
            tensile_from_brinell_mpa(300.0), BRINELL_TO_TENSILE_MPA * 300.0, places=9
        )

    def test_a_reading_below_the_fitted_range_raises(self):
        with self.assertRaises(ValueError):
            tensile_from_brinell_mpa(BRINELL_VALID_MIN - 1.0)

    def test_a_reading_above_the_fitted_range_raises(self):
        with self.assertRaises(ValueError):
            tensile_from_brinell_mpa(BRINELL_VALID_MAX + 1.0)

    def test_a_reading_on_the_range_edge_is_accepted(self):
        self.assertAlmostEqual(
            tensile_from_brinell_mpa(BRINELL_VALID_MIN),
            BRINELL_TO_TENSILE_MPA * BRINELL_VALID_MIN,
            places=9,
        )

    def test_a_close_pair_agrees(self):
        self.assertTrue(hardness_tensile_agreement(320.0, 1050.0)["agree"])

    def test_a_pair_exactly_on_the_agreement_band_agrees(self):
        derived = tensile_from_brinell_mpa(300.0)
        measured = derived / (1.0 + HARDNESS_TENSILE_AGREEMENT_FRACTION)
        result = hardness_tensile_agreement(300.0, measured)
        self.assertAlmostEqual(
            result["difference_fraction"],
            HARDNESS_TENSILE_AGREEMENT_FRACTION,
            places=9,
        )
        self.assertTrue(result["agree"])

    def test_a_distant_pair_does_not_agree(self):
        self.assertFalse(hardness_tensile_agreement(600.0, 1050.0)["agree"])

    def test_a_zero_measured_tensile_raises(self):
        with self.assertRaises(ValueError):
            hardness_tensile_agreement(300.0, 0.0)


class TestStressAreaAndProofLoad(unittest.TestCase):
    def test_the_stress_area_follows_from_diameter_and_pitch(self):
        self.assertAlmostEqual(stress_area_mm2(10.0, 1.5), 57.98947542534723,
                               places=9)

    def test_a_finer_pitch_gives_a_larger_stress_area(self):
        self.assertGreater(stress_area_mm2(10.0, 1.0), stress_area_mm2(10.0, 1.5))

    def test_the_proof_load_is_the_area_times_the_proof_stress(self):
        expected = (
            stress_area_mm2(10.0, 1.5)
            * class_strengths("10.9")["proof_stress_mpa"]
            / 1000.0
        )
        self.assertAlmostEqual(proof_load_kn(10.0, 1.5, "10.9"), expected, places=9)

    def test_a_higher_class_demands_a_higher_proof_load(self):
        self.assertGreater(
            proof_load_kn(10.0, 1.5, "12.9"), proof_load_kn(10.0, 1.5, "8.8")
        )

    def test_a_pitch_above_the_diameter_raises(self):
        with self.assertRaises(ValueError):
            stress_area_mm2(1.0, 1.5)

    def test_a_zero_diameter_raises(self):
        with self.assertRaises(ValueError):
            stress_area_mm2(0.0, 1.5)


class TestValidateCharge(unittest.TestCase):
    def test_a_well_formed_charge_normalizes(self):
        norm = validate_charge(charge())
        self.assertEqual(norm["charge_id"], "ht-5001")
        self.assertAlmostEqual(norm["section_mm"], 10.0, places=9)

    def test_a_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_charge("ht-5001")

    def test_a_charge_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(charge_id=" "))

    def test_a_charge_without_a_survey_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(survey_readings_c=[]))

    def test_a_charge_with_an_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            validate_charge(charge(property_class="14.9"))


class TestAssessCharge(unittest.TestCase):
    def test_a_sound_charge_conforms(self):
        result = assess_charge(charge())
        self.assertEqual(result["disposition"], CONFORMING)
        self.assertEqual(result["findings"], [])

    def test_a_short_soak_is_nonconforming(self):
        result = assess_charge(charge(section_mm=60.0))
        self.assertEqual(result["disposition"], NONCONFORMING)
        self.assertIn(
            "soak-shorter-than-the-governing-section-calls-for", result["findings"]
        )

    def test_a_failed_survey_is_nonconforming(self):
        result = assess_charge(charge(survey_readings_c=[858.0, 900.0]))
        self.assertEqual(result["disposition"], NONCONFORMING)
        self.assertIn(
            "furnace-survey-outside-its-uniformity-band", result["findings"]
        )

    def test_a_slow_quench_is_nonconforming(self):
        result = assess_charge(charge(quench_delay_s=25.0))
        self.assertIn("quench-transfer-slower-than-its-clock", result["findings"])

    def test_an_under_tempered_charge_is_nonconforming(self):
        result = assess_charge(charge(temper_temperature_c=390.0))
        self.assertEqual(result["disposition"], NONCONFORMING)
        self.assertIn("tempered-below-the-class-minimum", result["findings"])

    def test_the_same_temperature_suits_the_top_class(self):
        result = assess_charge(
            charge(property_class="12.9", temper_temperature_c=390.0,
                   brinell=400.0, measured_tensile_mpa=1300.0)
        )
        self.assertNotIn("tempered-below-the-class-minimum", result["findings"])

    def test_a_hardness_that_contradicts_the_tensile_is_conditional(self):
        result = assess_charge(charge(brinell=450.0))
        self.assertEqual(result["disposition"], CONDITIONAL)
        self.assertIn(
            "hardness-and-tensile-describe-different-conditions", result["findings"]
        )

    def test_a_tensile_below_the_class_target_is_nonconforming(self):
        result = assess_charge(charge(brinell=280.0, measured_tensile_mpa=920.0))
        self.assertEqual(result["disposition"], NONCONFORMING)
        self.assertIn("measured-tensile-below-the-class-target", result["findings"])

    def test_the_proof_load_is_reported_with_the_charge(self):
        result = assess_charge(charge())
        self.assertAlmostEqual(
            result["proof_load_kn"], proof_load_kn(10.0, 1.5, "10.9"), places=9
        )


class TestAssessLog(unittest.TestCase):
    def test_a_clean_log_conforms(self):
        report = assess_heat_treatment_log(
            [charge(), charge(charge_id="ht-5002")]
        )
        self.assertEqual(report["log_disposition"], CONFORMING)
        self.assertEqual(report["nonconforming_charges"], [])

    def test_the_worst_charge_sets_the_log_disposition(self):
        report = assess_heat_treatment_log(
            [charge(), charge(charge_id="ht-5003", temper_temperature_c=300.0)]
        )
        self.assertEqual(report["log_disposition"], NONCONFORMING)
        self.assertEqual(report["nonconforming_charges"], ["ht-5003"])

    def test_charges_needing_a_recheck_are_listed_separately(self):
        report = assess_heat_treatment_log(
            [charge(charge_id="ht-5004", brinell=450.0)]
        )
        self.assertEqual(report["charges_needing_recheck"], ["ht-5004"])

    def test_a_duplicate_charge_raises(self):
        with self.assertRaises(ValueError):
            assess_heat_treatment_log([charge(), charge()])

    def test_an_empty_log_raises(self):
        with self.assertRaises(ValueError):
            assess_heat_treatment_log([])


if __name__ == "__main__":
    unittest.main()
