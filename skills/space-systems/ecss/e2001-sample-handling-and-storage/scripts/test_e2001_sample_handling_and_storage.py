#!/usr/bin/env python3
"""Gate 3 contract test for e2001-sample-handling-and-storage."""

import unittest

from e2001_sample_handling_and_storage_logic import (
    MAX_RELATIVE_HUMIDITY_PCT,
    MAX_WEIGHTED_EXPOSURE_HOURS,
    SEVERITY_NOTE,
    SEVERITY_RECLEAN,
    SEVERITY_WITHDRAW,
    STORAGE_TEMPERATURE_BAND_C,
    VERDICT_ADMISSIBLE,
    VERDICT_RECLEAN,
    VERDICT_WITHDRAWN,
    assess_sample_custody,
    audit_handling_steps,
    audit_transport,
    check_exposure,
    check_storage_environment,
    container_profile,
    environment_weight,
    format_custody_report,
    storage_age_days,
    validate_coupon_record,
    verdict_from_findings,
    weighted_air_exposure,
)


def coupon(**overrides):
    record = {
        "coupon_id": "CPN-0117",
        "material": "silver-plated aluminium 6061",
        "cleanliness_level": "visibly-clean level 2",
        "container": "purge-gas-container",
        "prepared_on": "2026-01-10",
        "dielectric": False,
    }
    record.update(overrides)
    return record


def environment(**overrides):
    env = {"purge_gas": "dry nitrogen", "relative_humidity_pct": 20.0,
           "temperature_c": 21.0}
    env.update(overrides)
    return env


def custody_events():
    return [
        {"activity": "surface preparation", "duration_hours": 2.0,
         "environment": "cleanroom-air"},
        {"activity": "container loading", "duration_hours": 0.5,
         "environment": "cleanroom-air"},
        {"activity": "storage", "duration_hours": 300.0, "environment": "purge-gas"},
        {"activity": "bench load", "duration_hours": 1.0,
         "environment": "cleanroom-air"},
    ]


def handling_steps(**overrides):
    step = {"step": "transfer to holder", "gloves": "powder-free-nitrile",
            "tool_material": "ptfe-tipped-tweezers", "esd_control": True}
    step.update(overrides)
    return [{"step": "unpack", "gloves": "cleanroom-vinyl", "esd_control": True}, step]


def transport_leg(**overrides):
    leg = {"seal_intact": True, "transit_hours": 12.0, "shock_monitored": True}
    leg.update(overrides)
    return leg


RUN_DAY = "2026-02-10"


class TestCouponRecord(unittest.TestCase):
    def test_valid_record_is_normalised(self):
        record = validate_coupon_record(coupon(coupon_id="  CPN-0117 "))
        self.assertEqual(record["coupon_id"], "CPN-0117")
        self.assertFalse(record["dielectric"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_record("CPN-0117")

    def test_missing_identifier_raises(self):
        record = coupon()
        del record["coupon_id"]
        with self.assertRaises(ValueError):
            validate_coupon_record(record)

    def test_blank_material_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_record(coupon(material="  "))

    def test_unrecognised_container_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_record(coupon(container="cardboard-box"))

    def test_malformed_preparation_date_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_record(coupon(prepared_on="10/01/2026"))

    def test_non_boolean_dielectric_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_record(coupon(dielectric="yes"))

    def test_container_profile_is_a_copy(self):
        profile = container_profile("sealed-double-bag")
        profile["storage_life_days"] = 9999
        self.assertEqual(container_profile("sealed-double-bag")["storage_life_days"], 90)

    def test_unknown_container_profile_raises(self):
        with self.assertRaises(ValueError):
            container_profile("shoebox")


class TestStorageAge(unittest.TestCase):
    def test_age_in_whole_days(self):
        self.assertEqual(storage_age_days("2026-01-10", RUN_DAY), 31)

    def test_run_before_preparation_raises(self):
        with self.assertRaises(ValueError):
            storage_age_days("2026-03-10", RUN_DAY)

    def test_impossible_calendar_date_raises(self):
        with self.assertRaises(ValueError):
            storage_age_days("2026-02-31", RUN_DAY)


class TestStorageEnvironment(unittest.TestCase):
    def test_compliant_environment_has_no_finding(self):
        self.assertEqual(
            check_storage_environment("purge-gas-container", environment(), 31.0), [])

    def test_missing_purge_gas_withdraws(self):
        findings = check_storage_environment("purge-gas-container",
                                             environment(purge_gas=""), 31.0)
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_WITHDRAW])

    def test_container_not_needing_purge_gas_is_unaffected(self):
        findings = check_storage_environment("sealed-double-bag",
                                             environment(purge_gas=""), 31.0)
        self.assertEqual(findings, [])

    def test_humidity_above_the_allowance_demands_recleaning(self):
        findings = check_storage_environment("purge-gas-container",
                                             environment(relative_humidity_pct=62.0),
                                             31.0)
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_RECLEAN])

    def test_humidity_exactly_at_the_allowance_passes(self):
        findings = check_storage_environment(
            "purge-gas-container",
            environment(relative_humidity_pct=MAX_RELATIVE_HUMIDITY_PCT), 31.0)
        self.assertEqual(findings, [])

    def test_temperature_below_the_band_demands_recleaning(self):
        findings = check_storage_environment("purge-gas-container",
                                             environment(temperature_c=4.0), 31.0)
        self.assertTrue(any("outside the" in f["message"] for f in findings))

    def test_temperature_exactly_at_the_band_edges_passes(self):
        low, high = STORAGE_TEMPERATURE_BAND_C
        self.assertEqual(check_storage_environment("purge-gas-container",
                                                   environment(temperature_c=low),
                                                   31.0), [])
        self.assertEqual(check_storage_environment("purge-gas-container",
                                                   environment(temperature_c=high),
                                                   31.0), [])

    def test_storage_beyond_the_container_life_demands_recleaning(self):
        findings = check_storage_environment("sealed-double-bag", environment(), 120.0)
        self.assertTrue(any("storage-life" in f["message"] for f in findings))

    def test_storage_exactly_at_the_container_life_passes(self):
        self.assertEqual(
            check_storage_environment("sealed-double-bag", environment(), 90.0), [])

    def test_out_of_range_humidity_raises(self):
        with self.assertRaises(ValueError):
            check_storage_environment("purge-gas-container",
                                      environment(relative_humidity_pct=140.0), 31.0)

    def test_non_mapping_environment_raises(self):
        with self.assertRaises(ValueError):
            check_storage_environment("purge-gas-container", "dry nitrogen", 31.0)

    def test_negative_storage_days_raises(self):
        with self.assertRaises(ValueError):
            check_storage_environment("purge-gas-container", environment(), -1.0)


class TestWeightedExposure(unittest.TestCase):
    def test_purge_and_vacuum_time_costs_nothing(self):
        self.assertAlmostEqual(environment_weight("purge-gas"), 0.0)
        self.assertAlmostEqual(environment_weight("vacuum-chamber"), 0.0)

    def test_uncontrolled_air_costs_a_multiple_of_cleanroom_air(self):
        self.assertGreater(environment_weight("uncontrolled-air"),
                           environment_weight("cleanroom-air"))

    def test_nominal_custody_accumulates_only_cleanroom_hours(self):
        result = weighted_air_exposure(custody_events())
        self.assertAlmostEqual(result["weighted_hours"], 3.5)
        self.assertEqual(len(result["breakdown"]), 4)

    def test_uncontrolled_air_is_weighted_up(self):
        result = weighted_air_exposure([{"activity": "bench wait",
                                         "duration_hours": 2.0,
                                         "environment": "uncontrolled-air"}])
        self.assertAlmostEqual(result["weighted_hours"], 6.0)

    def test_empty_event_list_accumulates_nothing(self):
        self.assertAlmostEqual(weighted_air_exposure([])["weighted_hours"], 0.0)

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            weighted_air_exposure([{"activity": "transfer", "duration_hours": 1.0,
                                    "environment": "loading-dock"}])

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            weighted_air_exposure([{"activity": "transfer", "duration_hours": -1.0,
                                    "environment": "cleanroom-air"}])

    def test_event_without_activity_raises(self):
        with self.assertRaises(ValueError):
            weighted_air_exposure([{"duration_hours": 1.0,
                                    "environment": "cleanroom-air"}])

    def test_non_mapping_event_raises(self):
        with self.assertRaises(ValueError):
            weighted_air_exposure(["1 hour in cleanroom-air"])


class TestExposureAllowance(unittest.TestCase):
    def test_exposure_under_the_allowance_has_no_finding(self):
        self.assertEqual(check_exposure(3.5), [])

    def test_exposure_over_the_allowance_demands_recleaning(self):
        findings = check_exposure(40.0)
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_RECLEAN])

    def test_weighted_total_landing_a_few_ulps_over_the_allowance_passes(self):
        total = weighted_air_exposure([
            {"activity": "preparation", "duration_hours": 0.3,
             "environment": "cleanroom-air"},
            {"activity": "open-bench transfer", "duration_hours": 7.9,
             "environment": "uncontrolled-air"},
        ])["weighted_hours"]
        self.assertGreater(total, MAX_WEIGHTED_EXPOSURE_HOURS)  # bare <= would fail
        self.assertEqual(check_exposure(total), [])

    def test_negative_total_raises(self):
        with self.assertRaises(ValueError):
            check_exposure(-1.0)

    def test_non_positive_allowance_raises(self):
        with self.assertRaises(ValueError):
            check_exposure(1.0, allowance=0.0)


class TestHandlingSteps(unittest.TestCase):
    def test_compliant_steps_have_no_finding(self):
        self.assertEqual(audit_handling_steps(handling_steps()), [])

    def test_bare_hand_contact_withdraws_the_coupon(self):
        findings = audit_handling_steps(handling_steps(gloves="bare-hand"))
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_WITHDRAW])

    def test_unapproved_glove_demands_recleaning(self):
        findings = audit_handling_steps(handling_steps(gloves="powdered-latex"))
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_RECLEAN])

    def test_unapproved_tool_material_demands_recleaning(self):
        findings = audit_handling_steps(handling_steps(tool_material="brass-pliers"))
        self.assertTrue(any("tool-material" in f["message"] for f in findings))

    def test_dielectric_coupon_without_esd_control_is_withdrawn(self):
        findings = audit_handling_steps(handling_steps(esd_control=False),
                                        dielectric=True)
        self.assertIn(SEVERITY_WITHDRAW, [f["severity"] for f in findings])

    def test_dielectric_coupon_with_esd_control_passes(self):
        self.assertEqual(audit_handling_steps(handling_steps(), dielectric=True), [])

    def test_conductive_coupon_without_esd_control_passes(self):
        self.assertEqual(
            audit_handling_steps([{"step": "unpack", "gloves": "cleanroom-vinyl"}]), [])

    def test_empty_step_list_raises(self):
        with self.assertRaises(ValueError):
            audit_handling_steps([])

    def test_step_without_glove_record_raises(self):
        with self.assertRaises(ValueError):
            audit_handling_steps([{"step": "unpack"}])

    def test_non_boolean_esd_flag_raises(self):
        with self.assertRaises(ValueError):
            audit_handling_steps(handling_steps(esd_control="yes"))

    def test_non_mapping_step_raises(self):
        with self.assertRaises(ValueError):
            audit_handling_steps(["unpack with nitrile gloves"])


class TestTransportLeg(unittest.TestCase):
    def test_compliant_leg_has_no_finding(self):
        self.assertEqual(audit_transport(transport_leg(), "purge-gas-container"), [])

    def test_broken_seal_withdraws_a_sealed_container(self):
        findings = audit_transport(transport_leg(seal_intact=False),
                                   "purge-gas-container")
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_WITHDRAW])

    def test_vented_case_does_not_rely_on_a_seal(self):
        findings = audit_transport(transport_leg(seal_intact=False),
                                   "vented-transit-case")
        self.assertNotIn(SEVERITY_WITHDRAW, [f["severity"] for f in findings])

    def test_unmonitored_transit_in_an_open_container_is_a_note(self):
        findings = audit_transport(transport_leg(shock_monitored=False),
                                   "sealed-double-bag")
        self.assertEqual([f["severity"] for f in findings], [SEVERITY_NOTE])

    def test_over_long_transit_demands_recleaning(self):
        findings = audit_transport(transport_leg(transit_hours=200.0),
                                   "purge-gas-container")
        self.assertTrue(any("transit duration" in f["message"] for f in findings))

    def test_transit_exactly_at_the_limit_passes(self):
        self.assertEqual(audit_transport(transport_leg(transit_hours=72.0),
                                         "purge-gas-container"), [])

    def test_missing_seal_record_raises(self):
        leg = transport_leg()
        del leg["seal_intact"]
        with self.assertRaises(ValueError):
            audit_transport(leg, "purge-gas-container")

    def test_negative_transit_hours_raises(self):
        with self.assertRaises(ValueError):
            audit_transport(transport_leg(transit_hours=-4.0), "purge-gas-container")


class TestVerdict(unittest.TestCase):
    def test_no_finding_is_admissible(self):
        self.assertEqual(verdict_from_findings([]), VERDICT_ADMISSIBLE)

    def test_note_alone_stays_admissible(self):
        self.assertEqual(
            verdict_from_findings([{"severity": SEVERITY_NOTE, "message": "n"}]),
            VERDICT_ADMISSIBLE)

    def test_reclean_finding_demands_recleaning(self):
        self.assertEqual(
            verdict_from_findings([{"severity": SEVERITY_NOTE, "message": "n"},
                                   {"severity": SEVERITY_RECLEAN, "message": "r"}]),
            VERDICT_RECLEAN)

    def test_withdraw_outranks_reclean(self):
        self.assertEqual(
            verdict_from_findings([{"severity": SEVERITY_RECLEAN, "message": "r"},
                                   {"severity": SEVERITY_WITHDRAW, "message": "w"}]),
            VERDICT_WITHDRAWN)

    def test_unrecognised_severity_raises(self):
        with self.assertRaises(ValueError):
            verdict_from_findings([{"severity": "fatal", "message": "x"}])


class TestFullCustodyAudit(unittest.TestCase):
    def _assess(self, **overrides):
        kwargs = {"coupon": coupon(), "environment": environment(),
                  "events": custody_events(), "handling_steps": handling_steps(),
                  "transport_leg": transport_leg(), "run_on": RUN_DAY}
        kwargs.update(overrides)
        return assess_sample_custody(kwargs["coupon"], kwargs["environment"],
                                     kwargs["events"], kwargs["handling_steps"],
                                     kwargs["transport_leg"], kwargs["run_on"])

    def test_nominal_custody_is_admissible(self):
        result = self._assess()
        self.assertEqual(result["verdict"], VERDICT_ADMISSIBLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["storage_age_days"], 31)
        self.assertAlmostEqual(result["weighted_exposure_hours"], 3.5)

    def test_humidity_drift_is_recoverable_by_recleaning(self):
        result = self._assess(environment=environment(relative_humidity_pct=70.0))
        self.assertEqual(result["verdict"], VERDICT_RECLEAN)

    def test_bare_hand_contact_withdraws_the_coupon(self):
        result = self._assess(handling_steps=handling_steps(gloves="bare-hand"))
        self.assertEqual(result["verdict"], VERDICT_WITHDRAWN)

    def test_long_uncontrolled_exposure_demands_recleaning(self):
        events = custody_events() + [{"activity": "open-bench wait",
                                      "duration_hours": 20.0,
                                      "environment": "uncontrolled-air"}]
        result = self._assess(events=events)
        self.assertEqual(result["verdict"], VERDICT_RECLEAN)
        self.assertAlmostEqual(result["weighted_exposure_hours"], 63.5)

    def test_storage_beyond_the_container_life_demands_recleaning(self):
        result = self._assess(coupon=coupon(container="vented-transit-case"))
        self.assertEqual(result["verdict"], VERDICT_RECLEAN)

    def test_report_carries_verdict_exposure_and_findings(self):
        lines = format_custody_report(
            self._assess(handling_steps=handling_steps(gloves="powdered-latex")))
        self.assertTrue(lines[0].startswith("ECSS-E-ST-20-01C clause 9.4.1.1"))
        self.assertTrue(any("weighted ambient-air exposure" in line for line in lines))
        self.assertTrue(any(line.startswith("  [%s]" % SEVERITY_RECLEAN)
                            for line in lines))

    def test_clean_report_states_that_no_defect_was_recorded(self):
        lines = format_custody_report(self._assess())
        self.assertIn("  no custody defect recorded", lines)

    def test_report_rejects_a_non_result(self):
        with self.assertRaises(ValueError):
            format_custody_report({"outcome": "fine"})


if __name__ == "__main__":
    unittest.main()
