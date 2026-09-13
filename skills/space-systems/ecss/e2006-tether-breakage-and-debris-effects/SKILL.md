---
name: e2006-tether-breakage-and-debris-effects
description: "Use when assess the mechanical and debris consequences of a deployed tether severing from an electrical or a mechanical cause, under ECSS-E-ST-20-06C clause 10.2.7: screen every severance initiator against its own limit (conductor current-density against the fusing current-density, radiative-equilibrium strand temperature against the softening temperature, accumulated arc-erosion energy against its threshold, tension against breaking-strength, cumulative particulate-strike probability against the mission allowable), categorize the dominant initiator, then size the release - recoil speed and snap-back reach against the keep-out standoff, and each free segment's area-to-mass ratio, decay lifetime and released-object count against the disposal allowances. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-10-2-7, tether-severance, ohmic-burnout-margin, tether-recoil-envelope, severed-tether-debris, micrometeoroid-severance, post-mission-disposal-lifetime."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-breakage-and-debris-effects, tether-severance, ohmic-burnout-margin, tether-recoil-envelope, severed-tether-debris, micrometeoroid-severance, post-mission-disposal-lifetime]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Tether Breakage and Debris Effects (space-systems/ecss/e2006-tether-breakage-and-debris-effects)

Use when the task is the ECSS-E-ST-20-06C clause 10.2.7 question of what a
deployed tether does to the mission once it severs — what initiated the
sever, how the released strand recoils toward the host spacecraft, and what
the sever leaves behind in orbit.

## Domain quick reference

- Clause 10.2.7 takes the sever as a credible event rather than a remote
  one. A tether is a single-strand item kilometres long with no redundancy:
  an electrical cause (the conductor fusing under an over-current, a
  sustained arc eroding through the strand at an insulation defect) and a
  mechanical cause (tension past breaking-strength, a particulate strike
  that cuts it) all end in the same state, so the consequence analysis is
  common and the initiator screening is what differs.
- The electrical initiators are quantitative. Conductor current-density is
  screened against the fusing current-density of the conductor material.
  The steady strand temperature comes from a radiative balance — ohmic
  heating per unit length against radiation from the strand surface — and
  is screened against the softening temperature, because a polymer-load-
  bearing tether loses strength long before the metal melts. Arc erosion is
  screened as accumulated energy at one site against a threshold.
- The particulate initiator is probabilistic: a deployed strand presents a
  projected area of length times diameter, and the cut probability over the
  exposure follows the usual Poisson exhaustion of that area against the
  particulate flux. A kilometre-scale tether presents several square metres,
  which is why cut probability drives the design life of bare strands.
- Recoil is the immediate mechanical consequence. The strand is held in
  elastic strain by its operating tension, so the sever releases that stored
  energy: the freed end snaps back by the elastic contraction of the
  released length and arrives at the host with a speed set by the energy
  divided by the segment mass. The reach is screened against the keep-out
  standoff around solar-array wings, antennas and optics.
- The debris consequence is an inventory question. One sever makes two
  objects out of one: the length still attached to the host and a free
  length that is now a separate tracked object, plus any end body it
  carried. A free strand has an enormous area-to-mass ratio and usually
  decays in days; the same sever at a higher altitude, or a released compact
  end body, can sit for centuries, which is what the disposal-lifetime
  screen catches.

## Workflow

1. Validate the configuration and the environment: deployed length,
   diameter, linear density, conductor area, operating current, fusing
   current-density, resistivity, radiating perimeter, emissivity, ambient
   temperature, softening temperature, tension, breaking-strength, axial
   stiffness, arc energy and threshold, particulate flux, exposure, cut
   allowable, sever position, keep-out standoff and orbit altitude.
2. Evaluate each initiator's demand and limit: current-density, strand
   radiative-equilibrium temperature, arc energy, tension, cut probability.
3. Categorize the dominant initiator as the one with the largest ratio at
   or above unity; break an exact tie by a fixed priority order. When no
   ratio reaches unity the case stays uncategorized — no initiator is
   credible at the screened level.
4. Size the recoil: stored elastic energy from tension, length and axial
   stiffness, then the reach (elastic contraction of the released length)
   and the arrival speed for the free segment's mass.
5. Inventory the debris: attached length and mass, free length and mass,
   released-object count, then the free segment's area-to-mass ratio and its
   decay lifetime under an exponential-atmosphere drag estimate.
6. Judge the outcome: a named initiator, a burnout margin under unity, a
   reach inside the standoff, a lifetime past the disposal limit, or an
   object count over the allowance each raise a finding. The severance case
   is acceptable only when every list is empty.

## Pitfalls

- Screening the conductor on current alone. The fusing limit is a current
  density, so a thinner conductor at the same current is a different
  verdict; and the softening temperature, not the melting point, is what
  ends a load-bearing strand.
- Reading a compliant cut probability as a small consequence. The
  probability screens how likely the sever is; clause 10.2.7 still requires
  the recoil and debris consequences of the sever that does happen.
- Sizing the recoil from the whole deployed length when the sever is near
  one end. The reach follows the released length and its stored energy, and
  the arrival speed follows the free segment's mass, so a sever close to the
  host is the fast case, not the slow one.
- Assuming a severed tether always decays quickly because a strand has a
  large area-to-mass ratio. That holds at low altitude; the same object
  higher up, or a released end body with a compact area-to-mass ratio, is
  what fails the disposal-lifetime screen.
- Counting only the free strand as debris. A released end body is a second
  object, and the object allowance is what the mission debris plan commits
  to, not the mass.

## Behavior contract (gate 3)

The initiator-screening, categorization, recoil, debris-inventory and
decay-lifetime logic is exercised by the gate 3 contract test:
scripts/test_e2006_tether_breakage_and_debris_effects.py against
scripts/e2006_tether_breakage_and_debris_effects_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_tether_breakage_and_debris_effects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
