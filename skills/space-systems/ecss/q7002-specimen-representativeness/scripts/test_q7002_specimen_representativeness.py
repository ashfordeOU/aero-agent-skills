"""Contract tests for the outgassing test-item representativeness logic.

The cases follow a coupon from the balance bench backwards: the mass window the
method holds it to, the exposed area per unit mass that decides whether it is
the same geometry family as the flight part, the four process attributes that
fix the build it came out of, the preconditioning soak that sets what the
initial weighing means, and the sample-level verdict that comes out of all of
them.
"""

import unittest

from q7002_specimen_representativeness_logic import (
    AREA_RATIO_TOLERANCE,
    DEFAULT_CONDITIONING_HOURS,
    DEFAULT_MASS_WINDOW_MG,
    FLIGHT_STATE_KEYS,
    MIN_REPLICATES,
    area_finding,
    area_ratio_deviation,
    as_positive_float,
    assess_specimen_representativeness,
    conditioning_findings,
    evaluate_specimen,
    mass_window_finding,
    normalize_state_value,
    replicate_finding,
    specific_surface_area,
    state_deviations,
)

FLIGHT_STATE = {
    "cure-schedule": "120 C for 4 h",
    "cleaning-process": "isopropanol wipe",
    "surface-treatment": "as-moulded",
    "material-lot": "LOT-4471",
}

FLIGHT_PART = {"area_mm2": 1200.0, "mass_mg": 240.0, "state": dict(FLIGHT_STATE)}


def _conditioning(**overrides):
    record = {"hours": 24.0, "temperature_c": 23.0, "relative_humidity_pct": 50.0}
    record.update(overrides)
    return record


def _specimen(identifier="S1", **overrides):
    item = {
        "id": identifier,
        "mass_mg": 200.0,
        "area_mm2": 1000.0,
        "state": dict(FLIGHT_STATE),
        "conditioning": _conditioning(),
    }
    item.update(overrides)
    return item


class NumericGuardTests(unittest.TestCase):
    def test_positive_float_passes_through(self):
        self.assertAlmostEqual(as_positive_float(3, "x"), 3.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(0.0, "x")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(True, "x")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float(float("inf"), "x")

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            as_positive_float("200", "x")


class SpecificSurfaceAreaTests(unittest.TestCase):
    def test_ratio_is_area_over_mass(self):
        self.assertAlmostEqual(specific_surface_area(1000.0, 200.0), 5.0)

    def test_thinner_slice_raises_the_ratio(self):
        thick = specific_surface_area(1200.0, 240.0)
        thin = specific_surface_area(1200.0, 120.0)
        self.assertGreater(thin, thick * 1.5)

    def test_zero_mass_rejected(self):
        with self.assertRaises(ValueError):
            specific_surface_area(1000.0, 0.0)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            specific_surface_area(-1000.0, 200.0)


class MassWindowTests(unittest.TestCase):
    def test_mid_window_mass_has_no_finding(self):
        self.assertIsNone(mass_window_finding(200.0))

    def test_lower_bound_is_inclusive(self):
        self.assertIsNone(mass_window_finding(DEFAULT_MASS_WINDOW_MG[0]))

    def test_upper_bound_is_inclusive(self):
        self.assertIsNone(mass_window_finding(DEFAULT_MASS_WINDOW_MG[1]))

    def test_light_coupon_is_flagged(self):
        note = mass_window_finding(60.0)
        self.assertIn("below", note)

    def test_heavy_coupon_is_flagged(self):
        note = mass_window_finding(450.0)
        self.assertIn("above", note)

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            mass_window_finding(200.0, (300.0, 100.0))


class AreaFindingTests(unittest.TestCase):
    def test_matching_geometry_has_no_finding(self):
        self.assertIsNone(area_finding(5.0, 5.0))

    def test_deviation_is_signed(self):
        self.assertAlmostEqual(area_ratio_deviation(6.0, 5.0), 0.2)
        self.assertAlmostEqual(area_ratio_deviation(4.0, 5.0), -0.2)

    def test_deviation_exactly_on_the_allowance_is_accepted(self):
        deviation = area_ratio_deviation(6.0, 5.0)
        self.assertAlmostEqual(deviation, AREA_RATIO_TOLERANCE, places=9)
        self.assertIsNone(area_finding(6.0, 5.0))

    def test_thin_slice_is_flagged(self):
        note = area_finding(9.0, 5.0)
        self.assertIn("specific surface area", note)

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            area_finding(5.0, 5.0, 0.0)


class StateDeviationTests(unittest.TestCase):
    def test_identical_state_has_no_deviation(self):
        self.assertEqual(state_deviations(dict(FLIGHT_STATE), FLIGHT_STATE), [])

    def test_case_and_spacing_are_not_a_deviation(self):
        loose = dict(FLIGHT_STATE)
        loose["material-lot"] = "  lot-4471 "
        self.assertEqual(state_deviations(loose, FLIGHT_STATE), [])

    def test_changed_lot_is_named(self):
        other = dict(FLIGHT_STATE)
        other["material-lot"] = "LOT-9000"
        self.assertEqual(state_deviations(other, FLIGHT_STATE), ["material-lot"])

    def test_missing_attribute_counts_as_a_deviation(self):
        partial = dict(FLIGHT_STATE)
        del partial["cleaning-process"]
        self.assertEqual(state_deviations(partial, FLIGHT_STATE), ["cleaning-process"])

    def test_deviations_are_reported_in_order(self):
        other = dict(FLIGHT_STATE)
        other["surface-treatment"] = "primed"
        other["cure-schedule"] = "ambient"
        self.assertEqual(
            state_deviations(other, FLIGHT_STATE), ["cure-schedule", "surface-treatment"]
        )

    def test_flight_reference_missing_an_attribute_is_an_error(self):
        broken = dict(FLIGHT_STATE)
        del broken["cure-schedule"]
        with self.assertRaises(ValueError):
            state_deviations(dict(FLIGHT_STATE), broken)

    def test_blank_attribute_value_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state_value("   ")

    def test_non_string_attribute_value_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state_value(4471)

    def test_every_declared_attribute_is_compared(self):
        self.assertEqual(len(FLIGHT_STATE_KEYS), 4)


class ConditioningTests(unittest.TestCase):
    def test_nominal_soak_has_no_findings(self):
        self.assertEqual(conditioning_findings(_conditioning()), [])

    def test_exact_declared_hours_accepted(self):
        record = _conditioning(hours=DEFAULT_CONDITIONING_HOURS)
        self.assertEqual(conditioning_findings(record), [])

    def test_short_soak_is_flagged(self):
        notes = conditioning_findings(_conditioning(hours=6.0))
        self.assertEqual(len(notes), 1)
        self.assertIn("short of", notes[0])

    def test_warm_room_is_flagged(self):
        notes = conditioning_findings(_conditioning(temperature_c=29.0))
        self.assertIn("temperature", notes[0])

    def test_dry_room_is_flagged(self):
        notes = conditioning_findings(_conditioning(relative_humidity_pct=20.0))
        self.assertIn("humidity", notes[0])

    def test_three_departures_give_three_findings(self):
        notes = conditioning_findings(
            _conditioning(hours=2.0, temperature_c=31.0, relative_humidity_pct=12.0)
        )
        self.assertEqual(len(notes), 3)

    def test_impossible_humidity_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_findings(_conditioning(relative_humidity_pct=140.0))

    def test_negative_hours_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_findings(_conditioning(hours=-1.0))

    def test_missing_field_rejected(self):
        record = _conditioning()
        del record["temperature_c"]
        with self.assertRaises(ValueError):
            conditioning_findings(record)


class ReplicateTests(unittest.TestCase):
    def test_full_set_has_no_finding(self):
        self.assertIsNone(replicate_finding(MIN_REPLICATES))

    def test_single_coupon_is_flagged(self):
        self.assertIn("required", replicate_finding(1))

    def test_non_integer_count_rejected(self):
        with self.assertRaises(ValueError):
            replicate_finding(2.5)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            replicate_finding(-1)


class EvaluateSpecimenTests(unittest.TestCase):
    def test_flight_like_coupon_is_representative(self):
        record = evaluate_specimen(_specimen(), FLIGHT_PART)
        self.assertTrue(record["representative"])
        self.assertEqual(record["findings"], [])

    def test_ratio_is_reported(self):
        record = evaluate_specimen(_specimen(), FLIGHT_PART)
        self.assertAlmostEqual(record["specific_surface_area_mm2_per_mg"], 5.0)

    def test_thin_coupon_is_not_representative(self):
        record = evaluate_specimen(
            _specimen(area_mm2=1800.0, mass_mg=150.0), FLIGHT_PART
        )
        self.assertFalse(record["representative"])

    def test_wrong_lot_is_named_in_the_findings(self):
        state = dict(FLIGHT_STATE)
        state["material-lot"] = "LOT-0001"
        record = evaluate_specimen(_specimen(state=state), FLIGHT_PART)
        self.assertIn("material-lot", record["state_deviations"])

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen(_specimen(identifier="  "), FLIGHT_PART)

    def test_missing_specimen_key_rejected(self):
        item = _specimen()
        del item["area_mm2"]
        with self.assertRaises(ValueError):
            evaluate_specimen(item, FLIGHT_PART)

    def test_missing_flight_key_rejected(self):
        flight = dict(FLIGHT_PART)
        del flight["mass_mg"]
        with self.assertRaises(ValueError):
            evaluate_specimen(_specimen(), flight)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "specimens": [_specimen("S1"), _specimen("S2"), _specimen("S3")],
            "flight": FLIGHT_PART,
        }
        spec.update(overrides)
        return spec

    def test_clean_sample_is_representative(self):
        result = assess_specimen_representativeness(self._spec())
        self.assertTrue(result["representative_sample"])
        self.assertEqual(result["findings"], [])

    def test_accepted_list_carries_every_coupon(self):
        result = assess_specimen_representativeness(self._spec())
        self.assertEqual(result["accepted"], ["S1", "S2", "S3"])

    def test_short_sample_is_flagged(self):
        result = assess_specimen_representativeness(
            self._spec(specimens=[_specimen("S1"), _specimen("S2")])
        )
        self.assertFalse(result["representative_sample"])
        self.assertIn("2 coupon(s)", result["findings"][0])

    def test_duplicate_identifier_is_flagged(self):
        result = assess_specimen_representativeness(
            self._spec(specimens=[_specimen("S1"), _specimen("S1"), _specimen("S3")])
        )
        self.assertTrue(any("used more than once" in note for note in result["findings"]))

    def test_one_bad_coupon_rejects_the_sample(self):
        bad = _specimen("S3", mass_mg=40.0, area_mm2=200.0)
        result = assess_specimen_representativeness(
            self._spec(specimens=[_specimen("S1"), _specimen("S2"), bad])
        )
        self.assertEqual(result["rejected"], ["S3"])
        self.assertFalse(result["representative_sample"])

    def test_empty_sample_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen_representativeness(self._spec(specimens=[]))

    def test_missing_flight_reference_rejected(self):
        spec = self._spec()
        del spec["flight"]
        with self.assertRaises(ValueError):
            assess_specimen_representativeness(spec)

    def test_options_can_widen_the_geometry_allowance(self):
        thin = _specimen("S3", area_mm2=1500.0, mass_mg=200.0)
        strict = assess_specimen_representativeness(
            self._spec(specimens=[_specimen("S1"), _specimen("S2"), thin])
        )
        relaxed = assess_specimen_representativeness(
            self._spec(
                specimens=[_specimen("S1"), _specimen("S2"), thin],
                options={"area_tolerance": 0.75},
            )
        )
        self.assertFalse(strict["representative_sample"])
        self.assertTrue(relaxed["representative_sample"])


if __name__ == "__main__":
    unittest.main()
