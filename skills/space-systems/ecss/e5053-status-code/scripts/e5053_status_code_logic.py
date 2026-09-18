#!/usr/bin/env python3
"""Status code field of a CCSDS packet transfer PDU, ECSS-E-ST-50-53C 5.1.3.

Paraphrased requirement, no verbatim standard text. The clause puts two
obligations on the status field a sending node writes into a CCSDS packet
transfer protocol data unit: the field has to report the outcome of the
transfer it accompanies, and encodings that are not assigned a meaning are
not to be emitted and are not to be read as success by a receiver. This
module turns both into a deterministic decision:

  encoding + code registry   -> success, a defined error, user-defined,
                                unassigned or reserved
  category                   -> accept, report the error, or reject the PDU
  a run of received codes    -> outcome counts, first failure, error fraction

The code registry is supplied by the deployment; the module ships a default
partition so a caller with no registry still gets a working, explicit one
rather than a silent assumption. stdlib only, offline, deterministic.
"""

from __future__ import annotations

# The field is one octet wide.
STATUS_CODE_MIN = 0
STATUS_CODE_MAX = 255

# The encoding that reports a transfer that completed with nothing to report.
SUCCESS_CODE = 0

# Deployment default partition of the remaining encodings. Inclusive bands.
# A project with its own code assignment passes its own bands to
# build_registry; these exist so the default behaviour is stated, not hidden.
DEFAULT_DEFINED_ERROR_BAND = (1, 15)
DEFAULT_USER_DEFINED_BAND = (128, 191)
DEFAULT_RESERVED_BAND = (192, 255)

SUCCESS = "success"
DEFINED_ERROR = "defined-error"
USER_DEFINED = "user-defined"
UNASSIGNED = "unassigned"
RESERVED = "reserved"
STATUS_CATEGORIES = (SUCCESS, DEFINED_ERROR, USER_DEFINED, UNASSIGNED, RESERVED)

ACCEPT = "accept"
REPORT_ERROR = "report-error"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REPORT_ERROR, REJECT)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer encoding, got %r" % (name, value))
    return int(value)


def validate_status_code(code):
    """Validate one status encoding against the width of the field."""
    value = _integer(code, "status_code")
    if value < STATUS_CODE_MIN or value > STATUS_CODE_MAX:
        raise ValueError(
            "status_code %d does not fit the one octet field (%d..%d)"
            % (value, STATUS_CODE_MIN, STATUS_CODE_MAX)
        )
    return value


def _band(band, name):
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s must be a (low, high) pair, got %r" % (name, band))
    low = validate_status_code(band[0])
    high = validate_status_code(band[1])
    if high < low:
        raise ValueError("%s is inverted: %d..%d" % (name, low, high))
    if low <= SUCCESS_CODE <= high:
        raise ValueError(
            "%s (%d..%d) swallows the success encoding %d"
            % (name, low, high, SUCCESS_CODE)
        )
    return (low, high)


def build_registry(
    defined_error_band=DEFAULT_DEFINED_ERROR_BAND,
    user_defined_band=DEFAULT_USER_DEFINED_BAND,
    reserved_band=DEFAULT_RESERVED_BAND,
):
    """Validate a status-code assignment and return it as a registry."""
    bands = {
        DEFINED_ERROR: _band(defined_error_band, "defined_error_band"),
        USER_DEFINED: _band(user_defined_band, "user_defined_band"),
        RESERVED: _band(reserved_band, "reserved_band"),
    }
    names = sorted(bands)
    for i, first in enumerate(names):
        for second in names[i + 1:]:
            lo1, hi1 = bands[first]
            lo2, hi2 = bands[second]
            if lo1 <= hi2 and lo2 <= hi1:
                raise ValueError(
                    "%s band %d..%d overlaps %s band %d..%d"
                    % (first, lo1, hi1, second, lo2, hi2)
                )
    return bands


def categorize_status_code(code, registry=None):
    """Group one status encoding by the meaning the registry gives it."""
    value = validate_status_code(code)
    bands = build_registry() if registry is None else registry
    for name in (DEFINED_ERROR, USER_DEFINED, RESERVED):
        if name not in bands:
            raise ValueError("registry is missing the %s band" % name)
    if value == SUCCESS_CODE:
        return SUCCESS
    for name in (DEFINED_ERROR, USER_DEFINED, RESERVED):
        low, high = bands[name]
        if low <= value <= high:
            return name
    return UNASSIGNED


def is_success(code):
    """True only for the encoding that reports nothing to report."""
    return validate_status_code(code) == SUCCESS_CODE


def disposition(code, registry=None, accept_user_defined=True):
    """What a receiving node does with a PDU carrying this status encoding."""
    category = categorize_status_code(code, registry)
    if category == SUCCESS:
        return ACCEPT
    if category == DEFINED_ERROR:
        return REPORT_ERROR
    if category == USER_DEFINED:
        return ACCEPT if accept_user_defined else REJECT
    return REJECT


def emittable(code, registry=None):
    """True when a sending node is allowed to write this encoding out."""
    return categorize_status_code(code, registry) in (
        SUCCESS,
        DEFINED_ERROR,
        USER_DEFINED,
    )


def summarize_status_codes(codes, registry=None):
    """Outcome counts, first failure and error fraction over a run of PDUs."""
    if not isinstance(codes, (list, tuple)):
        raise ValueError("codes must be a list of status encodings")
    if len(codes) == 0:
        raise ValueError("codes must hold at least one received status encoding")
    bands = build_registry() if registry is None else registry
    counts = dict((name, 0) for name in STATUS_CATEGORIES)
    first_failure = None
    for index, code in enumerate(codes):
        category = categorize_status_code(code, bands)
        counts[category] += 1
        if first_failure is None and category != SUCCESS:
            first_failure = index
    total = len(codes)
    return {
        "total": total,
        "counts": counts,
        "first_failure_index": first_failure,
        "success_fraction": counts[SUCCESS] / float(total),
        "error_fraction": (total - counts[SUCCESS]) / float(total),
    }


def assess_status_code(code, registry=None, accept_user_defined=True):
    """Full clause 5.1.3 assessment of one received status encoding."""
    bands = build_registry() if registry is None else registry
    value = validate_status_code(code)
    category = categorize_status_code(value, bands)
    action = disposition(value, bands, accept_user_defined)

    findings = []
    limitations = []
    if category == DEFINED_ERROR:
        findings.append(
            "status encoding %d reports a defined transfer error" % value
        )
    elif category == RESERVED:
        findings.append(
            "status encoding %d is reserved and must not have been emitted" % value
        )
    elif category == UNASSIGNED:
        findings.append(
            "status encoding %d has no assigned meaning in this registry" % value
        )
    elif category == USER_DEFINED and not accept_user_defined:
        findings.append(
            "status encoding %d is user-defined and this node accepts none" % value
        )
    if category == USER_DEFINED and accept_user_defined:
        limitations.append(
            "status encoding %d is user-defined; its meaning is outside the "
            "transfer protocol" % value
        )

    return {
        "status_code": value,
        "category": category,
        "disposition": action,
        "emittable": emittable(value, bands),
        "findings": findings,
        "limitations": limitations,
        "verdict": "accept" if action == ACCEPT else "hold",
    }
