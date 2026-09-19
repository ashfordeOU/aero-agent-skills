#!/usr/bin/env python3
"""Updated verification and validation plans (ECSS-E-ST-20-40C clause 5.3.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
Once the device architecture is settled, the verification and validation
plans written against the earlier, blockless picture stop being true. The
clause asks for them to be refreshed, and refreshed is a claim that can
be checked rather than a status anyone may set.

* the plan cites the architecture revision it was written against. A
  plan citing a revision the architecture has moved past is stale on
  its face, whatever its own revision says;
* a plan whose own revision did not move while the architecture did was
  not updated, only re-dated. This is the single most common way the
  clause is reported closed without the work;
* every current requirement needs an entry in the updated plan, and
  every entry needs a requirement that still exists. Both directions
  matter: a dropped requirement leaves an orphan entry, a new one
  leaves a hole;
* an entry naming a block the architecture retired is pointing at
  nothing. An entry whose requirement was REALLOCATED to another block
  but whose own block field never changed is worse, because it still
  names a block that exists and is simply the wrong one;
* validation is a separate plan from verification and both are owed.
  Refreshing one and reporting the pair is how the validation plan ends
  up a phase behind.

The refresh ratio is entries touched over entries owed, so a target met
exactly is met and the comparison absorbs representation error.
"""

import math

PLAN_KINDS = ("verification", "validation")

_KIND_ALIASES = {
    "verification": "verification",
    "verif": "verification",
    "v": "verification",
    "validation": "validation",
    "valid": "validation",
}

REL_TOL = 1e-12
ABS_TOL = 1e-18

_CASE_REQUIRED_KEYS = ("architecture", "plans")
_CASE_OPTIONAL_KEYS = ("refresh_target",)
_ARCH_KEYS = ("revision", "blocks", "requirements", "reallocations")
_PLAN_KEYS = ("kind", "revision", "baseline_revision", "architecture_revision", "entries")
_ENTRY_KEYS = ("requirement", "block", "method", "level", "touched")


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not 0.0 <= out <= 1.0:
        raise ValueError("%s must lie in [0, 1], got %g" % (name, out))
    return out


def _identifier_set(name, values):
    if not isinstance(values, (list, tuple, set)):
        raise ValueError("%s must be a list of identifiers" % name)
    resolved = []
    for index, value in enumerate(sorted(values) if isinstance(values, set) else values):
        item = _text("%s[%d]" % (name, index), value)
        if item in resolved:
            raise ValueError("duplicate identifier %r in %s" % (item, name))
        resolved.append(item)
    return resolved


def normalize_plan_kind(value):
    """Fold a plan kind onto verification or validation."""
    key = _key("plan kind", value)
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    raise ValueError(
        "unknown plan kind %r; use one of %s" % (value, ", ".join(PLAN_KINDS))
    )


def revision_ordinal(value):
    """Order a dotted revision so two revisions can be compared."""
    text = _text("revision", value)
    parts = text.replace("-", ".").split(".")
    ordinal = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            raise ValueError("revision %r has an empty component" % value)
        if chunk.isdigit():
            ordinal.append((1, int(chunk), ""))
        else:
            ordinal.append((0, 0, chunk.lower()))
    return tuple(ordinal)


def revision_is_newer(candidate, reference):
    """True when the candidate revision sits after the reference one."""
    return revision_ordinal(candidate) > revision_ordinal(reference)


def validate_architecture(architecture):
    """Check the settled architecture and return its revision and sets."""
    if not isinstance(architecture, dict):
        raise ValueError("architecture must be a mapping")
    unknown = sorted(set(architecture) - set(_ARCH_KEYS))
    if unknown:
        raise ValueError("architecture has unknown keys: %s" % ", ".join(unknown))
    for key in ("revision", "blocks", "requirements"):
        if key not in architecture:
            raise ValueError("architecture missing key: %s" % key)
    reallocations = architecture.get("reallocations", {}) or {}
    if not isinstance(reallocations, dict):
        raise ValueError("architecture.reallocations must be a mapping")
    blocks = _identifier_set("architecture.blocks", architecture["blocks"])
    requirements = _identifier_set("architecture.requirements", architecture["requirements"])
    resolved_moves = {}
    for requirement, block in sorted(reallocations.items()):
        req = _text("reallocations key", requirement)
        target = _text("reallocations[%s]" % req, block)
        if req not in requirements:
            raise ValueError("reallocated requirement %r is not in the requirement set" % req)
        if target not in blocks:
            raise ValueError("requirement %r is reallocated to unknown block %r" % (req, target))
        resolved_moves[req] = target
    return {
        "revision": _text("architecture.revision", architecture["revision"]),
        "blocks": blocks,
        "requirements": requirements,
        "reallocations": resolved_moves,
    }


def validate_plan(plan, where="plan"):
    """Check one plan and return it resolved, entries keyed by requirement."""
    if not isinstance(plan, dict):
        raise ValueError("%s must be a mapping" % where)
    unknown = sorted(set(plan) - set(_PLAN_KEYS))
    if unknown:
        raise ValueError("%s has unknown keys: %s" % (where, ", ".join(unknown)))
    for key in ("kind", "revision", "architecture_revision", "entries"):
        if key not in plan:
            raise ValueError("%s missing key: %s" % (where, key))
    entries = plan["entries"]
    if not isinstance(entries, (list, tuple)):
        raise ValueError("%s.entries must be a list" % where)
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("%s.entries[%d] must be a mapping" % (where, index))
        stray = sorted(set(entry) - set(_ENTRY_KEYS))
        if stray:
            raise ValueError(
                "%s.entries[%d] has unknown keys: %s" % (where, index, ", ".join(stray))
            )
        if "requirement" not in entry:
            raise ValueError("%s.entries[%d] missing key: requirement" % (where, index))
        requirement = _text("%s.entries[%d].requirement" % (where, index), entry["requirement"])
        if requirement in resolved:
            raise ValueError("%s carries requirement %r twice" % (where, requirement))
        touched = entry.get("touched", False)
        if not isinstance(touched, bool):
            raise ValueError("%s.entries[%d].touched must be true or false" % (where, index))
        resolved[requirement] = {
            "requirement": requirement,
            "block": _text(
                "%s.entries[%d].block" % (where, index), entry.get("block", ""), allow_empty=True
            ),
            "method": _text(
                "%s.entries[%d].method" % (where, index), entry.get("method", ""), allow_empty=True
            ),
            "level": _text(
                "%s.entries[%d].level" % (where, index), entry.get("level", ""), allow_empty=True
            ),
            "touched": touched,
        }
    return {
        "kind": normalize_plan_kind(plan["kind"]),
        "revision": _text("%s.revision" % where, plan["revision"]),
        "baseline_revision": _text(
            "%s.baseline_revision" % where, plan.get("baseline_revision", ""), allow_empty=True
        ),
        "architecture_revision": _text(
            "%s.architecture_revision" % where, plan["architecture_revision"]
        ),
        "entries": resolved,
    }


def refresh_ratio(plan):
    """Fraction of a plan's entries marked as touched by the update."""
    entries = plan["entries"]
    if not entries:
        raise ValueError("refresh_ratio needs at least one entry")
    touched = sum(1 for e in entries.values() if e["touched"])
    return touched / len(entries)


def meets_refresh_target(achieved, target):
    """True when the refresh reaches the target, exact landings included."""
    achieved = _fraction("achieved", achieved)
    target = _fraction("target", target)
    return achieved > target or math.isclose(
        achieved, target, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def plan_delta(baseline_entries, updated_entries):
    """Requirements added, removed and changed between two entry sets."""
    if not isinstance(baseline_entries, dict) or not isinstance(updated_entries, dict):
        raise ValueError("plan_delta needs two entry mappings")
    added = sorted(set(updated_entries) - set(baseline_entries))
    removed = sorted(set(baseline_entries) - set(updated_entries))
    changed = sorted(
        requirement
        for requirement in set(baseline_entries) & set(updated_entries)
        if any(
            baseline_entries[requirement].get(field) != updated_entries[requirement].get(field)
            for field in ("block", "method", "level")
        )
    )
    return {"added": added, "removed": removed, "changed": changed}


def assess_updated_plans(case):
    """Full clause 5.3.3 assessment of the refreshed plan pair.

    Returns each plan's refresh ratio and delta, the findings and whether
    the pair is genuinely current with the settled architecture.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping of architecture and plans")
    known = set(_CASE_REQUIRED_KEYS) | set(_CASE_OPTIONAL_KEYS)
    unknown = sorted(set(case) - known)
    if unknown:
        raise ValueError("unknown case keys: %s" % ", ".join(unknown))
    missing = [key for key in _CASE_REQUIRED_KEYS if key not in case]
    if missing:
        raise ValueError("case missing required keys: %s" % ", ".join(missing))

    architecture = validate_architecture(case["architecture"])
    plans_in = case["plans"]
    if not isinstance(plans_in, (list, tuple)):
        raise ValueError("plans must be a list")
    plans = {}
    for index, plan in enumerate(plans_in):
        resolved = validate_plan(plan, "plans[%d]" % index)
        if resolved["kind"] in plans:
            raise ValueError("two %s plans were supplied" % resolved["kind"])
        plans[resolved["kind"]] = resolved

    findings = []
    summaries = {}

    for kind in PLAN_KINDS:
        if kind not in plans:
            findings.append(
                {
                    "code": "plan-not-supplied",
                    "plan": kind,
                    "detail": "the %s plan is owed at this clause and was not supplied"
                    % kind,
                }
            )

    for kind in PLAN_KINDS:
        plan = plans.get(kind)
        if plan is None:
            continue
        if plan["architecture_revision"] != architecture["revision"]:
            findings.append(
                {
                    "code": "plan-cites-stale-architecture",
                    "plan": kind,
                    "cited": plan["architecture_revision"],
                    "current": architecture["revision"],
                    "detail": "the %s plan was written against architecture %s and the "
                    "architecture is now at %s"
                    % (kind, plan["architecture_revision"], architecture["revision"]),
                }
            )
        if plan["baseline_revision"] and not revision_is_newer(
            plan["revision"], plan["baseline_revision"]
        ):
            findings.append(
                {
                    "code": "plan-revision-did-not-move",
                    "plan": kind,
                    "revision": plan["revision"],
                    "detail": "the %s plan is still at revision %s, so it was re-dated "
                    "rather than updated" % (kind, plan["revision"]),
                }
            )

        entries = plan["entries"]
        for requirement in architecture["requirements"]:
            if requirement not in entries:
                findings.append(
                    {
                        "code": "requirement-without-updated-entry",
                        "plan": kind,
                        "requirement": requirement,
                        "detail": "requirement %s has no entry in the updated %s plan"
                        % (requirement, kind),
                    }
                )
        for requirement in sorted(entries):
            entry = entries[requirement]
            if requirement not in architecture["requirements"]:
                findings.append(
                    {
                        "code": "entry-for-retired-requirement",
                        "plan": kind,
                        "requirement": requirement,
                        "detail": "the %s plan still carries an entry for %s, which the "
                        "requirement set no longer holds" % (kind, requirement),
                    }
                )
                continue
            if entry["block"] and entry["block"] not in architecture["blocks"]:
                findings.append(
                    {
                        "code": "entry-references-retired-block",
                        "plan": kind,
                        "requirement": requirement,
                        "block": entry["block"],
                        "detail": "the %s entry for %s names block %s, which the "
                        "architecture no longer declares"
                        % (kind, requirement, entry["block"]),
                    }
                )
            moved_to = architecture["reallocations"].get(requirement)
            if moved_to is not None and entry["block"] and entry["block"] != moved_to:
                findings.append(
                    {
                        "code": "entry-not-refreshed-after-reallocation",
                        "plan": kind,
                        "requirement": requirement,
                        "block": entry["block"],
                        "expected": moved_to,
                        "detail": "requirement %s moved to block %s and the %s entry "
                        "still names %s" % (requirement, moved_to, kind, entry["block"]),
                    }
                )
            if not entry["method"]:
                findings.append(
                    {
                        "code": "entry-without-method",
                        "plan": kind,
                        "requirement": requirement,
                        "detail": "the %s entry for %s nominates no method after the "
                        "update" % (kind, requirement),
                    }
                )

        ratio = refresh_ratio(plan) if entries else 0.0
        target = case.get("refresh_target")
        if target is not None and entries:
            target_value = _fraction("refresh_target", target)
            if not meets_refresh_target(ratio, target_value):
                findings.append(
                    {
                        "code": "refresh-target-missed",
                        "plan": kind,
                        "achieved": ratio,
                        "target": target_value,
                        "detail": "the %s plan refreshed %.1f %% of its entries against "
                        "a %.1f %% target" % (kind, 100.0 * ratio, 100.0 * target_value),
                    }
                )
        summaries[kind] = {
            "revision": plan["revision"],
            "entry_count": len(entries),
            "refresh_ratio": ratio,
        }

    return {
        "architecture_revision": architecture["revision"],
        "plans": summaries,
        "findings": findings,
        "current": not findings,
    }
