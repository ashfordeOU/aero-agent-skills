#!/usr/bin/env python3
"""certification_basis_logic.py - civil certification basis determination.

Regulation applicability, special condition detection, and certification
path selection for civil aircraft and systems programs.

Scope (this leaf): determine WHICH airworthiness regulations apply to a
product (14 CFR Part 25 / CS-25 for transport category airplanes, Part 23 /
CS-23 for normal category airplanes, Part 27 / CS-27 and Part 29 / CS-29 for
rotorcraft, Part 33 / CS-E for engines, Part 35 / CS-P for propellers), map
regulation paragraphs to the product, flag special conditions when the
design introduces a novel or unusual feature not covered by the regulation,
and select the certification path (type certificate, amended type
certificate, supplemental type certificate, TSO authorization) with the
required finding types.

Out of scope: the CONTENT of the airworthiness standards (25.1309 safety
assessment detail, system-level design requirements) lives in the
avionics/far-cs25 leaves; detailed special condition scoping for transport
airplanes lives in avionics/far-cs25/special-conditions. This module only
determines applicability, flags novelty, and selects the path.

Notes on fidelity:
- Regulation names, part numbers and paragraph numbers are public-domain
  references; every clause here is a paraphrase, not verbatim text.
- Subpart and paragraph listings are representative summaries for routing
  decisions; the authoritative listing is the regulation itself (eCFR for
  the FAR, EASA easy access rules for the CS).
- The module is deterministic: no randomness, no network, stdlib only.
"""

import re

# ---------------------------------------------------------------------------
# Regulation applicability table
# ---------------------------------------------------------------------------
# Each entry: part number (FAR), CS counterpart, product scope, categories,
# and a short paraphrase of what the regulation covers.

REGULATIONS = {
    "far-25": {
        "part": 25,
        "name": "14 CFR Part 25: Airworthiness Standards for Transport Category Airplanes",
        "cs_counterpart": "cs-25",
        "product": "airplane",
        "categories": ["transport"],
        "summary": "US airworthiness standards for transport category airplanes: flight, structures, design and construction, powerplant, equipment, operating limitations and EWIS.",
    },
    "cs-25": {
        "part": 25,
        "name": "CS-25: Certification Specifications and Acceptable Means of Compliance for Large Aeroplanes",
        "cs_counterpart": "far-25",
        "product": "airplane",
        "categories": ["transport"],
        "summary": "EASA certification specifications for large aeroplanes, mirroring FAR-25 with EU amendments and AMC-25 acceptable means of compliance.",
    },
    "far-23": {
        "part": 23,
        "name": "14 CFR Part 23: Airworthiness Standards for Normal Category Airplanes",
        "cs_counterpart": "cs-23",
        "product": "airplane",
        "categories": ["normal", "utility", "acrobatic", "commuter"],
        "summary": "US airworthiness standards for normal, utility, acrobatic and commuter category airplanes, performance-based since the 2017 reorganization.",
    },
    "cs-23": {
        "part": 23,
        "name": "CS-23: Certification Specifications for Normal, Utility, Aerobatic and Commuter Category Aeroplanes",
        "cs_counterpart": "far-23",
        "product": "airplane",
        "categories": ["normal", "utility", "acrobatic", "commuter"],
        "summary": "EASA certification specifications for normal, utility, aerobatic and commuter category aeroplanes.",
    },
    "far-27": {
        "part": 27,
        "name": "14 CFR Part 27: Airworthiness Standards for Normal Category Rotorcraft",
        "cs_counterpart": "cs-27",
        "product": "rotorcraft",
        "categories": ["normal"],
        "summary": "US airworthiness standards for normal category rotorcraft (rotorcraft up to the normal category weight limits).",
    },
    "cs-27": {
        "part": 27,
        "name": "CS-27: Certification Specifications for Small Rotorcraft",
        "cs_counterpart": "far-27",
        "product": "rotorcraft",
        "categories": ["normal"],
        "summary": "EASA certification specifications for small (normal category) rotorcraft.",
    },
    "far-29": {
        "part": 29,
        "name": "14 CFR Part 29: Airworthiness Standards for Transport Category Rotorcraft",
        "cs_counterpart": "cs-29",
        "product": "rotorcraft",
        "categories": ["transport"],
        "summary": "US airworthiness standards for transport category rotorcraft (larger, higher-performance rotorcraft).",
    },
    "cs-29": {
        "part": 29,
        "name": "CS-29: Certification Specifications for Large Rotorcraft",
        "cs_counterpart": "far-29",
        "product": "rotorcraft",
        "categories": ["transport"],
        "summary": "EASA certification specifications for large (transport category) rotorcraft.",
    },
    "far-33": {
        "part": 33,
        "name": "14 CFR Part 33: Airworthiness Standards for Aircraft Engines",
        "cs_counterpart": "cs-e",
        "product": "engine",
        "categories": [],
        "summary": "US airworthiness standards for aircraft engines: design and construction, block tests, cooling, induction, exhaust, controls, lubrication and fuel systems.",
    },
    "cs-e": {
        "part": 33,
        "name": "CS-E: Certification Specifications for Engines",
        "cs_counterpart": "far-33",
        "product": "engine",
        "categories": [],
        "summary": "EASA certification specifications for aircraft engines, mirroring FAR-33 with EU amendments.",
    },
    "far-35": {
        "part": 35,
        "name": "14 CFR Part 35: Airworthiness Standards for Propellers",
        "cs_counterpart": "cs-p",
        "product": "propeller",
        "categories": [],
        "summary": "US airworthiness standards for propellers: design and construction, tests and inspections.",
    },
    "cs-p": {
        "part": 35,
        "name": "CS-P: Certification Specifications for Propellers",
        "cs_counterpart": "far-35",
        "product": "propeller",
        "categories": [],
        "summary": "EASA certification specifications for propellers, mirroring FAR-35 with EU amendments.",
    },
}

# Product types this leaf recognizes and the categories each accepts.
PRODUCT_CATEGORIES = {
    "airplane": ["transport", "normal", "utility", "acrobatic", "commuter"],
    "rotorcraft": ["normal", "transport"],
    "engine": [],
    "propeller": [],
}

# ---------------------------------------------------------------------------
# Subpart and paragraph mapping (representative routing summaries)
# ---------------------------------------------------------------------------
SUBPARTS = {
    "far-25": ["A General", "B Flight", "C Structure", "D Design and Construction",
               "E Powerplant", "F Equipment", "G Operating Limitations and Information",
               "H Electrical Wiring Interconnection Systems"],
    "cs-25": ["A General", "B Flight", "C Structure", "D Design and Construction",
              "E Powerplant", "F Equipment", "G Operating Limitations and Information",
              "H Electrical Wiring Interconnection Systems"],
    "far-23": ["A General", "B Flight", "C Structure", "D Design and Construction",
               "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "cs-23": ["A General", "B Flight", "C Structure", "D Design and Construction",
              "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "far-27": ["A General", "B Flight", "C Strength Requirements", "D Design and Construction",
               "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "cs-27": ["A General", "B Flight", "C Strength Requirements", "D Design and Construction",
              "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "far-29": ["A General", "B Flight", "C Strength Requirements", "D Design and Construction",
               "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "cs-29": ["A General", "B Flight", "C Strength Requirements", "D Design and Construction",
              "E Powerplant", "F Equipment", "G Operating Limitations and Information"],
    "far-33": ["A General", "B Design and Construction", "C Design and Construction (Turbine)",
               "D Block Tests", "E Engine Cooling", "F Induction System", "G Exhaust System",
               "H Powerplant Controls and Accessories", "I Lubrication System", "J Fuel System"],
    "cs-e": ["A General", "B Design and Construction", "C Design and Construction (Turbine)",
             "D Block Tests", "E Engine Cooling", "F Induction System", "G Exhaust System",
             "H Powerplant Controls and Accessories", "I Lubrication System", "J Fuel System"],
    "far-35": ["A General", "B Design and Construction", "C Tests and Inspections"],
    "cs-p": ["A General", "B Design and Construction", "C Tests and Inspections"],
}

# Representative system-area to paragraph mapping for transport airplanes
# (FAR-25 / CS-25). Used to map regulation paragraphs to a product area;
# the authoritative paragraph set is the regulation itself.
AREA_PARAGRAPHS = {
    "systems": ["25.1309", "25.1310", "25.1329"],
    "flight-controls": ["25.671", "25.672", "25.675", "25.677", "25.679", "25.683"],
    "structure": ["25.301", "25.303", "25.305", "25.307", "25.571", "25.629"],
    "design-and-construction": ["25.601", "25.603", "25.605", "25.607", "25.609"],
    "powerplant": ["25.901", "25.903", "25.933", "25.943", "25.1101"],
    "equipment": ["25.1301", "25.1303", "25.1305", "25.1309", "25.1316"],
    "operating-limitations": ["25.1501", "25.1503", "25.1511", "25.1521"],
    "ewis": ["25.1701", "25.1703", "25.1707", "25.1709", "25.1711", "25.1713", "25.1717"],
}

# ---------------------------------------------------------------------------
# Special condition detection (novel or unusual design features)
# ---------------------------------------------------------------------------
# Keyword-driven novelty flags: a feature whose keyword appears in the
# feature description is treated as novel/unusual and therefore not fully
# covered by the existing regulation, which triggers the special condition
# mechanism (FAR 25.17 / CS-25.17 for transport airplanes, and the
# analogous paragraphs in the other parts). The verdict is a FLAG for the
# certification basis, not the detailed special condition scoping.
NOVEL_FEATURE_KEYWORDS = {
    "fly-by-wire": "full-authority electronic flight control with limited or no mechanical backup",
    "envelope-protection": "angle-of-attack or load-factor limiting in the flight control system",
    "autonomous": "autonomous or highly automated flight operation",
    "lithium-battery": "high-energy lithium battery chemistry not addressed by legacy equipment standards",
    "composite-primary-structure": "primary structural load path in composite material",
    "electric-propulsion": "electric or hybrid-electric propulsion system",
    "high-voltage": "high-voltage electrical power distribution",
    "morphing": "morphing or variable-geometry lifting surfaces",
    "active-load-alleviation": "active structural load alleviation in the flight control system",
    "hydrogen-fuel": "hydrogen fuel system or fuel cell power",
    "additive-structural": "additively manufactured primary structural parts",
    "blended-wing-body": "blended wing body or other non-conventional configuration",
}

# Conventional features that should NOT trigger a special condition.
# These describe the feature as conventional or proven. They only matter
# when a novel keyword also matches (e.g. "conventional fly-by-wire" is a
# contradiction); a feature with no novel keyword never flags.
CONVENTIONAL_FEATURE_MARKERS = (
    "conventional",
    "proven",
    "legacy",
    "existing",
    "aluminum",
    "metallic",
)

# ---------------------------------------------------------------------------
# Certification path selection
# ---------------------------------------------------------------------------
# Path decision rules, paraphrased from 14 CFR Part 21 procedures (and the
# CS-21 equivalents): a new type design needs a type certificate; a major
# change to a type design by the type certificate holder goes through an
# amended type certificate; a major change by anyone else goes through a
# supplemental type certificate; an article meeting a TSO needs TSO
# authorization.
PATH_RULES = {
    "type-certificate": {
        "name": "Type Certificate (TC)",
        "trigger": "new type design of an aircraft, engine or propeller",
        "procedure": "14 CFR Part 21 subpart B / CS-21 equivalent",
        "basis_clause": "certification basis established at application, regulation plus amendments plus special conditions",
        "finding_types": ["certification-basis", "means-of-compliance", "compliance-finding", "certification-program"],
    },
    "amended-type-certificate": {
        "name": "Amended Type Certificate",
        "trigger": "major change to a type design made by the type certificate holder",
        "procedure": "14 CFR Part 21 subpart B (change approval) / CS-21 equivalent",
        "basis_clause": "existing certification basis plus the delta for the changed areas",
        "finding_types": ["certification-basis", "means-of-compliance", "compliance-finding"],
    },
    "supplemental-type-certificate": {
        "name": "Supplemental Type Certificate (STC)",
        "trigger": "major change to a type design made by someone other than the type certificate holder",
        "procedure": "14 CFR Part 21 subpart E / CS-21 equivalent",
        "basis_clause": "existing type certificate basis plus the STC delta for the modification",
        "finding_types": ["certification-basis", "means-of-compliance", "compliance-finding"],
    },
    "tso-authorization": {
        "name": "TSO Authorization (TSOA)",
        "trigger": "article (equipment/appliance) that meets a Technical Standard Order",
        "procedure": "14 CFR Part 21 subpart O / CS-21 equivalent",
        "basis_clause": "the TSO minimum performance standard plus applicable airworthiness requirements",
        "finding_types": ["means-of-compliance", "compliance-finding"],
    },
    "minor-change": {
        "name": "Minor Change (no new certificate)",
        "trigger": "minor change to a type design by the type certificate holder, recorded per the change procedure",
        "procedure": "14 CFR Part 21 subpart B (minor change record) / CS-21 equivalent",
        "basis_clause": "no new certification basis; change shown not to affect the existing basis",
        "finding_types": ["compliance-finding"],
    },
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _validate_product(product_type, category):
    """Raise ValueError on unknown product type or unsupported category."""
    if product_type not in PRODUCT_CATEGORIES:
        raise ValueError(
            "unknown product type %r; expected one of %s"
            % (product_type, ", ".join(sorted(PRODUCT_CATEGORIES)))
        )
    allowed = PRODUCT_CATEGORIES[product_type]
    if allowed and category not in allowed:
        raise ValueError(
            "category %r not valid for product type %r; expected one of %s"
            % (category, product_type, ", ".join(allowed))
        )


def regulation_for(product_type, category=None, jurisdiction="FAA"):
    """Return the regulation record for a product type and category.

    jurisdiction: 'FAA' -> far-xx record, 'EASA' -> cs-xx record.
    Raises ValueError for unknown product/category/jurisdiction.
    """
    _validate_product(product_type, category)
    if jurisdiction not in ("FAA", "EASA"):
        raise ValueError("jurisdiction must be 'FAA' or 'EASA', got %r" % (jurisdiction,))
    for rid, rec in REGULATIONS.items():
        if rec["product"] != product_type:
            continue
        if rec["categories"] and category not in rec["categories"]:
            continue
        is_faa = rid.startswith("far-")
        if jurisdiction == "FAA" and is_faa:
            return dict(rec, id=rid)
        if jurisdiction == "EASA" and not is_faa:
            return dict(rec, id=rid)
    raise ValueError(
        "no regulation for product %r category %r jurisdiction %r"
        % (product_type, category, jurisdiction)
    )


def applicable_regulations(product_type, category=None):
    """Return the full certification basis regulation pair (FAA + EASA)."""
    _validate_product(product_type, category)
    faa = regulation_for(product_type, category, "FAA")
    easa = regulation_for(product_type, category, "EASA")
    return [faa, easa]


def subparts_for(regulation_id):
    """Return the representative subpart list for a regulation id."""
    try:
        return list(SUBPARTS[regulation_id])
    except KeyError:
        raise ValueError("unknown regulation id %r" % (regulation_id,)) from None


def paragraphs_for(regulation_id, area):
    """Return representative paragraphs mapping a product area for a part.

    area keys: systems, flight-controls, structure, design-and-construction,
    powerplant, equipment, operating-limitations, ewis. Transport-airplane
    oriented (FAR-25 / CS-25); other parts fall back to the subpart list.
    """
    if regulation_id not in REGULATIONS:
        raise ValueError("unknown regulation id %r" % (regulation_id,))
    if area in AREA_PARAGRAPHS:
        return list(AREA_PARAGRAPHS[area])
    if regulation_id in ("far-25", "cs-25"):
        raise ValueError(
            "unknown area %r for %s; expected one of %s"
            % (area, regulation_id, ", ".join(sorted(AREA_PARAGRAPHS)))
        )
    return list(SUBPARTS[regulation_id])


def detect_special_conditions(features):
    """Flag novel or unusual features that need a special condition.

    features: iterable of free-text feature descriptions (case-insensitive).
    Returns a list of verdict dicts:
      {feature, novel, keyword, rationale, special_condition}
    A feature is novel when it contains a NOVEL_FEATURE_KEYWORD and does not
    contain a conventional marker. Conventional features return
    special_condition False.
    """
    verdicts = []
    for feature in features:
        # Normalize to a bare alphanumeric string so that hyphenated,
        # space-separated and mixed forms ("fly-by-wire", "fly by wire",
        # "lithium battery", "lithium-battery") all match their keyword.
        text = re.sub(r"[^a-z0-9]", "", feature.lower())
        matched = None
        for keyword in NOVEL_FEATURE_KEYWORDS:
            if re.sub(r"[^a-z0-9]", "", keyword) in text:
                matched = keyword
                break
        conventional = any(
            re.sub(r"[^a-z0-9]", "", marker) in text
            for marker in CONVENTIONAL_FEATURE_MARKERS
        )
        novel = matched is not None and not conventional
        if novel:
            verdicts.append(
                {
                    "feature": feature,
                    "novel": True,
                    "keyword": matched,
                    "rationale": NOVEL_FEATURE_KEYWORDS[matched],
                    "special_condition": True,
                }
            )
        else:
            verdicts.append(
                {
                    "feature": feature,
                    "novel": False,
                    "keyword": matched,
                    "rationale": (
                        "feature appears covered by the existing regulation; "
                        "confirm coverage with the certification authority"
                        if matched is None
                        else "feature described as conventional; confirm coverage with the certification authority"
                    ),
                    "special_condition": False,
                }
            )
    return verdicts


def select_certification_path(product_type, change_kind, modifier_role="type_certificate_holder", article_tso=False):
    """Select the certification path from the change context.

    product_type: 'airplane' | 'rotorcraft' | 'engine' | 'propeller' | 'article'
    change_kind:   'new_type_design' | 'major_change' | 'minor_change' | 'none'
    modifier_role: 'type_certificate_holder' | 'other'
    article_tso:   True when the product is an article qualified to a TSO.

    Returns a dict {path, name, trigger, procedure, basis_clause,
    finding_types, rationale}. Raises ValueError on inconsistent input.
    """
    valid_products = {"airplane", "rotorcraft", "engine", "propeller", "article"}
    if product_type not in valid_products:
        raise ValueError("product_type must be one of %s" % (", ".join(sorted(valid_products)),))
    if change_kind not in ("new_type_design", "major_change", "minor_change", "none"):
        raise ValueError(
            "change_kind must be new_type_design|major_change|minor_change|none, got %r"
            % (change_kind,)
        )
    if modifier_role not in ("type_certificate_holder", "other"):
        raise ValueError(
            "modifier_role must be type_certificate_holder|other, got %r" % (modifier_role,)
        )

    if product_type == "article" and article_tso:
        path = "tso-authorization"
        rationale = "the product is an article meeting a Technical Standard Order, so TSO authorization is the path"
    elif change_kind == "new_type_design":
        path = "type-certificate"
        rationale = "a new type design of an aircraft, engine or propeller needs a type certificate"
    elif change_kind == "major_change":
        if modifier_role == "type_certificate_holder":
            path = "amended-type-certificate"
            rationale = "major change by the type certificate holder is approved through an amended type certificate"
        else:
            path = "supplemental-type-certificate"
            rationale = "major change by someone other than the type certificate holder needs a supplemental type certificate"
    elif change_kind == "minor_change":
        if modifier_role == "type_certificate_holder":
            path = "minor-change"
            rationale = "minor change by the type certificate holder is recorded, no new certificate"
        else:
            path = "supplemental-type-certificate"
            rationale = "change by someone other than the type certificate holder goes through the STC process even when minor"
    elif product_type == "article":
        path = "tso-authorization"
        rationale = "article product without a TSO election defaults to TSO authorization as the qualification path"
    else:
        path = "supplemental-type-certificate"
        rationale = "no new type design and no stated change; the conservative path for an alteration is the STC process"

    rec = dict(PATH_RULES[path])
    rec["path"] = path
    rec["rationale"] = rationale
    return rec


def certification_basis(
    project_type,
    category=None,
    features=None,
    change_kind=None,
    modifier_role="type_certificate_holder",
    article_tso=False,
    jurisdiction="FAA",
):
    """Assemble the full certification basis: regulations + special
    conditions + certification path.

    Returns a dict:
      {product, category, regulations: [records], special_conditions: [verdicts],
       certification_path: {path record}, basis_summary: str}
    """
    _validate_product(project_type, category)
    regs = applicable_regulations(project_type, category)
    chosen = regulation_for(project_type, category, jurisdiction)
    sc = detect_special_conditions(features or [])
    if change_kind is None:
        change_kind = "new_type_design" if project_type in ("airplane", "rotorcraft", "engine", "propeller") else "major_change"
    path = select_certification_path(project_type, change_kind, modifier_role, article_tso)

    sc_flags = [v for v in sc if v["special_condition"]]
    summary = (
        "certification basis for a %s %s: %s, %d special condition flag(s), "
        "certification path %s"
        % (
            category if category else "product",
            project_type,
            chosen["id"],
            len(sc_flags),
            path["path"],
        )
    )
    return {
        "product": project_type,
        "category": category,
        "regulations": regs,
        "special_conditions": sc,
        "certification_path": path,
        "basis_summary": summary,
    }


if __name__ == "__main__":
    import json

    demo = certification_basis(
        "airplane",
        "transport",
        features=["full-authority fly-by-wire flight controls", "conventional aluminum wing"],
        change_kind="major_change",
        modifier_role="other",
    )
    print(json.dumps(demo, indent=2, default=str))
