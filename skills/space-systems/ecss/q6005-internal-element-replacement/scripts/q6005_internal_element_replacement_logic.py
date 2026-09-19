"""Replacement of an element inside an opened hybrid assembly.

Anchor: ECSS-Q-ST-60-05C clause 10.5.2 (removing a chip or other mounted
element from a hybrid that is already built, and fitting a replacement in its
place). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the repair request: the site being reworked, the attach method the
   removal and refit will use, the elements already mounted around it and the
   provenance of the replacement part.
2. Count what the site has left. A site carries a replacement allowance and a
   thermal-excursion allowance, and they are consumed separately: one
   replacement can cost one or two excursions depending on how the element is
   attached.
3. Measure the neighbourhood. Elements inside the keep-out radius of the site
   are exposed to the attach temperature; the ones whose own limit is below
   that temperature are the ones the repair has to protect or move.
4. Grade the request as permitted, permitted-with-conditions or not-permitted,
   and return the verification set the repair carries once it is done.

Distances are compared with a tolerance because a keep-out radius is routinely
hit exactly by a nominal layout coordinate, and a Euclidean distance that
should land on the radius is not guaranteed to on every platform.
"""

import math

__all__ = [
    "LENGTH_TOLERANCE",
    "DEFAULT_KEEP_OUT_MM",
    "DEFAULT_REPLACEMENT_LIMIT",
    "DEFAULT_THERMAL_CYCLE_LIMIT",
    "ATTACH_METHODS",
    "BASE_VERIFICATIONS",
    "validate_attach_method",
    "validate_site",
    "validate_elements",
    "excursion_cost",
    "replacements_remaining",
    "projected_thermal_cycles",
    "thermal_headroom",
    "neighbours_within_keep_out",
    "heat_exposed_neighbours",
    "required_verifications",
    "assess_element_replacement",
]

# A keep-out radius is a layout number and a part sits on it exactly far more
# often than chance suggests. Absorb representation error in the comparison
# rather than by moving the radius.
LENGTH_TOLERANCE = 1e-9

DEFAULT_KEEP_OUT_MM = 1.5
DEFAULT_REPLACEMENT_LIMIT = 1
DEFAULT_THERMAL_CYCLE_LIMIT = 3

# How a mounted element is attached decides both what the removal costs the
# site in thermal excursions and how hot its neighbourhood gets.
ATTACH_METHODS = {
    "eutectic": {"excursions": 2, "peak_c": 420.0},
    "solder": {"excursions": 2, "peak_c": 260.0},
    "adhesive": {"excursions": 1, "peak_c": 150.0},
}

BASE_VERIFICATIONS = (
    "post-repair-visual-inspection",
    "interconnect-verification-on-new-bonds",
    "electrical-retest-of-the-repaired-unit",
    "repair-record-entry",
)


def _require_number(value, label, minimum=None):
    """Return value as a float, raising on anything that is not a real number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must be at least %g, got %g" % (label, minimum, number))
    return number


def _require_non_negative_int(value, label):
    """Return value as a non-negative int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def _require_identity(value, label):
    """Return a stripped non-empty identity string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def validate_attach_method(method):
    """Return the normalised attach-method name, raising on an unknown one."""
    name = _require_identity(method, "attach_method").lower()
    if name not in ATTACH_METHODS:
        raise ValueError(
            "unknown attach method %r; known: %s"
            % (method, ", ".join(sorted(ATTACH_METHODS)))
        )
    return name


def validate_site(site):
    """Return the normalised repair-site record.

    A site names where it is, how the element sitting there is attached, how
    many replacements it has already taken and how many thermal excursions it
    has already seen. History is data, not an error: a site that is out of
    allowance is a case to be graded, not an input to be refused.
    """
    if not isinstance(site, dict):
        raise ValueError("site must be a mapping")
    for key in ("site_id", "attach_method", "position_mm"):
        if key not in site:
            raise ValueError("site missing required key '%s'" % key)
    position = site["position_mm"]
    if (
        isinstance(position, (str, dict))
        or not isinstance(position, (list, tuple))
        or len(position) != 2
    ):
        raise ValueError("site['position_mm'] must be an (x, y) pair in millimetres")
    return {
        "site_id": _require_identity(site["site_id"], "site['site_id']"),
        "attach_method": validate_attach_method(site["attach_method"]),
        "position_mm": (
            _require_number(position[0], "site['position_mm'][0]"),
            _require_number(position[1], "site['position_mm'][1]"),
        ),
        "prior_replacements": _require_non_negative_int(
            site.get("prior_replacements", 0), "site['prior_replacements']"
        ),
        "prior_thermal_cycles": _require_non_negative_int(
            site.get("prior_thermal_cycles", 0), "site['prior_thermal_cycles']"
        ),
        "residue_removal_confirmed": bool(site.get("residue_removal_confirmed", False)),
    }


def validate_elements(elements):
    """Return the normalised records of the elements already on the substrate."""
    if isinstance(elements, dict) or not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence of element records")
    normalised = []
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            raise ValueError("elements[%d] must be a mapping" % index)
        for key in ("element_id", "position_mm", "temperature_limit_c"):
            if key not in element:
                raise ValueError("elements[%d] missing required key '%s'" % (index, key))
        position = element["position_mm"]
        if (
            isinstance(position, (str, dict))
            or not isinstance(position, (list, tuple))
            or len(position) != 2
        ):
            raise ValueError(
                "elements[%d]['position_mm'] must be an (x, y) pair in millimetres" % index
            )
        normalised.append(
            {
                "element_id": _require_identity(
                    element["element_id"], "elements[%d]['element_id']" % index
                ),
                "position_mm": (
                    _require_number(position[0], "elements[%d]['position_mm'][0]" % index),
                    _require_number(position[1], "elements[%d]['position_mm'][1]" % index),
                ),
                "temperature_limit_c": _require_number(
                    element["temperature_limit_c"],
                    "elements[%d]['temperature_limit_c']" % index,
                    minimum=0.0,
                ),
                "shielded": bool(element.get("shielded", False)),
            }
        )
    return normalised


def excursion_cost(attach_method):
    """Return the thermal excursions one removal-and-refit imposes on a site."""
    return ATTACH_METHODS[validate_attach_method(attach_method)]["excursions"]


def replacements_remaining(site, limit=DEFAULT_REPLACEMENT_LIMIT):
    """Return how many further replacements this site's allowance still permits."""
    record = validate_site(site)
    allowance = _require_non_negative_int(limit, "limit")
    return max(0, allowance - record["prior_replacements"])


def projected_thermal_cycles(site, limit=DEFAULT_THERMAL_CYCLE_LIMIT):
    """Return the excursion count the site would stand at after this repair."""
    record = validate_site(site)
    _require_non_negative_int(limit, "limit")
    return record["prior_thermal_cycles"] + excursion_cost(record["attach_method"])


def thermal_headroom(site, limit=DEFAULT_THERMAL_CYCLE_LIMIT):
    """Return the excursions left over after this repair; negative means over."""
    allowance = _require_non_negative_int(limit, "limit")
    return allowance - projected_thermal_cycles(site, limit)


def neighbours_within_keep_out(site, elements, keep_out_mm=DEFAULT_KEEP_OUT_MM):
    """Return (element_id, distance) for elements inside the site keep-out radius.

    Nearest first. The radius is inclusive within a tolerance, because a part
    placed on the nominal radius must not fall in or out of the set depending
    on which machine evaluated the distance.
    """
    record = validate_site(site)
    radius = _require_number(keep_out_mm, "keep_out_mm", minimum=0.0)
    origin_x, origin_y = record["position_mm"]
    inside = []
    for element in validate_elements(elements):
        x, y = element["position_mm"]
        distance = math.hypot(x - origin_x, y - origin_y)
        if distance <= radius + LENGTH_TOLERANCE:
            inside.append((element["element_id"], distance))
    return sorted(inside, key=lambda item: (item[1], item[0]))


def heat_exposed_neighbours(site, elements, keep_out_mm=DEFAULT_KEEP_OUT_MM):
    """Return the unshielded near neighbours the attach temperature would exceed."""
    record = validate_site(site)
    peak = ATTACH_METHODS[record["attach_method"]]["peak_c"]
    by_id = {e["element_id"]: e for e in validate_elements(elements)}
    exposed = []
    for element_id, distance in neighbours_within_keep_out(site, elements, keep_out_mm):
        element = by_id[element_id]
        if element["shielded"]:
            continue
        if element["temperature_limit_c"] < peak - LENGTH_TOLERANCE:
            exposed.append(
                {
                    "element_id": element_id,
                    "distance_mm": distance,
                    "temperature_limit_c": element["temperature_limit_c"],
                    "attach_peak_c": peak,
                }
            )
    return exposed


def required_verifications(conditions=()):
    """Return the verification set a completed replacement carries."""
    if isinstance(conditions, str) or not isinstance(conditions, (list, tuple, set, frozenset)):
        raise ValueError("conditions must be a sequence of condition names")
    verifications = list(BASE_VERIFICATIONS)
    named = {str(c).strip().lower() for c in conditions}
    if "heat-exposed-neighbours" in named:
        verifications.append("visual-check-of-elements-inside-the-keep-out-radius")
    if "residue-unconfirmed" in named:
        verifications.append("site-cleanliness-verification-before-refit")
    if "second-replacement" in named:
        verifications.append("substrate-metallisation-adhesion-check-at-the-site")
    return verifications


def assess_element_replacement(spec):
    """Run the full clause 10.5.2 internal element replacement assessment.

    spec keys: site, elements, replacement_part; optional keep_out_mm,
    replacement_limit, thermal_cycle_limit, approved_procedure (default False).
    replacement_part names its lot status and whether the part is removable at
    all -- an element built under an overlay or under another element is not.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("site", "elements", "replacement_part"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    part = spec["replacement_part"]
    if not isinstance(part, dict):
        raise ValueError("replacement_part must be a mapping")
    approved = spec.get("approved_procedure", False)
    if not isinstance(approved, bool):
        raise ValueError("approved_procedure must be a boolean")

    site = validate_site(spec["site"])
    elements = validate_elements(spec["elements"])
    keep_out = _require_number(
        spec.get("keep_out_mm", DEFAULT_KEEP_OUT_MM), "keep_out_mm", minimum=0.0
    )
    replacement_limit = _require_non_negative_int(
        spec.get("replacement_limit", DEFAULT_REPLACEMENT_LIMIT), "replacement_limit"
    )
    cycle_limit = _require_non_negative_int(
        spec.get("thermal_cycle_limit", DEFAULT_THERMAL_CYCLE_LIMIT), "thermal_cycle_limit"
    )
    lot_accepted = bool(part.get("from_accepted_lot", False))
    removable = bool(part.get("site_accessible", True))

    remaining = replacements_remaining(spec["site"], replacement_limit)
    projected = projected_thermal_cycles(spec["site"], cycle_limit)
    headroom = cycle_limit - projected
    exposed = heat_exposed_neighbours(spec["site"], spec["elements"], keep_out)
    near = neighbours_within_keep_out(spec["site"], spec["elements"], keep_out)

    blockers = []
    conditions = []
    if not approved:
        blockers.append("no approved repair procedure covers this replacement")
    if remaining <= 0:
        blockers.append(
            "site %s has used its %d replacement(s); no attempt remains"
            % (site["site_id"], replacement_limit)
        )
    if headroom < 0:
        blockers.append(
            "repair would take site %s to %d thermal excursions against an allowance of %d"
            % (site["site_id"], projected, cycle_limit)
        )
    if not lot_accepted:
        blockers.append("replacement part does not come from an accepted lot")
    if not removable:
        blockers.append(
            "element at site %s is not accessible for removal without disturbing the assembly"
            % site["site_id"]
        )

    if exposed:
        conditions.append("heat-exposed-neighbours")
    if not site["residue_removal_confirmed"]:
        conditions.append("residue-unconfirmed")
    if site["prior_replacements"] >= 1:
        conditions.append("second-replacement")

    if blockers:
        disposition = "not-permitted"
    elif conditions:
        disposition = "permitted-with-conditions"
    else:
        disposition = "permitted"

    return {
        "site_id": site["site_id"],
        "attach_method": site["attach_method"],
        "attach_peak_c": ATTACH_METHODS[site["attach_method"]]["peak_c"],
        "replacements_remaining": remaining,
        "projected_thermal_cycles": projected,
        "thermal_headroom": headroom,
        "element_count": len(elements),
        "neighbours_within_keep_out": near,
        "heat_exposed_neighbours": exposed,
        "conditions": conditions,
        "blockers": blockers,
        "disposition": disposition,
        "permitted": disposition != "not-permitted",
        "verifications": required_verifications(conditions),
    }
