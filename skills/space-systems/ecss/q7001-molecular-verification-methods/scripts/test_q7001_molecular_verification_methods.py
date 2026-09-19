"""Contract tests for the ECSS-Q-ST-70-01C molecular measurement-method logic."""

import unittest

from q7001_molecular_verification_methods_logic import (
    DENSITY_TOLERANCE,
    apply_rinse_recovery,
    assess_molecular_measurement,
    detection_floor_mg_per_m2,
    infrared_mass_mg,
    is_non_detect,
    net_residue_mg,
    surface_density_mg_per_m2,
    transfer_witness_density,
    validate_fraction,
    validate_positive,
    witness_transfer_ratio,
)


class ValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertAlmostEqual(validate_positive("x", 3), 3.0, places=9)

    def test_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", 0.0)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("x", float("inf"))

    def test_fraction_of_one_allowed(self):
        self.assertAlmostEqual(validate_fraction("f", 1.0), 1.0, places=9)

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction("f", 1.0001)

    def test_fraction_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_fraction("f", 0.0)


class GravimetricTests(unittest.TestCase):
    def test_blank_is_subtracted(self):
        self.assertAlmostEqual(net_residue_mg(2.40, 0.40), 2.0, places=9)

    def test_aliquot_scales_the_mass_up(self):
        self.assertAlmostEqual(net_residue_mg(0.50, 0.0, 0.25), 2.0, places=9)

    def test_blank_above_the_residue_gives_a_non_positive_mass(self):
        self.assertLess(net_residue_mg(0.20, 0.50), 0.0)

    def test_negative_weighed_mass_rejected(self):
        with self.assertRaises(ValueError):
            net_residue_mg(-0.10)

    def test_negative_blank_rejected(self):
        with self.assertRaises(ValueError):
            net_residue_mg(1.0, -0.1)

    def test_zero_aliquot_rejected(self):
        with self.assertRaises(ValueError):
            net_residue_mg(1.0, 0.0, 0.0)

    def test_density_divides_by_the_rinsed_area(self):
        self.assertAlmostEqual(surface_density_mg_per_m2(2.0, 0.5), 4.0, places=9)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            surface_density_mg_per_m2(2.0, 0.0)


class InfraredTests(unittest.TestCase):
    def test_beer_lambert_mass(self):
        # A = 0.2, a = 2 L/(g cm), b = 1 cm -> 0.1 g/L over 100 mL -> 10 mg.
        self.assertAlmostEqual(infrared_mass_mg(0.2, 1.0, 2.0, 100.0), 10.0, places=9)

    def test_mass_is_linear_in_absorbance(self):
        single = infrared_mass_mg(0.2, 1.0, 2.0, 100.0)
        double = infrared_mass_mg(0.4, 1.0, 2.0, 100.0)
        self.assertAlmostEqual(double, 2.0 * single, places=9)

    def test_longer_path_lowers_the_mass(self):
        short = infrared_mass_mg(0.2, 1.0, 2.0, 100.0)
        long_path = infrared_mass_mg(0.2, 5.0, 2.0, 100.0)
        self.assertAlmostEqual(long_path, short / 5.0, places=9)

    def test_zero_absorbance_gives_zero_mass(self):
        self.assertAlmostEqual(infrared_mass_mg(0.0, 1.0, 2.0, 100.0), 0.0, places=12)

    def test_negative_absorbance_rejected(self):
        with self.assertRaises(ValueError):
            infrared_mass_mg(-0.1, 1.0, 2.0, 100.0)

    def test_zero_absorptivity_rejected(self):
        with self.assertRaises(ValueError):
            infrared_mass_mg(0.2, 1.0, 0.0, 100.0)


class RecoveryAndFloorTests(unittest.TestCase):
    def test_recovery_scales_the_density_up(self):
        self.assertAlmostEqual(apply_rinse_recovery(4.0, 0.8), 5.0, places=9)

    def test_full_recovery_is_the_identity(self):
        self.assertAlmostEqual(apply_rinse_recovery(4.0, 1.0), 4.0, places=9)

    def test_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            apply_rinse_recovery(4.0, 1.5)

    def test_floor_from_balance_readability_and_area(self):
        self.assertAlmostEqual(
            detection_floor_mg_per_m2(0.01, 0.5), 0.02, places=12
        )

    def test_aliquot_raises_the_floor(self):
        whole = detection_floor_mg_per_m2(0.01, 0.5, 1.0)
        quarter = detection_floor_mg_per_m2(0.01, 0.5, 0.25)
        self.assertAlmostEqual(quarter, 4.0 * whole, places=12)

    def test_recovery_raises_the_floor(self):
        full = detection_floor_mg_per_m2(0.01, 0.5, 1.0, 1.0)
        partial = detection_floor_mg_per_m2(0.01, 0.5, 1.0, 0.5)
        self.assertAlmostEqual(partial, 2.0 * full, places=12)

    def test_value_below_the_floor_is_a_non_detect(self):
        self.assertTrue(is_non_detect(0.01, 0.02))

    def test_value_exactly_at_the_floor_is_a_non_detect(self):
        self.assertTrue(is_non_detect(0.02, 0.02))

    def test_value_above_the_floor_is_a_detect(self):
        self.assertFalse(is_non_detect(0.05, 0.02))


class WitnessTransferTests(unittest.TestCase):
    def test_equal_conditions_give_unity(self):
        self.assertAlmostEqual(
            witness_transfer_ratio(0.4, 0.4, 100.0, 100.0), 1.0, places=9
        )

    def test_view_factor_ratio_scales_the_transfer(self):
        self.assertAlmostEqual(
            witness_transfer_ratio(0.8, 0.4, 100.0, 100.0), 2.0, places=9
        )

    def test_exposure_ratio_scales_the_transfer(self):
        self.assertAlmostEqual(
            witness_transfer_ratio(0.4, 0.4, 250.0, 100.0), 2.5, places=9
        )

    def test_view_factor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            witness_transfer_ratio(1.2, 0.4, 100.0, 100.0)

    def test_zero_witness_exposure_rejected(self):
        with self.assertRaises(ValueError):
            witness_transfer_ratio(0.4, 0.4, 100.0, 0.0)

    def test_transfer_applies_the_ratio(self):
        self.assertAlmostEqual(transfer_witness_density(1.5, 2.0), 3.0, places=9)

    def test_negative_witness_density_rejected(self):
        with self.assertRaises(ValueError):
            transfer_witness_density(-1.0, 2.0)


class AssessmentTests(unittest.TestCase):
    def _gravimetric(self, **overrides):
        spec = {
            "method": "rinse-gravimetric",
            "weighed_mg": 0.60,
            "blank_mg": 0.10,
            "aliquot_fraction": 0.25,
            "recovery_fraction": 0.8,
            "area_m2": 0.5,
            "readability_mg": 0.01,
            "allowed_density_mg_per_m2": 10.0,
        }
        spec.update(overrides)
        return spec

    def _witness(self, **overrides):
        spec = {
            "method": "witness-plate",
            "witness_density_mg_per_m2": 1.0,
            "view_factor_hardware": 0.6,
            "view_factor_witness": 0.3,
            "exposure_hours_hardware": 200.0,
            "exposure_hours_witness": 100.0,
            "area_m2": 0.5,
            "readability_mg": 0.01,
            "allowed_density_mg_per_m2": 10.0,
        }
        spec.update(overrides)
        return spec

    def test_gravimetric_density_matches_the_hand_calculation(self):
        result = assess_molecular_measurement(self._gravimetric())
        # (0.60 - 0.10)/0.25 = 2.0 mg; /0.5 m2 = 4.0; /0.8 recovery = 5.0
        self.assertAlmostEqual(result["density_mg_per_m2"], 5.0, places=9)
        self.assertTrue(result["compliant"])

    def test_gravimetric_exceedance_is_flagged(self):
        result = assess_molecular_measurement(
            self._gravimetric(allowed_density_mg_per_m2=2.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds" in item for item in result["findings"]))

    def test_density_exactly_at_the_limit_is_compliant(self):
        base = assess_molecular_measurement(self._gravimetric())
        result = assess_molecular_measurement(
            self._gravimetric(allowed_density_mg_per_m2=base["density_mg_per_m2"])
        )
        self.assertTrue(result["compliant"])
        self.assertLessEqual(
            abs(result["density_mg_per_m2"] - result["allowed_density_mg_per_m2"]),
            DENSITY_TOLERANCE * result["allowed_density_mg_per_m2"],
        )

    def test_blank_above_the_residue_reports_a_non_detect(self):
        result = assess_molecular_measurement(
            self._gravimetric(weighed_mg=0.05, blank_mg=0.10)
        )
        self.assertTrue(result["non_detect"])

    def test_coarse_balance_makes_the_method_unable_to_substantiate(self):
        result = assess_molecular_measurement(
            self._gravimetric(readability_mg=5.0, allowed_density_mg_per_m2=1.0)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("cannot substantiate" in item for item in result["findings"])
        )

    def test_infrared_route_reduces_to_a_density(self):
        result = assess_molecular_measurement(
            {
                "method": "rinse-infrared",
                "absorbance": 0.2,
                "path_length_cm": 1.0,
                "absorptivity_l_per_g_cm": 2.0,
                "volume_ml": 100.0,
                "area_m2": 0.5,
                "readability_mg": 0.01,
                "allowed_density_mg_per_m2": 50.0,
            }
        )
        self.assertAlmostEqual(result["density_mg_per_m2"], 20.0, places=9)

    def test_infrared_route_needs_its_optical_inputs(self):
        with self.assertRaises(ValueError):
            assess_molecular_measurement(
                {
                    "method": "rinse-infrared",
                    "absorbance": 0.2,
                    "area_m2": 0.5,
                    "readability_mg": 0.01,
                    "allowed_density_mg_per_m2": 50.0,
                }
            )

    def test_witness_transfer_is_applied_and_declared(self):
        result = assess_molecular_measurement(self._witness())
        self.assertAlmostEqual(result["density_mg_per_m2"], 4.0, places=9)
        self.assertTrue(any("witness plate" in item for item in result["findings"]))

    def test_witness_transfer_without_a_declared_ratio_is_refused(self):
        spec = self._witness()
        del spec["view_factor_hardware"]
        with self.assertRaises(ValueError):
            assess_molecular_measurement(spec)

    def test_recovery_is_not_applied_to_a_witness_reading(self):
        with_recovery = assess_molecular_measurement(
            self._witness(recovery_fraction=0.5)
        )
        plain = assess_molecular_measurement(self._witness())
        self.assertAlmostEqual(
            with_recovery["density_mg_per_m2"], plain["density_mg_per_m2"], places=9
        )

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_molecular_measurement(self._gravimetric(method="swab-extract"))

    def test_missing_area_rejected(self):
        spec = self._gravimetric()
        del spec["area_m2"]
        with self.assertRaises(ValueError):
            assess_molecular_measurement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_molecular_measurement(["method"])

    def test_gravimetric_route_needs_a_weighed_mass(self):
        spec = self._gravimetric()
        del spec["weighed_mg"]
        with self.assertRaises(ValueError):
            assess_molecular_measurement(spec)


if __name__ == "__main__":
    unittest.main()
