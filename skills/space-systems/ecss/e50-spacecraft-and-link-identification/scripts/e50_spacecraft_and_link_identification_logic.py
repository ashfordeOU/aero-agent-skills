"""Spacecraft and space link identification for a communications design.

Anchor: ECSS-E-ST-50C clause 5.6.13.1 -- requirements on identifying the
spacecraft and the space links of a mission. Paraphrased into an implementable
procedure; no standard text is reproduced.

One normative obligation is implemented: every spacecraft and every space link
is identified unambiguously, so a receiving entity can say whose data it is
holding and which link delivered it. Doing that means three things a design can
get wrong independently: the identifier has to fit the field the chosen
transfer frame version gives it, it must not collide with another identifier in
the same namespace, and it must not be the reserved all-ones pattern that means
"no spacecraft" rather than a spacecraft.

Everything here is integer arithmetic on bit fields, so the result is exact and
identical on every platform.
"""

__all__ = [
    "FRAME_VERSION_ID_WIDTHS",
    "DIRECTIONS",
    "IDENTIFICATION_UNAMBIGUOUS",
    "IDENTIFICATION_AMBIGUOUS",
    "validate_frame_version",
    "identifier_field_width",
    "identifier_capacity",
    "reserved_identifier",
    "validate_spacecraft_id",
    "validate_direction",
    "normalize_spacecraft",
    "normalize_link",
    "link_identity",
    "free_identifiers",
    "next_free_identifier",
    "assess_identification",
]

# Width in bits of the spacecraft identifier field carried by each transfer
# frame version a mission may select. The width is what bounds the namespace,
# so it is the first thing an assignment has to be checked against.
FRAME_VERSION_ID_WIDTHS = {
    "tm-version-1": 10,
    "tc-version-1": 10,
    "aos-version-2": 8,
    "uslp-version-4": 16,
}

DIRECTIONS = ("forward", "return")

IDENTIFICATION_UNAMBIGUOUS = "identification-unambiguous"
IDENTIFICATION_AMBIGUOUS = "identification-ambiguous"


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    return value.strip()


def validate_frame_version(value, name="frame_version"):
    """Return a transfer frame version the identifier width is known for."""
    version = _text(value, name).lower()
    if version not in FRAME_VERSION_ID_WIDTHS:
        raise ValueError(
            "%s %r is not a frame version with a known identifier width; known: %s"
            % (name, value, ", ".join(sorted(FRAME_VERSION_ID_WIDTHS)))
        )
    return version


def identifier_field_width(frame_version):
    """Return the spacecraft identifier field width in bits."""
    return FRAME_VERSION_ID_WIDTHS[validate_frame_version(frame_version)]


def identifier_capacity(frame_version):
    """Return how many identifiers the field holds and how many may be assigned.

    The all-ones pattern is reserved to mean that no spacecraft is identified,
    so the assignable count is one short of the raw capacity. A namespace
    planned against the raw capacity runs out one spacecraft early.
    """
    width = identifier_field_width(frame_version)
    total = 2 ** width
    return {
        "frame_version": validate_frame_version(frame_version),
        "width_bits": width,
        "total": total,
        "reserved": total - 1,
        "assignable": total - 1,
    }


def reserved_identifier(frame_version):
    """Return the all-ones identifier that means no spacecraft."""
    return identifier_capacity(frame_version)["reserved"]


def validate_spacecraft_id(value, frame_version, name="spacecraft_id"):
    """Return a spacecraft identifier that fits and is not the reserved one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    capacity = identifier_capacity(frame_version)
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    if value >= capacity["total"]:
        raise ValueError(
            "%s %r does not fit the %d-bit field of %s"
            % (name, value, capacity["width_bits"], capacity["frame_version"])
        )
    if value == capacity["reserved"]:
        raise ValueError(
            "%s %r is the reserved all-ones pattern meaning no spacecraft"
            % (name, value)
        )
    return value


def validate_direction(value, name="direction"):
    """Return the direction of a space link."""
    direction = _text(value, name).lower()
    if direction not in DIRECTIONS:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(DIRECTIONS), value)
        )
    return direction


def normalize_spacecraft(record):
    """Return one declared spacecraft as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("spacecraft must be a mapping")
    for key in ("name", "frame_version", "spacecraft_id"):
        if key not in record:
            raise ValueError("spacecraft is missing %s" % key)
    version = validate_frame_version(record["frame_version"])
    return {
        "name": _text(record["name"], "spacecraft name"),
        "frame_version": version,
        "spacecraft_id": validate_spacecraft_id(record["spacecraft_id"], version),
    }


def normalize_link(record):
    """Return one declared space link as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("link must be a mapping")
    for key in ("name", "spacecraft", "direction", "physical_channel"):
        if key not in record:
            raise ValueError("link is missing %s" % key)
    return {
        "name": _text(record["name"], "link name"),
        "spacecraft": _text(record["spacecraft"], "link spacecraft"),
        "direction": validate_direction(record["direction"]),
        "physical_channel": _text(record["physical_channel"], "physical_channel"),
    }


def link_identity(link):
    """Return the tuple that has to be unique for a link to be unambiguous."""
    link = normalize_link(link)
    return (link["spacecraft"], link["direction"], link["physical_channel"])


def free_identifiers(frame_version, assigned, limit=16):
    """Return up to `limit` assignable identifiers this namespace still has."""
    capacity = identifier_capacity(frame_version)
    if isinstance(assigned, dict) or not isinstance(assigned, (list, tuple, set)):
        raise ValueError("assigned must be a list, tuple or set of identifiers")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer, got %r" % (limit,))
    taken = set()
    for value in assigned:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("assigned identifiers must be integers")
        taken.add(value)
    free = []
    for candidate in range(capacity["reserved"]):
        if candidate not in taken:
            free.append(candidate)
            if len(free) >= limit:
                break
    return free


def next_free_identifier(frame_version, assigned):
    """Return the lowest identifier this namespace can still assign.

    Raises when the namespace is exhausted rather than returning the reserved
    pattern or a value that would not fit the field.
    """
    free = free_identifiers(frame_version, assigned, limit=1)
    if not free:
        raise ValueError(
            "the %s spacecraft identifier namespace is exhausted" % frame_version
        )
    return free[0]


def assess_identification(spacecraft, links):
    """Assess whether every spacecraft and every link is unambiguously identified.

    Returns the identifier collisions inside each frame-version namespace, the
    links sharing one identity, the links naming a spacecraft that was never
    declared, and the headroom left in each namespace.
    """
    if isinstance(spacecraft, dict) or not isinstance(spacecraft, (list, tuple)):
        raise ValueError("spacecraft must be a list or tuple of mappings")
    if not spacecraft:
        raise ValueError("spacecraft must not be empty")
    if isinstance(links, dict) or not isinstance(links, (list, tuple)):
        raise ValueError("links must be a list or tuple of mappings")

    normalized_craft = [normalize_spacecraft(record) for record in spacecraft]

    by_name = {}
    duplicate_names = []
    for craft in normalized_craft:
        if craft["name"] in by_name:
            duplicate_names.append(craft["name"])
        by_name[craft["name"]] = craft

    namespaces = {}
    for craft in normalized_craft:
        namespaces.setdefault(craft["frame_version"], []).append(craft)

    id_collisions = []
    headroom = {}
    for version, members in sorted(namespaces.items()):
        seen = {}
        for craft in members:
            key = craft["spacecraft_id"]
            if key in seen:
                id_collisions.append(
                    {
                        "frame_version": version,
                        "spacecraft_id": key,
                        "spacecraft": sorted([seen[key], craft["name"]]),
                    }
                )
            else:
                seen[key] = craft["name"]
        capacity = identifier_capacity(version)
        headroom[version] = {
            "assignable": capacity["assignable"],
            "assigned": len(seen),
            "remaining": capacity["assignable"] - len(seen),
        }

    normalized_links = []
    link_names = set()
    duplicate_link_names = []
    for record in links:
        link = normalize_link(record)
        if link["name"] in link_names:
            duplicate_link_names.append(link["name"])
        link_names.add(link["name"])
        normalized_links.append(link)

    identity_seen = {}
    link_collisions = []
    undeclared = []
    for link in normalized_links:
        if link["spacecraft"] not in by_name:
            undeclared.append(link["name"])
        identity = (link["spacecraft"], link["direction"], link["physical_channel"])
        if identity in identity_seen:
            link_collisions.append(
                {
                    "identity": identity,
                    "links": sorted([identity_seen[identity], link["name"]]),
                }
            )
        else:
            identity_seen[identity] = link["name"]

    findings = []
    for collision in id_collisions:
        findings.append(
            "spacecraft identifier %d in %s is assigned to %s"
            % (
                collision["spacecraft_id"],
                collision["frame_version"],
                " and ".join(collision["spacecraft"]),
            )
        )
    for collision in link_collisions:
        findings.append(
            "links %s share one identity and cannot be told apart"
            % " and ".join(collision["links"])
        )
    for name in duplicate_names:
        findings.append("spacecraft name %r is declared more than once" % name)
    for name in duplicate_link_names:
        findings.append("link name %r is declared more than once" % name)
    for name in undeclared:
        findings.append("link %r names a spacecraft that was never declared" % name)

    unambiguous = not (
        id_collisions
        or link_collisions
        or duplicate_names
        or duplicate_link_names
        or undeclared
    )

    return {
        "spacecraft_count": len(normalized_craft),
        "link_count": len(normalized_links),
        "identifier_collisions": id_collisions,
        "link_identity_collisions": link_collisions,
        "duplicate_spacecraft_names": duplicate_names,
        "duplicate_link_names": duplicate_link_names,
        "links_with_undeclared_spacecraft": undeclared,
        "namespace_headroom": headroom,
        "unambiguous": unambiguous,
        "verdict": (
            IDENTIFICATION_UNAMBIGUOUS if unambiguous else IDENTIFICATION_AMBIGUOUS
        ),
        "findings": findings,
    }
