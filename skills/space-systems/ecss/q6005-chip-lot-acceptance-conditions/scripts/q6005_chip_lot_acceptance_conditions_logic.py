"""Acceptance conditions for a delivered batch of bare chips.

Anchor: ECSS-Q-ST-60-05C clause 8.1.4 (the traceability, homogeneity and
documentation conditions a delivered batch of bare semiconductor and passive
chips meets before it is accepted into stores). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the delivery as a set of sublots, each naming the wafer lot and
   the diffusion lot it came from and how many dice it contains.
2. Reconcile the quantities: the sublots have to sum to the declared delivered
   quantity, and the delivered quantity is compared with what was ordered.
   Paperwork disagreeing with the goods is a harder failure than a shortfall.
3. Measure traceability coverage as the fraction of delivered dice carrying
   both a wafer-lot and a diffusion-lot identity. Anything short of full
   coverage refuses the delivery: an untraceable die cannot be recovered by
   inspection.
4. Measure homogeneity as the largest wafer-lot aggregate over the whole
   delivery. A single wafer lot gives one; a split delivery gives less, which
   refuses the lot unless the order permitted multiple lots, in which case it
   is carried as a reservation.
5. Check the delivery documentation set, and return accept,
   accept-with-reservation or reject with every failing condition named.
"""

import math

__all__ = [
    "RATIO_TOLERANCE",
    "REQUIRED_DOCUMENTS",
    "validate_sublots",
    "delivered_quantity",
    "reconcile_quantities",
    "traceability_coverage",
    "untraceable_sublots",
    "homogeneity_ratio",
    "wafer_lot_breakdown",
    "missing_documents",
    "assess_lot_acceptance",
]

# Coverage and homogeneity are quotients of integers that land exactly on one
# for a clean delivery. Comparisons absorb representation error here rather
# than by relaxing the acceptance condition.
RATIO_TOLERANCE = 1e-9

# Documentation a delivered bare-chip batch carries with it.
REQUIRED_DOCUMENTS = (
    "certificate-of-conformity",
    "wafer-lot-acceptance-data",
    "visual-inspection-record",
    "packaging-and-storage-record",
    "esd-handling-record",
)


def _require_positive_int(value, label):
    """Return value as a positive int, raising on anything that is not one."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %d" % (label, value))
    return value


def _clean_identity(value):
    """Return a stripped identity string, or None when it identifies nothing."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("lot identity must be a string or None, got %r" % (value,))
    stripped = value.strip()
    if not stripped or stripped.lower() in {"unknown", "tbd", "n/a", "na", "-", "none"}:
        return None
    return stripped


def validate_sublots(sublots):
    """Return the normalised sublot records of a delivery.

    Each sublot names its wafer lot, its diffusion lot and its quantity. An
    identity that is absent or a placeholder normalises to None, which is what
    makes the sublot untraceable rather than an input error -- an untraceable
    delivery is a real thing that has to be graded, not rejected at the door.
    """
    if isinstance(sublots, dict) or not isinstance(sublots, (list, tuple)):
        raise ValueError("sublots must be a sequence of sublot records")
    if not sublots:
        raise ValueError("delivery contains no sublots")
    normalised = []
    for index, sublot in enumerate(sublots):
        if not isinstance(sublot, dict):
            raise ValueError("sublots[%d] must be a mapping" % index)
        if "quantity" not in sublot:
            raise ValueError("sublots[%d] needs a 'quantity'" % index)
        quantity = _require_positive_int(sublot["quantity"], "sublots[%d]['quantity']" % index)
        wafer_lot = _clean_identity(sublot.get("wafer_lot_id"))
        diffusion_lot = _clean_identity(sublot.get("diffusion_lot_id"))
        normalised.append(
            {
                "wafer_lot_id": wafer_lot,
                "diffusion_lot_id": diffusion_lot,
                "quantity": quantity,
                "traceable": wafer_lot is not None and diffusion_lot is not None,
            }
        )
    return normalised


def delivered_quantity(sublots):
    """Return the total number of dice across the delivery's sublots."""
    return sum(sublot["quantity"] for sublot in validate_sublots(sublots))


def reconcile_quantities(sublots, ordered_quantity, declared_quantity=None):
    """Return the quantity findings for a delivery.

    A declared quantity that disagrees with the sublot sum means the paperwork
    does not describe the goods. A delivered quantity short of or above the
    ordered quantity is a separate, softer finding.
    """
    total = delivered_quantity(sublots)
    ordered = _require_positive_int(ordered_quantity, "ordered_quantity")
    findings = []
    paperwork_disagrees = False
    if declared_quantity is not None:
        declared = _require_positive_int(declared_quantity, "declared_quantity")
        if declared != total:
            paperwork_disagrees = True
            findings.append(
                "delivery note declares %d dice but the sublots sum to %d"
                % (declared, total)
            )
    if total < ordered:
        findings.append("delivery is short: %d dice against %d ordered" % (total, ordered))
    elif total > ordered:
        findings.append("delivery is over: %d dice against %d ordered" % (total, ordered))
    return {
        "delivered": total,
        "ordered": ordered,
        "paperwork_disagrees": paperwork_disagrees,
        "quantity_matches_order": total == ordered,
        "findings": findings,
    }


def untraceable_sublots(sublots):
    """Return the indices of sublots missing a wafer-lot or diffusion-lot identity."""
    return [i for i, sublot in enumerate(validate_sublots(sublots)) if not sublot["traceable"]]


def traceability_coverage(sublots):
    """Return the fraction of delivered dice carrying a full lot identity."""
    normalised = validate_sublots(sublots)
    total = sum(sublot["quantity"] for sublot in normalised)
    traced = sum(sublot["quantity"] for sublot in normalised if sublot["traceable"])
    return traced / float(total)


def wafer_lot_breakdown(sublots):
    """Return the delivered quantity aggregated by wafer lot, largest first."""
    normalised = validate_sublots(sublots)
    totals = {}
    for sublot in normalised:
        key = sublot["wafer_lot_id"] if sublot["wafer_lot_id"] is not None else "unidentified"
        totals[key] = totals.get(key, 0) + sublot["quantity"]
    return sorted(totals.items(), key=lambda item: (-item[1], item[0]))


def homogeneity_ratio(sublots):
    """Return the largest wafer-lot aggregate as a fraction of the whole delivery."""
    breakdown = wafer_lot_breakdown(sublots)
    total = sum(quantity for _, quantity in breakdown)
    return breakdown[0][1] / float(total)


def missing_documents(provided, required=REQUIRED_DOCUMENTS):
    """Return the required delivery documents this batch did not carry."""
    if isinstance(provided, str) or not isinstance(provided, (list, tuple, set, frozenset)):
        raise ValueError("provided documents must be a sequence of document names")
    seen = set()
    for item in provided:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("document names must be non-empty strings, got %r" % (item,))
        seen.add(item.strip().lower().replace("_", "-").replace(" ", "-"))
    return [document for document in required if document not in seen]


def assess_lot_acceptance(spec):
    """Run the full clause 8.1.4 delivered-lot acceptance assessment.

    spec keys: sublots, ordered_quantity, documents, optional
    declared_quantity, optional multiple_wafer_lots_permitted (default False)
    and optional required_documents.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("sublots", "ordered_quantity", "documents"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    multi_permitted = spec.get("multiple_wafer_lots_permitted", False)
    if not isinstance(multi_permitted, bool):
        raise ValueError("multiple_wafer_lots_permitted must be a boolean")
    sublots = validate_sublots(spec["sublots"])
    quantities = reconcile_quantities(
        spec["sublots"], spec["ordered_quantity"], spec.get("declared_quantity")
    )
    coverage = traceability_coverage(spec["sublots"])
    homogeneity = homogeneity_ratio(spec["sublots"])
    absent_documents = missing_documents(
        spec["documents"], spec.get("required_documents", REQUIRED_DOCUMENTS)
    )
    fully_traceable = math.isclose(coverage, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE)
    single_wafer_lot = math.isclose(homogeneity, 1.0, rel_tol=0.0, abs_tol=RATIO_TOLERANCE)

    rejections = []
    reservations = []
    if not fully_traceable:
        rejections.append(
            "traceability coverage is %.4f; %d sublot(s) carry no full lot identity"
            % (coverage, len(untraceable_sublots(spec["sublots"])))
        )
    if absent_documents:
        rejections.append(
            "delivery documentation incomplete: %s" % ", ".join(absent_documents)
        )
    if quantities["paperwork_disagrees"]:
        rejections.append(
            "delivery note does not describe the goods; quantities cannot be reconciled"
        )
    if not single_wafer_lot:
        message = "delivery spans %d wafer lots; homogeneity ratio %.4f" % (
            len(wafer_lot_breakdown(spec["sublots"])),
            homogeneity,
        )
        if multi_permitted:
            reservations.append(message + " (multiple lots were permitted)")
        else:
            rejections.append(message)
    if not quantities["quantity_matches_order"] and not quantities["paperwork_disagrees"]:
        reservations.extend(
            f for f in quantities["findings"] if "delivery note" not in f
        )

    if rejections:
        disposition = "reject"
    elif reservations:
        disposition = "accept-with-reservation"
    else:
        disposition = "accept"
    return {
        "sublot_count": len(sublots),
        "delivered_quantity": quantities["delivered"],
        "ordered_quantity": quantities["ordered"],
        "traceability_coverage": coverage,
        "fully_traceable": fully_traceable,
        "homogeneity_ratio": homogeneity,
        "single_wafer_lot": single_wafer_lot,
        "wafer_lot_breakdown": wafer_lot_breakdown(spec["sublots"]),
        "missing_documents": absent_documents,
        "disposition": disposition,
        "rejections": rejections,
        "reservations": reservations,
        "accepted": disposition != "reject",
    }
