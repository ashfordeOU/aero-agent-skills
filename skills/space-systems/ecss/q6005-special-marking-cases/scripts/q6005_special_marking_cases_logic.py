"""Special marking cases: identifying a hybrid that cannot carry a direct body mark.

Anchor: ECSS-Q-ST-60-05 clause 10.2.2 (the alternative identification
arrangements allowed when the size of the package, or the finish of the
surface that would carry the mark, prevents the normal direct marking of the
delivered unit).

Offline, deterministic, python3 standard library only.

Procedure implemented here (paraphrased, no standard text reproduced):

* A special marking case has to be earned, not declared. Either the free area
  left on the body cannot hold the mandatory field set at the smallest
  legible character height, or the surface finish cannot hold lettering that
  survives handling. If neither holds, the unit is a normal direct-marking
  case and the alternative is a shortcut.
* The footprint of the mark is computed, not eyeballed. The mandatory fields
  carry a character count, characters have a width set by the height, lines
  need spacing, and a margin has to stay clear of the seal and the leads.
* The alternatives are ranked by how hard they are to separate from the unit.
  A permanent tag fixed to the body travels with it; a mark on the sealed
  individual container travels with the container; a mark on a multi-unit
  intermediate package identifies a group rather than a unit; a register
  entry keyed on a carrier position identifies nothing once the carrier is
  unloaded. The best arrangement the case admits is the one to use.
* Every arrangement below a direct body mark loses something, so it carries
  compensating controls: a serial register, a delivery document naming the
  arrangement, a rule that the identification is never separated from the
  unit, and a re-identification step at the next assembly level. A weaker
  arrangement needs more of them, not fewer.
* The identification-adequacy index is weighted credit over total weight. It
  ranks what is outstanding; an unsubstantiated special case, an arrangement
  the case does not admit, or a missing mandatory control decides the outcome
  on its own, at any index.
"""

from __future__ import annotations

import math

# Fields the identification has to carry, and the characters each needs.
MANDATORY_IDENTIFICATION_FIELDS = {
    "manufacturer-identification": 6,
    "part-or-type-number": 12,
    "lot-date-code": 6,
    "serial-number": 6,
}

# Lettering below this height is not read without aid, whatever the package.
MINIMUM_CHARACTER_HEIGHT_MM = 0.30

# Character cell geometry, as multiples of the character height.
CHARACTER_WIDTH_RATIO = 0.62
CHARACTER_PITCH_RATIO = 0.25
LINE_PITCH_RATIO = 0.45

# Edge band that stays clear of the seal ring and the lead exits, per side.
MARKING_EDGE_MARGIN_MM = 0.25

# Finishes that cannot hold a durable direct mark on the body.
DIRECT_MARKING_INCOMPATIBLE_FINISHES = (
    "soft-polymer-overcoat",
    "unplated-porous-ceramic",
    "thin-gold-flash-over-nickel",
    "textured-conformal-coating",
)
DIRECT_MARKING_COMPATIBLE_FINISHES = (
    "plated-metal-lid",
    "glazed-ceramic-body",
    "anodized-metal-body",
    "sealed-glass-lid",
)

# Alternative arrangements, ranked by how hard the identification is to
# separate from the unit it identifies. Lower rank is better.
IDENTIFICATION_ARRANGEMENTS = {
    "direct-body-marking": 0,
    "permanent-attached-tag": 1,
    "individual-sealed-container-marking": 2,
    "intermediate-package-marking": 3,
    "carrier-position-register-only": 4,
}

# The arrangement a case may fall back to, given why direct marking failed.
AREA_LIMITED_ADMISSIBLE = (
    "permanent-attached-tag",
    "individual-sealed-container-marking",
    "intermediate-package-marking",
)
FINISH_LIMITED_ADMISSIBLE = (
    "permanent-attached-tag",
    "individual-sealed-container-marking",
)

# Controls that compensate for identification that is not on the body, and
# the weakest arrangement each one is mandatory from.
COMPENSATING_CONTROLS = {
    "serial-register-held-by-manufacturer": 1,
    "arrangement-named-in-delivery-documentation": 1,
    "identification-never-separated-from-unit": 2,
    "re-identification-at-next-assembly-level": 3,
}

CONTROL_WEIGHTS = {
    "serial-register-held-by-manufacturer": 1.0,
    "arrangement-named-in-delivery-documentation": 0.8,
    "identification-never-separated-from-unit": 1.0,
    "re-identification-at-next-assembly-level": 0.9,
}

CONTROL_STATE_CREDIT = {
    "implemented-and-evidenced": 1.0,
    "implemented-not-evidenced": 0.7,
    "planned-only": 0.2,
    "absent": 0.0,
}

# Identification-adequacy index an acceptable arrangement has to reach. The
# index is taken over the controls the selected arrangement makes mandatory,
# so a weaker arrangement is graded against the longer list it has to satisfy.
ACCEPTANCE_INDEX = 0.80

# Areas and indices are sums of products; a case meant to sit on a bound can
# land a few units in the last place away from it.
MARKING_TOLERANCE = 1e-9

VERDICTS = (
    "direct-body-marking-required",
    "alternative-identification-accepted",
    "alternative-identification-accepted-with-open-actions",
    "alternative-identification-not-accepted",
    "special-marking-case-not-substantiated",
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
    """Return ``value`` as a strictly positive finite float or raise."""
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _count(value, label):
    """Return ``value`` as a positive whole count or raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (label, value))
    return value


def mark_line_length_mm(characters, character_height_mm):
    """Width one line of ``characters`` occupies at a given character height."""
    count = _count(characters, "characters")
    height = _positive(character_height_mm, "character_height_mm")
    cell = height * (CHARACTER_WIDTH_RATIO + CHARACTER_PITCH_RATIO)
    return count * cell - height * CHARACTER_PITCH_RATIO


def required_mark_area_mm2(character_height_mm, fields=None):
    """Body area the mandatory field set needs, one field to a line."""
    height = _positive(character_height_mm, "character_height_mm")
    names = tuple(MANDATORY_IDENTIFICATION_FIELDS) if fields is None else tuple(fields)
    if len(names) == 0:
        raise ValueError("a mark must carry at least one field")
    widest = 0.0
    for name in names:
        if name not in MANDATORY_IDENTIFICATION_FIELDS:
            raise ValueError(
                "unknown identification field %r (known: %s)"
                % (name, ", ".join(sorted(MANDATORY_IDENTIFICATION_FIELDS)))
            )
        widest = max(
            widest,
            mark_line_length_mm(MANDATORY_IDENTIFICATION_FIELDS[name], height),
        )
    lines = len(names)
    block_height = lines * height + (lines - 1) * height * LINE_PITCH_RATIO
    width = widest + 2.0 * MARKING_EDGE_MARGIN_MM
    depth = block_height + 2.0 * MARKING_EDGE_MARGIN_MM
    return width * depth


def finish_permits_direct_marking(finish):
    """True when a body finish can hold a durable direct mark."""
    if not isinstance(finish, str) or not finish.strip():
        raise ValueError("finish must be a non-empty string, got %r" % (finish,))
    if finish in DIRECT_MARKING_COMPATIBLE_FINISHES:
        return True
    if finish in DIRECT_MARKING_INCOMPATIBLE_FINISHES:
        return False
    raise ValueError(
        "unknown body finish %r (known: %s)"
        % (
            finish,
            ", ".join(
                sorted(
                    DIRECT_MARKING_COMPATIBLE_FINISHES
                    + DIRECT_MARKING_INCOMPATIBLE_FINISHES
                )
            ),
        )
    )


def special_case_reason(free_body_area_mm2, finish, character_height_mm=None):
    """Why direct body marking fails here, or None when it does not fail.

    Area is tested at the smallest legible character height, because a case
    that fits at that height is a normal marking case with small lettering.
    """
    area = _positive(free_body_area_mm2, "free_body_area_mm2")
    height = (
        MINIMUM_CHARACTER_HEIGHT_MM
        if character_height_mm is None
        else _positive(character_height_mm, "character_height_mm")
    )
    if height < MINIMUM_CHARACTER_HEIGHT_MM - MARKING_TOLERANCE:
        raise ValueError(
            "character_height_mm %r is below the legibility floor %r"
            % (character_height_mm, MINIMUM_CHARACTER_HEIGHT_MM)
        )
    if not finish_permits_direct_marking(finish):
        return "body-finish-cannot-hold-a-mark"
    needed = required_mark_area_mm2(height)
    if area < needed - MARKING_TOLERANCE:
        return "free-body-area-too-small"
    return None


def admissible_arrangements(reason):
    """Arrangements a substantiated special case may fall back to."""
    if reason is None:
        return ("direct-body-marking",)
    if reason == "free-body-area-too-small":
        return AREA_LIMITED_ADMISSIBLE
    if reason == "body-finish-cannot-hold-a-mark":
        return FINISH_LIMITED_ADMISSIBLE
    raise ValueError("unknown special marking reason %r" % (reason,))


def arrangement_rank(arrangement):
    """Separability rank of an identification arrangement; lower is better."""
    if arrangement not in IDENTIFICATION_ARRANGEMENTS:
        raise ValueError(
            "unknown identification arrangement %r (known: %s)"
            % (arrangement, ", ".join(sorted(IDENTIFICATION_ARRANGEMENTS)))
        )
    return IDENTIFICATION_ARRANGEMENTS[arrangement]


def select_identification_arrangement(reason, available):
    """Best available arrangement the case admits, or None when none does."""
    if not isinstance(available, (list, tuple)):
        raise ValueError(
            "available must be a list or tuple, got %r" % (type(available).__name__,)
        )
    if len(available) == 0:
        raise ValueError("at least one arrangement must be available")
    allowed = admissible_arrangements(reason)
    candidates = []
    for arrangement in available:
        rank = arrangement_rank(arrangement)
        if arrangement in allowed:
            candidates.append((rank, arrangement))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][1]


def required_controls(arrangement):
    """Compensating controls mandatory for an arrangement, in a stable order."""
    rank = arrangement_rank(arrangement)
    return tuple(
        name
        for name in sorted(COMPENSATING_CONTROLS)
        if rank >= COMPENSATING_CONTROLS[name]
    )


def control_state_credit(state):
    """Credit a compensating-control state earns."""
    if state not in CONTROL_STATE_CREDIT:
        raise ValueError(
            "unknown control state %r (known: %s)"
            % (state, ", ".join(sorted(CONTROL_STATE_CREDIT)))
        )
    return CONTROL_STATE_CREDIT[state]


def assess_control(name, state, arrangement):
    """Grade one compensating control into a credit and its findings."""
    if name not in CONTROL_WEIGHTS:
        raise ValueError(
            "unknown compensating control %r (known: %s)"
            % (name, ", ".join(sorted(CONTROL_WEIGHTS)))
        )
    credit = control_state_credit(state)
    weight = CONTROL_WEIGHTS[name]
    mandatory = name in required_controls(arrangement)
    findings = []
    if state == "absent":
        findings.append("control-absent")
    elif state == "planned-only":
        findings.append("control-planned-only")
    elif state == "implemented-not-evidenced":
        findings.append("control-not-evidenced")
    mandatory_missing = mandatory and state in ("absent", "planned-only")
    if mandatory_missing:
        findings.append("mandatory-compensating-control-missing")
    return {
        "control": name,
        "state": state,
        "mandatory": mandatory,
        "weight": weight,
        "credit": credit,
        "weighted_credit": weight * credit,
        "mandatory_missing": mandatory_missing,
        "findings": findings,
    }


def identification_adequacy_index(records):
    """Weighted credit of a set of graded controls over the total weight."""
    if not isinstance(records, (list, tuple)):
        raise ValueError(
            "records must be a list or tuple, got %r" % (type(records).__name__,)
        )
    if len(records) == 0:
        raise ValueError("an arrangement must carry at least one control")
    total_weight = 0.0
    earned = 0.0
    for record in records:
        total_weight += _real(record["weight"], "weight")
        earned += _real(record["weighted_credit"], "weighted_credit")
    if total_weight <= 0.0:
        raise ValueError("total control weight must be positive")
    return earned / total_weight


def assess_special_marking_case(
    unit_id,
    free_body_area_mm2,
    body_finish,
    available_arrangements,
    controls=None,
    proposed_arrangement=None,
):
    """Grade one special marking case end to end and name a single verdict."""
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id must be a non-empty string, got %r" % (unit_id,))
    if controls is None:
        controls = {}
    if not isinstance(controls, dict):
        raise ValueError("controls must be a mapping, got %r" % (type(controls).__name__,))

    reason = special_case_reason(free_body_area_mm2, body_finish)
    findings = []

    if reason is None:
        if proposed_arrangement in (None, "direct-body-marking"):
            return {
                "unit_id": unit_id,
                "special_case_reason": None,
                "selected_arrangement": "direct-body-marking",
                "required_mark_area_mm2": required_mark_area_mm2(
                    MINIMUM_CHARACTER_HEIGHT_MM
                ),
                "control_records": [],
                "identification_adequacy_index": 1.0,
                "findings": [],
                "verdict": "direct-body-marking-required",
                "identification_accepted": True,
            }
        arrangement_rank(proposed_arrangement)  # validation only
        return {
            "unit_id": unit_id,
            "special_case_reason": None,
            "selected_arrangement": None,
            "required_mark_area_mm2": required_mark_area_mm2(MINIMUM_CHARACTER_HEIGHT_MM),
            "control_records": [],
            "identification_adequacy_index": 0.0,
            "findings": [
                {
                    "item": proposed_arrangement,
                    "finding": "special-case-not-substantiated",
                    "detail": "the body can carry a direct mark",
                }
            ],
            "verdict": "special-marking-case-not-substantiated",
            "identification_accepted": False,
        }

    selected = select_identification_arrangement(reason, available_arrangements)
    if selected is None:
        return {
            "unit_id": unit_id,
            "special_case_reason": reason,
            "selected_arrangement": None,
            "required_mark_area_mm2": required_mark_area_mm2(MINIMUM_CHARACTER_HEIGHT_MM),
            "control_records": [],
            "identification_adequacy_index": 0.0,
            "findings": [
                {
                    "item": "arrangement",
                    "finding": "no-admissible-arrangement-available",
                    "detail": reason,
                }
            ],
            "verdict": "alternative-identification-not-accepted",
            "identification_accepted": False,
        }

    if proposed_arrangement is not None:
        proposed_rank = arrangement_rank(proposed_arrangement)
        if proposed_arrangement not in admissible_arrangements(reason):
            findings.append(
                {
                    "item": proposed_arrangement,
                    "finding": "arrangement-not-admissible-for-this-case",
                    "detail": reason,
                }
            )
        elif proposed_rank > arrangement_rank(selected):
            findings.append(
                {
                    "item": proposed_arrangement,
                    "finding": "weaker-arrangement-than-available",
                    "detail": "%s was available" % (selected,),
                }
            )
        else:
            selected = proposed_arrangement

    for name in controls:
        if name not in CONTROL_WEIGHTS:
            raise ValueError(
                "unknown compensating control %r (known: %s)"
                % (name, ", ".join(sorted(CONTROL_WEIGHTS)))
            )
    mandatory = required_controls(selected)
    control_records = []
    for name in mandatory:
        state = controls.get(name, "absent")
        if not isinstance(state, str):
            raise ValueError("control state must be a string, got %r" % (state,))
        control_records.append(assess_control(name, state, selected))
    additional = sorted(name for name in controls if name not in mandatory)

    index = identification_adequacy_index(control_records)
    for record in control_records:
        for finding in record["findings"]:
            findings.append(
                {"item": record["control"], "finding": finding, "detail": record["state"]}
            )

    blocked = any(entry["finding"] == "arrangement-not-admissible-for-this-case" for entry in findings)
    missing_mandatory = any(r["mandatory_missing"] for r in control_records)
    if blocked or missing_mandatory or index < ACCEPTANCE_INDEX - MARKING_TOLERANCE:
        verdict = "alternative-identification-not-accepted"
    elif findings:
        verdict = "alternative-identification-accepted-with-open-actions"
    else:
        verdict = "alternative-identification-accepted"

    return {
        "unit_id": unit_id,
        "special_case_reason": reason,
        "selected_arrangement": selected,
        "required_mark_area_mm2": required_mark_area_mm2(MINIMUM_CHARACTER_HEIGHT_MM),
        "mandatory_controls": list(mandatory),
        "additional_controls": additional,
        "control_records": control_records,
        "identification_adequacy_index": index,
        "findings": findings,
        "verdict": verdict,
        "identification_accepted": verdict
        in (
            "alternative-identification-accepted",
            "alternative-identification-accepted-with-open-actions",
        ),
    }
