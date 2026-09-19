"""Contract test for the witness plate sampling leaf (stdlib unittest)."""

import unittest

from q7005_witness_plate_method_logic import (
    AGREEMENT_TOLERANCE,
    AREAL_READING_NOISE_UG_PER_CM2,
    areal_mass_from_frequency_shift,
    assess_witness_sampling,
    control_corrected_gain,
    coupon_gross_gain,
    cross_check_coupon_and_crystal,
    deposition_rate_ug_per_cm2_per_h,
    project_accumulation_ug_per_cm2,
    scale_to_represented_surface,
    validate_coupon,
    validate_crystal,
    view_factor_ratio,
)


def exposed(**kw):
    record = {
        "id": "WP-01",
        "area_cm2": 25.0,
        "exposure_hours": 100.0,
        "pre_areal_ug_per_cm2": 0.0,
        "post_areal_ug_per_cm2": 1.2,
        "view_factor": 0.5,
        "exposed": True,
    }
    record.update(kw)
    return record


def control(**kw):
    record = {
        "id": "WP-CTRL",
        "area_cm2": 25.0,
        "exposure_hours": 0.0,
        "pre_areal_ug_per_cm2": 0.0,
        "post_areal_ug_per_cm2": 0.2,
        "view_factor": 0.5,
        "exposed": False,
    }
    record.update(kw)
    return record


def crystal(**kw):
    record = {
        "id": "QCM-A",
        "frequency_shift_hz": -2.0,
        "sensitivity_hz_per_ug_per_cm2": 2.0,
        "temperature_compensated": True,
    }
    record.update(kw)
    return record


def spec(**kw):
    base = {
        "exposed_coupon": exposed(),
        "control_coupon": control(),
        "crystal": crystal(),
        "surface_view_factor": 0.5,
        "allocated_ug_per_cm2": 2.0,
        "projection_hours": 100.0,
    }
    base.update(kw)
    return base


class TestValidateCoupon(unittest.TestCase):
    def test_valid_coupon_normalises(self):
        norm = validate_coupon(exposed(area_cm2=25))
        self.assertAlmostEqual(norm["area_cm2"], 25.0, places=9)
        self.assertEqual(norm["id"], "WP-01")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon("WP-01")

    def test_missing_key_raises(self):
        record = exposed()
        del record["view_factor"]
        with self.assertRaises(ValueError):
            validate_coupon(record)

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon(exposed(id="   "))

    def test_non_boolean_exposed_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon(exposed(exposed="yes"))

    def test_view_factor_above_unity_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon(exposed(view_factor=1.4))

    def test_zero_exposure_on_an_exposed_coupon_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon(exposed(exposure_hours=0.0))

    def test_zero_exposure_on_the_control_is_allowed(self):
        norm = validate_coupon(control())
        self.assertAlmostEqual(norm["exposure_hours"], 0.0, places=9)

    def test_negative_areal_reading_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon(exposed(pre_areal_ug_per_cm2=-0.1))


class TestCouponGain(unittest.TestCase):
    def test_gross_gain_is_post_minus_pre(self):
        self.assertAlmostEqual(coupon_gross_gain(exposed()), 1.2, places=9)

    def test_noise_level_loss_is_floored_at_zero(self):
        self.assertAlmostEqual(
            coupon_gross_gain(exposed(pre_areal_ug_per_cm2=0.10,
                                      post_areal_ug_per_cm2=0.09)),
            0.0,
            places=9,
        )

    def test_real_mass_loss_raises(self):
        with self.assertRaises(ValueError):
            coupon_gross_gain(exposed(pre_areal_ug_per_cm2=1.0,
                                      post_areal_ug_per_cm2=0.1))

    def test_control_gain_is_subtracted(self):
        gains = control_corrected_gain(exposed(), control())
        self.assertAlmostEqual(gains["gross_gain_ug_per_cm2"], 1.2, places=9)
        self.assertAlmostEqual(gains["control_gain_ug_per_cm2"], 0.2, places=9)
        self.assertAlmostEqual(gains["net_gain_ug_per_cm2"], 1.0, places=9)
        self.assertTrue(gains["quantifiable"])

    def test_control_gaining_more_than_the_exposed_coupon_raises(self):
        with self.assertRaises(ValueError):
            control_corrected_gain(exposed(post_areal_ug_per_cm2=0.1),
                                   control(post_areal_ug_per_cm2=0.9))

    def test_exposed_coupon_passed_as_control_raises(self):
        with self.assertRaises(ValueError):
            control_corrected_gain(exposed(), exposed(id="WP-02"))

    def test_control_coupon_passed_as_exposed_raises(self):
        with self.assertRaises(ValueError):
            control_corrected_gain(control(), control(id="WP-CTRL2"))

    def test_net_at_the_noise_floor_is_not_quantifiable(self):
        gains = control_corrected_gain(
            exposed(post_areal_ug_per_cm2=AREAL_READING_NOISE_UG_PER_CM2),
            control(post_areal_ug_per_cm2=0.0),
        )
        self.assertFalse(gains["quantifiable"])


class TestCrystal(unittest.TestCase):
    def test_shift_converts_through_the_sensitivity(self):
        self.assertAlmostEqual(
            areal_mass_from_frequency_shift(crystal()), 1.0, places=9
        )

    def test_larger_shift_gives_more_mass(self):
        self.assertAlmostEqual(
            areal_mass_from_frequency_shift(crystal(frequency_shift_hz=-6.0)),
            3.0,
            places=9,
        )

    def test_frequency_rise_raises(self):
        with self.assertRaises(ValueError):
            areal_mass_from_frequency_shift(crystal(frequency_shift_hz=3.0))

    def test_zero_sensitivity_raises(self):
        with self.assertRaises(ValueError):
            validate_crystal(crystal(sensitivity_hz_per_ug_per_cm2=0.0))

    def test_non_boolean_compensation_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_crystal(crystal(temperature_compensated="yes"))

    def test_missing_crystal_key_raises(self):
        record = crystal()
        del record["sensitivity_hz_per_ug_per_cm2"]
        with self.assertRaises(ValueError):
            validate_crystal(record)


class TestCrossCheck(unittest.TestCase):
    def test_equal_readings_agree(self):
        out = cross_check_coupon_and_crystal(1.0, 1.0)
        self.assertTrue(out["agrees"])
        self.assertAlmostEqual(out["relative_difference"], 0.0, places=9)

    def test_large_disagreement_is_flagged(self):
        out = cross_check_coupon_and_crystal(1.0, 3.0)
        self.assertFalse(out["agrees"])
        self.assertAlmostEqual(out["relative_difference"], 1.0, places=9)

    def test_difference_exactly_at_the_tolerance_still_agrees(self):
        out = cross_check_coupon_and_crystal(1.0, 9.0 / 7.0)
        self.assertAlmostEqual(
            out["relative_difference"], AGREEMENT_TOLERANCE, places=9
        )
        self.assertTrue(out["agrees"])

    def test_two_zero_readings_agree(self):
        out = cross_check_coupon_and_crystal(0.0, 0.0)
        self.assertTrue(out["agrees"])

    def test_negative_reading_raises(self):
        with self.assertRaises(ValueError):
            cross_check_coupon_and_crystal(-1.0, 1.0)


class TestScalingAndRate(unittest.TestCase):
    def test_equal_view_factors_give_unit_ratio(self):
        self.assertAlmostEqual(view_factor_ratio(0.5, 0.5), 1.0, places=9)

    def test_lower_surface_view_factor_reduces_the_figure(self):
        self.assertAlmostEqual(
            scale_to_represented_surface(1.0, 0.25, 0.5), 0.5, places=9
        )

    def test_view_factor_above_unity_raises(self):
        with self.assertRaises(ValueError):
            view_factor_ratio(1.2, 0.5)

    def test_zero_coupon_view_factor_raises(self):
        with self.assertRaises(ValueError):
            view_factor_ratio(0.5, 0.0)

    def test_rate_divides_by_the_exposure(self):
        self.assertAlmostEqual(
            deposition_rate_ug_per_cm2_per_h(1.0, 100.0), 0.01, places=9
        )

    def test_zero_exposure_hours_raises_in_the_rate(self):
        with self.assertRaises(ValueError):
            deposition_rate_ug_per_cm2_per_h(1.0, 0.0)

    def test_projection_within_the_measured_interval_is_not_extrapolated(self):
        out = project_accumulation_ug_per_cm2(0.01, 100.0, 100.0)
        self.assertAlmostEqual(out["projected_ug_per_cm2"], 1.0, places=9)
        self.assertFalse(out["beyond_measured_interval"])

    def test_projection_past_the_measured_interval_is_marked(self):
        out = project_accumulation_ug_per_cm2(0.01, 1000.0, 100.0)
        self.assertTrue(out["beyond_measured_interval"])
        self.assertAlmostEqual(out["projected_ug_per_cm2"], 10.0, places=9)


class TestAssessWitnessSampling(unittest.TestCase):
    def test_nominal_case_is_clean(self):
        out = assess_witness_sampling(spec())
        self.assertAlmostEqual(
            out["coupon_gains"]["net_gain_ug_per_cm2"], 1.0, places=9
        )
        self.assertAlmostEqual(out["crystal_areal_ug_per_cm2"], 1.0, places=9)
        self.assertAlmostEqual(out["view_factor_ratio"], 1.0, places=9)
        self.assertAlmostEqual(out["surface_areal_ug_per_cm2"], 1.0, places=9)
        self.assertAlmostEqual(
            out["deposition_rate_ug_per_cm2_per_h"], 0.01, places=9
        )
        self.assertTrue(out["within_allocation"])
        self.assertEqual(out["findings"], [])

    def test_view_factor_scaling_is_reported(self):
        out = assess_witness_sampling(spec(surface_view_factor=0.25))
        self.assertAlmostEqual(out["surface_areal_ug_per_cm2"], 0.5, places=9)
        self.assertTrue(any("view factors differ" in f for f in out["findings"]))

    def test_disagreeing_crystal_is_a_finding(self):
        out = assess_witness_sampling(spec(crystal=crystal(frequency_shift_hz=-6.0)))
        self.assertFalse(out["agreement"]["agrees"])
        self.assertTrue(any("agreement tolerance" in f for f in out["findings"]))

    def test_uncompensated_crystal_is_a_finding(self):
        out = assess_witness_sampling(
            spec(crystal=crystal(temperature_compensated=False))
        )
        self.assertTrue(any("temperature compensated" in f for f in out["findings"]))

    def test_projection_beyond_the_interval_is_a_finding(self):
        out = assess_witness_sampling(spec(projection_hours=1000.0,
                                           allocated_ug_per_cm2=50.0))
        self.assertTrue(any("decaying source" in f for f in out["findings"]))

    def test_exceeding_the_allocation_is_a_finding(self):
        out = assess_witness_sampling(spec(allocated_ug_per_cm2=0.5))
        self.assertFalse(out["within_allocation"])
        self.assertTrue(any("exceeds the allocated" in f for f in out["findings"]))

    def test_assessment_runs_without_a_crystal(self):
        out = assess_witness_sampling(spec(crystal=None))
        self.assertIsNone(out["crystal_areal_ug_per_cm2"])
        self.assertIsNone(out["agreement"])
        self.assertEqual(out["findings"], [])

    def test_below_noise_net_is_a_finding(self):
        out = assess_witness_sampling(
            spec(exposed_coupon=exposed(post_areal_ug_per_cm2=0.21),
                 crystal=None, allocated_ug_per_cm2=5.0)
        )
        self.assertTrue(any("reading noise" in f for f in out["findings"]))

    def test_missing_key_raises(self):
        broken = spec()
        del broken["allocated_ug_per_cm2"]
        with self.assertRaises(ValueError):
            assess_witness_sampling(broken)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_witness_sampling(["coupon"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
