"""Contract test for the fastener lot-identification leaf (stdlib unittest)."""

import unittest

from q7046_lot_identification_logic import (
    ACCEPTED,
    ACCEPTED_WITH_ACTIONS,
    IDENTIFIER_FIELDS,
    MARKING_DEPTH_FRACTION,
    MAX_FIELD_LENGTH,
    REJECTED,
    REQUIRED_LABEL_FIELDS,
    REQUIRED_TRACEABILITY_LINKS,
    assess_consignment,
    assess_delivery,
    character_cell_area_mm2,
    compose_lot_identifier,
    hex_head_markable_area_mm2,
    label_gaps,
    marking_character_capacity,
    marking_depth_limit_mm,
    marking_location_admissible,
    mixed_lot_codes,
    parse_lot_identifier,
    traceability_gaps,
    validate_consignment,
    validate_identifier_field,
)


def identifier_fields(**kw):
    fields = {
        "manufacturer_code": "ACME",
        "part_code": "M10X50",
        "heat_number": "H88421",
        "heat_treatment_charge": "HT5001",
        "date_code": "2609",
    }
    fields.update(kw)
    return fields


def chain(**kw):
    links = {link: "r-%s" % link for link in REQUIRED_TRACEABILITY_LINKS}
    links.update(kw)
    return links


def label(**kw):
    fields = {
        "lot_identifier": "ACME-M10X50-H88421-HT5001-2609",
        "part_code": "M10X50",
        "property_class": "10.9",
        "quantity": 200,
        "date_code": "2609",
    }
    fields.update(kw)
    return fields


def consignment(**kw):
    record = {
        "identifier_fields": identifier_fields(),
        "width_across_flats_mm": 16.0,
        "head_height_mm": 6.4,
        "character_height_mm": 1.6,
        "required_marking": "10.9 ACME",
        "marking_depth_mm": 0.10,
        "marking_location": "head-top",
        "fatigue_critical": False,
        "traceability_chain": chain(),
        "package_items": ["LOT-A", "LOT-A", "LOT-A"],
        "package_label": label(),
    }
    record.update(kw)
    return record


class TestIdentifierFields(unittest.TestCase):
    def test_a_field_normalizes_to_upper_case(self):
        self.assertEqual(validate_identifier_field("part_code", " m10x50 "), "M10X50")

    def test_an_empty_field_raises(self):
        with self.assertRaises(ValueError):
            validate_identifier_field("part_code", "   ")

    def test_a_field_with_a_separator_in_it_raises(self):
        with self.assertRaises(ValueError):
            validate_identifier_field("part_code", "M10-50")

    def test_an_over_long_field_raises(self):
        with self.assertRaises(ValueError):
            validate_identifier_field("part_code", "A" * (MAX_FIELD_LENGTH + 1))

    def test_a_field_exactly_at_the_length_limit_is_accepted(self):
        value = "A" * MAX_FIELD_LENGTH
        self.assertEqual(validate_identifier_field("part_code", value), value)

    def test_a_non_string_field_raises(self):
        with self.assertRaises(ValueError):
            validate_identifier_field("part_code", 1050)


class TestComposeAndParse(unittest.TestCase):
    def test_an_identifier_composes_in_field_order(self):
        self.assertEqual(
            compose_lot_identifier(identifier_fields()),
            "ACME-M10X50-H88421-HT5001-2609",
        )

    def test_a_missing_field_raises(self):
        fields = identifier_fields()
        del fields["heat_number"]
        with self.assertRaises(ValueError):
            compose_lot_identifier(fields)

    def test_an_identifier_round_trips(self):
        composed = compose_lot_identifier(identifier_fields())
        self.assertEqual(parse_lot_identifier(composed), identifier_fields())

    def test_every_declared_field_survives_the_round_trip(self):
        parsed = parse_lot_identifier(compose_lot_identifier(identifier_fields()))
        self.assertEqual(sorted(parsed), sorted(IDENTIFIER_FIELDS))

    def test_an_identifier_with_too_few_fields_raises(self):
        with self.assertRaises(ValueError):
            parse_lot_identifier("ACME-M10X50-H88421")

    def test_a_non_mapping_field_set_raises(self):
        with self.assertRaises(ValueError):
            compose_lot_identifier(["ACME"])


class TestMarkingCapacity(unittest.TestCase):
    def test_the_markable_area_grows_with_the_square_of_the_width(self):
        small = hex_head_markable_area_mm2(8.0)
        large = hex_head_markable_area_mm2(16.0)
        self.assertAlmostEqual(large / small, 4.0, places=9)

    def test_a_zero_width_raises(self):
        with self.assertRaises(ValueError):
            hex_head_markable_area_mm2(0.0)

    def test_a_usable_fraction_above_unity_raises(self):
        with self.assertRaises(ValueError):
            hex_head_markable_area_mm2(16.0, 1.5)

    def test_a_character_cell_includes_its_spacing(self):
        self.assertGreater(character_cell_area_mm2(1.6), 1.6 * 1.6 * 0.6)

    def test_an_area_of_exactly_three_cells_holds_three_characters(self):
        cell = character_cell_area_mm2(1.6)
        self.assertEqual(marking_character_capacity(3.0 * cell, 1.6), 3)

    def test_a_smaller_head_holds_fewer_characters(self):
        small = marking_character_capacity(hex_head_markable_area_mm2(7.0), 1.6)
        large = marking_character_capacity(hex_head_markable_area_mm2(16.0), 1.6)
        self.assertLess(small, large)

    def test_a_taller_character_costs_capacity(self):
        area = hex_head_markable_area_mm2(16.0)
        self.assertLess(
            marking_character_capacity(area, 3.2),
            marking_character_capacity(area, 1.6),
        )

    def test_a_zero_character_height_raises(self):
        with self.assertRaises(ValueError):
            marking_character_capacity(100.0, 0.0)


class TestMarkingDepthAndLocation(unittest.TestCase):
    def test_the_depth_limit_is_a_fraction_of_the_head_height(self):
        self.assertAlmostEqual(
            marking_depth_limit_mm(6.4), 6.4 * MARKING_DEPTH_FRACTION, places=9
        )

    def test_a_zero_head_height_raises(self):
        with self.assertRaises(ValueError):
            marking_depth_limit_mm(0.0)

    def test_the_head_top_is_always_admissible(self):
        self.assertTrue(marking_location_admissible("head-top", True))

    def test_the_shank_is_admissible_only_off_a_fatigue_duty(self):
        self.assertTrue(marking_location_admissible("shank", False))
        self.assertFalse(marking_location_admissible("shank", True))

    def test_the_thread_run_out_is_barred_on_a_fatigue_duty(self):
        self.assertFalse(marking_location_admissible("thread-run-out", True))

    def test_an_unknown_location_raises(self):
        with self.assertRaises(ValueError):
            marking_location_admissible("somewhere-on-it")


class TestTraceabilityAndPackaging(unittest.TestCase):
    def test_a_complete_chain_has_no_gaps(self):
        self.assertEqual(traceability_gaps(chain()), [])

    def test_a_blank_link_is_a_gap(self):
        self.assertEqual(traceability_gaps(chain(**{"bar-lot": "  "})), ["bar-lot"])

    def test_an_absent_link_is_a_gap(self):
        links = chain()
        del links["melt-certificate"]
        self.assertIn("melt-certificate", traceability_gaps(links))

    def test_a_non_mapping_chain_raises(self):
        with self.assertRaises(ValueError):
            traceability_gaps(["melt-certificate"])

    def test_one_lot_in_a_package_reports_one_code(self):
        self.assertEqual(mixed_lot_codes(["LOT-A", "lot-a"]), ["LOT-A"])

    def test_two_lots_in_a_package_report_both(self):
        self.assertEqual(mixed_lot_codes(["LOT-A", "LOT-B"]), ["LOT-A", "LOT-B"])

    def test_an_empty_package_raises(self):
        with self.assertRaises(ValueError):
            mixed_lot_codes([])

    def test_a_complete_label_has_no_gaps(self):
        self.assertEqual(label_gaps(label()), [])

    def test_a_missing_label_field_is_a_gap(self):
        fields = label()
        del fields["quantity"]
        self.assertIn("quantity", label_gaps(fields))

    def test_a_blank_label_field_is_a_gap(self):
        self.assertIn("date_code", label_gaps(label(date_code="   ")))

    def test_every_required_label_field_is_checked(self):
        self.assertEqual(sorted(label_gaps({})), sorted(REQUIRED_LABEL_FIELDS))


class TestAssessConsignment(unittest.TestCase):
    def test_a_clean_consignment_is_accepted(self):
        result = assess_consignment(consignment())
        self.assertEqual(result["disposition"], ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_marking_too_long_for_the_head_moves_to_the_package(self):
        result = assess_consignment(
            consignment(width_across_flats_mm=7.0,
                        required_marking="10.9 ACME H88421 HT5001")
        )
        self.assertEqual(result["disposition"], ACCEPTED_WITH_ACTIONS)
        self.assertFalse(result["marking_fits_on_the_head"])
        self.assertIn("move-the-surplus-marking-to-the-package", result["actions"])

    def test_a_stamp_exactly_on_the_depth_limit_is_admissible(self):
        limit = marking_depth_limit_mm(6.4)
        result = assess_consignment(consignment(marking_depth_mm=limit))
        self.assertTrue(result["marking_depth_admissible"])

    def test_a_deeper_stamp_is_rejected(self):
        result = assess_consignment(consignment(marking_depth_mm=0.8))
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "marking-stamped-deeper-than-the-head-admits", result["findings"]
        )

    def test_marking_the_run_out_of_a_fatigue_part_is_rejected(self):
        result = assess_consignment(
            consignment(marking_location="thread-run-out", fatigue_critical=True)
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "marking-placed-where-the-part-is-worked-hardest", result["findings"]
        )

    def test_the_same_location_passes_off_a_fatigue_duty(self):
        result = assess_consignment(
            consignment(marking_location="thread-run-out", fatigue_critical=False)
        )
        self.assertTrue(result["marking_location_admissible"])

    def test_a_broken_traceability_chain_is_rejected(self):
        result = assess_consignment(
            consignment(traceability_chain=chain(**{"bar-lot": ""}))
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn("traceability-chain-broken-at-bar-lot", result["findings"])

    def test_a_mixed_package_is_rejected(self):
        result = assess_consignment(
            consignment(package_items=["LOT-A", "LOT-B"])
        )
        self.assertEqual(result["disposition"], REJECTED)
        self.assertIn(
            "package-holds-more-than-one-production-lot", result["findings"]
        )

    def test_an_incomplete_label_asks_for_an_action(self):
        fields = label()
        del fields["quantity"]
        result = assess_consignment(consignment(package_label=fields))
        self.assertEqual(result["disposition"], ACCEPTED_WITH_ACTIONS)
        self.assertIn("complete-the-package-label-before-issue", result["actions"])

    def test_a_consignment_with_a_bad_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_consignment(
                consignment(identifier_fields=identifier_fields(date_code=""))
            )


class TestAssessDelivery(unittest.TestCase):
    def test_a_clean_delivery_is_accepted(self):
        report = assess_delivery(
            [
                consignment(),
                consignment(
                    identifier_fields=identifier_fields(heat_number="H99000")
                ),
            ]
        )
        self.assertEqual(report["delivery_disposition"], ACCEPTED)
        self.assertEqual(report["rejected_lots"], [])

    def test_the_worst_consignment_sets_the_delivery_disposition(self):
        report = assess_delivery(
            [
                consignment(),
                consignment(
                    identifier_fields=identifier_fields(heat_number="H99001"),
                    package_items=["LOT-A", "LOT-B"],
                ),
            ]
        )
        self.assertEqual(report["delivery_disposition"], REJECTED)
        self.assertEqual(len(report["rejected_lots"]), 1)

    def test_untraceable_lots_are_listed(self):
        report = assess_delivery(
            [
                consignment(
                    identifier_fields=identifier_fields(heat_number="H99002"),
                    traceability_chain=chain(**{"package-record": ""}),
                )
            ]
        )
        self.assertEqual(len(report["untraceable_lots"]), 1)

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_delivery([consignment(), consignment()])

    def test_an_empty_delivery_raises(self):
        with self.assertRaises(ValueError):
            assess_delivery([])


if __name__ == "__main__":
    unittest.main()
