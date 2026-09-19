#!/usr/bin/env python3
"""Contract tests for facility calibration control, clause 5.6.3.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
a chain with no plan, an inverted calibrated range, a correlated group
summed linearly before the quadrature, an accuracy ratio landing exactly
on its required value, an element the campaign drives out of range, a
certificate already expired and one expiring inside the campaign.
"""

import unittest

from q2007_tf_calibration_logic import (
    ACCURACY_RATIO_SHORT,
    CERTIFICATE_EXPIRED,
    CERTIFICATE_EXPIRING,
    CHAIN_FIT_FOR_CAMPAIGN,
    DEFAULT_CALIBRATION_POLICY,
    ELEMENT_OUT_OF_RANGE,
    NO_CALIBRATION_PLAN,
    PLAN_COVERAGE_SHORT,
    accuracy_ratio,
    assess_facility_calibration,
    certificates_expiring,
    chain_uncertainty,
    elements_outside_range,
    expired_certificates,
    plan_coverage,
    unplanned_elements,
    validate_calibration_policy,
    validate_campaign_range,
    validate_chain,
    validate_chain_element,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CALIBRATION_POLICY)
    policy.update(overrides)
    return policy


def _elements():
    return [
        {
            "element_id": "chamber-thermocouple-transducer",
            "uncertainty": 0.2,
            "range_min": -200.0,
            "range_max": 200.0,
            "certificate_expiry_day": 400,
        },
        {
            "element_id": "thermocouple-signal-conditioner",
            "uncertainty": 0.3,
            "range_min": -250.0,
            "range_max": 250.0,
            "certificate_expiry_day": 420,
        },
        {
            "element_id": "facility-acquisition-card",
            "uncertainty": 0.6,
            "range_min": -300.0,
            "range_max": 300.0,
            "certificate_expiry_day": 500,
        },
    ]


def _chain(**overrides):
    chain = {
        "elements": _elements(),
        "calibration_plan": True,
        "last_run_day": 300,
        "parameter_tolerance": 2.8,
        "campaign_range": {"campaign_min": -150.0, "campaign_max": 150.0},
    }
    chain.update(overrides)
    return chain


def _case(**overrides):
    case = {"policy": _policy(), "chain": _chain()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_calibration_policy(DEFAULT_CALIBRATION_POLICY),
            DEFAULT_CALIBRATION_POLICY,
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_calibration_policy(4.0)

    def test_a_ratio_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_calibration_policy(_policy(required_accuracy_ratio=0.5))

    def test_a_zero_ratio_is_refused(self):
        with self.assertRaises(ValueError):
            validate_calibration_policy(_policy(required_accuracy_ratio=0.0))

    def test_a_coverage_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_calibration_policy(_policy(min_plan_coverage=1.2))


class ElementValidationTests(unittest.TestCase):
    def test_element_is_read_back(self):
        record = validate_chain_element(_elements()[0])
        self.assertEqual(record["element_id"], "chamber-thermocouple-transducer")
        self.assertAlmostEqual(record["uncertainty"], 0.2, places=9)

    def test_an_inverted_calibrated_range_refused(self):
        element = _elements()[0]
        element["range_min"] = 300.0
        with self.assertRaises(ValueError):
            validate_chain_element(element)

    def test_a_zero_uncertainty_refused(self):
        element = _elements()[0]
        element["uncertainty"] = 0.0
        with self.assertRaises(ValueError):
            validate_chain_element(element)

    def test_a_non_boolean_plan_flag_refused(self):
        element = _elements()[0]
        element["in_calibration_plan"] = "yes"
        with self.assertRaises(ValueError):
            validate_chain_element(element)

    def test_the_same_element_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_chain(_elements() + [_elements()[0]])

    def test_an_empty_chain_refused(self):
        with self.assertRaises(ValueError):
            validate_chain([])


class CombinationTests(unittest.TestCase):
    def test_independent_elements_combine_in_quadrature(self):
        self.assertAlmostEqual(chain_uncertainty(_elements()), 0.7, places=9)

    def test_the_chain_is_below_the_arithmetic_sum(self):
        self.assertLess(chain_uncertainty(_elements()), 1.1)

    def test_the_chain_is_above_its_worst_element(self):
        self.assertGreater(chain_uncertainty(_elements()), 0.6)

    def test_a_correlated_group_is_summed_linearly_first(self):
        elements = _elements()
        elements[0]["correlation_group"] = "thermocouple-loop"
        elements[1]["correlation_group"] = "thermocouple-loop"
        expected = ((0.2 + 0.3) ** 2 + 0.6 ** 2) ** 0.5
        self.assertAlmostEqual(chain_uncertainty(elements), expected, places=9)

    def test_treating_a_pair_as_correlated_never_lowers_the_chain(self):
        elements = _elements()
        independent = chain_uncertainty(elements)
        elements[0]["correlation_group"] = "thermocouple-loop"
        elements[1]["correlation_group"] = "thermocouple-loop"
        self.assertGreater(chain_uncertainty(elements), independent)

    def test_the_accuracy_ratio_lands_on_its_required_value(self):
        self.assertAlmostEqual(accuracy_ratio(_elements(), 2.8), 4.0, places=9)

    def test_a_zero_parameter_tolerance_refused(self):
        with self.assertRaises(ValueError):
            accuracy_ratio(_elements(), 0.0)


class CoverageAndRangeTests(unittest.TestCase):
    def test_a_fully_planned_chain_has_full_coverage(self):
        self.assertAlmostEqual(plan_coverage(_elements()), 1.0, places=9)

    def test_an_unplanned_element_lowers_coverage_and_is_named(self):
        elements = _elements()
        elements[2]["in_calibration_plan"] = False
        self.assertAlmostEqual(plan_coverage(elements), 2.0 / 3.0, places=9)
        self.assertEqual(unplanned_elements(elements), ("facility-acquisition-card",))

    def test_a_campaign_inside_every_range_leaves_nothing_outside(self):
        self.assertEqual(
            elements_outside_range(
                _elements(), {"campaign_min": -150.0, "campaign_max": 150.0}
            ),
            (),
        )

    def test_a_campaign_exactly_on_a_range_edge_is_inside(self):
        self.assertEqual(
            elements_outside_range(
                _elements(), {"campaign_min": -200.0, "campaign_max": 200.0}
            ),
            (),
        )

    def test_a_campaign_past_an_element_range_names_it(self):
        self.assertEqual(
            elements_outside_range(
                _elements(), {"campaign_min": -240.0, "campaign_max": 240.0}
            ),
            ("chamber-thermocouple-transducer",),
        )

    def test_a_backwards_campaign_range_refused(self):
        with self.assertRaises(ValueError):
            validate_campaign_range({"campaign_min": 10.0, "campaign_max": -10.0})


class ValidityTests(unittest.TestCase):
    def test_certificates_reaching_the_last_run_day_are_not_expired(self):
        self.assertEqual(expired_certificates(_elements(), 300), ())

    def test_a_certificate_short_of_the_last_run_day_is_expired(self):
        self.assertEqual(
            expired_certificates(_elements(), 410),
            ("chamber-thermocouple-transducer",),
        )

    def test_a_certificate_expiring_on_the_last_run_day_is_flagged(self):
        elements = _elements()
        elements[0]["certificate_expiry_day"] = 300
        self.assertIn(
            "chamber-thermocouple-transducer", certificates_expiring(elements, 300)
        )

    def test_a_certificate_beyond_the_notice_period_is_not_flagged(self):
        self.assertEqual(certificates_expiring(_elements(), 300), ())


class AssessmentTests(unittest.TestCase):
    def test_a_fit_chain_passes(self):
        result = assess_facility_calibration(_case())
        self.assertEqual(result["verdict"], CHAIN_FIT_FOR_CAMPAIGN)
        self.assertAlmostEqual(result["accuracy_ratio"], 4.0, places=9)

    def test_no_chain_at_all_stops_the_assessment(self):
        result = assess_facility_calibration(_case(chain=None))
        self.assertEqual(result["verdict"], NO_CALIBRATION_PLAN)

    def test_a_chain_with_no_elements_stops_the_assessment(self):
        result = assess_facility_calibration(_case(chain=_chain(elements=[])))
        self.assertEqual(result["verdict"], NO_CALIBRATION_PLAN)

    def test_a_chain_outside_any_plan_stops_the_assessment(self):
        result = assess_facility_calibration(
            _case(chain=_chain(calibration_plan=False))
        )
        self.assertEqual(result["verdict"], NO_CALIBRATION_PLAN)

    def test_an_expired_certificate_outranks_a_short_ratio(self):
        result = assess_facility_calibration(
            _case(chain=_chain(last_run_day=410, parameter_tolerance=1.0))
        )
        self.assertEqual(result["verdict"], CERTIFICATE_EXPIRED)

    def test_an_out_of_range_element_outranks_short_plan_coverage(self):
        elements = _elements()
        elements[2]["in_calibration_plan"] = False
        result = assess_facility_calibration(
            _case(
                chain=_chain(
                    elements=elements,
                    campaign_range={"campaign_min": -240.0, "campaign_max": 240.0},
                )
            )
        )
        self.assertEqual(result["verdict"], ELEMENT_OUT_OF_RANGE)

    def test_short_plan_coverage_is_reported_on_its_own(self):
        elements = _elements()
        elements[2]["in_calibration_plan"] = False
        result = assess_facility_calibration(_case(chain=_chain(elements=elements)))
        self.assertEqual(result["verdict"], PLAN_COVERAGE_SHORT)
        self.assertAlmostEqual(result["plan_coverage"], 2.0 / 3.0, places=9)

    def test_a_tight_parameter_tolerance_fails_the_ratio(self):
        result = assess_facility_calibration(
            _case(chain=_chain(parameter_tolerance=1.0))
        )
        self.assertEqual(result["verdict"], ACCURACY_RATIO_SHORT)
        self.assertAlmostEqual(result["chain_uncertainty"], 0.7, places=9)

    def test_a_certificate_expiring_inside_the_campaign_is_an_advisory(self):
        elements = _elements()
        elements[1]["certificate_expiry_day"] = 310
        result = assess_facility_calibration(_case(chain=_chain(elements=elements)))
        self.assertEqual(result["verdict"], CERTIFICATE_EXPIRING)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_chain_with_no_parameter_tolerance_is_refused(self):
        chain = _chain()
        del chain["parameter_tolerance"]
        with self.assertRaises(ValueError):
            assess_facility_calibration(_case(chain=chain))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_calibration(["chain"])


if __name__ == "__main__":
    unittest.main()
