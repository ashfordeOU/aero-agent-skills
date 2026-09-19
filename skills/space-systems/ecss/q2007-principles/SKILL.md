---
name: q2007-principles
description: "Scope the quality and safety management of a space test centre on the principles of ECSS-Q-ST-20-07C clause 4, where assurance reaches the whole centre organization and every test service rather than the test run alone: take each centre function against both disciplines, refuse an exclusion on a core function whatever its rationale, demand a rationale and an accountable owner where an exclusion is admissible, keep subcontracted test services inside the centre's own scope, refuse an assurance line reporting into the operations it grades, and score the uncovered cells. Use when a test centre scope statement is written or audited. Trigger: ecss, q-st-20-07c, test-centre-assurance-scope, quality-and-safety-assurance-principles, test-service-scope-exclusion, subcontracted-test-service-scope, assurance-organizational-independence."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-principles, test-centre-assurance-scope, quality-and-safety-assurance-principles, test-service-scope-exclusion, subcontracted-test-service-scope, assurance-organizational-independence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre Quality And Safety Principles (space-systems/ecss/q2007-principles)

Use when the task is the clause 4 principles of ECSS-Q-ST-20-07C: a test
centre is writing or defending the scope of its quality and safety
assurance, and the question is whether that scope actually reaches the
organization and the services it sells.

## Domain quick reference

- The scope is the centre, not the test. A scope statement that covers test
  execution and stops there leaves calibration, maintenance, handling,
  documentation control and the training of the people who run the chamber
  outside assurance, and every one of those has ended a test campaign.
- Quality and safety are applied together, function by function. A function
  inside the quality scope and outside the safety scope is half covered,
  and scoring the two disciplines as separate cells is what makes that
  visible instead of averaging it away.
- Some functions cannot be excluded at all. Facility operations,
  calibration and metrology, and safety and emergency response are the
  centre's licence to operate, and a rationale against any of them is a
  rationale for not being a test centre.
- Where an exclusion is admissible it carries a rationale and an
  accountable owner. Both together are what makes it reviewable at the next
  audit; a rationale with nobody's name on it is a sentence.
- A subcontracted test service stays inside the centre's own scope. The
  supplier holding its own approval is the argument that is always made and
  it is the wrong one: the customer contracted the centre, and the centre
  answers for the service it resells.
- Independence is structural, not attitudinal. An assurance function
  reporting to the test operations manager or the facility manager grades
  its own line, and no amount of procedure compensates for that reporting
  line.
- A function nobody declared is not covered. An absent entry and a declared
  exclusion are different findings and the first is the more common one.

## Workflow

1. Normalise the declaration entry by entry: a recognised centre function,
   an explicit flag per discipline, and an optional owner and rationale;
   refuse a duplicated function and a blank rationale.
2. Report every centre function the declaration does not address at all,
   separately from the ones it addresses and excludes.
3. Refuse an exclusion on a core function whatever its rationale says.
4. On an admissible exclusion, demand both a rationale and an accountable
   owner before accepting it.
5. Apply the subcontracted-service rule independently, so a justified and
   owned exclusion there is still refused.
6. Check the assurance reporting line against the operations line it would
   otherwise grade.
7. Score the coverage over the quality and safety cells of every function,
   list the uncovered cells and return the verdict.

## Pitfalls

- Scoping the test and calling it the centre. The services around the test
  are where the campaign is lost, and they are what the principle names.
- Reporting one coverage number per function. Quality and safety are two
  cells and a function can be inside one and outside the other.
- Accepting an exclusion because it reads sensibly. The rationale plus a
  named owner is the reviewable form; either alone is not.
- Letting a supplier approval carry a subcontracted service out of scope.
  The centre resold the service and answers for it.
- Treating an undeclared function as covered by silence. Silence is the
  most common way a function leaves the scope, and it is the cheapest one
  to find.

## Behavior contract (gate 3)

The declaration normalisation, the undeclared-function reporting, the
core-function exclusion refusal, the rationale and owner rule, the
subcontracted-service rule, the reporting-line independence check and the
per-discipline coverage cells are exercised by the gate 3 contract test:
scripts/test_q2007_principles.py against scripts/q2007_principles_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q2007_principles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
