---
name: q60-class-2-buy-off-source-inspection
description: "Determine whether a final acceptance session held at the manufacturer releases a Class 2 EEE lot under ECSS-Q-ST-60C clause 5.3.6: settle first which shape the session took, on-site, remote, delegated or a package review standing in for a session, hold each shape to its own notice period and its own admissibility condition, test any delegate for independence from the line that built the parts, and cap the release at the pieces actually presented. Use when a session at the supplier has to become a ship-or-hold decision with a quantity attached. Trigger: ecss, q-st-60c-clause-5-3-6, class-2-source-buy-off, class-2-buy-off-mode-admissibility, class-2-delegate-independence-test, class-2-buy-off-notice-period, class-2-presented-quantity-release-cap."
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
  tags: [ecss, q-st-60c-eee-class-2-scope, q60-class-2-buy-off-source-inspection, class-2-source-buy-off, class-2-buy-off-mode-admissibility, class-2-delegate-independence-test, class-2-buy-off-notice-period, class-2-presented-quantity-release-cap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts -- Final Buy-Off At Source (space-systems/ecss/q60-class-2-buy-off-source-inspection)

Use when the task is the clause 5.3.6 buy-off of ECSS-Q-ST-60C: a Class 2 lot
is finished at the manufacturer, a final acceptance session has been held or
stood in for, and the question is whether the parts leave the premises and how
many of them do.

## Domain quick reference

- The shape of the session is the first question, not an afterthought. A Class 2
  buy-off may be held on-site, over a live remote link, by a delegated inspector
  or, where the manufacturer audit is current, replaced by a review of the
  acceptance data package. Each shape is a different promise.
- Each shape owes its own notice. Standing at the bench costs a journey and is
  called earliest; a package review is called latest. A session perfectly
  admissible on ten days of notice is not admissible on two, and the notice is
  counted in whole days from the call to the session.
- Delegation is worth something only when the delegate is independent. An
  inspector who reports into the line that built the parts is not standing in
  for the procuring entity, whatever the delegation letter says, so the
  reporting line is tested rather than the job title.
- Manufacturer staff are not a witness. Somebody has to be present who is the
  procuring entity or who is admissibly acting for it.
- A package review has no room and no witness, so it carries the whole weight
  itself: the audit has to be current and the package has to be complete, with
  no session at which a missing document could be raised.
- The release is capped three ways -- at the lot offered, at the pieces actually
  put in front of the inspection, and at what was asked for. Pieces nobody
  looked at stay at the manufacturer.

## Workflow

1. Normalise the declared mode and refuse a shape that is not one of the four,
   because the notice period and the admissibility condition both hang off it.
2. Count the whole days of advance notice from the call to the session, and
   compare them with what that mode owes rather than with a single figure.
3. Resolve the room: separate those who are the procuring entity from those
   acting for it, and test every delegate's reporting line against the build
   organisation before counting them.
4. Apply the mode's own condition -- a witness for the witnessed shapes, an
   independent inspector for the delegated shape, a current audit and a complete
   package for the review that replaces a session.
5. Check the acceptance data package for the documents the release sits on, and
   the activities that fed the buy-off for completion no later than the session.
6. Cap the release at the lot, at the pieces presented and at the quantity
   requested, then settle the disposition: hold on any blocking finding, a part
   lot when fewer pieces were presented than offered, otherwise the full lot.
7. Keep the reason a delegate was set aside even when somebody else witnessed,
   so a thin room reads as a thin room.

## Pitfalls

- Judging the session by its title. A meeting called a buy-off at which nobody
  independent of the manufacturer was present released nothing.
- Holding every mode to one notice period. A remote session called on six days
  is admissible; the same notice for an on-site session is not, and one figure
  across all four either blocks good sessions or waves through rushed ones.
- Accepting a delegation letter as independence. The letter names the delegate;
  the reporting line decides whether the delegation means anything.
- Letting a package review run on a stale audit. Without a current audit there
  is nothing standing behind a review that nobody attended.
- Releasing the lot offered rather than the lot presented. Pieces that were
  never put in front of the inspection have not been accepted, and shipping
  them turns a part-lot buy-off into an unverified full-lot release.
- Treating a set-aside delegate as nothing once another witness is found. The
  reason is still a finding about how thin the session was.

## Behavior contract (gate 3)

The mode normalisation, notice arithmetic, delegate independence test, room
resolution, package and prerequisite findings, the per-mode admissibility
condition and the release cap are exercised by the gate 3 contract test:
scripts/test_q60_class_2_buy_off_source_inspection.py against
scripts/q60_class_2_buy_off_source_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_buy_off_source_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
