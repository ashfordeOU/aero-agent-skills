---
name: e2040-database-update-after-layout
description: "Audit the device repository update that closes the layout phase under ECSS-E-ST-20-40C clause 5.6.5. Use when the task is deciding which post-layout artefacts the repository owes before implementation can start, working out which of them are technology-dependent and therefore owed once per implementation technology, confirming each deposited item was produced by the layout run it claims and not by a superseded one, checking that every item carries a configuration identifier and an integrity digest, and reporting a delivered-over-owed completeness figure with the gaps named. Trigger: ecss, e-st-20-40c, device-layout-database-update, post-layout-netlist-deposit, layout-timing-data-deposit, layout-bitstream-deposit, per-technology-artefact-owing, superseded-layout-run, layout-artefact-integrity-digest."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-database-update-after-layout, device-layout-database-update, post-layout-netlist-deposit, layout-timing-data-deposit, per-technology-artefact-owing, superseded-layout-run]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Database Update After Layout (space-systems/ecss/e2040-database-update-after-layout)

Use when the task is the repository update of ECSS-E-ST-20-40C clause
5.6.5 -- deciding what the layout phase owes the device database, which
of those items are owed once per implementation technology, and whether
what was actually deposited is the output of the layout run that the
phase is closing on.

## Domain quick reference

- The database is not an archive of convenience; it is the input set
  the implementation phase reads. So the owed list is derived from what
  the next phase consumes -- the post-layout netlist, the extracted
  timing data that back-annotates it, the place-and-route record that
  explains how it was reached, and, for a programmable device, the
  configuration bitstream that will actually be loaded.
- Some items are properties of the design and some are properties of
  the implementation. A requirement trace or an architecture record is
  deposited once. A post-layout netlist, its timing extraction and its
  bitstream belong to one technology, so a device implemented on two
  technologies owes those items twice, once under each technology, and
  a single deposit covering both is a gap wearing a tick.
- Every deposit has to name the layout run that produced it. A layout
  is re-run whenever a constraint, a floorplan or a tool version moves,
  and an item carried over from the previous run is not merely old: it
  describes a device that no longer exists. The run identifier, not the
  timestamp alone, is what ties the item to the phase being closed.
- Configuration identity and integrity are separate obligations. A
  version label says which revision was intended; a digest says which
  bytes arrived. An item with a version and no digest cannot be shown
  to be the item the next phase later reads back.
- Completeness is reported as a fraction of what was owed, with the
  missing items named. A count of deposits on its own rises when the
  same artefact is deposited twice and says nothing about coverage.

## Workflow

1. Validate the device record: identifier, device kind, and a non-empty
   list of implementation technologies with no duplicates. Reject an
   unknown device kind or an empty technology list rather than assuming
   a single default technology.
2. Build the owed set: the design-wide items once, plus every
   technology-dependent item paired with each declared technology. A
   programmable device additionally owes its configuration bitstream
   per technology; a non-programmable one does not owe it at all.
3. Validate every deposited item: known kind, non-empty configuration
   identifier, a technology naming a declared technology when the kind
   is technology-dependent and no technology when it is not, a
   non-negative run sequence, and a digest string when one is claimed.
4. Match deposits to the owed set. An owed entry with no deposit is a
   gap; a deposit whose kind is outside the owed set is an unexpected
   item and is reported rather than silently counted.
5. Check each matched deposit against the closing layout run: a run
   sequence below the closing run is a superseded deposit, one above it
   is an out-of-phase deposit, and both are findings.
6. Check the configuration attributes: a missing identifier, a missing
   digest, or two deposits of the same kind and technology each carry
   their own finding.
7. Compute completeness as matched-and-clean entries over owed entries
   and report the fraction, the named gaps, the findings and whether
   the phase may proceed.

## Pitfalls

- Depositing one post-layout netlist for a dual-technology device. The
  owed list is per technology, and a single deposit leaves the second
  technology with no implementation input while the deposit count looks
  healthy.
- Accepting an item from the previous layout run because its content
  still parses. The re-run happened for a reason, and the carried-over
  timing extraction describes the floorplan that was replaced.
- Treating the bitstream as universally owed. A device that is not
  programmable has no configuration bitstream, and demanding one turns
  a complete repository into a permanent open finding.
- Recording a version label and calling the item controlled. Without a
  digest there is nothing to compare when the item is read back, and a
  silent substitution is indistinguishable from a correct read.
- Reporting the number of deposits instead of the fraction of the owed
  set. Duplicates inflate the first figure and leave the second one
  exactly where it was.

## Behavior contract (gate 3)

The owed-set construction, deposit validation, run-sequence matching,
per-technology pairing, duplicate detection and completeness
computation are exercised by the gate 3 contract test:
scripts/test_e2040_database_update_after_layout.py against
scripts/e2040_database_update_after_layout_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_database_update_after_layout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
