"""
Gate 3 contract tests for e1024-tmtc-icd logic.
stdlib unittest only; deterministic, offline, no network.
Run: python3 test_e1024_tmtc_icd.py
"""
import sys
import os
import unittest

# Allow running from the scripts/ directory directly
sys.path.insert(0, os.path.dirname(__file__))

from e1024_tmtc_icd_logic import (
    APID_IDLE,
    APID_MAX,
    APID_MIN,
    CCSDS_MAX_DATA_LENGTH_FIELD,
    PUS_C_TC_SEC_HEADER_MIN,
    PUS_C_TM_SEC_HEADER_MIN,
    PUS_VERSION_C,
    ACK_ACCEPTANCE,
    ACK_COMPLETION,
    APIDError,
    ICDCompletenessError,
    ICDValidationError,
    PacketStructureError,
    TMTCIcd,
    build_tc_packet_def,
    build_tm_packet_def,
    validate_apid,
    validate_pus_service,
)


class TestValidateAPID(unittest.TestCase):

    def test_valid_apid_min(self):
        result = validate_apid(APID_MIN)
        self.assertEqual(result["apid"], 0x000)
        self.assertEqual(result["status"], "operational")
        self.assertTrue(result["valid"])

    def test_valid_apid_max(self):
        result = validate_apid(APID_MAX)
        self.assertEqual(result["apid"], APID_MAX)
        self.assertEqual(result["status"], "operational")

    def test_idle_apid(self):
        result = validate_apid(APID_IDLE)
        self.assertEqual(result["status"], "idle")
        self.assertTrue(result["valid"])

    def test_apid_too_high_raises(self):
        with self.assertRaises(APIDError):
            validate_apid(0x800)

    def test_apid_negative_raises(self):
        with self.assertRaises(APIDError):
            validate_apid(-1)

    def test_apid_non_integer_raises(self):
        with self.assertRaises(APIDError):
            validate_apid("0x100")


class TestValidatePUSService(unittest.TestCase):

    def test_valid_service_and_subservice(self):
        result = validate_pus_service(3, 25)
        self.assertEqual(result["service"], 3)
        self.assertEqual(result["subservice"], 25)
        self.assertEqual(result["service_name"], "Housekeeping")
        self.assertTrue(result["valid"])

    def test_project_specific_service(self):
        result = validate_pus_service(128, 1)
        self.assertEqual(result["service_name"], "Project-specific")

    def test_service_zero_raises(self):
        with self.assertRaises(PacketStructureError):
            validate_pus_service(0, 1)

    def test_subservice_zero_raises(self):
        with self.assertRaises(PacketStructureError):
            validate_pus_service(1, 0)

    def test_service_256_raises(self):
        with self.assertRaises(PacketStructureError):
            validate_pus_service(256, 1)

    def test_subservice_256_raises(self):
        with self.assertRaises(PacketStructureError):
            validate_pus_service(3, 256)


class TestBuildTMPacketDef(unittest.TestCase):

    def test_valid_tm_packet(self):
        pkt = build_tm_packet_def(
            apid=0x10,
            service=3,
            subservice=25,
            description="Housekeeping report A",
            data_field_bytes=20,
        )
        self.assertEqual(pkt["type"], "TM")
        self.assertEqual(pkt["apid"], 0x10)
        self.assertEqual(pkt["service"], 3)
        self.assertEqual(pkt["pus_version"], PUS_VERSION_C)
        self.assertTrue(pkt["valid"])

    def test_tm_packet_data_length_field(self):
        pkt = build_tm_packet_def(
            apid=0x20,
            service=5,
            subservice=1,
            description="Event report",
            data_field_bytes=10,
        )
        expected = PUS_C_TM_SEC_HEADER_MIN + 10 - 1
        self.assertEqual(pkt["packet_data_length_field"], expected)

    def test_tm_idle_apid_raises(self):
        with self.assertRaises(APIDError):
            build_tm_packet_def(APID_IDLE, 3, 25, "idle packet", 0)

    def test_tm_empty_description_raises(self):
        with self.assertRaises(PacketStructureError):
            build_tm_packet_def(0x10, 3, 25, "   ", 10)

    def test_tm_negative_data_field_raises(self):
        with self.assertRaises(PacketStructureError):
            build_tm_packet_def(0x10, 3, 25, "desc", -1)

    def test_tm_data_field_overflow_raises(self):
        too_large = CCSDS_MAX_DATA_LENGTH_FIELD + 2 - PUS_C_TM_SEC_HEADER_MIN
        with self.assertRaises(PacketStructureError):
            build_tm_packet_def(0x10, 3, 25, "overflow", too_large)

    def test_tm_zero_data_field_bytes_valid(self):
        pkt = build_tm_packet_def(0x30, 17, 2, "Test response", 0)
        self.assertEqual(pkt["data_field_bytes"], 0)
        self.assertEqual(pkt["packet_data_length_field"], PUS_C_TM_SEC_HEADER_MIN - 1)


class TestBuildTCPacketDef(unittest.TestCase):

    def test_valid_tc_packet(self):
        pkt = build_tc_packet_def(
            apid=0x11,
            service=8,
            subservice=1,
            description="Enable function",
            ack_flags=ACK_ACCEPTANCE | ACK_COMPLETION,
            param_bytes=4,
        )
        self.assertEqual(pkt["type"], "TC")
        self.assertEqual(pkt["apid"], 0x11)
        self.assertEqual(pkt["pus_version"], PUS_VERSION_C)
        self.assertEqual(pkt["ack_flags"], ACK_ACCEPTANCE | ACK_COMPLETION)
        self.assertTrue(pkt["valid"])

    def test_tc_packet_data_length_field(self):
        pkt = build_tc_packet_def(0x12, 8, 2, "Disable function", 0xF, 8)
        expected = PUS_C_TC_SEC_HEADER_MIN + 8 - 1
        self.assertEqual(pkt["packet_data_length_field"], expected)

    def test_tc_idle_apid_raises(self):
        with self.assertRaises(APIDError):
            build_tc_packet_def(APID_IDLE, 8, 1, "idle tc", 0, 0)

    def test_tc_empty_description_raises(self):
        with self.assertRaises(PacketStructureError):
            build_tc_packet_def(0x11, 8, 1, "", 0, 0)

    def test_tc_ack_flags_out_of_range_raises(self):
        with self.assertRaises(PacketStructureError):
            build_tc_packet_def(0x11, 8, 1, "test", 0x10, 0)

    def test_tc_negative_param_bytes_raises(self):
        with self.assertRaises(PacketStructureError):
            build_tc_packet_def(0x11, 8, 1, "test", 0, -1)

    def test_tc_param_overflow_raises(self):
        too_large = CCSDS_MAX_DATA_LENGTH_FIELD + 2 - PUS_C_TC_SEC_HEADER_MIN
        with self.assertRaises(PacketStructureError):
            build_tc_packet_def(0x11, 8, 1, "overflow", 0, too_large)

    def test_tc_zero_params_valid(self):
        pkt = build_tc_packet_def(0x13, 17, 1, "Test request", 0, 0)
        self.assertEqual(pkt["param_bytes"], 0)


class TestTMTCIcd(unittest.TestCase):

    def _make_icd(self):
        icd = TMTCIcd("OBC-ICD-001")
        icd.register_apid(0x10, "OBC Housekeeping")
        icd.register_apid(0x11, "OBC Commands")
        tm = build_tm_packet_def(0x10, 3, 25, "HK report", 20)
        tc = build_tc_packet_def(0x11, 8, 1, "Enable OBC function", 0xF, 4)
        icd.add_tm(tm)
        icd.add_tc(tc)
        return icd

    def test_icd_empty_name_raises(self):
        with self.assertRaises(ICDValidationError):
            TMTCIcd("  ")

    def test_register_idle_apid_raises(self):
        icd = TMTCIcd("test-icd")
        with self.assertRaises(APIDError):
            icd.register_apid(APID_IDLE, "Idle Process")

    def test_register_apid_empty_name_raises(self):
        icd = TMTCIcd("test-icd")
        with self.assertRaises(ICDValidationError):
            icd.register_apid(0x10, "")

    def test_add_wrong_type_tm_raises(self):
        icd = TMTCIcd("test-icd")
        with self.assertRaises(ICDValidationError):
            icd.add_tm({"type": "TC", "apid": 0x10})

    def test_add_wrong_type_tc_raises(self):
        icd = TMTCIcd("test-icd")
        with self.assertRaises(ICDValidationError):
            icd.add_tc({"type": "TM", "apid": 0x10})

    def test_compliant_icd(self):
        icd = self._make_icd()
        result = icd.check_completeness()
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["tm_count"], 1)
        self.assertEqual(result["tc_count"], 1)

    def test_missing_apid_registration_finding(self):
        icd = TMTCIcd("test-icd")
        icd.register_apid(0x10, "OBC HK")
        tm = build_tm_packet_def(0x10, 3, 25, "HK report", 20)
        tc = build_tc_packet_def(0x20, 8, 1, "Enable", 0xF, 0)
        icd.add_tm(tm)
        icd.add_tc(tc)
        result = icd.check_completeness()
        self.assertFalse(result["compliant"])
        self.assertTrue(
            any("0x020" in f or "0x0020" in f or "0x20" in f for f in result["findings"])
        )

    def test_registered_apid_without_packets_finding(self):
        icd = TMTCIcd("test-icd")
        icd.register_apid(0x10, "OBC HK")
        icd.register_apid(0x11, "OBC CMD")
        icd.register_apid(0x30, "Orphan Process")
        tm = build_tm_packet_def(0x10, 3, 25, "HK report", 20)
        tc = build_tc_packet_def(0x11, 8, 1, "Enable", 0, 0)
        icd.add_tm(tm)
        icd.add_tc(tc)
        result = icd.check_completeness()
        self.assertFalse(result["compliant"])
        self.assertTrue(any("0x030" in f or "0x30" in f for f in result["findings"]))

    def test_no_tm_finding(self):
        icd = TMTCIcd("test-icd")
        icd.register_apid(0x11, "OBC CMD")
        tc = build_tc_packet_def(0x11, 8, 1, "Enable", 0, 0)
        icd.add_tc(tc)
        result = icd.check_completeness()
        self.assertFalse(result["compliant"])
        self.assertTrue(any("TM" in f for f in result["findings"]))

    def test_no_tc_finding(self):
        icd = TMTCIcd("test-icd")
        icd.register_apid(0x10, "OBC HK")
        tm = build_tm_packet_def(0x10, 3, 25, "HK report", 20)
        icd.add_tm(tm)
        result = icd.check_completeness()
        self.assertFalse(result["compliant"])
        self.assertTrue(any("TC" in f for f in result["findings"]))

    def test_tm_count_and_tc_count(self):
        icd = self._make_icd()
        # Add a second TM packet on same APID
        tm2 = build_tm_packet_def(0x10, 3, 1, "Min HK", 4)
        icd.add_tm(tm2)
        self.assertEqual(icd.tm_count(), 2)
        self.assertEqual(icd.tc_count(), 1)

    def test_get_packets_by_service(self):
        icd = self._make_icd()
        pkts = icd.get_packets_by_service(3)
        self.assertEqual(len(pkts), 1)
        self.assertEqual(pkts[0]["service"], 3)
        self.assertEqual(pkts[0]["type"], "TM")

    def test_get_packets_by_service_no_match(self):
        icd = self._make_icd()
        pkts = icd.get_packets_by_service(99)
        self.assertEqual(pkts, [])

    def test_multiple_packets_same_apid(self):
        icd = TMTCIcd("multi-test")
        icd.register_apid(0x10, "OBC HK")
        icd.register_apid(0x11, "OBC CMD")
        for svc in (3, 5, 17):
            icd.add_tm(build_tm_packet_def(0x10, svc, 1, "pkt svc {0}".format(svc), 8))
        icd.add_tc(build_tc_packet_def(0x11, 17, 1, "Test request", 0xF, 0))
        result = icd.check_completeness()
        self.assertTrue(result["compliant"])
        self.assertEqual(result["tm_count"], 3)


if __name__ == "__main__":
    unittest.main()
