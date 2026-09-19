---
name: q7040-braze-acceptance-criteria
description: "Assess a brazement's fill, void and defect measurements against the acceptance limits the joint class carries. Use when an inspection has produced a filled area, a largest single void, a continuous void run, an indication count and a defect list, and the joint has to be accepted or rejected with a reason attached. Converts measured areas into a fill fraction, grades every criterion in the right direction, treats a value sitting exactly on a limit as acceptable, rejects a crack in any class whatever the fill, and names the criterion whose margin is thinnest so rework knows what to chase. Trigger: ecss, q-st-70-40-brazing-scope, braze-acceptance-criteria, braze-fill-fraction, braze-single-void-limit, braze-linear-void-run, braze-indication-count, braze-crack-rejection."
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
  tags: [ecss, q-st-70-40-brazing-scope, q7040-braze-acceptance-criteria, braze-fill-fraction, braze-single-void-limit, braze-linear-void-run, braze-indication-count, braze-crack-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Braze Acceptance Criteria (space-systems/ecss/q7040-braze-acceptance-criteria)

Use when the task is the acceptance step for a brazed joint -- reading
the inspection measurements against the limits the joint class sets on
fill, on voids and on defect types, and issuing an accept or reject
with the binding criterion named.

## Domain quick reference

- Acceptance is a set of criteria, not a single number. A joint can
  reach its fill fraction and still be rejected on a single void that
  sits in the load path, on a continuous void run that acts as a
  crack starter, or on the sheer count of indications; every
  criterion has to be read before anything is accepted.
- The criteria point in two directions and the comparison has to know
  which. Fill is a floor to be reached; voids, void runs and
  indication counts are ceilings not to be exceeded. Grading a floor
  with a ceiling test is how a badly filled joint passes.
- Total void area and largest single void are not the same criterion.
  Ten small voids scattered over the overlap and one void of the same
  total area behave completely differently under load, so the class
  limits both, and a joint can fail either one alone.
- A continuous void run along the joint is worse than its area
  suggests. It presents an unbonded line the length of the run, which
  is a crack of that length as far as the joint is concerned, so the
  limit is set on the run itself and not on the area it happens to
  occupy.
- Some defects are not gradeable. A crack is rejected in every class
  whatever the fill fraction says, because its limit is not a size
  but its existence. A disbond at the loaded edge of an overlap is
  the same for the structural classes.
- A value sitting exactly on a limit is acceptable. Fill fractions and
  void fractions are quotients of measured areas and lengths, so a
  measurement placed deliberately on a limit can land a few units in
  the last place on the wrong side of it, and the comparison absorbs
  that while the limit itself stays untouched.
- The reject has to be actionable. Naming the criterion with the
  thinnest relative margin tells rework whether to chase the flow,
  the fixture, the gap or the cleaning, so the binding criterion
  travels with the verdict.

## Workflow

1. Normalise the measurement set: joint area and voided area, or a
   fill fraction directly; the largest single void and the longest
   continuous run as fractions; the indication count; the defect type
   list. Reject an impossible combination rather than grading it.
2. Look up the limits the joint class sets and keep the direction of
   each criterion with it.
3. Where raw areas were supplied, compute the fill fraction from them
   rather than trusting a separately quoted figure.
4. Grade every criterion, recording the measured value, the limit, the
   verdict and the relative margin.
5. Apply the defect rules that are not gradeable: a crack rejects in
   every class, and a loaded-edge disbond rejects in the structural
   classes.
6. Issue accept or reject, name the binding criterion, and return the
   full criterion table so the reject can be worked or the accept can
   be evidenced.

## Pitfalls

- Reporting fill fraction and stopping. Fill is the criterion easiest
  to measure and the one least able on its own to say whether the
  joint carries load; a ninety-five percent filled joint with the
  missing five percent in one run at the loaded edge is worse than an
  evenly ninety percent filled one.
- Grading a fill fraction as though it were a ceiling. Reversing the
  direction of one criterion turns the worst joints in the lot into
  the ones that pass, and nothing in the report looks wrong.
- Quoting a fill fraction that was not computed from the areas
  actually measured. A separately entered figure drifts from the
  areas on the inspection record, and the two disagree only when
  somebody rechecks a reject.
- Accepting a crack because the fill fraction is high. A crack has no
  size limit to be within; it is rejected on existence, and a joint
  that grades cleanly on every measured criterion is still a reject
  once one is reported.
- Comparing a measured fraction with its limit by bare arithmetic. The
  fraction is a quotient of measured areas, so a joint deliberately
  built to the limit can read a few units in the last place outside
  it and be scrapped on representation error.

## Behavior contract (gate 3)

Measurement normalisation, fill computation from areas, the direction
of each criterion, the exact-limit case, the non-gradeable defect rules
and the binding-criterion selection are exercised by the gate 3
contract test: scripts/test_q7040_braze_acceptance_criteria.py against
scripts/q7040_braze_acceptance_criteria_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7040_braze_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
