#!/usr/bin/env python3
"""Contract test for the external protection diode acceptance programme.

Walks the clause workflow step by step: the table lookup, the build
configuration validation, the mandatory and conditional resolution, the
optional admissibility rule, the duplicate and untabulated refusals, the
covered share against the declared minimum, the relative ordering grade
and the roll-up into one programme verdict. Offline, stdlib only. This
is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_external_diode_acceptance_tests_logic import (
    CONDITIONAL,
    CONDITION_TOKENS,
    DEFAULT_PROGRAMME_POLICY,
    MANDATORY,
    OPTIONAL,
    PROGRAMME_COMPLETE,
    PROGRAMME_INCOMPLETE,
    TABULATED_TESTS,
    TEST_TABLE,
    admissible_tests,
    assess_external_diode_programme,
    build_programme,
    grade_coverage,
    grade_sequence,
    lookup_test,
    required_tests,
    resolve_policy,
    validate_configuration,
    validate_programme,
)

BONDED = "external-diode-bonded-to-substrate"
WIRED = "external-diode-wire-terminated"
OPTIONAL_ROW = "external-diode-humidity-exposure"


def _config(conditions=(BONDED,), declared_optional=(), build_id="BUILD-9"):
    return {
        "build_id": build_id,
        "conditions": list(conditions),
        "declared_optional": list(declared_optional),
    }


def _case(configuration=None, programme=None, **extra):
    configuration = configuration or _config()
    case = {
        "programme_id": "PRG-943",
        "configuration": configuration,
        "programme": programme
        if programme is not None
        else build_programme(configuration),
    }
    case.update(copy.deepcopy(extra))
    return case


class TableTests(unittest.TestCase):
    def test_every_row_carries_a_known_standing(self):
        for row in TEST_TABLE:
            self.assertIn(row["standing"], (MANDATORY, CONDITIONAL, OPTIONAL))

    def test_a_conditional_row_carries_a_condition_token(self):
        for row in TEST_TABLE:
            if row["standing"] == CONDITIONAL:
                self.assertIn(row["condition"], CONDITION_TOKENS)
            else:
                self.assertIsNone(row["condition"])

    def test_lookup_returns_the_row(self):
        row = lookup_test("external-diode-visual-inspection")
        self.assertEqual(row["standing"], MANDATORY)
        self.assertEqual(row["order"], 1)

    def test_a_test_outside_the_table_rejected(self):
        with self.assertRaises(ValueError):
            lookup_test("external-diode-launch-rehearsal")

    def test_a_blank_test_name_rejected(self):
        with self.assertRaises(ValueError):
            lookup_test("  ")


class ConfigurationTests(unittest.TestCase):
    def test_a_sound_configuration_validates(self):
        resolved = validate_configuration(_config())
        self.assertEqual(resolved["conditions"], [BONDED])
        self.assertEqual(resolved["findings"], [])

    def test_an_unreferenced_condition_is_reported_not_dropped(self):
        resolved = validate_configuration(_config(conditions=(BONDED, "riveted")))
        self.assertEqual(resolved["unreferenced_conditions"], ["riveted"])
        self.assertTrue(resolved["findings"])

    def test_a_condition_declared_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration(_config(conditions=(BONDED, BONDED)))

    def test_a_mandatory_row_cannot_be_declared_optional(self):
        with self.assertRaises(ValueError):
            validate_configuration(
                _config(declared_optional=("external-diode-visual-inspection",))
            )

    def test_a_blank_build_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration(_config(build_id="   "))


class ResolutionTests(unittest.TestCase):
    def test_every_mandatory_row_is_always_required(self):
        required = required_tests(_config(conditions=()))
        mandatory = [r["test"] for r in TEST_TABLE if r["standing"] == MANDATORY]
        self.assertEqual(required, mandatory)

    def test_a_raised_conditional_row_joins_the_required_set(self):
        self.assertIn(
            "external-diode-thermal-endurance-run", required_tests(_config())
        )

    def test_an_unraised_conditional_row_stays_out(self):
        self.assertNotIn(
            "external-diode-terminal-strength-pull", required_tests(_config())
        )

    def test_an_optional_row_is_admissible_only_once_declared(self):
        self.assertNotIn(OPTIONAL_ROW, admissible_tests(_config()))
        self.assertIn(
            OPTIONAL_ROW,
            admissible_tests(_config(declared_optional=(OPTIONAL_ROW,))),
        )


class ProgrammeValidationTests(unittest.TestCase):
    def test_a_duplicate_entry_rejected(self):
        programme = build_programme(_config())
        programme.append({"test": programme[0]["test"], "position": 99})
        with self.assertRaises(ValueError):
            validate_programme(programme)

    def test_two_entries_sharing_a_position_rejected(self):
        programme = build_programme(_config())
        programme[1]["position"] = programme[0]["position"]
        with self.assertRaises(ValueError):
            validate_programme(programme)

    def test_a_non_integer_position_rejected(self):
        programme = build_programme(_config())
        programme[0]["position"] = "first"
        with self.assertRaises(ValueError):
            validate_programme(programme)

    def test_an_empty_programme_rejected(self):
        with self.assertRaises(ValueError):
            validate_programme([])


class CoverageTests(unittest.TestCase):
    def test_a_drawn_programme_covers_its_required_set(self):
        configuration = _config()
        result = grade_coverage(build_programme(configuration), configuration)
        self.assertEqual(result["missing"], [])
        self.assertAlmostEqual(result["covered_share"], 1.0, places=9)
        self.assertTrue(result["meets_covered_share"])

    def test_a_dropped_mandatory_row_is_a_gap(self):
        configuration = _config()
        programme = [
            e
            for e in build_programme(configuration)
            if e["test"] != "external-diode-dimensional-check"
        ]
        result = grade_coverage(programme, configuration)
        self.assertEqual(result["missing"], ["external-diode-dimensional-check"])
        self.assertFalse(result["meets_covered_share"])

    def test_a_partial_share_is_reported_exactly(self):
        configuration = _config(conditions=())
        programme = build_programme(configuration)[:3]
        result = grade_coverage(programme, configuration, {"min_covered_share": 0.5})
        self.assertAlmostEqual(result["covered_share"], 3.0 / 5.0, places=9)
        self.assertTrue(result["meets_covered_share"])

    def test_an_untabulated_test_is_unagreed_scope(self):
        configuration = _config()
        programme = build_programme(configuration)
        programme.append(
            {"test": "external-diode-salt-fog-soak", "position": 40}
        )
        result = grade_coverage(programme, configuration)
        self.assertEqual(result["untabulated"], ["external-diode-salt-fog-soak"])

    def test_an_undeclared_optional_row_is_inadmissible(self):
        configuration = _config()
        programme = build_programme(configuration)
        programme.append({"test": OPTIONAL_ROW, "position": 41})
        result = grade_coverage(programme, configuration)
        self.assertEqual(result["inadmissible"], [OPTIONAL_ROW])


class SequenceTests(unittest.TestCase):
    def test_a_drawn_programme_is_in_tabulated_order(self):
        result = grade_sequence(build_programme(_config()))
        self.assertTrue(result["in_tabulated_order"])
        self.assertEqual(result["inversions"], [])

    def test_an_inverted_pair_is_reported(self):
        programme = build_programme(_config())
        first, second = programme[0]["test"], programme[1]["test"]
        programme[0]["test"], programme[1]["test"] = second, first
        result = grade_sequence(programme)
        self.assertFalse(result["in_tabulated_order"])
        self.assertIn((second, first), result["inversions"])

    def test_an_untabulated_entry_is_set_aside_not_ordered(self):
        programme = build_programme(_config())
        programme.append({"test": "external-diode-salt-fog-soak", "position": 30})
        result = grade_sequence(programme)
        self.assertEqual(result["untabulated"], ["external-diode-salt-fog-soak"])
        self.assertTrue(result["in_tabulated_order"])

    def test_a_gap_in_positions_is_not_an_ordering_break(self):
        programme = build_programme(_config())
        for index, entry in enumerate(programme):
            entry["position"] = 1 + index * 7
        self.assertTrue(grade_sequence(programme)["in_tabulated_order"])


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(
            settings["min_covered_share"],
            DEFAULT_PROGRAMME_POLICY["min_covered_share"],
            places=9,
        )
        self.assertFalse(settings["allow_untabulated_tests"])

    def test_a_non_boolean_untabulated_policy_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"allow_untabulated_tests": "maybe"})

    def test_a_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_covered_share": 1.2})


class RollUpTests(unittest.TestCase):
    def test_a_drawn_programme_is_complete(self):
        result = assess_external_diode_programme(_case())
        self.assertEqual(result["verdict"], PROGRAMME_COMPLETE)
        self.assertEqual(result["findings"], [])

    def test_a_gap_blocks_the_programme(self):
        configuration = _config()
        programme = [
            e
            for e in build_programme(configuration)
            if e["test"] != "external-diode-final-electrical-verification"
        ]
        result = assess_external_diode_programme(
            _case(configuration, programme)
        )
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)
        self.assertTrue(result["findings"])

    def test_an_ordering_break_blocks_the_programme(self):
        configuration = _config()
        programme = build_programme(configuration)
        programme[0]["test"], programme[-1]["test"] = (
            programme[-1]["test"],
            programme[0]["test"],
        )
        result = assess_external_diode_programme(_case(configuration, programme))
        self.assertEqual(result["verdict"], PROGRAMME_INCOMPLETE)

    def test_an_untabulated_entry_can_be_carried_by_policy(self):
        configuration = _config()
        programme = build_programme(configuration)
        programme.append({"test": "external-diode-salt-fog-soak", "position": 60})
        strict = assess_external_diode_programme(_case(configuration, programme))
        self.assertEqual(strict["verdict"], PROGRAMME_INCOMPLETE)
        carried = _case(
            configuration, programme, policy={"allow_untabulated_tests": True}
        )
        self.assertEqual(
            assess_external_diode_programme(carried)["verdict"],
            PROGRAMME_COMPLETE,
        )

    def test_every_tabulated_test_name_is_unique(self):
        self.assertEqual(len(set(TABULATED_TESTS)), len(TABULATED_TESTS))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_external_diode_programme("the programme was drawn from the table")


if __name__ == "__main__":
    unittest.main()
