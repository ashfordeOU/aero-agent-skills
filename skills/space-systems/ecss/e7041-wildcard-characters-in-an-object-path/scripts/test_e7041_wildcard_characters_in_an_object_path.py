"""Contract tests for the clause 6.23.3.3 object path wildcard logic."""

import unittest

from e7041_wildcard_characters_in_an_object_path_logic import (
    DEFAULT_WILDCARD,
    MAX_COMPONENT_CHARS,
    MAX_PATH_COMPONENTS,
    PATH_SEPARATOR,
    assess_object_path_request,
    component_matches,
    expand_object_path,
    is_wildcard_component,
    path_matches,
    split_object_path,
    validate_wildcard,
    wildcard_component_count,
)

CANDIDATES = (
    "/repo1/housekeeping/hk001",
    "/repo1/housekeeping/hk002",
    "/repo1/events/ev001",
    "/repo2/housekeeping/hk001",
    "/repo1/housekeeping/archive/hk003",
)


class WildcardDeclarationTests(unittest.TestCase):
    def test_the_default_wildcard_is_accepted(self):
        self.assertEqual(validate_wildcard(), DEFAULT_WILDCARD)

    def test_a_declared_alternative_wildcard_is_accepted(self):
        self.assertEqual(validate_wildcard("?"), "?")

    def test_a_multi_character_wildcard_is_refused(self):
        with self.assertRaises(ValueError):
            validate_wildcard("**")

    def test_the_separator_cannot_be_the_wildcard(self):
        with self.assertRaises(ValueError):
            validate_wildcard(PATH_SEPARATOR)

    def test_a_name_character_cannot_be_the_wildcard(self):
        with self.assertRaises(ValueError):
            validate_wildcard("a")


class PathShapeTests(unittest.TestCase):
    def test_a_rooted_path_splits_into_its_components(self):
        self.assertEqual(
            split_object_path("/repo1/housekeeping/hk001"),
            ("repo1", "housekeeping", "hk001"),
        )

    def test_a_relative_path_splits_the_same_way(self):
        self.assertEqual(split_object_path("repo1/hk001"), ("repo1", "hk001"))

    def test_an_empty_path_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path("")

    def test_a_path_of_only_the_separator_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path(PATH_SEPARATOR)

    def test_a_trailing_separator_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path("/repo1/housekeeping/")

    def test_an_empty_component_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path("/repo1//hk001")

    def test_a_component_past_the_length_limit_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path("/repo1/" + "x" * (MAX_COMPONENT_CHARS + 1))

    def test_a_path_past_the_component_limit_is_refused(self):
        deep = PATH_SEPARATOR + PATH_SEPARATOR.join(
            "d%d" % i for i in range(MAX_PATH_COMPONENTS + 1)
        )
        with self.assertRaises(ValueError):
            split_object_path(deep)

    def test_a_padded_component_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path("/repo1/ hk001")

    def test_a_non_string_path_is_refused(self):
        with self.assertRaises(ValueError):
            split_object_path(17)


class ComponentMatchTests(unittest.TestCase):
    def test_a_lone_wildcard_is_a_wildcard_component(self):
        self.assertTrue(is_wildcard_component("*"))

    def test_a_literal_component_is_not_a_wildcard(self):
        self.assertFalse(is_wildcard_component("hk001"))

    def test_a_component_mixing_wildcard_and_literal_is_refused(self):
        with self.assertRaises(ValueError):
            is_wildcard_component("hk*")

    def test_a_wildcard_component_matches_any_name(self):
        self.assertTrue(component_matches("*", "anything"))

    def test_a_literal_component_matches_only_itself(self):
        self.assertTrue(component_matches("hk001", "hk001"))
        self.assertFalse(component_matches("hk001", "hk002"))

    def test_a_stored_name_carrying_the_wildcard_is_refused(self):
        with self.assertRaises(ValueError):
            component_matches("*", "hk*01")

    def test_an_empty_candidate_name_is_refused(self):
        with self.assertRaises(ValueError):
            component_matches("*", "")


class PathMatchTests(unittest.TestCase):
    def test_a_fully_qualified_path_matches_itself(self):
        self.assertTrue(
            path_matches("/repo1/housekeeping/hk001", "/repo1/housekeeping/hk001")
        )

    def test_a_wildcard_matches_one_component(self):
        self.assertTrue(path_matches("/repo1/housekeeping/*", "/repo1/housekeeping/hk002"))

    def test_a_wildcard_does_not_span_the_separator(self):
        self.assertFalse(
            path_matches("/repo1/*", "/repo1/housekeeping/hk001")
        )

    def test_a_deeper_candidate_is_not_matched_by_a_shorter_pattern(self):
        self.assertFalse(
            path_matches(
                "/repo1/housekeeping/*", "/repo1/housekeeping/archive/hk003"
            )
        )

    def test_a_wildcard_in_the_repository_position_crosses_repositories(self):
        self.assertTrue(path_matches("/*/housekeeping/hk001", "/repo2/housekeeping/hk001"))

    def test_an_alternative_declared_wildcard_is_honoured(self):
        self.assertTrue(
            path_matches("/repo1/housekeeping/?", "/repo1/housekeeping/hk001", "?")
        )

    def test_wildcard_components_are_counted(self):
        self.assertEqual(wildcard_component_count("/*/housekeeping/*"), 2)
        self.assertEqual(wildcard_component_count("/repo1/housekeeping/hk001"), 0)


class ExpansionTests(unittest.TestCase):
    def test_expansion_returns_every_match_in_order(self):
        matches = expand_object_path("/repo1/housekeeping/*", CANDIDATES)
        self.assertEqual(
            matches, ("/repo1/housekeeping/hk001", "/repo1/housekeeping/hk002")
        )

    def test_a_fully_qualified_pattern_expands_to_one_object(self):
        self.assertEqual(
            expand_object_path("/repo1/events/ev001", CANDIDATES),
            ("/repo1/events/ev001",),
        )

    def test_an_unmatched_pattern_expands_to_nothing(self):
        self.assertEqual(expand_object_path("/repo3/*/*", CANDIDATES), ())

    def test_candidates_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            expand_object_path("/repo1/*/*", "/repo1/events/ev001")


class RequestTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {"pattern": "/repo1/events/ev001", "candidates": list(CANDIDATES)}
        spec.update(over)
        return spec

    def test_a_single_object_operation_on_one_match_is_accepted(self):
        result = assess_object_path_request(self._spec())
        self.assertTrue(result["accepted"])
        self.assertTrue(result["fully_qualified"])
        self.assertEqual(result["match_count"], 1)

    def test_a_single_object_operation_on_many_matches_is_rejected(self):
        result = assess_object_path_request(self._spec(pattern="/repo1/housekeeping/*"))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["match_count"], 2)

    def test_a_fan_out_operation_accepts_many_matches(self):
        result = assess_object_path_request(
            self._spec(pattern="/repo1/housekeeping/*", single_object_operation=False)
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["match_count"], 2)

    def test_a_fan_out_past_its_limit_is_rejected(self):
        result = assess_object_path_request(
            self._spec(
                pattern="/repo1/housekeeping/*",
                single_object_operation=False,
                fan_out_limit=1,
            )
        )
        self.assertFalse(result["accepted"])

    def test_an_unmatched_path_is_rejected(self):
        result = assess_object_path_request(self._spec(pattern="/repo9/*/*"))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("no object" in f for f in result["findings"]))

    def test_a_wildcard_resolving_to_one_object_is_flagged(self):
        result = assess_object_path_request(self._spec(pattern="/repo1/events/*"))
        self.assertTrue(result["accepted"])
        self.assertFalse(result["clean"])

    def test_a_mixed_component_in_the_pattern_is_refused(self):
        with self.assertRaises(ValueError):
            assess_object_path_request(self._spec(pattern="/repo1/housekeeping/hk*"))

    def test_a_non_boolean_operation_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_object_path_request(self._spec(single_object_operation="yes"))

    def test_a_zero_fan_out_limit_is_refused(self):
        with self.assertRaises(ValueError):
            assess_object_path_request(
                self._spec(single_object_operation=False, fan_out_limit=0)
            )

    def test_missing_spec_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_object_path_request({"pattern": "/repo1/events/ev001"})

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_object_path_request(["pattern"])


if __name__ == "__main__":
    unittest.main()
