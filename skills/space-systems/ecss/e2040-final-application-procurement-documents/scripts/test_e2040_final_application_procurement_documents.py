"""Contract test for the final-application-procurement-documents leaf (stdlib unittest)."""

import unittest

from e2040_final_application_procurement_documents_logic import (
    DISPOSITIONS,
    DOCUMENT_APPLICABILITY,
    DOCUMENT_ROLE,
    ISSUE_STATES,
    ROLES,
    ROUTES,
    assess_documents,
    assess_final_application_procurement_documents,
    compare_revisions,
    owed_documents,
    parse_revision,
    role_completeness,
    validate_document,
    validate_route,
)

DELIVERED = "DEV-FM-02"


def document(name, **kw):
    record = {
        "name": name,
        "issue": "final",
        "revision": "2.0",
        "previous_revision": "1.3",
        "configuration_id": DELIVERED,
        "approved": True,
    }
    record.update(kw)
    return record


def full_set(route="escc-evaluation", **overrides):
    records = [document(name) for name in owed_documents(route)]
    for key, changes in overrides.items():
        target = key.replace("_", "-")
        for record in records:
            if record["name"] == target:
                record.update(changes)
    return records


def clean_spec(route="escc-evaluation", **kw):
    spec = {
        "route": route,
        "documents": full_set(route),
        "delivered_configuration_id": DELIVERED,
    }
    spec.update(kw)
    return spec


class TestValidateRoute(unittest.TestCase):
    def test_mixed_case_is_normalised(self):
        self.assertEqual(validate_route("ESCC-Evaluation"), "escc-evaluation")

    def test_every_declared_route_round_trips(self):
        for route in ROUTES:
            self.assertEqual(validate_route(route), route)

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            validate_route("handshake")

    def test_non_string_route_raises(self):
        with self.assertRaises(ValueError):
            validate_route(7)


class TestOwedDocuments(unittest.TestCase):
    def test_evaluation_route_owes_the_detail_specification(self):
        self.assertIn("escc-detail-specification", owed_documents("escc-evaluation"))

    def test_licence_route_owes_no_detail_specification(self):
        self.assertNotIn("escc-detail-specification", owed_documents("ip-core-licence"))

    def test_licence_route_owes_a_licence_and_delivery_specification(self):
        self.assertIn(
            "licence-and-delivery-specification", owed_documents("ip-core-licence")
        )

    def test_every_route_owes_the_data_sheet(self):
        for route in ROUTES:
            self.assertIn("device-data-sheet", owed_documents(route))

    def test_every_owed_document_has_a_declared_role(self):
        for name in DOCUMENT_APPLICABILITY:
            self.assertIn(DOCUMENT_ROLE[name], ROLES)


class TestParseRevision(unittest.TestCase):
    def test_single_number_is_a_one_tuple(self):
        self.assertEqual(parse_revision("3"), (3,))

    def test_dotted_revision_is_split(self):
        self.assertEqual(parse_revision("2.11"), (2, 11))

    def test_integer_revision_is_accepted(self):
        self.assertEqual(parse_revision(4), (4,))

    def test_leading_zero_segment_is_accepted(self):
        self.assertEqual(parse_revision("01.02"), (1, 2))

    def test_non_numeric_segment_raises(self):
        with self.assertRaises(ValueError):
            parse_revision("1.a")

    def test_empty_segment_raises(self):
        with self.assertRaises(ValueError):
            parse_revision("1..2")

    def test_blank_revision_raises(self):
        with self.assertRaises(ValueError):
            parse_revision("   ")

    def test_negative_integer_revision_raises(self):
        with self.assertRaises(ValueError):
            parse_revision(-1)

    def test_already_parsed_revision_passes_through(self):
        self.assertEqual(parse_revision((2, 11)), (2, 11))

    def test_empty_revision_tuple_raises(self):
        with self.assertRaises(ValueError):
            parse_revision(())

    def test_revision_tuple_with_a_non_integer_raises(self):
        with self.assertRaises(ValueError):
            parse_revision((2, "11"))


class TestCompareRevisions(unittest.TestCase):
    def test_advance_is_positive(self):
        self.assertEqual(compare_revisions("2.0", "1.3"), 1)

    def test_equal_is_zero(self):
        self.assertEqual(compare_revisions("2.0", "2.0"), 0)

    def test_regression_is_negative(self):
        self.assertEqual(compare_revisions("1.3", "2.0"), -1)

    def test_shorter_revision_is_zero_padded_not_treated_as_smaller(self):
        self.assertEqual(compare_revisions("2", "2.0"), 0)

    def test_numeric_order_not_lexicographic_order(self):
        self.assertEqual(compare_revisions("2.10", "2.9"), 1)


class TestValidateDocument(unittest.TestCase):
    def test_name_is_lower_cased(self):
        self.assertEqual(
            validate_document(document("Device-Data-Sheet"))["name"], "device-data-sheet"
        )

    def test_role_is_resolved_from_the_name(self):
        self.assertEqual(
            validate_document(document("procurement-specification"))["role"], "procurement"
        )

    def test_unknown_document_raises(self):
        with self.assertRaises(ValueError):
            validate_document(document("marketing-brochure"))

    def test_unknown_issue_state_raises(self):
        with self.assertRaises(ValueError):
            validate_document(document("device-data-sheet", issue="nearly"))

    def test_every_declared_issue_state_is_accepted(self):
        for state in ISSUE_STATES:
            self.assertEqual(
                validate_document(document("device-data-sheet", issue=state))["issue"], state
            )

    def test_absent_previous_revision_is_kept_as_none(self):
        record = validate_document(document("device-data-sheet", previous_revision=None))
        self.assertIsNone(record["previous_revision"])

    def test_non_boolean_approval_raises(self):
        with self.assertRaises(ValueError):
            validate_document(document("device-data-sheet", approved="yes"))

    def test_missing_configuration_raises(self):
        broken = document("device-data-sheet")
        del broken["configuration_id"]
        with self.assertRaises(ValueError):
            validate_document(broken)


class TestAssessDocuments(unittest.TestCase):
    def test_clean_set_is_release_fraction_one(self):
        report = assess_documents(full_set(), "escc-evaluation", DELIVERED)
        self.assertAlmostEqual(report["release_fraction"], 1.0, places=9)

    def test_absent_document_is_named(self):
        records = [d for d in full_set() if d["name"] != "declared-limitations-list"]
        report = assess_documents(records, "escc-evaluation", DELIVERED)
        self.assertEqual(report["missing"], ["declared-limitations-list"])

    def test_document_not_owed_by_the_route_is_reported(self):
        records = full_set("ip-core-licence") + [document("escc-detail-specification")]
        report = assess_documents(records, "ip-core-licence", DELIVERED)
        self.assertEqual(report["issued_but_not_owed"], ["escc-detail-specification"])

    def test_interim_issue_is_named(self):
        report = assess_documents(
            full_set(device_user_manual={"issue": "interim"}), "escc-evaluation", DELIVERED
        )
        self.assertEqual(report["not_at_final_issue"], ["device-user-manual"])

    def test_unapproved_document_is_named(self):
        report = assess_documents(
            full_set(device_database={"approved": False}), "escc-evaluation", DELIVERED
        )
        self.assertEqual(report["unapproved"], ["device-database"])

    def test_revision_that_did_not_advance_is_named(self):
        report = assess_documents(
            full_set(device_data_sheet={"revision": "1.3"}), "escc-evaluation", DELIVERED
        )
        self.assertEqual(report["revision_not_advanced"], ["device-data-sheet"])

    def test_revision_that_went_backwards_is_named(self):
        report = assess_documents(
            full_set(device_data_sheet={"revision": "1.2"}), "escc-evaluation", DELIVERED
        )
        self.assertEqual(report["revision_regressed"], ["device-data-sheet"])

    def test_document_naming_another_article_is_named(self):
        report = assess_documents(
            full_set(device_database={"configuration_id": "DEV-EM-01"}),
            "escc-evaluation",
            DELIVERED,
        )
        self.assertEqual(report["wrong_article"], ["device-database"])

    def test_document_without_a_previous_revision_is_not_a_revision_finding(self):
        report = assess_documents(
            full_set(device_data_sheet={"previous_revision": None}),
            "escc-evaluation",
            DELIVERED,
        )
        self.assertEqual(report["revision_not_advanced"], [])

    def test_duplicate_document_raises(self):
        records = full_set() + [document("device-data-sheet")]
        with self.assertRaises(ValueError):
            assess_documents(records, "escc-evaluation", DELIVERED)

    def test_blank_delivered_configuration_raises(self):
        with self.assertRaises(ValueError):
            assess_documents(full_set(), "escc-evaluation", "  ")


class TestRoleCompleteness(unittest.TestCase):
    def test_clean_set_is_fraction_one_on_both_halves(self):
        report = assess_documents(full_set(), "escc-evaluation", DELIVERED)
        for role in ROLES:
            self.assertAlmostEqual(role_completeness(report, role)["fraction"], 1.0, places=9)

    def test_a_procurement_defect_leaves_the_application_half_clean(self):
        report = assess_documents(
            full_set(procurement_specification={"issue": "draft"}),
            "escc-evaluation",
            DELIVERED,
        )
        self.assertAlmostEqual(
            role_completeness(report, "application")["fraction"], 1.0, places=9
        )
        self.assertLess(role_completeness(report, "procurement")["fraction"], 1.0)

    def test_unknown_role_raises(self):
        report = assess_documents(full_set(), "escc-evaluation", DELIVERED)
        with self.assertRaises(ValueError):
            role_completeness(report, "marketing")

    def test_malformed_report_raises(self):
        with self.assertRaises(ValueError):
            role_completeness({"present": {}}, "application")


class TestAssessment(unittest.TestCase):
    def test_clean_evaluation_route_set_is_released(self):
        result = assess_final_application_procurement_documents(clean_spec())
        self.assertEqual(result["disposition"], "released")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["release_fraction"], 1.0, places=9)

    def test_clean_licence_route_set_is_released(self):
        result = assess_final_application_procurement_documents(clean_spec("ip-core-licence"))
        self.assertEqual(result["disposition"], "released")

    def test_unadvanced_revision_blocks_the_release(self):
        spec = clean_spec()
        spec["documents"] = full_set(device_user_manual={"revision": "1.3"})
        result = assess_final_application_procurement_documents(spec)
        self.assertEqual(result["disposition"], "release-blocked")
        self.assertEqual(result["revision_not_advanced"], ["device-user-manual"])

    def test_wrong_article_blocks_the_release(self):
        spec = clean_spec()
        spec["documents"] = full_set(device_data_sheet={"configuration_id": "DEV-EM-01"})
        result = assess_final_application_procurement_documents(spec)
        self.assertEqual(result["wrong_article"], ["device-data-sheet"])
        self.assertEqual(result["disposition"], "release-blocked")

    def test_absent_document_blocks_the_release(self):
        spec = clean_spec()
        spec["documents"] = [d for d in full_set() if d["name"] != "device-database"]
        result = assess_final_application_procurement_documents(spec)
        self.assertEqual(result["missing"], ["device-database"])
        self.assertLess(result["release_fraction"], 1.0)

    def test_every_disposition_returned_is_declared(self):
        result = assess_final_application_procurement_documents(clean_spec())
        self.assertIn(result["disposition"], DISPOSITIONS)

    def test_missing_spec_key_raises(self):
        spec = clean_spec()
        del spec["route"]
        with self.assertRaises(ValueError):
            assess_final_application_procurement_documents(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_final_application_procurement_documents([clean_spec()])


if __name__ == "__main__":
    unittest.main()
