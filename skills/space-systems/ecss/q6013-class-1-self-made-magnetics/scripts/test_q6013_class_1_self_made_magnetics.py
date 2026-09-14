"""Contract tests for the clause 4.6.8 in-house wound magnetic part logic."""

import unittest

from q6013_class_1_self_made_magnetics_logic import (
    DEFAULT_CURRENT_DENSITY_LIMIT_A_PER_MM2,
    DEFAULT_DIELECTRIC_WITHSTAND_FACTOR,
    DEFAULT_SATURATION_UTILIZATION_CEILING,
    MANDATORY_SCREENING,
    VALUE_TOLERANCE,
    assess_core_flux,
    assess_insulation_system,
    assess_self_made_magnetic,
    assess_winding,
    current_density,
    missing_screening_steps,
    normalize_token,
    saturation_utilization,
    validate_part_identity,
    validate_process_basis,
    validate_winding,
)

PART = {
    "designation": "TX-441 flyback transformer",
    "core_reference": "ferrite RM10 gapped",
    "winding_shop": "in-house magnetics bench",
}

BASIS = {
    "winding_process_document": "WP-MAG-018",
    "process_issue": "issue 2",
    "operator_qualified": True,
}


def _winding(**overrides):
    winding = {
        "name": "primary",
        "turns": 42,
        "conductor_area_mm2": 0.5,
        "rms_current_a": 1.5,
    }
    winding.update(overrides)
    return winding


def _core(**overrides):
    core = {"peak_flux_density_t": 0.2, "saturation_flux_density_hot_t": 0.4}
    core.update(overrides)
    return core


def _insulation(**overrides):
    insulation = {
        "hot_spot_temperature_c": 95.0,
        "system_rated_temperature_c": 130.0,
        "working_voltage_v": 120.0,
        "demonstrated_withstand_v": 500.0,
    }
    insulation.update(overrides)
    return insulation


def _record(**overrides):
    record = {
        "part": dict(PART),
        "process_basis": dict(BASIS),
        "windings": [_winding(), _winding(name="secondary", turns=9,
                                          rms_current_a=1.0)],
        "core": _core(),
        "insulation": _insulation(),
        "screening_steps": list(MANDATORY_SCREENING),
    }
    record.update(overrides)
    return record


class IdentityTests(unittest.TestCase):
    def test_identity_returned_stripped(self):
        identity = validate_part_identity(dict(PART, designation="  TX-441  "))
        self.assertEqual(identity["designation"], "TX-441")

    def test_missing_core_reference_rejected(self):
        bad = dict(PART)
        del bad["core_reference"]
        with self.assertRaises(ValueError):
            validate_part_identity(bad)

    def test_blank_winding_shop_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_identity(dict(PART, winding_shop="  "))

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_identity("TX-441")

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Dielectric Withstand Test"), "dielectric-withstand-test"
        )


class ProcessBasisTests(unittest.TestCase):
    def test_basis_returned(self):
        basis = validate_process_basis(dict(BASIS))
        self.assertEqual(basis["winding_process_document"], "WP-MAG-018")
        self.assertTrue(basis["operator_qualified"])

    def test_missing_process_issue_rejected(self):
        bad = dict(BASIS)
        del bad["process_issue"]
        with self.assertRaises(ValueError):
            validate_process_basis(bad)

    def test_blank_process_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_basis(dict(BASIS, winding_process_document=""))

    def test_non_boolean_operator_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_basis(dict(BASIS, operator_qualified="yes"))

    def test_unqualified_operator_is_a_finding_not_an_error(self):
        result = assess_self_made_magnetic(
            _record(process_basis=dict(BASIS, operator_qualified=False))
        )
        self.assertFalse(result["fit_for_class_1_use"])
        self.assertTrue(any("qualification" in f for f in result["findings"]))


class WindingTests(unittest.TestCase):
    def test_winding_returned_validated(self):
        record = validate_winding(_winding())
        self.assertEqual(record["turns"], 42)
        self.assertAlmostEqual(record["conductor_area_mm2"], 0.5, places=9)

    def test_zero_turns_rejected(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding(turns=0))

    def test_fractional_turns_rejected(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding(turns=4.5))

    def test_zero_conductor_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding(conductor_area_mm2=0.0))

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_winding(_winding(rms_current_a=-1.0))

    def test_missing_winding_name_rejected(self):
        bad = _winding()
        del bad["name"]
        with self.assertRaises(ValueError):
            validate_winding(bad)

    def test_current_density_is_current_over_area(self):
        self.assertAlmostEqual(current_density(1.5, 0.5), 3.0, places=9)

    def test_density_exactly_on_the_limit_is_admissible(self):
        record = assess_winding(
            _winding(rms_current_a=2.0, conductor_area_mm2=0.5),
            limit_a_per_mm2=4.0,
        )
        self.assertAlmostEqual(
            record["current_density_a_per_mm2"],
            record["current_density_limit_a_per_mm2"],
            places=9,
        )
        self.assertTrue(record["within_current_density_limit"])
        self.assertEqual(record["findings"], [])

    def test_density_above_the_limit_is_a_finding(self):
        record = assess_winding(_winding(rms_current_a=6.0))
        self.assertFalse(record["within_current_density_limit"])
        self.assertEqual(len(record["findings"]), 1)

    def test_default_density_limit_is_applied_when_none_declared(self):
        record = assess_winding(_winding())
        self.assertAlmostEqual(
            record["current_density_limit_a_per_mm2"],
            DEFAULT_CURRENT_DENSITY_LIMIT_A_PER_MM2,
            places=9,
        )


class CoreFluxTests(unittest.TestCase):
    def test_utilization_is_peak_over_saturation(self):
        self.assertAlmostEqual(saturation_utilization(0.2, 0.4), 0.5, places=9)

    def test_zero_saturation_rejected(self):
        with self.assertRaises(ValueError):
            saturation_utilization(0.2, 0.0)

    def test_utilization_exactly_on_the_ceiling_is_admissible(self):
        record = assess_core_flux(_core(peak_flux_density_t=0.32))
        self.assertAlmostEqual(record["utilization"], record["ceiling"], places=9)
        self.assertTrue(record["within_ceiling"])

    def test_utilization_above_the_ceiling_is_a_finding(self):
        record = assess_core_flux(_core(peak_flux_density_t=0.38))
        self.assertFalse(record["within_ceiling"])
        self.assertEqual(len(record["findings"]), 1)

    def test_tighter_declared_ceiling_is_applied(self):
        record = assess_core_flux(_core(), ceiling=0.6)
        self.assertAlmostEqual(record["ceiling"], 0.6, places=9)
        self.assertTrue(record["within_ceiling"])

    def test_tighter_declared_ceiling_can_raise_a_finding(self):
        record = assess_core_flux(_core(), ceiling=0.4)
        self.assertFalse(record["within_ceiling"])
        self.assertEqual(len(record["findings"]), 1)

    def test_looser_declared_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            assess_core_flux(_core(), ceiling=0.95)

    def test_ceiling_equal_to_the_default_is_accepted(self):
        record = assess_core_flux(
            _core(), ceiling=DEFAULT_SATURATION_UTILIZATION_CEILING
        )
        self.assertAlmostEqual(
            record["ceiling"], DEFAULT_SATURATION_UTILIZATION_CEILING, places=9
        )

    def test_missing_saturation_key_rejected(self):
        bad = _core()
        del bad["saturation_flux_density_hot_t"]
        with self.assertRaises(ValueError):
            assess_core_flux(bad)


class InsulationTests(unittest.TestCase):
    def test_clean_insulation_raises_no_finding(self):
        record = assess_insulation_system(_insulation())
        self.assertEqual(record["findings"], [])
        self.assertTrue(record["thermally_within_rating"])
        self.assertTrue(record["withstand_met"])

    def test_required_withstand_is_the_factor_times_working_voltage(self):
        record = assess_insulation_system(_insulation())
        self.assertAlmostEqual(record["required_withstand_v"], 240.0, places=9)

    def test_hot_spot_above_the_rating_is_a_finding(self):
        record = assess_insulation_system(
            _insulation(hot_spot_temperature_c=150.0)
        )
        self.assertFalse(record["thermally_within_rating"])

    def test_hot_spot_exactly_on_the_rating_is_admissible(self):
        record = assess_insulation_system(_insulation(hot_spot_temperature_c=130.0))
        self.assertAlmostEqual(
            record["hot_spot_temperature_c"],
            record["system_rated_temperature_c"],
            places=9,
        )
        self.assertTrue(record["thermally_within_rating"])

    def test_withstand_exactly_on_the_requirement_is_admissible(self):
        record = assess_insulation_system(_insulation(demonstrated_withstand_v=240.0))
        self.assertAlmostEqual(
            record["demonstrated_withstand_v"], record["required_withstand_v"],
            places=9,
        )
        self.assertTrue(record["withstand_met"])

    def test_short_withstand_is_a_finding(self):
        record = assess_insulation_system(_insulation(demonstrated_withstand_v=100.0))
        self.assertFalse(record["withstand_met"])

    def test_both_shortfalls_give_two_findings(self):
        record = assess_insulation_system(
            _insulation(hot_spot_temperature_c=150.0, demonstrated_withstand_v=100.0)
        )
        self.assertEqual(len(record["findings"]), 2)

    def test_stricter_declared_factor_is_applied(self):
        record = assess_insulation_system(_insulation(), withstand_factor=3.0)
        self.assertAlmostEqual(record["required_withstand_v"], 360.0, places=9)

    def test_weaker_declared_factor_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_system(_insulation(), withstand_factor=1.2)

    def test_factor_equal_to_the_default_is_accepted(self):
        record = assess_insulation_system(
            _insulation(), withstand_factor=DEFAULT_DIELECTRIC_WITHSTAND_FACTOR
        )
        self.assertAlmostEqual(record["required_withstand_v"], 240.0, places=9)

    def test_zero_working_voltage_rejected(self):
        with self.assertRaises(ValueError):
            assess_insulation_system(_insulation(working_voltage_v=0.0))


class ScreeningTests(unittest.TestCase):
    def test_complete_screening_leaves_nothing_absent(self):
        self.assertEqual(missing_screening_steps(list(MANDATORY_SCREENING)), [])

    def test_absent_step_is_named(self):
        absent = missing_screening_steps(["winding-visual-inspection"])
        self.assertIn("dielectric-withstand-test", absent)
        self.assertEqual(len(absent), len(MANDATORY_SCREENING) - 1)

    def test_no_declared_steps_names_every_required_step(self):
        self.assertEqual(
            len(missing_screening_steps(None)), len(MANDATORY_SCREENING)
        )

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            missing_screening_steps(
                ["thermal-vacuum-bakeout", "Thermal_Vacuum_Bakeout"]
            )

    def test_non_sequence_steps_rejected(self):
        with self.assertRaises(ValueError):
            missing_screening_steps("dielectric-withstand-test")


class MagneticAssessmentTests(unittest.TestCase):
    def test_complete_magnetic_is_fit_for_use(self):
        result = assess_self_made_magnetic(_record())
        self.assertTrue(result["fit_for_class_1_use"])
        self.assertEqual(result["findings"], [])

    def test_overloaded_winding_reaches_the_verdict(self):
        result = assess_self_made_magnetic(
            _record(windings=[_winding(rms_current_a=6.0)])
        )
        self.assertFalse(result["fit_for_class_1_use"])

    def test_repeated_winding_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_self_made_magnetic(_record(windings=[_winding(), _winding()]))

    def test_empty_winding_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_self_made_magnetic(_record(windings=[]))

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["core"]
        with self.assertRaises(ValueError):
            assess_self_made_magnetic(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_self_made_magnetic(["part"])

    def test_absent_screening_reaches_the_verdict(self):
        result = assess_self_made_magnetic(_record(screening_steps=[]))
        self.assertEqual(
            len(result["absent_screening_steps"]), len(MANDATORY_SCREENING)
        )
        self.assertFalse(result["fit_for_class_1_use"])

    def test_saturated_core_reaches_the_verdict(self):
        result = assess_self_made_magnetic(
            _record(core=_core(peak_flux_density_t=0.39))
        )
        self.assertFalse(result["fit_for_class_1_use"])

    def test_every_finding_is_named_not_only_the_first(self):
        result = assess_self_made_magnetic(
            _record(
                process_basis=dict(BASIS, operator_qualified=False),
                windings=[_winding(rms_current_a=6.0)],
                core=_core(peak_flux_density_t=0.39),
                insulation=_insulation(demonstrated_withstand_v=100.0),
                screening_steps=[],
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 10)

    def test_value_tolerance_is_representation_sized(self):
        self.assertLess(VALUE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
