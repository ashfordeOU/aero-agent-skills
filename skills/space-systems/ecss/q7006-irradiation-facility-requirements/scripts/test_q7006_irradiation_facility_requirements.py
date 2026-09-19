"""Contract tests for the irradiation facility requirement logic."""

import unittest

from q7006_irradiation_facility_requirements_logic import (
    MAX_ACCELERATION_FACTOR,
    MAX_UNIFORMITY_PCT,
    SEQUENTIAL_ORDERS,
    acceleration_factor,
    energy_coverage_findings,
    exposure_hours,
    exposure_mode,
    grade_facility,
    rank_facilities,
    select_irradiation_facility,
    uniformity_pct,
    validate_facility,
)


def facility(**overrides):
    record = {
        "name": "combined-beam-chamber",
        "agents": ["particles", "ultraviolet"],
        "energy_min_mev": 0.05,
        "energy_max_mev": 20.0,
        "max_particle_flux": 1.0e8,
        "max_uv_suns": 5.0,
        "uniformity_pct": 4.0,
        "base_pressure_pa": 1.0e-4,
        "temperature_window_c": (-100.0, 120.0),
        "combined_capable": True,
    }
    record.update(overrides)
    return record


def requirement(**overrides):
    req = {
        "agents": ["particles", "ultraviolet"],
        "energy_min_mev": 0.1,
        "energy_max_mev": 10.0,
        "mission_particle_flux": 1.0e6,
        "target_particle_fluence": 1.0e14,
        "max_pressure_pa": 1.0e-3,
        "specimen_temperature_c": 20.0,
        "synergy_expected": True,
    }
    req.update(overrides)
    return req


class ValidateFacilityTests(unittest.TestCase):
    def test_agents_are_deduplicated_and_sorted(self):
        record = validate_facility(facility(agents=["ultraviolet", "particles", "particles"]))
        self.assertEqual(record["agents"], ("particles", "ultraviolet"))

    def test_name_is_stripped(self):
        self.assertEqual(validate_facility(facility(name=" rig-a "))["name"], "rig-a")

    def test_unknown_agent_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(agents=["neutrinos"]))

    def test_empty_agent_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(agents=[]))

    def test_inverted_energy_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(energy_min_mev=20.0, energy_max_mev=0.05))

    def test_inverted_temperature_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(temperature_window_c=(120.0, -100.0)))

    def test_combined_claim_with_one_agent_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(agents=["particles"], combined_capable=True))

    def test_non_boolean_combined_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(facility(combined_capable="yes"))

    def test_missing_key_rejected(self):
        record = facility()
        del record["uniformity_pct"]
        with self.assertRaises(ValueError):
            validate_facility(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_facility(["name"])


class ArithmeticTests(unittest.TestCase):
    def test_acceleration_is_the_flux_ratio(self):
        self.assertAlmostEqual(acceleration_factor(1.0e8, 1.0e6), 100.0, places=9)

    def test_matching_flux_gives_unity_acceleration(self):
        self.assertAlmostEqual(acceleration_factor(4.2e5, 4.2e5), 1.0, places=9)

    def test_zero_mission_flux_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(1.0e8, 0.0)

    def test_beam_hours_from_fluence_and_flux(self):
        self.assertAlmostEqual(exposure_hours(3.6e9, 1.0e6), 1.0, places=9)

    def test_doubling_the_flux_halves_the_beam_hours(self):
        self.assertAlmostEqual(
            exposure_hours(1.0e12, 2.0e6) * 2.0, exposure_hours(1.0e12, 1.0e6), places=9
        )

    def test_zero_fluence_needs_no_beam_time(self):
        self.assertAlmostEqual(exposure_hours(0.0, 1.0e6), 0.0, places=9)

    def test_perfectly_flat_plane_has_zero_spread(self):
        self.assertAlmostEqual(uniformity_pct(100.0, 100.0), 0.0, places=9)

    def test_uniformity_is_a_plus_minus_percentage(self):
        self.assertAlmostEqual(uniformity_pct(90.0, 110.0), 10.0, places=9)

    def test_inverted_flux_pair_rejected(self):
        with self.assertRaises(ValueError):
            uniformity_pct(110.0, 90.0)


class EnergyCoverageTests(unittest.TestCase):
    def test_enveloping_facility_has_no_findings(self):
        record = validate_facility(facility())
        self.assertEqual(energy_coverage_findings(record, 0.1, 10.0), [])

    def test_exactly_matching_window_has_no_findings(self):
        record = validate_facility(facility(energy_min_mev=0.1, energy_max_mev=10.0))
        self.assertEqual(energy_coverage_findings(record, 0.1, 10.0), [])

    def test_soft_end_shortfall_reported(self):
        record = validate_facility(facility(energy_min_mev=1.0))
        self.assertEqual(len(energy_coverage_findings(record, 0.1, 10.0)), 1)

    def test_hard_end_shortfall_reported(self):
        record = validate_facility(facility(energy_max_mev=5.0))
        notes = energy_coverage_findings(record, 0.1, 10.0)
        self.assertIn("stops at", notes[0])

    def test_inverted_requirement_rejected(self):
        record = validate_facility(facility())
        with self.assertRaises(ValueError):
            energy_coverage_findings(record, 10.0, 0.1)


class ExposureModeTests(unittest.TestCase):
    def test_single_agent_campaign_has_no_ordering_question(self):
        record = validate_facility(facility())
        self.assertEqual(exposure_mode(record, ["particles"], True)[0], "single-agent")

    def test_combined_facility_runs_combined(self):
        record = validate_facility(facility())
        mode, notes = exposure_mode(record, ["particles", "ultraviolet"], True)
        self.assertEqual(mode, "combined")
        self.assertEqual(notes, [])

    def test_sequential_facility_uses_the_named_order(self):
        record = validate_facility(facility(combined_capable=False))
        mode, _notes = exposure_mode(
            record, ["particles", "ultraviolet"], False,
            sequential_order="ultraviolet-then-particles",
        )
        self.assertEqual(mode, "ultraviolet-then-particles")

    def test_lost_synergy_is_a_finding(self):
        record = validate_facility(facility(combined_capable=False))
        _mode, notes = exposure_mode(record, ["particles", "ultraviolet"], True)
        self.assertEqual(len(notes), 1)
        self.assertIn("synergistic", notes[0])

    def test_no_synergy_expected_leaves_no_finding(self):
        record = validate_facility(facility(combined_capable=False))
        _mode, notes = exposure_mode(record, ["particles", "ultraviolet"], False)
        self.assertEqual(notes, [])

    def test_unknown_order_rejected(self):
        record = validate_facility(facility())
        with self.assertRaises(ValueError):
            exposure_mode(record, ["particles"], False, sequential_order="uv-first")

    def test_every_named_order_is_accepted(self):
        record = validate_facility(facility(combined_capable=False))
        for order in SEQUENTIAL_ORDERS:
            mode, _notes = exposure_mode(
                record, ["particles", "ultraviolet"], False, sequential_order=order
            )
            self.assertEqual(mode, order)

    def test_empty_agent_requirement_rejected(self):
        record = validate_facility(facility())
        with self.assertRaises(ValueError):
            exposure_mode(record, [], False)


class GradeFacilityTests(unittest.TestCase):
    def test_capable_facility_is_admissible(self):
        graded = grade_facility(facility(), requirement())
        self.assertTrue(graded["admissible"])
        self.assertEqual(graded["exposure_mode"], "combined")

    def test_acceleration_factor_is_reported(self):
        graded = grade_facility(facility(), requirement())
        self.assertAlmostEqual(graded["acceleration_factor"], 100.0, places=9)

    def test_beam_hours_are_reported(self):
        graded = grade_facility(facility(), requirement())
        self.assertAlmostEqual(graded["beam_hours"], 1.0e14 / 1.0e8 / 3600.0, places=9)

    def test_missing_agent_is_a_finding(self):
        graded = grade_facility(
            facility(agents=["particles"], combined_capable=False), requirement()
        )
        self.assertFalse(graded["admissible"])
        self.assertTrue(any("does not produce" in note for note in graded["findings"]))

    def test_coarse_uniformity_is_a_finding(self):
        graded = grade_facility(
            facility(uniformity_pct=MAX_UNIFORMITY_PCT * 2.0), requirement()
        )
        self.assertTrue(any("uniformity" in note for note in graded["findings"]))

    def test_uniformity_exactly_at_the_limit_passes(self):
        graded = grade_facility(facility(uniformity_pct=MAX_UNIFORMITY_PCT), requirement())
        self.assertTrue(graded["admissible"])

    def test_poor_vacuum_is_a_finding(self):
        graded = grade_facility(facility(base_pressure_pa=1.0), requirement())
        self.assertTrue(any("Pa" in note for note in graded["findings"]))

    def test_temperature_outside_the_window_is_a_finding(self):
        graded = grade_facility(facility(), requirement(specimen_temperature_c=200.0))
        self.assertTrue(any("cannot hold" in note for note in graded["findings"]))

    def test_excessive_acceleration_is_a_finding(self):
        graded = grade_facility(
            facility(max_particle_flux=1.0e6 * MAX_ACCELERATION_FACTOR * 10.0), requirement()
        )
        self.assertTrue(any("acceleration" in note for note in graded["findings"]))

    def test_acceleration_exactly_at_the_limit_passes(self):
        graded = grade_facility(
            facility(max_particle_flux=1.0e6 * MAX_ACCELERATION_FACTOR), requirement()
        )
        self.assertTrue(graded["admissible"])

    def test_missing_requirement_key_rejected(self):
        req = requirement()
        del req["max_pressure_pa"]
        with self.assertRaises(ValueError):
            grade_facility(facility(), req)

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            grade_facility(facility(), ["agents"])


class SelectionTests(unittest.TestCase):
    def _candidates(self):
        return [
            facility(name="fast-rig", max_particle_flux=1.0e9),
            facility(name="slow-rig", max_particle_flux=1.0e7),
            facility(name="uv-only-rig", agents=["ultraviolet"], combined_capable=False),
        ]

    def test_lowest_acceleration_admissible_candidate_wins(self):
        result = select_irradiation_facility(self._candidates(), requirement())
        self.assertEqual(result["selected"]["name"], "slow-rig")

    def test_inadmissible_candidates_rank_last(self):
        ranked = rank_facilities(self._candidates(), requirement())
        self.assertEqual(ranked[-1]["name"], "uv-only-rig")

    def test_admissible_count_is_reported(self):
        result = select_irradiation_facility(self._candidates(), requirement())
        self.assertEqual(result["admissible_count"], 2)

    def test_tie_is_broken_on_the_name(self):
        candidates = [
            facility(name="rig-b", max_particle_flux=1.0e7),
            facility(name="rig-a", max_particle_flux=1.0e7),
        ]
        result = select_irradiation_facility(candidates, requirement())
        self.assertEqual(result["selected"]["name"], "rig-a")

    def test_no_admissible_candidate_is_reported(self):
        candidates = [facility(name="uv-only", agents=["ultraviolet"], combined_capable=False)]
        result = select_irradiation_facility(candidates, requirement())
        self.assertFalse(result["selection_made"])
        self.assertIsNone(result["selected"])
        self.assertEqual(len(result["findings"]), 1)

    def test_duplicate_names_rejected(self):
        candidates = [facility(name="rig"), facility(name="rig")]
        with self.assertRaises(ValueError):
            rank_facilities(candidates, requirement())

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_facilities([], requirement())

    def test_ranking_is_stable_under_input_order(self):
        forward = rank_facilities(self._candidates(), requirement())
        backward = rank_facilities(list(reversed(self._candidates())), requirement())
        self.assertEqual(
            [record["name"] for record in forward],
            [record["name"] for record in backward],
        )


if __name__ == "__main__":
    unittest.main()
