#!/usr/bin/env python3
"""Gate 3 contract test for e20-power-robustness-clause-applicability."""

import unittest

from e20_power_robustness_clause_applicability_logic import (
    APPLICABLE,
    NOT_APPLICABLE,
    VIA_INTERFACE,
    assess_robustness_applicability,
    build_applicability_matrix,
    categorize_element_role,
    check_margin,
    governing_threshold,
    justification_finding,
    resolve_applicability,
    validate_element,
    validate_provision,
)

PARAM = "bus-overvoltage-withstand-v"


def provision(**overrides):
    base = {
        "provision_id": "ROB-01",
        "scope": "both",
        "parameter": PARAM,
        "required_withstand": 40.0,
    }
    base.update(overrides)
    return base


def element(**overrides):
    base = {
        "element_id": "PCDU",
        "role": "power-subsystem",
        "presents_power_payload_interface": True,
        "demonstrated": {PARAM: 50.0},
        "interface_demand": {PARAM: 45.0},
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "element_id": "INSTR-A",
        "role": "payload",
        "presents_power_payload_interface": True,
        "demonstrated": {PARAM: 46.0},
        "interface_demand": {},
    }
    base.update(overrides)
    return base


class ProvisionValidationTests(unittest.TestCase):
    def test_nominal_provision_validates(self):
        prov = validate_provision(provision())
        self.assertEqual(prov["scope"], "both")
        self.assertAlmostEqual(prov["required_withstand"], 40.0)

    def test_non_mapping_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision("ROB-01")

    def test_missing_provision_field_is_rejected(self):
        bad = provision()
        del bad["parameter"]
        with self.assertRaises(ValueError):
            validate_provision(bad)

    def test_blank_provision_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(provision(provision_id=" "))

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(provision(scope="platform"))

    def test_unknown_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(provision(parameter="bus-colour"))

    def test_non_positive_required_withstand_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_provision(provision(required_withstand=0.0))


class ElementValidationTests(unittest.TestCase):
    def test_nominal_element_validates(self):
        elem = validate_element(element())
        self.assertEqual(elem["element_id"], "PCDU")
        self.assertAlmostEqual(elem["demonstrated"][PARAM], 50.0)

    def test_missing_element_field_is_rejected(self):
        bad = element()
        del bad["interface_demand"]
        with self.assertRaises(ValueError):
            validate_element(bad)

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element(role="ground-segment"))

    def test_non_boolean_interface_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element(presents_power_payload_interface="yes"))

    def test_unknown_parameter_in_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element(demonstrated={"bus-colour": 1.0}))

    def test_negative_evidence_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element(demonstrated={PARAM: -1.0}))

    def test_non_mapping_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element(interface_demand=[45.0]))

    def test_role_categorization_returns_the_canonical_role(self):
        self.assertEqual(categorize_element_role(payload()), "payload")


class ApplicabilityTests(unittest.TestCase):
    def test_both_scope_reaches_the_power_subsystem(self):
        self.assertEqual(resolve_applicability(provision(), element()), APPLICABLE)

    def test_both_scope_reaches_the_payload(self):
        self.assertEqual(resolve_applicability(provision(), payload()), APPLICABLE)

    def test_power_scope_reaches_the_power_subsystem_directly(self):
        prov = provision(scope="power-subsystem")
        self.assertEqual(resolve_applicability(prov, element()), APPLICABLE)

    def test_power_scope_reaches_an_interfacing_payload_via_the_interface(self):
        prov = provision(scope="power-subsystem")
        self.assertEqual(resolve_applicability(prov, payload()), VIA_INTERFACE)

    def test_power_scope_misses_a_non_interfacing_payload(self):
        prov = provision(scope="power-subsystem")
        elem = payload(presents_power_payload_interface=False)
        self.assertEqual(resolve_applicability(prov, elem), NOT_APPLICABLE)

    def test_payload_scope_reaches_the_payload_directly(self):
        prov = provision(scope="payload")
        self.assertEqual(resolve_applicability(prov, payload()), APPLICABLE)

    def test_payload_scope_reaches_an_interfacing_power_subsystem(self):
        prov = provision(scope="payload")
        self.assertEqual(resolve_applicability(prov, element()), VIA_INTERFACE)

    def test_payload_scope_misses_a_non_interfacing_power_subsystem(self):
        prov = provision(scope="payload")
        elem = element(presents_power_payload_interface=False)
        self.assertEqual(resolve_applicability(prov, elem), NOT_APPLICABLE)

    def test_self_conditioning_payload_is_reached_by_every_scope(self):
        elem = payload(
            element_id="INSTR-B",
            role="payload-with-power-conditioning",
            presents_power_payload_interface=False,
        )
        for scope in ("both", "power-subsystem", "payload"):
            self.assertEqual(
                resolve_applicability(provision(scope=scope), elem), APPLICABLE
            )


class ThresholdTests(unittest.TestCase):
    def test_strictest_interface_demand_governs(self):
        value = governing_threshold(provision(), [element(), payload()])
        self.assertAlmostEqual(value, 45.0)

    def test_provision_figure_governs_when_no_demand_exceeds_it(self):
        elem = element(interface_demand={PARAM: 20.0})
        value = governing_threshold(provision(), [elem])
        self.assertAlmostEqual(value, 40.0)

    def test_demand_from_an_unreached_element_does_not_govern(self):
        prov = provision(scope="power-subsystem")
        far = payload(
            presents_power_payload_interface=False,
            interface_demand={PARAM: 90.0},
        )
        value = governing_threshold(prov, [element(), far])
        self.assertAlmostEqual(value, 45.0)

    def test_provision_reaching_nothing_is_rejected(self):
        prov = provision(scope="power-subsystem")
        far = payload(presents_power_payload_interface=False)
        with self.assertRaises(ValueError):
            governing_threshold(prov, [far])

    def test_empty_element_set_is_rejected(self):
        with self.assertRaises(ValueError):
            governing_threshold(provision(), [])


class MarginTests(unittest.TestCase):
    def test_capability_above_the_threshold_passes(self):
        result = check_margin(provision(), element(), 45.0)
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["margin_pct"], 11.111111, places=5)

    def test_capability_exactly_at_the_threshold_passes_with_zero_margin(self):
        result = check_margin(provision(), element(demonstrated={PARAM: 45.0}), 45.0)
        self.assertEqual(result["verdict"], "pass")
        self.assertAlmostEqual(result["margin_pct"], 0.0)

    def test_capability_below_the_threshold_fails(self):
        result = check_margin(provision(), element(demonstrated={PARAM: 36.0}), 45.0)
        self.assertEqual(result["verdict"], "fail")
        self.assertAlmostEqual(result["margin_pct"], -20.0)

    def test_absent_evidence_is_not_a_failed_margin(self):
        result = check_margin(provision(), element(demonstrated={}), 45.0)
        self.assertEqual(result["verdict"], "evidence-missing")
        self.assertIsNone(result["margin_pct"])

    def test_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            check_margin(provision(), element(), 0.0)


class RationaleTests(unittest.TestCase):
    def test_recorded_rationale_clears_the_exclusion(self):
        out = justification_finding(
            provision(), payload(), {"ROB-01/INSTR-A": "no bus-facing port"}
        )
        self.assertIsNone(out)

    def test_missing_rationale_raises_a_finding(self):
        out = justification_finding(provision(), payload(), {})
        self.assertEqual(out, "not-applicable-without-rationale:ROB-01/INSTR-A")

    def test_blank_rationale_raises_a_finding(self):
        out = justification_finding(provision(), payload(), {"ROB-01/INSTR-A": "   "})
        self.assertIsNotNone(out)

    def test_non_mapping_rationale_store_is_rejected(self):
        with self.assertRaises(ValueError):
            justification_finding(provision(), payload(), ["ROB-01/INSTR-A"])


class MatrixTests(unittest.TestCase):
    def test_matrix_has_one_row_per_pair(self):
        rows = build_applicability_matrix([provision()], [element(), payload()])
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["element_id"] for r in rows}, {"PCDU", "INSTR-A"})

    def test_duplicate_provision_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            build_applicability_matrix([provision(), provision()], [element()])

    def test_duplicate_element_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            build_applicability_matrix([provision()], [element(), element()])

    def test_empty_provision_list_is_rejected(self):
        with self.assertRaises(ValueError):
            build_applicability_matrix([], [element()])


class AssessmentTests(unittest.TestCase):
    def test_nominal_scoping_closes_with_full_coverage(self):
        out = assess_robustness_applicability([provision()], [element(), payload()])
        self.assertTrue(out["scoping_closed"])
        self.assertEqual(out["applicable_pairs"], 2)
        self.assertAlmostEqual(out["coverage_fraction"], 1.0)

    def test_short_capability_lowers_coverage_and_raises_a_finding(self):
        weak = payload(demonstrated={PARAM: 30.0})
        out = assess_robustness_applicability([provision()], [element(), weak])
        self.assertFalse(out["scoping_closed"])
        self.assertAlmostEqual(out["coverage_fraction"], 0.5)
        self.assertIn("fail:ROB-01/INSTR-A", out["findings"])

    def test_missing_evidence_is_reported_separately_from_a_failure(self):
        blind = payload(demonstrated={})
        out = assess_robustness_applicability([provision()], [element(), blind])
        self.assertIn("evidence-missing:ROB-01/INSTR-A", out["findings"])

    def test_unjustified_exclusion_is_a_finding(self):
        prov = provision(scope="power-subsystem")
        far = payload(presents_power_payload_interface=False)
        out = assess_robustness_applicability([prov], [element(), far])
        self.assertIn("not-applicable-without-rationale:ROB-01/INSTR-A", out["findings"])

    def test_justified_exclusion_closes_the_scoping(self):
        prov = provision(scope="power-subsystem")
        far = payload(presents_power_payload_interface=False)
        out = assess_robustness_applicability(
            [prov],
            [element(), far],
            {"ROB-01/INSTR-A": "instrument draws from a separately conditioned rail"},
        )
        self.assertTrue(out["scoping_closed"])
        self.assertEqual(out["applicable_pairs"], 1)

    def test_excluded_row_carries_no_margin(self):
        prov = provision(scope="power-subsystem")
        far = payload(presents_power_payload_interface=False)
        out = assess_robustness_applicability(
            [prov], [element(), far], {"ROB-01/INSTR-A": "out of scope"}
        )
        excluded = [r for r in out["rows"] if r["element_id"] == "INSTR-A"][0]
        self.assertEqual(excluded["verdict"], NOT_APPLICABLE)
        self.assertIsNone(excluded["margin_pct"])

    def test_non_mapping_rationale_store_is_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_robustness_applicability([provision()], [element()], "none")


if __name__ == "__main__":
    unittest.main()
