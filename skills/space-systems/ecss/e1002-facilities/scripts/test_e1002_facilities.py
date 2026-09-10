import unittest

from e1002_facilities_logic import (
    check_calibration_currency,
    check_capability_envelope,
    check_plan_completeness,
    check_qc_accreditation,
    check_tool_interface_compatibility,
    qualify_facility,
    qualify_tool,
    required_facility_type_for_method,
    roll_up_ait_readiness,
    validate_facility_type,
    validate_tool_type,
)


class TestMethodMapping(unittest.TestCase):
    def test_thermal_vacuum_method_maps_to_thermal_vacuum_facility(self):
        self.assertEqual(
            required_facility_type_for_method("thermal-vacuum"), "thermal-vacuum"
        )

    def test_random_vibration_maps_to_vibration_facility(self):
        self.assertEqual(
            required_facility_type_for_method("random-vibration"), "vibration"
        )

    def test_unknown_test_method_is_rejected(self):
        with self.assertRaises(ValueError):
            required_facility_type_for_method("shock-tube")


class TestTypeValidation(unittest.TestCase):
    def test_known_facility_type_passes(self):
        validate_facility_type("clean-room")  # should not raise

    def test_unknown_facility_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility_type("wind-tunnel")

    def test_unknown_tool_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool_type("laser-tracker")


class TestCapabilityEnvelope(unittest.TestCase):
    def test_facility_envelope_covers_requirement(self):
        self.assertTrue(check_capability_envelope(-40, 80, -60, 100))

    def test_facility_envelope_matches_requirement_exactly(self):
        self.assertTrue(check_capability_envelope(-40, 80, -40, 80))

    def test_facility_envelope_falls_short_at_upper_bound(self):
        self.assertFalse(check_capability_envelope(-40, 80, -60, 70))

    def test_facility_envelope_falls_short_at_lower_bound(self):
        self.assertFalse(check_capability_envelope(-40, 80, -30, 100))

    def test_inverted_required_range_is_rejected(self):
        with self.assertRaises(ValueError):
            check_capability_envelope(80, -40, -60, 100)

    def test_inverted_facility_range_is_rejected(self):
        with self.assertRaises(ValueError):
            check_capability_envelope(-40, 80, 100, -60)


class TestCalibrationCurrency(unittest.TestCase):
    def test_freshly_calibrated_asset_is_current(self):
        result = check_calibration_currency(100, 365, 100)
        self.assertTrue(result["current"])
        self.assertEqual(result["days_remaining"], 365)

    def test_asset_at_interval_boundary_is_still_current(self):
        result = check_calibration_currency(100, 365, 465)
        self.assertTrue(result["current"])
        self.assertEqual(result["days_remaining"], 0)

    def test_asset_one_day_past_interval_is_expired(self):
        result = check_calibration_currency(100, 365, 466)
        self.assertFalse(result["current"])
        self.assertEqual(result["days_remaining"], -1)

    def test_nonpositive_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            check_calibration_currency(100, 0, 100)

    def test_current_day_before_last_calibration_is_rejected(self):
        with self.assertRaises(ValueError):
            check_calibration_currency(200, 365, 100)


class TestQcAccreditation(unittest.TestCase):
    def test_accredited_against_q_st_20_07_passes(self):
        self.assertTrue(check_qc_accreditation("accredited", "q-st-20-07"))

    def test_accredited_against_other_standard_fails(self):
        self.assertFalse(check_qc_accreditation("accredited", "iso-17025"))

    def test_provisional_status_fails(self):
        self.assertFalse(check_qc_accreditation("provisional", "q-st-20-07"))

    def test_expired_status_fails(self):
        self.assertFalse(check_qc_accreditation("expired", "q-st-20-07"))

    def test_unknown_status_is_rejected(self):
        with self.assertRaises(ValueError):
            check_qc_accreditation("self-certified", "q-st-20-07")


class TestToolInterfaceCompatibility(unittest.TestCase):
    def test_tool_covering_all_required_interfaces_is_compatible(self):
        compatible, missing = check_tool_interface_compatibility(
            {"db25", "lemo-00", "ethernet"}, {"db25", "ethernet"}
        )
        self.assertTrue(compatible)
        self.assertEqual(missing, set())

    def test_tool_missing_a_required_interface_is_incompatible(self):
        compatible, missing = check_tool_interface_compatibility(
            {"db25"}, {"db25", "ethernet"}
        )
        self.assertFalse(compatible)
        self.assertEqual(missing, {"ethernet"})


class TestQualifyFacility(unittest.TestCase):
    def _facility(self, **overrides):
        base = {
            "type": "thermal-vacuum",
            "capability_min": -60,
            "capability_max": 100,
            "accreditation_status": "accredited",
            "accreditation_standard": "q-st-20-07",
            "last_calibration_day": 100,
            "calibration_interval_days": 365,
        }
        base.update(overrides)
        return base

    def test_fully_compliant_facility_is_qualified(self):
        result = qualify_facility(
            self._facility(), {"min": -40, "max": 80}, current_day=200
        )
        self.assertEqual(result, {"status": "qualified", "findings": []})

    def test_facility_with_narrow_envelope_is_not_qualified(self):
        result = qualify_facility(
            self._facility(capability_max=50), {"min": -40, "max": 80},
            current_day=200,
        )
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("capability-envelope-insufficient", result["findings"])

    def test_facility_missing_accreditation_is_not_qualified(self):
        result = qualify_facility(
            self._facility(accreditation_status="expired"),
            {"min": -40, "max": 80},
            current_day=200,
        )
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("qc-accreditation-missing", result["findings"])

    def test_facility_with_expired_calibration_is_not_qualified(self):
        result = qualify_facility(
            self._facility(), {"min": -40, "max": 80}, current_day=1000
        )
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("calibration-expired", result["findings"])

    def test_facility_can_fail_on_multiple_findings_at_once(self):
        result = qualify_facility(
            self._facility(capability_max=50, accreditation_status="expired"),
            {"min": -40, "max": 80},
            current_day=200,
        )
        self.assertEqual(
            set(result["findings"]),
            {"capability-envelope-insufficient", "qc-accreditation-missing"},
        )

    def test_unknown_facility_type_is_rejected(self):
        with self.assertRaises(ValueError):
            qualify_facility(
                self._facility(type="wind-tunnel"),
                {"min": -40, "max": 80},
                current_day=200,
            )


class TestQualifyTool(unittest.TestCase):
    def test_compatible_mechanical_gse_is_qualified(self):
        tool = {"type": "mechanical-gse", "interfaces": {"db25", "ethernet"}}
        result = qualify_tool(tool, {"db25"}, current_day=200)
        self.assertEqual(result, {"status": "qualified", "findings": []})

    def test_incompatible_tool_interfaces_is_not_qualified(self):
        tool = {"type": "mechanical-gse", "interfaces": {"db25"}}
        result = qualify_tool(tool, {"db25", "ethernet"}, current_day=200)
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("interface-incompatible", result["findings"])

    def test_measurement_instrument_requires_current_calibration(self):
        tool = {
            "type": "measurement-instrument",
            "interfaces": {"db25"},
            "last_calibration_day": 100,
            "calibration_interval_days": 365,
        }
        result = qualify_tool(tool, {"db25"}, current_day=1000)
        self.assertEqual(result["status"], "not-qualified")
        self.assertIn("calibration-expired", result["findings"])

    def test_non_measurement_tool_is_not_calibration_checked(self):
        tool = {"type": "handling-equipment", "interfaces": {"crane-hook"}}
        result = qualify_tool(tool, {"crane-hook"}, current_day=99999)
        self.assertEqual(result, {"status": "qualified", "findings": []})


class TestPlanCompleteness(unittest.TestCase):
    def test_complete_plan_has_no_missing_fields(self):
        plan = {
            "facility_id": "tvac-1",
            "requirement_ref": "req-042",
            "capability_check": True,
            "calibration_check": True,
            "accreditation_check": True,
            "qualification_date": "2026-01-15",
        }
        self.assertEqual(check_plan_completeness(plan), set())

    def test_incomplete_plan_reports_missing_fields(self):
        plan = {"facility_id": "tvac-1", "requirement_ref": "req-042"}
        missing = check_plan_completeness(plan)
        self.assertEqual(
            missing,
            {"capability_check", "calibration_check", "accreditation_check",
             "qualification_date"},
        )


class TestRollUpAitReadiness(unittest.TestCase):
    def test_all_qualified_results_in_ready_gate(self):
        results = [
            {"status": "qualified", "findings": []},
            {"status": "qualified", "findings": []},
        ]
        self.assertEqual(
            roll_up_ait_readiness(results), {"ready": True, "blocking_count": 0}
        )

    def test_a_single_blocking_result_holds_the_gate(self):
        results = [
            {"status": "qualified", "findings": []},
            {"status": "not-qualified", "findings": ["calibration-expired"]},
        ]
        self.assertEqual(
            roll_up_ait_readiness(results), {"ready": False, "blocking_count": 1}
        )

    def test_empty_result_set_is_rejected(self):
        with self.assertRaises(ValueError):
            roll_up_ait_readiness([])


if __name__ == "__main__":
    unittest.main()
