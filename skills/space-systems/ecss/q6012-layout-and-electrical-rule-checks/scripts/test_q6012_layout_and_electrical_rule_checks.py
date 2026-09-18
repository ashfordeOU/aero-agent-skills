"""Contract tests for the clause 7.2.11 layout and electrical rule checks.

Each workflow step - deck and shape validation, the geometry checks, the
electrical checks, the waiver step and the grouped verdict - has its own cases,
including the shapes drawn exactly on a rule, which is where a rule checker
stops being trustworthy if the comparison is written strictly. Offline, stdlib
unittest only.
"""

import math
import unittest

from q6012_layout_and_electrical_rule_checks_logic import (
    GEOMETRY_TOLERANCE,
    apply_waivers,
    check_connectivity,
    check_current_capacity,
    check_enclosure,
    check_minimum_spacing,
    check_minimum_width,
    enclosure_margin_um,
    group_findings,
    rectangle_separation_um,
    run_rule_checks,
    validate_net,
    validate_rule_deck,
    validate_shape,
)

DECK = {
    "layers": {
        "metal1": {"min_width_um": 4.0, "min_spacing_um": 4.0,
                   "current_capacity_ma_per_um": 0.6},
        "metal2": {"min_width_um": 6.0, "min_spacing_um": 6.0,
                   "current_capacity_ma_per_um": 1.0},
        "via": {"min_width_um": 2.0, "min_spacing_um": 3.0},
    },
    "enclosures": [{"inner": "via", "outer": "metal1", "min_enclosure_um": 1.0}],
}


def rect(ident, layer, net, x, y, width, height):
    return {"id": ident, "layer": layer, "net": net, "x_um": x, "y_um": y,
            "width_um": width, "height_um": height}


# A clean layout: two metal1 runs drawn exactly on the 4 um spacing rule, and a
# via sitting 2 um inside the signal run, exactly on its own 2 um width rule.
M1A = rect("m1a", "metal1", "rf_in", 0.0, 0.0, 20.0, 6.0)
M1B = rect("m1b", "metal1", "gnd", 24.0, 0.0, 20.0, 6.0)
VIA = rect("v1", "via", "rf_in", 2.0, 2.0, 2.0, 2.0)

NETS = [
    {"name": "rf_in", "current_ma": 3.0, "connection_points": 2},
    {"name": "gnd", "current_ma": 0.0, "connection_points": 3},
]


def layout(shapes=None, nets=None):
    return {"shapes": list(shapes if shapes is not None else [M1A, M1B, VIA]),
            "nets": list(nets if nets is not None else NETS)}


class ValidationTests(unittest.TestCase):
    def test_shape_normalises(self):
        shape = validate_shape(rect("m1a", "metal1", "rf_in", 0, 0, 20, 6))
        self.assertEqual(shape["width_um"], 20.0)

    def test_zero_width_shape_rejected(self):
        with self.assertRaises(ValueError):
            validate_shape(rect("m1a", "metal1", "rf_in", 0.0, 0.0, 0.0, 6.0))

    def test_negative_coordinate_allowed(self):
        shape = validate_shape(rect("m1a", "metal1", "rf_in", -10.0, -4.0, 20.0, 6.0))
        self.assertAlmostEqual(shape["x_um"], -10.0, places=9)

    def test_blank_net_rejected(self):
        with self.assertRaises(ValueError):
            validate_shape(rect("m1a", "metal1", "  ", 0.0, 0.0, 20.0, 6.0))

    def test_missing_shape_key_rejected(self):
        broken = rect("m1a", "metal1", "rf_in", 0.0, 0.0, 20.0, 6.0)
        del broken["layer"]
        with self.assertRaises(ValueError):
            validate_shape(broken)

    def test_deck_normalises(self):
        deck = validate_rule_deck(DECK)
        self.assertAlmostEqual(deck["layers"]["metal1"]["min_spacing_um"], 4.0,
                               places=9)
        self.assertEqual(len(deck["enclosures"]), 1)

    def test_empty_layer_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_deck({"layers": {}})

    def test_layer_without_spacing_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_deck({"layers": {"metal1": {"min_width_um": 4.0}}})

    def test_enclosure_naming_one_layer_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule_deck({
                "layers": DECK["layers"],
                "enclosures": [{"inner": "via", "outer": "via",
                                "min_enclosure_um": 1.0}],
            })

    def test_net_defaults_to_two_connection_points(self):
        net = validate_net({"name": "rf_in"})
        self.assertEqual(net["connection_points"], 2)
        self.assertAlmostEqual(net["current_ma"], 0.0, places=9)

    def test_negative_connection_points_rejected(self):
        with self.assertRaises(ValueError):
            validate_net({"name": "rf_in", "connection_points": -1})


class GeometryPrimitiveTests(unittest.TestCase):
    def test_separation_along_one_axis(self):
        self.assertAlmostEqual(rectangle_separation_um(M1A, M1B), 4.0, places=9)

    def test_touching_rectangles_are_zero_apart(self):
        self.assertAlmostEqual(
            rectangle_separation_um(M1A, rect("x", "metal1", "gnd", 20.0, 0.0,
                                              10.0, 6.0)),
            0.0, places=9,
        )

    def test_overlapping_rectangles_are_zero_apart(self):
        self.assertAlmostEqual(
            rectangle_separation_um(M1A, rect("x", "metal1", "gnd", 10.0, 0.0,
                                              10.0, 6.0)),
            0.0, places=9,
        )

    def test_diagonal_separation_is_the_corner_distance(self):
        a = rect("a", "metal1", "n1", 0.0, 0.0, 4.0, 4.0)
        b = rect("b", "metal1", "n2", 7.0, 7.0, 4.0, 4.0)
        self.assertAlmostEqual(rectangle_separation_um(a, b), math.hypot(3.0, 3.0),
                               places=9)

    def test_enclosure_margin_is_the_tightest_side(self):
        self.assertAlmostEqual(enclosure_margin_um(VIA, M1A), 2.0, places=9)

    def test_an_uncovered_inner_shape_has_a_negative_margin(self):
        loose = rect("v2", "via", "rf_in", -1.0, 2.0, 2.0, 2.0)
        self.assertLess(enclosure_margin_um(loose, M1A), 0.0)


class MinimumWidthTests(unittest.TestCase):
    def test_a_compliant_layout_reports_nothing(self):
        self.assertEqual(check_minimum_width([M1A, M1B, VIA], DECK), [])

    def test_a_shape_exactly_on_the_width_rule_passes(self):
        exact = rect("m1c", "metal1", "gnd", 0.0, 40.0, 20.0, 4.0)
        self.assertEqual(check_minimum_width([exact], DECK), [])

    def test_a_narrow_shape_is_an_error(self):
        narrow = rect("m1c", "metal1", "gnd", 0.0, 40.0, 20.0, 3.0)
        findings = check_minimum_width([narrow], DECK)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "min-width")
        self.assertEqual(findings[0]["severity"], "error")

    def test_the_narrow_axis_governs_not_the_long_one(self):
        narrow = rect("m1c", "metal1", "gnd", 0.0, 40.0, 3.0, 200.0)
        self.assertEqual(len(check_minimum_width([narrow], DECK)), 1)

    def test_a_shape_on_an_undefined_layer_is_an_error(self):
        stray = rect("m3a", "metal3", "gnd", 0.0, 40.0, 20.0, 6.0)
        findings = check_minimum_width([stray], DECK)
        self.assertEqual(findings[0]["rule"], "unknown-layer")


class MinimumSpacingTests(unittest.TestCase):
    def test_shapes_exactly_on_the_spacing_rule_pass(self):
        self.assertEqual(check_minimum_spacing([M1A, M1B], DECK), [])

    def test_shapes_closer_than_the_rule_are_an_error(self):
        close = rect("m1b", "metal1", "gnd", 22.0, 0.0, 20.0, 6.0)
        findings = check_minimum_spacing([M1A, close], DECK)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["shapes"], ("m1a", "m1b"))

    def test_same_net_metal_may_touch(self):
        same = rect("m1b", "metal1", "rf_in", 20.0, 0.0, 20.0, 6.0)
        self.assertEqual(check_minimum_spacing([M1A, same], DECK), [])

    def test_different_layers_do_not_space_against_each_other(self):
        other = rect("m2a", "metal2", "gnd", 21.0, 0.0, 20.0, 8.0)
        self.assertEqual(check_minimum_spacing([M1A, other], DECK), [])

    def test_each_offending_pair_is_reported_once(self):
        b = rect("m1b", "metal1", "gnd", 21.0, 0.0, 6.0, 6.0)
        c = rect("m1c", "metal1", "vdd", 28.0, 0.0, 6.0, 6.0)
        findings = check_minimum_spacing([M1A, b, c], DECK)
        self.assertEqual(len(findings), 2)


class EnclosureTests(unittest.TestCase):
    def test_a_well_enclosed_via_reports_nothing(self):
        self.assertEqual(check_enclosure([M1A, VIA], DECK), [])

    def test_a_via_exactly_on_the_enclosure_rule_passes(self):
        exact = rect("v1", "via", "rf_in", 1.0, 1.0, 2.0, 2.0)
        self.assertEqual(check_enclosure([M1A, exact], DECK), [])

    def test_a_via_hanging_over_the_metal_edge_is_an_error(self):
        loose = rect("v1", "via", "rf_in", -1.0, 2.0, 2.0, 2.0)
        findings = check_enclosure([M1A, loose], DECK)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "enclosure")

    def test_a_via_with_no_metal_at_all_is_an_error(self):
        findings = check_enclosure([VIA], DECK)
        self.assertEqual(len(findings), 1)
        self.assertIn("no metal1 shape", findings[0]["message"])

    def test_the_best_covering_metal_is_the_one_judged(self):
        far = rect("m1z", "metal1", "gnd", 500.0, 500.0, 20.0, 6.0)
        self.assertEqual(check_enclosure([far, M1A, VIA], DECK), [])


class CurrentCapacityTests(unittest.TestCase):
    def test_a_net_inside_its_capacity_reports_nothing(self):
        self.assertEqual(check_current_capacity([M1A, M1B, VIA], NETS, DECK), [])

    def test_a_net_exactly_on_its_capacity_passes(self):
        nets = [{"name": "rf_in", "current_ma": 3.6, "connection_points": 2}]
        self.assertEqual(check_current_capacity([M1A], nets, DECK), [])

    def test_a_net_over_its_capacity_is_an_error(self):
        nets = [{"name": "rf_in", "current_ma": 5.0, "connection_points": 2}]
        findings = check_current_capacity([M1A], nets, DECK)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "error")

    def test_the_narrowest_metal_on_the_net_governs(self):
        neck = rect("m1n", "metal1", "rf_in", 0.0, 10.0, 20.0, 4.0)
        nets = [{"name": "rf_in", "current_ma": 3.0, "connection_points": 2}]
        findings = check_current_capacity([M1A, neck], nets, DECK)
        self.assertEqual(len(findings), 1)
        self.assertIn("m1n", findings[0]["message"])

    def test_a_current_carrying_net_with_no_rated_metal_is_a_warning(self):
        nets = [{"name": "rf_in", "current_ma": 3.0, "connection_points": 2}]
        findings = check_current_capacity([VIA], nets, DECK)
        self.assertEqual(findings[0]["severity"], "warning")

    def test_a_net_declaring_no_current_is_not_checked(self):
        nets = [{"name": "gnd", "current_ma": 0.0, "connection_points": 3}]
        self.assertEqual(check_current_capacity([M1B], nets, DECK), [])


class ConnectivityTests(unittest.TestCase):
    def test_a_consistent_netlist_reports_nothing(self):
        self.assertEqual(check_connectivity([M1A, M1B, VIA], NETS), [])

    def test_a_declared_but_undrawn_net_is_an_error(self):
        nets = NETS + [{"name": "vdd", "current_ma": 0.0, "connection_points": 2}]
        findings = check_connectivity([M1A, M1B, VIA], nets)
        self.assertEqual(len(findings), 1)
        self.assertIn("vdd", findings[0]["message"])

    def test_a_drawn_but_undeclared_net_is_an_error(self):
        stray = rect("m1c", "metal1", "vdd", 0.0, 40.0, 20.0, 6.0)
        findings = check_connectivity([M1A, M1B, VIA, stray], NETS)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["shapes"], ("m1c",))

    def test_a_single_ended_net_is_a_floating_node_warning(self):
        nets = [{"name": "rf_in", "current_ma": 0.0, "connection_points": 1},
                {"name": "gnd", "current_ma": 0.0, "connection_points": 3}]
        findings = check_connectivity([M1A, M1B, VIA], nets)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "warning")

    def test_a_net_declared_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            check_connectivity([M1A], NETS + [NETS[0]])


class WaiverTests(unittest.TestCase):
    def _spacing_finding(self):
        close = rect("m1b", "metal1", "gnd", 22.0, 0.0, 20.0, 6.0)
        return check_minimum_spacing([M1A, close], DECK)

    def test_no_waivers_leaves_every_finding_open(self):
        open_findings, waived = apply_waivers(self._spacing_finding(), None)
        self.assertEqual(len(open_findings), 1)
        self.assertEqual(waived, [])

    def test_a_rule_wide_waiver_covers_the_finding(self):
        open_findings, waived = apply_waivers(
            self._spacing_finding(), [{"rule": "min-spacing", "reference": "W-01"}]
        )
        self.assertEqual(open_findings, [])
        self.assertEqual(waived[0]["severity"], "waived")
        self.assertEqual(waived[0]["waiver_reference"], "W-01")

    def test_a_shape_specific_waiver_covers_only_its_shapes(self):
        open_findings, waived = apply_waivers(
            self._spacing_finding(),
            [{"rule": "min-spacing", "shapes": ["m1a", "m1z"]}],
        )
        self.assertEqual(len(open_findings), 1)
        self.assertEqual(waived, [])

    def test_a_waiver_for_another_rule_does_not_cover_it(self):
        open_findings, _ = apply_waivers(
            self._spacing_finding(), [{"rule": "min-width"}]
        )
        self.assertEqual(len(open_findings), 1)

    def test_a_waiver_without_a_rule_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_waivers(self._spacing_finding(), [{"reference": "W-01"}])


class GroupingTests(unittest.TestCase):
    def test_findings_group_by_severity_and_rule(self):
        grouped = group_findings([
            {"rule": "min-width", "severity": "error"},
            {"rule": "min-spacing", "severity": "error"},
            {"rule": "connectivity", "severity": "warning"},
        ])
        self.assertEqual(grouped["by_severity"]["error"], 2)
        self.assertEqual(grouped["by_rule"]["connectivity"], 1)

    def test_errors_are_ordered_ahead_of_warnings(self):
        grouped = group_findings([
            {"rule": "connectivity", "severity": "warning"},
            {"rule": "min-width", "severity": "error"},
        ])
        self.assertEqual(list(grouped["by_severity"])[0], "error")

    def test_a_finding_without_a_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            group_findings([{"rule": "min-width"}])


class RunRuleChecksTests(unittest.TestCase):
    def test_a_clean_layout_comes_back_clean(self):
        result = run_rule_checks(layout(), DECK)
        self.assertTrue(result["clean"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["error_count"], 0)

    def test_every_broken_rule_is_collected_in_one_run(self):
        narrow = rect("m1c", "metal1", "vdd", 0.0, 40.0, 20.0, 3.0)
        result = run_rule_checks(layout(shapes=[M1A, M1B, VIA, narrow]), DECK)
        rules = {f["rule"] for f in result["findings"]}
        self.assertIn("min-width", rules)
        self.assertIn("connectivity", rules)
        self.assertFalse(result["clean"])

    def test_findings_come_back_in_a_stable_order(self):
        narrow = rect("m1c", "metal1", "vdd", 0.0, 40.0, 20.0, 3.0)
        first = run_rule_checks(layout(shapes=[M1A, M1B, VIA, narrow]), DECK)
        second = run_rule_checks(layout(shapes=[narrow, VIA, M1B, M1A]), DECK)
        self.assertEqual([f["rule"] for f in first["findings"]],
                         [f["rule"] for f in second["findings"]])

    def test_a_waived_finding_is_reported_and_not_deleted(self):
        close = rect("m1b", "metal1", "gnd", 22.0, 0.0, 20.0, 6.0)
        result = run_rule_checks(
            layout(shapes=[M1A, close, VIA]), DECK,
            [{"rule": "min-spacing", "reference": "W-07"}],
        )
        self.assertTrue(result["clean"])
        self.assertEqual(len(result["waived"]), 1)
        self.assertEqual(result["grouped"]["by_severity"]["waived"], 1)

    def test_a_duplicate_shape_id_is_rejected(self):
        with self.assertRaises(ValueError):
            run_rule_checks(layout(shapes=[M1A, M1A]), DECK)

    def test_an_empty_layout_is_rejected(self):
        with self.assertRaises(ValueError):
            run_rule_checks({"shapes": []}, DECK)

    def test_a_layout_without_shapes_key_is_rejected(self):
        with self.assertRaises(ValueError):
            run_rule_checks({"nets": NETS}, DECK)

    def test_a_layout_with_no_netlist_reports_undeclared_nets(self):
        result = run_rule_checks({"shapes": [M1A]}, DECK)
        self.assertFalse(result["clean"])
        self.assertEqual(result["findings"][0]["rule"], "connectivity")

    def test_the_tolerance_stays_negligible_against_the_rules(self):
        self.assertLess(GEOMETRY_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
