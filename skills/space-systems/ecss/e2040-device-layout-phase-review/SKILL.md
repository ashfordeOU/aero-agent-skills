---
name: e2040-device-layout-phase-review
description: "Evaluate readiness for the device layout phase review under ECSS-E-ST-20-40C clause 5.6.8, the gate that has to close before implementation and production begin. Use when the task is confirming every input the review needs is issued rather than drafted, that each one reached the participants far enough ahead of the meeting date to be read, that actions carried over from the detailed design gate are closed, and that the open review items fall inside the agreed severity disposition, then deriving a pass, pass-with-actions or repeat outcome with the blocking items named. Trigger: ecss, e-st-20-40c, device-layout-phase-review, layout-gate-entry-criteria, review-document-distribution-lead-time, carried-over-review-action, review-item-severity-disposition, layout-gate-outcome."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-layout-phase-review, device-layout-phase-review, layout-gate-entry-criteria, review-document-distribution-lead-time, review-item-severity-disposition, layout-gate-outcome]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Device Layout Phase Review (space-systems/ecss/e2040-device-layout-phase-review)

Use when the task is the layout gate of ECSS-E-ST-20-40C clause 5.6.8
-- deciding whether the review can be held at all, and what outcome the
evidence in front of it supports before implementation and production
work is allowed to start.

## Domain quick reference

- A gate has entry criteria and an outcome, and they are separate
  judgements. The entry criteria ask whether the review is holdable:
  the inputs exist, they are issued rather than drafted, and they
  reached the participants in time to be read. The outcome asks what
  the evidence supports once it has been read.
- Distribution lead time is an entry criterion with teeth. A document
  handed out in the meeting has not been reviewed; it has been seen. A
  lead time measured in working days before the review date is the
  check, and a late issue of an otherwise complete document is still a
  late issue.
- Issue status is not the same as existence. A draft on the table is a
  statement of intent, and the review cannot dispose of an item whose
  content can still change before it is signed.
- Actions carried over from the previous gate close at this one. A
  detailed-design action still open at the layout review means the
  phase just finished was run on an input that was known to be wrong.
- Open review items are disposed of by severity, not by count. A major
  item blocks; minor items are tolerated up to an agreed cap and only
  when each carries an owner and a close-out date. An undated minor is
  an unowned one and is treated as blocking.
- The outcome is one of three, and pass-with-actions is not a soft
  pass. It says the gate is closed and named work continues under
  agreed dates; it is unavailable when anything blocking is open.

## Workflow

1. Validate the review record: device identifier, review date as a day
   number on a working-day calendar, the required lead time, and the
   agreed cap on open minor items. Reject a negative lead time or cap.
2. Validate each required input: name, issue status, and the day it was
   distributed. Reject an unknown input name or an unknown status
   rather than counting it towards readiness.
3. Check entry criteria per input: absent, still in draft, or
   distributed fewer than the required working days before the review
   date, each its own finding. Compute the actual lead time so a near
   miss is visible as a number rather than a flag.
4. Check carried-over actions: any action raised at the previous gate
   whose status is not closed is a blocking finding, named with its
   identifier.
5. Categorize the open review items by severity and apply the
   disposition: any major item blocks; a minor item without an owner or
   a close-out date blocks; minor items above the agreed cap block.
6. Derive the outcome: repeat when an entry criterion fails or any
   blocking item is open, pass-with-actions when the gate is holdable
   and only dated, owned minor items remain within the cap, pass when
   nothing is open at all.
7. Report the outcome, the per-input lead times, the blocking items and
   the actions the outcome carries forward.

## Pitfalls

- Holding the review because the documents exist. Existence is not
  distribution, and a package issued the evening before produces a
  meeting where the only reviewer is the author.
- Treating a draft as good enough to dispose of. The content can still
  change after the gate, so the disposition is against a document that
  will not be the one implementation reads.
- Counting open items instead of grading them. One major and eleven
  minors is not better than twelve minors, and a pure count cannot
  tell the two apart.
- Accepting an undated minor item. Without a close-out date it is not
  an action, it is a note, and it will surface unchanged at the next
  gate.
- Carrying a detailed-design action past this gate to keep the schedule
  intact. The layout phase already consumed the input that action was
  raised against.

## Behavior contract (gate 3)

The entry-criteria evaluation, lead-time computation, carried-over
action check, severity disposition and three-way outcome derivation are
exercised by the gate 3 contract test:
scripts/test_e2040_device_layout_phase_review.py against
scripts/e2040_device_layout_phase_review_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_layout_phase_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
