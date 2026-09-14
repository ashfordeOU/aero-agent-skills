---
name: q6013-class-2-screening-requirements
description: "Evaluate whether a purchased date-code lot of a commercial EEE part was screened as the intermediate assurance class requires under ECSS-Q-ST-60-13C clause 5.3.3: refuse a screen run on a sample instead of on every unit, take the screen set the package family demands, name each screen absent from the performed sequence, report an inverted order even when every screen is present, accumulate the removed units into a percent defective, hold burn-in to its own subtotal, and reject the whole lot rather than only its removed units once the allowance is passed. Use when screening results have to become a lot verdict. Trigger: ecss, q-st-60-13c-clause-5-3-3, class-two-commercial-eee-screening, hundred-percent-screen-coverage, package-family-screen-set, screening-sequence-order-check, cumulative-screening-percent-defective, burn-in-removal-subtotal, screened-lot-marginal-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-screening-requirements, class-two-commercial-eee-screening, hundred-percent-screen-coverage, package-family-screen-set, screening-sequence-order-check, cumulative-screening-percent-defective, burn-in-removal-subtotal, screened-lot-marginal-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Screening Requirements (space-systems/ecss/q6013-class-2-screening-requirements)

Use when the task is the clause 5.3.3 screening question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a date code of a
commercial part has been through a screening sequence whose job is to
remove the weak units, and the question is whether the survivors may be
offered for assembly.

## Domain quick reference

- Screening is a removal operation, not a sample plan. Every unit of the
  lot goes through every screen, because the point is to take the weak
  units out of the population, not to estimate how many there are. A
  sequence run on a sample has not screened the lot at all, and that is
  an input error rather than a partial result to be scaled up.
- The screen set follows the package family. A cavity package carries
  seal and particle screens that a solid-encapsulated package cannot
  carry; a solid-encapsulated package carries a moisture precondition
  that a cavity package does not need. Judging one family against the
  other's set produces findings that mean nothing.
- The sequence has an order, and the order is part of the requirement.
  Burn-in end points read the units after burn-in, the final electrical
  test closes the electrical evidence, and the external visual is the
  last thing done to the lot. A present-but-misordered sequence is a
  finding, because a screen run out of place did not see the stress it
  was placed after.
- Two allowances sit on the same removals. The cumulative percent
  defective judges the whole sequence; burn-in carries its own subtotal
  because infant mortality is the failure burn-in exists to expose, and
  pooling it with the visual screens lets a clean visual dilute it.
- Passing the allowance rejects the lot, not only the units removed. The
  removals are evidence about the population left behind: a lot that
  shed a tenth of itself is telling you what the survivors are, and
  shipping the remainder keeps exactly that population.

## Workflow

1. Confirm the screened count equals the lot size, and refuse a sequence
   offered on a sample rather than scaling its result to the lot.
2. Resolve the package family, take its ordered screen set, and name
   every required screen the performed sequence does not carry.
3. Check the relative position of the screens present, reporting an
   inverted pair and an external visual that does not close the run.
4. Validate the removals against the lot -- a negative count, or
   removals totalling more than the lot, is an input error -- and refuse
   a removal naming a screen the family's set does not carry.
5. Accumulate the removals into a cumulative percent defective and a
   burn-in subtotal, comparing each with its allowance and absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by widening the allowance.
6. Release the survivors only when no screen is absent, no screen is out
   of order, both allowances hold and the lot was not made up to size
   from another date code; otherwise reject the lot and report every
   finding, with a marginal advisory where an accepted lot has used up
   most of its allowance.

## Pitfalls

- Screening a sample and scaling the result. The removed units are the
  deliverable of a screen; a sample tells you a rate and leaves the weak
  units in the lot you are about to ship.
- Pooling burn-in into the cumulative percentage. A large clean visual
  screen buries an infant-mortality population, which is the one thing
  the burn-in subtotal exists to surface.
- Accepting a misordered sequence because every screen is present. End
  points read before burn-in measured a part that had not yet seen the
  stress, so the reading is not evidence about the screened lot.
- Removing the rejects and shipping the remainder after the allowance is
  passed. The allowance is a statement about the survivors, and topping
  the lot up from another date code compounds it.
- Widening the allowance to pass an exact-equality case. An equality at
  the limit is a representation question handled by the tolerance inside
  the comparison; the declared allowance stays as specified.

## Behavior contract (gate 3)

The hundred-percent coverage refusal, package-family screen set, missing
screen and sequence-order checks, removal validation, cumulative and
burn-in percent-defective comparisons and the release-or-reject
disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_screening_requirements.py against
scripts/q6013_class_2_screening_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_screening_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
