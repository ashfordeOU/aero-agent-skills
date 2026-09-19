"""Contract tests for the clause 10.1.2 buyer procurement methodology."""

import unittest

from q6012_procurement_methodology_steps_logic import (
    MANDATED_STEPS,
    TERMINALS,
    assess_procurement_methodology,
    build_method,
    dangling_targets,
    method_maturity_score,
    pass_chain,
    precondition_order_violations,
    reachable_steps,
    record_gaps,
    steps_without_fail_route,
    validate_step,
)

RECORD_OF = {name: "%s_record" % name for name in MANDATED_STEPS}


def full_steps():
    steps = []
    for index, name in enumerate(MANDATED_STEPS):
        nxt = MANDATED_STEPS[index + 1] if index + 1 < len(MANDATED_STEPS) else "complete"
        steps.append(
            {
                "step": name,
                "on_pass": nxt,
                "on_fail": "abandon" if index < 4 else "disposition",
                "produces": RECORD_OF[name],
                "requires": RECORD_OF[MANDATED_STEPS[index - 1]] if index else "",
            }
        )
    # 'disposition' is the last step; it must not send a failure back to itself.
    steps[-1]["on_fail"] = "abandon"
    return steps


def full_declaration(**overrides):
    declaration = {"steps": full_steps()}
    declaration.update(overrides)
    return declaration


class ValidateStepTests(unittest.TestCase):
    def test_step_name_is_folded(self):
        record = validate_step({"step": "Issue-Enquiry", "on_pass": "evaluate_offers",
                                "on_fail": "abandon"})
        self.assertEqual(record["step"], "issue_enquiry")

    def test_unrecognised_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step({"step": "haggle", "on_pass": "complete", "on_fail": "abandon"})

    def test_absent_step_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_step({"on_pass": "complete"})

    def test_blank_branch_is_kept_as_no_route(self):
        record = validate_step({"step": "disposition", "on_pass": "complete",
                                "on_fail": "   "})
        self.assertEqual(record["on_fail"], "")

    def test_non_text_produces_rejected(self):
        with self.assertRaises(ValueError):
            validate_step({"step": "disposition", "on_pass": "complete", "produces": 4})

    def test_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step(["disposition"])


class BuildMethodTests(unittest.TestCase):
    def test_entry_defaults_to_the_first_declared_step(self):
        method = build_method(full_steps())
        self.assertEqual(method["entry"], MANDATED_STEPS[0])

    def test_explicit_entry_is_honoured(self):
        method = build_method(full_steps(), entry="place_order")
        self.assertEqual(method["entry"], "place_order")

    def test_undeclared_entry_rejected(self):
        steps = [s for s in full_steps() if s["step"] != "disposition"]
        with self.assertRaises(ValueError):
            build_method(steps, entry="disposition")

    def test_repeated_step_rejected(self):
        steps = full_steps()
        steps.append(steps[0])
        with self.assertRaises(ValueError):
            build_method(steps)

    def test_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            build_method([])


class PassChainTests(unittest.TestCase):
    def test_full_method_walks_every_step_once(self):
        chain = pass_chain(build_method(full_steps()))
        self.assertEqual(chain["chain"], MANDATED_STEPS)
        self.assertFalse(chain["looped"])
        self.assertEqual(chain["ends_at"], "complete")

    def test_a_pass_branch_back_up_the_chain_is_a_loop(self):
        steps = full_steps()
        steps[-1]["on_pass"] = "place_order"
        chain = pass_chain(build_method(steps))
        self.assertTrue(chain["looped"])

    def test_terminals_are_the_two_declared_ends(self):
        self.assertEqual(set(TERMINALS), {"complete", "abandon"})


class ReachabilityTests(unittest.TestCase):
    def test_full_method_reaches_every_step(self):
        method = build_method(full_steps())
        self.assertEqual(reachable_steps(method), frozenset(MANDATED_STEPS))

    def test_a_step_nothing_points_at_is_unreachable(self):
        steps = full_steps()
        steps[2]["on_pass"] = "place_order"
        steps[2]["on_fail"] = "abandon"
        method = build_method(steps)
        self.assertNotIn("evaluate_offers", reachable_steps(method))

    def test_branch_to_an_undeclared_step_is_dangling(self):
        steps = full_steps()
        steps[0]["on_fail"] = "renegotiate"
        dangling = dangling_targets(build_method(steps))
        self.assertEqual(len(dangling), 1)
        self.assertEqual(dangling[0]["target"], "renegotiate")

    def test_full_method_has_no_dangling_branch(self):
        self.assertEqual(dangling_targets(build_method(full_steps())), ())


class FailRouteTests(unittest.TestCase):
    def test_full_method_gives_every_step_a_fail_route(self):
        self.assertEqual(steps_without_fail_route(build_method(full_steps())), ())

    def test_step_with_no_fail_route_is_named(self):
        steps = full_steps()
        steps[3]["on_fail"] = ""
        self.assertEqual(
            steps_without_fail_route(build_method(steps)), ("evaluate_offers",)
        )


class RecordTests(unittest.TestCase):
    def test_full_method_has_no_record_gap(self):
        gaps = record_gaps(build_method(full_steps()))
        self.assertEqual(gaps["steps_producing_no_record"], ())
        self.assertEqual(gaps["records_with_no_producer"], ())

    def test_step_producing_nothing_is_named(self):
        steps = full_steps()
        steps[5]["produces"] = ""
        gaps = record_gaps(build_method(steps))
        self.assertEqual(gaps["steps_producing_no_record"], ("monitor_fabrication",))

    def test_record_nobody_produces_is_named(self):
        steps = full_steps()
        steps[4]["requires"] = "credit_check_record"
        gaps = record_gaps(build_method(steps))
        self.assertEqual(gaps["records_with_no_producer"], ("credit_check_record",))

    def test_consuming_a_record_produced_later_is_an_order_fault(self):
        steps = full_steps()
        steps[1]["requires"] = RECORD_OF["place_order"]
        faults = precondition_order_violations(build_method(steps))
        self.assertEqual(len(faults), 1)
        self.assertEqual(faults[0]["step"], "survey_sources")
        self.assertEqual(faults[0]["produced_by"], "place_order")

    def test_full_method_has_no_order_fault(self):
        self.assertEqual(precondition_order_violations(build_method(full_steps())), ())


class MaturityTests(unittest.TestCase):
    def test_full_method_scores_one(self):
        maturity = method_maturity_score(build_method(full_steps()))
        self.assertAlmostEqual(maturity["score"], 1.0, places=9)
        self.assertAlmostEqual(maturity["step_coverage"], 1.0, places=9)
        self.assertAlmostEqual(maturity["reachability"], 1.0, places=9)

    def test_a_missing_fail_route_costs_a_quarter_of_one_step(self):
        steps = full_steps()
        steps[2]["on_fail"] = ""
        maturity = method_maturity_score(build_method(steps))
        expected = 1.0 - (1.0 / len(MANDATED_STEPS)) / 4.0
        self.assertAlmostEqual(maturity["score"], expected, places=9)

    def test_dropping_a_step_lowers_the_coverage_component(self):
        steps = [s for s in full_steps() if s["step"] != "witness_acceptance"]
        steps = [dict(s, on_pass="receive_and_verify")
                 if s["step"] == "monitor_fabrication" else s for s in steps]
        maturity = method_maturity_score(build_method(steps))
        expected = (len(MANDATED_STEPS) - 1) / len(MANDATED_STEPS)
        self.assertAlmostEqual(maturity["step_coverage"], expected, places=9)


class AssessmentTests(unittest.TestCase):
    def test_full_method_is_sound(self):
        result = assess_procurement_methodology(full_declaration())
        self.assertEqual(result["verdict"], "method-sound")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["fully_mature"])

    def test_dangling_branch_makes_the_method_unworkable(self):
        declaration = full_declaration()
        declaration["steps"][6]["on_fail"] = "escalate_to_board"
        result = assess_procurement_methodology(declaration)
        self.assertEqual(result["verdict"], "method-unworkable")

    def test_missing_step_makes_the_method_gapped(self):
        steps = [s for s in full_steps() if s["step"] != "survey_sources"]
        steps = [dict(s, on_pass="issue_enquiry") if s["step"] == "define_requirement"
                 else s for s in steps]
        steps = [dict(s, requires="") if s["step"] == "issue_enquiry" else s
                 for s in steps]
        result = assess_procurement_methodology({"steps": steps})
        self.assertEqual(result["verdict"], "method-gapped")
        self.assertIn("survey_sources", result["absent_steps"])

    def test_step_without_a_fail_route_is_reported(self):
        declaration = full_declaration()
        declaration["steps"][0]["on_fail"] = ""
        result = assess_procurement_methodology(declaration)
        self.assertIn("define_requirement", result["steps_without_fail_route"])
        self.assertEqual(result["verdict"], "method-gapped")

    def test_looping_pass_chain_is_unworkable(self):
        declaration = full_declaration()
        declaration["steps"][-1]["on_pass"] = "issue_enquiry"
        result = assess_procurement_methodology(declaration)
        self.assertTrue(result["pass_chain"]["looped"])
        self.assertEqual(result["verdict"], "method-unworkable")

    def test_missing_steps_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_methodology({"entry": "define_requirement"})

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_methodology("steps")


if __name__ == "__main__":
    unittest.main()
