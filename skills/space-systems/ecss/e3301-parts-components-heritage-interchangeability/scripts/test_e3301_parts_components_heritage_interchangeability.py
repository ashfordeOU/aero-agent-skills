"""Contract tests for the ECSS-E-ST-33-01 heritage and interchangeability logic."""

import unittest

from e3301_parts_components_heritage_interchangeability_logic import (
    DEFAULT_DELTA_LIMIT,
    HERITAGE_ACCEPTED,
    HERITAGE_DELTA,
    HERITAGE_FULL,
    PARAMETER_SENSE,
    assess_heritage,
    assess_interchangeability,
    assess_parts_and_interchangeability,
    envelope_assessment,
    heritage_verdict,
    severity,
    validate_envelope,
    validate_feature,
    worst_case_clearance,
)

QUALIFIED = {
    "temperature_max_k": 353.0,
    "temperature_min_k": 233.0,
    "operating_cycles": 100000.0,
    "peak_load_n": 500.0,
}

BENIGN_APPLICATION = {
    "temperature_max_k": 343.0,
    "temperature_min_k": 243.0,
    "operating_cycles": 50000.0,
    "peak_load_n": 400.0,
}


def application(**overrides):
    """Return an application envelope built from the benign one."""
    envelope = dict(BENIGN_APPLICATION)
    envelope.update(overrides)
    return envelope


def part(**overrides):
    """Return a heritage claim with a benign application."""
    claim = {
        "id": "PRT-BEARING-01",
        "qualified_envelope": dict(QUALIFIED),
        "application_envelope": application(),
    }
    claim.update(overrides)
    return claim


def shaft(nominal=9.95, plus=0.01, minus=0.01):
    """Return a shaft feature."""
    return {"nominal_mm": nominal, "plus_tol_mm": plus, "minus_tol_mm": minus}


def hole(nominal=10.0, plus=0.02, minus=0.0):
    """Return a hole feature."""
    return {"nominal_mm": nominal, "plus_tol_mm": plus, "minus_tol_mm": minus}


def group(**overrides):
    """Return an interchangeable group of two shafts and one mating hole."""
    record = {
        "id": "GRP-PIVOT-PIN",
        "items": [
            {"id": "PIN-A", "shaft": shaft()},
            {"id": "PIN-B", "shaft": shaft(nominal=9.96)},
        ],
        "mating_features": [{"id": "BRACKET-BORE", "hole": hole()}],
        "max_clearance_mm": 0.10,
    }
    record.update(overrides)
    return record


class EnvelopeValidationTests(unittest.TestCase):
    def test_known_parameters_validate(self):
        envelope = validate_envelope(QUALIFIED)
        self.assertAlmostEqual(envelope["peak_load_n"], 500.0)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"humidity_percent": 40.0})

    def test_empty_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({})

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"peak_load_n": -10.0})

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_envelope({"peak_load_n": True})

    def test_sense_table_covers_both_directions(self):
        self.assertEqual(PARAMETER_SENSE["temperature_max_k"], "upper")
        self.assertEqual(PARAMETER_SENSE["temperature_min_k"], "lower")
        self.assertEqual(PARAMETER_SENSE["ambient_pressure_pa"], "lower")


class SeverityTests(unittest.TestCase):
    def test_upper_sense_exceedance_is_positive_when_hotter(self):
        record = severity("temperature_max_k", 353.0, 363.0)
        self.assertAlmostEqual(record["exceedance"], 10.0)
        self.assertFalse(record["within_envelope"])

    def test_upper_sense_is_within_when_cooler(self):
        record = severity("temperature_max_k", 353.0, 343.0)
        self.assertAlmostEqual(record["exceedance"], -10.0)
        self.assertTrue(record["within_envelope"])

    def test_lower_sense_exceedance_is_positive_when_colder(self):
        record = severity("temperature_min_k", 233.0, 213.0)
        self.assertAlmostEqual(record["exceedance"], 20.0)
        self.assertFalse(record["within_envelope"])

    def test_lower_sense_is_within_when_warmer(self):
        record = severity("temperature_min_k", 233.0, 243.0)
        self.assertTrue(record["within_envelope"])

    def test_relative_exceedance_is_normalised_by_the_bound(self):
        record = severity("operating_cycles", 100000.0, 125000.0)
        self.assertAlmostEqual(record["relative_exceedance"], 0.25, places=9)

    def test_equal_values_sit_exactly_on_the_envelope(self):
        record = severity("peak_load_n", 500.0, 500.0)
        self.assertAlmostEqual(record["exceedance"], 0.0, places=9)
        self.assertTrue(record["within_envelope"])

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            severity("humidity_percent", 40.0, 50.0)

    def test_non_positive_applied_value_rejected(self):
        with self.assertRaises(ValueError):
            severity("peak_load_n", 500.0, 0.0)


class EnvelopeAssessmentTests(unittest.TestCase):
    def test_benign_application_exceeds_nothing(self):
        assessment = envelope_assessment(QUALIFIED, application())
        self.assertEqual(assessment["exceeded_parameters"], [])
        self.assertEqual(assessment["uncovered_parameters"], [])

    def test_exceeded_parameters_are_named(self):
        assessment = envelope_assessment(QUALIFIED, application(peak_load_n=600.0))
        self.assertEqual(assessment["exceeded_parameters"], ["peak_load_n"])

    def test_parameter_absent_from_the_qualification_is_uncovered(self):
        assessment = envelope_assessment(
            QUALIFIED, application(radiation_dose_krad=20.0))
        self.assertEqual(assessment["uncovered_parameters"], ["radiation_dose_krad"])

    def test_worst_relative_exceedance_picks_the_largest(self):
        assessment = envelope_assessment(
            QUALIFIED, application(operating_cycles=200000.0, peak_load_n=550.0))
        self.assertAlmostEqual(assessment["worst_relative_exceedance"], 1.0, places=9)


class HeritageVerdictTests(unittest.TestCase):
    def test_benign_application_keeps_the_heritage(self):
        assessment = envelope_assessment(QUALIFIED, application())
        self.assertEqual(heritage_verdict(assessment), HERITAGE_ACCEPTED)

    def test_small_exceedance_needs_a_delta_qualification(self):
        assessment = envelope_assessment(QUALIFIED, application(operating_cycles=110000.0))
        self.assertEqual(heritage_verdict(assessment), HERITAGE_DELTA)

    def test_exceedance_exactly_on_the_delta_limit_stays_a_delta(self):
        assessment = envelope_assessment(QUALIFIED, application(operating_cycles=125000.0))
        self.assertAlmostEqual(
            assessment["worst_relative_exceedance"], DEFAULT_DELTA_LIMIT, places=9)
        self.assertEqual(heritage_verdict(assessment), HERITAGE_DELTA)

    def test_gross_exceedance_needs_a_full_requalification(self):
        assessment = envelope_assessment(QUALIFIED, application(operating_cycles=200000.0))
        self.assertEqual(heritage_verdict(assessment), HERITAGE_FULL)

    def test_uncovered_parameter_needs_a_full_requalification(self):
        assessment = envelope_assessment(
            QUALIFIED, application(radiation_dose_krad=20.0))
        self.assertEqual(heritage_verdict(assessment), HERITAGE_FULL)

    def test_changed_configuration_needs_a_full_requalification(self):
        assessment = envelope_assessment(QUALIFIED, application())
        self.assertEqual(heritage_verdict(assessment, False), HERITAGE_FULL)

    def test_non_boolean_configuration_flag_rejected(self):
        assessment = envelope_assessment(QUALIFIED, application())
        with self.assertRaises(ValueError):
            heritage_verdict(assessment, "yes")

    def test_malformed_assessment_rejected(self):
        with self.assertRaises(ValueError):
            heritage_verdict({"exceeded": []})


class HeritageClaimTests(unittest.TestCase):
    def test_clean_claim_is_reusable_as_is(self):
        record = assess_heritage(part())
        self.assertTrue(record["reusable_as_is"])
        self.assertEqual(record["findings"], [])

    def test_exceeding_claim_carries_a_finding(self):
        record = assess_heritage(part(
            application_envelope=application(peak_load_n=600.0)))
        self.assertEqual(record["verdict"], HERITAGE_DELTA)
        self.assertTrue(any("exceeds its qualified peak_load_n" in f
                            for f in record["findings"]))

    def test_uncovered_parameter_carries_its_own_finding(self):
        record = assess_heritage(part(
            application_envelope=application(radiation_dose_krad=20.0)))
        self.assertTrue(any("never covered" in f for f in record["findings"]))

    def test_changed_configuration_carries_its_own_finding(self):
        record = assess_heritage(part(configuration_identical=False))
        self.assertTrue(any("configuration it was qualified in" in f
                            for f in record["findings"]))

    def test_delta_limit_can_be_tightened(self):
        record = assess_heritage(part(
            application_envelope=application(operating_cycles=110000.0),
            delta_limit=0.05,
        ))
        self.assertEqual(record["verdict"], HERITAGE_FULL)

    def test_missing_key_rejected(self):
        claim = part()
        del claim["qualified_envelope"]
        with self.assertRaises(ValueError):
            assess_heritage(claim)

    def test_non_mapping_claim_rejected(self):
        with self.assertRaises(ValueError):
            assess_heritage(["PRT-BEARING-01"])


class FeatureAndStackTests(unittest.TestCase):
    def test_feature_validates(self):
        record = validate_feature(hole())
        self.assertAlmostEqual(record["nominal_mm"], 10.0)

    def test_minus_tolerance_larger_than_the_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_feature({"nominal_mm": 0.5, "plus_tol_mm": 0.0, "minus_tol_mm": 0.6})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_feature({"nominal_mm": 10.0, "plus_tol_mm": -0.01,
                              "minus_tol_mm": 0.0})

    def test_missing_feature_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_feature({"nominal_mm": 10.0, "plus_tol_mm": 0.01})

    def test_tightest_clearance_uses_the_small_hole_and_big_shaft(self):
        clearance = worst_case_clearance(hole(), shaft())
        self.assertAlmostEqual(clearance["min_clearance_mm"], 0.04, places=9)

    def test_loosest_clearance_uses_the_big_hole_and_small_shaft(self):
        clearance = worst_case_clearance(hole(), shaft())
        self.assertAlmostEqual(clearance["max_clearance_mm"], 0.08, places=9)

    def test_line_to_line_stack_is_exactly_zero(self):
        clearance = worst_case_clearance(
            {"nominal_mm": 10.0, "plus_tol_mm": 0.0, "minus_tol_mm": 0.0},
            {"nominal_mm": 10.0, "plus_tol_mm": 0.0, "minus_tol_mm": 0.0},
        )
        self.assertAlmostEqual(clearance["min_clearance_mm"], 0.0, places=9)


class InterchangeabilityTests(unittest.TestCase):
    def test_clean_group_is_interchangeable(self):
        result = assess_interchangeability(group())
        self.assertTrue(result["interchangeable"])
        self.assertAlmostEqual(result["fitting_fraction"], 1.0, places=9)

    def test_every_item_is_paired_with_every_mating_feature(self):
        record = group(mating_features=[
            {"id": "BRACKET-BORE", "hole": hole()},
            {"id": "LEVER-BORE", "hole": hole(nominal=10.01)},
        ])
        self.assertEqual(assess_interchangeability(record)["pair_count"], 4)

    def test_oversized_item_interferes(self):
        record = group(items=[
            {"id": "PIN-A", "shaft": shaft()},
            {"id": "PIN-B", "shaft": shaft(nominal=10.01)},
        ])
        result = assess_interchangeability(record)
        self.assertFalse(result["interchangeable"])
        self.assertTrue(any("interference" in f for f in result["findings"]))

    def test_loose_fit_past_the_ceiling_is_a_finding(self):
        result = assess_interchangeability(group(max_clearance_mm=0.05))
        self.assertFalse(result["interchangeable"])
        self.assertTrue(any("the function allows" in f for f in result["findings"]))

    def test_clearance_exactly_on_the_ceiling_still_fits(self):
        result = assess_interchangeability(group(max_clearance_mm=0.08))
        self.assertTrue(result["interchangeable"])

    def test_zero_clearance_stack_still_fits(self):
        record = group(
            items=[
                {"id": "PIN-A", "shaft": {"nominal_mm": 10.0, "plus_tol_mm": 0.0,
                                          "minus_tol_mm": 0.0}},
                {"id": "PIN-B", "shaft": {"nominal_mm": 10.0, "plus_tol_mm": 0.0,
                                          "minus_tol_mm": 0.0}},
            ],
            mating_features=[{"id": "BRACKET-BORE",
                              "hole": {"nominal_mm": 10.0, "plus_tol_mm": 0.0,
                                       "minus_tol_mm": 0.0}}],
        )
        self.assertTrue(assess_interchangeability(record)["interchangeable"])

    def test_selective_fit_breaks_interchangeability(self):
        record = group(items=[
            {"id": "PIN-A", "shaft": shaft(), "selective_fit": True},
            {"id": "PIN-B", "shaft": shaft(nominal=9.96)},
        ])
        result = assess_interchangeability(record)
        self.assertFalse(result["interchangeable"])
        self.assertTrue(any("selective fit" in f for f in result["findings"]))

    def test_match_marking_breaks_interchangeability(self):
        record = group(items=[
            {"id": "PIN-A", "shaft": shaft(), "match_marked": True},
            {"id": "PIN-B", "shaft": shaft(nominal=9.96)},
        ])
        self.assertFalse(assess_interchangeability(record)["interchangeable"])

    def test_single_item_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_interchangeability(group(items=[{"id": "PIN-A", "shaft": shaft()}]))

    def test_group_without_a_mating_feature_rejected(self):
        with self.assertRaises(ValueError):
            assess_interchangeability(group(mating_features=[]))

    def test_repeated_item_identifier_rejected(self):
        record = group(items=[
            {"id": "PIN-A", "shaft": shaft()},
            {"id": "PIN-A", "shaft": shaft(nominal=9.96)},
        ])
        with self.assertRaises(ValueError):
            assess_interchangeability(record)

    def test_non_boolean_flag_rejected(self):
        record = group(items=[
            {"id": "PIN-A", "shaft": shaft(), "selective_fit": "yes"},
            {"id": "PIN-B", "shaft": shaft(nominal=9.96)},
        ])
        with self.assertRaises(ValueError):
            assess_interchangeability(record)


class CombinedAssessmentTests(unittest.TestCase):
    def test_clean_set_is_compliant(self):
        result = assess_parts_and_interchangeability({
            "parts": [part()],
            "groups": [group()],
        })
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["heritage_fraction"], 1.0, places=9)

    def test_findings_from_both_halves_are_collected(self):
        result = assess_parts_and_interchangeability({
            "parts": [part(application_envelope=application(peak_load_n=600.0))],
            "groups": [group(max_clearance_mm=0.05)],
        })
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_parts_only_set_is_accepted(self):
        result = assess_parts_and_interchangeability({"parts": [part()]})
        self.assertEqual(result["part_count"], 1)
        self.assertEqual(result["groups"], [])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_and_interchangeability({"parts": [], "groups": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_and_interchangeability(["parts"])


if __name__ == "__main__":
    unittest.main()
