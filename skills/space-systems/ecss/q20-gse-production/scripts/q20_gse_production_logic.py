"""Ground support equipment production quality assurance logic.

Anchor: ECSS-Q-ST-20C clause 5.8.3 (5.8.3.1-5.8.3.2) -- quality assurance of
ground support equipment production: the procurement assurance applied to the
parts and assemblies bought in, and the control of the manufacturing, assembly
and integration of the GSE item itself. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade each procurement lot on the approval state of its supplier, the
   incoming inspection result, the conformity evidence that arrived with it and
   whether it can be traced to a lot at all.
2. Apply the surveillance a conditionally approved supplier owes: the lot is
   usable, but only with the extra measure that made the approval conditional.
3. Replay the manufacturing, assembly and integration operations in sequence,
   refusing an operation performed out of order, one run on a lapsed process
   qualification and one run by an operator whose certification had expired.
4. Check every mandatory inspection point against the operation it belongs to:
   completed, and witnessed by the function the point calls for.
5. Combine into released, released-with-actions or held, with the completion
   fraction of the inspection points reported alongside.
"""

import math

__all__ = [
    "SUPPLIER_STATES",
    "INSPECTION_RESULTS",
    "WITNESS_FUNCTIONS",
    "RATIO_TOLERANCE",
    "normalize_token",
    "validate_lot",
    "procurement_findings",
    "validate_operation",
    "validate_operation_set",
    "operation_findings",
    "validate_inspection_point",
    "inspection_point_findings",
    "completion_ratio",
    "release_verdict",
    "assess_gse_production",
]

SUPPLIER_STATES = ("approved", "conditionally-approved", "not-approved")
INSPECTION_RESULTS = ("accepted", "rejected", "pending")
WITNESS_FUNCTIONS = ("customer", "quality-assurance", "none")

# Ratios of small integers can land a few ULPs off an exact value.
RATIO_TOLERANCE = 1e-9


def normalize_token(value, label="token"):
    """Return a lowercase, hyphen-joined comparison token for an identifier."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    token = "-".join(value.strip().lower().replace("_", " ").replace("-", " ").split())
    if not token:
        raise ValueError("%s must not be blank" % label)
    return token


def _whole(value, label, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    return value


def _flag(value, label):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_lot(lot, index=0):
    """Return one validated procurement lot record for a GSE item."""
    if not isinstance(lot, dict):
        raise ValueError("lots[%d] must be a mapping" % index)
    for key in ("id", "supplier_state", "inspection_result"):
        if key not in lot:
            raise ValueError("lots[%d] is missing '%s'" % (index, key))
    lot_id = normalize_token(lot["id"], "lots[%d]['id']" % index)
    supplier_state = normalize_token(lot["supplier_state"], "lots[%d]['supplier_state']" % index)
    if supplier_state not in SUPPLIER_STATES:
        raise ValueError(
            "lot %s supplier state %r is not one of %s" % (lot_id, supplier_state, SUPPLIER_STATES)
        )
    result = normalize_token(lot["inspection_result"], "lots[%d]['inspection_result']" % index)
    if result not in INSPECTION_RESULTS:
        raise ValueError(
            "lot %s inspection result %r is not one of %s" % (lot_id, result, INSPECTION_RESULTS)
        )
    return {
        "id": lot_id,
        "supplier_state": supplier_state,
        "inspection_result": result,
        "conformity_certificate": _flag(
            lot.get("conformity_certificate", False), "lots[%d]['conformity_certificate']" % index
        ),
        "lot_traceable": _flag(lot.get("lot_traceable", False), "lots[%d]['lot_traceable']" % index),
        "surveillance_applied": _flag(
            lot.get("surveillance_applied", False), "lots[%d]['surveillance_applied']" % index
        ),
    }


def procurement_findings(lots):
    """Return the grouped blocking and action findings for the bought-in lots."""
    if lots is None:
        lots = []
    if not isinstance(lots, (list, tuple)):
        raise ValueError("lots must be a sequence of procurement lot records")
    seen = set()
    blocking = []
    actions = []
    for i, raw in enumerate(lots):
        lot = validate_lot(raw, i)
        if lot["id"] in seen:
            raise ValueError("procurement lot %s is entered twice" % lot["id"])
        seen.add(lot["id"])
        if lot["supplier_state"] == "not-approved":
            blocking.append("lot %s came from a supplier that is not approved" % lot["id"])
        elif lot["supplier_state"] == "conditionally-approved" and not lot["surveillance_applied"]:
            blocking.append(
                "lot %s came from a conditionally approved supplier with no surveillance applied"
                % lot["id"]
            )
        if lot["inspection_result"] == "rejected":
            blocking.append("lot %s was rejected at incoming inspection" % lot["id"])
        elif lot["inspection_result"] == "pending":
            actions.append("lot %s has not completed incoming inspection" % lot["id"])
        if not lot["conformity_certificate"]:
            blocking.append("lot %s arrived without a conformity certificate" % lot["id"])
        if not lot["lot_traceable"]:
            blocking.append("lot %s cannot be traced to a manufacturing lot" % lot["id"])
    return {"blocking": blocking, "actions": actions}


def validate_operation(operation, index=0):
    """Return one validated manufacturing, assembly or integration operation."""
    if not isinstance(operation, dict):
        raise ValueError("operations[%d] must be a mapping" % index)
    for key in ("id", "sequence"):
        if key not in operation:
            raise ValueError("operations[%d] is missing '%s'" % (index, key))
    return {
        "id": normalize_token(operation["id"], "operations[%d]['id']" % index),
        "sequence": _whole(operation["sequence"], "operations[%d]['sequence']" % index, minimum=1),
        "completed": _flag(operation.get("completed", False), "operations[%d]['completed']" % index),
        "process_qualification_days": _whole(
            operation.get("process_qualification_days", 0),
            "operations[%d]['process_qualification_days']" % index,
        ),
        "operator_certification_days": _whole(
            operation.get("operator_certification_days", 0),
            "operations[%d]['operator_certification_days']" % index,
        ),
    }


def validate_operation_set(operations):
    """Return the validated operation set, refusing a duplicated identifier or sequence."""
    if not isinstance(operations, (list, tuple)) or not operations:
        raise ValueError("operations must be a non-empty sequence of operation records")
    ids = set()
    sequences = set()
    validated = []
    for i, operation in enumerate(operations):
        record = validate_operation(operation, i)
        if record["id"] in ids:
            raise ValueError("operation %s is declared twice" % record["id"])
        if record["sequence"] in sequences:
            raise ValueError("sequence number %d is used twice" % record["sequence"])
        ids.add(record["id"])
        sequences.add(record["sequence"])
        validated.append(record)
    validated.sort(key=lambda r: r["sequence"])
    return validated


def operation_findings(operations):
    """Return the findings from replaying the operations in sequence."""
    blocking = []
    actions = []
    previous_complete = True
    for operation in operations:
        if operation["completed"]:
            if not previous_complete:
                blocking.append(
                    "operation %s was performed before the operation ahead of it in sequence"
                    % operation["id"]
                )
            if operation["process_qualification_days"] < 0:
                blocking.append(
                    "operation %s was run on a process qualification that had lapsed by %d day(s)"
                    % (operation["id"], -operation["process_qualification_days"])
                )
            if operation["operator_certification_days"] < 0:
                blocking.append(
                    "operation %s was run by an operator whose certification had lapsed by %d day(s)"
                    % (operation["id"], -operation["operator_certification_days"])
                )
        else:
            actions.append("operation %s is not complete" % operation["id"])
            previous_complete = False
    return {"blocking": blocking, "actions": actions}


def validate_inspection_point(point, index=0):
    """Return one validated mandatory inspection point."""
    if not isinstance(point, dict):
        raise ValueError("inspection_points[%d] must be a mapping" % index)
    for key in ("id", "operation_id", "required_witness"):
        if key not in point:
            raise ValueError("inspection_points[%d] is missing '%s'" % (index, key))
    required = normalize_token(
        point["required_witness"], "inspection_points[%d]['required_witness']" % index
    )
    if required not in WITNESS_FUNCTIONS:
        raise ValueError(
            "inspection point witness %r is not one of %s" % (required, WITNESS_FUNCTIONS)
        )
    witnessed = point.get("witnessed_by")
    if witnessed is not None:
        witnessed = normalize_token(
            witnessed, "inspection_points[%d]['witnessed_by']" % index
        )
        if witnessed not in WITNESS_FUNCTIONS:
            raise ValueError(
                "inspection point witness %r is not one of %s" % (witnessed, WITNESS_FUNCTIONS)
            )
    return {
        "id": normalize_token(point["id"], "inspection_points[%d]['id']" % index),
        "operation_id": normalize_token(
            point["operation_id"], "inspection_points[%d]['operation_id']" % index
        ),
        "required_witness": required,
        "witnessed_by": witnessed,
        "completed": _flag(
            point.get("completed", False), "inspection_points[%d]['completed']" % index
        ),
    }


def inspection_point_findings(points, operations):
    """Return the findings about the mandatory inspection points of the build."""
    known = {operation["id"]: operation for operation in operations}
    blocking = []
    actions = []
    seen = set()
    for i, raw in enumerate(points):
        point = validate_inspection_point(raw, i)
        if point["id"] in seen:
            raise ValueError("inspection point %s is declared twice" % point["id"])
        seen.add(point["id"])
        operation = known.get(point["operation_id"])
        if operation is None:
            blocking.append(
                "inspection point %s belongs to %s, which is not an operation of this build"
                % (point["id"], point["operation_id"])
            )
            continue
        if operation["completed"] and not point["completed"]:
            blocking.append(
                "operation %s was completed past unfinished inspection point %s"
                % (operation["id"], point["id"])
            )
            continue
        if not point["completed"]:
            actions.append("inspection point %s is still open" % point["id"])
            continue
        if point["required_witness"] != "none" and point["witnessed_by"] != point["required_witness"]:
            blocking.append(
                "inspection point %s needed a %s witness but records %s"
                % (point["id"], point["required_witness"], point["witnessed_by"] or "none")
            )
    return {"blocking": blocking, "actions": actions}


def completion_ratio(points):
    """Return the fraction of the mandatory inspection points that are complete."""
    if not isinstance(points, (list, tuple)):
        raise ValueError("points must be a sequence of inspection point records")
    if not points:
        raise ValueError("a build with no mandatory inspection point has no completion ratio")
    done = 0
    for i, raw in enumerate(points):
        point = raw if isinstance(raw, dict) and "required_witness" in raw else None
        if point is None:
            raise ValueError("points[%d] must be an inspection point record" % i)
        if _flag(point.get("completed", False), "points[%d]['completed']" % i):
            done += 1
    return float(done) / float(len(points))


def release_verdict(blocking, actions):
    """Return released, released-with-actions or held for the finding sets."""
    if not isinstance(blocking, (list, tuple)) or not isinstance(actions, (list, tuple)):
        raise ValueError("blocking and actions must be sequences")
    if blocking:
        return "held"
    if actions:
        return "released-with-actions"
    return "released"


def assess_gse_production(spec):
    """Run the full clause 5.8.3 GSE production assurance assessment.

    spec keys: operations, inspection_points, optional lots and
    required_completion.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("operations", "inspection_points"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    points = spec["inspection_points"]
    if not isinstance(points, (list, tuple)):
        raise ValueError("spec['inspection_points'] must be a sequence")
    operations = validate_operation_set(spec["operations"])
    procurement = procurement_findings(spec.get("lots"))
    build = operation_findings(operations)
    inspection = inspection_point_findings(points, operations)
    ratio = completion_ratio(points) if points else 1.0

    blocking = list(procurement["blocking"]) + list(build["blocking"]) + list(inspection["blocking"])
    actions = list(procurement["actions"]) + list(build["actions"]) + list(inspection["actions"])

    required = spec.get("required_completion")
    if required is not None:
        if not isinstance(required, (int, float)) or isinstance(required, bool):
            raise ValueError("required_completion must be a real number")
        required = float(required)
        if not math.isfinite(required) or not 0.0 <= required <= 1.0:
            raise ValueError("required_completion must lie in [0, 1]")
        if ratio < required and not math.isclose(
            ratio, required, rel_tol=0.0, abs_tol=RATIO_TOLERANCE
        ):
            blocking.append(
                "inspection point completion %.3f is below the required %.3f" % (ratio, required)
            )
    verdict = release_verdict(blocking, actions)
    return {
        "operations": operations,
        "procurement_findings": procurement,
        "build_findings": build,
        "inspection_findings": inspection,
        "completion_ratio": ratio,
        "blocking": blocking,
        "actions": actions,
        "verdict": verdict,
        "releasable": verdict != "held",
    }
