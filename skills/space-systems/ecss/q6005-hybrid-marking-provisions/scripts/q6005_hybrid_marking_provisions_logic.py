"""The marking scheme a finished hybrid microcircuit is identified by.

Anchor: ECSS-Q-ST-60-05 clause 10.2 (the general provisions for marking a
finished hybrid, so that each delivered unit carries an identification that
stays on it, can be read on it, and leads back to the records that describe
it).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* Permanence is not a property of the marking method alone. It is the method
  measured against everything the unit still faces after it is marked: a mark
  that survives handling is not a mark that survives solvent cleaning, and the
  hardest exposure still to come is the one the method has to answer.
* A method also has to suit the surface it is put on. A method that will not
  take on the declared package material is refused outright rather than graded
  down, because the mark either does not form or does not stay.
* Legibility is a geometry question before it is an inspection question. The
  characters, the line count and the margins need a footprint, and that
  footprint either fits the face it is assigned to or it does not.
* Where the mark goes decides what it identifies. A mark on a removable lid
  identifies the lid; once the lid is changed the unit is anonymous. A mark on
  the container identifies the shipment, and is the route for a unit with no
  usable face -- but only when the container record is genuinely maintained,
  and never as a convenience for a unit whose body had the room.
* The mark is only an index into the records. A scheme that puts a beautiful
  permanent mark on every unit and does not bind it to the lot record and the
  serial register has identified nothing.
* The marking-provision index is weighted credit over total weight. It ranks
  what is outstanding; an unsuitable method, an unreachable permanence, a mark
  that does not fit or a broken traceability link decides the outcome on its
  own, at any index.
"""

from __future__ import annotations

import math

# How long a mark laid down by each method stays readable: 3 survives wet
# processing, 2 survives handling and coating, 1 is temporary.
MARKING_METHOD_PERMANENCE = {
    "laser-engraving": 3,
    "mechanical-engraving": 3,
    "fired-ceramic-ink": 3,
    "cured-epoxy-ink-stamp": 2,
    "cured-silk-screen": 2,
    "uncured-ink-stamp": 1,
    "adhesive-label": 1,
}

# Package surfaces each method can actually be applied to.
METHOD_SURFACES = {
    "laser-engraving": ("ceramic-body", "ceramic-lid", "metal-lid"),
    "mechanical-engraving": ("metal-lid",),
    "fired-ceramic-ink": ("ceramic-body", "ceramic-lid"),
    "cured-epoxy-ink-stamp": ("ceramic-body", "ceramic-lid", "metal-lid", "polymer-body"),
    "cured-silk-screen": ("ceramic-body", "ceramic-lid", "metal-lid"),
    "uncured-ink-stamp": ("ceramic-body", "ceramic-lid", "metal-lid", "polymer-body"),
    "adhesive-label": ("ceramic-body", "metal-lid", "polymer-body"),
}

# Permanence each downstream exposure demands of the mark.
EXPOSURE_PERMANENCE_DEMAND = {
    "handling-and-storage-only": 1,
    "conformal-coating": 2,
    "thermal-vacuum-bake": 3,
    "solvent-cleaning": 3,
    "board-level-soldering": 3,
}

# Where a mark may be placed.
MARKING_LOCATIONS = ("package-body", "package-lid", "carrier-or-container-only")

# Character geometry used to size a mark against the face it is assigned to.
CHARACTER_WIDTH_RATIO = 0.6
LINE_PITCH_RATIO = 1.5
MARKING_MARGIN_MM = 0.3

# Provision elements and the share of the marking scheme each supplies.
PROVISION_ELEMENT_WEIGHTS = {
    "marking-method-qualification": 1.0,
    "marking-permanence-demonstration": 1.0,
    "marking-legibility-verification": 1.0,
    "lot-and-serial-traceability-link": 1.0,
    "marking-placement-definition": 0.9,
    "marking-inspection-in-the-assembly-flow": 0.8,
    "marking-drawing-or-specification-reference": 0.7,
    "remarking-and-rework-rule": 0.6,
    "alternative-identification-rule": 0.5,
}

# The provisions the scheme rests on; without one it is not graded.
MANDATORY_PROVISION_ELEMENTS = (
    "marking-method-qualification",
    "marking-permanence-demonstration",
    "marking-legibility-verification",
    "lot-and-serial-traceability-link",
)

PROVISION_STATE_CREDIT = {
    "defined": 1.0,
    "defined-with-observation": 0.7,
    "deficient": 0.0,
    "not-defined": 0.0,
}

# Marking-provision index an adequate scheme has to reach.
ACCEPTANCE_INDEX = 0.90

# Footprints and indices are sums of products; a case meant to sit exactly on
# a bound can land a few units in the last place away from it.
MARKING_TOLERANCE = 1e-9

VERDICTS = (
    "marking-provisions-adequate",
    "marking-provisions-adequate-with-open-actions",
    "marking-provisions-inadequate",
    "marking-provisions-assessment-incomplete",
)


def _real(value, label):
    """Return ``value`` as a finite float or raise for anything else."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    """Return ``value`` as a finite positive float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _flag(mapping, key):
    """Return a required boolean field of a mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (key, value))
    return value


def method_permanence_grade(method):
    """How long a mark laid down by one method stays readable."""
    if method not in MARKING_METHOD_PERMANENCE:
        raise ValueError(
            "unknown marking method %r (known: %s)"
            % (method, ", ".join(sorted(MARKING_METHOD_PERMANENCE)))
        )
    return MARKING_METHOD_PERMANENCE[method]


def method_suits_surface(method, surface):
    """True when a marking method can be applied to a package surface."""
    allowed = METHOD_SURFACES[method] if method in METHOD_SURFACES else None
    if allowed is None:
        raise ValueError(
            "unknown marking method %r (known: %s)"
            % (method, ", ".join(sorted(METHOD_SURFACES)))
        )
    known = set()
    for surfaces in METHOD_SURFACES.values():
        known.update(surfaces)
    if surface not in known:
        raise ValueError(
            "unknown package surface %r (known: %s)" % (surface, ", ".join(sorted(known)))
        )
    return surface in allowed


def required_permanence_grade(exposures):
    """Permanence the hardest exposure still ahead of the unit demands."""
    if not isinstance(exposures, (list, tuple)):
        raise ValueError("exposures must be a list or tuple, got %r" % (type(exposures).__name__,))
    if len(exposures) == 0:
        raise ValueError("the processing a marked unit still faces must be declared")
    demands = []
    for exposure in exposures:
        if exposure not in EXPOSURE_PERMANENCE_DEMAND:
            raise ValueError(
                "unknown downstream exposure %r (known: %s)"
                % (exposure, ", ".join(sorted(EXPOSURE_PERMANENCE_DEMAND)))
            )
        demands.append(EXPOSURE_PERMANENCE_DEMAND[exposure])
    return max(demands)


def permanence_is_sufficient(method, exposures):
    """True when the method outlasts everything the unit still has to go through."""
    return method_permanence_grade(method) >= required_permanence_grade(exposures)


def required_marking_footprint_mm(marking_lines, character_height_mm):
    """Width and height one mark needs, margins included."""
    if not isinstance(marking_lines, (list, tuple)):
        raise ValueError(
            "marking_lines must be a list or tuple, got %r" % (type(marking_lines).__name__,)
        )
    if len(marking_lines) == 0:
        raise ValueError("a mark must carry at least one line")
    height = _positive(character_height_mm, "character_height_mm")
    longest = 0
    for line in marking_lines:
        if not isinstance(line, str) or not line.strip():
            raise ValueError("every marking line must be a non-empty string, got %r" % (line,))
        longest = max(longest, len(line))
    width = longest * height * CHARACTER_WIDTH_RATIO + 2.0 * MARKING_MARGIN_MM
    depth = len(marking_lines) * height * LINE_PITCH_RATIO + 2.0 * MARKING_MARGIN_MM
    return {"width_mm": width, "height_mm": depth, "longest_line": longest,
            "line_count": len(marking_lines)}


def face_dimensions(face):
    """Validate a package face the mark could be assigned to."""
    if not isinstance(face, dict):
        raise ValueError("face must be a mapping, got %r" % (type(face).__name__,))
    return (
        _positive(face.get("width_mm"), "face width_mm"),
        _positive(face.get("height_mm"), "face height_mm"),
    )


def marking_fits_face(marking_lines, character_height_mm, face):
    """Whether the mark fits the face, and which dimension is short if not."""
    footprint = required_marking_footprint_mm(marking_lines, character_height_mm)
    width, depth = face_dimensions(face)
    short = []
    if footprint["width_mm"] > width + MARKING_TOLERANCE:
        short.append("face-too-narrow-for-mark")
    if footprint["height_mm"] > depth + MARKING_TOLERANCE:
        short.append("face-too-short-for-mark")
    return {
        "footprint": footprint,
        "face_width_mm": width,
        "face_height_mm": depth,
        "fits": len(short) == 0,
        "findings": short,
    }


def assess_placement(location, lid_is_removable, body_fits):
    """Findings raised by where the scheme puts the mark."""
    if location not in MARKING_LOCATIONS:
        raise ValueError(
            "unknown marking location %r (known: %s)"
            % (location, ", ".join(sorted(MARKING_LOCATIONS)))
        )
    if not isinstance(lid_is_removable, bool) or not isinstance(body_fits, bool):
        raise ValueError("lid_is_removable and body_fits must be booleans")
    findings = []
    if location == "package-lid" and lid_is_removable:
        findings.append("identification-on-removable-lid")
    if location == "carrier-or-container-only" and body_fits:
        findings.append("body-marking-omitted-although-the-face-had-room")
    return findings


def traceability_findings(traceability, location):
    """Findings raised by the records the mark is supposed to lead back to."""
    if not isinstance(traceability, dict):
        raise ValueError(
            "traceability must be a mapping, got %r" % (type(traceability).__name__,)
        )
    findings = []
    if not _flag(traceability, "lot_record_linked"):
        findings.append("mark-not-linked-to-the-lot-record")
    if not _flag(traceability, "serial_register_maintained"):
        findings.append("no-serial-register-behind-the-mark")
    container = _flag(traceability, "container_record_maintained")
    if location == "carrier-or-container-only" and not container:
        findings.append("container-identification-without-a-container-record")
    return findings


def provision_element_weight(name):
    """Weight of one provision element; unknown names are rejected."""
    if name not in PROVISION_ELEMENT_WEIGHTS:
        raise ValueError(
            "unknown provision element %r (known: %s)"
            % (name, ", ".join(sorted(PROVISION_ELEMENT_WEIGHTS)))
        )
    return PROVISION_ELEMENT_WEIGHTS[name]


def provision_state_credit(state):
    """Credit a provision-element state earns."""
    if state not in PROVISION_STATE_CREDIT:
        raise ValueError(
            "unknown provision state %r (known: %s)"
            % (state, ", ".join(sorted(PROVISION_STATE_CREDIT)))
        )
    return PROVISION_STATE_CREDIT[state]


def normalize_provision(raw):
    """Validate one provision-element record and fill its default state."""
    if not isinstance(raw, dict):
        raise ValueError("provision must be a mapping, got %r" % (type(raw).__name__,))
    name = raw.get("element")
    provision_element_weight(name)  # validation only
    state = raw.get("state", "not-defined")
    provision_state_credit(state)  # validation only
    return {"element": name, "state": state}


def assess_provision(raw):
    """Grade one provision element into a credit and its findings."""
    record = normalize_provision(raw)
    name = record["element"]
    state = record["state"]
    weight = provision_element_weight(name)
    credit = provision_state_credit(state)
    findings = []
    if state == "defined-with-observation":
        findings.append("provision-observation-open")
    elif state == "deficient":
        findings.append("provision-deficient")
    elif state == "not-defined":
        findings.append("provision-not-defined")
    mandatory = name in MANDATORY_PROVISION_ELEMENTS
    return {
        "element": name,
        "state": state,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory": mandatory,
        "mandatory_missing": mandatory and state == "not-defined",
        "mandatory_deficient": mandatory and state == "deficient",
        "findings": findings,
    }


def marking_provision_index(records):
    """Weighted credit of a set of graded provisions over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("records must be a list or tuple, got %r" % (type(records).__name__,))
    if len(records) == 0:
        raise ValueError("a marking scheme must carry at least one provision")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total provision weight must be positive")
    return earned / total_weight


def assess_marking_provisions(product_id, scheme, exposures, body_face, traceability, provisions):
    """Grade a whole hybrid marking scheme and name one verdict."""
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("product_id must be a non-empty string, got %r" % (product_id,))
    if not isinstance(scheme, dict):
        raise ValueError("scheme must be a mapping, got %r" % (type(scheme).__name__,))
    if not isinstance(provisions, (list, tuple)):
        raise ValueError("provisions must be a list or tuple, got %r" % (type(provisions).__name__,))

    method = scheme.get("method")
    surface = scheme.get("surface")
    location = scheme.get("location")
    suits = method_suits_surface(method, surface)
    permanence = method_permanence_grade(method)
    demanded = required_permanence_grade(exposures)
    fit = marking_fits_face(
        scheme.get("marking_lines"), scheme.get("character_height_mm"), body_face
    )
    placement_findings = assess_placement(
        location, _flag(scheme, "lid_is_removable"), fit["fits"]
    )
    record_findings = traceability_findings(traceability, location)

    declared = {}
    for raw in provisions:
        record = normalize_provision(raw)
        if record["element"] in declared:
            raise ValueError("duplicate provision element %r" % (record["element"],))
        declared[record["element"]] = record
    provision_records = []
    for name in sorted(PROVISION_ELEMENT_WEIGHTS):
        provision_records.append(assess_provision(declared.get(name, {"element": name})))
    index = marking_provision_index(provision_records)

    findings = []
    if not suits:
        findings.append(
            {
                "item": method,
                "finding": "marking-method-not-applicable-to-the-surface",
                "detail": surface,
            }
        )
    if permanence < demanded:
        findings.append(
            {
                "item": method,
                "finding": "marking-permanence-below-the-processing-still-ahead",
                "detail": "grade %d against %d demanded" % (permanence, demanded),
            }
        )
    if location == "package-body" and not fit["fits"]:
        for finding in fit["findings"]:
            findings.append(
                {
                    "item": "package-body",
                    "finding": finding,
                    "detail": "%.2f x %.2f mm needed"
                    % (fit["footprint"]["width_mm"], fit["footprint"]["height_mm"]),
                }
            )
    for finding in placement_findings:
        findings.append({"item": location, "finding": finding, "detail": location})
    for finding in record_findings:
        findings.append({"item": "traceability", "finding": finding, "detail": location})
    for record in provision_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["element"], "finding": finding, "detail": record["state"]}
            )

    incomplete = any(record["mandatory_missing"] for record in provision_records)
    inadequate = (
        not suits
        or permanence < demanded
        or (location == "package-body" and not fit["fits"])
        or bool(placement_findings)
        or bool(record_findings)
        or any(record["mandatory_deficient"] for record in provision_records)
        or index < ACCEPTANCE_INDEX - MARKING_TOLERANCE
    )
    if incomplete:
        verdict = "marking-provisions-assessment-incomplete"
    elif inadequate:
        verdict = "marking-provisions-inadequate"
    elif findings:
        verdict = "marking-provisions-adequate-with-open-actions"
    else:
        verdict = "marking-provisions-adequate"
    return {
        "product_id": product_id,
        "method": method,
        "surface": surface,
        "location": location,
        "method_suits_surface": suits,
        "permanence_grade": permanence,
        "required_permanence_grade": demanded,
        "fit": fit,
        "provision_records": provision_records,
        "marking_provision_index": index,
        "findings": findings,
        "verdict": verdict,
        "scheme_accepted": verdict
        in (
            "marking-provisions-adequate",
            "marking-provisions-adequate-with-open-actions",
        ),
    }
