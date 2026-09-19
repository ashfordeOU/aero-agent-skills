"""Contract tests for the cleanliness responsibility assignment logic."""

import copy
import unittest

from q7001_cleanliness_responsibilities_logic import (
    ACTIVITIES,
    ACTOR_KINDS,
    FACILITY_DEPENDENT_ACTIVITIES,
    ROLES,
    accountability_findings,
    actors_in_role,
    assess_responsibilities,
    coverage_findings,
    facility_role_findings,
    responsibility_summary,
    supplier_flow_down_findings,
    validate_actors,
    validate_matrix,
    verification_independence_findings,
)


def sample_actors():
    return [
        {"name": "customer PA", "kind": "customer"},
        {"name": "prime engineering", "kind": "prime"},
        {"name": "prime PA", "kind": "product-assurance"},
        {"name": "optics supplier", "kind": "subsystem-supplier"},
        {"name": "cleanroom operator", "kind": "facility-operator"},
        {"name": "environmental test centre", "kind": "test-centre"},
    ]


def sample_matrix():
    return {
        "cleanliness-level-definition": {
            "prime engineering": "accountable",
            "prime PA": "responsible",
            "customer PA": "consulted",
        },
        "cleanliness-budget-allocation": {
            "prime PA": "accountable",
            "prime engineering": "responsible",
        },
        "design-provision-verification": {
            "prime PA": "accountable",
            "prime engineering": "responsible",
        },
        "facility-environment-monitoring": {
            "prime PA": "accountable",
            "cleanroom operator": "responsible",
            "environmental test centre": "consulted",
        },
        "cleaning-execution": {
            "prime PA": "accountable",
            "cleanroom operator": "responsible",
        },
        "cleanliness-verification": {
            "prime PA": "accountable",
            "prime engineering": "responsible",
        },
        "witness-sample-management": {
            "prime PA": "accountable",
            "cleanroom operator": "responsible",
        },
        "transport-and-storage-control": {
            "prime PA": "accountable",
            "cleanroom operator": "responsible",
        },
        "supplier-requirement-flow-down": {
            "prime PA": "accountable",
            "prime engineering": "responsible",
            "optics supplier": "informed",
        },
        "cleanliness-non-conformance-disposition": {
            "prime PA": "accountable",
            "prime engineering": "responsible",
            "customer PA": "informed",
        },
    }


def sample_spec(**overrides):
    spec = {"actors": sample_actors(), "matrix": sample_matrix()}
    spec.update(overrides)
    return copy.deepcopy(spec)


class ActorTests(unittest.TestCase):
    def test_catalogue_maps_name_to_kind(self):
        catalogue = validate_actors(sample_actors())
        self.assertEqual(catalogue["cleanroom operator"], "facility-operator")
        self.assertEqual(len(catalogue), 6)

    def test_every_declared_kind_is_recognised(self):
        for kind in ACTOR_KINDS:
            catalogue = validate_actors([{"name": "party", "kind": kind}])
            self.assertEqual(catalogue["party"], kind)

    def test_duplicate_actor_rejected(self):
        actors = sample_actors() + [sample_actors()[0]]
        with self.assertRaises(ValueError):
            validate_actors(actors)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_actors([{"name": "party", "kind": "sponsor"}])

    def test_blank_actor_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_actors([{"name": "  ", "kind": "prime"}])

    def test_empty_actor_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_actors([])

    def test_missing_actor_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_actors([{"name": "prime engineering"}])


class MatrixTests(unittest.TestCase):
    def _catalogue(self):
        return validate_actors(sample_actors())

    def test_valid_matrix_returned(self):
        matrix = validate_matrix(sample_matrix(), self._catalogue())
        self.assertEqual(len(matrix), len(ACTIVITIES))

    def test_unknown_activity_rejected(self):
        matrix = sample_matrix()
        matrix["catering"] = {"prime PA": "accountable"}
        with self.assertRaises(ValueError):
            validate_matrix(matrix, self._catalogue())

    def test_unknown_actor_in_a_row_rejected(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["ghost team"] = "responsible"
        with self.assertRaises(ValueError):
            validate_matrix(matrix, self._catalogue())

    def test_unknown_role_rejected(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["prime engineering"] = "supervising"
        with self.assertRaises(ValueError):
            validate_matrix(matrix, self._catalogue())

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix({}, self._catalogue())

    def test_non_mapping_row_rejected(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"] = ["cleanroom operator"]
        with self.assertRaises(ValueError):
            validate_matrix(matrix, self._catalogue())

    def test_actors_in_role_is_sorted(self):
        row = {"b party": "responsible", "a party": "responsible", "c": "informed"}
        self.assertEqual(actors_in_role(row, "responsible"), ["a party", "b party"])

    def test_actors_in_role_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            actors_in_role({"a": "responsible"}, "owning")

    def test_every_declared_role_is_recognised(self):
        for role in ROLES:
            self.assertEqual(actors_in_role({"a": role}, role), ["a"])


class CoverageAndAccountabilityTests(unittest.TestCase):
    def test_full_matrix_covers_every_activity(self):
        self.assertEqual(coverage_findings(sample_matrix()), [])

    def test_absent_activity_is_reported(self):
        matrix = sample_matrix()
        del matrix["witness-sample-management"]
        findings = coverage_findings(matrix)
        self.assertEqual(len(findings), 1)
        self.assertIn("witness-sample-management", findings[0])

    def test_sound_matrix_has_no_accountability_finding(self):
        self.assertEqual(accountability_findings(sample_matrix()), [])

    def test_activity_with_nobody_accountable_is_reported(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["prime PA"] = "consulted"
        findings = accountability_findings(matrix)
        self.assertTrue(any("nobody accountable" in f for f in findings))

    def test_split_accountability_is_reported(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["prime engineering"] = "accountable"
        findings = accountability_findings(matrix)
        self.assertTrue(any("splits accountability" in f for f in findings))

    def test_activity_with_nobody_carrying_it_out_is_reported(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["cleanroom operator"] = "informed"
        findings = accountability_findings(matrix)
        self.assertTrue(any("nobody carrying it out" in f for f in findings))

    def test_absent_activity_raises_no_accountability_finding(self):
        matrix = sample_matrix()
        del matrix["cleaning-execution"]
        self.assertEqual(accountability_findings(matrix), [])


class FacilityRoleTests(unittest.TestCase):
    def _catalogue(self):
        return validate_actors(sample_actors())

    def test_facility_party_present_on_every_facility_activity(self):
        self.assertEqual(facility_role_findings(sample_matrix(), self._catalogue()), [])

    def test_facility_activity_without_a_facility_party_is_reported(self):
        matrix = sample_matrix()
        matrix["transport-and-storage-control"] = {
            "prime PA": "accountable",
            "prime engineering": "responsible",
        }
        findings = facility_role_findings(matrix, self._catalogue())
        self.assertEqual(len(findings), 1)
        self.assertIn("transport-and-storage-control", findings[0])

    def test_test_centre_counts_as_a_facility_party(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"] = {
            "prime PA": "accountable",
            "environmental test centre": "responsible",
        }
        self.assertEqual(facility_role_findings(matrix, self._catalogue()), [])

    def test_facility_party_merely_informed_does_not_count(self):
        matrix = sample_matrix()
        matrix["witness-sample-management"]["cleanroom operator"] = "informed"
        matrix["witness-sample-management"]["prime engineering"] = "responsible"
        findings = facility_role_findings(matrix, self._catalogue())
        self.assertTrue(any("witness-sample-management" in f for f in findings))

    def test_every_facility_dependent_activity_is_checked(self):
        matrix = {
            activity: {"prime PA": "accountable", "prime engineering": "responsible"}
            for activity in FACILITY_DEPENDENT_ACTIVITIES
        }
        self.assertEqual(
            len(facility_role_findings(matrix, self._catalogue())),
            len(FACILITY_DEPENDENT_ACTIVITIES),
        )


class SupplierFlowDownTests(unittest.TestCase):
    def _catalogue(self):
        return validate_actors(sample_actors())

    def test_no_supplier_work_declared_gives_no_finding(self):
        self.assertEqual(
            supplier_flow_down_findings(sample_matrix(), self._catalogue(), None), []
        )

    def test_supplier_work_without_a_supplier_assigned_is_reported(self):
        findings = supplier_flow_down_findings(
            sample_matrix(), self._catalogue(), ["cleaning-execution"]
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no supplier is assigned", findings[0])

    def test_supplier_carrying_it_out_under_a_retained_owner_is_clean(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"]["optics supplier"] = "responsible"
        self.assertEqual(
            supplier_flow_down_findings(
                matrix, self._catalogue(), ["cleaning-execution"]
            ),
            [],
        )

    def test_accountability_moved_to_the_supplier_is_reported(self):
        matrix = sample_matrix()
        matrix["cleaning-execution"] = {
            "optics supplier": "accountable",
            "cleanroom operator": "responsible",
        }
        findings = supplier_flow_down_findings(
            matrix, self._catalogue(), ["cleaning-execution"]
        )
        self.assertTrue(any("retains it" in f for f in findings))

    def test_unknown_activity_in_the_supplier_list_rejected(self):
        with self.assertRaises(ValueError):
            supplier_flow_down_findings(
                sample_matrix(), self._catalogue(), ["catering"]
            )

    def test_non_sequence_supplier_list_rejected(self):
        with self.assertRaises(ValueError):
            supplier_flow_down_findings(
                sample_matrix(), self._catalogue(), "cleaning-execution"
            )


class VerificationIndependenceTests(unittest.TestCase):
    def test_independent_verification_gives_no_finding(self):
        self.assertEqual(verification_independence_findings(sample_matrix()), [])

    def test_cleaners_verifying_their_own_work_is_reported(self):
        matrix = sample_matrix()
        matrix["cleanliness-verification"] = {
            "prime PA": "accountable",
            "cleanroom operator": "responsible",
        }
        findings = verification_independence_findings(matrix)
        self.assertEqual(len(findings), 1)
        self.assertIn("not independent", findings[0])

    def test_one_independent_verifier_is_enough(self):
        matrix = sample_matrix()
        matrix["cleanliness-verification"]["cleanroom operator"] = "responsible"
        self.assertEqual(verification_independence_findings(matrix), [])

    def test_absent_activity_gives_no_finding(self):
        matrix = sample_matrix()
        del matrix["cleaning-execution"]
        self.assertEqual(verification_independence_findings(matrix), [])


class SummaryTests(unittest.TestCase):
    def test_summary_counts_roles_per_actor(self):
        catalogue = validate_actors(sample_actors())
        summary = responsibility_summary(sample_matrix(), catalogue)
        self.assertEqual(summary["prime PA"]["counts"]["accountable"], 9)
        self.assertEqual(summary["prime PA"]["kind"], "product-assurance")

    def test_summary_names_every_actor_even_when_unused(self):
        catalogue = validate_actors(sample_actors())
        matrix = {"cleaning-execution": sample_matrix()["cleaning-execution"]}
        summary = responsibility_summary(matrix, catalogue)
        self.assertEqual(len(summary), 6)
        self.assertEqual(sum(summary["optics supplier"]["counts"].values()), 0)


class AssessResponsibilitiesTests(unittest.TestCase):
    def test_sound_assignment_is_complete(self):
        result = assess_responsibilities(sample_spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_coverage_fraction_drops_with_an_unassigned_activity(self):
        spec = sample_spec()
        del spec["matrix"]["witness-sample-management"]
        result = assess_responsibilities(spec)
        self.assertFalse(result["complete"])
        self.assertAlmostEqual(
            result["coverage_fraction"], (len(ACTIVITIES) - 1) / len(ACTIVITIES),
            places=9,
        )

    def test_actor_holding_no_role_is_reported(self):
        spec = sample_spec()
        del spec["matrix"]["supplier-requirement-flow-down"]["optics supplier"]
        result = assess_responsibilities(spec)
        self.assertTrue(any("holds no cleanliness role" in f for f in result["findings"]))

    def test_supplier_work_is_graded_when_declared(self):
        spec = sample_spec(performed_at_supplier=["cleaning-execution"])
        result = assess_responsibilities(spec)
        self.assertFalse(result["complete"])
        self.assertTrue(any("no supplier is assigned" in f for f in result["findings"]))

    def test_several_defects_are_all_reported(self):
        spec = sample_spec()
        del spec["matrix"]["witness-sample-management"]
        spec["matrix"]["cleaning-execution"]["prime engineering"] = "accountable"
        spec["matrix"]["transport-and-storage-control"] = {
            "prime PA": "accountable",
            "prime engineering": "responsible",
        }
        result = assess_responsibilities(spec)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_spec_key_rejected(self):
        spec = sample_spec()
        del spec["matrix"]
        with self.assertRaises(ValueError):
            assess_responsibilities(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_responsibilities(["actors"])

    def test_summary_is_returned_with_the_assessment(self):
        result = assess_responsibilities(sample_spec())
        self.assertIn("cleanroom operator", result["summary"])


if __name__ == "__main__":
    unittest.main()
