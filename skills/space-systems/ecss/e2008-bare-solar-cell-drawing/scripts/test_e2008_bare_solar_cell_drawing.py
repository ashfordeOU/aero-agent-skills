#!/usr/bin/env python3
"""Contract test for the bare solar cell source control drawing (offline)."""

import copy
import unittest

from e2008_bare_solar_cell_drawing_logic import (
    BARE_CELL_DRAWING_NOT_RELEASABLE,
    BARE_CELL_DRAWING_OPEN_ITEMS,
    BARE_CELL_DRAWING_RELEASABLE,
    CHAR_CONTROLLED,
    CHAR_OPEN,
    CHAR_UNCONTROLLED,
    CHARACTERISTIC_KINDS,
    CHARACTERISTIC_WEIGHTS,
    LIMIT_FORMS,
    REQUIRED_CHARACTERISTICS,
    REQUIRED_CONDITION_KEYS,
    assess_bare_cell_drawing,
    characteristic_control,
    controlled_characteristic_share,
    limit_bounds,
    measurement_conditions,
)

CONDITIONS = {"spectrum": "AM0", "irradiance": 1367.0, "temperature": 28.0}

CHARACTERISTICS = [
    {
        "characteristic": "cell-length",
        "kind": "geometric",
        "unit": "mm",
        "limit_form": "nominal-with-tolerance",
        "nominal": 80.0,
        "tolerance": 0.1,
    },
    {
        "characteristic": "cell-width",
        "kind": "geometric",
        "unit": "mm",
        "limit_form": "range",
        "minimum": 39.9,
        "maximum": 40.1,
    },
    {
        "characteristic": "cell-thickness",
        "kind": "geometric",
        "unit": "um",
        "limit_form": "nominal-with-tolerance",
        "nominal": 150.0,
        "tolerance": 10.0,
    },
    {
        "characteristic": "contact-grid-geometry",
        "kind": "geometric",
        "unit": "mm",
        "limit_form": "minimum",
        "minimum": 0.05,
    },
    {
        "characteristic": "antireflection-coating",
        "kind": "physical",
        "unit": "nm",
        "limit_form": "range",
        "minimum": 60.0,
        "maximum": 90.0,
    },
    {
        "characteristic": "cell-mass",
        "kind": "physical",
        "unit": "g",
        "limit_form": "maximum",
        "maximum": 2.5,
    },
    {
        "characteristic": "open-circuit-voltage",
        "kind": "electrical",
        "unit": "V",
        "limit_form": "minimum",
        "minimum": 2.6,
        "conditions": dict(CONDITIONS),
    },
    {
        "characteristic": "short-circuit-current",
        "kind": "electrical",
        "unit": "mA",
        "limit_form": "minimum",
        "minimum": 400.0,
        "conditions": dict(CONDITIONS),
    },
    {
        "characteristic": "maximum-power-point",
        "kind": "electrical",
        "unit": "mW",
        "limit_form": "minimum",
        "minimum": 1000.0,
        "conditions": dict(CONDITIONS),
    },
]

CLEAN_SPEC = {"drawing": "BSC-SCD-0003", "characteristics": CHARACTERISTICS}

TOTAL_WEIGHT = float(sum(CHARACTERISTIC_WEIGHTS.values()))


def _spec(**overrides):
    item = copy.deepcopy(CLEAN_SPEC)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


def _characteristics(**per_name):
    out = copy.deepcopy(CHARACTERISTICS)
    for record in out:
        if record["characteristic"] in per_name:
            record.update(per_name[record["characteristic"]])
    return out


class LimitBoundsTests(unittest.TestCase):
    def test_a_nominal_with_a_band_carries_both_bounds(self):
        result = limit_bounds(CHARACTERISTICS[0])
        self.assertAlmostEqual(result["lower"], 79.9, places=9)
        self.assertAlmostEqual(result["upper"], 80.1, places=9)
        self.assertTrue(result["banded"])

    def test_a_minimum_leaves_the_upper_end_open(self):
        result = limit_bounds({"limit_form": "minimum", "minimum": 2.6})
        self.assertAlmostEqual(result["lower"], 2.6, places=9)
        self.assertIsNone(result["upper"])

    def test_a_maximum_leaves_the_lower_end_open(self):
        result = limit_bounds({"limit_form": "maximum", "maximum": 2.5})
        self.assertIsNone(result["lower"])
        self.assertAlmostEqual(result["upper"], 2.5, places=9)

    def test_a_range_carries_both_ends(self):
        result = limit_bounds(CHARACTERISTICS[1])
        self.assertAlmostEqual(result["lower"], 39.9, places=9)
        self.assertAlmostEqual(result["upper"], 40.1, places=9)
        self.assertFalse(result["degenerate"])

    def test_a_nominal_on_its_own_bands_nothing(self):
        result = limit_bounds({"limit_form": "nominal-only", "nominal": 150.0})
        self.assertFalse(result["banded"])
        self.assertTrue(any("not something a cell" in f for f in result["findings"]))

    def test_a_range_whose_bounds_coincide_names_a_point(self):
        result = limit_bounds(
            {"limit_form": "range", "minimum": 2.0, "maximum": 2.0}
        )
        self.assertAlmostEqual(result["lower"], result["upper"], places=9)
        self.assertTrue(result["degenerate"])
        self.assertFalse(result["banded"])

    def test_a_zero_tolerance_is_a_band_of_no_width(self):
        result = limit_bounds(
            {"limit_form": "nominal-with-tolerance", "nominal": 80.0, "tolerance": 0.0}
        )
        self.assertTrue(result["degenerate"])
        self.assertAlmostEqual(result["lower"], result["upper"], places=9)

    def test_a_range_running_downward_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_bounds({"limit_form": "range", "minimum": 5.0, "maximum": 1.0})

    def test_a_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_bounds(
                {"limit_form": "nominal-with-tolerance", "nominal": 80.0, "tolerance": -0.1}
            )

    def test_an_unknown_limit_form_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_bounds({"limit_form": "about", "nominal": 80.0})

    def test_a_limit_form_missing_the_value_it_needs_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_bounds({"limit_form": "range", "minimum": 1.0})

    def test_a_non_mapping_limit_record_is_rejected(self):
        with self.assertRaises(ValueError):
            limit_bounds(["range", 1.0, 2.0])

    def test_every_declared_limit_form_resolves(self):
        samples = {
            "minimum": {"minimum": 1.0},
            "maximum": {"maximum": 2.0},
            "range": {"minimum": 1.0, "maximum": 2.0},
            "nominal-with-tolerance": {"nominal": 1.0, "tolerance": 0.1},
            "nominal-only": {"nominal": 1.0},
        }
        for form in LIMIT_FORMS:
            record = dict(samples[form], limit_form=form)
            self.assertIn("banded", limit_bounds(record))


class MeasurementConditionTests(unittest.TestCase):
    def test_all_three_conditions_stated_is_complete(self):
        result = measurement_conditions(CONDITIONS)
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_temperature_is_reported(self):
        partial = {key: CONDITIONS[key] for key in ("spectrum", "irradiance")}
        result = measurement_conditions(partial)
        self.assertEqual(result["missing"], ["temperature"])
        self.assertFalse(result["complete"])

    def test_no_conditions_at_all_leaves_every_one_missing(self):
        result = measurement_conditions(None)
        self.assertEqual(sorted(result["missing"]), sorted(REQUIRED_CONDITION_KEYS))

    def test_a_named_condition_and_a_numeric_one_are_both_accepted(self):
        result = measurement_conditions(CONDITIONS)
        self.assertEqual(result["stated"]["spectrum"], "AM0")
        self.assertAlmostEqual(result["stated"]["irradiance"], 1367.0, places=9)

    def test_an_empty_condition_value_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_conditions(dict(CONDITIONS, spectrum="   "))

    def test_a_condition_that_is_neither_number_nor_name_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_conditions(dict(CONDITIONS, temperature=[28.0]))

    def test_a_non_mapping_condition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            measurement_conditions(["AM0", 1367.0, 28.0])


class CharacteristicControlTests(unittest.TestCase):
    def test_a_banded_geometric_characteristic_is_controlled(self):
        result = characteristic_control(CHARACTERISTICS[0])
        self.assertEqual(result["state"], CHAR_CONTROLLED)
        self.assertEqual(result["findings"], [])

    def test_a_nominal_only_characteristic_controls_nothing(self):
        record = dict(
            CHARACTERISTICS[2], limit_form="nominal-only", nominal=150.0
        )
        result = characteristic_control(record)
        self.assertEqual(result["state"], CHAR_UNCONTROLLED)
        self.assertFalse(result["controlled"])

    def test_a_band_of_no_width_leaves_the_characteristic_open(self):
        record = dict(CHARACTERISTICS[0], tolerance=0.0)
        self.assertEqual(characteristic_control(record)["state"], CHAR_OPEN)

    def test_an_electrical_number_without_its_conditions_controls_nothing(self):
        record = copy.deepcopy(CHARACTERISTICS[6])
        del record["conditions"]
        result = characteristic_control(record)
        self.assertEqual(result["state"], CHAR_UNCONTROLLED)
        self.assertEqual(sorted(result["conditions"]["missing"]),
                         sorted(REQUIRED_CONDITION_KEYS))

    def test_an_electrical_number_missing_one_condition_controls_nothing(self):
        record = copy.deepcopy(CHARACTERISTICS[7])
        del record["conditions"]["irradiance"]
        self.assertEqual(characteristic_control(record)["state"], CHAR_UNCONTROLLED)

    def test_an_electrical_number_with_its_conditions_is_controlled(self):
        self.assertEqual(
            characteristic_control(CHARACTERISTICS[8])["state"], CHAR_CONTROLLED
        )

    def test_a_geometric_characteristic_needs_no_measurement_conditions(self):
        result = characteristic_control(CHARACTERISTICS[3])
        self.assertTrue(result["conditions"]["complete"])
        self.assertEqual(result["state"], CHAR_CONTROLLED)

    def test_a_finding_names_the_characteristic_it_came_from(self):
        record = dict(CHARACTERISTICS[5], limit_form="nominal-only", nominal=2.5)
        result = characteristic_control(record)
        self.assertTrue(all(f.startswith("cell-mass:") for f in result["findings"]))

    def test_a_characteristic_with_no_unit_is_rejected(self):
        record = dict(CHARACTERISTICS[0], unit="")
        with self.assertRaises(ValueError):
            characteristic_control(record)

    def test_an_unknown_characteristic_kind_is_rejected(self):
        record = dict(CHARACTERISTICS[0], kind="spiritual")
        with self.assertRaises(ValueError):
            characteristic_control(record)

    def test_a_characteristic_missing_a_required_key_is_rejected(self):
        record = copy.deepcopy(CHARACTERISTICS[0])
        del record["limit_form"]
        with self.assertRaises(ValueError):
            characteristic_control(record)

    def test_every_declared_kind_is_handled(self):
        for kind in CHARACTERISTIC_KINDS:
            record = dict(CHARACTERISTICS[0], kind=kind, conditions=dict(CONDITIONS))
            self.assertIn("state", characteristic_control(record))


class ControlShareTests(unittest.TestCase):
    def test_a_fully_controlled_required_set_scores_one(self):
        results = [characteristic_control(r) for r in CHARACTERISTICS]
        self.assertAlmostEqual(
            controlled_characteristic_share(results), 1.0, places=9
        )

    def test_an_uncontrolled_characteristic_costs_exactly_its_weight(self):
        records = _characteristics(
            **{"cell-length": {"limit_form": "nominal-only", "nominal": 80.0}}
        )
        results = [characteristic_control(r) for r in records]
        expected = (TOTAL_WEIGHT - 3.0) / TOTAL_WEIGHT
        self.assertAlmostEqual(
            controlled_characteristic_share(results), expected, places=9
        )

    def test_a_characteristic_outside_the_required_set_earns_no_weight(self):
        extra = characteristic_control(
            {
                "characteristic": "supplier-lot-code",
                "kind": "physical",
                "unit": "text",
                "limit_form": "minimum",
                "minimum": 1.0,
            }
        )
        results = [characteristic_control(r) for r in CHARACTERISTICS] + [extra]
        self.assertAlmostEqual(
            controlled_characteristic_share(results), 1.0, places=9
        )

    def test_an_empty_result_set_scores_nothing(self):
        self.assertAlmostEqual(controlled_characteristic_share([]), 0.0, places=9)

    def test_a_non_sequence_result_set_is_rejected(self):
        with self.assertRaises(ValueError):
            controlled_characteristic_share({"characteristic": "cell-mass"})


class BareCellDrawingTests(unittest.TestCase):
    def test_a_complete_bare_cell_drawing_is_releasable(self):
        result = assess_bare_cell_drawing(_spec())
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_RELEASABLE)
        self.assertAlmostEqual(result["control_share"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_required_characteristic_the_drawing_omits_stops_the_release(self):
        records = [
            r for r in copy.deepcopy(CHARACTERISTICS)
            if r["characteristic"] != "cell-mass"
        ]
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(result["missing_characteristics"], ["cell-mass"])
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_NOT_RELEASABLE)

    def test_every_required_characteristic_is_looked_for(self):
        result = assess_bare_cell_drawing(
            _spec(characteristics=[CHARACTERISTICS[0]], required_control_share=0.0)
        )
        self.assertEqual(
            sorted(result["missing_characteristics"]),
            sorted(n for n, _k, _w in REQUIRED_CHARACTERISTICS if n != "cell-length"),
        )

    def test_a_nominal_only_required_characteristic_stops_the_release(self):
        records = _characteristics(
            **{"cell-thickness": {"limit_form": "nominal-only", "nominal": 150.0}}
        )
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(result["uncontrolled_characteristics"], ["cell-thickness"])
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_NOT_RELEASABLE)

    def test_an_electrical_number_without_conditions_stops_the_release(self):
        records = _characteristics(**{"open-circuit-voltage": {"conditions": {}}})
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(
            result["uncontrolled_characteristics"], ["open-circuit-voltage"]
        )
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_NOT_RELEASABLE)

    def test_a_band_of_no_width_releases_only_against_open_items(self):
        records = _characteristics(**{"cell-mass": {"limit_form": "range",
                                                    "minimum": 2.5,
                                                    "maximum": 2.5}})
        result = assess_bare_cell_drawing(
            _spec(characteristics=records, required_control_share=0.5)
        )
        self.assertEqual(result["open_characteristics"], ["cell-mass"])
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_OPEN_ITEMS)

    def test_a_weak_characteristic_beyond_the_required_set_does_not_stop_release(self):
        records = copy.deepcopy(CHARACTERISTICS)
        records.append(
            {
                "characteristic": "edge-bevel-note",
                "kind": "geometric",
                "unit": "mm",
                "limit_form": "nominal-only",
                "nominal": 0.2,
            }
        )
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(result["weak_extra_characteristics"], ["edge-bevel-note"])
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_OPEN_ITEMS)

    def test_a_sound_characteristic_beyond_the_required_set_changes_nothing(self):
        records = copy.deepcopy(CHARACTERISTICS)
        records.append(
            {
                "characteristic": "edge-bevel",
                "kind": "geometric",
                "unit": "mm",
                "limit_form": "maximum",
                "maximum": 0.2,
            }
        )
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_RELEASABLE)

    def test_a_required_characteristic_stated_as_the_wrong_kind_stops_release(self):
        records = _characteristics(
            **{"short-circuit-current": {"kind": "physical"}}
        )
        result = assess_bare_cell_drawing(_spec(characteristics=records))
        self.assertEqual(result["miskinded_characteristics"], ["short-circuit-current"])
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_NOT_RELEASABLE)

    def test_a_control_share_exactly_on_its_threshold_is_met(self):
        records = _characteristics(**{"cell-mass": {"limit_form": "range",
                                                    "minimum": 2.5,
                                                    "maximum": 2.5}})
        expected = (TOTAL_WEIGHT - 2.0) / TOTAL_WEIGHT
        result = assess_bare_cell_drawing(
            _spec(characteristics=records, required_control_share=expected)
        )
        self.assertAlmostEqual(result["control_share"], expected, places=9)
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_OPEN_ITEMS)

    def test_a_control_share_under_its_threshold_stops_the_release(self):
        records = _characteristics(**{"cell-mass": {"limit_form": "range",
                                                    "minimum": 2.5,
                                                    "maximum": 2.5}})
        result = assess_bare_cell_drawing(
            _spec(characteristics=records, required_control_share=1.0)
        )
        self.assertEqual(result["verdict"], BARE_CELL_DRAWING_NOT_RELEASABLE)

    def test_the_same_characteristic_stated_twice_is_rejected(self):
        records = copy.deepcopy(CHARACTERISTICS)
        records.append(copy.deepcopy(CHARACTERISTICS[0]))
        with self.assertRaises(ValueError):
            assess_bare_cell_drawing(_spec(characteristics=records))

    def test_a_drawing_stating_no_characteristic_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_drawing(_spec(characteristics=[]))

    def test_a_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_drawing(_spec(required_control_share=2.0))

    def test_a_spec_missing_its_drawing_number_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_drawing(_spec(drawing=None))

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_drawing([CLEAN_SPEC])


if __name__ == "__main__":
    unittest.main(verbosity=1)
