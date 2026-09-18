"""Recording outgassing screening results into a materials data set.

Anchor: ECSS-Q-ST-70-02C, the data-recording clause of the thermal-vacuum
outgassing screening test, feeding the materials selection and data-list
practice of the ECSS-Q-ST-70 family (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A data-set entry is identified by what was tested, not by what it is
   called. Designation, manufacturer, product form and processing state
   together form the key; two cure schedules of one adhesive are two
   entries, because they outgas differently.
2. Values go in at the resolution the data set is written at. Carrying
   the raw quotient forward makes two records of the same material
   compare unequal over digits neither report ever published.
3. Every entry cites the report it came from, and an entry whose source
   report was not reportable is not recorded at all. A data set is a
   pointer to evidence; an entry with no usable evidence behind it is
   worse than a gap, because a gap gets tested.
4. Meeting an existing entry for the same key is the interesting case.
   Identical values from the same report is a duplicate submission;
   identical values from a different report confirm the entry; new
   values from a later report supersede; new values from an earlier
   report are stale and do not overwrite; different values from the same
   date are a conflict a person has to resolve.

Stdlib only, offline, deterministic.
"""

import datetime

KEY_FIELDS = (
    "material_designation",
    "manufacturer",
    "product_form",
    "processing_state",
)

VALUE_FIELDS = (
    "total_mass_loss_pct",
    "cvcm_pct",
)

OPTIONAL_VALUE_FIELDS = ("recovered_mass_loss_pct",)

# Resolution the data set records screening values at.
ENTRY_DECIMALS = 2

# Values are quotients scaled by 100, so an equality between a recorded
# value and a freshly computed one can miss by a few units in the last
# place. This tolerance absorbs that representation error only.
VALUE_TOLERANCE = 1.0e-12

NEW_ENTRY = "new-entry"
DUPLICATE_ENTRY = "duplicate-entry"
CONFIRMED = "confirmed-by-an-independent-report"
SUPERSEDES = "supersedes-the-recorded-entry"
STALE = "stale-entry-not-recorded"
CONFLICT = "conflicting-entry-needs-resolution"


def _numeric(label, value, minimum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return float(value)


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def normalize_value(value):
    """Round a screening value to the resolution the data set records."""
    return round(_numeric("value", value), ENTRY_DECIMALS)


def parse_test_date(value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text("test_date", value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("test_date %r is not an ISO calendar date" % (value,))


def data_set_key(entry):
    """Identity of a data-set entry: what was tested, not what it is called."""
    if not isinstance(entry, dict):
        raise ValueError("entry must be a mapping")
    parts = []
    for field in KEY_FIELDS:
        parts.append(_text(field, entry.get(field)).lower())
    return tuple(parts)


def validate_entry(entry):
    """Validate one candidate data-set entry and return a normalized copy."""
    key = data_set_key(entry)
    report_reference = _text("test_report_reference", entry.get("test_report_reference"))
    reportable = entry.get("report_reportable", True)
    if not isinstance(reportable, bool):
        raise ValueError("report_reportable must be a boolean")
    test_date = parse_test_date(entry.get("test_date"))

    values = {}
    for field in VALUE_FIELDS:
        values[field] = normalize_value(
            _numeric(field, entry.get(field), 0.0)
        )
    for field in OPTIONAL_VALUE_FIELDS:
        raw = entry.get(field)
        values[field] = None if raw is None else normalize_value(
            _numeric(field, raw, 0.0)
        )

    if values["cvcm_pct"] > values["total_mass_loss_pct"] + VALUE_TOLERANCE:
        raise ValueError(
            "entry %s condensed %r percent from a total loss of %r percent"
            % (report_reference, values["cvcm_pct"], values["total_mass_loss_pct"])
        )
    recovered = values["recovered_mass_loss_pct"]
    if recovered is not None and recovered > values[
        "total_mass_loss_pct"
    ] + VALUE_TOLERANCE:
        raise ValueError(
            "entry %s recovered loss %r exceeds its total loss %r"
            % (report_reference, recovered, values["total_mass_loss_pct"])
        )

    normalized = {
        "key": key,
        "test_report_reference": report_reference,
        "report_reportable": reportable,
        "test_date": test_date,
    }
    for field in KEY_FIELDS:
        normalized[field] = _text(field, entry.get(field))
    normalized.update(values)
    return normalized


def values_match(left, right):
    """True when two normalized entries carry the same recorded values."""
    for field in VALUE_FIELDS + OPTIONAL_VALUE_FIELDS:
        a = left.get(field)
        b = right.get(field)
        if a is None or b is None:
            if a is not b:
                return False
            continue
        if abs(a - b) > VALUE_TOLERANCE:
            return False
    return True


def reconcile(recorded, candidate):
    """Decide what a candidate entry does to an entry already recorded."""
    if recorded is None:
        return NEW_ENTRY
    if data_set_key(recorded) != data_set_key(candidate):
        raise ValueError("reconcile compares entries under one data-set key")
    left = validate_entry(recorded)
    right = validate_entry(candidate)
    if values_match(left, right):
        if left["test_report_reference"] == right["test_report_reference"]:
            return DUPLICATE_ENTRY
        return CONFIRMED
    if right["test_date"] > left["test_date"]:
        return SUPERSEDES
    if right["test_date"] < left["test_date"]:
        return STALE
    return CONFLICT


def record_entries(entries, recorded=None):
    """Fold a list of candidate entries into a materials data set."""
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    if recorded is None:
        recorded = {}
    if not isinstance(recorded, dict):
        raise ValueError("recorded must be a mapping keyed by data-set key")

    data_set = {}
    for key, value in recorded.items():
        data_set[key] = validate_entry(value)

    actions = []
    findings = []
    for entry in entries:
        candidate = validate_entry(entry)
        key = candidate["key"]
        if not candidate["report_reportable"]:
            actions.append(
                {
                    "key": key,
                    "action": "not-recorded",
                    "reason": "source-report-not-reportable",
                }
            )
            findings.append("entry-offered-from-a-report-that-is-not-reportable")
            continue
        existing = data_set.get(key)
        action = reconcile(existing, candidate) if existing else NEW_ENTRY
        if action in (NEW_ENTRY, SUPERSEDES):
            data_set[key] = candidate
        if action == CONFLICT:
            findings.append("same-key-entries-disagree-on-the-same-date")
        if action == STALE:
            findings.append("earlier-report-offered-against-a-newer-entry")
        actions.append({"key": key, "action": action, "reason": None})

    return {
        "data_set": data_set,
        "actions": actions,
        "findings": findings,
        "recorded_keys": sorted(data_set),
        "clean": not findings,
    }
