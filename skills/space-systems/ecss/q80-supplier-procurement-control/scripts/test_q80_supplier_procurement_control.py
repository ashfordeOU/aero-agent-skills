"""Contract tests for the supplier and procurement control logic."""

import hashlib
import unittest

from q80_supplier_procurement_control_logic import (
    GROUND_SELECTION_CRITERIA,
    build_flowdown,
    check_flowdown_package,
    check_ground_selection,
    check_procured_item,
    check_supplier_monitoring,
    grade_supplier_selection,
    receiving_inspection,
)

GOOD_ITEM = {
    "name": "rtos", "origin": "procured",
    "ordering_criteria": "v5.2, SMP option", "receiving_inspection_criteria": "digest + docs",
    "backup_solution": "escrow", "contract_for_development_maintenance_upgrades": "MA-17",
    "cm_id": "SCI-042", "export_constraints_identified": True, "inspection_report": "RIR-3",
}


class SelectionTests(unittest.TestCase):
    def test_existing_software_needs_reuse_file(self):
        found = grade_supplier_selection({"pre_award_assessment": True, "source_recorded": True,
                                          "supplies_existing_software": True})
        self.assertEqual(found, ["existing software offered without its reuse file"])

    def test_clean(self):
        self.assertEqual(grade_supplier_selection({"pre_award_assessment": True,
                                                   "source_recorded": True}), [])


class FlowdownTests(unittest.TestCase):
    def test_development_sensitive_b(self):
        keys = [k for k, _ in build_flowdown("B", True)]
        for k in ("spap-required", "customer-acceptance", "higher-level-failures", "attack-scenarios"):
            self.assertIn(k, keys)

    def test_cots_provider_no_spap(self):
        keys = [k for k, _ in build_flowdown("C", False, "cots-provider")]
        self.assertNotIn("spap-required", keys)
        self.assertNotIn("attack-scenarios", keys)

    def test_category_d_no_failure_info(self):
        keys = [k for k, _ in build_flowdown("d", False)]
        self.assertNotIn("higher-level-failures", keys)
        with self.assertRaises(ValueError):
            build_flowdown("E", False)

    def test_package_gaps(self):
        pkg = {"spa-requirements": True, "spap-required": True, "criticality": True}
        missing = check_flowdown_package(pkg, "A", True)
        self.assertEqual(missing, ["customer-acceptance", "higher-level-failures",
                                   "sensitivity", "attack-scenarios"])


class MonitoringTests(unittest.TestCase):
    def test_nothing_owed_at_srr(self):
        self.assertEqual(check_supplier_monitoring({}, "srr"), [])

    def test_qr_gaps(self):
        found = check_supplier_monitoring({"spap_reviewed": True, "spap_sent_to_customer": True}, "qr")
        self.assertIn("supplier assurance plan not approved", found)
        self.assertIn("no process or product verification of the supplier on record", found)
        self.assertIn("final validation of the supplier product not monitored", found)


class ProcuredItemTests(unittest.TestCase):
    def test_complete_item(self):
        self.assertEqual(check_procured_item(GOOD_ITEM), [])

    def test_origin_and_gaps(self):
        item = dict(GOOD_ITEM, backup_solution="", cm_id="")
        found = check_procured_item(item, customer_requires_origin=True)
        self.assertIn("missing procurement data: backup solution", found)
        self.assertIn("not registered under configuration management", found)
        self.assertIn("country of origin required by the customer and not given", found)

    def test_customer_furnished(self):
        found = check_procured_item({"origin": "customer-furnished", "cm_id": "X",
                                     "export_constraints_identified": True,
                                     "inspection_report": "R"})
        self.assertEqual(found, ["customer-furnished software without a reuse assessment"])


class InspectionTests(unittest.TestCase):
    def test_accept_with_digest(self):
        image = b"\x7fELF flight image"
        res = receiving_inspection(
            {"version": "5.2", "options": ["smp"], "sha256": hashlib.sha256(image).hexdigest()},
            {"version": "5.2", "options": ["smp", "trace"], "documentation": True}, image)
        self.assertEqual(res["verdict"], "accept")

    def test_wrong_digest_rejects(self):
        res = receiving_inspection({"version": "1", "sha256": "00" * 32},
                                   {"version": "1", "documentation": True}, b"x")
        self.assertEqual(res["verdict"], "reject-return-to-supplier")

    def test_missing_docs_reservation(self):
        res = receiving_inspection({"version": "1"}, {"version": "1"})
        self.assertEqual(res["verdict"], "accept-with-reservation")

    def test_version_and_options(self):
        res = receiving_inspection({"version": "2", "options": ["a", "b"], "licences": 3},
                                   {"version": "1", "options": ["a"], "licences": 1,
                                    "documentation": True})
        self.assertEqual(len(res["findings"]), 3)


class GroundTests(unittest.TestCase):
    def test_partial(self):
        just = {c: "argued" for c in GROUND_SELECTION_CRITERIA[:10]}
        res = check_ground_selection(just, {"sla": True, "quality_of_service": True})
        self.assertEqual(res["covered"], "10/14")
        self.assertEqual(res["service_gaps"], ["escalation procedure",
                                               "maintenance over the specified life"])


if __name__ == "__main__":
    unittest.main()
