#!/usr/bin/env python3
"""Contract test for the two-phase technical specification content."""

import copy
import unittest

from e3102_technical_specification_ts_content_logic import (
    CONTENT_CATEGORIES,
    REQUIRED_TOPICS,
    TS_COMPLETE,
    TS_INCOMPLETE,
    VERIFICATION_METHODS,
    all_required_topics,
    assess_verifiability,
    category_coverage,
    coverage_report,
    index_requirements,
    specify_ts_content,
    validate_requirement,
)

_UNITS = {
    "transported-power": "W",
    "thermal-conductance": "W/K",
    "maximum-adverse-tilt": "mm",
    "start-up-capability": "W",
    "operating-temperature-range": "K",
    "non-operating-temperature-range": "K",
    "random-vibration-level": "g2/Hz",
    "radiation-environment": "krad",
    "mechanical-mounting-interface": "N.m",
    "thermal-contact-interface": "W/K",
    "dimensional-envelope-and-mass": "kg",
    "electrical-bonding-interface": "mohm",
    "acceptance-data-package-content": "count",
    "qualification-test-report-content": "count",
    "measurement-uncertainty-statement": "percent",
    "test-tolerance-and-conditions": "K",
}


def _full_requirements():
    records = []
    index = 0
    for category, topic in all_required_topics():
        index += 1
        records.append(
            {
                "id": "TS-%03d" % index,
                "category": category,
                "topic": topic,
                "value": 10.0 + index,
                "unit": _UNITS[topic],
                "tolerance": 0.5,
                "verification_method": "test",
            }
        )
    return records


FULL = tuple(_full_requirements())

BASE_CASE = {
    "specification": "TS-LHP-0001 issue 2",
    "requirements": FULL,
}


def _without(topic):
    return tuple(record for record in FULL if record["topic"] != topic)


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


def _record(**overrides):
    record = {
        "id": "TS-900",
        "category": "performance",
        "topic": "transported-power",
        "value": 120.0,
        "unit": "W",
        "tolerance": 5.0,
        "verification_method": "test",
    }
    record.update(overrides)
    return record


class TopicRegistryTests(unittest.TestCase):
    def test_every_category_declares_required_topics(self):
        for category in CONTENT_CATEGORIES:
            self.assertTrue(REQUIRED_TOPICS[category])

    def test_the_flat_topic_list_covers_every_category(self):
        categories = {category for category, _ in all_required_topics()}
        self.assertEqual(categories, set(CONTENT_CATEGORIES))

    def test_the_flat_topic_list_has_no_repeat(self):
        topics = all_required_topics()
        self.assertEqual(len(topics), len(set(topics)))

    def test_the_fixture_covers_every_required_topic(self):
        self.assertEqual(len(FULL), len(all_required_topics()))


class RequirementValidationTests(unittest.TestCase):
    def test_a_complete_requirement_validates(self):
        record = _record()
        self.assertIs(validate_requirement(record), record)

    def test_a_requirement_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_record(id=""))

    def test_a_requirement_with_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement(_record(category="commercial"))

    def test_a_requirement_without_a_topic_rejected(self):
        broken = _record()
        del broken["topic"]
        with self.assertRaises(ValueError):
            validate_requirement(broken)

    def test_a_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement("transported-power 120 W")


class VerifiabilityTests(unittest.TestCase):
    def test_a_complete_requirement_is_verifiable(self):
        verdict = assess_verifiability(_record())
        self.assertTrue(verdict["verifiable"])
        self.assertEqual(verdict["reasons"], [])

    def test_a_requirement_with_no_value_is_not_verifiable(self):
        verdict = assess_verifiability(_record(value=None))
        self.assertFalse(verdict["verifiable"])
        self.assertTrue(any("numeric value" in r for r in verdict["reasons"]))

    def test_a_requirement_with_no_unit_is_not_verifiable(self):
        verdict = assess_verifiability(_record(unit="  "))
        self.assertTrue(any("no unit" in r for r in verdict["reasons"]))

    def test_a_zero_tolerance_is_not_verifiable(self):
        verdict = assess_verifiability(_record(tolerance=0.0))
        self.assertTrue(any("zero tolerance" in r for r in verdict["reasons"]))

    def test_a_negative_tolerance_is_not_verifiable(self):
        verdict = assess_verifiability(_record(tolerance=-1.0))
        self.assertTrue(any("negative tolerance" in r for r in verdict["reasons"]))

    def test_an_unknown_verification_method_is_not_verifiable(self):
        verdict = assess_verifiability(_record(verification_method="vendor-word"))
        self.assertTrue(any("verification method" in r for r in verdict["reasons"]))

    def test_every_named_method_is_accepted(self):
        for method in VERIFICATION_METHODS:
            self.assertTrue(
                assess_verifiability(_record(verification_method=method))["verifiable"]
            )

    def test_a_boolean_value_is_not_a_number(self):
        verdict = assess_verifiability(_record(value=True))
        self.assertFalse(verdict["verifiable"])


class IndexTests(unittest.TestCase):
    def test_a_supplementary_topic_is_reported(self):
        extra = _record(id="TS-901", topic="colour-of-the-saddle")
        index = index_requirements(list(FULL) + [extra])
        self.assertIn(("performance", "colour-of-the-saddle"), index["supplementary"])

    def test_no_supplementary_topic_on_the_fixture(self):
        self.assertEqual(index_requirements(FULL)["supplementary"], ())

    def test_a_duplicate_requirement_id_rejected(self):
        with self.assertRaises(ValueError):
            index_requirements(list(FULL) + [copy.deepcopy(FULL[0])])

    def test_a_non_sequence_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            index_requirements("TS-001")


class CoverageTests(unittest.TestCase):
    def test_a_full_specification_covers_every_category(self):
        for category in CONTENT_CATEGORIES:
            block = category_coverage(FULL, category)
            self.assertTrue(block["complete"])
            self.assertAlmostEqual(block["fraction"], 1.0, places=9)

    def test_a_dropped_topic_shows_as_missing(self):
        block = category_coverage(_without("thermal-conductance"), "performance")
        self.assertIn("thermal-conductance", block["missing"])
        self.assertFalse(block["complete"])

    def test_a_dropped_topic_lowers_the_fraction(self):
        block = category_coverage(_without("thermal-conductance"), "performance")
        self.assertAlmostEqual(
            block["fraction"], (block["required"] - 1) / float(block["required"]),
            places=9,
        )

    def test_a_dropped_topic_in_one_family_leaves_the_others_complete(self):
        report = coverage_report(_without("radiation-environment"))
        self.assertFalse(report["by_category"]["environmental"]["complete"])
        self.assertTrue(report["by_category"]["performance"]["complete"])

    def test_the_overall_report_counts_every_required_topic(self):
        report = coverage_report(FULL)
        self.assertEqual(report["required"], len(all_required_topics()))
        self.assertEqual(report["covered"], report["required"])
        self.assertTrue(report["complete"])

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            category_coverage(FULL, "commercial")


class SpecifyTests(unittest.TestCase):
    def test_a_full_specification_is_complete(self):
        result = specify_ts_content(BASE_CASE)
        self.assertEqual(result["verdict"], TS_COMPLETE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unverifiable"], [])

    def test_a_missing_topic_makes_the_specification_incomplete(self):
        result = specify_ts_content(
            _case(BASE_CASE, requirements=_without("start-up-capability"))
        )
        self.assertEqual(result["verdict"], TS_INCOMPLETE)
        self.assertTrue(any("start-up-capability" in f for f in result["findings"]))

    def test_an_unverifiable_requirement_makes_it_incomplete(self):
        requirements = [copy.deepcopy(record) for record in FULL]
        requirements[0]["tolerance"] = 0.0
        result = specify_ts_content(_case(BASE_CASE, requirements=requirements))
        self.assertEqual(result["verdict"], TS_INCOMPLETE)
        self.assertEqual(len(result["unverifiable"]), 1)

    def test_coverage_can_be_complete_while_the_verdict_is_not(self):
        requirements = [copy.deepcopy(record) for record in FULL]
        requirements[3]["verification_method"] = "we-will-see"
        result = specify_ts_content(_case(BASE_CASE, requirements=requirements))
        self.assertTrue(result["coverage"]["complete"])
        self.assertEqual(result["verdict"], TS_INCOMPLETE)

    def test_a_supplementary_requirement_does_not_break_completeness(self):
        extra = _record(id="TS-902", topic="preferred-supplier-note", tolerance=1.0)
        result = specify_ts_content(
            _case(BASE_CASE, requirements=list(FULL) + [extra])
        )
        self.assertEqual(result["verdict"], TS_COMPLETE)
        self.assertTrue(result["supplementary_topics"])

    def test_an_empty_specification_rejected(self):
        with self.assertRaises(ValueError):
            specify_ts_content(_case(BASE_CASE, requirements=()))

    def test_a_specification_without_a_reference_rejected(self):
        case = _case(BASE_CASE)
        del case["specification"]
        with self.assertRaises(ValueError):
            specify_ts_content(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            specify_ts_content("TS-LHP-0001")

    def test_every_missing_topic_gets_its_own_finding(self):
        requirements = _without("transported-power")
        requirements = tuple(
            record for record in requirements if record["topic"] != "radiation-environment"
        )
        result = specify_ts_content(_case(BASE_CASE, requirements=requirements))
        self.assertEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
