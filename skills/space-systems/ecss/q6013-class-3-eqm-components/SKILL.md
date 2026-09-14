---
name: q6013-class-3-eqm-components
description: "Evaluate the candidate parts offered for an engineering qualification model slot at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.1.6: rule out a candidate whose function or pinout differs, because the model would then exercise a different design, rule out one that cannot arrive inside the build window, weight the remaining build-standard differences into a match fraction, take the best with a reproducible tie-break on lead time and reference, and name the deltas the flight build must carry on the record. Use when a model parts list or a substitution request is decided at the lowest class. Trigger: ecss, q-st-60-13c-clause-6-1-6, class-three-eqm-part-choice, eqm-candidate-admissibility, eqm-build-window-feasibility, eqm-build-standard-match-fraction, eqm-flight-build-delta-record."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-eqm-components, class-three-eqm-part-choice, eqm-candidate-admissibility, eqm-build-window-feasibility, eqm-build-standard-match-fraction, eqm-flight-build-delta-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Engineering Qualification Model Components (space-systems/ecss/q6013-class-3-eqm-components)

Use when the task is clause 6.1.6 of ECSS-Q-ST-60-13C at the lowest assurance
class: which commercial component to fit in an engineering qualification model
slot when several are available and none is the ideal one. This leaf decides
the slot, and records what the choice obliges the flight build to carry.

## Domain quick reference

- The lowest class widens what may be fitted; it does not change what the
  model is for. The model exists to exercise the design, so a candidate that
  changes the function or the pinout is not a lower-assurance version of the
  part, it is a different circuit, and no weighting recovers that.
- A candidate that cannot arrive before the model is built is not a candidate.
  Lead time belongs in the admissibility test, not in a footnote under the
  preferred choice, because a slot filled on paper and empty on the bench is
  the same as no decision at all.
- The differences that remain are real but rankable. Package, operating range,
  source, assurance level and assembly process each remove a share of the
  match, and the share is what lets two imperfect candidates be compared
  without arguing about which imperfection feels worse.
- The match fraction is a ranking device. What the programme actually plans
  against is the delta list: a package change obliges a mechanical interface
  record, a source change obliges a supply source record, and those records
  are what the flight build inherits.
- The intended part, when available inside the window, always wins. Building
  the argument for a substitution before checking whether the real part could
  simply have been ordered is the most common way a model acquires a delta it
  never needed.
- A tie has to break the same way twice. Lead time first, then the reference,
  so two reviewers reading the same list reach the same slot decision.

## Workflow

1. Validate the slot: the flight-intended part, the candidates offered and the
   window inside which the model has to be built.
2. Validate the weight set, refusing a hard attribute as a weighted one and
   refusing any attribute with no declared delta record.
3. Compare each candidate against the intended part on function and pinout,
   and rule out a candidate that differs on either.
4. Rule out a candidate whose lead time falls outside the build window,
   reporting the two rejection reasons separately so the slot's real problem
   is visible.
5. Compare the remaining candidates on the weighted build-standard attributes
   and form each match fraction from the differences.
6. Rank the admissible candidates on match, then lead time, then reference,
   and take the first.
7. Compare the chosen match with the declared floor through a named tolerance
   rather than by moving the floor.
8. Return the ranked references, the chosen candidate, the build-standard
   deltas, the records the flight build inherits, ranked findings and one
   verdict: intended part fitted, substitution recorded, or escalate.

## Pitfalls

- Treating a function or pinout change as a large deduction. It is not a
  deduction at all; the model would demonstrate something the flight build
  does not contain, and a high score on the remaining attributes hides that.
- Leaving availability out of admissibility. A candidate that arrives after
  the model is built cannot be chosen, and ranking it first wastes the review.
- Reading the match fraction as the decision. The fraction orders candidates;
  the delta list is what the flight build has to carry and what the programme
  plans against.
- Arguing a substitution before checking the intended part. When the real part
  is procurable inside the window it wins, and the delta never has to exist.
- Letting a tie break on whatever the list order happened to be. Two reviewers
  must reach the same slot, which needs the tie-break written down.
- Deciding the slot and never writing the delta down. A model built from a
  substitution nobody recorded is a build standard the flight programme cannot
  reconstruct.

## Behavior contract (gate 3)

The slot validation, hard-attribute and build-window admissibility tests,
weighted match fraction, ranking and tie-break, floor comparison, delta record
mapping and slot verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_eqm_components.py against
scripts/q6013_class_3_eqm_components_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6013_class_3_eqm_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
