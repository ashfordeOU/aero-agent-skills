#!/usr/bin/env python3
"""Gate 3 contract test for e2007-system-verification-entry-condition.

Stdlib unittest only, offline, deterministic.
"""

import unittest

from e2007_system_verification_entry_condition_logic import (
    DEFAULT_ENTRY_SPEC,
    RATIO_EPS,
    acceptance_age_days,
    admitted_fraction,
    article_findings,
    blocking_severities,
    build_inventory,
    entry_status,
    evaluate_entry_condition,
    normalize_status,
    resolve_spec,
    severity_rank,
    subsystem_rollup,
    validate_article,
    waiver_admissible,
)

CAMPAIGN_DAY = 1000


def nominal_articles():
    return [
        {"name": "power-subsystem", "level": "subsystem", "status": "passed",
         "acceptance_day": 950},
        {"name": "avionics-subsystem", "level": "subsystem", "status": "passed",
         "acceptance_day": 940},
        {"name": "power-control-unit", "level": "unit", "parent": "power-subsystem",
         "status": "passed", "acceptance_day": 900},
        {"name": "battery-module", "level": "unit", "parent": "power-subsystem",
         "status": "passed", "acceptance_day": 910},
        {"name": "onboard-computer", "level": "unit", "parent": "avionics-subsystem",
         "status": "passed", "acceptance_day": 920},
    ]


def nominal_config():
    return {"articles": nominal_articles(), "campaign_day": CAMPAIGN_DAY}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertEqual(spec["acceptance_validity_days"], 365)
        self.assertEqual(set(spec), set(DEFAULT_ENTRY_SPEC))

    def test_override_is_applied(self):
        self.assertEqual(resolve_spec({"acceptance_validity_days": 90})["acceptance_validity_days"], 90)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"acceptance_validity_days": 90})
        self.assertEqual(DEFAULT_ENTRY_SPEC["acceptance_validity_days"], 365)

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"reviewer_mood": 1})

    def test_negative_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"waiver_validity_days": -5})

    def test_fractional_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"waiver_validity_days": 10.5})


class TestVocabulary(unittest.TestCase):
    def test_status_is_normalized(self):
        self.assertEqual(normalize_status("NOT_RUN"), "not-run")

    def test_unrecognized_status_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_status("probably-fine")

    def test_empty_status_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_status("   ")

    def test_severity_ranks_are_ordered(self):
        self.assertLess(severity_rank("minor"), severity_rank("major"))
        self.assertLess(severity_rank("major"), severity_rank("critical"))

    def test_unrecognized_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            severity_rank("cosmetic")


class TestArticleValidation(unittest.TestCase):
    def test_a_unit_keeps_its_parent(self):
        record = validate_article(
            {"name": "u", "level": "unit", "parent": "s", "status": "passed",
             "acceptance_day": 900}
        )
        self.assertEqual(record["parent"], "s")

    def test_a_unit_without_a_parent_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "u", "level": "unit", "status": "passed",
                              "acceptance_day": 900})

    def test_a_unit_that_parents_itself_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "u", "level": "unit", "parent": "u",
                              "status": "passed", "acceptance_day": 900})

    def test_a_subsystem_with_a_parent_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "s", "level": "subsystem", "parent": "x",
                              "status": "passed", "acceptance_day": 900})

    def test_unrecognized_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "s", "level": "assembly", "status": "passed",
                              "acceptance_day": 900})

    def test_passed_article_without_an_acceptance_day_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "s", "level": "subsystem", "status": "passed"})

    def test_nonconformance_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_article({"name": "s", "level": "subsystem", "status": "passed",
                              "acceptance_day": 900, "nonconformances": "major"})


class TestInventory(unittest.TestCase):
    def test_a_well_formed_inventory_builds(self):
        inventory = build_inventory(nominal_articles())
        self.assertEqual(sorted(inventory["subsystems"]), ["avionics-subsystem", "power-subsystem"])
        self.assertEqual(sorted(inventory["children"]["power-subsystem"]),
                         ["battery-module", "power-control-unit"])

    def test_duplicate_names_are_rejected(self):
        articles = nominal_articles()
        articles[3]["name"] = articles[2]["name"]
        with self.assertRaises(ValueError):
            build_inventory(articles)

    def test_orphan_unit_is_rejected(self):
        articles = nominal_articles()
        articles[2]["parent"] = "thermal-subsystem"
        with self.assertRaises(ValueError):
            build_inventory(articles)

    def test_subsystem_without_a_unit_is_rejected(self):
        articles = [a for a in nominal_articles() if a["name"] != "onboard-computer"]
        with self.assertRaises(ValueError):
            build_inventory(articles)

    def test_inventory_without_a_subsystem_is_rejected(self):
        with self.assertRaises(ValueError):
            build_inventory([{"name": "u", "level": "unit", "parent": "s",
                              "status": "passed", "acceptance_day": 900}])

    def test_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            build_inventory([])


class TestArticleFindings(unittest.TestCase):
    def test_a_passed_article_raises_nothing(self):
        record = validate_article(nominal_articles()[2])
        self.assertEqual(article_findings(record, CAMPAIGN_DAY), [])

    def test_a_failed_article_is_a_finding(self):
        article = nominal_articles()[2]
        article["status"] = "failed"
        record = validate_article(article)
        self.assertTrue(any("not passed" in f for f in article_findings(record, CAMPAIGN_DAY)))

    def test_an_unrun_acceptance_is_a_finding(self):
        article = nominal_articles()[2]
        article["status"] = "not-run"
        record = validate_article(article)
        self.assertTrue(any("no functional acceptance result" in f
                            for f in article_findings(record, CAMPAIGN_DAY)))

    def test_a_major_nonconformance_blocks(self):
        article = nominal_articles()[2]
        article["nonconformances"] = ["major"]
        record = validate_article(article)
        self.assertEqual(len(blocking_severities(record)), 1)
        self.assertTrue(any("blocking severity" in f
                            for f in article_findings(record, CAMPAIGN_DAY)))

    def test_a_minor_nonconformance_does_not_block(self):
        article = nominal_articles()[2]
        article["nonconformances"] = ["minor", "minor"]
        record = validate_article(article)
        self.assertEqual(blocking_severities(record), [])
        self.assertEqual(article_findings(record, CAMPAIGN_DAY), [])

    def test_stale_acceptance_evidence_is_a_finding(self):
        article = nominal_articles()[2]
        article["acceptance_day"] = CAMPAIGN_DAY - 400
        record = validate_article(article)
        self.assertTrue(any("validity window" in f
                            for f in article_findings(record, CAMPAIGN_DAY)))

    def test_acceptance_exactly_on_the_validity_window_is_accepted(self):
        article = nominal_articles()[2]
        article["acceptance_day"] = CAMPAIGN_DAY - 365
        record = validate_article(article)
        self.assertEqual(acceptance_age_days(record, CAMPAIGN_DAY), 365)
        self.assertEqual(article_findings(record, CAMPAIGN_DAY), [])

    def test_acceptance_after_the_campaign_day_is_rejected(self):
        article = nominal_articles()[2]
        article["acceptance_day"] = CAMPAIGN_DAY + 1
        record = validate_article(article)
        with self.assertRaises(ValueError):
            acceptance_age_days(record, CAMPAIGN_DAY)


class TestWaivers(unittest.TestCase):
    def test_a_fresh_authorized_waiver_is_admissible(self):
        ok, reason = waiver_admissible(
            {"authority": "product-assurance-board", "raised_day": CAMPAIGN_DAY - 10},
            CAMPAIGN_DAY,
        )
        self.assertTrue(ok)
        self.assertIn("admissible", reason)

    def test_a_waiver_without_an_authority_is_not_admissible(self):
        ok, reason = waiver_admissible({"raised_day": CAMPAIGN_DAY - 10}, CAMPAIGN_DAY)
        self.assertFalse(ok)
        self.assertIn("authority", reason)

    def test_an_aged_waiver_is_not_admissible(self):
        ok, reason = waiver_admissible(
            {"authority": "board", "raised_day": CAMPAIGN_DAY - 200}, CAMPAIGN_DAY
        )
        self.assertFalse(ok)
        self.assertIn("validity window", reason)

    def test_a_waiver_exactly_on_its_window_is_admissible(self):
        ok, _ = waiver_admissible(
            {"authority": "board", "raised_day": CAMPAIGN_DAY - 180}, CAMPAIGN_DAY
        )
        self.assertTrue(ok)

    def test_a_waiver_raised_after_the_campaign_day_is_rejected(self):
        with self.assertRaises(ValueError):
            waiver_admissible({"authority": "board", "raised_day": CAMPAIGN_DAY + 1},
                              CAMPAIGN_DAY)

    def test_a_waived_article_without_a_waiver_record_is_a_finding(self):
        article = nominal_articles()[2]
        article["status"] = "waived"
        record = validate_article(article)
        self.assertTrue(any("no waiver record" in f
                            for f in article_findings(record, CAMPAIGN_DAY)))


class TestRollup(unittest.TestCase):
    def test_an_unaccepted_unit_holds_its_subsystem(self):
        inventory = build_inventory(nominal_articles())
        admitted = {r["name"]: True for r in inventory["records"]}
        admitted["battery-module"] = False
        rollup = subsystem_rollup(inventory, admitted)
        self.assertEqual(rollup["held"]["power-subsystem"], ["battery-module"])
        self.assertTrue(any("power-subsystem" in f for f in rollup["findings"]))

    def test_a_fully_accepted_tree_holds_nothing(self):
        inventory = build_inventory(nominal_articles())
        admitted = {r["name"]: True for r in inventory["records"]}
        self.assertEqual(subsystem_rollup(inventory, admitted)["findings"], [])

    def test_rollup_needs_a_mapping(self):
        inventory = build_inventory(nominal_articles())
        with self.assertRaises(ValueError):
            subsystem_rollup(inventory, ["battery-module"])

    def test_admitted_fraction_is_reported(self):
        self.assertAlmostEqual(admitted_fraction({"a": True, "b": False}), 0.5, places=9)

    def test_admitted_fraction_rejects_an_empty_mapping(self):
        with self.assertRaises(ValueError):
            admitted_fraction({})


class TestEndToEnd(unittest.TestCase):
    def test_a_clean_inventory_authorizes_the_system_test(self):
        report = evaluate_entry_condition(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "system-emc-test-authorized")
        self.assertTrue(report["authorized"])
        self.assertAlmostEqual(report["admitted_fraction"], 1.0, places=9)

    def test_one_failed_unit_holds_the_whole_campaign(self):
        config = nominal_config()
        config["articles"][2]["status"] = "failed"
        report = evaluate_entry_condition(config)
        self.assertFalse(report["authorized"])
        self.assertEqual(report["status"], "hold-system-test")
        self.assertEqual(report["held_subsystems"]["power-subsystem"], ["power-control-unit"])

    def test_an_accepted_subsystem_over_a_failed_unit_is_still_held(self):
        config = nominal_config()
        config["articles"][3]["status"] = "not-run"
        report = evaluate_entry_condition(config)
        self.assertTrue(any("subsystem power-subsystem cannot enter" in f
                            for f in report["findings"]))

    def test_an_admissible_waiver_lets_an_article_enter(self):
        config = nominal_config()
        config["articles"][4]["status"] = "waived"
        config["articles"][4]["waiver"] = {
            "authority": "product-assurance-board",
            "raised_day": CAMPAIGN_DAY - 30,
        }
        self.assertTrue(evaluate_entry_condition(config)["authorized"])

    def test_an_inadmissible_waiver_holds_the_campaign(self):
        config = nominal_config()
        config["articles"][4]["status"] = "waived"
        config["articles"][4]["waiver"] = {"raised_day": CAMPAIGN_DAY - 30}
        self.assertFalse(evaluate_entry_condition(config)["authorized"])

    def test_spec_override_can_requalify_a_campaign(self):
        config = nominal_config()
        config["articles"][2]["acceptance_day"] = CAMPAIGN_DAY - 400
        self.assertFalse(evaluate_entry_condition(config)["authorized"])
        config["spec"] = {"acceptance_validity_days": 500}
        self.assertTrue(evaluate_entry_condition(config)["authorized"])

    def test_blocking_rank_override_admits_a_major_finding(self):
        config = nominal_config()
        config["articles"][2]["nonconformances"] = ["major"]
        self.assertFalse(evaluate_entry_condition(config)["authorized"])
        config["spec"] = {"blocking_severity_rank": 3}
        self.assertTrue(evaluate_entry_condition(config)["authorized"])

    def test_missing_required_key_is_rejected(self):
        config = nominal_config()
        del config["campaign_day"]
        with self.assertRaises(ValueError):
            evaluate_entry_condition(config)

    def test_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_entry_condition([("articles", [])])

    def test_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            entry_status("hold")

    def test_named_tolerance_is_far_below_any_reported_fraction(self):
        self.assertLess(RATIO_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
