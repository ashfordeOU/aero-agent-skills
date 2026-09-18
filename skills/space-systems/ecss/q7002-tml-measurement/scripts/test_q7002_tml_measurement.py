"""Contract tests for the outgassing total-mass-loss measurement logic.

The cases follow the three weighings: the mass a coupon went in with, the mass
it came out with, and the mass it took back on in the laboratory air. From
those come total mass loss, water vapour regained, recovered mass loss, the
smallest loss the balance could have seen, and the agreement of the replicate
set with itself.
"""

import unittest

from q7002_tml_measurement_logic import (
    DEFAULT_RML_LIMIT_PCT,
    DEFAULT_SCATTER_ALLOWANCE_PCT,
    DEFAULT_TML_LIMIT_PCT,
    assess_tml_measurement,
    recovered_mass_loss_percent,
    resolution_floor_percent,
    set_statistics,
    specimen_record,
    total_mass_loss_percent,
    validate_mass,
    water_vapour_regained_percent,
    within_limit,
)


def _specimen(identifier="S1", initial=200.0, final=199.6, **overrides):
    item = {"id": identifier, "initial_mg": initial, "final_mg": final}
    item.update(overrides)
    return item


class ValidateMassTests(unittest.TestCase):
    def test_mass_passes_through(self):
        self.assertAlmostEqual(validate_mass(200, "m"), 200.0)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_mass(0.0, "m")

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_mass(-200.0, "m")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_mass(True, "m")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_mass(float("inf"), "m")


class TotalMassLossTests(unittest.TestCase):
    def test_one_percent_of_the_initial_mass(self):
        self.assertAlmostEqual(total_mass_loss_percent(200.0, 198.0), 1.0, places=12)

    def test_no_loss_is_zero_percent(self):
        self.assertAlmostEqual(total_mass_loss_percent(200.0, 200.0), 0.0, places=12)

    def test_the_result_is_a_ratio_not_an_absolute_loss(self):
        light = total_mass_loss_percent(100.0, 99.0)
        heavy = total_mass_loss_percent(300.0, 299.0)
        self.assertAlmostEqual(light, 1.0, places=12)
        self.assertGreater(light, heavy)

    def test_mass_gain_rejected(self):
        with self.assertRaises(ValueError):
            total_mass_loss_percent(200.0, 200.5)

    def test_zero_initial_mass_rejected(self):
        with self.assertRaises(ValueError):
            total_mass_loss_percent(0.0, 0.0)


class WaterVapourTests(unittest.TestCase):
    def test_regain_is_on_the_initial_mass_basis(self):
        self.assertAlmostEqual(
            water_vapour_regained_percent(200.0, 198.0, 199.0), 0.5, places=12
        )

    def test_no_regain_is_zero(self):
        self.assertAlmostEqual(
            water_vapour_regained_percent(200.0, 198.0, 198.0), 0.0, places=12
        )

    def test_regain_below_the_final_mass_rejected(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_percent(200.0, 198.0, 197.0)

    def test_regain_above_the_initial_mass_rejected(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_percent(200.0, 198.0, 201.0)

    def test_final_above_initial_rejected(self):
        with self.assertRaises(ValueError):
            water_vapour_regained_percent(200.0, 201.0, 201.0)


class RecoveredMassLossTests(unittest.TestCase):
    def test_recovered_is_total_less_regained(self):
        self.assertAlmostEqual(recovered_mass_loss_percent(1.0, 0.5), 0.5, places=12)

    def test_all_of_the_loss_coming_back_leaves_nothing(self):
        self.assertAlmostEqual(recovered_mass_loss_percent(0.8, 0.8), 0.0, places=12)

    def test_regain_beyond_the_loss_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_percent(0.5, 0.9)

    def test_negative_total_rejected(self):
        with self.assertRaises(ValueError):
            recovered_mass_loss_percent(-0.5, 0.1)


class ResolutionTests(unittest.TestCase):
    def test_floor_is_the_division_over_the_initial_mass(self):
        self.assertAlmostEqual(resolution_floor_percent(0.002, 200.0), 0.001, places=12)

    def test_a_heavier_coupon_resolves_a_smaller_percentage(self):
        self.assertLess(
            resolution_floor_percent(0.002, 300.0), resolution_floor_percent(0.002, 100.0)
        )

    def test_zero_division_rejected(self):
        with self.assertRaises(ValueError):
            resolution_floor_percent(0.0, 200.0)


class LimitTests(unittest.TestCase):
    def test_value_below_the_limit_passes(self):
        self.assertTrue(within_limit(0.4, DEFAULT_TML_LIMIT_PCT))

    def test_value_exactly_on_the_limit_passes(self):
        value = total_mass_loss_percent(200.0, 198.0)
        self.assertAlmostEqual(value, DEFAULT_TML_LIMIT_PCT, places=9)
        self.assertTrue(within_limit(value, DEFAULT_TML_LIMIT_PCT))

    def test_value_above_the_limit_fails(self):
        self.assertFalse(within_limit(1.4, DEFAULT_TML_LIMIT_PCT))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            within_limit(0.4, 0.0)

    def test_screening_limits_are_one_percent(self):
        self.assertAlmostEqual(DEFAULT_TML_LIMIT_PCT, 1.0, places=12)
        self.assertAlmostEqual(DEFAULT_RML_LIMIT_PCT, 1.0, places=12)


class SpecimenRecordTests(unittest.TestCase):
    def test_clean_specimen_is_compliant(self):
        record = specimen_record(_specimen())
        self.assertTrue(record["compliant"])
        self.assertAlmostEqual(record["total_mass_loss_pct"], 0.2, places=12)

    def test_regain_and_recovered_are_reported_when_a_third_weighing_exists(self):
        record = specimen_record(_specimen(final=198.0, recovered_mg=199.0))
        self.assertAlmostEqual(record["water_vapour_regained_pct"], 0.5, places=12)
        self.assertAlmostEqual(record["recovered_mass_loss_pct"], 0.5, places=12)

    def test_recovered_is_absent_without_the_third_weighing(self):
        record = specimen_record(_specimen())
        self.assertIsNone(record["recovered_mass_loss_pct"])

    def test_loss_above_the_limit_is_flagged(self):
        record = specimen_record(_specimen(final=195.0))
        self.assertFalse(record["compliant"])
        self.assertIn("exceeds", record["findings"][0])

    def test_a_loss_below_the_balance_resolution_is_flagged(self):
        record = specimen_record(
            _specimen(final=199.9999, readability_mg=0.01)
        )
        self.assertFalse(record["compliant"])
        self.assertIn("the balance can", record["findings"][0])

    def test_a_resolvable_loss_is_not_flagged(self):
        record = specimen_record(_specimen(readability_mg=0.001))
        self.assertTrue(record["compliant"])

    def test_recovered_loss_above_its_limit_is_flagged(self):
        record = specimen_record(
            _specimen(final=196.0, recovered_mg=197.0),
            {"rml_limit_pct": 1.0, "tml_limit_pct": 5.0},
        )
        self.assertFalse(record["compliant"])
        self.assertTrue(
            any("recovered mass loss" in note for note in record["findings"])
        )

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            specimen_record(_specimen(identifier=" "))

    def test_missing_final_mass_rejected(self):
        item = _specimen()
        del item["final_mg"]
        with self.assertRaises(ValueError):
            specimen_record(item)


class SetStatisticsTests(unittest.TestCase):
    def test_mean_of_a_set(self):
        stats = set_statistics([0.2, 0.3, 0.4])
        self.assertAlmostEqual(stats["mean"], 0.3, places=12)

    def test_spread_is_max_minus_min(self):
        stats = set_statistics([0.2, 0.3, 0.4])
        self.assertAlmostEqual(stats["spread"], 0.2, places=12)

    def test_single_value_has_zero_spread(self):
        self.assertAlmostEqual(set_statistics([0.25])["spread"], 0.0, places=12)

    def test_count_is_reported(self):
        self.assertEqual(set_statistics([0.2, 0.3])["count"], 2)

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            set_statistics([])

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            set_statistics([0.2, "0.3"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "specimens": [
                _specimen("S1", final=199.60),
                _specimen("S2", final=199.62),
                _specimen("S3", final=199.58),
            ]
        }
        spec.update(overrides)
        return spec

    def test_agreeing_replicates_pass_the_screening(self):
        result = assess_tml_measurement(self._spec())
        self.assertTrue(result["screened_pass"])
        self.assertEqual(result["findings"], [])

    def test_set_mean_is_reported(self):
        result = assess_tml_measurement(self._spec())
        self.assertAlmostEqual(result["total_mass_loss"]["mean"], 0.2, places=9)

    def test_set_count_is_reported(self):
        result = assess_tml_measurement(self._spec())
        self.assertEqual(result["total_mass_loss"]["count"], 3)

    def test_scattered_replicates_are_flagged(self):
        result = assess_tml_measurement(
            self._spec(
                specimens=[
                    _specimen("S1", final=199.6),
                    _specimen("S2", final=198.6),
                    _specimen("S3", final=199.5),
                ]
            )
        )
        self.assertFalse(result["screened_pass"])
        self.assertTrue(
            any("does not agree with itself" in note for note in result["findings"])
        )

    def test_scatter_exactly_on_the_allowance_is_accepted(self):
        low = total_mass_loss_percent(200.0, 199.7)
        high = total_mass_loss_percent(200.0, 199.5)
        self.assertAlmostEqual(high - low, DEFAULT_SCATTER_ALLOWANCE_PCT, places=9)
        result = assess_tml_measurement(
            self._spec(
                specimens=[
                    _specimen("S1", final=199.7),
                    _specimen("S2", final=199.6),
                    _specimen("S3", final=199.5),
                ]
            )
        )
        self.assertTrue(result["screened_pass"])

    def test_one_failing_coupon_fails_the_set(self):
        result = assess_tml_measurement(
            self._spec(
                specimens=[
                    _specimen("S1", final=199.6),
                    _specimen("S2", final=199.6),
                    _specimen("S3", final=190.0),
                ],
                options={"scatter_allowance_pct": 10.0},
            )
        )
        self.assertFalse(result["screened_pass"])

    def test_recovered_statistics_appear_with_third_weighings(self):
        result = assess_tml_measurement(
            self._spec(
                specimens=[
                    _specimen("S1", final=199.6, recovered_mg=199.7),
                    _specimen("S2", final=199.6, recovered_mg=199.7),
                ]
            )
        )
        self.assertIsNotNone(result["recovered_mass_loss"])
        self.assertAlmostEqual(result["recovered_mass_loss"]["mean"], 0.15, places=9)

    def test_recovered_statistics_absent_without_third_weighings(self):
        result = assess_tml_measurement(self._spec())
        self.assertIsNone(result["recovered_mass_loss"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_tml_measurement(
                self._spec(specimens=[_specimen("S1"), _specimen("S1")])
            )

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_tml_measurement(self._spec(specimens=[]))

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_tml_measurement({})

    def test_limits_can_be_tightened_through_options(self):
        strict = assess_tml_measurement(
            self._spec(options={"tml_limit_pct": 0.1})
        )
        self.assertFalse(strict["screened_pass"])


if __name__ == "__main__":
    unittest.main()
