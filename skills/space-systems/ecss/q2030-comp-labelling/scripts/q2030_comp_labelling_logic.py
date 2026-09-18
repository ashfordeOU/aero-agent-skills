"""Complementary labelling and marking requirements for a space harness.

Anchor: ECSS-Q-ST-20-30C clause 7.6 (complementary ECSS requirements on the
content, format and durability of harness labelling and marking). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Parse a harness label into the fields the project's format prescribes and
   refuse a token that does not decompose: a label that cannot be parsed
   cannot be traced, whatever it reads like.
2. Grade the content: every mandatory field present and non-empty, each field
   matching the character set and length its position carries.
3. Grade the format on the assembly: character height against the distance the
   label is read from, both-end marking of a routed wire, and the placement
   window from the termination the label belongs to.
4. Grade durability from the abrasion and solvent exposure the marking
   survived while staying legible, against what the project requires.
5. Enforce uniqueness across the harness, since two identical labels on
   different wires defeat the only purpose the label has.
6. Roll every label record up into one assessment with named findings.
"""

import math
import re

__all__ = [
    "HEIGHT_TOLERANCE_MM",
    "DEFAULT_FIELD_ORDER",
    "FIELD_PATTERNS",
    "parse_label",
    "validate_label_content",
    "minimum_character_height_mm",
    "character_height_adequate",
    "placement_in_window",
    "durability_verdict",
    "evaluate_label",
    "find_duplicate_labels",
    "assess_label_set",
]

# A character height or a placement distance landing exactly on a bound meets
# it; the equality is a representation question absorbed here.
HEIGHT_TOLERANCE_MM = 1e-9

# The field order a harness label token decomposes into.
DEFAULT_FIELD_ORDER = ("project", "harness", "connector", "serial")

# Character set and length each field position carries.
FIELD_PATTERNS = {
    "project": re.compile(r"^[A-Z]{2,6}$"),
    "harness": re.compile(r"^W[0-9]{2,4}$"),
    "connector": re.compile(r"^[JP][0-9]{1,3}$"),
    "serial": re.compile(r"^[0-9]{1,4}$"),
}

# Marking read at this reference distance needs the reference character height;
# the requirement scales with the distance it is actually read from.
REFERENCE_VIEW_DISTANCE_MM = 300.0
REFERENCE_CHARACTER_HEIGHT_MM = 1.5


def _require_number(value, label, positive=True):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _require_int(value, label, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def parse_label(token, field_order=DEFAULT_FIELD_ORDER, separator="-"):
    """Decompose a label token into its prescribed fields; refuse a token that will not."""
    if not isinstance(token, str):
        raise ValueError("label token must be a string")
    text = token.strip()
    if not text:
        raise ValueError("label token must not be blank")
    if not isinstance(separator, str) or len(separator) != 1:
        raise ValueError("separator must be a single character")
    if not isinstance(field_order, (list, tuple)) or not field_order:
        raise ValueError("field_order must be a non-empty sequence")
    parts = text.split(separator)
    if len(parts) != len(field_order):
        raise ValueError(
            "label %r decomposes into %d field(s); the format prescribes %d"
            % (token, len(parts), len(field_order))
        )
    fields = {}
    for name, part in zip(field_order, parts):
        if not part:
            raise ValueError("label %r has an empty '%s' field" % (token, name))
        fields[name] = part
    return fields


def validate_label_content(token, field_order=DEFAULT_FIELD_ORDER, patterns=None,
                           separator="-"):
    """Return the parsed fields plus any content finding for one label token."""
    patterns = FIELD_PATTERNS if patterns is None else patterns
    if not isinstance(patterns, dict):
        raise ValueError("patterns must be a mapping of field name to compiled pattern")
    fields = parse_label(token, field_order, separator)
    findings = []
    for name, value in fields.items():
        pattern = patterns.get(name)
        if pattern is None:
            continue
        if not pattern.match(value):
            findings.append(
                "label %r field '%s' value %r does not match the prescribed form"
                % (token, name, value)
            )
    return {"token": token.strip(), "fields": fields, "findings": findings}


def minimum_character_height_mm(view_distance_mm,
                                reference_distance_mm=REFERENCE_VIEW_DISTANCE_MM,
                                reference_height_mm=REFERENCE_CHARACTER_HEIGHT_MM):
    """Return the character height marking needs to stay readable at a distance."""
    distance = _require_number(view_distance_mm, "view_distance_mm")
    reference_distance = _require_number(reference_distance_mm, "reference_distance_mm")
    reference_height = _require_number(reference_height_mm, "reference_height_mm")
    return reference_height * (distance / reference_distance)


def character_height_adequate(actual_height_mm, view_distance_mm, **kwargs):
    """Return True when the marking is tall enough for the distance it is read from."""
    actual = _require_number(actual_height_mm, "actual_height_mm")
    needed = minimum_character_height_mm(view_distance_mm, **kwargs)
    return actual >= needed - HEIGHT_TOLERANCE_MM


def placement_in_window(distance_from_termination_mm, window_mm):
    """Return True when a label sits inside the placement window from its termination."""
    distance = _require_number(distance_from_termination_mm, "distance_from_termination_mm",
                               positive=False)
    if distance < 0.0:
        raise ValueError("distance_from_termination_mm must not be negative")
    if not isinstance(window_mm, (list, tuple)) or len(window_mm) != 2:
        raise ValueError("window_mm must be a (low, high) pair")
    low = _require_number(window_mm[0], "window low", positive=False)
    high = _require_number(window_mm[1], "window high", positive=False)
    if low < 0.0 or high <= low:
        raise ValueError("window_mm must be a non-negative increasing pair")
    return (distance >= low - HEIGHT_TOLERANCE_MM) and (distance <= high + HEIGHT_TOLERANCE_MM)


def durability_verdict(abrasion_cycles_legible, solvent_cycles_legible,
                       required_abrasion_cycles, required_solvent_cycles):
    """Grade the marking's durability evidence against what the project requires."""
    abrasion = _require_int(abrasion_cycles_legible, "abrasion_cycles_legible")
    solvent = _require_int(solvent_cycles_legible, "solvent_cycles_legible")
    required_abrasion = _require_int(required_abrasion_cycles, "required_abrasion_cycles", 1)
    required_solvent = _require_int(required_solvent_cycles, "required_solvent_cycles", 1)
    findings = []
    if abrasion < required_abrasion:
        findings.append(
            "marking stayed legible for %d abrasion cycle(s) against %d required"
            % (abrasion, required_abrasion)
        )
    if solvent < required_solvent:
        findings.append(
            "marking stayed legible for %d solvent cycle(s) against %d required"
            % (solvent, required_solvent)
        )
    return {
        "abrasion_margin": abrasion - required_abrasion,
        "solvent_margin": solvent - required_solvent,
        "durable": not findings,
        "findings": findings,
    }


def evaluate_label(record, requirements):
    """Evaluate one label record against the content, format and durability requirements."""
    if not isinstance(record, dict):
        raise ValueError("label record must be a mapping")
    if not isinstance(requirements, dict):
        raise ValueError("requirements must be a mapping")
    for key in ("id", "token", "character_height_mm", "view_distance_mm",
                "distance_from_termination_mm"):
        if key not in record:
            raise ValueError("label record missing required key '%s'" % key)
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("label record id must be a non-empty string")
    content = validate_label_content(
        record["token"],
        requirements.get("field_order", DEFAULT_FIELD_ORDER),
        requirements.get("patterns"),
        requirements.get("separator", "-"),
    )
    findings = list(content["findings"])
    if not character_height_adequate(record["character_height_mm"], record["view_distance_mm"]):
        findings.append(
            "label %s character height %.3f mm is short of the %.3f mm the %.0f mm read distance needs"
            % (
                identifier,
                float(record["character_height_mm"]),
                minimum_character_height_mm(record["view_distance_mm"]),
                float(record["view_distance_mm"]),
            )
        )
    window = requirements.get("placement_window_mm", (10.0, 60.0))
    if not placement_in_window(record["distance_from_termination_mm"], window):
        findings.append(
            "label %s sits %.1f mm from its termination, outside the [%.1f, %.1f] mm window"
            % (
                identifier,
                float(record["distance_from_termination_mm"]),
                float(window[0]),
                float(window[1]),
            )
        )
    if record.get("routed_through_bundle", False) and not record.get("marked_both_ends", False):
        findings.append("label %s marks one end only of a wire routed through a bundle" % identifier)
    durability = durability_verdict(
        record.get("abrasion_cycles_legible", 0),
        record.get("solvent_cycles_legible", 0),
        requirements.get("required_abrasion_cycles", 10),
        requirements.get("required_solvent_cycles", 3),
    )
    for finding in durability["findings"]:
        findings.append("label %s %s" % (identifier, finding))
    return {
        "id": identifier,
        "token": content["token"],
        "fields": content["fields"],
        "durability": durability,
        "findings": findings,
        "conforming": not findings,
    }


def find_duplicate_labels(tokens):
    """Return the label tokens that appear more than once in a harness."""
    if not isinstance(tokens, (list, tuple)):
        raise ValueError("tokens must be a sequence of label tokens")
    counts = {}
    for token in tokens:
        if not isinstance(token, str):
            raise ValueError("every label token must be a string")
        key = token.strip()
        counts[key] = counts.get(key, 0) + 1
    return sorted(token for token, count in counts.items() if count > 1)


def assess_label_set(records, requirements=None):
    """Assess a whole harness label set and return one rolled-up verdict."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of label records")
    requirements = {} if requirements is None else requirements
    evaluated = []
    seen = set()
    for record in records:
        result = evaluate_label(record, requirements)
        if result["id"] in seen:
            raise ValueError("duplicate label record identifier %r" % result["id"])
        seen.add(result["id"])
        evaluated.append(result)
    findings = []
    for result in evaluated:
        findings.extend(result["findings"])
    duplicates = find_duplicate_labels([r["token"] for r in evaluated])
    for token in duplicates:
        findings.append("label token %r is carried by more than one wire" % token)
    return {
        "records": evaluated,
        "evaluated_count": len(evaluated),
        "conforming_count": len([r for r in evaluated if r["conforming"]]),
        "duplicate_tokens": duplicates,
        "findings": findings,
        "compliant": not findings,
    }
