---
name: q7031-stripping-and-repainting
description: "Assess whether an existing paint system may be stripped from a space-hardware part and what may go back on it. Use when a full strip is proposed rather than a local touch-up: resolve the standing of the stripping method against the substrate as permitted, conditional or prohibited, accumulate the substrate loss this strip adds to what earlier strips already took, compare it with the wall the drawing keeps, count the further strips the part will still carry, land the stripped surface in the roughness window the new primer needs, and test primer, topcoat and substrate for compatibility. Trigger: ecss, q-st-70-31c-painting-scope, paint-stripping-method-substrate-compatibility, coating-strip-cycle-budget, stripped-surface-roughness-window, repaint-primer-topcoat-compatibility, substrate-material-loss-per-strip."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-stripping-and-repainting, paint-stripping-method-substrate-compatibility, coating-strip-cycle-budget, stripped-surface-roughness-window, repaint-primer-topcoat-compatibility, substrate-material-loss-per-strip]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Stripping and Re-Painting (space-systems/ecss/q7031-stripping-and-repainting)

Use when the task is the strip-and-repaint rule of ECSS-Q-ST-70-31C: a coating
system is coming off a part rather than being repaired locally, and the
questions are whether the removal method may be pointed at that substrate,
what the part has left after it, and what is allowed to go back on.

## Domain quick reference

- A strip is a hardware operation. Every method removes some substrate or
  changes its surface, so the method is chosen against the material, not
  against whichever booth is free.
- Method standing comes in three states, and the middle one is the one that
  gets lost. Permitted means the qualified procedure covers it; prohibited
  means the method attacks the substrate and is refused outright; conditional
  means it is usable only under an approved procedure with a witness coupon,
  which is not the same as allowed.
- The hazards are material-specific. Alkaline chemistry attacks aluminium and
  magnesium. Abrasive blast breaks fibres in a composite laminate long before
  it looks damaged. Solvent strippers attack a polymer matrix. Magnesium is
  restrictive on nearly every route.
- Substrate loss is cumulative across the life of the part. Each strip takes
  its per-cycle loss, earlier strips already took theirs, and the wall the
  drawing keeps is the difference between the nominal and the minimum
  thickness. A part whose margin is consumed is refused, not stripped
  carefully.
- How many further strips the part will carry is a whole number: a part cannot
  be stripped a fraction of a time, and a margin landing on a whole number of
  cycles is credited with that number rather than losing one to rounding.
- The stripped surface has to land inside a roughness window, not above a
  floor. Too smooth and the primer has nothing to key into; too rough and the
  film cannot cover the peaks at its specified thickness.
- The system going back on is two compatibilities, not one. The primer has to
  bond to that substrate, and the topcoat has to be one that primer will
  carry. Either half failing is an incompatible system.

## Workflow

1. Normalize the substrate and the proposed method, then take the method
   standing from the pair. Refuse a prohibited method and hold a conditional
   one until an approved procedure exists.
2. Accumulate the substrate loss: this strip's cycles times the per-cycle
   loss, added to what earlier strips already removed.
3. Compute the wall margin between the stripped part and its minimum
   thickness, and raise a consumed margin as a refusal.
4. Count the whole further strip cycles the remaining margin will carry, so
   the next rework decision starts from a number.
5. Put the stripped surface roughness against its window, treating both edges
   as inside and a missing measurement as an unverified finding.
6. Test the primer against the substrate and the topcoat against the primer,
   raising each half independently.
7. Confirm the residual coating was actually removed, then disposition the
   job -- approved, refused on a hard incompatibility or a consumed wall, or
   conditions outstanding -- and aggregate across the campaign.

## Pitfalls

- Reading conditional as permitted, which is how a composite panel ends up
  media-blasted with no approved procedure and no witness coupon behind it.
- Sizing the strip against this event only, so a part on its fourth strip is
  assessed as if it were on its first.
- Treating a wall margin of zero as acceptable because nothing has gone below
  the minimum yet; the next strip has nowhere to go.
- Chasing a mirror finish after stripping, which takes the surface below the
  roughness the primer needs to key into.
- Checking the primer against the substrate and assuming the topcoat follows,
  when the primer and topcoat pairing is its own compatibility.
- Calling a part stripped on appearance, with residual film left in fillets
  and fastener recesses under the new system.

## Behavior contract (gate 3)

The method standing matrix, cumulative substrate loss, wall margin and whole
remaining strip cycles, roughness window, primer and topcoat compatibility and
the job and campaign dispositions are exercised by the gate 3 contract test:
scripts/test_q7031_stripping_and_repainting.py against
scripts/q7031_stripping_and_repainting_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7031_stripping_and_repainting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
