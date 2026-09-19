"""Contract test for the actuator-electronics-redundancy leaf."""

import unittest

from e2021_actuator_electronics_redundancy_logic import (
    CHAIN_NOMINAL,
    CHAIN_REDUNDANT,
    FINDING_EMPTY_CHAIN,
    FINDING_SHARED_BLOCK,
    FINDING_UNDUPLICATED_FUNCTION,
    assess_actuator_electronics_redundancy,
    chain_blocks,
    chain_reliability,
    duplicated_functions,
    fault_tolerance_order,
    parallel_reliability,
    redundancy_findings,
    reliability_if_shared_were_duplicated,
    series_reliability,
    shared_blocks,
    single_point_failures,
    system_reliability,
    unduplicated_functions,
    validate_block,
    validate_design,
)

FUNCTIONS = ("command-decoder", "arm-driver", "fire-driver")


def block(function, assignment, probability=0.01, **kw):
    record = {
        "id": "%s-%s" % (function, assignment),
        "function": function,
        "assignment": assignment,
        "failure_probability": probability,
    }
    record.update(kw)
    return record


def duplicated_design(probability=0.01):
    design = []
    for function in FUNCTIONS:
        design.append(block(function, CHAIN_NOMINAL, probability))
        design.append(block(function, CHAIN_REDUNDANT, probability))
    return design


class TestValidateBlock(unittest.TestCase):
    def test_failure_probability_defaults_to_zero(self):
        record = block("arm-driver", CHAIN_NOMINAL)
        del record["failure_probability"]
        self.assertEqual(validate_block(record)["failure_probability"], 0.0)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_block(["arm-driver"])

    def test_blank_function_raises(self):
        record = block("arm-driver", CHAIN_NOMINAL)
        record["function"] = " "
        with self.assertRaises(ValueError):
            validate_block(record)

    def test_unknown_assignment_raises(self):
        record = block("arm-driver", CHAIN_NOMINAL)
        record["assignment"] = "spare"
        with self.assertRaises(ValueError):
            validate_block(record)

    def test_probability_above_one_raises(self):
        with self.assertRaises(ValueError):
            validate_block(block("arm-driver", CHAIN_NOMINAL, 1.5))

    def test_negative_probability_raises(self):
        with self.assertRaises(ValueError):
            validate_block(block("arm-driver", CHAIN_NOMINAL, -0.01))

    def test_boolean_probability_raises(self):
        with self.assertRaises(ValueError):
            validate_block(block("arm-driver", CHAIN_NOMINAL, True))

    def test_internally_redundant_on_a_chain_block_raises(self):
        with self.assertRaises(ValueError):
            validate_block(
                block("arm-driver", CHAIN_NOMINAL, internally_redundant=True)
            )

    def test_internally_redundant_is_allowed_on_a_shared_block(self):
        norm = validate_block(block("sequencer", "shared", internally_redundant=True))
        self.assertTrue(norm["internally_redundant"])


class TestValidateDesign(unittest.TestCase):
    def test_empty_design_raises(self):
        with self.assertRaises(ValueError):
            validate_design([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_design(block("arm-driver", CHAIN_NOMINAL))

    def test_duplicate_block_id_raises(self):
        design = duplicated_design()
        design[1]["id"] = design[0]["id"]
        with self.assertRaises(ValueError):
            validate_design(design)

    def test_unknown_chain_name_raises(self):
        with self.assertRaises(ValueError):
            chain_blocks(duplicated_design(), "backup")


class TestPartition(unittest.TestCase):
    def test_each_chain_carries_its_own_blocks(self):
        design = duplicated_design()
        self.assertEqual(len(chain_blocks(design, CHAIN_NOMINAL)), 3)
        self.assertEqual(len(chain_blocks(design, CHAIN_REDUNDANT)), 3)
        self.assertEqual(shared_blocks(design), [])

    def test_shared_block_is_in_neither_chain(self):
        design = duplicated_design() + [block("sequencer", "shared")]
        self.assertEqual(len(chain_blocks(design, CHAIN_NOMINAL)), 3)
        self.assertEqual([b["id"] for b in shared_blocks(design)], ["sequencer-shared"])

    def test_all_functions_are_duplicated(self):
        self.assertEqual(duplicated_functions(duplicated_design()), tuple(sorted(FUNCTIONS)))
        self.assertEqual(unduplicated_functions(duplicated_design()), ())

    def test_function_in_one_chain_only_is_named(self):
        design = duplicated_design()
        design = [b for b in design if b["id"] != "fire-driver-redundant"]
        self.assertEqual(unduplicated_functions(design), ("fire-driver",))


class TestSinglePointFailures(unittest.TestCase):
    def test_fully_duplicated_design_has_none(self):
        self.assertEqual(single_point_failures(duplicated_design()), [])
        self.assertEqual(fault_tolerance_order(duplicated_design()), 1)

    def test_shared_block_is_a_single_point(self):
        design = duplicated_design() + [block("sequencer", "shared")]
        self.assertEqual(single_point_failures(design), ["sequencer-shared"])
        self.assertEqual(fault_tolerance_order(design), 0)

    def test_internally_redundant_shared_block_is_not_a_single_point(self):
        design = duplicated_design() + [
            block("sequencer", "shared", internally_redundant=True)
        ]
        self.assertEqual(single_point_failures(design), [])
        self.assertEqual(fault_tolerance_order(design), 1)

    def test_unduplicated_chain_block_is_a_single_point(self):
        design = [b for b in duplicated_design() if b["id"] != "fire-driver-redundant"]
        self.assertEqual(single_point_failures(design), ["fire-driver-nominal"])


class TestReliability(unittest.TestCase):
    def test_series_reliability_multiplies(self):
        design = chain_blocks(duplicated_design(0.1), CHAIN_NOMINAL)
        self.assertAlmostEqual(series_reliability(design), 0.9 ** 3, places=9)

    def test_empty_series_is_certain(self):
        self.assertAlmostEqual(series_reliability([]), 1.0, places=9)

    def test_chain_reliability_uses_only_that_chain(self):
        design = duplicated_design(0.1) + [block("sequencer", "shared", 0.5)]
        self.assertAlmostEqual(chain_reliability(design, CHAIN_NOMINAL), 0.729, places=9)

    def test_parallel_reliability_of_two_equal_chains(self):
        self.assertAlmostEqual(parallel_reliability(0.9, 0.9), 0.99, places=9)

    def test_parallel_reliability_rejects_a_value_outside_the_unit_range(self):
        with self.assertRaises(ValueError):
            parallel_reliability(0.9, 1.2)

    def test_system_reliability_of_a_clean_duplicated_design(self):
        design = duplicated_design(0.1)
        expected = 1.0 - (1.0 - 0.9 ** 3) ** 2
        self.assertAlmostEqual(system_reliability(design), expected, places=9)

    def test_shared_block_multiplies_the_parallel_result(self):
        design = duplicated_design(0.1) + [block("sequencer", "shared", 0.5)]
        expected = 0.5 * (1.0 - (1.0 - 0.9 ** 3) ** 2)
        self.assertAlmostEqual(system_reliability(design), expected, places=9)

    def test_duplicating_the_shared_block_recovers_reliability(self):
        design = duplicated_design(0.1) + [block("sequencer", "shared", 0.5)]
        improved = reliability_if_shared_were_duplicated(design)
        expected = 0.75 * (1.0 - (1.0 - 0.9 ** 3) ** 2)
        self.assertAlmostEqual(improved, expected, places=9)
        self.assertGreater(improved, system_reliability(design))

    def test_no_shared_block_means_no_gain_available(self):
        design = duplicated_design(0.1)
        self.assertAlmostEqual(
            reliability_if_shared_were_duplicated(design),
            system_reliability(design),
            places=9,
        )


class TestFindings(unittest.TestCase):
    def test_clean_design_has_no_findings(self):
        self.assertEqual(redundancy_findings(duplicated_design()), [])

    def test_shared_block_raises_its_code(self):
        design = duplicated_design() + [block("sequencer", "shared")]
        codes = [f["code"] for f in redundancy_findings(design)]
        self.assertIn(FINDING_SHARED_BLOCK, codes)

    def test_unduplicated_function_raises_its_code(self):
        design = [b for b in duplicated_design() if b["id"] != "arm-driver-redundant"]
        codes = [f["code"] for f in redundancy_findings(design)]
        self.assertIn(FINDING_UNDUPLICATED_FUNCTION, codes)

    def test_missing_redundant_chain_raises_its_code(self):
        design = [b for b in duplicated_design() if b["assignment"] == CHAIN_NOMINAL]
        codes = [f["code"] for f in redundancy_findings(design)]
        self.assertIn(FINDING_EMPTY_CHAIN, codes)

    def test_findings_are_sorted_by_code_then_subject(self):
        design = duplicated_design() + [block("sequencer", "shared")]
        design = [b for b in design if b["id"] != "arm-driver-redundant"]
        keys = [(f["code"], f["subject"]) for f in redundancy_findings(design)]
        self.assertEqual(keys, sorted(keys))


class TestAssessment(unittest.TestCase):
    def test_clean_design_is_compliant(self):
        report = assess_actuator_electronics_redundancy(duplicated_design(0.1))
        self.assertTrue(report["compliant"])
        self.assertEqual(report["fault_tolerance_order"], 1)
        self.assertEqual(report["shared_block_ids"], [])
        self.assertAlmostEqual(report["reliability_gain_available"], 0.0, places=9)

    def test_shared_block_design_is_not_compliant(self):
        design = duplicated_design(0.1) + [block("sequencer", "shared", 0.5)]
        report = assess_actuator_electronics_redundancy(design)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["single_point_failures"], ["sequencer-shared"])
        self.assertGreater(report["reliability_gain_available"], 0.0)

    def test_report_lists_both_chains(self):
        report = assess_actuator_electronics_redundancy(duplicated_design())
        self.assertEqual(len(report["nominal_block_ids"]), 3)
        self.assertEqual(len(report["redundant_block_ids"]), 3)
        self.assertEqual(report["block_count"], 6)

    def test_single_chain_design_reports_order_zero(self):
        design = [b for b in duplicated_design() if b["assignment"] == CHAIN_NOMINAL]
        report = assess_actuator_electronics_redundancy(design)
        self.assertEqual(report["fault_tolerance_order"], 0)
        self.assertEqual(report["duplicated_functions"], ())


if __name__ == "__main__":
    unittest.main()
