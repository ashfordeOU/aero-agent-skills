"""
Offline deterministic contract tests for e1011_org_env_logic.
Run: python3 test_e1011_org_env.py
"""
import unittest
from e1011_org_env_logic import (
    validate_crew_role,
    check_commander_present,
    check_duplicate_titles,
    validate_ground_unit,
    check_mandatory_ground_functions,
    validate_procedure_entry,
    assess_org_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _crew_role(title="Commander", responsibility="Overall mission authority",
               authority_level="commander"):
    return {"title": title, "responsibility": responsibility,
            "authority_level": authority_level}


def _ground_unit(unit_name="MCC", function="flight-control",
                 interface_type="direct-voice"):
    return {"unit_name": unit_name, "function": function,
            "interface_type": interface_type}


def _procedure(proc_type="nominal", approval_authority="Flight Director",
               review_cycle_days=180):
    return {"proc_type": proc_type, "approval_authority": approval_authority,
            "review_cycle_days": review_cycle_days}


def _full_org_env():
    return {
        "crew_roles": [
            _crew_role("Commander", "Lead crew operations", "commander"),
            _crew_role("Flight Engineer", "Manage onboard systems", "crew-member"),
        ],
        "ground_units": [
            _ground_unit("MCC-H", "flight-control", "direct-voice"),
            _ground_unit("SysMon", "systems-monitoring", "data-link"),
            _ground_unit("CrewSupport", "crew-support", "video"),
        ],
        "procedures": [
            _procedure("nominal", "Flight Director", 180),
            _procedure("contingency", "Flight Director", 90),
            _procedure("emergency", "Commander", 60),
        ],
    }


# ---------------------------------------------------------------------------
# validate_crew_role
# ---------------------------------------------------------------------------

class TestValidateCrewRole(unittest.TestCase):

    def test_valid_entry_returns_no_errors(self):
        self.assertEqual(validate_crew_role(_crew_role()), [])

    def test_missing_title_is_reported(self):
        errors = validate_crew_role(_crew_role(title=""))
        self.assertTrue(any("title" in e for e in errors), errors)

    def test_missing_responsibility_is_reported(self):
        errors = validate_crew_role(_crew_role(responsibility=""))
        self.assertTrue(any("responsibility" in e for e in errors), errors)

    def test_missing_authority_level_is_reported(self):
        errors = validate_crew_role(_crew_role(authority_level=""))
        self.assertTrue(any("authority_level" in e for e in errors), errors)

    def test_unknown_authority_level_is_reported(self):
        errors = validate_crew_role(_crew_role(authority_level="overlord"))
        self.assertTrue(any("authority_level" in e for e in errors), errors)

    def test_all_valid_authority_levels_accepted(self):
        for level in ("commander", "crew-member", "specialist", "observer"):
            with self.subTest(level=level):
                self.assertEqual(
                    validate_crew_role(_crew_role(authority_level=level)), []
                )


# ---------------------------------------------------------------------------
# check_commander_present
# ---------------------------------------------------------------------------

class TestCheckCommanderPresent(unittest.TestCase):

    def test_commander_role_present_returns_true(self):
        roles = [_crew_role(authority_level="commander")]
        self.assertTrue(check_commander_present(roles))

    def test_no_commander_role_returns_false(self):
        roles = [_crew_role(authority_level="crew-member")]
        self.assertFalse(check_commander_present(roles))

    def test_empty_crew_list_returns_false(self):
        self.assertFalse(check_commander_present([]))

    def test_commander_found_among_multiple_roles(self):
        roles = [
            _crew_role("Engineer", authority_level="crew-member"),
            _crew_role("Commander", authority_level="commander"),
            _crew_role("Specialist", authority_level="specialist"),
        ]
        self.assertTrue(check_commander_present(roles))


# ---------------------------------------------------------------------------
# check_duplicate_titles
# ---------------------------------------------------------------------------

class TestCheckDuplicateTitles(unittest.TestCase):

    def test_unique_titles_returns_empty(self):
        roles = [_crew_role("Commander"), _crew_role("Engineer")]
        self.assertEqual(check_duplicate_titles(roles), [])

    def test_duplicate_title_detected(self):
        roles = [_crew_role("Commander"), _crew_role("Commander")]
        self.assertIn("Commander", check_duplicate_titles(roles))

    def test_three_instances_of_same_title_reported_once(self):
        roles = [_crew_role("Pilot"), _crew_role("Pilot"), _crew_role("Pilot")]
        dups = check_duplicate_titles(roles)
        self.assertEqual(dups.count("Pilot"), 1)


# ---------------------------------------------------------------------------
# validate_ground_unit
# ---------------------------------------------------------------------------

class TestValidateGroundUnit(unittest.TestCase):

    def test_valid_entry_returns_no_errors(self):
        self.assertEqual(validate_ground_unit(_ground_unit()), [])

    def test_missing_unit_name_is_reported(self):
        errors = validate_ground_unit(_ground_unit(unit_name=""))
        self.assertTrue(any("unit_name" in e for e in errors), errors)

    def test_missing_function_is_reported(self):
        errors = validate_ground_unit(_ground_unit(function=""))
        self.assertTrue(any("function" in e for e in errors), errors)

    def test_missing_interface_type_is_reported(self):
        errors = validate_ground_unit(_ground_unit(interface_type=""))
        self.assertTrue(any("interface_type" in e for e in errors), errors)

    def test_unknown_interface_type_is_reported(self):
        errors = validate_ground_unit(_ground_unit(interface_type="telepathy"))
        self.assertTrue(any("interface_type" in e for e in errors), errors)

    def test_all_valid_interface_types_accepted(self):
        for itype in ("direct-voice", "data-link", "video", "text", "indirect"):
            with self.subTest(itype=itype):
                self.assertEqual(
                    validate_ground_unit(_ground_unit(interface_type=itype)), []
                )


# ---------------------------------------------------------------------------
# check_mandatory_ground_functions
# ---------------------------------------------------------------------------

class TestCheckMandatoryGroundFunctions(unittest.TestCase):

    def test_all_mandatory_functions_covered_returns_empty(self):
        units = [
            _ground_unit(function="flight-control"),
            _ground_unit(function="systems-monitoring"),
            _ground_unit(function="crew-support"),
        ]
        self.assertEqual(check_mandatory_ground_functions(units), [])

    def test_missing_flight_control_is_flagged(self):
        units = [
            _ground_unit(function="systems-monitoring"),
            _ground_unit(function="crew-support"),
        ]
        self.assertIn("flight-control", check_mandatory_ground_functions(units))

    def test_missing_systems_monitoring_is_flagged(self):
        units = [
            _ground_unit(function="flight-control"),
            _ground_unit(function="crew-support"),
        ]
        self.assertIn("systems-monitoring", check_mandatory_ground_functions(units))

    def test_missing_crew_support_is_flagged(self):
        units = [
            _ground_unit(function="flight-control"),
            _ground_unit(function="systems-monitoring"),
        ]
        self.assertIn("crew-support", check_mandatory_ground_functions(units))

    def test_empty_units_returns_all_three_mandatory_functions(self):
        missing = check_mandatory_ground_functions([])
        self.assertEqual(len(missing), 3)


# ---------------------------------------------------------------------------
# validate_procedure_entry
# ---------------------------------------------------------------------------

class TestValidateProcedureEntry(unittest.TestCase):

    def test_valid_entry_returns_no_errors(self):
        self.assertEqual(validate_procedure_entry(_procedure()), [])

    def test_missing_approval_authority_is_reported(self):
        errors = validate_procedure_entry(_procedure(approval_authority=""))
        self.assertTrue(any("approval_authority" in e for e in errors), errors)

    def test_missing_proc_type_is_reported(self):
        errors = validate_procedure_entry(_procedure(proc_type=""))
        self.assertTrue(any("proc_type" in e for e in errors), errors)

    def test_unknown_proc_type_is_reported(self):
        errors = validate_procedure_entry(_procedure(proc_type="ultra-secret-op"))
        self.assertTrue(any("proc_type" in e for e in errors), errors)

    def test_negative_review_cycle_days_is_reported(self):
        errors = validate_procedure_entry(_procedure(review_cycle_days=-5))
        self.assertTrue(any("review_cycle_days" in e for e in errors), errors)

    def test_zero_review_cycle_days_is_reported(self):
        errors = validate_procedure_entry(_procedure(review_cycle_days=0))
        self.assertTrue(any("review_cycle_days" in e for e in errors), errors)

    def test_review_cycle_days_none_is_allowed(self):
        proc = _procedure()
        proc.pop("review_cycle_days")
        self.assertEqual(validate_procedure_entry(proc), [])

    def test_all_valid_proc_types_accepted(self):
        for ptype in ("nominal", "contingency", "emergency", "maintenance", "handover"):
            with self.subTest(ptype=ptype):
                self.assertEqual(
                    validate_procedure_entry(_procedure(proc_type=ptype)), []
                )


# ---------------------------------------------------------------------------
# assess_org_env
# ---------------------------------------------------------------------------

class TestAssessOrgEnv(unittest.TestCase):

    def test_complete_org_env_is_compliant(self):
        result = assess_org_env(_full_org_env())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_missing_commander_role_is_noncompliant(self):
        env = _full_org_env()
        env["crew_roles"] = [_crew_role("Engineer", "Systems", "crew-member")]
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("commander" in f for f in result["findings"]), result["findings"])

    def test_missing_mandatory_ground_function_is_noncompliant(self):
        env = _full_org_env()
        env["ground_units"] = [_ground_unit(function="flight-control")]
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("mandatory ground function" in f for f in result["findings"]),
            result["findings"],
        )

    def test_procedure_without_approval_authority_is_noncompliant(self):
        env = _full_org_env()
        env["procedures"] = [_procedure(approval_authority="")]
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("approval_authority" in f for f in result["findings"]),
            result["findings"],
        )

    def test_empty_ground_units_is_noncompliant(self):
        env = _full_org_env()
        env["ground_units"] = []
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("no ground support" in f for f in result["findings"]),
            result["findings"],
        )

    def test_duplicate_crew_titles_is_noncompliant(self):
        env = _full_org_env()
        env["crew_roles"].append(_crew_role("Commander", "Backup authority", "crew-member"))
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("duplicate" in f for f in result["findings"]),
            result["findings"],
        )

    def test_invalid_crew_role_authority_level_is_noncompliant(self):
        env = _full_org_env()
        env["crew_roles"][1]["authority_level"] = "unknown-rank"
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])

    def test_invalid_ground_unit_interface_type_is_noncompliant(self):
        env = _full_org_env()
        env["ground_units"][0]["interface_type"] = "morse-code"
        result = assess_org_env(env)
        self.assertFalse(result["compliant"])

    def test_result_always_has_compliant_and_findings_keys(self):
        result = assess_org_env({})
        self.assertIn("compliant", result)
        self.assertIn("findings", result)
        self.assertIsInstance(result["compliant"], bool)
        self.assertIsInstance(result["findings"], list)

    def test_empty_input_is_noncompliant(self):
        result = assess_org_env({})
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)


if __name__ == "__main__":
    unittest.main()
