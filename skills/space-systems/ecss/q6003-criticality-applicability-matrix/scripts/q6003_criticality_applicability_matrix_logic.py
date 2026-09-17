"""Tailoring device assurance requirements through the criticality matrix.

Anchor: ECSS-Q-ST-60-03C clause 9.2 (tailoring the assurance requirements by
the criticality category of the device, through the normative applicability
matrix). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Derive the device criticality category from the severity of the worst
   credible failure effect and from whether that effect can be recovered,
   so the category is a consequence of the design and not a declaration.
2. Validate the applicability matrix: every requirement row states an
   applicability for every category, from a closed vocabulary, and no
   requirement identifier appears twice.
3. Read the matrix at the device's category to obtain the requirement set
   that applies, separating the rows that apply outright from the rows that
   apply only with agreed tailoring.
4. Compare the declared tailoring against that set: a requirement dropped
   without a justification, a mandatory row weakened, a row claimed that the
   matrix does not carry, and a row left with no declaration at all are four
   different findings.
5. Score tailoring coverage and compare it with its floor under a named
   tolerance.
"""

import math

__all__ = [
    "COVERAGE_TOLERANCE",
    "CRITICALITY_CATEGORIES",
    "APPLICABILITY_VALUES",
    "SEVERITY_LEVELS",
    "RECOVERABILITY_LEVELS",
    "DECLARATION_VALUES",
    "normalize_token",
    "normalize_category",
    "normalize_applicability",
    "derive_category",
    "validate_matrix",
    "applicability_for",
    "applicable_requirements",
    "mandatory_requirements",
    "tailorable_requirements",
    "validate_declarations",
    "tailoring_findings",
    "tailoring_coverage",
    "assess_tailoring",
]

# Coverage is a ratio of exact integer counts compared with a floor that a
# caller may express as a decimal; absorb the representation error here.
COVERAGE_TOLERANCE = 1e-12

# Ordered most critical first.
CRITICALITY_CATEGORIES = ("category-1", "category-2", "category-3", "category-4")

APPLICABILITY_VALUES = ("applicable", "applicable-with-tailoring", "not-applicable")

# Ordered most severe first.
SEVERITY_LEVELS = ("catastrophic", "critical", "major", "minor")

RECOVERABILITY_LEVELS = (
    "not-recoverable",
    "ground-recoverable",
    "autonomously-recoverable",
)

DECLARATION_VALUES = ("retained", "tailored", "deleted")


def normalize_token(value, label):
    """Return a trimmed, lower-cased token, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = " ".join(value.split()).lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def normalize_category(value):
    """Return the canonical criticality category, or raise for an unknown one."""
    key = normalize_token(value, "criticality category")
    if key not in CRITICALITY_CATEGORIES:
        raise ValueError("unknown criticality category '%s'" % key)
    return key


def normalize_applicability(value):
    """Return the canonical applicability value, or raise for an unknown one."""
    key = normalize_token(value, "applicability")
    if key not in APPLICABILITY_VALUES:
        raise ValueError("unknown applicability value '%s'" % key)
    return key


def derive_category(severity, recoverability, mission_critical_function=True):
    """Return the criticality category implied by the worst failure effect."""
    sev = normalize_token(severity, "severity")
    if sev not in SEVERITY_LEVELS:
        raise ValueError("unknown severity level '%s'" % sev)
    rec = normalize_token(recoverability, "recoverability")
    if rec not in RECOVERABILITY_LEVELS:
        raise ValueError("unknown recoverability level '%s'" % rec)
    if not isinstance(mission_critical_function, bool):
        raise ValueError("mission_critical_function must be a boolean")

    base = {
        "catastrophic": 0,
        "critical": 1,
        "major": 2,
        "minor": 3,
    }[sev]
    # Recovery relaxes the category by at most one step, and never below the
    # step that a catastrophic effect commands.
    relief = {
        "not-recoverable": 0,
        "ground-recoverable": 1,
        "autonomously-recoverable": 1,
    }[rec]
    if sev == "catastrophic":
        relief = 0
    index = base + relief
    if not mission_critical_function:
        index += 1
    if index > len(CRITICALITY_CATEGORIES) - 1:
        index = len(CRITICALITY_CATEGORIES) - 1
    return CRITICALITY_CATEGORIES[index]


def validate_matrix(rows):
    """Return {requirement_id: {category: applicability}} for a valid matrix."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("the matrix needs at least one requirement row")
    matrix = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("matrix row must be a mapping, got %r" % (row,))
        if "requirement_id" not in row:
            raise ValueError("matrix row is missing 'requirement_id'")
        req = normalize_token(row["requirement_id"], "requirement_id").upper()
        if req in matrix:
            raise ValueError("requirement '%s' appears twice in the matrix" % req)
        cells = {}
        for category in CRITICALITY_CATEGORIES:
            if category not in row:
                raise ValueError(
                    "requirement '%s' states no applicability for %s" % (req, category)
                )
            cells[category] = normalize_applicability(row[category])
        matrix[req] = cells
    return matrix


def applicability_for(matrix, requirement_id, category):
    """Return the matrix cell for one requirement at one category."""
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping")
    req = normalize_token(requirement_id, "requirement_id").upper()
    if req not in matrix:
        raise ValueError("requirement '%s' is not in the matrix" % req)
    return matrix[req][normalize_category(category)]


def applicable_requirements(matrix, category):
    """Return the requirements that apply at this category, in identifier order."""
    key = normalize_category(category)
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping")
    return [
        req
        for req in sorted(matrix)
        if matrix[req][key] in ("applicable", "applicable-with-tailoring")
    ]


def mandatory_requirements(matrix, category):
    """Return the requirements that apply outright at this category."""
    key = normalize_category(category)
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping")
    return [req for req in sorted(matrix) if matrix[req][key] == "applicable"]


def tailorable_requirements(matrix, category):
    """Return the requirements that apply only with agreed tailoring."""
    key = normalize_category(category)
    if not isinstance(matrix, dict) or not matrix:
        raise ValueError("matrix must be a non-empty mapping")
    return [
        req
        for req in sorted(matrix)
        if matrix[req][key] == "applicable-with-tailoring"
    ]


def validate_declarations(declarations):
    """Return {requirement_id: (state, justification)} for the declared tailoring."""
    if declarations is None:
        declarations = []
    if not isinstance(declarations, (list, tuple)):
        raise ValueError("declarations must be a sequence")
    declared = {}
    for entry in declarations:
        if not isinstance(entry, dict):
            raise ValueError("declaration must be a mapping, got %r" % (entry,))
        for field in ("requirement_id", "state"):
            if field not in entry:
                raise ValueError("declaration is missing '%s'" % field)
        req = normalize_token(entry["requirement_id"], "requirement_id").upper()
        if req in declared:
            raise ValueError("requirement '%s' is declared twice" % req)
        state = normalize_token(entry["state"], "state")
        if state not in DECLARATION_VALUES:
            raise ValueError("unknown declaration state '%s'" % state)
        justification = entry.get("justification")
        if justification is not None:
            justification = normalize_token(justification, "justification")
        declared[req] = (state, justification)
    return declared


def tailoring_findings(matrix, category, declarations):
    """Return the four tailoring finding lists for this category."""
    key = normalize_category(category)
    applicable = set(applicable_requirements(matrix, key))
    mandatory = set(mandatory_requirements(matrix, key))
    declared = validate_declarations(declarations)

    unjustified_deletions = []
    weakened_mandatory = []
    outside_the_matrix = []
    undeclared = []

    for req in sorted(declared):
        state, justification = declared[req]
        if req not in matrix:
            outside_the_matrix.append(req)
            continue
        if req not in applicable:
            continue
        if state == "deleted" and justification is None:
            unjustified_deletions.append(req)
        if req in mandatory and state in ("deleted", "tailored"):
            weakened_mandatory.append(req)

    for req in sorted(applicable):
        if req not in declared:
            undeclared.append(req)

    return {
        "unjustified_deletions": unjustified_deletions,
        "weakened_mandatory": sorted(set(weakened_mandatory)),
        "outside_the_matrix": outside_the_matrix,
        "undeclared": undeclared,
    }


def tailoring_coverage(matrix, category, declarations):
    """Return the fraction of applicable requirements soundly declared."""
    key = normalize_category(category)
    applicable = applicable_requirements(matrix, key)
    if not applicable:
        raise ValueError("no requirement applies at %s; the matrix is degenerate" % key)
    mandatory = set(mandatory_requirements(matrix, key))
    declared = validate_declarations(declarations)
    sound = 0
    for req in applicable:
        if req not in declared:
            continue
        state, justification = declared[req]
        if state == "retained":
            sound += 1
        elif req in mandatory:
            continue
        elif justification is not None:
            sound += 1
    return sound / float(len(applicable))


def assess_tailoring(spec):
    """Run the full clause 9.2 criticality tailoring assessment.

    spec keys: matrix (rows), declarations, and either category or the pair
    severity / recoverability; optional mission_critical_function and
    required_coverage (default 1.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "matrix" not in spec:
        raise ValueError("spec missing required key 'matrix'")
    matrix = validate_matrix(spec["matrix"])

    if "category" in spec:
        category = normalize_category(spec["category"])
        derived = None
    else:
        for key in ("severity", "recoverability"):
            if key not in spec:
                raise ValueError(
                    "spec needs 'category', or both 'severity' and 'recoverability'"
                )
        derived = derive_category(
            spec["severity"],
            spec["recoverability"],
            spec.get("mission_critical_function", True),
        )
        category = derived

    required = spec.get("required_coverage", 1.0)
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_coverage must be a real number")
    required = float(required)
    if not math.isfinite(required) or required < 0.0 or required > 1.0:
        raise ValueError("required_coverage must lie in [0, 1], got %g" % required)

    declarations = spec.get("declarations")
    applicable = applicable_requirements(matrix, category)
    mandatory = mandatory_requirements(matrix, category)
    tailorable = tailorable_requirements(matrix, category)
    issues = tailoring_findings(matrix, category, declarations)
    coverage = tailoring_coverage(matrix, category, declarations)
    coverage_ok = coverage > required or math.isclose(
        coverage, required, rel_tol=0.0, abs_tol=COVERAGE_TOLERANCE
    )

    findings = []
    for req in issues["unjustified_deletions"]:
        findings.append("requirement %s was deleted with no justification" % req)
    for req in issues["weakened_mandatory"]:
        findings.append(
            "requirement %s applies outright at %s and cannot be tailored away"
            % (req, category)
        )
    for req in issues["outside_the_matrix"]:
        findings.append("declaration cites %s, which the matrix does not carry" % req)
    for req in issues["undeclared"]:
        findings.append("requirement %s applies at %s but is not declared" % (req, category))
    if not coverage_ok:
        findings.append(
            "tailoring coverage %.4f is below the required %.4f" % (coverage, required)
        )
    return {
        "category": category,
        "derived_category": derived,
        "applicable_requirements": applicable,
        "mandatory_requirements": mandatory,
        "tailorable_requirements": tailorable,
        "issues": issues,
        "tailoring_coverage": coverage,
        "required_coverage": required,
        "coverage_ok": coverage_ok,
        "findings": findings,
        "tailoring_acceptable": not findings,
    }
