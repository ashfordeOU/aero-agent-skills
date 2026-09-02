---
name: bird-strike
description: "Use when the task is bird strike impact analysis and certification of transport aeroplane structure per FAR 25.631 and CS-25: estimate the impact kinetic energy of a 4 pound or 8 pound bird at cruise velocity with impact_energy, convert the bird mass to kilograms with bird_mass_kg, compute the specific energy with specific_energy, and rate the strike against the component damage threshold with damage_severity_ratio, penetration_verdict, and residual_strength_fraction for the residual strength after impact. Covers leading edge, windshield, radome, and engine inlet damage modes, energy absorption, soft-body impact behavior, and test versus analysis compliance. Trigger: bird strike, birdstrike, bird-strike, soft body impact, soft-body-impact, impact energy, impact-energy, leading edge, leading-edge, 4 pound bird, 8 pound bird, FAR 25.631, windshield, radome, engine inlet."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: damage-tolerance
  tags: [bird-strike, birdstrike, soft-body-impact, impact-energy, leading-edge, energy-absorption, residual-strength, windshield-impact, radome-impact, engine-inlet]
  version: 0.1.0
  author: Aero Agent Skills
---

# Bird Strike (structures/damage-tolerance/bird-strike)

Use when the task is bird strike impact analysis for
damage-tolerant structure: impact kinetic energy, soft-body impact
damage severity, and residual strength after impact.

## Domain quick reference

- The impact kinetic energy E = 0.5 * m * v^2 is the governing
  parameter for soft-body impact damage; m is the bird mass and v is
  the velocity of the aeroplane relative to the bird along the flight
  path.
- Bird mass classes: the 4 pound bird (about 1.81 kg) is the FAR
  25.631 empennage impact case; the 8 pound bird (about 3.63 kg) is
  the heavier class used for windshield, radome, and engine inlet
  assessments. Convert with bird_mass_kg.
- Impact velocity: cruise speed of the aeroplane relative to the
  bird, about 250 m/s for a transport at Mach 0.8 cruise. Anchors at
  250 m/s: the 4 pound bird gives 56.6 kJ, the 8 pound bird gives
  113.4 kJ (twice the energy, mass enters linearly), and the specific
  energy is 31.25 kJ/kg.
- Soft-body impact behavior: the bird deforms on impact, so the
  struck component sees an impact pulse rather than a rigid-body
  collision; a softer, more compliant target stretches the pulse and
  lowers the peak pressure, and the kinetic energy governs the damage
  extent.
- Damage modes by component: leading edge skin and substructure
  denting, tearing, and penetration; windshield glazing fracture and
  crew protection; radome skin fracture and radar degradation; engine
  inlet lip damage and fan blade ingestion risk.
- Energy absorption: stringers, frames, and crush zones absorb part
  of the strike energy by deformation, so leading edge damage
  resistance scales with skin gauge, stringer pitch, and absorbed
  energy; the residual strength fraction after impact is rated by
  comparing the strike energy with the component damage threshold.
- Certification compliance is normally test-based (a bird gun fires a
  gel bird at representative components) with analysis used to show
  equivalence for other masses, velocities, and impact positions.
  The threshold comparison below is an analysis aid, not a test
  substitute.
- Units (single convention, consistent across the logic module):
  mass in kg, velocity in m/s, energy and threshold in joules.
  Anchor: an 8 pound bird at 250 m/s against a 60 kJ leading edge
  threshold gives severity ratio 1.89 (penetration) and residual
  strength fraction about 0.05.

## Workflow

1. Identify the certification case: the component (leading edge,
   windshield, radome, or engine inlet) and the bird class (4 or 8
   pound).
2. Convert the bird mass with bird_mass_kg; take the impact velocity
   as the aeroplane cruise speed relative to the bird.
3. Compute the impact kinetic energy with impact_energy and the
   specific energy with specific_energy.
4. Compare the strike energy with the component damage threshold with
   damage_severity_ratio and penetration_verdict.
5. Estimate the residual strength after impact with
   residual_strength_fraction; feed the result into the continued
   safe flight and landing assessment.
6. Position the result in the compliance argument: test evidence for
   the critical case, analysis for the remaining conditions.

## Pitfalls

- Using the aeroplane ground speed instead of the velocity relative
  to the bird along the flight path.
- Mixing units: a mass in pounds with a velocity in m/s shifts the
  energy by the kg per pound factor; keep kg and m/s.
- Dropping the 0.5 factor in 0.5 * m * v^2.
- Sizing the component to the 4 pound bird when the strike case is
  the 8 pound windshield, radome, or engine inlet case.
- Using momentum instead of kinetic energy: energy scales with v^2
  and governs penetration damage, momentum does not.
- Treating the threshold comparison as certification evidence: the
  severity and residual strength models are analysis aids, the
  compliance basis is test plus similarity.
- Routing event probability questions here: bird strike probability
  per flight and hazard classification belong to
  particular-risk-analysis (ARP4761A).
- Routing fatigue crack questions here: crack growth and Paris law
  belong to crack-growth, residual strength after a crack belongs to
  residual-strength, and rainflow counting of the load spectrum
  belongs to load-spectrum-counting.

## Behavior contract (gate 3)

The impact energy, severity, and residual strength logic is exercised
by the gate 3 contract test: scripts/test_bird_strike.py against
scripts/bird_strike_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_bird_strike.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; bird strike
  methodology is common soft-body impact knowledge, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
