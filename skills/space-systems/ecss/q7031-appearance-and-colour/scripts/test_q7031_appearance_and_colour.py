"""Contract tests for the painted-area colour and appearance logic.

The cases walk one painted area through the checks the Quality clause asks
for: the CIELAB difference against the reference chip, the gloss band, the
appearance defect tally by mechanism and by density, the thermo-optical band a
thermal-control finish also owes, and the disposition that comes out of all of
them together.
"""

import unittest

from q7031_appearance_and_colour_logic import (
    APPEARANCE_DEFECTS,
    DEFAULT_DELTA_E_LIMIT,
    assess_appearance_survey,
    assess_painted_area,
    categorize_appearance_defect,
    colour_difference_de76,
    colour_within_tolerance,
    defect_density_per_m2,
    defect_findings,
    gloss_within_band,
    thermo_optical_findings,
    validate_lab,
)

REFERENCE = {"L": 92.0, "a": -1.2, "b": 2.4}


def _area(**overrides):
    spec = {
        "name": "radiator-panel-A",
        "measured_lab": {"L": 92.3, "a": -1.1, "b": 2.6},
        "reference_lab": REFERENCE,
        "delta_e_limit": 1.5,
        "gloss_units": 12.0,
        "gloss_band": (5.0, 20.0),
        "area_m2": 2.0,
        "defects": {"orange-peel": 2},
        "defect_density_limit": 4.0,
        "thermal_control": True,
        "thermo_optical": {"absorptance": 0.18, "emittance": 0.88},
        "thermo_optical_bands": {"absorptance": (0.12, 0.22), "emittance": (0.84, 0.92)},
    }
    spec.update(overrides)
    return spec


class ColourTests(unittest.TestCase):
    def test_identical_colour_has_zero_difference(self):
        self.assertAlmostEqual(colour_difference_de76(REFERENCE, REFERENCE), 0.0, places=9)

    def test_difference_is_the_euclidean_lab_distance(self):
        measured = {"L": 95.0, "a": -1.2, "b": 6.4}
        self.assertAlmostEqual(colour_difference_de76(measured, REFERENCE), 5.0, places=9)

    def test_a_difference_exactly_on_the_tolerance_is_accepted(self):
        measured = {"L": 93.5, "a": -1.2, "b": 2.4}
        self.assertAlmostEqual(colour_difference_de76(measured, REFERENCE), 1.5, places=9)
        self.assertTrue(colour_within_tolerance(measured, REFERENCE, 1.5))

    def test_a_clearly_larger_difference_is_refused(self):
        measured = {"L": 80.0, "a": -1.2, "b": 2.4}
        self.assertFalse(colour_within_tolerance(measured, REFERENCE, DEFAULT_DELTA_E_LIMIT))

    def test_lightness_outside_the_scale_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lab({"L": 101.0, "a": 0.0, "b": 0.0})

    def test_a_triple_of_the_wrong_length_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lab((92.0, -1.2))

    def test_a_boolean_lightness_is_refused(self):
        with self.assertRaises(ValueError):
            validate_lab({"L": True, "a": 0.0, "b": 0.0})

    def test_a_non_positive_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            colour_within_tolerance(REFERENCE, REFERENCE, 0.0)


class GlossTests(unittest.TestCase):
    def test_a_reading_inside_the_band_passes(self):
        self.assertTrue(gloss_within_band(12.0, (5.0, 20.0)))

    def test_a_reading_on_the_band_edge_passes(self):
        self.assertTrue(gloss_within_band(20.0, (5.0, 20.0)))

    def test_a_reading_above_the_band_fails(self):
        self.assertFalse(gloss_within_band(41.0, (5.0, 20.0)))

    def test_an_inverted_band_is_refused(self):
        with self.assertRaises(ValueError):
            gloss_within_band(12.0, (20.0, 5.0))

    def test_a_negative_gloss_reading_is_refused(self):
        with self.assertRaises(ValueError):
            gloss_within_band(-1.0, (5.0, 20.0))


class DefectTests(unittest.TestCase):
    def test_every_catalogued_defect_has_a_mechanism_family(self):
        for defect in APPEARANCE_DEFECTS:
            self.assertTrue(categorize_appearance_defect(defect))

    def test_a_run_is_grouped_as_a_flow_defect(self):
        self.assertEqual(categorize_appearance_defect("Run"), "flow")

    def test_an_unknown_defect_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_appearance_defect("sparkle")

    def test_density_is_per_square_metre_of_inspected_area(self):
        self.assertAlmostEqual(defect_density_per_m2({"inclusion": 6}, 3.0), 2.0, places=9)

    def test_zero_inspected_area_is_refused(self):
        with self.assertRaises(ValueError):
            defect_density_per_m2({"inclusion": 1}, 0.0)

    def test_a_negative_count_is_refused(self):
        with self.assertRaises(ValueError):
            defect_density_per_m2({"inclusion": -1}, 2.0)

    def test_density_exactly_on_the_limit_raises_no_finding(self):
        result = defect_findings({"inclusion": 8}, 2.0, 4.0)
        self.assertAlmostEqual(result["density_per_m2"], 4.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_single_blister_is_a_film_integrity_finding(self):
        result = defect_findings({"blister": 1}, 10.0, 4.0)
        self.assertIn("film-integrity-defect:blister", result["findings"])

    def test_defect_families_are_reported_for_the_present_defects_only(self):
        result = defect_findings({"run": 1, "inclusion": 0}, 2.0, 4.0)
        self.assertEqual(result["families"], ["flow"])


class ThermoOpticalTests(unittest.TestCase):
    def test_readings_inside_both_bands_raise_nothing(self):
        findings = thermo_optical_findings(
            {"absorptance": 0.18, "emittance": 0.88},
            {"absorptance": (0.12, 0.22), "emittance": (0.84, 0.92)},
        )
        self.assertEqual(findings, [])

    def test_absorptance_above_its_band_is_a_finding(self):
        findings = thermo_optical_findings(
            {"absorptance": 0.40, "emittance": 0.88},
            {"absorptance": (0.12, 0.22), "emittance": (0.84, 0.92)},
        )
        self.assertIn("solar-absorptance-outside-band", findings)

    def test_an_absent_band_set_is_its_own_finding(self):
        self.assertEqual(thermo_optical_findings({}, None), ["thermo-optical-band-absent"])

    def test_an_unmeasured_property_is_a_finding_not_a_pass(self):
        findings = thermo_optical_findings(
            {"absorptance": 0.18},
            {"absorptance": (0.12, 0.22), "emittance": (0.84, 0.92)},
        )
        self.assertIn("infrared-emittance-not-measured", findings)

    def test_an_emittance_outside_zero_to_one_is_refused(self):
        with self.assertRaises(ValueError):
            thermo_optical_findings(
                {"absorptance": 0.18, "emittance": 1.4},
                {"absorptance": (0.12, 0.22), "emittance": (0.84, 0.92)},
            )


class AreaAssessmentTests(unittest.TestCase):
    def test_a_conforming_area_is_accepted(self):
        result = assess_painted_area(_area())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"], "accepted")
        self.assertTrue(result["accepted"])

    def test_a_colour_miss_drives_rework(self):
        result = assess_painted_area(_area(measured_lab={"L": 80.0, "a": -1.2, "b": 2.4}))
        self.assertIn("colour-difference-exceeded", result["findings"])
        self.assertEqual(result["disposition"], "rework-required")

    def test_an_ungraded_gloss_is_a_review_finding_not_a_pass(self):
        result = assess_painted_area(_area(gloss_band=None))
        self.assertIn("gloss-not-verified", result["findings"])
        self.assertEqual(result["disposition"], "review-required")

    def test_a_non_thermal_area_owes_no_thermo_optical_numbers(self):
        result = assess_painted_area(
            _area(thermal_control=False, thermo_optical={}, thermo_optical_bands=None)
        )
        self.assertEqual(result["findings"], [])

    def test_an_area_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            assess_painted_area(_area(name="  "))

    def test_a_non_mapping_area_is_refused(self):
        with self.assertRaises(ValueError):
            assess_painted_area(["radiator-panel-A"])


class SurveyTests(unittest.TestCase):
    def test_a_survey_of_conforming_areas_passes(self):
        survey = assess_appearance_survey([_area(), _area(name="radiator-panel-B")])
        self.assertTrue(survey["survey_accepted"])
        self.assertEqual(survey["rework_areas"], [])

    def test_one_bad_area_fails_the_survey(self):
        survey = assess_appearance_survey(
            [_area(), _area(name="radiator-panel-B", defects={"blister": 2})]
        )
        self.assertFalse(survey["survey_accepted"])
        self.assertEqual(survey["rework_areas"], ["radiator-panel-B"])

    def test_duplicate_area_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_appearance_survey([_area(), _area()])

    def test_an_empty_survey_is_refused(self):
        with self.assertRaises(ValueError):
            assess_appearance_survey([])


if __name__ == "__main__":
    unittest.main()
