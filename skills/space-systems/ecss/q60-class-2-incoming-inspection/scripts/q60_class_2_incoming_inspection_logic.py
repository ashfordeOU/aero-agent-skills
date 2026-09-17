"""Arrival inspection of Class 2 EEE deliveries at the procuring entity.

Anchor: ECSS-Q-ST-60C clause 5.3.7 -- the checks performed when Class 2 parts
arrive at the premises of the procuring entity. Paraphrased into an
implementable procedure; no standard text is reproduced.

What this module decides
------------------------
Whether an unpacked delivery enters the bonded store, is screened piece by
piece, is quarantined, or waits on paperwork -- and how many pieces of it are
accepted at all.

A Class 2 arrival check is an attribute inspection on a sample, not a hundred
per cent examination, so three things have to be settled together:

1. The plan. Lot size fixes how many pieces are drawn and how many defects of
   each severity the draw may carry before the lot stops being acceptable. A
   lot smaller than its own draw is examined whole.
2. The tally. Defects are grouped by severity and counted against the number
   belonging to that severity, because a cosmetic mark and a bent lead are not
   the same evidence. One critical defect ends the question on its own: it is
   not counted against an acceptance number, it quarantines the lot, because a
   sample that produced a critical defect says nothing reassuring about the
   pieces that were not drawn.
3. The pieces. The count that arrived, the count on the note and the pieces
   damaged in transit are reconciled before any of it, so the accepted quantity
   is the quantity that can actually be drawn from.

Packaging is judged as evidence about the pieces inside rather than about the
wrapping: a breached static-protective bag exposed every piece in it, not only
the ones the inspector happened to draw, so it carries critical weight.
"""

__all__ = [
    "DEFECT_SEVERITIES",
    "DEFAULT_SAMPLE_PLAN",
    "REQUIRED_ARRIVAL_DOCUMENTS",
    "DISPOSITION_PRECEDENCE",
    "sampling_plan",
    "reconcile_quantity",
    "tally_defects",
    "packaging_findings",
    "documentation_findings",
    "assess_incoming_inspection",
]

# How severely a defect bears on the lot. Critical is not an acceptance-number
# question; the other two are.
DEFECT_SEVERITIES = ("critical", "major", "minor")

# (lot size upper bound, pieces drawn, majors allowed, minors allowed).
# The last tier has no upper bound and catches every larger lot.
DEFAULT_SAMPLE_PLAN = (
    (15, 5, 0, 1),
    (50, 8, 0, 2),
    (150, 13, 1, 3),
    (500, 20, 1, 5),
    (1200, 32, 2, 7),
    (None, 50, 3, 10),
)

# The paperwork that has to travel with the parts for them to enter the store.
REQUIRED_ARRIVAL_DOCUMENTS = (
    "delivery-note",
    "certificate-of-conformity",
    "lot-traceability-record",
)

# Worst first. The disposition of a delivery is the worst one it earns.
DISPOSITION_PRECEDENCE = (
    "quarantine-lot",
    "hold-for-documentation",
    "screen-remainder",
    "accept-to-bonded-store",
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
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def _severity(label, value):
    """Return value as one of the defect severities."""
    name = _text(label, value).lower()
    if name not in DEFECT_SEVERITIES:
        raise ValueError(
            "%s must be one of %s, got %r" % (label, ", ".join(DEFECT_SEVERITIES), value)
        )
    return name


def sampling_plan(lot_size, plan_table=DEFAULT_SAMPLE_PLAN):
    """Return the draw and the acceptance numbers for a lot of this size.

    A lot smaller than the draw its tier asks for is examined whole rather than
    refused, and the acceptance numbers travel with the tier, not with the
    number of pieces that ended up being looked at.
    """
    size = _count("lot_size", lot_size)
    if size < 1:
        raise ValueError("lot_size must be at least 1, got %d" % size)
    if not isinstance(plan_table, (list, tuple)) or not plan_table:
        raise ValueError("plan_table must be a non-empty sequence of tiers")
    for index, tier in enumerate(plan_table):
        if not isinstance(tier, (list, tuple)) or len(tier) != 4:
            raise ValueError(
                "plan_table[%d] must be (upper_bound, sample, majors, minors)" % index
            )
        upper, sample, majors, minors = tier
        if upper is not None:
            upper = _count("plan_table[%d] upper_bound" % index, upper)
        sample = _count("plan_table[%d] sample" % index, sample)
        if sample < 1:
            raise ValueError("plan_table[%d] sample must be at least 1" % index)
        majors = _count("plan_table[%d] majors" % index, majors)
        minors = _count("plan_table[%d] minors" % index, minors)
        if upper is None or size <= upper:
            drawn = min(sample, size)
            return {
                "lot_size": size,
                "sample_size": drawn,
                "accept_major": majors,
                "accept_minor": minors,
                "whole_lot_examined": drawn == size,
            }
    raise ValueError("plan_table has no tier covering a lot of %d pieces" % size)


def reconcile_quantity(declared, counted, damaged=0):
    """Return the pieces actually available after the count and transit damage.

    Damage found on arrival comes out of the accepted quantity instead of being
    left in it and dealt with later.
    """
    said = _count("declared", declared)
    if said < 1:
        raise ValueError("declared must be at least 1, got %d" % said)
    found = _count("counted", counted)
    hurt = _count("damaged", damaged)
    if hurt > found:
        raise ValueError("damaged %d exceeds the pieces counted %d" % (hurt, found))
    findings = []
    if found != said:
        findings.append(
            "delivery note declares %d pieces, %d were counted" % (said, found)
        )
    if hurt:
        findings.append("%d pieces arrived damaged and leave the accepted count" % hurt)
    return {
        "declared": said,
        "counted": found,
        "damaged": hurt,
        "accepted": found - hurt,
        "findings": findings,
    }


def tally_defects(defects):
    """Return the defects found in the draw, grouped by severity.

    Each defect keeps its description so the tally can be shown rather than
    just totalled.
    """
    if defects is None:
        defects = []
    if not isinstance(defects, (list, tuple)):
        raise ValueError("defects must be a sequence of defect records")
    counts = {name: 0 for name in DEFECT_SEVERITIES}
    detail = {name: [] for name in DEFECT_SEVERITIES}
    for index, item in enumerate(defects):
        if not isinstance(item, dict):
            raise ValueError("defects[%d] must be a mapping" % index)
        if "severity" not in item:
            raise ValueError("defects[%d] missing required key 'severity'" % index)
        name = _severity("defects[%d] severity" % index, item["severity"])
        description = item.get("description", "")
        description = (
            _text("defects[%d] description" % index, description)
            if description not in (None, "")
            else name + " defect"
        )
        counts[name] += 1
        detail[name].append(description)
    return {"counts": counts, "detail": detail, "total": sum(counts.values())}


def packaging_findings(packaging):
    """Return what the packaging says about the pieces inside.

    A breached static-protective bag exposed every piece it held, so it is
    reported as a critical finding about the lot, not as a note about wrapping.
    """
    if packaging is None:
        packaging = {}
    if not isinstance(packaging, dict):
        raise ValueError("packaging must be a mapping")
    bag_intact = _flag(
        "packaging static_protective_bag_intact",
        packaging.get("static_protective_bag_intact", True),
    )
    seal_intact = _flag(
        "packaging shipping_seal_intact", packaging.get("shipping_seal_intact", True)
    )
    critical = []
    advisory = []
    if not bag_intact:
        critical.append(
            "static-protective bag was breached; every piece it held was exposed"
        )
    if not seal_intact:
        advisory.append(
            "shipping seal was not intact on arrival; traceability of the transit is broken"
        )
    return {"critical": critical, "advisory": advisory}


def documentation_findings(documents, required=REQUIRED_ARRIVAL_DOCUMENTS):
    """Return the arrival documents the delivery did not bring with it."""
    if documents is None:
        documents = []
    if not isinstance(documents, (list, tuple, set, frozenset)):
        raise ValueError("documents must be a sequence of document names")
    if not isinstance(required, (list, tuple, set, frozenset)) or not required:
        raise ValueError("required must be a non-empty sequence of document names")
    held = set()
    for index, item in enumerate(documents):
        held.add(_text("documents[%d]" % index, item).lower())
    missing = []
    for item in required:
        name = _text("required document", item).lower()
        if name not in held:
            missing.append(name)
    return missing


def _worst(dispositions):
    """Return the worst disposition earned."""
    for candidate in DISPOSITION_PRECEDENCE:
        if candidate in dispositions:
            return candidate
    return "accept-to-bonded-store"


def assess_incoming_inspection(spec):
    """Return the clause 5.3.7 arrival disposition for one Class 2 delivery.

    spec keys: declared_quantity, counted_quantity, optional damaged_quantity,
    defects, documents, packaging and plan_table.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declared_quantity", "counted_quantity"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    quantity = reconcile_quantity(
        spec["declared_quantity"],
        spec["counted_quantity"],
        spec.get("damaged_quantity", 0),
    )
    if quantity["accepted"] < 1:
        return {
            "quantity": quantity,
            "plan": None,
            "tally": None,
            "missing_documents": documentation_findings(spec.get("documents")),
            "accepted_quantity": 0,
            "disposition": "quarantine-lot",
            "blocking": ["no undamaged pieces remain to inspect"],
            "advisory": quantity["findings"],
            "findings": ["no undamaged pieces remain to inspect"] + quantity["findings"],
        }

    plan = sampling_plan(
        quantity["accepted"], spec.get("plan_table", DEFAULT_SAMPLE_PLAN)
    )
    tally = tally_defects(spec.get("defects"))
    packaging = packaging_findings(spec.get("packaging"))
    missing_documents = documentation_findings(spec.get("documents"))

    blocking = []
    advisory = list(quantity["findings"]) + list(packaging["advisory"])
    earned = []

    if tally["total"] > plan["sample_size"]:
        raise ValueError(
            "%d defects reported from a draw of %d pieces"
            % (tally["total"], plan["sample_size"])
        )

    if packaging["critical"]:
        blocking.extend(packaging["critical"])
        earned.append("quarantine-lot")
    if tally["counts"]["critical"]:
        blocking.append(
            "%d critical defect(s) in the draw: %s"
            % (tally["counts"]["critical"], ", ".join(tally["detail"]["critical"]))
        )
        earned.append("quarantine-lot")
    if tally["counts"]["major"] > plan["accept_major"]:
        blocking.append(
            "%d major defects against an acceptance number of %d"
            % (tally["counts"]["major"], plan["accept_major"])
        )
        earned.append("quarantine-lot")
    elif tally["counts"]["major"]:
        advisory.append(
            "%d major defect(s) within the acceptance number of %d"
            % (tally["counts"]["major"], plan["accept_major"])
        )
    if tally["counts"]["minor"] > plan["accept_minor"]:
        advisory.append(
            "%d minor defects against an acceptance number of %d; the remainder is screened"
            % (tally["counts"]["minor"], plan["accept_minor"])
        )
        earned.append("screen-remainder")
    if missing_documents:
        blocking.append(
            "delivery arrived without %s" % ", ".join(missing_documents)
        )
        earned.append("hold-for-documentation")

    disposition = _worst(earned)
    accepted = quantity["accepted"] if disposition != "quarantine-lot" else 0
    return {
        "quantity": quantity,
        "plan": plan,
        "tally": tally,
        "missing_documents": missing_documents,
        "accepted_quantity": accepted,
        "disposition": disposition,
        "blocking": blocking,
        "advisory": advisory,
        "findings": blocking + advisory,
    }
