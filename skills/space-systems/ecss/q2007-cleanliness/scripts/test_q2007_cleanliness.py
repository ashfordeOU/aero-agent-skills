"""Contract test for the q2007-cleanliness leaf (stdlib unittest).

The airborne limits are checked against the independently published class
table (class 5 at 0.5 um = 3520 particles per cubic metre, class 8 at
5.0 um = 29300, and so on), not against a second copy of the formula, so
the oracle cannot fail in the same direction as the code under test. The
formula is a power expression and is not exactly representable, so those
comparisons are made on the ratio with a stated relative tolerance.
"""

import unittest

from q2007_cleanliness_logic import (
    COUNT_RELATIVE_TOLERANCE,
    FINDING_COUNT_ABOVE_LIMIT,
    FINDING_INTERVAL_TOO_LONG,
    FINDING_NO_LEVEL,
    FINDING_NO_MONITORING,
    FINDING_SURFACE_ABOVE_LIMIT,
    FINDING_SURFACE_LEVEL_TOO_COARSE,
    MAX_ISO_CLASS,
    VALID_SURFACE_LEVELS,
    assess_activity,
    assess_test_centre_cleanliness,
    count_conforms,
    iso_class_limit,
    margin_ratio,
    surface_level_meets,
    surface_obscuration_limit_pct,
    tightest_class,
    validate_activity,
)

# Published airborne class table entries, used as the independent oracle.
TABLE = {
    (5, 0.5): 3520.0,
    (5, 0.1): 100000.0,
    (6, 1.0): 8320.0,
    (7, 0.5): 352000.0,
    (8, 5.0): 29300.0,
}
TABLE_RELATIVE_TOLERANCE = 3.0e-3


def cell(activity_id="A-1", **kw):
    record = {
        "id": activity_id,
        "required_iso_class": 8,
        "particle_size_um": 0.5,
        "counts_per_m3": [1.0e6, 1.2e6],
        "monitoring_interval_h": 12.0,
        "required_interval_h": 24.0,
    }
    record.update(kw)
    return record


def bench(activity_id="B-1", **kw):
    record = {
        "id": activity_id,
        "required_surface_level": 300,
        "certified_surface_level": 300,
        "measured_obscuration_pct": 0.10,
    }
    record.update(kw)
    return record


class TestAirborneLimit(unittest.TestCase):
    def test_formula_reproduces_the_published_table(self):
        for (iso_class, size), tabulated in TABLE.items():
            computed = iso_class_limit(iso_class, size)
            self.assertAlmostEqual(
                computed / tabulated, 1.0, delta=TABLE_RELATIVE_TOLERANCE
            )

    def test_reference_size_gives_the_decade_exactly(self):
        self.assertAlmostEqual(iso_class_limit(5, 0.1) / 1.0e5, 1.0, places=9)

    def test_a_cleaner_class_admits_fewer_particles(self):
        cleaner = iso_class_limit(5, 0.5)
        dirtier = iso_class_limit(6, 0.5)
        self.assertAlmostEqual(dirtier / cleaner, 10.0, places=6)

    def test_a_larger_particle_size_lowers_the_limit(self):
        self.assertLess(iso_class_limit(7, 5.0), iso_class_limit(7, 0.5))

    def test_class_below_the_range_raises(self):
        with self.assertRaises(ValueError):
            iso_class_limit(0, 0.5)

    def test_class_above_the_range_raises(self):
        with self.assertRaises(ValueError):
            iso_class_limit(MAX_ISO_CLASS + 1, 0.5)

    def test_non_integer_class_raises(self):
        with self.assertRaises(ValueError):
            iso_class_limit(5.5, 0.5)

    def test_particle_size_outside_the_covered_range_raises(self):
        with self.assertRaises(ValueError):
            iso_class_limit(5, 10.0)

    def test_non_numeric_particle_size_raises(self):
        with self.assertRaises(ValueError):
            iso_class_limit(5, "half a micron")


class TestCountComparison(unittest.TestCase):
    def test_count_below_the_limit_conforms(self):
        self.assertTrue(count_conforms(1000.0, 3520.0))

    def test_count_exactly_on_a_computed_limit_conforms(self):
        limit = iso_class_limit(5, 0.5)
        self.assertTrue(count_conforms(limit, limit))

    def test_count_above_the_limit_does_not_conform(self):
        self.assertFalse(count_conforms(4000.0, 3520.0))

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            count_conforms(-1.0, 3520.0)

    def test_margin_ratio_above_one_means_room_left(self):
        self.assertAlmostEqual(margin_ratio(1000.0, 3520.0), 3.52, places=9)

    def test_margin_ratio_below_one_means_exceedance(self):
        self.assertAlmostEqual(margin_ratio(7040.0, 3520.0), 0.5, places=9)

    def test_zero_count_has_no_margin_ratio(self):
        with self.assertRaises(ValueError):
            margin_ratio(0.0, 3520.0)


class TestSurfaceLevels(unittest.TestCase):
    def test_level_300_obscuration_limit(self):
        self.assertAlmostEqual(surface_obscuration_limit_pct(300), 0.162, places=9)

    def test_levels_are_ordered_cleaner_to_dirtier(self):
        limits = [surface_obscuration_limit_pct(v) for v in VALID_SURFACE_LEVELS]
        self.assertEqual(limits, sorted(limits))

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            surface_obscuration_limit_pct(250)

    def test_non_integer_level_raises(self):
        with self.assertRaises(ValueError):
            surface_obscuration_limit_pct("300")

    def test_a_cleaner_certificate_meets_a_coarser_requirement(self):
        self.assertTrue(surface_level_meets(500, 300))

    def test_an_equal_certificate_meets_the_requirement(self):
        self.assertTrue(surface_level_meets(300, 300))

    def test_a_coarser_certificate_does_not_meet_the_requirement(self):
        self.assertFalse(surface_level_meets(300, 500))


class TestValidation(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_activity({"id": "A-9"})
        self.assertIsNone(norm["required_iso_class"])
        self.assertEqual(norm["counts_per_m3"], [])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(["A-1"])

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(cell(""))

    def test_string_counts_raise(self):
        with self.assertRaises(ValueError):
            validate_activity(cell(counts_per_m3="1e6"))

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(cell(counts_per_m3=[-5.0]))

    def test_non_positive_monitoring_interval_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(cell(monitoring_interval_h=0.0))

    def test_unknown_required_surface_level_raises(self):
        with self.assertRaises(ValueError):
            validate_activity(bench(required_surface_level=275))


class TestAssessActivity(unittest.TestCase):
    def test_a_conforming_cell_carries_no_finding(self):
        result = assess_activity(cell())
        self.assertTrue(result["conforming"])
        self.assertEqual(result["findings"], [])

    def test_margin_ratio_is_reported_against_the_worst_count(self):
        result = assess_activity(cell(counts_per_m3=[1.0e6, 2.0e6]))
        expected = result["airborne_limit_per_m3"] / 2.0e6
        self.assertAlmostEqual(result["margin_ratio"] / expected, 1.0, places=9)

    def test_count_above_the_class_limit_is_flagged(self):
        result = assess_activity(cell(counts_per_m3=[9.9e6]))
        self.assertIn(FINDING_COUNT_ABOVE_LIMIT, result["findings"])

    def test_activity_declaring_no_level_is_flagged(self):
        result = assess_activity({"id": "A-2"})
        self.assertIn(FINDING_NO_LEVEL, result["findings"])

    def test_unmonitored_cell_is_flagged(self):
        result = assess_activity(cell(counts_per_m3=[]))
        self.assertIn(FINDING_NO_MONITORING, result["findings"])

    def test_slow_sampling_is_flagged_even_with_clean_counts(self):
        result = assess_activity(cell(monitoring_interval_h=48.0))
        self.assertIn(FINDING_INTERVAL_TOO_LONG, result["findings"])
        self.assertNotIn(FINDING_COUNT_ABOVE_LIMIT, result["findings"])

    def test_sampling_exactly_at_the_required_interval_passes(self):
        result = assess_activity(cell(monitoring_interval_h=24.0))
        self.assertNotIn(FINDING_INTERVAL_TOO_LONG, result["findings"])

    def test_coarse_surface_certificate_is_flagged(self):
        result = assess_activity(bench(certified_surface_level=500))
        self.assertIn(FINDING_SURFACE_LEVEL_TOO_COARSE, result["findings"])

    def test_surface_obscuration_above_the_level_limit_is_flagged(self):
        result = assess_activity(bench(measured_obscuration_pct=0.5))
        self.assertIn(FINDING_SURFACE_ABOVE_LIMIT, result["findings"])

    def test_surface_obscuration_exactly_on_the_limit_conforms(self):
        limit = surface_obscuration_limit_pct(300)
        result = assess_activity(bench(measured_obscuration_pct=limit))
        self.assertNotIn(FINDING_SURFACE_ABOVE_LIMIT, result["findings"])


class TestRollUp(unittest.TestCase):
    def test_tightest_class_is_the_lowest_number(self):
        self.assertEqual(tightest_class([cell("A-1"), cell("A-2",
                                                           required_iso_class=5)]), 5)

    def test_tightest_class_without_any_airborne_activity_raises(self):
        with self.assertRaises(ValueError):
            tightest_class([bench()])

    def test_clean_centre_is_conforming(self):
        report = assess_test_centre_cleanliness([cell(), bench()])
        self.assertTrue(report["conforming"])
        self.assertEqual(report["tightest_iso_class"], 8)

    def test_one_exceedance_makes_the_centre_non_conforming(self):
        report = assess_test_centre_cleanliness(
            [cell(), cell("A-2", counts_per_m3=[9.9e6])]
        )
        self.assertFalse(report["conforming"])
        self.assertEqual(report["non_conforming_ids"], ["A-2"])

    def test_monitoring_gaps_are_listed_separately(self):
        report = assess_test_centre_cleanliness(
            [cell(), cell("A-2", monitoring_interval_h=48.0)]
        )
        self.assertEqual(report["monitoring_gap_ids"], ["A-2"])

    def test_duplicate_activity_id_raises(self):
        with self.assertRaises(ValueError):
            assess_test_centre_cleanliness([cell("A-1"), cell("A-1")])

    def test_empty_centre_raises(self):
        with self.assertRaises(ValueError):
            assess_test_centre_cleanliness([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_test_centre_cleanliness(cell())

    def test_tolerance_is_far_below_counter_resolution(self):
        self.assertLess(COUNT_RELATIVE_TOLERANCE, 1.0e-6)


if __name__ == "__main__":
    unittest.main()
