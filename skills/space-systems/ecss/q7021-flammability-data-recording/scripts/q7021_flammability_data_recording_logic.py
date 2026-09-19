"""Recording upward flame propagation results into a materials data set.

Anchor: ECSS-Q-ST-70-21C, the data clause of the flammability screening
test, feeding the declared-materials and materials-selection practice of
ECSS-Q-ST-70-71C and ECSS-Q-ST-70C (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A flammability entry is identified by what was tested AND by the
   atmosphere it was tested in. Designation, manufacturer, product form
   and processing state name the material; thickness band and the
   oxygen partial pressure of the test atmosphere name the condition.
   The same laminate at 0.5 mm in air and at 2.0 mm in an enriched
   atmosphere are two entries, because one result says nothing about
   the other.
2. The recorded rating comes from the specimen set, not from one
   specimen. A run needs a minimum specimen count; the worst specimen
   governs; a specimen that burned past the observation limit or never
   self-extinguished makes the whole run propagating.
3. Dripping that ignites the indicator below the specimen does not make
   the material propagating, but it does restrict where the entry may
   be used, so the restriction travels with the entry into the declared
   list rather than being remembered by whoever ran the test.
4. An entry whose run was not reportable is not recorded at all.
5. Coverage runs one way. A test atmosphere at least as severe as the
   use atmosphere covers it; a milder test is not evidence, however
   convenient the number looks.

Stdlib only, offline, deterministic.
"""

import datetime

KEY_FIELDS = (
    "material_designation",
    "manufacturer",
    "product_form",
    "processing_state",
)

# Resolution the data set records geometry and atmosphere at.
THICKNESS_DECIMALS = 2
PRESSURE_DECIMALS = 2

# A screening run below this specimen count is not a run.
MIN_SPECIMENS = 3

# Observation limit on the specimen: burning past it is propagation.
BURN_LENGTH_LIMIT_MM = 150.0

# Atmospheres are quotients of measured quantities, so an equality can
# miss by a few units in the last place. This absorbs representation
# error only.
TOLERANCE = 1.0e-9

NOT_PROPAGATING = "not-propagating"
NOT_PROPAGATING_RESTRICTED = "not-propagating-with-drip-restriction"
PROPAGATING = "propagating"

NEW_ENTRY = "new-entry"
DUPLICATE_ENTRY = "duplicate-entry"
CONFIRMED = "confirmed-by-an-independent-run"
SUPERSEDES = "supersedes-the-recorded-entry"
STALE = "stale-entry-not-recorded"
CONFLICT = "conflicting-entry-needs-resolution"

COVERED = "test-atmosphere-covers-the-use-atmosphere"
NOT_COVERED = "test-atmosphere-milder-than-use-atmosphere"


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return " ".join(value.split())


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean" % label)
    return value


def parse_test_date(value):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    text = _text("test_date", value)
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        raise ValueError("test_date %r is not an ISO calendar date" % (value,))


def oxygen_partial_pressure(oxygen_volume_pct, total_pressure_kpa):
    """Oxygen partial pressure of a test or use atmosphere, in kPa."""
    fraction = _numeric("oxygen_volume_pct", oxygen_volume_pct, 0.0, 100.0)
    total = _numeric("total_pressure_kpa", total_pressure_kpa, 0.0)
    if total <= 0.0:
        raise ValueError("total_pressure_kpa must be greater than zero")
    return round(fraction * total / 100.0, PRESSURE_DECIMALS)


def atmosphere_key(oxygen_volume_pct, total_pressure_kpa):
    """Identity of the atmosphere a run was performed in."""
    return (
        oxygen_partial_pressure(oxygen_volume_pct, total_pressure_kpa),
        round(_numeric("total_pressure_kpa", total_pressure_kpa, 0.0), PRESSURE_DECIMALS),
    )


def thickness_band(thickness_mm):
    """Recorded thickness, rounded to the resolution of the data set."""
    value = _numeric("thickness_mm", thickness_mm, 0.0)
    if value <= 0.0:
        raise ValueError("thickness_mm must be greater than zero")
    return round(value, THICKNESS_DECIMALS)


def data_set_key(record):
    """Identity of a flammability entry: material, geometry, atmosphere."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    parts = [_text(f, record.get(f)).lower() for f in KEY_FIELDS]
    parts.append(thickness_band(record.get("thickness_mm")))
    parts.extend(
        atmosphere_key(
            record.get("oxygen_volume_pct"), record.get("total_pressure_kpa")
        )
    )
    return tuple(parts)


def validate_specimen(specimen):
    """Validate one observed specimen and return a normalized copy."""
    if not isinstance(specimen, dict):
        raise ValueError("specimen must be a mapping")
    burn = _numeric("burn_length_mm", specimen.get("burn_length_mm"), 0.0)
    return {
        "burn_length_mm": burn,
        "self_extinguished": _flag(
            "self_extinguished", specimen.get("self_extinguished")
        ),
        "drip_ignited_indicator": _flag(
            "drip_ignited_indicator", specimen.get("drip_ignited_indicator", False)
        ),
    }


def rate_run(specimens):
    """Categorize a specimen set into the rating the data set records."""
    if not isinstance(specimens, list):
        raise ValueError("specimens must be a list")
    if len(specimens) < MIN_SPECIMENS:
        raise ValueError(
            "a run needs at least %d specimens, got %d"
            % (MIN_SPECIMENS, len(specimens))
        )
    observed = [validate_specimen(s) for s in specimens]
    worst_burn = max(s["burn_length_mm"] for s in observed)
    dripped = any(s["drip_ignited_indicator"] for s in observed)
    if any(not s["self_extinguished"] for s in observed):
        rating = PROPAGATING
    elif worst_burn > BURN_LENGTH_LIMIT_MM + TOLERANCE:
        rating = PROPAGATING
    elif dripped:
        rating = NOT_PROPAGATING_RESTRICTED
    else:
        rating = NOT_PROPAGATING
    return {
        "rating": rating,
        "worst_burn_length_mm": worst_burn,
        "specimen_count": len(observed),
        "drip_ignited_indicator": dripped,
    }


def validate_record(record):
    """Validate one candidate flammability entry and normalize it."""
    key = data_set_key(record)
    report_reference = _text(
        "test_report_reference", record.get("test_report_reference")
    )
    reportable = _flag("report_reportable", record.get("report_reportable", True))
    test_date = parse_test_date(record.get("test_date"))
    outcome = rate_run(record.get("specimens"))

    normalized = {
        "key": key,
        "test_report_reference": report_reference,
        "report_reportable": reportable,
        "test_date": test_date,
        "thickness_mm": thickness_band(record.get("thickness_mm")),
        "oxygen_partial_pressure_kpa": oxygen_partial_pressure(
            record.get("oxygen_volume_pct"), record.get("total_pressure_kpa")
        ),
        "total_pressure_kpa": round(
            _numeric("total_pressure_kpa", record.get("total_pressure_kpa"), 0.0),
            PRESSURE_DECIMALS,
        ),
    }
    for field in KEY_FIELDS:
        normalized[field] = _text(field, record.get(field))
    normalized.update(outcome)
    return normalized


def covers_use_atmosphere(entry, use_oxygen_volume_pct, use_total_pressure_kpa):
    """Does the tested atmosphere bound the atmosphere of intended use?"""
    tested = entry["oxygen_partial_pressure_kpa"]
    wanted = oxygen_partial_pressure(use_oxygen_volume_pct, use_total_pressure_kpa)
    if tested + TOLERANCE >= wanted:
        return {"verdict": COVERED, "tested_kpa": tested, "use_kpa": wanted}
    return {"verdict": NOT_COVERED, "tested_kpa": tested, "use_kpa": wanted}


def declared_list_link(entry):
    """The cross-reference this entry contributes to the declared list."""
    restriction = None
    if entry["rating"] == NOT_PROPAGATING_RESTRICTED:
        restriction = "no-ignitable-item-below-the-installed-material"
    elif entry["rating"] == PROPAGATING:
        restriction = "use-requires-an-accepted-justification"
    return {
        "key": entry["key"],
        "material_designation": entry["material_designation"],
        "rating": entry["rating"],
        "tested_oxygen_partial_pressure_kpa": entry["oxygen_partial_pressure_kpa"],
        "thickness_mm": entry["thickness_mm"],
        "source_report": entry["test_report_reference"],
        "restriction": restriction,
    }


def as_entry(record):
    """Accept either a raw candidate or an already-normalized entry."""
    if isinstance(record, dict) and "key" in record and "rating" in record:
        return record
    return validate_record(record)


def reconcile(recorded, candidate):
    """Decide what a candidate entry does to an entry already recorded."""
    if recorded is None:
        return NEW_ENTRY
    left = as_entry(recorded)
    right = as_entry(candidate)
    if left["key"] != right["key"]:
        raise ValueError("reconcile compares entries under one data-set key")
    same_rating = left["rating"] == right["rating"]
    same_burn = abs(left["worst_burn_length_mm"] - right["worst_burn_length_mm"]) <= (
        TOLERANCE
    )
    if same_rating and same_burn:
        if left["test_report_reference"] == right["test_report_reference"]:
            return DUPLICATE_ENTRY
        return CONFIRMED
    if right["test_date"] > left["test_date"]:
        return SUPERSEDES
    if right["test_date"] < left["test_date"]:
        return STALE
    return CONFLICT


def record_results(records, recorded=None):
    """Fold candidate flammability results into a materials data set."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    if recorded is None:
        recorded = {}
    if not isinstance(recorded, dict):
        raise ValueError("recorded must be a mapping keyed by data-set key")

    data_set = {}
    for key, value in recorded.items():
        data_set[key] = as_entry(value)

    actions = []
    findings = []
    for record in records:
        candidate = validate_record(record)
        key = candidate["key"]
        if not candidate["report_reportable"]:
            actions.append(
                {
                    "key": key,
                    "action": "not-recorded",
                    "reason": "source-run-not-reportable",
                }
            )
            findings.append("entry-offered-from-a-run-that-is-not-reportable")
            continue
        existing = data_set.get(key)
        action = reconcile(existing, candidate) if existing else NEW_ENTRY
        if action in (NEW_ENTRY, SUPERSEDES):
            data_set[key] = candidate
        if action == CONFLICT:
            findings.append("same-key-runs-disagree-on-the-same-date")
        if action == STALE:
            findings.append("earlier-run-offered-against-a-newer-entry")
        actions.append({"key": key, "action": action, "reason": None})

    links = [declared_list_link(e) for _, e in sorted(data_set.items())]
    return {
        "data_set": data_set,
        "actions": actions,
        "findings": findings,
        "declared_list_links": links,
        "recorded_keys": sorted(data_set),
        "clean": not findings,
    }
