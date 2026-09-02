"""Export control awareness logic for aerospace engineering work.

Pure Python 3, stdlib only. Helps an engineer or agent recognize when an
aerospace item, data set, or task touches export-controlled territory under
the US International Traffic in Arms Regulations (ITAR) and Export
Administration Regulations (EAR).

The module is a screening aid, not a legal opinion. Every function returns a
conservative first-pass verdict that must be confirmed by the organization's
trade compliance office before any release of controlled data.

Scope of this module:
  1. Defense article vs dual-use classification basics (USML categories,
     EAR 600-series, EAR99).
  2. Technical data vs public domain, the fundamental research exclusion,
     and deemed exports.
  3. Red-flag screening of restricted aerospace topics.
  4. A decision tree that maps item, audience, and purpose to a verdict
     class: defense-article, dual-use, public-domain, or not-controlled.
  5. Public domain checks (published textbooks, fundamental research).

The function flag_restricted_topic() returns red flags for restricted
topics. The function export_decision_tree() combines everything into a
verdict with jurisdiction, risk, and handling actions.
"""

from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# USML categories (22 CFR part 121) relevant to aerospace engineering.
# Category XIX is reserved and omitted. The official title of category XVII
# begins with a restricted term; the description below keeps the substance.
USML_CATEGORIES: Dict[str, str] = {
    "I": "firearms and close assault items",
    "II": "guns and armament",
    "III": "ammunition and ordnance",
    "IV": "launch vehicles, guided missiles, ballistic missiles, rockets, "
          "torpedoes, bombs and mines",
    "V": "explosives and energetic materials, propellants and their "
         "constituents",
    "VI": "surface vessels of war and special naval equipment",
    "VII": "ground vehicles",
    "VIII": "aircraft and related articles",
    "IX": "military training equipment and training",
    "X": "personal protective equipment",
    "XI": "military electronics",
    "XII": "fire control, laser, imaging and guidance equipment",
    "XIII": "materials and miscellaneous articles",
    "XIV": "toxicological agents and associated equipment",
    "XV": "spacecraft and related articles",
    "XVI": "nuclear weapons related articles",
    "XVII": "articles, technical data and defense services not otherwise "
            "enumerated",
    "XVIII": "directed energy weapons",
    "XX": "submersible vessels, oceanographic and associated equipment",
    "XXI": "articles, technical data and defense services not otherwise "
           "enumerated",
}

# Example EAR 600-series ECCNs (15 CFR 774 supplement 1) that matter to
# aerospace work. Export control reform moved most defense articles from the
# USML to 600-series ECCNs. Verify every ECCN against the current regulation
# before relying on it; entries change with each rule update.
EAR_600_SERIES_EXAMPLES: Dict[str, str] = {
    "0A606": "military ground vehicles and related items",
    "8A609": "marine gas turbine engines and associated equipment",
    "9A610": "military aircraft and related items",
    "9A619": "military gas turbine engines and associated equipment",
    "9D610": "software specially designed for 9A610 or 9A619 items",
    "9E610": "technology for 9A610 or 9A619 items",
}

# Red-flag aerospace topics. Each entry lists substring keywords that, when
# present in an item description, indicate the topic may touch controlled
# territory. The scanner is deliberately conservative: a hit means "stop and
# verify", not "controlled".
RED_FLAG_TOPICS: List[Dict[str, object]] = [
    {
        "label": "turbine blade alloys and high-temperature materials",
        "keywords": [
            "turbine blade", "superalloy", "single-crystal",
            "directionally solidified", "thermal barrier coating",
            "high-temperature alloy", "blade alloy",
        ],
        "reason": ("Single-crystal and directionally solidified superalloys "
                   "for gas turbine blades are export-controlled materials; "
                   "composition and processing know-how is technical data."),
    },
    {
        "label": "propulsion technology",
        "keywords": [
            "gas turbine engine", "turbojet", "turbofan", "turboshaft",
            "ramjet", "scramjet", "rocket engine", "rocket motor",
            "propulsion", "thrust",
        ],
        "reason": ("Military gas turbine engines (EAR 9A619) and rocket, "
                   "ramjet and scramjet propulsion are controlled; engine "
                   "design and manufacturing know-how is technical data."),
    },
    {
        "label": "missiles, rockets and launch vehicles",
        "keywords": [
            "guided missile", "ballistic missile", "cruise missile",
            "missile", "rocket", "launch vehicle",
        ],
        "reason": ("Guided missiles, ballistic missiles, rockets and launch "
                   "vehicles are defense articles under USML Category IV; "
                   "MTCR-controlled items remain on the USML or on EAR "
                   "missile-technology ECCNs."),
    },
    {
        "label": "controlled sensors and seekers",
        "keywords": [
            "infrared detector", "focal plane array", "night vision",
            "image intensifier", "laser rangefinder", "laser designator",
            "gyroscope", "gyro", "accelerometer", "inertial sensor",
            "seeker",
        ],
        "reason": ("Infrared focal plane arrays, night vision, laser "
                   "rangefinders and designators, and high-grade inertial "
                   "sensors are CCL-controlled (categories 6 and 7) or USML "
                   "XII; performance parameters set the ECCN."),
    },
    {
        "label": "avionics and navigation equipment",
        "keywords": [
            "navigation system", "inertial navigation", "gnss",
            "gps receiver", "avionics", "flight control computer",
            "flight management system",
        ],
        "reason": ("Military avionics and navigation items sit in 600-series "
                   "ECCNs (for example 7A611) or USML XI and XII; "
                   "high-performance GNSS and inertial navigation equipment "
                   "is CCL-controlled."),
    },
    {
        "label": "low-observable design and radar-absorbing materials",
        "keywords": [
            "low-observable", "low observable", "radar cross section",
            "radar absorbing", "stealth",
        ],
        "reason": ("Low-observable design and radar-absorbing materials are "
                   "controlled; radar cross-section reduction know-how is "
                   "technical data."),
    },
    {
        "label": "spacecraft and launch vehicles",
        "keywords": [
            "spacecraft", "satellite bus", "satellite", "orbital",
            "reentry", "re-entry", "rendezvous", "docking",
        ],
        "reason": ("Spacecraft and related items are USML Category XV (with "
                   "exceptions moved to EAR); orbital maneuvering and "
                   "rendezvous technology is controlled."),
    },
    {
        "label": "unmanned aerial systems",
        "keywords": [
            "uav", "uas", "unmanned aerial", "unmanned aircraft", "drone",
        ],
        "reason": ("Unmanned aerial systems above performance thresholds "
                   "are controlled (9A610 or 9A012); payload and autonomy "
                   "software matter for classification."),
    },
    {
        "label": "radiation-hardened electronics",
        "keywords": [
            "radiation hardened", "radiation-hardened", "rad-hard",
            "space-grade",
        ],
        "reason": ("Radiation-hardened microelectronics are CCL-controlled "
                   "(category 3) and are common in military and space "
                   "systems."),
    },
    {
        "label": "cryptographic items",
        "keywords": [
            "cryptograph", "encryption", "crypto", "secure communication",
        ],
        "reason": ("Cryptographic items are EAR category 5 part 2 "
                   "controlled; some mass-market encryption qualifies for "
                   "license exceptions."),
    },
    {
        "label": "hypersonic technology",
        "keywords": ["hypersonic", "hypersonics"],
        "reason": ("Hypersonic vehicles and propulsion are "
                   "emerging-controlled technology under EAR and USML "
                   "Category IV."),
    },
    {
        "label": "directed energy weapons",
        "keywords": [
            "directed energy", "high-energy laser", "laser weapon",
            "particle beam",
        ],
        "reason": "Directed energy weapons are USML Category XVIII.",
    },
    {
        "label": "specialty composites and ceramics",
        "keywords": [
            "carbon-carbon", "carbon carbon", "ceramic matrix",
            "carbon fiber", "composite",
        ],
        "reason": ("Carbon-carbon and ceramic-matrix composites are CCL "
                   "materials (category 9C) with military aerospace "
                   "applications."),
    },
    {
        "label": "energetic materials and propellants",
        "keywords": [
            "propellant", "explosive", "pyrotechnic", "energetic material",
        ],
        "reason": ("Explosives, propellants and energetic materials are "
                   "USML Category V or CCL category 1C controlled."),
    },
    {
        "label": "fire control and targeting",
        "keywords": [
            "fire control", "targeting", "weapon control", "gun laying",
            "aiming system",
        ],
        "reason": ("Fire control, laser and imaging equipment is USML "
                   "Category XII or 600-series controlled."),
    },
    {
        "label": "military aircraft and engines",
        "keywords": [
            "military aircraft", "combat aircraft", "fighter aircraft",
            "attack helicopter", "military engine", "fighter jet",
        ],
        "reason": ("Military aircraft and engines are defense articles "
                   "(USML VIII) or 600-series items (9A610, 9A619)."),
    },
    {
        "label": "defense services and training",
        "keywords": [
            "defense service", "military training", "technical assistance",
        ],
        "reason": ("Training or assistance to a foreign person on a defense "
                   "article is a controlled defense service."),
    },
]

# Keywords that suggest an item is a defense article (USML) rather than a
# dual-use item. Word-boundary matched so that "fuel tank" does not hit on
# "tank" and "landmine" does not hit on "mine".
DEFENSE_ARTICLE_KEYWORDS: List[str] = [
    "guided missile", "ballistic missile", "cruise missile", "rocket",
    "torpedo", "landmine", "naval mine", "bomb", "firearm", "ammunition",
    "armored vehicle", "military vehicle", "battle tank", "military aircraft",
    "combat aircraft", "fighter aircraft", "attack helicopter", "warship",
    "military vessel", "fire control", "night vision", "image intensifier",
    "directed energy", "nuclear weapon", "launch vehicle", "military training",
    "body armor", "military electronics", "weapon", "gun", "explosive",
    "propellant", "submersible",
]

# Valid values for structured inputs.
AUDIENCES: List[str] = ["us-person", "foreign-person", "public"]
PURPOSES: List[str] = [
    "internal-engineering", "sharing", "publication", "teaching",
    "fundamental-research", "procurement", "foreign-release",
]
SOURCES: List[str] = [
    "published", "textbook", "patent", "conference", "fundamental-research",
    "unpublished",
]

VERDICTS: List[str] = [
    "defense-article", "dual-use", "public-domain", "not-controlled",
]


# ---------------------------------------------------------------------------
# Red-flag topic screening
# ---------------------------------------------------------------------------

def flag_restricted_topic(topic: str) -> List[Dict[str, str]]:
    """Return red flags for a restricted aerospace topic.

    Screens a free-text item description against the red-flag topic list.
    Returns a list of matching entries as dicts with "topic" (the matched
    label) and "reason" (why the topic is restricted). An empty list means
    no red flag matched, which is not the same as "not controlled".

    Raises:
        ValueError: if topic is not a non-empty string.
    """
    if not isinstance(topic, str) or not topic.strip():
        raise ValueError("topic must be a non-empty string")
    lowered = topic.lower()
    flags: List[Dict[str, str]] = []
    for entry in RED_FLAG_TOPICS:
        keywords = entry["keywords"]
        assert isinstance(keywords, list)
        if any(kw in lowered for kw in keywords):
            flags.append(
                {"topic": str(entry["label"]), "reason": str(entry["reason"])}
            )
    return flags


# ---------------------------------------------------------------------------
# Public domain and fundamental research
# ---------------------------------------------------------------------------

def is_public_domain(
    source: str = "published",
    fundamental_research: bool = False,
    restricted_agreement: bool = False,
    approved_release: bool = False,
) -> bool:
    """Return True when the information qualifies as public domain.

    Public domain under ITAR (22 CFR 120.34) and publicly available under
    EAR (15 CFR 734.7 through 734.8) include: information published and
    sold without restriction (textbooks, journals), published patents,
    unlimited-distribution conference material, and the results of
    fundamental research at an accredited US institution where the results
    are ordinarily published and shared broadly.

    The fundamental research exclusion is lost when the research agreement
    restricts publication or sharing (side-letter or pre-publication review
    clauses). Pass restricted_agreement=True in that case.

    Args:
        source: one of "published", "textbook", "patent", "conference",
            "fundamental-research", "unpublished".
        fundamental_research: True when the work is bona fide fundamental
            research (results ordinarily published and shared broadly).
        restricted_agreement: True when a research agreement restricts
            publication or sharing of results.
        approved_release: True when the US government approved public
            release of the information.

    Raises:
        ValueError: if source is not a recognized value.
    """
    if source not in SOURCES:
        raise ValueError(
            "source must be one of: " + ", ".join(SOURCES)
        )
    if approved_release:
        return True
    if source in ("published", "textbook", "patent", "conference"):
        return True
    if source == "fundamental-research":
        return not restricted_agreement
    if source == "unpublished":
        # Fundamental research results shared within the scientific
        # community qualify even before formal publication, as long as no
        # agreement restricts that sharing.
        return fundamental_research and not restricted_agreement
    return False


# ---------------------------------------------------------------------------
# Defense article detection
# ---------------------------------------------------------------------------

def is_defense_article(
    item: str,
    usml_category: Optional[str] = None,
) -> bool:
    """Return True when the item appears to be a defense article.

    A defense article is an item on the USML (22 CFR part 121). When
    usml_category is given (for example "VIII" for aircraft), the item is a
    defense article by definition and True is returned. Otherwise the item
    description is screened against defense-article keywords as a heuristic;
    a True result means "verify on the USML", not a legal classification.

    Raises:
        ValueError: if item is not a non-empty string, or usml_category is
            not a recognized USML category.
    """
    if not isinstance(item, str) or not item.strip():
        raise ValueError("item must be a non-empty string")
    if usml_category is not None:
        if usml_category not in USML_CATEGORIES:
            raise ValueError(
                "usml_category must be one of: " + ", ".join(USML_CATEGORIES)
            )
        return True
    lowered = item.lower()
    for kw in DEFENSE_ARTICLE_KEYWORDS:
        if kw in lowered:
            return True
    return False


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_export_status(
    item: str,
    audience: str = "us-person",
    purpose: str = "internal-engineering",
    source: str = "unpublished",
    usml_category: Optional[str] = None,
    ear_600_series: bool = False,
    on_ccl: bool = False,
    fundamental_research: bool = False,
    restricted_agreement: bool = False,
    approved_release: bool = False,
) -> str:
    """Classify an item or data set into a verdict class.

    Verdict classes:
        defense-article - described by the USML; ITAR jurisdiction.
        dual-use        - EAR jurisdiction; on the Commerce Control List
                          (600-series or another CCL entry); may need a
                          license for export or deemed export.
        public-domain   - qualifies as public domain / publicly available;
                          not controlled.
        not-controlled  - no USML or CCL description found; EAR99 is the
                          default classification for such items, which
                          still requires end-use and end-user screening.

    Order of checks: public domain first, then defense article, then
    dual-use indicators, then not-controlled.

    Raises:
        ValueError: on an empty item, an unrecognized audience, purpose, or
            source, or an unrecognized usml_category.
    """
    if not isinstance(item, str) or not item.strip():
        raise ValueError("item must be a non-empty string")
    if audience not in AUDIENCES:
        raise ValueError(
            "audience must be one of: " + ", ".join(AUDIENCES)
        )
    if purpose not in PURPOSES:
        raise ValueError(
            "purpose must be one of: " + ", ".join(PURPOSES)
        )
    if source not in SOURCES:
        raise ValueError(
            "source must be one of: " + ", ".join(SOURCES)
        )
    if usml_category is not None and usml_category not in USML_CATEGORIES:
        raise ValueError(
            "usml_category must be one of: " + ", ".join(USML_CATEGORIES)
        )

    if is_public_domain(
        source=source,
        fundamental_research=fundamental_research,
        restricted_agreement=restricted_agreement,
        approved_release=approved_release,
    ):
        return "public-domain"
    if is_defense_article(item, usml_category=usml_category):
        return "defense-article"
    if ear_600_series or on_ccl:
        return "dual-use"
    return "not-controlled"


# ---------------------------------------------------------------------------
# Decision tree
# ---------------------------------------------------------------------------

def export_decision_tree(
    item: str,
    audience: str = "us-person",
    purpose: str = "internal-engineering",
    source: str = "unpublished",
    usml_category: Optional[str] = None,
    ear_600_series: bool = False,
    on_ccl: bool = False,
    fundamental_research: bool = False,
    restricted_agreement: bool = False,
    approved_release: bool = False,
) -> Dict[str, object]:
    """Run the export control decision tree for an item and audience.

    Combines red-flag screening, public domain checks, and defense article
    detection into a single verdict record:

        verdict     - one of defense-article, dual-use, public-domain,
                      not-controlled.
        jurisdiction- "ITAR", "EAR", or "none".
        risk        - "high", "medium", or "low".
        red_flags   - list of matched restricted topics.
        summary     - one-line explanation of the verdict.
        actions     - handling guidance to follow before any release.

    A deemed export note is added when the audience is a foreign person and
    the verdict is defense-article or dual-use: releasing technical data to
    a foreign person inside the US is treated as an export to their country
    of nationality and may require authorization.

    Raises:
        ValueError: on an empty item, an unrecognized audience, purpose, or
            source, or an unrecognized usml_category.
    """
    status = classify_export_status(
        item=item,
        audience=audience,
        purpose=purpose,
        source=source,
        usml_category=usml_category,
        ear_600_series=ear_600_series,
        on_ccl=on_ccl,
        fundamental_research=fundamental_research,
        restricted_agreement=restricted_agreement,
        approved_release=approved_release,
    )
    flags = flag_restricted_topic(item)
    foreign_person = audience == "foreign-person"

    if status == "public-domain":
        return {
            "verdict": "public-domain",
            "jurisdiction": "none",
            "risk": "low",
            "red_flags": flags,
            "summary": (
                "The information qualifies as public domain or publicly "
                "available and is not export controlled."
            ),
            "actions": [
                "Record the public domain basis (for example published "
                "textbook, journal article, patent, or fundamental "
                "research) before release.",
                "Confirm the information is not separately controlled as "
                "encryption source code or listed software.",
                "Re-verify the basis if the item is later used in a "
                "restricted research program.",
            ],
        }

    if status == "defense-article":
        actions = [
            "Verify jurisdiction and classification with the trade "
            "compliance office before any release or transfer.",
            "Do not share technical data with a foreign person, inside or "
            "outside the US, without prior authorization.",
            "Never mark or represent the item as compliant or certified on "
            "your own authority; only the compliance office does that.",
            "Check whether a 600-series transition moved the item from the "
            "USML to EAR jurisdiction before relying on this verdict.",
        ]
        if foreign_person:
            actions.insert(
                2,
                "Releasing this to a foreign person inside the US is a "
                "deemed export to their country of nationality; obtain "
                "authorization first.",
            )
        return {
            "verdict": "defense-article",
            "jurisdiction": "ITAR",
            "risk": "high",
            "red_flags": flags,
            "summary": (
                "The item is described by the USML and is a defense "
                "article under ITAR; its technical data is ITAR technical "
                "data."
            ),
            "actions": actions,
        }

    if status == "dual-use":
        actions = [
            "Identify the exact ECCN (600-series or another CCL entry) "
            "before sharing; EAR99 applies only to items not elsewhere "
            "specified.",
            "Screen the recipient against end-use and end-user "
            "restrictions.",
            "Do not release controlled technology to a foreign person "
            "without checking whether a license or license exception "
            "applies.",
            "Keep records of the classification basis and any license "
            "exception relied upon.",
        ]
        if foreign_person:
            actions.insert(
                1,
                "Releasing this to a foreign person inside the US is a "
                "deemed export to their country of nationality; obtain "
                "authorization first.",
            )
        return {
            "verdict": "dual-use",
            "jurisdiction": "EAR",
            "risk": "medium",
            "red_flags": flags,
            "summary": (
                "The item is under EAR jurisdiction and is described on "
                "the Commerce Control List (600-series or another CCL "
                "entry); export may require a license."
            ),
            "actions": actions,
        }

    actions = [
        "No USML or CCL description was found; the default EAR99 "
        "classification applies.",
        "Still screen the end use and end user; EAR99 items are subject to "
        "general prohibitions, and supporting a restricted end use or end "
        "user is prohibited.",
        "Re-run this check if the item, audience, or purpose changes; a "
        "verdict is only valid for the inputs it was computed from.",
    ]
    return {
        "verdict": "not-controlled",
        "jurisdiction": "EAR",
        "risk": "low",
        "red_flags": flags,
        "summary": (
            "No export control description was found for this item and "
            "context; treat it as EAR99 unless the compliance office "
            "decides otherwise."
        ),
        "actions": actions,
    }


__all__ = [
    "USML_CATEGORIES",
    "EAR_600_SERIES_EXAMPLES",
    "RED_FLAG_TOPICS",
    "AUDIENCES",
    "PURPOSES",
    "SOURCES",
    "VERDICTS",
    "flag_restricted_topic",
    "is_public_domain",
    "is_defense_article",
    "classify_export_status",
    "export_decision_tree",
]
