"""Contract tests for the SCC environment identification logic."""

import unittest

from q7036_scc_environment_identification_logic import (
    AGENT_REGISTRY,
    HOURS_TOLERANCE,
    HUMIDITY_MODERATE_PCT,
    HUMIDITY_SEVERE_PCT,
    SEVERITY_LEVELS,
    agent_severity,
    assess_environments,
    evaluate_phase,
    governing_environment,
    humidity_severity,
    normalize_agent,
    phase_severity,
    protected_severity,
)


def phase(name, agent="chloride-solution", hours=100.0, **extra):
    record = {"name": name, "agent": agent, "duration_hours": hours}
    record.update(extra)
    return record


class RegistryTests(unittest.TestCase):
    def test_every_agent_carries_a_ladder_severity(self):
        for agent, entry in AGENT_REGISTRY.items():
            self.assertIn(entry["severity"], SEVERITY_LEVELS, agent)

    def test_chloride_solution_is_severe(self):
        self.assertEqual(agent_severity("chloride-solution"), "severe")

    def test_vacuum_is_inert(self):
        self.assertEqual(agent_severity("orbit"), "inert")

    def test_purge_gas_is_inert(self):
        self.assertEqual(agent_severity("gn2"), "inert")

    def test_ammonia_is_severe(self):
        self.assertEqual(agent_severity("ammonia"), "severe")

    def test_agent_alias_resolved(self):
        self.assertEqual(normalize_agent("Marine Atmosphere"), "coastal-salt-air")

    def test_unknown_agent_rejected(self):
        with self.assertRaises(ValueError):
            normalize_agent("moon-dust")

    def test_blank_agent_rejected(self):
        with self.assertRaises(ValueError):
            normalize_agent("   ")

    def test_non_string_agent_rejected(self):
        with self.assertRaises(ValueError):
            normalize_agent(70.36)


class HumidityTests(unittest.TestCase):
    def test_dry_air_is_benign(self):
        self.assertEqual(humidity_severity(30.0), "benign")

    def test_humidity_exactly_on_the_moderate_threshold_counts(self):
        self.assertAlmostEqual(HUMIDITY_MODERATE_PCT, 60.0, places=9)
        self.assertEqual(humidity_severity(HUMIDITY_MODERATE_PCT), "moderate")

    def test_humidity_exactly_on_the_severe_threshold_counts(self):
        self.assertAlmostEqual(HUMIDITY_SEVERE_PCT, 85.0, places=9)
        self.assertEqual(humidity_severity(HUMIDITY_SEVERE_PCT), "severe")

    def test_humidity_just_below_the_moderate_threshold_is_benign(self):
        self.assertEqual(humidity_severity(HUMIDITY_MODERATE_PCT - 1e-3), "benign")

    def test_saturated_air_is_severe(self):
        self.assertEqual(humidity_severity(100.0), "severe")

    def test_humidity_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            humidity_severity(140.0)

    def test_negative_humidity_rejected(self):
        with self.assertRaises(ValueError):
            humidity_severity(-5.0)

    def test_boolean_humidity_rejected(self):
        with self.assertRaises(ValueError):
            humidity_severity(True)

    def test_tolerance_is_tight(self):
        self.assertLess(HOURS_TOLERANCE, 1e-6)


class ProtectionTests(unittest.TestCase):
    def test_conformal_coat_drops_one_step(self):
        self.assertEqual(protected_severity("severe", "conformal-coat"), "moderate")

    def test_purge_drops_one_step(self):
        self.assertEqual(protected_severity("moderate", "purge"), "benign")

    def test_protection_never_goes_below_inert(self):
        self.assertEqual(protected_severity("inert", "purge"), "inert")

    def test_declared_none_protection_changes_nothing(self):
        self.assertEqual(protected_severity("severe", "none"), "severe")

    def test_absent_protection_changes_nothing(self):
        self.assertEqual(protected_severity("severe"), "severe")

    def test_unknown_protection_rejected(self):
        with self.assertRaises(ValueError):
            protected_severity("severe", "hopeful-handling")


class PhaseSeverityTests(unittest.TestCase):
    def test_humid_air_severity_comes_from_the_humidity(self):
        self.assertEqual(phase_severity("humid-air", 90.0), "severe")
        self.assertEqual(phase_severity("humid-air", 40.0), "benign")

    def test_humid_air_without_a_humidity_reading_rejected(self):
        with self.assertRaises(ValueError):
            phase_severity("ambient-air")

    def test_chemical_agent_is_not_overridden_by_a_dry_reading(self):
        self.assertEqual(phase_severity("chloride-solution", 5.0), "severe")

    def test_chemical_agent_still_validates_the_humidity_reading(self):
        with self.assertRaises(ValueError):
            phase_severity("chloride-solution", 150.0)

    def test_protection_applies_after_the_humidity_lift(self):
        self.assertEqual(
            phase_severity("humid-air", 90.0, "sealed-bag-desiccant"), "moderate"
        )


class EvaluatePhaseTests(unittest.TestCase):
    def test_severe_phase_is_promoting(self):
        record = evaluate_phase(phase("launch-site"))
        self.assertTrue(record["promoting"])
        self.assertEqual(record["effective_severity"], "severe")

    def test_inert_phase_is_not_promoting(self):
        record = evaluate_phase(phase("on-orbit", agent="vacuum", hours=43800.0))
        self.assertFalse(record["promoting"])

    def test_protection_can_clear_a_promoting_phase(self):
        record = evaluate_phase(
            phase("storage", agent="humid-air", relative_humidity_pct=65.0,
                  protection="sealed-bag-desiccant")
        )
        self.assertEqual(record["effective_severity"], "benign")
        self.assertFalse(record["promoting"])

    def test_base_severity_is_kept_alongside_the_effective_one(self):
        record = evaluate_phase(phase("transport", protection="sealed-container"))
        self.assertEqual(record["base_severity"], "severe")
        self.assertEqual(record["effective_severity"], "moderate")

    def test_missing_key_rejected(self):
        broken = phase("p1")
        del broken["agent"]
        with self.assertRaises(ValueError):
            evaluate_phase(broken)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_phase(phase("p2", hours=-10.0))

    def test_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_phase(["p3"])


class GoverningTests(unittest.TestCase):
    def test_worst_severity_governs(self):
        records = [
            evaluate_phase(phase("a", agent="vacuum")),
            evaluate_phase(phase("b", agent="coastal-salt-air")),
        ]
        self.assertEqual(governing_environment(records)["name"], "b")

    def test_equal_severity_breaks_on_duration(self):
        records = [
            evaluate_phase(phase("short", hours=10.0)),
            evaluate_phase(phase("long", hours=900.0)),
        ]
        self.assertEqual(governing_environment(records)["name"], "long")

    def test_equal_severity_and_duration_breaks_on_name(self):
        records = [
            evaluate_phase(phase("bravo", hours=100.0)),
            evaluate_phase(phase("alpha", hours=100.0)),
        ]
        self.assertEqual(governing_environment(records)["name"], "alpha")

    def test_empty_record_set_rejected(self):
        with self.assertRaises(ValueError):
            governing_environment([])

    def test_malformed_record_rejected(self):
        with self.assertRaises(ValueError):
            governing_environment([{"name": "a"}])


class AssessEnvironmentsTests(unittest.TestCase):
    def test_life_profile_reports_the_governing_environment(self):
        result = assess_environments(
            [
                phase("integration", agent="cleanroom-air", hours=500.0),
                phase("launch-site", agent="coastal-salt-air", hours=720.0),
                phase("on-orbit", agent="vacuum", hours=43800.0),
            ]
        )
        self.assertEqual(result["governing"]["name"], "launch-site")
        self.assertEqual(result["governing_severity"], "severe")
        self.assertTrue(result["any_promoting"])

    def test_promoting_hours_exclude_the_inert_phases(self):
        result = assess_environments(
            [
                phase("launch-site", agent="coastal-salt-air", hours=720.0),
                phase("on-orbit", agent="vacuum", hours=43800.0),
            ]
        )
        self.assertAlmostEqual(result["promoting_hours"], 720.0, places=9)
        self.assertEqual(result["promoting_phase_count"], 1)

    def test_unprotected_severe_phase_is_a_finding(self):
        result = assess_environments([phase("launch-site", hours=720.0)])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("unprotected", result["findings"][0])

    def test_protected_severe_phase_is_not_a_finding(self):
        result = assess_environments(
            [phase("launch-site", hours=720.0, protection="conformal-coat")]
        )
        self.assertEqual(result["findings"], [])

    def test_fully_inert_profile_has_nothing_promoting(self):
        result = assess_environments(
            [
                phase("purged-storage", agent="gn2", hours=2000.0),
                phase("on-orbit", agent="vacuum", hours=43800.0),
            ]
        )
        self.assertFalse(result["any_promoting"])
        self.assertAlmostEqual(result["promoting_hours"], 0.0, places=9)

    def test_zero_duration_promoting_phase_is_flagged_as_incomplete(self):
        result = assess_environments(
            [phase("launch-site", hours=0.0, protection="conformal-coat")]
        )
        self.assertTrue(
            any("life profile is incomplete" in f for f in result["findings"])
        )

    def test_duplicate_phase_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_environments([phase("a"), phase("a")])

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            assess_environments([])

    def test_record_count_matches_the_profile(self):
        result = assess_environments(
            [phase("a"), phase("b", agent="vacuum"), phase("c", agent="gn2")]
        )
        self.assertEqual(len(result["records"]), 3)


if __name__ == "__main__":
    unittest.main()
