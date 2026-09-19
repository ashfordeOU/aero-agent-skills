"""Contract tests for the launch-site cleanliness control logic."""

import unittest

from q7001_launch_site_control_logic import (
    BUDGET_TOLERANCE,
    ENVIRONMENT_FALLOUT_PPM_PER_HOUR,
    PROTECTION_TRANSMISSION,
    STAGE_ACTIVITIES,
    accumulate_launch_campaign,
    encapsulation_findings,
    environment_rate,
    plan_launch_site_control,
    propellant_findings,
    protection_transmission,
    purge_findings,
    stage_molecular_mg_per_m2,
    stage_particulate_ppm,
    validate_sequence,
    validate_stage,
)


def _stage(**overrides):
    stage = {
        "activity": "integration",
        "environment": "ISO-8",
        "duration_hours": 20.0,
        "protection": "open",
    }
    stage.update(overrides)
    return stage


def _stages():
    return [
        _stage(activity="arrival", environment="transfer-corridor",
               duration_hours=8.0, protection="transport-container"),
        _stage(activity="unpacking", environment="ISO-8", duration_hours=6.0,
               protection="open"),
        _stage(activity="integration", environment="ISO-8", duration_hours=60.0,
               protection="open"),
        _stage(activity="propellant-loading", environment="ISO-8",
               duration_hours=10.0, protection="covered", vapour_protection=True),
        _stage(activity="encapsulation", environment="ISO-7", duration_hours=6.0,
               protection="open", fairing_verified=True),
        _stage(activity="transfer", environment="transfer-corridor",
               duration_hours=4.0, protection="encapsulated-purged",
               purge_connected=True),
        _stage(activity="pad-stay", environment="pad-open-air",
               duration_hours=48.0, protection="encapsulated-purged",
               purge_connected=True),
    ]


def _campaign(**overrides):
    campaign = {
        "stages": _stages(),
        "particulate_budget_ppm": 5.0,
        "molecular_budget_mg_per_m2": 3.0,
    }
    campaign.update(overrides)
    return campaign


class EnvironmentTests(unittest.TestCase):
    def test_pad_is_the_worst_environment(self):
        worst = max(ENVIRONMENT_FALLOUT_PPM_PER_HOUR.values())
        self.assertAlmostEqual(environment_rate("pad-open-air"), worst)

    def test_cleanroom_beats_the_corridor(self):
        self.assertLess(environment_rate("ISO-6"), environment_rate("transfer-corridor"))

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            environment_rate("hangar")

    def test_open_hardware_sees_everything(self):
        self.assertAlmostEqual(protection_transmission("open"), 1.0)

    def test_purged_fairing_is_the_best_protection(self):
        best = min(PROTECTION_TRANSMISSION.values())
        self.assertAlmostEqual(protection_transmission("encapsulated-purged"), best)

    def test_unpurged_fairing_is_worse_than_a_purged_one(self):
        self.assertGreater(
            protection_transmission("encapsulated-unpurged"),
            protection_transmission("encapsulated-purged"),
        )

    def test_unknown_protection_rejected(self):
        with self.assertRaises(ValueError):
            protection_transmission("tarpaulin")


class StageValidationTests(unittest.TestCase):
    def test_valid_stage_normalizes_with_defaults(self):
        normalized = validate_stage(_stage())
        self.assertFalse(normalized["purge_connected"])
        self.assertFalse(normalized["fairing_verified"])

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage(_stage(activity="refuelling"))

    def test_missing_key_rejected(self):
        broken = _stage()
        del broken["environment"]
        with self.assertRaises(ValueError):
            validate_stage(broken)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage(_stage(duration_hours=-4.0))

    def test_non_mapping_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_stage("integration")

    def test_campaign_order_is_accepted(self):
        self.assertEqual(len(validate_sequence(_stages())), len(STAGE_ACTIVITIES))

    def test_out_of_order_campaign_rejected(self):
        stages = [
            _stage(activity="encapsulation", fairing_verified=True),
            _stage(activity="integration"),
        ]
        with self.assertRaises(ValueError):
            validate_sequence(stages)

    def test_repeated_activity_rejected(self):
        stages = [_stage(activity="integration"), _stage(activity="integration")]
        with self.assertRaises(ValueError):
            validate_sequence(stages)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])


class StageContributionTests(unittest.TestCase):
    def test_particulate_is_rate_times_hours_times_transmission(self):
        value = stage_particulate_ppm(
            _stage(environment="ISO-8", duration_hours=10.0, protection="covered")
        )
        self.assertAlmostEqual(value, 0.025 * 10.0 * 0.30, places=12)

    def test_transport_container_cuts_the_pickup(self):
        openly = stage_particulate_ppm(_stage(protection="open"))
        boxed = stage_particulate_ppm(_stage(protection="transport-container"))
        self.assertAlmostEqual(boxed, openly * 0.05, places=12)

    def test_zero_duration_adds_nothing(self):
        self.assertAlmostEqual(stage_particulate_ppm(_stage(duration_hours=0.0)), 0.0)

    def test_pad_stay_dominates_an_unprotected_campaign(self):
        pad = stage_particulate_ppm(
            _stage(activity="pad-stay", environment="pad-open-air",
                   duration_hours=48.0, protection="open")
        )
        hall = stage_particulate_ppm(
            _stage(activity="integration", environment="ISO-8",
                   duration_hours=48.0, protection="open")
        )
        self.assertGreater(pad, hall)

    def test_propellant_vapour_adds_a_molecular_source(self):
        loading = stage_molecular_mg_per_m2(
            _stage(activity="propellant-loading", environment="ISO-8",
                   duration_hours=10.0, protection="open")
        )
        plain = stage_molecular_mg_per_m2(
            _stage(activity="integration", environment="ISO-8",
                   duration_hours=10.0, protection="open")
        )
        self.assertAlmostEqual(loading - plain, 0.06 * 10.0, places=12)

    def test_vapour_protection_cuts_the_propellant_source(self):
        unprotected = stage_molecular_mg_per_m2(
            _stage(activity="propellant-loading", environment="ISO-8",
                   duration_hours=10.0, protection="open")
        )
        protected = stage_molecular_mg_per_m2(
            _stage(activity="propellant-loading", environment="ISO-8",
                   duration_hours=10.0, protection="open", vapour_protection=True)
        )
        self.assertLess(protected, unprotected)


class RuleTests(unittest.TestCase):
    def test_verified_fairing_raises_no_finding(self):
        self.assertEqual(encapsulation_findings(_stages()), [])

    def test_unverified_fairing_is_a_finding(self):
        stages = _stages()
        stages[4] = _stage(activity="encapsulation", environment="ISO-7",
                           duration_hours=6.0, protection="open")
        findings = encapsulation_findings(stages)
        self.assertEqual(len(findings), 1)
        self.assertIn("without a cleanliness verification", findings[0])

    def test_protected_loading_raises_no_finding(self):
        self.assertEqual(propellant_findings(_stages()), [])

    def test_unprotected_loading_is_a_finding(self):
        stages = _stages()
        stages[3] = _stage(activity="propellant-loading", environment="ISO-8",
                           duration_hours=10.0, protection="covered")
        findings = propellant_findings(stages)
        self.assertEqual(len(findings), 1)
        self.assertIn("vapour", findings[0])

    def test_connected_purge_raises_no_finding(self):
        self.assertEqual(purge_findings(_stages()), [])

    def test_purge_credit_without_a_purge_is_a_finding(self):
        stages = _stages()
        stages[6] = _stage(activity="pad-stay", environment="pad-open-air",
                           duration_hours=48.0, protection="encapsulated-purged")
        findings = purge_findings(stages)
        self.assertEqual(len(findings), 1)
        self.assertIn("no purge", findings[0])


class AccumulationTests(unittest.TestCase):
    def test_one_row_per_stage(self):
        self.assertEqual(len(accumulate_launch_campaign(_stages())), 7)

    def test_cumulative_matches_the_sum_of_additions(self):
        rows = accumulate_launch_campaign(_stages())
        total = sum(row["added_particulate_ppm"] for row in rows)
        self.assertAlmostEqual(rows[-1]["cumulative_particulate_ppm"], total, places=12)

    def test_cumulative_never_decreases(self):
        rows = accumulate_launch_campaign(_stages())
        values = [row["cumulative_molecular_mg_per_m2"] for row in rows]
        self.assertEqual(values, sorted(values))


class PlanTests(unittest.TestCase):
    def test_well_run_campaign_is_ready(self):
        result = plan_launch_site_control(_campaign())
        self.assertTrue(result["ready_for_launch"])
        self.assertEqual(result["findings"], [])

    def test_dominant_stage_is_named(self):
        result = plan_launch_site_control(_campaign())
        self.assertIn(result["dominant_stage"], STAGE_ACTIVITIES)

    def test_margin_is_budget_less_total(self):
        result = plan_launch_site_control(_campaign())
        self.assertAlmostEqual(
            result["particulate_margin_ppm"],
            5.0 - result["total_particulate_ppm"],
            places=12,
        )

    def test_arrival_state_is_carried_in(self):
        clean = plan_launch_site_control(_campaign())
        dirty = plan_launch_site_control(_campaign(arrival_particulate_ppm=0.5))
        self.assertAlmostEqual(
            dirty["total_particulate_ppm"] - clean["total_particulate_ppm"],
            0.5,
            places=12,
        )

    def test_tight_budget_is_broken(self):
        result = plan_launch_site_control(_campaign(particulate_budget_ppm=0.01))
        self.assertFalse(result["ready_for_launch"])
        self.assertTrue(any("obscuration at lift-off" in n for n in result["findings"]))

    def test_molecular_budget_is_tracked_separately(self):
        result = plan_launch_site_control(_campaign(molecular_budget_mg_per_m2=0.01))
        self.assertFalse(result["ready_for_launch"])
        self.assertTrue(any("molecular loading" in n for n in result["findings"]))

    def test_unverified_fairing_blocks_the_campaign(self):
        stages = _stages()
        stages[4] = _stage(activity="encapsulation", environment="ISO-7",
                           duration_hours=6.0, protection="open")
        result = plan_launch_site_control(_campaign(stages=stages))
        self.assertFalse(result["ready_for_launch"])

    def test_leaving_the_fairing_open_on_the_pad_costs_budget(self):
        stages = _stages()
        stages[6] = _stage(activity="pad-stay", environment="pad-open-air",
                           duration_hours=48.0, protection="covered")
        exposed = plan_launch_site_control(_campaign(stages=stages))
        closed = plan_launch_site_control(_campaign())
        self.assertGreater(
            exposed["total_particulate_ppm"], closed["total_particulate_ppm"]
        )

    def test_budget_exactly_consumed_is_still_within_budget(self):
        baseline = plan_launch_site_control(_campaign())
        exact = plan_launch_site_control(
            _campaign(particulate_budget_ppm=baseline["total_particulate_ppm"])
        )
        self.assertTrue(exact["ready_for_launch"])
        self.assertLessEqual(abs(exact["particulate_margin_ppm"]), BUDGET_TOLERANCE)

    def test_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            plan_launch_site_control(_campaign(particulate_budget_ppm=0.0))

    def test_missing_campaign_key_rejected(self):
        campaign = _campaign()
        del campaign["molecular_budget_mg_per_m2"]
        with self.assertRaises(ValueError):
            plan_launch_site_control(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            plan_launch_site_control(["stages"])


if __name__ == "__main__":
    unittest.main()
