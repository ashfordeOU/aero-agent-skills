#!/usr/bin/env python3
"""DO-160 environmental qualification logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, do-160: gated):
DO-160G (RTCA, EUROCAE twin ED-14G) defines environmental test
conditions and procedures for airborne equipment, organized by
numbered sections (temperature and altitude, temperature variation,
humidity, shocks, vibration, explosion proofness, waterproofness,
fluids, power input, EMC/induced/RF/emission, lightning, icing, ESD).
Equipment categories carry typical operating temperature ranges.
Category-specific section exclusions must be confirmed against the
current revision of the standard.
"""

SECTIONS = {
    4: "Temperature and altitude",
    5: "Temperature variation",
    6: "Humidity",
    7: "Operational shocks and crash safety",
    8: "Vibration",
    9: "Explosion proofness",
    10: "Waterproofness",
    11: "Fluids susceptibility",
    16: "Power input",
    19: "Induced signal susceptibility",
    20: "Radio frequency susceptibility",
    21: "Emission of radio frequency energy",
    22: "Lightning induced transient susceptibility",
    23: "Lightning direct effects",
    24: "Icing",
    25: "Electrostatic discharge",
}

# Typical operating temperature ranges (deg C) per equipment category,
# (lo, hi). Typical values -- verify against the current revision.
TEMPERATURE_RANGES = {
    "A1": (-55, 70),
    "A2": (-55, 70),
    "B1": (-55, 55),
    "B2": (-55, 70),
    "C1": (-55, 70),
    "C2": (-55, 70),
    "D1": (-55, 55),
    "D2": (-55, 70),
}


def section_name(section_id):
    """DO-160 test-condition section name for a section number."""
    if section_id not in SECTIONS:
        raise ValueError("unknown DO-160 section: %r" % (section_id,))
    return SECTIONS[section_id]


def required_sections(category):
    """Required DO-160 sections for an equipment category: the full set
    of test-condition sections. Category-specific exclusions must be
    confirmed against the current revision of the standard."""
    return sorted(SECTIONS)


def matrix_complete(planned_sections, category):
    """(missing, ok) for a planned test matrix: missing lists the
    required sections not planned; ok is True when nothing is missing.
    Raises ValueError on an unknown planned section id."""
    unknown = [s for s in planned_sections if s not in SECTIONS]
    if unknown:
        raise ValueError(
            "unknown planned section id(s): %r" % (sorted(unknown),)
        )
    required = required_sections(category)
    missing = [s for s in required if s not in planned_sections]
    return (missing, not missing)


def temperature_category_range(category):
    """Typical operating temperature range (deg C) (lo, hi) for a DO-160
    equipment category. Typical values; verify against the current
    revision (e.g. DO-160G) before use."""
    if category not in TEMPERATURE_RANGES:
        raise ValueError("unknown equipment category: %r" % (category,))
    return TEMPERATURE_RANGES[category]


def temp_within_range(temp_c, category):
    """True when the temperature (deg C) lies within the category's
    typical operating range, inclusive."""
    lo, hi = temperature_category_range(category)
    return lo <= temp_c <= hi
