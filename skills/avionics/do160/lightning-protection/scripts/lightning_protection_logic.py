#!/usr/bin/env python3
"""DO-160 lightning protection logic (paraphrase, summary only).

Common-knowledge summary (standards-map.yaml, do-160: proprietary
RTCA, summary-only): DO-160 section 22 covers induced transient
susceptibility to lightning and section 23 covers lightning direct
effects. Equipment is tested at a selected test level (1-5) with a
selected waveform set (A-H); the pass verdict requires no physical
damage, no upset, and no latch-up. The actual level and waveform
tables are standard data and must be read from the current
revision; this module only validates inputs and classifies the
verdict. No standard tables are reproduced here.
"""


def test_level_in_range(level):
    """True when level is an int in the defined 1-5 range.

    Raises ValueError when level is not an int.
    """
    if not isinstance(level, int):
        raise ValueError("test level must be an int, got %r" % (level,))
    return 1 <= level <= 5


def waveform_supported(waveform):
    """True when waveform is a supported set letter A-H (case-insensitive).

    Raises ValueError when waveform is not a str.
    """
    if not isinstance(waveform, str):
        raise ValueError("waveform must be a str, got %r" % (waveform,))
    return waveform.upper() in {"A", "B", "C", "D", "E", "F", "G", "H"}


def pass_verdict(physical_damage, upset, latch_up):
    """True (pass) only when all three flags are False.

    Raises ValueError when any argument is not a bool.
    """
    for flag in (physical_damage, upset, latch_up):
        if not isinstance(flag, bool):
            raise ValueError("verdict flags must be bool, got %r" % (flag,))
    return not physical_damage and not upset and not latch_up
