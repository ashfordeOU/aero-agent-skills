"""Contract tests for the clause 5.8.2 GSE configuration control logic."""

import unittest

from q20_gse_config_logic import (
    RATIO_TOLERANCE,
    applied_ratio,
    assess_gse_configuration,
    declared_configuration_findings,
    identification_findings,
    normalize_token,
    replay_changes,
    validate_baseline,
    validate_change,
    validate_change_log,
    validate_item,
)

BASELINE = [
    {"item_id": "gse-handling-dolly", "part_number": "pn-100", "serial_number": "sn-1", "version": 1},
    {"item_id": "gse-test-rack", "part_number": "pn-200", "serial_number": "sn-2", "version": 3},
]

CHANGES = [
    {"id": "ecr-1", "item_id": "gse-handling-dolly", "from_version": 1, "to_version": 2, "approved": True},
    {"id": "ecr-2", "item_id": "gse-test-rack", "from_version": 3, "to_version": 4, "approved": True},
]

DECLARED = [
    {"item_id": "gse-handling-dolly", "version": 2},
    {"item_id": "gse-test-rack", "version": 4},
]


def _spec(**overrides):
    spec = {
        "baseline": [dict(i) for i in BASELINE],
        "changes": [dict(c) for c in CHANGES],
        "declared": [dict(d) for d in DECLARED],
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_identifier_case_folded(self):
        self.assertEqual(normalize_token("GSE Test_Rack"), "gse-test-rack")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("\t")


class ValidateItemTests(unittest.TestCase):
    def test_item_normalized(self):
        item = validate_item(BASELINE[0])
        self.assertEqual(item["item_id"], "gse-handling-dolly")
        self.assertEqual(item["version"], 1)

    def test_version_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"item_id": "x", "version": 0})

    def test_boolean_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"item_id": "x", "version": True})

    def test_float_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"item_id": "x", "version": 2.0})

    def test_missing_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_item({"item_id": "x"})

    def test_duplicate_baseline_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline([dict(BASELINE[0]), dict(BASELINE[0])])

    def test_empty_baseline_rejected(self):
        with self.assertRaises(ValueError):
            validate_baseline([])


class IdentificationTests(unittest.TestCase):
    def test_fully_identified_baseline_is_clean(self):
        self.assertEqual(identification_findings(validate_baseline(BASELINE)), [])

    def test_missing_serial_is_a_finding(self):
        baseline = validate_baseline([{"item_id": "gse-crane", "part_number": "pn-9", "version": 1}])
        findings = identification_findings(baseline)
        self.assertEqual(len(findings), 1)
        self.assertIn("individual serial", findings[0])

    def test_missing_part_number_is_a_separate_finding(self):
        baseline = validate_baseline([{"item_id": "gse-crane", "serial_number": "sn-9", "version": 1}])
        self.assertIn("part number", identification_findings(baseline)[0])

    def test_both_missing_gives_two_findings(self):
        baseline = validate_baseline([{"item_id": "gse-crane", "version": 1}])
        self.assertEqual(len(identification_findings(baseline)), 2)


class ValidateChangeTests(unittest.TestCase):
    def test_change_normalized(self):
        change = validate_change(CHANGES[0])
        self.assertEqual(change["id"], "ecr-1")
        self.assertTrue(change["approved"])

    def test_approval_defaults_to_false(self):
        change = validate_change(
            {"id": "ecr-9", "item_id": "gse-test-rack", "from_version": 1, "to_version": 2}
        )
        self.assertFalse(change["approved"])

    def test_non_boolean_approval_rejected(self):
        with self.assertRaises(ValueError):
            validate_change(
                {"id": "e", "item_id": "i", "from_version": 1, "to_version": 2, "approved": "yes"}
            )

    def test_missing_target_rejected(self):
        with self.assertRaises(ValueError):
            validate_change({"id": "e", "from_version": 1, "to_version": 2})

    def test_duplicate_change_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_change_log([dict(CHANGES[0]), dict(CHANGES[0])])

    def test_none_log_is_empty(self):
        self.assertEqual(validate_change_log(None), [])


class ReplayTests(unittest.TestCase):
    def test_approved_in_sequence_changes_apply(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        self.assertEqual(replay["findings"], [])
        versions = {item["item_id"]: item["version"] for item in replay["as_built"]}
        self.assertEqual(versions["gse-handling-dolly"], 2)
        self.assertEqual(versions["gse-test-rack"], 4)

    def test_unapproved_change_is_refused_and_named(self):
        changes = [dict(CHANGES[0], approved=False)]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertIn("never approved", replay["findings"][0])
        self.assertEqual(replay["as_built"][0]["version"], 1)

    def test_out_of_sequence_change_is_refused(self):
        changes = [dict(CHANGES[0], from_version=2, to_version=3)]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertIn("starts from version 2", replay["findings"][0])

    def test_version_jump_is_refused(self):
        changes = [dict(CHANGES[0], to_version=5)]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertIn("instead of one increment", replay["findings"][0])

    def test_change_against_an_unbaselined_item_is_refused(self):
        changes = [dict(CHANGES[0], item_id="gse-unknown-jig")]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertIn("not in the GSE baseline", replay["findings"][0])

    def test_two_changes_on_one_item_chain(self):
        changes = [
            dict(CHANGES[0]),
            {"id": "ecr-3", "item_id": "gse-handling-dolly", "from_version": 2, "to_version": 3, "approved": True},
        ]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        versions = {item["item_id"]: item["version"] for item in replay["as_built"]}
        self.assertEqual(versions["gse-handling-dolly"], 3)

    def test_a_refused_change_does_not_advance_the_ones_after_it(self):
        changes = [
            dict(CHANGES[0], approved=False),
            {"id": "ecr-4", "item_id": "gse-handling-dolly", "from_version": 2, "to_version": 3, "approved": True},
        ]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertEqual(len(replay["refused"]), 2)
        self.assertEqual(replay["as_built"][0]["version"], 1)

    def test_every_refusal_is_reported_not_just_the_first(self):
        changes = [
            dict(CHANGES[0], approved=False),
            dict(CHANGES[1], item_id="gse-unknown-jig"),
        ]
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(changes))
        self.assertEqual(len(replay["findings"]), 2)


class RatioTests(unittest.TestCase):
    def test_all_applied_is_unity(self):
        self.assertAlmostEqual(applied_ratio(["a", "b"], []), 1.0, places=9)

    def test_half_applied(self):
        self.assertAlmostEqual(applied_ratio(["a"], ["b"]), 0.5, places=9)

    def test_empty_log_rejected(self):
        with self.assertRaises(ValueError):
            applied_ratio([], [])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            applied_ratio("a", [])

    def test_tolerance_is_small(self):
        self.assertLess(RATIO_TOLERANCE, 1e-6)


class DeclaredConfigurationTests(unittest.TestCase):
    def test_matching_declaration_is_clean(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        self.assertEqual(declared_configuration_findings(replay["as_built"], DECLARED), [])

    def test_version_mismatch_is_named(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        declared = [dict(DECLARED[0], version=1), dict(DECLARED[1])]
        findings = declared_configuration_findings(replay["as_built"], declared)
        self.assertIn("declared at version 1", findings[0])

    def test_unlisted_item_is_named(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        findings = declared_configuration_findings(replay["as_built"], [dict(DECLARED[0])])
        self.assertTrue(any("does not list" in f for f in findings))

    def test_extra_declared_item_is_named(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        declared = DECLARED + [{"item_id": "gse-spare-cart", "version": 1}]
        findings = declared_configuration_findings(replay["as_built"], declared)
        self.assertTrue(any("not a baselined GSE item" in f for f in findings))

    def test_duplicate_declared_item_rejected(self):
        replay = replay_changes(validate_baseline(BASELINE), validate_change_log(CHANGES))
        with self.assertRaises(ValueError):
            declared_configuration_findings(replay["as_built"], DECLARED + [dict(DECLARED[0])])


class AssessGseConfigurationTests(unittest.TestCase):
    def test_controlled_configuration_is_clean(self):
        result = assess_gse_configuration(_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["under_control"])
        self.assertAlmostEqual(result["applied_ratio"], 1.0, places=9)

    def test_unapproved_change_breaks_control(self):
        spec = _spec()
        spec["changes"][0]["approved"] = False
        result = assess_gse_configuration(spec)
        self.assertFalse(result["under_control"])
        self.assertAlmostEqual(result["applied_ratio"], 0.5, places=9)

    def test_missing_serial_breaks_control(self):
        spec = _spec()
        del spec["baseline"][0]["serial_number"]
        result = assess_gse_configuration(spec)
        self.assertFalse(result["under_control"])
        self.assertEqual(len(result["identification_findings"]), 1)

    def test_no_change_log_leaves_the_baseline_standing(self):
        spec = _spec(changes=None, declared=[{"item_id": i["item_id"], "version": i["version"]} for i in BASELINE])
        result = assess_gse_configuration(spec)
        self.assertIsNone(result["applied_ratio"])
        self.assertTrue(result["under_control"])

    def test_required_ratio_shortfall_is_a_finding(self):
        spec = _spec(required_applied_ratio=1.0)
        spec["changes"][1]["approved"] = False
        result = assess_gse_configuration(spec)
        self.assertTrue(any("reached the configuration" in f for f in result["ratio_findings"]))

    def test_required_ratio_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_configuration(_spec(required_applied_ratio=-0.5))

    def test_declaration_is_optional(self):
        spec = _spec()
        del spec["declared"]
        result = assess_gse_configuration(spec)
        self.assertEqual(result["declared_findings"], [])

    def test_missing_baseline_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_configuration({"changes": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_configuration(["baseline"])


if __name__ == "__main__":
    unittest.main()
