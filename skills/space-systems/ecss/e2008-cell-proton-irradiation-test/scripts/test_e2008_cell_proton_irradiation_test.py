"""Contract tests for the clause 7.5.14 bare-cell proton irradiation test."""

import unittest

from e2008_cell_proton_irradiation_test_logic import (
    LOSS_TOLERANCE,
    MAX_OFF_NORMAL_DEG,
    NOISE_ALLOWANCE,
    REFERENCE_ENERGY_MEV,
    accumulated_equivalent_fluence,
    assess_cell_proton_irradiation,
    coverage_findings,
    damage_coefficient_findings,
    equivalent_contribution,
    incidence_findings,
    loss_track_findings,
    path_length_factor,
    power_loss_fraction,
    range_findings,
    validate_exposure,
)

REFERENCE_POWER_W = 1.200
JUNCTION_DEPTH_UM = 20.0
EXPOSURE_TEMPLATES = [
    {
        "label": "p-01",
        "energy_mev": 10.0,
        "fluence_p_per_cm2": 1.0e11,
        "relative_damage_coefficient": 1.0,
        "projected_range_um": 200.0,
        "off_normal_deg": 0.0,
        "power_after_w": 1.176,
    },
    {
        "label": "p-02",
        "energy_mev": 3.0,
        "fluence_p_per_cm2": 5.0e10,
        "relative_damage_coefficient": 2.0,
        "projected_range_um": 60.0,
        "off_normal_deg": 0.0,
        "power_after_w": 1.140,
    },
    {
        "label": "p-03",
        "energy_mev": 30.0,
        "fluence_p_per_cm2": 2.0e11,
        "relative_damage_coefficient": 0.5,
        "projected_range_um": 4000.0,
        "off_normal_deg": 0.0,
        "power_after_w": 1.092,
    },
]
TOTAL_EQUIVALENT = 3.0e11


def exposures():
    return [dict(item) for item in EXPOSURE_TEMPLATES]


class ExposureValidationTests(unittest.TestCase):
    def test_exposure_is_returned_as_floats(self):
        item = validate_exposure(exposures()[0])
        self.assertAlmostEqual(item["energy_mev"], 10.0, places=9)
        self.assertEqual(item["label"], "p-01")

    def test_missing_key_rejected(self):
        record = exposures()[0]
        del record["projected_range_um"]
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_zero_fluence_rejected(self):
        record = exposures()[0]
        record["fluence_p_per_cm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_negative_range_rejected(self):
        record = exposures()[0]
        record["projected_range_um"] = -5.0
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_grazing_incidence_rejected(self):
        record = exposures()[0]
        record["off_normal_deg"] = 90.0
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_boolean_energy_rejected(self):
        record = exposures()[0]
        record["energy_mev"] = True
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_empty_label_rejected(self):
        record = exposures()[0]
        record["label"] = "   "
        with self.assertRaises(ValueError):
            validate_exposure(record)

    def test_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(["p-01"])


class PathLengthTests(unittest.TestCase):
    def test_normal_incidence_crosses_one_path(self):
        self.assertAlmostEqual(path_length_factor(0.0), 1.0, places=9)

    def test_sixty_degrees_doubles_the_path(self):
        self.assertAlmostEqual(path_length_factor(60.0), 2.0, places=9)

    def test_path_grows_with_the_tilt(self):
        self.assertGreater(path_length_factor(45.0), path_length_factor(10.0))

    def test_grazing_path_rejected(self):
        with self.assertRaises(ValueError):
            path_length_factor(90.0)

    def test_negative_tilt_rejected(self):
        with self.assertRaises(ValueError):
            path_length_factor(-1.0)


class EquivalentFluenceTests(unittest.TestCase):
    def test_contribution_is_fluence_times_coefficient(self):
        value = equivalent_contribution(exposures()[1])
        self.assertAlmostEqual(value / 1.0e11, 1.0, places=12)

    def test_tilted_beam_contributes_more(self):
        record = exposures()[0]
        record["off_normal_deg"] = 60.0
        value = equivalent_contribution(record)
        self.assertAlmostEqual(value / 2.0e11, 1.0, places=9)

    def test_running_total_after_each_exposure(self):
        totals = accumulated_equivalent_fluence(exposures())
        self.assertEqual(len(totals), 3)
        self.assertAlmostEqual(totals[0] / 1.0e11, 1.0, places=12)
        self.assertAlmostEqual(totals[-1] / TOTAL_EQUIVALENT, 1.0, places=12)

    def test_running_total_never_falls(self):
        totals = accumulated_equivalent_fluence(exposures())
        for earlier, later in zip(totals, totals[1:]):
            self.assertGreater(later, earlier)

    def test_empty_exposure_list_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_equivalent_fluence([])


class DamageCoefficientTests(unittest.TestCase):
    def test_reference_energy_is_ten_mev(self):
        self.assertAlmostEqual(REFERENCE_ENERGY_MEV, 10.0, places=9)

    def test_normalised_table_gives_no_finding(self):
        self.assertEqual(damage_coefficient_findings(exposures()), [])

    def test_reference_energy_off_unity_is_a_finding(self):
        records = exposures()
        records[0]["relative_damage_coefficient"] = 1.3
        findings = damage_coefficient_findings(records)
        self.assertEqual(len(findings), 1)
        self.assertIn("p-01", findings[0])

    def test_other_energies_may_carry_any_coefficient(self):
        records = exposures()
        records[1]["relative_damage_coefficient"] = 7.5
        self.assertEqual(damage_coefficient_findings(records), [])

    def test_custom_reference_energy_is_honoured(self):
        findings = damage_coefficient_findings(exposures(), 3.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("p-02", findings[0])

    def test_empty_exposures_rejected(self):
        with self.assertRaises(ValueError):
            damage_coefficient_findings([])


class RangeTests(unittest.TestCase):
    def test_energies_reaching_the_junction_give_no_finding(self):
        self.assertEqual(range_findings(exposures(), JUNCTION_DEPTH_UM), [])

    def test_range_exactly_at_the_junction_is_accepted(self):
        records = exposures()
        records[1]["projected_range_um"] = JUNCTION_DEPTH_UM
        self.assertEqual(range_findings(records, JUNCTION_DEPTH_UM), [])

    def test_short_range_is_a_finding(self):
        records = exposures()
        records[1]["projected_range_um"] = 5.0
        findings = range_findings(records, JUNCTION_DEPTH_UM)
        self.assertEqual(len(findings), 1)
        self.assertIn("ahead of the junction", findings[0])

    def test_zero_junction_depth_rejected(self):
        with self.assertRaises(ValueError):
            range_findings(exposures(), 0.0)


class IncidenceTests(unittest.TestCase):
    def test_normal_incidence_gives_no_finding(self):
        self.assertEqual(incidence_findings(exposures()), [])

    def test_angle_exactly_on_the_allowance_is_accepted(self):
        records = exposures()
        records[2]["off_normal_deg"] = MAX_OFF_NORMAL_DEG
        self.assertEqual(incidence_findings(records), [])

    def test_tilted_beam_is_a_finding(self):
        records = exposures()
        records[2]["off_normal_deg"] = 25.0
        findings = incidence_findings(records)
        self.assertEqual(len(findings), 1)
        self.assertIn("off normal", findings[0])

    def test_default_incidence_allowance(self):
        self.assertAlmostEqual(MAX_OFF_NORMAL_DEG, 3.0, places=9)

    def test_grazing_allowance_rejected(self):
        with self.assertRaises(ValueError):
            incidence_findings(exposures(), 95.0)


class LossTrackTests(unittest.TestCase):
    def test_loss_is_one_minus_the_power_ratio(self):
        self.assertAlmostEqual(
            power_loss_fraction(1.176, REFERENCE_POWER_W), 0.02, places=9
        )

    def test_undamaged_cell_has_no_loss(self):
        self.assertAlmostEqual(
            power_loss_fraction(REFERENCE_POWER_W, REFERENCE_POWER_W),
            0.0,
            places=9,
        )

    def test_zero_reference_power_rejected(self):
        with self.assertRaises(ValueError):
            power_loss_fraction(1.176, 0.0)

    def test_rising_loss_gives_no_finding(self):
        self.assertEqual(
            loss_track_findings(["a", "b", "c"], [0.02, 0.05, 0.09]), []
        )

    def test_shrinking_loss_is_a_finding(self):
        findings = loss_track_findings(["a", "b", "c"], [0.02, 0.09, 0.04])
        self.assertTrue(any("recovered" in item for item in findings))

    def test_dip_inside_the_noise_allowance_is_accepted(self):
        self.assertEqual(
            loss_track_findings(["a", "b"], [0.050, 0.049]), []
        )

    def test_power_above_the_starting_point_is_a_finding(self):
        findings = loss_track_findings(["a", "b"], [-0.05, 0.02])
        self.assertTrue(
            any("above its starting power" in item for item in findings)
        )

    def test_label_and_loss_count_must_match(self):
        with self.assertRaises(ValueError):
            loss_track_findings(["a", "b"], [0.02])

    def test_default_noise_allowance(self):
        self.assertAlmostEqual(NOISE_ALLOWANCE, 0.002, places=9)

    def test_loss_tolerance_is_small(self):
        self.assertAlmostEqual(LOSS_TOLERANCE, 1e-9, places=12)


class CoverageTests(unittest.TestCase):
    def test_reaching_the_requirement_gives_no_finding(self):
        self.assertEqual(
            coverage_findings(TOTAL_EQUIVALENT, TOTAL_EQUIVALENT), []
        )

    def test_exceeding_the_requirement_gives_no_finding(self):
        self.assertEqual(coverage_findings(5.0e11, TOTAL_EQUIVALENT), [])

    def test_falling_short_is_a_finding(self):
        findings = coverage_findings(1.0e11, TOTAL_EQUIVALENT)
        self.assertEqual(len(findings), 1)
        self.assertIn("under", findings[0])

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(TOTAL_EQUIVALENT, 0.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "exposures": exposures(),
            "reference_power_w": REFERENCE_POWER_W,
            "junction_depth_um": JUNCTION_DEPTH_UM,
            "required_equivalent_fluence_p_per_cm2": TOTAL_EQUIVALENT,
            "allowed_power_loss": 0.10,
        }
        spec.update(overrides)
        return spec

    def test_conformant_run_has_no_finding(self):
        result = assess_cell_proton_irradiation(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["run_conformant"])

    def test_every_exposure_is_reported(self):
        result = assess_cell_proton_irradiation(self._spec())
        self.assertEqual(result["exposure_count"], 3)
        self.assertEqual(len(result["exposures"]), 3)

    def test_accumulated_equivalent_fluence_is_reported(self):
        result = assess_cell_proton_irradiation(self._spec())
        self.assertAlmostEqual(
            result["accumulated_equivalent_p_per_cm2"] / TOTAL_EQUIVALENT,
            1.0,
            places=12,
        )

    def test_end_power_loss_is_reported(self):
        result = assess_cell_proton_irradiation(self._spec())
        self.assertAlmostEqual(
            result["end_power_loss_fraction"], 0.09, places=9
        )

    def test_normal_incidence_path_factor_is_unity(self):
        result = assess_cell_proton_irradiation(self._spec())
        for item in result["exposures"]:
            self.assertAlmostEqual(item["path_length_factor"], 1.0, places=9)

    def test_short_range_energy_fails_the_run(self):
        spec = self._spec()
        spec["exposures"][1]["projected_range_um"] = 4.0
        result = assess_cell_proton_irradiation(spec)
        self.assertFalse(result["run_conformant"])

    def test_tilted_beam_fails_the_run(self):
        spec = self._spec()
        spec["exposures"][0]["off_normal_deg"] = 20.0
        result = assess_cell_proton_irradiation(spec)
        self.assertFalse(result["run_conformant"])

    def test_recovered_power_fails_the_run(self):
        spec = self._spec()
        spec["exposures"][2]["power_after_w"] = 1.150
        result = assess_cell_proton_irradiation(spec)
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("recovered" in item for item in result["findings"])
        )

    def test_loss_over_the_allowance_fails_the_run(self):
        result = assess_cell_proton_irradiation(
            self._spec(allowed_power_loss=0.05)
        )
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("the mission allows" in item for item in result["findings"])
        )

    def test_short_equivalent_fluence_fails_the_run(self):
        result = assess_cell_proton_irradiation(
            self._spec(required_equivalent_fluence_p_per_cm2=9.0e11)
        )
        self.assertFalse(result["run_conformant"])

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["junction_depth_um"]
        with self.assertRaises(ValueError):
            assess_cell_proton_irradiation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_proton_irradiation(["exposures"])

    def test_exposure_without_a_power_reading_rejected(self):
        spec = self._spec()
        del spec["exposures"][0]["power_after_w"]
        with self.assertRaises(ValueError):
            assess_cell_proton_irradiation(spec)

    def test_allowed_loss_of_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_proton_irradiation(self._spec(allowed_power_loss=1.0))

    def test_empty_exposures_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_proton_irradiation(self._spec(exposures=[]))


if __name__ == "__main__":
    unittest.main()
