#!/usr/bin/env python3
"""Contract test for bare-cell qualification grants, clause 7.4.1 (offline)."""

import copy
import unittest

from e2008_bare_cell_qualification_general_logic import (
    CONFIGURATION_KEYS,
    DEFAULT_GRANT_POLICY,
    GRANT_AUTHORITY_INVALID,
    GRANT_BLOCKED_OPEN_NONCONFORMANCE,
    GRANT_EVIDENCE_INCOMPLETE,
    GRANT_NOT_ISSUED,
    GRANT_SCOPE_MISMATCH,
    GRANTING_AUTHORITY,
    PROGRAMME_FULLY_QUALIFIED,
    PROGRAMME_NOT_FULLY_QUALIFIED,
    QUALIFICATION_GRANTED,
    REQUIRED_QUALIFICATION_EVIDENCE,
    article_configuration,
    assess_qualification_grant,
    assess_qualification_programme,
    configuration_delta,
    evidence_completeness,
    grant_authority,
    grant_scope,
    open_nonconformances,
    required_qualification_evidence,
    validate_grant_policy,
)


def _article(article_id="cell-type-a", **overrides):
    article = {
        "article_id": article_id,
        "cell_type": "triple-junction-bare-cell",
        "supplier": "cell-supplier-one",
        "process_baseline": "baseline-2026-a",
    }
    article.update(overrides)
    return article


def _evidence(skip=(), unbacked=()):
    entries = []
    for activity in REQUIRED_QUALIFICATION_EVIDENCE:
        if activity in skip:
            continue
        entry = {"activity": activity}
        if activity not in unbacked:
            entry["report_ref"] = "rep-%s" % activity
        entries.append(entry)
    return entries


def _dossier(skip=(), unbacked=(), nonconformances=None):
    dossier = {"evidence": _evidence(skip, unbacked)}
    if nonconformances is not None:
        dossier["nonconformances"] = nonconformances
    return dossier


def _grant(article_id="cell-type-a", **overrides):
    grant = {
        "grant_ref": "qual-grant-%s" % article_id,
        "issued_by": GRANTING_AUTHORITY,
        "scope": {
            "cell_type": "triple-junction-bare-cell",
            "supplier": "cell-supplier-one",
            "process_baseline": "baseline-2026-a",
        },
    }
    grant.update(overrides)
    return grant


def _submission(article_id="cell-type-a", **overrides):
    case = {
        "article": _article(article_id),
        "dossier": _dossier(),
        "grant": _grant(article_id),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_grant_policy(DEFAULT_GRANT_POLICY), DEFAULT_GRANT_POLICY)

    def test_default_policy_refuses_supplier_self_declaration(self):
        self.assertFalse(DEFAULT_GRANT_POLICY["admit_supplier_self_declaration"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_grant_policy("grant it")

    def test_non_boolean_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRANT_POLICY)
        broken["require_customer_grant"] = "yes"
        with self.assertRaises(ValueError):
            validate_grant_policy(broken)

    def test_missing_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRANT_POLICY)
        del broken["require_scope_match"]
        with self.assertRaises(ValueError):
            validate_grant_policy(broken)


class ConfigurationTests(unittest.TestCase):
    def test_evidence_set_is_returned_as_a_tuple_copy(self):
        activities = required_qualification_evidence()
        self.assertEqual(activities, REQUIRED_QUALIFICATION_EVIDENCE)
        self.assertIsInstance(activities, tuple)

    def test_configuration_reads_every_identity_attribute(self):
        configuration = article_configuration(_article())
        self.assertEqual(sorted(configuration), sorted(CONFIGURATION_KEYS))

    def test_matching_configurations_have_no_delta(self):
        self.assertEqual(configuration_delta(_article(), _article("other")), [])

    def test_a_changed_process_baseline_shows_in_the_delta(self):
        other = _article("other", process_baseline="baseline-2026-b")
        self.assertEqual(configuration_delta(_article(), other), ["process_baseline"])

    def test_article_missing_an_identity_attribute_rejected(self):
        article = _article()
        del article["supplier"]
        with self.assertRaises(ValueError):
            article_configuration(article)

    def test_non_mapping_article_rejected(self):
        with self.assertRaises(ValueError):
            article_configuration("cell-type-a")


class EvidenceTests(unittest.TestCase):
    def test_a_full_dossier_is_complete(self):
        result = evidence_completeness(_dossier())
        self.assertTrue(result["complete"])
        self.assertAlmostEqual(result["evidence_fraction"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_absent_activity_is_named(self):
        result = evidence_completeness(_dossier(skip=("bare-cell-thermal-cycling",)))
        self.assertEqual(result["absent_activities"], ["bare-cell-thermal-cycling"])
        self.assertFalse(result["complete"])

    def test_an_activity_without_a_report_is_not_evidence(self):
        result = evidence_completeness(
            _dossier(unbacked=("bare-cell-humidity-exposure",))
        )
        self.assertEqual(result["unbacked_activities"], ["bare-cell-humidity-exposure"])
        self.assertFalse(result["complete"])

    def test_evidence_fraction_counts_only_backed_activities(self):
        total = float(len(REQUIRED_QUALIFICATION_EVIDENCE))
        result = evidence_completeness(
            _dossier(unbacked=("bare-cell-humidity-exposure",))
        )
        self.assertAlmostEqual(
            result["evidence_fraction"], (total - 1.0) / total, places=9
        )

    def test_an_unknown_activity_rejected(self):
        dossier = _dossier()
        dossier["evidence"].append({"activity": "bare-cell-taste-test", "report_ref": "x"})
        with self.assertRaises(ValueError):
            evidence_completeness(dossier)

    def test_a_repeated_activity_rejected(self):
        dossier = _dossier()
        dossier["evidence"].append(dict(dossier["evidence"][0]))
        with self.assertRaises(ValueError):
            evidence_completeness(dossier)

    def test_non_sequence_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evidence_completeness({"evidence": "everything"})


class NonconformanceTests(unittest.TestCase):
    def test_a_dossier_without_the_key_has_none_open(self):
        self.assertEqual(open_nonconformances(_dossier()), [])

    def test_a_closed_nonconformance_does_not_block(self):
        dossier = _dossier(
            nonconformances=[{"ncr_id": "ncr-1", "state": "closed"}]
        )
        self.assertEqual(open_nonconformances(dossier), [])

    def test_an_open_nonconformance_is_named(self):
        dossier = _dossier(
            nonconformances=[
                {"ncr_id": "ncr-1", "state": "closed"},
                {"ncr_id": "ncr-2", "state": "open"},
            ]
        )
        self.assertEqual(open_nonconformances(dossier), ["ncr-2"])

    def test_an_unknown_nonconformance_state_rejected(self):
        dossier = _dossier(nonconformances=[{"ncr_id": "ncr-1", "state": "pending"}])
        with self.assertRaises(ValueError):
            open_nonconformances(dossier)

    def test_a_repeated_nonconformance_rejected(self):
        dossier = _dossier(
            nonconformances=[
                {"ncr_id": "ncr-1", "state": "open"},
                {"ncr_id": "ncr-1", "state": "closed"},
            ]
        )
        with self.assertRaises(ValueError):
            open_nonconformances(dossier)


class AuthorityTests(unittest.TestCase):
    def test_a_customer_grant_is_valid(self):
        result = grant_authority(_grant())
        self.assertTrue(result["issued"])
        self.assertTrue(result["authority_valid"])

    def test_no_grant_is_not_issued(self):
        result = grant_authority(None)
        self.assertFalse(result["issued"])
        self.assertFalse(result["authority_valid"])

    def test_a_supplier_declaration_is_refused_by_default(self):
        result = grant_authority(_grant(issued_by="supplier"))
        self.assertFalse(result["authority_valid"])
        self.assertTrue(any("supplier" in f for f in result["findings"]))

    def test_a_supplier_declaration_stands_where_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_GRANT_POLICY)
        policy["admit_supplier_self_declaration"] = True
        result = grant_authority(_grant(issued_by="supplier"), policy)
        self.assertTrue(result["authority_valid"])

    def test_a_laboratory_statement_is_refused_by_default(self):
        result = grant_authority(_grant(issued_by="third-party-laboratory"))
        self.assertFalse(result["authority_valid"])

    def test_a_laboratory_statement_stands_where_no_customer_grant_is_required(self):
        policy = copy.deepcopy(DEFAULT_GRANT_POLICY)
        policy["require_customer_grant"] = False
        result = grant_authority(_grant(issued_by="third-party-laboratory"), policy)
        self.assertTrue(result["authority_valid"])

    def test_an_unknown_issuer_rejected(self):
        with self.assertRaises(ValueError):
            grant_authority(_grant(issued_by="the-project-manager"))

    def test_a_grant_without_a_reference_rejected(self):
        grant = _grant()
        del grant["grant_ref"]
        with self.assertRaises(ValueError):
            grant_authority(grant)


class ScopeTests(unittest.TestCase):
    def test_a_matching_scope_covers_the_article(self):
        result = grant_scope(_grant(), _article())
        self.assertTrue(result["scope_matches"])
        self.assertEqual(result["configuration_delta"], [])

    def test_a_changed_baseline_falls_outside_the_scope(self):
        article = _article(process_baseline="baseline-2026-b")
        result = grant_scope(_grant(), article)
        self.assertFalse(result["scope_matches"])
        self.assertEqual(result["configuration_delta"], ["process_baseline"])

    def test_a_scope_mismatch_stands_where_policy_drops_the_check(self):
        article = _article(process_baseline="baseline-2026-b")
        policy = copy.deepcopy(DEFAULT_GRANT_POLICY)
        policy["require_scope_match"] = False
        result = grant_scope(_grant(), article, policy)
        self.assertTrue(result["scope_matches"])

    def test_a_grant_naming_no_scope_is_reported(self):
        grant = _grant()
        del grant["scope"]
        result = grant_scope(grant, _article())
        self.assertFalse(result["scoped"])
        self.assertTrue(any("no configuration" in f for f in result["findings"]))

    def test_no_grant_has_no_scope(self):
        result = grant_scope(None, _article())
        self.assertFalse(result["scoped"])
        self.assertFalse(result["scope_matches"])


class ArticleVerdictTests(unittest.TestCase):
    def test_a_complete_submission_is_granted(self):
        result = assess_qualification_grant(_submission())
        self.assertEqual(result["verdict"], QUALIFICATION_GRANTED)
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])

    def test_incomplete_evidence_outranks_a_missing_grant(self):
        case = _submission(
            dossier=_dossier(skip=("bare-cell-electron-irradiation",)), grant=None
        )
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_EVIDENCE_INCOMPLETE)

    def test_a_grant_resting_on_thin_evidence_is_called_out(self):
        case = _submission(dossier=_dossier(skip=("bare-cell-electron-irradiation",)))
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_EVIDENCE_INCOMPLETE)
        self.assertTrue(any("rests on an incomplete" in f for f in result["findings"]))

    def test_an_open_nonconformance_outranks_a_wrong_issuer(self):
        case = _submission(
            dossier=_dossier(nonconformances=[{"ncr_id": "ncr-9", "state": "open"}]),
            grant=_grant(issued_by="supplier"),
        )
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_BLOCKED_OPEN_NONCONFORMANCE)

    def test_an_open_nonconformance_stands_where_policy_allows_it(self):
        policy = copy.deepcopy(DEFAULT_GRANT_POLICY)
        policy["allow_grant_with_open_nonconformance"] = True
        case = _submission(
            dossier=_dossier(nonconformances=[{"ncr_id": "ncr-9", "state": "open"}])
        )
        result = assess_qualification_grant(case, policy)
        self.assertEqual(result["verdict"], QUALIFICATION_GRANTED)

    def test_a_missing_grant_with_full_evidence_is_the_lightest_finding(self):
        case = _submission(grant=None)
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_NOT_ISSUED)
        self.assertTrue(any("no customer grant" in f for f in result["findings"]))

    def test_a_supplier_declaration_is_an_authority_finding(self):
        case = _submission(grant=_grant(issued_by="supplier"))
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_AUTHORITY_INVALID)

    def test_a_grant_outside_the_delivered_configuration(self):
        case = _submission(article=_article(process_baseline="baseline-2026-b"))
        result = assess_qualification_grant(case)
        self.assertEqual(result["verdict"], GRANT_SCOPE_MISMATCH)

    def test_a_case_without_an_article_rejected(self):
        case = _submission()
        del case["article"]
        with self.assertRaises(ValueError):
            assess_qualification_grant(case)

    def test_a_case_without_a_dossier_rejected(self):
        case = _submission()
        del case["dossier"]
        with self.assertRaises(ValueError):
            assess_qualification_grant(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_grant([_article()])


class ProgrammeTests(unittest.TestCase):
    def test_a_clean_programme_is_fully_qualified(self):
        case = {"submissions": [_submission("cell-type-a"), _submission("cell-type-b")]}
        result = assess_qualification_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_FULLY_QUALIFIED)
        self.assertAlmostEqual(result["qualified_fraction"], 1.0, places=9)
        self.assertTrue(result["every_article_qualified"])

    def test_one_open_article_opens_the_programme(self):
        case = {
            "submissions": [
                _submission("cell-type-a"),
                _submission("cell-type-b", grant=None),
            ]
        }
        result = assess_qualification_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_NOT_FULLY_QUALIFIED)
        self.assertEqual(result["open_article_ids"], ["cell-type-b"])
        self.assertAlmostEqual(result["qualified_fraction"], 0.5, places=9)

    def test_a_delivered_article_nobody_submitted_is_the_worst_finding(self):
        case = {
            "submissions": [_submission("cell-type-a")],
            "delivered_article_ids": ["cell-type-a", "cell-type-z"],
        }
        result = assess_qualification_programme(case)
        self.assertEqual(result["unsubmitted_article_ids"], ["cell-type-z"])
        self.assertTrue(any("never put forward" in f for f in result["findings"]))

    def test_an_article_submitted_but_not_delivered_is_not_a_finding(self):
        case = {
            "submissions": [
                _submission("cell-type-a"),
                _submission("cell-type-b", grant=None),
            ],
            "delivered_article_ids": ["cell-type-a"],
        }
        result = assess_qualification_programme(case)
        self.assertEqual(result["verdict"], PROGRAMME_FULLY_QUALIFIED)

    def test_articles_are_grouped_by_verdict(self):
        case = {
            "submissions": [
                _submission("cell-type-a"),
                _submission("cell-type-b", grant=_grant("cell-type-b", issued_by="supplier")),
            ]
        }
        result = assess_qualification_programme(case)
        self.assertEqual(
            result["grouped_by_verdict"][GRANT_AUTHORITY_INVALID], ["cell-type-b"]
        )

    def test_records_come_back_in_article_order(self):
        case = {"submissions": [_submission("cell-type-b"), _submission("cell-type-a")]}
        result = assess_qualification_programme(case)
        self.assertEqual(
            [r["article_id"] for r in result["article_records"]],
            ["cell-type-a", "cell-type-b"],
        )

    def test_a_repeated_article_rejected(self):
        case = {"submissions": [_submission("cell-type-a"), _submission("cell-type-a")]}
        with self.assertRaises(ValueError):
            assess_qualification_programme(case)

    def test_an_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_programme({"submissions": []})

    def test_an_empty_delivered_list_rejected(self):
        case = {
            "submissions": [_submission("cell-type-a")],
            "delivered_article_ids": [],
        }
        with self.assertRaises(ValueError):
            assess_qualification_programme(case)

    def test_the_programme_carries_every_article_finding(self):
        case = {"submissions": [_submission("cell-type-a", grant=None)]}
        result = assess_qualification_programme(case)
        self.assertTrue(any("cell-type-a" in f for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
