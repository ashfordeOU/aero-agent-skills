"""Contract tests for the clause 6.6.3 lowest-class hybrid procurement logic."""

import unittest

from q6013_class_3_hybrid_components_logic import (
    BASIS_RANK,
    DEFAULT_BASIS_FLOOR,
    DEFAULT_CRITICALITY,
    DEFAULT_EXPOSURE_CAP,
    DEFAULT_TRACEABILITY_FLOOR,
    ELEMENT_KINDS,
    PROCUREMENT_VERDICTS,
    ROLLUP_TOLERANCE,
    UNREFERENCED_BASIS,
    assess_hybrid_procurement,
    basis_rank,
    element_weights,
    validate_criticality,
    validate_element,
    validate_elements,
    validate_identifier,
    weakest_basis,
    weighted_share,
)

GOOD_BASIS = "vendor-detail-specification"


def element(identifier, kind, basis=GOOD_BASIS, traceable=True, notified=True):
    """Return one normalisable constituent-element mapping."""
    return {
        "identifier": identifier,
        "kind": kind,
        "basis": basis,
        "lot_traceable": traceable,
        "change_notified": notified,
    }


def full_set(**overrides):
    """Return one element of every recognised kind, with overrides by kind."""
    items = []
    for index, kind in enumerate(ELEMENT_KINDS):
        item = element("EL-%02d" % index, kind)
        item.update(overrides.get(kind, {}))
        items.append(item)
    return items


def record(**overrides):
    """Return a clean hybrid record with overrides applied."""
    base = {"reference": "HYB-1", "elements": full_set()}
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier("  HYB-1 ", "reference"), "HYB-1")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ", "reference")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7, "reference")


class CriticalityTests(unittest.TestCase):
    def test_default_weights_sum_to_unity(self):
        self.assertAlmostEqual(sum(validate_criticality().values()), 1.0, places=9)

    def test_default_set_returned_when_omitted(self):
        self.assertEqual(sorted(validate_criticality()), sorted(DEFAULT_CRITICALITY))

    def test_weights_not_summing_to_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_criticality({"die": 0.5, "substrate": 0.2})

    def test_unrecognised_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_criticality({"paint": 1.0})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_criticality({"die": -1.0, "substrate": 2.0})

    def test_empty_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_criticality({})


class BasisRankTests(unittest.TestCase):
    def test_generic_plus_detail_outranks_vendor_detail(self):
        self.assertGreater(
            basis_rank("generic-and-detail-specification"),
            basis_rank("vendor-detail-specification"),
        )

    def test_unreferenced_sits_below_every_referenced_basis(self):
        self.assertEqual(basis_rank(UNREFERENCED_BASIS), 0)

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            basis_rank("a-handshake")


class ValidateElementTests(unittest.TestCase):
    def test_clean_element_normalises(self):
        item = validate_element(element("EL-1", "die"))
        self.assertEqual(item["basis_rank"], BASIS_RANK[GOOD_BASIS])

    def test_unrecognised_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_element(element("EL-1", "lid-label"))

    def test_non_boolean_traceability_rejected(self):
        item = element("EL-1", "die")
        item["lot_traceable"] = "yes"
        with self.assertRaises(ValueError):
            validate_element(item)

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([element("EL-1", "die"), element("EL-1", "substrate")])

    def test_element_list_without_a_die_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([element("EL-1", "substrate")])

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_elements([])


class ElementWeightTests(unittest.TestCase):
    def test_one_of_each_kind_carries_the_full_criticality(self):
        shares = element_weights(validate_elements(full_set()))
        self.assertAlmostEqual(sum(shares), 1.0, places=9)

    def test_two_elements_of_a_kind_share_that_kinds_weight(self):
        items = validate_elements(
            [element("EL-1", "die"), element("EL-2", "die")]
        )
        shares = element_weights(items)
        self.assertAlmostEqual(shares[0], DEFAULT_CRITICALITY["die"] / 2.0, places=9)

    def test_weakest_basis_governs_the_assembly(self):
        items = validate_elements(
            [
                element("EL-1", "die", "generic-and-detail-specification"),
                element("EL-2", "substrate", "catalogue-datasheet"),
            ]
        )
        self.assertEqual(weakest_basis(items)[0], "catalogue-datasheet")

    def test_weighted_share_of_a_fully_traceable_build_is_unity(self):
        items = validate_elements(full_set())
        self.assertAlmostEqual(weighted_share(items, "lot_traceable"), 1.0, places=9)

    def test_weighted_share_drops_by_the_untraceable_kinds_weight(self):
        items = validate_elements(full_set(die={"lot_traceable": False}))
        self.assertAlmostEqual(
            weighted_share(items, "lot_traceable"),
            1.0 - DEFAULT_CRITICALITY["die"],
            places=9,
        )

    def test_unknown_share_key_rejected(self):
        with self.assertRaises(ValueError):
            weighted_share(validate_elements(full_set()), "colour")


class AssessmentTests(unittest.TestCase):
    def test_clean_build_is_accepted(self):
        result = assess_hybrid_procurement(record())
        self.assertEqual(result["verdict"], "procurement-accepted")

    def test_clean_build_reports_full_traceability(self):
        result = assess_hybrid_procurement(record())
        self.assertAlmostEqual(result["traceability_coverage"], 1.0, places=9)

    def test_clean_build_reports_no_exposure(self):
        result = assess_hybrid_procurement(record())
        self.assertAlmostEqual(result["source_change_exposure"], 0.0, places=9)

    def test_unreferenced_element_closes_the_assessment(self):
        result = assess_hybrid_procurement(
            record(elements=full_set(substrate={"basis": UNREFERENCED_BASIS}))
        )
        self.assertEqual(result["verdict"], "refuse-unreferenced-element")

    def test_unreferenced_element_is_named(self):
        result = assess_hybrid_procurement(
            record(elements=full_set(substrate={"basis": UNREFERENCED_BASIS}))
        )
        self.assertEqual(len(result["unreferenced_elements"]), 1)

    def test_effective_basis_is_the_poorest_present(self):
        result = assess_hybrid_procurement(
            record(elements=full_set(interconnect={"basis": "catalogue-datasheet"}))
        )
        self.assertEqual(result["effective_basis"], "catalogue-datasheet")

    def test_basis_below_a_raised_floor_escalates(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(interconnect={"basis": "catalogue-datasheet"}),
                basis_floor=2,
            )
        )
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_basis_shortfall_lists_the_weak_element(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(interconnect={"basis": "catalogue-datasheet"}),
                basis_floor=2,
            )
        )
        self.assertEqual(len(result["basis_shortfall"]), 1)

    def test_traceability_below_its_floor_escalates(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(
                    die={"lot_traceable": False},
                    substrate={"lot_traceable": False},
                    interconnect={"lot_traceable": False},
                )
            )
        )
        self.assertEqual(result["verdict"], "escalate-to-parts-control-board")

    def test_traceability_landing_exactly_on_its_floor_counts_as_met(self):
        floor = 1.0 - DEFAULT_CRITICALITY["die"]
        result = assess_hybrid_procurement(
            record(
                elements=full_set(die={"lot_traceable": False}),
                traceability_floor=floor,
            )
        )
        self.assertTrue(result["traceability_met"])

    def test_exposure_above_its_cap_is_recorded_not_refused(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(
                    die={"change_notified": False},
                    substrate={"change_notified": False},
                )
            )
        )
        self.assertEqual(result["verdict"], "accepted-with-recorded-exposure")

    def test_exposure_landing_exactly_on_its_cap_counts_as_met(self):
        cap = DEFAULT_CRITICALITY["package-seal"]
        item = full_set()
        item[ELEMENT_KINDS.index("package-seal")]["change_notified"] = False
        result = assess_hybrid_procurement(record(elements=item, exposure_cap=cap))
        self.assertTrue(result["exposure_met"])

    def test_unreferenced_element_outranks_an_exposure_finding(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(
                    substrate={"basis": UNREFERENCED_BASIS, "change_notified": False},
                    die={"change_notified": False},
                )
            )
        )
        self.assertEqual(result["verdict"], "refuse-unreferenced-element")

    def test_findings_are_ordered_by_severity(self):
        result = assess_hybrid_procurement(
            record(
                elements=full_set(
                    substrate={"basis": UNREFERENCED_BASIS},
                    die={"change_notified": False},
                )
            )
        )
        severities = [item["severity"] for item in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_missing_elements_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement({"reference": "HYB-1"})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(["HYB-1"])

    def test_basis_floor_below_a_referenced_rank_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(record(basis_floor=0))

    def test_traceability_floor_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(record(traceability_floor=1.4))

    def test_exposure_cap_below_zero_rejected(self):
        with self.assertRaises(ValueError):
            assess_hybrid_procurement(record(exposure_cap=-0.1))

    def test_verdict_is_drawn_from_the_published_set(self):
        result = assess_hybrid_procurement(record())
        self.assertIn(result["verdict"], PROCUREMENT_VERDICTS)

    def test_default_floor_and_cap_are_fractions(self):
        self.assertLess(DEFAULT_EXPOSURE_CAP, DEFAULT_TRACEABILITY_FLOOR)

    def test_default_basis_floor_is_a_referenced_rank(self):
        self.assertEqual(DEFAULT_BASIS_FLOOR, BASIS_RANK["catalogue-datasheet"])

    def test_tolerance_is_representation_sized(self):
        self.assertLess(ROLLUP_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
