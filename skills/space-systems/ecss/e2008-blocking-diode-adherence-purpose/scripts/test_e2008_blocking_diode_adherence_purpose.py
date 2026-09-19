"""Contract tests for the clause 12.6.4.2.1 adherence purpose logic."""

import unittest

from e2008_blocking_diode_adherence_purpose_logic import (
    ADHERENCE_JUSTIFIED,
    ADHERENCE_NOT_APPLICABLE,
    ATTACHED_CONTACTS_PRESENT,
    CONTACT_CONFIGURATIONS,
    CRITICALITY_BELOW_THRESHOLD,
    DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY,
    EVIDENCE_COVERAGE_INCOMPLETE,
    EXPOSURES_NOT_DECLARED,
    EXPOSURE_WEIGHTS,
    NON_PLANAR_CONSTRUCTION,
    NO_ATTACHED_CONTACTS,
    OUT_OF_CLAUSE_SCOPE,
    PURPOSE_VERDICTS,
    RECOGNISED_EXPOSURES,
    SERVICE_EXPOSURES,
    assess_blocking_diode_adherence_purpose,
    attachment_criticality,
    evidence_coverage,
    exposure_evidence_map,
    planar_contact_configuration,
    service_exposure_index,
    string_loss_fraction,
    validate_blocking_diode_purpose_policy,
)

ALL_EXPOSURES = list(RECOGNISED_EXPOSURES)
ALL_PARAMETERS = [SERVICE_EXPOSURES[name] for name in ALL_EXPOSURES]


def _policy(**overrides):
    policy = dict(DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "diode": {"construction": "planar", "attached_contact_count": 2},
        "exposures": list(ALL_EXPOSURES),
        "consequence": {
            "string_power_w": 250.0,
            "array_power_w": 3000.0,
            "redundant_diode": False,
        },
        "recorded_parameters": list(ALL_PARAMETERS),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_the_default_policy_validates(self):
        self.assertIs(
            validate_blocking_diode_purpose_policy(
                DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY
            ),
            DEFAULT_BLOCKING_DIODE_PURPOSE_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_purpose_policy("planar")

    def test_a_zero_criticality_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_purpose_policy(
                _policy(min_attachment_criticality=0.0)
            )

    def test_a_coverage_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_purpose_policy(_policy(min_evidence_coverage=2.0))

    def test_a_negative_relief_factor_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocking_diode_purpose_policy(
                _policy(redundancy_relief_factor=-0.5)
            )

    def test_every_purpose_verdict_is_declared_once(self):
        self.assertEqual(len(set(PURPOSE_VERDICTS)), 6)

    def test_every_contact_configuration_is_declared_once(self):
        self.assertEqual(len(set(CONTACT_CONFIGURATIONS)), 3)


class ContactConfigurationTests(unittest.TestCase):
    def test_a_planar_device_with_leads_carries_an_attachment(self):
        self.assertEqual(
            planar_contact_configuration(
                {"construction": "planar", "attached_contact_count": 2}
            ),
            ATTACHED_CONTACTS_PRESENT,
        )

    def test_a_planar_device_with_bare_metallisation_carries_none(self):
        self.assertEqual(
            planar_contact_configuration(
                {"construction": "planar", "attached_contact_count": 0}
            ),
            NO_ATTACHED_CONTACTS,
        )

    def test_a_mesa_build_falls_outside_this_clause(self):
        self.assertEqual(
            planar_contact_configuration(
                {"construction": "mesa", "attached_contact_count": 2}
            ),
            NON_PLANAR_CONSTRUCTION,
        )

    def test_the_construction_label_is_read_case_insensitively(self):
        self.assertEqual(
            planar_contact_configuration(
                {"construction": "Planar", "attached_contact_count": 1}
            ),
            ATTACHED_CONTACTS_PRESENT,
        )

    def test_a_missing_construction_label_rejected(self):
        with self.assertRaises(ValueError):
            planar_contact_configuration({"attached_contact_count": 2})

    def test_a_negative_contact_count_rejected(self):
        with self.assertRaises(ValueError):
            planar_contact_configuration(
                {"construction": "planar", "attached_contact_count": -1}
            )

    def test_a_non_mapping_diode_rejected(self):
        with self.assertRaises(ValueError):
            planar_contact_configuration(["planar", 2])


class ConsequenceTests(unittest.TestCase):
    def test_the_loss_is_the_string_share_of_the_array(self):
        self.assertAlmostEqual(string_loss_fraction(250.0, 1000.0), 0.25, places=9)

    def test_a_single_string_array_loses_everything(self):
        self.assertAlmostEqual(string_loss_fraction(500.0, 500.0), 1.0, places=9)

    def test_a_bigger_array_dilutes_the_same_string(self):
        self.assertLess(
            string_loss_fraction(250.0, 6000.0), string_loss_fraction(250.0, 1000.0)
        )

    def test_a_string_larger_than_its_array_rejected(self):
        with self.assertRaises(ValueError):
            string_loss_fraction(1200.0, 1000.0)

    def test_a_zero_array_power_rejected(self):
        with self.assertRaises(ValueError):
            string_loss_fraction(250.0, 0.0)


class ExposureTests(unittest.TestCase):
    def test_the_weights_account_for_the_whole_downstream_life(self):
        self.assertAlmostEqual(sum(EXPOSURE_WEIGHTS.values()), 1.0, places=9)

    def test_the_full_exposure_set_indexes_at_one(self):
        self.assertAlmostEqual(service_exposure_index(ALL_EXPOSURES), 1.0, places=9)

    def test_the_full_exposure_set_never_indexes_above_one(self):
        # The declared weights sum to one, and the leaf clamps any
        # representation error back onto the literal 1.0, so a full set
        # indexes at EXACTLY one. Assert that equality rather than an
        # inequality whose two sides are the same bit pattern.
        self.assertEqual(service_exposure_index(ALL_EXPOSURES), 1.0)

    def test_a_repeated_exposure_counts_once(self):
        single = service_exposure_index(["diode-lead-series-weld"])
        doubled = service_exposure_index(
            ["diode-lead-series-weld", "diode-lead-series-weld"]
        )
        self.assertAlmostEqual(single, doubled, places=12)

    def test_an_unrecognised_exposure_rejected(self):
        with self.assertRaises(ValueError):
            service_exposure_index(["shelf-storage"])

    def test_a_bare_string_is_not_an_exposure_list(self):
        with self.assertRaises(ValueError):
            service_exposure_index("diode-lead-series-weld")

    def test_every_exposure_maps_onto_an_evidence_parameter(self):
        mapped = exposure_evidence_map(ALL_EXPOSURES)
        self.assertEqual(len(mapped), len(ALL_EXPOSURES))
        self.assertEqual(len(set(mapped.values())), len(ALL_EXPOSURES))

    def test_an_empty_exposure_list_maps_to_nothing(self):
        self.assertEqual(exposure_evidence_map([]), {})

    def test_an_unrecognised_exposure_is_not_silently_mapped(self):
        with self.assertRaises(ValueError):
            exposure_evidence_map(["shelf-storage"])


class EvidenceCoverageTests(unittest.TestCase):
    def test_a_fully_recorded_campaign_covers_everything(self):
        self.assertAlmostEqual(
            evidence_coverage(ALL_EXPOSURES, ALL_PARAMETERS), 1.0, places=9
        )

    def test_a_missing_parameter_lowers_the_coverage(self):
        self.assertAlmostEqual(
            evidence_coverage(ALL_EXPOSURES, ALL_PARAMETERS[:-1]), 0.8, places=9
        )

    def test_recording_nothing_covers_nothing(self):
        self.assertAlmostEqual(evidence_coverage(ALL_EXPOSURES, []), 0.0, places=9)

    def test_an_unrelated_parameter_does_not_cover_an_exposure(self):
        self.assertAlmostEqual(
            evidence_coverage(["diode-lead-series-weld"], ["shelf-life-record"]),
            0.0,
            places=9,
        )

    def test_coverage_of_no_exposure_rejected(self):
        with self.assertRaises(ValueError):
            evidence_coverage([], ALL_PARAMETERS)


class CriticalityTests(unittest.TestCase):
    def test_criticality_is_the_consequence_weighted_by_the_exposure(self):
        self.assertAlmostEqual(
            attachment_criticality(0.25, 0.40, False), 0.10, places=9
        )

    def test_a_parallel_diode_relieves_the_criticality_by_the_factor(self):
        policy = _policy()
        plain = attachment_criticality(0.25, 0.40, False, policy)
        relieved = attachment_criticality(0.25, 0.40, True, policy)
        self.assertAlmostEqual(
            relieved, plain * policy["redundancy_relief_factor"], places=12
        )

    def test_a_relief_factor_of_one_relieves_nothing(self):
        policy = _policy(redundancy_relief_factor=1.0)
        self.assertAlmostEqual(
            attachment_criticality(0.25, 0.40, True, policy),
            attachment_criticality(0.25, 0.40, False, policy),
            places=12,
        )

    def test_a_non_boolean_redundancy_flag_rejected(self):
        with self.assertRaises(ValueError):
            attachment_criticality(0.25, 0.40, "yes")

    def test_a_loss_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            attachment_criticality(1.4, 0.40, False)

    def test_a_zero_exposure_index_rejected(self):
        with self.assertRaises(ValueError):
            attachment_criticality(0.25, 0.0, False)


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_nominal_case_justifies_the_verification(self):
        result = assess_blocking_diode_adherence_purpose(_case())
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)
        self.assertEqual(result["findings"], [])

    def test_a_non_planar_build_is_outside_the_clause(self):
        result = assess_blocking_diode_adherence_purpose(
            _case(diode={"construction": "integrated", "attached_contact_count": 2})
        )
        self.assertEqual(result["verdict"], OUT_OF_CLAUSE_SCOPE)
        self.assertEqual(result["contact_configuration"], NON_PLANAR_CONSTRUCTION)

    def test_bare_metallisation_makes_the_check_not_applicable(self):
        result = assess_blocking_diode_adherence_purpose(
            _case(diode={"construction": "planar", "attached_contact_count": 0})
        )
        self.assertEqual(result["verdict"], ADHERENCE_NOT_APPLICABLE)
        self.assertEqual(result["evidence_map"], {})

    def test_applicability_is_settled_before_any_consequence(self):
        case = _case(diode={"construction": "planar", "attached_contact_count": 0})
        del case["consequence"]
        result = assess_blocking_diode_adherence_purpose(case)
        self.assertEqual(result["verdict"], ADHERENCE_NOT_APPLICABLE)

    def test_no_declared_exposure_leaves_the_pull_unargued(self):
        result = assess_blocking_diode_adherence_purpose(_case(exposures=[]))
        self.assertEqual(result["verdict"], EXPOSURES_NOT_DECLARED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_small_string_on_a_large_array_falls_below_threshold(self):
        result = assess_blocking_diode_adherence_purpose(
            _case(
                exposures=["panel-harness-routing-strain"],
                consequence={
                    "string_power_w": 10.0,
                    "array_power_w": 3000.0,
                    "redundant_diode": False,
                },
                recorded_parameters=[
                    SERVICE_EXPOSURES["panel-harness-routing-strain"]
                ],
            )
        )
        self.assertEqual(result["verdict"], CRITICALITY_BELOW_THRESHOLD)

    def test_a_criticality_exactly_at_the_floor_is_justified(self):
        policy = _policy()
        result = assess_blocking_diode_adherence_purpose(
            _case(
                consequence={
                    "string_power_w": 20.0,
                    "array_power_w": 1000.0,
                    "redundant_diode": False,
                }
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["attachment_criticality"],
            policy["min_attachment_criticality"],
            places=9,
        )
        self.assertEqual(result["verdict"], ADHERENCE_JUSTIFIED)

    def test_the_relief_can_drop_a_borderline_case_below_the_floor(self):
        policy = _policy()
        result = assess_blocking_diode_adherence_purpose(
            _case(
                consequence={
                    "string_power_w": 20.0,
                    "array_power_w": 1000.0,
                    "redundant_diode": True,
                }
            ),
            policy,
        )
        self.assertEqual(result["verdict"], CRITICALITY_BELOW_THRESHOLD)
        self.assertTrue(result["redundant_diode"])

    def test_an_unrecorded_exposure_leaves_the_evidence_incomplete(self):
        result = assess_blocking_diode_adherence_purpose(
            _case(recorded_parameters=ALL_PARAMETERS[:-1])
        )
        self.assertEqual(result["verdict"], EVIDENCE_COVERAGE_INCOMPLETE)
        self.assertAlmostEqual(result["evidence_coverage"], 0.8, places=9)

    def test_the_uncovered_exposure_is_named_in_the_finding(self):
        missing = ALL_EXPOSURES[-1]
        result = assess_blocking_diode_adherence_purpose(
            _case(recorded_parameters=ALL_PARAMETERS[:-1])
        )
        self.assertIn(missing, result["findings"][0])

    def test_criticality_outranks_an_incomplete_evidence_map(self):
        result = assess_blocking_diode_adherence_purpose(
            _case(
                consequence={
                    "string_power_w": 10.0,
                    "array_power_w": 3000.0,
                    "redundant_diode": False,
                },
                recorded_parameters=[],
            )
        )
        self.assertEqual(result["verdict"], CRITICALITY_BELOW_THRESHOLD)
        self.assertEqual(len(result["findings"]), 2)

    def test_the_string_loss_and_exposure_index_are_reported(self):
        result = assess_blocking_diode_adherence_purpose(_case())
        self.assertAlmostEqual(
            result["string_loss_fraction"], 250.0 / 3000.0, places=12
        )
        self.assertAlmostEqual(result["exposure_index"], 1.0, places=9)

    def test_a_missing_diode_block_rejected(self):
        case = _case()
        del case["diode"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_adherence_purpose(case)

    def test_a_missing_exposures_list_rejected(self):
        case = _case()
        del case["exposures"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_adherence_purpose(case)

    def test_a_missing_consequence_block_rejected(self):
        case = _case()
        del case["consequence"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_adherence_purpose(case)

    def test_a_missing_recorded_parameters_list_rejected(self):
        case = _case()
        del case["recorded_parameters"]
        with self.assertRaises(ValueError):
            assess_blocking_diode_adherence_purpose(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_adherence_purpose(["diode"])

    def test_the_verdict_is_always_one_of_the_declared_verdicts(self):
        result = assess_blocking_diode_adherence_purpose(_case())
        self.assertIn(result["verdict"], PURPOSE_VERDICTS)


if __name__ == "__main__":
    unittest.main()
