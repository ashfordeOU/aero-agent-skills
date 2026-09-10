#!/usr/bin/env python3
"""ECSS-E-ST-10C Annex D system engineering plan (SEP) DRD check (paraphrase).

Pure stdlib, no network. This module checks a produced System Engineering
Plan document against the document-requirements-definition (DRD) content
list of Annex D -- not the SEP maintenance/consistency logic of the sibling
e10-sep leaf. Common-knowledge summary (standards-map.yaml, ecss: gated
false): Annex D fixes the mandatory content blocks of the SEP (an
introduction and applicable/reference documents section, the project's
system engineering organisation and its interfaces to other project
functions, the system engineering process description, the system
engineering task list, and the SEP's linkage to the other documents it
plans/controls in the project's document tree), and this module verifies
each block is present, that every organisational interface is covered by
an assigned role, that every task has a known owner, and that every
document the SEP claims to plan or control actually exists in the
project's master document list.

A produced SEP document is a dict: section key -> section content string.
Organisation roles are a list of dicts with keys "role" (str) and
"interfaces" (list of organisation-interface tags). Tasks are a list of
dicts with keys "task_id" and "owner_role". DRD links are a list of
document identifiers the SEP claims to plan or control.
"""

REQUIRED_SEP_SECTIONS = [
    "introduction",
    "applicable-and-reference-documents",
    "se-organisation",
    "se-processes",
    "se-tasks",
    "drd-linkage",
]

ORG_INTERFACES = {
    "product-assurance",
    "aiv",
    "risk-management",
    "configuration-management",
    "software-engineering",
}


def missing_sections(document):
    """Return the required SEP sections that are absent or blank.

    document must be a dict mapping section key to section content
    (a non-empty string once stripped counts as present). Returns a list
    of REQUIRED_SEP_SECTIONS entries missing or blank, in the DRD's
    required content order. Raises ValueError if document is not a dict.
    """
    if not isinstance(document, dict):
        raise ValueError("document must be a dict, got %r" % (document,))
    missing = []
    for key in REQUIRED_SEP_SECTIONS:
        content = document.get(key)
        if not isinstance(content, str) or not content.strip():
            missing.append(key)
    return missing


def missing_organisation_interfaces(org_roles):
    """Return organisation interfaces not covered by any SEP role.

    org_roles must be a non-empty list of dicts, each with a "role" key
    (str) and an "interfaces" key (list of tags drawn from
    ORG_INTERFACES, case-insensitive). Returns a sorted list of
    ORG_INTERFACES entries no role covers. Raises ValueError for a
    malformed entry or an interface tag outside ORG_INTERFACES.
    """
    if not isinstance(org_roles, list) or not org_roles:
        raise ValueError("org_roles must be a non-empty list of role dicts")
    covered = set()
    for entry in org_roles:
        if (
            not isinstance(entry, dict)
            or "role" not in entry
            or "interfaces" not in entry
            or not isinstance(entry["interfaces"], list)
        ):
            raise ValueError(
                "each org_roles entry must be a dict with 'role' and "
                "'interfaces' (list), got %r" % (entry,)
            )
        for tag in entry["interfaces"]:
            key = tag.strip().lower() if isinstance(tag, str) else None
            if key not in ORG_INTERFACES:
                raise ValueError(
                    "unknown organisation interface %r; expected one of %s"
                    % (tag, ", ".join(sorted(ORG_INTERFACES)))
                )
            covered.add(key)
    return sorted(ORG_INTERFACES - covered)


def unowned_tasks(tasks, known_roles):
    """Return task_id values whose owner_role is not a known SEP role.

    tasks must be a non-empty list of dicts with "task_id" and
    "owner_role" keys. known_roles is an iterable of valid role names.
    Returns the offending task_id values in input order. Raises
    ValueError for a malformed task entry.
    """
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty list of task dicts")
    roles = set(known_roles)
    unowned = []
    for task in tasks:
        if (
            not isinstance(task, dict)
            or "task_id" not in task
            or "owner_role" not in task
        ):
            raise ValueError(
                "each task must be a dict with 'task_id' and 'owner_role', "
                "got %r" % (task,)
            )
        if task["owner_role"] not in roles:
            unowned.append(task["task_id"])
    return unowned


def dangling_drd_links(drd_links, project_document_list):
    """Return SEP-claimed document links absent from the project's documents.

    drd_links is the list of document identifiers the SEP claims to plan
    or control; project_document_list is the project's master document
    list (e.g. the Annex A delivery-schedule document set). Returns the
    drd_links entries not present in project_document_list, in input
    order (duplicates preserved). Raises ValueError if either argument
    is not a list.
    """
    if not isinstance(drd_links, list):
        raise ValueError("drd_links must be a list")
    if not isinstance(project_document_list, list):
        raise ValueError("project_document_list must be a list")
    known = set(project_document_list)
    return [link for link in drd_links if link not in known]


def sep_drd_compliance(document, org_roles, tasks, drd_links, project_document_list):
    """Build the aggregate SEP-per-DRD compliance verdict.

    Combines missing_sections, missing_organisation_interfaces,
    unowned_tasks (against the roles named in org_roles), and
    dangling_drd_links. Returns a dict with each violation list plus
    'status' ('sep-drd-compliant' when every list is empty, otherwise
    'sep-drd-non-compliant').
    """
    known_roles = {
        entry["role"]
        for entry in org_roles
        if isinstance(entry, dict) and "role" in entry
    }
    result = {
        "missing_sections": missing_sections(document),
        "missing_organisation_interfaces": missing_organisation_interfaces(
            org_roles
        ),
        "unowned_tasks": unowned_tasks(tasks, known_roles),
        "dangling_drd_links": dangling_drd_links(drd_links, project_document_list),
    }
    compliant = not any(result.values())
    result["status"] = "sep-drd-compliant" if compliant else "sep-drd-non-compliant"
    return result


if __name__ == "__main__":
    import doctest

    doctest.testmod()
