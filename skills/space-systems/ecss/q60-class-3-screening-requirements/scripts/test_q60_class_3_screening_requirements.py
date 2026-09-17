"""Contract test for the ECSS-Q-ST-60C clause 6.3.3 Class 3 screening leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_3_screening_requirements.py
"""

import unittest

from q60_class_3_screening_requirements_logic import (
    DESTINATIONS,
    FLIGHT_DESTINATION,
    HOURS_TOLERANCE,
    LOT_STATUSES,
    MINIMUM_BURN_IN_HOURS,
    NON_FLIGHT_DESTINATIONS,
    PACKAGE_FAMILIES,
    PDA_TOLERANCE,
    PERCENT_DEFECTIVE_ALLOWABLE,
    SCREEN_PRECEDENCE,
    SCREEN_SETS,
    acceleration_factor,
    assess_class_3_screening_campaign,
    assess_screening_lot,
    burn_in_findings,
    credited_screens,
    equivalent_burn_in_hours,
    missing_screens,
    normalize_performed,
    ordering_findings,
    pda_findings,
    percent_defective,
    screen_set_for,
    screening_is_owed,
    uncredited_claims,
)

FAMILY = "plastic-encapsulated"


def performed_set(family=FAMILY, performer="project", reference="scr-001"):
    """A full screening record for a package family, in the required order."""
    return [
        {
            "screen": screen,
            "performed_by": performer,
            "evidence_reference": reference,
        }
        for screen in screen_set_for(family)
    ]


def burn_in(**overrides):
    """A burn-in run at its reference temperature for the reduced duration."""
    entry = {
        "hours": MINIMUM_BURN_IN_HOURS,
        "activation_energy_ev": 0.7,
        "reference_c": 125.0,
        "actual_c": 125.0,
    }
    entry.update(overrides)
    return entry


def lot(**overrides):
    entry = {
        "lot_id": "lot-77a",
        "declared_category": "class-3",
        "destination": FLIGHT_DESTINATION,
        "package_family": FAMILY,
        "performed": performed_set(),
        "burn_in": burn_in(),
        "devices_screened": 200,
        "devices_rejected": 4,
        "non_flight_marking_present": False,
    }
    entry.update(overrides)
    return entry


class DestinationTests(unittest.TestCase):
    def test_a_flight_standard_destination_owes_screening(self):
        self.assertTrue(screening_is_owed(FLIGHT_DESTINATION))

    def test_every_non_flight_destination_owes_no_flight_screening(self):
        for destination in NON_FLIGHT_DESTINATIONS:
            self.assertFalse(screening_is_owed(destination))

    def test_the_destination_list_covers_both_groups(self):
        self.assertEqual(
            set(DESTINATIONS), {FLIGHT_DESTINATION} | set(NON_FLIGHT_DESTINATIONS)
        )

    def test_an_unknown_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            screening_is_owed("somebody-took-it-home")


class ScreenSetTests(unittest.TestCase):
    def test_every_package_family_publishes_a_screen_set(self):
        for family in PACKAGE_FAMILIES:
            self.assertGreater(len(screen_set_for(family)), 0)

    def test_every_screen_named_anywhere_sits_in_the_precedence_order(self):
        for family in PACKAGE_FAMILIES:
            for screen in SCREEN_SETS[family]:
                self.assertIn(screen, SCREEN_PRECEDENCE)

    def test_every_screen_set_ends_with_the_final_measurement(self):
        for family in PACKAGE_FAMILIES:
            self.assertEqual(
                screen_set_for(family)[-1], "final-electrical-measurement"
            )

    def test_a_hermetic_family_owes_a_seal_test_a_plastic_one_does_not(self):
        self.assertIn("seal-test", screen_set_for("hermetic-ceramic"))
        self.assertNotIn("seal-test", screen_set_for("plastic-encapsulated"))

    def test_an_unknown_package_family_is_rejected(self):
        with self.assertRaises(ValueError):
            screen_set_for("shrink-wrapped")


class ManufacturerCreditTests(unittest.TestCase):
    def test_a_project_performed_screen_always_counts(self):
        record = [
            {
                "screen": "temperature-cycling",
                "performed_by": "project",
                "evidence_reference": None,
            }
        ]
        self.assertEqual(credited_screens(record), ("temperature-cycling",))

    def test_a_manufacturer_claim_with_an_evidence_reference_earns_credit(self):
        record = [
            {
                "screen": "burn-in",
                "performed_by": "manufacturer-standard-flow",
                "evidence_reference": "mfr-flow-2026-04",
            }
        ]
        self.assertEqual(credited_screens(record), ("burn-in",))

    def test_a_manufacturer_claim_citing_nothing_earns_no_credit(self):
        record = [
            {
                "screen": "burn-in",
                "performed_by": "manufacturer-standard-flow",
                "evidence_reference": None,
            }
        ]
        self.assertEqual(credited_screens(record), ())

    def test_a_manufacturer_claim_citing_blank_text_earns_no_credit(self):
        record = [
            {
                "screen": "burn-in",
                "performed_by": "manufacturer-standard-flow",
                "evidence_reference": "   ",
            }
        ]
        self.assertEqual(credited_screens(record), ())

    def test_an_uncredited_claim_is_named_so_it_can_be_chased(self):
        record = [
            {
                "screen": "burn-in",
                "performed_by": "manufacturer-standard-flow",
                "evidence_reference": None,
            }
        ]
        self.assertEqual(uncredited_claims(record), ("burn-in",))

    def test_a_credited_claim_is_not_reported_as_uncredited(self):
        record = [
            {
                "screen": "burn-in",
                "performed_by": "manufacturer-standard-flow",
                "evidence_reference": "mfr-flow-2026-04",
            }
        ]
        self.assertEqual(uncredited_claims(record), ())

    def test_an_uncredited_claim_leaves_the_screen_owed(self):
        record = performed_set()
        record[2] = {
            "screen": "burn-in",
            "performed_by": "manufacturer-standard-flow",
            "evidence_reference": None,
        }
        self.assertIn("burn-in", missing_screens(record, FAMILY))

    def test_a_full_credited_record_leaves_no_screen_owed(self):
        self.assertEqual(missing_screens(performed_set(), FAMILY), ())

    def test_an_empty_record_leaves_the_whole_set_owed(self):
        self.assertEqual(missing_screens([], FAMILY), screen_set_for(FAMILY))

    def test_an_unknown_performer_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_performed(
                [
                    {
                        "screen": "burn-in",
                        "performed_by": "a-subcontractor-probably",
                        "evidence_reference": "x",
                    }
                ]
            )

    def test_an_unknown_screen_name_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_performed(
                [
                    {
                        "screen": "shake-it",
                        "performed_by": "project",
                        "evidence_reference": None,
                    }
                ]
            )

    def test_a_screen_recorded_twice_is_rejected(self):
        record = [
            {"screen": "burn-in", "performed_by": "project", "evidence_reference": None},
            {"screen": "burn-in", "performed_by": "project", "evidence_reference": None},
        ]
        with self.assertRaises(ValueError):
            normalize_performed(record)

    def test_a_bare_string_is_not_a_screening_record(self):
        with self.assertRaises(ValueError):
            normalize_performed("burn-in")


class OrderingTests(unittest.TestCase):
    def test_a_record_in_the_required_order_raises_nothing(self):
        self.assertEqual(ordering_findings(performed_set()), ())

    def test_a_measurement_taken_before_its_stress_is_a_finding(self):
        record = [
            {
                "screen": "final-electrical-measurement",
                "performed_by": "project",
                "evidence_reference": None,
            },
            {"screen": "burn-in", "performed_by": "project", "evidence_reference": None},
        ]
        findings = ordering_findings(record)
        self.assertEqual(
            findings[0]["finding"], "screen-performed-out-of-the-required-order"
        )

    def test_the_out_of_order_finding_names_both_screens(self):
        record = [
            {"screen": "burn-in", "performed_by": "project", "evidence_reference": None},
            {
                "screen": "temperature-cycling",
                "performed_by": "project",
                "evidence_reference": None,
            },
        ]
        detail = ordering_findings(record)[0]["detail"]
        self.assertIn("temperature-cycling", detail)
        self.assertIn("burn-in", detail)

    def test_a_record_with_one_entry_cannot_be_out_of_order(self):
        record = [
            {"screen": "burn-in", "performed_by": "project", "evidence_reference": None}
        ]
        self.assertEqual(ordering_findings(record), ())


class BurnInTests(unittest.TestCase):
    def test_burn_in_at_the_reference_temperature_has_a_unit_factor(self):
        self.assertAlmostEqual(acceleration_factor(0.7, 125.0, 125.0), 1.0, places=9)

    def test_a_hotter_burn_in_accelerates(self):
        self.assertGreater(acceleration_factor(0.7, 125.0, 150.0), 1.0)

    def test_a_cooler_burn_in_decelerates(self):
        self.assertLess(acceleration_factor(0.7, 125.0, 100.0), 1.0)

    def test_hours_at_the_reference_temperature_convert_to_themselves(self):
        self.assertAlmostEqual(
            equivalent_burn_in_hours(MINIMUM_BURN_IN_HOURS, 0.7, 125.0, 125.0),
            MINIMUM_BURN_IN_HOURS,
            places=9,
        )

    def test_a_run_exactly_on_the_reduced_duration_is_accepted(self):
        equivalent = equivalent_burn_in_hours(
            MINIMUM_BURN_IN_HOURS, 0.7, 125.0, 125.0
        )
        self.assertAlmostEqual(equivalent, MINIMUM_BURN_IN_HOURS, places=9)
        self.assertEqual(burn_in_findings(burn_in()), ())

    def test_a_short_run_at_the_reference_temperature_is_a_finding(self):
        findings = burn_in_findings(burn_in(hours=MINIMUM_BURN_IN_HOURS / 2.0))
        self.assertEqual(
            findings[0]["finding"], "burn-in-short-of-the-reduced-duration-allowed"
        )

    def test_a_short_hot_run_can_still_reach_the_reduced_duration(self):
        entry = burn_in(hours=MINIMUM_BURN_IN_HOURS / 4.0, actual_c=175.0)
        self.assertGreater(
            equivalent_burn_in_hours(
                entry["hours"], entry["activation_energy_ev"],
                entry["reference_c"], entry["actual_c"]
            ),
            MINIMUM_BURN_IN_HOURS,
        )
        self.assertEqual(burn_in_findings(entry), ())

    def test_a_negative_burn_in_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_findings(burn_in(hours=-1.0))

    def test_a_non_positive_activation_energy_is_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(0.0, 125.0, 150.0)

    def test_a_temperature_at_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(0.7, -273.15, 150.0)

    def test_a_non_positive_minimum_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            burn_in_findings(burn_in(), minimum_hours=0.0)

    def test_the_hours_tolerance_is_small_enough_to_separate_the_bound(self):
        self.assertLess(HOURS_TOLERANCE, 1e-6)


class PercentDefectiveTests(unittest.TestCase):
    def test_a_clean_lot_produces_no_defectives(self):
        self.assertAlmostEqual(percent_defective(200, 0), 0.0, places=9)

    def test_the_percentage_is_computed_off_the_screened_count(self):
        self.assertAlmostEqual(percent_defective(200, 10), 5.0, places=9)

    def test_a_lot_exactly_on_the_allowable_is_accepted(self):
        produced = percent_defective(200, 20)
        self.assertAlmostEqual(produced, PERCENT_DEFECTIVE_ALLOWABLE, places=9)
        self.assertEqual(pda_findings(200, 20), ())

    def test_a_lot_well_above_the_allowable_is_rejected(self):
        findings = pda_findings(200, 60)
        self.assertEqual(
            findings[0]["finding"], "percent-defective-above-the-allowable"
        )

    def test_a_zero_screened_count_is_rejected(self):
        with self.assertRaises(ValueError):
            percent_defective(0, 0)

    def test_more_rejects_than_devices_is_rejected(self):
        with self.assertRaises(ValueError):
            percent_defective(10, 11)

    def test_a_fractional_device_count_is_rejected(self):
        with self.assertRaises(ValueError):
            percent_defective(10.5, 1)

    def test_an_allowable_outside_its_range_is_rejected(self):
        with self.assertRaises(ValueError):
            pda_findings(200, 4, allowable=0.0)

    def test_the_pda_tolerance_is_small_enough_to_separate_the_bound(self):
        self.assertLess(PDA_TOLERANCE, 1e-6)


class LotTests(unittest.TestCase):
    def test_a_clean_flight_lot_is_accepted(self):
        record = assess_screening_lot(lot())
        self.assertEqual(
            record["status"], "class-3-lot-accepted-for-flight-standard-use"
        )
        self.assertTrue(record["accepted"])
        self.assertEqual(record["findings"], [])

    def test_a_marked_non_flight_lot_owes_no_flight_screening(self):
        record = assess_screening_lot(
            lot(
                destination="breadboard",
                non_flight_marking_present=True,
                performed=[],
            )
        )
        self.assertEqual(record["status"], "class-3-lot-not-for-flight-standard-use")
        self.assertEqual(record["findings"], [])
        self.assertFalse(record["screening_owed"])

    def test_an_unmarked_non_flight_lot_is_a_finding(self):
        record = assess_screening_lot(
            lot(destination="engineering-model", non_flight_marking_present=False)
        )
        self.assertIn(
            "non-flight-lot-carries-no-marking",
            [f["finding"] for f in record["findings"]],
        )

    def test_an_uncredited_manufacturer_claim_leaves_the_lot_incomplete(self):
        record = performed_set()
        record[2] = {
            "screen": "burn-in",
            "performed_by": "manufacturer-standard-flow",
            "evidence_reference": None,
        }
        result = assess_screening_lot(lot(performed=record))
        names = [f["finding"] for f in result["findings"]]
        self.assertIn("manufacturer-flow-credit-claimed-without-evidence", names)
        self.assertIn("owed-screen-not-covered", names)
        self.assertEqual(result["status"], "class-3-lot-screening-incomplete")

    def test_an_evidenced_manufacturer_flow_covers_the_whole_set(self):
        result = assess_screening_lot(
            lot(
                performed=performed_set(
                    performer="manufacturer-standard-flow",
                    reference="mfr-flow-2026-04",
                )
            )
        )
        self.assertTrue(result["accepted"])

    def test_a_missing_screen_is_named_on_the_lot_record(self):
        record = [e for e in performed_set() if e["screen"] != "temperature-cycling"]
        result = assess_screening_lot(lot(performed=record))
        self.assertEqual(result["missing_screens"], ["temperature-cycling"])

    def test_a_lot_above_the_allowable_is_rejected_on_percent_defective(self):
        result = assess_screening_lot(lot(devices_rejected=100))
        self.assertEqual(
            result["status"], "class-3-lot-rejected-on-percent-defective"
        )

    def test_a_lot_declared_in_another_category_is_not_checked_here(self):
        result = assess_screening_lot(lot(declared_category="class-2"))
        self.assertIn(
            "declared-category-is-not-the-one-being-checked",
            [f["finding"] for f in result["findings"]],
        )

    def test_a_policy_may_tighten_the_reduced_burn_in_duration(self):
        result = assess_screening_lot(
            lot(), {"minimum_burn_in_hours": MINIMUM_BURN_IN_HOURS * 4.0}
        )
        self.assertIn(
            "burn-in-short-of-the-reduced-duration-allowed",
            [f["finding"] for f in result["findings"]],
        )

    def test_a_policy_may_tighten_the_allowable_percent_defective(self):
        result = assess_screening_lot(lot(), {"percent_defective_allowable": 1.0})
        self.assertEqual(
            result["status"], "class-3-lot-rejected-on-percent-defective"
        )

    def test_every_status_name_is_one_the_module_publishes(self):
        self.assertIn(assess_screening_lot(lot())["status"], LOT_STATUSES)
        self.assertIn(
            assess_screening_lot(
                lot(destination="breadboard", non_flight_marking_present=True)
            )["status"],
            LOT_STATUSES,
        )

    def test_an_empty_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_screening_lot(lot(lot_id="  "))

    def test_a_non_mapping_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_screening_lot("lot-77a")


class CampaignTests(unittest.TestCase):
    def test_a_campaign_of_clean_lots_is_clear(self):
        report = assess_class_3_screening_campaign(
            {"campaign_id": "camp-9", "lots": [lot(), lot(lot_id="lot-77b")]}
        )
        self.assertTrue(report["campaign_clear"])
        self.assertEqual(len(report["accepted_lots"]), 2)
        self.assertAlmostEqual(report["accepted_fraction"], 1.0, places=9)

    def test_one_defective_lot_stops_the_campaign(self):
        report = assess_class_3_screening_campaign(
            {
                "campaign_id": "camp-9",
                "lots": [lot(), lot(lot_id="lot-77b", devices_rejected=100)],
            }
        )
        self.assertFalse(report["campaign_clear"])
        self.assertAlmostEqual(report["accepted_fraction"], 0.5, places=9)

    def test_the_accepted_fraction_is_taken_over_flight_lots_only(self):
        report = assess_class_3_screening_campaign(
            {
                "campaign_id": "camp-9",
                "lots": [
                    lot(),
                    lot(
                        lot_id="lot-77c",
                        destination="ground-support-equipment",
                        non_flight_marking_present=True,
                    ),
                ],
            }
        )
        self.assertEqual(report["flight_lot_count"], 1)
        self.assertAlmostEqual(report["accepted_fraction"], 1.0, places=9)

    def test_the_status_counts_add_up_to_the_campaign(self):
        report = assess_class_3_screening_campaign(
            {
                "campaign_id": "camp-9",
                "lots": [
                    lot(),
                    lot(lot_id="lot-77b", devices_rejected=100),
                    lot(
                        lot_id="lot-77c",
                        destination="breadboard",
                        non_flight_marking_present=True,
                    ),
                ],
            }
        )
        self.assertEqual(sum(report["status_counts"].values()), 3)

    def test_a_campaign_policy_reaches_every_lot(self):
        report = assess_class_3_screening_campaign(
            {
                "campaign_id": "camp-9",
                "lots": [lot(), lot(lot_id="lot-77b")],
                "policy": {"percent_defective_allowable": 1.0},
            }
        )
        self.assertEqual(report["accepted_lots"], [])

    def test_a_repeated_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_screening_campaign(
                {"campaign_id": "camp-9", "lots": [lot(), lot()]}
            )

    def test_a_campaign_with_no_lots_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_screening_campaign({"campaign_id": "camp-9", "lots": []})

    def test_an_empty_campaign_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_screening_campaign({"campaign_id": "  ", "lots": [lot()]})

    def test_a_non_sequence_lot_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_screening_campaign(
                {"campaign_id": "camp-9", "lots": {"lot_id": "x"}}
            )

    def test_every_finding_carries_the_lot_it_belongs_to(self):
        report = assess_class_3_screening_campaign(
            {"campaign_id": "camp-9", "lots": [lot(devices_rejected=100)]}
        )
        for finding in report["findings"]:
            self.assertEqual(finding["lot_id"], "lot-77a")


if __name__ == "__main__":
    unittest.main()
