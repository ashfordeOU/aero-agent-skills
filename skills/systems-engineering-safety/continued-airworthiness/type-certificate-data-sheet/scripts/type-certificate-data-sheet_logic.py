"""type_certificate_data_sheet_logic.py - TCDS style type design record logic (pure stdlib).

Compile and validate a type-certificate-data-sheet style type design record
for a civil product: check that every required section is present, validate
the weight block consistency, validate the category airspeed limitations,
check the approved configuration consistency, and diff two revisions of the
record into a per-section change summary for type certificate amendment or
STC integration review.

Conventions
-----------
A record is a dict with a "category" key plus the REQUIRED_SECTIONS keys.
weights is a dict with max_ramp, max_takeoff and max_landing values.
operating_limitations is a dict of named limits; it may carry an optional
"engines" key holding a list of engine model references (the approved
configuration check verifies each reference appears in engine_models).
models, engine_models and propeller_models are lists.

Checks split by concern: missing_sections reports section ABSENCE (key not
in the record), while weight_errors, airspeed_errors and
approved_config_errors report CONTENT defects inside sections that exist.
A record without a category key, a weights section that is not a dict, or
an operating_limitations section that is not a dict raises ValueError.

The module is deterministic: no randomness, no network, stdlib only.
"""

REQUIRED_SECTIONS = (
    "models",
    "type_design",
    "engine_models",
    "propeller_models",
    "weights",
    "certification_basis",
    "operating_limitations",
    "noise_standards",
)
"""Sections a complete TCDS style type design record must carry."""

CATEGORY_AIRSPEED_KEYS = {
    "transport": ("vmo", "mmo"),
    "normal": ("vne",),
    "utility": ("vne",),
    "acrobatic": ("vne",),
}
"""Airspeed limitation keys that satisfy each category rule. Any one listed
key present and positive satisfies the category."""

AIRSPEED_LIMIT_KEYS = tuple(
    sorted({key for keys in CATEGORY_AIRSPEED_KEYS.values() for key in keys})
)
"""All airspeed limit keys recognised anywhere (mmo, vmo, vne); used to pick
the airspeed entries out of operating_limitations for the summary."""

WEIGHT_KEYS = ("max_ramp", "max_takeoff", "max_landing")
"""Weight block keys of the TCDS weights section."""

ENGINE_REF_KEY = "engines"
"""Optional operating_limitations key carrying approved engine model
references for the approved configuration check."""


def _require_record(record):
    """Raise ValueError when record is not a dict."""
    if not isinstance(record, dict):
        raise ValueError("record must be a dict, got %s" % type(record).__name__)


def _require_category(record):
    """Return the category, raising ValueError when the key is absent."""
    _require_record(record)
    if "category" not in record:
        raise ValueError("record has no category key")
    return record["category"]


def _as_float(value, name):
    """Return value as float, raising ValueError for non-numeric input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    return float(value)


def _fmt_number(value):
    """Short stable decimal rendering of a limit value, e.g. 340 or 0.84."""
    return "%g" % _as_float(value, "value")


def _operating_limits(record):
    """Return the operating_limitations dict, {} when absent."""
    if "operating_limitations" not in record or record["operating_limitations"] is None:
        return {}
    limits = record["operating_limitations"]
    if not isinstance(limits, dict):
        raise ValueError("operating_limitations section must be a dict")
    return limits


def missing_sections(record):
    """List of REQUIRED_SECTIONS keys absent from the record, in order."""
    _require_record(record)
    return [key for key in REQUIRED_SECTIONS if key not in record]


def weight_errors(record):
    """Content errors of the weights section.

    Checks empty or missing weight keys, non-positive weights, max_ramp
    below max_takeoff and max_landing above max_takeoff. A record with no
    weights section at all returns [] (section absence is reported by
    missing_sections). Raises ValueError when the weights section exists
    but is not a dict, or a weight value is not numeric.
    """
    _require_record(record)
    if "weights" not in record or record["weights"] is None:
        return []
    weights = record["weights"]
    if not isinstance(weights, dict):
        raise ValueError("weights section must be a dict")
    errors = []
    for key in WEIGHT_KEYS:
        if key not in weights or weights[key] is None:
            errors.append("missing weight key %s" % key)
    for key in WEIGHT_KEYS:
        if key in weights and weights[key] is not None:
            if _as_float(weights[key], key) <= 0.0:
                errors.append("%s not positive" % key)
    present = {key for key in WEIGHT_KEYS if key in weights and weights[key] is not None}
    if {"max_ramp", "max_takeoff"} <= present:
        ramp = _as_float(weights["max_ramp"], "max_ramp")
        takeoff = _as_float(weights["max_takeoff"], "max_takeoff")
        if ramp < takeoff:
            errors.append("max_ramp below max_takeoff")
    if {"max_takeoff", "max_landing"} <= present:
        takeoff = _as_float(weights["max_takeoff"], "max_takeoff")
        landing = _as_float(weights["max_landing"], "max_landing")
        if landing > takeoff:
            errors.append("max_landing above max_takeoff")
    return errors


def airspeed_errors(record):
    """Airspeed limitation errors for the record category.

    The category rule needs any one listed key present and positive. Raises
    ValueError when the category key is absent or operating_limitations is
    not a dict.
    """
    category = _require_category(record)
    limits = _operating_limits(record)
    if category not in CATEGORY_AIRSPEED_KEYS:
        return ["unknown category %s" % category]
    needed = CATEGORY_AIRSPEED_KEYS[category]
    present = [key for key in needed if key in limits and limits[key] is not None]
    positive = [key for key in present if _as_float(limits[key], key) > 0.0]
    if positive:
        return []
    if not present:
        return ["missing %s for category %s" % (" or ".join(needed), category)]
    return ["%s not positive for category %s" % (" or ".join(present), category)]


def approved_config_errors(record):
    """Approved configuration consistency errors.

    Flags an empty engine_models or propeller_models list (a TCDS lists the
    approved engine and propeller models) and engine references under the
    operating_limitations "engines" key that are not in engine_models.
    Absent model list sections are left to missing_sections; the reference
    check runs only when engine_models is a non-empty list.
    """
    _require_record(record)
    errors = []
    for section, message in (
        ("engine_models", "no approved engine models listed"),
        ("propeller_models", "no approved propeller models listed"),
    ):
        if section not in record or record[section] is None:
            continue
        models = record[section]
        if not isinstance(models, list):
            raise ValueError("%s section must be a list" % section)
        if not models:
            errors.append(message)
    limits = _operating_limits(record)
    if not limits:
        return errors
    refs = limits.get(ENGINE_REF_KEY)
    if refs is None:
        return errors
    if not isinstance(refs, list):
        raise ValueError("operating_limitations %s must be a list" % ENGINE_REF_KEY)
    approved = record.get("engine_models")
    if not isinstance(approved, list) or not approved:
        return errors
    for ref in refs:
        if ref not in approved:
            errors.append(
                "engine reference %s not in approved engine models" % ref
            )
    return errors


def validate_tcds(record):
    """Full validation of a type design record.

    Returns {missing_sections, weight_errors, airspeed_errors,
    config_errors, valid} with valid True exactly when all four error lists
    are empty. Raises ValueError for a record without a category key or a
    weights section that is not a dict.
    """
    _require_category(record)
    missing = missing_sections(record)
    weight_errs = weight_errors(record)
    airspeed_errs = airspeed_errors(record)
    config_errs = approved_config_errors(record)
    return {
        "missing_sections": missing,
        "weight_errors": weight_errs,
        "airspeed_errors": airspeed_errs,
        "config_errors": config_errs,
        "valid": not (missing or weight_errs or airspeed_errs or config_errs),
    }


def tcds_summary(record):
    """Summary counts and headline values of a type design record.

    Returns {models, engine_models, propeller_models, max_takeoff_weight,
    airspeed_limits} where the counts are list lengths, max_takeoff_weight
    is the float max takeoff weight, and airspeed_limits is the sorted
    list of "key=value" strings for the airspeed entries found in
    operating_limitations. Raises ValueError when a model list section is
    not a list, weights lacks max_takeoff, or an airspeed value is not
    numeric.
    """
    _require_record(record)
    counts = {}
    for section in ("models", "engine_models", "propeller_models"):
        value = record.get(section)
        if value is None:
            counts[section] = 0
        elif not isinstance(value, list):
            raise ValueError("%s section must be a list" % section)
        else:
            counts[section] = len(value)
    if "weights" not in record or not isinstance(record["weights"], dict):
        raise ValueError("weights section must be a dict for a summary")
    weights = record["weights"]
    if "max_takeoff" not in weights or weights["max_takeoff"] is None:
        raise ValueError("weights section missing max_takeoff for a summary")
    limits = _operating_limits(record)
    airspeed_limits = sorted(
        "%s=%s" % (key, _fmt_number(limits[key]))
        for key in AIRSPEED_LIMIT_KEYS
        if key in limits and limits[key] is not None
    )
    return {
        "models": counts["models"],
        "engine_models": counts["engine_models"],
        "propeller_models": counts["propeller_models"],
        "max_takeoff_weight": _as_float(weights["max_takeoff"], "max_takeoff"),
        "airspeed_limits": airspeed_limits,
    }


def tcds_revision_diff(old, new):
    """Per-section change summary between two revisions of a record.

    Returns {sections, models_added, models_removed, weight_deltas} where
    sections maps each REQUIRED_SECTIONS key present in either revision to
    "unchanged", "added", "removed" or "modified", models_added and
    models_removed carry the per-model change of the models section, and
    weight_deltas carries "<key>_delta" float entries for weight keys that
    changed between the two revisions. Sections absent from both revisions
    are omitted. Raises ValueError for a non-dict record, a models section
    that is not a list, or a weights section that is not a dict.
    """
    _require_record(old)
    _require_record(new)
    sections = {}
    for key in REQUIRED_SECTIONS:
        in_old = key in old
        in_new = key in new
        if not in_old and not in_new:
            continue
        if in_old and not in_new:
            sections[key] = "removed"
        elif in_new and not in_old:
            sections[key] = "added"
        elif old[key] == new[key]:
            sections[key] = "unchanged"
        else:
            sections[key] = "modified"
    models_added = []
    models_removed = []
    if "models" in old and "models" in new:
        old_models = old["models"]
        new_models = new["models"]
        if not isinstance(old_models, list) or not isinstance(new_models, list):
            raise ValueError("models section must be a list")
        models_added = [model for model in new_models if model not in old_models]
        models_removed = [model for model in old_models if model not in new_models]
    weight_deltas = {}
    if "weights" in old and "weights" in new:
        old_weights = old["weights"]
        new_weights = new["weights"]
        if not isinstance(old_weights, dict) or not isinstance(new_weights, dict):
            raise ValueError("weights section must be a dict")
        for key in WEIGHT_KEYS:
            if key in old_weights and key in new_weights:
                delta = _as_float(new_weights[key], key) - _as_float(
                    old_weights[key], key
                )
                if delta != 0.0:
                    weight_deltas["%s_delta" % key] = delta
    return {
        "sections": sections,
        "models_added": models_added,
        "models_removed": models_removed,
        "weight_deltas": weight_deltas,
    }
