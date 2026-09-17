---
name: q60-class-3-quality-control-general
description: "Map the control measures a received Class 3 EEE lot owes into one resolved route, under clause 6.5.1 of ECSS-Q-ST-60C: derive the activities from the lot profile with the ones every lot owes held apart from attribute-driven ones, close the set over its prerequisites so a triggered activity never depends on a missing one, resolve a deterministic order, admit an omission only where a justification names a reference and an approver, report an activity recorded closed while something it depends on is open, and weight completeness so a heavy step left open is not offset by light ones. Use when a received lot has to become a release decision. Trigger: ecss, q-st-60c-clause-6-5-1, q60-c3-post-receipt-control-route, q60-c3-control-prerequisite-closure, q60-c3-control-omission-justification, q60-c3-out-of-order-closure-breach, q60-c3-weighted-route-completeness."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c-clause-6-5-1, q60-class-3-quality-control-general, q60-c3-post-receipt-control-route, q60-c3-control-prerequisite-closure, q60-c3-control-omission-justification, q60-c3-out-of-order-closure-breach, q60-c3-weighted-route-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Post-Receipt Quality Control Route (space-systems/ecss/q60-class-3-quality-control-general)

Use when the task is clause 6.5.1 of ECSS-Q-ST-60C: the entry point to the
control measures a Class 3 lot is put through once it has been received. This
clause opens onto the rest of the control section rather than prescribing one
test, so the leaf's job is to turn a lot profile into the route that lot owes,
in the order it owes it, and to say what the closure records let it do next.

## Domain quick reference

- An entry-point clause is a router, not a test. Its output is which measures
  apply to this lot, in what order, and on what evidence they may be skipped —
  and getting that wrong costs more than getting any single measure wrong.
- The route is grouped in two. A short set is owed by every received lot; the
  rest are brought in by an attribute of the part or of the delivery. Treating
  the second group as a menu is how a lot reaches stores with a gap in it.
- Prerequisites are not advice about scheduling. A destructive analysis on parts
  that have not had an external examination is a destructive analysis of
  unknown parts, so the order carries the meaning, not just the sequence.
- A triggered activity can depend on one the profile never triggered. Electrical
  verification of a lot presupposes the lot is one lot; if nothing established
  that, the route has to pull the homogeneity check in rather than fail.
- The order has to be reproducible. Two people resolving the same profile must
  get the same route, so ties among ready activities are broken by name rather
  than by whatever order the records happened to arrive in.
- An omission is a record, not a decision. Attribute-driven measures can be
  dropped where a reference and a named approver exist; a mandatory one cannot
  be dropped at all, and neither can one the rest of the route depends on.
- Closed out of order is not closed. A record showing a later activity complete
  while its prerequisite is open means one of the two records is wrong, and the
  lot stays where it is until that is resolved.
- Completeness is weighted. Four light activities closed and a destructive
  analysis open is not eighty per cent done, and a plain count reports it as if
  it were.

## Workflow

1. Validate the lot profile and derive the owed activities: the mandatory set
   plus everything an attribute brings in.
2. Close that set over its prerequisites, and report each activity pulled in
   that way so the route explains itself.
3. Resolve the closed set into dependency order by a deterministic pass that
   refuses a cycle and refuses a prerequisite missing from the route.
4. Test each requested omission: the activity must be attribute-driven, the
   justification must carry a reference and an approver, and nothing still in
   the route may depend on it.
5. Read the closure records against the route and report any activity recorded
   as closed while something it depends on is not.
6. Take the weighted completeness over the route, separating what is open from
   what was done and failed.
7. Return the release decision: to stores, pending an attribute-driven item,
   held in quarantine, or rejected, with every reason named.

## Pitfalls

- Reading the entry-point clause as a formality and going straight to the
  individual measures. The route is the deliverable this clause owes.
- Treating attribute-driven measures as optional. They are conditional on the
  part, not on the schedule, and a lot with the attribute owes them outright.
- Resolving the route by hand from the order the records arrived in. The
  arrival order reflects who was free that week, not what depends on what.
- Failing a route because a prerequisite was not triggered. Pull it in and say
  so; refusing to resolve leaves the receiving team with no route at all.
- Accepting an omission with a justification that names nobody. An unapproved
  reference is a note, and it will not be there when the lot is questioned.
- Reading an out-of-order closure as a paperwork slip. One of the two records is
  wrong, and which one it is changes what the lot actually is.
- Reporting completeness as a count of closed activities. The weighting is what
  keeps a heavy open item visible behind several light closed ones.

## Behavior contract (gate 3)

The applicability derivation, prerequisite closure, deterministic route
resolution, cycle and missing-prerequisite refusal, omission admissibility,
out-of-order closure detection, weighted completeness and the release decision
are exercised by the gate 3 contract test:
scripts/test_q60_class_3_quality_control_general.py against
scripts/q60_class_3_quality_control_general_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_quality_control_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
