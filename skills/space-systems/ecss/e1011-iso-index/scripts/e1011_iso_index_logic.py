#!/usr/bin/env python3
"""ECSS-E-ST-10-11C Annex E (informative) — HFE ISO and European standards index.
(paraphrase, not copy)

Common-knowledge summary (standards-map.yaml, ecss: gated false): Annex E of
the ECSS human factors engineering standard lists related ISO and European
standards as informative supporting references, grouped by HFE topic area.
The principal standard families cover ergonomics of human-system interaction
(ISO 9241 series), ergonomic design of control centres (ISO 11064),
anthropometric workstation requirements (ISO 14738), ergonomic principles
for mental workload (ISO 10075), thermal stress (ISO 7933), and safety of
machinery ergonomics (EN 614, EN 894). This module implements catalog
lookup, topic-to-standard mapping, and coverage-gap checking for HFE design
plans and requirement documents; it does not implement the normative HFE
requirements of ECSS-E-ST-10-11C itself.
"""

# Catalog of ISO and European standards relevant to HFE in space systems.
# Each entry maps a standard identifier to its title and HFE topic tags.
# Source anchor: ECSS-E-ST-10-11C Annex E.
ISO_STANDARDS = {
    "ISO 9241-11": {
        "title": (
            "Ergonomics of human-system interaction — "
            "Usability: definitions and concepts"
        ),
        "topics": ["context_of_use", "usability", "user_interface"],
    },
    "ISO 9241-110": {
        "title": (
            "Ergonomics of human-system interaction — Dialogue principles"
        ),
        "topics": ["cognitive_ergonomics", "display_design", "user_interface"],
    },
    "ISO 9241-210": {
        "title": (
            "Ergonomics of human-system interaction — "
            "Human-centred design for interactive systems"
        ),
        "topics": ["context_of_use", "human_centred_design", "user_interface"],
    },
    "ISO 9241-400": {
        "title": (
            "Ergonomics of human-system interaction — "
            "Principles and requirements for physical input devices"
        ),
        "topics": ["display_design", "physical_ergonomics", "workstation_layout"],
    },
    "ISO 10075-1": {
        "title": (
            "Ergonomic principles related to mental workload — "
            "Introduction and general concepts"
        ),
        "topics": ["cognitive_ergonomics", "mental_workload"],
    },
    "ISO 10075-2": {
        "title": (
            "Ergonomic principles related to mental workload — "
            "Design principles"
        ),
        "topics": ["cognitive_ergonomics", "mental_workload"],
    },
    "ISO 11064-1": {
        "title": (
            "Ergonomic design of control centres — "
            "Principles for the design of control centres"
        ),
        "topics": ["control_room_design", "display_design", "workstation_layout"],
    },
    "ISO 11064-4": {
        "title": (
            "Ergonomic design of control centres — "
            "Layout and dimensions of workstations"
        ),
        "topics": ["anthropometry", "workstation_layout"],
    },
    "ISO 14738": {
        "title": (
            "Safety of machinery — Anthropometric requirements "
            "for the design of workstations at machinery"
        ),
        "topics": ["anthropometry", "workstation_layout"],
    },
    "ISO 7933": {
        "title": (
            "Ergonomics of the thermal environment — "
            "Analytical determination of thermal stress"
        ),
        "topics": ["environmental_ergonomics", "thermal_environment"],
    },
    "EN 614-1": {
        "title": (
            "Safety of machinery — Ergonomic design principles — "
            "Basic terminology and general principles"
        ),
        "topics": ["physical_ergonomics", "workstation_layout"],
    },
    "EN 894-2": {
        "title": (
            "Safety of machinery — Ergonomics requirements for the design "
            "of displays and control actuators — Displays"
        ),
        "topics": ["display_design", "physical_ergonomics"],
    },
}

# Reverse mapping: topic tag -> frozenset of standard IDs.
# Built once at module load from ISO_STANDARDS to guarantee consistency.
_TOPICS_INDEX = {}
for _sid, _rec in ISO_STANDARDS.items():
    for _topic in _rec["topics"]:
        _TOPICS_INDEX.setdefault(_topic, set()).add(_sid)
_TOPICS_INDEX = {t: frozenset(sids) for t, sids in _TOPICS_INDEX.items()}


def lookup_standard(standard_id):
    """Return a copy of the catalog record for standard_id.

    Raises ValueError if standard_id is not in the catalog.
    The returned dict is a new object; mutating it does not affect the catalog.
    """
    record = ISO_STANDARDS.get(standard_id)
    if record is None:
        raise ValueError(
            "standard %r is not in the HFE ISO/EN index "
            "(ECSS-E-ST-10-11C Annex E)" % (standard_id,)
        )
    return {"title": record["title"], "topics": list(record["topics"])}


def standards_for_topic(topic):
    """Return a sorted list of standard IDs whose record includes topic.

    Returns an empty list when no cataloged standard covers topic;
    does not raise — absence of a match is a coverage gap, not an error.
    """
    return sorted(_TOPICS_INDEX.get(topic, frozenset()))


def topics_for_standard(standard_id):
    """Return a sorted list of HFE topic tags for standard_id.

    Raises ValueError if standard_id is not in the catalog.
    """
    record = ISO_STANDARDS.get(standard_id)
    if record is None:
        raise ValueError(
            "standard %r is not in the HFE ISO/EN index "
            "(ECSS-E-ST-10-11C Annex E)" % (standard_id,)
        )
    return sorted(record["topics"])


def check_topic_coverage(topic_list):
    """Check which topics in topic_list have at least one indexed standard.

    Returns a new dict:
      "covered": list of {"topic": str, "standards": [str, ...]} for each
                 topic that has at least one indexed standard (standards sorted).
      "gaps":    list of topic strings with no indexed standard.

    topic_list is not mutated. Order of entries in "covered" and "gaps"
    follows the order of topic_list.
    """
    covered = []
    gaps = []
    for topic in topic_list:
        matched = standards_for_topic(topic)
        if matched:
            covered.append({"topic": topic, "standards": matched})
        else:
            gaps.append(topic)
    return {"covered": covered, "gaps": gaps}


def coverage_gaps(topic_list):
    """Return the list of topics from topic_list with no indexed standard.

    Convenience wrapper around check_topic_coverage.
    """
    return check_topic_coverage(topic_list)["gaps"]
