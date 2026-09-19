---
name: e3301-separable-contact-surfaces
description: "Assess a separable contact interface against ECSS-E-ST-33-01C clause 4.7.5.4.5. Use when a connector, slip-ring brush or separable mechanical contact must survive its mate-demate life: applying the life factor to the required cycles, spending the noble plating with an Archard model over two wipes per cycle, reading the residual thickness left over the underplate, converting normal force into a Holm constriction resistance plus a film term against the budget, and grading fretting exposure from wipe length and the plating couple against the environment allowance. Trigger: ecss, e-st-33-01-mechanisms-scope, separable-contact-plating-wear, contact-wipe-length, holm-constriction-resistance, separable-contact-fretting, mate-demate-life-factor, separable-contact-galvanic-couple."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-separable-contact-surfaces, separable-contact-plating-wear, contact-wipe-length, holm-constriction-resistance, separable-contact-fretting, mate-demate-life-factor, separable-contact-galvanic-couple]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Separable Contact Surfaces (space-systems/ecss/e3301-separable-contact-surfaces)

Use when the task is the separable-contact design of ECSS-E-ST-33-01C
clause 4.7.5.4.5 -- showing that an interface which is mated and
demated during integration, test and operation still meets its wear,
plating and life requirements at the end of that cycle count, not on
the day it was plated.

## Domain quick reference

- The design driver is the cycle count the contact is qualified to, not
  the cycle count the mission plans. A life factor multiplies the
  required mate-demate cycles, and the wear budget is spent against that
  larger number. Applying the factor as a reduction of the allowable
  wear instead gives a different, non-conservative answer whenever the
  wear law is not linear in depth.
- Each mate-demate cycle sweeps the contact twice, so the sliding
  distance is two wipes per cycle. An Archard model turns that distance
  into a worn volume, V = k * F * s / H, which divided by the apparent
  contact area gives the plating depth consumed.
- What has to survive is the noble plating over the underplate, not the
  plating over the base metal. Once the underplate is exposed the
  couple, the film growth rate and the resistance all change, so a
  residual noble thickness is held at end of life rather than allowing
  the plating to run to zero.
- Contact resistance is set by the force, not by the nominal contact
  geometry. The plastically loaded a-spot has a Holm radius
  a = sqrt(F / (pi * H)); the constriction term is rho / (2a) and any
  surface film adds its own term over the same spot area. Softer plating
  spreads a larger spot and conducts better, and wears faster: the two
  requirements pull in opposite directions and are traded, not
  optimised separately.
- A short wipe is a fretting condition, not merely a packaging choice.
  Below roughly half a millimetre of wipe the stroke stops sweeping
  transferred debris clear of the spot, and soft plating or a high cycle
  count turns that into a resistance-growth mechanism.
- The two halves of a separable contact are frequently plated
  differently, so the interface carries a galvanic couple whose
  allowable potential difference depends on the environment the assembly
  sees, from a controlled cleanroom to a humid integration hall.

## Workflow

1. Validate the interface inputs: normal force, wipe length, apparent
   contact area, plating stock on each half, plating thickness and the
   required mate-demate cycle count. A zero force, zero wipe or
   non-integer cycle count is an input error, not a degenerate case.
2. Apply the life factor to the required cycles and round up; that is
   the design cycle count everything downstream is computed at.
3. Form the sliding distance as two wipes per design cycle and run the
   Archard model with the wear coefficient and hardness of the plating
   actually specified, not a generic metal value.
4. Subtract the worn depth from the plating thickness and compare the
   residual with the minimum noble cover held over the underplate.
5. Compute the Holm a-spot radius at the design normal force, add the
   constriction and film terms, and compare the total with the contact
   resistance budget, absorbing representation error at the boundary
   with a named tolerance rather than by relaxing the budget.
6. Grade fretting exposure from wipe length, design cycles and plating
   hardness, and compute the plating-to-plating potential difference
   against the allowance the declared environment carries.
7. Report every computed number with the finding list, so a reviewer can
   see which of the four checks drove the verdict.

## Pitfalls

- Spending the wear budget against the mission cycle count and quoting
  the life factor separately. The factor belongs inside the cycle count;
  quoting it beside an unfactored wear depth reads as compliance that
  was never demonstrated.
- Counting one wipe per mate-demate cycle. The contact slides on the way
  in and on the way out, so a single-wipe distance halves the predicted
  wear and roughly doubles the apparent plating life.
- Taking plating thickness to zero as the wear limit. The requirement is
  continuous noble cover over the underplate, so the limit sits at a
  residual thickness above zero.
- Choosing the plating on contact resistance alone. Soft gold gives the
  lowest resistance and the shortest wear life of the usual stock; the
  choice is a trade between the resistance budget and the cycle count,
  and hard gold or palladium-nickel is often the answer.
- Treating a short wipe as acceptable because the static resistance
  measures well on a fresh part. Fretting is a growth mechanism: the
  first measurement is the best one the interface will ever give.
- Ignoring the couple because both halves are "gold". A gold flash over
  a tin substrate is a tin contact once the flash is worn through, which
  is exactly the end-of-life condition being assessed.

## Behavior contract (gate 3)

The input validation, life-factor cycle count, Archard wear depth,
residual plating check, Holm contact-resistance build-up, fretting
grading and galvanic couple comparison are exercised by the gate 3
contract test:
scripts/test_e3301_separable_contact_surfaces.py against
scripts/e3301_separable_contact_surfaces_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_separable_contact_surfaces.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
