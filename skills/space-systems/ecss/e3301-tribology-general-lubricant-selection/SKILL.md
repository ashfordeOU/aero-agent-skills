---
name: e3301-tribology-general-lubricant-selection
description: "Determine which qualified lubricant provides the lubrication function of a moving mechanism interface for its specified life, per ECSS-E-ST-33-01C clause 4.7.3.1. Use when the task is choosing between candidate lubricants for a bearing, gear, hinge or sliding pair: reducing the duty to peak Hertzian contact pressure, sliding speed, required cycles after the life factor and the temperature range to be covered, eliminating unqualified candidates and any that fall short on one of those, reporting the governing margin for each, and ordering the survivors reproducibly. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-lubricant-selection, mechanism-tribology-general, mechanism-hertzian-contact-pressure, mechanism-sliding-speed-duty, mechanism-lubricated-life-cycles, lubricant-temperature-coverage."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-tribology-general-lubricant-selection, mechanism-lubricant-selection, mechanism-tribology-general, mechanism-hertzian-contact-pressure, mechanism-sliding-speed-duty, mechanism-lubricated-life-cycles, lubricant-temperature-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Tribology, General and Lubricant Selection (space-systems/ecss/e3301-tribology-general-lubricant-selection)

Use when the task is the clause 4.7.3.1 general tribology requirement
of ECSS-E-ST-33-01C — a lubrication function exists between every pair
of surfaces that move against each other, it lasts the specified life,
and the lubricant that provides it is a qualified one suited to the
load, speed, cycle count and temperature of the duty.

## Domain quick reference

- The requirement is on the function, not on the part. Every moving
  pair needs one: a bearing, a gear mesh, a hinge bush, a latch face, a
  harness clamp that slides during deployment. A pair with no declared
  lubrication is a gap even if nothing in the design calls it a
  bearing.
- Four duty quantities decide the choice, and they have to be reduced
  before any candidate is looked at: peak Hertzian contact pressure,
  sliding speed at the contact, required cycles, temperature range.
  Comparing candidates on data sheets before reducing the duty is how
  a lubricant with a splendid pressure rating gets chosen for an
  interface that is actually speed-limited.
- Required cycles are not duty cycles. Life is demonstrated with a
  factor applied to the duty count, so the number a candidate is
  screened against is larger than the mission actuation count, and
  ground testing has already consumed part of it.
- Temperature coverage is an enclosure, both ends. A lubricant that
  stiffens at the cold limit fails the duty just as surely as one that
  volatilises at the hot limit, and a cold shortfall is the one more
  often missed because the failure is torque rather than loss.
- Being qualified is a gate, not a margin. An excellent unqualified
  candidate does not compete with a qualified one; it is eliminated,
  and the route back in is qualification, not a better margin.
- The margin that matters is the governing one — the smallest of the
  pressure, speed and cycle ratios. Averaging the three, or quoting
  the largest, hides the quantity that will end the lubrication
  function first.

## Workflow

1. Reduce the interface to the duty: Hertzian peak pressure from the
   load, contact radius and effective modulus; sliding speed from the
   radius and rotational speed; required cycles from the duty count
   and the life factor; the temperature range to be covered.
2. Refuse degenerate inputs — a zero load, a zero contact radius, an
   inverted temperature range, a life factor below one — rather than
   clamping them into something that runs.
3. Screen each candidate: qualification status first, then rated
   contact pressure, rated sliding speed, qualified cycles and
   temperature enclosure, collecting a reason for every shortfall
   instead of stopping at the first.
4. Compute each candidate's pressure, speed and cycle ratios and take
   the smallest finite one as the governing margin; a static interface
   leaves the speed ratio unbounded rather than dividing by zero.
5. Order survivors by governing margin, breaking ties by name so the
   same candidate list gives the same answer on every machine.
6. When nothing survives, report a finding that names each candidate
   and the duty quantity that eliminated it, rather than returning the
   least unsuitable one as a selection.

## Pitfalls

- Screening on nominal load instead of peak Hertzian pressure. Contact
  pressure goes as the cube root of load and the inverse two-thirds of
  the ball radius, so a modest load on a small contact is far more
  severe than the load figure suggests.
- Comparing a lubricant's qualified cycle count with the mission
  actuation count. The comparison is against the factored requirement,
  which the ground test programme has already eaten into.
- Ranking on the largest margin. The governing margin is the smallest
  of the ratios; a candidate with a huge pressure margin and a speed
  ratio just above unity is the marginal one.
- Letting an unqualified candidate win on numbers. Qualification is a
  gate; the finding is that qualification is missing, not that the
  margin is thin.
- Returning the least bad candidate when none qualifies. That reads
  downstream as a selection; the honest output is a finding that names
  what eliminated each one.

## Behavior contract (gate 3)

The duty reduction, Hertzian pressure, sliding speed, DN value,
factored life, temperature enclosure, candidate screening, governing
margin and reproducible ranking are exercised by the gate 3 contract
test: scripts/test_e3301_tribology_general_lubricant_selection.py
against scripts/e3301_tribology_general_lubricant_selection_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_tribology_general_lubricant_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
