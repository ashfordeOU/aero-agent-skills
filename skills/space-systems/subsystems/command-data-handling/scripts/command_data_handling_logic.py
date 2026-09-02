"""Spacecraft command and data handling (C&DH) logic, pure stdlib.

Deterministic, offline building blocks for the C&DH subsystem sizing and
design checks:

- crc16_ccitt: CRC-16-CCITT (poly 0x1021, init 0xFFFF, no reflection,
  no final xor) over arbitrary bytes; the error-detection layer used by
  both the telemetry and command formats here.
- telemetry_packet / parse_telemetry_packet: CCSDS-style space packet
  (6-byte primary header + data + CRC-16 trailer). Header fields:
  version (3 bits) = 0, packet type (1 bit) = 0 for telemetry, APID
  (11 bits), sequence flags (2 bits), sequence count (14 bits), packet
  data length (16 bits, CCSDS convention: length = len(data) - 1).
- command_packet / validate_command_packet: fixed 5-byte command header
  (opcode, APID, 16-bit payload length) + payload + CRC-16; validation
  checks structure first (too short, length field), then CRC, then
  expected opcode/APID.
- downlink_time_s / data_rate_for_window / downlink_fits_window:
  downlink budgeting from stored data volume (bits) and link rate
  (bps); window_s is the contact duration.
- storage_size_bytes: onboard mass-memory sizing from per-orbit data
  volume with an integer-exact margin (basis points, no float drift).
- frame_count: number of fixed-size downlink frames for a data volume.
- redundancy_ok: N-string availability check (dual-string C&DH).

Units: data volume in bits (downlink functions) or bytes (storage),
rates in bits per second, time in seconds, frames are whole units.
Invalid physical inputs raise ValueError with a clear message.
"""

import math

CRC16_POLY = 0x1021
CRC16_INIT = 0xFFFF


def crc16_ccitt(data):
    """CRC-16-CCITT (0x1021, init 0xFFFF) of a bytes-like object.

    Args:
        data: bytes-like payload.
    Returns:
        int: 16-bit CRC value.
    """
    crc = CRC16_INIT
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _crc_bytes(body):
    c = crc16_ccitt(body)
    return bytes([(c >> 8) & 0xFF, c & 0xFF])


def telemetry_packet(apid, seq_count, data, seq_flags=3):
    """Assemble a CCSDS-style telemetry space packet with CRC-16 trailer.

    Layout: version(3)=0 | type(1)=0 | sec-hdr(1)=0 | APID(11), then
    seq-flags(2) | seq-count(14), then packet data length (len(data)-1),
    then data, then CRC-16 over header+data (big endian).

    Args:
        apid: application process id, 0..2047 (11 bits).
        seq_count: packet sequence count, 0..16383 (14 bits).
        data: bytes-like payload, 1..256 bytes (length field is 16 bits
            but the layout here targets a single 8-bit page).
        seq_flags: 0..3, default 3 = unsegmented packet.
    Returns:
        bytes: the complete packet.
    Raises:
        ValueError: on out-of-range apid, seq_count, seq_flags, or empty data.
    """
    if not (0 <= apid <= 0x7FF):
        raise ValueError("apid must be 0..2047 (got %r)" % (apid,))
    if not (0 <= seq_count <= 0x3FFF):
        raise ValueError("seq_count must be 0..16383 (got %r)" % (seq_count,))
    if not (0 <= seq_flags <= 0x3):
        raise ValueError("seq_flags must be 0..3 (got %r)" % (seq_flags,))
    data = bytes(data)
    if len(data) < 1:
        raise ValueError("telemetry packet data must be at least 1 byte")
    if len(data) > 256:
        raise ValueError("telemetry packet data must be at most 256 bytes")
    word1 = apid  # version 0, type 0, secondary header flag 0
    word2 = (seq_flags << 14) | seq_count
    header = bytes(
        [
            (word1 >> 8) & 0xFF,
            word1 & 0xFF,
            (word2 >> 8) & 0xFF,
            word2 & 0xFF,
            0x00,
            (len(data) - 1) & 0xFF,
        ]
    )
    body = header + data
    return body + _crc_bytes(body)


def parse_telemetry_packet(packet):
    """Parse a CCSDS-style telemetry packet, verifying structure and CRC.

    Args:
        packet: bytes-like packet produced by telemetry_packet.
    Returns:
        dict: version, type, apid, seq_flags, seq_count, data (bytes).
    Raises:
        ValueError: if the packet is too short, the CRC does not match,
            the length field disagrees with the payload, or the packet
            type bits are not telemetry (type=0).
    """
    packet = bytes(packet)
    if len(packet) < 9:
        raise ValueError("packet too short: %d bytes (need >= 9)" % len(packet))
    body, trailer = packet[:-2], packet[-2:]
    if crc16_ccitt(body) != (trailer[0] << 8) | trailer[1]:
        raise ValueError("CRC mismatch")
    word1 = (packet[0] << 8) | packet[1]
    version = (word1 >> 13) & 0x7
    ptype = (word1 >> 12) & 0x1
    apid = word1 & 0x7FF
    word2 = (packet[2] << 8) | packet[3]
    seq_flags = (word2 >> 14) & 0x3
    seq_count = word2 & 0x3FFF
    data_len_field = (packet[4] << 8) | packet[5]
    data = packet[6 : 6 + data_len_field + 1]
    if len(data) != data_len_field + 1:
        raise ValueError("length field mismatch")
    if version != 0 or ptype != 0:
        raise ValueError("not a telemetry packet (version/type bits)")
    return {
        "version": version,
        "type": ptype,
        "apid": apid,
        "seq_flags": seq_flags,
        "seq_count": seq_count,
        "data": data,
    }


def command_packet(opcode, apid, payload=b"", crc=True):
    """Assemble a C&DH command: opcode, APID, 16-bit length, payload, CRC.

    Layout: opcode (1 byte), APID (2 bytes, 11 bits used), payload length
    (2 bytes, big endian), payload, CRC-16 over everything before it.

    Args:
        opcode: command opcode, 0..255.
        apid: addressed subsystem, 0..2047.
        payload: bytes-like command arguments.
        crc: if True (default) append the CRC-16 trailer.
    Returns:
        bytes: the command packet.
    Raises:
        ValueError: on out-of-range opcode/apid or oversized payload.
    """
    if not (0 <= opcode <= 0xFF):
        raise ValueError("opcode must be 0..255 (got %r)" % (opcode,))
    if not (0 <= apid <= 0x7FF):
        raise ValueError("apid must be 0..2047 (got %r)" % (apid,))
    payload = bytes(payload)
    if len(payload) > 0xFFFF:
        raise ValueError("command payload too long (%d bytes)" % len(payload))
    header = bytes(
        [
            opcode,
            (apid >> 8) & 0xFF,
            apid & 0xFF,
            (len(payload) >> 8) & 0xFF,
            len(payload) & 0xFF,
        ]
    )
    body = header + payload
    if not crc:
        return body
    return body + _crc_bytes(body)


def validate_command_packet(packet, expected_opcode=None, expected_apid=None):
    """Validate a command packet: structure, CRC, then expected fields.

    Checks in order: minimum length, length-field consistency, CRC-16,
    expected opcode, expected APID. The first failure wins.

    Args:
        packet: bytes-like command packet.
        expected_opcode: optional opcode the command must carry.
        expected_apid: optional APID the command must address.
    Returns:
        tuple (bool, str): (True, "ok") or (False, "<reason>").
    """
    packet = bytes(packet)
    if len(packet) < 7:
        return (False, "packet too short")
    opcode = packet[0]
    apid = (packet[1] << 8) | packet[2]
    length = (packet[3] << 8) | packet[4]
    if len(packet) != 5 + length + 2:
        return (False, "length field mismatch")
    body, trailer = packet[:-2], packet[-2:]
    if crc16_ccitt(body) != (trailer[0] << 8) | trailer[1]:
        return (False, "crc mismatch")
    if expected_opcode is not None and opcode != expected_opcode:
        return (False, "unexpected opcode")
    if expected_apid is not None and apid != expected_apid:
        return (False, "unexpected apid")
    return (True, "ok")


def downlink_time_s(data_bits, data_rate_bps):
    """Time in seconds to downlink a data volume at a link rate.

    Args:
        data_bits: stored data volume in bits, >= 0.
        data_rate_bps: downlink rate in bits per second, > 0.
    Returns:
        float: contact time in seconds.
    Raises:
        ValueError: if data_bits < 0 or data_rate_bps <= 0.
    """
    if data_bits < 0:
        raise ValueError("data_bits must be >= 0 (got %r)" % (data_bits,))
    if data_rate_bps <= 0:
        raise ValueError("data_rate_bps must be > 0 (got %r)" % (data_rate_bps,))
    return data_bits / data_rate_bps


def data_rate_for_window(data_bits, window_s):
    """Required downlink rate in bps to clear a data volume in a window.

    Args:
        data_bits: stored data volume in bits, >= 0.
        window_s: available downlink window in seconds, > 0.
    Returns:
        float: required rate in bits per second.
    Raises:
        ValueError: if data_bits < 0 or window_s <= 0.
    """
    if data_bits < 0:
        raise ValueError("data_bits must be >= 0 (got %r)" % (data_bits,))
    if window_s <= 0:
        raise ValueError("window_s must be > 0 (got %r)" % (window_s,))
    return data_bits / window_s


def downlink_fits_window(data_bits, data_rate_bps, window_s):
    """True if the data volume clears within the downlink window."""
    return downlink_time_s(data_bits, data_rate_bps) <= window_s


def storage_size_bytes(per_orbit_bytes, orbits, margin_fraction=0.0):
    """Onboard storage size for N orbits of data plus a sizing margin.

    The margin is applied with integer basis-point math so that e.g. a
    10% margin on 3000 bytes is exactly 3300 bytes (no float ceil drift).

    Args:
        per_orbit_bytes: data volume per orbit in bytes, >= 0.
        orbits: number of orbits, >= 0.
        margin_fraction: sizing margin as a fraction, >= 0 (e.g. 0.1).
    Returns:
        int: storage size in bytes, rounded up to a whole byte.
    Raises:
        ValueError: on negative inputs.
    """
    if per_orbit_bytes < 0:
        raise ValueError("per_orbit_bytes must be >= 0 (got %r)" % (per_orbit_bytes,))
    if orbits < 0:
        raise ValueError("orbits must be >= 0 (got %r)" % (orbits,))
    if margin_fraction < 0:
        raise ValueError("margin_fraction must be >= 0 (got %r)" % (margin_fraction,))
    total = per_orbit_bytes * orbits
    if margin_fraction == 0.0:
        return total
    margin_bp = int(round(margin_fraction * 10000.0))
    return (total * (10000 + margin_bp) + 9999) // 10000


def frame_count(data_bits, frame_data_bits):
    """Number of fixed-size frames needed for a data volume (ceil division).

    Args:
        data_bits: data volume in bits, >= 0.
        frame_data_bits: usable data capacity per frame in bits, > 0.
    Returns:
        int: whole frames required; 0 for an empty volume.
    Raises:
        ValueError: if data_bits < 0 or frame_data_bits <= 0.
    """
    if data_bits < 0:
        raise ValueError("data_bits must be >= 0 (got %r)" % (data_bits,))
    if frame_data_bits <= 0:
        raise ValueError("frame_data_bits must be > 0 (got %r)" % (frame_data_bits,))
    return (data_bits + frame_data_bits - 1) // frame_data_bits


def redundancy_ok(healthy_strings, required=1):
    """Availability check: healthy redundant strings meet the requirement.

    Dual-string C&DH keeps working with one healthy string; this is the
    generic check behind that decision.

    Args:
        healthy_strings: number of healthy redundant strings, >= 0.
        required: minimum healthy strings needed, >= 1.
    Returns:
        bool: True if healthy_strings >= required.
    Raises:
        ValueError: if required < 1 or healthy_strings < 0.
    """
    if healthy_strings < 0:
        raise ValueError("healthy_strings must be >= 0 (got %r)" % (healthy_strings,))
    if required < 1:
        raise ValueError("required must be >= 1 (got %r)" % (required,))
    return healthy_strings >= required


if __name__ == "__main__":  # pragma: no cover
    print("crc16_ccitt(b'123456789') = %#06x (expect 0x29b1)" % crc16_ccitt(b"123456789"))
    print("crc16_ccitt(b'') = %#06x (expect 0xffff)" % crc16_ccitt(b""))
