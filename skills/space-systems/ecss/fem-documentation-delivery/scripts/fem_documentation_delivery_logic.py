#!/usr/bin/env python3
"""ECSS-E-ST-32C model documentation and delivery (MMDD) verification
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structural engineering standard's model documentation and delivery
requirements specify which document types must accompany a finite
element model delivery (model description, element quality report,
material property record, coordinate system description, load case
list, mass properties check), which metadata fields each document must
carry (document identifier, revision, model identifier, model revision,
author, date), that all documents in the package must reference the
same model revision, and which file types must be present in the
delivery set (FEM input file, documentation package bundle). This
module implements document-type validation, metadata field checking,
document completeness assessment, revision consistency verification,
and file delivery confirmation; it does not implement content quality
checks of individual documents.
"""

REQUIRED_DOCUMENT_TYPES = frozenset({
    "model_description",
    "element_quality_report",
    "material_property_record",
    "coordinate_system_description",
    "load_case_list",
    "mass_properties_check",
})

OPTIONAL_DOCUMENT_TYPES = frozenset({
    "modal_analysis_summary",
    "boundary_condition_description",
    "model_correlation_report",
    "sensitivity_analysis_report",
})

ALL_KNOWN_DOCUMENT_TYPES = REQUIRED_DOCUMENT_TYPES | OPTIONAL_DOCUMENT_TYPES

REQUIRED_METADATA_FIELDS = frozenset({
    "document_id",
    "revision",
    "model_id",
    "model_revision",
    "author",
    "date",
})

REQUIRED_FILE_TYPES = frozenset({
    "fem_input_file",
    "documentation_package",
})


def validate_document_type(doc_type):
    """Return "required" or "optional" for a recognized document type.
    Raises ValueError for any type outside both known sets."""
    if doc_type in REQUIRED_DOCUMENT_TYPES:
        return "required"
    if doc_type in OPTIONAL_DOCUMENT_TYPES:
        return "optional"
    raise ValueError(
        "unrecognized FEM document type %r under E-ST-32C MMDD" % (doc_type,)
    )


def check_metadata_fields(document):
    """Violation list (empty if compliant) for a single document dict.
    Returns one finding per missing required metadata field.
    Does not mutate the document."""
    violations = []
    doc_id = document.get("document_id") or document.get("document_type", "<unknown>")
    for field in sorted(REQUIRED_METADATA_FIELDS):
        if not document.get(field):
            violations.append({
                "issue": "missing_metadata_field",
                "document": doc_id,
                "field": field,
            })
    return violations


def check_document_completeness(documents):
    """Violation list (empty if compliant) for the set of document types
    in a delivery package. Returns one finding per missing required type.
    Raises ValueError for any document with an unrecognized type.
    Does not mutate the input."""
    present_types = set()
    for doc in documents:
        doc_type = doc.get("document_type", "")
        validate_document_type(doc_type)
        present_types.add(doc_type)
    violations = []
    for required_type in sorted(REQUIRED_DOCUMENT_TYPES):
        if required_type not in present_types:
            violations.append({
                "issue": "missing_required_document_type",
                "document_type": required_type,
            })
    return violations


def check_revision_consistency(documents):
    """Violation list (empty if compliant) for model revision consistency
    across all documents. All documents must carry the same non-empty
    model_revision. Returns [] when the document list is empty.
    Raises ValueError if any document is missing the model_revision
    field. Does not mutate the input."""
    docs = list(documents)
    if not docs:
        return []
    doc_revisions = {}
    for doc in docs:
        rev = doc.get("model_revision")
        if not rev:
            raise ValueError(
                "document %r is missing model_revision; "
                "cannot perform consistency check"
                % (doc.get("document_id", "<unknown>"),)
            )
        doc_revisions[doc.get("document_id", "<unknown>")] = rev
    unique_revisions = set(doc_revisions.values())
    if len(unique_revisions) <= 1:
        return []
    return [
        {
            "issue": "revision_mismatch",
            "revisions_found": sorted(unique_revisions),
            "document_revisions": doc_revisions,
        }
    ]


def check_file_delivery(files):
    """Violation list (empty if compliant) for the set of delivered
    files. Returns one finding per missing required file type.
    Does not mutate the input."""
    present_types = {f.get("file_type") for f in files}
    violations = []
    for required_type in sorted(REQUIRED_FILE_TYPES):
        if required_type not in present_types:
            violations.append({
                "issue": "missing_required_file_type",
                "file_type": required_type,
            })
    return violations


def assess_delivery_package(package):
    """Full ECSS-E-ST-32C MMDD assessment for one delivery package.

    package: {
        "documents": [
            {
                "document_type": str,
                "document_id": str,
                "revision": str,
                "model_id": str,
                "model_revision": str,
                "author": str,
                "date": str,
            },
            ...
        ],
        "files": [{"file_type": str, ...}, ...]
    }

    Returns: {
        "completeness": [...],  # missing required document types
        "metadata": [...],      # per-document missing metadata fields
        "consistency": [...],   # model revision mismatches
        "file_delivery": [...], # missing required file types
    }

    Raises ValueError for unrecognized document types or documents
    that are missing model_revision during the consistency check.
    Does not mutate the input package.
    """
    documents = package.get("documents", [])
    files = package.get("files", [])
    completeness = check_document_completeness(documents)
    metadata = []
    for doc in documents:
        metadata.extend(check_metadata_fields(doc))
    consistency = check_revision_consistency(documents)
    file_delivery = check_file_delivery(files)
    return {
        "completeness": completeness,
        "metadata": metadata,
        "consistency": consistency,
        "file_delivery": file_delivery,
    }


def is_delivery_compliant(assessment):
    """True when all finding categories in an assess_delivery_package
    result are empty -- the package satisfies E-ST-32C MMDD delivery
    requirements for this check."""
    return all(len(findings) == 0 for findings in assessment.values())
