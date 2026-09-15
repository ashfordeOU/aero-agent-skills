"""Contract tests for the clause 4.6.3 class 1 hybrid procurement check.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a construction with no listed
family, a citation of the wrong family, a superseded issue, a missing detail
specification, a supplier off the approval list or past its expiry week, and a
constituent element with no specification of its own.
"""

import unittest

from q60_class_1_hybrid_procurement_logic import (
    DEFAULT_PROCUREMENT_POLICY,
    DETAIL_SPECIFICATION_MISSING,
    ELEMENT_SPECIFICATION_GAP,
    PROCUREMENT_SPECIFICATION_COMPLETE,
    SPECIFICATION_CATALOGUE,
    SPECIFICATION_FAMILY_MISMATCH,
    SPECIFICATION_ISSUE_SUPERSEDED,
    SUPPLIER_NOT_APPROVED,
    WEEKS_PER_YEAR,
    assess_hybrid_procurement,
    check_specification_citation,
    element_specification_coverage,
    parse_week_code,
    select_specification_family,
    supplier_approval_status,
    uncovered_elements,
    validate_elements,
    validate_package,
    validate_procurement_policy,
    week_index,
)

THICK_FILM = SPECIFICATION_CATALOGUE["thick-film"]


def _package(**overrides):
    package = {
        "cited_family": THICK_FILM["generic_family"],
        "cited_issue": THICK_FILM["current_issue"],
        "detail_specification": "detail-0091",
        "supplier": "supplier-north",
        "order_week": "2520",
    }
    package.update(overrides)
    return package


def _elements(**overrides):
    kinds = dict((kind, "element-spec-%s" % kind) for kind in THICK_FILM["element_kinds"])
    kinds.update(overrides)
    return [{"kind": kind, "specification": spec} for kind, spec in sorted(kinds.items())]


def _approvals(**overrides):
    record = {
        "families": [THICK_FILM["generic_family"]],
        "approval_expiry_week": "2740",
    }
    record.update(overrides)
    return {"supplier-north": record}


def _policy(**overrides):
    policy = dict(DEFAULT_PROCUREMENT_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "hybrid_type": "thick-film",
        "package": _package(),
        "elements": _elements(),
        "approvals": _approvals(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_procurement_policy(None)
        self.assertFalse(settings["allow_superseded_issue"])
        self.assertTrue(settings["require_element_specifications"])

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_procurement_policy({"allow_any_issue": True})

    def test_non_boolean_policy_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_procurement_policy({"allow_superseded_issue": 1})


class WeekCodeTests(unittest.TestCase):
    def test_a_well_formed_code_parses(self):
        self.assertEqual(parse_week_code("2520"), (25, 20))

    def test_a_short_code_is_refused(self):
        with self.assertRaises(ValueError):
            parse_week_code("252")

    def test_a_week_beyond_the_year_is_refused(self):
        with self.assertRaises(ValueError):
            parse_week_code("2554")

    def test_the_index_is_monotone_across_a_year_boundary(self):
        self.assertEqual(week_index("2601") - week_index("2552"), 1)

    def test_the_index_uses_the_declared_week_count(self):
        self.assertEqual(week_index("0101") - week_index("0001"), WEEKS_PER_YEAR)


class FamilySelectionTests(unittest.TestCase):
    def test_thick_film_selects_its_generic_family(self):
        entry = select_specification_family("thick-film")
        self.assertEqual(entry["generic_family"], "hybrid-thick-film-generic")

    def test_selection_is_case_insensitive(self):
        self.assertEqual(
            select_specification_family("Multichip-Module")["generic_family"],
            "multichip-module-generic",
        )

    def test_a_microwave_hybrid_needs_no_detail_specification(self):
        entry = select_specification_family("microwave-hybrid")
        self.assertFalse(entry["detail_specification_required"])

    def test_an_unlisted_construction_is_refused(self):
        with self.assertRaises(ValueError):
            select_specification_family("printed-circuit-assembly")

    def test_a_blank_construction_is_refused(self):
        with self.assertRaises(ValueError):
            select_specification_family("   ")


class PackageValidationTests(unittest.TestCase):
    def test_a_complete_package_normalises(self):
        record = validate_package(_package(supplier=" supplier-north "))
        self.assertEqual(record["supplier"], "supplier-north")

    def test_a_package_citing_no_family_is_refused(self):
        with self.assertRaises(ValueError):
            validate_package(_package(cited_family=""))

    def test_a_non_integer_issue_is_refused(self):
        with self.assertRaises(ValueError):
            validate_package(_package(cited_issue="4"))

    def test_a_blank_detail_reference_is_refused(self):
        with self.assertRaises(ValueError):
            validate_package(_package(detail_specification="  "))

    def test_an_absent_detail_reference_is_allowed_at_this_level(self):
        record = validate_package(_package(detail_specification=None))
        self.assertIsNone(record["detail_specification"])

    def test_a_malformed_order_week_is_refused(self):
        with self.assertRaises(ValueError):
            validate_package(_package(order_week="week-20"))

    def test_an_element_with_no_kind_is_refused(self):
        with self.assertRaises(ValueError):
            validate_elements([{"specification": "element-spec-die"}])

    def test_an_element_with_a_blank_specification_is_refused(self):
        with self.assertRaises(ValueError):
            validate_elements([{"kind": "die", "specification": " "}])


class CitationTests(unittest.TestCase):
    def test_a_matching_citation_raises_no_finding(self):
        result = check_specification_citation(
            select_specification_family("thick-film"), _package()
        )
        self.assertEqual(result["findings"], [])

    def test_a_wrong_family_is_named(self):
        result = check_specification_citation(
            select_specification_family("thick-film"),
            _package(cited_family="hybrid-thin-film-generic"),
        )
        self.assertTrue(result["family_mismatch"])

    def test_a_superseded_issue_is_named(self):
        result = check_specification_citation(
            select_specification_family("thick-film"), _package(cited_issue=2)
        )
        self.assertTrue(result["issue_superseded"])

    def test_a_later_issue_is_not_superseded(self):
        result = check_specification_citation(
            select_specification_family("thick-film"), _package(cited_issue=9)
        )
        self.assertFalse(result["issue_superseded"])

    def test_a_missing_detail_specification_is_named(self):
        result = check_specification_citation(
            select_specification_family("thick-film"),
            _package(detail_specification=None),
        )
        self.assertTrue(result["detail_specification_missing"])

    def test_a_non_entry_argument_is_refused(self):
        with self.assertRaises(ValueError):
            check_specification_citation({"current_issue": 4}, _package())


class SupplierApprovalTests(unittest.TestCase):
    def test_an_approved_supplier_passes(self):
        status = supplier_approval_status(
            _approvals(), "supplier-north", THICK_FILM["generic_family"], "2520"
        )
        self.assertTrue(status["approved"])
        self.assertEqual(status["weeks_remaining"], week_index("2740") - week_index("2520"))

    def test_a_supplier_off_the_list_fails(self):
        status = supplier_approval_status(
            _approvals(), "supplier-south", THICK_FILM["generic_family"], "2520"
        )
        self.assertFalse(status["approved"])
        self.assertEqual(status["reason"], "supplier-not-on-approval-list")

    def test_an_approval_for_another_family_fails(self):
        status = supplier_approval_status(
            _approvals(families=["multichip-module-generic"]),
            "supplier-north", THICK_FILM["generic_family"], "2520",
        )
        self.assertEqual(status["reason"], "family-outside-supplier-approval")

    def test_the_expiry_week_itself_is_still_approved_by_default(self):
        status = supplier_approval_status(
            _approvals(approval_expiry_week="2520"),
            "supplier-north", THICK_FILM["generic_family"], "2520",
        )
        self.assertTrue(status["approved"])
        self.assertEqual(status["weeks_remaining"], 0)

    def test_the_expiry_week_can_be_excluded_by_policy(self):
        status = supplier_approval_status(
            _approvals(approval_expiry_week="2520"),
            "supplier-north", THICK_FILM["generic_family"], "2520",
            _policy(approval_valid_through_expiry_week=False),
        )
        self.assertFalse(status["approved"])

    def test_a_lapsed_approval_fails(self):
        status = supplier_approval_status(
            _approvals(approval_expiry_week="2510"),
            "supplier-north", THICK_FILM["generic_family"], "2520",
        )
        self.assertEqual(status["reason"], "supplier-approval-lapsed")

    def test_a_century_straddling_pair_is_refused(self):
        with self.assertRaises(ValueError):
            supplier_approval_status(
                _approvals(approval_expiry_week="0210"),
                "supplier-north", THICK_FILM["generic_family"], "9820",
            )

    def test_an_approval_record_with_no_families_is_refused(self):
        with self.assertRaises(ValueError):
            supplier_approval_status(
                _approvals(families=[]),
                "supplier-north", THICK_FILM["generic_family"], "2520",
            )


class ElementCoverageTests(unittest.TestCase):
    def test_a_full_element_set_leaves_no_gap(self):
        entry = select_specification_family("thick-film")
        self.assertEqual(uncovered_elements(entry, validate_elements(_elements())), [])

    def test_an_element_without_a_specification_is_a_gap(self):
        entry = select_specification_family("thick-film")
        gaps = uncovered_elements(entry, validate_elements(_elements(die=None)))
        self.assertEqual(gaps, ["die"])

    def test_an_element_kind_absent_from_the_build_is_a_gap(self):
        entry = select_specification_family("thick-film")
        records = validate_elements([{"kind": "die", "specification": "element-spec-die"}])
        self.assertIn("substrate", uncovered_elements(entry, records))

    def test_coverage_of_a_complete_build(self):
        entry = select_specification_family("thick-film")
        self.assertAlmostEqual(
            element_specification_coverage(entry, validate_elements(_elements())),
            1.0, places=9,
        )

    def test_coverage_of_a_build_missing_one_kind(self):
        entry = select_specification_family("thick-film")
        expected = (len(entry["element_kinds"]) - 1) / float(len(entry["element_kinds"]))
        self.assertAlmostEqual(
            element_specification_coverage(entry, validate_elements(_elements(die=None))),
            expected, places=9,
        )

    def test_coverage_needs_a_catalogue_entry(self):
        with self.assertRaises(ValueError):
            element_specification_coverage({"generic_family": "x"}, [])


class AssessmentTests(unittest.TestCase):
    def test_a_complete_package_is_orderable(self):
        result = assess_hybrid_procurement(_case())
        self.assertEqual(result["verdict"], PROCUREMENT_SPECIFICATION_COMPLETE)
        self.assertTrue(result["orderable"])
        self.assertEqual(result["findings"], [])

    def test_the_applicable_family_travels_with_the_verdict(self):
        result = assess_hybrid_procurement(_case())
        self.assertEqual(result["applicable_generic_family"], "hybrid-thick-film-generic")

    def test_a_wrong_family_stops_the_order(self):
        result = assess_hybrid_procurement(
            _case(package=_package(cited_family="multichip-module-generic"))
        )
        self.assertEqual(result["verdict"], SPECIFICATION_FAMILY_MISMATCH)

    def test_a_superseded_issue_stops_the_order(self):
        result = assess_hybrid_procurement(_case(package=_package(cited_issue=1)))
        self.assertEqual(result["verdict"], SPECIFICATION_ISSUE_SUPERSEDED)

    def test_a_superseded_issue_can_be_admitted_by_policy(self):
        result = assess_hybrid_procurement(
            _case(package=_package(cited_issue=1), policy=_policy(allow_superseded_issue=True))
        )
        self.assertEqual(result["verdict"], PROCUREMENT_SPECIFICATION_COMPLETE)

    def test_a_missing_detail_specification_stops_the_order(self):
        result = assess_hybrid_procurement(
            _case(package=_package(detail_specification=None))
        )
        self.assertEqual(result["verdict"], DETAIL_SPECIFICATION_MISSING)

    def test_an_unapproved_supplier_stops_the_order(self):
        result = assess_hybrid_procurement(_case(approvals={}))
        self.assertEqual(result["verdict"], SUPPLIER_NOT_APPROVED)
        self.assertFalse(result["supplier_approved"])

    def test_an_element_gap_stops_the_order(self):
        result = assess_hybrid_procurement(_case(elements=_elements(substrate=None)))
        self.assertEqual(result["verdict"], ELEMENT_SPECIFICATION_GAP)
        self.assertEqual(result["uncovered_element_kinds"], ["substrate"])

    def test_the_element_requirement_can_be_waived_by_policy(self):
        result = assess_hybrid_procurement(
            _case(elements=_elements(substrate=None),
                  policy=_policy(require_element_specifications=False))
        )
        self.assertEqual(result["verdict"], PROCUREMENT_SPECIFICATION_COMPLETE)

    def test_the_family_mismatch_outranks_the_supplier_finding(self):
        result = assess_hybrid_procurement(
            _case(package=_package(cited_family="hybrid-thin-film-generic"), approvals={})
        )
        self.assertEqual(result["verdict"], SPECIFICATION_FAMILY_MISMATCH)
        self.assertGreater(len(result["findings"]), 1)

    def test_element_coverage_is_reported_with_the_verdict(self):
        result = assess_hybrid_procurement(_case())
        self.assertAlmostEqual(result["element_specification_coverage"], 1.0, places=9)

    def test_a_missing_package_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement({"hybrid_type": "thick-film"})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(["thick-film"])


if __name__ == "__main__":
    unittest.main()
