---
name: e10-engineering-data
description: "Use when manage a space project's engineering data items under ECSS-E-ST-10C clause 5.6.3 consistently with the ECSS-M-ST-40 configuration identification scheme: parse and check an item identifier against its declared type, originator and revision, place the item in a controlled repository with a retention period, link it to a configuration baseline before distribution is authorized, and report which items in the register are still short of configuration control. Trigger: ecss, e-st-10-system-scope, engineering-data, data-identification, m-st-40, configuration-control, controlled-storage, data-distribution, retention."
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
  tags: [ecss, e-st-10-system-scope, engineering-data, data-identification, configuration-control, controlled-storage, data-distribution]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Engineering Data Management (space-systems/ecss/e10-engineering-data)

Use when the task is to manage engineering data items under
ECSS-E-ST-10C clause 5.6.3 -- identification, controlled storage,
configuration linkage and authorized distribution -- with identifiers
consistent with the ECSS-M-ST-40 configuration-management scheme.

## Domain quick reference

- An identifier carries four fields: originator, type code, sequence
  number and revision. Parsing it is a check, not a formality -- a
  wrong field count, an unrecognized type code or a non-numeric
  sequence number is rejected at the point of identification.
- The identifier and the declared metadata must agree. An item whose
  identifier says one originator, type or revision while its record
  says another is rejected, because the whole point of the scheme is
  that the identifier alone locates the item.
- The lifecycle is a strict order: identified, then stored, then
  configuration-controlled, then distributed. Each transition requires
  the previous state, so an item cannot be linked to a baseline before
  it has a controlled storage location, and cannot be distributed
  before it is linked.
- Controlled storage takes a named repository and a positive retention
  period. A retention period of zero or a missing repository leaves
  the item outside configuration management, not loosely inside it.
- Distribution takes a non-empty recipient list with no duplicates. A
  duplicated recipient is an input error -- a distribution list is a
  set of parties, and a duplicate usually signals two merged lists.
- The transitions return new records rather than mutating the caller's
  -- the register's earlier states stay intact, which is what makes
  the item's history auditable.
- A stored item not yet linked to a baseline is the register's
  characteristic gap: data already in a repository that clause 5.6.3
  requires under configuration control before it may leave.

## Workflow

1. Parse each new item's identifier and confirm its originator, type
   code and revision match the declared metadata; reject on any
   mismatch or malformed field.
2. Register the identified item with its type and description.
3. Place the item in a named controlled repository with a positive
   retention period, moving it to stored.
4. Link the stored item to a configuration baseline, moving it to
   configuration-controlled.
5. Authorize distribution to a de-duplicated, non-empty recipient list
   only once the item is configuration-controlled.
6. Report register readiness: the items still pending distribution,
   and separately the stored items not yet under configuration
   control.

## Pitfalls

- Accepting an identifier that parses but contradicts the record's own
  type, originator or revision. The identifier is the index into the
  repository, so a silent disagreement makes the item unfindable by
  the very key it was issued under.
- Linking a baseline to an item that has not been stored yet. The
  baseline then points at data with no controlled location, and the
  ordering exists precisely to prevent that.
- Distributing an item that is stored but not baselined. The recipient
  cannot trace the copy back to a controlled revision, which is the
  failure mode clause 5.6.3 addresses.
- Mutating a register record in place across a transition, which
  destroys the prior state and with it the item's history.
- Treating a duplicated recipient as harmless. It normally means two
  distribution lists were merged, and the duplicate is the visible
  symptom of a list that was never reconciled.
- Reading "every item distributed" as the only register health check.
  Stored-but-uncontrolled items are a distinct gap and are reported
  separately.

## Behavior contract (gate 3)

The identifier parsing, identification, controlled-storage,
configuration-linkage, distribution-authorization, register-status and
gap-reporting logic is exercised by the gate 3 contract test:
scripts/test_e10_engineering_data.py against
scripts/e10_engineering_data_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_engineering_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
