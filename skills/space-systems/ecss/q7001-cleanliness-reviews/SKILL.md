---
name: q7001-cleanliness-reviews
description: "Assess the cleanliness status a programme has to put in front of a design or production readiness review under ECSS-Q-ST-70-01C. Use when the contamination data pack for a preliminary design, critical design, manufacturing readiness, test readiness or flight acceptance review is being assembled, or when a board has to decide whether contamination control is ready to let the next phase start: derive the items the review owes from its type and the contamination sensitivity of the hardware, compare them with what was submitted, weigh the open contamination actions by severity, and return a ready, conditional or not-ready verdict that names every missing item. Trigger: ecss, q-st-70-01c-cleanliness-scope, cleanliness-review-data-pack, contamination-control-readiness-review, design-review-cleanliness-input, contamination-open-action-severity, cleanliness-review-verdict, contamination-control-plan-maturity."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-cleanliness-reviews, cleanliness-review-data-pack, contamination-control-readiness-review, design-review-cleanliness-input, contamination-open-action-severity, cleanliness-review-verdict, contamination-control-plan-maturity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Status Inputs to Readiness Reviews (space-systems/ecss/q7001-cleanliness-reviews)

Use when the task is the review duty of ECSS-Q-ST-70-01C — deciding
what contamination control has to show at a design or production
readiness review, and whether what has been submitted lets the board
release the next phase.

## Domain quick reference

- A review is a gate on evidence, not a status briefing. The question
  is not whether contamination control is going well but whether the
  items this particular review depends on exist and say what they need
  to say.
- The data pack is a function of the review, not of the programme. A
  preliminary design review wants requirements, a budget and a plan; a
  test readiness review wants the facility, the monitoring set-up and
  the measurement the article entered with. Sending the same pack to
  both leaves each one short of the thing it actually gates.
- Contamination sensitivity widens the pack. Optics, cryogenic
  surfaces, detectors and propulsion feed systems carry effects that
  ordinary structure does not, so sensitive hardware additionally owes
  the sensitivity analysis and the end-of-life performance prediction.
- Items are mandatory or supporting, and the two do not trade. A
  missing mandatory item is a stop; a missing supporting item is an
  action. Averaging them into a completeness percentage hides which
  kind is absent.
- Open actions are weighted by severity, and a major carries a veto. A
  board that lets a major contamination action run past its own gate
  has moved the risk into a phase with less time to absorb it.
- The useful output names what is absent. A percentage tells the board
  how it feels; a list tells it what to ask for before it sits again.
- Conditional is a real verdict, not a softened pass. It says the gate
  opens once named, dated actions close, and it is only honest if
  those actions are listed.

## Workflow

1. Take the review type, the contamination sensitivity of the hardware
   and the submitted item list, and reject a case that cannot name the
   review rather than assuming one.
2. Derive the required pack: the items the review type owes, plus the
   items sensitive hardware adds, each carrying its mandatory or
   supporting status.
3. Compare the required pack with what was submitted, and separate the
   absentees into mandatory and supporting.
4. Categorize and count the open contamination actions by severity,
   and compute a weighted action load so several minors are visible
   next to one major.
5. Compute a completeness fraction over the mandatory items only, so
   the number cannot be inflated by supporting material.
6. Decide the verdict: not-ready while a mandatory item is absent or a
   major action is open; conditional while supporting items or minor
   actions remain; ready only when both are clear.
7. Report the missing items and the open actions together, so one
   board sitting can clear them all.

## Pitfalls

- Sending one data pack to every review. Each gate depends on
  different evidence, and a pack built for the last review is missing
  exactly the item this one exists to check.
- Treating the contamination control plan as sufficient at every gate.
  The plan is what the programme intends; from the manufacturing
  readiness review onwards the board also needs what the facility and
  the hardware have actually done.
- Trading a missing mandatory item against a rich set of supporting
  material. A pack can be thick and still be missing the one document
  the gate is about.
- Carrying a major contamination action through the gate on a promise.
  The later the action closes, the less able the programme is to act
  on what it finds.
- Omitting the sensitivity analysis for optical or cryogenic hardware
  because the general budget looks comfortable. The budget is an areal
  figure; the sensitivity analysis is what turns it into a performance
  loss, and only one of the two answers the board's question.
- Reporting completeness as a single percentage. Two packs at the same
  percentage can be in entirely different states, and the one missing
  a mandatory item is not ready at any percentage.

## Behavior contract (gate 3)

Pack derivation, sensitivity extension, mandatory and supporting
separation, action weighting, mandatory completeness and the review
verdict are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_reviews.py against
scripts/q7001_cleanliness_reviews_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7001_cleanliness_reviews.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
