"""Contract test for the actuator-electronics-command-interfaces leaf."""

import unittest

from e2021_actuator_electronics_command_interfaces_logic import (
    COMMAND_CHAIN_NOMINAL,
    COMMAND_CHAIN_REDUNDANT,
    COMMAND_CHAINS,
    COMMAND_TYPES,
    ELECTRONICS_CHAINS,
    ELECTRONICS_NOMINAL,
    ELECTRONICS_REDUNDANT,
    FINDING_CELL_NOT_ACCEPTED,
    FINDING_COMMAND_CHAIN_LOSS_FATAL,
    FINDING_CROSS_STRAP_NOT_ISOLATED,
    REQUIRED_CELL_COUNT,
    accepted_keys,
    assess_command_interfaces,
    cell_key,
    command_chain_loss_report,
    command_interface_findings,
    command_type_fully_cross_strapped,
    commandable_electronics,
    coverage_fraction,
    cross_strap_cells,
    missing_cells,
    required_cells,
    unisolated_cross_straps,
    validate_cell,
    validate_matrix,
)


def cell(command_type, electronics, command_chain, **kw):
    record = {
        "command_type": command_type,
        "electronics_chain": electronics,
        "command_chain": command_chain,
        "accepted": True,
        "isolated": True,
    }
    record.update(kw)
    return record


def full_matrix():
    return [
        cell(command_type, electronics, command_chain)
        for command_type in COMMAND_TYPES
        for electronics in ELECTRONICS_CHAINS
        for command_chain in COMMAND_CHAINS
    ]


def home_only_matrix():
    return [
        cell(command_type, ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL)
        for command_type in COMMAND_TYPES
    ] + [
        cell(command_type, ELECTRONICS_REDUNDANT, COMMAND_CHAIN_REDUNDANT)
        for command_type in COMMAND_TYPES
    ]


class TestValidateCell(unittest.TestCase):
    def test_acceptance_and_isolation_default_to_true(self):
        record = cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL)
        del record["accepted"]
        del record["isolated"]
        norm = validate_cell(record)
        self.assertTrue(norm["accepted"])
        self.assertTrue(norm["isolated"])

    def test_home_cell_is_not_a_cross_strap(self):
        norm = validate_cell(cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL))
        self.assertFalse(norm["is_cross_strap"])

    def test_foreign_cell_is_a_cross_strap(self):
        norm = validate_cell(cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_REDUNDANT))
        self.assertTrue(norm["is_cross_strap"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_cell(["arm"])

    def test_unknown_command_type_raises(self):
        with self.assertRaises(ValueError):
            validate_cell(cell("safe", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL))

    def test_unknown_electronics_chain_raises(self):
        with self.assertRaises(ValueError):
            validate_cell(cell("arm", "third-electronics", COMMAND_CHAIN_NOMINAL))

    def test_unknown_command_chain_raises(self):
        with self.assertRaises(ValueError):
            validate_cell(cell("arm", ELECTRONICS_NOMINAL, "ground-link"))

    def test_non_boolean_acceptance_raises(self):
        with self.assertRaises(ValueError):
            validate_cell(
                cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL, accepted="yes")
            )


class TestValidateMatrix(unittest.TestCase):
    def test_full_matrix_normalizes(self):
        self.assertEqual(len(validate_matrix(full_matrix())), REQUIRED_CELL_COUNT)

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            validate_matrix([])

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_matrix(cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL))

    def test_duplicate_cell_raises(self):
        matrix = full_matrix()
        matrix.append(cell("arm", ELECTRONICS_NOMINAL, COMMAND_CHAIN_NOMINAL))
        with self.assertRaises(ValueError):
            validate_matrix(matrix)


class TestCoverage(unittest.TestCase):
    def test_twelve_cells_are_required(self):
        self.assertEqual(len(required_cells()), 12)
        self.assertEqual(REQUIRED_CELL_COUNT, 12)

    def test_full_matrix_misses_nothing(self):
        self.assertEqual(missing_cells(full_matrix()), ())
        self.assertAlmostEqual(coverage_fraction(full_matrix()), 1.0, places=9)

    def test_home_only_matrix_covers_half(self):
        self.assertAlmostEqual(coverage_fraction(home_only_matrix()), 0.5, places=9)
        self.assertEqual(len(missing_cells(home_only_matrix())), 6)

    def test_a_cell_declared_not_accepted_counts_as_missing(self):
        matrix = full_matrix()
        matrix[0]["accepted"] = False
        self.assertEqual(len(missing_cells(matrix)), 1)
        self.assertEqual(len(accepted_keys(matrix)), 11)

    def test_missing_cell_key_names_all_three_axes(self):
        matrix = [c for c in full_matrix() if cell_key(validate_cell(c)) != ("fire", ELECTRONICS_NOMINAL, COMMAND_CHAIN_REDUNDANT)]
        self.assertEqual(
            missing_cells(matrix),
            (("fire", ELECTRONICS_NOMINAL, COMMAND_CHAIN_REDUNDANT),),
        )


class TestCrossStraps(unittest.TestCase):
    def test_full_matrix_has_six_cross_straps(self):
        self.assertEqual(len(cross_strap_cells(full_matrix())), 6)

    def test_home_only_matrix_has_none(self):
        self.assertEqual(cross_strap_cells(home_only_matrix()), [])

    def test_unisolated_cross_strap_is_reported(self):
        matrix = full_matrix()
        for record in matrix:
            if (
                record["electronics_chain"] == ELECTRONICS_NOMINAL
                and record["command_chain"] == COMMAND_CHAIN_REDUNDANT
                and record["command_type"] == "fire"
            ):
                record["isolated"] = False
        self.assertEqual(
            unisolated_cross_straps(matrix),
            (("fire", ELECTRONICS_NOMINAL, COMMAND_CHAIN_REDUNDANT),),
        )

    def test_an_unisolated_home_cell_is_not_a_cross_strap_finding(self):
        matrix = full_matrix()
        for record in matrix:
            if (
                record["electronics_chain"] == ELECTRONICS_NOMINAL
                and record["command_chain"] == COMMAND_CHAIN_NOMINAL
            ):
                record["isolated"] = False
        self.assertEqual(unisolated_cross_straps(matrix), ())

    def test_every_command_is_fully_cross_strapped_in_the_full_matrix(self):
        for command_type in COMMAND_TYPES:
            self.assertTrue(command_type_fully_cross_strapped(full_matrix(), command_type))

    def test_unknown_command_type_raises_on_the_cross_strap_query(self):
        with self.assertRaises(ValueError):
            command_type_fully_cross_strapped(full_matrix(), "safe")


class TestCommandChainLoss(unittest.TestCase):
    def test_full_matrix_keeps_both_electronics_chains(self):
        report = command_chain_loss_report(full_matrix())
        self.assertEqual(report[COMMAND_CHAIN_NOMINAL], ELECTRONICS_CHAINS)
        self.assertEqual(report[COMMAND_CHAIN_REDUNDANT], ELECTRONICS_CHAINS)

    def test_home_only_matrix_loses_one_electronics_chain(self):
        report = command_chain_loss_report(home_only_matrix())
        self.assertEqual(report[COMMAND_CHAIN_NOMINAL], (ELECTRONICS_REDUNDANT,))
        self.assertEqual(report[COMMAND_CHAIN_REDUNDANT], (ELECTRONICS_NOMINAL,))

    def test_partial_acceptance_removes_a_chain_from_the_survivors(self):
        matrix = [
            c
            for c in full_matrix()
            if not (
                c["command_type"] == "fire"
                and c["electronics_chain"] == ELECTRONICS_REDUNDANT
            )
        ]
        self.assertEqual(
            commandable_electronics(matrix, COMMAND_CHAINS), (ELECTRONICS_NOMINAL,)
        )

    def test_unknown_available_chain_raises(self):
        with self.assertRaises(ValueError):
            commandable_electronics(full_matrix(), ["ground-link"])

    def test_non_collection_available_chains_raises(self):
        with self.assertRaises(ValueError):
            commandable_electronics(full_matrix(), COMMAND_CHAIN_NOMINAL)


class TestFindings(unittest.TestCase):
    def test_full_matrix_has_no_findings(self):
        self.assertEqual(command_interface_findings(full_matrix()), [])

    def test_missing_cell_raises_its_code(self):
        matrix = full_matrix()
        matrix[0]["accepted"] = False
        codes = [f["code"] for f in command_interface_findings(matrix)]
        self.assertIn(FINDING_CELL_NOT_ACCEPTED, codes)

    def test_unisolated_cross_strap_raises_its_code(self):
        matrix = full_matrix()
        for record in matrix:
            if record["electronics_chain"] == ELECTRONICS_REDUNDANT and record[
                "command_chain"
            ] == COMMAND_CHAIN_NOMINAL:
                record["isolated"] = False
        codes = [f["code"] for f in command_interface_findings(matrix)]
        self.assertIn(FINDING_CROSS_STRAP_NOT_ISOLATED, codes)

    def test_fatal_command_chain_loss_raises_its_code(self):
        matrix = [
            c
            for c in full_matrix()
            if c["command_chain"] == COMMAND_CHAIN_NOMINAL
        ]
        codes = [f["code"] for f in command_interface_findings(matrix)]
        self.assertIn(FINDING_COMMAND_CHAIN_LOSS_FATAL, codes)

    def test_findings_are_sorted_by_code_then_subject(self):
        matrix = full_matrix()
        matrix[0]["accepted"] = False
        matrix[5]["isolated"] = False
        keys = [(f["code"], f["subject"]) for f in command_interface_findings(matrix)]
        self.assertEqual(keys, sorted(keys))


class TestAssessment(unittest.TestCase):
    def test_full_matrix_is_compliant(self):
        report = assess_command_interfaces(full_matrix())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["accepted_cell_count"], 12)
        self.assertEqual(report["cross_strap_count"], 6)
        self.assertEqual(report["fully_cross_strapped_commands"], COMMAND_TYPES)

    def test_home_only_matrix_is_not_compliant(self):
        report = assess_command_interfaces(home_only_matrix())
        self.assertFalse(report["compliant"])
        self.assertAlmostEqual(report["coverage_fraction"], 0.5, places=9)
        self.assertEqual(report["fully_cross_strapped_commands"], ())
        self.assertIn(FINDING_CELL_NOT_ACCEPTED, report["finding_codes"])

    def test_report_counts_the_declared_cells(self):
        report = assess_command_interfaces(full_matrix())
        self.assertEqual(report["declared_cell_count"], 12)
        self.assertEqual(report["required_cell_count"], 12)

    def test_single_command_chain_design_reports_the_fatal_loss(self):
        matrix = [c for c in full_matrix() if c["command_chain"] == COMMAND_CHAIN_NOMINAL]
        report = assess_command_interfaces(matrix)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["command_chain_loss"][COMMAND_CHAIN_NOMINAL], ())
        self.assertIn(FINDING_COMMAND_CHAIN_LOSS_FATAL, report["finding_codes"])


if __name__ == "__main__":
    unittest.main()
