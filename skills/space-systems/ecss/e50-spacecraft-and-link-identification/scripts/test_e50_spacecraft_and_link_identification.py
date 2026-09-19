"""Contract tests for the clause 5.6.13.1 spacecraft and link identification logic."""

import unittest

from e50_spacecraft_and_link_identification_logic import (
    IDENTIFICATION_AMBIGUOUS,
    IDENTIFICATION_UNAMBIGUOUS,
    assess_identification,
    free_identifiers,
    identifier_capacity,
    identifier_field_width,
    link_identity,
    next_free_identifier,
    normalize_link,
    normalize_spacecraft,
    reserved_identifier,
    validate_direction,
    validate_frame_version,
    validate_spacecraft_id,
)

CRAFT = [
    {"name": "orbiter", "frame_version": "tm-version-1", "spacecraft_id": 42},
    {"name": "lander", "frame_version": "tm-version-1", "spacecraft_id": 43},
]

LINKS = [
    {
        "name": "orbiter-return-x",
        "spacecraft": "orbiter",
        "direction": "return",
        "physical_channel": "x-band-rf",
    },
    {
        "name": "orbiter-forward-s",
        "spacecraft": "orbiter",
        "direction": "forward",
        "physical_channel": "s-band-rf",
    },
    {
        "name": "lander-return-uhf",
        "spacecraft": "lander",
        "direction": "return",
        "physical_channel": "uhf-proximity",
    },
]


class FrameVersionTests(unittest.TestCase):
    def test_known_frame_version_accepted(self):
        self.assertEqual(validate_frame_version("TM-Version-1"), "tm-version-1")

    def test_unknown_frame_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_frame_version("tm-version-9")

    def test_blank_frame_version_rejected(self):
        with self.assertRaises(ValueError):
            validate_frame_version("   ")

    def test_field_width_follows_the_frame_version(self):
        self.assertEqual(identifier_field_width("tm-version-1"), 10)
        self.assertEqual(identifier_field_width("aos-version-2"), 8)

    def test_capacity_reserves_the_all_ones_pattern(self):
        capacity = identifier_capacity("tm-version-1")
        self.assertEqual(capacity["total"], 1024)
        self.assertEqual(capacity["reserved"], 1023)
        self.assertEqual(capacity["assignable"], 1023)

    def test_reserved_identifier_is_the_all_ones_value(self):
        self.assertEqual(reserved_identifier("aos-version-2"), 255)


class SpacecraftIdTests(unittest.TestCase):
    def test_identifier_inside_the_field_accepted(self):
        self.assertEqual(validate_spacecraft_id(42, "tm-version-1"), 42)

    def test_zero_identifier_accepted(self):
        self.assertEqual(validate_spacecraft_id(0, "tm-version-1"), 0)

    def test_identifier_beyond_the_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_spacecraft_id(1024, "tm-version-1")

    def test_identifier_that_fits_one_version_and_not_another(self):
        self.assertEqual(validate_spacecraft_id(300, "tm-version-1"), 300)
        with self.assertRaises(ValueError):
            validate_spacecraft_id(300, "aos-version-2")

    def test_reserved_pattern_rejected(self):
        with self.assertRaises(ValueError):
            validate_spacecraft_id(1023, "tm-version-1")

    def test_negative_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_spacecraft_id(-1, "tm-version-1")

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_spacecraft_id(True, "tm-version-1")

    def test_float_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_spacecraft_id(42.0, "tm-version-1")


class DirectionAndNormalisationTests(unittest.TestCase):
    def test_direction_is_lowercased(self):
        self.assertEqual(validate_direction("Return"), "return")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            validate_direction("crosslink")

    def test_spacecraft_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_spacecraft({"name": "orbiter", "frame_version": "tm-version-1"})

    def test_link_without_a_channel_rejected(self):
        with self.assertRaises(ValueError):
            normalize_link(
                {"name": "a", "spacecraft": "orbiter", "direction": "return"}
            )

    def test_link_identity_is_craft_direction_and_channel(self):
        self.assertEqual(
            link_identity(LINKS[0]), ("orbiter", "return", "x-band-rf")
        )

    def test_normalised_spacecraft_keeps_its_identifier(self):
        self.assertEqual(normalize_spacecraft(CRAFT[0])["spacecraft_id"], 42)


class FreeIdentifierTests(unittest.TestCase):
    def test_lowest_free_identifier_is_offered(self):
        self.assertEqual(next_free_identifier("tm-version-1", [0, 1, 2]), 3)

    def test_free_identifiers_skip_the_assigned_ones(self):
        free = free_identifiers("tm-version-1", [0, 2], limit=3)
        self.assertEqual(free, [1, 3, 4])

    def test_the_reserved_pattern_is_never_offered(self):
        assigned = list(range(1023))
        with self.assertRaises(ValueError):
            next_free_identifier("tm-version-1", assigned)

    def test_an_exhausted_namespace_offers_nothing(self):
        assigned = list(range(255))
        self.assertEqual(free_identifiers("aos-version-2", assigned), [])

    def test_non_integer_assignment_rejected(self):
        with self.assertRaises(ValueError):
            free_identifiers("tm-version-1", ["42"])

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            free_identifiers("tm-version-1", [], limit=0)


class AssessIdentificationTests(unittest.TestCase):
    def test_a_sound_design_is_unambiguous(self):
        result = assess_identification(CRAFT, LINKS)
        self.assertEqual(result["verdict"], IDENTIFICATION_UNAMBIGUOUS)
        self.assertTrue(result["unambiguous"])

    def test_counts_are_reported(self):
        result = assess_identification(CRAFT, LINKS)
        self.assertEqual(result["spacecraft_count"], 2)
        self.assertEqual(result["link_count"], 3)

    def test_identifier_collision_is_caught(self):
        craft = CRAFT + [
            {"name": "probe", "frame_version": "tm-version-1", "spacecraft_id": 42}
        ]
        result = assess_identification(craft, LINKS)
        self.assertEqual(len(result["identifier_collisions"]), 1)
        self.assertEqual(result["verdict"], IDENTIFICATION_AMBIGUOUS)

    def test_the_same_number_in_two_namespaces_is_not_a_collision(self):
        craft = CRAFT + [
            {"name": "probe", "frame_version": "aos-version-2", "spacecraft_id": 42}
        ]
        result = assess_identification(craft, LINKS)
        self.assertEqual(result["identifier_collisions"], [])
        self.assertTrue(result["unambiguous"])

    def test_two_links_sharing_one_identity_are_caught(self):
        links = LINKS + [
            {
                "name": "orbiter-return-x-backup",
                "spacecraft": "orbiter",
                "direction": "return",
                "physical_channel": "x-band-rf",
            }
        ]
        result = assess_identification(CRAFT, links)
        self.assertEqual(len(result["link_identity_collisions"]), 1)
        self.assertFalse(result["unambiguous"])

    def test_a_different_channel_makes_two_links_distinguishable(self):
        links = LINKS + [
            {
                "name": "orbiter-return-ka",
                "spacecraft": "orbiter",
                "direction": "return",
                "physical_channel": "ka-band-rf",
            }
        ]
        result = assess_identification(CRAFT, links)
        self.assertEqual(result["link_identity_collisions"], [])
        self.assertTrue(result["unambiguous"])

    def test_link_naming_an_undeclared_spacecraft_is_caught(self):
        links = LINKS + [
            {
                "name": "ghost-return",
                "spacecraft": "rover",
                "direction": "return",
                "physical_channel": "uhf-proximity",
            }
        ]
        result = assess_identification(CRAFT, links)
        self.assertEqual(result["links_with_undeclared_spacecraft"], ["ghost-return"])

    def test_duplicate_link_name_is_caught(self):
        links = LINKS + [dict(LINKS[0], physical_channel="ka-band-rf")]
        result = assess_identification(CRAFT, links)
        self.assertEqual(result["duplicate_link_names"], ["orbiter-return-x"])

    def test_namespace_headroom_is_reported(self):
        result = assess_identification(CRAFT, LINKS)
        headroom = result["namespace_headroom"]["tm-version-1"]
        self.assertEqual(headroom["assigned"], 2)
        self.assertEqual(headroom["remaining"], 1021)

    def test_findings_name_the_colliding_spacecraft(self):
        craft = CRAFT + [
            {"name": "probe", "frame_version": "tm-version-1", "spacecraft_id": 42}
        ]
        result = assess_identification(craft, LINKS)
        self.assertTrue(any("orbiter" in f and "probe" in f for f in result["findings"]))

    def test_a_mission_with_no_links_is_still_assessed(self):
        result = assess_identification(CRAFT, [])
        self.assertEqual(result["link_count"], 0)
        self.assertTrue(result["unambiguous"])

    def test_empty_spacecraft_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification([], LINKS)

    def test_non_list_spacecraft_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification(CRAFT[0], LINKS)

    def test_non_list_link_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_identification(CRAFT, LINKS[0])


if __name__ == "__main__":
    unittest.main()
