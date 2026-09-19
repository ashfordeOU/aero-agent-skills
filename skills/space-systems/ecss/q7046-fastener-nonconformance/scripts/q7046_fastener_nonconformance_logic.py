#!/usr/bin/env python3
"""Nonconforming threaded fastener lots: quarantine, disposition, scrap.

Anchor: ECSS-Q-ST-70-46 nonconformance clause on threaded fasteners. The
procedure below is a paraphrase into implementable steps; no standard
text is reproduced.

Three decisions follow a nonconformance raised against a fastener lot.

How far the quarantine reaches. A defect made by one operation on one
lot is contained by that lot. A defect that came out of the heat, the
heat-treatment charge or the plating tank reaches every lot that shared
it, and where the traceability records cannot resolve which lots those
were, the quarantine has to reach the whole of the supplier's stock on
hand because nothing narrower can be justified from the records.

Which dispositions are even on the table. Use-as-is and rework are not
available for every defect. A material, heat-treatment or
hydrogen-embrittlement defect is a property of the metal itself, so no
amount of rework returns the part to the specification it was bought
against and the lot is scrapped or returned. A coating defect is a
surface condition and can be stripped and re-applied, but only while the
part still has re-plating cycles left, because each strip removes base
metal and each re-bake is another thermal exposure.

Who has to sign. A review board always. The customer as well, whenever
the part is kept against the specification it failed.

Scrap is a physical act, not a paperwork state: a scrapped fastener is
mutilated so it cannot be picked back out of a bin and fitted.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CRITICALITIES = ("critical", "major", "minor")

DEFECT_MATERIAL = "material-property"
DEFECT_HEAT_TREATMENT = "heat-treatment"
DEFECT_HYDROGEN_EMBRITTLEMENT = "hydrogen-embrittlement"
DEFECT_DIMENSIONAL = "dimensional"
DEFECT_SURFACE = "surface-discontinuity"
DEFECT_COATING = "coating"
DEFECT_MARKING = "marking"
DEFECT_DOCUMENTATION = "documentation"

DEFECT_CLASSES = (
    DEFECT_MATERIAL,
    DEFECT_HEAT_TREATMENT,
    DEFECT_HYDROGEN_EMBRITTLEMENT,
    DEFECT_DIMENSIONAL,
    DEFECT_SURFACE,
    DEFECT_COATING,
    DEFECT_MARKING,
    DEFECT_DOCUMENTATION,
)

# Defects that live in the metal. No rework returns the part to the
# specification it was bought against.
IRRECOVERABLE_DEFECTS = (
    DEFECT_MATERIAL,
    DEFECT_HEAT_TREATMENT,
    DEFECT_HYDROGEN_EMBRITTLEMENT,
)

ORIGIN_SINGLE_LOT = "single-lot-operation"
ORIGIN_HEAT = "heat"
ORIGIN_HEAT_TREAT_CHARGE = "heat-treatment-charge"
ORIGIN_PLATING_BATCH = "plating-batch"
ORIGIN_UNKNOWN = "unknown"

DEFECT_ORIGINS = (
    ORIGIN_SINGLE_LOT,
    ORIGIN_HEAT,
    ORIGIN_HEAT_TREAT_CHARGE,
    ORIGIN_PLATING_BATCH,
    ORIGIN_UNKNOWN,
)

SCOPE_LOT = "this-lot"
SCOPE_SHARED_PROCESS = "every-lot-sharing-the-process-record"
SCOPE_SUPPLIER_STOCK = "all-stock-from-this-supplier"

DISPOSITION_USE_AS_IS = "use-as-is"
DISPOSITION_REWORK = "rework"
DISPOSITION_REPAIR = "repair"
DISPOSITION_RETURN = "return-to-supplier"
DISPOSITION_SCRAP = "scrap"

DISPOSITIONS = (
    DISPOSITION_USE_AS_IS,
    DISPOSITION_REWORK,
    DISPOSITION_REPAIR,
    DISPOSITION_RETURN,
    DISPOSITION_SCRAP,
)

# Dispositions that keep the part in the build against the requirement
# it failed, so the customer signs as well as the review board.
CUSTOMER_APPROVED = (DISPOSITION_USE_AS_IS, DISPOSITION_REPAIR)

MAX_REPLATING_CYCLES = 2


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


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
    return value


def quarantine_scope(defect_origin, traceability_intact):
    """How far the hold reaches, given where the defect came from."""
    _require_choice("defect_origin", defect_origin, DEFECT_ORIGINS)
    intact = _require_bool("traceability_intact", traceability_intact)
    if not intact:
        return {
            "scope": SCOPE_SUPPLIER_STOCK,
            "reason": "the records cannot resolve which lots shared the "
            "process, so nothing narrower than the supplier's whole stock "
            "can be justified",
        }
    if defect_origin == ORIGIN_UNKNOWN:
        return {
            "scope": SCOPE_SUPPLIER_STOCK,
            "reason": "the origin of the defect is not established, so the "
            "hold cannot be narrowed to a process record yet",
        }
    if defect_origin == ORIGIN_SINGLE_LOT:
        return {
            "scope": SCOPE_LOT,
            "reason": "the defect was made by an operation this lot alone "
            "went through",
        }
    return {
        "scope": SCOPE_SHARED_PROCESS,
        "reason": "the defect came out of the %s, so every lot carrying that "
        "record is held with it" % defect_origin.replace("-", " "),
    }


def replating_available(cycles_used):
    """Whether the coating can be stripped and re-applied once more."""
    used = _require_count("cycles_used", cycles_used)
    return used < MAX_REPLATING_CYCLES


def permitted_dispositions(defect_class, criticality, replating_cycles_used=0):
    """Dispositions that are genuinely on the table for this defect."""
    _require_choice("defect_class", defect_class, DEFECT_CLASSES)
    _require_choice("criticality", criticality, CRITICALITIES)
    used = _require_count("replating_cycles_used", replating_cycles_used)
    if defect_class in IRRECOVERABLE_DEFECTS:
        return [DISPOSITION_RETURN, DISPOSITION_SCRAP]
    if defect_class == DEFECT_COATING:
        options = [DISPOSITION_RETURN, DISPOSITION_SCRAP]
        if replating_available(used):
            options.insert(0, DISPOSITION_REWORK)
        if criticality == "minor":
            options.insert(0, DISPOSITION_USE_AS_IS)
        return options
    if defect_class in (DEFECT_MARKING, DEFECT_DOCUMENTATION):
        options = [DISPOSITION_RETURN, DISPOSITION_SCRAP]
        if defect_class == DEFECT_MARKING:
            options.insert(0, DISPOSITION_REWORK)
        if criticality != "critical":
            options.insert(0, DISPOSITION_USE_AS_IS)
        return options
    # dimensional and surface defects: the geometry is wrong, and only
    # removing material can change it, which a fastener cannot afford in
    # the zones that carry the load.
    options = [DISPOSITION_RETURN, DISPOSITION_SCRAP]
    if criticality == "critical":
        return options
    options.insert(0, DISPOSITION_USE_AS_IS)
    return options


def approvals_required(disposition, criticality):
    """Signatures a disposition needs before it may be actioned."""
    _require_choice("disposition", disposition, DISPOSITIONS)
    _require_choice("criticality", criticality, CRITICALITIES)
    approvals = ["nonconformance-review-board"]
    if disposition in CUSTOMER_APPROVED:
        approvals.append("customer")
    if disposition == DISPOSITION_SCRAP and criticality == "critical":
        approvals.append("quality-assurance-witness-of-mutilation")
    return approvals


def scrap_actions(criticality):
    """What scrapping a fastener physically requires, not just records."""
    _require_choice("criticality", criticality, CRITICALITIES)
    actions = [
        "mutilate each part so it cannot be fitted",
        "remove the lot identity from the stock record",
        "record the mutilated quantity against the lot",
    ]
    if criticality == "critical":
        actions.append("witness the mutilation and sign the record")
    return actions


def disposition_case(case):
    """Quarantine, permitted dispositions and approvals for one finding."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    lot_id = case.get("lot_id")
    if not isinstance(lot_id, str) or not lot_id.strip():
        raise ValueError("case needs a non-empty string lot_id, got %r" % (lot_id,))
    defect_class = _require_choice(
        "defect_class", case.get("defect_class"), DEFECT_CLASSES
    )
    criticality = _require_choice(
        "criticality", case.get("criticality"), CRITICALITIES
    )
    origin = _require_choice(
        "defect_origin", case.get("defect_origin"), DEFECT_ORIGINS
    )
    intact = _require_bool(
        "traceability_intact", case.get("traceability_intact", True)
    )
    used = _require_count(
        "replating_cycles_used", case.get("replating_cycles_used", 0)
    )
    installed = _require_count("quantity_installed", case.get("quantity_installed", 0))
    quarantine = quarantine_scope(origin, intact)
    options = permitted_dispositions(defect_class, criticality, used)
    findings = []
    if defect_class in IRRECOVERABLE_DEFECTS:
        findings.append(
            "a %s defect is a property of the metal; no rework returns the "
            "part to the specification it was bought against"
            % defect_class.replace("-", " ")
        )
    if defect_class == DEFECT_COATING and not replating_available(used):
        findings.append(
            "the coating has already been stripped and re-applied %d times; "
            "another strip removes base metal the part cannot spare" % used
        )
    if installed > 0:
        findings.append(
            "%d part(s) from this lot are already installed; raise the recall "
            "against the assemblies before the lot record is closed" % installed
        )
    proposed = case.get("proposed_disposition")
    result = {
        "lot_id": lot_id,
        "defect_class": defect_class,
        "criticality": criticality,
        "quarantine_scope": quarantine["scope"],
        "quarantine_reason": quarantine["reason"],
        "permitted_dispositions": options,
        "quantity_installed": installed,
        "findings": findings,
    }
    if proposed is None:
        result.update(
            {
                "proposed_disposition": None,
                "accepted": False,
                "approvals_required": [],
                "verdict": "awaiting-disposition",
            }
        )
        return result
    _require_choice("proposed_disposition", proposed, DISPOSITIONS)
    if proposed not in options:
        findings.append(
            "%s is not available for a %s defect on a %s fastener; the "
            "options are %s" % (proposed, defect_class, criticality,
                                ", ".join(options))
        )
        result.update(
            {
                "proposed_disposition": proposed,
                "accepted": False,
                "approvals_required": [],
                "verdict": "disposition-refused",
            }
        )
        return result
    result.update(
        {
            "proposed_disposition": proposed,
            "accepted": True,
            "approvals_required": approvals_required(proposed, criticality),
            "verdict": "disposition-accepted",
        }
    )
    if proposed == DISPOSITION_SCRAP:
        result["scrap_actions"] = scrap_actions(criticality)
    return result
