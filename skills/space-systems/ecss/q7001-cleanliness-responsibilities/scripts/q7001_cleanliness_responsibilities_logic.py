"""Cleanliness responsibilities: who owns each activity, including facilities.

Anchor: ECSS-Q-ST-70-01C, the *programme* clause -- assigning the cleanliness
activities of a project to named actors, covering the facility operators and
the suppliers as well as the prime's own organisation. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the actor list: every actor named once and grouped by the kind of
   party it is, because the rules below turn on the kind, not the name.
2. Validate the assignment matrix: every cleanliness activity assigned, every
   assignment naming a known actor and a known role.
3. Require exactly one accountable actor per activity, and at least one actor
   carrying it out. Nobody accountable means the activity has no owner; two
   means neither of them is one.
4. Require a facility party in the loop for every activity whose outcome the
   facility decides.
5. Flow down, but do not delegate away: an activity carried out at a supplier
   needs that supplier carrying it out and the party holding the requirement
   still accountable for it.
6. Keep verification independent of execution: the people who cleaned an item
   cannot be the only people who say it is clean.
"""

__all__ = [
    "ROLES",
    "ACTIVITIES",
    "ACTOR_KINDS",
    "FACILITY_PARTY_KINDS",
    "FACILITY_DEPENDENT_ACTIVITIES",
    "RETAINING_KINDS",
    "validate_actors",
    "validate_matrix",
    "actors_in_role",
    "accountability_findings",
    "coverage_findings",
    "facility_role_findings",
    "supplier_flow_down_findings",
    "verification_independence_findings",
    "responsibility_summary",
    "assess_responsibilities",
]

# Roles an actor can hold against an activity.
ROLES = ("accountable", "responsible", "consulted", "informed")

# Cleanliness activities a project has to assign.
ACTIVITIES = (
    "cleanliness-level-definition",
    "cleanliness-budget-allocation",
    "design-provision-verification",
    "facility-environment-monitoring",
    "cleaning-execution",
    "cleanliness-verification",
    "witness-sample-management",
    "transport-and-storage-control",
    "supplier-requirement-flow-down",
    "cleanliness-non-conformance-disposition",
)

# Kinds of party an actor can be.
ACTOR_KINDS = (
    "customer",
    "prime",
    "subsystem-supplier",
    "facility-operator",
    "test-centre",
    "product-assurance",
)

# Parties that own the environment the hardware sits in.
FACILITY_PARTY_KINDS = ("facility-operator", "test-centre")

# Activities whose outcome the facility decides, so a facility party has to be
# in the loop on them.
FACILITY_DEPENDENT_ACTIVITIES = (
    "facility-environment-monitoring",
    "cleaning-execution",
    "witness-sample-management",
    "transport-and-storage-control",
)

# Parties that may retain accountability for work carried out elsewhere.
RETAINING_KINDS = ("prime", "product-assurance")

_IN_THE_LOOP = ("accountable", "responsible", "consulted")


def validate_actors(actors):
    """Return a mapping of actor name to its kind."""
    if not isinstance(actors, (list, tuple)) or not actors:
        raise ValueError("actors must be a non-empty sequence")
    catalogue = {}
    for i, actor in enumerate(actors):
        if not isinstance(actor, dict):
            raise ValueError("actors[%d] must be a mapping" % i)
        for key in ("name", "kind"):
            if key not in actor:
                raise ValueError("actors[%d] missing required key %r" % (i, key))
        name = actor["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("actors[%d] name must be a non-empty string" % i)
        name = name.strip()
        if name in catalogue:
            raise ValueError("actor %r appears twice" % name)
        kind = actor["kind"]
        if kind not in ACTOR_KINDS:
            raise ValueError(
                "actor %r has kind %r, which is not one of %s"
                % (name, kind, list(ACTOR_KINDS))
            )
        catalogue[name] = kind
    return catalogue


def validate_matrix(matrix, catalogue):
    """Return the assignment matrix as activity -> {actor name: role}."""
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping of activity to roles")
    cleaned = {}
    for activity, assignments in matrix.items():
        if activity not in ACTIVITIES:
            raise ValueError(
                "activity %r is not one of %s" % (activity, list(ACTIVITIES))
            )
        if not isinstance(assignments, dict):
            raise ValueError("assignments for %r must be a mapping" % activity)
        row = {}
        for name, role in assignments.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("actor name in %r must be a non-empty string" % activity)
            name = name.strip()
            if name not in catalogue:
                raise ValueError(
                    "activity %r assigns unknown actor %r" % (activity, name)
                )
            if role not in ROLES:
                raise ValueError(
                    "activity %r gives actor %r role %r, which is not one of %s"
                    % (activity, name, role, list(ROLES))
                )
            row[name] = role
        cleaned[activity] = row
    return cleaned


def actors_in_role(row, role):
    """Return the sorted actor names holding a role in one assignment row."""
    if role not in ROLES:
        raise ValueError("role %r is not one of %s" % (role, list(ROLES)))
    if not isinstance(row, dict):
        raise ValueError("row must be a mapping of actor name to role")
    return sorted(name for name, held in row.items() if held == role)


def coverage_findings(matrix):
    """Return findings for activities the matrix leaves out entirely."""
    return [
        "activity %r is not assigned to anyone" % activity
        for activity in ACTIVITIES
        if activity not in matrix
    ]


def accountability_findings(matrix):
    """Return findings about single-point accountability and execution."""
    findings = []
    for activity in ACTIVITIES:
        row = matrix.get(activity)
        if row is None:
            continue
        accountable = actors_in_role(row, "accountable")
        if not accountable:
            findings.append("activity %r has nobody accountable for it" % activity)
        elif len(accountable) > 1:
            findings.append(
                "activity %r splits accountability across %s; exactly one party "
                "carries it" % (activity, accountable)
            )
        if not actors_in_role(row, "responsible"):
            findings.append("activity %r has nobody carrying it out" % activity)
    return findings


def facility_role_findings(matrix, catalogue):
    """Return findings where a facility-decided activity has no facility party."""
    findings = []
    for activity in FACILITY_DEPENDENT_ACTIVITIES:
        row = matrix.get(activity)
        if row is None:
            continue
        involved = [
            name
            for name, role in row.items()
            if role in _IN_THE_LOOP and catalogue[name] in FACILITY_PARTY_KINDS
        ]
        if not involved:
            findings.append(
                "activity %r names no facility party, yet the facility decides "
                "its outcome" % activity
            )
    return findings


def supplier_flow_down_findings(matrix, catalogue, performed_at_supplier):
    """Return findings about work carried out at a supplier."""
    if performed_at_supplier is None:
        performed_at_supplier = []
    if not isinstance(performed_at_supplier, (list, tuple, set)):
        raise ValueError("performed_at_supplier must be a sequence of activities")
    findings = []
    for activity in performed_at_supplier:
        if activity not in ACTIVITIES:
            raise ValueError(
                "performed_at_supplier names unknown activity %r" % (activity,)
            )
        row = matrix.get(activity)
        if row is None:
            continue
        suppliers = [
            name
            for name in actors_in_role(row, "responsible")
            if catalogue[name] == "subsystem-supplier"
        ]
        if not suppliers:
            findings.append(
                "activity %r is carried out at a supplier but no supplier is "
                "assigned to carry it out" % activity
            )
        accountable = actors_in_role(row, "accountable")
        for name in accountable:
            if catalogue[name] not in RETAINING_KINDS:
                findings.append(
                    "activity %r is carried out at a supplier and accountability "
                    "has gone with it to %r; the requirement holder retains it"
                    % (activity, name)
                )
    return findings


def verification_independence_findings(matrix):
    """Return findings where the cleaners are the only people verifying."""
    verify = matrix.get("cleanliness-verification")
    clean = matrix.get("cleaning-execution")
    if verify is None or clean is None:
        return []
    verifiers = set(actors_in_role(verify, "responsible"))
    cleaners = set(actors_in_role(clean, "responsible"))
    if not verifiers:
        return []
    if verifiers.issubset(cleaners):
        return [
            "every party verifying cleanliness also carried out the cleaning; "
            "the verification is not independent"
        ]
    return []


def responsibility_summary(matrix, catalogue):
    """Return, per actor, how many activities it holds in each role."""
    summary = {
        name: {"kind": kind, "counts": {role: 0 for role in ROLES}}
        for name, kind in catalogue.items()
    }
    for row in matrix.values():
        for name, role in row.items():
            summary[name]["counts"][role] += 1
    return summary


def assess_responsibilities(spec):
    """Grade a cleanliness responsibility assignment.

    spec keys: actors (sequence of {name, kind}), matrix (activity -> {actor:
    role}), optional performed_at_supplier (sequence of activity names).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("actors", "matrix"):
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    catalogue = validate_actors(spec["actors"])
    matrix = validate_matrix(spec["matrix"], catalogue)
    findings = []
    findings.extend(coverage_findings(matrix))
    findings.extend(accountability_findings(matrix))
    findings.extend(facility_role_findings(matrix, catalogue))
    findings.extend(
        supplier_flow_down_findings(
            matrix, catalogue, spec.get("performed_at_supplier")
        )
    )
    findings.extend(verification_independence_findings(matrix))
    assigned = [activity for activity in ACTIVITIES if activity in matrix]
    unassigned_actors = [
        name
        for name, entry in responsibility_summary(matrix, catalogue).items()
        if sum(entry["counts"].values()) == 0
    ]
    for name in sorted(unassigned_actors):
        findings.append(
            "actor %r is named in the plan but holds no cleanliness role" % name
        )
    return {
        "activities_assigned": assigned,
        "coverage_fraction": len(assigned) / len(ACTIVITIES),
        "summary": responsibility_summary(matrix, catalogue),
        "complete": not findings,
        "findings": findings,
    }
