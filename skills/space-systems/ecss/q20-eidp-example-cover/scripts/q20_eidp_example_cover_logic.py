"""End item data package cover page as the standard header format.

Anchor: ECSS-Q-ST-20C Annex F (informative), the worked cover page of the end
item data package. The example is used here as the house header format for the
package whose content Annex B fixes: the same identification fields in the
same order, a package number built to one pattern, and an approval block whose
three roles are signed in sequence. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the header field order the example fixes and which fields are
   mandatory on every cover.
2. Validate a submitted header: nothing mandatory blank, the issue and the
   document count positive integers, the issue date an ISO day.
3. Build and check the package number against the pattern the contract and
   the serial number give, so two packages cannot share one number.
4. Check the approval block: three distinct people, signed in the order
   prepared, checked, approved, none of them dated after the cover issue.
5. Cross-check the declared document count against the index it heads.
6. Render the header deterministically and return the verdict.
"""

from datetime import date

__all__ = [
    "HEADER_FIELDS",
    "MANDATORY_HEADER_FIELDS",
    "APPROVAL_ROLES",
    "normalise_identifier",
    "parse_day",
    "format_eidp_number",
    "validate_header",
    "approval_chain_findings",
    "document_count_findings",
    "number_findings",
    "render_header",
    "assess_eidp_cover",
]

# The header in the order the worked example prints it.
HEADER_FIELDS = (
    "project",
    "contract_number",
    "item_designation",
    "part_number",
    "serial_number",
    "eidp_number",
    "issue",
    "issue_date",
    "document_count",
    "index_reference",
    "customer_acceptance",
)

# Fields without which the cover heads nothing in particular.
MANDATORY_HEADER_FIELDS = (
    "project",
    "contract_number",
    "item_designation",
    "part_number",
    "serial_number",
    "eidp_number",
    "issue",
    "issue_date",
    "document_count",
    "index_reference",
)

# The approval block, in the order the signatures are taken.
APPROVAL_ROLES = ("prepared-by", "checked-by", "approved-by")

_INTEGER_FIELDS = ("issue", "document_count")
_DATE_FIELDS = ("issue_date",)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def parse_day(value, label):
    """Return an ISO date; raise on anything that is not one."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s must be an ISO date (YYYY-MM-DD), got %r" % (label, value))


def _positive_integer(value, label):
    """Return a positive integer; raise on anything else."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s must be an integer of at least 1, got %r" % (label, value))
    return value


def format_eidp_number(contract_number, serial_number):
    """Return the package number the contract and serial number give."""
    contract = normalise_identifier(contract_number, "contract_number")
    serial = normalise_identifier(serial_number, "serial_number")
    return "%s-eidp-%s" % (contract, serial)


def validate_header(header):
    """Return the normalised cover header; raise on a malformed one."""
    if not isinstance(header, dict):
        raise ValueError("header must be a mapping")
    unknown = sorted(key for key in header if key not in HEADER_FIELDS)
    if unknown:
        raise ValueError(
            "header carries fields the cover has no place for: %s" % ", ".join(unknown)
        )
    result = {}
    for field in HEADER_FIELDS:
        if field not in header or header[field] is None:
            result[field] = None
            continue
        if field in _INTEGER_FIELDS:
            result[field] = _positive_integer(header[field], "header[%r]" % field)
        elif field in _DATE_FIELDS:
            result[field] = parse_day(header[field], "header[%r]" % field)
        else:
            result[field] = normalise_identifier(header[field], "header[%r]" % field)
    absent = [field for field in MANDATORY_HEADER_FIELDS if result[field] is None]
    if absent:
        raise ValueError("header leaves mandatory fields blank: %s" % ", ".join(absent))
    return result


def number_findings(normalised):
    """Return findings where the package number breaks the house pattern."""
    expected = format_eidp_number(normalised["contract_number"], normalised["serial_number"])
    if normalised["eidp_number"] != expected:
        return [
            "the cover reads %s while the contract and serial number give %s"
            % (normalised["eidp_number"], expected)
        ]
    return []


def _validate_approval(approvals):
    """Return the approval block normalised by role."""
    if not isinstance(approvals, dict):
        raise ValueError("approvals must be a mapping of role to signature")
    block = {}
    for role in APPROVAL_ROLES:
        entry = approvals.get(role)
        if entry is None:
            block[role] = None
            continue
        if not isinstance(entry, dict):
            raise ValueError("approvals[%r] must be a mapping" % role)
        block[role] = {
            "name": normalise_identifier(entry.get("name"), "approvals[%r].name" % role),
            "signed_on": parse_day(
                entry.get("signed_on"), "approvals[%r].signed_on" % role
            ),
        }
    unknown = sorted(role for role in approvals if role not in APPROVAL_ROLES)
    if unknown:
        raise ValueError("approvals carries unknown roles: %s" % ", ".join(unknown))
    return block


def approval_chain_findings(normalised, approvals):
    """Return findings on the three-signature approval block."""
    block = _validate_approval(approvals)
    findings = []
    absent = [role for role in APPROVAL_ROLES if block[role] is None]
    if absent:
        findings.append("the approval block is unsigned by %s" % ", ".join(absent))
    signed = [role for role in APPROVAL_ROLES if block[role] is not None]
    names = [block[role]["name"] for role in signed]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    for name in duplicates:
        findings.append(
            "%s holds more than one role in the approval block, so the check is self-made"
            % name
        )
    for earlier, later in zip(signed, signed[1:]):
        if block[later]["signed_on"] < block[earlier]["signed_on"]:
            findings.append(
                "%s signed on %s, before %s signed on %s"
                % (
                    later,
                    block[later]["signed_on"].isoformat(),
                    earlier,
                    block[earlier]["signed_on"].isoformat(),
                )
            )
    issue_date = normalised["issue_date"]
    for role in signed:
        if block[role]["signed_on"] > issue_date:
            findings.append(
                "%s signed on %s, after the cover was issued on %s"
                % (role, block[role]["signed_on"].isoformat(), issue_date.isoformat())
            )
    return findings


def document_count_findings(normalised, index_entries):
    """Return findings where the declared count misses the index length."""
    if not isinstance(index_entries, (list, tuple)):
        raise ValueError("index_entries must be a sequence of index lines")
    listed = []
    for position, entry in enumerate(index_entries):
        listed.append(normalise_identifier(entry, "index_entries[%d]" % position))
    repeated = sorted({name for name in listed if listed.count(name) > 1})
    findings = []
    if repeated:
        findings.append("the index lists twice: %s" % ", ".join(repeated))
    if normalised["document_count"] != len(listed):
        findings.append(
            "the cover declares %d document(s) while the index lists %d"
            % (normalised["document_count"], len(listed))
        )
    return findings


def _render_value(field, value):
    """Return the printed form of one header value."""
    if value is None:
        return "-"
    if field in _DATE_FIELDS:
        return value.isoformat()
    return str(value)


def render_header(normalised):
    """Return the cover header as aligned label and value lines."""
    if not isinstance(normalised, dict):
        raise ValueError("normalised must be the mapping returned by validate_header")
    width = max(len(field) for field in HEADER_FIELDS)
    lines = []
    for field in HEADER_FIELDS:
        label = field.replace("_", " ").upper()
        lines.append(
            "%s : %s" % (label.ljust(width), _render_value(field, normalised.get(field)))
        )
    return tuple(lines)


def assess_eidp_cover(header, approvals, index_entries):
    """Grade a data package cover page against the Annex F header format."""
    normalised = validate_header(header)
    findings = []
    findings.extend(number_findings(normalised))
    findings.extend(approval_chain_findings(normalised, approvals))
    findings.extend(document_count_findings(normalised, index_entries))
    return {
        "eidp_number": normalised["eidp_number"],
        "issue": normalised["issue"],
        "declared_count": normalised["document_count"],
        "indexed_count": len(index_entries),
        "rendered": render_header(normalised),
        "findings": findings,
        "verdict": "cover-conformant" if not findings else "cover-nonconformant",
    }
