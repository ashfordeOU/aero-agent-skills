#!/usr/bin/env python3
"""Contract tests for the clause 7.5.10 contact thickness logic (offline)."""

import copy
import unittest

from e2008_cell_contact_thickness_test_logic import (
    ABOVE_MAXIMUM,
    BELOW_MINIMUM,
    CONFORMING,
    CONTACT_TYPES,
    DEFAULT_ACCEPTANCE_POLICY,
    DISPOSITIONS,
    INDETERMINATE_HIGH,
    INDETERMINATE_LOW,
    LOT_INDETERMINATE,
    LOT_REJECTED,
    LOT_RELEASED,
    SAMPLE_INADEQUATE,
    acceptance_limits,
    assess_lot_release,
    capability_indices,
    conformance_zone,
    disposition_counts,
    indeterminate_cells,
    lot_statistics,
    nonconforming_cells,
    nonconforming_fraction,
    normalise_measurements,
    reading_disposition,
    required_sample_size,
    sample_adequacy,
    validate_acceptance_policy,
)

RELEASABLE_SAMPLE = [
    ("cell-01", 7.4),
    ("cell-02", 7.6),
    ("cell-03", 7.5),
    ("cell-04", 7.3),
    ("cell-05", 7.7),
    ("cell-06", 7.5),
]

THIN_CELL_SAMPLE = [
    ("cell-01", 7.4),
    ("cell-02", 7.6),
    ("cell-03", 2.8),
    ("cell-04", 7.3),
    ("cell-05", 7.7),
    ("cell-06", 7.5),
]

GUARD_BAND_SAMPLE = [
    ("cell-01", 7.4),
    ("cell-02", 7.6),
    ("cell-03", 3.10),
    ("cell-04", 7.3),
    ("cell-05", 7.7),
    ("cell-06", 7.5),
]

WIDE_SPREAD_SAMPLE = [
    ("cell-01", 3.3),
    ("cell-02", 11.7),
    ("cell-03", 3.4),
    ("cell-04", 11.6),
    ("cell-05", 3.5),
    ("cell-06", 11.5),
]

FLAT_SAMPLE = [("cell-0%d" % index, 7.5) for index in range(1, 7)]


def _case(**overrides):
    case = {
        "lot_identifier": "lot-14",
        "contact_type": "front-bus-bar",
        "lot_size": 50,
        "measurements": copy.deepcopy(RELEASABLE_SAMPLE),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_normalises(self):
        limits = validate_acceptance_policy()
        self.assertAlmostEqual(limits["minimum_thickness_um"], 3.0, places=9)
        self.assertAlmostEqual(limits["maximum_thickness_um"], 12.0, places=9)

    def test_an_unknown_policy_key_is_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy({"minimum_uniformity_ratio": 0.8})

    def test_an_inverted_tolerance_band_is_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(
                {"minimum_thickness_um": 9.0, "maximum_thickness_um": 4.0}
            )

    def test_an_uncertainty_that_swallows_the_band_is_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy(
                {
                    "minimum_thickness_um": 6.0,
                    "maximum_thickness_um": 6.2,
                    "measurement_uncertainty_um": 0.5,
                }
            )

    def test_a_zero_sample_fraction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy({"sample_fraction": 0.0})

    def test_a_non_integer_sample_floor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance_policy({"sample_size_floor": 4.5})

    def test_the_declared_limits_are_returned_as_a_pair(self):
        low, high = acceptance_limits()
        self.assertAlmostEqual(low, 3.0, places=9)
        self.assertAlmostEqual(high, 12.0, places=9)


class GuardBandTests(unittest.TestCase):
    def test_the_conformance_zone_is_pulled_in_by_the_uncertainty(self):
        low, high = conformance_zone()
        self.assertAlmostEqual(low, 3.15, places=9)
        self.assertAlmostEqual(high, 11.85, places=9)

    def test_a_zero_uncertainty_leaves_the_zone_at_the_limits(self):
        low, high = conformance_zone({"measurement_uncertainty_um": 0.0})
        self.assertAlmostEqual(low, 3.0, places=9)
        self.assertAlmostEqual(high, 12.0, places=9)

    def test_a_reading_below_the_floor_is_named_so(self):
        self.assertEqual(reading_disposition(2.8), BELOW_MINIMUM)

    def test_a_reading_above_the_ceiling_is_named_so(self):
        self.assertEqual(reading_disposition(12.6), ABOVE_MAXIMUM)

    def test_a_reading_inside_the_lower_guard_band_is_unplaceable(self):
        self.assertEqual(reading_disposition(3.05), INDETERMINATE_LOW)

    def test_a_reading_inside_the_upper_guard_band_is_unplaceable(self):
        self.assertEqual(reading_disposition(11.95), INDETERMINATE_HIGH)

    def test_a_reading_on_the_guard_boundary_conforms(self):
        low, _ = conformance_zone()
        self.assertAlmostEqual(low, 3.15, places=9)
        self.assertEqual(reading_disposition(low), CONFORMING)

    def test_every_disposition_is_a_declared_one(self):
        for value in (2.0, 3.05, 7.5, 11.95, 13.0):
            self.assertIn(reading_disposition(value), DISPOSITIONS)

    def test_a_zero_thickness_reading_is_refused(self):
        with self.assertRaises(ValueError):
            reading_disposition(0.0)


class SampleSizeTests(unittest.TestCase):
    def test_a_small_lot_is_sampled_to_the_floor(self):
        self.assertEqual(required_sample_size(20), 5)

    def test_a_lot_smaller_than_the_floor_is_measured_whole(self):
        self.assertEqual(required_sample_size(3), 3)

    def test_a_round_fraction_does_not_buy_an_extra_cell(self):
        self.assertEqual(required_sample_size(100), 10)
        self.assertEqual(required_sample_size(1000), 100)

    def test_a_part_cell_rounds_up(self):
        self.assertEqual(required_sample_size(101), 11)

    def test_a_zero_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(0)

    def test_a_fractional_lot_size_is_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(12.5)

    def test_an_undersized_sample_is_reported(self):
        adequacy = sample_adequacy(200, RELEASABLE_SAMPLE)
        self.assertFalse(adequacy["adequate"])
        self.assertEqual(adequacy["required_sample_size"], 20)


class MeasurementValidationTests(unittest.TestCase):
    def test_bare_values_are_given_positional_identifiers(self):
        sample = normalise_measurements([7.4, 7.5, 7.6])
        self.assertEqual(len(sample), 3)
        self.assertEqual(sample[0][0], "cell-0")

    def test_mapping_form_measurements_are_accepted(self):
        sample = normalise_measurements(
            [{"cell_identifier": "c9", "thickness_um": 7.5}]
        )
        self.assertEqual(sample[0][0], "c9")
        self.assertAlmostEqual(sample[0][1], 7.5, places=9)

    def test_a_repeated_cell_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_measurements([("cell-01", 7.4), ("cell-01", 7.6)])

    def test_an_empty_sample_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_measurements([])

    def test_a_negative_thickness_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_measurements([("cell-01", -7.4)])


class StatisticsTests(unittest.TestCase):
    def test_the_sample_mean_and_spread_are_reported(self):
        statistics = lot_statistics(RELEASABLE_SAMPLE)
        self.assertEqual(statistics["sample_size"], 6)
        self.assertAlmostEqual(statistics["mean_um"], 7.5, places=9)
        self.assertAlmostEqual(statistics["range_um"], 0.4, places=9)

    def test_a_single_reading_has_no_spread(self):
        statistics = lot_statistics([("cell-01", 7.5)])
        self.assertAlmostEqual(statistics["sample_stdev_um"], 0.0, places=9)

    def test_a_capable_sample_clears_the_capability_floor(self):
        capability = capability_indices(RELEASABLE_SAMPLE)
        self.assertTrue(capability["resolved"])
        self.assertGreater(capability["capability_index"], 5.0)

    def test_a_wide_sample_fails_the_capability_floor(self):
        capability = capability_indices(WIDE_SPREAD_SAMPLE)
        self.assertTrue(capability["resolved"])
        self.assertLess(capability["capability_index"], 0.5)

    def test_an_unresolvable_spread_returns_no_capability_number(self):
        capability = capability_indices(FLAT_SAMPLE)
        self.assertFalse(capability["resolved"])
        self.assertIsNone(capability["capability_index"])

    def test_disposition_counts_cover_the_whole_sample(self):
        counts = disposition_counts(GUARD_BAND_SAMPLE)
        self.assertEqual(sum(counts.values()), len(GUARD_BAND_SAMPLE))
        self.assertEqual(counts[INDETERMINATE_LOW], 1)

    def test_nonconforming_cells_are_named(self):
        self.assertEqual(nonconforming_cells(THIN_CELL_SAMPLE), ("cell-03",))
        self.assertAlmostEqual(
            nonconforming_fraction(THIN_CELL_SAMPLE), 1.0 / 6.0, places=9
        )

    def test_unplaceable_cells_are_named_separately(self):
        self.assertEqual(indeterminate_cells(GUARD_BAND_SAMPLE), ("cell-03",))
        self.assertEqual(nonconforming_cells(GUARD_BAND_SAMPLE), ())


class LotReleaseTests(unittest.TestCase):
    def test_a_clean_sample_releases_the_lot(self):
        result = assess_lot_release(_case())
        self.assertEqual(result["verdict"], LOT_RELEASED)
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])

    def test_one_thin_cell_rejects_the_lot(self):
        result = assess_lot_release(_case(measurements=THIN_CELL_SAMPLE))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["nonconforming_cells"], ("cell-03",))

    def test_a_guard_band_reading_holds_the_lot_rather_than_passing_it(self):
        result = assess_lot_release(_case(measurements=GUARD_BAND_SAMPLE))
        self.assertEqual(result["verdict"], LOT_INDETERMINATE)
        self.assertFalse(result["released"])
        self.assertTrue(
            any("remeasure" in finding for finding in result["findings"])
        )

    def test_a_lot_inside_the_limits_can_still_fail_on_capability(self):
        result = assess_lot_release(_case(measurements=WIDE_SPREAD_SAMPLE))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["nonconforming_cells"], ())
        self.assertTrue(
            any("capability index" in finding for finding in result["findings"])
        )

    def test_an_unresolvable_spread_holds_the_lot(self):
        result = assess_lot_release(_case(measurements=FLAT_SAMPLE))
        self.assertEqual(result["verdict"], LOT_INDETERMINATE)

    def test_an_undersized_sample_outranks_a_bad_reading(self):
        result = assess_lot_release(
            _case(lot_size=400, measurements=THIN_CELL_SAMPLE)
        )
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)

    def test_every_contact_type_is_accepted(self):
        for contact in CONTACT_TYPES:
            result = assess_lot_release(_case(contact_type=contact))
            self.assertEqual(result["contact_type"], contact)

    def test_an_unknown_contact_type_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_release(_case(contact_type="edge-seal"))

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_release("lot-14")

    def test_a_case_without_a_lot_size_is_refused(self):
        case = _case()
        del case["lot_size"]
        with self.assertRaises(ValueError):
            assess_lot_release(case)

    def test_a_tighter_policy_travels_with_the_case(self):
        result = assess_lot_release(
            _case(policy={"minimum_thickness_um": 7.45})
        )
        self.assertEqual(result["verdict"], LOT_REJECTED)

    def test_the_reported_zone_matches_the_reported_limits(self):
        result = assess_lot_release(_case())
        low, high = result["acceptance_limits_um"]
        zone_low, zone_high = result["conformance_zone_um"]
        self.assertAlmostEqual(zone_low - low, 0.15, places=9)
        self.assertAlmostEqual(high - zone_high, 0.15, places=9)

    def test_the_default_policy_is_not_mutated_by_a_case_policy(self):
        assess_lot_release(_case(policy={"minimum_thickness_um": 4.0}))
        self.assertAlmostEqual(
            DEFAULT_ACCEPTANCE_POLICY["minimum_thickness_um"], 3.0, places=9
        )



class WorkflowOrderTests(unittest.TestCase):
    """The disposition runs as ranked steps and the sample gate is first.

    An undersized sample must stop the workflow before any reading is
    turned into a lot verdict, and a reading the gauge cannot place must
    hold the lot rather than being counted either way.
    """

    def test_the_sample_gate_stops_a_lot_whose_readings_also_fail(self):
        result = assess_lot_release(
            _case(lot_size=400, measurements=GUARD_BAND_SAMPLE)
        )
        self.assertEqual(result["verdict"], SAMPLE_INADEQUATE)
        self.assertEqual(result["sample_adequacy"]["required_sample_size"], 40)

    def test_a_rejection_outranks_an_unplaceable_reading(self):
        mixed = list(THIN_CELL_SAMPLE[:5]) + [("cell-06", 3.10)]
        result = assess_lot_release(_case(measurements=mixed))
        self.assertEqual(result["verdict"], LOT_REJECTED)
        self.assertEqual(result["nonconforming_cells"], ("cell-03",))
        self.assertEqual(result["indeterminate_cells"], ("cell-06",))

    def test_every_step_of_the_workflow_reports_its_own_section(self):
        result = assess_lot_release(_case())
        for section in (
            "sample_adequacy",
            "disposition_counts",
            "statistics",
            "capability",
            "verdict",
        ):
            self.assertIn(section, result)


if __name__ == "__main__":
    unittest.main()
