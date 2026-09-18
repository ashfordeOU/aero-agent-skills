"""Contract tests for the ECSS-Q-ST-70-29 offgassing acceptance-criteria logic."""

import unittest

from q7029_acceptance_criteria_logic import (
    ODOUR_FAIL,
    ODOUR_NOT_GRADED,
    ODOUR_PASS,
    VERDICT_ACCEPTED,
    VERDICT_OPEN,
    VERDICT_REJECTED,
    apply_acceptance,
    class_criteria,
    compound_criteria,
    governing_criterion,
    odour_criterion,
    toxicity_criterion,
    unidentified_criterion,
    utilisation,
    validate_limit_map,
)

COMPOUND_LIMITS = {
    "toluene": 8.0,
    "benzene": 0.3,
    "hexanal": 5.0,
    "heptanal": 5.0,
}

CLASS_CAPS = {
    "aromatic-hydrocarbon": 10.0,
    "aldehyde": 6.0,
}


def product(compound, conc, chem_class):
    return {
        "compound": compound,
        "concentration_mg_m3": conc,
        "chemical_class": chem_class,
    }


class LimitMapTests(unittest.TestCase):
    def test_limits_are_normalised(self):
        limits = validate_limit_map({" toluene ": 8.0})
        self.assertAlmostEqual(limits["toluene"], 8.0, places=9)

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_map({"toluene": 0.0})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_map(["toluene"])

    def test_empty_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_map({"  ": 8.0})


class UtilisationTests(unittest.TestCase):
    def test_half_of_the_limit(self):
        self.assertAlmostEqual(utilisation(4.0, 8.0), 0.5, places=9)

    def test_exactly_on_the_limit(self):
        self.assertAlmostEqual(utilisation(8.0, 8.0), 1.0, places=9)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            utilisation(4.0, 0.0)

    def test_negative_observation_rejected(self):
        with self.assertRaises(ValueError):
            utilisation(-4.0, 8.0)


class CompoundCriteriaTests(unittest.TestCase):
    def test_every_limited_compound_gets_a_criterion(self):
        crits, opens = compound_criteria(
            [product("toluene", 4.0, "aromatic-hydrocarbon")], COMPOUND_LIMITS
        )
        self.assertEqual(len(crits), 1)
        self.assertEqual(opens, [])
        self.assertTrue(crits[0]["met"])

    def test_compound_exactly_on_its_limit_is_met(self):
        crits, _ = compound_criteria(
            [product("toluene", 8.0, "aromatic-hydrocarbon")], COMPOUND_LIMITS
        )
        self.assertAlmostEqual(crits[0]["utilisation"], 1.0, places=9)
        self.assertTrue(crits[0]["met"])

    def test_compound_over_its_limit_is_not_met(self):
        crits, _ = compound_criteria(
            [product("benzene", 0.9, "aromatic-hydrocarbon")], COMPOUND_LIMITS
        )
        self.assertFalse(crits[0]["met"])

    def test_unlimited_compound_becomes_an_open_item(self):
        crits, opens = compound_criteria(
            [product("unknown-siloxane", 4.0, "siloxane")], COMPOUND_LIMITS
        )
        self.assertEqual(crits, [])
        self.assertEqual(len(opens), 1)

    def test_duplicate_compound_rejected(self):
        with self.assertRaises(ValueError):
            compound_criteria(
                [product("toluene", 1.0, "aromatic-hydrocarbon"),
                 product("toluene", 2.0, "aromatic-hydrocarbon")],
                COMPOUND_LIMITS,
            )

    def test_product_missing_a_class_rejected(self):
        with self.assertRaises(ValueError):
            compound_criteria([{"compound": "toluene", "concentration_mg_m3": 1.0}],
                              COMPOUND_LIMITS)

    def test_empty_product_set_rejected(self):
        with self.assertRaises(ValueError):
            compound_criteria([], COMPOUND_LIMITS)


class ClassCriteriaTests(unittest.TestCase):
    def test_class_sum_adds_its_members(self):
        _, _, sums = class_criteria(
            [product("hexanal", 3.0, "aldehyde"), product("heptanal", 2.0, "aldehyde")],
            CLASS_CAPS,
        )
        self.assertAlmostEqual(sums["aldehyde"], 5.0, places=9)

    def test_members_inside_their_own_limits_can_breach_the_cap(self):
        products = [product("hexanal", 4.0, "aldehyde"), product("heptanal", 4.0, "aldehyde")]
        comp_crits, _ = compound_criteria(products, COMPOUND_LIMITS)
        self.assertTrue(all(c["met"] for c in comp_crits))
        class_crits, _, _ = class_criteria(products, CLASS_CAPS)
        self.assertFalse(class_crits[0]["met"])

    def test_class_sum_exactly_on_the_cap_is_met(self):
        products = [product("hexanal", 3.0, "aldehyde"), product("heptanal", 3.0, "aldehyde")]
        class_crits, _, _ = class_criteria(products, CLASS_CAPS)
        self.assertAlmostEqual(class_crits[0]["utilisation"], 1.0, places=9)
        self.assertTrue(class_crits[0]["met"])

    def test_class_without_a_cap_becomes_an_open_item(self):
        _, opens, _ = class_criteria([product("unknown", 1.0, "siloxane")], CLASS_CAPS)
        self.assertEqual(len(opens), 1)

    def test_empty_class_name_rejected(self):
        with self.assertRaises(ValueError):
            class_criteria([product("toluene", 1.0, "  ")], CLASS_CAPS)


class SingleCriterionTests(unittest.TestCase):
    def test_toxicity_total_under_the_bound_is_met(self):
        self.assertTrue(toxicity_criterion(0.4)["met"])

    def test_toxicity_total_exactly_on_the_bound_is_met(self):
        crit = toxicity_criterion(1.0)
        self.assertAlmostEqual(crit["utilisation"], 1.0, places=9)
        self.assertTrue(crit["met"])

    def test_toxicity_total_over_the_bound_is_not_met(self):
        self.assertFalse(toxicity_criterion(1.4)["met"])

    def test_odour_pass_is_met(self):
        self.assertTrue(odour_criterion(ODOUR_PASS)["met"])

    def test_odour_fail_is_not_met(self):
        self.assertFalse(odour_criterion(ODOUR_FAIL)["met"])

    def test_unknown_odour_verdict_rejected(self):
        with self.assertRaises(ValueError):
            odour_criterion("maybe")

    def test_unidentified_fraction_inside_its_budget_is_met(self):
        self.assertTrue(unidentified_criterion(0.02, 0.05)["met"])

    def test_unidentified_fraction_over_its_budget_is_not_met(self):
        self.assertFalse(unidentified_criterion(0.09, 0.05)["met"])

    def test_unidentified_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            unidentified_criterion(1.4, 0.05)

    def test_governing_criterion_is_the_highest_utilisation(self):
        best = governing_criterion([
            {"criterion": "a", "utilisation": 0.4, "detail": "x"},
            {"criterion": "b", "utilisation": 0.9, "detail": "y"},
        ])
        self.assertEqual(best["criterion"], "b")

    def test_governing_criterion_needs_a_criterion(self):
        with self.assertRaises(ValueError):
            governing_criterion([])


class ApplyAcceptanceTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "products": [
                product("toluene", 4.0, "aromatic-hydrocarbon"),
                product("hexanal", 2.0, "aldehyde"),
            ],
            "compound_limits": COMPOUND_LIMITS,
            "class_caps": CLASS_CAPS,
            "governing_t_value": 0.4,
            "odour_verdict": ODOUR_PASS,
            "unidentified_fraction": 0.02,
            "unidentified_budget": 0.05,
        }
        spec.update(overrides)
        return spec

    def test_clean_article_is_accepted(self):
        result = apply_acceptance(self._spec())
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["breached"], [])

    def test_governing_criterion_is_named(self):
        result = apply_acceptance(self._spec())
        # toluene sits at 4.0 of its 8.0 limit, above every other utilisation.
        self.assertEqual(result["governing_criterion"], "compound-limit")
        self.assertEqual(result["governing_detail"], "toluene")
        self.assertAlmostEqual(result["governing_utilisation"], 0.5, places=9)

    def test_toxicity_total_can_govern_when_it_is_the_highest(self):
        result = apply_acceptance(self._spec(governing_t_value=0.95))
        self.assertEqual(result["governing_criterion"], "toxicity-total")
        self.assertAlmostEqual(result["governing_utilisation"], 0.95, places=9)

    def test_one_breached_compound_rejects_the_article(self):
        spec = self._spec(products=[
            product("benzene", 0.9, "aromatic-hydrocarbon"),
            product("hexanal", 2.0, "aldehyde"),
        ])
        result = apply_acceptance(spec)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(len(result["breached"]), 1)

    def test_class_cap_rejects_an_article_with_compliant_members(self):
        spec = self._spec(products=[
            product("hexanal", 4.0, "aldehyde"),
            product("heptanal", 4.0, "aldehyde"),
        ])
        result = apply_acceptance(spec)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["governing_criterion"], "class-cap")

    def test_odour_failure_alone_rejects_the_article(self):
        result = apply_acceptance(self._spec(odour_verdict=ODOUR_FAIL))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_ungraded_odour_panel_leaves_the_article_open(self):
        result = apply_acceptance(self._spec(odour_verdict=ODOUR_NOT_GRADED))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(any("not graded" in item for item in result["open_items"]))

    def test_unlimited_compound_leaves_the_article_open_not_accepted(self):
        spec = self._spec(products=[
            product("toluene", 4.0, "aromatic-hydrocarbon"),
            product("unknown-siloxane", 0.1, "aromatic-hydrocarbon"),
        ])
        result = apply_acceptance(spec)
        self.assertEqual(result["verdict"], VERDICT_OPEN)
        self.assertFalse(result["accepted"])

    def test_unidentified_budget_breach_rejects_the_article(self):
        result = apply_acceptance(self._spec(unidentified_fraction=0.2))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["governing_criterion"], "unidentified-area")

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["class_caps"]
        with self.assertRaises(ValueError):
            apply_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            apply_acceptance(["products"])


if __name__ == "__main__":
    unittest.main()
