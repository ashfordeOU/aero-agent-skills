"""Contract tests for the clause 5.9.1 test-centre safety-programme logic."""

import unittest

from q2007_safety_programme_logic import (
    CONSEQUENCE_RANK,
    CONTROL_RANK,
    DESIGN_CONTROL_MAX_RANK,
    FRACTION_TOLERANCE,
    LIKELIHOOD_RANK,
    REVIEW_MIN,
    UNACCEPTABLE_MIN,
    UNDESIRABLE_MIN,
    assess_hazard,
    assess_organization,
    assess_safety_programme,
    assess_scenario,
    control_rank,
    drill_status,
    risk_acceptance,
    risk_index,
)

HAZARD = {
    "id": "HZ-04",
    "consequence": "marginal",
    "likelihood": "remote",
    "controls": ["engineered-control", "procedure"],
    "control_verified": True,
}

SCENARIO = {
    "name": "propellant spill in the cleanroom",
    "interval_days": 180,
    "elapsed_days": 90,
    "response_plan": True,
    "reporting_route": "centre safety officer and national authority",
}

ORG = {
    "safety_officer": "centre safety officer",
    "reports_to": "centre management",
    "trained_staff": 8,
    "staff_on_shift": 8,
    "required_trained_fraction": 1.0,
    "deputy_appointed": True,
}


def hazard(**overrides):
    out = dict(HAZARD)
    out.update(overrides)
    return out


def scenario(**overrides):
    out = dict(SCENARIO)
    out.update(overrides)
    return out


def org(**overrides):
    out = dict(ORG)
    out.update(overrides)
    return out


class RiskIndexTests(unittest.TestCase):
    def test_worst_pair_is_twenty(self):
        self.assertEqual(risk_index("catastrophic", "frequent"), 20)

    def test_best_pair_is_one(self):
        self.assertEqual(risk_index("negligible", "improbable"), 1)

    def test_index_is_the_product_of_the_ranks(self):
        self.assertEqual(
            risk_index("critical", "occasional"),
            CONSEQUENCE_RANK["critical"] * LIKELIHOOD_RANK["occasional"],
        )

    def test_unknown_consequence_rejected(self):
        with self.assertRaises(ValueError):
            risk_index("severe", "remote")

    def test_unknown_likelihood_rejected(self):
        with self.assertRaises(ValueError):
            risk_index("critical", "sometimes")

    def test_acceptance_bands_are_inclusive(self):
        self.assertEqual(risk_acceptance(UNACCEPTABLE_MIN), "unacceptable")
        self.assertEqual(risk_acceptance(UNACCEPTABLE_MIN - 1), "undesirable")
        self.assertEqual(risk_acceptance(UNDESIRABLE_MIN), "undesirable")
        self.assertEqual(risk_acceptance(UNDESIRABLE_MIN - 1), "acceptable-with-review")
        self.assertEqual(risk_acceptance(REVIEW_MIN), "acceptable-with-review")
        self.assertEqual(risk_acceptance(REVIEW_MIN - 1), "acceptable")

    def test_index_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            risk_acceptance(21)

    def test_non_integer_index_rejected(self):
        with self.assertRaises(ValueError):
            risk_acceptance(12.0)


class ControlTests(unittest.TestCase):
    def test_elimination_is_the_strongest(self):
        self.assertEqual(control_rank("elimination"), min(CONTROL_RANK.values()))

    def test_protective_equipment_is_the_weakest(self):
        self.assertEqual(
            control_rank("protective-equipment"), max(CONTROL_RANK.values())
        )

    def test_interlock_counts_as_an_engineered_control(self):
        self.assertEqual(control_rank("interlock"), control_rank("engineered-control"))

    def test_unknown_control_rejected(self):
        with self.assertRaises(ValueError):
            control_rank("vigilance")


class HazardTests(unittest.TestCase):
    def test_controlled_hazard_has_no_findings(self):
        record = assess_hazard(hazard())
        self.assertTrue(record["controlled"])
        self.assertEqual(record["acceptance"], "acceptable-with-review")

    def test_unacceptable_band_is_a_finding(self):
        record = assess_hazard(
            hazard(consequence="catastrophic", likelihood="probable")
        )
        self.assertEqual(record["acceptance"], "unacceptable")
        self.assertFalse(record["controlled"])

    def test_severe_hazard_on_a_procedure_alone_is_a_finding(self):
        record = assess_hazard(
            hazard(consequence="critical", likelihood="improbable", controls=["procedure"])
        )
        self.assertEqual(record["strongest_control_rank"], CONTROL_RANK["procedure"])
        self.assertFalse(record["controlled"])

    def test_severe_hazard_with_a_design_control_passes(self):
        record = assess_hazard(
            hazard(
                consequence="critical",
                likelihood="improbable",
                controls=["interlock", "procedure"],
            )
        )
        self.assertLessEqual(record["strongest_control_rank"], DESIGN_CONTROL_MAX_RANK)
        self.assertTrue(record["controlled"])

    def test_unverified_control_on_a_severe_hazard_is_a_finding(self):
        record = assess_hazard(
            hazard(
                consequence="critical",
                likelihood="improbable",
                controls=["interlock"],
                control_verified=False,
            )
        )
        self.assertFalse(record["controlled"])

    def test_unverified_control_on_a_mild_hazard_is_accepted(self):
        record = assess_hazard(hazard(control_verified=False))
        self.assertTrue(record["controlled"])

    def test_hazard_with_no_control_rejected(self):
        with self.assertRaises(ValueError):
            assess_hazard(hazard(controls=[]))

    def test_blank_hazard_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_hazard(hazard(id=" "))

    def test_non_boolean_verification_rejected(self):
        with self.assertRaises(ValueError):
            assess_hazard(hazard(control_verified="yes"))


class DrillTests(unittest.TestCase):
    def test_inside_the_interval_is_current(self):
        self.assertEqual(drill_status(180, 90), "current")

    def test_exactly_on_the_interval_is_due(self):
        self.assertEqual(drill_status(180, 180), "due")

    def test_past_the_interval_is_overdue(self):
        self.assertEqual(drill_status(180, 200), "overdue")

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            drill_status(0, 10)

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            drill_status(180, -1)

    def test_non_integer_interval_rejected(self):
        with self.assertRaises(ValueError):
            drill_status(180.0, 10)


class ScenarioTests(unittest.TestCase):
    def test_prepared_scenario_has_no_findings(self):
        self.assertTrue(assess_scenario(scenario())["prepared"])

    def test_missing_response_plan_is_a_finding(self):
        self.assertFalse(assess_scenario(scenario(response_plan=False))["prepared"])

    def test_overdue_drill_is_a_finding(self):
        record = assess_scenario(scenario(elapsed_days=400))
        self.assertEqual(record["drill_status"], "overdue")
        self.assertFalse(record["prepared"])

    def test_due_drill_is_not_yet_a_finding(self):
        record = assess_scenario(scenario(elapsed_days=180))
        self.assertEqual(record["drill_status"], "due")
        self.assertTrue(record["prepared"])

    def test_missing_reporting_route_is_a_finding(self):
        self.assertFalse(assess_scenario(scenario(reporting_route=None))["prepared"])

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_scenario(scenario(name=""))


class OrganizationTests(unittest.TestCase):
    def test_sound_organization_has_no_findings(self):
        self.assertTrue(assess_organization(org())["adequate"])

    def test_no_officer_is_a_finding(self):
        self.assertFalse(assess_organization(org(safety_officer=None))["adequate"])

    def test_officer_inside_the_execution_line_is_not_independent(self):
        record = assess_organization(org(reports_to="test conductor"))
        self.assertFalse(record["independent"])
        self.assertFalse(record["adequate"])

    def test_no_deputy_is_a_finding(self):
        self.assertFalse(assess_organization(org(deputy_appointed=False))["adequate"])

    def test_trained_fraction_exactly_on_the_requirement_passes(self):
        record = assess_organization(
            org(trained_staff=6, staff_on_shift=8, required_trained_fraction=0.75)
        )
        self.assertAlmostEqual(record["trained_fraction"], 0.75, places=9)
        self.assertTrue(record["adequate"])

    def test_short_training_coverage_is_a_finding(self):
        record = assess_organization(
            org(trained_staff=4, staff_on_shift=8, required_trained_fraction=0.75)
        )
        self.assertFalse(record["adequate"])

    def test_more_trained_than_on_shift_rejected(self):
        with self.assertRaises(ValueError):
            assess_organization(org(trained_staff=9, staff_on_shift=8))

    def test_empty_shift_rejected(self):
        with self.assertRaises(ValueError):
            assess_organization(org(trained_staff=0, staff_on_shift=0))

    def test_required_fraction_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_organization(org(required_trained_fraction=1.2))


class ProgrammeTests(unittest.TestCase):
    def spec(self, **overrides):
        out = {
            "organization": org(),
            "hazards": [hazard()],
            "scenarios": [scenario()],
        }
        out.update(overrides)
        return out

    def test_sound_programme_has_no_findings(self):
        result = assess_safety_programme(self.spec())
        self.assertTrue(result["programme_sound"])
        self.assertEqual(result["unacceptable_count"], 0)

    def test_worst_index_drives_the_headline_band(self):
        result = assess_safety_programme(
            self.spec(
                hazards=[
                    hazard(),
                    hazard(id="HZ-05", consequence="catastrophic", likelihood="frequent"),
                ]
            )
        )
        self.assertEqual(result["worst_risk_index"], 20)
        self.assertEqual(result["worst_acceptance"], "unacceptable")
        self.assertEqual(result["unacceptable_count"], 1)

    def test_overdue_drill_is_counted_and_blocks(self):
        result = assess_safety_programme(
            self.spec(scenarios=[scenario(elapsed_days=400)])
        )
        self.assertEqual(result["overdue_drill_count"], 1)
        self.assertFalse(result["programme_sound"])

    def test_organization_finding_propagates(self):
        result = assess_safety_programme(self.spec(organization=org(safety_officer=None)))
        self.assertFalse(result["programme_sound"])

    def test_duplicate_hazard_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_programme(self.spec(hazards=[hazard(), hazard()]))

    def test_empty_hazard_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_programme(self.spec(hazards=[]))

    def test_missing_key_rejected(self):
        bad = self.spec()
        del bad["scenarios"]
        with self.assertRaises(ValueError):
            assess_safety_programme(bad)

    def test_tolerance_is_representation_sized(self):
        self.assertAlmostEqual(FRACTION_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
