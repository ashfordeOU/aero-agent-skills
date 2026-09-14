#!/usr/bin/env python3
"""Contract test for the blocking diode dispatch check, clause 12.9 (offline)."""

import unittest

from e2008_blocking_diode_delivery_logic import (
    BLOCKING_VOLTAGE_CLASSES,
    DISPATCH_HELD,
    DISPATCH_RELEASABLE,
    DIODE_HELD,
    DIODE_SHIPPABLE,
    FILL_TOLERANCE,
    HOLD_DOCUMENTATION,
    HOLD_STORAGE_LIFE,
    HOLD_TRACEABILITY,
    HOLD_UNKNOWN_BATCH,
    LINE_COMPLETE,
    LINE_PARTIAL,
    LINE_REFUSED,
    allocate_diodes_to_lines,
    assess_diode,
    assess_diodes,
    batch_storage_state,
    class_rank,
    evaluate_dispatch,
    normalize_class,
    parse_delivery_date,
    validate_batch_register,
    validate_order,
    validate_order_line,
)

PART = "bd-4401"
DISPATCH_DATE = "2026-06-10"


def _serials(count, prefix="sn"):
    return ["%s-%03d" % (prefix, n) for n in range(1, count + 1)]


def _batch(
    batch_id="bat-01",
    released=True,
    serials=None,
    expiry="2026-12-31",
    revalidation=None,
):
    return {
        "batch_id": batch_id,
        "data_package_released": released,
        "delivered_serials": serials if serials is not None else _serials(4),
        "storage_life_expiry": expiry,
        "revalidation": revalidation,
    }


def _diode(serial, part_number=PART, voltage_class="bv-200v", batch_id="bat-01"):
    return {
        "serial": serial,
        "part_number": part_number,
        "blocking_voltage_class": voltage_class,
        "batch_id": batch_id,
    }


def _order(lines=None, floor=0.8, order_id="ord-2026-11"):
    return {
        "order_id": order_id,
        "partial_delivery_floor": floor,
        "lines": lines
        if lines is not None
        else [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 4,
            }
        ],
    }


def _spec(**overrides):
    spec = {
        "dispatch_id": "dsp-0007",
        "dispatch_date": DISPATCH_DATE,
        "order": _order(),
        "batch_register": [_batch()],
        "diodes": [_diode(s) for s in _serials(4)],
    }
    spec.update(overrides)
    return spec


def _register(batches=None):
    return validate_batch_register(batches if batches is not None else [_batch()])


def _date(value):
    return parse_delivery_date(value, "d")


class ClassLadderTests(unittest.TestCase):
    def test_ladder_runs_lowest_blocking_capability_first(self):
        self.assertEqual(BLOCKING_VOLTAGE_CLASSES[0], "bv-100v")
        self.assertEqual(BLOCKING_VOLTAGE_CLASSES[-1], "bv-400v")

    def test_rank_orders_the_ladder(self):
        self.assertLess(class_rank("bv-100v"), class_rank("bv-400v"))

    def test_class_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_class("  BV-400V "), "bv-400v")

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            normalize_class("bv-9000v")


class OrderValidationTests(unittest.TestCase):
    def test_zero_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "part_number": PART,
                    "blocking_voltage_class": "bv-200v",
                    "ordered_count": 0,
                }
            )

    def test_boolean_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "part_number": PART,
                    "blocking_voltage_class": "bv-200v",
                    "ordered_count": True,
                }
            )

    def test_missing_part_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "blocking_voltage_class": "bv-200v",
                    "ordered_count": 2,
                }
            )

    def test_upgrade_permission_must_be_boolean(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "part_number": PART,
                    "blocking_voltage_class": "bv-200v",
                    "ordered_count": 2,
                    "allow_class_upgrade": "if you like",
                }
            )

    def test_upgrade_permission_defaults_to_refused(self):
        line = validate_order_line(
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 2,
            }
        )
        self.assertFalse(line["allow_class_upgrade"])

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor=1.4))

    def test_floor_must_be_a_number(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor="most of it"))

    def test_repeated_line_id_rejected(self):
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 2,
            },
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-400v",
                "ordered_count": 2,
            },
        ]
        with self.assertRaises(ValueError):
            validate_order(_order(lines=lines))

    def test_order_with_no_lines_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(lines=[]))


class BatchRegisterTests(unittest.TestCase):
    def test_release_is_read_as_a_state(self):
        register = _register([_batch(released=False)])
        self.assertFalse(register["bat-01"]["data_package_released"])

    def test_non_boolean_release_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(released="pending")])

    def test_repeated_batch_entry_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(), _batch()])

    def test_batch_with_no_serials_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(serials=[])])

    def test_repeated_serial_in_a_batch_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(serials=["sn-001", "sn-001"])])

    def test_malformed_expiry_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(expiry="31/12/2026")])

    def test_revalidation_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            _register([_batch(revalidation={"date": "2026-06-01"})])


class StorageLifeTests(unittest.TestCase):
    def test_batch_within_life_passes(self):
        entry = _register()["bat-01"]
        self.assertTrue(batch_storage_state(entry, _date(DISPATCH_DATE))["within_life"])

    def test_dispatch_on_the_expiry_day_is_within_life(self):
        entry = _register([_batch(expiry=DISPATCH_DATE)])["bat-01"]
        self.assertTrue(batch_storage_state(entry, _date(DISPATCH_DATE))["within_life"])

    def test_expired_batch_without_revalidation_is_held(self):
        entry = _register([_batch(expiry="2026-01-01")])["bat-01"]
        state = batch_storage_state(entry, _date(DISPATCH_DATE))
        self.assertFalse(state["within_life"])
        self.assertIsNotNone(state["reason"])

    def test_revalidation_predating_the_expiry_revalidates_nothing(self):
        entry = _register(
            [
                _batch(
                    expiry="2026-01-01",
                    revalidation={"reference": "rv-1", "date": "2025-11-01"},
                )
            ]
        )["bat-01"]
        self.assertFalse(batch_storage_state(entry, _date(DISPATCH_DATE))["within_life"])

    def test_revalidation_after_the_shipment_left_does_not_count(self):
        entry = _register(
            [
                _batch(
                    expiry="2026-01-01",
                    revalidation={"reference": "rv-1", "date": "2026-08-01"},
                )
            ]
        )["bat-01"]
        self.assertFalse(batch_storage_state(entry, _date(DISPATCH_DATE))["within_life"])

    def test_revalidation_between_expiry_and_dispatch_restores_the_batch(self):
        entry = _register(
            [
                _batch(
                    expiry="2026-01-01",
                    revalidation={"reference": "rv-1", "date": "2026-03-15"},
                )
            ]
        )["bat-01"]
        state = batch_storage_state(entry, _date(DISPATCH_DATE))
        self.assertTrue(state["within_life"])
        self.assertTrue(state["revalidated"])


class DiodeDispositionTests(unittest.TestCase):
    def test_clean_diode_is_shippable(self):
        result = assess_diode(_diode("sn-001"), _register(), _date(DISPATCH_DATE))
        self.assertEqual(result["disposition"], DIODE_SHIPPABLE)
        self.assertEqual(result["hold_codes"], ())

    def test_unreleased_package_holds_the_diode(self):
        register = _register([_batch(released=False)])
        result = assess_diode(_diode("sn-001"), register, _date(DISPATCH_DATE))
        self.assertEqual(result["disposition"], DIODE_HELD)
        self.assertIn(HOLD_DOCUMENTATION, result["hold_codes"])

    def test_serial_absent_from_the_batch_list_holds_the_diode(self):
        result = assess_diode(_diode("sn-999"), _register(), _date(DISPATCH_DATE))
        self.assertIn(HOLD_TRACEABILITY, result["hold_codes"])

    def test_unknown_batch_holds_the_diode(self):
        result = assess_diode(
            _diode("sn-001", batch_id="bat-zz"), _register(), _date(DISPATCH_DATE)
        )
        self.assertEqual(result["hold_codes"], (HOLD_UNKNOWN_BATCH,))

    def test_expired_batch_holds_the_diode(self):
        register = _register([_batch(expiry="2026-01-01")])
        result = assess_diode(_diode("sn-001"), register, _date(DISPATCH_DATE))
        self.assertIn(HOLD_STORAGE_LIFE, result["hold_codes"])

    def test_a_diode_can_fail_two_arms_at_once(self):
        register = _register([_batch(released=False, expiry="2026-01-01")])
        result = assess_diode(_diode("sn-001"), register, _date(DISPATCH_DATE))
        self.assertIn(HOLD_DOCUMENTATION, result["hold_codes"])
        self.assertIn(HOLD_STORAGE_LIFE, result["hold_codes"])
        self.assertEqual(len(result["reasons"]), 2)

    def test_diode_missing_a_key_rejected(self):
        bad = _diode("sn-001")
        del bad["batch_id"]
        with self.assertRaises(ValueError):
            assess_diode(bad, _register(), _date(DISPATCH_DATE))

    def test_repeated_serial_offered_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_diodes(
                [_diode("sn-001"), _diode("sn-001")],
                _register(),
                _date(DISPATCH_DATE),
            )

    def test_empty_offer_rejected(self):
        with self.assertRaises(ValueError):
            assess_diodes([], _register(), _date(DISPATCH_DATE))


class AllocationTests(unittest.TestCase):
    def _assess(self, diodes, batches=None):
        return assess_diodes(
            diodes, _register(batches), _date(DISPATCH_DATE)
        )

    def test_exact_class_fills_the_line(self):
        assessed = self._assess([_diode(s) for s in _serials(4)])
        result = allocate_diodes_to_lines(assessed, _order())
        self.assertEqual(result["lines"][0]["state"], LINE_COMPLETE)
        self.assertEqual(result["lines"][0]["upgraded_serials"], ())

    def test_lower_class_never_fills_a_higher_line(self):
        assessed = self._assess(
            [_diode(s, voltage_class="bv-100v") for s in _serials(4)]
        )
        result = allocate_diodes_to_lines(assessed, _order(floor=0.0))
        self.assertEqual(result["lines"][0]["shipped_count"], 0)

    def test_upgrade_refused_when_the_order_does_not_permit_it(self):
        assessed = self._assess(
            [_diode(s, voltage_class="bv-400v") for s in _serials(4)]
        )
        result = allocate_diodes_to_lines(assessed, _order(floor=0.0))
        self.assertEqual(result["lines"][0]["shipped_count"], 0)

    def test_permitted_upgrade_fills_the_line_and_is_named(self):
        assessed = self._assess(
            [_diode(s, voltage_class="bv-400v") for s in _serials(4)]
        )
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 4,
                "allow_class_upgrade": True,
            }
        ]
        result = allocate_diodes_to_lines(assessed, _order(lines=lines))
        self.assertEqual(result["lines"][0]["state"], LINE_COMPLETE)
        self.assertEqual(len(result["lines"][0]["upgraded_serials"]), 4)

    def test_another_part_number_is_not_a_substitution(self):
        assessed = self._assess(
            [_diode(s, part_number="bd-9999") for s in _serials(4)]
        )
        result = allocate_diodes_to_lines(assessed, _order(floor=0.0))
        self.assertEqual(result["lines"][0]["shipped_count"], 0)
        self.assertEqual(len(result["surplus_serials"]), 4)

    def test_exact_class_is_spent_before_a_permitted_upgrade(self):
        diodes = [
            _diode("sn-001", voltage_class="bv-200v"),
            _diode("sn-002", voltage_class="bv-400v"),
        ]
        lines = [
            {
                "line_id": "ln-low",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 1,
                "allow_class_upgrade": True,
            },
            {
                "line_id": "ln-high",
                "part_number": PART,
                "blocking_voltage_class": "bv-400v",
                "ordered_count": 1,
            },
        ]
        assessed = self._assess(diodes, [_batch(serials=["sn-001", "sn-002"])])
        result = allocate_diodes_to_lines(assessed, _order(lines=lines, floor=0.0))
        self.assertEqual(result["lines"][0]["allocated_serials"], ("sn-001",))
        self.assertEqual(result["lines"][1]["allocated_serials"], ("sn-002",))

    def test_surplus_shippable_diode_is_reported(self):
        assessed = self._assess(
            [_diode(s) for s in _serials(4)],
            [_batch(serials=_serials(4))],
        )
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 2,
            }
        ]
        result = allocate_diodes_to_lines(assessed, _order(lines=lines))
        self.assertEqual(len(result["surplus_serials"]), 2)

    def test_line_exactly_on_the_floor_clears_it(self):
        assessed = self._assess(
            [_diode(s) for s in _serials(4)], [_batch(serials=_serials(4))]
        )
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 5,
            }
        ]
        result = allocate_diodes_to_lines(assessed, _order(lines=lines, floor=0.8))
        self.assertEqual(result["lines"][0]["state"], LINE_PARTIAL)
        self.assertAlmostEqual(result["lines"][0]["fill_fraction"], 0.8, places=9)

    def test_line_below_the_floor_is_refused(self):
        assessed = self._assess(
            [_diode("sn-001")], [_batch(serials=["sn-001"])]
        )
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 4,
            }
        ]
        result = allocate_diodes_to_lines(assessed, _order(lines=lines, floor=0.8))
        self.assertEqual(result["lines"][0]["state"], LINE_REFUSED)
        self.assertFalse(result["lines"][0]["accepted"])

    def test_tolerance_is_named_and_small(self):
        self.assertLess(FILL_TOLERANCE, 1e-6)


class DispatchTests(unittest.TestCase):
    def test_clean_dispatch_is_releasable(self):
        result = evaluate_dispatch(_spec())
        self.assertEqual(result["verdict"], DISPATCH_RELEASABLE)
        self.assertEqual(result["findings"], [])

    def test_full_count_from_an_unreleased_batch_is_held(self):
        spec = _spec(batch_register=[_batch(released=False)])
        result = evaluate_dispatch(spec)
        self.assertEqual(result["verdict"], DISPATCH_HELD)
        self.assertEqual(result["shipped_total"], 0)
        self.assertEqual(len(result["held_serials"]), 4)

    def test_hold_codes_are_collected_across_the_shipment(self):
        spec = _spec(
            batch_register=[_batch(released=False, expiry="2026-01-01")],
        )
        result = evaluate_dispatch(spec)
        self.assertIn(HOLD_DOCUMENTATION, result["hold_codes"])
        self.assertIn(HOLD_STORAGE_LIFE, result["hold_codes"])

    def test_totals_sum_across_lines(self):
        lines = [
            {
                "line_id": "ln-1",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 2,
            },
            {
                "line_id": "ln-2",
                "part_number": PART,
                "blocking_voltage_class": "bv-200v",
                "ordered_count": 2,
            },
        ]
        result = evaluate_dispatch(_spec(order=_order(lines=lines, floor=0.0)))
        self.assertEqual(result["ordered_total"], 4)
        self.assertEqual(result["shipped_total"], 4)
        self.assertAlmostEqual(result["dispatch_fill_fraction"], 1.0, places=9)

    def test_partial_dispatch_is_named(self):
        spec = _spec(
            batch_register=[_batch(serials=_serials(3))],
            diodes=[_diode(s) for s in _serials(3)],
        )
        result = evaluate_dispatch(spec)
        self.assertTrue(result["partial"])
        self.assertAlmostEqual(result["dispatch_fill_fraction"], 0.75, places=9)

    def test_malformed_dispatch_date_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dispatch(_spec(dispatch_date="10 June 2026"))

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["batch_register"]
        with self.assertRaises(ValueError):
            evaluate_dispatch(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_dispatch("just ship it")


if __name__ == "__main__":
    unittest.main()
