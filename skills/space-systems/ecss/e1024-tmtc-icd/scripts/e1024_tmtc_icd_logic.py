"""
ECSS-E-ST-10-24C §5.9 — TM/TC ICD logic.
Validates CCSDS/PUS-C packet definitions and checks ICD completeness.
stdlib only; no external dependencies.
"""

# ---------------------------------------------------------------------------
# Constants — CCSDS 133.0-B-2 and ECSS-E-ST-70-41C (PUS-C)
# ---------------------------------------------------------------------------

PACKET_TYPE_TM = 0
PACKET_TYPE_TC = 1

CCSDS_VERSION = 0  # 3-bit version field; always 0 per CCSDS 133.0-B-2

APID_MIN = 0x000
APID_MAX = 0x7FE   # 0x7FF is reserved as idle-packet APID
APID_IDLE = 0x7FF

PUS_VERSION_C = 2  # PUS-C version nibble (ECSS-E-ST-70-41C)

SEQ_FLAG_CONTINUATION = 0b00
SEQ_FLAG_FIRST        = 0b01
SEQ_FLAG_LAST         = 0b10
SEQ_FLAG_STANDALONE   = 0b11

# CCSDS Packet Data Length field is 16-bit; max encoded value = 65535
CCSDS_MAX_DATA_LENGTH_FIELD = 65535

# Minimum secondary header sizes (bytes)
PUS_C_TM_SEC_HEADER_MIN = 10
PUS_C_TC_SEC_HEADER_MIN = 5

# Acknowledgement flag bit positions (TC secondary header nibble)
ACK_ACCEPTANCE  = 0b0001
ACK_START       = 0b0010
ACK_PROGRESS    = 0b0100
ACK_COMPLETION  = 0b1000

# Subset of PUS-C reserved service numbers for reference cross-check
PUS_RESERVED_SERVICES = {
    1:  "Request Verification",
    3:  "Housekeeping",
    5:  "Event Reporting",
    6:  "Memory Management",
    8:  "Function Management",
    11: "TC Scheduling",
    12: "On-Board Monitoring",
    13: "Large Data Transfer",
    14: "Real-Time Forwarding Control",
    15: "On-Board Storage and Retrieval",
    17: "Test",
    19: "Event-Action",
    20: "On-Board Parameter Management",
    21: "Request Sequencing",
    23: "File Management",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ICDValidationError(Exception):
    """Base for all ICD validation failures."""


class APIDError(ICDValidationError):
    """Raised when an APID value is out of range or misused."""


class PacketStructureError(ICDValidationError):
    """Raised when a packet field value violates CCSDS or PUS-C rules."""


class ICDCompletenessError(ICDValidationError):
    """Raised when an ICD is structurally incomplete."""


# ---------------------------------------------------------------------------
# APID validation
# ---------------------------------------------------------------------------

def validate_apid(apid):
    """
    Validate a CCSDS APID value.
    Returns a dict describing the APID status.
    Raises APIDError if the value is out of range.
    """
    if not isinstance(apid, int):
        raise APIDError(
            "APID must be an integer, got {t}".format(t=type(apid).__name__)
        )
    if apid < APID_MIN or apid > APID_IDLE:
        raise APIDError(
            "APID {v:#05x} out of valid range [0x000, 0x7FF]".format(v=apid)
        )
    if apid == APID_IDLE:
        return {"apid": apid, "status": "idle", "valid": True}
    return {"apid": apid, "status": "operational", "valid": True}


# ---------------------------------------------------------------------------
# PUS service / subservice validation
# ---------------------------------------------------------------------------

def validate_pus_service(service, subservice):
    """
    Validate a PUS-C service/subservice pair.
    Both fields must be in the range [1, 255].
    Returns a dict with the service name (reserved or project-specific).
    Raises PacketStructureError if either field is out of range.
    """
    if not isinstance(service, int) or not (1 <= service <= 255):
        raise PacketStructureError(
            "PUS service {s!r} out of range [1, 255]".format(s=service)
        )
    if not isinstance(subservice, int) or not (1 <= subservice <= 255):
        raise PacketStructureError(
            "PUS subservice {s!r} out of range [1, 255]".format(s=subservice)
        )
    name = PUS_RESERVED_SERVICES.get(service, "Project-specific")
    return {
        "service": service,
        "subservice": subservice,
        "service_name": name,
        "valid": True,
    }


# ---------------------------------------------------------------------------
# Packet definition builders
# ---------------------------------------------------------------------------

def build_tm_packet_def(apid, service, subservice, description, data_field_bytes):
    """
    Build and validate a TM packet definition entry for the ICD.

    Per ECSS-E-ST-10-24C §5.9, a TM ICD entry must specify the APID,
    PUS service/subservice, a plain-language description, and the application
    data field size. The CCSDS Packet Data Length field value is derived as:
      (PUS-C TM secondary header size + data_field_bytes) - 1

    Raises APIDError, PacketStructureError, or ICDValidationError on failure.
    """
    if apid == APID_IDLE:
        raise APIDError(
            "APID 0x7FF (idle) must not be used in a TM ICD application entry"
        )
    validate_apid(apid)
    validate_pus_service(service, subservice)
    if not isinstance(description, str) or not description.strip():
        raise PacketStructureError("TM packet description must be a non-empty string")
    if not isinstance(data_field_bytes, int) or data_field_bytes < 0:
        raise PacketStructureError(
            "data_field_bytes must be a non-negative integer"
        )
    total_data_field = PUS_C_TM_SEC_HEADER_MIN + data_field_bytes
    pkt_data_length = total_data_field - 1
    if pkt_data_length > CCSDS_MAX_DATA_LENGTH_FIELD:
        raise PacketStructureError(
            "Computed Packet Data Length {v} exceeds CCSDS maximum {m}".format(
                v=pkt_data_length, m=CCSDS_MAX_DATA_LENGTH_FIELD
            )
        )
    return {
        "type": "TM",
        "apid": apid,
        "service": service,
        "subservice": subservice,
        "description": description,
        "data_field_bytes": data_field_bytes,
        "pus_version": PUS_VERSION_C,
        "packet_data_length_field": pkt_data_length,
        "valid": True,
    }


def build_tc_packet_def(apid, service, subservice, description, ack_flags, param_bytes):
    """
    Build and validate a TC packet definition entry for the ICD.

    Per ECSS-E-ST-10-24C §5.9, a TC ICD entry must specify the APID,
    PUS service/subservice, a plain-language description, the 4-bit
    acknowledgement flags nibble, and the parameter field size. The CCSDS
    Packet Data Length field value is derived as:
      (PUS-C TC secondary header size + param_bytes) - 1

    Raises APIDError, PacketStructureError, or ICDValidationError on failure.
    """
    if apid == APID_IDLE:
        raise APIDError(
            "APID 0x7FF (idle) must not be used in a TC ICD application entry"
        )
    validate_apid(apid)
    validate_pus_service(service, subservice)
    if not isinstance(description, str) or not description.strip():
        raise PacketStructureError("TC packet description must be a non-empty string")
    if not isinstance(ack_flags, int) or not (0 <= ack_flags <= 0xF):
        raise PacketStructureError(
            "ack_flags must be an integer in [0, 15], got {v!r}".format(v=ack_flags)
        )
    if not isinstance(param_bytes, int) or param_bytes < 0:
        raise PacketStructureError(
            "param_bytes must be a non-negative integer"
        )
    total_data_field = PUS_C_TC_SEC_HEADER_MIN + param_bytes
    pkt_data_length = total_data_field - 1
    if pkt_data_length > CCSDS_MAX_DATA_LENGTH_FIELD:
        raise PacketStructureError(
            "Computed Packet Data Length {v} exceeds CCSDS maximum {m}".format(
                v=pkt_data_length, m=CCSDS_MAX_DATA_LENGTH_FIELD
            )
        )
    return {
        "type": "TC",
        "apid": apid,
        "service": service,
        "subservice": subservice,
        "description": description,
        "ack_flags": ack_flags,
        "param_bytes": param_bytes,
        "pus_version": PUS_VERSION_C,
        "packet_data_length_field": pkt_data_length,
        "valid": True,
    }


# ---------------------------------------------------------------------------
# ICD registry
# ---------------------------------------------------------------------------

class TMTCIcd:
    """
    Registry of TM and TC packet definitions for a single ICD deliverable.
    Enforces APID registration and checks completeness per ECSS-E-ST-10-24C §5.9.
    """

    def __init__(self, icd_name):
        if not isinstance(icd_name, str) or not icd_name.strip():
            raise ICDValidationError("ICD name must be a non-empty string")
        self.icd_name = icd_name
        self._tm = {}            # apid -> list[dict]
        self._tc = {}            # apid -> list[dict]
        self._apid_names = {}    # apid -> str

    def register_apid(self, apid, name):
        """Register an APID with a human-readable process name."""
        result = validate_apid(apid)
        if result["status"] == "idle":
            raise APIDError("APID 0x7FF (idle) must not be registered as an application")
        if not isinstance(name, str) or not name.strip():
            raise ICDValidationError("APID name must be a non-empty string")
        self._apid_names[apid] = name

    def add_tm(self, packet_def):
        """Add a pre-validated TM packet definition to the ICD."""
        if not isinstance(packet_def, dict) or packet_def.get("type") != "TM":
            raise ICDValidationError("Expected a TM packet definition dict")
        apid = packet_def["apid"]
        self._tm.setdefault(apid, []).append(packet_def)

    def add_tc(self, packet_def):
        """Add a pre-validated TC packet definition to the ICD."""
        if not isinstance(packet_def, dict) or packet_def.get("type") != "TC":
            raise ICDValidationError("Expected a TC packet definition dict")
        apid = packet_def["apid"]
        self._tc.setdefault(apid, []).append(packet_def)

    def tm_count(self):
        """Return the total number of TM packet definitions."""
        return sum(len(v) for v in self._tm.values())

    def tc_count(self):
        """Return the total number of TC packet definitions."""
        return sum(len(v) for v in self._tc.values())

    def get_packets_by_service(self, service):
        """Return all TM and TC definitions for a given PUS service number."""
        result = []
        for pkts in self._tm.values():
            for p in pkts:
                if p["service"] == service:
                    result.append(p)
        for pkts in self._tc.values():
            for p in pkts:
                if p["service"] == service:
                    result.append(p)
        return result

    def check_completeness(self):
        """
        Evaluate ICD completeness per ECSS-E-ST-10-24C §5.9.
        Rules:
          - Every APID used in packet definitions must be registered.
          - Every registered APID must have at least one packet definition.
          - The ICD must contain at least one TM definition.
          - The ICD must contain at least one TC definition.
        Returns a dict; the ICD is compliant when findings is an empty list.
        """
        findings = []
        used_apids = set(self._tm.keys()) | set(self._tc.keys())
        registered_apids = set(self._apid_names.keys())

        for apid in sorted(used_apids - registered_apids):
            findings.append(
                "APID {a:#05x} appears in packet definitions but is not registered".format(
                    a=apid
                )
            )
        for apid in sorted(registered_apids - used_apids):
            findings.append(
                "APID {a:#05x} is registered but has no packet definitions".format(
                    a=apid
                )
            )
        if self.tm_count() == 0:
            findings.append("ICD contains no TM packet definitions")
        if self.tc_count() == 0:
            findings.append("ICD contains no TC packet definitions")

        return {
            "icd_name": self.icd_name,
            "tm_count": self.tm_count(),
            "tc_count": self.tc_count(),
            "registered_apids": sorted(self._apid_names.keys()),
            "compliant": len(findings) == 0,
            "findings": findings,
        }
