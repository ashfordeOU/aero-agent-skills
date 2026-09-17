"""Contract tests for the clause 6.3.7 Class 3 incoming inspection logic.

The cases follow a Class 3 delivery across the goods-in bench: the chain it
came through and the examination depth that earns, the breach that pushes the
depth a step deeper, the integer draw the depth takes, the evidence an
unfranchised source owes, the defects grouped by severity against their
acceptance numbers, and the bonded-store, conditional-release or quarantine
decision that comes out of all of it.
"""

import unittest

from q60_class_3_incoming_inspection_logic import (
    BASE_ARRIVAL_DOCUMENTS,
    DEFECT_SEVERITIES,
    DEPTHS,
    DEPTH_DRAW_MULTIPLIER,
    DISPOSITION_PRECEDENCE,
    MINIMUM_ARRIVAL_DRAW,
    SOURCE_TIERS,
    UNFRANCHISED_ARRIVAL_DOCUMENTS,
    acceptance_numbers,
    arrival_draw,
    assess_incoming_inspection,
    documentation_findings,
    escalate_depth,
    inspection_depth,
    normalize_source_tier,
    packaging_findings,
    reconcile_quantity,
    required_documents_for_tier,
    tally_defects,
)


def _packaging(**overrides):
    record = {"seal_intact": True, "esd_bag_intact": True, "humidity_indicator": "blue"}
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "source_tier": "franchised-distributor",
        "packaging": _packaging(),
        "documents": list(BASE_ARRIVAL_DOCUMENTS),
        "declared": 400,
        "counted": 400,
        "damaged": 0,
        "defects": [],
    }
    spec.update(overrides)
    return spec


def _defect(severity="minor", description="cosmetic mark on the body"):
    return {"severity": severity, "description": description}


class SourceTierTests(unittest.TestCase):
    def test_every_declared_tier_normalizes(self):
        for tier in SOURCE_TIERS:
            self.assertEqual(normalize_source_tier(tier.upper()), tier)

    def test_an_undeclared_tier_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_source_tier("a-man-at-a-trade-show")

    def test_an_empty_tier_is_refused(self):
        with self.assertRaises(ValueError):
            normalize_source_tier("   ")

    def test_an_unfranchised_chain_owes_extra_evidence(self):
        owed = required_documents_for_tier("open-market-broker")
        for name in UNFRANCHISED_ARRIVAL_DOCUMENTS:
            self.assertIn(name, owed)

    def test_a_franchised_chain_owes_only_the_base_pack(self):
        self.assertEqual(
            required_documents_for_tier("franchised-distributor"),
            tuple(BASE_ARRIVAL_DOCUMENTS),
        )


class DepthTests(unittest.TestCase):
    def test_manufacturer_direct_starts_reduced(self):
        record = inspection_depth("manufacturer-direct", _packaging())
        self.assertEqual(record["depth"], "reduced")
        self.assertFalse(record["escalated"])

    def test_an_open_market_chain_starts_extended(self):
        record = inspection_depth("open-market-broker", _packaging())
        self.assertEqual(record["depth"], "extended")
        self.assertTrue(record["authenticity_required"])

    def test_a_broken_seal_escalates_one_step(self):
        record = inspection_depth("manufacturer-direct", _packaging(seal_intact=False))
        self.assertEqual(record["depth"], "standard")
        self.assertTrue(record["escalated"])

    def test_an_open_bag_escalates_one_step(self):
        record = inspection_depth(
            "franchised-distributor", _packaging(esd_bag_intact=False)
        )
        self.assertEqual(record["depth"], "extended")

    def test_escalation_stops_at_the_deepest_examination(self):
        self.assertEqual(escalate_depth("extended", 4), "extended")

    def test_escalating_by_nothing_holds_the_depth(self):
        self.assertEqual(escalate_depth("standard", 0), "standard")

    def test_an_undeclared_depth_is_refused(self):
        with self.assertRaises(ValueError):
            escalate_depth("thorough")

    def test_a_damp_indicator_is_a_finding_but_not_an_escalation(self):
        record = inspection_depth(
            "manufacturer-direct", _packaging(humidity_indicator="pink")
        )
        self.assertEqual(record["depth"], "reduced")
        self.assertFalse(record["packaging"]["sound"])

    def test_packaging_missing_a_key_is_refused(self):
        packaging = _packaging()
        del packaging["humidity_indicator"]
        with self.assertRaises(ValueError):
            packaging_findings(packaging)

    def test_a_non_boolean_seal_is_refused(self):
        with self.assertRaises(ValueError):
            packaging_findings(_packaging(seal_intact="yes"))


class DrawTests(unittest.TestCase):
    def test_the_draw_scales_with_the_depth(self):
        shallow = arrival_draw(400, "reduced")
        deep = arrival_draw(400, "extended")
        self.assertEqual(deep, DEPTH_DRAW_MULTIPLIER["extended"] * shallow)

    def test_the_draw_is_integer_square_root_plus_one(self):
        self.assertEqual(arrival_draw(400, "reduced"), 21)

    def test_a_non_square_quantity_draws_the_floor_of_its_root(self):
        self.assertEqual(arrival_draw(399, "reduced"), 20)

    def test_the_draw_is_raised_to_the_floor(self):
        self.assertEqual(arrival_draw(1, "reduced"), 1)

    def test_the_draw_never_exceeds_the_delivery(self):
        self.assertEqual(arrival_draw(4, "extended"), 4)

    def test_a_small_delivery_still_draws_the_minimum(self):
        self.assertEqual(arrival_draw(9, "reduced"), max(MINIMUM_ARRIVAL_DRAW, 4))

    def test_a_zero_quantity_draw_is_refused(self):
        with self.assertRaises(ValueError):
            arrival_draw(0, "reduced")

    def test_an_undeclared_depth_draw_is_refused(self):
        with self.assertRaises(ValueError):
            arrival_draw(400, "exhaustive")


class AcceptanceNumberTests(unittest.TestCase):
    def test_a_critical_defect_is_never_tolerated(self):
        for depth in DEPTHS:
            self.assertEqual(acceptance_numbers(50, depth)["critical"], 0)

    def test_an_extended_examination_tolerates_no_major_defect(self):
        self.assertEqual(acceptance_numbers(60, "extended")["major"], 0)

    def test_a_standard_examination_tolerates_a_major_defect_on_a_wide_draw(self):
        self.assertEqual(acceptance_numbers(50, "standard")["major"], 2)

    def test_the_minor_allowance_grows_with_the_draw(self):
        self.assertGreater(
            acceptance_numbers(100, "standard")["minor"],
            acceptance_numbers(10, "standard")["minor"],
        )

    def test_an_empty_draw_has_no_acceptance_numbers(self):
        with self.assertRaises(ValueError):
            acceptance_numbers(0, "standard")


class DefectTallyTests(unittest.TestCase):
    def test_defects_are_grouped_by_severity(self):
        tally = tally_defects([_defect("minor"), _defect("minor"), _defect("major")])
        self.assertEqual(tally["counts"]["minor"], 2)
        self.assertEqual(tally["counts"]["major"], 1)

    def test_the_worst_severity_present_is_reported(self):
        tally = tally_defects([_defect("minor"), _defect("critical")])
        self.assertEqual(tally["worst"], "critical")

    def test_an_empty_draw_report_has_no_worst_severity(self):
        self.assertIsNone(tally_defects([])["worst"])

    def test_an_ungraded_severity_is_refused(self):
        with self.assertRaises(ValueError):
            tally_defects([_defect("cosmetic")])

    def test_a_defect_without_a_description_is_refused(self):
        with self.assertRaises(ValueError):
            tally_defects([{"severity": "minor"}])

    def test_defects_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            tally_defects(_defect())

    def test_every_declared_severity_appears_in_the_tally(self):
        tally = tally_defects([])
        for severity in DEFECT_SEVERITIES:
            self.assertIn(severity, tally["counts"])


class QuantityTests(unittest.TestCase):
    def test_transit_damage_leaves_the_accepted_count(self):
        record = reconcile_quantity(400, 400, 4)
        self.assertEqual(record["accepted"], 396)
        self.assertFalse(record["reconciled"])

    def test_a_short_delivery_is_a_signed_discrepancy(self):
        self.assertEqual(reconcile_quantity(400, 390)["discrepancy"], -10)

    def test_damage_above_the_bench_count_is_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(400, 10, 11)

    def test_a_zero_declared_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            reconcile_quantity(0, 0)


class DispositionTests(unittest.TestCase):
    def test_a_clean_franchised_delivery_enters_the_bonded_store(self):
        result = assess_incoming_inspection(_spec())
        self.assertEqual(result["disposition"], "accept-into-bonded-store")
        self.assertEqual(result["findings"], [])

    def test_every_disposition_is_one_of_the_declared_dispositions(self):
        result = assess_incoming_inspection(_spec())
        self.assertIn(result["disposition"], DISPOSITION_PRECEDENCE)

    def test_a_critical_defect_quarantines_the_delivery(self):
        result = assess_incoming_inspection(_spec(defects=[_defect("critical", "cracked body")]))
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(result["accepted_pieces"], 0)

    def test_missing_traceability_quarantines_an_open_market_delivery(self):
        result = assess_incoming_inspection(
            _spec(
                source_tier="open-market-broker",
                documents=list(BASE_ARRIVAL_DOCUMENTS),
                marking_permanency_pass=True,
            )
        )
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(len(result["documents"]["missing"]), 2)

    def test_an_extended_examination_without_a_marking_result_is_refused(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(_spec(source_tier="independent-distributor"))

    def test_a_failed_marking_permanency_test_quarantines(self):
        documents = list(BASE_ARRIVAL_DOCUMENTS) + list(UNFRANCHISED_ARRIVAL_DOCUMENTS)
        result = assess_incoming_inspection(
            _spec(
                source_tier="open-market-broker",
                documents=documents,
                marking_permanency_pass=False,
            )
        )
        self.assertEqual(result["disposition"], "quarantine")

    def test_a_clean_open_market_delivery_can_still_be_accepted(self):
        documents = list(BASE_ARRIVAL_DOCUMENTS) + list(UNFRANCHISED_ARRIVAL_DOCUMENTS)
        result = assess_incoming_inspection(
            _spec(
                source_tier="open-market-broker",
                documents=documents,
                marking_permanency_pass=True,
            )
        )
        self.assertEqual(result["disposition"], "accept-into-bonded-store")
        self.assertEqual(result["depth"]["depth"], "extended")

    def test_transit_damage_gives_a_conditional_release(self):
        result = assess_incoming_inspection(_spec(damaged=2))
        self.assertEqual(result["disposition"], "conditional-release")
        self.assertEqual(result["accepted_pieces"], 398)

    def test_minor_defects_over_the_allowance_give_a_conditional_release(self):
        defects = [_defect("minor") for _ in range(20)]
        result = assess_incoming_inspection(_spec(defects=defects))
        self.assertEqual(result["disposition"], "conditional-release")
        self.assertTrue(result["over_acceptance"]["minor"])

    def test_a_delivery_of_only_damaged_pieces_quarantines(self):
        result = assess_incoming_inspection(_spec(declared=4, counted=4, damaged=4))
        self.assertEqual(result["disposition"], "quarantine")
        self.assertEqual(result["draw"], 0)

    def test_the_draw_follows_the_escalated_depth_not_the_base_depth(self):
        clean = assess_incoming_inspection(_spec())
        breached = assess_incoming_inspection(
            _spec(packaging=_packaging(seal_intact=False), marking_permanency_pass=True)
        )
        self.assertEqual(breached["depth"]["depth"], "extended")
        self.assertGreater(breached["draw"], clean["draw"])

    def test_spec_missing_a_required_key_is_refused(self):
        spec = _spec()
        del spec["packaging"]
        with self.assertRaises(ValueError):
            assess_incoming_inspection(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_incoming_inspection(["source_tier"])

    def test_documentation_findings_names_each_missing_document(self):
        record = documentation_findings(["delivery-note"], "franchised-distributor")
        self.assertEqual(record["missing"], ["certificate-of-conformity"])
        self.assertEqual(len(record["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
