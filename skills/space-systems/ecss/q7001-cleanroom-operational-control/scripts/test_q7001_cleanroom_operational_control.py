"""Contract test for the clean-area operational control leaf (stdlib unittest)."""

import unittest

from q7001_cleanroom_operational_control_logic import (
    ACTIVITY_EMISSION_PER_S,
    assess_gowning,
    assess_operational_control,
    class_ceiling_per_m3,
    occupant_generation_per_s,
    removal_flow_m3_per_s,
    required_gowning,
    steady_state_concentration_per_m3,
    supported_occupancy,
)

CLASS_EIGHT_GOWNING = ["coat", "hair-cover", "overshoes", "gloves"]


def occupant(oid="TECH-1", activity="seated-hand-work", gowning=None):
    return {
        "id": oid,
        "activity": activity,
        "gowning": list(CLASS_EIGHT_GOWNING) if gowning is None else list(gowning),
    }


def area(**kw):
    record = {
        "id": "AIT-HALL-2",
        "iso_class": 8,
        "volume_m3": 200.0,
        "air_changes_per_hour": 60.0,
        "transit_ceiling_per_hour": 12.0,
    }
    record.update(kw)
    return record


def session(**kw):
    record = {
        "occupants": [occupant("TECH-1"), occupant("TECH-2"), occupant("TECH-3")],
        "materials": ["cleanroom-wipe", "cleanroom-notebook"],
        "tools": [{"id": "TORQUE-DRIVER-7", "cleaning_record": "CLN-2211"}],
        "airlock_interlock_respected": True,
        "transits_per_hour": 4,
    }
    record.update(kw)
    return record


class TestFlowAndGeneration(unittest.TestCase):
    def test_the_removal_flow_is_the_air_changes_times_the_volume(self):
        self.assertAlmostEqual(removal_flow_m3_per_s(60.0, 200.0), 200.0 / 60.0, places=9)

    def test_a_zero_air_change_rate_raises(self):
        with self.assertRaises(ValueError):
            removal_flow_m3_per_s(0.0, 200.0)

    def test_a_negative_volume_raises(self):
        with self.assertRaises(ValueError):
            removal_flow_m3_per_s(60.0, -200.0)

    def test_generation_adds_over_the_occupants(self):
        total = occupant_generation_per_s([occupant("A"), occupant("B")])
        self.assertAlmostEqual(
            total, 2.0 * ACTIVITY_EMISSION_PER_S["seated-hand-work"], places=6
        )

    def test_a_heavier_activity_generates_more(self):
        light = occupant_generation_per_s([occupant("A", "still")])
        heavy = occupant_generation_per_s([occupant("A", "heavy-movement")])
        self.assertLess(light, heavy)

    def test_an_unknown_activity_raises(self):
        with self.assertRaises(ValueError):
            occupant_generation_per_s([occupant("A", "vibing")])

    def test_an_empty_occupant_list_raises(self):
        with self.assertRaises(ValueError):
            occupant_generation_per_s([])


class TestSteadyState(unittest.TestCase):
    def test_the_steady_state_is_generation_over_the_removal_flow(self):
        value = steady_state_concentration_per_m3(1.5e6, 60.0, 200.0)
        self.assertAlmostEqual(value, 1.5e6 / (200.0 / 60.0), places=6)

    def test_doubling_the_air_change_rate_halves_the_concentration(self):
        one = steady_state_concentration_per_m3(1.5e6, 60.0, 200.0)
        two = steady_state_concentration_per_m3(1.5e6, 120.0, 200.0)
        self.assertAlmostEqual(two, one / 2.0, places=6)

    def test_no_generation_gives_no_concentration(self):
        self.assertAlmostEqual(
            steady_state_concentration_per_m3(0.0, 60.0, 200.0), 0.0, places=12
        )

    def test_a_negative_generation_raises(self):
        with self.assertRaises(ValueError):
            steady_state_concentration_per_m3(-1.0, 60.0, 200.0)


class TestOccupancy(unittest.TestCase):
    def test_a_looser_class_supports_more_people(self):
        seven = supported_occupancy(7, "seated-hand-work", 60.0, 200.0)
        eight = supported_occupancy(8, "seated-hand-work", 60.0, 200.0)
        self.assertLess(seven, eight)

    def test_a_heavier_activity_supports_fewer_people(self):
        light = supported_occupancy(8, "seated-hand-work", 60.0, 200.0)
        heavy = supported_occupancy(8, "heavy-movement", 60.0, 200.0)
        self.assertLess(heavy, light)

    def test_a_safety_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            supported_occupancy(8, "seated-hand-work", 60.0, 200.0, safety_factor=0.5)

    def test_an_unknown_activity_for_occupancy_raises(self):
        with self.assertRaises(ValueError):
            supported_occupancy(8, "vibing", 60.0, 200.0)

    def test_a_class_outside_the_scheme_raises(self):
        with self.assertRaises(ValueError):
            class_ceiling_per_m3(12, 0.5)


class TestGowning(unittest.TestCase):
    def test_a_cleaner_class_demands_more_garments(self):
        self.assertGreater(len(required_gowning(5)), len(required_gowning(8)))

    def test_goggles_are_demanded_at_the_cleanest_band(self):
        self.assertIn("goggles", required_gowning(5))

    def test_the_loosest_band_does_not_demand_goggles(self):
        self.assertNotIn("goggles", required_gowning(8))

    def test_a_fully_gowned_occupant_has_no_shortfall(self):
        self.assertEqual(assess_gowning([occupant()], 8), [])

    def test_a_missing_garment_is_named(self):
        bare = occupant(gowning=["coat", "hair-cover", "overshoes"])
        shortfalls = assess_gowning([bare], 8)
        self.assertEqual(shortfalls[0]["missing_garments"], ["gloves"])

    def test_class_eight_gowning_is_short_for_a_class_five_area(self):
        shortfalls = assess_gowning([occupant()], 5)
        self.assertIn("coverall", shortfalls[0]["missing_garments"])

    def test_a_non_list_gowning_entry_raises(self):
        with self.assertRaises(ValueError):
            assess_gowning([{"id": "TECH-1", "gowning": "everything"}], 8)


class TestOperationalControl(unittest.TestCase):
    def test_a_controlled_session_is_clear(self):
        report = assess_operational_control(area(), session())
        self.assertTrue(report["clear"])
        self.assertEqual(report["verdict"], "session-under-control")
        self.assertEqual(report["occupant_count"], 3)

    def test_the_predicted_concentration_sits_under_the_ceiling(self):
        report = assess_operational_control(area(), session())
        self.assertLess(report["class_utilization_fraction"], 1.0)

    def test_an_overloaded_room_is_reported(self):
        crowd = [occupant("T%d" % i, "heavy-movement") for i in range(10)]
        report = assess_operational_control(area(), session(occupants=crowd))
        self.assertIn(
            "predicted-working-concentration-above-the-class-ceiling",
            report["findings"],
        )

    def test_a_headcount_above_capacity_is_reported(self):
        crowd = [occupant("T%d" % i, "walking") for i in range(8)]
        report = assess_operational_control(area(), session(occupants=crowd))
        self.assertIn(
            "headcount-above-the-occupancy-the-ventilation-supports",
            report["findings"],
        )

    def test_a_gowning_shortfall_is_reported_with_the_garment(self):
        bare = occupant("TECH-1", gowning=["coat", "hair-cover", "overshoes"])
        report = assess_operational_control(area(), session(occupants=[bare]))
        self.assertIn("gowning-short-of-what-the-class-demands", report["findings"])
        self.assertEqual(
            report["gowning_shortfalls"][0]["missing_garments"], ["gloves"]
        )

    def test_a_refused_material_is_named(self):
        report = assess_operational_control(
            area(), session(materials=["cleanroom-wipe", "cardboard"])
        )
        self.assertIn("material-not-permitted-in-the-clean-area", report["findings"])
        self.assertEqual(report["refused_materials_present"], ["cardboard"])

    def test_a_tool_without_a_cleaning_record_is_named(self):
        report = assess_operational_control(
            area(), session(tools=[{"id": "SHIM-SET-3"}])
        )
        self.assertIn("tool-admitted-with-no-cleaning-record", report["findings"])
        self.assertEqual(report["tools_without_a_cleaning_record"], ["SHIM-SET-3"])

    def test_a_defeated_interlock_is_reported(self):
        report = assess_operational_control(
            area(), session(airlock_interlock_respected=False)
        )
        self.assertIn(
            "airlock-interlock-defeated-during-the-session", report["findings"]
        )

    def test_a_transit_rate_above_the_ceiling_is_reported(self):
        report = assess_operational_control(area(), session(transits_per_hour=30))
        self.assertIn(
            "transit-rate-above-what-the-airlock-was-sized-for", report["findings"]
        )

    def test_the_activity_mix_is_reported(self):
        mixed = [occupant("A", "still"), occupant("B", "walking")]
        report = assess_operational_control(area(), session(occupants=mixed))
        self.assertEqual(report["activity_mix"], ["still", "walking"])

    def test_duplicate_occupant_ids_raise(self):
        with self.assertRaises(ValueError):
            assess_operational_control(
                area(), session(occupants=[occupant("A"), occupant("A")])
            )

    def test_a_session_with_no_occupants_raises(self):
        with self.assertRaises(ValueError):
            assess_operational_control(area(), session(occupants=[]))

    def test_an_area_with_no_class_raises(self):
        record = area()
        del record["iso_class"]
        with self.assertRaises(ValueError):
            assess_operational_control(record, session())

    def test_a_non_mapping_session_raises(self):
        with self.assertRaises(ValueError):
            assess_operational_control(area(), "three people and a trolley")

    def test_a_negative_transit_count_raises(self):
        with self.assertRaises(ValueError):
            assess_operational_control(area(), session(transits_per_hour=-1))


if __name__ == "__main__":
    unittest.main()
