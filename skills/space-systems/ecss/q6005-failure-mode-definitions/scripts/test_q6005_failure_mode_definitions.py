#!/usr/bin/env python3
"""Gate 3 contract test for q6005-failure-mode-definitions.

Offline, stdlib unittest. Exercises the failure mode catalogue, the intrinsic
versus extrinsic split, the evidenced-attribution rule, the handling of an
uncatalogued mode and the charged tally of ECSS-Q-ST-60-05C clause 10.4.1 as
paraphrased in the logic module. Counts are integers throughout, so the
assertions compare them exactly; no float bound is asserted from a side.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_failure_mode_definitions_logic import (  # noqa: E402
    FAILURE_MODES,
    UNATTRIBUTED_GROUP,
    charged_count,
    is_chargeable,
    mode_group,
    mode_is_intrinsic,
    normalize_mode,
    tally_failures,
    unknown_modes,
    validate_observations,
)


def observation(mode="wire-bond-lift", count=1, evidenced=False):
    return {"mode": mode, "count": count, "attribution_evidenced": evidenced}


class CatalogueTests(unittest.TestCase):
    def test_catalogue_places_every_mode_in_a_group(self):
        for mode, (group, intrinsic) in FAILURE_MODES.items():
            self.assertTrue(group)
            self.assertIsInstance(intrinsic, bool)
            self.assertEqual(normalize_mode(mode), mode)

    def test_assembly_mode_is_intrinsic_to_the_product(self):
        self.assertTrue(mode_is_intrinsic("wire-bond-lift"))
        self.assertEqual(mode_group("wire-bond-lift"), "interconnection")

    def test_hermeticity_mode_is_intrinsic(self):
        self.assertTrue(mode_is_intrinsic("seal-gross-leak"))
        self.assertEqual(mode_group("loose-particle"), "hermeticity")

    def test_test_environment_mode_is_extrinsic(self):
        self.assertFalse(mode_is_intrinsic("test-equipment-fault"))
        self.assertEqual(mode_group("test-socket-contact-failure"), "test-environment")

    def test_post_process_handling_mode_is_extrinsic(self):
        self.assertFalse(mode_is_intrinsic("handling-damage-after-screening"))

    def test_mode_names_are_matched_case_and_separator_insensitively(self):
        self.assertEqual(normalize_mode("  Die_Attach  Void "), "die-attach-void")
        self.assertEqual(mode_group("DIE ATTACH VOID"), "element-attachment")

    def test_uncatalogued_mode_lookup_is_refused(self):
        with self.assertRaises(ValueError):
            mode_group("lid-discolouration")
        with self.assertRaises(ValueError):
            mode_is_intrinsic("lid-discolouration")

    def test_blank_or_non_string_mode_is_refused(self):
        for bad in ("", "   ", 17, None):
            with self.assertRaises(ValueError):
                normalize_mode(bad)


class ChargeabilityTests(unittest.TestCase):
    def test_intrinsic_mode_always_counts(self):
        self.assertTrue(is_chargeable("die-crack"))
        self.assertTrue(is_chargeable("die-crack", attribution_evidenced=True))

    def test_extrinsic_mode_counts_until_the_attribution_is_evidenced(self):
        self.assertTrue(is_chargeable("test-equipment-fault"))
        self.assertFalse(is_chargeable("test-equipment-fault", attribution_evidenced=True))

    def test_uncatalogued_mode_counts_rather_than_being_dropped(self):
        self.assertTrue(is_chargeable("lid-discolouration"))
        self.assertTrue(is_chargeable("lid-discolouration", attribution_evidenced=True))

    def test_non_boolean_evidence_flag_is_refused(self):
        with self.assertRaises(ValueError):
            is_chargeable("die-crack", attribution_evidenced="yes")


class ObservationValidationTests(unittest.TestCase):
    def test_mapping_is_not_a_sequence_of_observations(self):
        with self.assertRaises(ValueError):
            validate_observations({"mode": "die-crack", "count": 1})

    def test_observation_without_a_mode_is_refused(self):
        with self.assertRaises(ValueError):
            validate_observations([{"count": 2}])

    def test_non_positive_count_is_refused(self):
        for bad in (0, -3):
            with self.assertRaises(ValueError):
                validate_observations([observation(count=bad)])

    def test_boolean_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_observations([observation(count=True)])

    def test_count_defaults_to_one_unit(self):
        self.assertEqual(validate_observations([{"mode": "die-crack"}])[0]["count"], 1)

    def test_empty_observation_set_is_allowed_and_tallies_to_zero(self):
        self.assertEqual(validate_observations([]), [])
        self.assertEqual(charged_count([]), 0)

    def test_uncatalogued_mode_is_grouped_as_unattributed(self):
        record = validate_observations([observation(mode="lid-discolouration")])[0]
        self.assertEqual(record["group"], UNATTRIBUTED_GROUP)
        self.assertFalse(record["catalogued"])
        self.assertIsNone(record["intrinsic"])

    def test_unknown_modes_are_reported_once_each(self):
        observations = [
            observation(mode="lid-discolouration"),
            observation(mode="lid discolouration"),
            observation(mode="die-crack"),
        ]
        self.assertEqual(unknown_modes(observations), ["lid-discolouration"])


class TallyTests(unittest.TestCase):
    def test_intrinsic_failures_all_land_in_the_charged_total(self):
        observations = [observation(mode="wire-bond-lift", count=3),
                        observation(mode="seal-fine-leak", count=2)]
        result = tally_failures(observations)
        self.assertEqual(result["observed_failures"], 5)
        self.assertEqual(result["charged_failures"], 5)
        self.assertEqual(result["excused_failures"], 0)

    def test_evidenced_extrinsic_failure_leaves_the_charged_total(self):
        observations = [observation(mode="die-crack", count=2),
                        observation(mode="test-socket-contact-failure", count=4, evidenced=True)]
        result = tally_failures(observations)
        self.assertEqual(result["observed_failures"], 6)
        self.assertEqual(result["charged_failures"], 2)
        self.assertEqual(result["excused"], [{"mode": "test-socket-contact-failure", "count": 4}])

    def test_unevidenced_extrinsic_failure_stays_charged_and_is_flagged(self):
        result = tally_failures([observation(mode="test-equipment-fault", count=4)])
        self.assertEqual(result["charged_failures"], 4)
        self.assertTrue(any("no failure analysis" in f for f in result["findings"]))

    def test_uncatalogued_mode_is_charged_and_flagged(self):
        result = tally_failures([observation(mode="lid-discolouration", count=2)])
        self.assertEqual(result["charged_failures"], 2)
        self.assertEqual(result["uncatalogued_modes"], ["lid-discolouration"])
        self.assertTrue(any("uncatalogued" in f for f in result["findings"]))

    def test_charged_totals_are_grouped_largest_group_first(self):
        observations = [
            observation(mode="wire-bond-lift", count=2),
            observation(mode="die-attach-void", count=5),
            observation(mode="die-crack", count=1),
        ]
        result = tally_failures(observations)
        self.assertEqual(result["charged_by_group"][0], ("element-attachment", 6))
        self.assertEqual(result["charged_by_mode"][0], ("die-attach-void", 5))

    def test_the_same_mode_recorded_twice_accumulates(self):
        observations = [observation(mode="die-crack", count=2),
                        observation(mode="DIE CRACK", count=3)]
        self.assertEqual(tally_failures(observations)["charged_by_mode"], [("die-crack", 5)])

    def test_charged_count_matches_the_tally(self):
        observations = [
            observation(mode="wire-bond-neck-break", count=2),
            observation(mode="test-program-error", count=7, evidenced=True),
        ]
        self.assertEqual(charged_count(observations), tally_failures(observations)["charged_failures"])
        self.assertEqual(charged_count(observations), 2)

    def test_a_clean_lot_has_nothing_to_charge_and_no_findings(self):
        result = tally_failures([])
        self.assertEqual(result["charged_failures"], 0)
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
