"""Contract tests for the outgassing chamber apparatus configuration logic.

The cases walk the chamber as it is built: the aperture and gap that decide
how much of a compartment's effused flux its collector can intercept, the
one-compartment-to-one-collector pairing, the spread of compartment
temperatures inside a heated zone, the controlled collector plates, and the
base pressure the pump set has to reach under the run condition.
"""

import unittest

from q7002_test_chamber_configuration_logic import (
    DEFAULT_BASE_PRESSURE_MARGIN,
    DEFAULT_CAPTURE_FRACTION_BAND,
    DEFAULT_COLLECTOR_BAND_C,
    DEFAULT_ZONE_SPREAD_C,
    aperture_findings,
    as_positive_float,
    assess_chamber_configuration,
    base_pressure_findings,
    capture_fraction,
    collector_assignment_findings,
    collector_temperature_findings,
    validate_compartment,
    zone_spread_c,
    zone_uniformity_findings,
)


def _compartment(identifier="C1", collector="P1", zone="Z1", **overrides):
    record = {
        "id": identifier,
        "collector_id": collector,
        "zone": zone,
        "aperture_diameter_mm": 8.0,
        "gap_mm": 10.0,
        "temperature_c": 125.0,
    }
    record.update(overrides)
    return record


def _records(*raw):
    return [validate_compartment(item) for item in raw]


class GuardTests(unittest.TestCase):
    def test_positive_float_passes_through(self):
        self.assertAlmostEqual(as_positive_float(8, "x"), 8.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(False, "x")

    def test_nan_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(float("nan"), "x")


class CaptureFractionTests(unittest.TestCase):
    def test_radius_equal_to_gap_intercepts_half(self):
        self.assertAlmostEqual(capture_fraction(10.0, 5.0), 0.5, places=9)

    def test_doubling_the_gap_lowers_the_fraction(self):
        near = capture_fraction(8.0, 10.0)
        far = capture_fraction(8.0, 20.0)
        self.assertLess(far, near)

    def test_widening_the_aperture_raises_the_fraction(self):
        narrow = capture_fraction(4.0, 10.0)
        wide = capture_fraction(12.0, 10.0)
        self.assertGreater(wide, narrow)

    def test_fraction_is_below_one(self):
        self.assertLess(capture_fraction(200.0, 1.0), 1.0)

    def test_known_geometry_value(self):
        self.assertAlmostEqual(capture_fraction(8.0, 10.0), 16.0 / 116.0, places=12)

    def test_zero_gap_rejected(self):
        with self.assertRaises(ValueError):
            capture_fraction(8.0, 0.0)

    def test_negative_aperture_rejected(self):
        with self.assertRaises(ValueError):
            capture_fraction(-8.0, 10.0)


class CompartmentValidationTests(unittest.TestCase):
    def test_record_carries_its_capture_fraction(self):
        record = validate_compartment(_compartment())
        self.assertAlmostEqual(record["capture_fraction"], 16.0 / 116.0, places=12)

    def test_identifiers_are_stripped(self):
        record = validate_compartment(_compartment(identifier="  C4 "))
        self.assertEqual(record["id"], "C4")

    def test_blank_collector_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(_compartment(collector="   "))

    def test_missing_zone_rejected(self):
        record = _compartment()
        del record["zone"]
        with self.assertRaises(ValueError):
            validate_compartment(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_compartment(["C1"])


class ApertureFindingTests(unittest.TestCase):
    def test_in_band_geometry_is_silent(self):
        self.assertEqual(aperture_findings(_records(_compartment())), [])

    def test_band_upper_edge_is_inclusive(self):
        record = _compartment(aperture_diameter_mm=10.0, gap_mm=5.0)
        self.assertAlmostEqual(
            capture_fraction(10.0, 5.0), DEFAULT_CAPTURE_FRACTION_BAND[1], places=9
        )
        self.assertEqual(aperture_findings(_records(record)), [])

    def test_distant_collector_is_flagged(self):
        record = _compartment(aperture_diameter_mm=2.0, gap_mm=20.0)
        notes = aperture_findings(_records(record))
        self.assertEqual(len(notes), 1)
        self.assertIn("outside", notes[0])

    def test_oversized_aperture_is_flagged(self):
        record = _compartment(aperture_diameter_mm=40.0, gap_mm=4.0)
        self.assertEqual(len(aperture_findings(_records(record))), 1)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            aperture_findings(_records(_compartment()), (0.9, 0.1))


class CollectorPairingTests(unittest.TestCase):
    def test_one_to_one_pairing_is_silent(self):
        records = _records(_compartment("C1", "P1"), _compartment("C2", "P2"))
        self.assertEqual(collector_assignment_findings(records), [])

    def test_shared_collector_is_flagged(self):
        records = _records(_compartment("C1", "P1"), _compartment("C2", "P1"))
        notes = collector_assignment_findings(records)
        self.assertEqual(len(notes), 1)
        self.assertIn("serves 2 compartments", notes[0])

    def test_three_on_one_collector_is_one_finding(self):
        records = _records(
            _compartment("C1", "P1"), _compartment("C2", "P1"), _compartment("C3", "P1")
        )
        self.assertEqual(len(collector_assignment_findings(records)), 1)


class ZoneUniformityTests(unittest.TestCase):
    def test_spread_of_a_single_reading_is_zero(self):
        self.assertAlmostEqual(zone_spread_c([125.0]), 0.0)

    def test_spread_is_max_minus_min(self):
        self.assertAlmostEqual(zone_spread_c([124.0, 125.5, 125.0]), 1.5)

    def test_empty_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_spread_c([])

    def test_uniform_zone_is_silent(self):
        records = _records(
            _compartment("C1", "P1", "Z1", temperature_c=125.0),
            _compartment("C2", "P2", "Z1", temperature_c=125.4),
        )
        self.assertEqual(zone_uniformity_findings(records), [])

    def test_spread_exactly_on_the_allowance_is_accepted(self):
        records = _records(
            _compartment("C1", "P1", "Z1", temperature_c=124.0),
            _compartment("C2", "P2", "Z1", temperature_c=125.0),
        )
        self.assertAlmostEqual(
            zone_spread_c([124.0, 125.0]), DEFAULT_ZONE_SPREAD_C, places=9
        )
        self.assertEqual(zone_uniformity_findings(records), [])

    def test_hot_end_of_the_bar_is_flagged(self):
        records = _records(
            _compartment("C1", "P1", "Z1", temperature_c=122.0),
            _compartment("C2", "P2", "Z1", temperature_c=129.0),
        )
        notes = zone_uniformity_findings(records)
        self.assertEqual(len(notes), 1)
        self.assertIn("Z1", notes[0])

    def test_each_zone_is_reported_separately(self):
        records = _records(
            _compartment("C1", "P1", "Z1", temperature_c=120.0),
            _compartment("C2", "P2", "Z1", temperature_c=130.0),
            _compartment("C3", "P3", "Z2", temperature_c=118.0),
            _compartment("C4", "P4", "Z2", temperature_c=128.0),
        )
        self.assertEqual(len(zone_uniformity_findings(records)), 2)


class CollectorTemperatureTests(unittest.TestCase):
    def test_controlled_plates_are_silent(self):
        self.assertEqual(
            collector_temperature_findings({"P1": 25.0, "P2": 24.8}), []
        )

    def test_band_edges_are_inclusive(self):
        low, high = DEFAULT_COLLECTOR_BAND_C
        self.assertEqual(collector_temperature_findings({"P1": low, "P2": high}), [])

    def test_warm_plate_is_flagged(self):
        notes = collector_temperature_findings({"P1": 31.0})
        self.assertEqual(len(notes), 1)
        self.assertIn("P1", notes[0])

    def test_empty_collector_set_rejected(self):
        with self.assertRaises(ValueError):
            collector_temperature_findings({})


class BasePressureTests(unittest.TestCase):
    def test_deep_base_pressure_is_silent(self):
        self.assertEqual(base_pressure_findings(1.0e-5, 1.0e-3), [])

    def test_exactly_the_required_margin_is_accepted(self):
        run = 1.0e-3
        base = run / DEFAULT_BASE_PRESSURE_MARGIN
        self.assertEqual(base_pressure_findings(base, run), [])

    def test_shallow_base_pressure_is_flagged(self):
        notes = base_pressure_findings(5.0e-4, 1.0e-3)
        self.assertEqual(len(notes), 1)
        self.assertIn("times below", notes[0])

    def test_zero_run_pressure_rejected(self):
        with self.assertRaises(ValueError):
            base_pressure_findings(1.0e-5, 0.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "compartments": [
                _compartment("C1", "P1", "Z1", temperature_c=125.0),
                _compartment("C2", "P2", "Z1", temperature_c=125.2),
                _compartment("C3", "P3", "Z2", temperature_c=124.9),
            ],
            "collectors": {"P1": 25.0, "P2": 25.1, "P3": 24.9},
            "base_pressure_pa": 1.0e-5,
            "run_pressure_pa": 1.0e-3,
        }
        spec.update(overrides)
        return spec

    def test_nominal_chamber_is_configured(self):
        result = assess_chamber_configuration(self._spec())
        self.assertTrue(result["configured"])
        self.assertEqual(result["findings"], [])

    def test_capture_fractions_are_reported_per_compartment(self):
        result = assess_chamber_configuration(self._spec())
        self.assertEqual(sorted(result["capture_fractions"]), ["C1", "C2", "C3"])

    def test_zones_are_listed(self):
        result = assess_chamber_configuration(self._spec())
        self.assertEqual(result["zones"], ["Z1", "Z2"])

    def test_unknown_collector_is_flagged(self):
        spec = self._spec()
        spec["compartments"][0]["collector_id"] = "P9"
        result = assess_chamber_configuration(spec)
        self.assertFalse(result["configured"])
        self.assertTrue(any("does not have" in note for note in result["findings"]))

    def test_unpaired_collector_is_flagged(self):
        spec = self._spec()
        spec["collectors"]["P4"] = 25.0
        result = assess_chamber_configuration(spec)
        self.assertTrue(
            any("not paired with any compartment" in note for note in result["findings"])
        )

    def test_duplicate_compartment_id_rejected(self):
        spec = self._spec()
        spec["compartments"][1]["id"] = "C1"
        with self.assertRaises(ValueError):
            assess_chamber_configuration(spec)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["collectors"]
        with self.assertRaises(ValueError):
            assess_chamber_configuration(spec)

    def test_empty_compartment_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_chamber_configuration(self._spec(compartments=[]))

    def test_several_defects_are_all_reported(self):
        spec = self._spec()
        spec["compartments"][1]["collector_id"] = "P1"
        spec["compartments"][2]["temperature_c"] = 140.0
        spec["collectors"]["P3"] = 40.0
        result = assess_chamber_configuration(spec)
        self.assertGreaterEqual(len(result["findings"]), 3)
        self.assertFalse(result["configured"])


if __name__ == "__main__":
    unittest.main()
