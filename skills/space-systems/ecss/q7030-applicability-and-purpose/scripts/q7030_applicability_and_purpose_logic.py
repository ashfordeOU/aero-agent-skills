"""Applicability and purpose of the wire-wrapping requirements.

Anchor: ECSS-Q-ST-70-30 scope -- which electrical connections are solderless
wrapped connections the standard governs, which terminals can carry one, and
what the wrap is for. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Decide whether a proposed connection is a solderless wrapped connection at
   all, or a joining method that a different process standard governs.
2. Decide whether the terminal can carry a wrap: the post has to present sharp
   corners that the wire can bite into, which a round or radiused post does not.
3. Decide whether the conductor can be wrapped: a wrap is a solid-conductor
   process, and the gauge has to sit inside the span the wrapping tools and
   terminals cover.
4. Count the gas-tight metal-to-metal contact areas the wrap would produce --
   turns times sharp corners -- because that count, not the wrap's appearance,
   is the purpose the whole standard exists to secure.
5. Return the requirement areas that apply to the connection once it is inside
   scope, so a caller knows which controls it has taken on.
"""

__all__ = [
    "WRAPPABLE_METHODS",
    "WRAPPABLE_SHAPES",
    "MIN_SHARP_CORNERS",
    "WRAPPABLE_CONSTRUCTIONS",
    "APPLICABLE_GAUGE_RANGE",
    "MIN_GAS_TIGHT_CONTACTS",
    "BASE_REQUIREMENT_AREAS",
    "MODIFIED_WRAP_AREA",
    "FLIGHT_REQUIREMENT_AREA",
    "FLIGHT_APPLICATIONS",
    "WRAP_TYPES",
    "method_exclusions",
    "terminal_exclusions",
    "conductor_exclusions",
    "gas_tight_contact_points",
    "requirement_areas",
    "assess_applicability",
]

# Only a solderless wrap is the process this standard governs. A soldered or
# crimped joint on the same post is a different process with its own controls.
WRAPPABLE_METHODS = ("solderless-wrap",)

# A wrap holds because the wire deforms over a corner. A post without corners
# cannot produce the contact areas the connection depends on.
WRAPPABLE_SHAPES = ("rectangular", "square", "rectangular-slotted")
MIN_SHARP_CORNERS = 2

# Wrapping is a solid-conductor process; a stranded conductor cannot hold the
# tension a wrap needs and its strands take the deformation unevenly.
WRAPPABLE_CONSTRUCTIONS = ("solid",)

# AWG span the wrapping tools and terminal posts cover. The lower number is the
# thickest wire, so the pair reads (thickest, thinnest).
APPLICABLE_GAUGE_RANGE = (18, 32)

# Turns times sharp corners. Below this the joint is a wrap in appearance only.
MIN_GAS_TIGHT_CONTACTS = 12

BASE_REQUIREMENT_AREAS = (
    "wire-and-terminal-specification",
    "wrapping-tool-certification",
    "wire-stripping-and-preparation",
    "wrap-turn-count-and-dimensions",
    "wrap-inspection-and-acceptance",
    "wrap-rework-and-repair-limits",
)
MODIFIED_WRAP_AREA = "modified-wrap-insulation-turn"
FLIGHT_REQUIREMENT_AREA = "operator-certification-and-first-article"
FLIGHT_APPLICATIONS = ("flight-hardware", "flight-spare", "qualification-model")
WRAP_TYPES = ("conventional", "modified")


def _token(label, value):
    """Return a lowercase, stripped token, or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def _count(label, value):
    """Return a non-negative integer count, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def method_exclusions(connection_method):
    """Return the scope exclusions raised by the joining method."""
    method = _token("connection_method", connection_method)
    if method in WRAPPABLE_METHODS:
        return []
    return [{
        "control": "joining-method",
        "detail": "%s is not a solderless wrapped connection; a different "
                  "process standard governs it" % method,
    }]


def terminal_exclusions(terminal_shape, sharp_corner_count):
    """Return the scope exclusions raised by the terminal post."""
    shape = _token("terminal_shape", terminal_shape)
    corners = _count("sharp_corner_count", sharp_corner_count)
    exclusions = []
    if shape not in WRAPPABLE_SHAPES:
        exclusions.append({
            "control": "terminal-shape",
            "detail": "a %s post presents no corner for the wire to bite into" % shape,
        })
    if corners < MIN_SHARP_CORNERS:
        exclusions.append({
            "control": "terminal-corners",
            "detail": "post presents %d sharp corners, fewer than the %d a wrap needs"
                      % (corners, MIN_SHARP_CORNERS),
        })
    return exclusions


def conductor_exclusions(conductor_construction, conductor_gauge_awg):
    """Return the scope exclusions raised by the conductor."""
    construction = _token("conductor_construction", conductor_construction)
    gauge = conductor_gauge_awg
    if isinstance(gauge, bool) or not isinstance(gauge, int):
        raise ValueError("conductor_gauge_awg must be an integer, got %r" % (gauge,))
    exclusions = []
    if construction not in WRAPPABLE_CONSTRUCTIONS:
        exclusions.append({
            "control": "conductor-construction",
            "detail": "a %s conductor is outside the wrapping process, which "
                      "relies on one solid conductor deforming over the corner"
                      % construction,
        })
    thickest, thinnest = APPLICABLE_GAUGE_RANGE
    if gauge < thickest or gauge > thinnest:
        exclusions.append({
            "control": "conductor-gauge",
            "detail": "AWG %d is outside the covered span AWG %d to AWG %d"
                      % (gauge, thickest, thinnest),
        })
    return exclusions


def gas_tight_contact_points(turns, sharp_corner_count):
    """Return the number of gas-tight contact areas a wrap would produce."""
    wraps = _count("turns", turns)
    corners = _count("sharp_corner_count", sharp_corner_count)
    return wraps * corners


def requirement_areas(wrap_type, application):
    """Return the requirement areas a connection inside scope has taken on."""
    kind = _token("wrap_type", wrap_type)
    if kind not in WRAP_TYPES:
        raise ValueError("unknown wrap_type %r" % (kind,))
    use = _token("application", application)
    areas = list(BASE_REQUIREMENT_AREAS)
    if kind == "modified":
        areas.append(MODIFIED_WRAP_AREA)
    if use in FLIGHT_APPLICATIONS:
        areas.append(FLIGHT_REQUIREMENT_AREA)
    return areas


def assess_applicability(connection):
    """Decide whether a connection is inside the wire-wrapping requirements.

    connection keys: connection_method, terminal_shape, sharp_corner_count,
    conductor_construction, conductor_gauge_awg, turns, wrap_type, application.
    """
    if not isinstance(connection, dict):
        raise ValueError("connection must be a mapping")
    for key in ("connection_method", "terminal_shape", "sharp_corner_count",
                "conductor_construction", "conductor_gauge_awg", "turns",
                "wrap_type", "application"):
        if key not in connection:
            raise ValueError("connection missing required key '%s'" % key)
    exclusions = []
    exclusions.extend(method_exclusions(connection["connection_method"]))
    exclusions.extend(terminal_exclusions(
        connection["terminal_shape"], connection["sharp_corner_count"]
    ))
    exclusions.extend(conductor_exclusions(
        connection["conductor_construction"], connection["conductor_gauge_awg"]
    ))
    contacts = gas_tight_contact_points(
        connection["turns"], connection["sharp_corner_count"]
    )
    in_scope = not exclusions
    findings = []
    if in_scope and contacts < MIN_GAS_TIGHT_CONTACTS:
        findings.append({
            "control": "gas-tight-contact-count",
            "detail": "%d contact areas, fewer than the %d a gas-tight wrap owes"
                      % (contacts, MIN_GAS_TIGHT_CONTACTS),
        })
    areas = requirement_areas(connection["wrap_type"], connection["application"]) \
        if in_scope else []
    if not in_scope:
        disposition = "outside-scope"
    elif findings:
        disposition = "within-scope-with-actions"
    else:
        disposition = "within-scope"
    return {
        "in_scope": in_scope,
        "exclusions": exclusions,
        "gas_tight_contact_points": contacts,
        "requirement_areas": areas,
        "findings": findings,
        "disposition": disposition,
    }
