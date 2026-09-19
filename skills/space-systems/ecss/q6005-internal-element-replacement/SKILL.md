---
name: q6005-internal-element-replacement
description: "Determine whether an element inside an opened hybrid assembly may be removed and a replacement fitted under ECSS-Q-ST-60-05C clause 10.5.2. Use when a chip or other mounted part has to come out of a unit that is already built: count the replacement attempts the site has left, add the thermal excursions the removal and refit impose and weigh them against the site allowance, find the neighbours inside the keep-out radius whose temperature limit the attach method would pass, and return permitted, permitted-with-conditions or not-permitted with the verification set the repair then carries. Trigger: ecss, q-st-60-05c, hybrid-internal-element-replacement, hybrid-repair-site-thermal-budget, hybrid-element-removal-and-refit, hybrid-repair-keep-out-radius, hybrid-repair-verification-set, hybrid-repair-disposition."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-internal-element-replacement, hybrid-internal-element-replacement, hybrid-repair-site-thermal-budget, hybrid-element-removal-and-refit, hybrid-repair-keep-out-radius, hybrid-repair-verification-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Internal Element Replacement (space-systems/ecss/q6005-internal-element-replacement)

Use when the task is clause 10.5.2 of ECSS-Q-ST-60-05C: taking a mounted
element out of a hybrid that is already assembled and putting another one in
its place, and deciding beforehand whether the site, its neighbourhood and the
replacement part make that a repair rather than a second defect.

## Domain quick reference

- A replacement is not one operation on one part. It is two thermal events on
  a substrate site — the removal and the refit — plus a disturbance of
  everything that sits close enough to feel them. Grading only the part being
  swapped misses both of the other two.
- A site carries two separate allowances and they run down at different
  rates. The replacement allowance counts how many times that site may be
  reworked at all. The thermal allowance counts excursions, and an element
  attached eutectically or with solder costs two of them per replacement
  where an adhesive-attached one costs one. A site can have a replacement
  left and no thermal headroom to spend it, and the reverse.
- The attach method sets the temperature the neighbourhood sees, not just the
  site. A eutectic rework runs far above a solder rework, and far above what
  a nearby adhesive-attached passive or a polymer element tolerates. Which
  neighbours matter is a geometry question — the keep-out radius — and which
  of those are at risk is a temperature question, and the two are independent.
- Shielding changes the answer. A near neighbour that is protected for the
  operation is not exposed; one that is merely far from the hottest point
  still is if it is inside the radius. Recording the shield is what turns a
  blocked repair into a conditional one.
- A replacement part is only a replacement if its provenance holds. A part
  taken from an unaccepted lot puts a component of unknown pedigree into a
  unit that has otherwise been controlled end to end, and no post-repair test
  recovers the lot history that was never there.
- Accessibility is a physical fact, not a permission. An element under an
  overlay, under a crossing wire run or beneath another element cannot be
  removed without disturbing hardware the repair was not authorised to touch,
  and that is a refusal rather than a condition.
- The outcome is three-way. Permitted, permitted-with-conditions and
  not-permitted carry different obligations downstream, and collapsing the
  middle one either blocks a repairable unit or lets an unshielded rework
  proceed next to a part that will not survive it.

## Workflow

1. Validate the site: where it is, how the element there is attached, and how
   many replacements and thermal excursions it has already taken. History is
   an input to be graded, not an error to be refused — a site already out of
   allowance is exactly the case this assessment exists for.
2. Validate the elements already on the substrate, each with a position and
   its own temperature limit, and note which are shielded for the operation.
3. Count the replacement allowance the site has left, and separately project
   the excursion count the repair would leave it at against its thermal
   allowance. Report the headroom as a signed number so an overrun is visible
   as a quantity rather than as a boolean.
4. Search the keep-out radius for neighbours, nearest first, comparing the
   distance to the radius with a tolerance so a part placed on the nominal
   radius does not fall in or out depending on the machine.
5. Filter those neighbours by temperature: unshielded, and a limit below the
   attach peak for the method in use. That set, not the whole neighbourhood,
   is what the repair has to protect.
6. Sort the findings into blockers and conditions: an unapproved procedure, a
   spent allowance, a thermal overrun, an unaccepted part lot and an
   inaccessible element block; exposed neighbours, unconfirmed residue removal
   and a site on its second replacement attach conditions.
7. Return the disposition with the verification set the completed repair
   carries, so the repair record can be written from the assessment rather
   than reconstructed afterwards.

## Pitfalls

- Spending the replacement allowance without checking the thermal one. The
  two are independent, and a site with one replacement left and no excursions
  left is not repairable even though the obvious counter says it is.
- Charging every attach method the same excursion cost. A eutectic or solder
  removal-and-refit costs twice what an adhesive one does, so the same repair
  history reaches the allowance at different points depending on how the
  element was mounted.
- Reading the keep-out radius as a strict boundary. Layout coordinates land on
  the radius constantly, and a float distance that should equal it will not
  always compare that way; the inclusion test needs a tolerance or the same
  design gives two answers on two machines.
- Treating every near neighbour as a problem. Proximity decides who is in the
  conversation; the temperature limit against the attach peak decides who is
  actually at risk, and a heat-tolerant part sitting next to the site is not
  a finding.
- Letting an unaccepted replacement part pass because the repair itself is
  sound. The workmanship and the provenance are separate conditions, and only
  one of them can be verified after the lid goes back on.
- Recording a completed repair without its extra verifications. The base set
  is not the whole set: a second replacement at the same site owes a check on
  the substrate metallisation that a first one does not.

## Behavior contract (gate 3)

The site and element validation, the replacement and thermal-excursion
allowances, the keep-out neighbourhood search, the heat-exposure filter, the
verification set and the three-way disposition are exercised by the gate 3
contract test: scripts/test_q6005_internal_element_replacement.py against
scripts/q6005_internal_element_replacement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_internal_element_replacement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
