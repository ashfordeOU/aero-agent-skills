"""Contract tests for the clause 6.4.3.17.2 cell assembly flatness run logic."""

import unittest

from e2008_sca_flatness_test_process_logic import (
    EDGES,
    RUN_COVERAGE_SHORT,
    RUN_UNDERSIZED,
    RUN_VALID,
    edge_band_coverage,
    guard_band,
    maximum_deflection,
    measure_sample,
    pattern_coverage,
    run_flatness_measurement,
    seated_deflections,
    validate_footprint,
    validate_policy,
    validate_readings,
    validate_reference_flat,
)

FOOTPRINT = {"length_mm": 80.0, "width_mm": 40.0}
REFERENCE = {"flat_residual_um": 2.0, "probe_uncertainty_um": 1.5}

# A nine point pattern that reaches every cell of the default 3x3 grid and
# every edge band. The assembly seats at the centre and bows to the corners.
FULL_PATTERN = [
    {"x_mm": 4.0, "y_mm": 2.0, "standoff_um": 60.0},
    {"x_mm": 40.0, "y_mm": 2.0, "standoff_um": 30.0},
    {"x_mm": 76.0, "y_mm": 2.0, "standoff_um": 62.0},
    {"x_mm": 4.0, "y_mm": 20.0, "standoff_um": 32.0},
    {"x_mm": 40.0, "y_mm": 20.0, "standoff_um": 10.0},
    {"x_mm": 76.0, "y_mm": 20.0, "standoff_um": 34.0},
    {"x_mm": 4.0, "y_mm": 38.0, "standoff_um": 64.0},
    {"x_mm": 40.0, "y_mm": 38.0, "standoff_um": 31.0},
    {"x_mm": 76.0, "y_mm": 38.0, "standoff_um": 70.0},
]

# Corners plus centre: the edge bands are reached but five of nine cells are
# never read, so the pattern cannot speak for the whole footprint.
SPARSE_PATTERN = [
    {"x_mm": 4.0, "y_mm": 2.0, "standoff_um": 60.0},
    {"x_mm": 76.0, "y_mm": 2.0, "standoff_um": 62.0},
    {"x_mm": 40.0, "y_mm": 20.0, "standoff_um": 10.0},
    {"x_mm": 4.0, "y_mm": 38.0, "standoff_um": 64.0},
    {"x_mm": 76.0, "y_mm": 38.0, "standoff_um": 70.0},
]

# A pattern that never leaves the interior: every cell is reached but the
# corners that carry the bow are not.
INBOARD_PATTERN = [
    {"x_mm": 20.0, "y_mm": 10.0, "standoff_um": 20.0},
    {"x_mm": 40.0, "y_mm": 10.0, "standoff_um": 14.0},
    {"x_mm": 60.0, "y_mm": 10.0, "standoff_um": 21.0},
    {"x_mm": 20.0, "y_mm": 20.0, "standoff_um": 15.0},
    {"x_mm": 40.0, "y_mm": 20.0, "standoff_um": 10.0},
    {"x_mm": 60.0, "y_mm": 20.0, "standoff_um": 16.0},
    {"x_mm": 20.0, "y_mm": 30.0, "standoff_um": 22.0},
    {"x_mm": 40.0, "y_mm": 30.0, "standoff_um": 15.0},
    {"x_mm": 60.0, "y_mm": 30.0, "standoff_um": 24.0},
]


def _sample(sample_id, pattern=None):
    return {
        "sample_id": sample_id,
        "readings": [dict(r) for r in (pattern or FULL_PATTERN)],
    }


def _spec(**overrides):
    spec = {
        "footprint": dict(FOOTPRINT),
        "reference_flat": dict(REFERENCE),
        "samples": [_sample("sca-01"), _sample("sca-02"), _sample("sca-03"), _sample("sca-04")],
    }
    spec.update(overrides)
    return spec


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_returned(self):
        policy = validate_policy()
        self.assertEqual(policy["grid_divisions"], 3)
        self.assertEqual(policy["min_subgroup_samples"], 4)

    def test_unrecognised_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"grid_divisons": 4})

    def test_non_integer_grid_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"grid_divisions": 2.5})

    def test_reading_floor_below_three_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_readings": 2})

    def test_edge_band_above_half_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"edge_band_fraction": 0.6})

    def test_coverage_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"min_cell_coverage_fraction": 1.4})

    def test_non_boolean_edge_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy({"require_every_edge_band": "yes"})


class FootprintAndReferenceTests(unittest.TestCase):
    def test_footprint_is_normalized(self):
        footprint = validate_footprint(FOOTPRINT)
        self.assertAlmostEqual(footprint["length_mm"], 80.0, places=9)

    def test_zero_length_footprint_rejected(self):
        with self.assertRaises(ValueError):
            validate_footprint({"length_mm": 0.0, "width_mm": 40.0})

    def test_missing_footprint_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_footprint({"length_mm": 80.0})

    def test_negative_flat_residual_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_flat({"flat_residual_um": -1.0, "probe_uncertainty_um": 1.0})

    def test_missing_probe_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_flat({"flat_residual_um": 1.0})

    def test_perfect_reference_has_no_guard_band(self):
        band = guard_band({"flat_residual_um": 0.0, "probe_uncertainty_um": 0.0})
        self.assertAlmostEqual(band, 0.0, places=9)

    def test_guard_band_combines_in_quadrature(self):
        self.assertAlmostEqual(guard_band(REFERENCE), 2.5, places=9)


class ReadingValidationTests(unittest.TestCase):
    def test_readings_are_normalized(self):
        points = validate_readings(FULL_PATTERN, FOOTPRINT)
        self.assertEqual(len(points), 9)
        self.assertAlmostEqual(points[0][2], 60.0, places=9)

    def test_reading_off_the_footprint_in_length_rejected(self):
        bad = [dict(r) for r in FULL_PATTERN]
        bad[0]["x_mm"] = 81.0
        with self.assertRaises(ValueError):
            validate_readings(bad, FOOTPRINT)

    def test_reading_off_the_footprint_in_width_rejected(self):
        bad = [dict(r) for r in FULL_PATTERN]
        bad[0]["y_mm"] = -0.5
        with self.assertRaises(ValueError):
            validate_readings(bad, FOOTPRINT)

    def test_repeated_probe_point_rejected(self):
        bad = [dict(r) for r in FULL_PATTERN] + [dict(FULL_PATTERN[0])]
        with self.assertRaises(ValueError):
            validate_readings(bad, FOOTPRINT)

    def test_negative_standoff_rejected(self):
        bad = [dict(r) for r in FULL_PATTERN]
        bad[0]["standoff_um"] = -3.0
        with self.assertRaises(ValueError):
            validate_readings(bad, FOOTPRINT)

    def test_too_few_readings_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings(FULL_PATTERN[:3], FOOTPRINT)

    def test_missing_reading_key_rejected(self):
        bad = [dict(r) for r in FULL_PATTERN]
        del bad[0]["standoff_um"]
        with self.assertRaises(ValueError):
            validate_readings(bad, FOOTPRINT)


class SeatingPlaneTests(unittest.TestCase):
    def test_seating_plane_puts_the_lowest_point_at_zero(self):
        seated = seated_deflections(FULL_PATTERN, FOOTPRINT)
        self.assertAlmostEqual(min(p["deflection_um"] for p in seated), 0.0, places=9)

    def test_deflection_is_the_span_of_the_readings(self):
        worst = maximum_deflection(FULL_PATTERN, FOOTPRINT)
        self.assertAlmostEqual(worst["max_deflection_um"], 60.0, places=9)

    def test_worst_point_is_reported(self):
        worst = maximum_deflection(FULL_PATTERN, FOOTPRINT)
        self.assertAlmostEqual(worst["x_mm"], 76.0, places=9)
        self.assertAlmostEqual(worst["y_mm"], 38.0, places=9)

    def test_probe_zero_offset_does_not_change_the_deflection(self):
        shifted = [dict(r, standoff_um=r["standoff_um"] + 500.0) for r in FULL_PATTERN]
        worst = maximum_deflection(shifted, FOOTPRINT)
        self.assertAlmostEqual(worst["max_deflection_um"], 60.0, places=9)

    def test_a_perfectly_flat_assembly_reads_zero(self):
        flat = [dict(r, standoff_um=25.0) for r in FULL_PATTERN]
        worst = maximum_deflection(flat, FOOTPRINT)
        self.assertAlmostEqual(worst["max_deflection_um"], 0.0, places=9)


class PatternCoverageTests(unittest.TestCase):
    def test_full_pattern_reaches_every_cell(self):
        cover = pattern_coverage(FULL_PATTERN, FOOTPRINT)
        self.assertEqual(cover["cells_read"], 9)
        self.assertAlmostEqual(cover["coverage_fraction"], 1.0, places=9)

    def test_sparse_pattern_leaves_cells_unread(self):
        cover = pattern_coverage(SPARSE_PATTERN, FOOTPRINT)
        self.assertEqual(cover["cells_read"], 5)
        self.assertEqual(len(cover["unread_cells"]), 4)

    def test_a_point_on_the_far_corner_stays_inside_the_grid(self):
        pattern = [dict(r) for r in FULL_PATTERN]
        pattern[-1] = {"x_mm": 80.0, "y_mm": 40.0, "standoff_um": 70.0}
        cover = pattern_coverage(pattern, FOOTPRINT)
        self.assertEqual(cover["cells_read"], 9)

    def test_full_pattern_reaches_every_edge_band(self):
        edges = edge_band_coverage(FULL_PATTERN, FOOTPRINT)
        self.assertEqual(edges["unread_edges"], [])
        self.assertEqual(sorted(edges["edges_read"]), sorted(EDGES))

    def test_inboard_pattern_reaches_no_edge_band(self):
        edges = edge_band_coverage(INBOARD_PATTERN, FOOTPRINT)
        self.assertEqual(sorted(edges["unread_edges"]), sorted(EDGES))


class SampleMeasurementTests(unittest.TestCase):
    def test_nominal_sample_is_measured_and_covered(self):
        result = measure_sample(_sample("sca-01"), FOOTPRINT, REFERENCE)
        self.assertTrue(result["coverage_sufficient"])
        self.assertAlmostEqual(result["max_deflection_um"], 60.0, places=9)

    def test_guard_banded_deflection_carries_the_uncertainty(self):
        result = measure_sample(_sample("sca-01"), FOOTPRINT, REFERENCE)
        self.assertAlmostEqual(result["guard_banded_deflection_um"], 62.5, places=9)

    def test_sparse_pattern_is_a_coverage_finding(self):
        result = measure_sample(_sample("sca-01", SPARSE_PATTERN), FOOTPRINT, REFERENCE)
        self.assertFalse(result["coverage_sufficient"])
        self.assertEqual(len(result["findings"]), 1)

    def test_inboard_pattern_is_an_edge_band_finding(self):
        result = measure_sample(_sample("sca-01", INBOARD_PATTERN), FOOTPRINT, REFERENCE)
        self.assertEqual(
            len([f for f in result["findings"] if "edge" in f or "bow" in f]), 1
        )

    def test_edge_requirement_can_be_stood_down_by_policy(self):
        result = measure_sample(
            _sample("sca-01", INBOARD_PATTERN),
            FOOTPRINT,
            REFERENCE,
            {"require_every_edge_band": False},
        )
        self.assertTrue(result["coverage_sufficient"])

    def test_blank_sample_identifier_rejected(self):
        with self.assertRaises(ValueError):
            measure_sample({"sample_id": "  ", "readings": FULL_PATTERN}, FOOTPRINT, REFERENCE)

    def test_missing_sample_key_rejected(self):
        with self.assertRaises(ValueError):
            measure_sample({"sample_id": "sca-01"}, FOOTPRINT, REFERENCE)


class SubgroupRunTests(unittest.TestCase):
    def test_nominal_run_is_valid(self):
        result = run_flatness_measurement(_spec())
        self.assertEqual(result["verdict"], RUN_VALID)
        self.assertEqual(result["findings"], [])

    def test_undersized_subgroup_is_its_own_verdict(self):
        result = run_flatness_measurement(_spec(samples=[_sample("sca-01"), _sample("sca-02")]))
        self.assertEqual(result["verdict"], RUN_UNDERSIZED)
        self.assertEqual(result["sample_count"], 2)

    def test_coverage_short_sample_sentences_the_run(self):
        samples = [_sample("sca-01"), _sample("sca-02"), _sample("sca-03"),
                   _sample("sca-04", SPARSE_PATTERN)]
        result = run_flatness_measurement(_spec(samples=samples))
        self.assertEqual(result["verdict"], RUN_COVERAGE_SHORT)
        self.assertEqual(len(result["findings"]), 1)

    def test_undersized_outranks_coverage(self):
        result = run_flatness_measurement(_spec(samples=[_sample("sca-01", SPARSE_PATTERN)]))
        self.assertEqual(result["verdict"], RUN_UNDERSIZED)

    def test_worst_sample_is_reported(self):
        bowed = [dict(r) for r in FULL_PATTERN]
        bowed[-1]["standoff_um"] = 130.0
        samples = [_sample("sca-01"), _sample("sca-02"), _sample("sca-03"),
                   _sample("sca-04", bowed)]
        result = run_flatness_measurement(_spec(samples=samples))
        self.assertEqual(result["worst_sample_id"], "sca-04")
        self.assertAlmostEqual(result["worst_max_deflection_um"], 120.0, places=9)

    def test_repeated_sample_identifier_rejected(self):
        with self.assertRaises(ValueError):
            run_flatness_measurement(
                _spec(samples=[_sample("sca-01"), _sample("sca-01")])
            )

    def test_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            run_flatness_measurement(_spec(samples=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["reference_flat"]
        with self.assertRaises(ValueError):
            run_flatness_measurement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            run_flatness_measurement(["footprint"])

    def test_guard_band_is_echoed_for_the_run(self):
        result = run_flatness_measurement(_spec())
        self.assertAlmostEqual(result["guard_band_um"], 2.5, places=9)
        self.assertAlmostEqual(result["worst_guard_banded_deflection_um"], 62.5, places=9)


if __name__ == "__main__":
    unittest.main()
