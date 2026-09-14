#!/usr/bin/env python3
"""Planar blocking diode qualification is granted to the company running the process.

Anchor: ECSS-E-ST-20-08C clause 12.5.1. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

The clause puts the grant in one place and one place only: the customer makes
it, and it lands on the organisation that actually runs the production
process. It does not land on a part number. That distinction is the whole
job here, because a part number travels and a process does not. A diode type
qualified at one company is an unqualified diode type the moment a second
company builds it, however identical the drawing, and however recently the
register was refreshed.

Four questions are therefore asked about every lot, and they fail for
different reasons:

    scope       is this a planar diode at all, since the clause reaches
                planar construction and a mesa part is a different article
    existence   is there a grant on record for this diode type
    holder      was that grant made to the company that ran THIS lot, or to
                somebody else who happens to build the same type
    reach       does the grant still cover the site, the process baseline and
                every step handed to a subcontractor, and is it still live

The arms are ranked rather than merged because they ask for different work.
A mesa lot needs a different clause, not a grant. A type nobody ever granted
needs a qualification campaign. A type granted to another company needs a
campaign at this one, which is the finding a register lookup keyed on the
type alone can never produce. A drifted site or baseline needs a delta
justification, an uncovered subcontracted step needs the subcontractor
brought inside the grant, and a withdrawn grant needs the customer asked.

Dates are not read here; the register state is the caller's input. Nothing is
read from the clock, so the same programme returns the same verdict every run.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PROCESS_IDENTITY_KEYS = (
    "process_owner",
    "production_site",
    "diode_construction",
    "process_baseline",
)

SCOPE_PINNED_KEYS = ("production_site", "process_baseline")

QUALIFIED_CONSTRUCTION = "planar"
ACCEPTED_CONSTRUCTIONS = ("planar", "mesa")

GRANTING_AUTHORITY = "customer"
ACCEPTED_AUTHORITIES = ("customer", "supplier", "third-party-laboratory")

GRANT_STATES = ("issued", "withdrawn")

LOT_QUALIFIED = "lot-qualified"
LOT_CONSTRUCTION_OUT_OF_SCOPE = "lot-blocked-construction-out-of-scope"
LOT_NO_GRANT = "lot-blocked-no-grant-for-type"
LOT_HOLDER_MISMATCH = "lot-blocked-grant-held-by-another-company"
LOT_AUTHORITY_INVALID = "lot-blocked-grant-authority-invalid"
LOT_SCOPE_MISMATCH = "lot-blocked-grant-scope-mismatch"
LOT_SUBCONTRACTED_STEP_UNCOVERED = "lot-blocked-subcontracted-step-uncovered"
LOT_GRANT_WITHDRAWN = "lot-blocked-grant-withdrawn"

LOT_VERDICT_RANK = (
    LOT_CONSTRUCTION_OUT_OF_SCOPE,
    LOT_NO_GRANT,
    LOT_HOLDER_MISMATCH,
    LOT_AUTHORITY_INVALID,
    LOT_SCOPE_MISMATCH,
    LOT_SUBCONTRACTED_STEP_UNCOVERED,
    LOT_GRANT_WITHDRAWN,
    LOT_QUALIFIED,
)

PROGRAMME_FULLY_QUALIFIED = "blocking-diode-programme-fully-qualified"
PROGRAMME_NOT_FULLY_QUALIFIED = "blocking-diode-programme-not-fully-qualified"

DEFAULT_GRANT_POLICY = {
    "require_customer_grant": True,
    "admit_supplier_self_declaration": False,
    "require_holder_match": True,
    "require_planar_construction": True,
    "admit_undeclared_subcontractor": False,
    "min_qualified_lot_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_fraction(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    value = float(value)
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return value


def validate_grant_policy(policy):
    """Check a qualification authority policy declares a usable rule set."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in (
        "require_customer_grant",
        "admit_supplier_self_declaration",
        "require_holder_match",
        "require_planar_construction",
        "admit_undeclared_subcontractor",
    ):
        _require_flag(key, policy.get(key))
    _require_fraction(
        "min_qualified_lot_fraction", policy.get("min_qualified_lot_fraction")
    )
    return policy


def process_identity(article):
    """The attributes a blocking diode grant is matched against."""
    if not isinstance(article, dict):
        raise ValueError("article must be a mapping, got %r" % (article,))
    missing = sorted(key for key in PROCESS_IDENTITY_KEYS if key not in article)
    if missing:
        raise ValueError("article is missing %s" % ", ".join(missing))
    identity = {
        key: _require_text(key, article[key]) for key in PROCESS_IDENTITY_KEYS
    }
    construction = identity["diode_construction"].lower()
    if construction not in ACCEPTED_CONSTRUCTIONS:
        raise ValueError(
            "diode_construction must be one of %s, got %r"
            % (", ".join(ACCEPTED_CONSTRUCTIONS), construction)
        )
    identity["diode_construction"] = construction
    return identity


def identity_delta(lot, scope):
    """Which process attributes the granted scope does not reach."""
    built = process_identity(lot)
    granted = process_identity(scope)
    return sorted(
        key for key in PROCESS_IDENTITY_KEYS if built[key] != granted[key]
    )


def construction_in_clause_scope(lot, policy=DEFAULT_GRANT_POLICY):
    """Is this lot the planar construction the clause reaches."""
    validate_grant_policy(policy)
    identity = process_identity(lot)
    construction = identity["diode_construction"]
    in_scope = construction == QUALIFIED_CONSTRUCTION
    if not policy["require_planar_construction"]:
        in_scope = True
    return {"diode_construction": construction, "in_scope": in_scope}


def grants_for_type(grant_register, diode_type):
    """Every grant the register holds for one diode type, in holder order."""
    if not isinstance(grant_register, (list, tuple)):
        raise ValueError(
            "grant_register must be a sequence, got %r" % (grant_register,)
        )
    wanted = _require_text("diode_type", diode_type)
    found = []
    seen = set()
    for grant in grant_register:
        if not isinstance(grant, dict):
            raise ValueError("grant must be a mapping, got %r" % (grant,))
        named = _require_text("diode_type", grant.get("diode_type"))
        holder = _require_text("granted_to", grant.get("granted_to"))
        if named != wanted:
            continue
        if holder in seen:
            raise ValueError(
                "the register holds more than one grant for diode type %s at %s"
                % (wanted, holder)
            )
        seen.add(holder)
        found.append(grant)
    found.sort(key=lambda entry: _require_text("granted_to", entry["granted_to"]))
    return found


def find_grant(grant_register, diode_type, process_owner):
    """The grant made to the company that ran this lot, or nothing."""
    owner = _require_text("process_owner", process_owner)
    for grant in grants_for_type(grant_register, diode_type):
        if _require_text("granted_to", grant["granted_to"]) == owner:
            return grant
    return None


def grant_issuing_authority(grant, policy=DEFAULT_GRANT_POLICY):
    """Who made the grant, and is that a party allowed to make it."""
    validate_grant_policy(policy)
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    issued_by = _require_text("issued_by", grant.get("issued_by")).lower()
    if issued_by not in ACCEPTED_AUTHORITIES:
        raise ValueError(
            "issued_by must be one of %s, got %r"
            % (", ".join(ACCEPTED_AUTHORITIES), issued_by)
        )
    if issued_by == GRANTING_AUTHORITY:
        valid = True
    elif issued_by == "supplier":
        valid = bool(policy["admit_supplier_self_declaration"])
    else:
        valid = not policy["require_customer_grant"]
    return {"issued_by": issued_by, "valid": valid}


def grant_state(grant):
    """Is the grant still live, or has the customer taken it back."""
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    state = grant.get("state")
    state = "issued" if state is None else _require_text("state", state).lower()
    if state not in GRANT_STATES:
        raise ValueError(
            "state must be one of %s, got %r" % (", ".join(GRANT_STATES), state)
        )
    return {"state": state, "withdrawn": state == "withdrawn"}


def subcontracted_step_coverage(lot, grant, policy=DEFAULT_GRANT_POLICY):
    """Which handed-out process steps the grant does not reach."""
    validate_grant_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    if not isinstance(grant, dict):
        raise ValueError("grant must be a mapping, got %r" % (grant,))
    holder = _require_text("granted_to", grant.get("granted_to"))
    permitted = grant.get("permitted_subcontractors", [])
    if not isinstance(permitted, (list, tuple)):
        raise ValueError(
            "permitted_subcontractors must be a sequence, got %r" % (permitted,)
        )
    allowed = {holder}
    for party in permitted:
        allowed.add(_require_text("permitted_subcontractor", party))
    steps = lot.get("subcontracted_steps", [])
    if not isinstance(steps, (list, tuple)):
        raise ValueError(
            "subcontracted_steps must be a sequence, got %r" % (steps,)
        )
    uncovered = []
    named = set()
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("subcontracted step must be a mapping, got %r" % (step,))
        step_id = _require_text("step", step.get("step"))
        performed_by = _require_text("performed_by", step.get("performed_by"))
        if step_id in named:
            raise ValueError("lot declares subcontracted step %s twice" % step_id)
        named.add(step_id)
        if performed_by not in allowed and not policy["admit_undeclared_subcontractor"]:
            uncovered.append({"step": step_id, "performed_by": performed_by})
    uncovered.sort(key=lambda entry: entry["step"])
    return {
        "declared_steps": sorted(named),
        "permitted_parties": sorted(allowed),
        "uncovered_steps": uncovered,
        "covered": not uncovered,
    }


def assess_lot_qualification(lot, grant_register, policy=DEFAULT_GRANT_POLICY):
    """May this blocking diode lot be treated as qualified, and if not, why."""
    validate_grant_policy(policy)
    if not isinstance(lot, dict):
        raise ValueError("lot must be a mapping, got %r" % (lot,))
    lot_id = _require_text("lot_id", lot.get("lot_id"))
    diode_type = _require_text("diode_type", lot.get("diode_type"))
    identity = process_identity(lot)
    construction = construction_in_clause_scope(lot, policy)

    base = {
        "lot_id": lot_id,
        "diode_type": diode_type,
        "identity": identity,
        "construction": construction,
        "grant_id": None,
        "grant_holder": None,
        "other_holders": [],
        "authority": None,
        "state": None,
        "identity_delta": [],
        "uncovered_steps": [],
    }

    if not construction["in_scope"]:
        base.update(
            {
                "verdict": LOT_CONSTRUCTION_OUT_OF_SCOPE,
                "qualified": False,
                "findings": [
                    "lot %s is %s construction and clause 12.5.1 reaches the %s "
                    "blocking diode" % (lot_id, construction["diode_construction"],
                                        QUALIFIED_CONSTRUCTION)
                ],
            }
        )
        return base

    candidates = grants_for_type(grant_register, diode_type)
    holders = sorted(
        _require_text("granted_to", grant["granted_to"]) for grant in candidates
    )
    base["other_holders"] = [h for h in holders if h != identity["process_owner"]]

    if not candidates:
        base.update(
            {
                "verdict": LOT_NO_GRANT,
                "qualified": False,
                "findings": [
                    "diode type %s is built on lot %s with no qualification grant "
                    "on record for any company" % (diode_type, lot_id)
                ],
            }
        )
        return base

    grant = find_grant(grant_register, diode_type, identity["process_owner"])
    if grant is None and policy["require_holder_match"]:
        base.update(
            {
                "verdict": LOT_HOLDER_MISMATCH,
                "qualified": False,
                "findings": [
                    "diode type %s is granted to %s, and lot %s was run by %s"
                    % (
                        diode_type,
                        ", ".join(holders),
                        lot_id,
                        identity["process_owner"],
                    )
                ],
            }
        )
        return base
    if grant is None:
        grant = candidates[0]

    grant_id = _require_text("grant_id", grant.get("grant_id"))
    holder = _require_text("granted_to", grant.get("granted_to"))
    authority = grant_issuing_authority(grant, policy)
    state = grant_state(grant)
    scope = grant.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("grant %s declares no scope mapping" % grant_id)
    delta = identity_delta(lot, scope)
    pinned = [key for key in delta if key in SCOPE_PINNED_KEYS]
    coverage = subcontracted_step_coverage(lot, grant, policy)

    base.update(
        {
            "grant_id": grant_id,
            "grant_holder": holder,
            "authority": authority,
            "state": state,
            "identity_delta": delta,
            "uncovered_steps": coverage["uncovered_steps"],
        }
    )

    findings = []
    if not authority["valid"]:
        verdict = LOT_AUTHORITY_INVALID
        findings.append(
            "grant %s was issued by the %s, and qualification is granted by the %s"
            % (grant_id, authority["issued_by"], GRANTING_AUTHORITY)
        )
    elif pinned:
        verdict = LOT_SCOPE_MISMATCH
        findings.append(
            "grant %s does not reach the %s of lot %s"
            % (grant_id, ", ".join(pinned), lot_id)
        )
    elif not coverage["covered"]:
        verdict = LOT_SUBCONTRACTED_STEP_UNCOVERED
        findings.append(
            "lot %s hands %s to a party grant %s never reached"
            % (
                lot_id,
                ", ".join(
                    "%s (%s)" % (entry["step"], entry["performed_by"])
                    for entry in coverage["uncovered_steps"]
                ),
                grant_id,
            )
        )
    elif state["withdrawn"]:
        verdict = LOT_GRANT_WITHDRAWN
        findings.append(
            "grant %s held by %s has been withdrawn, so lot %s is unqualified"
            % (grant_id, holder, lot_id)
        )
    else:
        verdict = LOT_QUALIFIED

    base["verdict"] = verdict
    base["qualified"] = verdict == LOT_QUALIFIED
    base["findings"] = findings
    return base


def worst_lot_verdict(verdicts):
    """The verdict that has to be closed first across a set of lots."""
    if not isinstance(verdicts, (list, tuple, set, frozenset)) or not verdicts:
        raise ValueError("verdicts must be a non-empty sequence")
    ranked = []
    for verdict in verdicts:
        verdict = _require_text("verdict", verdict)
        if verdict not in LOT_VERDICT_RANK:
            raise ValueError("unknown lot verdict %s" % verdict)
        ranked.append(LOT_VERDICT_RANK.index(verdict))
    return LOT_VERDICT_RANK[min(ranked)]


def assess_blocking_diode_qualification_authority(
    programme, policy=DEFAULT_GRANT_POLICY
):
    """Full clause 12.5.1 sweep over the lots a production programme builds."""
    validate_grant_policy(policy)
    if not isinstance(programme, dict):
        raise ValueError("programme must be a mapping, got %r" % (programme,))
    programme_id = _require_text("programme_id", programme.get("programme_id"))
    register = programme.get("grant_register")
    if not isinstance(register, (list, tuple)):
        raise ValueError("programme grant_register must be a sequence of mappings")
    lots = programme.get("lots")
    if not isinstance(lots, (list, tuple)) or not lots:
        raise ValueError("programme lots must be a non-empty sequence")

    seen = set()
    assessments = []
    for lot in lots:
        assessed = assess_lot_qualification(lot, register, policy)
        if assessed["lot_id"] in seen:
            raise ValueError("programme declares lot %s twice" % assessed["lot_id"])
        seen.add(assessed["lot_id"])
        assessments.append(assessed)
    assessments.sort(key=lambda entry: entry["lot_id"])

    findings = []
    for entry in assessments:
        findings.extend(entry["findings"])

    qualified = [entry for entry in assessments if entry["qualified"]]
    blocked = sorted(
        entry["lot_id"] for entry in assessments if not entry["qualified"]
    )
    grouped = {}
    for entry in assessments:
        grouped.setdefault(entry["verdict"], []).append(entry["lot_id"])

    total = len(assessments)
    qualified_fraction = len(qualified) / float(total)
    minimum = float(policy["min_qualified_lot_fraction"])
    share_ok = _at_least(qualified_fraction, minimum)
    if not share_ok:
        findings.append(
            "the programme qualifies %d of %d blocking diode lots against a "
            "required share of %.3f" % (len(qualified), total, minimum)
        )

    ungranted_types = sorted(
        {
            entry["diode_type"]
            for entry in assessments
            if entry["verdict"] == LOT_NO_GRANT
        }
    )
    foreign_process_owners = sorted(
        {
            entry["identity"]["process_owner"]
            for entry in assessments
            if entry["verdict"] == LOT_HOLDER_MISMATCH
        }
    )
    return {
        "verdict": PROGRAMME_FULLY_QUALIFIED
        if share_ok and not blocked
        else PROGRAMME_NOT_FULLY_QUALIFIED,
        "programme_id": programme_id,
        "lot_assessments": assessments,
        "grouped_by_verdict": {k: sorted(v) for k, v in grouped.items()},
        "blocked_lot_ids": blocked,
        "ungranted_diode_types": ungranted_types,
        "unqualified_process_owners": foreign_process_owners,
        "worst_verdict": worst_lot_verdict(
            [entry["verdict"] for entry in assessments]
        ),
        "qualified_lot_fraction": qualified_fraction,
        "required_lot_fraction": minimum,
        "every_lot_qualified": not blocked,
        "findings": findings,
    }
