"""Contract test for the actuation-safety-barrier-architecture leaf."""

import unittest

from e2021_actuation_safety_barrier_architecture_logic import (
    BARRIER_FUNCTIONS,
    FINDING_BARRIER_RELEASED_BY_DEFAULT,
    FINDING_DEPTH_BELOW_REQUIREMENT,
    FINDING_NO_ENERGY_ISOLATION,
    FINDING_SHARED_COMMAND_DOMAIN,
    FINDING_SHARED_RELEASE_ELEMENT,
    REQUIRED_BARRIER_DEPTH,
    activation_depth,
    assess_barrier_architecture,
    depth_after_single_failure,
    energy_isolating_barriers,
    functions_covered,
    independence_findings,
    missing_functions,
    shared_command_domains,
    shared_release_elements,
    validate_architecture,
    validate_barrier,
)


def barrier(function, **kw):
    record = {
        "id": "B-%s" % function,
        "function": function,
        "release_element": "%s-switch" % function,
        "command_domain": "%s-command-domain" % function,
        "isolation_kind": "relay-contact",
        "default_state": "inhibited",
    }
    record.update(kw)
    return record


def good_architecture():
    return [barrier(f) for f in BARRIER_FUNCTIONS]


class TestValidateBarrier(unittest.TestCase):
    def test_energy_isolating_defaults_from_isolation_kind(self):
        norm = validate_barrier(barrier("arm", isolation_kind="series-power-switch"))
        self.assertTrue(norm["energy_isolating"])

    def test_logic_enable_is_not_energy_isolating_by_default(self):
        norm = validate_barrier(barrier("arm", isolation_kind="logic-enable"))
        self.assertFalse(norm["energy_isolating"])

    def test_default_state_defaults_to_inhibited(self):
        record = barrier("fire")
        del record["default_state"]
        self.assertEqual(validate_barrier(record)["default_state"], "inhibited")

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(["B-arm"])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(barrier("arm", id="   "))

    def test_unknown_function_raises(self):
        record = barrier("arm")
        record["function"] = "disarm"
        with self.assertRaises(ValueError):
            validate_barrier(record)

    def test_unknown_isolation_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(barrier("arm", isolation_kind="paint"))

    def test_unknown_default_state_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(barrier("arm", default_state="maybe"))

    def test_missing_release_element_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(barrier("arm", release_element=""))

    def test_non_boolean_energy_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_barrier(barrier("arm", energy_isolating="yes"))


class TestValidateArchitecture(unittest.TestCase):
    def test_normalizes_every_record(self):
        records = validate_architecture(good_architecture())
        self.assertEqual(len(records), 3)
        self.assertEqual([r["function"] for r in records], list(BARRIER_FUNCTIONS))

    def test_empty_architecture_raises(self):
        with self.assertRaises(ValueError):
            validate_architecture([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_architecture(barrier("arm"))

    def test_duplicate_id_raises(self):
        arch = good_architecture()
        arch[1]["id"] = arch[0]["id"]
        with self.assertRaises(ValueError):
            validate_architecture(arch)

    def test_duplicate_function_raises(self):
        arch = good_architecture()
        arch[2]["function"] = "arm"
        arch[2]["id"] = "B-arm-2"
        with self.assertRaises(ValueError):
            validate_architecture(arch)


class TestCoverage(unittest.TestCase):
    def test_full_coverage_reported_in_order(self):
        self.assertEqual(functions_covered(good_architecture()), BARRIER_FUNCTIONS)

    def test_missing_function_is_named(self):
        arch = [barrier("arm"), barrier("fire")]
        self.assertEqual(missing_functions(arch), ("select",))

    def test_nothing_missing_on_a_full_set(self):
        self.assertEqual(missing_functions(good_architecture()), ())


class TestIndependence(unittest.TestCase):
    def test_distinct_elements_share_nothing(self):
        self.assertEqual(shared_release_elements(good_architecture()), {})
        self.assertEqual(shared_command_domains(good_architecture()), {})

    def test_one_relay_releasing_two_barriers_is_reported(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        shared = shared_release_elements(arch)
        self.assertEqual(sorted(shared), ["arm-switch"])
        self.assertEqual(shared["arm-switch"], ["B-arm", "B-select"])

    def test_one_command_domain_ordering_two_barriers_is_reported(self):
        arch = good_architecture()
        arch[2]["command_domain"] = arch[0]["command_domain"]
        shared = shared_command_domains(arch)
        self.assertEqual(shared["arm-command-domain"], ["B-arm", "B-fire"])

    def test_findings_carry_the_shared_element_code(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        codes = [f["code"] for f in independence_findings(arch)]
        self.assertIn(FINDING_SHARED_RELEASE_ELEMENT, codes)

    def test_findings_carry_the_shared_domain_code(self):
        arch = good_architecture()
        arch[1]["command_domain"] = arch[0]["command_domain"]
        codes = [f["code"] for f in independence_findings(arch)]
        self.assertIn(FINDING_SHARED_COMMAND_DOMAIN, codes)

    def test_released_default_state_is_a_finding(self):
        arch = good_architecture()
        arch[0]["default_state"] = "released"
        codes = [f["code"] for f in independence_findings(arch)]
        self.assertIn(FINDING_BARRIER_RELEASED_BY_DEFAULT, codes)

    def test_clean_architecture_has_no_findings(self):
        self.assertEqual(independence_findings(good_architecture()), [])


class TestDepth(unittest.TestCase):
    def test_three_distinct_elements_give_depth_three(self):
        self.assertEqual(activation_depth(good_architecture()), 3)

    def test_shared_element_collapses_the_depth(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        self.assertEqual(activation_depth(arch), 2)

    def test_released_barrier_does_not_count_towards_depth(self):
        arch = good_architecture()
        arch[0]["default_state"] = "released"
        self.assertEqual(activation_depth(arch), 2)

    def test_single_failure_leaves_two_barriers(self):
        remaining, element = depth_after_single_failure(good_architecture())
        self.assertEqual(remaining, 2)
        self.assertIn(element, ("arm-switch", "select-switch", "fire-switch"))

    def test_single_failure_on_a_shared_element_leaves_one(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        remaining, element = depth_after_single_failure(arch)
        self.assertEqual(remaining, 1)
        self.assertEqual(element, "arm-switch")

    def test_all_released_leaves_no_depth(self):
        arch = [barrier(f, default_state="released") for f in BARRIER_FUNCTIONS]
        self.assertEqual(depth_after_single_failure(arch), (0, None))


class TestEnergyIsolation(unittest.TestCase):
    def test_relay_barriers_are_energy_isolating(self):
        self.assertEqual(
            energy_isolating_barriers(good_architecture()),
            ["B-arm", "B-fire", "B-select"],
        )

    def test_all_logic_enables_isolate_no_energy(self):
        arch = [barrier(f, isolation_kind="logic-enable") for f in BARRIER_FUNCTIONS]
        self.assertEqual(energy_isolating_barriers(arch), [])


class TestAssessment(unittest.TestCase):
    def test_clean_architecture_is_compliant(self):
        report = assess_barrier_architecture(good_architecture())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["activation_depth"], REQUIRED_BARRIER_DEPTH)
        self.assertEqual(report["barrier_count"], 3)

    def test_missing_function_blocks_compliance(self):
        report = assess_barrier_architecture([barrier("arm"), barrier("fire")])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["missing_functions"], ("select",))
        self.assertIn(FINDING_DEPTH_BELOW_REQUIREMENT, report["finding_codes"])

    def test_command_only_architecture_is_flagged(self):
        arch = [barrier(f, isolation_kind="logic-enable") for f in BARRIER_FUNCTIONS]
        report = assess_barrier_architecture(arch)
        self.assertFalse(report["compliant"])
        self.assertIn(FINDING_NO_ENERGY_ISOLATION, report["finding_codes"])

    def test_shared_relay_architecture_is_not_compliant(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        report = assess_barrier_architecture(arch)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["activation_depth"], 2)
        self.assertIn(FINDING_SHARED_RELEASE_ELEMENT, report["finding_codes"])
        self.assertIn(FINDING_DEPTH_BELOW_REQUIREMENT, report["finding_codes"])

    def test_findings_are_sorted_by_code_then_subject(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        arch[2]["command_domain"] = arch[0]["command_domain"]
        keys = [(f["code"], f["subject"]) for f in assess_barrier_architecture(arch)["findings"]]
        self.assertEqual(keys, sorted(keys))

    def test_required_depth_must_be_a_positive_integer(self):
        with self.assertRaises(ValueError):
            assess_barrier_architecture(good_architecture(), required_depth=0)
        with self.assertRaises(ValueError):
            assess_barrier_architecture(good_architecture(), required_depth=True)

    def test_relaxed_depth_still_reports_the_shared_element(self):
        arch = good_architecture()
        arch[1]["release_element"] = arch[0]["release_element"]
        report = assess_barrier_architecture(arch, required_depth=2)
        self.assertNotIn(FINDING_DEPTH_BELOW_REQUIREMENT, report["finding_codes"])
        self.assertIn(FINDING_SHARED_RELEASE_ELEMENT, report["finding_codes"])
        self.assertFalse(report["compliant"])


if __name__ == "__main__":
    unittest.main()
