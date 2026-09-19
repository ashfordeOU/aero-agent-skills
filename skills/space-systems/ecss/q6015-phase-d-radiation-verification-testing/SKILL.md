---
name: q6015-phase-d-radiation-verification-testing
description: "Evaluate the flight lot radiation verification campaign and the hardness assurance actions still open before a production milestone. Use when the ECSS-Q-ST-60-15C clause 4.4.4 phase D work has to be produced or graded: decide which delivered lots owe a verification test from the part category and whether heritage data on the same diffusion lot covers them, accept or reject each tested lot on its worst result over a sample as large as the category demands, and report every assurance action due by the qualification, production readiness or acceptance review that is not yet closed. Trigger: ecss, q-st-60-15c-clause-4-4-4, flight-lot-radiation-verification, radiation-lot-acceptance-test, diffusion-lot-heritage-coverage, radiation-part-category-sample-size, hardness-assurance-action-closure."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-phase-d-radiation-verification-testing, q-st-60-15c-clause-4-4-4, flight-lot-radiation-verification, radiation-lot-acceptance-test, diffusion-lot-heritage-coverage, radiation-part-category-sample-size, hardness-assurance-action-closure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Phase D Verification (space-systems/ecss/q6015-phase-d-radiation-verification-testing)

Use when the task is the production end of ECSS-Q-ST-60-15C clause 4.4.4 —
verifying that the parts actually delivered for flight behave like the parts
the frozen baseline assumed, and closing the hardness assurance actions the
qualification and production milestones depend on.

## Domain quick reference

- Phase D verifies material, not design. The design capability was settled at
  the freeze; what is in question now is whether this particular delivery of
  silicon matches it, because radiation response moves with the process run
  that made the parts.
- The unit of verification is the diffusion lot. Two deliveries of the same
  part reference from different lots are different populations, and a date
  code that happens to look adjacent proves nothing about the process. That is
  why heritage coverage is tested on the diffusion lot identity and the part
  reference together, and on nothing else.
- The part category decides two things at once: whether a verification test is
  owed regardless of heritage, and how many parts of the lot have to be
  consumed to produce the answer. A hard category owes the test even when
  heritage exists; a tolerant category owes it only when heritage does not.
- Lot acceptance reads the worst result, not the average. The purpose is to
  bound the lot, and one weak part in the sample is evidence about the lot,
  not an outlier to be trimmed.
- Sample size and margin are independent gates. A lot whose three tested parts
  are all excellent has not been verified if its category demanded ten, and
  reporting it as accepted on margin alone hides the shortfall.
- Milestone readiness is cumulative. An action due at an earlier review and
  still open is still open at every later one, so the closure check runs
  against the milestone being approached rather than against the action's own
  due date in isolation.

## Workflow

1. Normalise each flight lot's part reference, diffusion lot and category, and
   refuse a lot whose identity is incomplete rather than treating it as new
   material.
2. Decide whether the lot owes a verification test: mandatory by category, or
   forced because no heritage lot shares its diffusion lot.
3. Validate the test sample: every result positive, and the count at least the
   size the category demands.
4. Take the worst result, form the margin against the specified level, and
   accept an exact equality with the required margin through a named tolerance
   rather than relaxing the requirement.
5. Record sample sufficiency and margin separately so a rejection names the
   gate it failed, and sort the lot records by identity so two runs agree.
6. Grade the assurance actions against the milestone being approached — every
   action due at or before it and not closed is a blocker — and return
   milestone readiness only when no blocker remains.

## Pitfalls

- Accepting a flight lot on heritage from a different diffusion lot. The part
  reference and the date code can both match while the process run does not,
  and the earlier data then says nothing about the delivered material.
- Averaging the lot sample. The acceptance question is about the weakest part
  the lot can produce, so the minimum is the statistic and trimming it away
  removes the evidence.
- Treating a comfortable margin as compensation for a short sample. The two
  gates answer different questions, and passing one does not close the other.
- Reading an exempt lot as an untested risk. A tolerant-category lot with
  genuine heritage on its own diffusion lot is verified by that heritage; the
  record says so explicitly rather than leaving a silent gap.
- Checking only the actions whose due milestone is the one being held. Actions
  from earlier reviews do not expire, and a review held with an older action
  open is a review held on an incomplete baseline.

## Behavior contract (gate 3)

The category and milestone normalisation, diffusion-lot heritage coverage, the
verification-owed decision, the worst-result lot acceptance with its separate
sample-size gate, the action-closure grading and the campaign verdict are
exercised by the gate 3 contract test:
scripts/test_q6015_phase_d_radiation_verification_testing.py against
scripts/q6015_phase_d_radiation_verification_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_phase_d_radiation_verification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
