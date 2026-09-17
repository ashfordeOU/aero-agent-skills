"""Contract tests for the clause 5.3.4 Class 2 pre-cap source inspection logic.

The cases walk the coverage question one step at a time: whether the package
presents a witness point at all, where that point sits relative to the seal,
what may run between the two, who is allowed to hold the witness and on whose
delegation, the in-line route offered in place of a witness, and the
witnessed coverage each part type achieved. Every limit is exercised on both
sides, and a coverage landing on its minimum is compared with a
representation-sized tolerance.
"""

import datetime
import unittest

from q60_class_2_precap_source_inspection_logic import (
    AGENCY_ROLE,
    CAVITY_AFFECTING_OPERATIONS,
    CAVITY_PACKAGE_FAMILIES,
    COVERAGE_TOLERANCE,
    DELEGATED_WITNESS_ROLES,
    MANUFACTURER_ROLES,
    SEALLESS_PACKAGE_FAMILIES,
    assess_precap_inspection,
    assess_precap_lot,
    coverage_findings,
    inline_programme_findings,
    normalize_token,
    parse_iso_date,
    precap_applies_to,
    seal_placement_findings,
    witness_authority_findings,
)

FLOW = [
    "die-attach",
    "wire-bond",
    "internal-clean",
    "pre-cap-visual",
    "lid-place",
    "seal",
    "fine-leak",
    "external-visual",
]

LOT_DATE = "2026-06-09"


def _witness(**overrides):
    witness = {
        "name": "j-source-inspector",
        "role": "customer-product-assurance",
    }
    witness.update(overrides)
    return witness


def _lot(**overrides):
    lot = {
        "lot_id": "LOT-2C-51",
        "part_type": "hermetic-ceramic-hybrid-hb-series",
        "package_family": "hermetic-cavity",
        "lot_date": LOT_DATE,
        "witnessed": True,
        "flow": list(FLOW),
        "witness_step": "pre-cap-visual",
        "seal_step": "seal",
        "witness": _witness(),
    }
    lot.update(overrides)
    return lot


def _programme(**overrides):
    programme = {
        "approval_reference": "ILM-2025-004",
        "customer_accepted": True,
        "valid_until": "2026-12-31",
    }
    programme.update(overrides)
    return programme


def _order(**overrides):
    order = {
        "order_reference": "PO-2026-661",
        "minimum_coverage": 1.0,
        "lots": [_lot()],
    }
    order.update(overrides)
    return order


class TokenAndDateTests(unittest.TestCase):
    def test_token_normalised(self):
        self.assertEqual(normalize_token("Pre_Cap Visual", "step"), "pre-cap-visual")

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "step")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date(LOT_DATE, "date"), datetime.date(2026, 6, 9))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 6, 9)
        self.assertEqual(parse_iso_date(day, "date"), day)

    def test_non_calendar_date_refused(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-06-31", "date")


class ApplicabilityTests(unittest.TestCase):
    def test_cavity_family_carries_a_witness_point(self):
        for family in CAVITY_PACKAGE_FAMILIES:
            self.assertTrue(precap_applies_to(family))

    def test_sealless_family_carries_none(self):
        for family in SEALLESS_PACKAGE_FAMILIES:
            self.assertFalse(precap_applies_to(family))

    def test_the_two_families_do_not_overlap(self):
        self.assertEqual(
            set(CAVITY_PACKAGE_FAMILIES) & set(SEALLESS_PACKAGE_FAMILIES), set()
        )

    def test_unknown_family_refused(self):
        with self.assertRaises(ValueError):
            precap_applies_to("something-in-a-bag")


class SealPlacementTests(unittest.TestCase):
    def test_witness_before_the_seal_raises_nothing(self):
        self.assertEqual(seal_placement_findings(FLOW, "pre-cap-visual", "seal"), [])

    def test_witness_after_the_seal_reported(self):
        findings = seal_placement_findings(FLOW, "fine-leak", "seal")
        self.assertTrue(any("after the seal" in f for f in findings))

    def test_witness_on_the_seal_step_reported(self):
        findings = seal_placement_findings(FLOW, "seal", "seal")
        self.assertTrue(any("one step" in f for f in findings))

    def test_cavity_affecting_step_between_witness_and_seal_reported(self):
        flow = list(FLOW)
        flow.insert(flow.index("seal"), "lid-rework")
        findings = seal_placement_findings(flow, "pre-cap-visual", "seal")
        self.assertTrue(any("never witnessed" in f for f in findings))

    def test_benign_step_between_witness_and_seal_accepted(self):
        self.assertEqual(seal_placement_findings(FLOW, "pre-cap-visual", "seal"), [])

    def test_cavity_operations_before_the_witness_are_fine(self):
        for token in CAVITY_AFFECTING_OPERATIONS:
            if token in FLOW:
                self.assertLess(FLOW.index(token), FLOW.index("pre-cap-visual"))

    def test_step_absent_from_the_flow_refused(self):
        with self.assertRaises(ValueError):
            seal_placement_findings(FLOW, "x-ray", "seal")

    def test_repeated_step_in_the_flow_refused(self):
        with self.assertRaises(ValueError):
            seal_placement_findings(FLOW + ["seal"], "pre-cap-visual", "seal")

    def test_empty_flow_refused(self):
        with self.assertRaises(ValueError):
            seal_placement_findings([], "pre-cap-visual", "seal")


class WitnessAuthorityTests(unittest.TestCase):
    def test_customer_assurance_witness_raises_nothing(self):
        self.assertEqual(witness_authority_findings(_witness()), [])

    def test_agency_with_a_delegation_raises_nothing(self):
        witness = _witness(role=AGENCY_ROLE, delegation_reference="DEL-2026-07")
        self.assertEqual(witness_authority_findings(witness), [])

    def test_agency_without_a_delegation_reported(self):
        findings = witness_authority_findings(_witness(role=AGENCY_ROLE))
        self.assertTrue(any("no delegation" in f for f in findings))

    def test_manufacturer_role_reported(self):
        for role in MANUFACTURER_ROLES:
            findings = witness_authority_findings(_witness(role=role))
            self.assertTrue(any("manufacturer's own check" in f for f in findings))

    def test_manufacturer_delegation_reference_does_not_rescue_the_role(self):
        witness = _witness(role="manufacturer-quality", delegation_reference="DEL-2026-07")
        self.assertTrue(witness_authority_findings(witness))

    def test_delegated_roles_exclude_the_manufacturer_roles(self):
        self.assertEqual(set(DELEGATED_WITNESS_ROLES) & set(MANUFACTURER_ROLES), set())

    def test_unknown_role_refused(self):
        with self.assertRaises(ValueError):
            witness_authority_findings(_witness(role="a-visiting-engineer"))

    def test_missing_witness_key_refused(self):
        with self.assertRaises(ValueError):
            witness_authority_findings({"name": "j-source-inspector"})


class InlineProgrammeTests(unittest.TestCase):
    def test_complete_programme_raises_nothing(self):
        self.assertEqual(inline_programme_findings(_programme(), LOT_DATE), [])

    def test_programme_expiring_on_the_lot_date_is_still_valid(self):
        self.assertEqual(inline_programme_findings(_programme(valid_until=LOT_DATE), LOT_DATE), [])

    def test_lapsed_programme_reported(self):
        findings = inline_programme_findings(_programme(valid_until="2026-01-31"), LOT_DATE)
        self.assertTrue(any("lapsed" in f for f in findings))

    def test_programme_without_an_approval_reference_reported(self):
        programme = _programme()
        del programme["approval_reference"]
        findings = inline_programme_findings(programme, LOT_DATE)
        self.assertTrue(any("no approval reference" in f for f in findings))

    def test_programme_the_customer_never_accepted_reported(self):
        findings = inline_programme_findings(_programme(customer_accepted=False), LOT_DATE)
        self.assertTrue(any("never accepted" in f for f in findings))

    def test_programme_without_a_validity_reported(self):
        programme = _programme()
        del programme["valid_until"]
        findings = inline_programme_findings(programme, LOT_DATE)
        self.assertTrue(any("no validity date" in f for f in findings))

    def test_absent_programme_reported(self):
        findings = inline_programme_findings(None, LOT_DATE)
        self.assertTrue(any("no in-line monitoring programme" in f for f in findings))


class CoverageTests(unittest.TestCase):
    def test_full_coverage_raises_nothing(self):
        entry = coverage_findings(4, 4, 1.0, "hb-series")
        self.assertEqual(entry["findings"], [])
        self.assertAlmostEqual(entry["coverage"], 1.0, places=9)

    def test_partial_coverage_below_the_minimum_reported(self):
        entry = coverage_findings(1, 4, 0.5, "hb-series")
        self.assertTrue(any("against the" in f for f in entry["findings"]))

    def test_coverage_landing_on_the_minimum_is_accepted(self):
        entry = coverage_findings(1, 2, 0.5, "hb-series")
        self.assertEqual(entry["findings"], [])
        self.assertAlmostEqual(entry["coverage"], 0.5, places=9)

    def test_representation_sized_shortfall_is_not_a_finding(self):
        # 1/3 and 1 - 2/3 differ in the last bit; the tolerance keeps the
        # verdict the same on every machine.
        entry = coverage_findings(1, 3, 1.0 - 2.0 / 3.0, "hb-series")
        self.assertEqual(entry["findings"], [])

    def test_zero_coverage_against_a_zero_minimum_is_accepted(self):
        entry = coverage_findings(0, 5, 0.0, "hb-series")
        self.assertEqual(entry["findings"], [])

    def test_witnessed_above_the_lot_count_refused(self):
        with self.assertRaises(ValueError):
            coverage_findings(6, 4, 1.0, "hb-series")

    def test_no_cavity_lot_refused(self):
        with self.assertRaises(ValueError):
            coverage_findings(0, 0, 1.0, "hb-series")

    def test_minimum_outside_the_unit_range_refused(self):
        with self.assertRaises(ValueError):
            coverage_findings(1, 2, 1.4, "hb-series")

    def test_non_integer_lot_count_refused(self):
        with self.assertRaises(ValueError):
            coverage_findings(1, 2.5, 0.5, "hb-series")

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class LotRecordTests(unittest.TestCase):
    def test_clean_cavity_lot_is_acceptable(self):
        record = assess_precap_lot(_lot())
        self.assertTrue(record["acceptable"])
        self.assertTrue(record["applicable"])

    def test_sealless_lot_is_not_applicable_and_not_a_finding(self):
        record = assess_precap_lot(_lot(package_family="moulded-plastic"))
        self.assertFalse(record["applicable"])
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["findings"], [])

    def test_unwitnessed_lot_on_a_live_programme_is_acceptable(self):
        lot = {
            "lot_id": "LOT-2C-52",
            "part_type": "hermetic-ceramic-hybrid-hb-series",
            "package_family": "hermetic-cavity",
            "lot_date": LOT_DATE,
            "witnessed": False,
            "inline_programme": _programme(),
        }
        record = assess_precap_lot(lot)
        self.assertTrue(record["acceptable"])
        self.assertFalse(record["witnessed"])

    def test_unwitnessed_lot_with_no_programme_reported(self):
        lot = {
            "lot_id": "LOT-2C-52",
            "part_type": "hermetic-ceramic-hybrid-hb-series",
            "package_family": "hermetic-cavity",
            "lot_date": LOT_DATE,
            "witnessed": False,
        }
        record = assess_precap_lot(lot)
        self.assertFalse(record["acceptable"])

    def test_missing_lot_key_refused(self):
        lot = _lot()
        del lot["lot_date"]
        with self.assertRaises(ValueError):
            assess_precap_lot(lot)

    def test_witnessed_lot_without_a_flow_refused(self):
        lot = _lot()
        del lot["flow"]
        with self.assertRaises(ValueError):
            assess_precap_lot(lot)

    def test_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_lot(["LOT-2C-51"])


class OrderTests(unittest.TestCase):
    def test_clean_order_is_complete(self):
        verdict = assess_precap_inspection(_order())
        self.assertTrue(verdict["inspection_complete"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["witnessed_fraction"], 1.0, places=9)

    def test_sealless_lots_stay_out_of_the_coverage_arithmetic(self):
        order = _order(
            lots=[_lot(), _lot(lot_id="LOT-2C-99", package_family="passive-chip")]
        )
        verdict = assess_precap_inspection(order)
        self.assertEqual(verdict["cavity_lot_count"], 1)
        self.assertTrue(verdict["inspection_complete"])

    def test_coverage_is_reported_per_part_type(self):
        order = _order(
            minimum_coverage=0.5,
            lots=[
                _lot(),
                _lot(lot_id="LOT-2C-52", witnessed=False, inline_programme=_programme()),
                _lot(lot_id="LOT-2C-53", part_type="metal-can-oscillator-os-series"),
            ],
        )
        verdict = assess_precap_inspection(order)
        types = [entry["part_type"] for entry in verdict["coverage_by_part_type"]]
        self.assertEqual(types, ["hermetic-ceramic-hybrid-hb-series", "metal-can-oscillator-os-series"])

    def test_coverage_shortfall_reported(self):
        order = _order(
            minimum_coverage=1.0,
            lots=[
                _lot(),
                _lot(lot_id="LOT-2C-52", witnessed=False, inline_programme=_programme()),
            ],
        )
        verdict = assess_precap_inspection(order)
        self.assertTrue(any("cavity lots" in f for f in verdict["findings"]))
        self.assertAlmostEqual(verdict["witnessed_fraction"], 0.5, places=9)

    def test_order_with_no_cavity_lot_reports_a_zero_fraction(self):
        verdict = assess_precap_inspection(
            _order(lots=[_lot(package_family="encapsulated-nonhermetic")])
        )
        self.assertEqual(verdict["cavity_lot_count"], 0)
        self.assertAlmostEqual(verdict["witnessed_fraction"], 0.0, places=9)

    def test_every_finding_is_carried_not_only_the_first(self):
        flow = list(FLOW)
        flow.insert(flow.index("seal"), "lid-rework")
        order = _order(
            lots=[_lot(flow=flow, witness=_witness(role="manufacturer-quality"))]
        )
        verdict = assess_precap_inspection(order)
        self.assertGreaterEqual(len(verdict["findings"]), 3)

    def test_lot_reported_twice_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_inspection(_order(lots=[_lot(), _lot()]))

    def test_empty_lot_list_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_inspection(_order(lots=[]))

    def test_missing_order_key_refused(self):
        order = _order()
        del order["minimum_coverage"]
        with self.assertRaises(ValueError):
            assess_precap_inspection(order)

    def test_non_mapping_order_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_inspection("PO-2026-661")

    def test_order_reference_echoed(self):
        verdict = assess_precap_inspection(_order())
        self.assertEqual(verdict["order_reference"], "PO-2026-661")


if __name__ == "__main__":
    unittest.main()
