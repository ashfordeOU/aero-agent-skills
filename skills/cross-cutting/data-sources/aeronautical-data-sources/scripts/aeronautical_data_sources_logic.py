#!/usr/bin/env python3
"""Aeronautical engineering data source registry and credibility logic.

The data-sources-pack discipline for choosing and citing an
aeronautical engineering data source before it is used as the
engineering reference: authoritative data types (atmospheric models,
aerodynamic databases, materials properties, standard part libraries,
regulatory data), publisher class and revision tracking, review
status, a credibility score heuristic (regulatory highest, then
industry, then vendor, then community), and a citation line for the
report. All helpers are deterministic, offline, stdlib only; invalid
inputs raise ValueError.
"""

SOURCE_TYPES = (
    "atmospheric-model",
    "aerodynamic-database",
    "materials-properties",
    "standard-part-library",
    "regulatory-data",
    "other",
)

# Publisher class -> base credibility score. Regulatory is the
# highest class (airworthiness authorities, government reference
# data), industry next (standards bodies, professional societies),
# vendor lower (manufacturer catalogs), community lowest (public
# forums, personal pages).
PUBLISHER_CLASSES = {
    "regulatory": 10,
    "industry": 7,
    "vendor": 4,
    "community": 2,
}

REVIEW_STATUSES = ("approved", "in-review", "unreviewed", "superseded")

SCORE_FLOOR = 1
REVIEW_PENALTY = 2
SUPERSEDED_SCORE = 1


def _require_nonempty_string(value, argname):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % argname)
    return value.strip()


def register_source(
    name,
    source_type,
    publisher,
    publisher_class,
    edition,
    review_status,
    access_date,
):
    """Return the registry entry dict for one data source.

    Fields: name, source_type, publisher, publisher_class, edition,
    review_status, access_date. source_type must be one of SOURCE_TYPES,
    publisher_class one of PUBLISHER_CLASSES, review_status one of
    REVIEW_STATUSES; every text field must be a non-empty string.
    Raises ValueError on any violation.
    """
    entry = {
        "name": _require_nonempty_string(name, "name"),
        "source_type": _require_nonempty_string(source_type, "source_type"),
        "publisher": _require_nonempty_string(publisher, "publisher"),
        "publisher_class": _require_nonempty_string(
            publisher_class, "publisher_class"
        ),
        "edition": _require_nonempty_string(edition, "edition"),
        "review_status": _require_nonempty_string(review_status, "review_status"),
        "access_date": _require_nonempty_string(access_date, "access_date"),
    }
    if entry["source_type"] not in SOURCE_TYPES:
        raise ValueError(
            "source_type must be one of %s, got %r"
            % (", ".join(SOURCE_TYPES), entry["source_type"])
        )
    if entry["publisher_class"] not in PUBLISHER_CLASSES:
        raise ValueError(
            "publisher_class must be one of %s, got %r"
            % (", ".join(sorted(PUBLISHER_CLASSES)), entry["publisher_class"])
        )
    if entry["review_status"] not in REVIEW_STATUSES:
        raise ValueError(
            "review_status must be one of %s, got %r"
            % (", ".join(REVIEW_STATUSES), entry["review_status"])
        )
    return entry


def authoritative_type_ok(source_type):
    """True when source_type is a recognized authoritative data type.

    Recognized types: atmospheric-model, aerodynamic-database,
    materials-properties, standard-part-library, regulatory-data.
    "other" is a legal registry value but fails this check, which
    flags it for extra scrutiny. Raises ValueError when source_type is
    not a string.
    """
    if not isinstance(source_type, str):
        raise ValueError(
            "source_type must be a string, got %r" % (source_type,)
        )
    return source_type.strip() in SOURCE_TYPES and source_type.strip() != "other"


def review_status_ok(review_status):
    """True when review_status is a recognized review status value.

    Recognized statuses: approved, in-review, unreviewed, superseded.
    Raises ValueError when review_status is not a string.
    """
    if not isinstance(review_status, str):
        raise ValueError(
            "review_status must be a string, got %r" % (review_status,)
        )
    return review_status.strip() in REVIEW_STATUSES


def source_verdict(source):
    """Registry verdict: "approved" or "review-required".

    A source passes the registry check only when its review status is
    "approved". Every other status (in-review, unreviewed, superseded)
    returns "review-required" so the engineer re-checks the source
    before using it as the engineering reference. Raises ValueError
    when source is not a registry entry dict.
    """
    if not isinstance(source, dict) or "review_status" not in source:
        raise ValueError("source must be a registry entry dict from register_source")
    return "approved" if source["review_status"] == "approved" else "review-required"


def credibility_score(source):
    """Credibility score from publisher class and review status.

    Base score by publisher class: regulatory 10, industry 7, vendor
    4, community 2. A superseded source scores 1 regardless of class;
    an in-review or unreviewed source loses 2 points with a floor at
    1. Returns an int in [1, 10]; a regulatory source scores highest.
    Raises ValueError when source is not a registry entry dict.
    """
    if not isinstance(source, dict) or "publisher_class" not in source:
        raise ValueError("source must be a registry entry dict from register_source")
    base = PUBLISHER_CLASSES[source["publisher_class"]]
    if source["review_status"] == "superseded":
        return SUPERSEDED_SCORE
    if source["review_status"] in ("in-review", "unreviewed"):
        return max(SCORE_FLOOR, base - REVIEW_PENALTY)
    return base


def format_citation(source):
    """One-line citation for the engineering report references.

    Format: "Name, Edition, Publisher, accessed ACCESS_DATE." The
    publisher, the edition, and the access date all appear in the
    line, in that order. Raises ValueError when source is not a
    registry entry dict.
    """
    if not isinstance(source, dict) or not all(
        k in source
        for k in ("name", "edition", "publisher", "access_date")
    ):
        raise ValueError("source must be a registry entry dict from register_source")
    return "%s, %s, %s, accessed %s." % (
        source["name"],
        source["edition"],
        source["publisher"],
        source["access_date"],
    )
