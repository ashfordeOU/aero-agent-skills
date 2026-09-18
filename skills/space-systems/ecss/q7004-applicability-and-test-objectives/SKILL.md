---
name: q7004-applicability-and-test-objectives
description: "Determine whether a thermal cycling or thermal vacuum campaign applies to an item and what objective it carries. Use when the ECSS-Q-ST-70-04C framework decision comes before any profile is written: read the cycling driver off the predicted temperature span and the vacuum driver off the operating pressure, separate a screening run that eliminates weak candidates from a qualification run that demonstrates capability, test an identical-item heritage claim against envelope, cycle count and process before accepting it, then size the specimen and cycle counts the objective demands. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-applicability-decision, screening-versus-qualification-objective, thermal-test-heritage-justification, predicted-thermal-environment-driver, thermal-test-campaign-sizing."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-applicability-and-test-objectives, thermal-test-applicability-decision, screening-versus-qualification-objective, thermal-test-heritage-justification, predicted-thermal-environment-driver, thermal-test-campaign-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Applicability and Test Objectives (space-systems/ecss/q7004-applicability-and-test-objectives)

Use when the task is the framework decision of ECSS-Q-ST-70-04C — whether a
thermal cycling or thermal vacuum campaign applies to this item at all, and,
if it does, what the campaign is for. Both answers come before a profile,
a specimen or a chamber booking.

## Domain quick reference

- Applicability is read off the environment, not off habit. The span between
  the predicted cold and hot extremes is the cyclic driver; below a declared
  span there is nothing for a cycling run to exercise. The pressure the item
  operates at is the vacuum driver, and a degradation mechanism that only
  appears once the surrounding gas is gone drives a vacuum run even for an
  item that lives at ambient pressure.
- The two drivers are independent. A narrow-span item in deep vacuum owes a
  vacuum run and no cycling run; a wide-span item inside a pressurized module
  owes the reverse. Reporting both as a single go or no-go loses that.
- Objective follows the programme phase. A screening run in development is a
  cheap elimination of weak candidates on few specimens over few cycles, and
  it demonstrates nothing. A qualification run demonstrates capability
  against the environment on the full specimen and cycle counts. An
  acceptance run verifies a delivered item against workmanship escapes.
- The objective, not the item, sizes the campaign. Specimen count and cycle
  count are read from the declared policy for the objective, so changing the
  objective changes both and a screening count carried into a qualification
  report is an unsupported claim.
- A heritage claim can retire a campaign, but only a complete one. An
  identical item qualified beyond this envelope with the heritage margin, for
  at least the cycle count this campaign needs, on the same manufacturing
  process. A shortfall in any one of the four returns the campaign.
- A similar item is not an identical item. Similarity supports a reduced
  screening set at best, and it never retires the qualification run.

## Workflow

1. Declare the item category, the programme phase, the heritage basis and the
   pressure environment. Reject an uncategorized value rather than defaulting
   it, because every downstream decision hangs on these four.
2. Compute the predicted span from the cold and hot extremes and compare it
   against the policy span threshold to settle the cycling driver. A span
   sitting exactly on the threshold counts as driving a run.
3. Settle the vacuum driver from the operating pressure and from any declared
   vacuum-sensitive mechanism, which drives a run on its own.
4. Test the heritage claim against all four conditions and collect the
   shortfalls. An empty shortfall list, and only that, retires the campaign.
5. Select the objective: the heritage result first, otherwise the programme
   phase. Record the rationale with the objective; an objective without one
   cannot be defended at the review.
6. Size the campaign from the objective, attach the duties the objective
   creates, and close with the drivers, the objective and the counts stated
   together so the test specification can be written from the result.

## Pitfalls

- Booking a cycling run because the item is flight hardware. The driver is
  the predicted span, and an item held within a few kelvin by its mounting
  has no cyclic driver to exercise however critical it is.
- Reading the vacuum driver off the mission rather than the item. An item
  inside a pressurized volume on a vacuum mission does not see vacuum, while
  an item at ambient pressure with a solvent-retaining process does.
- Reporting a screening result as evidence of capability. The specimen count
  and cycle count behind it were chosen to be cheap, so the result eliminates
  candidates and supports nothing else.
- Accepting a heritage claim on the envelope alone. The cycle count and the
  manufacturing process are two of the four conditions, and a process change
  breaks the claim even when the qualified envelope is far wider.
- Applying the heritage margin to the wrong side of the envelope. The cold
  extreme has to be qualified below the prediction and the hot extreme above
  it, so a claim that widens toward the prediction on one side only is short.
- Comparing the span against the threshold by bare arithmetic. A span built
  from two subtracted extremes can land a few units in the last place under a
  threshold it should meet; the comparison absorbs that representation error
  while the threshold itself stays untouched.

## Behavior contract (gate 3)

The span computation, cycling and vacuum driver decisions, heritage shortfall
collection, objective selection and campaign sizing are exercised by the gate
3 contract test:
scripts/test_q7004_applicability_and_test_objectives.py against
scripts/q7004_applicability_and_test_objectives_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7004_applicability_and_test_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
