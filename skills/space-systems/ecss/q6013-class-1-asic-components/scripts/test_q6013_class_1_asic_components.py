"""Contract tests for the clause 4.6.2 class 1 ASIC routing and reuse grading.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: an unknown device kind, a missing
application record, an absent heritage record, a foundry or node change, a
temperature envelope the heritage never covered, and a dose margin that lands
exactly on the factor.
"""

import unittest

from q6013_class_1_asic_components_logic import (
    ASIC_KINDS,
    DEFAULT_REUSE_POLICY,
    GENERIC_COMPONENT_ROUTE,
    HERITAGE_ACTIVITIES,
    MICROELECTRONICS_STANDARD_ROUTE,
    NEW_DEVELOPMENT_REQUIRED,
    NOT_AN_ASIC,
    REUSE_ACCEPTED,
    REUSE_WITH_REOPENED_ACTIVITIES,
    assess_asic_route,
    dose_adequate,
    dose_margin_ratio,
    heritage_deltas,
    reopened_activities,
    required_dose_krad,
    reuse_credit,
    route_for_kind,
    temperature_envelope_covered,
    validate_design_record,
    validate_reuse_policy,
)


def _design(**overrides):
    record = {
        "foundry": "foundry-alpha",
        "process_node_nm": 65.0,
        "package": "cqfp-256",
        "design_revision": "rev-c",
        "temperature_range_c": (-55.0, 125.0),
        "total_dose_krad": 100.0,
    }
    record.update(overrides)
    return record


def _policy(**overrides):
    policy = dict(DEFAULT_REUSE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "kind": "standard-cell-asic",
        "heritage": _design(),
        "application": _design(total_dose_krad=50.0),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        settings = validate_reuse_policy(None)
        self.assertAlmostEqual(settings["dose_margin_factor"], 2.0, places=9)

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_policy({"dose_margin": 2.0})

    def test_margin_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_policy({"dose_margin_factor": 0.5})

    def test_negative_temperature_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_reuse_policy({"temperature_tolerance_c": -1.0})


class RoutingTests(unittest.TestCase):
    def test_every_application_specific_kind_takes_the_microelectronics_route(self):
        for kind in ASIC_KINDS:
            self.assertEqual(route_for_kind(kind), MICROELECTRONICS_STANDARD_ROUTE)

    def test_standard_microcircuit_stays_on_the_generic_route(self):
        self.assertEqual(route_for_kind("standard-microcircuit"), GENERIC_COMPONENT_ROUTE)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            route_for_kind("mystery-part")

    def test_blank_kind_rejected(self):
        with self.assertRaises(ValueError):
            route_for_kind("   ")

    def test_generic_kind_gives_the_not_an_asic_verdict(self):
        result = assess_asic_route({"kind": "passive-component"})
        self.assertEqual(result["verdict"], NOT_AN_ASIC)
        self.assertEqual(result["route"], GENERIC_COMPONENT_ROUTE)


class DoseTests(unittest.TestCase):
    def test_required_dose_applies_the_factor(self):
        self.assertAlmostEqual(required_dose_krad(50.0, 2.0), 100.0, places=9)

    def test_dose_exactly_on_the_factor_is_adequate(self):
        self.assertTrue(dose_adequate(100.0, 50.0, 2.0))

    def test_dose_below_the_factor_is_not_adequate(self):
        self.assertFalse(dose_adequate(99.0, 50.0, 2.0))

    def test_dose_margin_ratio_is_reported(self):
        self.assertAlmostEqual(dose_margin_ratio(100.0, 40.0), 2.5, places=9)

    def test_zero_mission_dose_rejected(self):
        with self.assertRaises(ValueError):
            dose_margin_ratio(100.0, 0.0)


class EnvelopeTests(unittest.TestCase):
    def test_wider_heritage_envelope_covers_the_application(self):
        self.assertTrue(temperature_envelope_covered((-55.0, 125.0), (-40.0, 85.0)))

    def test_identical_envelope_is_covered(self):
        self.assertTrue(temperature_envelope_covered((-40.0, 85.0), (-40.0, 85.0)))

    def test_cold_shortfall_is_not_covered(self):
        self.assertFalse(temperature_envelope_covered((-40.0, 125.0), (-55.0, 85.0)))

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            temperature_envelope_covered((125.0, -55.0), (-40.0, 85.0))


class RecordTests(unittest.TestCase):
    def test_record_without_foundry_rejected(self):
        record = _design()
        record["foundry"] = ""
        with self.assertRaises(ValueError):
            validate_design_record(record, "heritage record")

    def test_record_with_non_numeric_node_rejected(self):
        record = _design(process_node_nm="65nm")
        with self.assertRaises(ValueError):
            validate_design_record(record, "heritage record")

    def test_record_with_negative_dose_rejected(self):
        record = _design(total_dose_krad=-10.0)
        with self.assertRaises(ValueError):
            validate_design_record(record, "heritage record")


class DeltaTests(unittest.TestCase):
    def test_an_identical_design_opens_nothing(self):
        self.assertEqual(heritage_deltas(_design(), _design(total_dose_krad=50.0)), [])

    def test_a_foundry_change_reopens_process_qualification(self):
        deltas = heritage_deltas(
            _design(), _design(foundry="foundry-beta", total_dose_krad=50.0)
        )
        self.assertEqual(reopened_activities(deltas), ("process-qualification",))

    def test_a_node_change_reopens_timing_characterization(self):
        deltas = heritage_deltas(
            _design(), _design(process_node_nm=28.0, total_dose_krad=50.0)
        )
        self.assertEqual(reopened_activities(deltas), ("timing-characterization",))

    def test_activities_are_reported_in_the_declared_order(self):
        deltas = heritage_deltas(
            _design(),
            _design(package="bga-625", foundry="foundry-beta", total_dose_krad=50.0),
        )
        self.assertEqual(
            reopened_activities(deltas),
            ("process-qualification", "package-qualification"),
        )

    def test_a_delta_without_an_activity_rejected(self):
        with self.assertRaises(ValueError):
            reopened_activities([{"attribute": "foundry"}])


class CreditTests(unittest.TestCase):
    def test_no_reopened_activity_gives_full_credit(self):
        self.assertAlmostEqual(reuse_credit(0), 1.0, places=9)

    def test_every_activity_reopened_gives_no_credit(self):
        self.assertAlmostEqual(reuse_credit(len(HERITAGE_ACTIVITIES)), 0.0, places=9)

    def test_credit_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            reuse_credit(len(HERITAGE_ACTIVITIES) + 1)


class AssessmentTests(unittest.TestCase):
    def test_clean_heritage_is_accepted_reuse(self):
        result = assess_asic_route(_case())
        self.assertEqual(result["verdict"], REUSE_ACCEPTED)
        self.assertEqual(result["route"], MICROELECTRONICS_STANDARD_ROUTE)
        self.assertAlmostEqual(result["reuse_credit"], 1.0, places=9)

    def test_absent_heritage_is_a_new_development(self):
        result = assess_asic_route(_case(heritage=None))
        self.assertEqual(result["verdict"], NEW_DEVELOPMENT_REQUIRED)
        self.assertEqual(len(result["reopened_activities"]), len(HERITAGE_ACTIVITIES))

    def test_two_deltas_still_read_as_reuse(self):
        result = assess_asic_route(
            _case(application=_design(
                foundry="foundry-beta", package="bga-625", total_dose_krad=50.0
            ))
        )
        self.assertEqual(result["verdict"], REUSE_WITH_REOPENED_ACTIVITIES)
        self.assertEqual(len(result["reopened_activities"]), 2)

    def test_three_deltas_collapse_into_a_new_development(self):
        result = assess_asic_route(
            _case(application=_design(
                foundry="foundry-beta",
                package="bga-625",
                design_revision="rev-d",
                total_dose_krad=50.0,
            ))
        )
        self.assertEqual(result["verdict"], NEW_DEVELOPMENT_REQUIRED)

    def test_dose_shortfall_reopens_radiation_verification(self):
        result = assess_asic_route(_case(application=_design(total_dose_krad=80.0)))
        self.assertIn("radiation-verification", result["reopened_activities"])

    def test_dose_landing_exactly_on_the_factor_does_not_reopen(self):
        result = assess_asic_route(_case(application=_design(total_dose_krad=50.0)))
        self.assertNotIn("radiation-verification", result["reopened_activities"])

    def test_reuse_credit_falls_with_each_reopened_activity(self):
        result = assess_asic_route(
            _case(application=_design(foundry="foundry-beta", total_dose_krad=50.0))
        )
        self.assertAlmostEqual(
            result["reuse_credit"],
            float(len(HERITAGE_ACTIVITIES) - 1) / float(len(HERITAGE_ACTIVITIES)),
            places=9,
        )

    def test_missing_application_record_rejected(self):
        case = _case()
        del case["application"]
        with self.assertRaises(ValueError):
            assess_asic_route(case)

    def test_missing_kind_rejected(self):
        case = _case()
        del case["kind"]
        with self.assertRaises(ValueError):
            assess_asic_route(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_route(["kind"])


if __name__ == "__main__":
    unittest.main()
