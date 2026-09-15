"""Arrival checks for a Class 1 EEE delivery at the procuring entity.

Anchor: ECSS-Q-ST-60C clause 4.3.7 -- the inspection performed when Class 1
parts arrive at the premises of the procuring entity. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether the delivery that has just been unpacked goes into the bonded store or
into quarantine, and what has to be raised before it can move.

1. Quantity. The pieces counted on the bench are reconciled against the pieces
   the delivery note declares, and pieces damaged in transit are taken out of
   the accepted count rather than left in it.
2. Packaging. A Class 1 part arrives sealed and static-safe. A broken seal, an
   opened bag or a humidity indicator that has changed is a finding about the
   pieces inside, not about the bag.
3. Documentation. The evidence pack travels with the parts; a document that
   did not arrive is named, not assumed to be following on.
4. Age. The date code fixes the week the pieces were built, and a lot that has
   aged past the declared threshold on arrival owes a solderability re-test
   before it is drawn from store.
5. Visual sample. The external examination draws an integer sample from the
   delivered quantity, sized by integer square root so the same delivery gives
   the same sample on every platform.
"""

import math
from datetime import date

__all__ = [
    "DEFAULT_SOLDERABILITY_MONTHS",
    "MINIMUM_VISUAL_SAMPLE",
    "REQUIRED_DOCUMENTS",
    "DRY_INDICATORS",
    "parse_day",
    "date_code_week_start",
    "part_age_months",
    "solderability_retest_due",
    "reconcile_quantity",
    "visual_sample_size",
    "documentation_findings",
    "packaging_findings",
    "assess_incoming_inspection",
]

# A lot older than this many whole months on arrival owes a solderability
# re-test before it is drawn from the bonded store.
DEFAULT_SOLDERABILITY_MONTHS = 24

# No external visual examination draws fewer pieces than this unless the
# delivery itself is smaller.
MINIMUM_VISUAL_SAMPLE = 3

# Evidence that travels with a Class 1 delivery.
REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "lot-acceptance-report",
    "buy-off-record",
    "screening-data",
)

# Humidity indicator readings that mean the pieces stayed dry.
DRY_INDICATORS = ("blue", "dry")


def _count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer count, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must be non-negative, got %d" % (label, value))
    return value


def _text(label, value):
    """Return value as a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _flag(label, value):
    """Return value as a strict boolean."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def parse_day(label, value):
    """Return an ISO YYYY-MM-DD string or date object as a date."""
    if isinstance(value, date):
        return value
    text = _text(label, value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise ValueError("%s must be an ISO YYYY-MM-DD day, got %r" % (label, value))


def date_code_week_start(date_code, century_base=2000):
    """Return the first day of the build week a YYWW date code names.

    A week number a calendar year does not have is refused rather than rolled
    into the next year, because that would silently make the lot younger.
    """
    text = _text("date_code", date_code)
    if len(text) != 4 or not text.isdigit():
        raise ValueError("date_code must be four digits YYWW, got %r" % (date_code,))
    base = _count("century_base", century_base)
    if base % 100:
        raise ValueError("century_base must be a whole century, got %d" % base)
    year = base + int(text[:2])
    week = int(text[2:])
    if week < 1 or week > 53:
        raise ValueError("date_code week must lie in 01..53, got %r" % (date_code,))
    try:
        return date.fromisocalendar(year, week, 1)
    except ValueError:
        raise ValueError("calendar year %d has no week %02d" % (year, week))


def part_age_months(date_code, receipt_day, century_base=2000):
    """Return the whole calendar months from the build week to the receipt day."""
    built = date_code_week_start(date_code, century_base)
    received = parse_day("receipt_day", receipt_day)
    if received < built:
        raise ValueError(
            "receipt day %s precedes the build week starting %s" % (received, built)
        )
    months = (received.year - built.year) * 12 + (received.month - built.month)
    if received.day < built.day:
        months -= 1
    return months


def solderability_retest_due(
    date_code, receipt_day, threshold_months=DEFAULT_SOLDERABILITY_MONTHS, century_base=2000
):
    """Return the solderability record for one lot arriving on a given day."""
    threshold = _count("threshold_months", threshold_months)
    if threshold < 1:
        raise ValueError("threshold_months must be at least 1, got %d" % threshold)
    age = part_age_months(date_code, receipt_day, century_base)
    return {
        "date_code": _text("date_code", date_code),
        "age_months": age,
        "threshold_months": threshold,
        "retest_due": age > threshold,
    }


def reconcile_quantity(declared, counted, damaged=0):
    """Return the quantity reconciliation between the note and the bench.

    Pieces damaged in transit leave the accepted count; a bench count that
    disagrees with the note is reported as a signed discrepancy either way.
    """
    noted = _count("declared", declared)
    bench = _count("counted", counted)
    broken = _count("damaged", damaged)
    if noted < 1:
        raise ValueError("declared must be at least 1, got %d" % noted)
    if broken > bench:
        raise ValueError("damaged %d exceeds the counted quantity %d" % (broken, bench))
    accepted = bench - broken
    return {
        "declared": noted,
        "counted": bench,
        "damaged": broken,
        "accepted": accepted,
        "discrepancy": bench - noted,
        "reconciled": bench == noted and broken == 0,
    }


def visual_sample_size(quantity, minimum_sample=MINIMUM_VISUAL_SAMPLE):
    """Return the pieces the external visual examination draws.

    Integer square root plus one, raised to the declared floor and clamped to
    the delivery. Integer arithmetic throughout, so the draw is identical on
    every platform rather than depending on how a square root rounded.
    """
    held = _count("quantity", quantity)
    if held < 1:
        raise ValueError("quantity must be at least 1, got %d" % held)
    floor_sample = _count("minimum_sample", minimum_sample)
    drawn = math.isqrt(held) + 1
    if drawn < floor_sample:
        drawn = floor_sample
    if drawn > held:
        drawn = held
    return drawn


def documentation_findings(documents, required=REQUIRED_DOCUMENTS):
    """Return the evidence-pack record for a delivery.

    documents: sequence of document names that arrived with the parts.
    """
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a sequence of document names")
    arrived = []
    for index, item in enumerate(documents):
        arrived.append(_text("documents[%d]" % index, item).lower())
    expected = [_text("required document", name).lower() for name in required]
    if not expected:
        raise ValueError("required must name at least one document")
    missing = [name for name in expected if name not in arrived]
    return {
        "arrived": arrived,
        "required": expected,
        "missing": missing,
        "complete": not missing,
        "findings": ["evidence pack is missing '%s'" % name for name in missing],
    }


def packaging_findings(packaging):
    """Return the packaging record for a delivery.

    packaging keys: seal_intact, esd_bag_intact and humidity_indicator.
    """
    if not isinstance(packaging, dict):
        raise ValueError("packaging must be a mapping")
    for key in ("seal_intact", "esd_bag_intact", "humidity_indicator"):
        if key not in packaging:
            raise ValueError("packaging missing required key '%s'" % key)
    seal = _flag("seal_intact", packaging["seal_intact"])
    bag = _flag("esd_bag_intact", packaging["esd_bag_intact"])
    indicator = _text("humidity_indicator", packaging["humidity_indicator"]).lower()
    findings = []
    if not seal:
        findings.append("shipping seal arrived broken")
    if not bag:
        findings.append("static-protective bag arrived open or torn")
    dry = indicator in DRY_INDICATORS
    if not dry:
        findings.append("humidity indicator reads '%s'; the lot arrived damp" % indicator)
    return {
        "seal_intact": seal,
        "esd_bag_intact": bag,
        "humidity_indicator": indicator,
        "dry": dry,
        "sound": seal and bag and dry,
        "findings": findings,
    }


def assess_incoming_inspection(spec):
    """Return the clause 4.3.7 arrival decision for one Class 1 delivery.

    spec keys: date_code, receipt_day, declared, counted, packaging, documents,
    optional damaged, required_documents, threshold_months, minimum_sample and
    century_base.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("date_code", "receipt_day", "declared", "counted", "packaging", "documents"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    century_base = spec.get("century_base", 2000)
    quantity = reconcile_quantity(spec["declared"], spec["counted"], spec.get("damaged", 0))
    packaging = packaging_findings(spec["packaging"])
    documents = documentation_findings(
        spec["documents"], spec.get("required_documents", REQUIRED_DOCUMENTS)
    )
    solderability = solderability_retest_due(
        spec["date_code"],
        spec["receipt_day"],
        spec.get("threshold_months", DEFAULT_SOLDERABILITY_MONTHS),
        century_base,
    )
    findings = []
    if quantity["discrepancy"]:
        findings.append(
            "bench count %d disagrees with the delivery note %d"
            % (quantity["counted"], quantity["declared"])
        )
    if quantity["damaged"]:
        findings.append("%d piece(s) arrived damaged and leave the accepted count" % quantity["damaged"])
    findings.extend(packaging["findings"])
    findings.extend(documents["findings"])
    if solderability["retest_due"]:
        findings.append(
            "lot is %d months old against a %d month threshold; solderability re-test is due"
            % (solderability["age_months"], solderability["threshold_months"])
        )
    if quantity["accepted"] < 1:
        findings.append("no undamaged pieces arrived")
        sample = 0
    else:
        sample = visual_sample_size(
            quantity["accepted"], spec.get("minimum_sample", MINIMUM_VISUAL_SAMPLE)
        )
    accepted = (
        quantity["reconciled"]
        and packaging["sound"]
        and documents["complete"]
        and not solderability["retest_due"]
        and quantity["accepted"] > 0
    )
    return {
        "quantity": quantity,
        "packaging": packaging,
        "documents": documents,
        "solderability": solderability,
        "visual_sample_size": sample,
        "accepted_pieces": quantity["accepted"] if accepted else 0,
        "accepted": accepted,
        "disposition": "accept-into-bonded-store" if accepted else "quarantine",
        "findings": findings,
    }
