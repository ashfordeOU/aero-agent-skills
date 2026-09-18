"""Contract tests for the clause 5.4.1.3.1 off-state leakage and voltage logic."""

import unittest

from e2020_off_state_leakage_and_voltage_logic import (
    LEAKAGE_TOLERANCE_UA,
    MEASUREMENT_CORNERS,
    OFF_STATE_CATEGORIES,
    REQUIRED_CORNERS,
    VOLTAGE_TOLERANCE_V,
    assess_off_state,
    governing_leakage_ceiling_ua,
    grade_corner,
    implied_residual_voltage_v,
    leakage_margin_ua,
    normalise_category,
    normalise_corner,
    residual_voltage_margin_v,
    validate_limits,
    validate_measurements,
    worst_corner,
)

# A latching channel permitted 5 uA of off-state leakage and 1 V of residual
# output voltage into a 100 kohm off-state load, measured at all three corners.
BASE_MEASUREMENTS = [
    {"corner": "cold", "leakage_ua": 1.0, "residual_voltage_v": 0.1},
    {"corner": "ambient", "leakage_ua": 2.0, "residual_voltage_v": 0.2},
    {"corner": "hot", "leakage_ua": 4.0, "residual_voltage_v": 0.4},
]

BASE = {
    "category": "latching",
    "max_leakage_ua": 5.0,
    "max_residual_voltage_v": 1.0,
    "load_off_resistance_ohm": 100000.0,
    "measurements": BASE_MEASUREMENTS,
}


def spec(**overrides):
    merged = dict(BASE)
    merged["measurements"] = [dict(m) for m in BASE_MEASUREMENTS]
    merged.update(overrides)
    return merged


def with_corner(corner, **changes):
    rows = []
    for entry in BASE_MEASUREMENTS:
        row = dict(entry)
        if row["corner"] == corner:
            row.update(changes)
        rows.append(row)
    return spec(measurements=rows)


class NormalisationTests(unittest.TestCase):
    def test_category_aliases_are_folded(self):
        self.assertEqual(normalise_category("LCL"), "latching")
        self.assertEqual(normalise_category(" hpc "), "high-power")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("diode")

    def test_corner_aliases_are_folded(self):
        self.assertEqual(normalise_corner("Room-Temperature"), "ambient")
        self.assertEqual(normalise_corner("high-temperature"), "hot")

    def test_unknown_corner_rejected(self):
        with self.assertRaises(ValueError):
            normalise_corner("vibration")

    def test_empty_corner_rejected(self):
        with self.assertRaises(ValueError):
            normalise_corner("   ")

    def test_vocabularies_are_fixed(self):
        self.assertEqual(REQUIRED_CORNERS, ("cold", "ambient", "hot"))
        self.assertEqual(MEASUREMENT_CORNERS, REQUIRED_CORNERS)
        self.assertEqual(OFF_STATE_CATEGORIES, ("latching", "high-power"))


class ValidationTests(unittest.TestCase):
    def test_valid_limits_are_canonicalised(self):
        limits = validate_limits(spec(category="hpc"))
        self.assertEqual(limits["category"], "high-power")
        self.assertAlmostEqual(limits["max_leakage_ua"], 5.0, places=9)

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(["latching"])

    def test_missing_resistance_rejected(self):
        broken = spec()
        del broken["load_off_resistance_ohm"]
        with self.assertRaises(ValueError):
            validate_limits(broken)

    def test_zero_residual_voltage_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(spec(max_residual_voltage_v=0.0))

    def test_boolean_leakage_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(spec(max_leakage_ua=True))

    def test_zero_leakage_measurement_is_allowed(self):
        measurements = validate_measurements(
            [{"corner": "cold", "leakage_ua": 0.0, "residual_voltage_v": 0.0}]
        )
        self.assertAlmostEqual(measurements["cold"]["leakage_ua"], 0.0, places=9)

    def test_negative_leakage_measurement_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurements(
                [{"corner": "cold", "leakage_ua": -1.0, "residual_voltage_v": 0.1}]
            )

    def test_empty_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurements([])

    def test_non_sequence_measurement_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurements({"corner": "cold"})

    def test_duplicate_corner_rejected(self):
        rows = [dict(m) for m in BASE_MEASUREMENTS]
        rows.append({"corner": "room", "leakage_ua": 1.0, "residual_voltage_v": 0.1})
        with self.assertRaises(ValueError):
            validate_measurements(rows)

    def test_missing_measurement_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurements([{"corner": "cold", "leakage_ua": 1.0}])


class CouplingTests(unittest.TestCase):
    def test_implied_voltage_is_leakage_through_the_off_state_load(self):
        self.assertAlmostEqual(
            implied_residual_voltage_v(5.0, 100000.0), 0.5, places=9
        )

    def test_implied_voltage_rejects_a_zero_resistance(self):
        with self.assertRaises(ValueError):
            implied_residual_voltage_v(5.0, 0.0)

    def test_ceiling_is_the_leakage_limit_when_the_limits_agree(self):
        self.assertAlmostEqual(
            governing_leakage_ceiling_ua(validate_limits(spec())), 5.0, places=9
        )

    def test_ceiling_tightens_when_the_voltage_limit_binds(self):
        limits = validate_limits(spec(max_residual_voltage_v=0.2))
        self.assertAlmostEqual(governing_leakage_ceiling_ua(limits), 2.0, places=9)

    def test_margins_are_taken_against_the_governing_ceiling(self):
        limits = validate_limits(spec(max_residual_voltage_v=0.2))
        measurement = validate_measurements(BASE_MEASUREMENTS)["hot"]
        self.assertAlmostEqual(leakage_margin_ua(limits, measurement), -2.0, places=9)

    def test_residual_voltage_margin_is_limit_less_measurement(self):
        limits = validate_limits(spec())
        measurement = validate_measurements(BASE_MEASUREMENTS)["hot"]
        self.assertAlmostEqual(
            residual_voltage_margin_v(limits, measurement), 0.6, places=9
        )


class CornerGradingTests(unittest.TestCase):
    def test_corner_inside_both_limits_is_clean(self):
        record = grade_corner(
            validate_limits(spec()), validate_measurements(BASE_MEASUREMENTS)["cold"]
        )
        self.assertTrue(record["within_limits"])
        self.assertEqual(record["findings"], [])

    def test_leakage_exactly_on_the_ceiling_is_accepted(self):
        rows = [{"corner": "hot", "leakage_ua": 5.0, "residual_voltage_v": 0.4}]
        record = grade_corner(
            validate_limits(spec()), validate_measurements(rows)["hot"]
        )
        self.assertAlmostEqual(record["leakage_margin_ua"], 0.0, places=9)
        self.assertTrue(record["within_limits"])

    def test_residual_voltage_exactly_on_the_limit_is_accepted(self):
        rows = [{"corner": "hot", "leakage_ua": 1.0, "residual_voltage_v": 1.0}]
        record = grade_corner(
            validate_limits(spec()), validate_measurements(rows)["hot"]
        )
        self.assertAlmostEqual(record["residual_voltage_margin_v"], 0.0, places=9)
        self.assertTrue(record["within_limits"])

    def test_leakage_above_the_ceiling_is_reported(self):
        rows = [{"corner": "hot", "leakage_ua": 9.0, "residual_voltage_v": 0.4}]
        record = grade_corner(
            validate_limits(spec()), validate_measurements(rows)["hot"]
        )
        self.assertFalse(record["within_limits"])
        self.assertTrue(any("leakage" in f for f in record["findings"]))

    def test_worst_corner_is_the_smallest_margin(self):
        result = assess_off_state(spec())
        self.assertEqual(result["worst_leakage_corner"], "hot")
        self.assertEqual(result["worst_residual_voltage_corner"], "hot")

    def test_worst_corner_rejects_an_unknown_margin_key(self):
        result = assess_off_state(spec())
        with self.assertRaises(ValueError):
            worst_corner(result["corner_records"], "temperature_margin_c")

    def test_worst_corner_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            worst_corner([], "leakage_margin_ua")


class AssessmentTests(unittest.TestCase):
    def test_device_inside_both_limits_at_every_corner_is_compliant(self):
        result = assess_off_state(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_corners"], [])

    def test_high_power_category_is_graded_the_same_way(self):
        result = assess_off_state(spec(category="high-power"))
        self.assertEqual(result["verdict"], "compliant")

    def test_leakage_breach_at_the_hot_corner_fails(self):
        result = assess_off_state(with_corner("hot", leakage_ua=9.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("hot corner" in f for f in result["findings"]))

    def test_residual_voltage_breach_fails_independently_of_leakage(self):
        result = assess_off_state(with_corner("ambient", residual_voltage_v=1.4))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(
            any("residual output voltage" in f for f in result["findings"])
        )

    def test_mutually_inconsistent_limits_are_caught_before_any_measurement(self):
        result = assess_off_state(spec(max_residual_voltage_v=0.2))
        self.assertFalse(result["limits_consistent"])
        self.assertAlmostEqual(result["governing_leakage_ceiling_ua"], 2.0, places=9)
        self.assertTrue(any("governing leakage ceiling" in f for f in result["findings"]))

    def test_limits_that_meet_exactly_are_consistent(self):
        result = assess_off_state(spec(max_residual_voltage_v=0.5))
        self.assertAlmostEqual(
            result["residual_voltage_from_leakage_limit_v"], 0.5, places=9
        )
        self.assertTrue(result["limits_consistent"])
        self.assertEqual(result["verdict"], "compliant")

    def test_ambient_only_data_set_is_reported_as_unbounded(self):
        rows = [{"corner": "ambient", "leakage_ua": 2.0, "residual_voltage_v": 0.2}]
        result = assess_off_state(spec(measurements=rows))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertEqual(result["missing_corners"], ["cold", "hot"])
        self.assertTrue(any("not bounded" in f for f in result["findings"]))

    def test_foldback_category_is_reported_out_of_scope(self):
        result = assess_off_state(spec(category="foldback"))
        self.assertEqual(result["verdict"], "out-of-scope")
        self.assertFalse(result["in_scope"])

    def test_missing_measurements_key_rejected(self):
        broken = spec()
        del broken["measurements"]
        with self.assertRaises(ValueError):
            assess_off_state(broken)

    def test_corner_records_are_returned_in_a_stable_order(self):
        result = assess_off_state(spec())
        self.assertEqual(
            [r["corner"] for r in result["corner_records"]],
            ["ambient", "cold", "hot"],
        )

    def test_implied_voltage_is_carried_per_corner(self):
        result = assess_off_state(spec())
        hot = [r for r in result["corner_records"] if r["corner"] == "hot"][0]
        self.assertAlmostEqual(hot["implied_residual_voltage_v"], 0.4, places=9)

    def test_tolerances_are_representation_sized(self):
        self.assertLess(LEAKAGE_TOLERANCE_UA, 1e-6)
        self.assertLess(VOLTAGE_TOLERANCE_V, 1e-6)


if __name__ == "__main__":
    unittest.main()
