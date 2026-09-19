---
name: q7054-cleaning-method-selection
description: "Evaluate the candidate ultracleaning routes for one part under ECSS-Q-ST-70-54C — precision solvent by wipe or immersion, aqueous detergent with ultrasonic agitation, carbon-dioxide snow, plasma and ultraviolet-ozone — and rank the survivors: screen each route on substrate compatibility, on the geometry its transport mechanism actually reaches, on whether it removes the contaminant present at all, and on the particulate level and residue allowance it can hold, then score removal effectiveness against margin and aggressiveness. Use when deciding how a part will be cleaned to an ultraclean level. Trigger: ecss, q-st-70-54c, ultracleaning-method-selection, precision-solvent-cleaning, aqueous-ultrasonic-cleaning, carbon-dioxide-snow-cleaning, plasma-ultracleaning, ultraviolet-ozone-cleaning."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-cleaning-method-selection, ultracleaning-method-selection, precision-solvent-cleaning, aqueous-ultrasonic-cleaning, carbon-dioxide-snow-cleaning, plasma-ultracleaning, ultraviolet-ozone-cleaning]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Cleaning Method Selection (space-systems/ecss/q7054-cleaning-method-selection)

Use when the task is the methods clause of ECSS-Q-ST-70-54C: putting the
routes in general ultraclean use against one real part and its one real
contaminant, and coming out with a ranked shortlist and a reasoned rejection
list rather than a house preference.

## Domain quick reference

- The routes are not interchangeable. A precision solvent dissolves organic
  films, an aqueous detergent with ultrasonic agitation lifts particles and
  ionic residue, carbon-dioxide snow knocks particles off by momentum and
  thermal shock, plasma and ultraviolet-ozone oxidise thin organic layers in
  place. Each is excellent at one family and indifferent to the rest.
- Transport mechanism sets the reachable geometry. A photon or a snow jet
  cleans what it can see, so a blind hole or an internal passage is outside
  both regardless of how well they work on an open face; only a wetting route
  gets inside, and that is a geometry fact, not a process parameter.
- Substrate compatibility is a hard screen and it runs first. An oxidising
  route tarnishes silver, ultrasonic cavitation damages optical coatings,
  aqueous chemistry attacks magnesium, and a solvent immersion is absorbed by
  a polymer composite. None of these is traded against capability.
- A route with zero effect on the contaminant present is not a weak candidate,
  it is not a candidate. Scoring it low leaves it on a list where somebody
  will eventually pick it because everything else was excluded.
- Capability is a pair. A route that holds an excellent residue allowance can
  be ordinary on particles, so both ladders are screened before any scoring,
  and clearing one of them is not a partial pass.
- Margin is worth credit, aggressiveness is worth a penalty. A route that
  clears the requirement by a decade is robust to a bad day; a route that is
  far more capable than the job needs is spending surface life, cycle time
  and handling exposure to buy nothing.
- The rejection list is a deliverable. It is what stops the same unsuitable
  route being proposed again at the next review, and it is what tells the
  designer which constraint to relax when nothing survives.

## Workflow

1. State the job as four facts: the contaminant family actually present, the
   substrate, the geometry that has to be reached, and the two levels the part
   owes. Reject an uncategorized value rather than defaulting it.
2. Screen each catalogued route in a fixed order — substrate, geometry,
   contaminant effect, particulate capability, residue capability — and keep
   the first reason it fails, so a rejection always names the earliest and
   most fundamental blocker.
3. Treat a capability landing exactly on the requirement as meeting it,
   absorbing the representation error in the comparison rather than by
   loosening the requirement.
4. Score the survivors: removal effectiveness for the contaminant present,
   plus the capped decade margin on each ladder, minus a penalty proportional
   to aggressiveness.
5. Rank by descending score and break a tie on route name so the shortlist is
   reproducible between runs and between reviewers.
6. Raise the findings the ranking implies: nothing survived and which
   constraint to relax; only one survivor and therefore no fallback if the
   agent supply or the facility changes; a leading route that is weak on the
   contaminant and so needs a preceding step.
7. Report the recommendation with the full ranked list, the rejection list
   with reasons, and the request the decision was made against.

## Pitfalls

- Choosing the route the facility already has. The installed route is a real
  constraint, but it belongs in the decision as a constraint, not as the
  answer; a shop that runs everything through its ultrasonic tank will
  eventually put an optic in it.
- Scoring an ineffective route instead of rejecting it. A zero-effect route
  with a good margin can still out-score a modest but effective one once the
  margin credit is added, which is exactly how a part gets cleaned by
  something that does not touch the contaminant on it.
- Treating geometry as a process parameter. Raising the plasma power or the
  snow flow does not put either inside a blind passage, so an unreachable
  geometry is answered by disassembly or by a wetting route, never by turning
  the same route up.
- Reading a route's headline cleanliness figure as its capability. The figure
  quoted for a route is usually its best ladder; the other one decides just as
  much, and a part matched on the headline alone is half unmatched.
- Taking the most capable route as the safe default. Over-capable routes are
  the ones that erode coatings, embrittle polymers and add handling steps, so
  defaulting to the strongest is a durability decision made by accident.
- Discarding the rejection list once a route is chosen. The reasons are what
  justify the choice at review, and without them the next reviewer re-opens
  the same options and reaches a different answer.

## Behavior contract (gate 3)

The request validation, ordered hard screens, exact-landing capability
comparison, margin-capped scoring, descending rank with a stable tie-break,
and the no-survivor, single-survivor and weak-leader findings are exercised by
the gate 3 contract test:
scripts/test_q7054_cleaning_method_selection.py against
scripts/q7054_cleaning_method_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7054_cleaning_method_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
