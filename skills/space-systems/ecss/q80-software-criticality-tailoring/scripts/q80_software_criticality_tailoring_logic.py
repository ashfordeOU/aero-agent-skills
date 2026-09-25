"""Software criticality categories and the tailoring they drive.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025), Annex D (normative): D.1 relates
the software criticality category A to D to the severity of the functions the
software implements and to the compensating provisions that exist at system
level; D.2 states, clause by clause, whether a requirement applies to software
of each category, applies in reduced form, or does not apply. The applicability
is encoded here as data (clause identifiers and a four-letter code per
clause); no requirement wording is reproduced. Paraphrased into an
implementable procedure.

Procedure implemented here
--------------------------
1. Normalise the function severity (I to IV) and the software category.
2. Assign the category of a software product from the highest severity of the
   functions it takes part in and the compensating provisions available, and
   state the constraint a software provision itself inherits.
3. Resolve, for one category, the status of every requirement of the
   standard: applicable, reduced, not applicable, or driven by the security
   sensitivity rather than by criticality.
4. Summarise the matrix per requirement group, so a tailoring proposal can be
   read at the level a customer negotiates it.
5. Compare two categories and list the requirements that relax, which is the
   evidence a downgrade argument has to carry.
6. Resolve the category of a product made of components from its most
   critical component, unless a documented partition justifies otherwise.
"""

__all__ = [
    "CATEGORIES",
    "SEVERITIES",
    "PROVISION_KINDS",
    "STATUS_BY_CODE",
    "HEADINGS",
    "REQUIREMENT_IDS",
    "APPLICABILITY_EXCEPTIONS",
    "REDUCTION_NOTES",
    "normalise_category",
    "normalise_severity",
    "normalise_requirement_id",
    "heading_of",
    "assign_category",
    "applicability",
    "tailoring_matrix",
    "group_summary",
    "relaxed_requirements",
    "project_category",
]

CATEGORIES = ("A", "B", "C", "D")

# Function severity categories as used at system level: I catastrophic,
# II critical, III major, IV minor or negligible.
SEVERITIES = ("I", "II", "III", "IV")

_SEVERITY_ALIASES = {
    "1": "I", "2": "II", "3": "III", "4": "IV",
    "i": "I", "ii": "II", "iii": "III", "iv": "IV",
    "catastrophic": "I", "critical": "II", "major": "III",
    "minor": "IV", "negligible": "IV",
}

# Kinds of compensating provision that may lower the category by one step.
PROVISION_KINDS = ("hardware", "software", "operational-procedure")

_PROVISION_ALIASES = {
    "hw": "hardware", "hardware": "hardware",
    "sw": "software", "software": "software",
    "procedure": "operational-procedure",
    "operational": "operational-procedure",
    "operational-procedure": "operational-procedure",
    "ops-procedure": "operational-procedure",
}

STATUS_BY_CODE = {
    "Y": "applicable",
    "N": "not-applicable",
    "R": "reduced",
    "S": "security-driven",
}

# Paraphrased reading of each reduced entry (code R) of the matrix. The note
# says what shrinks, never the standard's words.
REDUCTION_NOTES = {
    "5.1.5.1": "training need still met; the formal training output is not demanded",
    "5.2.3": "audits held only where a need is identified, not on a fixed plan",
    "5.2.7.2": "only the quality characteristics that matter for this software are kept",
    "5.4.1.1": "supplier selection still done; the formal output is not demanded",
    "5.6.1.1": "methods and tools must have a prior successful use, any domain",
    "5.6.1.2": "the activity stays; the formal output is not demanded",
    "5.6.1.3": "the activity stays; the formal output is not demanded",
    "5.6.2.1": "the activity stays; the formal output is not demanded",
    "5.6.2.2": "the activity stays; the formal output is not demanded",
    "6.2.5.4": "process metrics limited to problems found during validation",
    "6.2.7.4": "reuse analysis trimmed to a subset of its items, design scope limited",
    "6.2.7.7": "kept only as far as maintainability of the software needs it",
    "6.2.7.8": "kept only as far as maintainability of the software needs it",
    "6.3.3.1": "only document control is asked of the design",
    "6.3.3.2": "design standards become a recommendation",
    "6.3.3.4": "applies only if design standards were adopted",
    "6.3.4.4": "not asked unless the software is security sensitive",
    "6.3.4.8": "code enters configuration control no later than validation start",
    "6.3.5.1": "no formal unit and integration test activity is demanded",
    "6.3.5.2": "no formal unit and integration test activity is demanded",
    "6.3.5.3": "test procedures and data are verified by sampling",
    "6.3.5.4": "held for validation and acceptance testing only",
    "6.3.5.14": "held for validation and acceptance testing only",
    "6.3.8.2": "the safety-feature item of the clause drops out",
    "6.3.9.7": "statistical data need not be collected",
    "7.1.4": "one product metric item drops out",
    "7.1.5": "design and fault-density or failure-intensity metrics not demanded",
}

# Applicability data, derived from the clause structure of the standard.
# Codes per requirement, in category order A B C D: Y applicable, N not
# applicable, R reduced, S set by security sensitivity. Default YYYY.
HEADINGS = {
    '5': 'assurance programme',
    '5.1': 'organisation',
    '5.1.1': 'assurance organisation set-up',
    '5.1.2': 'who answers for what',
    '5.1.3': 'staff and means',
    '5.1.4': 'the assurance lead',
    '5.1.5': 'skills and training',
    '5.2': 'programme management',
    '5.2.1': 'planning and control of the programme',
    '5.2.2': 'assurance reporting',
    '5.2.3': 'audit programme',
    '5.2.4': 'alert handling',
    '5.2.5': 'problem reporting',
    '5.2.6': 'nonconformance handling',
    '5.2.7': 'quality model',
    '5.3': 'risks and critical items',
    '5.3.1': 'risk handling',
    '5.3.2': 'critical items',
    '5.4': 'suppliers',
    '5.4.1': 'choosing suppliers',
    '5.4.2': 'what suppliers are held to',
    '5.4.3': 'watching suppliers',
    '5.4.4': 'category flow-down to suppliers',
    '5.4.5': 'security flow-down to suppliers',
    '5.5': 'buying software',
    '5.5.1': 'purchase documents',
    '5.5.2': 'bought-in component list',
    '5.5.3': 'purchase data',
    '5.5.4': 'marking of bought items',
    '5.5.5': 'incoming checks',
    '5.5.6': 'export constraints',
    '5.6': 'tools and environment',
    '5.6.1': 'methods and tools chosen',
    '5.6.2': 'choice of development environment',
    '5.7': 'process capability',
    '5.7.1': 'capability assessment',
    '5.7.2': 'how assessments are run',
    '5.7.3': 'improving the process',
    '6': 'process assurance',
    '6.1': 'life cycle',
    '6.1.1': 'defining the life cycle',
    '6.1.2': 'process targets',
    '6.1.3': 'reviewing the life cycle',
    '6.1.4': 'means for the life cycle',
    '6.1.5': 'validation timing',
    '6.2': 'cross-process obligations',
    '6.2.1': 'process documentation',
    '6.2.2': 'dependability and safety of software',
    '6.2.3': 'critical software',
    '6.2.4': 'configuration management',
    '6.2.5': 'process measurement',
    '6.2.6': 'verification',
    '6.2.7': 'reusing existing software',
    '6.2.8': 'generated code',
    '6.2.9': 'security',
    '6.2.10': 'security-sensitive software',
    '6.3': 'per-process obligations',
    '6.3.1': 'system-level software requirements',
    '6.3.2': 'requirements analysis',
    '6.3.3': 'architecture and design',
    '6.3.4': 'coding',
    '6.3.5': 'testing and validation',
    '6.3.6': 'delivery and installation',
    '6.3.7': 'acceptance',
    '6.3.8': 'operations',
    '6.3.9': 'maintenance',
    '7': 'product quality assurance',
    '7.1': 'quality targets and measurement',
    '7.1.1': 'deriving quality requirements',
    '7.1.2': 'quality requirements as numbers',
    '7.1.3': 'checking quality requirements',
    '7.1.4': 'product measures',
    '7.1.5': 'basic measures',
    '7.1.6': 'reporting measures',
    '7.1.7': 'numerical accuracy',
    '7.1.8': 'maturity analysis',
    '7.2': 'product quality obligations',
    '7.2.1': 'requirement documents',
    '7.2.2': 'design documents',
    '7.2.3': 'test and validation documents',
    '7.3': 'software built for reuse',
    '7.3.1': 'what the customer asks for',
    '7.3.2': 'own documentation set',
    '7.3.3': 'standalone information',
    '7.3.4': 'reuse requirements',
    '7.3.5': 'configuration of reusable items',
    '7.3.6': 'multi-platform testing',
    '7.3.7': 'conformance certificate',
    '7.4': 'ground hardware and services',
    '7.4.1': 'buying ground hardware',
    '7.4.2': 'buying services',
    '7.4.3': 'limits',
    '7.4.4': 'choice',
    '7.4.5': 'upkeep',
    '7.5': 'programmable devices',
    '7.5.1': 'programming devices',
    '7.5.2': 'device marking',
    '7.5.3': 'device calibration',
}

REQUIREMENT_IDS = (
    '5.1.1', '5.1.2.1', '5.1.2.2', '5.1.2.3', '5.1.3.1', '5.1.3.2', '5.1.4.1', '5.1.4.2',
    '5.1.5.1', '5.1.5.2', '5.1.5.3', '5.1.5.4', '5.2.1.1', '5.2.1.2', '5.2.1.3', '5.2.1.4',
    '5.2.1.5', '5.2.2.1', '5.2.2.2', '5.2.2.3', '5.2.3', '5.2.4', '5.2.5.1', '5.2.5.2',
    '5.2.5.3', '5.2.5.4', '5.2.6.1', '5.2.6.2', '5.2.7.1', '5.2.7.2', '5.3.1', '5.3.2.1',
    '5.3.2.2', '5.4.1.1', '5.4.1.2', '5.4.2.1', '5.4.2.2', '5.4.3.1', '5.4.3.2', '5.4.3.3',
    '5.4.3.4', '5.4.4', '5.4.5', '5.5.1', '5.5.2', '5.5.3', '5.5.4', '5.5.5',
    '5.5.6', '5.6.1.1', '5.6.1.2', '5.6.1.3', '5.6.2.1', '5.6.2.2', '5.6.2.3', '5.7.1',
    '5.7.2.1', '5.7.2.2', '5.7.2.3', '5.7.2.4', '5.7.3.1', '5.7.3.2', '5.7.3.3', '6.1.1',
    '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.2.1.1', '6.2.1.2', '6.2.1.3', '6.2.1.4',
    '6.2.1.5', '6.2.1.6', '6.2.1.7', '6.2.1.8', '6.2.1.9', '6.2.2.1', '6.2.2.2', '6.2.2.3',
    '6.2.2.4', '6.2.2.5', '6.2.2.6', '6.2.2.7', '6.2.2.8', '6.2.2.9', '6.2.2.10', '6.2.3.2',
    '6.2.3.3', '6.2.3.4', '6.2.3.5', '6.2.3.6', '6.2.3.7', '6.2.3.8', '6.2.4.1', '6.2.4.2',
    '6.2.4.3', '6.2.4.4', '6.2.4.5', '6.2.4.6', '6.2.4.7', '6.2.4.8', '6.2.4.9', '6.2.4.10',
    '6.2.4.11', '6.2.4.12', '6.2.5.1', '6.2.5.2', '6.2.5.3', '6.2.5.4', '6.2.5.5', '6.2.6.1',
    '6.2.6.2', '6.2.6.3', '6.2.6.4', '6.2.6.5', '6.2.6.6', '6.2.6.7', '6.2.6.8', '6.2.6.9',
    '6.2.6.10', '6.2.6.11', '6.2.6.12', '6.2.6.13', '6.2.7.1', '6.2.7.2', '6.2.7.3', '6.2.7.4',
    '6.2.7.5', '6.2.7.6', '6.2.7.7', '6.2.7.8', '6.2.7.9', '6.2.7.10', '6.2.7.11', '6.2.8.1',
    '6.2.8.2', '6.2.8.3', '6.2.8.4', '6.2.8.5', '6.2.8.6', '6.2.8.7', '6.2.9.1', '6.2.9.2',
    '6.2.9.3', '6.2.9.4', '6.2.9.5', '6.2.9.6', '6.2.9.7', '6.2.10.1', '6.2.10.2', '6.2.10.3',
    '6.2.10.4', '6.3.1.1', '6.3.1.2', '6.3.1.3', '6.3.2.1', '6.3.2.2', '6.3.2.3', '6.3.2.4',
    '6.3.2.5', '6.3.3.1', '6.3.3.2', '6.3.3.3', '6.3.3.4', '6.3.3.5', '6.3.3.6', '6.3.3.7',
    '6.3.4.1', '6.3.4.2', '6.3.4.3', '6.3.4.4', '6.3.4.5', '6.3.4.6', '6.3.4.7', '6.3.4.8',
    '6.3.5.1', '6.3.5.2', '6.3.5.3', '6.3.5.4', '6.3.5.5', '6.3.5.6', '6.3.5.7', '6.3.5.8',
    '6.3.5.9', '6.3.5.10', '6.3.5.11', '6.3.5.12', '6.3.5.13', '6.3.5.14', '6.3.5.15', '6.3.5.16',
    '6.3.5.17', '6.3.5.18', '6.3.5.19', '6.3.5.20', '6.3.5.21', '6.3.5.22', '6.3.5.23', '6.3.5.24',
    '6.3.5.25', '6.3.5.26', '6.3.5.27', '6.3.5.28', '6.3.5.29', '6.3.5.30', '6.3.5.31', '6.3.5.32',
    '6.3.5.33', '6.3.6.1', '6.3.6.2', '6.3.6.3', '6.3.6.4', '6.3.7.1', '6.3.7.2', '6.3.7.3',
    '6.3.7.5', '6.3.7.6', '6.3.7.7', '6.3.8.1', '6.3.8.2', '6.3.8.3', '6.3.9.1', '6.3.9.2',
    '6.3.9.3', '6.3.9.4', '6.3.9.5', '6.3.9.6', '6.3.9.7', '7.1.1', '7.1.2', '7.1.3',
    '7.1.4', '7.1.5', '7.1.6', '7.1.7', '7.1.8', '7.2.1.1', '7.2.1.2', '7.2.1.3',
    '7.2.2.1', '7.2.2.2', '7.2.2.3', '7.2.3.1', '7.2.3.2', '7.2.3.3', '7.2.3.4', '7.2.3.5',
    '7.2.3.6', '7.3.1', '7.3.2', '7.3.3', '7.3.4', '7.3.5', '7.3.6', '7.3.7',
    '7.4.1', '7.4.2', '7.4.3', '7.4.4', '7.4.5', '7.5.1', '7.5.2', '7.5.3',
)

APPLICABILITY_EXCEPTIONS = {
    '5.1.3.2': 'YYYN',
    '5.1.5.1': 'YYYR',
    '5.1.5.2': 'YYYN',
    '5.2.3': 'YYYR',
    '5.2.7.2': 'YYYR',
    '5.4.1.1': 'YYYR',
    '5.4.2.2': 'YYYN',
    '5.4.3.4': 'YYYN',
    '5.6.1.1': 'YYYR',
    '5.6.1.2': 'YYYR',
    '5.6.1.3': 'YYYR',
    '5.6.2.1': 'YYYR',
    '5.6.2.2': 'YYYR',
    '5.7.1': 'YYYN',
    '5.7.2.1': 'YYYN',
    '5.7.2.2': 'YYYN',
    '5.7.2.3': 'YYYN',
    '5.7.2.4': 'YYYN',
    '5.7.3.1': 'YYYN',
    '5.7.3.2': 'YYYN',
    '5.7.3.3': 'YYYN',
    '6.2.1.9': 'YYYN',
    '6.2.2.2': 'YYYN',
    '6.2.2.3': 'YYYN',
    '6.2.2.4': 'YYYN',
    '6.2.2.5': 'YYYN',
    '6.2.2.6': 'YYYN',
    '6.2.2.7': 'YYYN',
    '6.2.3.2': 'YYYN',
    '6.2.3.3': 'YYYN',
    '6.2.3.4': 'YYYN',
    '6.2.3.5': 'YYYN',
    '6.2.3.6': 'YYYN',
    '6.2.3.7': 'YYNN',
    '6.2.3.8': 'YYYN',
    '6.2.5.4': 'YYYR',
    '6.2.6.5': 'YYYN',
    '6.2.6.6': 'YYYN',
    '6.2.6.13': 'YYNN',
    '6.2.7.4': 'YYYR',
    '6.2.7.7': 'YYYR',
    '6.2.7.8': 'YYYR',
    '6.2.9.1': 'SSSS',
    '6.2.9.2': 'SSSS',
    '6.2.9.3': 'SSSS',
    '6.2.9.4': 'SSSS',
    '6.2.9.5': 'SSSS',
    '6.2.9.6': 'SSSS',
    '6.2.9.7': 'SSSS',
    '6.2.10.1': 'SSSS',
    '6.2.10.2': 'SSSS',
    '6.2.10.3': 'SSSS',
    '6.2.10.4': 'SSSS',
    '6.3.3.1': 'YYYR',
    '6.3.3.2': 'YYYR',
    '6.3.3.3': 'YYYN',
    '6.3.3.4': 'YYYR',
    '6.3.3.5': 'YYYN',
    '6.3.3.6': 'YYYN',
    '6.3.4.3': 'YYYN',
    '6.3.4.4': 'YYYR',
    '6.3.4.8': 'YYYR',
    '6.3.5.1': 'YYYR',
    '6.3.5.2': 'YYYR',
    '6.3.5.3': 'YYYR',
    '6.3.5.4': 'YYYR',
    '6.3.5.9': 'YYYN',
    '6.3.5.10': 'YYYN',
    '6.3.5.14': 'YYYR',
    '6.3.5.19': 'YYYN',
    '6.3.5.28': 'YYNN',
    '6.3.5.30': 'YYYN',
    '6.3.5.31': 'YYYN',
    '6.3.8.2': 'YYRR',
    '6.3.9.7': 'YYYR',
    '7.1.4': 'YYYR',
    '7.1.5': 'YYYR',
    '7.1.8': 'YYYN',
}


def normalise_category(value):
    """Return the category letter A to D for a letter or 'cat-b' style input.

    Raises ValueError for anything that is not a category.
    """
    if not isinstance(value, str):
        raise ValueError("category must be a string, got %r" % (value,))
    text = value.strip().upper()
    for prefix in ("CATEGORY", "CAT", "SW"):
        if text.startswith(prefix):
            text = text[len(prefix):].strip(" -_.:")
    if text not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return text


def normalise_severity(value):
    """Return the severity I to IV for a roman numeral, digit or name."""
    if isinstance(value, int) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise ValueError("severity must be a string or int, got %r" % (value,))
    key = value.strip().lower()
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    for prefix in ("category", "cat"):
        if key.startswith(prefix):
            key = key[len(prefix):].strip(" -_.:")
            break
    if key.upper() in SEVERITIES:
        return key.upper()
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    raise ValueError("unknown function severity %r" % (value,))


def normalise_requirement_id(value):
    """Return a clause identifier such as '6.2.3.4' with any item letter cut.

    '6.2.3.4a', '6.2.3.4.a' and ' 6.2.3.4 ' all normalise to '6.2.3.4'.
    """
    if not isinstance(value, str):
        raise ValueError("requirement id must be a string, got %r" % (value,))
    text = value.strip().rstrip(".")
    while text and text[-1].isalpha():
        text = text[:-1].rstrip(".")
    parts = text.split(".")
    if len(parts) < 2 or not all(p.isdigit() for p in parts):
        raise ValueError("not a clause identifier: %r" % (value,))
    return ".".join(str(int(p)) for p in parts)


def heading_of(requirement_id):
    """Return (heading id, heading title) of the group a requirement sits in."""
    rid = normalise_requirement_id(requirement_id)
    parts = rid.split(".")
    for depth in (3, 2, 1):
        key = ".".join(parts[:depth])
        if key in HEADINGS:
            return key, HEADINGS[key]
    raise ValueError("no heading for %r" % (requirement_id,))


def _provision_kind(value):
    key = str(value).strip().lower()
    if key not in _PROVISION_ALIASES:
        raise ValueError("unknown compensating provision kind %r" % (value,))
    return _PROVISION_ALIASES[key]


def assign_category(severity, compensating_provisions=(), provides_provision_for=None):
    """Assign the software criticality category.

    severity: the highest severity (I to IV) of the functions the software
        takes part in.
    compensating_provisions: kinds of system-level provision that are in place
        for those functions (hardware, software, operational-procedure).
    provides_provision_for: if the software under assessment IS itself the
        compensating provision for functions of some severity, give that
        severity here; such software is placed as if no provision existed.

    Returns a dict with the category, the base category, whether a provision
    lowered it, the rationale lines and the constraints the assignment places
    on other items (a software provision must itself sit one category higher).
    """
    sev = normalise_severity(severity)
    base = CATEGORIES[SEVERITIES.index(sev)]
    rationale = ["highest function severity %s gives base category %s" % (sev, base)]
    constraints = []
    if provides_provision_for is not None:
        prov_sev = normalise_severity(provides_provision_for)
        prov_base = CATEGORIES[SEVERITIES.index(prov_sev)]
        category = min(base, prov_base)  # 'A' < 'B': the stricter letter
        rationale.append(
            "software is itself a compensating provision for severity %s "
            "functions, so it takes category %s without credit" % (prov_sev, prov_base)
        )
        return {
            "category": category,
            "base_category": base,
            "lowered_by_provision": False,
            "rationale": rationale,
            "constraints": constraints,
        }
    kinds = sorted(set(_provision_kind(k) for k in (compensating_provisions or ())))
    lowered = bool(kinds) and base != "D"
    if lowered:
        category = CATEGORIES[CATEGORIES.index(base) + 1]
        rationale.append(
            "compensating provision(s) %s lower %s to %s" % (", ".join(kinds), base, category)
        )
        if "software" in kinds:
            constraints.append(
                "the software implementing the provision must itself be category %s" % base
            )
        constraints.append(
            "each provision must meet the system dependability and safety "
            "requirements before the lower category is claimed"
        )
    else:
        category = base
        if kinds:
            rationale.append("severity IV software is already category D; no credit to take")
    return {
        "category": category,
        "base_category": base,
        "lowered_by_provision": lowered,
        "rationale": rationale,
        "constraints": constraints,
    }


def _code(requirement_id):
    rid = normalise_requirement_id(requirement_id)
    if rid not in _REQUIREMENT_SET:
        raise ValueError("requirement %r is not in the applicability matrix" % (requirement_id,))
    return APPLICABILITY_EXCEPTIONS.get(rid, "YYYY")


def applicability(requirement_id, category):
    """Return the status of one requirement for one category.

    One of 'applicable', 'reduced', 'not-applicable', 'security-driven'.
    """
    cat = normalise_category(category)
    return STATUS_BY_CODE[_code(requirement_id)[CATEGORIES.index(cat)]]


def tailoring_matrix(category, security_sensitive=False):
    """Return the tailoring rows for a category, one per requirement.

    Each row carries the requirement id, its heading id and title, the status
    and a note. Security-driven requirements resolve to applicable when the
    software is security sensitive and to not-applicable otherwise, with the
    note saying so, because that decision is not a criticality decision.
    """
    cat = normalise_category(category)
    rows = []
    for rid in REQUIREMENT_IDS:
        status = applicability(rid, cat)
        note = ""
        if status == "reduced":
            note = REDUCTION_NOTES.get(rid, "reduced scope for this category")
        elif status == "security-driven":
            status = "applicable" if security_sensitive else "not-applicable"
            note = "set by the security sensitivity of the software, not its category"
        elif status == "not-applicable":
            note = "tailored out for category %s" % cat
        head, title = heading_of(rid)
        rows.append({
            "requirement": rid,
            "heading": head,
            "heading_title": title,
            "category": cat,
            "status": status,
            "note": note,
        })
    return rows


def group_summary(category, security_sensitive=False):
    """Summarise the tailoring per requirement group for one category.

    Returns an ordered list of dicts: heading, title, counts per status and a
    group verdict ('full', 'partial' or 'none').
    """
    groups = {}
    order = []
    for row in tailoring_matrix(category, security_sensitive):
        key = row["heading"]
        if key not in groups:
            groups[key] = {
                "heading": key,
                "title": row["heading_title"],
                "applicable": 0,
                "reduced": 0,
                "not-applicable": 0,
            }
            order.append(key)
        groups[key][row["status"]] += 1
    out = []
    for key in order:
        g = groups[key]
        total = g["applicable"] + g["reduced"] + g["not-applicable"]
        if g["applicable"] == total:
            g["verdict"] = "full"
        elif g["not-applicable"] == total:
            g["verdict"] = "none"
        else:
            g["verdict"] = "partial"
        out.append(g)
    return out


_RANK = {"applicable": 2, "reduced": 1, "not-applicable": 0}


def relaxed_requirements(from_category, to_category, security_sensitive=False):
    """List what relaxes when software moves from one category to another.

    Returns rows (requirement, heading_title, from_status, to_status) for
    every requirement whose status is weaker in the target category. Moving
    to a stricter category returns an empty list.
    """
    src = {r["requirement"]: r for r in tailoring_matrix(from_category, security_sensitive)}
    dst = tailoring_matrix(to_category, security_sensitive)
    out = []
    for row in dst:
        before = src[row["requirement"]]["status"]
        if _RANK[row["status"]] < _RANK[before]:
            out.append({
                "requirement": row["requirement"],
                "heading_title": row["heading_title"],
                "from_status": before,
                "to_status": row["status"],
            })
    return out


def project_category(components, partitioned=False):
    """Resolve the category of a product from its components.

    components: iterable of dicts with 'name' and 'category'.
    partitioned: True only when a documented partitioning analysis shows the
        components cannot interfere; then each keeps its own category.

    Returns a dict: the product category (the most critical component unless
    partitioned), the per-component categories, and the components that are
    raised to the product category when no partition is claimed.
    """
    items = []
    for comp in components:
        if not isinstance(comp, dict) or "name" not in comp or "category" not in comp:
            raise ValueError("each component needs 'name' and 'category'")
        items.append((str(comp["name"]), normalise_category(comp["category"])))
    if not items:
        raise ValueError("no components given")
    names = [n for n, _ in items]
    if len(set(names)) != len(names):
        raise ValueError("duplicate component name")
    top = min(c for _, c in items)
    per = {n: (c if partitioned else top) for n, c in items}
    raised = sorted(n for n, c in items if c != top and not partitioned)
    return {
        "product_category": top,
        "per_component": per,
        "raised": raised,
        "partitioned": bool(partitioned),
    }


_REQUIREMENT_SET = frozenset(REQUIREMENT_IDS)
