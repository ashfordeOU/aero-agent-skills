"""Contract tests for the clause 5.4.5.1.1 protection line voltage drop budget."""

import unittest

from e2020_line_voltage_drop_budget_logic import (
    COPPER_ALPHA_PER_K,
    DEFAULT_LINE_DROP_POLICY,
    DROP_EXCEEDS_BUDGET,
    DROP_MARGIN_THIN,
    DROP_WITHIN_BUDGET,
    ELEMENT_BLOCKING_DEVICE,
    ELEMENT_CONNECTOR,
    ELEMENT_HARNESS,
    ELEMENT_SENSE_SHUNT,
    ELEMENT_SWITCH,
    allowed_drop_v,
    assess_line_voltage_drop,
    categorize_element_kind,
    class_entry,
    contributor_drop,
    dominant_kind,
    hot_resistance_ohm,
    line_drop_breakdown,
    validate_class_table,
    validate_line_drop_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LINE_DROP_POLICY)
    policy.update(overrides)
    return policy


def _table(allowed_drop_v_value=0.6, **overrides):
    entry = {
        "name": "class-2",
        "class_current_a": 1.5,
        "allowed_drop_v": allowed_drop_v_value,
    }
    entry.update(overrides)
    return [
        {"name": "class-1", "class_current_a": 0.5, "allowed_drop_v": 0.4},
        entry,
    ]


def _contributors():
    return [
        {
            "id": "lcl-switch",
            "kind": ELEMENT_SWITCH,
            "resistance_ohm": 0.040,
            "alpha_per_k": 0.0,
        },
        {
            "id": "harness-out",
            "kind": ELEMENT_HARNESS,
            "resistance_ohm": 0.080,
            "alpha_per_k": 0.0,
        },
        {
            "id": "connector-j3",
            "kind": ELEMENT_CONNECTOR,
            "resistance_ohm": 0.010,
            "alpha_per_k": 0.0,
        },
        {
            "id": "blocking-diode",
            "kind": ELEMENT_BLOCKING_DEVICE,
            "forward_drop_v": 0.150,
        },
    ]


def _design(**overrides):
    design = {
        "class_table": _table(),
        "class_name": "class-2",
        "bus_voltage_v": 28.0,
        "contributors": _contributors(),
    }
    design.update(overrides)
    return design


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_line_drop_policy(DEFAULT_LINE_DROP_POLICY),
            DEFAULT_LINE_DROP_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_drop_policy("half a volt")

    def test_a_hot_case_below_the_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_drop_policy(_policy(hot_temperature_c=-10.0))

    def test_a_tolerance_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_drop_policy(_policy(tolerance_factor=0.95))

    def test_a_tolerance_factor_of_exactly_one_accepted(self):
        self.assertIsNotNone(validate_line_drop_policy(_policy(tolerance_factor=1.0)))

    def test_a_thin_margin_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_drop_policy(_policy(thin_margin_fraction=1.0))

    def test_a_zero_dominant_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_drop_policy(_policy(dominant_share_fraction=0.0))


class ClassTableTests(unittest.TestCase):
    def test_a_sound_table_validates(self):
        entries = validate_class_table(_table())
        self.assertEqual(len(entries), 2)

    def test_an_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table([])

    def test_a_class_named_twice_rejected(self):
        table = _table()
        table[0]["name"] = "class-2"
        with self.assertRaises(ValueError):
            validate_class_table(table)

    def test_a_non_positive_class_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table(_table(class_current_a=0.0))

    def test_a_class_with_both_budget_forms_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table(_table(allowed_drop_fraction=0.02))

    def test_a_class_with_no_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_class_table(_table(allowed_drop_v_value=None))

    def test_an_unknown_class_name_rejected(self):
        with self.assertRaises(ValueError):
            class_entry(_table(), "class-9")

    def test_the_named_class_row_is_returned(self):
        entry = class_entry(_table(), "  class-2 ")
        self.assertAlmostEqual(entry["class_current_a"], 1.5, places=9)

    def test_an_absolute_budget_is_taken_as_declared(self):
        entry = class_entry(_table(), "class-2")
        self.assertAlmostEqual(allowed_drop_v(entry, 28.0), 0.6, places=9)

    def test_a_fractional_budget_is_taken_against_the_bus(self):
        table = _table()
        table[1] = {
            "name": "class-2",
            "class_current_a": 1.5,
            "allowed_drop_fraction": 0.02,
        }
        entry = class_entry(table, "class-2")
        self.assertAlmostEqual(allowed_drop_v(entry, 28.0), 0.56, places=9)

    def test_a_fractional_budget_needs_a_bus_voltage(self):
        table = _table()
        table[1] = {
            "name": "class-2",
            "class_current_a": 1.5,
            "allowed_drop_fraction": 0.02,
        }
        with self.assertRaises(ValueError):
            allowed_drop_v(class_entry(table, "class-2"), 0.0)


class ElementTests(unittest.TestCase):
    def test_a_known_kind_is_trimmed_and_returned(self):
        self.assertEqual(categorize_element_kind("  connector-contact "), ELEMENT_CONNECTOR)

    def test_an_unrecognised_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_kind("slip-ring")

    def test_an_empty_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_kind("  ")

    def test_a_copper_path_gains_resistance_when_hot(self):
        self.assertAlmostEqual(
            hot_resistance_ohm(0.100), 0.100 * (1.0 + COPPER_ALPHA_PER_K * 50.0),
            places=12,
        )

    def test_a_zero_temperature_coefficient_leaves_the_resistance_alone(self):
        self.assertAlmostEqual(hot_resistance_ohm(0.100, 0.0), 0.100, places=12)

    def test_a_negative_temperature_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            hot_resistance_ohm(0.100, -0.001)

    def test_a_negative_reference_resistance_rejected(self):
        with self.assertRaises(ValueError):
            hot_resistance_ohm(-0.100)

    def test_a_resistive_element_scales_with_the_current(self):
        record = contributor_drop(_contributors()[1], 2.0)
        self.assertAlmostEqual(record["drop_v"], 0.160, places=12)

    def test_a_fixed_drop_does_not_scale_with_the_current(self):
        low = contributor_drop(_contributors()[3], 0.5)
        high = contributor_drop(_contributors()[3], 5.0)
        self.assertAlmostEqual(low["drop_v"], high["drop_v"], places=12)

    def test_an_element_with_no_loss_declared_rejected(self):
        with self.assertRaises(ValueError):
            contributor_drop({"id": "strap", "kind": ELEMENT_HARNESS}, 1.5)

    def test_an_element_with_no_id_rejected(self):
        with self.assertRaises(ValueError):
            contributor_drop(
                {"id": " ", "kind": ELEMENT_HARNESS, "resistance_ohm": 0.01}, 1.5
            )

    def test_a_negative_resistance_rejected(self):
        with self.assertRaises(ValueError):
            contributor_drop(
                {"id": "x", "kind": ELEMENT_HARNESS, "resistance_ohm": -0.01}, 1.5
            )

    def test_a_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            contributor_drop(_contributors()[1], 0.0)


class BreakdownTests(unittest.TestCase):
    def test_the_total_is_the_sum_of_the_parts(self):
        breakdown = line_drop_breakdown(_contributors(), 1.5)
        self.assertAlmostEqual(breakdown["nominal_drop_v"], 0.345, places=12)

    def test_resistive_and_fixed_drops_are_reported_apart(self):
        breakdown = line_drop_breakdown(_contributors(), 1.5)
        self.assertAlmostEqual(breakdown["resistive_drop_v"], 0.195, places=12)
        self.assertAlmostEqual(breakdown["fixed_drop_v"], 0.150, places=12)

    def test_the_worst_case_carries_the_tolerance_factor(self):
        breakdown = line_drop_breakdown(_contributors(), 1.5)
        self.assertAlmostEqual(
            breakdown["worst_case_drop_v"], 0.345 * 1.05, places=12
        )

    def test_the_shares_add_up_to_the_whole(self):
        breakdown = line_drop_breakdown(_contributors(), 1.5)
        total = sum(record["share"] for record in breakdown["contributors"])
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_the_largest_contributor_is_named(self):
        breakdown = line_drop_breakdown(_contributors(), 1.5)
        self.assertEqual(breakdown["dominant"], "blocking-diode")

    def test_contributors_are_grouped_by_element_kind(self):
        contributors = _contributors() + [
            {
                "id": "harness-return",
                "kind": ELEMENT_HARNESS,
                "resistance_ohm": 0.080,
                "alpha_per_k": 0.0,
            }
        ]
        breakdown = line_drop_breakdown(contributors, 1.5)
        self.assertAlmostEqual(breakdown["by_kind"][ELEMENT_HARNESS], 0.240, places=12)

    def test_the_dominant_kind_is_the_heaviest_group(self):
        contributors = _contributors() + [
            {
                "id": "harness-return",
                "kind": ELEMENT_HARNESS,
                "resistance_ohm": 0.080,
                "alpha_per_k": 0.0,
            }
        ]
        self.assertEqual(
            dominant_kind(line_drop_breakdown(contributors, 1.5)), ELEMENT_HARNESS
        )

    def test_a_contributor_declared_twice_rejected(self):
        contributors = _contributors()
        contributors[1]["id"] = "lcl-switch"
        with self.assertRaises(ValueError):
            line_drop_breakdown(contributors, 1.5)

    def test_an_empty_line_rejected(self):
        with self.assertRaises(ValueError):
            line_drop_breakdown([], 1.5)

    def test_a_breakdown_with_no_groups_rejected(self):
        with self.assertRaises(ValueError):
            dominant_kind({"by_kind": {}})


class BudgetAssessmentTests(unittest.TestCase):
    def test_a_line_inside_its_budget_passes_clean(self):
        result = assess_line_voltage_drop(_design())
        self.assertEqual(result["verdict"], DROP_WITHIN_BUDGET)
        self.assertEqual(result["findings"], [])

    def test_the_budget_is_graded_at_the_class_current(self):
        result = assess_line_voltage_drop(_design(operating_current_a=0.4))
        self.assertAlmostEqual(result["graded_current_a"], 1.5, places=9)

    def test_an_operating_current_above_its_class_rejected(self):
        with self.assertRaises(ValueError):
            assess_line_voltage_drop(_design(operating_current_a=2.0))

    def test_an_operating_current_exactly_on_its_class_accepted(self):
        result = assess_line_voltage_drop(_design(operating_current_a=1.5))
        self.assertEqual(result["verdict"], DROP_WITHIN_BUDGET)

    def test_a_line_over_its_budget_is_reported(self):
        result = assess_line_voltage_drop(
            _design(class_table=_table(allowed_drop_v_value=0.30))
        )
        self.assertEqual(result["verdict"], DROP_EXCEEDS_BUDGET)
        self.assertTrue(result["findings"])

    def test_a_thin_budget_is_reported_without_a_breach(self):
        result = assess_line_voltage_drop(
            _design(class_table=_table(allowed_drop_v_value=0.38))
        )
        self.assertEqual(result["verdict"], DROP_MARGIN_THIN)

    def test_a_drop_landing_exactly_on_the_ceiling_is_not_a_breach(self):
        worst_v = line_drop_breakdown(_contributors(), 1.5)["worst_case_drop_v"]
        result = assess_line_voltage_drop(
            _design(class_table=_table(allowed_drop_v_value=worst_v))
        )
        self.assertEqual(result["verdict"], DROP_MARGIN_THIN)
        self.assertAlmostEqual(result["margin_v"], 0.0, places=12)

    def test_a_margin_landing_exactly_on_the_thin_floor_still_passes(self):
        worst_v = line_drop_breakdown(_contributors(), 1.5)["worst_case_drop_v"]
        ceiling_v = worst_v / (1.0 - DEFAULT_LINE_DROP_POLICY["thin_margin_fraction"])
        result = assess_line_voltage_drop(
            _design(class_table=_table(allowed_drop_v_value=ceiling_v))
        )
        self.assertAlmostEqual(result["margin_fraction"], 0.10, places=9)
        self.assertEqual(result["verdict"], DROP_WITHIN_BUDGET)

    def test_a_dominant_element_raises_an_advisory(self):
        contributors = _contributors()
        contributors[3]["forward_drop_v"] = 0.70
        result = assess_line_voltage_drop(
            _design(
                contributors=contributors, class_table=_table(allowed_drop_v_value=1.2)
            )
        )
        self.assertEqual(result["verdict"], DROP_WITHIN_BUDGET)
        self.assertTrue(
            any("carries" in finding for finding in result["findings"])
        )

    def test_the_voltage_the_load_actually_sees_is_reported(self):
        result = assess_line_voltage_drop(_design())
        self.assertAlmostEqual(
            result["load_input_v"], 28.0 - 0.345 * 1.05, places=12
        )

    def test_a_hotter_policy_costs_more_budget(self):
        contributors = [
            {"id": "harness-out", "kind": ELEMENT_HARNESS, "resistance_ohm": 0.080},
            {"id": "shunt", "kind": ELEMENT_SENSE_SHUNT, "resistance_ohm": 0.005},
        ]
        cold = assess_line_voltage_drop(
            _design(contributors=contributors), _policy(hot_temperature_c=20.0)
        )
        hot = assess_line_voltage_drop(_design(contributors=contributors))
        self.assertGreater(
            hot["breakdown"]["nominal_drop_v"], cold["breakdown"]["nominal_drop_v"]
        )

    def test_a_missing_bus_voltage_rejected(self):
        design = _design()
        del design["bus_voltage_v"]
        with self.assertRaises(ValueError):
            assess_line_voltage_drop(design)

    def test_a_design_with_no_contributors_rejected(self):
        with self.assertRaises(ValueError):
            assess_line_voltage_drop(_design(contributors=[]))

    def test_a_design_on_an_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            assess_line_voltage_drop(_design(class_name="class-7"))


if __name__ == "__main__":
    unittest.main()
