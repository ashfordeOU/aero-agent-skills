"""
Contract tests for mission_lifetime_environment_spec_logic.
Run: python3 test_mission_lifetime_environment_spec.py
stdlib unittest only — offline, deterministic.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mission_lifetime_environment_spec_logic import (
    EnvironmentEntry,
    MissionLifetimeSpec,
    categorize_environment_family,
    validate_lifetime_margins,
    MIN_QUALIFICATION_FACTOR,
    MIN_ACCEPTANCE_FACTOR,
    REQUIRED_ENVIRONMENT_FAMILIES,
)


def _make_entry(family="thermal", category="natural", phases=None, quantified=True):
    if phases is None:
        phases = ["on_orbit"]
    return EnvironmentEntry(family=family, category=category, phases=phases, quantified=quantified)


class TestMissionLifetimeSpecCreation(unittest.TestCase):

    def test_valid_spec_stores_design_lifetime(self):
        spec = MissionLifetimeSpec(design_lifetime_years=10.0)
        self.assertAlmostEqual(spec.design_lifetime_years, 10.0)

    def test_qualification_lifetime_is_design_times_factor(self):
        spec = MissionLifetimeSpec(design_lifetime_years=10.0, qualification_factor=1.5)
        self.assertAlmostEqual(spec.qualification_lifetime_years, 15.0)

    def test_acceptance_lifetime_is_design_times_factor(self):
        spec = MissionLifetimeSpec(design_lifetime_years=10.0, acceptance_factor=1.25)
        self.assertAlmostEqual(spec.acceptance_lifetime_years, 12.5)

    def test_negative_design_lifetime_raises(self):
        with self.assertRaises(ValueError):
            MissionLifetimeSpec(design_lifetime_years=-1.0)

    def test_zero_design_lifetime_raises(self):
        with self.assertRaises(ValueError):
            MissionLifetimeSpec(design_lifetime_years=0.0)

    def test_qualification_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            MissionLifetimeSpec(design_lifetime_years=5.0, qualification_factor=0.9)

    def test_acceptance_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            MissionLifetimeSpec(design_lifetime_years=5.0, acceptance_factor=0.5)


class TestEnvironmentEntryValidation(unittest.TestCase):

    def test_valid_natural_entry(self):
        e = EnvironmentEntry("thermal", "natural", ["on_orbit"], True)
        self.assertEqual(e.family, "thermal")
        self.assertEqual(e.category, "natural")
        self.assertTrue(e.quantified)

    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            EnvironmentEntry("thermal", "other", ["on_orbit"], True)

    def test_unrecognized_phase_raises(self):
        with self.assertRaises(ValueError):
            EnvironmentEntry("thermal", "natural", ["cruise"], True)

    def test_multiple_phases_accepted(self):
        e = EnvironmentEntry("acoustic", "induced", ["launch", "on_orbit"], True)
        self.assertIn("launch", e.phases)
        self.assertIn("on_orbit", e.phases)


class TestInventoryOperations(unittest.TestCase):

    def _full_spec(self):
        spec = MissionLifetimeSpec(design_lifetime_years=15.0)
        for family, category in [
            ("thermal", "natural"),
            ("radiation", "natural"),
            ("acoustic", "induced"),
            ("vibration", "induced"),
            ("shock", "induced"),
        ]:
            spec.add_environment(EnvironmentEntry(family, category, ["launch", "on_orbit"], True))
        return spec

    def test_get_inventory_returns_all_added_entries(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        spec.add_environment(_make_entry("thermal", "natural"))
        spec.add_environment(_make_entry("acoustic", "induced"))
        self.assertEqual(len(spec.get_inventory()), 2)

    def test_get_inventory_is_a_copy(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        spec.add_environment(_make_entry())
        copy = spec.get_inventory()
        copy.clear()
        self.assertEqual(len(spec.get_inventory()), 1)

    def test_add_environment_rejects_non_entry(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        with self.assertRaises(TypeError):
            spec.add_environment({"family": "thermal"})

    def test_categorize_by_type_splits_natural_and_induced(self):
        spec = self._full_spec()
        groups = spec.categorize_by_type()
        natural_names = {e.family for e in groups["natural"]}
        induced_names = {e.family for e in groups["induced"]}
        self.assertIn("thermal", natural_names)
        self.assertIn("acoustic", induced_names)
        self.assertNotIn("acoustic", natural_names)
        self.assertNotIn("thermal", induced_names)

    def test_families_by_phase_filters_correctly(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        spec.add_environment(EnvironmentEntry("acoustic", "induced", ["launch"], True))
        spec.add_environment(EnvironmentEntry("thermal", "natural", ["on_orbit"], True))
        launch_families = {e.family for e in spec.families_by_phase("launch")}
        self.assertIn("acoustic", launch_families)
        self.assertNotIn("thermal", launch_families)

    def test_families_by_phase_unknown_phase_raises(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        with self.assertRaises(ValueError):
            spec.families_by_phase("cruise")

    def test_unquantified_families_returns_only_unquantified(self):
        spec = MissionLifetimeSpec(design_lifetime_years=5.0)
        spec.add_environment(_make_entry("thermal", "natural", quantified=True))
        spec.add_environment(_make_entry("radiation", "natural", quantified=False))
        unq = {e.family for e in spec.unquantified_families()}
        self.assertIn("radiation", unq)
        self.assertNotIn("thermal", unq)


class TestCompletenessCheck(unittest.TestCase):

    def _full_spec(self):
        spec = MissionLifetimeSpec(design_lifetime_years=15.0)
        for family, category in [
            ("thermal", "natural"),
            ("radiation", "natural"),
            ("acoustic", "induced"),
            ("vibration", "induced"),
            ("shock", "induced"),
        ]:
            spec.add_environment(EnvironmentEntry(family, category, ["on_orbit"], True))
        return spec

    def test_complete_inventory_has_no_findings(self):
        spec = self._full_spec()
        self.assertEqual(spec.check_completeness(), [])

    def test_missing_required_family_produces_finding(self):
        spec = MissionLifetimeSpec(design_lifetime_years=10.0)
        spec.add_environment(EnvironmentEntry("thermal", "natural", ["on_orbit"], True))
        findings = spec.check_completeness()
        missing_findings = [f for f in findings if "missing" in f]
        self.assertTrue(len(missing_findings) > 0)

    def test_unquantified_entry_produces_finding(self):
        spec = self._full_spec()
        spec.add_environment(
            EnvironmentEntry("debris", "natural", ["on_orbit"], False)
        )
        findings = spec.check_completeness()
        unq_findings = [f for f in findings if "not quantified" in f]
        self.assertTrue(len(unq_findings) > 0)

    def test_all_required_families_present_in_complete_spec(self):
        spec = self._full_spec()
        present = {e.family for e in spec.get_inventory()}
        for family in REQUIRED_ENVIRONMENT_FAMILIES:
            self.assertIn(family, present)


class TestValidateLifetimeMargins(unittest.TestCase):

    def test_compliant_margins_return_no_findings(self):
        findings = validate_lifetime_margins(10.0, MIN_QUALIFICATION_FACTOR, MIN_ACCEPTANCE_FACTOR)
        self.assertEqual(findings, [])

    def test_qualification_factor_below_minimum_returns_finding(self):
        findings = validate_lifetime_margins(10.0, 1.2, MIN_ACCEPTANCE_FACTOR)
        self.assertTrue(any("qualification" in f for f in findings))

    def test_acceptance_factor_below_minimum_returns_finding(self):
        findings = validate_lifetime_margins(10.0, MIN_QUALIFICATION_FACTOR, 1.0)
        self.assertTrue(any("acceptance" in f for f in findings))

    def test_non_positive_design_lifetime_returns_finding(self):
        findings = validate_lifetime_margins(0.0, MIN_QUALIFICATION_FACTOR, MIN_ACCEPTANCE_FACTOR)
        self.assertTrue(len(findings) > 0)

    def test_generous_factors_above_minimum_are_compliant(self):
        findings = validate_lifetime_margins(20.0, 2.0, 1.5)
        self.assertEqual(findings, [])

    def test_both_factors_below_minimum_returns_two_findings(self):
        findings = validate_lifetime_margins(5.0, 1.1, 1.0)
        qual_findings = [f for f in findings if "qualification" in f]
        acc_findings = [f for f in findings if "acceptance" in f]
        self.assertEqual(len(qual_findings), 1)
        self.assertEqual(len(acc_findings), 1)


class TestCategorizeEnvironmentFamily(unittest.TestCase):

    def test_thermal_is_natural(self):
        self.assertEqual(categorize_environment_family("thermal"), "natural")

    def test_radiation_is_natural(self):
        self.assertEqual(categorize_environment_family("radiation"), "natural")

    def test_acoustic_is_induced(self):
        self.assertEqual(categorize_environment_family("acoustic"), "induced")

    def test_vibration_is_induced(self):
        self.assertEqual(categorize_environment_family("vibration"), "induced")

    def test_shock_is_induced(self):
        self.assertEqual(categorize_environment_family("shock"), "induced")

    def test_debris_is_natural(self):
        self.assertEqual(categorize_environment_family("debris"), "natural")

    def test_unrecognized_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_environment_family("solar_wind_unknown")

    def test_natural_families_never_return_induced(self):
        natural = ["thermal", "radiation", "debris", "atomic_oxygen", "uv", "vacuum"]
        for family in natural:
            self.assertEqual(categorize_environment_family(family), "natural")

    def test_induced_families_never_return_natural(self):
        induced = ["acoustic", "vibration", "shock", "quasi_static", "pressure"]
        for family in induced:
            self.assertEqual(categorize_environment_family(family), "induced")


if __name__ == "__main__":
    unittest.main()
