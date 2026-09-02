#!/usr/bin/env python3
"""Widespread fatigue damage (WFD) screening logic (stdlib only).

Implements the screening ideas of FAR 25.571(b)/(c) for transport
airplane structure: classify damage as multiple site damage (MSD,
cracks at adjacent fastener holes of one element) or multiple element
damage (MED, cracks in adjacent load-path elements), run the MSD
susceptibility screening over a set of site crack lengths against a
threshold, and flag when a supplemental inspection applies to fatigue
critical baseline structure. Paraphrase of the WFD methodology; FAR 25
is public-domain regulation and CS-25 is free-download, both
referenced by id only (standards-map.yaml). No single-crack growth
mechanics here: this is the site-population screen.

Conventions: a site is one fastener hole with a detected crack length
in consistent units (for example mm). Sites strictly above the
screening threshold are counted; the verdict is "susceptible" when at
least two sites exceed the threshold, because MSD means a population
of cracked adjacent sites, not a single worst site. MED is declared
from the count of cracked load-path elements. The supplemental
inspection flag follows the certification date threshold: fatigue
critical baseline structure that screens susceptible, or that lacks
demonstrated WFD resistance, needs supplemental inspections (for
example the SID/SLWFD program).
"""


def classify_damage(site_cracks, element_cracks):
    """Classify MSD vs MED from cracked-site and cracked-element counts.

    MSD (multiple site damage) needs at least 2 cracked sites, MED
    (multiple element damage) needs at least 2 cracked load-path
    elements. Returns 'msd', 'med', 'msd+med', or 'none'. Raises
    ValueError on negative counts.
    """
    if site_cracks < 0 or element_cracks < 0:
        raise ValueError(
            "counts cannot be negative: site_cracks=%r element_cracks=%r"
            % (site_cracks, element_cracks)
        )
    msd = site_cracks >= 2
    med = element_cracks >= 2
    if msd and med:
        return "msd+med"
    if msd:
        return "msd"
    if med:
        return "med"
    return "none"


def screen_msd(crack_lengths, threshold):
    """MSD susceptibility screening over site crack lengths.

    Counts the sites whose crack length is strictly above the
    threshold; the verdict is 'susceptible' when at least 2 sites
    exceed it, else 'not-susceptible'. Returns a dict with
    total_sites, sites_exceeding, threshold, and verdict. Raises
    ValueError on a non-positive threshold or a negative crack length.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive: got %r" % (threshold,))
    for length in crack_lengths:
        if length < 0:
            raise ValueError("crack length cannot be negative: got %r" % (length,))
    exceeding = sum(1 for length in crack_lengths if length > threshold)
    return {
        "total_sites": len(crack_lengths),
        "sites_exceeding": exceeding,
        "threshold": threshold,
        "verdict": "susceptible" if exceeding >= 2 else "not-susceptible",
    }


def supplemental_inspection_required(verdict, fatigue_critical_baseline,
                                     wfd_resistance_shown):
    """Supplemental inspection flag for fatigue critical baseline structure.

    Required when the structure is fatigue critical baseline and either
    the MSD screen verdict is 'susceptible' or WFD resistance has not
    been shown for the certification date threshold (FAR 25.571).
    Non-baseline structure never triggers the flag. Returns bool.
    """
    if not fatigue_critical_baseline:
        return False
    if verdict == "susceptible":
        return True
    return not wfd_resistance_shown


def wfd_screen_report(site_crack_lengths, element_cracks, threshold,
                      fatigue_critical_baseline, wfd_resistance_shown):
    """One-shot WFD screen: classification, susceptibility, inspection flag.

    site_crack_lengths is the list of detected crack lengths at the
    adjacent fastener-hole sites; element_cracks is the count of
    cracked load-path elements. Returns a dict with classification,
    site_cracks, element_cracks, sites_exceeding, verdict, and
    supplemental_inspection_required.
    """
    classification = classify_damage(len(site_crack_lengths), element_cracks)
    screen = screen_msd(site_crack_lengths, threshold)
    return {
        "classification": classification,
        "site_cracks": len(site_crack_lengths),
        "element_cracks": element_cracks,
        "sites_exceeding": screen["sites_exceeding"],
        "verdict": screen["verdict"],
        "supplemental_inspection_required": supplemental_inspection_required(
            screen["verdict"], fatigue_critical_baseline, wfd_resistance_shown
        ),
    }
