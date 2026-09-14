"""Contract tests for the clause 6.3.1 class 3 purchasing-control logic."""

import unittest

from q6013_class_3_procurement_overview_logic import (
    ASSURANCE_TOLERANCE,
    BASE_CONTROL_MINIMA,
    CHANNEL_CONTROL_MINIMA,
    RIGOUR_LADDER,
    SUPPLY_CHANNELS,
    assess_class3_procurement,
    assurance_index,
    collect_declarations,
    control_register,
    effective_rigour,
    grade_purchasing_control,
    rigour_index,
    validate_assurance_policy,
    validate_channel,
    validate_control_declaration,
)

POLICY = {"assurance_floor": 0.8}


def _declared(control, rigour="project-verified", evidence="PO-3310 receipt file"):
    return {"control": control, "rigour": rigour, "evidence": evidence}


def _full(channel="manufacturer-direct", rigour="project-verified"):
    return [_declared(name, rigour) for name, _ in control_register(channel)]


def _case(**overrides):
    case = {
        "policy": dict(POLICY),
        "supply_channel": "manufacturer-direct",
        "declarations": _full(),
    }
    case.update(overrides)
    return case


class LadderTests(unittest.TestCase):
    def test_ladder_is_ordered_weakest_first(self):
        self.assertEqual(rigour_index("not-performed"), 0)
        self.assertLess(rigour_index("supplier-declared"), rigour_index("project-verified"))

    def test_rigour_returned_normalized(self):
        self.assertEqual(rigour_index("Project Recorded"), RIGOUR_LADDER.index("project-recorded"))

    def test_rigour_off_the_ladder_rejected(self):
        with self.assertRaises(ValueError):
            rigour_index("about right")

    def test_blank_rigour_rejected(self):
        with self.assertRaises(ValueError):
            rigour_index("   ")


class ChannelTests(unittest.TestCase):
    def test_channel_returned_normalized(self):
        self.assertEqual(validate_channel("Open Market Broker"), "open-market-broker")

    def test_undeclared_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(None)

    def test_unrecognized_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel("a marketplace listing")

    def test_every_channel_has_a_register_entry(self):
        for channel in SUPPLY_CHANNELS:
            self.assertIn(channel, CHANNEL_CONTROL_MINIMA)


class RegisterTests(unittest.TestCase):
    def test_direct_channel_carries_the_base_register_only(self):
        self.assertEqual(control_register("manufacturer-direct"), tuple(BASE_CONTROL_MINIMA))

    def test_open_market_register_is_the_largest(self):
        sizes = {c: len(control_register(c)) for c in SUPPLY_CHANNELS}
        self.assertEqual(max(sizes, key=lambda c: sizes[c]), "open-market-broker")

    def test_independent_distributor_adds_the_counterfeit_control(self):
        names = [n for n, _ in control_register("independent-distributor")]
        self.assertIn("counterfeit-avoidance-screening-performed", names)

    def test_no_control_is_repeated_in_any_register(self):
        for channel in SUPPLY_CHANNELS:
            names = [n for n, _ in control_register(channel)]
            self.assertEqual(len(set(names)), len(names), channel)

    def test_no_minimum_sits_at_the_not_performed_level(self):
        for channel in SUPPLY_CHANNELS:
            for _, minimum in control_register(channel):
                self.assertGreater(rigour_index(minimum), 0)


class PolicyTests(unittest.TestCase):
    def test_floor_returned_as_a_float(self):
        self.assertAlmostEqual(validate_assurance_policy(dict(POLICY))["assurance_floor"], 0.8, places=9)

    def test_zero_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_policy({"assurance_floor": 0.0})

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_policy({"assurance_floor": 1.4})

    def test_missing_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_assurance_policy({})


class DeclarationTests(unittest.TestCase):
    def test_declaration_returned_normalized(self):
        record = validate_control_declaration(
            {"control": "Receipt Record Kept On The Order", "rigour": "Project Recorded",
             "evidence": "GRN 8812"}
        )
        self.assertEqual(record["control"], "receipt-record-kept-on-the-order")
        self.assertEqual(record["claimed_rigour"], "project-recorded")

    def test_missing_rigour_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_declaration({"control": "receipt-record-kept-against-the-order"})

    def test_non_string_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_control_declaration(
                {"control": "date-code-band-requested-on-the-order",
                 "rigour": "project-recorded", "evidence": 11}
            )

    def test_repeated_declaration_rejected(self):
        with self.assertRaises(ValueError):
            collect_declarations([_declared("date-code-band-requested-on-the-order"),
                                  _declared("date-code-band-requested-on-the-order")])

    def test_non_sequence_declarations_rejected(self):
        with self.assertRaises(ValueError):
            collect_declarations(_declared("date-code-band-requested-on-the-order"))


class DemotionTests(unittest.TestCase):
    def test_evidenced_claim_keeps_its_rigour(self):
        reached, demoted = effective_rigour(
            validate_control_declaration(_declared("receipt-record-kept-against-the-order"))
        )
        self.assertEqual(reached, RIGOUR_LADDER.index("project-verified"))
        self.assertFalse(demoted)

    def test_unevidenced_claim_is_demoted_to_a_supplier_declaration(self):
        reached, demoted = effective_rigour(
            validate_control_declaration(
                _declared("receipt-record-kept-against-the-order", evidence="")
            )
        )
        self.assertEqual(reached, RIGOUR_LADDER.index("supplier-declared"))
        self.assertTrue(demoted)

    def test_supplier_declared_claim_is_not_demoted_further(self):
        reached, demoted = effective_rigour(
            validate_control_declaration(
                _declared("receipt-record-kept-against-the-order",
                          rigour="supplier-declared", evidence="")
            )
        )
        self.assertEqual(reached, RIGOUR_LADDER.index("supplier-declared"))
        self.assertFalse(demoted)

    def test_non_mapping_declaration_rejected_by_effective_rigour(self):
        with self.assertRaises(ValueError):
            effective_rigour("project-verified")


class GradingTests(unittest.TestCase):
    def test_control_at_its_minimum_is_met_with_full_credit(self):
        graded = grade_purchasing_control(
            "date-code-band-requested-on-the-order",
            "project-recorded",
            validate_control_declaration(
                _declared("date-code-band-requested-on-the-order", "project-recorded")
            ),
        )
        self.assertEqual(graded["state"], "met")
        self.assertAlmostEqual(graded["credit"], 1.0, places=9)

    def test_control_above_its_minimum_is_credited_no_more_than_one(self):
        graded = grade_purchasing_control(
            "packaging-and-esd-condition-stated-on-the-order",
            "supplier-declared",
            validate_control_declaration(
                _declared("packaging-and-esd-condition-stated-on-the-order")
            ),
        )
        self.assertAlmostEqual(graded["credit"], 1.0, places=9)

    def test_undeclared_control_is_not_performed(self):
        graded = grade_purchasing_control(
            "counterfeit-avoidance-screening-performed", "project-verified", None
        )
        self.assertEqual(graded["state"], "not-performed")
        self.assertAlmostEqual(graded["credit"], 0.0, places=9)

    def test_short_control_is_credited_by_the_rigour_ratio(self):
        graded = grade_purchasing_control(
            "counterfeit-avoidance-screening-performed",
            "project-verified",
            validate_control_declaration(
                _declared("counterfeit-avoidance-screening-performed", "project-recorded")
            ),
        )
        self.assertEqual(graded["state"], "short")
        self.assertAlmostEqual(graded["credit"], 2.0 / 3.0, places=9)
        self.assertIn("project-verified", graded["reason"])

    def test_demotion_is_named_in_the_reason(self):
        graded = grade_purchasing_control(
            "counterfeit-avoidance-screening-performed",
            "project-verified",
            validate_control_declaration(
                _declared("counterfeit-avoidance-screening-performed", evidence="")
            ),
        )
        self.assertTrue(graded["demoted"])
        self.assertIn("no evidence cited", graded["reason"])

    def test_minimum_at_the_not_performed_level_rejected(self):
        with self.assertRaises(ValueError):
            grade_purchasing_control("some-control", "not-performed", None)

    def test_empty_graded_register_rejected(self):
        with self.assertRaises(ValueError):
            assurance_index([])


class AssessmentTests(unittest.TestCase):
    def test_fully_verified_direct_order_is_acceptable(self):
        result = assess_class3_procurement(_case())
        self.assertEqual(result["verdict"], "purchasing controls meet class 3 expectations")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["figures"]["assurance_index"], 1.0, places=9)

    def test_direct_register_applied_to_a_broker_order_leaves_controls_unperformed(self):
        result = assess_class3_procurement(
            _case(supply_channel="open-market-broker", declarations=_full("manufacturer-direct"))
        )
        self.assertEqual(result["verdict"], "purchasing control not performed")
        self.assertEqual(len(result["controls_not_performed"]), 4)

    def test_undeclared_channel_refused_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            assess_class3_procurement(_case(supply_channel=None))

    def test_no_declaration_at_all_closes_on_not_declared(self):
        result = assess_class3_procurement(_case(declarations=[]))
        self.assertEqual(result["verdict"], "purchasing controls not declared")

    def test_extraneous_declaration_is_its_own_finding(self):
        declarations = _full() + [_declared("counterfeit-avoidance-screening-performed")]
        result = assess_class3_procurement(_case(declarations=declarations))
        self.assertEqual(result["extraneous_declarations"],
                         ["counterfeit-avoidance-screening-performed"])
        self.assertTrue(any("does not carry" in f for f in result["findings"]))

    def test_supplier_declared_order_falls_short_of_the_recorded_minima(self):
        result = assess_class3_procurement(_case(declarations=_full(rigour="supplier-declared")))
        self.assertEqual(result["verdict"], "purchasing control below its required rigour")
        self.assertEqual(len(result["controls_short"]), 4)
        self.assertAlmostEqual(result["figures"]["assurance_index"], 0.6, places=9)

    def test_index_exactly_on_the_floor_raises_no_floor_finding(self):
        result = assess_class3_procurement(
            _case(policy={"assurance_floor": 0.6},
                  declarations=_full(rigour="supplier-declared"))
        )
        self.assertAlmostEqual(result["figures"]["assurance_index"],
                               result["policy"]["assurance_floor"], places=9)
        self.assertFalse(any("below the declared floor" in f for f in result["findings"]))

    def test_every_unperformed_control_is_named_not_only_the_first(self):
        result = assess_class3_procurement(
            _case(supply_channel="open-market-broker", declarations=[])
        )
        self.assertEqual(len(result["controls_not_performed"]), 9)
        self.assertEqual(result["verdict"], "purchasing controls not declared")

    def test_demoted_claims_are_reported_separately(self):
        declarations = [
            _declared(name, "project-verified", "")
            for name, _ in control_register("manufacturer-direct")
        ]
        result = assess_class3_procurement(_case(declarations=declarations))
        self.assertEqual(len(result["demoted_claims"]), 5)
        self.assertEqual(len(result["controls_short"]), 4)
        self.assertNotIn("packaging-and-esd-condition-stated-on-the-order",
                         result["controls_short"])

    def test_register_size_follows_the_channel(self):
        result = assess_class3_procurement(
            _case(supply_channel="open-market-broker", declarations=_full("open-market-broker"))
        )
        self.assertEqual(result["figures"]["register_size"], 9)
        self.assertTrue(result["acceptable"])

    def test_missing_case_key_rejected(self):
        case = _case()
        del case["declarations"]
        with self.assertRaises(ValueError):
            assess_class3_procurement(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_class3_procurement(["policy"])

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(ASSURANCE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
