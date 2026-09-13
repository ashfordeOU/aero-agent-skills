#!/usr/bin/env python3
"""EMC control plan content logic (ECSS-E-ST-20C Annex A anchor).

Deterministic, offline, stdlib-only. Paraphrased procedure -- no standard
text is reproduced. The module checks one electromagnetic-compatibility
control plan against the four content families the Annex A data-requirement
calls for: the organisation that owns compatibility control, the register of
control measures, the electromagnetic budgets those measures have to buy,
and the schedule that ties the work to the programme reviews.

Levels are handled in dB relative to 1 microvolt per metre or 1 microvolt
(dBuV), so several emitters combine by a power sum, not by addition.
"""

import math

__all__ = [
    "REQUIRED_BLOCKS",
    "MECHANISMS",
    "CONTROL_MEASURES",
    "REVIEW_ANCHORS",
    "MEASURE_EFFECTIVENESS",
    "normalize_block_key",
    "normalize_mechanism",
    "normalize_measure",
    "normalize_anchor",
    "check_block_presence",
    "validate_organisation_block",
    "validate_control_measure_register",
    "aggregate_emission_dbuv",
    "evaluate_budget_entry",
    "assess_budget_table",
    "check_schedule_milestones",
    "assess_control_plan",
]

# Tolerance used only to absorb float representation error when a computed
# margin sits on an exactly met requirement. The required margin itself is
# never reduced.
_MARGIN_REL_TOL = 1e-9
_MARGIN_ABS_TOL = 1e-9

DEFAULT_REQUIRED_MARGIN_DB = 6.0
DEFAULT_MIN_LEAD_DAYS = 30

REQUIRED_BLOCKS = (
    "organisation-and-responsibility",
    "control-measure-register",
    "electromagnetic-budget-table",
    "verification-approach-reference",
    "schedule-and-milestone-list",
    "deviation-handling-route",
)

_BLOCK_SYNONYMS = {
    "organisation": "organisation-and-responsibility",
    "organization-and-responsibility": "organisation-and-responsibility",
    "responsibilities": "organisation-and-responsibility",
    "control-measures": "control-measure-register",
    "design-measures": "control-measure-register",
    "budgets": "electromagnetic-budget-table",
    "emc-budgets": "electromagnetic-budget-table",
    "verification-approach": "verification-approach-reference",
    "schedule": "schedule-and-milestone-list",
    "milestones": "schedule-and-milestone-list",
    "deviations": "deviation-handling-route",
    "waiver-route": "deviation-handling-route",
}

MECHANISMS = (
    "conducted-emission",
    "conducted-susceptibility",
    "radiated-emission",
    "radiated-susceptibility",
    "electrostatic-discharge",
    "lightning-induced-transient",
)

_MECHANISM_SYNONYMS = {
    "ce": "conducted-emission",
    "cs": "conducted-susceptibility",
    "re": "radiated-emission",
    "rs": "radiated-susceptibility",
    "esd": "electrostatic-discharge",
    "lightning": "lightning-induced-transient",
    "indirect-lightning": "lightning-induced-transient",
}

CONTROL_MEASURES = (
    "grounding-scheme",
    "bonding-scheme",
    "shielding-scheme",
    "cable-category-segregation",
    "filtering-scheme",
    "galvanic-isolation-scheme",
)

_MEASURE_SYNONYMS = {
    "grounding": "grounding-scheme",
    "bonding": "bonding-scheme",
    "shielding": "shielding-scheme",
    "segregation": "cable-category-segregation",
    "cable-segregation": "cable-category-segregation",
    "filtering": "filtering-scheme",
    "isolation": "galvanic-isolation-scheme",
}

# Which control measure actually buys margin against which mechanism. A
# register entry outside this map names a measure that does not act on the
# coupling path it claims to control.
MEASURE_EFFECTIVENESS = {
    "conducted-emission": ("filtering-scheme", "galvanic-isolation-scheme",
                           "grounding-scheme"),
    "conducted-susceptibility": ("filtering-scheme", "galvanic-isolation-scheme",
                                 "grounding-scheme"),
    "radiated-emission": ("shielding-scheme", "bonding-scheme",
                          "cable-category-segregation"),
    "radiated-susceptibility": ("shielding-scheme", "bonding-scheme",
                                "cable-category-segregation"),
    "electrostatic-discharge": ("bonding-scheme", "grounding-scheme"),
    "lightning-induced-transient": ("bonding-scheme", "shielding-scheme",
                                    "filtering-scheme"),
}

REVIEW_ANCHORS = (
    "preliminary-design-review",
    "critical-design-review",
    "qualification-review",
    "acceptance-review",
    "flight-readiness-review",
)

_ANCHOR_SYNONYMS = {
    "pdr": "preliminary-design-review",
    "cdr": "critical-design-review",
    "qr": "qualification-review",
    "ar": "acceptance-review",
    "frr": "flight-readiness-review",
}

_MANDATORY_ANCHORS = ("preliminary-design-review", "critical-design-review")


def _canonical(raw, what):
    if not isinstance(raw, str):
        raise ValueError("%s must be a string, got %r" % (what, type(raw).__name__))
    token = "-".join(raw.strip().lower().split())
    if not token:
        raise ValueError("%s must not be empty" % what)
    return token


def _resolve(raw, what, synonyms, allowed):
    token = _canonical(raw, what)
    token = synonyms.get(token, token)
    if token not in allowed:
        raise ValueError(
            "unknown %s %r; expected one of %s" % (what, raw, ", ".join(allowed))
        )
    return token


def _margin_met(margin_db, required_db):
    """True when the margin reaches the requirement, absorbing float
    representation error at an exactly met requirement."""
    if margin_db >= required_db:
        return True
    return math.isclose(margin_db, required_db, rel_tol=_MARGIN_REL_TOL,
                        abs_tol=_MARGIN_ABS_TOL)


def _number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (what, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (what, value))
    return value


def normalize_block_key(raw):
    """Resolve a declared plan block name to its canonical token."""
    return _resolve(raw, "plan block", _BLOCK_SYNONYMS, REQUIRED_BLOCKS)


def normalize_mechanism(raw):
    """Resolve a declared interference mechanism to its canonical token."""
    return _resolve(raw, "mechanism", _MECHANISM_SYNONYMS, MECHANISMS)


def normalize_measure(raw):
    """Resolve a declared control measure to its canonical token."""
    return _resolve(raw, "control measure", _MEASURE_SYNONYMS, CONTROL_MEASURES)


def normalize_anchor(raw):
    """Resolve a declared review anchor to its canonical token."""
    return _resolve(raw, "review anchor", _ANCHOR_SYNONYMS, REVIEW_ANCHORS)


def check_block_presence(plan):
    """Report the Annex A content blocks the plan does not declare."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping of block name to content")
    declared = set()
    for key, value in plan.items():
        token = normalize_block_key(key)
        if value in (None, "", [], {}):
            continue  # a declared but empty block counts as not declared
        declared.add(token)
    missing = [b for b in REQUIRED_BLOCKS if b not in declared]
    return {
        "declared": sorted(declared),
        "missing": missing,
        "complete": not missing,
    }


def validate_organisation_block(block):
    """Check the organisation block names an owner, a route and a forum."""
    if not isinstance(block, dict):
        raise ValueError("organisation block must be a mapping")
    findings = []
    for field, finding in (
        ("responsible_authority", "compatibility-owner-unnamed"),
        ("reporting_path", "reporting-path-undeclared"),
        ("control_board_interface", "control-board-interface-undeclared"),
    ):
        value = block.get(field)
        if not (isinstance(value, str) and value.strip()):
            findings.append({"field": field, "finding": finding})
    delegates = block.get("delegates") or ()
    if isinstance(delegates, (str, dict)):
        raise ValueError("delegates must be a sequence of mappings")
    for position, delegate in enumerate(delegates):
        if not isinstance(delegate, dict):
            raise ValueError("delegates[%d] must be a mapping" % position)
        name = delegate.get("name")
        scope = delegate.get("scope")
        if not (isinstance(name, str) and name.strip()):
            findings.append({"field": "delegates[%d].name" % position,
                             "finding": "delegate-unnamed"})
        if not (isinstance(scope, str) and scope.strip()):
            findings.append({"field": "delegates[%d].scope" % position,
                             "finding": "delegate-scope-undeclared"})
    return findings


def validate_control_measure_register(entries, mechanisms_in_scope=None):
    """Check every register entry and every mechanism the plan must control.

    An entry pairs a mechanism with a control measure and an owner. The
    measure has to act on that mechanism's coupling path, and each
    mechanism in scope needs at least one entry that does.
    """
    if entries is None or isinstance(entries, (str, dict)):
        raise ValueError("register must be a sequence of entry mappings")
    entries = list(entries)
    if not entries:
        raise ValueError("register must declare at least one entry")
    in_scope = [normalize_mechanism(m) for m in (mechanisms_in_scope or MECHANISMS)]
    findings = []
    covered = {}
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("register[%d] must be a mapping" % position)
        mechanism = normalize_mechanism(entry.get("mechanism"))
        measure = normalize_measure(entry.get("measure"))
        owner = entry.get("owner")
        if not (isinstance(owner, str) and owner.strip()):
            findings.append({"entry": position, "mechanism": mechanism,
                             "finding": "measure-owner-unnamed"})
        if measure not in MEASURE_EFFECTIVENESS[mechanism]:
            findings.append({"entry": position, "mechanism": mechanism,
                             "measure": measure,
                             "finding": "measure-does-not-act-on-mechanism"})
            continue
        covered.setdefault(mechanism, []).append(measure)
    for mechanism in in_scope:
        if mechanism not in covered:
            findings.append({"mechanism": mechanism,
                             "finding": "mechanism-uncontrolled"})
    return {
        "covered": {k: sorted(v) for k, v in sorted(covered.items())},
        "findings": findings,
    }


def aggregate_emission_dbuv(levels):
    """Combine emitter levels given in dB by a power sum, not by addition."""
    if levels is None or isinstance(levels, (str, dict)):
        raise ValueError("levels must be a sequence of dB values")
    levels = [_number(v, "emitter level") for v in levels]
    if not levels:
        raise ValueError("levels must declare at least one emitter")
    total = 0.0
    for level in levels:
        total += 10.0 ** (level / 10.0)
    return 10.0 * math.log10(total)


def evaluate_budget_entry(entry, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Compute the margin one victim holds against its emitter set."""
    if not isinstance(entry, dict):
        raise ValueError("budget entry must be a mapping")
    required = _number(required_margin_db, "required margin")
    if required < 0.0:
        raise ValueError("required margin must not be negative")
    victim = entry.get("victim")
    if not (isinstance(victim, str) and victim.strip()):
        raise ValueError("budget entry needs a non-empty 'victim'")
    mechanism = normalize_mechanism(entry.get("mechanism"))
    susceptibility = _number(entry.get("susceptibility_level_dbuv"),
                             "susceptibility level")
    aggregate = aggregate_emission_dbuv(entry.get("emitter_levels_dbuv"))
    margin = susceptibility - aggregate
    compliant = _margin_met(margin, required)
    return {
        "victim": victim.strip(),
        "mechanism": mechanism,
        "aggregate_emission_dbuv": aggregate,
        "margin_db": margin,
        "required_margin_db": required,
        "shortfall_db": 0.0 if compliant else required - margin,
        "compliant": compliant,
    }


def assess_budget_table(entries, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB):
    """Evaluate every budget row and report the worst margin on the table."""
    if entries is None or isinstance(entries, (str, dict)):
        raise ValueError("budget table must be a sequence of entry mappings")
    entries = list(entries)
    if not entries:
        raise ValueError("budget table must declare at least one entry")
    rows = [evaluate_budget_entry(e, required_margin_db) for e in entries]
    rows.sort(key=lambda r: (r["victim"], r["mechanism"]))
    breaches = [r for r in rows if not r["compliant"]]
    worst = min(rows, key=lambda r: r["margin_db"])
    return {
        "rows": rows,
        "worst_margin_db": worst["margin_db"],
        "worst_victim": worst["victim"],
        "breaches": breaches,
        "findings": [{"victim": r["victim"], "mechanism": r["mechanism"],
                      "finding": "margin-shortfall",
                      "shortfall_db": r["shortfall_db"]} for r in breaches],
    }


def check_schedule_milestones(milestones, min_lead_days=DEFAULT_MIN_LEAD_DAYS):
    """Check each milestone anchors to a review with enough lead time."""
    if milestones is None or isinstance(milestones, (str, dict)):
        raise ValueError("milestones must be a sequence of mappings")
    milestones = list(milestones)
    if not milestones:
        raise ValueError("schedule must declare at least one milestone")
    if isinstance(min_lead_days, bool) or not isinstance(min_lead_days, int):
        raise ValueError("min_lead_days must be an integer number of days")
    if min_lead_days < 0:
        raise ValueError("min_lead_days must not be negative")
    findings = []
    anchored = set()
    for position, milestone in enumerate(milestones):
        if not isinstance(milestone, dict):
            raise ValueError("milestones[%d] must be a mapping" % position)
        name = milestone.get("name")
        if not (isinstance(name, str) and name.strip()):
            raise ValueError("milestones[%d] needs a non-empty 'name'" % position)
        anchor = normalize_anchor(milestone.get("anchor"))
        lead = milestone.get("lead_days")
        if isinstance(lead, bool) or not isinstance(lead, int):
            raise ValueError("milestones[%d] needs an integer 'lead_days'" % position)
        anchored.add(anchor)
        if lead < 0:
            findings.append({"milestone": name.strip(), "anchor": anchor,
                             "finding": "milestone-lands-after-its-review"})
        elif lead < min_lead_days:
            findings.append({"milestone": name.strip(), "anchor": anchor,
                             "finding": "milestone-lead-too-short",
                             "lead_days": lead})
    for anchor in _MANDATORY_ANCHORS:
        if anchor not in anchored:
            findings.append({"anchor": anchor, "finding": "review-anchor-unserved"})
    return {"anchored": sorted(anchored), "findings": findings}


def assess_control_plan(plan, required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
                        min_lead_days=DEFAULT_MIN_LEAD_DAYS,
                        mechanisms_in_scope=None):
    """Run the full Annex A content check over one control plan.

    The plan is acceptable when every content block is declared and
    non-empty, the organisation block names its owner, route and forum,
    every mechanism in scope carries at least one effective control
    measure, every budget row holds its required margin, and every
    milestone anchors to a review with enough lead time.
    """
    presence = check_block_presence(plan)
    findings = [{"block": b, "finding": "content-block-undeclared"}
                for b in presence["missing"]]
    organisation = []
    register = {"covered": {}, "findings": []}
    budget = None
    schedule = {"anchored": [], "findings": []}
    if "organisation-and-responsibility" not in presence["missing"]:
        organisation = validate_organisation_block(
            plan.get("organisation-and-responsibility")
            or plan.get("organisation"))
        findings.extend(organisation)
    if "control-measure-register" not in presence["missing"]:
        register = validate_control_measure_register(
            plan.get("control-measure-register") or plan.get("control-measures"),
            mechanisms_in_scope)
        findings.extend(register["findings"])
    if "electromagnetic-budget-table" not in presence["missing"]:
        budget = assess_budget_table(
            plan.get("electromagnetic-budget-table") or plan.get("budgets"),
            required_margin_db)
        findings.extend(budget["findings"])
    if "schedule-and-milestone-list" not in presence["missing"]:
        schedule = check_schedule_milestones(
            plan.get("schedule-and-milestone-list") or plan.get("schedule"),
            min_lead_days)
        findings.extend(schedule["findings"])
    return {
        "presence": presence,
        "organisation_findings": organisation,
        "register": register,
        "budget": budget,
        "schedule": schedule,
        "findings": findings,
        "acceptable": not findings,
    }
