"""Arrival checks for a Class 3 EEE delivery at the procuring entity.

Anchor: ECSS-Q-ST-60C clause 6.3.7 -- the checks performed on arrival of Class 3
parts at the premises of the procuring entity. Paraphrased into an implementable
procedure; no standard text is reproduced.

What this module decides
------------------------
How deep the goods-in bench has to go on a Class 3 delivery, and where the
pieces go afterwards.

1. Depth. Class 3 parts reach the door through very different chains. A part
   bought from the manufacturer or its franchised distributor arrives with an
   unbroken chain behind it and earns a reduced examination. A part bought from
   an independent distributor or on the open market does not, and owes the
   extended examination that includes authenticity evidence.
2. Escalation. A broken shipping seal or an open static-protective bag is
   evidence about the pieces inside, so it pushes the examination one step
   deeper rather than being written down and passed over.
3. Draw. The examination draws an integer sample sized by integer square root
   and scaled by the depth, so the same delivery gives the same draw on every
   platform rather than depending on how a square root rounded.
4. Severity. Defects found are grouped by severity. A cosmetic mark and a
   cracked body are not one tally, and only the critical tally ends the
   delivery outright.
5. Evidence. What the delivery owes in paperwork depends on the chain it came
   through; an unfranchised source owes traceability back to the manufacturer
   and an authenticity report on top of the ordinary pack.
"""

import math

__all__ = [
    "SOURCE_TIERS",
    "UNFRANCHISED_TIERS",
    "DEPTHS",
    "TIER_BASE_DEPTH",
    "DEPTH_DRAW_MULTIPLIER",
    "MINIMUM_ARRIVAL_DRAW",
    "DEFECT_SEVERITIES",
    "BASE_ARRIVAL_DOCUMENTS",
    "UNFRANCHISED_ARRIVAL_DOCUMENTS",
    "DRY_INDICATORS",
    "MAJOR_ACCEPTANCE_DIVISOR",
    "MINOR_ACCEPTANCE_DIVISOR",
    "DISPOSITION_PRECEDENCE",
    "normalize_source_tier",
    "escalate_depth",
    "packaging_findings",
    "inspection_depth",
    "arrival_draw",
    "required_documents_for_tier",
    "documentation_findings",
    "reconcile_quantity",
    "tally_defects",
    "acceptance_numbers",
    "assess_incoming_inspection",
]

# The chains a Class 3 part can reach the procuring entity through.
SOURCE_TIERS = (
    "manufacturer-direct",
    "franchised-distributor",
    "independent-distributor",
    "open-market-broker",
)

# Chains with no unbroken link back to the manufacturer.
UNFRANCHISED_TIERS = ("independent-distributor", "open-market-broker")

# Examination depths, shallowest first.
DEPTHS = ("reduced", "standard", "extended")

# Where each chain starts before any escalation.
TIER_BASE_DEPTH = {
    "manufacturer-direct": "reduced",
    "franchised-distributor": "standard",
    "independent-distributor": "extended",
    "open-market-broker": "extended",
}

# How much of the square-root draw each depth takes.
DEPTH_DRAW_MULTIPLIER = {"reduced": 1, "standard": 2, "extended": 3}

# No arrival examination draws fewer pieces than this unless fewer arrived.
MINIMUM_ARRIVAL_DRAW = 3

# Severities an arrival defect can carry, worst first.
DEFECT_SEVERITIES = ("critical", "major", "minor")

# Evidence every Class 3 delivery carries.
BASE_ARRIVAL_DOCUMENTS = ("certificate-of-conformity", "delivery-note")

# What an unfranchised chain owes on top of the base pack.
UNFRANCHISED_ARRIVAL_DOCUMENTS = (
    "traceability-to-manufacturer",
    "authenticity-screening-report",
)

# Humidity indicator readings that mean the pieces stayed dry.
DRY_INDICATORS = ("blue", "dry")

# One major defect is tolerated per this many pieces drawn.
MAJOR_ACCEPTANCE_DIVISOR = 25

# One minor defect is tolerated per this many pieces drawn, plus one.
MINOR_ACCEPTANCE_DIVISOR = 10

# Dispositions, worst first; the first one that fires wins.
DISPOSITION_PRECEDENCE = (
    "quarantine",
    "conditional-release",
    "accept-into-bonded-store",
)


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


def normalize_source_tier(tier):
    """Return a declared supply chain tier in canonical form."""
    text = _text("source_tier", tier).lower()
    if text not in SOURCE_TIERS:
        raise ValueError(
            "source_tier %r is not one of %s" % (tier, ", ".join(SOURCE_TIERS))
        )
    return text


def escalate_depth(depth, steps=1):
    """Return the depth reached after escalating a given number of steps."""
    text = _text("depth", depth).lower()
    if text not in DEPTHS:
        raise ValueError("depth %r is not one of %s" % (depth, ", ".join(DEPTHS)))
    moves = _count("steps", steps)
    index = DEPTHS.index(text) + moves
    if index >= len(DEPTHS):
        index = len(DEPTHS) - 1
    return DEPTHS[index]


def packaging_findings(packaging):
    """Return the packaging record for a Class 3 delivery.

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
    breached = (not seal) or (not bag)
    return {
        "seal_intact": seal,
        "esd_bag_intact": bag,
        "humidity_indicator": indicator,
        "dry": dry,
        "breached": breached,
        "sound": seal and bag and dry,
        "findings": findings,
    }


def inspection_depth(source_tier, packaging):
    """Return the examination depth this delivery has earned.

    The chain sets the base depth; a breached seal or bag pushes it one step
    deeper, because the breach is evidence about the pieces the bag held.
    """
    tier = normalize_source_tier(source_tier)
    pack = packaging_findings(packaging)
    base = TIER_BASE_DEPTH[tier]
    steps = 1 if pack["breached"] else 0
    depth = escalate_depth(base, steps)
    return {
        "source_tier": tier,
        "base_depth": base,
        "escalated": depth != base,
        "depth": depth,
        "authenticity_required": tier in UNFRANCHISED_TIERS,
        "packaging": pack,
    }


def arrival_draw(quantity, depth, minimum=MINIMUM_ARRIVAL_DRAW):
    """Return the pieces the arrival examination draws.

    Integer square root plus one, scaled by the depth, raised to the floor and
    clamped to the delivery. Integer arithmetic throughout.
    """
    held = _count("quantity", quantity)
    if held < 1:
        raise ValueError("quantity must be at least 1, got %d" % held)
    text = _text("depth", depth).lower()
    if text not in DEPTHS:
        raise ValueError("depth %r is not one of %s" % (depth, ", ".join(DEPTHS)))
    floor_draw = _count("minimum", minimum)
    if floor_draw < 1:
        raise ValueError("minimum must be at least 1, got %d" % floor_draw)
    drawn = DEPTH_DRAW_MULTIPLIER[text] * (math.isqrt(held) + 1)
    if drawn < floor_draw:
        drawn = floor_draw
    if drawn > held:
        drawn = held
    return drawn


def required_documents_for_tier(source_tier):
    """Return the evidence a delivery from this chain owes on arrival."""
    tier = normalize_source_tier(source_tier)
    documents = list(BASE_ARRIVAL_DOCUMENTS)
    if tier in UNFRANCHISED_TIERS:
        documents.extend(UNFRANCHISED_ARRIVAL_DOCUMENTS)
    return tuple(documents)


def documentation_findings(documents, source_tier):
    """Return the evidence-pack record for a delivery from one chain."""
    if not isinstance(documents, (list, tuple)):
        raise ValueError("documents must be a sequence of document names")
    arrived = []
    for index, item in enumerate(documents):
        arrived.append(_text("documents[%d]" % index, item).lower())
    expected = list(required_documents_for_tier(source_tier))
    missing = [name for name in expected if name not in arrived]
    return {
        "arrived": arrived,
        "required": expected,
        "missing": missing,
        "complete": not missing,
        "findings": ["evidence pack is missing '%s'" % name for name in missing],
    }


def reconcile_quantity(declared, counted, damaged=0):
    """Return the quantity reconciliation between the note and the bench."""
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


def tally_defects(defects):
    """Return the defects found on the draw, grouped by severity.

    defects: sequence of mappings carrying a severity and a description. A
    severity the project never declared is refused, because an ungraded defect
    can be counted neither against the critical tally nor against the minor one.
    """
    if defects is None:
        defects = ()
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of defect records")
    counts = {severity: 0 for severity in DEFECT_SEVERITIES}
    detail = {severity: [] for severity in DEFECT_SEVERITIES}
    for index, item in enumerate(defects):
        if not isinstance(item, dict):
            raise ValueError("defects[%d] must be a mapping" % index)
        for key in ("severity", "description"):
            if key not in item:
                raise ValueError("defects[%d] missing required key '%s'" % (index, key))
        severity = _text("defects[%d].severity" % index, item["severity"]).lower()
        if severity not in DEFECT_SEVERITIES:
            raise ValueError(
                "defects[%d] severity %r is not one of %s"
                % (index, item["severity"], ", ".join(DEFECT_SEVERITIES))
            )
        description = _text("defects[%d].description" % index, item["description"])
        counts[severity] += 1
        detail[severity].append(description)
    return {
        "counts": counts,
        "detail": detail,
        "total": sum(counts.values()),
        "worst": next(
            (s for s in DEFECT_SEVERITIES if counts[s]),
            None,
        ),
    }


def acceptance_numbers(draw, depth):
    """Return the defects of each severity this draw may carry and still pass.

    A critical defect is never tolerated. An extended examination tolerates no
    major defect either, because that depth was reached over a doubt about the
    pieces themselves.
    """
    drawn = _count("draw", draw)
    if drawn < 1:
        raise ValueError("draw must be at least 1, got %d" % drawn)
    text = _text("depth", depth).lower()
    if text not in DEPTHS:
        raise ValueError("depth %r is not one of %s" % (depth, ", ".join(DEPTHS)))
    major = 0 if text == "extended" else drawn // MAJOR_ACCEPTANCE_DIVISOR
    minor = drawn // MINOR_ACCEPTANCE_DIVISOR + 1
    return {"critical": 0, "major": major, "minor": minor}


def assess_incoming_inspection(spec):
    """Return the clause 6.3.7 arrival decision for one Class 3 delivery.

    spec keys: source_tier, packaging, documents, declared, counted; optional
    damaged, defects, marking_permanency_pass and minimum_draw. An extended
    examination without a marking permanency result is refused, because the
    result is part of what makes the examination extended.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("source_tier", "packaging", "documents", "declared", "counted"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    depth_record = inspection_depth(spec["source_tier"], spec["packaging"])
    depth = depth_record["depth"]
    quantity = reconcile_quantity(
        spec["declared"], spec["counted"], spec.get("damaged", 0)
    )
    documents = documentation_findings(spec["documents"], spec["source_tier"])
    defects = tally_defects(spec.get("defects"))
    findings = list(depth_record["packaging"]["findings"])
    findings.extend(documents["findings"])
    marking = None
    if depth == "extended":
        if "marking_permanency_pass" not in spec:
            raise ValueError(
                "an extended examination needs a marking_permanency_pass result"
            )
        marking = _flag("marking_permanency_pass", spec["marking_permanency_pass"])
        if not marking:
            findings.append(
                "part marking did not survive the permanency test; authenticity is in doubt"
            )
    if quantity["discrepancy"]:
        findings.append(
            "bench count %d disagrees with the delivery note %d"
            % (quantity["counted"], quantity["declared"])
        )
    if quantity["damaged"]:
        findings.append(
            "%d piece(s) arrived damaged and leave the accepted count"
            % quantity["damaged"]
        )
    if quantity["accepted"] < 1:
        findings.append("no undamaged pieces arrived")
        draw = 0
        limits = {"critical": 0, "major": 0, "minor": 0}
    else:
        draw = arrival_draw(
            quantity["accepted"], depth, spec.get("minimum_draw", MINIMUM_ARRIVAL_DRAW)
        )
        limits = acceptance_numbers(draw, depth)
    counts = defects["counts"]
    over = {
        severity: counts[severity] > limits[severity] for severity in DEFECT_SEVERITIES
    }
    for severity in DEFECT_SEVERITIES:
        if over[severity]:
            findings.append(
                "%d %s defect(s) against an acceptance number of %d"
                % (counts[severity], severity, limits[severity])
            )
    quarantine = (
        over["critical"]
        or over["major"]
        or not documents["complete"]
        or quantity["accepted"] < 1
        or marking is False
    )
    conditional = (
        over["minor"]
        or not depth_record["packaging"]["sound"]
        or bool(quantity["discrepancy"])
        or bool(quantity["damaged"])
    )
    if quarantine:
        disposition = "quarantine"
    elif conditional:
        disposition = "conditional-release"
    else:
        disposition = "accept-into-bonded-store"
    return {
        "depth": depth_record,
        "quantity": quantity,
        "documents": documents,
        "defects": defects,
        "draw": draw,
        "acceptance_numbers": limits,
        "over_acceptance": over,
        "marking_permanency_pass": marking,
        "accepted_pieces": quantity["accepted"] if disposition != "quarantine" else 0,
        "disposition": disposition,
        "findings": findings,
    }
