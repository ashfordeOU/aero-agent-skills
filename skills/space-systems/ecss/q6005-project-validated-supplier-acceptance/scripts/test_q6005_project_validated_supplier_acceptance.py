#!/usr/bin/env python3
"""Gate 3 contract test for q6005-project-validated-supplier-acceptance.

Offline, stdlib unittest. Exercises the validation-record and build-request
validation, the programme/technology/type/date coverage decision, the
assembly of the production acceptance steps a build owes, the outstanding
step comparison and the accept/refuse disposition of ECSS-Q-ST-60-05C clause
12.3 as paraphrased in the logic module. Every quantity here is an integer
count or a date, so no float bound is compared.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_project_validated_supplier_acceptance_logic import (  # noqa: E402
    BASE_ACCEPTANCE_STEPS,
    ENHANCED_RELIABILITY_ADDITIONAL_STEPS,
    FIRST_LOT_ADDITIONAL_STEPS,
    assess_project_validated_acceptance,
    missing_acceptance_steps,
    parse_date,
    required_acceptance_steps,
    validate_build_request,
    validate_validation_record,
    validation_covers,
)


def record(**overrides):
    base = {
        "programme": "SENTRY-4",
        "technology": "thick-film-hybrid",
        "hybrid_types": ["dc-dc-converter", "signal-conditioner"],
        "valid_from": "2026-01-01",
        "valid_until": "2027-12-31",
        "reference": "PV-2026-0187",
    }
    base.update(overrides)
    return base


def request(**overrides):
    base = {
        "programme": "SENTRY-4",
        "technology": "thick-film-hybrid",
        "hybrid_type": "dc-dc-converter",
        "build_date": "2026-09-01",
        "reliability_level": "standard",
        "first_production_lot": False,
    }
    base.update(overrides)
    return base


class RecordValidationTests(unittest.TestCase):
    def test_complete_record_normalises(self):
        normalised = validate_validation_record(record())
        self.assertEqual(normalised["programme"], "sentry-4")
        self.assertEqual(normalised["valid_until"], datetime.date(2027, 12, 31))

    def test_record_missing_a_required_key_is_refused(self):
        for key in ("programme", "technology", "valid_from", "valid_until"):
            bad = record()
            del bad[key]
            with self.assertRaises(ValueError):
                validate_validation_record(bad)

    def test_record_covering_no_hybrid_type_is_refused(self):
        with self.assertRaises(ValueError):
            validate_validation_record(record(hybrid_types=[]))

    def test_string_of_types_is_not_a_type_list(self):
        with self.assertRaises(ValueError):
            validate_validation_record(record(hybrid_types="dc-dc-converter"))

    def test_expiry_before_start_is_refused(self):
        with self.assertRaises(ValueError):
            validate_validation_record(record(valid_from="2027-01-01", valid_until="2026-01-01"))

    def test_non_iso_date_is_refused(self):
        with self.assertRaises(ValueError):
            validate_validation_record(record(valid_until="31/12/2027"))

    def test_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            validate_validation_record([("programme", "SENTRY-4")])

    def test_date_objects_are_accepted_as_well_as_strings(self):
        self.assertEqual(parse_date(datetime.date(2026, 5, 4), "d"), datetime.date(2026, 5, 4))


class RequestValidationTests(unittest.TestCase):
    def test_complete_request_normalises(self):
        normalised = validate_build_request(request())
        self.assertEqual(normalised["hybrid_type"], "dc-dc-converter")
        self.assertFalse(normalised["first_production_lot"])

    def test_request_missing_a_required_key_is_refused(self):
        for key in ("programme", "technology", "hybrid_type", "build_date"):
            bad = request()
            del bad[key]
            with self.assertRaises(ValueError):
                validate_build_request(bad)

    def test_unknown_reliability_level_is_refused(self):
        with self.assertRaises(ValueError):
            validate_build_request(request(reliability_level="ultra"))

    def test_non_boolean_first_lot_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_build_request(request(first_production_lot="yes"))

    def test_reliability_level_defaults_to_standard(self):
        bare = request()
        del bare["reliability_level"]
        self.assertEqual(validate_build_request(bare)["reliability_level"], "standard")

    def test_tokens_are_matched_case_and_separator_insensitively(self):
        normalised = validate_build_request(request(hybrid_type="DC DC Converter"))
        self.assertEqual(normalised["hybrid_type"], "dc-dc-converter")


class CoverageTests(unittest.TestCase):
    def test_build_inside_the_validation_scope_is_covered(self):
        result = validation_covers(record(), request())
        self.assertTrue(result["covered"])
        self.assertEqual(result["reasons"], [])

    def test_another_programme_is_not_covered(self):
        result = validation_covers(record(), request(programme="ORBIS-2"))
        self.assertFalse(result["covered"])
        self.assertTrue(any("scoped to programme" in r for r in result["reasons"]))

    def test_another_technology_is_not_covered(self):
        result = validation_covers(record(), request(technology="thin-film-hybrid"))
        self.assertTrue(any("technology" in r for r in result["reasons"]))

    def test_unvalidated_hybrid_type_is_not_covered(self):
        result = validation_covers(record(), request(hybrid_type="rf-front-end"))
        self.assertTrue(any("not among the validated types" in r for r in result["reasons"]))

    def test_build_before_the_validation_window_is_not_covered(self):
        result = validation_covers(record(), request(build_date="2025-06-01"))
        self.assertTrue(any("precedes the validation start" in r for r in result["reasons"]))

    def test_build_after_the_validation_expiry_is_not_covered(self):
        result = validation_covers(record(), request(build_date="2028-02-01"))
        self.assertTrue(any("past the validation expiry" in r for r in result["reasons"]))

    def test_build_on_the_window_edges_is_covered(self):
        for edge in ("2026-01-01", "2027-12-31"):
            self.assertTrue(validation_covers(record(), request(build_date=edge))["covered"])

    def test_every_failing_condition_is_named_not_only_the_first(self):
        result = validation_covers(
            record(), request(programme="ORBIS-2", hybrid_type="rf-front-end")
        )
        self.assertEqual(len(result["reasons"]), 2)


class AcceptanceStepTests(unittest.TestCase):
    def test_standard_repeat_build_owes_the_base_steps_only(self):
        self.assertEqual(required_acceptance_steps(request()), list(BASE_ACCEPTANCE_STEPS))

    def test_first_production_lot_adds_its_own_steps(self):
        steps = required_acceptance_steps(request(first_production_lot=True))
        for step in FIRST_LOT_ADDITIONAL_STEPS:
            self.assertIn(step, steps)

    def test_enhanced_reliability_adds_its_own_steps(self):
        steps = required_acceptance_steps(request(reliability_level="enhanced"))
        for step in ENHANCED_RELIABILITY_ADDITIONAL_STEPS:
            self.assertIn(step, steps)

    def test_first_lot_at_enhanced_level_owes_both_additions(self):
        steps = required_acceptance_steps(
            request(first_production_lot=True, reliability_level="enhanced")
        )
        self.assertEqual(
            len(steps),
            len(BASE_ACCEPTANCE_STEPS)
            + len(FIRST_LOT_ADDITIONAL_STEPS)
            + len(ENHANCED_RELIABILITY_ADDITIONAL_STEPS),
        )

    def test_nothing_performed_leaves_every_step_outstanding(self):
        self.assertEqual(missing_acceptance_steps(request(), []), list(BASE_ACCEPTANCE_STEPS))

    def test_everything_performed_leaves_nothing_outstanding(self):
        self.assertEqual(missing_acceptance_steps(request(), list(BASE_ACCEPTANCE_STEPS)), [])

    def test_step_names_are_matched_case_and_separator_insensitively(self):
        performed = [s.replace("-", " ").upper() for s in BASE_ACCEPTANCE_STEPS]
        self.assertEqual(missing_acceptance_steps(request(), performed), [])

    def test_string_of_steps_is_not_a_step_list(self):
        with self.assertRaises(ValueError):
            missing_acceptance_steps(request(), "lot-construction-analysis")

    def test_blank_step_name_is_refused(self):
        with self.assertRaises(ValueError):
            missing_acceptance_steps(request(), ["   "])


class AssessmentTests(unittest.TestCase):
    def test_in_scope_build_with_every_step_run_is_accepted(self):
        result = assess_project_validated_acceptance(
            {
                "validation": record(),
                "request": request(),
                "performed_steps": list(BASE_ACCEPTANCE_STEPS),
            }
        )
        self.assertEqual(result["disposition"], "accept")
        self.assertTrue(result["accepted"])
        self.assertFalse(result["out_of_scope"])
        self.assertEqual(result["steps_completed"], len(BASE_ACCEPTANCE_STEPS))

    def test_out_of_scope_build_is_refused_even_with_every_step_run(self):
        result = assess_project_validated_acceptance(
            {
                "validation": record(),
                "request": request(programme="ORBIS-2"),
                "performed_steps": list(BASE_ACCEPTANCE_STEPS),
            }
        )
        self.assertEqual(result["disposition"], "refuse")
        self.assertTrue(result["out_of_scope"])
        self.assertEqual(result["outstanding_steps"], [])

    def test_in_scope_build_with_a_step_outstanding_is_refused(self):
        performed = [s for s in BASE_ACCEPTANCE_STEPS if s != "lot-construction-analysis"]
        result = assess_project_validated_acceptance(
            {"validation": record(), "request": request(), "performed_steps": performed}
        )
        self.assertEqual(result["disposition"], "refuse")
        self.assertFalse(result["out_of_scope"])
        self.assertEqual(result["outstanding_steps"], ["lot-construction-analysis"])

    def test_first_lot_build_owes_more_than_a_repeat_build(self):
        result = assess_project_validated_acceptance(
            {
                "validation": record(),
                "request": request(first_production_lot=True),
                "performed_steps": list(BASE_ACCEPTANCE_STEPS),
            }
        )
        self.assertEqual(len(result["outstanding_steps"]), len(FIRST_LOT_ADDITIONAL_STEPS))

    def test_performed_steps_default_to_none_run(self):
        result = assess_project_validated_acceptance(
            {"validation": record(), "request": request()}
        )
        self.assertEqual(result["steps_completed"], 0)

    def test_report_carries_the_validation_reference(self):
        result = assess_project_validated_acceptance(
            {"validation": record(), "request": request()}
        )
        self.assertEqual(result["validation_reference"], "PV-2026-0187")

    def test_missing_required_key_is_refused(self):
        for key in ("validation", "request"):
            spec = {"validation": record(), "request": request()}
            del spec[key]
            with self.assertRaises(ValueError):
                assess_project_validated_acceptance(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_project_validated_acceptance([("validation", record())])


if __name__ == "__main__":
    unittest.main(verbosity=2)
