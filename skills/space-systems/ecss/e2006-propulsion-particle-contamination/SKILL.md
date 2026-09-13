---
name: e2006-propulsion-particle-contamination
description: "Use when compute the particle deposition an electric-propulsion plume leaves on a spacecraft surface and hold it under the limit the customer agreed, per ECSS-E-ST-20-06C clause 11.2.3: categorize every efflux source as neutral-efflux or charged-efflux, resolve its transport path as direct plume-cone impingement, charge-exchange-backflow, neutral-scatter-backflow or no-transport-path, propagate the source rate through cone solid-angle, inverse-square distance and incidence-cosine into an areal flux, accumulate that flux over the firing duration with the sticking-coefficient into a deposited-film-thickness, and compare it against the agreed allowance. Trigger: ecss, e-st-20-electrical-scope, propulsion-particle-deposition, neutral-efflux-deposition, charged-efflux-deposition, charge-exchange-backflow, plume-deposition-budget, deposited-film-thickness, customer-agreed-deposition-limit."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-propulsion-particle-contamination, propulsion-particle-deposition, neutral-efflux-deposition, charged-efflux-deposition, charge-exchange-backflow, plume-deposition-budget, deposited-film-thickness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging -- Propulsion Particle Deposition (space-systems/ecss/e2006-propulsion-particle-contamination)

Use when the task is the efflux-deposition requirement of
ECSS-E-ST-20-06C clause 11.2.3 -- showing that the neutral and charged
particles an electric-propulsion system throws out deposit less on a
sensitive surface than the limit the customer agreed for it.

## Domain quick reference

- An electric thruster expels two families of particle and clause
  11.2.3 covers both. Neutral-efflux is propellant that left without
  being ionized, cathode neutral flow, thermal vapour and sputtered
  neutrals. Charged-efflux is beam ions, doubly charged ions,
  charge-exchange ions and sputtered ions. Each declared source is
  categorized into exactly one family before its transport is traced;
  a species outside the recognized set is uncategorized and rejected.
- Transport to a given surface follows one of four paths. A surface
  inside the plume cone with an unobstructed view takes direct
  impingement, at the full source strength. Outside the cone, charged
  species arrive by charge-exchange-backflow (a beam ion exchanges
  charge with a slow neutral and the resulting slow ion is steered out
  of the beam) and neutral species by scatter backflow, both at a
  small backflow fraction of the source rate. A shadowed surface has
  no transport path and takes nothing -- it is dropped, not treated as
  a worst case.
- The arriving areal flux is the source rate spread over the solid
  angle the path opens into, attenuated by inverse-square distance and
  the incidence cosine on the surface. Direct impingement spreads over
  the cone solid angle 2*pi*(1 - cos(half-angle)), so a narrow beam
  concentrates flux; backflow spreads its fraction over the full
  sphere, 4*pi steradians. A surface at grazing incidence collects
  nothing.
- Deposition is the flux held over the firing duration and multiplied
  by the sticking-coefficient of that species on that surface. The
  areal mass divides by the film density to give the
  deposited-film-thickness, which is the quantity the agreed limit is
  normally written against (optics and thermal-control surfaces are
  specified in nanometres of film, not in kilograms).
- The limit is the customer's to set, and the assessment holds two
  provisions in reserve: a surface with no agreed limit on record has
  an unevidenced requirement rather than a pass, and a backflow path
  with no backflow fraction on record is an incomplete model rather
  than a zero contribution.

## Workflow

1. Categorize every declared efflux source as neutral-efflux or
   charged-efflux; reject an unrecognized species before any number is
   computed.
2. Resolve the transport path per source and surface from the plume
   half-angle, the off-axis angle of the surface and its line of
   sight: direct impingement, charge-exchange-backflow,
   neutral-scatter-backflow or no transport path.
3. Compute the areal flux: source rate over the path solid angle,
   divided by the square of the distance, multiplied by the incidence
   cosine, and by the backflow fraction on a backflow path.
4. Accumulate over the firing duration with the sticking-coefficient,
   then divide by the film density to get the
   deposited-film-thickness. A source with no measured sticking is
   carried at unity, which is the worst case, and recorded as an
   observation so the assumption is visible.
5. Sum the per-source thickness into a neutral total, a charged total
   and a surface total, then compare the surface total against the
   agreed allowance, reporting margin and utilisation.
6. Flag the evidence gaps: no agreed limit on record, no backflow
   fraction on a backflow path, and a source list that carries only
   one of the two particle families when the clause covers both.
7. Aggregate across surfaces, naming the worst surface; the campaign
   is compliant only when every surface carries an empty
   blocking-finding list.

## Pitfalls

- Applying the source rate straight to the surface as though the plume
  were collimated. The solid-angle spread, the inverse-square distance
  and the incidence cosine are each order-of-magnitude terms; skipping
  them overstates a far off-axis surface by several decades.
- Assessing only the charged family because the thruster is an ion
  engine. Unionized propellant is routinely the larger depositing mass
  on a cold surface, and clause 11.2.3 names both families.
- Treating a missing backflow fraction as zero and reading the
  resulting clean number as compliance -- the path exists, so the
  contribution is unknown, not absent.
- Assuming unity sticking silently. Unity is the right default, but an
  assumed value driving a marginal verdict has to be visible in the
  record, or the margin is not the customer's to accept.
- Widening the agreed limit to admit a case that lands a few
  representation bits over it. The comparison already carries a named
  closeness tolerance, so an equality passes without the agreed limit
  being moved.

## Behavior contract (gate 3)

The species categorization, transport-path, flux, accumulation,
thickness, allowance and aggregation logic is exercised by the gate 3
contract test:
scripts/test_e2006_propulsion_particle_contamination.py against
scripts/e2006_propulsion_particle_contamination_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_propulsion_particle_contamination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
