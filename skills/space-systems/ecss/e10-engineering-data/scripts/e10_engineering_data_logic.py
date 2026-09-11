#!/usr/bin/env python3
"""ECSS-E-ST-10C clause 5.6.3 -- management of engineering data
(paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): an
engineering data item (drawing, specification, model, analysis, or
report) must carry a unique identifier consistent with the M-ST-40
configuration-management identification scheme (originator, type,
sequence number, revision) before it is stored in a controlled
repository; it must then be linked to a configuration baseline before
it is authorized for distribution, so that anyone receiving a data
item can trace it back to a controlled revision. This module scopes
only the identification / storage / configuration-link / distribution
control point -- it does not replace baseline-establishment mechanics
(sibling e10-config-baselines leaf, 10C clause 5.4.2.2) or engineering
change control (sibling e10-changes-nc leaf, 10C clause 5.6.9).
"""

DATA_ITEM_TYPES = ("drawing", "specification", "model", "analysis", "report", "dataset")

TYPE_CODES = {
    "drawing": "DRW",
    "specification": "SPC",
    "model": "MOD",
    "analysis": "ANL",
    "report": "RPT",
    "dataset": "DAT",
}

STATUSES = ("identified", "stored", "controlled", "distributed")


def parse_identifier(item_id):
    """Split an M-ST-40-consistent identifier of the form
    '<originator>-<type-code>-<number>-<revision>' (e.g.
    'ESA-DRW-0012-A') into a dict with keys originator, type_code,
    number, revision. Raises ValueError if item_id is empty, does not
    have exactly four hyphen-separated fields, has an unrecognized
    type_code, or has a non-digit number field."""
    if not item_id:
        raise ValueError("item_id must be non-empty")
    fields = item_id.split("-")
    if len(fields) != 4:
        raise ValueError(
            "item_id %r must have 4 hyphen-separated fields "
            "(originator-type-number-revision)" % (item_id,)
        )
    originator, type_code, number, revision = fields
    if not originator:
        raise ValueError("item_id %r has an empty originator field" % (item_id,))
    if type_code not in TYPE_CODES.values():
        raise ValueError(
            "item_id %r has type code %r, must be one of %r"
            % (item_id, type_code, sorted(TYPE_CODES.values()))
        )
    if not number.isdigit():
        raise ValueError("item_id %r has non-numeric number field %r" % (item_id, number))
    if not revision:
        raise ValueError("item_id %r has an empty revision field" % (item_id,))
    return {
        "originator": originator,
        "type_code": type_code,
        "number": number,
        "revision": revision,
    }


def identify_item(item_id, item_type, originator, revision, description):
    """Identify a new engineering data item and return a new register
    record (dict). Does not mutate any input. item_type must be one of
    DATA_ITEM_TYPES; item_id is parsed with parse_identifier and its
    originator, type code, and revision must match the item_type,
    originator, and revision arguments given, so the identifier and
    the declared metadata cannot silently disagree. description must
    be non-empty. The record starts with status='identified', not yet
    stored, not configuration-controlled, and with no distribution
    list."""
    if item_type not in DATA_ITEM_TYPES:
        raise ValueError("item_type must be one of %r: %r" % (DATA_ITEM_TYPES, item_type))
    if not description:
        raise ValueError("description must be non-empty")
    parsed = parse_identifier(item_id)
    if parsed["type_code"] != TYPE_CODES[item_type]:
        raise ValueError(
            "item_id %r has type code %r but item_type %r expects %r"
            % (item_id, parsed["type_code"], item_type, TYPE_CODES[item_type])
        )
    if parsed["originator"] != originator:
        raise ValueError(
            "item_id %r originator %r does not match declared originator %r"
            % (item_id, parsed["originator"], originator)
        )
    if parsed["revision"] != revision:
        raise ValueError(
            "item_id %r revision %r does not match declared revision %r"
            % (item_id, parsed["revision"], revision)
        )
    return {
        "item_id": item_id,
        "item_type": item_type,
        "originator": originator,
        "revision": revision,
        "description": description,
        "status": "identified",
        "storage_repository": None,
        "retention_years": None,
        "configuration_controlled": False,
        "baseline_id": None,
        "distribution_list": (),
    }


def assign_storage(record, repository, retention_years):
    """Return a new record placed in a controlled storage repository,
    with status set to 'stored'. Does not mutate record. Raises
    ValueError if the record is not in status 'identified', if
    repository is empty, or if retention_years is not a positive
    integer."""
    if record["status"] != "identified":
        raise ValueError(
            "item %r is %r, must be 'identified' to assign storage"
            % (record["item_id"], record["status"])
        )
    if not repository:
        raise ValueError("repository must be non-empty")
    if not isinstance(retention_years, int) or isinstance(retention_years, bool) or retention_years <= 0:
        raise ValueError("retention_years must be a positive integer: %r" % (retention_years,))
    updated = dict(record)
    updated["storage_repository"] = repository
    updated["retention_years"] = retention_years
    updated["status"] = "stored"
    return updated


def link_configuration(record, baseline_id):
    """Return a new record linked to a configuration baseline, with
    configuration_controlled=True and status set to 'controlled'. Does
    not mutate record. Raises ValueError if the record is not in
    status 'stored' or if baseline_id is empty, so an item cannot be
    linked to a baseline before it has a controlled storage location."""
    if record["status"] != "stored":
        raise ValueError(
            "item %r is %r, must be 'stored' to link a configuration baseline"
            % (record["item_id"], record["status"])
        )
    if not baseline_id:
        raise ValueError("baseline_id must be non-empty")
    updated = dict(record)
    updated["configuration_controlled"] = True
    updated["baseline_id"] = baseline_id
    updated["status"] = "controlled"
    return updated


def authorize_distribution(record, recipients):
    """Return a new record authorized for distribution, with
    distribution_list set and status set to 'distributed'. Does not
    mutate record or recipients. Raises ValueError if the record is
    not in status 'controlled' (identification, storage, and
    configuration linkage must all precede distribution), if
    recipients is empty, or if recipients contains a duplicate."""
    if record["status"] != "controlled":
        raise ValueError(
            "item %r is %r, must be 'controlled' before distribution"
            % (record["item_id"], record["status"])
        )
    recipients = tuple(recipients)
    if not recipients:
        raise ValueError("recipients must be non-empty")
    if len(set(recipients)) != len(recipients):
        raise ValueError("recipients must not contain duplicates: %r" % (recipients,))
    updated = dict(record)
    updated["distribution_list"] = recipients
    updated["status"] = "distributed"
    return updated


def may_distribute(record):
    """True when the item may be distributed: it is configuration-
    controlled (status 'controlled' or already 'distributed') --
    i.e. it has passed identification, storage, and configuration
    linkage."""
    return record["status"] in ("controlled", "distributed") and record["configuration_controlled"]


def register_status(records):
    """(ready, pending_items) across an engineering data register
    (iterable of records). ready is True only when every record has
    status 'distributed'. pending_items lists the not-yet-distributed
    records, in input order."""
    pending_items = [record for record in records if record["status"] != "distributed"]
    return (not pending_items, pending_items)


def items_missing_configuration_control(records):
    """Records that are stored but not yet linked to a configuration
    baseline (status 'stored'), in input order -- these are gaps: data
    already in a repository that clause 5.6.3 requires to be under
    configuration control before it can be distributed."""
    return [record for record in records if record["status"] == "stored"]


def items_by_type(records, item_type):
    """Records in the register of one item_type (member of
    DATA_ITEM_TYPES), in input order."""
    return [record for record in records if record["item_type"] == item_type]
