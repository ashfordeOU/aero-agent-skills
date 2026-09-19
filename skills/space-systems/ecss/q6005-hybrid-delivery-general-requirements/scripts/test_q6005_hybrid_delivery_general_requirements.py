#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hybrid-delivery-general-requirements.

Offline, stdlib unittest. Exercises the delivery validation, the conditional
assembly of the owed delivery documents, the unit-level serial coverage of
the data pack, the orphan-record finding, the packaging provisions and the
release/hold disposition of ECSS-Q-ST-60-05C clause 13.1 as paraphrased in
the logic module. Serial coverage is a quotient of integers that lands
exactly on one for a complete pack, so it is asserted with assertAlmostEqual
rather than a strict inequality that libm could round either way between
build host and CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_hybrid_delivery_general_requirements_logic import (  # noqa: E402
    BASE_DELIVERY_DOCUMENTS,
    ENHANCED_LEVEL_DOCUMENT,
    HERMETIC_PACKAGE_DOCUMENT,
    NONCONFORMANCE_DOCUMENT,
    missing_documents,
    normalise_name,
    orphan_records,
    packaging_gaps,
    required_documents,
    serial_coverage,
    uncovered_serials,
    validate_delivery,
    verify_delivery_package,
)

SERIALS = ["SN-001", "SN-002", "SN-003", "SN-004"]


def delivery(**overrides):
    """A complete four-unit non-hermetic delivery with a full data pack."""
    base = {
        "delivered_serials": list(SERIALS),
        "data_pack_serials": list(SERIALS),
        "documents": list(BASE_DELIVERY_DOCUMENTS),
        "reliability_level": "standard",
        "nonconformances_raised": 0,
        "hermetic": False,
        "packaging": {
            "esd_protective_packaging": True,
            "individual_unit_separation": True,
            "desiccant_and_humidity_indicator": True,
        },
    }
    base.update(overrides)
    return base


class DeliveryValidationTests(unittest.TestCase):
    def test_complete_delivery_normalises(self):
        normalised = validate_delivery(delivery())
        self.assertEqual(len(normalised["delivered_serials"]), 4)
        self.assertEqual(normalised["reliability_level"], "standard")

    def test_delivery_without_serials_is_refused(self):
        bad = delivery()
        del bad["delivered_serials"]
        with self.assertRaises(ValueError):
            validate_delivery(bad)

    def test_empty_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(delivered_serials=[]))

    def test_repeated_serial_number_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(delivered_serials=["SN-001", "SN-001"]))

    def test_string_of_serials_is_not_a_serial_list(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(delivered_serials="SN-001"))

    def test_blank_serial_number_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(delivered_serials=["SN-001", "  "]))

    def test_unknown_reliability_level_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(reliability_level="ultra"))

    def test_negative_nonconformance_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(nonconformances_raised=-1))

    def test_boolean_nonconformance_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(nonconformances_raised=True))

    def test_non_boolean_packaging_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_delivery(delivery(packaging={"esd_protective_packaging": "yes"}))

    def test_absent_documents_normalise_to_an_empty_pack(self):
        bare = delivery()
        del bare["documents"]
        self.assertEqual(validate_delivery(bare)["documents"], set())

    def test_names_are_normalised_for_case_and_separator(self):
        self.assertEqual(normalise_name("Certificate Of Conformity", "d"), "certificate-of-conformity")


class RequiredDocumentTests(unittest.TestCase):
    def test_clean_standard_batch_owes_the_base_set_only(self):
        self.assertEqual(required_documents(delivery()), list(BASE_DELIVERY_DOCUMENTS))

    def test_a_raised_nonconformance_adds_its_report(self):
        self.assertIn(
            NONCONFORMANCE_DOCUMENT, required_documents(delivery(nonconformances_raised=2))
        )

    def test_enhanced_level_adds_the_construction_analysis_report(self):
        self.assertIn(
            ENHANCED_LEVEL_DOCUMENT, required_documents(delivery(reliability_level="enhanced"))
        )

    def test_hermetic_package_adds_its_test_record(self):
        self.assertIn(HERMETIC_PACKAGE_DOCUMENT, required_documents(delivery(hermetic=True)))

    def test_every_condition_at_once_adds_every_document(self):
        owed = required_documents(
            delivery(nonconformances_raised=1, reliability_level="enhanced", hermetic=True)
        )
        self.assertEqual(len(owed), len(BASE_DELIVERY_DOCUMENTS) + 3)

    def test_complete_pack_leaves_nothing_missing(self):
        self.assertEqual(missing_documents(delivery()), [])

    def test_absent_document_is_reported(self):
        thin = [d for d in BASE_DELIVERY_DOCUMENTS if d != "marking-record"]
        self.assertEqual(missing_documents(delivery(documents=thin)), ["marking-record"])

    def test_document_names_are_matched_case_and_separator_insensitively(self):
        loud = [d.replace("-", " ").upper() for d in BASE_DELIVERY_DOCUMENTS]
        self.assertEqual(missing_documents(delivery(documents=loud)), [])

    def test_conditional_document_missing_from_the_pack_is_reported(self):
        self.assertEqual(
            missing_documents(delivery(hermetic=True)), [HERMETIC_PACKAGE_DOCUMENT]
        )


class SerialCoverageTests(unittest.TestCase):
    def test_full_data_pack_covers_every_shipped_unit(self):
        self.assertEqual(uncovered_serials(delivery()), [])
        self.assertAlmostEqual(serial_coverage(delivery()), 1.0, places=9)

    def test_unit_without_a_record_is_named(self):
        thin = delivery(data_pack_serials=SERIALS[:3])
        self.assertEqual(uncovered_serials(thin), ["sn-004"])
        self.assertAlmostEqual(serial_coverage(thin), 0.75, places=9)

    def test_empty_data_pack_covers_nothing(self):
        self.assertAlmostEqual(serial_coverage(delivery(data_pack_serials=[])), 0.0, places=9)

    def test_record_for_a_unit_that_did_not_ship_is_an_orphan(self):
        wide = delivery(data_pack_serials=SERIALS + ["SN-099"])
        self.assertEqual(orphan_records(wide), ["sn-099"])
        self.assertAlmostEqual(serial_coverage(wide), 1.0, places=9)

    def test_a_thick_pack_can_still_miss_a_shipped_unit(self):
        crossed = delivery(data_pack_serials=SERIALS[:3] + ["SN-097", "SN-098"])
        self.assertEqual(uncovered_serials(crossed), ["sn-004"])
        self.assertEqual(len(orphan_records(crossed)), 2)

    def test_serial_matching_ignores_case_and_separator(self):
        loud = delivery(data_pack_serials=[s.lower().replace("-", " ") for s in SERIALS])
        self.assertEqual(uncovered_serials(loud), [])


class PackagingTests(unittest.TestCase):
    def test_compliant_packaging_has_no_gaps(self):
        self.assertEqual(packaging_gaps(delivery()), [])

    def test_missing_electrostatic_protection_is_a_gap(self):
        bad = delivery(packaging={"esd_protective_packaging": False,
                                  "individual_unit_separation": True,
                                  "desiccant_and_humidity_indicator": True})
        self.assertTrue(any("electrostatic" in g for g in packaging_gaps(bad)))

    def test_multi_unit_shipment_without_separation_is_a_gap(self):
        bad = delivery(packaging={"esd_protective_packaging": True,
                                  "individual_unit_separation": False,
                                  "desiccant_and_humidity_indicator": True})
        self.assertTrue(any("separated" in g for g in packaging_gaps(bad)))

    def test_single_unit_shipment_needs_no_separation(self):
        single = delivery(
            delivered_serials=["SN-001"],
            data_pack_serials=["SN-001"],
            packaging={"esd_protective_packaging": True,
                       "individual_unit_separation": False,
                       "desiccant_and_humidity_indicator": True},
        )
        self.assertEqual(packaging_gaps(single), [])

    def test_non_hermetic_units_owe_a_moisture_provision(self):
        bad = delivery(packaging={"esd_protective_packaging": True,
                                  "individual_unit_separation": True,
                                  "desiccant_and_humidity_indicator": False})
        self.assertTrue(any("desiccant" in g for g in packaging_gaps(bad)))

    def test_hermetic_units_owe_no_moisture_provision(self):
        hermetic = delivery(
            hermetic=True,
            documents=list(BASE_DELIVERY_DOCUMENTS) + [HERMETIC_PACKAGE_DOCUMENT],
            packaging={"esd_protective_packaging": True,
                       "individual_unit_separation": True,
                       "desiccant_and_humidity_indicator": False},
        )
        self.assertEqual(packaging_gaps(hermetic), [])


class VerificationTests(unittest.TestCase):
    def test_complete_delivery_is_released(self):
        report = verify_delivery_package(delivery())
        self.assertEqual(report["disposition"], "release")
        self.assertTrue(report["releasable"])
        self.assertTrue(report["fully_covered"])
        self.assertEqual(report["holds"], [])

    def test_missing_document_holds_the_delivery(self):
        thin = [d for d in BASE_DELIVERY_DOCUMENTS if d != "certificate-of-conformity"]
        report = verify_delivery_package(delivery(documents=thin))
        self.assertEqual(report["disposition"], "hold")
        self.assertEqual(report["missing_documents"], ["certificate-of-conformity"])

    def test_uncovered_unit_holds_the_delivery(self):
        report = verify_delivery_package(delivery(data_pack_serials=SERIALS[:2]))
        self.assertEqual(report["disposition"], "hold")
        self.assertEqual(len(report["uncovered_serials"]), 2)

    def test_orphan_record_holds_the_delivery_even_at_full_coverage(self):
        report = verify_delivery_package(delivery(data_pack_serials=SERIALS + ["SN-099"]))
        self.assertTrue(report["fully_covered"])
        self.assertEqual(report["disposition"], "hold")
        self.assertEqual(report["orphan_records"], ["sn-099"])

    def test_packaging_gap_alone_holds_the_delivery(self):
        report = verify_delivery_package(
            delivery(packaging={"esd_protective_packaging": False,
                                "individual_unit_separation": True,
                                "desiccant_and_humidity_indicator": True})
        )
        self.assertEqual(report["disposition"], "hold")
        self.assertEqual(report["missing_documents"], [])

    def test_report_counts_units_and_records_separately(self):
        report = verify_delivery_package(delivery(data_pack_serials=SERIALS[:3]))
        self.assertEqual(report["units_delivered"], 4)
        self.assertEqual(report["records_supplied"], 3)

    def test_several_findings_are_all_reported(self):
        report = verify_delivery_package(
            delivery(
                documents=["certificate-of-conformity"],
                data_pack_serials=SERIALS[:1] + ["SN-099"],
                packaging={"esd_protective_packaging": False,
                           "individual_unit_separation": False,
                           "desiccant_and_humidity_indicator": False},
            )
        )
        self.assertGreaterEqual(len(report["holds"]), 6)

    def test_non_mapping_delivery_is_refused(self):
        with self.assertRaises(ValueError):
            verify_delivery_package([("delivered_serials", SERIALS)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
