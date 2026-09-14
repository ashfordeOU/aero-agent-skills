#!/usr/bin/env python3
"""Contract test for photon irradiation and annealing, clause 7.5.15 (offline)."""

import copy
import unittest

from e2008_photon_irradiation_and_annealing_logic import (
    DEFAULT_PHOTON_POLICY,
    LOT_OPEN,
    LOT_QUALIFIED,
    PROFILE_AS_DECLARED,
    PROFILE_OUT_OF_ORDER,
    PROFILE_SHORT,
    RECOVERY_COMPLETE,
    RECOVERY_NONE,
    RECOVERY_NOT_APPLICABLE,
    RECOVERY_OVERSHOOT,
    RECOVERY_PARTIAL,
    REQUIRED_SEQUENCE,
    SPECIMEN_NOT_EVALUATED,
    SPECIMEN_QUALIFIED,
    SPECIMEN_REJECTED,
    STEP_ANNEAL,
    STEP_EXPOSURE,
    assess_photon_irradiation_and_annealing,
    assess_specimen,
    categorize_recovery,
    read_anneal,
    read_exposure,
    recovered_share,
    relative_loss,
    validate_photon_policy,
    validate_sequence,
)


def _exposure(**overrides):
    record = {
        "equivalent_sun_hours": 1000.0,
        "temperature_c": 60.0,
        "pressure_pa": 1.0e-4,
    }
    record.update(overrides)
    return record


def _anneal(**overrides):
    record = {"soak_temperature_c": 90.0, "soak_hours": 4.0}
    record.update(overrides)
    return record


def _specimen(specimen_id="cell-a", pre=1.000, exposed=0.990, annealed=1.000, **over):
    record = {
        "specimen_id": specimen_id,
        "pre_exposure_pmax_w": pre,
        "post_exposure_pmax_w": exposed,
        "post_anneal_pmax_w": annealed,
        "steps": list(REQUIRED_SEQUENCE),
        "exposure": _exposure(),
        "anneal": _anneal(),
    }
    record.update(over)
    return record


def _case(*specimens, **overrides):
    case = {
        "specimens": list(specimens)
        or [
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c"),
        ]
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_photon_policy(DEFAULT_PHOTON_POLICY), DEFAULT_PHOTON_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_photon_policy("expose then soak")

    def test_zero_dose_requirement_rejected(self):
        broken = copy.deepcopy(DEFAULT_PHOTON_POLICY)
        broken["required_equivalent_sun_hours"] = 0.0
        with self.assertRaises(ValueError):
            validate_photon_policy(broken)

    def test_inverted_exposure_temperature_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_PHOTON_POLICY)
        broken["min_exposure_temperature_c"] = 90.0
        with self.assertRaises(ValueError):
            validate_photon_policy(broken)

    def test_inverted_anneal_soak_window_rejected(self):
        broken = copy.deepcopy(DEFAULT_PHOTON_POLICY)
        broken["max_anneal_soak_temperature_c"] = 40.0
        with self.assertRaises(ValueError):
            validate_photon_policy(broken)

    def test_non_integer_specimen_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_PHOTON_POLICY)
        broken["min_specimens"] = 2.5
        with self.assertRaises(ValueError):
            validate_photon_policy(broken)


class SequenceTests(unittest.TestCase):
    def test_declared_order_is_accepted(self):
        read = validate_sequence(list(REQUIRED_SEQUENCE))
        self.assertEqual(read["status"], PROFILE_AS_DECLARED)
        self.assertEqual(read["findings"], [])

    def test_soak_before_exposure_is_out_of_order(self):
        steps = list(REQUIRED_SEQUENCE)
        exposure_at = steps.index(STEP_EXPOSURE)
        anneal_at = steps.index(STEP_ANNEAL)
        steps[exposure_at], steps[anneal_at] = steps[anneal_at], steps[exposure_at]
        read = validate_sequence(steps)
        self.assertEqual(read["status"], PROFILE_OUT_OF_ORDER)
        self.assertTrue(read["findings"])

    def test_missing_step_is_reported_as_short(self):
        steps = [s for s in REQUIRED_SEQUENCE if s != STEP_ANNEAL]
        read = validate_sequence(steps)
        self.assertEqual(read["status"], PROFILE_SHORT)
        self.assertTrue(any(STEP_ANNEAL in text for text in read["findings"]))

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(list(REQUIRED_SEQUENCE) + ["coffee-break"])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(list(REQUIRED_SEQUENCE) + [STEP_EXPOSURE])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])


class ExposureTests(unittest.TestCase):
    def test_profile_exposure_is_accepted(self):
        read = read_exposure(_exposure())
        self.assertEqual(read["status"], PROFILE_AS_DECLARED)

    def test_exposure_exactly_on_the_declared_dose_is_accepted(self):
        read = read_exposure(_exposure(equivalent_sun_hours=1000.0))
        self.assertEqual(read["status"], PROFILE_AS_DECLARED)
        self.assertAlmostEqual(read["equivalent_sun_hours"], 1000.0, places=9)

    def test_short_dose_is_reported(self):
        read = read_exposure(_exposure(equivalent_sun_hours=400.0))
        self.assertEqual(read["status"], PROFILE_SHORT)
        self.assertTrue(any("equivalent sun hours" in t for t in read["findings"]))

    def test_exposure_outside_the_temperature_window_is_reported(self):
        read = read_exposure(_exposure(temperature_c=110.0))
        self.assertEqual(read["status"], PROFILE_SHORT)

    def test_exposure_above_the_pressure_ceiling_is_reported(self):
        read = read_exposure(_exposure(pressure_pa=5.0))
        self.assertEqual(read["status"], PROFILE_SHORT)
        self.assertTrue(any("filtered ultraviolet" in t for t in read["findings"]))

    def test_non_positive_pressure_rejected(self):
        with self.assertRaises(ValueError):
            read_exposure(_exposure(pressure_pa=0.0))

    def test_negative_dose_rejected(self):
        with self.assertRaises(ValueError):
            read_exposure(_exposure(equivalent_sun_hours=-10.0))

    def test_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            read_exposure("a thousand hours")


class AnnealTests(unittest.TestCase):
    def test_profile_soak_is_accepted(self):
        read = read_anneal(_anneal())
        self.assertEqual(read["status"], PROFILE_AS_DECLARED)

    def test_soak_on_the_minimum_duration_is_accepted(self):
        read = read_anneal(_anneal(soak_hours=DEFAULT_PHOTON_POLICY["min_anneal_soak_hours"]))
        self.assertEqual(read["status"], PROFILE_AS_DECLARED)

    def test_short_soak_is_reported(self):
        read = read_anneal(_anneal(soak_hours=0.5))
        self.assertEqual(read["status"], PROFILE_SHORT)

    def test_soak_outside_the_temperature_window_is_reported(self):
        read = read_anneal(_anneal(soak_temperature_c=20.0))
        self.assertEqual(read["status"], PROFILE_SHORT)

    def test_non_numeric_soak_duration_rejected(self):
        with self.assertRaises(ValueError):
            read_anneal(_anneal(soak_hours="overnight"))


class RecoveryTests(unittest.TestCase):
    def test_relative_loss_is_the_share_given_up(self):
        self.assertAlmostEqual(relative_loss(1.000, 0.950), 0.05, places=9)

    def test_relative_loss_on_a_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            relative_loss(0.0, 0.0)

    def test_full_recovery_returns_a_unit_share(self):
        self.assertAlmostEqual(recovered_share(1.000, 0.950, 1.000), 1.0, places=9)

    def test_half_recovery_returns_a_half_share(self):
        self.assertAlmostEqual(recovered_share(1.000, 0.950, 0.975), 0.5, places=9)

    def test_no_loss_leaves_the_recovery_share_undefined(self):
        self.assertIsNone(recovered_share(1.000, 1.000, 1.000))

    def test_full_recovery_is_grouped_as_complete(self):
        self.assertEqual(
            categorize_recovery(1.000, 0.950, 1.000), RECOVERY_COMPLETE
        )

    def test_partial_recovery_is_grouped_as_partial(self):
        self.assertEqual(categorize_recovery(1.000, 0.950, 0.975), RECOVERY_PARTIAL)

    def test_soak_that_gave_nothing_back_is_grouped_as_none(self):
        self.assertEqual(categorize_recovery(1.000, 0.950, 0.950), RECOVERY_NONE)

    def test_reading_above_the_baseline_is_grouped_as_an_overshoot(self):
        self.assertEqual(categorize_recovery(1.000, 0.950, 1.020), RECOVERY_OVERSHOOT)

    def test_an_undamaged_cell_has_no_recovery_to_group(self):
        self.assertEqual(
            categorize_recovery(1.000, 1.000, 1.000), RECOVERY_NOT_APPLICABLE
        )


class SpecimenTests(unittest.TestCase):
    def test_a_clean_specimen_qualifies(self):
        record = assess_specimen(_specimen())
        self.assertEqual(record["verdict"], SPECIMEN_QUALIFIED)
        self.assertEqual(record["findings"], [])
        self.assertAlmostEqual(record["residual_loss_fraction"], 0.0, places=9)

    def test_residual_loss_over_the_allowance_rejects_the_specimen(self):
        record = assess_specimen(_specimen(pre=1.000, exposed=0.900, annealed=0.950))
        self.assertEqual(record["verdict"], SPECIMEN_REJECTED)
        self.assertAlmostEqual(record["residual_loss_fraction"], 0.05, places=9)

    def test_residual_loss_exactly_on_the_allowance_qualifies(self):
        record = assess_specimen(_specimen(pre=1.000, exposed=0.950, annealed=0.980))
        self.assertTrue(record["residual_within_allowance"])
        self.assertEqual(record["verdict"], SPECIMEN_QUALIFIED)

    def test_a_short_exposure_leaves_the_specimen_unsentenced(self):
        record = assess_specimen(
            _specimen(exposure=_exposure(equivalent_sun_hours=200.0))
        )
        self.assertEqual(record["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertFalse(record["profile_met"])

    def test_an_out_of_order_run_leaves_the_specimen_unsentenced(self):
        steps = list(REQUIRED_SEQUENCE)
        steps[1], steps[3] = steps[3], steps[1]
        record = assess_specimen(_specimen(steps=steps))
        self.assertEqual(record["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(record["sequence_status"], PROFILE_OUT_OF_ORDER)

    def test_an_overshoot_leaves_the_specimen_unsentenced(self):
        record = assess_specimen(_specimen(pre=1.000, exposed=0.950, annealed=1.020))
        self.assertEqual(record["verdict"], SPECIMEN_NOT_EVALUATED)
        self.assertEqual(record["recovery_category"], RECOVERY_OVERSHOOT)
        self.assertTrue(any("reference conditions" in t for t in record["findings"]))

    def test_exposure_loss_is_kept_apart_from_the_residual(self):
        record = assess_specimen(_specimen(pre=1.000, exposed=0.900, annealed=0.990))
        self.assertAlmostEqual(record["exposure_loss_fraction"], 0.10, places=9)
        self.assertAlmostEqual(record["residual_loss_fraction"], 0.01, places=9)

    def test_specimen_without_an_identifier_rejected(self):
        broken = _specimen()
        del broken["specimen_id"]
        with self.assertRaises(ValueError):
            assess_specimen(broken)

    def test_specimen_with_a_zero_baseline_rejected(self):
        with self.assertRaises(ValueError):
            assess_specimen(_specimen(pre=0.0))

    def test_specimen_missing_its_anneal_record_rejected(self):
        broken = _specimen()
        del broken["anneal"]
        with self.assertRaises(ValueError):
            assess_specimen(broken)


class RunTests(unittest.TestCase):
    def test_a_clean_run_qualifies_the_lot(self):
        result = assess_photon_irradiation_and_annealing(_case())
        self.assertEqual(result["verdict"], LOT_QUALIFIED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["specimen_count"], 3)

    def test_a_rejected_specimen_opens_the_lot(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", pre=1.000, exposed=0.900, annealed=0.950),
        )
        result = assess_photon_irradiation_and_annealing(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertEqual(result["specimens_by_verdict"][SPECIMEN_REJECTED], ["cell-c"])

    def test_an_unsentenced_specimen_opens_the_lot(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", exposure=_exposure(equivalent_sun_hours=100.0)),
        )
        result = assess_photon_irradiation_and_annealing(case)
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertTrue(any("unsentenced" in t for t in result["findings"]))

    def test_a_run_short_of_specimens_opens_the_lot(self):
        result = assess_photon_irradiation_and_annealing(_case(_specimen("cell-a")))
        self.assertEqual(result["verdict"], LOT_OPEN)
        self.assertFalse(result["population_met"])

    def test_records_come_back_in_identifier_order(self):
        case = _case(_specimen("cell-c"), _specimen("cell-a"), _specimen("cell-b"))
        result = assess_photon_irradiation_and_annealing(case)
        self.assertEqual(
            [r["specimen_id"] for r in result["specimen_records"]],
            ["cell-a", "cell-b", "cell-c"],
        )

    def test_worst_and_mean_residual_are_reported(self):
        case = _case(
            _specimen("cell-a", pre=1.000, exposed=0.950, annealed=1.000),
            _specimen("cell-b", pre=1.000, exposed=0.950, annealed=0.990),
            _specimen("cell-c", pre=1.000, exposed=0.950, annealed=0.980),
        )
        result = assess_photon_irradiation_and_annealing(case)
        self.assertAlmostEqual(result["worst_residual_loss_fraction"], 0.02, places=9)
        self.assertAlmostEqual(result["mean_residual_loss_fraction"], 0.01, places=9)

    def test_repeated_specimen_identifier_rejected(self):
        case = _case(_specimen("cell-a"), _specimen("cell-a"), _specimen("cell-b"))
        with self.assertRaises(ValueError):
            assess_photon_irradiation_and_annealing(case)

    def test_empty_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_photon_irradiation_and_annealing({"specimens": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_photon_irradiation_and_annealing([_specimen()])

    def test_the_lot_carries_every_specimen_finding(self):
        case = _case(
            _specimen("cell-a"),
            _specimen("cell-b"),
            _specimen("cell-c", pre=1.000, exposed=0.900, annealed=0.950),
        )
        result = assess_photon_irradiation_and_annealing(case)
        self.assertTrue(any("cell-c" in t for t in result["findings"]))


if __name__ == "__main__":
    unittest.main()
