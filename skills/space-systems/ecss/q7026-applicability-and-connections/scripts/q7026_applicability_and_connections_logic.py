"""Scope and category of a crimped electrical connection.

Anchor: ECSS-Q-ST-70-26C, the framework clause that says which
connections the crimping practice governs — machined and stamped
contacts, in-line splices, terminal lugs and coaxial ferrules — and the
loading limits that apply to each (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. Scope is decided by the joining method first. A soldered, welded,
   wire-wrapped, insulation-displacement or screw-clamp joint is not a
   crimp, and nothing downstream of that answer applies to it. Calling
   such a joint a crimp because it happens to be in a harness is how a
   qualification argument ends up covering a joint it never tested.
2. Inside the crimp family, the termination type is the category, and
   the category carries the conductor-count limit. A machined contact
   barrel takes one conductor; a splice barrel is the one termination
   built to take several; a lug takes at most a pair.
3. Barrel loading is a ratio, not a gauge number. Total conductor
   cross-section against barrel bore cross-section has both a floor and
   a ceiling: too little metal and the crimp has nothing to deform
   around, too much and the barrel cannot close without cutting strands.
4. A barrel loaded with both solid and stranded conductors is refused
   whatever the fill says. They yield differently under the die, so the
   stranded conductor carries the joint alone once the solid one has
   taken its set.
5. Every refusal names itself. A connection that is merely out of scope
   is not the same finding as one that is in scope and overloaded.

Stdlib only, offline, deterministic.
"""

TOLERANCE = 1.0e-9

CRIMP = "crimp"
OUT_OF_SCOPE_METHODS = (
    "solder",
    "weld",
    "wire-wrap",
    "insulation-displacement",
    "screw-clamp",
)
METHODS = (CRIMP,) + OUT_OF_SCOPE_METHODS

MACHINED_CONTACT = "machined-contact-crimp"
STAMPED_CONTACT = "stamped-and-formed-contact-crimp"
SPLICE = "in-line-splice-crimp"
LUG = "terminal-lug-crimp"
COAX_FERRULE = "coaxial-ferrule-crimp"

# Termination type as written on a harness definition -> crimp category.
TERMINATION_CATEGORIES = {
    "machined-contact": MACHINED_CONTACT,
    "stamped-contact": STAMPED_CONTACT,
    "in-line-splice": SPLICE,
    "terminal-lug": LUG,
    "coaxial-ferrule": COAX_FERRULE,
}

# Conductors one barrel of each category may take.
CONDUCTOR_LIMITS = {
    MACHINED_CONTACT: 1,
    STAMPED_CONTACT: 1,
    SPLICE: 4,
    LUG: 2,
    COAX_FERRULE: 1,
}

# Acceptance window on total conductor cross-section over barrel bore.
FILL_MIN = 0.35
FILL_MAX = 0.85

STRANDED = "stranded"
SOLID = "solid"
CONSTRUCTIONS = (STRANDED, SOLID)

UNDERFILLED = "barrel-underfilled"
ACCEPTABLE_FILL = "barrel-fill-acceptable"
OVERFILLED = "barrel-overfilled"

IN_SCOPE = "governed-by-the-crimping-practice"
OUT_OF_SCOPE = "outside-the-crimping-practice"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def normalize_method(value):
    """Fold a joining method as written into a known token."""
    text = _text("joining_method", value).lower().replace(" ", "-").replace("_", "-")
    if text.endswith("ed") and text[:-2] in METHODS:
        text = text[:-2]
    if text not in METHODS:
        raise ValueError("joining_method %r is not a recognised joining method" % value)
    return text


def normalize_termination(value):
    """Fold a termination type as written into a known token."""
    text = _text("termination_type", value).lower().replace(" ", "-").replace("_", "-")
    if text not in TERMINATION_CATEGORIES:
        raise ValueError("termination_type %r is not recognised" % value)
    return text


def validate_conductor(conductor):
    """Validate one conductor offered to a barrel."""
    if not isinstance(conductor, dict):
        raise ValueError("conductor must be a mapping")
    construction = _text("construction", conductor.get("construction")).lower()
    if construction not in CONSTRUCTIONS:
        raise ValueError("construction %r is not stranded or solid" % construction)
    csa = _numeric("conductor_csa_mm2", conductor.get("conductor_csa_mm2"), 0.0)
    if csa <= 0.0:
        raise ValueError("conductor_csa_mm2 must be greater than zero")
    return {"conductor_csa_mm2": csa, "construction": construction}


def validate_connection(connection):
    """Validate one proposed connection and normalize it."""
    if not isinstance(connection, dict):
        raise ValueError("connection must be a mapping")
    conductors = connection.get("conductors")
    if not isinstance(conductors, list) or not conductors:
        raise ValueError("conductors must be a non-empty list")
    bore = _numeric("barrel_bore_csa_mm2", connection.get("barrel_bore_csa_mm2"), 0.0)
    if bore <= 0.0:
        raise ValueError("barrel_bore_csa_mm2 must be greater than zero")
    return {
        "connection_id": _text("connection_id", connection.get("connection_id")),
        "joining_method": normalize_method(connection.get("joining_method")),
        "termination_type": normalize_termination(connection.get("termination_type")),
        "conductors": [validate_conductor(c) for c in conductors],
        "barrel_bore_csa_mm2": bore,
    }


def in_scope(connection):
    """Is this joint governed by the crimping practice at all?"""
    checked = validate_connection(connection)
    if checked["joining_method"] != CRIMP:
        return {
            "in_scope": False,
            "verdict": OUT_OF_SCOPE,
            "reason": "joining-method-is-%s" % checked["joining_method"],
        }
    return {"in_scope": True, "verdict": IN_SCOPE, "reason": None}


def categorize_connection(connection):
    """Which crimp category governs this connection."""
    checked = validate_connection(connection)
    if checked["joining_method"] != CRIMP:
        raise ValueError(
            "connection %s is a %s joint and has no crimp category"
            % (checked["connection_id"], checked["joining_method"])
        )
    return TERMINATION_CATEGORIES[checked["termination_type"]]


def conductor_limit(category):
    """Conductors one barrel of this category may take."""
    if category not in CONDUCTOR_LIMITS:
        raise ValueError("%r is not a crimp category" % (category,))
    return CONDUCTOR_LIMITS[category]


def barrel_fill_ratio(conductors, barrel_bore_csa_mm2):
    """Total conductor cross-section over barrel bore cross-section."""
    if not isinstance(conductors, list) or not conductors:
        raise ValueError("conductors must be a non-empty list")
    bore = _numeric("barrel_bore_csa_mm2", barrel_bore_csa_mm2, 0.0)
    if bore <= 0.0:
        raise ValueError("barrel_bore_csa_mm2 must be greater than zero")
    total = sum(validate_conductor(c)["conductor_csa_mm2"] for c in conductors)
    return total / bore


def fill_verdict(ratio):
    """Categorize a barrel fill ratio against its acceptance window."""
    value = _numeric("ratio", ratio, 0.0)
    if value < FILL_MIN - TOLERANCE:
        return UNDERFILLED
    if value > FILL_MAX + TOLERANCE:
        return OVERFILLED
    return ACCEPTABLE_FILL


def mixed_construction(conductors):
    """True when one barrel is offered both solid and stranded conductors."""
    kinds = {validate_conductor(c)["construction"] for c in conductors}
    return len(kinds) > 1


def assess_connection(connection):
    """Scope, category and barrel loading of one proposed connection."""
    checked = validate_connection(connection)
    scope = in_scope(connection)
    if not scope["in_scope"]:
        return {
            "connection_id": checked["connection_id"],
            "in_scope": False,
            "category": None,
            "findings": [scope["reason"]],
            "acceptable": False,
        }

    category = TERMINATION_CATEGORIES[checked["termination_type"]]
    limit = conductor_limit(category)
    count = len(checked["conductors"])
    ratio = barrel_fill_ratio(
        checked["conductors"], checked["barrel_bore_csa_mm2"]
    )
    verdict = fill_verdict(ratio)

    findings = []
    if count > limit:
        findings.append(
            "conductor-count-%d-over-the-limit-%d-for-%s" % (count, limit, category)
        )
    if mixed_construction(checked["conductors"]):
        findings.append("solid-and-stranded-conductors-in-one-barrel")
    if verdict != ACCEPTABLE_FILL:
        findings.append(verdict)

    return {
        "connection_id": checked["connection_id"],
        "in_scope": True,
        "category": category,
        "conductor_count": count,
        "conductor_limit": limit,
        "fill_ratio": ratio,
        "fill_verdict": verdict,
        "findings": findings,
        "acceptable": not findings,
    }


def assess_harness(connections):
    """Scope and bound every connection in a harness definition."""
    if not isinstance(connections, list) or not connections:
        raise ValueError("connections must be a non-empty list")
    results = [assess_connection(c) for c in connections]
    by_category = {}
    for result in results:
        key = result["category"] or OUT_OF_SCOPE
        by_category[key] = by_category.get(key, 0) + 1
    findings = []
    for result in results:
        for finding in result["findings"]:
            findings.append("%s: %s" % (result["connection_id"], finding))
    return {
        "results": results,
        "counts_by_category": by_category,
        "in_scope_count": sum(1 for r in results if r["in_scope"]),
        "findings": findings,
        "clean": not findings,
    }
