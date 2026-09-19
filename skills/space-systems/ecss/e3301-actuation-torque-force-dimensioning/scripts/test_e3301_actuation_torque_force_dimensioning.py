"""Contract test for the actuation-dimensioning leaf (stdlib unittest)."""

import unittest

from e3301_actuation_torque_force_dimensioning_logic import (
    END_OF_LIFE_DERATION_KEY,
    VERDICT_NEGATIVE,
    VERDICT_POSITIVE,
    VERDICT_ZERO,
    assess_actuation_dimensioning,
    assess_station,
    available_capability,
    margin_verdict,
    motorization_margin,
    travel_coverage_findings,
    validate_derations,
    validate_station,
)


def station(sid="S-0", position=0.0, life_point="begin-of-life", **kw):
    record = {
        "id": sid,
        "travel_position": position,
        "life_point": life_point,
        "nominal_capability": 1.00,
        "factored_resistive": 0.50,
        "derations": {"low-bus-voltage": 0.90},
    }
    if life_point == "end-of-life":
        record["derations"] = {
            "low-bus-voltage": 0.90,
            END_OF_LIFE_DERATION_KEY: 0.85,
        }
    record.update(kw)
    return record


def schedule(life_point="begin-of-life", prefix="B"):
    return [
        station("%s-%d" % (prefix, p), float(p), life_point)
        for p in range(0, 91, 6)
    ]


def function_record(**kw):
    record = {
        "id": "SADM-DRIVE",
        "units": "torque-nm",
        "travel_range": 90.0,
        "required_margin": 0.0,
        "required_life_points": ["begin-of-life", "end-of-life"],
        "stations": schedule("begin-of-life", "B") + schedule("end-of-life", "E"),
    }
    record.update(kw)
    return record


class TestDerations(unittest.TestCase):
    def test_absent_derations_normalize_to_empty(self):
        self.assertEqual(validate_derations(None), {})

    def test_unknown_deration_key_raises(self):
        with self.assertRaises(ValueError):
            validate_derations({"cosmic-rays": 0.9})

    def test_deration_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_derations({"low-bus-voltage": 1.2})

    def test_zero_deration_raises(self):
        with self.assertRaises(ValueError):
            validate_derations({"low-bus-voltage": 0.0})

    def test_non_mapping_derations_raise(self):
        with self.assertRaises(ValueError):
            validate_derations(["low-bus-voltage"])


class TestAvailableCapability(unittest.TestCase):
    def test_derations_multiply(self):
        value = available_capability(
            1.0, {"low-bus-voltage": 0.90, "temperature-extreme": 0.80}
        )
        self.assertAlmostEqual(value, 0.72, places=9)

    def test_no_derations_passes_the_nominal_through(self):
        self.assertAlmostEqual(available_capability(2.5, {}), 2.5, places=9)

    def test_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            available_capability(0.0, {})


class TestMotorizationMargin(unittest.TestCase):
    def test_twice_the_demand_gives_unit_margin(self):
        self.assertAlmostEqual(motorization_margin(1.0, 0.5), 1.0, places=9)

    def test_capability_equal_to_demand_gives_zero(self):
        self.assertAlmostEqual(motorization_margin(0.5, 0.5), 0.0, places=9)

    def test_zero_demand_raises(self):
        with self.assertRaises(ValueError):
            motorization_margin(1.0, 0.0)

    def test_boolean_available_raises(self):
        with self.assertRaises(ValueError):
            motorization_margin(True, 0.5)

    def test_verdict_against_a_raised_requirement(self):
        self.assertEqual(margin_verdict(0.30, 0.50), VERDICT_NEGATIVE)
        self.assertEqual(margin_verdict(0.80, 0.50), VERDICT_POSITIVE)

    def test_margin_exactly_on_the_requirement_is_zero(self):
        self.assertEqual(margin_verdict(0.50, 0.50), VERDICT_ZERO)

    def test_last_place_noise_is_grouped_as_zero(self):
        self.assertEqual(margin_verdict(0.5 - 1.0e-15, 0.5), VERDICT_ZERO)


class TestValidateStation(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_station("S-0")

    def test_unknown_life_point_raises(self):
        with self.assertRaises(ValueError):
            validate_station(station(life_point="mid-life"))

    def test_zero_resistive_demand_raises(self):
        with self.assertRaises(ValueError):
            validate_station(station(factored_resistive=0.0))

    def test_negative_travel_position_raises(self):
        with self.assertRaises(ValueError):
            validate_station(station(position=-5.0))


class TestAssessStation(unittest.TestCase):
    def test_healthy_station_passes(self):
        result = assess_station(station())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["available_capability"], 0.90, places=9)
        self.assertAlmostEqual(result["motorization_margin"], 0.80, places=9)

    def test_short_station_is_reported(self):
        result = assess_station(station(factored_resistive=1.20))
        self.assertFalse(result["compliant"])
        self.assertIn("motorization-margin-below-requirement", result["findings"])
        self.assertEqual(result["verdict"], VERDICT_NEGATIVE)

    def test_raised_requirement_can_fail_a_positive_margin(self):
        result = assess_station(station(), required_margin=1.50)
        self.assertFalse(result["compliant"])

    def test_end_of_life_station_without_degradation_is_reported(self):
        result = assess_station(
            station(life_point="end-of-life", derations={"low-bus-voltage": 0.9})
        )
        self.assertIn("end-of-life-degradation-not-applied", result["findings"])


class TestTravelCoverage(unittest.TestCase):
    def test_dense_schedule_covers_the_range(self):
        self.assertEqual(
            travel_coverage_findings(schedule(), 90.0, "begin-of-life"), []
        )

    def test_two_point_schedule_leaves_a_gap(self):
        stations = [station("S-0", 0.0), station("S-1", 90.0)]
        findings = travel_coverage_findings(stations, 90.0, "begin-of-life")
        self.assertIn("travel-gap-wider-than-allowed:begin-of-life", findings)

    def test_schedule_stopping_short_is_reported(self):
        stations = [station("S-%d" % p, float(p)) for p in range(0, 50, 5)]
        findings = travel_coverage_findings(stations, 90.0, "begin-of-life")
        self.assertIn("travel-end-not-covered:begin-of-life", findings)

    def test_absent_life_point_is_reported(self):
        findings = travel_coverage_findings(schedule(), 90.0, "end-of-life")
        self.assertEqual(findings, ["no-station-at:end-of-life"])

    def test_zero_travel_range_raises(self):
        with self.assertRaises(ValueError):
            travel_coverage_findings(schedule(), 0.0, "begin-of-life")


class TestAssessFunction(unittest.TestCase):
    def test_complete_function_passes(self):
        report = assess_actuation_dimensioning(function_record())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["coverage_findings"], [])

    def test_governing_station_is_the_worst_one(self):
        record = function_record()
        record["stations"] = list(record["stations"])
        record["stations"].append(
            station("E-PEAK", 45.0, "end-of-life", factored_resistive=0.70)
        )
        report = assess_actuation_dimensioning(record)
        self.assertEqual(report["governing_station_id"], "E-PEAK")
        self.assertEqual(report["governing_life_point"], "end-of-life")

    def test_missing_end_of_life_schedule_fails_coverage(self):
        report = assess_actuation_dimensioning(
            function_record(stations=schedule("begin-of-life", "B"))
        )
        self.assertFalse(report["compliant"])
        self.assertIn("no-station-at:end-of-life", report["coverage_findings"])

    def test_one_short_station_fails_the_function(self):
        record = function_record()
        record["stations"] = list(record["stations"])
        record["stations"].append(
            station("E-STALL", 45.0, "end-of-life", factored_resistive=2.0)
        )
        report = assess_actuation_dimensioning(record)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_station_ids"], ["E-STALL"])

    def test_duplicate_station_id_raises(self):
        record = function_record(stations=[station("S-0"), station("S-0")])
        with self.assertRaises(ValueError):
            assess_actuation_dimensioning(record)

    def test_empty_station_list_raises(self):
        with self.assertRaises(ValueError):
            assess_actuation_dimensioning(function_record(stations=[]))

    def test_unknown_units_raise(self):
        with self.assertRaises(ValueError):
            assess_actuation_dimensioning(function_record(units="newton-fathoms"))

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            assess_actuation_dimensioning(function_record(required_margin=-0.1))


if __name__ == "__main__":
    unittest.main()
