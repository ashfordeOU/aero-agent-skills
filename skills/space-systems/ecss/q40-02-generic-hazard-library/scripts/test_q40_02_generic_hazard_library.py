"""Contract test for the q40-02-generic-hazard-library leaf (stdlib unittest)."""

import unittest

from q40_02_generic_hazard_library_logic import (
    GENERIC_HAZARD_LIBRARY,
    REGISTER_RECORD_FIELDS,
    call_strength,
    grade_register,
    hazard_groups,
    known_characteristics,
    seed_and_grade,
    seed_candidates,
    uncalled_groups,
    validate_characteristics,
    validate_register_record,
)


def record(hid="HZ-1", group="stored-pressure-energy-release", **kw):
    rec = {
        "hazard_id": hid,
        "hazard_group": group,
        "cause": "overpressure of the storage vessel above its design limit",
        "effect": "vessel rupture releasing fragments into the surrounding bay",
        "control": "relief device sized for the worst credible inflow rate",
        "verification_reference": "HR-1-VER-011",
    }
    rec.update(kw)
    return rec


class TestLibraryShape(unittest.TestCase):
    def test_library_is_not_empty(self):
        self.assertGreaterEqual(len(GENERIC_HAZARD_LIBRARY), 12)

    def test_every_group_keys_on_at_least_one_characteristic(self):
        for group, keys in GENERIC_HAZARD_LIBRARY.items():
            self.assertTrue(keys, "group %s keys on nothing" % group)

    def test_hazard_groups_are_sorted(self):
        self.assertEqual(hazard_groups(), sorted(GENERIC_HAZARD_LIBRARY))

    def test_known_characteristics_are_unique_and_sorted(self):
        known = known_characteristics()
        self.assertEqual(known, sorted(set(known)))

    def test_a_characteristic_can_call_several_groups(self):
        calling = [
            g for g, keys in GENERIC_HAZARD_LIBRARY.items()
            if "high-energy-battery" in keys
        ]
        self.assertGreaterEqual(len(calling), 2)


class TestValidateCharacteristics(unittest.TestCase):
    def test_sorts_and_deduplicates(self):
        out = validate_characteristics(
            ["pyrotechnic-device", "crew-compartment", "pyrotechnic-device"]
        )
        self.assertEqual(out, ["crew-compartment", "pyrotechnic-device"])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristics([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristics("crew-compartment")

    def test_unknown_characteristic_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristics(["warp-core"])

    def test_blank_characteristic_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristics(["   "])


class TestCallStrength(unittest.TestCase):
    def test_all_keys_present_is_full_strength(self):
        keys = list(GENERIC_HAZARD_LIBRARY["cryogenic-contact-and-embrittlement"])
        self.assertAlmostEqual(
            call_strength("cryogenic-contact-and-embrittlement", keys), 1.0, places=9
        )

    def test_one_of_three_keys_is_a_third(self):
        strength = call_strength(
            "stored-pressure-energy-release", ["pressurized-vessel"]
        )
        self.assertAlmostEqual(strength, 1.0 / 3.0, places=9)

    def test_no_key_present_is_zero(self):
        self.assertAlmostEqual(
            call_strength("crew-injury-and-habitability-loss", ["laser-payload"]),
            0.0,
            places=9,
        )

    def test_unknown_group_raises(self):
        with self.assertRaises(ValueError):
            call_strength("bad-vibes", ["laser-payload"])


class TestSeeding(unittest.TestCase):
    def test_a_characteristic_seeds_its_group(self):
        groups = [c["hazard_group"] for c in seed_candidates(["pyrotechnic-device"])]
        self.assertIn("pyrotechnic-initiation", groups)

    def test_candidates_are_ranked_by_call_strength(self):
        candidates = seed_candidates(
            ["cryogenic-fluid", "cryogenic-feed-line", "pressurized-vessel"]
        )
        strengths = [c["call_strength"] for c in candidates]
        self.assertEqual(strengths, sorted(strengths, reverse=True))
        self.assertEqual(
            candidates[0]["hazard_group"], "cryogenic-contact-and-embrittlement"
        )

    def test_matched_characteristics_are_reported(self):
        candidates = seed_candidates(["high-energy-battery"])
        battery = [
            c for c in candidates if c["hazard_group"] == "battery-thermal-runaway"
        ][0]
        self.assertEqual(battery["matched_characteristics"], ["high-energy-battery"])

    def test_uncalled_groups_complement_the_candidates(self):
        chars = ["laser-payload"]
        called = {c["hazard_group"] for c in seed_candidates(chars)}
        uncalled = set(uncalled_groups(chars))
        self.assertEqual(called & uncalled, set())
        self.assertEqual(called | uncalled, set(hazard_groups()))

    def test_one_characteristic_leaves_most_groups_uncalled(self):
        self.assertGreater(len(uncalled_groups(["laser-payload"])), 5)


class TestRegisterGrading(unittest.TestCase):
    def test_complete_record_is_clean(self):
        self.assertEqual(validate_register_record(record())["findings"], [])

    def test_each_missing_field_is_named(self):
        result = validate_register_record({})
        self.assertEqual(len(result["findings"]), len(REGISTER_RECORD_FIELDS))
        self.assertIn("register-record-missing:cause", result["findings"])

    def test_blank_field_counts_as_missing(self):
        result = validate_register_record(record(control="  "))
        self.assertEqual(result["findings"], ["register-record-missing:control"])

    def test_group_outside_the_library_is_a_finding(self):
        result = validate_register_record(record(hazard_group="general-unease"))
        self.assertIn(
            "register-record-group-outside-library:general-unease", result["findings"]
        )

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_register_record(["HZ-1"])

    def test_register_with_a_gap_is_incomplete(self):
        graded = grade_register([record("HZ-1"), record("HZ-2", effect="")])
        self.assertFalse(graded["complete"])
        self.assertEqual(graded["incomplete_ids"], ["HZ-2"])

    def test_duplicate_register_id_raises(self):
        with self.assertRaises(ValueError):
            grade_register([record("HZ-1"), record("HZ-1")])

    def test_empty_register_raises(self):
        with self.assertRaises(ValueError):
            grade_register([])


class TestSeedAndGrade(unittest.TestCase):
    def test_registered_candidate_leaves_no_gap(self):
        result = seed_and_grade(["pressurized-vessel"], [record("HZ-1")])
        self.assertEqual(result["unregistered_candidates"], [])
        self.assertTrue(result["seeded"])

    def test_unregistered_candidate_is_a_finding(self):
        result = seed_and_grade(
            ["pressurized-vessel", "pyrotechnic-device"], [record("HZ-1")]
        )
        self.assertIn("pyrotechnic-initiation", result["unregistered_candidates"])
        self.assertIn(
            "seeded-candidate-not-in-register:pyrotechnic-initiation",
            result["findings"],
        )
        self.assertFalse(result["seeded"])

    def test_record_findings_reach_the_verdict(self):
        result = seed_and_grade(
            ["pressurized-vessel"], [record("HZ-1", verification_reference="")]
        )
        self.assertIn(
            "register-record-missing:verification_reference:HZ-1", result["findings"]
        )

    def test_uncalled_groups_travel_with_the_result(self):
        result = seed_and_grade(["pressurized-vessel"], [record("HZ-1")])
        self.assertIn("crew-injury-and-habitability-loss", result["uncalled_groups"])

    def test_candidates_travel_with_the_result(self):
        result = seed_and_grade(["pressurized-vessel"], [record("HZ-1")])
        self.assertTrue(result["candidates"])
        self.assertAlmostEqual(
            result["candidates"][0]["call_strength"], 1.0 / 3.0, places=9
        )


if __name__ == "__main__":
    unittest.main()
