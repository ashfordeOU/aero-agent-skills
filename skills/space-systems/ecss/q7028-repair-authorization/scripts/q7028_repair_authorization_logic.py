"""Authorization of board repairs and modifications.

Anchor: ECSS-Q-ST-70-28C, programme clause -- nothing is repaired or modified
on a delivered board until an authority competent for that kind of work has
approved it, and until the file that will outlive the hardware holds the
entries that make the repair traceable. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Derive the minimum approving authority from the work type, the hardware
   model, the criticality of the item and whether the method is a listed one.
2. Compare the authority actually obtained against that minimum on an ordered
   ladder, so a signature one rung short is a refusal, not a detail.
3. List the record entries the repair file still owes, including the extra
   entries a modification and a customer-level approval pull in.
4. Check the retention period declared for the file against the minimum the
   programme has to keep.
5. Return the authorization verdict with every finding that produced it.
"""

__all__ = [
    "AUTHORITY_LADDER",
    "WORK_TYPES",
    "HARDWARE_MODELS",
    "MODEL_MINIMUM_AUTHORITY",
    "WORK_TYPE_MINIMUM_AUTHORITY",
    "CRITICALITY_MINIMUM_AUTHORITY",
    "BASE_RECORDS",
    "MODIFICATION_RECORDS",
    "CUSTOMER_RECORDS",
    "UNLISTED_METHOD_AUTHORITY",
    "MINIMUM_RETENTION_YEARS",
    "authority_rank",
    "required_authority",
    "missing_records",
    "retention_findings",
    "authorize_repair",
]

# Approving authorities, weakest first. The index is the rung.
AUTHORITY_LADDER = (
    "operator",
    "inspector",
    "quality-assurance",
    "design-authority",
    "customer",
)

# Work the clause governs.
WORK_TYPES = ("repair", "modification")

# Hardware models, and the floor each one puts under any approval.
HARDWARE_MODELS = ("breadboard", "engineering-model", "qualification-model", "flight")
MODEL_MINIMUM_AUTHORITY = {
    "breadboard": "operator",
    "engineering-model": "inspector",
    "qualification-model": "quality-assurance",
    "flight": "quality-assurance",
}

# A modification changes the design, so the design authority owns it.
WORK_TYPE_MINIMUM_AUTHORITY = {
    "repair": "inspector",
    "modification": "design-authority",
}

# Criticality of the function the board carries, 1 being the most severe.
CRITICALITY_MINIMUM_AUTHORITY = {
    1: "customer",
    2: "design-authority",
    3: "quality-assurance",
    4: "inspector",
}

# A method outside the listed catalogue always reaches the customer.
UNLISTED_METHOD_AUTHORITY = "customer"

# Entries every repair file carries.
BASE_RECORDS = (
    "repair-request-id",
    "damage-description",
    "method-reference",
    "operator-id",
    "inspection-result",
    "repair-date",
)

# Extra entries a design-altering change pulls in.
MODIFICATION_RECORDS = ("drawing-change-ref", "as-built-update-ref")

# Extra entry a customer-level approval pulls in.
CUSTOMER_RECORDS = ("customer-approval-ref",)

# The repair file outlives the hardware it describes.
MINIMUM_RETENTION_YEARS = 10


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def authority_rank(authority):
    """Return the rung of an authority on the ladder."""
    token = _token(authority, "authority")
    if token not in AUTHORITY_LADDER:
        raise ValueError(
            "unknown authority '%s'; expected one of %s"
            % (token, ", ".join(AUTHORITY_LADDER))
        )
    return AUTHORITY_LADDER.index(token)


def _highest(*authorities):
    return max(authorities, key=authority_rank)


def required_authority(work_type, hardware_model, criticality, listed_method=True):
    """Return the minimum authority that may approve this piece of work."""
    work = _token(work_type, "work_type")
    if work not in WORK_TYPES:
        raise ValueError("unknown work_type '%s'" % work)
    model = _token(hardware_model, "hardware_model")
    if model not in HARDWARE_MODELS:
        raise ValueError("unknown hardware_model '%s'" % model)
    if not isinstance(criticality, int) or isinstance(criticality, bool):
        raise ValueError("criticality must be an integer level, got %r" % (criticality,))
    if criticality not in CRITICALITY_MINIMUM_AUTHORITY:
        raise ValueError(
            "criticality must be one of %s, got %d"
            % (sorted(CRITICALITY_MINIMUM_AUTHORITY), criticality)
        )
    if not isinstance(listed_method, bool):
        raise ValueError("listed_method must be a boolean")

    needed = _highest(
        WORK_TYPE_MINIMUM_AUTHORITY[work],
        MODEL_MINIMUM_AUTHORITY[model],
        CRITICALITY_MINIMUM_AUTHORITY[criticality],
    )
    if not listed_method:
        needed = _highest(needed, UNLISTED_METHOD_AUTHORITY)
    return needed


def missing_records(record, work_type="repair", approving_authority="inspector"):
    """Return the record entries the repair file still owes, in order."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    work = _token(work_type, "work_type")
    if work not in WORK_TYPES:
        raise ValueError("unknown work_type '%s'" % work)
    expected = list(BASE_RECORDS)
    if work == "modification":
        expected.extend(MODIFICATION_RECORDS)
    if authority_rank(approving_authority) >= authority_rank("customer"):
        expected.extend(CUSTOMER_RECORDS)
    missing = []
    for key in expected:
        value = record.get(key)
        if value is None:
            missing.append(key)
        elif isinstance(value, str) and not value.strip():
            missing.append(key)
    return missing


def retention_findings(retention_years):
    """Grade the declared retention period for the repair file."""
    if not isinstance(retention_years, (int, float)) or isinstance(retention_years, bool):
        raise ValueError("retention_years must be a real number")
    years = float(retention_years)
    if years < 0.0:
        raise ValueError("retention_years must be non-negative, got %g" % years)
    if years < MINIMUM_RETENTION_YEARS:
        return [
            "repair file retention of %g years is short of the %d years the "
            "programme has to keep" % (years, MINIMUM_RETENTION_YEARS)
        ]
    return []


def authorize_repair(request):
    """Decide whether one repair or modification request is authorized.

    request keys: work_type, hardware_model, criticality, approved_by, optional
    listed_method, record and retention_years.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    for key in ("work_type", "hardware_model", "criticality", "approved_by"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)

    listed = request.get("listed_method", True)
    needed = required_authority(
        request["work_type"],
        request["hardware_model"],
        request["criticality"],
        listed,
    )
    obtained = _token(request["approved_by"], "approved_by")
    obtained_rank = authority_rank(obtained)
    needed_rank = authority_rank(needed)

    findings = []
    if obtained_rank < needed_rank:
        findings.append(
            "approval was given at '%s' but this work needs '%s' or above"
            % (obtained, needed)
        )
    if not listed:
        findings.append(
            "the proposed method is outside the listed catalogue, so the customer "
            "approves it and the method is written into the file"
        )

    record = request.get("record", {})
    missing = missing_records(record, request["work_type"], needed)
    if missing:
        findings.append(
            "the repair file is missing %d entry/entries: %s"
            % (len(missing), ", ".join(missing))
        )

    retention = request.get("retention_years", MINIMUM_RETENTION_YEARS)
    findings.extend(retention_findings(retention))

    return {
        "work_type": _token(request["work_type"], "work_type"),
        "hardware_model": _token(request["hardware_model"], "hardware_model"),
        "criticality": request["criticality"],
        "listed_method": listed,
        "required_authority": needed,
        "obtained_authority": obtained,
        "rungs_short": max(0, needed_rank - obtained_rank),
        "missing_records": missing,
        "findings": findings,
        "authorized": not findings,
    }
