#!/usr/bin/env python3
"""ECSS-E-ST-10-04C Annex B.7 solar energetic ion spectra (heavy ions,
Z-dependent abundances) for single-event-effects (SEE) analysis
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex
B.7 characterizes the heavy-ion (Z > 2) content of the solar energetic
particle (SEP) worst-case environment used for SEE analyses, given as
an element-by-element differential energy spectrum. Because a
first-principles spectrum for every element is impractical, per-species
spectra are conventionally derived by scaling a reference element's
(oxygen, Z=8) measured/modeled differential flux spectrum by that
element's abundance ratio relative to the reference element. Abundance
ratios differ sharply between SEP event classes: "gradual"
(shock-associated) events carry roughly average solar/coronal
composition, while "impulsive" (flare-associated) events are strongly
enhanced in heavy ions -- especially iron -- as summarized by the
iron-to-oxygen (Fe/O) abundance ratio. This module implements event-type
classification from Fe/O ratio, abundance-table lookup and per-species
spectrum scaling, and the heavy-ion species-coverage and worst-case
event-classification checks for an SEE case; it does not implement LET
calculation from an ion spectrum or shielding/path-length effects, and
the embedded abundance ratios are representative engineering
placeholders, not a transcription of a specific measured event.
"""

REFERENCE_SPECIES_Z = 8  # oxygen

# Minimum heavy-ion species coverage an SEE analysis needs: through the
# iron group (nickel, Z=28). Truncating below this discards ions that
# can dominate the single-event rate for high-LET-sensitive parts.
MIN_SPECIES_MAX_Z_SEE = 28

# Fe/O abundance-ratio thresholds (by particle number, relative to
# oxygen = 1.0) discriminating SEP event classes. At or below the
# gradual threshold the event carries roughly average solar/coronal
# composition; at or above the impulsive threshold it is Fe-enhanced.
FE_O_RATIO_GRADUAL_THRESHOLD = 0.1
FE_O_RATIO_IMPULSIVE_THRESHOLD = 1.0

EVENT_TYPES = frozenset({"gradual", "impulsive", "mixed"})

# Elemental abundance ratios relative to oxygen (O=1.0), representative
# engineering placeholders calibrated to the published sense of gradual
# vs. impulsive SEP composition (impulsive events markedly Fe-enhanced
# relative to gradual events) -- not a transcription of a measured
# event's coefficients. For mission-grade analysis, replace these
# tables with a vetted source (e.g. a CREME96/SEPEM-class abundance
# table or a mission-specific measured event) keeping the same lookup
# interface (abundance_ratio, scale_element_spectrum).
GRADUAL_ABUNDANCE_BY_Z = {
    1: 50.0,   # H
    2: 5.0,    # He
    6: 0.5,    # C
    7: 0.15,   # N
    8: 1.0,    # O (reference)
    10: 0.15,  # Ne
    12: 0.2,   # Mg
    14: 0.15,  # Si
    26: 0.1,   # Fe
}
IMPULSIVE_ABUNDANCE_BY_Z = {
    1: 10.0,
    2: 3.0,
    6: 0.5,
    7: 0.15,
    8: 1.0,
    10: 0.3,
    12: 0.5,
    14: 0.4,
    26: 1.0,
}


def classify_event_type(fe_o_ratio):
    """SEP event type from its Fe/O abundance ratio: "gradual" at or
    below FE_O_RATIO_GRADUAL_THRESHOLD, "impulsive" at or above
    FE_O_RATIO_IMPULSIVE_THRESHOLD, otherwise "mixed". Raises
    ValueError for a negative ratio."""
    if fe_o_ratio < 0:
        raise ValueError("fe_o_ratio must be >= 0")
    if fe_o_ratio <= FE_O_RATIO_GRADUAL_THRESHOLD:
        return "gradual"
    if fe_o_ratio >= FE_O_RATIO_IMPULSIVE_THRESHOLD:
        return "impulsive"
    return "mixed"


def _lookup_abundance(table, species_z):
    if species_z not in table:
        raise ValueError(
            "species Z=%r not in Annex B.7 abundance table catalog" % (species_z,)
        )
    return table[species_z]


def abundance_ratio(species_z, event_type):
    """Abundance ratio of species_z relative to the reference element
    (oxygen) for the given event_type. "mixed" returns the conservative
    envelope (max) of the gradual and impulsive ratios. Raises
    ValueError for an unrecognized event_type or a species_z absent
    from the abundance tables."""
    if event_type not in EVENT_TYPES:
        raise ValueError("unrecognized event type %r" % (event_type,))
    if event_type == "mixed":
        gradual = _lookup_abundance(GRADUAL_ABUNDANCE_BY_Z, species_z)
        impulsive = _lookup_abundance(IMPULSIVE_ABUNDANCE_BY_Z, species_z)
        return max(gradual, impulsive)
    table = (
        GRADUAL_ABUNDANCE_BY_Z if event_type == "gradual" else IMPULSIVE_ABUNDANCE_BY_Z
    )
    return _lookup_abundance(table, species_z)


def scale_element_spectrum(reference_flux, species_z, event_type):
    """Differential flux for species_z at one energy point: the
    reference element's (oxygen) differential flux at that energy times
    the species' abundance ratio for event_type. Raises ValueError for
    a negative reference_flux."""
    if reference_flux < 0:
        raise ValueError("reference_flux must be >= 0")
    return reference_flux * abundance_ratio(species_z, event_type)


def build_heavy_ion_spectra(reference_spectrum, species_list, event_type):
    """Per-species differential flux spectrum dict {species_z: [flux,
    ...]} built by scaling every point of reference_spectrum (an
    iterable of reference-element differential flux values) by each
    species' abundance ratio for event_type. Does not mutate
    reference_spectrum."""
    return {
        species_z: [
            scale_element_spectrum(flux, species_z, event_type)
            for flux in reference_spectrum
        ]
        for species_z in species_list
    }


def species_coverage_violations(case_id, species_max_z):
    """Violation list (empty if compliant) for heavy-ion species
    coverage on one SEE case. Raises ValueError for a negative
    species_max_z."""
    if species_max_z < 0:
        raise ValueError("species_max_z must be >= 0")
    if species_max_z < MIN_SPECIES_MAX_Z_SEE:
        return [
            {
                "issue": "insufficient_heavy_ion_species_coverage",
                "case": case_id,
                "species_max_z": species_max_z,
                "required_species_max_z": MIN_SPECIES_MAX_Z_SEE,
            }
        ]
    return []


def event_class_violations(case_id, event_type):
    """Violation list (empty if compliant) for the worst-case event
    classification on one SEE case. Only "impulsive" or "mixed" satisfy
    the SEE worst-case requirement; "gradual" alone understates
    heavy-ion fluence. Raises ValueError for an unrecognized
    event_type."""
    if event_type not in EVENT_TYPES:
        raise ValueError("unrecognized event type %r" % (event_type,))
    if event_type == "gradual":
        return [
            {
                "issue": "gradual_event_insufficient_for_see_worst_case",
                "case": case_id,
                "event_type": event_type,
            }
        ]
    return []


def annex_b7_review(case):
    """Full Annex B.7 review for one SEE case.

    case: {"case_id": str, "species_max_z": int, "fe_o_ratio": float}.
    Determines the case's event type from fe_o_ratio internally.
    Returns {"species": [...], "event_class": [...], "event_type":
    str}, the first two each a violation list. Raises ValueError for a
    negative fe_o_ratio or species_max_z."""
    case_id = case["case_id"]
    event_type = classify_event_type(case["fe_o_ratio"])
    return {
        "species": species_coverage_violations(case_id, case["species_max_z"]),
        "event_class": event_class_violations(case_id, event_type),
        "event_type": event_type,
    }


def is_annex_b7_compliant(review):
    """True when both violation categories in an annex_b7_review result
    are empty -- the case satisfies Annex B.7 for this SEE
    assessment."""
    return len(review["species"]) == 0 and len(review["event_class"]) == 0
