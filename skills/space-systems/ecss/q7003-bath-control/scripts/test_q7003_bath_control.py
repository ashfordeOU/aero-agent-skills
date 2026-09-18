"""Contract test for the black-anodizing bath-control leaf (stdlib unittest)."""

import unittest

from q7003_bath_control_logic import (
    ADJUST,
    ANALYSIS_SCHEDULE,
    IN_CONTROL,
    OUT_OF_SERVICE,
    OVERDUE_GRACE_FRACTION,
    addition_mass_kg,
    analysis_status,
    assess_line,
    assess_tank,
    correction_for,
    dilution_volume_l,
    parameter_disposition,
    validate_parameter,
    validate_tank,
)


def parameter(name="free-acid", measured=180.0, **kw):
    record = {
        "name": name,
        "nominal": 180.0,
        "control_low": 160.0,
        "control_high": 200.0,
        "reject_low": 140.0,
        "reject_high": 220.0,
        "measured": measured,
    }
    record.update(kw)
    return record


def tank(name="anodizing-electrolyte", **kw):
    record = {
        "tank": name,
        "volume_l": 1000.0,
        "hours_since_analysis": 4.0,
        "area_since_analysis_dm2": 100.0,
        "additive_strength_fraction": 1.0,
        "parameters": [parameter()],
    }
    record.update(kw)
    return record


class TestValidateParameter(unittest.TestCase):
    def test_a_well_formed_parameter_normalizes(self):
        norm = validate_parameter(parameter())
        self.assertEqual(norm["name"], "free-acid")
        self.assertAlmostEqual(norm["measured"], 180.0, places=9)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(["free-acid"])

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(name=""))

    def test_unnested_bands_raise(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(reject_low=170.0))

    def test_nominal_outside_the_control_band_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(parameter(nominal=210.0))

    def test_missing_measurement_raises(self):
        record = parameter()
        del record["measured"]
        with self.assertRaises(ValueError):
            validate_parameter(record)


class TestParameterDisposition(unittest.TestCase):
    def test_inside_the_control_band_is_in_control(self):
        self.assertEqual(parameter_disposition(parameter(measured=180.0)),
                         IN_CONTROL)

    def test_exactly_on_the_control_bound_is_in_control(self):
        self.assertEqual(parameter_disposition(parameter(measured=160.0)),
                         IN_CONTROL)
        self.assertEqual(parameter_disposition(parameter(measured=200.0)),
                         IN_CONTROL)

    def test_between_control_and_reject_needs_an_adjustment(self):
        self.assertEqual(parameter_disposition(parameter(measured=150.0)), ADJUST)
        self.assertEqual(parameter_disposition(parameter(measured=210.0)), ADJUST)

    def test_outside_the_reject_band_takes_the_tank_off_line(self):
        self.assertEqual(parameter_disposition(parameter(measured=100.0)),
                         OUT_OF_SERVICE)
        self.assertEqual(parameter_disposition(parameter(measured=300.0)),
                         OUT_OF_SERVICE)


class TestCorrectionArithmetic(unittest.TestCase):
    def test_addition_is_volume_times_shortfall(self):
        self.assertAlmostEqual(addition_mass_kg(1000.0, 20.0), 20.0, places=9)

    def test_a_weaker_additive_needs_more_of_it(self):
        self.assertAlmostEqual(addition_mass_kg(1000.0, 20.0, 0.5), 40.0, places=9)

    def test_zero_volume_raises(self):
        with self.assertRaises(ValueError):
            addition_mass_kg(0.0, 20.0)

    def test_strength_outside_the_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            addition_mass_kg(1000.0, 20.0, 1.5)

    def test_dilution_volume_brings_a_tank_back_to_target(self):
        volume = dilution_volume_l(1000.0, 220.0, 200.0)
        self.assertAlmostEqual(volume, 100.0, places=9)
        final = 1000.0 * 220.0 / (1000.0 + volume)
        self.assertAlmostEqual(final, 200.0, places=9)

    def test_a_tank_already_at_target_needs_no_dilution(self):
        self.assertAlmostEqual(dilution_volume_l(1000.0, 200.0, 200.0), 0.0,
                               places=9)

    def test_zero_target_raises(self):
        with self.assertRaises(ValueError):
            dilution_volume_l(1000.0, 220.0, 0.0)

    def test_a_low_parameter_asks_for_an_addition(self):
        correction = correction_for(parameter(measured=150.0), 1000.0)
        self.assertEqual(correction["action"], "addition")
        self.assertAlmostEqual(correction["addition_kg"], 30.0, places=9)

    def test_a_high_parameter_asks_for_a_dilution(self):
        correction = correction_for(parameter(measured=210.0), 1000.0)
        self.assertEqual(correction["action"], "dilution")
        self.assertGreater(correction["dilution_l"], 0.0)

    def test_an_in_control_parameter_asks_for_nothing(self):
        correction = correction_for(parameter(measured=180.0), 1000.0)
        self.assertEqual(correction["action"], "none")


class TestAnalysisSchedule(unittest.TestCase):
    def test_a_fresh_tank_is_current(self):
        status = analysis_status("anodizing-electrolyte", 1.0, 10.0)
        self.assertEqual(status["state"], "current")

    def test_elapsed_time_can_drive_the_schedule(self):
        hours = ANALYSIS_SCHEDULE["dye-bath"]["interval_hours"] * 1.2
        status = analysis_status("dye-bath", hours, 0.0)
        self.assertEqual(status["state"], "due")
        self.assertEqual(status["driver"], "elapsed-time")

    def test_processed_area_can_drive_the_schedule(self):
        area = ANALYSIS_SCHEDULE["dye-bath"]["interval_area_dm2"] * 1.2
        status = analysis_status("dye-bath", 0.0, area)
        self.assertEqual(status["state"], "due")
        self.assertEqual(status["driver"], "processed-area")

    def test_exactly_on_the_interval_is_still_current(self):
        hours = ANALYSIS_SCHEDULE["seal-bath"]["interval_hours"]
        status = analysis_status("seal-bath", hours, 0.0)
        self.assertEqual(status["state"], "current")
        self.assertAlmostEqual(status["fraction_of_interval"], 1.0, places=9)

    def test_past_the_grace_the_analysis_is_overdue(self):
        hours = ANALYSIS_SCHEDULE["seal-bath"]["interval_hours"] * (
            1.0 + OVERDUE_GRACE_FRACTION + 0.2
        )
        status = analysis_status("seal-bath", hours, 0.0)
        self.assertEqual(status["state"], "overdue")

    def test_unknown_tank_raises(self):
        with self.assertRaises(ValueError):
            analysis_status("passivation", 1.0, 1.0)

    def test_negative_hours_raise(self):
        with self.assertRaises(ValueError):
            analysis_status("dye-bath", -1.0, 0.0)


class TestValidateTank(unittest.TestCase):
    def test_a_well_formed_tank_normalizes(self):
        norm = validate_tank(tank())
        self.assertEqual(norm["tank"], "anodizing-electrolyte")
        self.assertEqual(len(norm["parameters"]), 1)

    def test_unknown_tank_raises(self):
        with self.assertRaises(ValueError):
            validate_tank(tank(name="passivation"))

    def test_empty_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            validate_tank(tank(parameters=[]))

    def test_repeated_parameter_name_raises(self):
        with self.assertRaises(ValueError):
            validate_tank(tank(parameters=[parameter(), parameter()]))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_tank(["anodizing-electrolyte"])


class TestAssessTank(unittest.TestCase):
    def test_a_healthy_tank_is_in_control(self):
        result = assess_tank(tank())
        self.assertEqual(result["disposition"], IN_CONTROL)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["corrections"], [])

    def test_a_drifted_parameter_asks_for_an_adjustment(self):
        result = assess_tank(tank(parameters=[parameter(measured=150.0)]))
        self.assertEqual(result["disposition"], ADJUST)
        self.assertIn("free-acid-outside-its-control-band", result["findings"])
        self.assertEqual(result["corrections"][0]["action"], "addition")

    def test_a_rejected_parameter_takes_the_tank_off_line(self):
        result = assess_tank(tank(parameters=[parameter(measured=100.0)]))
        self.assertEqual(result["disposition"], OUT_OF_SERVICE)
        self.assertIn("free-acid-outside-its-reject-band", result["findings"])

    def test_a_due_analysis_alone_asks_for_an_adjustment(self):
        hours = ANALYSIS_SCHEDULE["anodizing-electrolyte"]["interval_hours"] * 1.2
        result = assess_tank(tank(hours_since_analysis=hours))
        self.assertEqual(result["disposition"], ADJUST)
        self.assertIn("analysis-due-on-elapsed-time", result["findings"])

    def test_an_overdue_analysis_takes_the_tank_off_line(self):
        hours = ANALYSIS_SCHEDULE["anodizing-electrolyte"]["interval_hours"] * 3.0
        result = assess_tank(tank(hours_since_analysis=hours))
        self.assertEqual(result["disposition"], OUT_OF_SERVICE)
        self.assertIn("analysis-overdue-on-elapsed-time", result["findings"])

    def test_the_worst_parameter_sets_the_tank_disposition(self):
        result = assess_tank(
            tank(parameters=[parameter("free-acid", 180.0),
                             parameter("dissolved-aluminium", 100.0)])
        )
        self.assertEqual(result["disposition"], OUT_OF_SERVICE)


class TestAssessLine(unittest.TestCase):
    def test_a_healthy_line_is_in_control(self):
        report = assess_line([tank("anodizing-electrolyte"), tank("dye-bath")])
        self.assertEqual(report["line_disposition"], IN_CONTROL)
        self.assertEqual(report["tanks_out_of_service"], [])

    def test_the_worst_tank_sets_the_line_disposition(self):
        report = assess_line([
            tank("anodizing-electrolyte"),
            tank("dye-bath", parameters=[parameter(measured=100.0)]),
        ])
        self.assertEqual(report["line_disposition"], OUT_OF_SERVICE)
        self.assertEqual(report["tanks_out_of_service"], ["dye-bath"])

    def test_tanks_needing_analysis_are_listed(self):
        hours = ANALYSIS_SCHEDULE["seal-bath"]["interval_hours"] * 1.2
        report = assess_line([
            tank("anodizing-electrolyte"),
            tank("seal-bath", hours_since_analysis=hours),
        ])
        self.assertEqual(report["analysis_due_tanks"], ["seal-bath"])

    def test_duplicate_tank_raises(self):
        with self.assertRaises(ValueError):
            assess_line([tank("dye-bath"), tank("dye-bath")])

    def test_empty_line_raises(self):
        with self.assertRaises(ValueError):
            assess_line([])


if __name__ == "__main__":
    unittest.main()
