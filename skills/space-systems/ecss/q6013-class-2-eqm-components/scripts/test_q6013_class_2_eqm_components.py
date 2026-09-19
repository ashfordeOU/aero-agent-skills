"""Contract tests for the clause 5.1.6 Class 2 qualification-model transfer logic."""

import unittest

from q6013_class_2_eqm_components_logic import (
    ATTRIBUTE_DOMAIN_LOSS,
    COMPONENT_CATEGORIES,
    CREDIT_TOLERANCE,
    DEFAULT_ACCEPTANCE_CREDIT,
    DEFAULT_CREDIT_FLOOR,
    FUNDAMENTAL_ATTRIBUTES,
    TRANSFER_DOMAINS,
    assess_class2_eqm_transfer,
    compare_build_standard,
    component_category,
    domain_transfer_credit,
    domains_below_floor,
    evaluate_eqm_component,
    model_domain_credit,
    validate_acceptance,
)

FLIGHT = {
    "manufacturer": "Vendor-A",
    "part_number": "XR-2209-QT",
    "package": "QFN-32",
    "die_lot": "LOT-7712",
    "screening_flow": "vendor-flow-b",
    "board_mounting": "smt-reflow",
    "date_code_range": "2431-2438",
}


def fitted(**overrides):
    """Return a fitted part identical to the flight build unless overridden."""
    base = dict(FLIGHT)
    base.update(overrides)
    return base


def acceptance(attribute, domains, credit=None, **overrides):
    """Return a deviation acceptance record for the given attribute."""
    record = {
        "attribute": attribute,
        "justification": "delta assessed against the flight build",
        "delta_test": "targeted delta test campaign",
        "domains": list(domains),
    }
    if credit is not None:
        record["credit"] = credit
    record.update(overrides)
    return record


def item(reference="U1", quantity=1, acceptances=(), **overrides):
    """Return a model component item for the assessment entry point."""
    return {
        "reference": reference,
        "quantity": quantity,
        "fitted": fitted(**overrides),
        "intended": dict(FLIGHT),
        "acceptances": list(acceptances),
    }


class CatalogueTests(unittest.TestCase):
    def test_every_attribute_touches_a_known_domain(self):
        for attribute, losses in ATTRIBUTE_DOMAIN_LOSS.items():
            self.assertTrue(losses, attribute)
            for domain in losses:
                self.assertIn(domain, TRANSFER_DOMAINS)

    def test_every_loss_share_lies_in_the_unit_interval(self):
        # These shares are declared table literals, not computed values.
        # A full loss of credit is exactly 1.0, so state that case as the
        # equality it is and hold every other share strictly inside the
        # interval; together that is still 0 < share <= 1.
        for attribute, losses in ATTRIBUTE_DOMAIN_LOSS.items():
            for domain, share in losses.items():
                where = "%s/%s" % (attribute, domain)
                self.assertGreater(share, 0.0, where)
                if share == 1.0:
                    continue
                self.assertLess(share, 1.0, where)

    def test_fundamental_attributes_remove_every_domain(self):
        for attribute in FUNDAMENTAL_ATTRIBUTES:
            self.assertEqual(set(ATTRIBUTE_DOMAIN_LOSS[attribute]), set(TRANSFER_DOMAINS))

    def test_category_set_is_the_declared_one(self):
        self.assertEqual(
            COMPONENT_CATEGORIES,
            ("representative", "delta-credited", "non-representative"),
        )

    def test_tolerance_is_representation_sized(self):
        self.assertLess(CREDIT_TOLERANCE, 1e-6)


class CompareBuildStandardTests(unittest.TestCase):
    def test_identical_build_standard_has_no_deviation(self):
        self.assertEqual(compare_build_standard(fitted(), dict(FLIGHT)), ())

    def test_package_substitution_is_found(self):
        self.assertEqual(
            compare_build_standard(fitted(package="LQFP-32"), dict(FLIGHT)), ("package",)
        )

    def test_comparison_is_case_insensitive(self):
        self.assertEqual(compare_build_standard(fitted(package="qfn-32"), dict(FLIGHT)), ())

    def test_deviations_are_returned_sorted(self):
        found = compare_build_standard(
            fitted(package="LQFP-32", die_lot="LOT-9000"), dict(FLIGHT)
        )
        self.assertEqual(found, ("die_lot", "package"))

    def test_missing_attribute_is_refused_not_read_as_a_match(self):
        short = dict(FLIGHT)
        del short["die_lot"]
        with self.assertRaises(ValueError):
            compare_build_standard(short, dict(FLIGHT))

    def test_blank_attribute_value_rejected(self):
        with self.assertRaises(ValueError):
            compare_build_standard(fitted(package="   "), dict(FLIGHT))

    def test_non_mapping_component_rejected(self):
        with self.assertRaises(ValueError):
            compare_build_standard(["package"], dict(FLIGHT))


class ValidateAcceptanceTests(unittest.TestCase):
    def test_well_formed_record_is_normalised(self):
        record = validate_acceptance(
            acceptance("package", ["thermal", "mechanical"]), ("package",)
        )
        self.assertEqual(record["domains"], ("mechanical", "thermal"))
        self.assertAlmostEqual(record["credit"], DEFAULT_ACCEPTANCE_CREDIT, places=9)

    def test_acceptance_on_a_fundamental_attribute_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("part_number", ["mechanical"]), ("part_number",)
            )

    def test_acceptance_for_a_non_deviating_attribute_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(acceptance("package", ["mechanical"]), ("die_lot",))

    def test_delta_test_claiming_an_untouched_domain_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(acceptance("package", ["radiation"]), ("package",))

    def test_blank_justification_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("package", ["mechanical"], justification="  "), ("package",)
            )

    def test_blank_delta_test_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("package", ["mechanical"], delta_test=""), ("package",)
            )

    def test_empty_domain_list_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(acceptance("package", []), ("package",))

    def test_zero_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("package", ["mechanical"], credit=0.0), ("package",)
            )

    def test_credit_above_unity_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("package", ["mechanical"], credit=1.4), ("package",)
            )

    def test_duplicate_domain_refused(self):
        with self.assertRaises(ValueError):
            validate_acceptance(
                acceptance("package", ["thermal", "thermal"]), ("package",)
            )


class DomainTransferCreditTests(unittest.TestCase):
    def test_no_deviation_leaves_full_credit(self):
        credits = domain_transfer_credit(())
        for domain in TRANSFER_DOMAINS:
            self.assertAlmostEqual(credits[domain], 1.0, places=9)

    def test_package_deviation_costs_mechanical_outright_and_thermal_in_part(self):
        credits = domain_transfer_credit(("package",))
        self.assertAlmostEqual(credits["mechanical"], 0.0, places=9)
        self.assertAlmostEqual(credits["thermal"], 0.4, places=9)
        self.assertAlmostEqual(credits["electrical"], 1.0, places=9)

    def test_untouched_domains_keep_full_credit(self):
        credits = domain_transfer_credit(("die_lot",))
        self.assertAlmostEqual(credits["mechanical"], 1.0, places=9)
        self.assertAlmostEqual(credits["radiation"], 0.0, places=9)
        self.assertAlmostEqual(credits["lifetime"], 0.2, places=9)

    def test_acceptance_restores_the_declared_share_only(self):
        credits = domain_transfer_credit(
            ("package",), [acceptance("package", ["mechanical", "thermal"], credit=0.5)]
        )
        self.assertAlmostEqual(credits["mechanical"], 0.5, places=9)
        self.assertAlmostEqual(credits["thermal"], 0.7, places=9)

    def test_acceptance_restores_only_the_domains_its_delta_test_covers(self):
        credits = domain_transfer_credit(
            ("package",), [acceptance("package", ["mechanical"], credit=1.0)]
        )
        self.assertAlmostEqual(credits["mechanical"], 1.0, places=9)
        self.assertAlmostEqual(credits["thermal"], 0.4, places=9)

    def test_deviations_compound_on_a_shared_domain(self):
        credits = domain_transfer_credit(("board_mounting", "date_code_range"))
        self.assertAlmostEqual(credits["mechanical"], 0.3, places=9)
        self.assertAlmostEqual(credits["thermal"], 0.6, places=9)
        self.assertAlmostEqual(credits["lifetime"], 0.7, places=9)

    def test_duplicate_deviation_rejected(self):
        with self.assertRaises(ValueError):
            domain_transfer_credit(("package", "package"))

    def test_unknown_deviation_rejected(self):
        with self.assertRaises(ValueError):
            domain_transfer_credit(("paint_colour",))

    def test_two_acceptance_records_for_one_attribute_rejected(self):
        with self.assertRaises(ValueError):
            domain_transfer_credit(
                ("package",),
                [
                    acceptance("package", ["mechanical"]),
                    acceptance("package", ["thermal"]),
                ],
            )


class FloorAndCategoryTests(unittest.TestCase):
    def test_credit_exactly_at_the_floor_counts_as_met(self):
        credits = {domain: 1.0 for domain in TRANSFER_DOMAINS}
        credits["lifetime"] = DEFAULT_CREDIT_FLOOR
        self.assertEqual(domains_below_floor(credits), ())

    def test_credit_a_representation_step_under_the_floor_counts_as_met(self):
        credits = {domain: 1.0 for domain in TRANSFER_DOMAINS}
        credits["lifetime"] = DEFAULT_CREDIT_FLOOR - CREDIT_TOLERANCE / 10.0
        self.assertEqual(domains_below_floor(credits), ())

    def test_short_domains_are_reported_sorted(self):
        credits = domain_transfer_credit(("board_mounting",))
        self.assertEqual(domains_below_floor(credits), ("mechanical", "thermal"))

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            domains_below_floor({domain: 1.0 for domain in TRANSFER_DOMAINS}, floor=1.5)

    def test_unknown_domain_in_credit_map_rejected(self):
        with self.assertRaises(ValueError):
            domains_below_floor({"acoustic": 1.0})

    def test_clean_component_is_representative(self):
        credits = domain_transfer_credit(())
        self.assertEqual(component_category((), credits), "representative")

    def test_fundamental_deviation_is_non_representative_whatever_the_credit(self):
        credits = {domain: 1.0 for domain in TRANSFER_DOMAINS}
        self.assertEqual(
            component_category(("manufacturer",), credits), "non-representative"
        )

    def test_deviation_inside_the_floor_is_delta_credited(self):
        credits = domain_transfer_credit(("date_code_range",))
        self.assertEqual(
            component_category(("date_code_range",), credits), "delta-credited"
        )

    def test_deviation_under_the_floor_is_non_representative(self):
        credits = domain_transfer_credit(("screening_flow",))
        self.assertEqual(
            component_category(("screening_flow",), credits), "non-representative"
        )


class EvaluateComponentTests(unittest.TestCase):
    def test_clean_component_record(self):
        record = evaluate_eqm_component(item())
        self.assertEqual(record["category"], "representative")
        self.assertEqual(record["deviations"], ())
        self.assertEqual(record["retest_domains"], ())

    def test_undocumented_deviation_is_reported_even_inside_the_floor(self):
        record = evaluate_eqm_component(item(date_code_range="2501-2506"))
        self.assertEqual(record["category"], "delta-credited")
        self.assertEqual(record["undocumented_deviations"], ("date_code_range",))

    def test_accepted_deviation_leaves_no_undocumented_entry(self):
        record = evaluate_eqm_component(
            item(
                date_code_range="2501-2506",
                acceptances=[acceptance("date_code_range", ["lifetime"], credit=1.0)],
            )
        )
        self.assertEqual(record["undocumented_deviations"], ())
        self.assertAlmostEqual(record["domain_credit"]["lifetime"], 1.0, places=9)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_eqm_component(item(quantity=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_eqm_component(item(quantity=True))

    def test_blank_reference_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_eqm_component(item(reference="  "))


class ModelLevelTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "components": [
                item(reference="U1"),
                item(reference="U2", quantity=3, date_code_range="2501-2506"),
            ]
        }
        spec.update(overrides)
        return spec

    def test_installed_quantity_weights_the_model_credit(self):
        result = assess_class2_eqm_transfer(self._spec())
        self.assertAlmostEqual(result["model_domain_credit"]["lifetime"], 0.775, places=9)

    def test_model_verdict_is_delta_test_bound_when_a_part_is_credited(self):
        result = assess_class2_eqm_transfer(self._spec())
        self.assertEqual(result["verdict"], "transferable-with-delta-tests")

    def test_clean_model_transfers(self):
        result = assess_class2_eqm_transfer(
            {"components": [item(reference="U1"), item(reference="U2")]}
        )
        self.assertEqual(result["verdict"], "transferable")
        self.assertEqual(result["retest_domains"], ())
        self.assertEqual(result["findings"], [])

    def test_one_fundamental_deviation_stops_the_whole_transfer(self):
        result = assess_class2_eqm_transfer(
            {
                "components": [
                    item(reference="U1"),
                    item(reference="U2", manufacturer="Vendor-B"),
                ]
            }
        )
        self.assertEqual(result["verdict"], "not-transferable")
        self.assertEqual(result["category_counts"]["non-representative"], 1)

    def test_retest_set_is_the_union_across_components(self):
        result = assess_class2_eqm_transfer(
            {
                "components": [
                    item(reference="U1", package="LQFP-32"),
                    item(reference="U2", die_lot="LOT-9000"),
                ]
            }
        )
        self.assertEqual(
            result["retest_domains"], ("lifetime", "mechanical", "radiation", "thermal")
        )

    def test_findings_are_ordered_worst_first(self):
        result = assess_class2_eqm_transfer(
            {
                "components": [
                    item(reference="U9", date_code_range="2501-2506"),
                    item(reference="U1", package="LQFP-32"),
                ]
            }
        )
        self.assertEqual(result["findings"][0]["severity"], 0)
        self.assertEqual(result["findings"][0]["reference"], "U1")

    def test_duplicate_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_eqm_transfer(
                {"components": [item(reference="U1"), item(reference="U1")]}
            )

    def test_empty_component_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_eqm_transfer({"components": []})

    def test_missing_components_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_eqm_transfer({"floor": 0.7})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_eqm_transfer(["components"])

    def test_raising_the_floor_can_turn_a_credited_part_short(self):
        result = assess_class2_eqm_transfer(self._spec(floor=0.9))
        self.assertEqual(result["verdict"], "not-transferable")

    def test_model_credit_requires_records(self):
        with self.assertRaises(ValueError):
            model_domain_credit([])


if __name__ == "__main__":
    unittest.main()
