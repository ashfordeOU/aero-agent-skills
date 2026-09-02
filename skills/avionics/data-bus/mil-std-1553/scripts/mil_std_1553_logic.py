#!/usr/bin/env python3
"""MIL-STD-1553B command/response data bus word logic (paraphrase, summary only).

Common-knowledge summary (standards-map.yaml, mil-std-1553: public-domain
US government work, paraphrase preferred): MIL-STD-1553B is a 1 Mbps time
division command/response multiplex data bus for military avionics. One bus
controller (BC) commands up to 31 remote terminals (RTs) on the bus; a bus
monitor (BM) records traffic without responding. The bus is dual redundant
(A and B): the second bus carries the same schedule and serves as the retry
path. The exact word-format tables, mode code assignments, and timing
limits are standard data in the current revision and are NOT reproduced
here; this module implements the 20-bit word layout, odd parity, and
message format classification used for typical traffic.

Integer convention (bit 0 is the least significant bit and the last sync
bit transmitted): bit 19 holds parity, bits 18-3 hold the 16 information
bits in transmission order (bit 18 is the first information bit
transmitted), and bits 2-0 hold the 3-bit sync pattern. The command and
status sync pattern is 1-0-0 (integer 0b100); the data sync pattern is
0-1-1 (integer 0b011). Odd parity is computed over the full 20-bit word:
the parity bit makes the total number of 1 bits in the word odd, so a
single flipped bit is always detected.

Command word layout (transmitted order): 5-bit remote terminal address,
1-bit T/R (0 = receive, 1 = transmit), 5-bit subaddress, 5-bit word count,
parity. Subaddress 00000 or 11111 marks a mode command, in which case the
word-count field carries the mode code. RT address 11111 marks a broadcast
command. Status word layout: RT address, message error, instrumentation,
service request, 3 reserved zeros, broadcast command received, busy,
subsystem flag, dynamic bus control acceptance, terminal flag, parity.
Data word: 16 data bits, parity.

Worked anchors (verified by test_mil_std_1553_logic.py):
- encode_command_word(5, 12, 16, 1) -> 93316 (odd parity)
- decode_command_word(93316) -> rt_address 5, transmit_receive 1,
  subaddress 12, word_count 16, parity 0, parity_ok True
- encode_data_word(0x7FFF) -> 262139 (odd parity)
- encode_status_word(5, busy=1) -> 606276 (odd parity)
- classify_message(31, 8, 8, 0) -> "broadcast"
- classify_message(3, 0, 17, 0) -> "mode-code"
- classify_message(5, 12, 16, 1) -> "rt-to-bc"
- is_rt_to_rt_pair(receive_cmd, transmit_cmd) -> True
"""

WORD_BITS = 20
WORD_MASK = (1 << WORD_BITS) - 1
RT_MASK = 0x1F
DATA16_MASK = 0xFFFF

# Sync patterns in integer bits 2-0 (first transmitted sync bit in bit 2).
SYNC_COMMAND = 0b100
SYNC_DATA = 0b011

# Subaddress values that mark a mode command rather than a data transfer.
MODE_SUBADDRESSES = (0, 0x1F)
# Remote terminal address that marks a broadcast command.
BROADCAST_RT = 0x1F


def _require_int(value, name, lo, hi):
    """Return value when it is an int in [lo, hi]; raise ValueError otherwise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if not (lo <= value <= hi):
        raise ValueError(
            "%s %d out of range [%d, %d]" % (name, value, lo, hi)
        )
    return value


def _require_word(value):
    """Return value when it is a 20-bit integer; raise ValueError otherwise."""
    return _require_int(value, "word", 0, WORD_MASK)


def odd_parity_bit(data16, sync):
    """Parity bit (0 or 1) that makes the full 20-bit word odd-parity.

    The parity bit goes in bit 19 so that the total number of 1 bits in
    the 20-bit word (16 information bits, 3-bit sync, parity) is odd.
    """
    ones = bin(data16 & DATA16_MASK).count("1") + bin(sync & 0b111).count("1")
    return 0 if (ones % 2) else 1


def parity_ok(word):
    """True when the 20-bit word carries an odd number of 1 bits."""
    return (bin(_require_word(word)).count("1") % 2) == 1


def encode_command_word(rt_address, subaddress, word_count, transmit_receive):
    """Pack RT address, T/R bit, subaddress, word count, and parity into a
    20-bit command word.

    All fields are validated: RT address 0-31, subaddress 0-31, word count
    0-31 (also used as the mode code for mode commands), transmit_receive
    0 or 1. ValueError is raised for out-of-range or non-integer fields.
    The odd parity bit is computed over the full 20-bit word.
    """
    rt_address = _require_int(rt_address, "rt_address", 0, RT_MASK)
    subaddress = _require_int(subaddress, "subaddress", 0, RT_MASK)
    word_count = _require_int(word_count, "word_count", 0, RT_MASK)
    tr = _require_int(transmit_receive, "transmit_receive", 0, 1)
    data16 = (rt_address << 11) | (tr << 10) | (subaddress << 5) | word_count
    parity = odd_parity_bit(data16, SYNC_COMMAND)
    return (parity << 19) | (data16 << 3) | SYNC_COMMAND


def decode_command_word(word):
    """Split a 20-bit command word into its fields.

    Returns a dict with rt_address, transmit_receive, subaddress,
    word_count, parity, and parity_ok (True when the word has odd parity).
    Raises ValueError when the word is not a 20-bit integer or does not
    carry the command sync pattern (0b100).
    """
    word = _require_word(word)
    if (word & 0b111) != SYNC_COMMAND:
        raise ValueError(
            "word 0x%X does not carry the command sync pattern 100" % word
        )
    data16 = (word >> 3) & DATA16_MASK
    return {
        "rt_address": (data16 >> 11) & RT_MASK,
        "transmit_receive": (data16 >> 10) & 1,
        "subaddress": (data16 >> 5) & RT_MASK,
        "word_count": data16 & RT_MASK,
        "parity": (word >> 19) & 1,
        "parity_ok": (bin(word).count("1") % 2) == 1,
    }


def encode_data_word(data):
    """Pack 16 data bits and odd parity into a 20-bit data word.

    The data sync pattern is 0-1-1 (0b011). Raises ValueError when data
    is not an integer in [0, 65535].
    """
    data = _require_int(data, "data", 0, DATA16_MASK)
    parity = odd_parity_bit(data, SYNC_DATA)
    return (parity << 19) | (data << 3) | SYNC_DATA


def decode_data_word(word):
    """Split a 20-bit data word into data, parity, and parity_ok.

    Raises ValueError when the word is not a 20-bit integer or does not
    carry the data sync pattern (0b011).
    """
    word = _require_word(word)
    if (word & 0b111) != SYNC_DATA:
        raise ValueError(
            "word 0x%X does not carry the data sync pattern 011" % word
        )
    return {
        "data": (word >> 3) & DATA16_MASK,
        "parity": (word >> 19) & 1,
        "parity_ok": (bin(word).count("1") % 2) == 1,
    }


def encode_status_word(rt_address, message_error=0, instrumentation=0,
                       service_request=0, broadcast_received=0, busy=0,
                       subsystem_flag=0, dynamic_bus_control_acceptance=0,
                       terminal_flag=0):
    """Pack RT address, status flags, and odd parity into a 20-bit status word.

    Flag layout in transmission order: message error, instrumentation,
    service request, 3 reserved zeros, broadcast command received, busy,
    subsystem flag, dynamic bus control acceptance, terminal flag. The
    status word uses the command sync pattern (0b100). Raises ValueError
    on out-of-range fields.
    """
    rt_address = _require_int(rt_address, "rt_address", 0, RT_MASK)
    me = _require_int(message_error, "message_error", 0, 1)
    inst = _require_int(instrumentation, "instrumentation", 0, 1)
    sr = _require_int(service_request, "service_request", 0, 1)
    bcr = _require_int(broadcast_received, "broadcast_received", 0, 1)
    bsy = _require_int(busy, "busy", 0, 1)
    ssf = _require_int(subsystem_flag, "subsystem_flag", 0, 1)
    dbca = _require_int(dynamic_bus_control_acceptance,
                        "dynamic_bus_control_acceptance", 0, 1)
    tfl = _require_int(terminal_flag, "terminal_flag", 0, 1)
    data16 = (
        (rt_address << 11)
        | (me << 10)
        | (inst << 9)
        | (sr << 8)
        | (bcr << 4)
        | (bsy << 3)
        | (ssf << 2)
        | (dbca << 1)
        | tfl
    )
    parity = odd_parity_bit(data16, SYNC_COMMAND)
    return (parity << 19) | (data16 << 3) | SYNC_COMMAND


def decode_status_word(word):
    """Split a 20-bit status word into its fields.

    Returns a dict with rt_address, message_error, instrumentation,
    service_request, broadcast_received, busy, subsystem_flag,
    dynamic_bus_control_acceptance, terminal_flag, parity, and parity_ok.
    Raises ValueError when the word is not a 20-bit integer or does not
    carry the command sync pattern.
    """
    word = _require_word(word)
    if (word & 0b111) != SYNC_COMMAND:
        raise ValueError(
            "word 0x%X does not carry the status sync pattern 100" % word
        )
    data16 = (word >> 3) & DATA16_MASK
    return {
        "rt_address": (data16 >> 11) & RT_MASK,
        "message_error": (data16 >> 10) & 1,
        "instrumentation": (data16 >> 9) & 1,
        "service_request": (data16 >> 8) & 1,
        "broadcast_received": (data16 >> 4) & 1,
        "busy": (data16 >> 3) & 1,
        "subsystem_flag": (data16 >> 2) & 1,
        "dynamic_bus_control_acceptance": (data16 >> 1) & 1,
        "terminal_flag": data16 & 1,
        "parity": (word >> 19) & 1,
        "parity_ok": (bin(word).count("1") % 2) == 1,
    }


def classify_message(rt_address, subaddress, word_count, transmit_receive):
    """Classify the message format a command word initiates.

    Returns one of "broadcast" (RT address 31), "mode-code" (subaddress 0
    or 31), "bc-to-rt" (T/R 0), or "rt-to-bc" (T/R 1). RT-to-RT transfers
    need two command words and are recognized by is_rt_to_rt_pair.
    Raises ValueError when any field is out of range (RT address 0-31,
    subaddress 0-31, word count 0-31, transmit_receive 0-1).
    """
    rt_address = _require_int(rt_address, "rt_address", 0, RT_MASK)
    subaddress = _require_int(subaddress, "subaddress", 0, RT_MASK)
    word_count = _require_int(word_count, "word_count", 0, RT_MASK)
    tr = _require_int(transmit_receive, "transmit_receive", 0, 1)
    if rt_address == BROADCAST_RT:
        return "broadcast"
    if subaddress in MODE_SUBADDRESSES:
        return "mode-code"
    if tr == 1:
        return "rt-to-bc"
    return "bc-to-rt"


def is_rt_to_rt_pair(cmd_rx, cmd_tx):
    """True when the two command words form a valid RT-to-RT transfer.

    In an RT-to-RT message the bus controller sends a receive command
    (T/R 0) to the receiving terminal followed by a transmit command
    (T/R 1) to the transmitting terminal. Neither word may be a broadcast
    (RT address 31) or a mode command (subaddress 0 or 31). Raises
    ValueError when either word is not a valid command word.
    """
    rx = decode_command_word(cmd_rx)
    tx = decode_command_word(cmd_tx)
    if rx["transmit_receive"] != 0 or tx["transmit_receive"] != 1:
        return False
    if rx["rt_address"] == BROADCAST_RT or tx["rt_address"] == BROADCAST_RT:
        return False
    if rx["subaddress"] in MODE_SUBADDRESSES:
        return False
    if tx["subaddress"] in MODE_SUBADDRESSES:
        return False
    return True
