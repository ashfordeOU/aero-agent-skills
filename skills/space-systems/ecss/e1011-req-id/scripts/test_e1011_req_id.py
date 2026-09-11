"""
Gate-3 contract tests for e1011_req_id_logic.py.

stdlib unittest only. Deterministic, offline. Run:
    python3 test_e1011_req_id.py
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory or from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from e1011_req_id_logic import (
    MANDATORY_DRIVERS,
    VALID_DRIVERS,
    VALID_PHASES,
    VALID_ROLES,
    ValidationError,
    check_completeness,
    check_uniqueness,
    generate_req_id,
    identify_requirements,
    run_identification,
    validate_driver,
    validate_phase,
    validate_req_id_format,
    validate_role,
)


class TestPhaseValidation(unittest.TestCase):
    def test_known_phase_returns_code(self):
        self.assertEqual(validate_phase("orbit"), "ORB")

    def test_all_valid_phases_accepted(self):
        for phase, code in VALID_PHASES.items():
            self.assertEqual(validate_phase(phase), code)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValidationError):
            validate_phase("cruise")

    def test_empty_string_phase_raises(self):
        with self.assertRaises(ValidationError):
            validate_phase("")


class TestRoleValidation(unittest.TestCase):
    def test_known_role_returns_code(self):
        self.assertEqual(validate_role("crew"), "CRW")

    def test_all_valid_roles_accepted(self):
        for role, code in VALID_ROLES.items():
            self.assertEqual(validate_role(role), code)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValidationError):
            validate_role("pilot")

    def test_empty_string_role_raises(self):
        with self.assertRaises(ValidationError):
            validate_role("")


class TestDriverValidation(unittest.TestCase):
    def test_known_driver_returns_code(self):
        self.assertEqual(validate_driver("safety"), "SAF")

    def test_all_valid_drivers_accepted(self):
        for driver, code in VALID_DRIVERS.items():
            self.assertEqual(validate_driver(driver), code)

    def test_unknown_driver_raises(self):
        with self.assertRaises(ValidationError):
            validate_driver("ergonomics")

    def test_mandatory_drivers_are_valid(self):
        for driver in MANDATORY_DRIVERS:
            code = validate_driver(driver)
            self.assertIsInstance(code, str)
            self.assertEqual(len(code), 3)


class TestReqIdFormat(unittest.TestCase):
    def test_well_formed_id_passes(self):
        self.assertTrue(validate_req_id_format("HFE-ORB-CRW-SAF-001"))

    def test_wrong_prefix_fails(self):
        self.assertFalse(validate_req_id_format("REQ-ORB-CRW-SAF-001"))

    def test_lowercase_fails(self):
        self.assertFalse(validate_req_id_format("HFE-orb-CRW-SAF-001"))

    def test_seq_too_long_fails(self):
        self.assertFalse(validate_req_id_format("HFE-ORB-CRW-SAF-0001"))

    def test_missing_seq_fails(self):
        self.assertFalse(validate_req_id_format("HFE-ORB-CRW-SAF"))

    def test_generated_id_passes_format(self):
        req_id = generate_req_id("orbit", "crew", "safety", 1)
        self.assertTrue(validate_req_id_format(req_id))


class TestGenerateReqId(unittest.TestCase):
    def test_basic_generation(self):
        req_id = generate_req_id("orbit", "crew", "workload", 1)
        self.assertEqual(req_id, "HFE-ORB-CRW-WKL-001")

    def test_seq_zero_padded(self):
        req_id = generate_req_id("launch", "commander", "safety", 7)
        self.assertEqual(req_id, "HFE-LCH-CMD-SAF-007")

    def test_seq_at_max(self):
        req_id = generate_req_id("landing", "maintainer", "visibility", 999)
        self.assertEqual(req_id, "HFE-LND-MNT-VIS-999")

    def test_seq_out_of_range_raises(self):
        with self.assertRaises(ValidationError):
            generate_req_id("orbit", "crew", "safety", 0)

    def test_seq_over_max_raises(self):
        with self.assertRaises(ValidationError):
            generate_req_id("orbit", "crew", "safety", 1000)

    def test_invalid_phase_in_generate_raises(self):
        with self.assertRaises(ValidationError):
            generate_req_id("docking", "crew", "safety", 1)

    def test_invalid_role_in_generate_raises(self):
        with self.assertRaises(ValidationError):
            generate_req_id("orbit", "observer", "safety", 1)

    def test_invalid_driver_in_generate_raises(self):
        with self.assertRaises(ValidationError):
            generate_req_id("orbit", "crew", "posture", 1)


class TestIdentifyRequirements(unittest.TestCase):
    def _minimal_input(self):
        phases = ["orbit"]
        roles = {"orbit": ["crew"]}
        drivers = {("orbit", "crew"): ["visibility"]}
        return phases, roles, drivers

    def test_mandatory_drivers_injected(self):
        phases, roles, drivers = self._minimal_input()
        reqs = identify_requirements(phases, roles, drivers)
        codes_present = {r.split("-")[3] for r in reqs}
        self.assertIn("SAF", codes_present)
        self.assertIn("WKL", codes_present)

    def test_explicit_driver_included(self):
        phases, roles, drivers = self._minimal_input()
        reqs = identify_requirements(phases, roles, drivers)
        codes_present = {r.split("-")[3] for r in reqs}
        self.assertIn("VIS", codes_present)

    def test_no_duplicate_drivers_in_output(self):
        phases = ["launch"]
        roles = {"launch": ["crew"]}
        # workload listed twice — should appear only once
        drivers = {("launch", "crew"): ["workload", "workload", "safety"]}
        reqs = identify_requirements(phases, roles, drivers)
        wkl_count = sum(1 for r in reqs if "WKL" in r)
        self.assertEqual(wkl_count, 1)

    def test_phase_with_no_roles_raises(self):
        with self.assertRaises(ValidationError):
            identify_requirements(["orbit"], {"orbit": []}, {})

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValidationError):
            identify_requirements(["docking"], {"docking": ["crew"]}, {})

    def test_unknown_role_raises(self):
        with self.assertRaises(ValidationError):
            identify_requirements(["orbit"], {"orbit": ["observer"]}, {})

    def test_unknown_driver_raises(self):
        with self.assertRaises(ValidationError):
            identify_requirements(
                ["orbit"],
                {"orbit": ["crew"]},
                {("orbit", "crew"): ["posture"]},
            )

    def test_multi_phase_multi_role(self):
        phases = ["launch", "orbit"]
        roles = {"launch": ["crew", "commander"], "orbit": ["crew"]}
        drivers = {}
        reqs = identify_requirements(phases, roles, drivers)
        # launch: 2 roles × 2 mandatory = 4; orbit: 1 role × 2 mandatory = 2
        self.assertEqual(len(reqs), 6)

    def test_all_ids_pass_format_check(self):
        phases = ["ascent", "landing"]
        roles = {"ascent": ["crew"], "landing": ["crew", "maintainer"]}
        drivers = {
            ("ascent", "crew"): ["cognitive", "communication"],
            ("landing", "crew"): ["visibility"],
            ("landing", "maintainer"): ["anthropometry"],
        }
        reqs = identify_requirements(phases, roles, drivers)
        for req_id in reqs:
            self.assertTrue(
                validate_req_id_format(req_id),
                f"Bad format: {req_id}",
            )


class TestCompletenessCheck(unittest.TestCase):
    def test_complete_set_returns_no_gaps(self):
        reqs = [
            "HFE-ORB-CRW-SAF-001",
            "HFE-ORB-CRW-WKL-002",
        ]
        gaps = check_completeness(reqs, ["orbit"])
        self.assertEqual(gaps, [])

    def test_missing_safety_flagged(self):
        reqs = ["HFE-ORB-CRW-WKL-001"]
        gaps = check_completeness(reqs, ["orbit"])
        self.assertTrue(any("safety" in g for g in gaps))

    def test_missing_workload_flagged(self):
        reqs = ["HFE-ORB-CRW-SAF-001"]
        gaps = check_completeness(reqs, ["orbit"])
        self.assertTrue(any("workload" in g for g in gaps))

    def test_both_missing_gives_two_gaps(self):
        reqs = ["HFE-ORB-CRW-VIS-001"]
        gaps = check_completeness(reqs, ["orbit"])
        self.assertEqual(len(gaps), 2)

    def test_unknown_phase_in_check_flagged(self):
        gaps = check_completeness([], ["docking"])
        self.assertTrue(any("docking" in g for g in gaps))


class TestUniquenessCheck(unittest.TestCase):
    def test_unique_set_returns_empty(self):
        reqs = ["HFE-ORB-CRW-SAF-001", "HFE-ORB-CRW-WKL-002"]
        self.assertEqual(check_uniqueness(reqs), [])

    def test_duplicate_detected(self):
        reqs = ["HFE-ORB-CRW-SAF-001", "HFE-ORB-CRW-SAF-001"]
        dups = check_uniqueness(reqs)
        self.assertEqual(len(dups), 1)
        self.assertIn("HFE-ORB-CRW-SAF-001", dups[0])

    def test_empty_list_is_unique(self):
        self.assertEqual(check_uniqueness([]), [])


class TestRunIdentificationPipeline(unittest.TestCase):
    def test_ready_flag_true_when_no_gaps_or_duplicates(self):
        result = run_identification(
            ["orbit"],
            {"orbit": ["crew"]},
            {("orbit", "crew"): ["visibility", "cognitive"]},
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["duplicates"], [])
        self.assertGreater(len(result["requirements"]), 0)

    def test_result_keys_present(self):
        result = run_identification(
            ["launch"],
            {"launch": ["crew"]},
            {},
        )
        for key in ("requirements", "gaps", "duplicates", "ready"):
            self.assertIn(key, result)

    def test_validation_error_propagates(self):
        with self.assertRaises(ValidationError):
            run_identification(
                ["unknown_phase"],
                {"unknown_phase": ["crew"]},
                {},
            )


if __name__ == "__main__":
    unittest.main()
