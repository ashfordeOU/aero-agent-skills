---
name: q7031-application-methods
description: "Verify that a paint system is being applied by an approved method and to the specified build under ECSS-Q-ST-70-31C: reject a method the specification does not list, a brushed or rolled film on a thermo-optical surface and a dipped item carrying keep-out areas, convert the specified dry film into the wet film through volume solids, size the passes, theoretical coverage and paint volume after transfer losses, and grade the recoat interval and application-area conditions. Use when a coat is about to be laid down or an application record is reviewed. Trigger: ecss, q-st-70-31c, paint-application-method, paint-wet-film-thickness, paint-pass-count, paint-recoat-interval, paint-transfer-efficiency."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-application-methods, paint-application-method, paint-wet-film-thickness, paint-pass-count, paint-recoat-interval, paint-transfer-efficiency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Application Methods (space-systems/ecss/q7031-application-methods)

Use when the task is the application clause of ECSS-Q-ST-70-31C: laying the
selected paint system down by a method the specification approves, in enough
passes to reach the specified dry film, inside the recoat interval and inside
the conditions the material was qualified in.

## Domain quick reference

- The method is part of the qualification, not an operator preference. A film
  that looks right but was laid down by an unapproved method has no qualified
  relationship to the data the selection was made on, so the method is checked
  before anything is computed about the film.
- Method and surface role interact. A brushed or rolled film carries brush
  marks and edge build that change local absorptance and emittance, which is
  tolerable on a bracket and not tolerable on a thermo-optical surface. Dipping
  cannot respect a keep-out area at all, so an item with masked bare areas
  cannot be dipped whatever the drawing says elsewhere.
- The applicator controls wet film, not dry film. The specified dry film is
  reached by laying down wet film equal to that value divided by the material's
  volume solids, and a thinner-rich material needs far more wet film for the
  same dry result.
- Pass count follows the per-pass build of the method. Trying to reach a heavy
  specification in one pass of a light-build method gives runs and sags; the
  honest answer is more passes, which is what drives the recoat interval into
  the plan.
- The recoat interval is two-sided. Too soon traps solvent under a skinned
  surface and blisters later; too late lets the previous coat cure past the
  point where the next one can bite into it, and then adhesion is mechanical
  only.
- Transfer efficiency decides how much paint is bought, not how thick the film
  is. Conventional spray puts a minority of the material on the item, and
  sizing a job on theoretical coverage alone runs the batch out mid-coat.

## Workflow

1. Normalise the method and check it against the recognised methods, the
   approved list for the item, the thermo-optical role and any keep-out areas.
   An unapproved method closes the assessment before any sizing.
2. Convert the specified dry film into wet film through the material's volume
   solids.
3. Compute the pass count at the method's per-pass build, or the per-item
   override, rounding a partial pass up but not adding a pass for a
   representation error at an exact multiple.
4. Compute theoretical coverage and the paint volume the area needs once the
   method's transfer efficiency is applied.
5. Grade the elapsed time since the previous coat against the two-sided recoat
   interval, treating a time exactly on either bound as inside it.
6. Grade the application-area temperature and humidity, then close on
   compliant, rework-required or method-not-approved with every finding named.

## Pitfalls

- Specifying wet film and measuring dry film, or the reverse. The two differ by
  the volume solids, and mixing them up is how a coat lands at half or double
  the specified build.
- Reaching a heavy specification in one pass. The per-pass build is a property
  of the method; exceeding it produces sags and a film whose real thickness
  nobody knows.
- Sizing the paint order on theoretical coverage. Transfer efficiency is the
  difference between what leaves the gun and what lands, and for conventional
  spray it is most of the material.
- Treating the recoat interval as a minimum only. Recoating a fully cured
  previous layer loses the chemical bite between coats, and the failure appears
  much later as intercoat delamination.
- Painting outside the temperature or humidity window because the surface
  itself checked out clean. The film's cure and flow depend on the conditions
  during application, not only on the state of the substrate beforehand.

## Behavior contract (gate 3)

The method approval screens, wet-film conversion, pass-count rounding,
coverage and transfer-loss volume, the two-sided recoat interval, the
application-conditions window and the disposition are exercised by the gate 3
contract test: scripts/test_q7031_application_methods.py against
scripts/q7031_application_methods_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_application_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
