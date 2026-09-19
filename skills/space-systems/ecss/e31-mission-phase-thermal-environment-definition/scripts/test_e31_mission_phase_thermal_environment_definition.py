"""Contract tests for the ECSS-E-ST-31 clause 4.1 mission-phase logic."""

import unittest

from e31_mission_phase_thermal_environment_definition_logic import (
    ROLE_ASCENT,
    ROLE_DESCENT,
    ROLE_DOCKED,
    ROLE_GROUND,
    ROLE_OPERATIONAL,
    ROLE_POST_LANDING,
    ROLE_PRE_LAUNCH,
    define_mission_thermal_environment,
    missing_environment_inputs,
    missing_roles,
    sink_envelope,
    timeline_findings,
    validate_phase,
    validate_phase_set,
)

ORBITAL_ENV = {
    "sink_temperature_k": 120.0,
    "conducted_interface_w": 4.0,
    "solar_flux_w_m2": 1361.0,
    "albedo_fraction": 0.3,
    "planetary_ir_w_m2": 237.0,
}


def phase(name, role, start, end, environment):
    return {
        "name": name,
        "role": role,
        "start_h": start,
        "end_h": end,
        "environment": dict(environment),
    }


def full_profile():
    return [
        phase("hangar", ROLE_GROUND, 0.0, 100.0,
              {"sink_temperature_k": 290.0, "conducted_interface_w": 0.0,
               "ambient_temperature_k": 295.0}),
        phase("pad", ROLE_PRE_LAUNCH, 100.0, 110.0,
              {"sink_temperature_k": 300.0, "conducted_interface_w": 2.0,
               "ambient_temperature_k": 305.0, "ground_conditioning_w": 150.0}),
        phase("ascent", ROLE_ASCENT, 110.0, 110.2,
              {"sink_temperature_k": 330.0, "conducted_interface_w": 3.0,
               "aerothermal_flux_w_m2": 1135.0}),
        phase("cruise", ROLE_OPERATIONAL, 110.2, 900.0, ORBITAL_ENV),
        phase("berthed", ROLE_DOCKED, 900.0, 1000.0,
              dict(ORBITAL_ENV, partner_interface_w=25.0)),
        phase("entry", ROLE_DESCENT, 1000.0, 1000.5,
              {"sink_temperature_k": 340.0, "conducted_interface_w": 3.0,
               "aerothermal_flux_w_m2": 24000.0}),
        phase("recovery", ROLE_POST_LANDING, 1000.5, 1020.0,
              {"sink_temperature_k": 285.0, "conducted_interface_w": 1.0,
               "ambient_temperature_k": 288.0}),
    ]


REQUIRED = [
    ROLE_GROUND, ROLE_PRE_LAUNCH, ROLE_ASCENT, ROLE_OPERATIONAL,
    ROLE_DESCENT, ROLE_POST_LANDING,
]


class PhaseValidationTests(unittest.TestCase):
    def test_valid_phase_carries_its_duration(self):
        p = validate_phase(phase("cruise", ROLE_OPERATIONAL, 10.0, 30.0, ORBITAL_ENV))
        self.assertAlmostEqual(p["duration_h"], 20.0, places=9)

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("cruise", "loitering", 10.0, 30.0, ORBITAL_ENV))

    def test_zero_length_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("cruise", ROLE_OPERATIONAL, 10.0, 10.0, ORBITAL_ENV))

    def test_unnamed_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(phase("  ", ROLE_OPERATIONAL, 10.0, 30.0, ORBITAL_ENV))

    def test_albedo_above_one_rejected(self):
        bad = dict(ORBITAL_ENV, albedo_fraction=1.4)
        with self.assertRaises(ValueError):
            validate_phase(phase("cruise", ROLE_OPERATIONAL, 10.0, 30.0, bad))

    def test_albedo_of_zero_is_accepted(self):
        env = dict(ORBITAL_ENV, albedo_fraction=0.0)
        p = validate_phase(phase("eclipse", ROLE_OPERATIONAL, 10.0, 30.0, env))
        self.assertAlmostEqual(p["environment"]["albedo_fraction"], 0.0, places=9)

    def test_non_positive_sink_temperature_rejected(self):
        bad = dict(ORBITAL_ENV, sink_temperature_k=0.0)
        with self.assertRaises(ValueError):
            validate_phase(phase("cruise", ROLE_OPERATIONAL, 10.0, 30.0, bad))

    def test_negative_flux_rejected(self):
        bad = dict(ORBITAL_ENV, solar_flux_w_m2=-1.0)
        with self.assertRaises(ValueError):
            validate_phase(phase("cruise", ROLE_OPERATIONAL, 10.0, 30.0, bad))

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase_set([])

    def test_duplicate_phase_name_rejected(self):
        p = phase("cruise", ROLE_OPERATIONAL, 10.0, 30.0, ORBITAL_ENV)
        with self.assertRaises(ValueError):
            validate_phase_set([p, dict(p)])

    def test_phases_are_sorted_by_start(self):
        out = validate_phase_set(
            [
                phase("second", ROLE_OPERATIONAL, 30.0, 40.0, ORBITAL_ENV),
                phase("first", ROLE_OPERATIONAL, 10.0, 30.0, ORBITAL_ENV),
            ]
        )
        self.assertEqual([p["name"] for p in out], ["first", "second"])


class TimelineTests(unittest.TestCase):
    def test_contiguous_timeline_has_no_findings(self):
        gaps, overlaps = timeline_findings(validate_phase_set(full_profile()))
        self.assertEqual(gaps, [])
        self.assertEqual(overlaps, [])

    def test_gap_is_detected_and_measured(self):
        phases = full_profile()
        phases[3]["start_h"] = 120.0
        gaps, overlaps = timeline_findings(validate_phase_set(phases))
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["gap_h"], 9.8, places=9)
        self.assertEqual(overlaps, [])

    def test_overlap_is_detected_and_measured(self):
        phases = full_profile()
        phases[4]["start_h"] = 880.0
        gaps, overlaps = timeline_findings(validate_phase_set(phases))
        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(overlaps[0]["overlap_h"], 20.0, places=9)
        self.assertEqual(gaps, [])

    def test_single_phase_timeline_has_no_findings(self):
        gaps, overlaps = timeline_findings(
            validate_phase_set([phase("only", ROLE_OPERATIONAL, 0.0, 5.0, ORBITAL_ENV)])
        )
        self.assertEqual((gaps, overlaps), ([], []))


class RoleCoverageTests(unittest.TestCase):
    def test_full_profile_covers_every_required_role(self):
        self.assertEqual(missing_roles(validate_phase_set(full_profile()), REQUIRED), [])

    def test_missing_post_landing_is_reported(self):
        phases = [p for p in full_profile() if p["role"] != ROLE_POST_LANDING]
        self.assertEqual(
            missing_roles(validate_phase_set(phases), REQUIRED), [ROLE_POST_LANDING]
        )

    def test_unknown_required_role_rejected(self):
        with self.assertRaises(ValueError):
            missing_roles(validate_phase_set(full_profile()), ["loitering"])

    def test_empty_required_roles_rejected(self):
        with self.assertRaises(ValueError):
            missing_roles(validate_phase_set(full_profile()), [])


class EnvironmentCompletenessTests(unittest.TestCase):
    def test_complete_orbital_phase_has_no_missing_inputs(self):
        p = validate_phase(phase("cruise", ROLE_OPERATIONAL, 0.0, 5.0, ORBITAL_ENV))
        self.assertEqual(missing_environment_inputs(p), [])

    def test_ascent_phase_needs_aerothermal_heating(self):
        p = validate_phase(
            phase("ascent", ROLE_ASCENT, 0.0, 0.2,
                  {"sink_temperature_k": 330.0, "conducted_interface_w": 3.0})
        )
        self.assertIn("aerothermal_flux_w_m2", missing_environment_inputs(p))

    def test_orbital_set_on_a_ground_phase_still_misses_the_ambient(self):
        p = validate_phase(phase("hangar", ROLE_GROUND, 0.0, 5.0, ORBITAL_ENV))
        self.assertEqual(missing_environment_inputs(p), ["ambient_temperature_k"])

    def test_docked_phase_needs_the_partner_interface(self):
        p = validate_phase(phase("berthed", ROLE_DOCKED, 0.0, 5.0, ORBITAL_ENV))
        self.assertEqual(missing_environment_inputs(p), ["partner_interface_w"])

    def test_empty_environment_reports_every_demanded_input(self):
        p = validate_phase(phase("cruise", ROLE_OPERATIONAL, 0.0, 5.0, {}))
        self.assertEqual(len(missing_environment_inputs(p)), 5)


class SinkEnvelopeTests(unittest.TestCase):
    def test_envelope_attributes_both_ends(self):
        env = sink_envelope(validate_phase_set(full_profile()))
        self.assertAlmostEqual(env["minimum_k"], 120.0, places=9)
        self.assertEqual(env["minimum_phase"], "berthed")
        self.assertAlmostEqual(env["maximum_k"], 340.0, places=9)
        self.assertEqual(env["maximum_phase"], "entry")

    def test_envelope_extreme_can_belong_to_an_atmospheric_phase(self):
        env = sink_envelope(validate_phase_set(full_profile()))
        self.assertNotEqual(env["maximum_phase"], "cruise")

    def test_no_declared_sink_gives_no_envelope(self):
        p = phase("cruise", ROLE_OPERATIONAL, 0.0, 5.0, {"conducted_interface_w": 1.0})
        self.assertIsNone(sink_envelope(validate_phase_set([p])))


class DefineMissionTests(unittest.TestCase):
    def test_complete_profile_is_complete(self):
        result = define_mission_thermal_environment(
            {"phases": full_profile(), "required_roles": REQUIRED}
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["phase_count"], 7)

    def test_covered_hours_equal_the_span_when_contiguous(self):
        result = define_mission_thermal_environment(
            {"phases": full_profile(), "required_roles": REQUIRED}
        )
        self.assertAlmostEqual(result["covered_h"], result["span_h"], places=9)
        self.assertAlmostEqual(result["uncovered_h"], 0.0, places=9)

    def test_gap_shows_up_as_uncovered_hours(self):
        phases = full_profile()
        phases[3]["start_h"] = 120.0
        result = define_mission_thermal_environment(
            {"phases": phases, "required_roles": REQUIRED}
        )
        self.assertAlmostEqual(result["uncovered_h"], 9.8, places=9)
        self.assertFalse(result["complete"])

    def test_profile_starting_at_liftoff_is_incomplete(self):
        phases = [p for p in full_profile() if p["role"] not in ("ground", "pre-launch")]
        result = define_mission_thermal_environment(
            {"phases": phases, "required_roles": REQUIRED}
        )
        self.assertFalse(result["complete"])
        self.assertIn("ground", result["missing_roles"])

    def test_phase_with_no_environment_is_not_ready_for_analysis(self):
        phases = full_profile()
        phases[2]["environment"] = {}
        result = define_mission_thermal_environment(
            {"phases": phases, "required_roles": REQUIRED}
        )
        record = [r for r in result["phases"] if r["name"] == "ascent"][0]
        self.assertFalse(record["ready_for_analysis"])
        self.assertTrue(any("environment inputs missing" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            define_mission_thermal_environment({"phases": full_profile()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            define_mission_thermal_environment(["phases"])


if __name__ == "__main__":
    unittest.main()
