"""Software product assurance evidence owed at each milestone review.

Anchor: ECSS-Q-ST-80C Rev.2 (30 April 2025). Every requirement of the
standard names the output that evidences it and the reviews at which that
output is expected; Annex F regroups those outputs per review (SRR, PDR,
CDR, QR, AR, ORR, with test readiness reviews held per test campaign) and
Annex C defines the software product assurance milestone report (SPAMR).
Here the outputs are grouped into document kinds of our own naming, each
holding the clause identifiers that drive it and the reviews each clause
expects it at. No requirement text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the review and the project scope (suppliers, procured items,
   reuse, security sensitivity, operations and maintenance).
2. Resolve the documents a review owes for a category: a document is owed
   when at least one of its driving clauses expects it at that review and
   that clause is not tailored out for the category.
3. Grade a submitted review pack against what is owed: missing, present
   only in draft where issue was owed, and unplanned items.
4. Build the milestone report skeleton for the review from the SPAMR
   outline, marking the sections the available inputs cannot fill.
5. Walk the reviews in order and report the first one whose pack is not
   complete.
"""

__all__ = [
    "CATEGORIES",
    "REVIEWS",
    "SCOPE_FLAGS",
    "DOCUMENT_TITLES",
    "DOCUMENT_CONDITIONS",
    "DOCUMENT_CLAUSE_REVIEWS",
    "SPAMR_SECTIONS",
    "normalise_category",
    "normalise_review",
    "normalise_scope",
    "clause_applies",
    "evidence_due",
    "continuous_evidence",
    "assess_review_pack",
    "spamr_skeleton",
    "first_incomplete_review",
]

CATEGORIES = ("A", "B", "C", "D")

REVIEWS = ("srr", "pdr", "cdr", "trr", "qr", "ar", "orr")

_REVIEW_ALIASES = {
    "system-requirements-review": "srr",
    "preliminary-design-review": "pdr",
    "critical-design-review": "cdr",
    "test-readiness-review": "trr",
    "qualification-review": "qr",
    "acceptance-review": "ar",
    "operational-readiness-review": "orr",
}

SCOPE_FLAGS = ("suppliers", "procured", "reuse", "security", "operations")

DOCUMENT_TITLES = {
    "acceptance-documentation": "acceptance test plan, report and joint review",
    "alerts": "alert information raised and received",
    "audit-plan": "audit plan and schedule",
    "coding-standards": "coding standards and their tools",
    "criticality-classification": "criticality classification of software products and components",
    "dependability-safety-analysis": "software dependability and safety analysis report",
    "design-justification": "justification of design choices",
    "design-standards": "design and modelling standards",
    "isvv-plan": "independent software verification and validation plan",
    "isvv-report": "independent software verification and validation report",
    "maintenance": "maintenance plan and records",
    "nonconformance-reports": "nonconformance reports and review board records",
    "operations": "operations support and ground equipment selection",
    "problem-reports": "software problem reports and their closure",
    "procedures-standards": "procedures and standards in force",
    "process-assessment": "process assessment and improvement records",
    "procurement": "procurement data and receiving inspection",
    "requirements-baseline": "quality requirements in the requirements baseline",
    "review-inspection-records": "review and inspection plans and reports",
    "scm-plan": "software configuration management plan",
    "sdp": "software development plan and project plans",
    "security-analysis": "software security analysis report",
    "security-management-plan": "software security management plan",
    "software-configuration-file": "software configuration file and release data",
    "software-reuse-file": "software reuse file",
    "software-verification-plan": "software verification plan",
    "software-verification-report": "software verification report",
    "spa-reports": "periodic software product assurance reports",
    "spamr": "software product assurance milestone report (SPAMR)",
    "spap": "software product assurance plan (SPAP)",
    "supplier-control": "supplier selection, requirements flow-down and monitoring",
    "technical-specification": "quality requirements in the technical specification",
    "test-readiness": "test readiness confirmation and test compliance statement",
    "training": "training plan and records",
    "validation-documentation": "test and validation plans, specifications and reports",
}

# Documents owed only when the project has the matching scope.
DOCUMENT_CONDITIONS = {
    "software-reuse-file": "reuse",
    "security-analysis": "security",
    "security-management-plan": "security",
    "supplier-control": "suppliers",
    "procurement": "procured",
    "operations": "operations",
    "maintenance": "operations",
}

# SPAMR outline: (section id, topic in our words, input key or None)
SPAMR_SECTIONS = (
    ("1", "purpose and scope of this milestone report", None),
    ("2", "applicable and reference documents", None),
    ("3", "terms and abbreviations", None),
    ("4", "verification activities performed by product assurance", "verification_activities"),
    ("5", "suitability of methods and tools", "methods_tools"),
    ("6", "adherence to design and coding standards", "standards_adherence"),
    ("7", "product and process metrics against their targets", "metrics"),
    ("8", "testing and validation status and coverage", "testing"),
    ("9", "status of software problem reports and nonconformances", "problems"),
    ("10", "references to progress reports", "progress_reports"),
)

_MATURITY = {"draft": 0, "issued": 1, "approved": 2}

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

# Document kind -> {driving clause: reviews that expect it}. An empty tuple
# means the clause expects the output continuously, not at a review.
DOCUMENT_CLAUSE_REVIEWS = {
    'acceptance-documentation': {
        '6.3.7.1': ('qr', 'ar'),
        '6.3.7.6': ('ar',),
        '6.3.7.7': ('ar',),
    },
    'alerts': {
        '5.2.4': (),
    },
    'audit-plan': {
        '5.2.3': ('srr',),
    },
    'coding-standards': {
        '6.3.4.1': ('pdr',),
        '6.3.4.2': ('pdr',),
        '6.3.4.4': ('pdr',),
    },
    'criticality-classification': {
        '6.2.2.1': ('srr', 'pdr'),
        '6.2.2.3': ('pdr',),
    },
    'dependability-safety-analysis': {
        '6.2.2.2': ('pdr',),
        '6.2.2.5': ('cdr', 'qr', 'ar'),
        '6.2.2.6': ('cdr', 'qr', 'ar'),
        '6.2.2.7': ('pdr', 'cdr'),
        '6.2.2.10': ('pdr', 'cdr', 'qr', 'ar'),
        '6.2.10.1': ('pdr', 'cdr', 'qr', 'ar'),
    },
    'design-justification': {
        '7.2.2.3': ('pdr', 'cdr'),
    },
    'design-standards': {
        '6.2.8.4': ('srr', 'pdr'),
        '6.3.3.2': ('srr', 'pdr'),
    },
    'isvv-plan': {
        '6.2.6.13': ('srr', 'pdr'),
        '6.3.5.28': ('srr', 'pdr'),
    },
    'isvv-report': {
        '6.2.6.13': ('pdr', 'cdr', 'qr', 'ar'),
        '6.3.5.28': ('pdr', 'cdr', 'qr', 'ar'),
    },
    'maintenance': {
        '6.3.9.1': ('qr', 'ar', 'orr'),
        '6.3.9.2': ('qr', 'ar', 'orr'),
        '6.3.9.4': ('qr', 'ar', 'orr'),
        '6.3.9.5': ('qr', 'ar', 'orr'),
        '6.3.9.6': (),
        '6.3.9.7': (),
    },
    'nonconformance-reports': {
        '5.2.6.1': ('srr',),
        '6.3.7.5': ('ar',),
    },
    'operations': {
        '6.3.8.1': ('orr',),
        '6.3.8.2': ('orr',),
        '7.4.1': ('srr', 'pdr'),
        '7.4.2': ('srr', 'pdr'),
        '7.4.3': ('srr', 'pdr'),
        '7.4.4': ('srr', 'pdr'),
    },
    'problem-reports': {
        '5.2.5.1': ('pdr',),
        '5.2.5.2': ('pdr',),
        '5.2.5.3': ('pdr',),
        '6.2.6.4': ('srr', 'pdr', 'cdr', 'qr', 'ar', 'orr'),
        '6.3.5.6': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.8': ('srr', 'pdr', 'cdr', 'qr', 'ar', 'orr'),
    },
    'procedures-standards': {
        '6.2.1.6': ('pdr',),
        '6.2.1.7': ('pdr',),
    },
    'process-assessment': {
        '5.7.1': (),
        '5.7.2.1': (),
        '5.7.2.2': (),
        '5.7.2.3': (),
        '5.7.2.4': (),
        '5.7.3.1': (),
        '5.7.3.2': (),
        '5.7.3.3': (),
    },
    'procurement': {
        '5.5.3': ('srr', 'pdr'),
        '5.5.5': ('pdr', 'cdr', 'qr'),
        '7.4.1': ('srr', 'pdr'),
    },
    'requirements-baseline': {
        '7.1.1': ('srr',),
        '7.1.2': ('srr',),
        '7.2.1.1': ('srr',),
        '7.2.1.3': ('srr',),
    },
    'review-inspection-records': {
        '6.2.6.9': (),
        '6.2.6.10': (),
        '6.2.6.11': (),
    },
    'scm-plan': {
        '6.2.4.2': ('srr', 'pdr'),
        '6.2.4.5': ('srr', 'pdr'),
        '6.2.4.12': ('srr', 'pdr'),
        '7.3.5': ('srr', 'pdr'),
    },
    'sdp': {
        '5.5.2': ('srr', 'pdr'),
        '5.6.2.1': ('srr', 'pdr'),
        '5.6.2.2': ('srr', 'pdr'),
        '6.2.1.1': (),
        '6.2.1.2': (),
        '6.2.1.3': (),
        '6.3.4.5': ('pdr',),
    },
    'security-analysis': {
        '5.4.5': ('srr',),
        '6.2.9.2': ('pdr',),
        '6.2.9.5': ('cdr', 'qr', 'ar'),
        '6.2.9.6': ('cdr', 'qr', 'ar'),
        '6.2.9.7': ('pdr', 'cdr'),
        '6.2.10.1': ('pdr', 'cdr', 'qr', 'ar'),
    },
    'security-management-plan': {
        '6.2.4.8': ('srr', 'pdr'),
        '6.2.4.9': ('srr',),
        '6.2.4.11': ('srr',),
        '6.2.10.2': ('pdr', 'cdr', 'qr', 'ar'),
        '6.2.10.3': ('pdr', 'cdr'),
        '6.2.10.4': ('pdr', 'cdr'),
    },
    'software-configuration-file': {
        '6.2.4.3': (),
        '6.2.4.4': ('cdr', 'qr', 'ar', 'orr'),
        '6.2.4.5': ('cdr', 'qr', 'ar', 'orr'),
        '6.2.4.6': ('cdr', 'qr', 'ar', 'orr'),
        '6.2.4.8': ('cdr', 'qr', 'ar', 'orr'),
        '6.2.4.10': (),
        '6.2.4.11': (),
        '6.3.6.2': ('ar',),
    },
    'software-reuse-file': {
        '6.2.7.2': ('srr', 'pdr'),
        '6.2.7.3': ('srr', 'pdr'),
        '6.2.7.4': ('srr', 'pdr'),
        '6.2.7.5': ('srr', 'pdr'),
        '6.2.7.6': ('srr', 'pdr'),
        '6.2.7.7': ('srr', 'pdr'),
        '6.2.7.8': ('srr', 'pdr'),
        '6.2.7.9': ('cdr', 'qr', 'ar'),
        '6.2.7.11': ('srr', 'pdr', 'cdr', 'qr', 'ar'),
        '7.3.6': ('cdr',),
        '7.3.7': ('cdr',),
    },
    'software-verification-plan': {
        '6.2.6.1': ('srr', 'pdr'),
    },
    'software-verification-report': {
        '6.2.6.5': ('cdr', 'qr', 'ar'),
        '6.2.6.6': ('cdr', 'qr', 'ar'),
        '7.1.7': ('pdr', 'cdr', 'qr'),
        '7.2.3.6': ('cdr', 'qr', 'ar'),
    },
    'spa-reports': {
        '5.2.2.1': (),
        '5.2.2.2': (),
        '5.6.1.3': (),
        '6.2.5.4': (),
        '6.2.5.5': (),
        '6.2.6.2': (),
        '6.2.6.3': (),
        '6.2.6.7': (),
        '6.2.8.5': (),
        '6.3.3.4': (),
        '6.3.3.6': (),
        '6.3.3.7': (),
        '6.3.4.7': (),
        '6.3.5.3': (),
        '6.3.5.5': (),
        '6.3.5.12': (),
        '7.1.6': (),
        '7.1.8': (),
    },
    'spamr': {
        '5.2.2.3': ('srr', 'pdr', 'cdr', 'qr', 'ar', 'orr'),
        '5.6.1.2': ('srr', 'pdr'),
        '6.2.3.3': ('pdr', 'cdr', 'qr', 'ar'),
        '6.2.6.12': ('srr', 'pdr', 'cdr', 'qr', 'ar', 'orr'),
    },
    'spap': {
        '5.1.2.1': ('srr',),
        '5.1.2.2': ('srr',),
        '5.1.2.3': ('srr',),
        '5.1.3.1': ('srr',),
        '5.1.4.1': ('srr',),
        '5.2.1.1': ('srr', 'pdr'),
        '5.2.1.3': ('cdr', 'qr', 'ar', 'orr'),
        '5.2.1.4': ('ar',),
        '5.2.1.5': ('srr', 'pdr'),
        '5.2.6.1': ('srr',),
        '5.2.6.2': ('srr', 'pdr'),
        '5.2.7.1': ('pdr',),
        '5.2.7.2': ('pdr',),
        '5.4.3.3': ('pdr',),
        '5.4.3.4': ('pdr',),
        '5.6.1.1': ('srr', 'pdr'),
        '6.1.1': ('srr', 'pdr'),
        '6.2.1.4': ('srr', 'pdr'),
        '6.2.2.10': ('pdr', 'cdr'),
        '6.2.3.2': ('pdr', 'cdr'),
        '6.2.3.4': ('pdr', 'cdr'),
        '6.2.3.5': ('pdr', 'cdr'),
        '6.2.4.8': ('srr', 'pdr'),
        '6.2.4.9': ('srr', 'pdr'),
        '6.2.4.11': ('srr', 'pdr'),
        '6.2.5.1': ('srr', 'pdr'),
        '6.2.5.2': ('srr', 'pdr'),
        '6.2.7.2': ('srr', 'pdr'),
        '6.2.7.3': ('srr', 'pdr'),
        '6.2.7.4': ('srr', 'pdr'),
        '6.2.7.5': ('srr', 'pdr'),
        '6.2.9.1': ('srr', 'pdr', 'cdr'),
        '6.2.10.3': ('pdr', 'cdr'),
        '6.2.10.4': ('pdr', 'cdr'),
        '6.3.3.3': ('pdr',),
        '6.3.3.5': ('pdr',),
        '6.3.3.7': ('pdr',),
        '6.3.4.3': ('pdr',),
        '6.3.4.6': ('pdr',),
        '6.3.5.1': ('pdr', 'cdr'),
        '6.3.5.2': ('pdr', 'cdr'),
        '6.3.8.3': ('orr',),
        '7.1.3': ('srr', 'pdr'),
        '7.1.4': ('srr', 'pdr'),
        '7.1.5': ('srr', 'pdr'),
        '7.2.2.3': ('srr', 'pdr'),
        '7.5.1': ('pdr',),
        '7.5.2': ('pdr',),
    },
    'supplier-control': {
        '5.4.1.1': (),
        '5.4.2.1': ('srr',),
        '5.4.2.2': ('srr',),
        '5.4.4': ('srr',),
    },
    'technical-specification': {
        '6.3.2.4': ('pdr',),
        '7.1.1': ('pdr',),
        '7.1.2': ('pdr',),
        '7.2.1.1': ('pdr',),
        '7.2.1.3': ('pdr',),
        '7.3.4': ('pdr',),
    },
    'test-readiness': {
        '6.1.5': ('trr',),
        '6.3.5.4': ('trr',),
        '6.3.5.7': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.11': ('cdr', 'qr', 'ar', 'orr'),
    },
    'training': {
        '5.1.5.1': ('srr',),
        '5.1.5.2': (),
    },
    'validation-documentation': {
        '6.2.8.2': ('pdr', 'cdr', 'qr', 'ar'),
        '6.2.8.7': ('pdr', 'cdr', 'qr', 'ar'),
        '6.3.5.13': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.16': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.17': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.18': ('cdr', 'qr', 'ar', 'orr'),
        '6.3.5.22': ('pdr', 'cdr'),
        '6.3.5.23': ('pdr', 'cdr'),
        '6.3.5.24': ('pdr', 'cdr'),
        '6.3.5.25': ('pdr', 'cdr', 'qr', 'ar'),
        '6.3.5.27': ('ar',),
        '6.3.5.29': ('pdr', 'cdr', 'qr', 'ar'),
        '6.3.5.30': ('cdr', 'qr', 'ar'),
        '6.3.5.31': ('cdr', 'qr', 'ar'),
        '6.3.5.32': ('cdr', 'qr', 'ar'),
        '6.3.5.33': ('cdr', 'qr', 'ar'),
    },
}


def normalise_category(value):
    """Return the category letter A to D; raise ValueError otherwise."""
    if not isinstance(value, str) or value.strip().upper() not in CATEGORIES:
        raise ValueError("unknown software criticality category %r" % (value,))
    return value.strip().upper()


def normalise_review(value):
    """Return the short review name, accepting spelled-out names."""
    key = str(value).strip().lower().replace(" ", "-")
    key = _REVIEW_ALIASES.get(key, key)
    if key not in REVIEWS:
        raise ValueError("unknown review %r" % (value,))
    return key


def normalise_scope(flags):
    """Return the scope flags as a sorted tuple; refuse unknown flags."""
    out = set()
    for flag in flags or ():
        key = str(flag).strip().lower()
        if key not in SCOPE_FLAGS:
            raise ValueError("unknown scope flag %r" % (flag,))
        out.add(key)
    return tuple(sorted(out))


def clause_applies(clause, category, security_sensitive=False):
    """True when a clause is applicable (fully or reduced) for a category."""
    cat = normalise_category(category)
    code = APPLICABILITY_EXCEPTIONS.get(clause, "YYYY")[CATEGORIES.index(cat)]
    if code == "S":
        return bool(security_sensitive)
    return code in ("Y", "R")


def evidence_due(review, category, scope=()):
    """Return the documents a review owes, with the clauses that drive each.

    Returns an ordered list of dicts: document key, title and the driving
    clauses that expect it at this review and apply to the category.
    """
    rev = normalise_review(review)
    cat = normalise_category(category)
    flags = set(normalise_scope(scope))
    out = []
    for doc in sorted(DOCUMENT_CLAUSE_REVIEWS):
        cond = DOCUMENT_CONDITIONS.get(doc)
        if cond is not None and cond not in flags:
            continue
        clauses = [c for c, revs in DOCUMENT_CLAUSE_REVIEWS[doc].items()
                   if rev in revs and clause_applies(c, cat, "security" in flags)]
        if clauses:
            out.append({"document": doc, "title": DOCUMENT_TITLES[doc], "clauses": clauses})
    return out


def continuous_evidence(category, scope=()):
    """Documents tied to no review: kept current and sampled at any audit."""
    cat = normalise_category(category)
    flags = set(normalise_scope(scope))
    out = []
    for doc in sorted(DOCUMENT_CLAUSE_REVIEWS):
        cond = DOCUMENT_CONDITIONS.get(doc)
        if cond is not None and cond not in flags:
            continue
        clauses = [c for c, revs in DOCUMENT_CLAUSE_REVIEWS[doc].items()
                   if not revs and clause_applies(c, cat, "security" in flags)]
        if clauses:
            out.append({"document": doc, "title": DOCUMENT_TITLES[doc], "clauses": clauses})
    return out


def assess_review_pack(review, category, submitted, scope=(), required_maturity="issued"):
    """Grade a review pack against the documents the review owes.

    submitted: list of dicts with 'document' (a key of DOCUMENT_TITLES) and
        'maturity' ('draft', 'issued' or 'approved').
    required_maturity: the lowest maturity accepted for an owed document.

    Returns a dict with owed, missing, immature, unplanned (submitted but not
    owed at this review) and complete (bool).
    """
    if required_maturity not in _MATURITY:
        raise ValueError("unknown maturity %r" % (required_maturity,))
    owed = [d["document"] for d in evidence_due(review, category, scope)]
    got = {}
    for item in submitted:
        doc = str(item.get("document") or "").strip()
        if doc not in DOCUMENT_TITLES:
            raise ValueError("unknown document %r" % (doc,))
        if doc in got:
            raise ValueError("document %s submitted twice" % doc)
        mat = str(item.get("maturity") or "").strip().lower()
        if mat not in _MATURITY:
            raise ValueError("unknown maturity %r for %s" % (mat, doc))
        got[doc] = mat
    missing = [d for d in owed if d not in got]
    immature = [d for d in owed if d in got and _MATURITY[got[d]] < _MATURITY[required_maturity]]
    unplanned = sorted(d for d in got if d not in owed)
    return {
        "review": normalise_review(review),
        "owed": owed,
        "missing": missing,
        "immature": immature,
        "unplanned": unplanned,
        "complete": not missing and not immature,
    }


def spamr_skeleton(review, inputs):
    """Build the milestone report skeleton for a review.

    inputs: mapping of input key (see SPAMR_SECTIONS) -> content; a falsy
        value means the input is not available.

    Returns a dict with the review, the sections (id, topic, status
    'filled', 'boilerplate' or 'missing-input') and the list of missing
    inputs. The report is always marked as a draft for human review.
    """
    rev = normalise_review(review)
    sections = []
    missing = []
    for sid, topic, key in SPAMR_SECTIONS:
        if key is None:
            status = "boilerplate"
        elif inputs.get(key):
            status = "filled"
        else:
            status = "missing-input"
            missing.append(key)
        sections.append({"id": sid, "topic": topic, "status": status})
    return {"review": rev, "sections": sections, "missing_inputs": missing,
            "status": "DRAFT - requires human review and sign-off"}


def first_incomplete_review(packs, category, scope=(), required_maturity="issued"):
    """Walk the reviews in order and return the first incomplete one.

    packs: mapping review -> submitted list (as for assess_review_pack).
    Reviews with no pack given are skipped (not yet due). Returns a dict
    with the review (or None) and its assessment.
    """
    given = {normalise_review(k): v for k, v in dict(packs).items()}
    for rev in REVIEWS:
        if rev not in given:
            continue
        res = assess_review_pack(rev, category, given[rev], scope, required_maturity)
        if not res["complete"]:
            return {"review": rev, "assessment": res}
    return {"review": None, "assessment": None}
