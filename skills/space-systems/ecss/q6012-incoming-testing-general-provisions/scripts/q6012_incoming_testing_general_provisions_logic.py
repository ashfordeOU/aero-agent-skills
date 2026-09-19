"""Baseline arrangements for receipt testing of arriving die material.

Anchor: ECSS-Q-ST-60-12C clause 10.3.1 (the general provisions under which
receipt testing is arranged - how much of an arriving lot is tested, on what
acceptance basis, what happens to the lot on the result, and how the severity
of the arrangement moves as a supplier's record builds up).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Place the lot size in a size band and take its code letter. The band, not
   the lot size itself, sets how much is drawn, so a lot of 300 and a lot of
   1,100 are sampled the same way and a lot of 1,300 is not.
2. Take the sample size from the code letter and the inspection level, then
   cap it at the lot size: a sample that reaches the lot is one hundred
   percent inspection and is reported as such rather than as a sample.
3. Derive the acceptance number from the sample size and the acceptance
   quality in whole defectives per thousand, using integer arithmetic so the
   boundary lot gets the same answer on every machine.
4. Apply the severity: tightened inspection lowers the acceptance number,
   reduced inspection halves the draw, normal leaves both alone.
5. Dispose of the lot by comparing observed defectives against the acceptance
   number, refusing a defective count larger than the sample it came from.
6. Apply the switching rules to say what severity the next lot is inspected
   under, so a supplier's record actually changes the arrangement.
"""

__all__ = [
    "INSPECTION_LEVELS",
    "SEVERITIES",
    "ACCEPTANCE_QUALITIES",
    "CODE_LETTERS",
    "TIGHTEN_AFTER_REJECTS",
    "TIGHTEN_WINDOW",
    "RELAX_AFTER_ACCEPTS",
    "REDUCE_AFTER_ACCEPTS",
    "code_letter",
    "base_sample_size",
    "acceptance_number",
    "apply_severity",
    "sampling_plan",
    "lot_disposition",
    "next_severity",
    "receipt_findings",
    "assess_receipt_testing",
]

INSPECTION_LEVELS = ("general-i", "general-ii", "general-iii")

SEVERITIES = ("reduced", "normal", "tightened")

# Acceptance quality expressed as whole permitted defectives per thousand, so
# the acceptance number is integer arithmetic from end to end.
ACCEPTANCE_QUALITIES = {
    "zero-defect": 0,
    "critical-10": 10,
    "major-25": 25,
    "minor-40": 40,
    "minor-65": 65,
}

# Upper bound of the band (None is the open top band), code letter.
_SIZE_BANDS = (
    (8, "A"),
    (25, "B"),
    (90, "C"),
    (280, "D"),
    (1200, "E"),
    (3200, "F"),
    (None, "G"),
)

CODE_LETTERS = tuple(letter for _bound, letter in _SIZE_BANDS)

# code letter -> sample size at each inspection level.
_SAMPLE_TABLE = {
    "A": {"general-i": 2, "general-ii": 3, "general-iii": 5},
    "B": {"general-i": 3, "general-ii": 5, "general-iii": 8},
    "C": {"general-i": 5, "general-ii": 8, "general-iii": 13},
    "D": {"general-i": 8, "general-ii": 13, "general-iii": 20},
    "E": {"general-i": 13, "general-ii": 20, "general-iii": 32},
    "F": {"general-i": 20, "general-ii": 32, "general-iii": 50},
    "G": {"general-i": 32, "general-ii": 50, "general-iii": 80},
}

# Switching rules.
TIGHTEN_AFTER_REJECTS = 2
TIGHTEN_WINDOW = 5
RELAX_AFTER_ACCEPTS = 5
REDUCE_AFTER_ACCEPTS = 10

_MINIMUM_REDUCED_SAMPLE = 2

_LOT_RESULTS = ("accept", "reject")


def _whole(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number" % label)
    if value < minimum:
        raise ValueError("%s must be at least %d" % (label, minimum))
    return value


def _token(value, label, table):
    if not isinstance(value, str):
        raise ValueError("%s must be a string token" % label)
    token = value.strip().lower()
    if token not in table:
        raise ValueError(
            "%s '%s' is not one of %s" % (label, value, ", ".join(sorted(table)))
        )
    return token


def code_letter(lot_size):
    """Return the size band code letter an arriving lot falls in."""
    lot_size = _whole(lot_size, "lot_size", minimum=1)
    for bound, letter in _SIZE_BANDS:
        if bound is None or lot_size <= bound:
            return letter
    raise ValueError("lot size %d fell through every band" % lot_size)


def base_sample_size(letter, level):
    """Return the tabled sample size for a code letter at an inspection level."""
    if letter not in _SAMPLE_TABLE:
        raise ValueError("unknown code letter '%s'" % (letter,))
    level = _token(level, "inspection level", set(INSPECTION_LEVELS))
    return _SAMPLE_TABLE[letter][level]


def acceptance_number(sample_size, quality):
    """Return the permitted defectives in the sample, by integer arithmetic."""
    sample_size = _whole(sample_size, "sample_size", minimum=1)
    quality = _token(quality, "acceptance quality", ACCEPTANCE_QUALITIES)
    per_thousand = ACCEPTANCE_QUALITIES[quality]
    return (sample_size * per_thousand) // 1000


def apply_severity(sample_size, accept_number, severity):
    """Return the sample size and acceptance number adjusted for severity."""
    sample_size = _whole(sample_size, "sample_size", minimum=1)
    accept_number = _whole(accept_number, "accept_number")
    severity = _token(severity, "severity", set(SEVERITIES))
    if severity == "tightened":
        return sample_size, max(0, accept_number - 1)
    if severity == "reduced":
        halved = (sample_size + 1) // 2
        return max(_MINIMUM_REDUCED_SAMPLE, halved), accept_number
    return sample_size, accept_number


def sampling_plan(lot_size, level="general-ii", quality="major-25",
                  severity="normal"):
    """Return the receipt testing sampling plan for an arriving lot."""
    lot_size = _whole(lot_size, "lot_size", minimum=1)
    level = _token(level, "inspection level", set(INSPECTION_LEVELS))
    quality = _token(quality, "acceptance quality", ACCEPTANCE_QUALITIES)
    severity = _token(severity, "severity", set(SEVERITIES))
    letter = code_letter(lot_size)
    tabled = base_sample_size(letter, level)
    accept = acceptance_number(tabled, quality)
    sample, accept = apply_severity(tabled, accept, severity)
    hundred_percent = sample >= lot_size
    if hundred_percent:
        sample = lot_size
        accept = acceptance_number(sample, quality)
        if severity == "tightened":
            accept = max(0, accept - 1)
    return {
        "lot_size": lot_size,
        "code_letter": letter,
        "level": level,
        "quality": quality,
        "severity": severity,
        "tabled_sample_size": tabled,
        "sample_size": sample,
        "acceptance_number": accept,
        "rejection_number": accept + 1,
        "hundred_percent": hundred_percent,
        "sampled_fraction": sample / float(lot_size),
    }


def lot_disposition(plan, defectives):
    """Return accept or reject for an observed defective count against a plan."""
    if not isinstance(plan, dict) or "acceptance_number" not in plan:
        raise ValueError("plan must come from sampling_plan")
    defectives = _whole(defectives, "defectives")
    if defectives > plan["sample_size"]:
        raise ValueError(
            "%d defectives cannot come from a sample of %d"
            % (defectives, plan["sample_size"])
        )
    if defectives <= plan["acceptance_number"]:
        return "accept"
    return "reject"


def next_severity(current, history):
    """Return the severity the next arriving lot is inspected under.

    history is the supplier's lot results oldest first; only the results that
    matter to each rule are read.
    """
    current = _token(current, "severity", set(SEVERITIES))
    if not isinstance(history, (list, tuple)):
        raise ValueError("history must be a sequence of lot results")
    results = []
    for item in history:
        if not isinstance(item, str):
            raise ValueError("each lot result must be a string")
        token = item.strip().lower()
        if token not in _LOT_RESULTS:
            raise ValueError(
                "lot result '%s' is not one of %s" % (item, ", ".join(_LOT_RESULTS))
            )
        results.append(token)

    trailing_accepts = 0
    for token in reversed(results):
        if token != "accept":
            break
        trailing_accepts += 1

    if current == "reduced":
        if results and results[-1] == "reject":
            return "normal"
        return "reduced"
    if current == "tightened":
        if trailing_accepts >= RELAX_AFTER_ACCEPTS:
            return "normal"
        return "tightened"
    window = results[-TIGHTEN_WINDOW:]
    if window.count("reject") >= TIGHTEN_AFTER_REJECTS:
        return "tightened"
    if trailing_accepts >= REDUCE_AFTER_ACCEPTS:
        return "reduced"
    return "normal"


def receipt_findings(plan, defectives, disposition, upcoming):
    """Return the findings the receipt testing arrangement raises."""
    if not isinstance(plan, dict) or "acceptance_number" not in plan:
        raise ValueError("plan must come from sampling_plan")
    findings = []
    if plan["hundred_percent"]:
        findings.append(
            "the tabled sample reaches the lot size, so this is one hundred percent "
            "inspection of %d items, not a sample" % plan["lot_size"]
        )
    if plan["acceptance_number"] == 0:
        findings.append(
            "acceptance number is zero: a single defective in the sample rejects "
            "the whole lot"
        )
    if disposition == "reject":
        findings.append(
            "lot rejected: %d defectives against an acceptance number of %d"
            % (defectives, plan["acceptance_number"])
        )
    elif defectives > 0:
        findings.append(
            "lot accepted with %d defectives in the sample; the material is still "
            "screened before use" % defectives
        )
    if upcoming != plan["severity"]:
        findings.append(
            "inspection severity moves from %s to %s for the next lot"
            % (plan["severity"], upcoming)
        )
    return findings


def assess_receipt_testing(spec):
    """Run the full clause 10.3.1 receipt testing arrangement for one lot."""
    if not isinstance(spec, dict):
        raise ValueError("receipt testing spec must be a mapping")
    required = ("lot_size", "defectives")
    optional = ("level", "quality", "severity", "history")
    for key in required:
        if key not in spec:
            raise ValueError("receipt testing spec missing required key '%s'" % key)
    for key in spec:
        if key not in required + optional:
            raise ValueError("receipt testing spec carries unknown key '%s'" % key)
    plan = sampling_plan(
        spec["lot_size"],
        spec.get("level", "general-ii"),
        spec.get("quality", "major-25"),
        spec.get("severity", "normal"),
    )
    defectives = _whole(spec["defectives"], "defectives")
    disposition = lot_disposition(plan, defectives)
    history = list(spec.get("history", ())) + [disposition]
    upcoming = next_severity(plan["severity"], history)
    return {
        "plan": plan,
        "defectives": defectives,
        "disposition": disposition,
        "next_severity": upcoming,
        "findings": receipt_findings(plan, defectives, disposition, upcoming),
        "released_to_production": disposition == "accept",
    }
