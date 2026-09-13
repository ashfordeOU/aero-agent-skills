---
name: e2006-tether-high-current-hazards
description: "Use when evaluate the large-current hazards of an electrodynamic-tether circuit under ECSS-E-ST-20-06C clause 10.2.3: categorize every current-carrying segment as tether-conductor, structural-return-path or bonding-strap, compute the ohmic voltage-drop and dissipation each carries at operating current, derive the conductor temperature-rise against its insulation rating, check bonding-joint resistance and rated-current headroom on the structural-return leg, and compare fault let-through-energy against the adiabatic conductor withstand so an unprotected path is flagged. Trigger: ecss, e-st-20-06c, electrodynamic-tether, tether-current-hazard, structural-return-path, ohmic-dissipation, bonding-joint-resistance, fault-let-through-energy, conductor-temperature-rise."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-high-current-hazards, electrodynamic-tether, tether-current-hazard, structural-return-path, ohmic-dissipation, bonding-joint-resistance, fault-let-through-energy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Tether — High-Current Hazards (space-systems/ecss/e2006-tether-high-current-hazards)

Use when the task is the large-current hazard assessment of
ECSS-E-ST-20-06C clause 10.2.3 -- tracing the current a tethered
system drives along its tether-conductor and back through the
structural-return-path, and checking every segment on that loop for
ohmic-dissipation, temperature-rise, bonding-joint and
fault-withstand violations.

## Domain quick reference

- Clause 10.2.3 is about the whole loop, not the tether alone. An
  electrodynamic-tether drives a current out along the conductor and
  must return it through something: a plasma-contactor lead, a
  deployer slip-ring, a bonding-strap, or -- most often the hazard --
  the spacecraft primary structure acting as a structural-return-path.
  Each segment on that loop is categorized into one of three families
  before it is evaluated: tether (the deployed conductor and its
  shield), return (structure, bonding-strap, chassis bond joint), and
  interface (slip-ring, plasma-contactor lead, deployment-mechanism
  lead). An unrecognized segment type is rejected, not defaulted.
- Every segment is a resistance carrying the loop current, so it
  produces a voltage-drop of I x R and dissipates I^2 x R. The
  dissipation is carried away by the segment's thermal conductance to
  its sink, giving a steady temperature-rise of P / G above the local
  sink temperature. The hazard is not the current itself but the
  resulting conductor temperature against the insulation rating of
  that segment, plus the rated-current headroom of the metal.
- Return-path segments carry two extra checks that tether segments do
  not. First, a bonding joint has a maximum interface resistance; a
  loose or corroded joint concentrates the loop dissipation into a
  millimetre-scale contact and is the classic source of a burned
  structural return. Second, structure sized for mechanical loads is
  not sized for current, so its rated-current headroom must be stated
  explicitly rather than assumed generous.
- Fault behaviour is graded separately from steady operation. A short
  on the loop drives a fault current for the protection device's
  clearing time, depositing a let-through-energy of I^2 x t into the
  conductor. The adiabatic withstand of the conductor is (k x A)^2,
  where k is the material constant and A the metallic cross-section.
  A segment whose let-through-energy exceeds its withstand fuses; a
  segment with no protection device on record is an open finding
  regardless of the arithmetic.

## Workflow

1. Inventory every segment on the current loop -- tether conductor,
   tether shield, structural return, bonding strap, chassis bond
   joint, slip-ring, plasma-contactor lead, deployment-mechanism lead
   -- and categorize each into the tether, return or interface family.
   Reject an unrecognized segment type before it enters the loop.
2. For each segment compute the voltage-drop (I x R) and the
   ohmic-dissipation (I^2 x R) at the declared operating current, then
   the steady temperature-rise (P / G) and the resulting conductor
   temperature above the segment's local sink temperature.
3. Flag the segment when the conductor temperature exceeds the
   insulation rating, when the operating current exceeds the
   rated-current, or when the voltage-drop exceeds the drop allocated
   to that segment. Treat an exactly-at-limit value as compliant --
   the comparison absorbs floating-point representation error rather
   than widening the limit.
4. For every return-family segment additionally check the bonding
   joint: its interface resistance against the maximum on record, and
   the absence of a stated rated-current as a finding in its own
   right, not a pass.
5. For each segment compute the fault let-through-energy from the
   fault current and the clearing time of its protection device, and
   compare it against the adiabatic withstand (k x A)^2. Flag an
   exceedance, and separately flag any segment with no protection
   device on record.
6. Sum the segment voltage-drops around the loop and compare against
   the loop drop budget; the loop is not compliant until the segment
   list, the bonding list and the fault list are all empty.

## Pitfalls

- Grading the tether conductor alone and never modelling the return.
  The return leg is usually the shorter, hotter, less-instrumented
  half of the loop, and a bonding joint on it carries the same current
  through a far smaller contact area.
- Reading "no temperature-rise violation" as thermally safe when the
  thermal conductance was assumed rather than measured. A conductance
  that is optimistic by a factor of two halves every computed rise.
- Treating steady operating current as the sizing case and never
  computing let-through-energy. The adiabatic withstand is fixed by
  cross-section; a clearing time that drifts by a decade moves the
  deposited energy by the same decade.
- Leaving a segment's rated-current or protection device unset and
  scoring it as compliant. An unset value means the requirement was
  never captured, which is a finding, not an absence of one.
- Widening an engineering limit so an exactly-at-limit case passes.
  The limit stays; the comparison is what absorbs the representation
  error of a sum or difference of floats.

## Behavior contract (gate 3)

The segment-categorization, voltage-drop, ohmic-dissipation,
temperature-rise, bonding-joint and fault-let-through-energy logic is
exercised by the gate 3 contract test:
scripts/test_e2006_tether_high_current_hazards.py against
scripts/e2006_tether_high_current_hazards_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_tether_high_current_hazards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
