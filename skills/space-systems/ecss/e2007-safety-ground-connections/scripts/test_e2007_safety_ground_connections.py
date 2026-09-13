#!/usr/bin/env python3
"""Gate 3 contract test for e2007-safety-ground-connections.

Offline, deterministic, stdlib unittest only.
"""

import unittest

import e2007_safety_ground_connections_logic as logic


def terminal_provision(studs=2):
    return {"terminal_studs": studs}


def pin_provision(pins=("A1", "B7")):
    return {"earth_pin_designations": list(pins)}


def base_segments():
    return [
        {"resistance_ohm": 0.01},
        {"resistance_ohm": 0.02},
        {"resistance_ohm": 0.03},
    ]


class ProvisionCategoryTests(unittest.TestCase):
    def test_terminal_stud_gives_a_terminal_provision(self):
        self.assertEqual(
            logic.categorize_safety_ground_provision(terminal_provision()),
            "protective-earth-terminal",
        )

    def test_connector_pin_gives_a_pin_provision(self):
        self.assertEqual(
            logic.categorize_safety_ground_provision(pin_provision()),
            "protective-earth-pin",
        )

    def test_mounting_base_bond_is_its_own_provision(self):
        self.assertEqual(
            logic.categorize_safety_ground_provision(
                {"mounting_base_bonded": True}
            ),
            "mounting-base-bond",
        )

    def test_no_declared_hardware_is_uncategorized_as_unbonded(self):
        self.assertEqual(
            logic.categorize_safety_ground_provision({}), "unbonded"
        )

    def test_terminal_wins_over_a_pin_when_both_are_declared(self):
        record = {"terminal_studs": 1, "earth_pin_designations": ["A1"]}
        self.assertEqual(
            logic.categorize_safety_ground_provision(record),
            "protective-earth-terminal",
        )

    def test_every_category_is_in_the_declared_tuple(self):
        for record in (terminal_provision(), pin_provision(),
                       {"mounting_base_bonded": True}, {}):
            self.assertIn(
                logic.categorize_safety_ground_provision(record),
                logic.PROVISION_CATEGORIES,
            )

    def test_non_mapping_record_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision(["terminal_studs", 2])

    def test_negative_terminal_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision({"terminal_studs": -1})

    def test_pin_designation_string_instead_of_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision(
                {"earth_pin_designations": "A1"}
            )

    def test_blank_pin_designation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision(
                {"earth_pin_designations": ["A1", "  "]}
            )

    def test_repeated_pin_designation_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision(
                {"earth_pin_designations": ["A1", "A1"]}
            )

    def test_non_boolean_mounting_base_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.categorize_safety_ground_provision(
                {"mounting_base_bonded": "yes"}
            )


class ConductorSizingTests(unittest.TestCase):
    def test_adiabatic_area_follows_current_and_square_root_of_time(self):
        area = logic.required_earth_conductor_area(286.0, 1.0, "copper-pvc")
        self.assertAlmostEqual(area, 2.0, places=12)

    def test_area_grows_with_the_square_root_of_clearing_time(self):
        short = logic.required_earth_conductor_area(200.0, 0.25)
        long = logic.required_earth_conductor_area(200.0, 1.0)
        self.assertAlmostEqual(long, short * 2.0, places=12)

    def test_area_grows_linearly_with_fault_current(self):
        low = logic.required_earth_conductor_area(100.0, 0.5)
        high = logic.required_earth_conductor_area(300.0, 0.5)
        self.assertAlmostEqual(high, low * 3.0, places=12)

    def test_a_better_material_constant_needs_less_area(self):
        pvc = logic.required_earth_conductor_area(500.0, 1.0, "copper-pvc")
        xl = logic.required_earth_conductor_area(500.0, 1.0,
                                                 "copper-cross-linked")
        self.assertLess(xl, pvc)

    def test_aluminium_needs_more_area_than_copper(self):
        copper = logic.required_earth_conductor_area(500.0, 1.0, "copper-pvc")
        aluminium = logic.required_earth_conductor_area(500.0, 1.0,
                                                        "aluminium-pvc")
        self.assertGreater(aluminium, copper)

    def test_adequate_conductor_raises_no_finding(self):
        result = logic.check_earth_conductor_sizing(4.0, 286.0, 1.0)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_conductor_exactly_at_the_required_area_passes(self):
        required = logic.required_earth_conductor_area(286.0, 1.0)
        result = logic.check_earth_conductor_sizing(required, 286.0, 1.0)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_operating_current_sizing_fails_the_fault_case(self):
        result = logic.check_earth_conductor_sizing(0.5, 1200.0, 0.8)
        self.assertFalse(result["adequate"])
        self.assertIn("protective-earth-conductor-undersized",
                      result["findings"][0])

    def test_zero_clearing_time_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_earth_conductor_area(286.0, 0.0)

    def test_negative_fault_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_earth_conductor_area(-10.0, 1.0)

    def test_unknown_conductor_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_earth_conductor_area(286.0, 1.0, "tin-plated-steel")

    def test_zero_installed_area_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_earth_conductor_sizing(0.0, 286.0, 1.0)


class PathResistanceTests(unittest.TestCase):
    def test_conductor_resistance_follows_resistivity_length_and_area(self):
        value = logic.conductor_resistance(2.0, 4.0)
        self.assertAlmostEqual(value, 1.72e-8 * 2.0 / 4.0e-6, places=12)

    def test_doubling_the_area_halves_the_resistance(self):
        thin = logic.conductor_resistance(1.5, 2.0)
        thick = logic.conductor_resistance(1.5, 4.0)
        self.assertAlmostEqual(thick, thin / 2.0, places=12)

    def test_measured_segment_is_taken_as_measured(self):
        self.assertAlmostEqual(
            logic.segment_resistance({"resistance_ohm": 0.004}), 0.004,
            places=12,
        )

    def test_geometry_segment_is_resolved(self):
        value = logic.segment_resistance({"length_m": 1.0, "area_mm2": 2.0})
        self.assertAlmostEqual(value, 1.72e-8 / 2.0e-6, places=12)

    def test_interfaces_are_summed_with_the_conductor_runs(self):
        segments = [{"length_m": 1.0, "area_mm2": 2.0},
                    {"resistance_ohm": 0.005}]
        total = logic.safety_ground_path_resistance(segments)
        self.assertAlmostEqual(total, 1.72e-8 / 2.0e-6 + 0.005, places=12)

    def test_path_under_the_limit_raises_no_finding(self):
        total = logic.safety_ground_path_resistance(base_segments())
        result = logic.check_path_resistance(total, 0.1)
        self.assertTrue(result["within_limit"])
        self.assertEqual(result["findings"], [])

    def test_representation_error_at_the_limit_is_absorbed(self):
        # 0.5 + 1.6 + 7.9 milliohm is exactly on a 10 milliohm interface
        # limit, but the running sum lands a few ULPs above it; a path that
        # is physically compliant must not be graded as an exceedance.
        segments = [{"resistance_ohm": 0.0005}, {"resistance_ohm": 0.0016},
                    {"resistance_ohm": 0.0079}]
        total = logic.safety_ground_path_resistance(segments)
        self.assertGreater(total, 0.01)
        result = logic.check_path_resistance(total, 0.01)
        self.assertTrue(result["within_limit"])
        self.assertEqual(result["findings"], [])

    def test_path_over_the_limit_is_flagged(self):
        result = logic.check_path_resistance(0.25, 0.1)
        self.assertFalse(result["within_limit"])
        self.assertIn("safety-ground-path-resistance-exceeded",
                      result["findings"][0])

    def test_empty_segment_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.safety_ground_path_resistance([])

    def test_segment_list_given_as_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.safety_ground_path_resistance({"resistance_ohm": 0.01})

    def test_segment_with_neither_measurement_nor_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.segment_resistance({"note": "strap into the bench"})

    def test_segment_with_both_measurement_and_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.segment_resistance({"resistance_ohm": 0.01,
                                      "length_m": 1.0, "area_mm2": 2.0})

    def test_negative_measured_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.segment_resistance({"resistance_ohm": -0.01})

    def test_zero_area_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.segment_resistance({"length_m": 1.0, "area_mm2": 0.0})

    def test_zero_path_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_path_resistance(0.01, 0.0)


class ProvisionComparisonTests(unittest.TestCase):
    def test_matching_terminal_provisions_raise_no_finding(self):
        result = logic.compare_safety_ground_provision(terminal_provision(),
                                                       terminal_provision())
        self.assertEqual(result["findings"], [])

    def test_matching_pin_provisions_raise_no_finding(self):
        result = logic.compare_safety_ground_provision(pin_provision(),
                                                       pin_provision())
        self.assertEqual(result["findings"], [])

    def test_pin_substituted_for_a_terminal_is_a_mismatch(self):
        result = logic.compare_safety_ground_provision(terminal_provision(),
                                                       pin_provision())
        self.assertIn("safety-ground-provision-mismatch",
                      " ".join(result["findings"]))

    def test_terminal_count_mismatch_is_flagged(self):
        result = logic.compare_safety_ground_provision(
            terminal_provision(2), terminal_provision(1)
        )
        self.assertIn("protective-earth-terminal-count-mismatch",
                      " ".join(result["findings"]))

    def test_earth_pin_missing_on_the_bench_is_flagged(self):
        result = logic.compare_safety_ground_provision(
            pin_provision(("A1", "B7")), pin_provision(("A1",))
        )
        joined = " ".join(result["findings"])
        self.assertIn("protective-earth-pin-missing-on-bench", joined)
        self.assertIn("B7", joined)

    def test_earth_pin_added_on_the_bench_is_flagged(self):
        result = logic.compare_safety_ground_provision(
            pin_provision(("A1",)), pin_provision(("A1", "C3"))
        )
        joined = " ".join(result["findings"])
        self.assertIn("protective-earth-pin-added-on-bench", joined)
        self.assertIn("C3", joined)

    def test_pin_order_does_not_matter(self):
        result = logic.compare_safety_ground_provision(
            pin_provision(("A1", "B7")), pin_provision(("B7", "A1"))
        )
        self.assertEqual(result["findings"], [])

    def test_absent_bench_provision_is_flagged(self):
        result = logic.compare_safety_ground_provision(terminal_provision(), {})
        self.assertIn("bench-safety-ground-provision-absent",
                      " ".join(result["findings"]))

    def test_absent_flight_provision_is_flagged(self):
        result = logic.compare_safety_ground_provision({}, terminal_provision())
        self.assertIn("flight-safety-ground-provision-absent",
                      " ".join(result["findings"]))

    def test_both_sides_absent_reports_both(self):
        result = logic.compare_safety_ground_provision({}, {})
        self.assertEqual(len(result["findings"]), 2)


class AssessmentTests(unittest.TestCase):
    def base_setup(self, **overrides):
        setup = {
            "unit_id": "PCDU-1",
            "flight_provision": terminal_provision(2),
            "bench_provision": terminal_provision(2),
            "conductor": {"area_mm2": 4.0, "family": "copper-pvc"},
            "fault_current_a": 286.0,
            "clearing_time_s": 1.0,
            "path_segments": base_segments(),
            "path_limit_ohm": 0.1,
        }
        setup.update(overrides)
        return setup

    def test_a_mirrored_and_sized_provision_passes(self):
        result = logic.assess_safety_ground_connections(self.base_setup())
        self.assertTrue(result["mirrors_installation"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["bench_category"],
                         "protective-earth-terminal")

    def test_improvised_bench_bond_is_flagged(self):
        setup = self.base_setup(
            bench_provision={"mounting_base_bonded": True}
        )
        result = logic.assess_safety_ground_connections(setup)
        self.assertFalse(result["mirrors_installation"])
        self.assertIn("safety-ground-provision-mismatch",
                      " ".join(result["findings"]))

    def test_undersized_conductor_is_flagged(self):
        setup = self.base_setup(conductor={"area_mm2": 0.5},
                                fault_current_a=1200.0,
                                clearing_time_s=0.8)
        result = logic.assess_safety_ground_connections(setup)
        self.assertIn("protective-earth-conductor-undersized",
                      " ".join(result["findings"]))
        self.assertFalse(result["conductor_sizing"]["adequate"])

    def test_excessive_path_resistance_is_flagged(self):
        setup = self.base_setup(
            path_segments=[{"resistance_ohm": 0.4}]
        )
        result = logic.assess_safety_ground_connections(setup)
        self.assertIn("safety-ground-path-resistance-exceeded",
                      " ".join(result["findings"]))

    def test_shared_signal_return_is_flagged(self):
        setup = self.base_setup(carries_signal_return=True)
        result = logic.assess_safety_ground_connections(setup)
        self.assertIn("protective-earth-shared-with-signal-return",
                      " ".join(result["findings"]))

    def test_several_defects_are_all_reported(self):
        setup = self.base_setup(
            bench_provision=pin_provision(("A1",)),
            conductor={"area_mm2": 0.4},
            fault_current_a=1500.0,
            clearing_time_s=1.0,
            carries_signal_return=True,
        )
        result = logic.assess_safety_ground_connections(setup)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_path_resistance_total_is_reported(self):
        result = logic.assess_safety_ground_connections(self.base_setup())
        self.assertAlmostEqual(result["path_resistance"]["total_ohm"], 0.06,
                               places=9)

    def test_missing_unit_id_is_rejected(self):
        setup = self.base_setup()
        del setup["unit_id"]
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections(setup)

    def test_blank_unit_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections(
                self.base_setup(unit_id="  ")
            )

    def test_missing_bench_provision_is_rejected(self):
        setup = self.base_setup()
        del setup["bench_provision"]
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections(setup)

    def test_missing_path_segments_are_rejected(self):
        setup = self.base_setup()
        del setup["path_segments"]
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections(setup)

    def test_non_boolean_signal_return_flag_is_rejected(self):
        setup = self.base_setup(carries_signal_return="shared")
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections(setup)

    def test_non_mapping_setup_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_safety_ground_connections("PCDU-1")


if __name__ == "__main__":
    unittest.main()
