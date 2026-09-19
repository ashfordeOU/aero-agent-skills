"""Contract test for the latching, locking and end-stop leaf (stdlib unittest)."""

import unittest

from e3301_latching_locking_end_stops_logic import (
    MIN_ENERGY_FACTOR,
    VERDICT_NEGATIVE,
    VERDICT_POSITIVE,
    VERDICT_ZERO,
    applied_energy_factor,
    arriving_energy,
    assess_end_stop,
    assess_latch,
    assess_latching_and_end_stops,
    capture_findings,
    kinetic_energy,
    margin_verdict,
    preload_margin,
    required_absorption_energy,
    validate_end_stop,
    validate_latch,
    work_over_residual_travel,
)


def end_stop(sid="ES-1", travel_limit="end", **kw):
    record = {
        "id": sid,
        "travel_limit": travel_limit,
        "inertia": 2.0,
        "approach_rate": 1.0,
        "residual_travel": 0.0,
        "stored_spring_effort": 0.0,
        "residual_drive_effort": 0.0,
        "absorption_capacity": 5.0,
    }
    record.update(kw)
    return record


def latch(lid="L-1", **kw):
    record = {
        "id": lid,
        "capture_window": [88.0, 92.0],
        "arrival_position": 90.0,
        "overshoot": 1.0,
        "lock_preload": 20.0,
        "disturbing_load": 5.0,
        "status_indication": True,
    }
    record.update(kw)
    return record


def mechanism(**kw):
    record = {
        "id": "SOLAR-WING-HINGE",
        "travel_range": 90.0,
        "reachable_limits": ["start", "end"],
        "end_stops": [end_stop("ES-0", "start"), end_stop("ES-1", "end")],
        "latches": [latch("L-1")],
    }
    record.update(kw)
    return record


class TestEnergyTerms(unittest.TestCase):
    def test_kinetic_energy_is_half_inertia_rate_squared(self):
        self.assertAlmostEqual(kinetic_energy(2.0, 3.0), 9.0, places=9)

    def test_zero_rate_gives_zero_kinetic_energy(self):
        self.assertAlmostEqual(kinetic_energy(2.0, 0.0), 0.0, places=9)

    def test_zero_inertia_raises(self):
        with self.assertRaises(ValueError):
            kinetic_energy(0.0, 3.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            kinetic_energy(2.0, -1.0)

    def test_work_is_effort_times_residual_travel(self):
        self.assertAlmostEqual(work_over_residual_travel(4.0, 0.25), 1.0, places=9)

    def test_negative_residual_travel_raises(self):
        with self.assertRaises(ValueError):
            work_over_residual_travel(4.0, -0.1)

    def test_all_three_sources_are_summed(self):
        energy = arriving_energy(
            end_stop(
                residual_travel=0.10,
                stored_spring_effort=3.0,
                residual_drive_effort=2.0,
            )
        )
        self.assertAlmostEqual(energy["kinetic"], 1.0, places=9)
        self.assertAlmostEqual(energy["stored_spring"], 0.30, places=9)
        self.assertAlmostEqual(energy["driven"], 0.20, places=9)
        self.assertAlmostEqual(energy["total"], 1.50, places=9)


class TestEnergyFactor(unittest.TestCase):
    def test_absent_declaration_falls_to_the_floor(self):
        factor, findings = applied_energy_factor(end_stop())
        self.assertAlmostEqual(factor, MIN_ENERGY_FACTOR, places=9)
        self.assertEqual(findings, [])

    def test_declaration_on_the_floor_is_accepted(self):
        factor, findings = applied_energy_factor(
            end_stop(declared_energy_factor=MIN_ENERGY_FACTOR)
        )
        self.assertAlmostEqual(factor, MIN_ENERGY_FACTOR, places=9)
        self.assertEqual(findings, [])

    def test_light_declaration_is_raised_and_flagged(self):
        factor, findings = applied_energy_factor(end_stop(declared_energy_factor=1.1))
        self.assertAlmostEqual(factor, MIN_ENERGY_FACTOR, places=9)
        self.assertEqual(findings, ["declared-energy-factor-below-minimum"])

    def test_conservative_declaration_is_kept(self):
        factor, findings = applied_energy_factor(end_stop(declared_energy_factor=2.5))
        self.assertAlmostEqual(factor, 2.5, places=9)
        self.assertEqual(findings, [])

    def test_required_energy_applies_the_factor(self):
        self.assertAlmostEqual(
            required_absorption_energy(end_stop()), 1.0 * MIN_ENERGY_FACTOR, places=9
        )


class TestValidateEndStop(unittest.TestCase):
    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_end_stop("ES-1")

    def test_unknown_travel_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_end_stop(end_stop(travel_limit="middle"))

    def test_zero_absorption_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_end_stop(end_stop(absorption_capacity=0.0))

    def test_boolean_inertia_raises(self):
        with self.assertRaises(ValueError):
            validate_end_stop(end_stop(inertia=True))


class TestAssessEndStop(unittest.TestCase):
    def test_capable_stop_passes(self):
        result = assess_end_stop(end_stop())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["required_energy"], 1.5, places=9)
        self.assertEqual(result["verdict"], VERDICT_POSITIVE)

    def test_capacity_exactly_on_the_requirement_is_zero_not_negative(self):
        result = assess_end_stop(end_stop(absorption_capacity=1.5))
        self.assertEqual(result["verdict"], VERDICT_ZERO)
        self.assertAlmostEqual(result["energy_margin"], 0.0, places=9)
        self.assertTrue(result["compliant"])

    def test_short_stop_is_reported(self):
        result = assess_end_stop(end_stop(absorption_capacity=0.5))
        self.assertFalse(result["compliant"])
        self.assertIn("absorption-capacity-below-required-energy", result["findings"])

    def test_spring_energy_can_be_what_breaks_the_stop(self):
        result = assess_end_stop(
            end_stop(residual_travel=0.5, stored_spring_effort=8.0)
        )
        self.assertFalse(result["compliant"])

    def test_stop_with_no_arriving_energy_is_reported(self):
        result = assess_end_stop(end_stop(approach_rate=0.0))
        self.assertIn("no-arriving-energy-declared", result["findings"])
        self.assertIsNone(result["energy_margin"])


class TestLatch(unittest.TestCase):
    def test_arrival_inside_the_window_is_clean(self):
        self.assertEqual(capture_findings(latch()), [])

    def test_arrival_short_of_the_window_is_reported(self):
        self.assertIn(
            "arrival-outside-capture-window",
            capture_findings(latch(arrival_position=80.0, overshoot=0.0)),
        )

    def test_overshoot_past_the_window_is_reported(self):
        self.assertIn(
            "overshoot-carries-past-capture-window",
            capture_findings(latch(overshoot=6.0)),
        )

    def test_arrival_on_the_window_edge_is_accepted(self):
        self.assertEqual(capture_findings(latch(arrival_position=92.0, overshoot=0.0)), [])

    def test_preload_margin_is_preload_over_disturbance(self):
        self.assertAlmostEqual(preload_margin(latch()), 3.0, places=9)

    def test_equal_preload_and_disturbance_give_zero_margin(self):
        self.assertAlmostEqual(
            preload_margin(latch(lock_preload=5.0)), 0.0, places=9
        )

    def test_weak_preload_fails_the_latch(self):
        result = assess_latch(latch(lock_preload=1.0))
        self.assertFalse(result["compliant"])
        self.assertIn("locking-preload-below-disturbance", result["findings"])

    def test_unindicated_lock_is_reported(self):
        result = assess_latch(latch(status_indication=False))
        self.assertIn("locked-state-not-indicated", result["findings"])

    def test_healthy_latch_passes(self):
        self.assertTrue(assess_latch(latch())["compliant"])

    def test_inverted_capture_window_raises(self):
        with self.assertRaises(ValueError):
            validate_latch(latch(capture_window=[92.0, 88.0]))

    def test_capture_window_of_wrong_length_raises(self):
        with self.assertRaises(ValueError):
            validate_latch(latch(capture_window=[90.0]))

    def test_zero_disturbing_load_raises(self):
        with self.assertRaises(ValueError):
            validate_latch(latch(disturbing_load=0.0))

    def test_non_boolean_status_indication_raises(self):
        with self.assertRaises(ValueError):
            validate_latch(latch(status_indication="green"))


class TestMarginVerdict(unittest.TestCase):
    def test_last_place_noise_is_grouped_as_zero(self):
        self.assertEqual(margin_verdict(-1.0e-15), VERDICT_ZERO)

    def test_clear_signs_are_kept(self):
        self.assertEqual(margin_verdict(0.5), VERDICT_POSITIVE)
        self.assertEqual(margin_verdict(-0.5), VERDICT_NEGATIVE)


class TestAssessMechanism(unittest.TestCase):
    def test_complete_mechanism_passes(self):
        report = assess_latching_and_end_stops(mechanism())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["coverage_findings"], [])

    def test_missing_stop_at_a_reachable_limit_is_reported(self):
        report = assess_latching_and_end_stops(
            mechanism(end_stops=[end_stop("ES-1", "end")])
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["coverage_findings"], ["no-end-stop-at:start"])

    def test_limit_declared_unreachable_needs_no_stop(self):
        report = assess_latching_and_end_stops(
            mechanism(
                reachable_limits=["end"], end_stops=[end_stop("ES-1", "end")]
            )
        )
        self.assertTrue(report["compliant"])

    def test_one_failing_latch_fails_the_mechanism(self):
        report = assess_latching_and_end_stops(
            mechanism(latches=[latch("L-1", status_indication=False)])
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_latch_ids"], ["L-1"])

    def test_one_failing_stop_fails_the_mechanism(self):
        report = assess_latching_and_end_stops(
            mechanism(
                end_stops=[
                    end_stop("ES-0", "start"),
                    end_stop("ES-1", "end", absorption_capacity=0.1),
                ]
            )
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_end_stop_ids"], ["ES-1"])

    def test_duplicate_end_stop_id_raises(self):
        with self.assertRaises(ValueError):
            assess_latching_and_end_stops(
                mechanism(end_stops=[end_stop("ES-1"), end_stop("ES-1")])
            )

    def test_duplicate_latch_id_raises(self):
        with self.assertRaises(ValueError):
            assess_latching_and_end_stops(
                mechanism(latches=[latch("L-1"), latch("L-1")])
            )

    def test_empty_end_stop_list_raises(self):
        with self.assertRaises(ValueError):
            assess_latching_and_end_stops(mechanism(end_stops=[]))

    def test_zero_travel_range_raises(self):
        with self.assertRaises(ValueError):
            assess_latching_and_end_stops(mechanism(travel_range=0.0))

    def test_unknown_reachable_limit_raises(self):
        with self.assertRaises(ValueError):
            assess_latching_and_end_stops(mechanism(reachable_limits=["middle"]))


if __name__ == "__main__":
    unittest.main()
