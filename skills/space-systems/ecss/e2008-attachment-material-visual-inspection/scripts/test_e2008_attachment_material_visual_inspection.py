#!/usr/bin/env python3
"""Contract test for the bonded attachment cure and tack screen (offline)."""

import copy
import unittest

from e2008_attachment_material_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_CURE_ALLOWANCES,
    INSPECTION_INCOMPLETE,
    REJECT,
    REWORK,
    TACK_FREE,
    TACK_MARGINAL,
    TACK_NOT_TESTED,
    TACKY,
    assess_attachment,
    attachment_cure_state,
    cure_acceleration,
    equivalent_cure_minutes,
    inspect_attachment_material,
    validate_cure_allowances,
    validate_cure_schedule,
)


def _schedule(**overrides):
    record = {
        "adhesive_id": "ADH-566",
        "reference_temperature_c": 65.0,
        "reference_dwell_minutes": 120.0,
        "activation_temperature_k": 6000.0,
        "minimum_cure_temperature_c": 10.0,
        "max_temperature_c": 120.0,
    }
    record.update(overrides)
    return record


def _profile(temperature_c=65.0, minutes=120.0):
    return [{"temperature_c": temperature_c, "minutes": minutes}]


def _attachment(attachment_id="ATT-001", **overrides):
    record = {
        "attachment_id": attachment_id,
        "adhesive_id": "ADH-566",
        "cure_profile": _profile(),
        "tack_state": TACK_FREE,
        "fillet_coverage": 1.0,
        "void_fraction": 0.0,
    }
    record.update(overrides)
    return record


def _assembly(how_many, declared=None):
    return {
        "assembly_id": "PVA-21",
        "declared_attachment_count": declared if declared is not None else how_many,
        "attachments": [_attachment("ATT-%03d" % n) for n in range(1, how_many + 1)],
    }


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_cure_allowances(DEFAULT_CURE_ALLOWANCES),
            DEFAULT_CURE_ALLOWANCES,
        )

    def test_non_mapping_allowances_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_allowances(0.9)

    def test_missing_fraction_refused(self):
        broken = copy.deepcopy(DEFAULT_CURE_ALLOWANCES)
        del broken["max_void_fraction"]
        with self.assertRaises(ValueError):
            validate_cure_allowances(broken)

    def test_fillet_coverage_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_CURE_ALLOWANCES)
        broken["min_fillet_coverage"] = 1.3
        with self.assertRaises(ValueError):
            validate_cure_allowances(broken)

    def test_review_ratio_above_the_cured_ratio_refused(self):
        broken = copy.deepcopy(DEFAULT_CURE_ALLOWANCES)
        broken["review_cure_ratio"] = 1.1
        with self.assertRaises(ValueError):
            validate_cure_allowances(broken)

    def test_non_positive_cure_ratio_refused(self):
        broken = copy.deepcopy(DEFAULT_CURE_ALLOWANCES)
        broken["min_cure_ratio"] = 0.0
        with self.assertRaises(ValueError):
            validate_cure_allowances(broken)

    def test_rework_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_CURE_ALLOWANCES)
        broken["rework_margin_factor"] = 0.75
        with self.assertRaises(ValueError):
            validate_cure_allowances(broken)


class CureScheduleTests(unittest.TestCase):
    def test_a_valid_schedule_returns_itself(self):
        schedule = _schedule()
        self.assertIs(validate_cure_schedule(schedule), schedule)

    def test_schedule_without_an_adhesive_id_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(adhesive_id=" "))

    def test_non_positive_reference_dwell_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(reference_dwell_minutes=0.0))

    def test_temperature_below_absolute_zero_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(reference_temperature_c=-300.0))

    def test_cure_floor_at_or_above_the_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(minimum_cure_temperature_c=65.0))

    def test_damage_ceiling_below_the_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(max_temperature_c=50.0))

    def test_non_positive_activation_temperature_refused(self):
        with self.assertRaises(ValueError):
            validate_cure_schedule(_schedule(activation_temperature_k=0.0))


class CureAccelerationTests(unittest.TestCase):
    def test_the_reference_temperature_advances_at_unity(self):
        self.assertAlmostEqual(cure_acceleration(65.0, _schedule()), 1.0, places=9)

    def test_below_the_cure_floor_nothing_advances(self):
        self.assertEqual(cure_acceleration(5.0, _schedule()), 0.0)

    def test_the_cure_floor_itself_still_advances(self):
        self.assertGreater(cure_acceleration(10.0, _schedule()), 0.0)

    def test_hotter_advances_faster_than_the_reference(self):
        self.assertGreater(cure_acceleration(85.0, _schedule()), 1.2)

    def test_cooler_advances_slower_than_the_reference(self):
        self.assertLess(cure_acceleration(30.0, _schedule()), 0.8)

    def test_a_temperature_below_absolute_zero_refused(self):
        with self.assertRaises(ValueError):
            cure_acceleration(-400.0, _schedule())


class EquivalentCureTests(unittest.TestCase):
    def test_the_reference_dwell_accumulates_exactly_one_ratio(self):
        accumulation = equivalent_cure_minutes(_profile(), _schedule())
        self.assertAlmostEqual(accumulation["cure_ratio"], 1.0, places=9)
        self.assertAlmostEqual(accumulation["equivalent_minutes"], 120.0, places=9)
        self.assertAlmostEqual(accumulation["elapsed_minutes"], 120.0, places=9)

    def test_time_below_the_cure_floor_credits_nothing(self):
        accumulation = equivalent_cure_minutes(
            _profile(temperature_c=5.0, minutes=600.0), _schedule()
        )
        self.assertAlmostEqual(accumulation["equivalent_minutes"], 0.0, places=9)
        self.assertAlmostEqual(accumulation["minutes_below_cure_floor"], 600.0, places=9)
        self.assertAlmostEqual(accumulation["elapsed_minutes"], 600.0, places=9)

    def test_segments_accumulate_independently(self):
        profile = [
            {"temperature_c": 65.0, "minutes": 60.0},
            {"temperature_c": 5.0, "minutes": 300.0},
            {"temperature_c": 65.0, "minutes": 60.0},
        ]
        accumulation = equivalent_cure_minutes(profile, _schedule())
        self.assertAlmostEqual(accumulation["equivalent_minutes"], 120.0, places=9)
        self.assertAlmostEqual(accumulation["elapsed_minutes"], 420.0, places=9)
        self.assertAlmostEqual(accumulation["cure_ratio"], 1.0, places=9)

    def test_a_hotter_dwell_reaches_the_ratio_sooner(self):
        accumulation = equivalent_cure_minutes(
            _profile(temperature_c=85.0, minutes=60.0), _schedule()
        )
        self.assertTrue(accumulation["cure_ratio"] > 1.0)

    def test_the_peak_temperature_is_the_hottest_segment(self):
        profile = [
            {"temperature_c": 40.0, "minutes": 30.0},
            {"temperature_c": 95.0, "minutes": 30.0},
            {"temperature_c": 65.0, "minutes": 30.0},
        ]
        accumulation = equivalent_cure_minutes(profile, _schedule())
        self.assertAlmostEqual(accumulation["peak_temperature_c"], 95.0, places=9)
        self.assertFalse(accumulation["over_temperature"])

    def test_a_peak_exactly_on_the_ceiling_is_not_over_temperature(self):
        accumulation = equivalent_cure_minutes(
            _profile(temperature_c=120.0, minutes=5.0), _schedule()
        )
        self.assertFalse(accumulation["over_temperature"])

    def test_a_peak_past_the_ceiling_is_flagged(self):
        accumulation = equivalent_cure_minutes(
            _profile(temperature_c=140.0, minutes=5.0), _schedule()
        )
        self.assertTrue(accumulation["over_temperature"])

    def test_an_empty_profile_refused(self):
        with self.assertRaises(ValueError):
            equivalent_cure_minutes([], _schedule())

    def test_a_non_list_profile_refused(self):
        with self.assertRaises(ValueError):
            equivalent_cure_minutes("120 minutes at 65", _schedule())

    def test_a_non_positive_segment_duration_refused(self):
        with self.assertRaises(ValueError):
            equivalent_cure_minutes(_profile(minutes=0.0), _schedule())

    def test_a_non_mapping_segment_refused(self):
        with self.assertRaises(ValueError):
            equivalent_cure_minutes([65.0], _schedule())


class CureStateTests(unittest.TestCase):
    def test_a_clean_attachment_reads_as_cured(self):
        state = attachment_cure_state(_attachment(), _schedule())
        self.assertTrue(state["schedule_says_cured"])
        self.assertTrue(state["tack_tested"])
        self.assertAlmostEqual(state["cure_ratio"], 1.0, places=9)

    def test_an_untested_attachment_reports_itself_untested(self):
        state = attachment_cure_state(
            _attachment(tack_state=TACK_NOT_TESTED), _schedule()
        )
        self.assertFalse(state["tack_tested"])

    def test_an_adhesive_the_schedule_is_not_for_is_refused(self):
        with self.assertRaises(ValueError):
            attachment_cure_state(_attachment(adhesive_id="ADH-577"), _schedule())

    def test_an_unknown_tack_state_is_refused(self):
        with self.assertRaises(ValueError):
            attachment_cure_state(_attachment(tack_state="sticky"), _schedule())

    def test_a_fillet_coverage_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            attachment_cure_state(_attachment(fillet_coverage=1.4), _schedule())

    def test_an_attachment_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            attachment_cure_state(_attachment(attachment_id=""), _schedule())


class AttachmentDispositionTests(unittest.TestCase):
    def test_a_fully_cured_tack_free_attachment_accepts(self):
        result = assess_attachment(_attachment(), _schedule())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["findings"], [])

    def test_remaining_tackiness_rejects(self):
        result = assess_attachment(_attachment(tack_state=TACKY), _schedule())
        self.assertEqual(result["verdict"], REJECT)

    def test_tackiness_overrides_a_profile_that_says_cured(self):
        result = assess_attachment(
            _attachment(
                tack_state=TACKY, cure_profile=_profile(temperature_c=85.0, minutes=120.0)
            ),
            _schedule(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("the surface governs" in f for f in result["findings"]))

    def test_marginal_tackiness_returns_the_part_to_cure(self):
        result = assess_attachment(_attachment(tack_state=TACK_MARGINAL), _schedule())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_profile_on_the_review_floor_reworks(self):
        result = assess_attachment(
            _attachment(cure_profile=_profile(minutes=114.0)), _schedule()
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["cure_ratio"], 0.95, places=9)

    def test_a_profile_under_the_review_floor_rejects(self):
        result = assess_attachment(
            _attachment(cure_profile=_profile(minutes=60.0)), _schedule()
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_tack_free_surface_over_a_short_profile_is_still_called_out(self):
        result = assess_attachment(
            _attachment(cure_profile=_profile(minutes=114.0)), _schedule()
        )
        self.assertTrue(any("skins before the bond line" in f for f in result["findings"]))

    def test_a_profile_that_never_left_the_cold_rejects(self):
        result = assess_attachment(
            _attachment(cure_profile=_profile(temperature_c=5.0, minutes=1200.0)),
            _schedule(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertAlmostEqual(result["cure_ratio"], 0.0, places=9)

    def test_an_over_temperature_profile_rejects(self):
        result = assess_attachment(
            _attachment(cure_profile=_profile(temperature_c=150.0, minutes=120.0)),
            _schedule(),
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("tolerates" in f for f in result["findings"]))

    def test_a_short_fillet_inside_the_rework_floor_reworks(self):
        result = assess_attachment(_attachment(fillet_coverage=0.80), _schedule())
        self.assertEqual(result["verdict"], REWORK)

    def test_a_fillet_under_the_rework_floor_rejects(self):
        result = assess_attachment(_attachment(fillet_coverage=0.30), _schedule())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_fillet_exactly_on_the_allowance_accepts(self):
        result = assess_attachment(_attachment(fillet_coverage=0.90), _schedule())
        self.assertEqual(result["verdict"], ACCEPT)

    def test_voids_inside_the_rework_margin_rework(self):
        result = assess_attachment(_attachment(void_fraction=0.08), _schedule())
        self.assertEqual(result["verdict"], REWORK)

    def test_voids_past_the_rework_margin_reject(self):
        result = assess_attachment(_attachment(void_fraction=0.30), _schedule())
        self.assertEqual(result["verdict"], REJECT)

    def test_voids_exactly_on_the_allowance_accept(self):
        result = assess_attachment(_attachment(void_fraction=0.05), _schedule())
        self.assertEqual(result["verdict"], ACCEPT)

    def test_an_ungraded_attachment_says_it_has_no_tack_test(self):
        result = assess_attachment(_attachment(tack_state=TACK_NOT_TESTED), _schedule())
        self.assertFalse(result["tack_tested"])
        self.assertTrue(any("no tack test" in f for f in result["findings"]))


class AssemblyRollupTests(unittest.TestCase):
    def test_a_clean_assembly_accepts(self):
        result = inspect_attachment_material(_assembly(40), _schedule())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["affected_count"], 0)
        self.assertEqual(result["tacky_count"], 0)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 2.0, places=9)

    def test_two_affected_attachments_stay_inside_the_allowance(self):
        assembly = _assembly(40)
        assembly["attachments"][5]["void_fraction"] = 0.08
        assembly["attachments"][6]["fillet_coverage"] = 0.80
        result = inspect_attachment_material(assembly, _schedule())
        self.assertEqual(result["affected_count"], 2)
        self.assertEqual(result["verdict"], REWORK)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 0.0, places=9)

    def test_the_assembly_allowance_bites_once_it_is_exceeded(self):
        assembly = _assembly(40)
        for index in range(5):
            assembly["attachments"][index]["void_fraction"] = 0.08
        result = inspect_attachment_material(assembly, _schedule())
        self.assertEqual(result["affected_count"], 5)
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("rework margin of" in f for f in result["findings"]))

    def test_one_tacky_attachment_takes_the_assembly(self):
        assembly = _assembly(40)
        assembly["attachments"][11]["tack_state"] = TACKY
        result = inspect_attachment_material(assembly, _schedule())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["tacky_count"], 1)
        self.assertEqual(result["not_accepted_ids"], ["ATT-012"])
        self.assertEqual(result["disposition_counts"][ACCEPT], 39)

    def test_an_attachment_without_a_tack_test_leaves_the_assembly_open(self):
        assembly = _assembly(40)
        assembly["attachments"][3]["tack_state"] = TACK_NOT_TESTED
        result = inspect_attachment_material(assembly, _schedule())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["untested_attachment_ids"], ["ATT-004"])
        self.assertFalse(result["inspection_complete"])

    def test_a_short_record_set_leaves_the_assembly_open(self):
        result = inspect_attachment_material(_assembly(38, declared=40), _schedule())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            inspect_attachment_material(_assembly(6, declared=5), _schedule())

    def test_duplicate_attachment_ids_refused(self):
        assembly = _assembly(4)
        assembly["attachments"][3]["attachment_id"] = "ATT-001"
        with self.assertRaises(ValueError):
            inspect_attachment_material(assembly, _schedule())

    def test_non_mapping_assembly_refused(self):
        with self.assertRaises(ValueError):
            inspect_attachment_material("PVA-21", _schedule())

    def test_attachments_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            inspect_attachment_material(
                {
                    "assembly_id": "PVA-21",
                    "declared_attachment_count": 3,
                    "attachments": "three",
                },
                _schedule(),
            )

    def test_non_integer_declared_count_refused(self):
        assembly = _assembly(3)
        assembly["declared_attachment_count"] = "three"
        with self.assertRaises(ValueError):
            inspect_attachment_material(assembly, _schedule())

    def test_the_report_carries_the_adhesive_it_answered_to(self):
        result = inspect_attachment_material(_assembly(5), _schedule())
        self.assertEqual(result["adhesive_id"], "ADH-566")
        self.assertEqual(result["declared_attachment_count"], 5)
        self.assertEqual(result["inspected_count"], 5)


if __name__ == "__main__":
    unittest.main()
