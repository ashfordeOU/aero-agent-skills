#!/usr/bin/env python3
"""Contract test for cell assembly hardware delivery (offline).

Walks the clause workflow step by step: the release policy and its
refusal to default an unstated rule, the documentation package handoff,
the per-unit disposition including the lot-coverage join between the
hardware and the paperwork, the order line reconciliation short and
over, the inclusive partial-release floor, and the roll-up into one
release verdict. This is the gate 3 review evidence for the leaf.
"""

import unittest

from e2008_sca_hardware_delivery_logic import (
    CONFORMANCE_STATES,
    DEFAULT_DELIVERY_POLICY,
    DELIVERY_HELD,
    DELIVERY_RELEASABLE,
    LINE_HELD,
    LINE_RELEASABLE,
    LINE_RELEASABLE_PARTIAL,
    UNIT_HELD_LOT_UNCOVERED,
    UNIT_HELD_NONCONFORMING,
    UNIT_SHIPPABLE,
    UNIT_SHIPPABLE_ON_CONCESSION,
    assess_hardware_delivery,
    assess_shipment_unit,
    normalize_conformance,
    reconcile_order_line,
    validate_delivery_policy,
    validate_documentation_release,
    validate_order_line,
)

COVERED = ("LOT-A", "LOT-B")
LINE = {"line_id": "L1", "assembly_type": "SCA-3J-80", "ordered_quantity": 4}


def _documentation(**overrides):
    package = {
        "package_reference": "DDP-2026-07",
        "released": True,
        "covered_lots": list(COVERED),
    }
    package.update(overrides)
    return package


def _unit(unit_id, lot_id="LOT-A", conformance="conforming", line_id="L1"):
    return {
        "unit_id": unit_id,
        "line_id": line_id,
        "lot_id": lot_id,
        "conformance": conformance,
    }


def _units(count, **kwargs):
    return [_unit("U%02d" % index, **kwargs) for index in range(count)]


def _records(units, covered=COVERED):
    return [assess_shipment_unit(unit, covered) for unit in units]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        resolved = validate_delivery_policy(dict(DEFAULT_DELIVERY_POLICY))
        self.assertTrue(resolved["allow_partial_shipment"])
        self.assertAlmostEqual(
            resolved["minimum_release_fraction"],
            DEFAULT_DELIVERY_POLICY["minimum_release_fraction"],
            places=9,
        )

    def test_unstated_policy_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_policy({"allow_partial_shipment": True})

    def test_unrecognized_policy_key_rejected(self):
        policy = dict(DEFAULT_DELIVERY_POLICY)
        policy["ship_it_anyway"] = True
        with self.assertRaises(ValueError):
            validate_delivery_policy(policy)

    def test_non_boolean_partial_flag_rejected(self):
        policy = dict(DEFAULT_DELIVERY_POLICY)
        policy["allow_partial_shipment"] = "sometimes"
        with self.assertRaises(ValueError):
            validate_delivery_policy(policy)

    def test_release_fraction_above_one_rejected(self):
        policy = dict(DEFAULT_DELIVERY_POLICY)
        policy["minimum_release_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_delivery_policy(policy)


class DocumentationTests(unittest.TestCase):
    def test_released_package_with_lots_is_usable(self):
        result = validate_documentation_release(_documentation())
        self.assertTrue(result["usable"])
        self.assertEqual(result["covered_lots"], COVERED)
        self.assertEqual(result["findings"], [])

    def test_unreleased_package_is_not_usable(self):
        result = validate_documentation_release(_documentation(released=False))
        self.assertFalse(result["usable"])
        self.assertTrue(result["findings"])

    def test_package_covering_no_lot_is_not_usable(self):
        result = validate_documentation_release(_documentation(covered_lots=[]))
        self.assertFalse(result["usable"])

    def test_lot_covered_twice_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_release(
                _documentation(covered_lots=["LOT-A", "LOT-A"])
            )

    def test_non_boolean_release_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_release(_documentation(released="yes"))

    def test_missing_documentation_key_rejected(self):
        package = _documentation()
        del package["covered_lots"]
        with self.assertRaises(ValueError):
            validate_documentation_release(package)


class UnitDispositionTests(unittest.TestCase):
    def test_conforming_unit_from_a_covered_lot_ships(self):
        record = assess_shipment_unit(_unit("U1"), COVERED)
        self.assertEqual(record["disposition"], UNIT_SHIPPABLE)
        self.assertTrue(record["shippable"])

    def test_unit_on_an_accepted_concession_ships_and_is_counted_apart(self):
        record = assess_shipment_unit(
            _unit("U2", conformance="nonconforming-with-accepted-concession"),
            COVERED,
        )
        self.assertEqual(record["disposition"], UNIT_SHIPPABLE_ON_CONCESSION)
        self.assertTrue(record["shippable"])
        self.assertTrue(record["findings"])

    def test_nonconforming_unit_is_held(self):
        record = assess_shipment_unit(
            _unit("U3", conformance="nonconforming"), COVERED
        )
        self.assertEqual(record["disposition"], UNIT_HELD_NONCONFORMING)
        self.assertFalse(record["shippable"])

    def test_unit_from_an_uncovered_lot_is_held_even_when_conforming(self):
        record = assess_shipment_unit(_unit("U4", lot_id="LOT-Z"), COVERED)
        self.assertEqual(record["disposition"], UNIT_HELD_LOT_UNCOVERED)
        self.assertFalse(record["shippable"])
        self.assertTrue(any("LOT-Z" in f for f in record["findings"]))

    def test_lot_coverage_is_read_before_conformance(self):
        record = assess_shipment_unit(
            _unit("U5", lot_id="LOT-Z", conformance="nonconforming"), COVERED
        )
        self.assertEqual(record["disposition"], UNIT_HELD_LOT_UNCOVERED)

    def test_unrecognized_conformance_rejected(self):
        with self.assertRaises(ValueError):
            assess_shipment_unit(_unit("U6", conformance="probably-fine"), COVERED)

    def test_conformance_is_normalized(self):
        self.assertEqual(normalize_conformance("  Conforming "), "conforming")
        self.assertEqual(len(CONFORMANCE_STATES), 3)

    def test_blank_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_shipment_unit(_unit("  "), COVERED)


class OrderLineTests(unittest.TestCase):
    def test_order_line_validates(self):
        entry = validate_order_line(dict(LINE))
        self.assertEqual(entry["ordered_quantity"], 4)

    def test_zero_ordered_quantity_rejected(self):
        line = dict(LINE)
        line["ordered_quantity"] = 0
        with self.assertRaises(ValueError):
            validate_order_line(line)

    def test_non_integer_ordered_quantity_rejected(self):
        line = dict(LINE)
        line["ordered_quantity"] = 4.0
        with self.assertRaises(ValueError):
            validate_order_line(line)

    def test_full_count_releases_the_line(self):
        result = reconcile_order_line(dict(LINE), _records(_units(4)))
        self.assertEqual(result["verdict"], LINE_RELEASABLE)
        self.assertEqual(result["shortfall"], 0)
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)

    def test_over_shipment_holds_the_line(self):
        result = reconcile_order_line(dict(LINE), _records(_units(5)))
        self.assertEqual(result["verdict"], LINE_HELD)
        self.assertEqual(result["overage"], 1)

    def test_permitted_partial_above_the_floor_releases(self):
        result = reconcile_order_line(dict(LINE), _records(_units(3)))
        self.assertEqual(result["verdict"], LINE_RELEASABLE_PARTIAL)
        self.assertEqual(result["shortfall"], 1)
        self.assertTrue(result["releasable"])

    def test_partial_exactly_on_the_floor_releases(self):
        policy = {"allow_partial_shipment": True, "minimum_release_fraction": 0.5}
        result = reconcile_order_line(dict(LINE), _records(_units(2)), policy)
        self.assertAlmostEqual(result["release_share"], 0.5, places=9)
        self.assertEqual(result["verdict"], LINE_RELEASABLE_PARTIAL)

    def test_partial_below_the_floor_holds(self):
        result = reconcile_order_line(dict(LINE), _records(_units(1)))
        self.assertEqual(result["verdict"], LINE_HELD)
        self.assertFalse(result["releasable"])

    def test_partial_refused_outright_when_the_order_forbids_it(self):
        policy = {"allow_partial_shipment": False, "minimum_release_fraction": 0.1}
        result = reconcile_order_line(dict(LINE), _records(_units(3)), policy)
        self.assertEqual(result["verdict"], LINE_HELD)

    def test_held_units_do_not_count_toward_the_line(self):
        units = _units(2) + [
            _unit("U8", conformance="nonconforming"),
            _unit("U9", lot_id="LOT-Z"),
        ]
        result = reconcile_order_line(dict(LINE), _records(units))
        self.assertEqual(result["offered_quantity"], 4)
        self.assertEqual(result["shippable_quantity"], 2)

    def test_concession_units_are_counted_separately(self):
        units = _units(3) + [
            _unit("U9", conformance="nonconforming-with-accepted-concession")
        ]
        result = reconcile_order_line(dict(LINE), _records(units))
        self.assertEqual(result["shippable_quantity"], 4)
        self.assertEqual(result["concession_quantity"], 1)
        self.assertEqual(result["verdict"], LINE_RELEASABLE)

    def test_units_of_another_line_are_ignored(self):
        units = _units(4) + [_unit("X1", line_id="L2")]
        result = reconcile_order_line(dict(LINE), _records(units))
        self.assertEqual(result["offered_quantity"], 4)


class DeliveryTests(unittest.TestCase):
    def _case(self, **overrides):
        case = {
            "delivery_id": "DEL-9",
            "order_lines": [dict(LINE)],
            "units": _units(4),
            "documentation": _documentation(),
        }
        case.update(overrides)
        return case

    def test_full_shipment_with_a_released_package_is_releasable(self):
        result = assess_hardware_delivery(self._case())
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(result["shippable_quantity"], 4)
        self.assertEqual(result["findings"], [])

    def test_right_count_with_an_unreleased_package_is_held(self):
        result = assess_hardware_delivery(
            self._case(documentation=_documentation(released=False))
        )
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertEqual(result["lines"][0]["verdict"], LINE_RELEASABLE)

    def test_a_unit_outside_the_covered_lots_holds_the_delivery(self):
        units = _units(3) + [_unit("U9", lot_id="LOT-Z")]
        result = assess_hardware_delivery(self._case(units=units))
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertEqual(result["uncovered_unit_ids"], ("U9",))

    def test_shortfall_below_the_floor_holds_the_delivery(self):
        result = assess_hardware_delivery(self._case(units=_units(1)))
        self.assertEqual(result["verdict"], DELIVERY_HELD)

    def test_two_lines_are_reconciled_independently(self):
        lines = [dict(LINE), {"line_id": "L2", "assembly_type": "SCA-3J-40", "ordered_quantity": 2}]
        units = _units(4) + [
            _unit("V1", lot_id="LOT-B", line_id="L2"),
            _unit("V2", lot_id="LOT-B", line_id="L2"),
        ]
        result = assess_hardware_delivery(self._case(order_lines=lines, units=units))
        self.assertEqual(result["ordered_quantity"], 6)
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(len(result["lines"]), 2)

    def test_unit_citing_an_unknown_line_rejected(self):
        units = _units(4) + [_unit("V9", line_id="L7")]
        with self.assertRaises(ValueError):
            assess_hardware_delivery(self._case(units=units))

    def test_unit_offered_twice_rejected(self):
        units = _units(4)
        units.append(dict(units[0]))
        with self.assertRaises(ValueError):
            assess_hardware_delivery(self._case(units=units))

    def test_order_line_repeated_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_delivery(
                self._case(order_lines=[dict(LINE), dict(LINE)])
            )

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_delivery(self._case(order_lines=[]))

    def test_findings_carry_the_paperwork_and_the_count_arms(self):
        result = assess_hardware_delivery(
            self._case(
                units=_units(1), documentation=_documentation(released=False)
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_delivery("everything shipped on Tuesday")


if __name__ == "__main__":
    unittest.main()
