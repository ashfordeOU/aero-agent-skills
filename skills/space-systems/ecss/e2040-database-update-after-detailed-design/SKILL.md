---
name: e2040-database-update-after-detailed-design
description: "Determine whether the device repository update ECSS-E-ST-20-40C 5.5.5 requires actually lets the following phase start: resolve every deposited item onto a recognised kind, state and dotted revision, keep only items released at or above the design baseline, and report the required inputs that are absent, the ones present but still draft or superseded, and the ones released against a design that no longer exists. Use when detailed design is depositing its outputs and the next phase has to build on them. Trigger: ecss, e-st-20-electrical-scope, database-update-after-detailed-design, device-repository-readiness, required-input-coverage, design-baseline-revision-check, superseded-deposit-detection, phase-handover-inputs."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-database-update-after-detailed-design, database-update-after-detailed-design, device-repository-readiness, required-input-coverage, design-baseline-revision-check, superseded-deposit-detection, phase-handover-inputs]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Detailed Design — Database Update (space-systems/ecss/e2040-database-update-after-detailed-design)

Use when the task is the repository duty of ECSS-E-ST-20-40C 5.5.5 --
saying whether detailed design has deposited into the device repository
everything the following phase needs, in a state that phase can build
against.

## Domain quick reference

- The repository is the hand-over surface between phases. It is judged by
  whether the following phase can start, not by how many items were
  deposited, so the required-input set of that phase is the frame for
  every check.
- Different following phases need different inputs. Layout needs the
  netlist, the constraints, the timing model and the design report;
  manufacturing needs the layout database and the pattern set;
  validation needs the benches, the models and the validation plan.
- An item is usable only when it is released. A draft reads as coverage
  in a deposit listing and cannot be built against, and a superseded item
  reads the same way while pointing at a design that has moved.
- A released item older than the design baseline is the hardest defect to
  see, because the item is perfectly valid -- for a device that no longer
  exists. Revisions are compared as integer tuples, so 2.10 sorts above
  2.9 rather than below it as text would have it.
- An item exactly at the baseline revision carries the baseline and
  counts. Revisions are compared exactly, never as decimal numbers.
- Integrity belongs with the deposit. An item with no checksum cannot be
  shown later to be the artefact it claimed to be.
- Deposits beyond the following phase's need are legitimate. They are
  listed, not faulted, so the readiness figure stays about the inputs
  that gate the phase.

## Workflow

1. Resolve the following phase and its required input kinds.
2. Resolve every deposited item: unique identifier, recognised kind, a
   dotted revision that parses, a deposit state and a checksum. Refuse a
   repeated identifier, an unknown key or a malformed revision.
3. Keep as usable only the items released at or above the design
   baseline, grouping them by kind.
4. Report each required kind with no usable item, separating the kind
   that is absent from the kind that is present but unusable.
5. Report every draft, superseded and behind-baseline item individually,
   and every item deposited with no integrity record.
6. Compute readiness as the fraction of required kinds satisfied, and
   compare it with the goal, absorbing an exact landing.
7. List the kinds deposited beyond the need without faulting them.

## Pitfalls

- Counting a deposit as coverage because the kind appears in the listing.
  A draft netlist and a released netlist look identical in a count, and
  only one of them can be built against.
- Comparing revisions as text or as decimal numbers. 2.10 then sorts
  below 2.9, and a repository that is ahead of the baseline reports as
  behind it.
- Treating an item exactly at the baseline as stale. It carries the
  baseline, and rejecting it stalls a hand-over that is correct.
- Letting superseded items stay invisible. They satisfy a kind in a naive
  grouping and point the following phase at a design that has moved.
- Faulting deposits the following phase does not need. They are normal,
  and treating them as defects buries the required inputs that are
  actually missing.

## Behavior contract (gate 3)

The kind, state and phase folding, dotted-revision parsing and
comparison, baseline filtering, required-input coverage, integrity
reporting and readiness comparison are exercised by the gate 3 contract
test: scripts/test_e2040_database_update_after_detailed_design.py against
scripts/e2040_database_update_after_detailed_design_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_database_update_after_detailed_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
