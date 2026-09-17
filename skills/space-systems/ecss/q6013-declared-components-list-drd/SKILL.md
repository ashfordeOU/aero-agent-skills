---
name: q6013-declared-components-list-drd
description: "Verify that a declared components list meets the entry structure its data item fixes under ECSS-Q-ST-60-13C Annex B. Use when a commercial-parts programme submits its list and a reviewer must decide whether every line can be traced, procured and accepted: refuse a list with no reference, issue or entries, check each line carries a part identifier, manufacturer, grade, procurement route, radiation evidence and an application reference, catch a part number declared twice under a different part, group the lines by approval state, and report the share complete enough to submit. Trigger: ecss, q-st-60-13c-annex-b, declared-components-list-drd, declared-components-list-entry-completeness, declared-components-list-duplicate-part-conflict, declared-components-list-approval-state, commercial-part-broker-procurement-justification."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-declared-components-list-drd, declared-components-list-entry-completeness, declared-components-list-duplicate-part-conflict, declared-components-list-approval-state, commercial-part-broker-procurement-justification, commercial-part-radiation-evidence-entry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components — Declared Components List DRD (space-systems/ecss/q6013-declared-components-list-drd)

Use when the task is the Annex B data item of ECSS-Q-ST-60-13C: a
declared components list has been issued for a programme buying parts
from the commercial market, and the question is whether the list is
built the way the data item requires, line by line.

## Domain quick reference

- The list is the one place where the project, the customer and the
  supplier look at the same part. Its structure is therefore fixed: a
  part identifier, a manufacturer, a quality grade, a procurement route,
  a radiation evidence reference and an application reference on every
  line, so that a reader can take any line back to a purchase order and
  forward to a circuit.
- A line missing any of those fields is incomplete however confident its
  approval column looks. Completeness is taken as the share of lines
  carrying every field, and the incomplete lines are named by their part
  identifier, or by position when even that is blank.
- A part number declared twice under different data is worse than a part
  number declared once badly. Two lines with the same identifier but a
  different manufacturer or grade mean two different parts are being
  bought under one name, and no later audit can separate them; an
  identical repeat of the same line is not that, and is not a finding.
- Approval state is a grouping, not a score. Approved, conditionally
  approved, pending and rejected lines are counted apart, so a list that
  is complete and entirely pending is not read as a finished list. A
  conditional approval passes with an advisory naming the condition
  still to be closed.
- Radiation evidence and the broker route are the two commercial-market
  risks the list makes visible. A part in a radiation environment with
  no evidence reference, and a part bought from an independent broker
  with no justification recorded, each stop the list rather than
  lowering a percentage.

## Workflow

1. Validate the data-item policy first: the minimum entry completeness,
   the pending share the list may still carry, and whether rejected
   entries, missing radiation evidence and unjustified broker purchases
   are tolerated. A completeness floor or pending share outside zero to
   one is refused rather than clamped.
2. Validate the list identity: a non-blank list reference and a non-blank
   issue label. An absent list, one with a blank reference or issue, or
   one carrying no entries at all, closes the assessment on list not
   established.
3. Validate every entry: the six required fields read as strings that may
   be blank but are then absent, a recognised quality grade and
   procurement route when either is given, a recognised approval state,
   a boolean radiation-environment flag and an optional broker
   justification. An unrecognised grade, route or state is an input
   error, not a new category.
4. Take the completeness as the share of lines carrying every required
   field and name the incomplete lines in full.
5. Walk the identifiers once, keeping the manufacturer and grade each was
   first declared under, and report an identifier whose later line
   disagrees with that signature.
6. Group the lines by approval state, take the pending share, and collect
   the exposed lines with no radiation evidence and the broker purchases
   with no justification.
7. Close on one verdict in order: list not established, entry
   completeness short, duplicate part conflict, radiation evidence
   missing, broker route unjustified, approval state outstanding, or list
   satisfies the data item. Report the counts, the completeness, the
   grouping and every named line alongside it.

## Pitfalls

- Reading a high completeness as a finished list. Completeness measures
  the fields, not the decisions; a list where every field is filled and
  every line is pending has not yet let anybody buy anything.
- Treating an identical repeat as a duplicate finding. The same part
  declared twice under the same manufacturer and grade is a tidiness
  matter; the finding is the identifier whose data disagrees with
  itself.
- Dropping a line with no part identifier. It still has to be reported,
  named by its position, or the one line nobody can trace is the one
  line that leaves the assessment.
- Averaging the radiation evidence away. An exposed part with no
  evidence is the risk the standard exists to manage, so it stops the
  list rather than moving a percentage.
- Reporting a bare verdict. The completeness, the pending share and the
  named lines are what the next issue of the list is compared against,
  and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, list identity validation, entry validation, the
completeness and its named lines, the duplicate-identifier walk, the
approval-state grouping and pending share, the radiation-evidence and
broker-justification findings and the list verdict are exercised by the
gate 3 contract test:
scripts/test_q6013_declared_components_list_drd.py against
scripts/q6013_declared_components_list_drd_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_declared_components_list_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
