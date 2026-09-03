"""DO-160 section 21 radio frequency emission (RF emissions) math.

Deterministic, offline, stdlib-only helpers for planning and checking the
equipment emission side of DO-160 (RTCA DO-160, EUROCAE twin ED-14)
section 21: conducted emissions CE102 and radiated emissions RE102.
Covers dBuV and dBuV/m unit conversion, the simplified reference-only
typical limit curves (piecewise constant CE102 band model, category
floors for RE102), emission margin at each frequency, worst case
frequency selection, the pass or fail verdict, and an inverse-square
far-field sanity check of a characterized radiating source via ERP.
All units are SI: voltage in V, field in V/m, frequency in Hz, ERP in W,
distance in m.

Summary reference only. The CE102 and RE102 limit curves here are
representative typical values, clearly NOT the normative RTCA table:
the normative limits come from the current DO-160 revision and must be
verified against it before any qualification decision (standards-map.yaml
brief 06).

Modeling assumptions (recorded per the wave-25 spec): the simplified
CE102 curve is applied for every supported installation category (the
published curve is a single band curve; the category argument is still
validated and carried through for installation classification), and the
RE102 category floors A 24, B 34, C 44 dBuV/m are representative
reference-only values applied across the 2 MHz to 18 GHz test band.

Contract exercised by scripts/test_radio_frequency_emissions.py.
"""

import math

MICRO = 1e-6

# CE102 test band, Hz (10 kHz to 10 MHz).
CE102_BAND_LO_HZ = 10e3
CE102_BAND_HI_HZ = 10e6

# Simplified CE102 reference-only typical limit, dBuV, piecewise constant
# bands: 10 kHz to 100 kHz 78 dBuV, 100 kHz to 2 MHz 60 dBuV,
# 2 MHz to 10 MHz 70 dBuV. Reference-only, NOT the normative RTCA curve.
_CE102_BAND_LIMITS_DBU_V = (
    (10e3, 100e3, 78.0),
    (100e3, 2e6, 60.0),
    (2e6, 10e6, 70.0),
)

# RE102 test band, Hz (2 MHz to 18 GHz).
RE102_BAND_LO_HZ = 2e6
RE102_BAND_HI_HZ = 18e9

# Reference-only typical RE102 category floors, dBuV/m. Category A is the
# strictest installation (24 dBuV/m floor), adjacent categories differ by
# 10 dBuV/m. Representative values only, NOT the normative RTCA table.
_RE102_FLOOR_DBU_VPM = {"A": 24.0, "B": 34.0, "C": 44.0}

SUPPORTED_CATEGORIES = frozenset(_RE102_FLOOR_DBU_VPM)

# Accepted kind labels for emission_verdict, canonicalized internally.
_CONDUCTED_KINDS = frozenset(("conducted", "ce102"))
_RADIATED_KINDS = frozenset(("radiated", "re102"))


def _validate_frequency(freq_hz):
    """Raise ValueError unless freq_hz is a finite positive frequency."""
    if not math.isfinite(freq_hz):
        raise ValueError("frequency must be finite, got %r" % (freq_hz,))
    if freq_hz <= 0:
        raise ValueError("frequency must be > 0, got %r" % (freq_hz,))


def _validate_category(category):
    """Return the uppercased category, raising ValueError if unsupported."""
    key = str(category).upper()
    if key not in SUPPORTED_CATEGORIES:
        raise ValueError(
            "category must be one of %s, got %r"
            % (sorted(SUPPORTED_CATEGORIES), category)
        )
    return key


def dbu_v_from_volts(volts):
    """Return the conducted emission level in dBuV for a voltage in V.

    dBuV = 20 * log10(V_uV) with V_uV = volts * 1e6. Anchor: 1 V is
    120 dBuV, 1 mV is 60 dBuV, 1 uV is 0 dBuV.

    Raises ValueError for a negative or zero amplitude.
    """
    if volts < 0:
        raise ValueError("amplitude must be >= 0, got %r" % (volts,))
    if volts == 0:
        raise ValueError("amplitude must be > 0 to express in dBuV, got 0")
    return 20.0 * math.log10(volts / MICRO)


def volts_from_dbu_v(dbu_v):
    """Return the amplitude in V for a conducted emission level in dBuV.

    V = 10 ** (dbu_v / 20) * 1e-6. Anchor: 120 dBuV is 1 V, 0 dBuV is
    1 uV. Any dB level (including negative) is physical.
    """
    return 10.0 ** (dbu_v / 20.0) * MICRO


def dbu_v_per_m_from_v_per_m(volts_per_m):
    """Return the radiated field level in dBuV/m for a field in V/m.

    dBuV/m = 20 * log10(E_uV/m) with E_uV/m = volts_per_m * 1e6.
    Anchor: 1 V/m is 120 dBuV/m, 1 uV/m is 0 dBuV/m.

    Raises ValueError for a negative or zero field.
    """
    if volts_per_m < 0:
        raise ValueError("field must be >= 0, got %r" % (volts_per_m,))
    if volts_per_m == 0:
        raise ValueError("field must be > 0 to express in dBuV/m, got 0")
    return 20.0 * math.log10(volts_per_m / MICRO)


def ce102_limit_db(freq_hz, category):
    """Return the CE102 conducted emission limit in dBuV at a frequency.

    Reference-only typical piecewise constant band model over 10 kHz to
    10 MHz: 78 dBuV below 100 kHz, 60 dBuV from 100 kHz to 2 MHz,
    70 dBuV above 2 MHz. Band edges: 100 kHz sits in the middle band and
    2 MHz in the top band. The category is validated and carried through
    for installation classification but does not shift this simplified
    curve. Anchor: 150 kHz gives 60 dBuV.

    Raises ValueError for a frequency outside 10 kHz to 10 MHz, for a
    non-positive frequency, or for an unsupported category.
    """
    key = _validate_category(category)
    _validate_frequency(freq_hz)
    if freq_hz < CE102_BAND_LO_HZ or freq_hz > CE102_BAND_HI_HZ:
        raise ValueError(
            "CE102 limit band is 10 kHz to 10 MHz, got %r Hz" % (freq_hz,)
        )
    for lo_hz, hi_hz, limit_dbu_v in _CE102_BAND_LIMITS_DBU_V:
        if freq_hz < hi_hz:
            return limit_dbu_v
    return _CE102_BAND_LIMITS_DBU_V[-1][2]


def re102_limit_db(freq_hz, category):
    """Return the RE102 radiated emission limit in dBuV/m at a frequency.

    Reference-only typical category floor model over 2 MHz to 18 GHz:
    category A 24 dBuV/m, B 34 dBuV/m, C 44 dBuV/m. Anchor: category A
    at 100 MHz gives 24 dBuV/m.

    Raises ValueError for a frequency outside 2 MHz to 18 GHz, for a
    non-positive frequency, or for an unsupported category.
    """
    key = _validate_category(category)
    _validate_frequency(freq_hz)
    if freq_hz < RE102_BAND_LO_HZ or freq_hz > RE102_BAND_HI_HZ:
        raise ValueError(
            "RE102 limit band is 2 MHz to 18 GHz, got %r Hz" % (freq_hz,)
        )
    return _RE102_FLOOR_DBU_VPM[key]


def _margin_db(measured_db, limit_db):
    """Return limit_db - measured_db, rejecting non-finite dB levels."""
    if not math.isfinite(measured_db):
        raise ValueError("measured level must be finite, got %r" % (measured_db,))
    if not math.isfinite(limit_db):
        raise ValueError("limit level must be finite, got %r" % (limit_db,))
    return limit_db - measured_db


def conducted_emission_margin(measured_dbu_v, limit_dbu_v):
    """Return the CE102 conducted emission margin in dB.

    margin_db = limit_db - measured_db at one frequency; a negative
    margin is a fail against the CE102 limit curve. Negative dB levels
    are physical (sub-microvolt amplitudes), so only non-finite levels
    are rejected.
    """
    return _margin_db(measured_dbu_v, limit_dbu_v)


def radiated_emission_margin(measured_dbu_vpm, limit_dbu_vpm):
    """Return the RE102 radiated emission margin in dB.

    margin_db = limit_db - measured_db at one frequency; a negative
    margin is a fail against the RE102 limit curve. Negative dB levels
    are physical (sub-microvolt-per-meter fields), so only non-finite
    levels are rejected.
    """
    return _margin_db(measured_dbu_vpm, limit_dbu_vpm)


def worst_case_frequency(freqs, margins):
    """Return (frequency, margin) of the minimum margin over a sweep.

    The worst case is the frequency carrying the most negative (or
    smallest positive) emission margin. Ties resolve to the first
    occurrence in the sweep order. Anchors: margins (18, -12, 2) dB at
    (50 kHz, 150 kHz, 5 MHz) give (150 kHz, -12 dB).

    Raises ValueError for empty arrays, mismatched lengths, non-positive
    frequencies, or non-finite levels.
    """
    if len(freqs) == 0 or len(margins) == 0:
        raise ValueError("frequency and margin arrays must not be empty")
    if len(freqs) != len(margins):
        raise ValueError(
            "frequency and margin arrays must match, got %d and %d"
            % (len(freqs), len(margins))
        )
    for freq_hz in freqs:
        _validate_frequency(freq_hz)
    for margin_db in margins:
        if not math.isfinite(margin_db):
            raise ValueError("margin must be finite, got %r" % (margin_db,))
    idx = min(range(len(margins)), key=margins.__getitem__)
    return freqs[idx], margins[idx]


def _canonicalize_kind(kind):
    """Return 'CE102' or 'RE102' for an accepted kind label."""
    key = str(kind).lower()
    if key in _CONDUCTED_KINDS:
        return "CE102"
    if key in _RADIATED_KINDS:
        return "RE102"
    raise ValueError(
        "kind must be one of conducted, CE102, radiated, RE102, got %r"
        % (kind,)
    )


def emission_verdict(margins, freq_hz, category, kind):
    """Return the pass or fail emission verdict dict for a sweep.

    Accepts a single measurement (scalar margin and frequency) or equal
    length sweeps. Verdict: pass when the minimum margin is >= 0 dB, with
    the worst margin, the worst case frequency, and the equipment
    category. kind selects the emission side: 'conducted' or 'CE102' for
    the conducted emission sweep, 'radiated' or 'RE102' for the radiated
    emission sweep (case insensitive).

    Raises ValueError for empty or mismatched arrays, non-positive
    frequencies, unsupported categories, or unknown kinds.
    """
    key = _validate_category(category)
    kind_key = _canonicalize_kind(kind)
    margin_scalar = isinstance(margins, (int, float))
    freq_scalar = isinstance(freq_hz, (int, float))
    if margin_scalar != freq_scalar:
        raise ValueError(
            "margin and frequency inputs must both be scalar or both be sequences"
        )
    if margin_scalar:
        margin_list = [margins]
        freq_list = [freq_hz]
    else:
        margin_list = list(margins)
        freq_list = list(freq_hz)
    if len(margin_list) != len(freq_list):
        raise ValueError(
            "margin and frequency sequences must match, got %d and %d"
            % (len(margin_list), len(freq_list))
        )
    worst_freq, worst_margin = worst_case_frequency(freq_list, margin_list)
    return {
        "pass": worst_margin >= 0.0,
        "worst_margin_db": worst_margin,
        "worst_frequency_hz": worst_freq,
        "category": key,
        "kind": kind_key,
    }


def field_strength_from_erp(erp_w, distance_m):
    """Return the far-field strength E in V/m for a source ERP in W.

    E = sqrt(30 * P_erp) / d, the free-space inverse-square far-field
    relation. Used as a sanity check of a characterized radiating source
    on the emission side (convert the result with
    dbu_v_per_m_from_v_per_m to compare against RE102), not to size an
    immunity amplifier. Anchor: 100 W ERP at 10 m gives about 5.477 V/m
    (about 134.77 dBuV/m).

    Raises ValueError for negative ERP or non-positive distance.
    """
    if erp_w < 0:
        raise ValueError("ERP must be >= 0, got %r" % (erp_w,))
    if distance_m <= 0:
        raise ValueError("distance must be > 0, got %r" % (distance_m,))
    return math.sqrt(30.0 * erp_w) / distance_m
