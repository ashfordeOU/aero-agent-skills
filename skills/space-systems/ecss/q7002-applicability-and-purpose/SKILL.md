---
name: q7002-applicability-and-purpose
description: "Determine whether a candidate space material owes the thermal-vacuum outgassing screening of ECSS-Q-ST-70-02C and grade the result it returns: read applicability from material category, environment, exposed mass and the contamination-sensitive surfaces in view, reuse valid data for the same material in the same processed condition, then compare total mass loss and collected volatile condensable material against their limits and recover the total once regained water vapour is removed. Use when compiling a declared materials list, reviewing a supplier data sheet or dispositioning an outgassing report. Trigger: ecss, q-st-70-02c, outgassing-screening-applicability, outgassing-total-mass-loss, outgassing-collected-volatile-condensable, outgassing-recovered-mass-loss, declared-materials-list-screening."
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
  tags: [ecss, q-st-70-02c-outgassing-screening-test, q-st-70-02c, q7002-applicability-and-purpose, outgassing-screening-applicability, outgassing-total-mass-loss, outgassing-collected-volatile-condensable, outgassing-recovered-mass-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Applicability and Purpose (space-systems/ecss/q7002-applicability-and-purpose)

Use when the task is the scope clause of ECSS-Q-ST-70-02C: what the
thermal-vacuum outgassing screening test is for, which materials owe it, and
how the two quantities it returns are read.

## Domain quick reference

- The test is a screen, not a qualification. It separates materials that are
  obviously unsuitable for a vacuum environment from those worth carrying
  forward; a material that clears it has earned a place on the candidate list,
  not a clean bill for the specific application.
- Two quantities come out of one specimen and answer different questions.
  Total mass loss says how much of the material leaves; collected volatile
  condensable material says how much of what leaves will settle on a cold
  surface somewhere else. A material can be quiet and still deposit, or lose a
  lot and deposit almost nothing.
- Some of the mass loss is water the material had absorbed from the air and
  will not have in orbit. Recovering the total by the regained water vapour
  turns a laboratory artefact back into a flight-relevant figure, which is why
  a material over the total-loss limit is not automatically finished.
- The condensable limit does not have that escape. A material that deposits is
  going to deposit, and no water-regain argument changes the amount of it that
  settles on an optic, so a condensable failure ends the screen.
- Applicability is a property of the usage, not of the material. The same
  polymer owes the test on an externally mounted bracket and does not owe it
  sealed inside a pressurised volume, because the environment decides whether
  released volatiles can reach anything.
- A de-minimis mass keeps the list finite, and a sensitive surface removes it.
  A fraction of a gram of adhesive matters enormously when it is in view of a
  cryogenic detector and matters not at all when it is buried in a harness
  bundle.
- A screening result belongs to a material in a stated processed condition.
  The same resin cured on a different schedule is a different material for this
  purpose, so existing data is reused only when designation and cure state both
  match.

## Workflow

1. Read the usage: material category, environment, exposed mass, and the
   surfaces in view of the material. Applicability is decided from these, not
   from the trade name.
2. Set aside the categories with no organic volatile inventory, and treat a
   category on neither the screened nor the exempt list as screened until
   somebody places it on one.
3. Set aside environments that cannot carry released volatiles anywhere, and
   apply the de-minimis exposed mass only where no contamination-sensitive
   surface is in view.
4. Before booking a test, check for existing data on the same designation in
   the same processed condition, and reuse it where both match.
5. Where results exist, grade the condensable figure first: over its limit is
   the end of the screen. Then grade the total mass loss.
6. Where the total is over its limit but regained water vapour is reported,
   recover the total and grade the recovered figure, returning a conditional
   result that names the water-regain basis rather than a silent pass.
7. Close with a combined status: not required, owed, acceptable, acceptable
   with justification, or rejected.

## Pitfalls

- Reading the screen as a qualification. Clearing it says the material is worth
  carrying into the application-specific assessment; the contamination budget
  for the particular geometry and temperature is a separate calculation.
- Rescuing a condensable failure with the water-regain argument. The recovery
  applies to the total mass loss only, and applying it to the condensable
  figure passes exactly the materials that deposit on optics.
- Deciding applicability from the material rather than the usage. The same
  polymer owes the test in one fit and not in another, so an applicability
  answer with no environment and no exposed mass behind it is not an answer.
- Applying the de-minimis mass in front of a sensitive surface. Small
  quantities in view of a cold detector or a solar cell are exactly the ones
  contamination budgets are spent on.
- Reusing data across a cure change. The processed condition is part of the
  material's identity for this test, and a different cure schedule invalidates
  the reuse even when the designation is identical.
- Moving a limit to pass a result that lands exactly on it. The equality is a
  representation question handled by the tolerance inside the comparison; the
  acceptance figures stay as specified.

## Behavior contract (gate 3)

The applicability decision, category and environment sets, de-minimis and
sensitive-surface rule, existing-data reuse, recovered-mass-loss arithmetic and
the pass, conditional and fail verdicts are exercised by the gate 3 contract
test: scripts/test_q7002_applicability_and_purpose.py against
scripts/q7002_applicability_and_purpose_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7002_applicability_and_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
