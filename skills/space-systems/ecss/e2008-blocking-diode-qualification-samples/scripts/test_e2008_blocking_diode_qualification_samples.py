"""Contract tests for the clause 12.5.4 qualification sample conformance leaf.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, a
document that cannot serve as a baseline, a sample citing the wrong issue
or built before that issue took effect, a build parameter outside its
declared band, a declared parameter with nothing recorded against it, and
a submitted set carrying more nonconformance than the policy admits.
"""

import unittest

from e2008_blocking_diode_qualification_samples_logic import (
    BUILD_PARAMETER_NOT_RECORDED,
    BUILD_PARAMETER_OUT_OF_BAND,
    BUILT_BEFORE_ISSUE_EFFECTIVE,
    CONSTRUCTION_OUTSIDE_SCOPE,
    DEFAULT_CONFORMANCE_POLICY,
    PROCESS_IDENTIFICATION_NOT_ESTABLISHED,
    PROCESS_ISSUE_MISMATCH,
    PROCESS_REFERENCE_MISMATCH,
    SAMPLES_CONFORM,
    SAMPLES_DO_NOT_CONFORM,
    assess_qualification_sample_conformance,
    band_utilisation,
    marginal_sample_advisories,
    nonconforming_fraction,
    parameter_within_band,
    sample_conformance,
    sample_conformances,
    validate_conformance_policy,
    validate_declared_parameter,
    validate_process_identification,
    validate_sample_record,
    within_nonconformance_allowance,
    worst_sample,
)

JUNCTION_NOMINAL = 1.20
JUNCTION_TOLERANCE = 0.05
METAL_NOMINAL = 4.0
METAL_TOLERANCE = 0.4


def _policy(**overrides):
    policy = dict(DEFAULT_CONFORMANCE_POLICY)
    policy.update(overrides)
    return policy


def _document(**overrides):
    document = {
        "reference": "PID-4417",
        "issue": "C",
        "effective_day": 120.0,
        "construction": "planar",
        "parameters": [
            {
                "name": "junction-depth-um",
                "nominal": JUNCTION_NOMINAL,
                "tolerance": JUNCTION_TOLERANCE,
            },
            {
                "name": "contact-metal-thickness-um",
                "nominal": METAL_NOMINAL,
                "tolerance": METAL_TOLERANCE,
            },
        ],
    }
    document.update(overrides)
    return document


def _sample(identifier, **overrides):
    sample = {
        "id": identifier,
        "process_reference": "PID-4417",
        "process_issue": "C",
        "build_day": 145.0,
        "construction": "planar",
        "parameters": {
            "junction-depth-um": 1.21,
            "contact-metal-thickness-um": 4.05,
        },
    }
    sample.update(overrides)
    return sample


def _samples():
    return [_sample("qs-01"), _sample("qs-02"), _sample("qs-03")]


def _case(**overrides):
    case = {"process_identification": _document(), "samples": _samples()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_conformance_policy(DEFAULT_CONFORMANCE_POLICY),
            DEFAULT_CONFORMANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_conformance_policy("max_nonconforming_fraction")

    def test_a_nonconformance_allowance_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_conformance_policy(_policy(max_nonconforming_fraction=1.2))

    def test_a_negative_nonconformance_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_conformance_policy(_policy(max_nonconforming_fraction=-0.1))

    def test_a_zero_allowance_is_the_legitimate_default(self):
        self.assertAlmostEqual(
            float(DEFAULT_CONFORMANCE_POLICY["max_nonconforming_fraction"]),
            0.0,
            places=12,
        )

    def test_a_marginal_point_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_conformance_policy(_policy(marginal_band_utilisation=1.4))


class DocumentTests(unittest.TestCase):
    def test_an_identified_document_validates(self):
        checked = validate_process_identification(_document())
        self.assertEqual(checked["reference"], "PID-4417")
        self.assertEqual(checked["issue"], "C")
        self.assertEqual(len(checked["parameters"]), 2)

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_identification("PID-4417")

    def test_a_non_string_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_identification(_document(issue=3))

    def test_a_negative_effective_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_identification(_document(effective_day=-1.0))

    def test_a_parameter_declared_twice_rejected(self):
        document = _document()
        document["parameters"].append(dict(document["parameters"][0]))
        with self.assertRaises(ValueError):
            validate_process_identification(document)

    def test_a_zero_tolerance_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_parameter(
                {"name": "junction-depth-um", "nominal": 1.2, "tolerance": 0.0}
            )

    def test_a_blank_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_parameter(
                {"name": "  ", "nominal": 1.2, "tolerance": 0.05}
            )

    def test_a_blank_reference_survives_validation_for_the_assessor(self):
        checked = validate_process_identification(_document(reference="   "))
        self.assertEqual(checked["reference"], "")


class SampleRecordTests(unittest.TestCase):
    def test_a_sample_record_is_read_back(self):
        record = validate_sample_record(_sample("qs-01"))
        self.assertEqual(record["id"], "qs-01")
        self.assertEqual(record["process_issue"], "C")
        self.assertAlmostEqual(record["build_day"], 145.0, places=12)

    def test_a_blank_sample_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_record(_sample(" "))

    def test_a_boolean_build_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_record(_sample("qs-01", build_day=True))

    def test_a_non_mapping_parameter_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_record(_sample("qs-01", parameters=[1.21, 4.05]))


class BandTests(unittest.TestCase):
    def test_a_value_on_nominal_has_spent_nothing(self):
        self.assertAlmostEqual(
            band_utilisation(JUNCTION_NOMINAL, JUNCTION_NOMINAL, JUNCTION_TOLERANCE),
            0.0,
            places=12,
        )

    def test_a_value_on_the_limit_has_spent_the_whole_band(self):
        self.assertAlmostEqual(
            band_utilisation(
                JUNCTION_NOMINAL + JUNCTION_TOLERANCE,
                JUNCTION_NOMINAL,
                JUNCTION_TOLERANCE,
            ),
            1.0,
            places=9,
        )

    def test_the_band_is_two_sided(self):
        self.assertAlmostEqual(
            band_utilisation(
                JUNCTION_NOMINAL - JUNCTION_TOLERANCE,
                JUNCTION_NOMINAL,
                JUNCTION_TOLERANCE,
            ),
            1.0,
            places=9,
        )

    def test_a_value_exactly_on_the_limit_is_inside_the_band(self):
        self.assertTrue(
            parameter_within_band(
                JUNCTION_NOMINAL + JUNCTION_TOLERANCE,
                JUNCTION_NOMINAL,
                JUNCTION_TOLERANCE,
            )
        )

    def test_a_value_clearly_past_the_limit_is_outside(self):
        self.assertFalse(
            parameter_within_band(
                JUNCTION_NOMINAL + 2.0 * JUNCTION_TOLERANCE,
                JUNCTION_NOMINAL,
                JUNCTION_TOLERANCE,
            )
        )

    def test_a_zero_tolerance_is_rejected_rather_than_divided_by(self):
        with self.assertRaises(ValueError):
            band_utilisation(1.21, 1.20, 0.0)


class SampleConformanceTests(unittest.TestCase):
    def test_a_sample_built_to_the_document_conforms(self):
        result = sample_conformance(_sample("qs-01"), _document())
        self.assertTrue(result["conforming"])
        self.assertEqual(result["reasons"], ())

    def test_a_wrong_issue_is_a_nonconformance(self):
        result = sample_conformance(_sample("qs-04", process_issue="B"), _document())
        self.assertFalse(result["conforming"])
        self.assertIn(PROCESS_ISSUE_MISMATCH, result["reasons"])

    def test_a_wrong_document_reference_is_a_nonconformance(self):
        result = sample_conformance(
            _sample("qs-05", process_reference="PID-9001"), _document()
        )
        self.assertIn(PROCESS_REFERENCE_MISMATCH, result["reasons"])

    def test_a_sample_built_before_the_issue_took_effect_is_caught(self):
        result = sample_conformance(_sample("qs-06", build_day=90.0), _document())
        self.assertIn(BUILT_BEFORE_ISSUE_EFFECTIVE, result["reasons"])

    def test_a_sample_built_on_the_effective_day_is_admitted(self):
        result = sample_conformance(_sample("qs-07", build_day=120.0), _document())
        self.assertNotIn(BUILT_BEFORE_ISSUE_EFFECTIVE, result["reasons"])
        self.assertTrue(result["conforming"])

    def test_a_construction_outside_the_document_scope_is_caught(self):
        result = sample_conformance(_sample("qs-08", construction="mesa"), _document())
        self.assertIn(CONSTRUCTION_OUTSIDE_SCOPE, result["reasons"])

    def test_a_parameter_outside_its_band_is_caught_and_named(self):
        result = sample_conformance(
            _sample(
                "qs-09",
                parameters={
                    "junction-depth-um": 1.40,
                    "contact-metal-thickness-um": 4.05,
                },
            ),
            _document(),
        )
        self.assertIn(BUILD_PARAMETER_OUT_OF_BAND, result["reasons"])
        self.assertTrue(
            any("junction-depth-um" in line for line in result["parameter_findings"])
        )

    def test_an_unrecorded_parameter_is_held_apart_from_a_drifted_one(self):
        result = sample_conformance(
            _sample("qs-10", parameters={"junction-depth-um": 1.21}), _document()
        )
        self.assertIn(BUILD_PARAMETER_NOT_RECORDED, result["reasons"])
        self.assertNotIn(BUILD_PARAMETER_OUT_OF_BAND, result["reasons"])

    def test_every_nonconformance_is_named_not_only_the_first(self):
        result = sample_conformance(
            _sample("qs-11", process_issue="A", construction="mesa", build_day=10.0),
            _document(),
        )
        self.assertGreaterEqual(len(result["reasons"]), 3)

    def test_the_worst_parameter_travels_with_the_sample(self):
        result = sample_conformance(
            _sample(
                "qs-12",
                parameters={
                    "junction-depth-um": 1.245,
                    "contact-metal-thickness-um": 4.02,
                },
            ),
            _document(),
        )
        self.assertEqual(result["worst_parameter"], "junction-depth-um")

    def test_a_duplicate_sample_id_rejected(self):
        samples = _samples()
        samples[2]["id"] = "qs-01"
        with self.assertRaises(ValueError):
            sample_conformances(samples, _document())

    def test_an_empty_submitted_set_rejected(self):
        with self.assertRaises(ValueError):
            sample_conformances([], _document())


class SetTests(unittest.TestCase):
    def test_a_clean_set_has_no_nonconformance(self):
        results = sample_conformances(_samples(), _document())
        self.assertAlmostEqual(nonconforming_fraction(results), 0.0, places=12)

    def test_one_bad_sample_in_four_is_a_quarter(self):
        samples = _samples()
        samples.append(_sample("qs-04", process_issue="B"))
        results = sample_conformances(samples, _document())
        self.assertAlmostEqual(nonconforming_fraction(results), 0.25, places=12)

    def test_a_set_exactly_on_the_allowance_is_admitted(self):
        samples = _samples()
        samples.append(_sample("qs-04", process_issue="B"))
        results = sample_conformances(samples, _document())
        self.assertTrue(
            within_nonconformance_allowance(
                results, _policy(max_nonconforming_fraction=0.25)
            )
        )

    def test_the_worst_sample_is_the_one_deepest_into_a_band(self):
        samples = _samples()
        samples[1] = _sample(
            "qs-02",
            parameters={
                "junction-depth-um": 1.245,
                "contact-metal-thickness-um": 4.05,
            },
        )
        results = sample_conformances(samples, _document())
        self.assertEqual(worst_sample(results)["id"], "qs-02")

    def test_an_empty_result_set_rejected_by_the_worst_sample_search(self):
        with self.assertRaises(ValueError):
            worst_sample([])

    def test_a_sample_against_its_process_limit_raises_an_advisory(self):
        results = sample_conformances(
            [
                _sample(
                    "qs-13",
                    parameters={
                        "junction-depth-um": JUNCTION_NOMINAL
                        + 0.96 * JUNCTION_TOLERANCE,
                        "contact-metal-thickness-um": METAL_NOMINAL,
                    },
                )
            ],
            _document(),
        )
        advisories = marginal_sample_advisories(results)
        self.assertEqual(len(advisories), 1)
        self.assertIn("qs-13", advisories[0])

    def test_a_comfortable_set_raises_no_advisory(self):
        results = sample_conformances(_samples(), _document())
        self.assertEqual(marginal_sample_advisories(results), ())


class AssessmentTests(unittest.TestCase):
    def test_a_conforming_set_passes(self):
        result = assess_qualification_sample_conformance(_case())
        self.assertEqual(result["verdict"], SAMPLES_CONFORM)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["conforming_samples"]), 3)

    def test_a_missing_document_closes_the_assessment(self):
        case = _case()
        del case["process_identification"]
        result = assess_qualification_sample_conformance(case)
        self.assertEqual(result["verdict"], PROCESS_IDENTIFICATION_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_blank_issue_closes_the_assessment(self):
        result = assess_qualification_sample_conformance(
            _case(process_identification=_document(issue="   "))
        )
        self.assertEqual(result["verdict"], PROCESS_IDENTIFICATION_NOT_ESTABLISHED)

    def test_a_document_declaring_no_band_closes_the_assessment(self):
        result = assess_qualification_sample_conformance(
            _case(process_identification=_document(parameters=[]))
        )
        self.assertEqual(result["verdict"], PROCESS_IDENTIFICATION_NOT_ESTABLISHED)

    def test_one_wrong_issue_fails_the_default_zero_allowance(self):
        samples = _samples()
        samples[0] = _sample("qs-01", process_issue="B")
        result = assess_qualification_sample_conformance(_case(samples=samples))
        self.assertEqual(result["verdict"], SAMPLES_DO_NOT_CONFORM)
        self.assertIn("qs-01", result["nonconforming_samples"])

    def test_every_bad_sample_is_reported_not_only_the_first(self):
        samples = _samples()
        samples[0] = _sample("qs-01", process_issue="B")
        samples[1] = _sample("qs-02", construction="mesa")
        result = assess_qualification_sample_conformance(_case(samples=samples))
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_the_worst_sample_travels_with_the_verdict(self):
        result = assess_qualification_sample_conformance(_case())
        self.assertIn(result["worst_sample_id"], ("qs-01", "qs-02", "qs-03"))
        self.assertGreaterEqual(result["worst_band_utilisation"], 0.0)

    def test_advisories_do_not_move_the_verdict(self):
        samples = [
            _sample(
                "qs-14",
                parameters={
                    "junction-depth-um": JUNCTION_NOMINAL + 0.95 * JUNCTION_TOLERANCE,
                    "contact-metal-thickness-um": METAL_NOMINAL,
                },
            )
        ]
        result = assess_qualification_sample_conformance(_case(samples=samples))
        self.assertEqual(result["verdict"], SAMPLES_CONFORM)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_nonconforming_share_is_reported(self):
        result = assess_qualification_sample_conformance(_case())
        self.assertAlmostEqual(result["nonconforming_fraction"], 0.0, places=12)

    def test_a_missing_sample_block_rejected(self):
        case = _case()
        del case["samples"]
        with self.assertRaises(ValueError):
            assess_qualification_sample_conformance(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_sample_conformance(["process_identification"])


if __name__ == "__main__":
    unittest.main()
