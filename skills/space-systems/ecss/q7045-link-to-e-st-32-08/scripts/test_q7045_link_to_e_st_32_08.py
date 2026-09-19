"""Contract tests for the allowables-support assessment of a metallic data set."""

import math
import unittest

from q7045_link_to_e_st_32_08_logic import (
    A_BASIS_FACTORS,
    B_BASIS_FACTORS,
    MIN_HEATS,
    MIN_SPECIMENS,
    MIN_SPECIMENS_PER_HEAT,
    POOLING_LIMIT_SIGMA,
    assess_allowables_support,
    basis_kinds,
    basis_value,
    heat_census,
    pooling_check,
    sample_statistics,
    supportable_basis,
    tolerance_factor,
    within_heat_pooled_sd,
)


def _records(per_heat_counts, base=900.0, step=4.0):
    records = []
    index = 0
    for heat_index, count in enumerate(per_heat_counts, start=1):
        for _ in range(count):
            records.append(
                {"heat": "h%d" % heat_index, "value": base + ((index * 3) % 5) * step}
            )
            index += 1
    return records


class StatisticsTests(unittest.TestCase):
    def test_mean_of_a_symmetric_set(self):
        stats = sample_statistics([90.0, 100.0, 110.0])
        self.assertAlmostEqual(stats["mean"], 100.0, places=9)

    def test_sample_standard_deviation_uses_n_minus_one(self):
        stats = sample_statistics([90.0, 100.0, 110.0])
        self.assertAlmostEqual(stats["standard_deviation"], 10.0, places=9)

    def test_identical_values_have_no_scatter(self):
        self.assertAlmostEqual(
            sample_statistics([100.0, 100.0, 100.0])["standard_deviation"], 0.0, places=12
        )

    def test_single_value_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([100.0])

    def test_non_positive_value_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([100.0, -1.0])

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            sample_statistics([100.0, "110"])


class ToleranceFactorTests(unittest.TestCase):
    def test_tabulated_point_is_returned_exactly(self):
        self.assertAlmostEqual(tolerance_factor("b", 30), 1.778, places=9)

    def test_interpolation_sits_between_the_neighbours(self):
        value = tolerance_factor("b", 35)
        self.assertAlmostEqual(value, (1.778 + 1.697) / 2.0, places=9)

    def test_a_basis_factor_exceeds_b_basis_at_the_same_size(self):
        self.assertGreater(tolerance_factor("a", 30), tolerance_factor("b", 30) + 0.5)

    def test_factor_falls_as_the_sample_grows(self):
        self.assertLess(tolerance_factor("b", 100), tolerance_factor("b", 20) - 0.1)

    def test_above_the_table_returns_the_last_point(self):
        self.assertAlmostEqual(
            tolerance_factor("a", 5000), A_BASIS_FACTORS[-1][1], places=9
        )

    def test_below_the_table_is_refused_rather_than_extrapolated(self):
        with self.assertRaises(ValueError):
            tolerance_factor("b", B_BASIS_FACTORS[0][0] - 1)

    def test_specification_basis_has_no_factor(self):
        with self.assertRaises(ValueError):
            tolerance_factor("s", 30)

    def test_non_integer_sample_size_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor("b", 30.5)

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_factor("c", 30)

    def test_basis_kinds_are_strongest_first(self):
        self.assertEqual(basis_kinds()[0], "a")


class CensusTests(unittest.TestCase):
    def test_census_counts_heats_and_specimens(self):
        census = heat_census(_records([5, 5, 5]))
        self.assertEqual(census["heat_count"], 3)
        self.assertEqual(census["specimen_count"], 15)

    def test_thinnest_heat_is_reported(self):
        census = heat_census(_records([6, 2, 7]))
        self.assertEqual(census["thinnest_heat_count"], 2)

    def test_heat_order_is_first_seen(self):
        self.assertEqual(heat_census(_records([1, 1]))["heats"], ["h1", "h2"])

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            heat_census([])

    def test_record_without_a_heat_rejected(self):
        with self.assertRaises(ValueError):
            heat_census([{"value": 900.0}])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            heat_census([900.0])


class PoolingTests(unittest.TestCase):
    def test_similar_heats_pool(self):
        self.assertTrue(pooling_check(heat_census(_records([5, 5, 5])))["poolable"])

    def test_an_offset_heat_breaks_pooling(self):
        records = _records([5, 5]) + [
            {"heat": "h3", "value": 1400.0},
            {"heat": "h3", "value": 1405.0},
        ]
        result = pooling_check(heat_census(records))
        self.assertFalse(result["poolable"])
        self.assertEqual(result["worst_heat"], "h3")

    def test_identical_heats_pool_trivially(self):
        records = []
        for heat_index in range(1, 4):
            for _ in range(3):
                records.append({"heat": "h%d" % heat_index, "value": 900.0})
        self.assertTrue(pooling_check(heat_census(records))["poolable"])

    def test_single_specimen_heats_cannot_be_pooled(self):
        records = [{"heat": "h%d" % i, "value": 900.0 + i} for i in range(1, 4)]
        result = pooling_check(heat_census(records))
        self.assertFalse(result["poolable"])
        self.assertIsNotNone(result["reason"])

    def test_tight_heats_with_different_means_do_not_pool(self):
        records = []
        for heat_index, level in enumerate((900.0, 900.0, 1200.0), start=1):
            for _ in range(3):
                records.append({"heat": "h%d" % heat_index, "value": level})
        self.assertFalse(pooling_check(heat_census(records))["poolable"])

    def test_within_heat_scatter_ignores_the_heat_offsets(self):
        tight = []
        offset = []
        for heat_index, level in enumerate((900.0, 901.0), start=1):
            for delta in (-1.0, 0.0, 1.0):
                tight.append({"heat": "h%d" % heat_index, "value": 900.0 + delta})
                offset.append({"heat": "h%d" % heat_index, "value": level * 1.0 + delta
                               + (0.0 if heat_index == 1 else 400.0)})
        self.assertAlmostEqual(
            within_heat_pooled_sd(heat_census(tight)),
            within_heat_pooled_sd(heat_census(offset)),
            places=9,
        )

    def test_within_heat_scatter_is_none_without_replicates(self):
        records = [{"heat": "h%d" % i, "value": 900.0 + i} for i in range(1, 4)]
        self.assertIsNone(within_heat_pooled_sd(heat_census(records)))

    def test_pooling_limit_is_reported_back(self):
        result = pooling_check(heat_census(_records([5, 5, 5])))
        self.assertAlmostEqual(result["limit_sigma"], POOLING_LIMIT_SIGMA, places=9)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            pooling_check(heat_census(_records([5, 5])), limit_sigma=0.0)

    def test_non_census_argument_rejected(self):
        with self.assertRaises(ValueError):
            pooling_check({"values": [1.0, 2.0]})


class BasisValueTests(unittest.TestCase):
    def test_value_is_mean_less_factor_times_scatter(self):
        values = [900.0 + i for i in range(20)]
        stats = sample_statistics(values)
        result = basis_value(values, "b")
        self.assertAlmostEqual(
            result["value"],
            stats["mean"] - result["factor"] * stats["standard_deviation"],
            places=9,
        )

    def test_a_basis_is_more_conservative_than_b_basis(self):
        values = [900.0 + i for i in range(20)]
        self.assertLess(
            basis_value(values, "a")["value"], basis_value(values, "b")["value"] - 1.0
        )

    def test_no_scatter_puts_the_value_on_the_mean(self):
        values = [900.0] * 20
        self.assertAlmostEqual(basis_value(values, "b")["value"], 900.0, places=9)

    def test_specification_basis_has_no_computed_value(self):
        with self.assertRaises(ValueError):
            basis_value([900.0] * 20, "s")

    def test_too_small_a_sample_is_refused(self):
        with self.assertRaises(ValueError):
            basis_value([900.0, 905.0, 910.0], "b")


class SupportableBasisTests(unittest.TestCase):
    def test_full_set_supports_the_requested_a_basis(self):
        census = heat_census(_records([5, 5, 5]))
        self.assertEqual(supportable_basis(census, "a"), "a")

    def test_two_heats_downgrade_an_a_request_to_specification(self):
        census = heat_census(_records([8, 8]))
        self.assertEqual(supportable_basis(census, "a"), "s")

    def test_a_thin_set_downgrades_to_b(self):
        census = heat_census(_records([4, 4, 4]))
        self.assertEqual(supportable_basis(census, "a"), "b")

    def test_a_request_never_upgrades(self):
        census = heat_census(_records([10, 10, 10]))
        self.assertEqual(supportable_basis(census, "b"), "b")

    def test_a_single_heat_supports_only_specification(self):
        census = heat_census(_records([20]))
        self.assertEqual(supportable_basis(census, "b"), "s")


class AssessmentTests(unittest.TestCase):
    def test_full_set_supports_the_request_with_no_findings(self):
        result = assess_allowables_support(
            {"records": _records([5, 5, 5]), "requested_basis": "a"}
        )
        self.assertTrue(result["supports_request"])
        self.assertEqual(result["findings"], [])

    def test_specimen_shortfall_is_named(self):
        result = assess_allowables_support(
            {"records": _records([4, 4, 4]), "requested_basis": "a"}
        )
        self.assertFalse(result["supports_request"])
        self.assertTrue(any("specimens" in f for f in result["findings"]))

    def test_heat_shortfall_downgrades_to_specification(self):
        result = assess_allowables_support(
            {"records": _records([8, 8]), "requested_basis": "a"}
        )
        self.assertEqual(result["granted_basis"], "s")
        self.assertTrue(result["downgraded"])

    def test_thin_heat_is_named_separately(self):
        result = assess_allowables_support(
            {"records": _records([7, 7, 1]), "requested_basis": "a"}
        )
        self.assertTrue(any("thinnest heat" in f for f in result["findings"]))

    def test_unpoolable_heats_force_specification_basis(self):
        records = _records([5, 5]) + [
            {"heat": "h3", "value": 1400.0},
            {"heat": "h3", "value": 1405.0},
            {"heat": "h3", "value": 1410.0},
            {"heat": "h3", "value": 1415.0},
            {"heat": "h3", "value": 1420.0},
        ]
        result = assess_allowables_support({"records": records, "requested_basis": "a"})
        self.assertEqual(result["granted_basis"], "s")
        self.assertTrue(any("one population" in f for f in result["findings"]))

    def test_specification_minimum_is_carried_through_when_granted(self):
        result = assess_allowables_support(
            {
                "records": _records([8, 8]),
                "requested_basis": "a",
                "specification_minimum": 830.0,
            }
        )
        self.assertAlmostEqual(result["allowable"]["value"], 830.0, places=9)

    def test_granted_value_uses_the_granted_basis_factor(self):
        result = assess_allowables_support(
            {"records": _records([4, 4, 4]), "requested_basis": "a"}
        )
        self.assertEqual(result["granted_basis"], "b")
        self.assertAlmostEqual(
            result["allowable"]["factor"], tolerance_factor("b", 12), places=9
        )

    def test_minima_tables_cover_every_basis(self):
        for basis in basis_kinds():
            self.assertIn(basis, MIN_SPECIMENS)
            self.assertIn(basis, MIN_HEATS)
            self.assertIn(basis, MIN_SPECIMENS_PER_HEAT)

    def test_allowable_sits_below_the_mean_when_there_is_scatter(self):
        result = assess_allowables_support(
            {"records": _records([5, 5, 5]), "requested_basis": "a"}
        )
        self.assertLess(
            result["allowable"]["value"], result["allowable"]["mean"] - 1.0
        )

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_allowables_support({"records": _records([5, 5, 5])})

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            assess_allowables_support(["records"])

    def test_unknown_requested_basis_rejected(self):
        with self.assertRaises(ValueError):
            assess_allowables_support(
                {"records": _records([5, 5, 5]), "requested_basis": "gold"}
            )


if __name__ == "__main__":
    unittest.main()
