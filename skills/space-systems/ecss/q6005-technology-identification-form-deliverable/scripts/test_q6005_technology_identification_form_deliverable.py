"""Contract tests for the Annex A technology identification form data item."""

import unittest

from q6005_technology_identification_form_deliverable_logic import (
    CONDITIONAL_FIELD_RULES,
    MANDATED_BODY_FIELDS,
    MANDATED_HEADER_FIELDS,
    MANDATED_ORDER,
    activated_conditional_fields,
    assess_identification_form,
    blank_fields,
    categorize_extra_fields,
    completeness_ratio,
    longest_ordered_run,
    missing_fields,
    normalise_field_name,
    normalise_submission,
    required_fields,
    structure_order_ratio,
)


def base_form(**overrides):
    """A non-hermetic, non-RF, non-polymer form delivered in mandated order."""
    values = {
        "form_reference": "TIF-4471",
        "issue": "3",
        "issue_date": "2026-04-02",
        "manufacturer": "Line Works",
        "manufacturing_line": "Hybrid line B",
        "prepared_by": "Process engineering",
        "approved_by": "Product assurance",
        "hybrid_type": "power",
        "substrate_technology": "thick film alumina",
        "interconnection_technology": "aluminium wedge bond",
        "die_attach_technology": "silver filled epoxy",
        "encapsulation_technology": "metal lid",
        "sealing_method": "welded",
        "process_control_documents": "PCD-12, PCD-19",
        "qualification_status": "qualified",
    }
    values.update(overrides)
    return {name: values[name] for name in MANDATED_ORDER if name in values}


class NormaliseFieldNameTests(unittest.TestCase):
    def test_hyphen_and_space_become_underscore(self):
        self.assertEqual(normalise_field_name("Sealing-Method"), "sealing_method")

    def test_surrounding_space_is_dropped(self):
        self.assertEqual(normalise_field_name("  issue  "), "issue")

    def test_repeated_separators_collapse(self):
        self.assertEqual(normalise_field_name("die  attach--technology"),
                         "die_attach_technology")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            normalise_field_name("   ")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            normalise_field_name(7)


class NormaliseSubmissionTests(unittest.TestCase):
    def test_returns_canonical_field_map(self):
        fields = normalise_submission({"Form-Reference": " TIF-1 "})
        self.assertEqual(fields, {"form_reference": "TIF-1"})

    def test_none_value_becomes_blank(self):
        self.assertEqual(normalise_submission({"issue": None})["issue"], "")

    def test_numeric_value_is_kept_as_text(self):
        self.assertEqual(normalise_submission({"issue": 3})["issue"], "3")

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            normalise_submission({"issue": True})

    def test_duplicate_after_normalisation_rejected(self):
        with self.assertRaises(ValueError):
            normalise_submission({"Issue": "3", "issue": "4"})

    def test_empty_submission_rejected(self):
        with self.assertRaises(ValueError):
            normalise_submission({})

    def test_non_mapping_submission_rejected(self):
        with self.assertRaises(ValueError):
            normalise_submission([("issue", "3")])


class ConditionalRuleTests(unittest.TestCase):
    def test_no_option_pulls_nothing_in(self):
        fields = normalise_submission(base_form())
        self.assertEqual(activated_conditional_fields(fields), ())

    def test_hermetic_seal_pulls_in_its_entries(self):
        fields = normalise_submission(base_form(sealing_method="Hermetic"))
        self.assertEqual(
            activated_conditional_fields(fields),
            ("internal_gas_analysis_reference", "seal_leak_test_method"),
        )

    def test_polymer_encapsulation_pulls_in_outgassing_entry(self):
        fields = normalise_submission(base_form(encapsulation_technology="polymer"))
        self.assertIn("outgassing_screening_reference", activated_conditional_fields(fields))

    def test_two_options_accumulate(self):
        fields = normalise_submission(
            base_form(sealing_method="hermetic", hybrid_type="RF")
        )
        owed = activated_conditional_fields(fields)
        self.assertIn("frequency_range_declaration", owed)
        self.assertIn("seal_leak_test_method", owed)

    def test_blank_trigger_value_fires_no_rule(self):
        fields = normalise_submission(base_form(sealing_method=None))
        self.assertEqual(activated_conditional_fields(fields), ())

    def test_required_set_extends_the_mandated_order(self):
        fields = normalise_submission(base_form(hybrid_type="rf"))
        required = required_fields(fields)
        self.assertEqual(required[: len(MANDATED_ORDER)], MANDATED_ORDER)
        self.assertEqual(required[-1], "frequency_range_declaration")

    def test_every_rule_names_at_least_one_owed_entry(self):
        for key, owed in CONDITIONAL_FIELD_RULES.items():
            self.assertTrue(owed, "rule %r owes nothing" % (key,))


class MissingAndBlankTests(unittest.TestCase):
    def test_complete_form_has_no_absent_entry(self):
        self.assertEqual(missing_fields(normalise_submission(base_form())), ())

    def test_dropped_header_entry_is_reported(self):
        form = base_form()
        del form["approved_by"]
        self.assertEqual(missing_fields(normalise_submission(form)), ("approved_by",))

    def test_heading_with_no_value_is_reported_blank_not_absent(self):
        fields = normalise_submission(base_form(qualification_status=""))
        self.assertEqual(blank_fields(fields), ("qualification_status",))
        self.assertEqual(missing_fields(fields), ())

    def test_unfiled_conditional_entry_is_absent(self):
        fields = normalise_submission(base_form(sealing_method="hermetic"))
        self.assertIn("seal_leak_test_method", missing_fields(fields))

    def test_header_and_body_blocks_are_disjoint(self):
        self.assertEqual(
            set(MANDATED_HEADER_FIELDS) & set(MANDATED_BODY_FIELDS), set()
        )


class ExtraFieldTests(unittest.TestCase):
    def test_unknown_entry_is_grouped_as_unknown(self):
        form = base_form()
        form["marketing_note"] = "best in class"
        extras = categorize_extra_fields(normalise_submission(form))
        self.assertEqual(extras["unknown"], ("marketing_note",))
        self.assertEqual(extras["out_of_scope"], ())

    def test_conditional_entry_without_its_option_is_out_of_scope(self):
        form = base_form()
        form["seal_leak_test_method"] = "fine and gross"
        extras = categorize_extra_fields(normalise_submission(form))
        self.assertEqual(extras["out_of_scope"], ("seal_leak_test_method",))
        self.assertEqual(extras["unknown"], ())

    def test_conditional_entry_with_its_option_is_not_extra(self):
        form = base_form(sealing_method="hermetic")
        form["seal_leak_test_method"] = "fine and gross"
        form["internal_gas_analysis_reference"] = "IGA-7"
        extras = categorize_extra_fields(normalise_submission(form))
        self.assertEqual(extras["out_of_scope"], ())
        self.assertEqual(extras["unknown"], ())


class OrderTests(unittest.TestCase):
    def test_in_sequence_run_is_the_whole_list(self):
        self.assertEqual(longest_ordered_run(["a", "b", "c"], ["a", "b", "c"]), 3)

    def test_reversed_delivery_leaves_a_run_of_one(self):
        self.assertEqual(longest_ordered_run(["c", "b", "a"], ["a", "b", "c"]), 1)

    def test_one_displaced_entry_keeps_the_rest_in_run(self):
        self.assertEqual(longest_ordered_run(["a", "c", "b", "d"], ["a", "b", "c", "d"]), 3)

    def test_unrecognised_entries_are_ignored_by_the_run(self):
        self.assertEqual(longest_ordered_run(["z", "a", "b"], ["a", "b"]), 2)

    def test_no_recognised_entry_gives_a_zero_run(self):
        self.assertEqual(longest_ordered_run(["z"], ["a", "b"]), 0)

    def test_ratio_is_one_for_a_form_in_order(self):
        self.assertAlmostEqual(structure_order_ratio(["a", "b", "c"], ["a", "b", "c"]),
                               1.0, places=9)

    def test_ratio_falls_when_entries_are_displaced(self):
        self.assertAlmostEqual(structure_order_ratio(["c", "b", "a"], ["a", "b", "c"]),
                               1.0 / 3.0, places=9)

    def test_ratio_is_zero_when_nothing_is_recognised(self):
        self.assertAlmostEqual(structure_order_ratio(["z"], ["a"]), 0.0, places=9)

    def test_non_sequence_delivery_rejected(self):
        with self.assertRaises(ValueError):
            longest_ordered_run("abc", ["a"])

    def test_empty_expected_order_rejected(self):
        with self.assertRaises(ValueError):
            longest_ordered_run(["a"], [])


class CompletenessRatioTests(unittest.TestCase):
    def test_full_form_scores_one(self):
        self.assertAlmostEqual(completeness_ratio(normalise_submission(base_form())),
                               1.0, places=9)

    def test_one_blank_entry_costs_exactly_one_slot(self):
        fields = normalise_submission(base_form(issue=""))
        expected = (len(MANDATED_ORDER) - 1) / len(MANDATED_ORDER)
        self.assertAlmostEqual(completeness_ratio(fields), expected, places=9)

    def test_conditional_entries_enlarge_the_denominator(self):
        fields = normalise_submission(base_form(hybrid_type="rf"))
        expected = len(MANDATED_ORDER) / (len(MANDATED_ORDER) + 1)
        self.assertAlmostEqual(completeness_ratio(fields), expected, places=9)


class AssessmentTests(unittest.TestCase):
    def test_clean_form_is_accepted(self):
        result = assess_identification_form(base_form())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["in_mandated_order"])
        self.assertAlmostEqual(result["completeness_ratio"], 1.0, places=9)

    def test_absent_entry_holds_the_form(self):
        form = base_form()
        del form["manufacturing_line"]
        result = assess_identification_form(form)
        self.assertEqual(result["verdict"], "hold")
        self.assertIn("manufacturing_line", result["missing_fields"])

    def test_out_of_scope_entry_only_earns_a_remark(self):
        form = base_form()
        form["frequency_range_declaration"] = "2 to 4 GHz"
        result = assess_identification_form(form)
        self.assertEqual(result["verdict"], "accept-with-remarks")
        self.assertEqual(result["extra_fields"]["out_of_scope"],
                         ("frequency_range_declaration",))

    def test_unknown_entry_holds_the_form(self):
        form = base_form()
        form["internal_cost_code"] = "CC-9"
        self.assertEqual(assess_identification_form(form)["verdict"], "hold")

    def test_shuffled_delivery_is_reported_out_of_order(self):
        form = base_form()
        shuffled = dict(reversed(list(form.items())))
        result = assess_identification_form(shuffled)
        self.assertFalse(result["in_mandated_order"])
        self.assertEqual(result["verdict"], "hold")

    def test_explicit_delivered_order_is_honoured(self):
        form = base_form()
        order = list(reversed(list(form.keys())))
        result = assess_identification_form(form, delivered_order=order)
        self.assertFalse(result["in_mandated_order"])

    def test_delivered_order_must_match_the_delivered_fields(self):
        with self.assertRaises(ValueError):
            assess_identification_form(base_form(), delivered_order=["issue"])

    def test_hermetic_case_reports_the_entries_it_owes(self):
        form = base_form(sealing_method="hermetic")
        result = assess_identification_form(form)
        self.assertEqual(
            result["conditional_fields"],
            ("internal_gas_analysis_reference", "seal_leak_test_method"),
        )
        self.assertEqual(result["verdict"], "hold")

    def test_findings_are_ordered_absent_then_blank(self):
        form = base_form(issue="")
        del form["approved_by"]
        findings = assess_identification_form(form)["findings"]
        self.assertIn("approved_by", findings[0])
        self.assertIn("issue", findings[1])


if __name__ == "__main__":
    unittest.main()
