"""Quality and safety management principles of a space test centre.

Anchor: ECSS-Q-ST-20-07C clause 4 (informative), the principles on which
quality assurance and safety assurance are applied to a test centre: the whole
organization of the centre and every test service it offers sit inside the
scope, not the test execution alone, and the assurance function is
organizationally independent of the operations it grades. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Hold the functions a test centre organization is made of and the services
   it sells, and which of them can never leave the assurance scope.
2. Normalise the declared scope: per function, whether quality assurance and
   safety assurance are applied, who owns it, and any exclusion rationale.
3. Refuse an exclusion on a core function, and demand a rationale and an
   accountable owner on any exclusion where one is admissible.
4. Keep a subcontracted service inside the centre's own scope: the supplier
   holding its own approval is not a reason for the centre to drop it.
5. Check the assurance function does not report into the operations line it
   grades.
6. Score coverage over the quality and safety cells of every function and
   return the principle findings and the verdict.
"""

__all__ = [
    "CENTRE_FUNCTIONS",
    "CORE_FUNCTIONS",
    "DISCIPLINES",
    "OPERATIONS_LINE",
    "normalise_identifier",
    "centre_function",
    "validate_declaration",
    "exclusion_findings",
    "subcontract_findings",
    "independence_findings",
    "coverage_cells",
    "coverage_fraction",
    "uncovered_cells",
    "assess_test_centre_scope",
]

# The organization and the services a test centre is made of. The principle
# is that assurance reaches all of them, not the test run alone.
CENTRE_FUNCTIONS = (
    "test-facility-operations",
    "test-preparation-and-integration",
    "instrumentation-and-data-acquisition",
    "calibration-and-metrology",
    "facility-maintenance",
    "facility-safety-and-emergency-response",
    "handling-transport-and-storage",
    "configuration-and-documentation-control",
    "personnel-training-and-certification",
    "subcontracted-test-services",
)

# Functions that carry the centre's licence to operate at all; an exclusion
# here is refused whatever the rationale says.
CORE_FUNCTIONS = (
    "test-facility-operations",
    "calibration-and-metrology",
    "facility-safety-and-emergency-response",
)

# The two assurance disciplines applied to every function.
DISCIPLINES = ("quality", "safety")

# Reporting lines that make the assurance function part of what it grades.
OPERATIONS_LINE = (
    "test-operations-manager",
    "facility-manager",
    "test-conductor",
    "production-manager",
)


def normalise_identifier(value, label):
    """Return a trimmed lowercase identifier; raise on anything else."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip().lower()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def centre_function(function):
    """Return the recognised name of a test centre function."""
    key = normalise_identifier(function, "function")
    if key not in CENTRE_FUNCTIONS:
        raise ValueError(
            "function must be one of %s, got %r"
            % ("/".join(CENTRE_FUNCTIONS), function)
        )
    return key


def validate_declaration(declaration):
    """Return the normalised per-function assurance scope declaration."""
    if not isinstance(declaration, (list, tuple)) or not declaration:
        raise ValueError("declaration must be a non-empty sequence of entries")
    entries = {}
    for index, item in enumerate(declaration):
        if not isinstance(item, dict):
            raise ValueError("declaration[%d] must be a mapping" % index)
        if "function" not in item:
            raise ValueError("declaration[%d] is missing 'function'" % index)
        function = centre_function(item["function"])
        if function in entries:
            raise ValueError("function %r is declared twice" % function)
        record = {"function": function, "owner": None, "rationale": None}
        for discipline in DISCIPLINES:
            key = "%s_assurance" % discipline
            if key not in item:
                raise ValueError(
                    "declaration[%d] is missing '%s' for %s" % (index, key, function)
                )
            record[discipline] = bool(item[key])
        owner = item.get("owner")
        if owner is not None:
            record["owner"] = normalise_identifier(
                owner, "declaration[%d].owner" % index
            )
        rationale = item.get("exclusion_rationale")
        if rationale is not None:
            if not isinstance(rationale, str) or not rationale.strip():
                raise ValueError(
                    "declaration[%d].exclusion_rationale must be a non-empty string"
                    % index
                )
            record["rationale"] = rationale.strip()
        entries[function] = record
    return entries


def exclusion_findings(entries):
    """Return findings on functions left outside an assurance discipline."""
    findings = []
    for function in CENTRE_FUNCTIONS:
        record = entries.get(function)
        if record is None:
            findings.append(
                "%s is not addressed by the declared assurance scope" % function
            )
            continue
        excluded = [d for d in DISCIPLINES if not record[d]]
        if not excluded:
            continue
        listed = " and ".join("%s assurance" % d for d in excluded)
        if function in CORE_FUNCTIONS:
            findings.append(
                "%s is a core function and cannot be left outside %s"
                % (function, listed)
            )
            continue
        if record["rationale"] is None:
            findings.append(
                "%s is left outside %s with no rationale" % (function, listed)
            )
            continue
        if record["owner"] is None:
            findings.append(
                "%s is left outside %s with no accountable owner"
                % (function, listed)
            )
    return findings


def subcontract_findings(entries):
    """Return findings where a subcontracted service is pushed out of scope."""
    record = entries.get("subcontracted-test-services")
    if record is None:
        return []
    excluded = [d for d in DISCIPLINES if not record[d]]
    if not excluded:
        return []
    return [
        "subcontracted test services stay inside the centre's own assurance "
        "scope; a supplier approval does not remove %s"
        % " and ".join("%s assurance" % d for d in excluded)
    ]


def independence_findings(assurance_reports_to):
    """Return findings where the assurance function reports into operations."""
    reports_to = normalise_identifier(assurance_reports_to, "assurance_reports_to")
    if reports_to in OPERATIONS_LINE:
        return [
            "the assurance function reports to the %s and so grades its own line"
            % reports_to
        ]
    return []


def coverage_cells(entries):
    """Return the (function, discipline) cells and whether each is covered."""
    cells = []
    for function in CENTRE_FUNCTIONS:
        record = entries.get(function)
        for discipline in DISCIPLINES:
            cells.append({
                "function": function,
                "discipline": discipline,
                "covered": bool(record is not None and record[discipline]),
            })
    return cells


def uncovered_cells(entries):
    """Return the cells no assurance discipline reaches."""
    return [
        "%s/%s" % (cell["function"], cell["discipline"])
        for cell in coverage_cells(entries)
        if not cell["covered"]
    ]


def coverage_fraction(entries):
    """Return the fraction of assurance cells the declaration covers."""
    cells = coverage_cells(entries)
    if not cells:
        raise ValueError("no assurance cells to score")
    return sum(1 for cell in cells if cell["covered"]) / float(len(cells))


def assess_test_centre_scope(spec):
    """Grade a test centre assurance scope against the clause 4 principles.

    spec keys: declaration (per-function entries), assurance_reports_to.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("declaration", "assurance_reports_to"):
        if key not in spec:
            raise ValueError("spec is missing required key '%s'" % key)
    entries = validate_declaration(spec["declaration"])
    findings = []
    findings.extend(exclusion_findings(entries))
    findings.extend(subcontract_findings(entries))
    findings.extend(independence_findings(spec["assurance_reports_to"]))
    fraction = coverage_fraction(entries)
    return {
        "declared_functions": sorted(entries),
        "undeclared_functions": [
            function for function in CENTRE_FUNCTIONS if function not in entries
        ],
        "coverage_fraction": fraction,
        "uncovered_cells": uncovered_cells(entries),
        "findings": findings,
        "verdict": "scope-covers-the-centre" if not findings else "scope-incomplete",
    }
