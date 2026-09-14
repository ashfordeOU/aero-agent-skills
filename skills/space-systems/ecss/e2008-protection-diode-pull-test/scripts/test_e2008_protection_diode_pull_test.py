"""Contract tests for the clause 9.6.11 protection diode pull test.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused pull policy, a lot
pulled before its environmental block was finished, a grip dragged off the
contact normal, a required contact never pulled, a sample too thin to sentence
a lot, and a device sentenced by whichever contact releases first.
"""

import math
import unittest

from e2008_protection_diode_pull_test_logic import (
    BOND_STRENGTH_BELOW_MINIMUM,
    BOND_STRENGTH_DEMONSTRATED,
    CONTACT_SITES_MISSING,
    DEFAULT_PULL_POLICY,
    ENVIRONMENTAL_BLOCK_INCOMPLETE,
    PULL_DRAGGED_OFF_NORMAL,
    PULL_SAMPLE_NOT_REPRESENTATIVE,
    assess_protection_diode_pull,
    bond_strength_mpa,
    bond_strength_sufficient,
    contact_bond_strength_mpa,
    environmental_block_complete,
    environmental_block_shortfalls,
    missing_contacts,
    normal_force_n,
    off_normal_within_allowance,
    sample_fraction,
    sample_representative,
    validate_contact_pull,
    validate_environmental_record,
    validate_pull_policy,
    weaker_contact,
)

MIN_STRENGTH = 4.0
MAX_ANGLE = 15.0


def _policy(**overrides):
    policy = dict(DEFAULT_PULL_POLICY)
    policy.update(overrides)
    return policy


def _environmental(**overrides):
    record = {"thermal_cycles_completed": 12, "humidity_soak_hours": 30.0}
    record.update(overrides)
    return record


def _contacts(positive_force=18.0, negative_force=16.5, angle=0.0):
    return [
        {
            "contact": "positive-contact",
            "pull_force_n": positive_force,
            "off_normal_angle_deg": angle,
            "bonded_area_mm2": 3.0,
        },
        {
            "contact": "negative-contact",
            "pull_force_n": negative_force,
            "off_normal_angle_deg": angle,
            "bonded_area_mm2": 3.0,
        },
    ]


def _devices():
    return [
        {"id": "pd-01", "contacts": _contacts()},
        {"id": "pd-02", "contacts": _contacts(17.4, 19.2)},
    ]


def _case(**overrides):
    case = {
        "environmental": _environmental(),
        "lot_size": 12,
        "devices": _devices(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_pull_policy(DEFAULT_PULL_POLICY), DEFAULT_PULL_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy("min_bond_strength_mpa")

    def test_zero_minimum_strength_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(min_bond_strength_mpa=0.0))

    def test_a_ninety_degree_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(max_off_normal_angle_deg=90.0))

    def test_a_fractional_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(required_thermal_cycles=10.5))

    def test_a_sample_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(_policy(min_sample_fraction=1.2))

    def test_a_repeated_required_contact_rejected(self):
        with self.assertRaises(ValueError):
            validate_pull_policy(
                _policy(required_contacts=("positive-contact", "positive-contact"))
            )


class EnvironmentalTests(unittest.TestCase):
    def test_the_conditioning_record_is_read_back(self):
        cycles, hours = validate_environmental_record(_environmental())
        self.assertEqual(cycles, 12)
        self.assertAlmostEqual(hours, 30.0, places=9)

    def test_a_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            validate_environmental_record(_environmental(humidity_soak_hours=-1.0))

    def test_a_missing_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_environmental_record({"humidity_soak_hours": 30.0})

    def test_a_complete_block_reports_no_shortfall(self):
        self.assertEqual(environmental_block_shortfalls(_environmental()), [])
        self.assertTrue(environmental_block_complete(_environmental()))

    def test_a_block_exactly_on_the_owed_soak_is_complete(self):
        self.assertTrue(
            environmental_block_complete(
                _environmental(thermal_cycles_completed=10, humidity_soak_hours=24.0)
            )
        )

    def test_a_short_cycle_count_is_a_shortfall(self):
        notes = environmental_block_shortfalls(
            _environmental(thermal_cycles_completed=4)
        )
        self.assertEqual(len(notes), 1)

    def test_both_shortfalls_are_reported_together(self):
        notes = environmental_block_shortfalls(
            _environmental(thermal_cycles_completed=4, humidity_soak_hours=2.0)
        )
        self.assertEqual(len(notes), 2)


class ForceTests(unittest.TestCase):
    def test_a_pull_on_the_normal_keeps_its_whole_force(self):
        self.assertAlmostEqual(normal_force_n(18.0, 0.0), 18.0, places=9)

    def test_an_off_normal_pull_keeps_only_its_cosine_component(self):
        self.assertAlmostEqual(
            normal_force_n(18.0, 30.0), 18.0 * math.cos(math.radians(30.0)), places=12
        )

    def test_a_pull_in_the_contact_plane_rejected(self):
        with self.assertRaises(ValueError):
            normal_force_n(18.0, 90.0)

    def test_a_negative_angle_rejected(self):
        with self.assertRaises(ValueError):
            normal_force_n(18.0, -5.0)

    def test_an_angle_exactly_on_the_allowance_is_admitted(self):
        self.assertTrue(off_normal_within_allowance(MAX_ANGLE))

    def test_an_angle_beyond_the_allowance_is_refused(self):
        self.assertFalse(off_normal_within_allowance(MAX_ANGLE * 2.0))

    def test_bond_strength_divides_normal_force_by_bonded_area(self):
        self.assertAlmostEqual(bond_strength_mpa(18.0, 3.0), 6.0, places=9)

    def test_a_wider_contact_reports_a_lower_strength_for_the_same_force(self):
        self.assertAlmostEqual(
            bond_strength_mpa(18.0, 6.0), bond_strength_mpa(18.0, 3.0) / 2.0, places=9
        )

    def test_zero_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            bond_strength_mpa(18.0, 0.0)

    def test_the_two_corrections_compose_into_one_strength(self):
        value = contact_bond_strength_mpa(18.0, 20.0, 3.0)
        expected = (18.0 * math.cos(math.radians(20.0))) / 3.0
        self.assertAlmostEqual(value, expected, places=12)

    def test_a_strength_exactly_on_the_minimum_is_sufficient(self):
        self.assertTrue(bond_strength_sufficient(MIN_STRENGTH))

    def test_a_strength_below_the_minimum_is_refused(self):
        self.assertFalse(bond_strength_sufficient(MIN_STRENGTH * 0.5))


class RecordTests(unittest.TestCase):
    def test_a_contact_pull_is_read_back_in_full(self):
        name, force, angle, area = validate_contact_pull(_contacts()[0])
        self.assertEqual(name, "positive-contact")
        self.assertAlmostEqual(force, 18.0, places=9)
        self.assertAlmostEqual(angle, 0.0, places=9)
        self.assertAlmostEqual(area, 3.0, places=9)

    def test_a_blank_contact_name_rejected(self):
        contact = _contacts()[0]
        contact["contact"] = "  "
        with self.assertRaises(ValueError):
            validate_contact_pull(contact)

    def test_a_negative_pull_force_rejected(self):
        contact = _contacts()[0]
        contact["pull_force_n"] = -4.0
        with self.assertRaises(ValueError):
            validate_contact_pull(contact)

    def test_a_complete_device_leaves_no_contact_missing(self):
        self.assertEqual(
            missing_contacts(["positive-contact", "negative-contact"]), ()
        )

    def test_an_unpulled_contact_is_named(self):
        self.assertEqual(
            missing_contacts(["positive-contact"]), ("negative-contact",)
        )

    def test_the_weaker_contact_sentences_the_device(self):
        records = [
            {"contact": "positive-contact", "bond_strength_mpa": 6.0},
            {"contact": "negative-contact", "bond_strength_mpa": 5.5},
        ]
        self.assertEqual(weaker_contact(records)["contact"], "negative-contact")

    def test_sentencing_an_empty_contact_set_rejected(self):
        with self.assertRaises(ValueError):
            weaker_contact([])

    def test_sample_fraction_is_the_pulled_share_of_the_lot(self):
        self.assertAlmostEqual(sample_fraction(3, 12), 0.25, places=9)

    def test_a_sample_larger_than_its_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_fraction(13, 12)

    def test_an_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            sample_fraction(0, 0)

    def test_a_sample_exactly_on_the_policy_share_is_representative(self):
        self.assertTrue(sample_representative(1, 10))

    def test_a_sample_below_the_policy_share_is_refused(self):
        self.assertFalse(sample_representative(1, 40))


class RunTests(unittest.TestCase):
    def test_a_clean_run_demonstrates_bond_strength(self):
        result = assess_protection_diode_pull(_case())
        self.assertEqual(result["verdict"], BOND_STRENGTH_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["device_records"]), 2)

    def test_each_device_carries_its_weaker_contact(self):
        result = assess_protection_diode_pull(_case())
        first = result["device_records"][0]
        self.assertEqual(first["weaker_contact"], "negative-contact")
        self.assertAlmostEqual(first["bond_strength_mpa"], 16.5 / 3.0, places=9)

    def test_the_lot_weakest_and_mean_strengths_are_reported(self):
        result = assess_protection_diode_pull(_case())
        self.assertAlmostEqual(
            result["weakest_bond_strength_mpa"], 16.5 / 3.0, places=9
        )
        self.assertAlmostEqual(
            result["mean_bond_strength_mpa"],
            ((16.5 / 3.0) + (17.4 / 3.0)) / 2.0,
            places=9,
        )

    def test_a_short_environmental_block_stops_the_run_first(self):
        result = assess_protection_diode_pull(
            _case(environmental=_environmental(thermal_cycles_completed=2))
        )
        self.assertEqual(result["verdict"], ENVIRONMENTAL_BLOCK_INCOMPLETE)
        self.assertTrue(result["findings"])

    def test_an_off_normal_pull_stops_the_run(self):
        devices = _devices()
        devices[1]["contacts"][0]["off_normal_angle_deg"] = 35.0
        result = assess_protection_diode_pull(_case(devices=devices))
        self.assertEqual(result["verdict"], PULL_DRAGGED_OFF_NORMAL)

    def test_an_unpulled_required_contact_stops_the_run(self):
        devices = _devices()
        devices[0]["contacts"] = [devices[0]["contacts"][0]]
        result = assess_protection_diode_pull(_case(devices=devices))
        self.assertEqual(result["verdict"], CONTACT_SITES_MISSING)
        self.assertIn("pd-01/negative-contact", result["missing_contacts"])

    def test_a_thin_sample_cannot_sentence_a_lot(self):
        result = assess_protection_diode_pull(_case(lot_size=400))
        self.assertEqual(result["verdict"], PULL_SAMPLE_NOT_REPRESENTATIVE)

    def test_a_weak_bond_sentences_the_lot(self):
        devices = _devices()
        devices[1]["contacts"][1]["pull_force_n"] = 4.5
        result = assess_protection_diode_pull(_case(devices=devices))
        self.assertEqual(result["verdict"], BOND_STRENGTH_BELOW_MINIMUM)
        self.assertTrue(any("pd-02" in note for note in result["findings"]))

    def test_the_sample_fraction_travels_with_the_result(self):
        result = assess_protection_diode_pull(_case())
        self.assertAlmostEqual(result["sample_fraction"], 2.0 / 12.0, places=9)

    def test_a_duplicate_device_id_rejected(self):
        devices = _devices()
        devices[1]["id"] = "pd-01"
        with self.assertRaises(ValueError):
            assess_protection_diode_pull(_case(devices=devices))

    def test_a_repeated_contact_on_one_device_rejected(self):
        devices = _devices()
        devices[0]["contacts"][1]["contact"] = "positive-contact"
        with self.assertRaises(ValueError):
            assess_protection_diode_pull(_case(devices=devices))

    def test_an_empty_pulled_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_pull(_case(devices=[]))

    def test_a_missing_environmental_record_rejected(self):
        case = _case()
        del case["environmental"]
        with self.assertRaises(ValueError):
            assess_protection_diode_pull(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_pull(["environmental"])

    def test_the_normal_force_is_kept_beside_the_machine_reading(self):
        devices = _devices()
        devices[0]["contacts"][0]["off_normal_angle_deg"] = 10.0
        result = assess_protection_diode_pull(_case(devices=devices))
        entry = result["device_records"][0]["contacts"][0]
        self.assertAlmostEqual(entry["pull_force_n"], 18.0, places=9)
        self.assertAlmostEqual(
            entry["normal_force_n"], 18.0 * math.cos(math.radians(10.0)), places=12
        )


if __name__ == "__main__":
    unittest.main()
