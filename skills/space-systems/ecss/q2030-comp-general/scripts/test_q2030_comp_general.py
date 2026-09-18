"""Contract test for the complementary general-provisions leaf (stdlib unittest)."""

import unittest

from q2030_comp_general_logic import (
    ANY,
    BLOCKING_FINDINGS,
    SOURCE_ECSS_ADDENDUM,
    SOURCE_ECSS_COMPLEMENTARY,
    SOURCE_EXTERNAL_BASE,
    SOURCE_PROJECT_DEVIATION,
    effective_rank,
    group_by_topic,
    requirement_applies,
    resolve_requirement_set,
    resolve_topic,
    source_rank,
    validate_harness,
    validate_requirement,
)


def harness(hid="H-1", harness_type="shielded-multicore", assurance_level="level-1"):
    return {
        "id": hid,
        "harness_type": harness_type,
        "assurance_level": assurance_level,
    }


def requirement(topic="strain-relief", source=SOURCE_EXTERNAL_BASE, **kw):
    record = {
        "topic": topic,
        "source": source,
        "criterion": "criterion-from-%s" % source,
    }
    record.update(kw)
    return record


class TestValidation(unittest.TestCase):
    def test_harness_fields_are_required(self):
        with self.assertRaises(ValueError):
            validate_harness({"id": "H-1", "harness_type": "coax"})

    def test_non_mapping_harness_raises(self):
        with self.assertRaises(ValueError):
            validate_harness(["H-1"])

    def test_non_mapping_requirement_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(["strain-relief"])

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(source="folklore"))

    def test_empty_topic_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(topic=""))

    def test_missing_criterion_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement({"topic": "strain-relief", "source": SOURCE_EXTERNAL_BASE})

    def test_bare_string_scope_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(applies_to_types="coax"))

    def test_empty_scope_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(applies_to_levels=[]))

    def test_waiver_on_a_non_deviation_raises(self):
        with self.assertRaises(ValueError):
            validate_requirement(requirement(waiver_reference="WVR-1"))

    def test_absent_scope_defaults_to_any(self):
        norm = validate_requirement(requirement())
        self.assertEqual(norm["applies_to_types"], (ANY,))
        self.assertEqual(norm["applies_to_levels"], (ANY,))


class TestPrecedenceRanks(unittest.TestCase):
    def test_complementary_outranks_the_addendum(self):
        self.assertGreater(
            source_rank(SOURCE_ECSS_COMPLEMENTARY), source_rank(SOURCE_ECSS_ADDENDUM)
        )

    def test_addendum_outranks_the_external_basis(self):
        self.assertGreater(
            source_rank(SOURCE_ECSS_ADDENDUM), source_rank(SOURCE_EXTERNAL_BASE)
        )

    def test_approved_deviation_outranks_everything(self):
        self.assertGreater(
            source_rank(SOURCE_PROJECT_DEVIATION), source_rank(SOURCE_ECSS_COMPLEMENTARY)
        )

    def test_unknown_source_rank_raises(self):
        with self.assertRaises(ValueError):
            source_rank("folklore")

    def test_unwaived_deviation_has_no_effective_rank(self):
        self.assertEqual(
            effective_rank(requirement(source=SOURCE_PROJECT_DEVIATION)), 0
        )

    def test_waived_deviation_keeps_its_rank(self):
        waived = requirement(source=SOURCE_PROJECT_DEVIATION, waiver_reference="WVR-1")
        self.assertEqual(effective_rank(waived), source_rank(SOURCE_PROJECT_DEVIATION))


class TestApplicability(unittest.TestCase):
    def test_any_scope_applies_everywhere(self):
        self.assertTrue(requirement_applies(requirement(), harness()))

    def test_type_scope_excludes_another_type(self):
        scoped = requirement(applies_to_types=["coax"])
        self.assertFalse(requirement_applies(scoped, harness(harness_type="ribbon")))

    def test_type_scope_includes_a_listed_type(self):
        scoped = requirement(applies_to_types=["coax", "ribbon"])
        self.assertTrue(requirement_applies(scoped, harness(harness_type="ribbon")))

    def test_level_scope_excludes_another_level(self):
        scoped = requirement(applies_to_levels=["level-3"])
        self.assertFalse(requirement_applies(scoped, harness(assurance_level="level-1")))

    def test_both_scopes_must_match(self):
        scoped = requirement(applies_to_types=["coax"], applies_to_levels=["level-1"])
        self.assertFalse(
            requirement_applies(scoped, harness(harness_type="coax", assurance_level="level-3"))
        )


class TestResolveTopic(unittest.TestCase):
    def test_complementary_governs_over_addendum_and_base(self):
        governing, findings = resolve_topic(
            [
                requirement(source=SOURCE_EXTERNAL_BASE),
                requirement(source=SOURCE_ECSS_ADDENDUM),
                requirement(source=SOURCE_ECSS_COMPLEMENTARY),
            ],
            harness(),
        )
        self.assertEqual(governing["source"], SOURCE_ECSS_COMPLEMENTARY)
        self.assertEqual(findings, [])

    def test_base_alone_is_reported_but_governs(self):
        governing, findings = resolve_topic(
            [requirement(source=SOURCE_EXTERNAL_BASE)], harness()
        )
        self.assertEqual(governing["source"], SOURCE_EXTERNAL_BASE)
        self.assertIn("topic-governed-by-the-external-basis-alone", findings)

    def test_unwaived_deviation_is_demoted_and_reported(self):
        governing, findings = resolve_topic(
            [
                requirement(source=SOURCE_ECSS_COMPLEMENTARY),
                requirement(source=SOURCE_PROJECT_DEVIATION),
            ],
            harness(),
        )
        self.assertEqual(governing["source"], SOURCE_ECSS_COMPLEMENTARY)
        self.assertIn("deviation-without-an-approved-waiver", findings)

    def test_waived_deviation_governs(self):
        governing, findings = resolve_topic(
            [
                requirement(source=SOURCE_ECSS_COMPLEMENTARY),
                requirement(source=SOURCE_PROJECT_DEVIATION, waiver_reference="WVR-1"),
            ],
            harness(),
        )
        self.assertEqual(governing["source"], SOURCE_PROJECT_DEVIATION)
        self.assertEqual(findings, [])

    def test_inapplicable_requirement_is_out_of_the_contest(self):
        governing, _ = resolve_topic(
            [
                requirement(source=SOURCE_EXTERNAL_BASE),
                requirement(
                    source=SOURCE_ECSS_COMPLEMENTARY, applies_to_types=["coax"]
                ),
            ],
            harness(harness_type="ribbon"),
        )
        self.assertEqual(governing["source"], SOURCE_EXTERNAL_BASE)

    def test_no_applicable_requirement_is_a_finding(self):
        governing, findings = resolve_topic(
            [requirement(source=SOURCE_EXTERNAL_BASE, applies_to_types=["coax"])],
            harness(harness_type="ribbon"),
        )
        self.assertIsNone(governing)
        self.assertIn("topic-has-no-applicable-requirement", findings)

    def test_same_rank_disagreement_is_a_finding(self):
        governing, findings = resolve_topic(
            [
                requirement(source=SOURCE_ECSS_COMPLEMENTARY, criterion="one"),
                requirement(source=SOURCE_ECSS_COMPLEMENTARY, criterion="two"),
            ],
            harness(),
        )
        self.assertIsNotNone(governing)
        self.assertIn("conflicting-sources-at-the-same-precedence-rank", findings)

    def test_same_rank_agreement_is_clean(self):
        _, findings = resolve_topic(
            [
                requirement(source=SOURCE_ECSS_COMPLEMENTARY, criterion="one"),
                requirement(source=SOURCE_ECSS_COMPLEMENTARY, criterion="one"),
            ],
            harness(),
        )
        self.assertEqual(findings, [])

    def test_mixed_topics_raise(self):
        with self.assertRaises(ValueError):
            resolve_topic(
                [requirement(topic="strain-relief"), requirement(topic="marking")],
                harness(),
            )

    def test_empty_topic_group_raises(self):
        with self.assertRaises(ValueError):
            resolve_topic([], harness())


class TestGroupByTopic(unittest.TestCase):
    def test_grouping_preserves_first_seen_order(self):
        grouped = group_by_topic(
            [
                requirement(topic="marking"),
                requirement(topic="strain-relief"),
                requirement(topic="marking", source=SOURCE_ECSS_ADDENDUM),
            ]
        )
        self.assertEqual([topic for topic, _ in grouped], ["marking", "strain-relief"])
        self.assertEqual(len(grouped[0][1]), 2)

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            group_by_topic(requirement())

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            group_by_topic([])


class TestResolveRequirementSet(unittest.TestCase):
    def test_a_clean_set_is_compliant(self):
        report = resolve_requirement_set(
            [
                requirement(topic="marking", source=SOURCE_ECSS_COMPLEMENTARY),
                requirement(topic="strain-relief", source=SOURCE_ECSS_ADDENDUM),
            ],
            harness(),
        )
        self.assertTrue(report["compliant"])
        self.assertEqual(report["governed_by"][SOURCE_ECSS_COMPLEMENTARY], 1)
        self.assertEqual(report["governed_by"][SOURCE_ECSS_ADDENDUM], 1)

    def test_external_basis_only_topics_are_listed(self):
        report = resolve_requirement_set(
            [
                requirement(topic="marking", source=SOURCE_EXTERNAL_BASE),
                requirement(topic="strain-relief", source=SOURCE_ECSS_COMPLEMENTARY),
            ],
            harness(),
        )
        self.assertEqual(report["external_basis_only_topics"], ["marking"])
        self.assertTrue(report["compliant"])

    def test_ecss_governed_fraction_is_reported(self):
        report = resolve_requirement_set(
            [
                requirement(topic="marking", source=SOURCE_EXTERNAL_BASE),
                requirement(topic="strain-relief", source=SOURCE_ECSS_COMPLEMENTARY),
            ],
            harness(),
        )
        self.assertAlmostEqual(report["ecss_governed_fraction"], 0.5, places=9)

    def test_unwaived_deviation_blocks_the_set(self):
        report = resolve_requirement_set(
            [
                requirement(topic="marking", source=SOURCE_ECSS_COMPLEMENTARY),
                requirement(topic="marking", source=SOURCE_PROJECT_DEVIATION),
            ],
            harness(),
        )
        self.assertFalse(report["compliant"])
        self.assertIn("deviation-without-an-approved-waiver", report["blocking_findings"])

    def test_unresolved_topic_is_listed_and_blocks(self):
        report = resolve_requirement_set(
            [
                requirement(
                    topic="marking", source=SOURCE_EXTERNAL_BASE, applies_to_types=["coax"]
                )
            ],
            harness(harness_type="ribbon"),
        )
        self.assertEqual(report["unresolved_topics"], ["marking"])
        self.assertFalse(report["compliant"])

    def test_external_basis_only_is_not_a_blocking_finding(self):
        self.assertNotIn("topic-governed-by-the-external-basis-alone", BLOCKING_FINDINGS)

    def test_non_list_requirement_set_raises(self):
        with self.assertRaises(ValueError):
            resolve_requirement_set(requirement(), harness())

    def test_bad_harness_raises(self):
        with self.assertRaises(ValueError):
            resolve_requirement_set([requirement()], {"id": "H-1"})


if __name__ == "__main__":
    unittest.main()
