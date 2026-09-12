---
name: structural-data-exchange
description: "Use when verify structural data exchange items among design, analysis, manufacturing, subsystem, and test disciplines per ECSS-E-ST-32C clause 4.9: categorize each data item by type (FEM model, CAD geometry, loads file, material card, test result), confirm every sender–receiver pair is authorized by an interface control document, validate that each item carries a version identifier and a traceable source document reference, and flag format mismatches against the allowed set for each item type. Trigger: ecss, e-st-32-structures-scope, structural-data-exchange, data-traceability, interface-control, fem-model, loads-exchange, material-card, icd."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, structural-data-exchange, data-traceability, interface-control, fem-model, loads-exchange, material-card, icd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Structural Data Exchange (space-systems/ecss/structural-data-exchange)

Use when the task is verifying structural data exchange packages under
ECSS-E-ST-32C clause 4.9 — categorizing data items by discipline type,
confirming interface control document authorization for each
sender–receiver pair, checking version and traceability of every item,
and flagging format non-conformances before the package is accepted.

## Domain quick reference

- Clause 4.9 covers the controlled exchange of structural engineering
  data among the following disciplines: design (CAD geometry, interface
  control documents), analysis (FEM models, loads files, material cards),
  manufacturing (material cards, process specifications), subsystems
  (interface loads, interface geometry), and test (test results,
  correlated models). Each data item belongs to at least one discipline
  group; an item with an unrecognized type is left uncategorized and
  must be resolved before the package is accepted.
- Every sender–receiver data flow must be authorized by an interface
  control document (ICD). An ICD entry identifies the sending
  organization, the receiving organization, and the agreed data scope.
  A data item flowing outside a declared ICD entry is unauthorized
  regardless of its content quality or completeness.
- Traceability requires each data item to carry three attributes: a
  unique item identifier, a version string, and a reference to the
  source document from which the item was derived or formally released.
  A missing or empty source document reference is a traceability gap,
  not a minor annotation — it breaks the change-management chain
  required by clause 4.9.
- Allowed formats are defined per data type. FEM models are exchanged
  in bulk-data formats (NASTRAN BDF, ABAQUS INP, ANSYS CDB) or neutral
  geometry (STEP). CAD geometry is exchanged in STEP, IGES, or
  established native formats. Loads files and material cards use
  structured text (CSV, TXT) or JSON. Test results use structured text
  or PDF. ICDs use PDF or DOCX. A data item delivered in an unlisted
  format is non-conformant regardless of readability.

## Workflow

1. Receive the data exchange package as a list of data items, each
   carrying: item_id, data_type, sender, receiver, format, version,
   and source_doc. Reject any item missing a required field before it
   enters further checks — partial items must not propagate.
2. Categorize each data item into one or more discipline groups (design,
   analysis, manufacturing, test) based on its data_type. Items with an
   unrecognized data_type are placed in the uncategorized group and
   flagged; they must be resolved or removed before the package can be
   accepted.
3. For each item, confirm that the (sender, receiver) pair appears in
   the declared ICD pair list. Items whose pair is absent are flagged as
   unauthorized; record the offending pair for ICD update or rejection.
4. Validate the format of each item against the allowed set for its
   data_type. A format not in the allowed list is a non-conformance;
   record the item_id, the submitted format, and the allowed formats for
   that type.
5. Check traceability: every item must have a non-empty version string
   and a non-empty source_doc reference. A blank or whitespace-only
   value in either field is a traceability gap, reported independently
   of other validation errors.
6. Build the traceability matrix from all items. Detect duplicate
   item_id values — two items sharing an identifier create an ambiguous
   traceability chain. Flag all duplicates; do not include them in the
   accepted matrix entry.
7. Aggregate findings per item and per package. The package is
   conformant only when all items pass field and format validation, all
   pairs are ICD-authorized, and the traceability matrix contains no
   duplicate identifiers.

## Pitfalls

- Accepting a data item without checking its sender–receiver pair
  against the ICD list — an item flowing between two teams with no ICD
  entry is not a minor administrative gap; it is an unauthorized
  interface and must be flagged before the data is used downstream.
- Treating a missing source_doc as a low-priority annotation — a blank
  source_doc means the item cannot be traced to a released document,
  which breaks the change-management chain required by clause 4.9 and
  makes later version audits impossible.
- Conflating format readability with format acceptance — a receiver may
  technically be able to open a non-listed format, but the exchange
  standard requires listed formats to ensure long-term retrievability
  and toolchain interoperability across the project lifecycle.
- Accepting a package with duplicate item_id values without flagging
  them — two items sharing an identifier make it impossible to determine
  which version a downstream analysis or manufacturing document is
  referencing.
- Silently dropping uncategorized items rather than flagging them — an
  item whose data_type is not recognized may represent a new data
  interface that has not been formally established; it must be resolved,
  not silently removed.

## Behavior contract (gate 3)

The item validation, ICD authorization, format check, traceability
matrix, and discipline categorization logic is exercised by the gate 3
contract test:
scripts/test_structural_data_exchange.py against
scripts/structural_data_exchange_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_structural_data_exchange.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
