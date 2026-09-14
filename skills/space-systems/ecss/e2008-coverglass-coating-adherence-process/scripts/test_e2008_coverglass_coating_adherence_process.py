"""Contract tests for the clause 8.7.11.2.2 chamber-loading logic."""

import unittest

from e2008_coverglass_coating_adherence_process_logic import (
    CHAMBER_NOT_AMBIENT,
    DEFAULT_LOADING_POLICY,
    FACE_DOWN,
    FACE_OUTBOARD,
    FACE_UP,
    LOADING_INCOMPLETE,
    LOADING_NOT_ATTRIBUTABLE,
    LOT_LOADED,
    LOT_NOT_ESTABLISHED,
    assess_coverglass_chamber_loading,
    batch_count,
    chamber_capacity,
    chamber_vented_to_ambient,
    loaded_fraction,
    lot_membership,
    orientation_exposes_the_coating,
    slot_findings,
    validate_loading_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LOADING_POLICY)
    policy.update(overrides)
    return policy


def _roster(count=6):
    return ["cg-%02d" % index for index in range(1, count + 1)]


def _record(identifier, slot, **overrides):
    record = {
        "id": identifier,
        "rack": 1,
        "slot": slot,
        "batch": 1,
        "orientation": FACE_UP,
        "stacked_on_another": False,
    }
    record.update(overrides)
    return record


def _records(count=6):
    return [_record("cg-%02d" % index, index) for index in range(1, count + 1)]


def _case(**overrides):
    case = {
        "lot_roster": _roster(),
        "loaded_records": _records(),
        "gauge_pressure_kpa": 0.0,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_loading_policy(DEFAULT_LOADING_POLICY), DEFAULT_LOADING_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_loading_policy("racks")

    def test_zero_slots_per_rack_rejected(self):
        with self.assertRaises(ValueError):
            validate_loading_policy(_policy(slots_per_rack=0))

    def test_negative_pressure_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_loading_policy(_policy(max_gauge_pressure_kpa=-1.0))

    def test_non_boolean_slot_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_loading_policy(_policy(require_slot_record="yes"))


class CapacityTests(unittest.TestCase):
    def test_capacity_is_slots_times_racks(self):
        self.assertEqual(chamber_capacity(_policy(slots_per_rack=25, max_racks=4)), 100)

    def test_a_lot_inside_one_capacity_is_one_batch(self):
        self.assertEqual(batch_count(60, 100), 1)

    def test_a_lot_exactly_filling_the_chamber_is_one_batch(self):
        self.assertEqual(batch_count(100, 100), 1)

    def test_one_article_over_capacity_costs_a_whole_batch(self):
        self.assertEqual(batch_count(101, 100), 2)

    def test_a_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            batch_count(0, 100)

    def test_a_full_load_is_the_whole_lot(self):
        self.assertAlmostEqual(loaded_fraction(6, 6), 1.0, places=12)

    def test_a_partial_load_is_reported_as_a_share(self):
        self.assertAlmostEqual(loaded_fraction(3, 6), 0.5, places=12)

    def test_loading_more_than_the_roster_rejected(self):
        with self.assertRaises(ValueError):
            loaded_fraction(7, 6)


class MembershipTests(unittest.TestCase):
    def test_a_complete_load_omits_nothing(self):
        loaded, omitted, strangers = lot_membership(_roster(), _records())
        self.assertEqual(len(loaded), 6)
        self.assertEqual(omitted, ())
        self.assertEqual(strangers, ())

    def test_an_unloaded_roster_article_is_an_omission(self):
        _loaded, omitted, _strangers = lot_membership(_roster(), _records(4))
        self.assertEqual(omitted, ("cg-05", "cg-06"))

    def test_an_article_off_the_roster_is_a_stranger(self):
        records = _records() + [_record("cg-99", 7)]
        _loaded, _omitted, strangers = lot_membership(_roster(), records)
        self.assertEqual(strangers, ("cg-99",))

    def test_an_empty_roster_yields_nothing(self):
        self.assertEqual(lot_membership([], _records()), ((), (), ()))

    def test_a_duplicate_roster_entry_rejected(self):
        with self.assertRaises(ValueError):
            lot_membership(["cg-01", "cg-01"], _records(1))

    def test_an_article_loaded_twice_rejected(self):
        with self.assertRaises(ValueError):
            lot_membership(_roster(), [_record("cg-01", 1), _record("cg-01", 2)])

    def test_a_blank_load_record_id_rejected(self):
        with self.assertRaises(ValueError):
            lot_membership(_roster(), [_record("   ", 1)])


class OrientationTests(unittest.TestCase):
    def test_face_up_exposes_the_coating(self):
        self.assertTrue(orientation_exposes_the_coating(FACE_UP))

    def test_face_outboard_exposes_the_coating(self):
        self.assertTrue(orientation_exposes_the_coating(FACE_OUTBOARD))

    def test_face_down_does_not(self):
        self.assertFalse(orientation_exposes_the_coating(FACE_DOWN))

    def test_an_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            orientation_exposes_the_coating("edge-on-ish")


class SlotTests(unittest.TestCase):
    def test_a_clean_load_reports_nothing(self):
        self.assertEqual(slot_findings(_records()), ())

    def test_a_missing_slot_is_reported(self):
        record = _record("cg-01", 1)
        del record["slot"]
        findings = slot_findings([record])
        self.assertTrue(any("records no slot" in f for f in findings))

    def test_a_missing_slot_is_tolerated_when_the_policy_says_so(self):
        record = _record("cg-01", 1)
        del record["slot"]
        self.assertEqual(slot_findings([record], _policy(require_slot_record=False)), ())

    def test_two_articles_in_one_slot_are_reported(self):
        findings = slot_findings([_record("cg-01", 3), _record("cg-02", 3)])
        self.assertTrue(any("both recorded in rack" in f for f in findings))

    def test_the_same_slot_in_another_rack_is_a_different_place(self):
        self.assertEqual(
            slot_findings([_record("cg-01", 3), _record("cg-02", 3, rack=2)]), ()
        )

    def test_a_slot_beyond_the_rack_is_reported(self):
        findings = slot_findings([_record("cg-01", 99)])
        self.assertTrue(any("beyond the 25 a rack" in f for f in findings))

    def test_a_rack_beyond_the_chamber_is_reported(self):
        findings = slot_findings([_record("cg-01", 1, rack=9)])
        self.assertTrue(any("beyond the 4 the" in f for f in findings))

    def test_a_missing_batch_is_reported(self):
        record = _record("cg-01", 1)
        del record["batch"]
        findings = slot_findings([record])
        self.assertTrue(any("records no batch" in f for f in findings))

    def test_a_face_down_article_is_reported(self):
        findings = slot_findings([_record("cg-01", 1, orientation=FACE_DOWN)])
        self.assertTrue(any("against the rack" in f for f in findings))

    def test_a_stacked_article_is_reported(self):
        findings = slot_findings([_record("cg-01", 1, stacked_on_another=True)])
        self.assertTrue(any("stacked on another" in f for f in findings))

    def test_every_attribution_defect_is_listed_not_just_the_first(self):
        record = _record(
            "cg-01", 99, rack=9, orientation=FACE_DOWN, stacked_on_another=True
        )
        del record["batch"]
        self.assertEqual(len(slot_findings([record])), 5)


class PressureTests(unittest.TestCase):
    def test_a_vented_chamber_is_ambient(self):
        self.assertTrue(chamber_vented_to_ambient(0.0))

    def test_a_pressure_exactly_on_the_tolerance_is_ambient(self):
        self.assertTrue(chamber_vented_to_ambient(0.5))

    def test_a_pressurised_chamber_is_not(self):
        self.assertFalse(chamber_vented_to_ambient(20.0))

    def test_a_partial_vacuum_is_not_either(self):
        self.assertFalse(chamber_vented_to_ambient(-20.0))


class VerdictTests(unittest.TestCase):
    def test_a_complete_load_is_accepted(self):
        result = assess_coverglass_chamber_loading(_case())
        self.assertEqual(result["verdict"], LOT_LOADED)
        self.assertEqual(result["findings"], [])

    def test_the_load_figures_are_reported_on_the_accepted_case(self):
        result = assess_coverglass_chamber_loading(_case())
        self.assertEqual(result["lot_size"], 6)
        self.assertEqual(result["required_batches"], 1)
        self.assertAlmostEqual(result["loaded_fraction"], 1.0, places=12)
        self.assertEqual(result["chamber_capacity"], 100)

    def test_an_empty_roster_stops_the_run_before_the_capacity_step(self):
        result = assess_coverglass_chamber_loading(_case(lot_roster=[]))
        self.assertEqual(result["verdict"], LOT_NOT_ESTABLISHED)
        self.assertIsNone(result["required_batches"])
        self.assertIsNone(result["loaded_fraction"])

    def test_a_lot_needing_too_many_runs_is_refused(self):
        case = _case(
            lot_roster=_roster(40), loaded_records=[_record("cg-01", 1)]
        )
        result = assess_coverglass_chamber_loading(
            case, _policy(slots_per_rack=2, max_racks=1, max_batches=3)
        )
        self.assertEqual(result["verdict"], LOT_NOT_ESTABLISHED)
        self.assertEqual(result["required_batches"], 20)

    def test_an_omitted_article_leaves_the_load_incomplete(self):
        result = assess_coverglass_chamber_loading(
            _case(loaded_records=_records(5))
        )
        self.assertEqual(result["verdict"], LOADING_INCOMPLETE)
        self.assertEqual(result["omitted_articles"], ("cg-06",))
        self.assertAlmostEqual(result["loaded_fraction"], 5.0 / 6.0, places=12)

    def test_a_stranger_leaves_the_load_incomplete(self):
        result = assess_coverglass_chamber_loading(
            _case(loaded_records=_records() + [_record("cg-99", 7)])
        )
        self.assertEqual(result["verdict"], LOADING_INCOMPLETE)
        self.assertEqual(result["stranger_articles"], ("cg-99",))

    def test_the_completeness_step_is_judged_before_the_attribution_step(self):
        records = _records(5)
        records[0]["orientation"] = FACE_DOWN
        result = assess_coverglass_chamber_loading(_case(loaded_records=records))
        self.assertEqual(result["verdict"], LOADING_INCOMPLETE)
        self.assertFalse(
            any("against the rack" in f for f in result["findings"])
        )

    def test_a_duplicated_slot_makes_the_load_unattributable(self):
        records = _records()
        records[1]["slot"] = records[0]["slot"]
        result = assess_coverglass_chamber_loading(_case(loaded_records=records))
        self.assertEqual(result["verdict"], LOADING_NOT_ATTRIBUTABLE)

    def test_a_face_down_article_makes_the_load_unattributable(self):
        records = _records()
        records[2]["orientation"] = FACE_DOWN
        result = assess_coverglass_chamber_loading(_case(loaded_records=records))
        self.assertEqual(result["verdict"], LOADING_NOT_ATTRIBUTABLE)
        self.assertTrue(any("cg-03" in f for f in result["findings"]))

    def test_a_sealed_chamber_fails_the_load(self):
        result = assess_coverglass_chamber_loading(
            _case(gauge_pressure_kpa=35.0)
        )
        self.assertEqual(result["verdict"], CHAMBER_NOT_AMBIENT)

    def test_missing_roster_key_rejected(self):
        case = _case()
        del case["lot_roster"]
        with self.assertRaises(ValueError):
            assess_coverglass_chamber_loading(case)

    def test_missing_load_records_rejected(self):
        case = _case()
        del case["loaded_records"]
        with self.assertRaises(ValueError):
            assess_coverglass_chamber_loading(case)

    def test_missing_gauge_pressure_rejected(self):
        case = _case()
        del case["gauge_pressure_kpa"]
        with self.assertRaises(ValueError):
            assess_coverglass_chamber_loading(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_chamber_loading(["lot_roster"])


if __name__ == "__main__":
    unittest.main()
