"""Configuration status accounting for the software tools that build a device.

Anchor: ECSS-Q-ST-60-03C clause 8.2.3 (recording the configuration status of
the software tools used to produce the device). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each tool status record: a record has to pin the tool, its
   version, its patch or build level, a digest of the option set it was
   driven with, the host platform it ran on, its qualification state and the
   date it was used.
2. Refuse a floating version token. "latest" or "current" names whatever the
   machine had that day, which is the opposite of a status record.
3. Cover the declared build flow: every role the flow uses needs a record,
   and a record for a role the flow never used is a stale entry.
4. Compare the recorded baseline against what actually ran, role by role, so
   version or option drift is reported rather than averaged away.
5. Hold an unqualified tool to its mitigation, and an open tool advisory to
   its named mitigation reference.
6. Score the accounting index and decide reproducibility: a build is
   reproducible only when every used role has a complete, pinned,
   drift-free record.
"""

import math

__all__ = [
    "INDEX_TOLERANCE",
    "TOOL_ROLES",
    "RECORD_FIELDS",
    "QUALIFICATION_STATES",
    "FLOATING_VERSION_TOKENS",
    "normalize_token",
    "normalize_role",
    "normalize_version",
    "is_floating_version",
    "parse_iso_date",
    "validate_record",
    "build_record_index",
    "flow_roles",
    "missing_role_records",
    "stale_role_records",
    "version_drift",
    "unmitigated_conditions",
    "accounting_index",
    "assess_tool_status",
]

# The index is a ratio of exact integer counts compared against a floor a
# caller may express as a decimal; absorb the representation error here.
INDEX_TOLERANCE = 1e-12

TOOL_ROLES = (
    "design-entry",
    "synthesis",
    "place-and-route",
    "simulation",
    "static-timing-analysis",
    "device-programming",
    "verification-coverage",
)

RECORD_FIELDS = (
    "tool_name",
    "version",
    "build_or_patch",
    "option_set_digest",
    "host_platform",
    "qualification_state",
    "used_on",
)

QUALIFICATION_STATES = (
    "qualified",
    "qualified-with-restrictions",
    "unqualified",
)

# Version strings that name whatever was installed rather than a fixed build.
FLOATING_VERSION_TOKENS = (
    "latest",
    "current",
    "head",
    "trunk",
    "dev",
    "nightly",
    "*",
)


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_role(value):
    """Return the canonical tool-role key, or raise for an unknown role."""
    key = normalize_token(value, "tool role")
    if key not in TOOL_ROLES:
        raise ValueError("unknown tool role '%s'" % key)
    return key


def normalize_version(value):
    """Return the trimmed version string, preserving its case, or raise."""
    if not isinstance(value, str):
        raise ValueError("version must be a string, got %r" % (value,))
    text = " ".join(value.split())
    if not text:
        raise ValueError("version must not be empty")
    return text


def is_floating_version(value):
    """Return True when the version names a moving target rather than a build."""
    text = normalize_version(value).lower()
    if text in FLOATING_VERSION_TOKENS:
        return True
    for token in FLOATING_VERSION_TOKENS:
        if token == "*":
            if "*" in text:
                return True
            continue
        if text.endswith("-" + token) or text.startswith(token + "-"):
            return True
    return False


def parse_iso_date(value):
    """Return (year, month, day) from a YYYY-MM-DD string, or raise."""
    if not isinstance(value, str):
        raise ValueError("date must be a string, got %r" % (value,))
    text = value.strip()
    parts = text.split("-")
    if len(parts) != 3:
        raise ValueError("date '%s' is not in YYYY-MM-DD form" % text)
    if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
        raise ValueError("date '%s' is not in YYYY-MM-DD form" % text)
    try:
        year, month, day = (int(p) for p in parts)
    except ValueError:
        raise ValueError("date '%s' has non-numeric fields" % text)
    if not 1 <= month <= 12:
        raise ValueError("date '%s' has an out-of-range month" % text)
    if not 1 <= day <= 31:
        raise ValueError("date '%s' has an out-of-range day" % text)
    return (year, month, day)


def validate_record(entry):
    """Return a normalized tool status record, raising on an unusable one."""
    if not isinstance(entry, dict):
        raise ValueError("tool record must be a mapping, got %r" % (entry,))
    if "role" not in entry:
        raise ValueError("tool record is missing 'role'")
    record = {"role": normalize_role(entry["role"])}
    for field in RECORD_FIELDS:
        if field not in entry:
            raise ValueError(
                "tool record for role '%s' is missing '%s'" % (record["role"], field)
            )
    record["tool_name"] = normalize_token(entry["tool_name"], "tool_name")
    record["version"] = normalize_version(entry["version"])
    record["build_or_patch"] = normalize_token(entry["build_or_patch"], "build_or_patch")
    record["option_set_digest"] = normalize_token(
        entry["option_set_digest"], "option_set_digest"
    )
    record["host_platform"] = normalize_token(entry["host_platform"], "host_platform")
    state = normalize_token(entry["qualification_state"], "qualification_state")
    if state not in QUALIFICATION_STATES:
        raise ValueError("unknown qualification state '%s'" % state)
    record["qualification_state"] = state
    record["used_on"] = parse_iso_date(entry["used_on"])
    record["floating_version"] = is_floating_version(record["version"])
    mitigation = entry.get("mitigation_reference")
    if mitigation is None:
        record["mitigation_reference"] = None
    else:
        record["mitigation_reference"] = normalize_token(
            mitigation, "mitigation_reference"
        )
    return record


def build_record_index(entries):
    """Return {role: record}, raising when one role is recorded twice."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("tool records must be a sequence")
    index = {}
    for entry in entries:
        record = validate_record(entry)
        if record["role"] in index:
            raise ValueError(
                "tool role '%s' has two status records" % record["role"]
            )
        index[record["role"]] = record
    return index


def flow_roles(flow):
    """Return the sorted set of roles the declared build flow actually uses."""
    if not isinstance(flow, (list, tuple)) or not flow:
        raise ValueError("build flow must be a non-empty sequence of roles")
    roles = []
    for item in flow:
        role = normalize_role(item)
        if role not in roles:
            roles.append(role)
    return sorted(roles)


def missing_role_records(used_roles, index):
    """Return the used roles with no status record at all."""
    if not isinstance(index, dict):
        raise ValueError("record index must be a mapping")
    return [role for role in sorted(used_roles) if role not in index]


def stale_role_records(used_roles, index):
    """Return the recorded roles the declared flow never used."""
    if not isinstance(index, dict):
        raise ValueError("record index must be a mapping")
    used = set(used_roles)
    return [role for role in sorted(index) if role not in used]


def version_drift(index, as_run):
    """Return the roles whose as-run tool state differs from the record."""
    if not isinstance(index, dict):
        raise ValueError("record index must be a mapping")
    if as_run is None:
        as_run = {}
    if not isinstance(as_run, dict):
        raise ValueError("as_run must be a mapping of role to observed state")
    drift = []
    for role_key in sorted(as_run):
        role = normalize_role(role_key)
        observed = as_run[role_key]
        if not isinstance(observed, dict):
            raise ValueError("as-run state for '%s' must be a mapping" % role)
        if role not in index:
            continue
        record = index[role]
        for field, normaliser in (
            ("version", normalize_version),
            ("build_or_patch", lambda v: normalize_token(v, "build_or_patch")),
            ("option_set_digest", lambda v: normalize_token(v, "option_set_digest")),
        ):
            if field not in observed:
                continue
            value = normaliser(observed[field])
            if value != record[field]:
                drift.append(
                    {
                        "role": role,
                        "field": field,
                        "recorded": record[field],
                        "as_run": value,
                    }
                )
    return drift


def unmitigated_conditions(index, open_advisories=None):
    """Return the records whose qualification state or advisory lacks a mitigation."""
    if not isinstance(index, dict):
        raise ValueError("record index must be a mapping")
    if open_advisories is None:
        open_advisories = []
    if not isinstance(open_advisories, (list, tuple, set, frozenset)):
        raise ValueError("open_advisories must be a sequence of roles")
    advised = set(normalize_role(role) for role in open_advisories)
    unmitigated = []
    for role in sorted(index):
        record = index[role]
        needs = record["qualification_state"] != "qualified" or role in advised
        if needs and record["mitigation_reference"] is None:
            unmitigated.append(
                {
                    "role": role,
                    "qualification_state": record["qualification_state"],
                    "advisory_open": role in advised,
                }
            )
    return unmitigated


def accounting_index(used_roles, index, drift_roles=None):
    """Return the fraction of used roles carrying a pinned, drift-free record."""
    roles = sorted(set(used_roles))
    if not roles:
        raise ValueError("the build flow uses no roles")
    if not isinstance(index, dict):
        raise ValueError("record index must be a mapping")
    drifted = set(drift_roles or [])
    accounted = 0
    for role in roles:
        record = index.get(role)
        if record is None:
            continue
        if record["floating_version"]:
            continue
        if role in drifted:
            continue
        accounted += 1
    return accounted / float(len(roles))


def assess_tool_status(spec):
    """Run the full clause 8.2.3 tool status accounting assessment.

    spec keys: build_flow (roles), records (status records), optional
    as_run (role -> observed state), open_advisories and required_index
    (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("build_flow", "records"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    required = spec.get("required_index", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_index must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_index must lie in [0, 1], got %g" % required)

    used = flow_roles(spec["build_flow"])
    index = build_record_index(spec["records"])
    missing = missing_role_records(used, index)
    stale = stale_role_records(used, index)
    drift = version_drift(index, spec.get("as_run"))
    floating = [role for role in sorted(index) if index[role]["floating_version"]]
    unmitigated = unmitigated_conditions(index, spec.get("open_advisories"))
    drift_roles = sorted(set(item["role"] for item in drift))
    score = accounting_index(used, index, drift_roles)
    index_ok = score > required or math.isclose(
        score, required, rel_tol=0.0, abs_tol=INDEX_TOLERANCE
    )

    findings = []
    for role in missing:
        findings.append("build-flow role '%s' has no tool status record" % role)
    for role in stale:
        findings.append("status record for role '%s' is not used by the build flow" % role)
    for role in floating:
        findings.append(
            "role '%s' records the floating version '%s' instead of a fixed build"
            % (role, index[role]["version"])
        )
    for item in drift:
        findings.append(
            "role '%s' recorded %s %s but ran %s"
            % (item["role"], item["field"], item["recorded"], item["as_run"])
        )
    for item in unmitigated:
        reason = "an open tool advisory" if item["advisory_open"] else (
            "qualification state '%s'" % item["qualification_state"]
        )
        findings.append(
            "role '%s' carries %s with no mitigation reference" % (item["role"], reason)
        )
    if not index_ok:
        findings.append(
            "status accounting index %.4f is below the required %.4f" % (score, required)
        )
    reproducible = not missing and not floating and not drift and index_ok
    return {
        "used_roles": used,
        "recorded_roles": sorted(index),
        "missing_records": missing,
        "stale_records": stale,
        "floating_versions": floating,
        "drift": drift,
        "unmitigated": unmitigated,
        "accounting_index": score,
        "required_index": required,
        "index_ok": index_ok,
        "build_reproducible": reproducible,
        "findings": findings,
    }
