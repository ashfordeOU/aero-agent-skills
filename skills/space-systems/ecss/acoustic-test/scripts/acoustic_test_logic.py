#!/usr/bin/env python3
"""ECSS-E-ST-32C clause 4.6.3.10 acoustic test of structure
(paraphrase, not copy).

Common-knowledge summary: the structures mechanical testing standard's
acoustic test clause covers vibro-acoustic verification of spacecraft
structures exposed to the launch acoustic environment. A test spectrum
is defined in 1/3-octave bands across a frequency range of at least
31.5 Hz to 10 000 Hz; the qualification spectrum is derived from the
acceptance spectrum by adding a qualification margin per band; the
Overall Sound Pressure Level (OASPL) is the power sum of all band
levels; each test category (qualification, acceptance, protoflight)
carries a minimum test duration; and the measured test spectrum is
checked against the required spectrum within a per-band level
tolerance. This module implements SPL-to-pressure conversion, OASPL
computation by power summation, qualification margin application,
frequency range coverage checking, test duration checking, band-by-band
spectrum compliance, and a full acoustic test review function. It does
not define the source acoustic environment or structural response models.
"""

import math

P_REF_PA = 20e-6  # reference pressure 20 μPa per standard acoustics

QUALIFICATION_MARGIN_DB = 3.0  # per-band dB margin added to acceptance levels

MIN_DURATION_S = {
    "qualification": 120,
    "acceptance": 60,
    "protoflight": 120,
}

FREQ_RANGE_MIN_HZ = 31.5
FREQ_RANGE_MAX_HZ = 10000.0

TEST_CATEGORIES = frozenset({"qualification", "acceptance", "protoflight"})

DEFAULT_LEVEL_TOLERANCE_DB = 1.0


def spl_to_pressure(spl_db):
    """Convert a Sound Pressure Level (dB re 20 μPa) to RMS pressure (Pa).
    Raises ValueError for a non-finite input."""
    if not math.isfinite(spl_db):
        raise ValueError("spl_db must be finite, got %r" % (spl_db,))
    return P_REF_PA * 10.0 ** (spl_db / 20.0)


def pressure_to_spl(pressure_pa):
    """Convert an RMS pressure (Pa) to Sound Pressure Level in dB (re 20 μPa).
    Raises ValueError for a non-positive or non-finite pressure."""
    if not math.isfinite(pressure_pa) or pressure_pa <= 0:
        raise ValueError(
            "pressure_pa must be finite and positive, got %r" % (pressure_pa,)
        )
    return 20.0 * math.log10(pressure_pa / P_REF_PA)


def compute_oaspl(band_levels_db):
    """Compute the Overall Sound Pressure Level (dB) by power-summing a
    sequence of 1/3-octave band SPL values (dB re 20 μPa). Two equal-level
    bands produce an OASPL 10*log10(2) = 3.0103 dB above either band (the
    familiar "+3 dB" is a rounding of that figure).
    Raises ValueError for an empty sequence or any non-finite band level."""
    if not band_levels_db:
        raise ValueError("band_levels_db must contain at least one value")
    total_p_sq = 0.0
    for level in band_levels_db:
        if not math.isfinite(level):
            raise ValueError("band level must be finite, got %r" % (level,))
        p = spl_to_pressure(level)
        total_p_sq += p * p
    return pressure_to_spl(math.sqrt(total_p_sq))


def apply_qualification_margin(acceptance_levels_db, margin_db=QUALIFICATION_MARGIN_DB):
    """Return a new list of qualification-level SPL values by adding margin_db
    to each acceptance-level band. Does not mutate the input.
    Raises ValueError for a non-positive margin."""
    if margin_db <= 0:
        raise ValueError("margin_db must be positive, got %r" % (margin_db,))
    return [level + margin_db for level in acceptance_levels_db]


def categorize_test(test_type):
    """Return test_type if it is a recognized acoustic test category:
    'qualification', 'acceptance', or 'protoflight'.
    Raises ValueError for an unrecognized type."""
    if test_type not in TEST_CATEGORIES:
        raise ValueError(
            "unrecognized acoustic test category %r; expected one of %s"
            % (test_type, sorted(TEST_CATEGORIES))
        )
    return test_type


def check_frequency_coverage(band_center_freqs_hz):
    """Verify the list of band centre frequencies covers the required acoustic
    test range [FREQ_RANGE_MIN_HZ, FREQ_RANGE_MAX_HZ]. Returns a list of
    finding dicts (empty when coverage is adequate).
    Raises ValueError for an empty frequency list."""
    if not band_center_freqs_hz:
        raise ValueError("band_center_freqs_hz must contain at least one entry")
    findings = []
    lo = min(band_center_freqs_hz)
    hi = max(band_center_freqs_hz)
    if lo > FREQ_RANGE_MIN_HZ:
        findings.append(
            {
                "issue": "low_frequency_coverage_gap",
                "lowest_band_hz": lo,
                "required_min_hz": FREQ_RANGE_MIN_HZ,
            }
        )
    if hi < FREQ_RANGE_MAX_HZ:
        findings.append(
            {
                "issue": "high_frequency_coverage_gap",
                "highest_band_hz": hi,
                "required_max_hz": FREQ_RANGE_MAX_HZ,
            }
        )
    return findings


def check_test_duration(duration_s, test_type):
    """Verify duration_s meets the minimum for test_type. Returns a list with
    one finding dict if deficient, otherwise empty.
    Raises ValueError for a negative duration or unrecognized test_type."""
    if duration_s < 0:
        raise ValueError("duration_s must be >= 0, got %r" % (duration_s,))
    categorize_test(test_type)
    minimum = MIN_DURATION_S[test_type]
    if duration_s < minimum:
        return [
            {
                "issue": "test_duration_below_minimum",
                "test_type": test_type,
                "duration_s": duration_s,
                "minimum_s": minimum,
            }
        ]
    return []


def check_spectrum_compliance(
    measured_levels_db,
    required_levels_db,
    tolerance_db=DEFAULT_LEVEL_TOLERANCE_DB,
):
    """Check measured 1/3-octave band levels against required levels within
    tolerance_db. Returns a list of band finding dicts for any band where
    measured < required - tolerance_db (underdrive) or
    measured > required + tolerance_db (overdrive).
    Raises ValueError for mismatched list lengths or non-positive tolerance."""
    if tolerance_db <= 0:
        raise ValueError("tolerance_db must be positive, got %r" % (tolerance_db,))
    if len(measured_levels_db) != len(required_levels_db):
        raise ValueError(
            "measured_levels_db and required_levels_db must have the same length"
        )
    findings = []
    for i, (meas, req) in enumerate(zip(measured_levels_db, required_levels_db)):
        if meas < req - tolerance_db:
            findings.append(
                {
                    "issue": "spectrum_underdrive",
                    "band_index": i,
                    "measured_db": meas,
                    "required_db": req,
                    "tolerance_db": tolerance_db,
                }
            )
        elif meas > req + tolerance_db:
            findings.append(
                {
                    "issue": "spectrum_overdrive",
                    "band_index": i,
                    "measured_db": meas,
                    "required_db": req,
                    "tolerance_db": tolerance_db,
                }
            )
    return findings


def acoustic_test_review(test_record):
    """Full ECSS-E-ST-32C clause 4.6.3.10 acoustic test review for one run.

    test_record keys:
      "test_type"           : str  — "qualification"|"acceptance"|"protoflight"
      "duration_s"          : float
      "band_center_freqs_hz": list[float]
      "required_levels_db"  : list[float]
      "measured_levels_db"  : list[float]
      "tolerance_db"        : float  (optional, default DEFAULT_LEVEL_TOLERANCE_DB)

    Returns:
      {
        "test_type"        : str,
        "oaspl_required_db": float,
        "oaspl_measured_db": float,
        "findings": {
          "duration"           : [...],
          "frequency_coverage" : [...],
          "spectrum"           : [...],
        }
      }

    Raises ValueError for an unrecognized test_type or mismatched list lengths.
    """
    test_type = categorize_test(test_record["test_type"])
    duration_s = test_record["duration_s"]
    band_freqs = test_record["band_center_freqs_hz"]
    required = test_record["required_levels_db"]
    measured = test_record["measured_levels_db"]
    tolerance = test_record.get("tolerance_db", DEFAULT_LEVEL_TOLERANCE_DB)

    return {
        "test_type": test_type,
        "oaspl_required_db": compute_oaspl(required),
        "oaspl_measured_db": compute_oaspl(measured),
        "findings": {
            "duration": check_test_duration(duration_s, test_type),
            "frequency_coverage": check_frequency_coverage(band_freqs),
            "spectrum": check_spectrum_compliance(measured, required, tolerance),
        },
    }


def is_acoustic_test_compliant(review):
    """True when every finding list in an acoustic_test_review result is
    empty — the test satisfies clause 4.6.3.10 for this assessment."""
    return all(len(v) == 0 for v in review["findings"].values())
