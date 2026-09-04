"""Contract test for type-certificate-data-sheet logic (offline, stdlib).

Run:  python3 test_type-certificate-data-sheet.py
Expected values below were read from real module outputs; the error texts
follow the spec worked example ("max_ramp below max_takeoff", "missing vne
for category normal").
"""

import importlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

m = importlib.import_module("type-certificate-data-sheet_logic")


def _record_a():
    """Worked example record A: transport category, fully consistent."""
    return {
        "category": "transport",
        "models": ["T-100"],
        "type_design": "T-100 basic",
        "engine_models": ["E-1", "E-2"],
        "propeller_models": ["P-1"],
        "weights": {"max_ramp": 80000, "max_takeoff": 79000, "max_landing": 70000},
        "certification_basis": ["far-25"],
        "operating_limitations": {"vmo": 340, "mmo": 0.84},
        "noise_standards": ["far-36"],
    }


def _record_b():
    """Worked example record B: normal category, ramp below takeoff, no VNE."""
    record = _record_a()
    record["category"] = "normal"
    record["weights"] = {"max_ramp": 75000, "max_takeoff": 79000, "max_landing": 70000}
    record["operating_limitations"] = {}
    return record


def _record_a2():
    """Revision A2: adds model T-101 and raises max_takeoff to 79400."""
    record = _record_a()
    record["models"] = ["T-100", "T-101"]
    record["weights"] = {"max_ramp": 80000, "max_takeoff": 79400, "max_landing": 70000}
    return record


class MissingSectionsTests(unittest.TestCase):
    def test_complete_record_has_no_missing_sections(self):
        self.assertEqual(m.missing_sections(_record_a()), [])

    def test_missing_sections_lists_exactly_two_absent(self):
        record = _record_a()
        del record["propeller_models"]
        del record["noise_standards"]
        self.assertEqual(m.missing_sections(record), ["propeller_models", "noise_standards"])

    def test_missing_sections_all_and_single_in_order(self):
        self.assertEqual(m.missing_sections({"category": "normal"}),
                         list(m.REQUIRED_SECTIONS))
        record = {key: [] for key in m.REQUIRED_SECTIONS}
        del record["weights"]
        self.assertEqual(m.missing_sections(record), ["weights"])

    def test_record_not_a_dict_raises(self):
        with self.assertRaises(ValueError):
            m.missing_sections(["not", "a", "dict"])


class WeightErrorTests(unittest.TestCase):
    def test_valid_weight_block_no_errors(self):
        self.assertEqual(m.weight_errors(_record_a()), [])
        record = dict(_record_a())
        del record["weights"]
        self.assertEqual(m.weight_errors(record), [])

    def test_ramp_below_takeoff_flagged(self):
        self.assertEqual(m.weight_errors(_record_b()), ["max_ramp below max_takeoff"])

    def test_landing_above_takeoff_flagged(self):
        record = _record_a()
        record["weights"]["max_landing"] = 81000
        self.assertEqual(m.weight_errors(record), ["max_landing above max_takeoff"])

    def test_non_positive_and_zero_weights_flagged(self):
        record = _record_a()
        record["weights"]["max_ramp"] = -5
        self.assertIn("max_ramp not positive", m.weight_errors(record))
        record = _record_a()
        record["weights"]["max_takeoff"] = 0
        self.assertIn("max_takeoff not positive", m.weight_errors(record))

    def test_missing_weight_keys_flagged_in_order(self):
        record = _record_a()
        record["weights"] = {}
        self.assertEqual(
            m.weight_errors(record),
            ["missing weight key max_ramp", "missing weight key max_takeoff",
             "missing weight key max_landing"],
        )

    def test_weights_not_a_dict_raises(self):
        record = _record_a()
        record["weights"] = [79000]
        with self.assertRaises(ValueError):
            m.weight_errors(record)

    def test_non_numeric_weight_raises(self):
        record = _record_a()
        record["weights"]["max_takeoff"] = "heavy"
        with self.assertRaises(ValueError):
            m.weight_errors(record)


class AirspeedErrorTests(unittest.TestCase):
    def test_transport_satisfied_by_vmo_or_mmo_alone(self):
        self.assertEqual(m.airspeed_errors(_record_a()), [])
        record = _record_a()
        record["operating_limitations"] = {"mmo": 0.84}
        self.assertEqual(m.airspeed_errors(record), [])

    def test_normal_missing_vne_exact_message(self):
        self.assertEqual(m.airspeed_errors(_record_b()),
                         ["missing vne for category normal"])

    def test_truth_table_all_categories(self):
        for category in ("normal", "utility", "acrobatic"):
            record = _record_b()
            record["category"] = category
            self.assertEqual(
                m.airspeed_errors(record), ["missing vne for category %s" % category]
            )
            record["operating_limitations"] = {"vne": 280}
            self.assertEqual(m.airspeed_errors(record), [])

    def test_transport_missing_both_limits_flagged(self):
        record = _record_a()
        record["operating_limitations"] = {}
        self.assertEqual(
            m.airspeed_errors(record), ["missing vmo or mmo for category transport"]
        )

    def test_unknown_category_flagged(self):
        record = _record_a()
        record["category"] = "commuter"
        self.assertEqual(m.airspeed_errors(record), ["unknown category commuter"])

    def test_non_positive_limit_flagged(self):
        record = _record_a()
        record["operating_limitations"] = {"vmo": 0.0}
        self.assertEqual(
            m.airspeed_errors(record), ["vmo not positive for category transport"]
        )

    def test_missing_category_and_bad_limits_raise(self):
        record = _record_a()
        del record["category"]
        with self.assertRaises(ValueError):
            m.airspeed_errors(record)
        record = _record_a()
        record["operating_limitations"] = ["vmo"]
        with self.assertRaises(ValueError):
            m.airspeed_errors(record)


class ApprovedConfigTests(unittest.TestCase):
    def test_approved_config_ok(self):
        self.assertEqual(m.approved_config_errors(_record_a()), [])
        self.assertEqual(m.approved_config_errors(_record_b()), [])

    def test_empty_engine_or_propeller_models_flagged(self):
        record = _record_a()
        record["engine_models"] = []
        self.assertEqual(
            m.approved_config_errors(record), ["no approved engine models listed"]
        )
        record = _record_a()
        record["propeller_models"] = []
        self.assertEqual(
            m.approved_config_errors(record), ["no approved propeller models listed"]
        )

    def test_engine_reference_checks(self):
        record = _record_a()
        record["operating_limitations"]["engines"] = ["E-9"]
        self.assertEqual(
            m.approved_config_errors(record),
            ["engine reference E-9 not in approved engine models"],
        )
        record = _record_a()
        record["operating_limitations"]["engines"] = ["E-1", "E-2"]
        self.assertEqual(m.approved_config_errors(record), [])


class ValidateTests(unittest.TestCase):
    def test_record_a_valid_with_exact_keys(self):
        result = m.validate_tcds(_record_a())
        self.assertEqual(
            set(result),
            {"missing_sections", "weight_errors", "airspeed_errors",
             "config_errors", "valid"},
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_sections"], [])
        self.assertEqual(result["weight_errors"], [])
        self.assertEqual(result["airspeed_errors"], [])
        self.assertEqual(result["config_errors"], [])

    def test_record_b_invalid_with_both_content_errors(self):
        result = m.validate_tcds(_record_b())
        self.assertFalse(result["valid"])
        self.assertEqual(result["weight_errors"], ["max_ramp below max_takeoff"])
        self.assertEqual(result["airspeed_errors"], ["missing vne for category normal"])

    def test_valid_flag_equals_all_empty_identity(self):
        record = _record_a()
        record["noise_standards"] = None
        record["weights"]["max_ramp"] = 70000
        result = m.validate_tcds(record)
        all_empty = not any(
            [result["missing_sections"], result["weight_errors"],
             result["airspeed_errors"], result["config_errors"]]
        )
        self.assertEqual(result["valid"], all_empty)
        self.assertFalse(result["valid"])

    def test_record_without_category_raises(self):
        record = _record_a()
        del record["category"]
        with self.assertRaises(ValueError):
            m.validate_tcds(record)


class SummaryTests(unittest.TestCase):
    def test_summary_counts_identity_and_max_takeoff(self):
        summary = m.tcds_summary(_record_a())
        record = _record_a()
        self.assertEqual(summary["models"], 1)
        self.assertEqual(summary["engine_models"], 2)
        self.assertEqual(summary["propeller_models"], 1)
        self.assertEqual(summary["max_takeoff_weight"], 79000.0)
        self.assertEqual(summary["models"], len(record["models"]))
        self.assertEqual(summary["engine_models"], len(record["engine_models"]))
        self.assertEqual(summary["propeller_models"], len(record["propeller_models"]))

    def test_summary_airspeed_limits_sorted(self):
        summary = m.tcds_summary(_record_a())
        self.assertEqual(summary["airspeed_limits"], ["mmo=0.84", "vmo=340"])
        self.assertEqual(m.tcds_summary(_record_b())["airspeed_limits"], [])

    def test_summary_missing_max_takeoff_raises(self):
        record = _record_a()
        del record["weights"]["max_takeoff"]
        with self.assertRaises(ValueError):
            m.tcds_summary(record)


class RevisionDiffTests(unittest.TestCase):
    def test_identical_record_all_unchanged(self):
        diff = m.tcds_revision_diff(_record_a(), _record_a())
        for key in m.REQUIRED_SECTIONS:
            self.assertEqual(diff["sections"][key], "unchanged")
        self.assertEqual(diff["models_added"], [])
        self.assertEqual(diff["models_removed"], [])
        self.assertEqual(diff["weight_deltas"], {})

    def test_added_model_and_weight_delta(self):
        diff = m.tcds_revision_diff(_record_a(), _record_a2())
        self.assertEqual(diff["sections"]["models"], "modified")
        self.assertEqual(diff["sections"]["weights"], "modified")
        self.assertEqual(diff["models_added"], ["T-101"])
        self.assertEqual(diff["models_removed"], [])
        self.assertEqual(diff["weight_deltas"]["max_takeoff_delta"], 400.0)
        self.assertEqual(len(diff["weight_deltas"]), 1)

    def test_removed_model_and_disjoint_identity(self):
        diff = m.tcds_revision_diff(_record_a2(), _record_a())
        self.assertEqual(diff["models_added"], [])
        self.assertEqual(diff["models_removed"], ["T-101"])
        old_rec = _record_a()
        old_rec["models"] = ["T-100", "T-101"]
        new_rec = _record_a()
        new_rec["models"] = ["T-100", "T-102"]
        diff = m.tcds_revision_diff(old_rec, new_rec)
        self.assertEqual(diff["models_added"], ["T-102"])
        self.assertEqual(diff["models_removed"], ["T-101"])
        self.assertTrue(set(diff["models_added"]).isdisjoint(diff["models_removed"]))

    def test_weight_and_limits_only_changes(self):
        record = dict(_record_a())
        record["weights"] = {"max_ramp": 80000, "max_takeoff": 79200, "max_landing": 70000}
        diff = m.tcds_revision_diff(_record_a(), record)
        self.assertEqual(diff["sections"]["models"], "unchanged")
        self.assertEqual(diff["weight_deltas"]["max_takeoff_delta"], 200.0)
        record = dict(_record_a())
        record["operating_limitations"] = {"vmo": 350, "mmo": 0.85}
        diff = m.tcds_revision_diff(_record_a(), record)
        self.assertEqual(diff["sections"]["operating_limitations"], "modified")

    def test_section_removed_and_added_between_revisions(self):
        new_rec = _record_a()
        del new_rec["noise_standards"]
        diff = m.tcds_revision_diff(_record_a(), new_rec)
        self.assertEqual(diff["sections"]["noise_standards"], "removed")
        self.assertEqual(diff["sections"]["certification_basis"], "unchanged")
        old_rec = dict(_record_a())
        del old_rec["noise_standards"]
        back = m.tcds_revision_diff(old_rec, _record_a())
        self.assertEqual(back["sections"]["noise_standards"], "added")

    def test_reorder_only_counts_as_modified(self):
        old_rec = _record_a()
        old_rec["models"] = ["T-100", "T-101"]
        new_rec = _record_a()
        new_rec["models"] = ["T-101", "T-100"]
        diff = m.tcds_revision_diff(old_rec, new_rec)
        self.assertEqual(diff["sections"]["models"], "modified")
        self.assertEqual(diff["models_added"], [])
        self.assertEqual(diff["models_removed"], [])


class DeterminismTests(unittest.TestCase):
    def test_validate_and_diff_deterministic_across_runs(self):
        self.assertEqual(m.validate_tcds(_record_a()), m.validate_tcds(_record_a()))
        self.assertEqual(
            m.tcds_revision_diff(_record_a(), _record_a2()),
            m.tcds_revision_diff(_record_a(), _record_a2()),
        )


if __name__ == "__main__":
    unittest.main()
