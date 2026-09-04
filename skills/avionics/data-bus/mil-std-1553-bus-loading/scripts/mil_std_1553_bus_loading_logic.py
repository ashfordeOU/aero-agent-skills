"""MIL-STD-1553 bus loading model (conceptual level, pure stdlib).

Converts a minor-frame message schedule into wire-word counts per message
type, applies the fixed 24 microsecond word slot (20 us of word time at
the 1 Mbps data rate plus a 4 us inter-word gap), sums the schedule time,
and returns the bus utilization against the minor-frame length with an
80 percent loading guideline verdict.

Message kinds follow the command/response conventions:
- BCRT (BC-to-RT): 1 command word + data words + 1 status word.
- RTBC (RT-to-BC): 1 command word + 1 status word + data words.
- RTRT (RT-to-RT): 2 command words + 1 status word + data words.

A message carries between 1 and 32 data words. No word encode/decode,
framing or line coding is modelled here; this module works at the
schedule time-budget level only.
"""

WORD_TIME_US = 20.0      # microseconds per word, 20 bit times at 1 Mbps
WORD_GAP_US = 4.0        # microseconds inter-word gap
WORD_SLOT_US = WORD_TIME_US + WORD_GAP_US  # 24.0 us per wire word
FRAME_US_DEFAULT = 5000.0   # microseconds, 5 ms minor frame
LOAD_BUDGET_FRACTION = 0.80  # 80 percent loading guideline

_MESSAGE_KINDS = ("BCRT", "RTBC", "RTRT")


def wire_words(kind, data_words):
    """Wire words on the bus for one message of the given kind.

    kind is one of BCRT, RTBC, RTRT. data_words must be an integer in
    1..32. Returns the command/status overhead plus the data words.
    """
    if kind not in _MESSAGE_KINDS:
        raise ValueError("unknown message kind %r, use BCRT, RTBC or RTRT"
                         % (kind,))
    if not isinstance(data_words, int):
        raise ValueError("data_words must be an integer")
    if data_words < 1 or data_words > 32:
        raise ValueError("data_words must be in 1..32")
    if kind == "RTRT":
        return data_words + 3
    return data_words + 2


def message_time_us(kind, data_words):
    """Bus time in microseconds for one message: wire words times slot."""
    return float(wire_words(kind, data_words)) * WORD_SLOT_US


def _schedule_total_us(messages):
    """Sum of per-message bus times for a schedule of (kind, data_words)."""
    if not messages:
        raise ValueError("schedule is empty, nothing to load")
    return sum(message_time_us(kind, words) for kind, words in messages)


def schedule_utilization(messages, frame_us=FRAME_US_DEFAULT):
    """Utilization of a minor frame by a message schedule.

    messages is a list of (kind, data_words) pairs. frame_us is the
    minor-frame length in microseconds (default 5000 us). Returns a dict
    with keys total_us, utilization_fraction, utilization_pct, budget_us,
    headroom_us, headroom_pct and verdict. The budget is 80 percent of
    the frame; verdict is FITS when the total fits within the budget and
    OVER otherwise.
    """
    if frame_us <= 0:
        raise ValueError("frame_us must be positive")
    total_us = _schedule_total_us(messages)
    budget_us = LOAD_BUDGET_FRACTION * frame_us
    utilization_fraction = total_us / frame_us
    headroom_us = budget_us - total_us
    verdict = "FITS" if total_us <= budget_us else "OVER"
    return {
        "total_us": total_us,
        "utilization_fraction": utilization_fraction,
        "utilization_pct": utilization_fraction * 100.0,
        "budget_us": budget_us,
        "headroom_us": headroom_us,
        "headroom_pct": headroom_us / frame_us * 100.0,
        "verdict": verdict,
    }


def schedule_headroom(messages, frame_us=FRAME_US_DEFAULT):
    """Percent headroom to the 80 percent budget, negative when OVER."""
    if frame_us <= 0:
        raise ValueError("frame_us must be positive")
    total_us = _schedule_total_us(messages)
    budget_us = LOAD_BUDGET_FRACTION * frame_us
    return (budget_us - total_us) / frame_us * 100.0
