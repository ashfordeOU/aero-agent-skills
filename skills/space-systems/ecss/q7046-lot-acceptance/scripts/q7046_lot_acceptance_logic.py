#!/usr/bin/env python3
"""Lot acceptance sampling for procured threaded fasteners.

Anchor: ECSS-Q-ST-70-46 acceptance clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Acceptance runs per manufacturing lot, and what the lot owes depends on
the criticality of the fastener in it:

critical        the failure of one fastener loses the function, so the
                lot is inspected whole. There is no sample to argue
                about and no defective is allowed.
major           a tight quality limit, entered at tightened severity, so
                zero or few defectives are allowed in a large sample.
minor           an ordinary quality limit under normal severity.

The sample itself is drawn by the general-level-two letter for the lot
size, which is the standard attribute plan: the letter fixes the sample,
the quality limit fixes how many defectives that sample may carry, and
where the letter's sample is too small to discriminate at the quality
limit asked for, the plan steps up to the next larger sample rather than
pretending the small one resolves it.

Severity is not a property of the lot. It is carried between lots by the
supplier's recent record: repeated rejects tighten the plan, a run of
clean lots relaxes it, and a tightened supplier that does not recover
has its inspection suspended rather than continued indefinitely.

Standard library only, offline, deterministic. All arithmetic is
integer, so a plan computed here is the plan computed anywhere.
"""

from __future__ import annotations

CRITICALITIES = ("critical", "major", "minor")

SEVERITY_TIGHTENED = "tightened"
SEVERITY_NORMAL = "normal"
SEVERITY_REDUCED = "reduced"
SEVERITY_SUSPENDED = "suspended"
SEVERITIES = (
    SEVERITY_TIGHTENED,
    SEVERITY_NORMAL,
    SEVERITY_REDUCED,
    SEVERITY_SUSPENDED,
)

LOT_ACCEPT = "accept"
LOT_REJECT = "reject"

# Sample size code letters for general inspection level two, as
# (inclusive lot lower bound, inclusive lot upper bound, letter).
_CODE_LETTER_BANDS = (
    (2, 8, "A"),
    (9, 15, "B"),
    (16, 25, "C"),
    (26, 50, "D"),
    (51, 90, "E"),
    (91, 150, "F"),
    (151, 280, "G"),
    (281, 500, "H"),
    (501, 1200, "J"),
    (1201, 3200, "K"),
    (3201, 10000, "L"),
    (10001, 35000, "M"),
    (35001, 150000, "N"),
    (150001, 500000, "P"),
)
_LARGEST_LETTER = "Q"

_LETTER_SAMPLE = {
    "A": 2,
    "B": 3,
    "C": 5,
    "D": 8,
    "E": 13,
    "F": 20,
    "G": 32,
    "H": 50,
    "J": 80,
    "K": 125,
    "L": 200,
    "M": 315,
    "N": 500,
    "P": 800,
    "Q": 1250,
}

_LETTER_ORDER = ("A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N", "P", "Q")

# Acceptance numbers by quality limit and sample size. None marks a
# sample too small to discriminate at that quality limit; the plan steps
# up to the next larger sample instead of using it.
_ACCEPTANCE = {
    "0.65": {
        2: None, 3: None, 5: None, 8: None, 13: None, 20: None, 32: None,
        50: 0, 80: 1, 125: 2, 200: 3, 315: 5, 500: 7, 800: 10, 1250: 14,
    },
    "1.0": {
        2: None, 3: None, 5: None, 8: None, 13: None, 20: None,
        32: 0, 50: 1, 80: 2, 125: 3, 200: 5, 315: 7, 500: 10, 800: 14,
        1250: 21,
    },
    "2.5": {
        2: None, 3: None, 5: None, 8: None,
        13: 0, 20: 1, 32: 2, 50: 3, 80: 5, 125: 7, 200: 10, 315: 14,
        500: 21, 800: 21, 1250: 21,
    },
}

_CRITICALITY_PLAN = {
    "critical": {"quality_limit": None, "severity": SEVERITY_TIGHTENED,
                 "hundred_percent": True},
    "major": {"quality_limit": "1.0", "severity": SEVERITY_TIGHTENED,
              "hundred_percent": False},
    "minor": {"quality_limit": "2.5", "severity": SEVERITY_NORMAL,
              "hundred_percent": False},
}

# A tightened plan moves one quality limit finer; a reduced plan moves
# one coarser. Nothing is finer than the finest limit carried here.
_TIGHTER = {"2.5": "1.0", "1.0": "0.65", "0.65": "0.65"}
_LOOSER = {"0.65": "1.0", "1.0": "2.5", "2.5": "2.5"}


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_count(name, value, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer count, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    return value


def sample_code_letter(lot_size):
    """Sample size code letter for a lot at general inspection level two."""
    lot = _require_count("lot_size", lot_size, minimum=1)
    if lot == 1:
        raise ValueError(
            "a lot of one cannot be sampled; inspect it whole instead"
        )
    for low, high, letter in _CODE_LETTER_BANDS:
        if low <= lot <= high:
            return letter
    return _LARGEST_LETTER


def letter_sample_size(letter):
    """Sample the code letter calls for."""
    _require_choice("letter", letter, _LETTER_ORDER)
    return _LETTER_SAMPLE[letter]


def _next_letter(letter):
    index = _LETTER_ORDER.index(letter)
    if index + 1 >= len(_LETTER_ORDER):
        return None
    return _LETTER_ORDER[index + 1]


def resolve_plan(lot_size, quality_limit):
    """Sample and acceptance number for a lot at one quality limit.

    Where the letter's sample cannot discriminate at the quality limit,
    the plan steps up to the next larger sample and says so, rather than
    accepting on a sample that could not have detected the defect rate
    being asked about.
    """
    lot = _require_count("lot_size", lot_size, minimum=2)
    _require_choice("quality_limit", quality_limit, tuple(_ACCEPTANCE))
    letter = sample_code_letter(lot)
    stepped_up = False
    while True:
        sample = _LETTER_SAMPLE[letter]
        accept = _ACCEPTANCE[quality_limit].get(sample)
        if accept is not None:
            break
        nxt = _next_letter(letter)
        if nxt is None:
            raise ValueError(
                "no sample in the plan discriminates at quality limit %s"
                % quality_limit
            )
        letter = nxt
        stepped_up = True
    if sample >= lot:
        return {
            "letter": letter,
            "sample_size": lot,
            "accept_number": 0,
            "reject_number": 1,
            "hundred_percent": True,
            "stepped_up": stepped_up,
            "quality_limit": quality_limit,
        }
    return {
        "letter": letter,
        "sample_size": sample,
        "accept_number": accept,
        "reject_number": accept + 1,
        "hundred_percent": False,
        "stepped_up": stepped_up,
        "quality_limit": quality_limit,
    }


def _adjust_limit(quality_limit, severity):
    if severity == SEVERITY_TIGHTENED:
        return _TIGHTER[quality_limit]
    if severity == SEVERITY_REDUCED:
        return _LOOSER[quality_limit]
    return quality_limit


def acceptance_plan(lot_size, criticality, severity=None):
    """Full sampling plan for one lot of one criticality at one severity."""
    lot = _require_count("lot_size", lot_size, minimum=1)
    _require_choice("criticality", criticality, CRITICALITIES)
    base = _CRITICALITY_PLAN[criticality]
    if severity is None:
        severity = base["severity"]
    _require_choice("severity", severity, SEVERITIES)
    if severity == SEVERITY_SUSPENDED:
        raise ValueError(
            "inspection of this supplier is suspended; no lot may be sampled "
            "until the supplier's process has been reviewed and re-qualified"
        )
    if base["hundred_percent"]:
        return {
            "criticality": criticality,
            "severity": SEVERITY_TIGHTENED,
            "lot_size": lot,
            "letter": None,
            "sample_size": lot,
            "accept_number": 0,
            "reject_number": 1,
            "hundred_percent": True,
            "stepped_up": False,
            "quality_limit": None,
            "rationale": "a critical fastener is inspected whole; there is no "
            "sample that stands for the parts it did not touch",
        }
    if lot < 2:
        raise ValueError(
            "a lot of one cannot be sampled; inspect it whole instead"
        )
    limit = _adjust_limit(base["quality_limit"], severity)
    plan = resolve_plan(lot, limit)
    plan.update(
        {
            "criticality": criticality,
            "severity": severity,
            "lot_size": lot,
            "rationale": "quality limit %s at %s severity for a %s fastener"
            % (limit, severity, criticality),
        }
    )
    return plan


def judge_lot(lot_size, criticality, defectives, severity=None):
    """Accept or reject one lot on the defectives found in its sample."""
    plan = acceptance_plan(lot_size, criticality, severity)
    found = _require_count("defectives", defectives)
    if found > plan["sample_size"]:
        raise ValueError(
            "%d defectives cannot come out of a sample of %d"
            % (found, plan["sample_size"])
        )
    accepted = found <= plan["accept_number"]
    findings = []
    if plan["stepped_up"]:
        findings.append(
            "the code letter's sample could not discriminate at quality limit "
            "%s, so the plan stepped up to %d parts" % (plan["quality_limit"],
                                                        plan["sample_size"])
        )
    if not accepted:
        findings.append(
            "%d defectives in a sample of %d reaches the reject number of %d"
            % (found, plan["sample_size"], plan["reject_number"])
        )
    result = dict(plan)
    result.update(
        {
            "defectives": found,
            "disposition": LOT_ACCEPT if accepted else LOT_REJECT,
            "findings": findings,
        }
    )
    return result


def next_severity(current, recent_results):
    """Carry severity forward from the supplier's recent lot record.

    recent_results is ordered oldest first and holds only the accept or
    reject strings this module already uses.
    """
    _require_choice("current", current, SEVERITIES)
    if not isinstance(recent_results, (list, tuple)):
        raise ValueError("recent_results must be a sequence of dispositions")
    for entry in recent_results:
        _require_choice("recent_results entry", entry, (LOT_ACCEPT, LOT_REJECT))
    if current == SEVERITY_SUSPENDED:
        return SEVERITY_SUSPENDED
    trailing_accepts = 0
    for entry in reversed(recent_results):
        if entry != LOT_ACCEPT:
            break
        trailing_accepts += 1
    if current == SEVERITY_TIGHTENED:
        if len(recent_results) >= 5 and trailing_accepts >= 5:
            return SEVERITY_NORMAL
        if len(recent_results) >= 5 and recent_results[-5:].count(LOT_REJECT) >= 5:
            return SEVERITY_SUSPENDED
        return SEVERITY_TIGHTENED
    if current == SEVERITY_REDUCED:
        if recent_results and recent_results[-1] == LOT_REJECT:
            return SEVERITY_NORMAL
        return SEVERITY_REDUCED
    window = recent_results[-5:]
    if window.count(LOT_REJECT) >= 2:
        return SEVERITY_TIGHTENED
    if trailing_accepts >= 10:
        return SEVERITY_REDUCED
    return SEVERITY_NORMAL
