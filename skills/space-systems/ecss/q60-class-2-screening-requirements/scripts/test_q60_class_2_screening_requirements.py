"""Contract tests for the clause 5.3.3 Class 2 screening logic.

The cases walk the regime one step at a time: the destination that decides
whether flight screening is owed at all, the screen set each package family
carries, the order the screens were run in, the Arrhenius conversion of a
burn-in run off its reference temperature, and the percent defective against
the allowable. Every limit is exercised on both sides, and a value landing on
its limit is compared with a representation-sized tolerance so the verdict
does not change between machines.
"""

import unittest

from q60_class_2_screening_requirements_logic import (
    FLIGHT_DESTINATION,
    HOURS_TOLERANCE,
    NON_FLIGHT_DESTINATIONS,
    PDA_TOLERANCE,
    SCREEN_PRECEDENCE,
    SCREEN_SETS,
    acceleration_factor,
    assess_screening_campaign,
    assess_screening_lot,
    burn_in_findings,
    equivalent_burn_in_hours,
    missing_screens,
    normalize_token,
    ordering_findings,
    pda_findings,
    percent_defective,
    screen_set_for,
)

HERMETIC_SEQUENCE = [
    "internal-visual",
    "temperature-cycling",
    "constant-acceleration",
    "burn-in",
    "final-electrical",
    "seal-fine-and-gross-leak",
    "external-visual",
]


def _policy(**overrides):
    policy = {
        "burn_in_reference_c": 125.0,
        "burn_in_required_hours": 168.0,
        "activation_energy_ev": 0.7,
        "pda_percent": 5.0,
    }
    policy.update(overrides)
    return policy


def _lot(**overrides):
    lot = {
        "lot_id": "LOT-2C-11",
        "destination": "flight-standard",
        "package_family": "hermetic-cavity",
        "screens_performed": list(HERMETIC_SEQUENCE),
        "burn_in": {"hours": 168.0, "temperature_c": 125.0},
        "devices_screened": 500,
        "devices_rejected": 10,
    }
    lot.update(overrides)
    return lot


def _campaign(**overrides):
    campaign = {
        "build_reference": "FM1-BOARD-07",
        "policy": _policy(),
        "lots": [_lot()],
    }
    campaign.update(overrides)
    return campaign


class TokenAndFamilyTests(unittest.TestCase):
    def test_token_normalised(self):
        self.assertEqual(normalize_token("Hermetic_Cavity", "family"), "hermetic-cavity")

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "family")

    def test_cavity_family_owes_a_hermeticity_check(self):
        self.assertIn("seal-fine-and-gross-leak", screen_set_for("hermetic-cavity"))

    def test_encapsulated_family_owes_no_hermeticity_check(self):
        self.assertNotIn("seal-fine-and-gross-leak", screen_set_for("encapsulated-nonhermetic"))

    def test_every_family_owes_a_final_electrical(self):
        for family in SCREEN_SETS:
            self.assertIn("final-electrical", screen_set_for(family))

    def test_unknown_family_refused(self):
        with self.assertRaises(ValueError):
            screen_set_for("potted-module-of-some-kind")


class ScreenSetTests(unittest.TestCase):
    def test_full_sequence_omits_nothing(self):
        self.assertEqual(missing_screens(HERMETIC_SEQUENCE, "hermetic-cavity"), [])

    def test_omitted_screen_is_named(self):
        sequence = [s for s in HERMETIC_SEQUENCE if s != "constant-acceleration"]
        self.assertEqual(missing_screens(sequence, "hermetic-cavity"), ["constant-acceleration"])

    def test_cavity_sequence_over_covers_an_encapsulated_family(self):
        self.assertEqual(missing_screens(HERMETIC_SEQUENCE, "encapsulated-nonhermetic"), [])

    def test_encapsulated_sequence_under_covers_a_cavity_family(self):
        sequence = list(SCREEN_SETS["encapsulated-nonhermetic"])
        self.assertIn("seal-fine-and-gross-leak", missing_screens(sequence, "hermetic-cavity"))

    def test_repeated_screen_refused(self):
        with self.assertRaises(ValueError):
            missing_screens(HERMETIC_SEQUENCE + ["burn-in"], "hermetic-cavity")

    def test_non_sequence_screens_refused(self):
        with self.assertRaises(ValueError):
            missing_screens("burn-in", "hermetic-cavity")


class OrderingTests(unittest.TestCase):
    def test_correct_order_raises_nothing(self):
        self.assertEqual(ordering_findings(HERMETIC_SEQUENCE), [])

    def test_final_electrical_before_burn_in_reported(self):
        sequence = list(HERMETIC_SEQUENCE)
        sequence.remove("final-electrical")
        sequence.insert(sequence.index("burn-in"), "final-electrical")
        findings = ordering_findings(sequence)
        self.assertTrue(any("'burn-in' was run after 'final-electrical'" in f for f in findings))

    def test_leak_check_before_temperature_cycling_reported(self):
        sequence = list(HERMETIC_SEQUENCE)
        sequence.remove("seal-fine-and-gross-leak")
        sequence.insert(0, "seal-fine-and-gross-leak")
        self.assertTrue(ordering_findings(sequence))

    def test_a_rule_whose_screens_are_both_absent_raises_nothing(self):
        self.assertEqual(ordering_findings(["temperature-cycling"]), [])

    def test_every_precedence_pair_is_satisfied_by_the_house_sequence(self):
        for first, second in SCREEN_PRECEDENCE:
            if first in HERMETIC_SEQUENCE and second in HERMETIC_SEQUENCE:
                self.assertLess(
                    HERMETIC_SEQUENCE.index(first), HERMETIC_SEQUENCE.index(second)
                )


class AccelerationTests(unittest.TestCase):
    def test_burn_in_at_the_reference_is_not_accelerated(self):
        self.assertAlmostEqual(acceleration_factor(0.7, 125.0, 125.0), 1.0, places=9)

    def test_hotter_burn_in_accelerates(self):
        self.assertGreater(acceleration_factor(0.7, 125.0, 150.0), 2.0)

    def test_known_acceleration_value(self):
        self.assertAlmostEqual(acceleration_factor(0.7, 125.0, 150.0), 3.338028336, places=6)

    def test_cooler_burn_in_decelerates(self):
        self.assertLess(acceleration_factor(0.7, 125.0, 100.0), 0.5)

    def test_higher_activation_energy_accelerates_more(self):
        self.assertGreater(
            acceleration_factor(1.0, 125.0, 150.0), acceleration_factor(0.5, 125.0, 150.0)
        )

    def test_equivalent_hours_scale_with_the_factor(self):
        hours = equivalent_burn_in_hours(60.0, 0.7, 125.0, 150.0)
        self.assertAlmostEqual(hours, 60.0 * acceleration_factor(0.7, 125.0, 150.0), places=9)

    def test_zero_activation_energy_refused(self):
        with self.assertRaises(ValueError):
            acceleration_factor(0.0, 125.0, 150.0)

    def test_temperature_below_absolute_zero_refused(self):
        with self.assertRaises(ValueError):
            acceleration_factor(0.7, 125.0, -300.0)

    def test_negative_burn_in_hours_refused(self):
        with self.assertRaises(ValueError):
            equivalent_burn_in_hours(-1.0, 0.7, 125.0, 125.0)


class BurnInTests(unittest.TestCase):
    def test_burn_in_landing_on_the_requirement_is_accepted(self):
        record = burn_in_findings({"hours": 168.0, "temperature_c": 125.0}, _policy())
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["equivalent_hours"], 168.0, places=9)

    def test_short_hot_burn_in_can_still_meet_the_requirement(self):
        record = burn_in_findings({"hours": 60.0, "temperature_c": 150.0}, _policy())
        self.assertEqual(record["findings"], [])

    def test_cool_burn_in_of_nominal_length_falls_short(self):
        record = burn_in_findings({"hours": 168.0, "temperature_c": 100.0}, _policy())
        self.assertTrue(any("short of the" in f for f in record["findings"]))

    def test_missing_burn_in_key_refused(self):
        with self.assertRaises(ValueError):
            burn_in_findings({"hours": 168.0}, _policy())

    def test_missing_policy_key_refused(self):
        policy = _policy()
        del policy["activation_energy_ev"]
        with self.assertRaises(ValueError):
            burn_in_findings({"hours": 168.0, "temperature_c": 125.0}, policy)

    def test_hours_tolerance_is_representation_sized_only(self):
        self.assertLess(HOURS_TOLERANCE, 1e-6)


class PdaTests(unittest.TestCase):
    def test_percent_defective_computed(self):
        self.assertAlmostEqual(percent_defective(500, 10), 2.0, places=9)

    def test_clean_lot_is_zero_percent(self):
        self.assertAlmostEqual(percent_defective(500, 0), 0.0, places=9)

    def test_defective_rate_landing_on_the_allowable_is_accepted(self):
        record = pda_findings(200, 10, 5.0)
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["percent_defective"], 5.0, places=9)

    def test_representation_sized_excess_is_not_a_breach(self):
        # 5/6 expressed two ways differs in the last bit; the tolerance keeps
        # the verdict the same on every machine.
        record = pda_findings(6, 5, 100.0 * 5 / 6)
        self.assertEqual(record["findings"], [])

    def test_breach_of_the_allowable_reported(self):
        record = pda_findings(200, 30, 5.0)
        self.assertTrue(any("above the" in f for f in record["findings"]))

    def test_more_rejects_than_screened_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(10, 40)

    def test_empty_lot_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(0, 0)

    def test_allowable_outside_the_range_refused(self):
        with self.assertRaises(ValueError):
            pda_findings(200, 10, 140.0)

    def test_non_integer_reject_count_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(200, 10.5)

    def test_pda_tolerance_is_representation_sized_only(self):
        self.assertLess(PDA_TOLERANCE, 1e-6)


class LotTests(unittest.TestCase):
    def test_clean_flight_lot_is_acceptable(self):
        record = assess_screening_lot(_lot(), _policy())
        self.assertTrue(record["acceptable"])
        self.assertTrue(record["flight_screened"])

    def test_omitted_screen_reported_on_a_flight_lot(self):
        sequence = [s for s in HERMETIC_SEQUENCE if s != "burn-in"]
        record = assess_screening_lot(_lot(screens_performed=sequence), _policy())
        self.assertIn("burn-in", record["missing_screens"])
        self.assertFalse(record["acceptable"])

    def test_marked_non_flight_lot_needs_no_flight_screening(self):
        lot = {
            "lot_id": "LOT-GSE-3",
            "destination": "ground-support-equipment",
            "marked_non_flight": True,
        }
        record = assess_screening_lot(lot, _policy())
        self.assertTrue(record["acceptable"])
        self.assertFalse(record["flight_screened"])

    def test_unmarked_non_flight_lot_reported(self):
        for destination in NON_FLIGHT_DESTINATIONS:
            lot = {"lot_id": "LOT-X", "destination": destination}
            record = assess_screening_lot(lot, _policy())
            self.assertTrue(any("not marked" in f for f in record["findings"]))

    def test_unknown_destination_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_lot(_lot(destination="somewhere-useful"), _policy())

    def test_missing_flight_lot_key_refused(self):
        lot = _lot()
        del lot["burn_in"]
        with self.assertRaises(ValueError):
            assess_screening_lot(lot, _policy())

    def test_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_lot(["LOT-2C-11"], _policy())


class CampaignTests(unittest.TestCase):
    def test_clean_campaign_is_complete(self):
        verdict = assess_screening_campaign(_campaign())
        self.assertTrue(verdict["screening_complete"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["flight_ready_fraction"], 1.0, places=9)

    def test_flight_ready_fraction_counts_only_flight_lots(self):
        campaign = _campaign(
            lots=[
                _lot(),
                _lot(lot_id="LOT-2C-12", devices_rejected=200),
                {
                    "lot_id": "LOT-GSE-3",
                    "destination": "engineering-model",
                    "marked_non_flight": True,
                },
            ]
        )
        verdict = assess_screening_campaign(campaign)
        self.assertEqual(verdict["flight_lot_count"], 2)
        self.assertAlmostEqual(verdict["flight_ready_fraction"], 0.5, places=9)

    def test_campaign_with_no_flight_lot_reports_a_zero_fraction(self):
        campaign = _campaign(
            lots=[{"lot_id": "LOT-GSE-3", "destination": "breadboard", "marked_non_flight": True}]
        )
        verdict = assess_screening_campaign(campaign)
        self.assertEqual(verdict["flight_lot_count"], 0)
        self.assertAlmostEqual(verdict["flight_ready_fraction"], 0.0, places=9)

    def test_every_finding_is_carried_not_only_the_first(self):
        sequence = [s for s in HERMETIC_SEQUENCE if s != "internal-visual"]
        campaign = _campaign(
            lots=[
                _lot(
                    screens_performed=sequence,
                    burn_in={"hours": 24.0, "temperature_c": 125.0},
                    devices_rejected=300,
                )
            ]
        )
        verdict = assess_screening_campaign(campaign)
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_lot_reported_twice_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_campaign(_campaign(lots=[_lot(), _lot()]))

    def test_empty_lot_list_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_campaign(_campaign(lots=[]))

    def test_missing_campaign_key_refused(self):
        campaign = _campaign()
        del campaign["policy"]
        with self.assertRaises(ValueError):
            assess_screening_campaign(campaign)

    def test_non_mapping_campaign_refused(self):
        with self.assertRaises(ValueError):
            assess_screening_campaign("FM1-BOARD-07")

    def test_build_reference_echoed(self):
        verdict = assess_screening_campaign(_campaign())
        self.assertEqual(verdict["build_reference"], "FM1-BOARD-07")

    def test_flight_destination_is_distinct_from_the_non_flight_set(self):
        self.assertNotIn(FLIGHT_DESTINATION, NON_FLIGHT_DESTINATIONS)


if __name__ == "__main__":
    unittest.main()
