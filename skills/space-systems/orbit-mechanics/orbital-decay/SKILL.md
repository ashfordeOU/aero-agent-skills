---
name: orbital-decay
description: "Use when you must estimate orbital decay and deorbit lifetime of a low Earth orbit spacecraft from atmospheric drag: compute the ballistic coefficient from mass, drag area, and drag coefficient, the altitude decay rate and decay per orbit, the decay per day, and the deorbit lifetime down to a target altitude with the closed-form exponential lifetime, then assess compliance with the 25-year disposal rule and size drag augmentation for end-of-life deorbit. Trigger: orbital decay, atmospheric drag, ballistic coefficient, deorbit lifetime, decay rate, drag area, 25-year disposal rule, LEO disposal, decay per orbit, drag augmentation."
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
  subdomain: orbit-mechanics
  tags: [orbital-decay, atmospheric-drag, ballistic-coefficient, deorbit-lifetime, decay-rate, drag-area, 25-year-disposal-rule, leo-disposal, decay-per-orbit, drag-augmentation, decay-per-day]
  version: 0.1.0
  author: Aero Agent Skills
---

# Orbital Decay and Deorbit Lifetime (space-systems/orbit-mechanics/orbital-decay)

Use when the task is the drag decay of a circular low Earth orbit
spacecraft: the ballistic coefficient, the altitude decay rate and the
decay per orbit and per day, the deorbit lifetime, and the 25-year
disposal compliance of the mission.

## Domain quick reference

- Atmospheric drag is the dominant non-conservative perturbation below
  roughly 600 km: it removes orbital energy and the orbit shrinks
  continuously until reentry. The decay is fastest at low altitude
  because density rises exponentially as the orbit descends.
- Ballistic coefficient B = m / (Cd * A) in kg/m^2, with m the mass,
  A the projected drag area, and Cd the drag coefficient (typically
  2.0 to 2.5 for satellites in the free-molecule to continuum
  transition regime). High B decays slowly, low B decays fast.
- Single-layer exponential atmosphere model:
  rho(h) = rho_ref * exp(-(h - h_ref) / H), with default rho_ref =
  2.789e-10 kg/m^3 at h_ref = 200 km and scale height H = 60 km. These
  are representative thermospheric values for first-order sizing; the
  logic accepts refined densities (MSIS or standard atmosphere tables)
  as parameters. Real density varies by an order of magnitude over the
  solar cycle, so treat any single-point answer as a snapshot.
- Decay rate from orbital energy balance, dE/dt = -F_drag * v:
  dh/dt = -rho * Cd * A / m * sqrt(mu * a), negative (altitude
  decreases). Per orbit: dh/dt * T; per day: dh/dt * 86400.
- Deorbit lifetime, closed form of the exponential-atmosphere decay
  equation with sqrt(mu * a) held constant:
  t = (H / |dh/dt_0|) * (1 - exp(-(h0 - hf) / H)). As the target
  altitude hf approaches 0, the factor approaches 1 and the lifetime
  approaches H / |dh/dt_0|, the classic scale-height estimate.
- Worked anchor: a 300 kg satellite with 1.5 m^2 drag area and Cd 2.2
  at 500 km circular has B = 90.91 kg/m^2, decays at 1.0818e-3 m/s
  (93.47 m per day, 6.13 m per orbit), and deorbits to 200 km in about
  1.746 years. The same bus at 400 km decays at 5.6858e-3 m/s
  (491.25 m per day) because density is 5.3 times higher there, and
  deorbits in about 0.32 years.
- Disposal rule: post-mission disposal guidance for LEO commonly
  requires a deorbit lifetime of 25 years or less from end of mission.
  If the computed lifetime exceeds the limit, drag augmentation (a
  deployed drag sail or a higher-drag attitude) lowers the ballistic
  coefficient and shortens the lifetime; the lifetime scales linearly
  with B, so doubling the drag area halves the lifetime.

## Workflow

1. Collect the bus inputs: mass (kg), projected drag area (m^2), drag
   coefficient (2.0 to 2.5), the initial circular altitude (km), and
   the target altitude (km, commonly 0 or the reentry interface).
2. Compute the ballistic coefficient with ballistic_coefficient(mass,
   area, cd) and the density at altitude with atmospheric_density.
3. Compute the instantaneous decay with decay_rate, then convert to
   the mission-facing numbers with decay_per_orbit and decay_per_day.
4. Compute the deorbit lifetime with lifetime_seconds or
   lifetime_years down to the target altitude.
5. Run the disposal check with disposal_compliant(lifetime_years)
   against the 25-year limit; if not compliant, raise the drag area
   (drag augmentation) and re-run until the lifetime meets the limit.
6. Sanity-check the model regime: below 600 km the exponential model
   is a sizing tool, not a precise ephemeris; for a committed
   deorbit plan, redo the estimate with a higher-fidelity atmosphere
   and solar activity model.

## Pitfalls

- Routing J2 questions here: secular J2 effects (RAAN drift, argument
  of perigee drift, nodal period change) belong to the
  orbital-perturbations leaf; drag is dissipative and shrinks the
  orbit, J2 is conservative and rotates it.
- Routing maneuver questions here: propulsive delta-v budgets, the
  rocket equation, and transfer burns belong to hohmann-transfer,
  lambert-transfer, or the propulsion domain pack; this leaf sizes
  passive decay, not engine burns.
- Routing airfoil aerodynamics here: wing drag polars, cd0, and
  induced drag belong to the aerodynamics domain; the drag coefficient
  here multiplies a spacecraft reference area against the tenuous
  upper atmosphere, a different regime entirely.
- Routing standard atmosphere questions here: temperature, pressure,
  and density profiles for aircraft belong to the cross-cutting
  isa-atmosphere leaf; the exponential model here is a thermospheric
  density approximation for drag decay, not an ISA profile.
- Treating the decay rate as constant: density rises as the orbit
  drops, so the decay accelerates; the closed-form lifetime accounts
  for this with the (1 - exp(...)) factor, do not multiply the initial
  rate by time directly.
- Ignoring the drag area: the decay scales linearly with Cd * A / m,
  so a deployed drag sail changes the lifetime by an order of
  magnitude; always state the area assumption.
- Using the wrong density parameters: rho_ref and H must match the
  altitude band of the orbit; the 60 km single scale height is a
  sizing assumption and differs from the scale height of a precise
  standard atmosphere at any one altitude.
- Sign errors: decay_rate, decay_per_orbit, and decay_per_day are
  negative (altitude decreases); the lifetime uses the magnitude of
  the initial rate.
- Forgetting the target altitude: lifetime to the reentry interface
  is shorter than lifetime to a higher parking altitude; quote the
  target with the answer.
- Trusting a single snapshot: solar activity moves density by roughly
  an order of magnitude over the 11-year cycle; give a range or state
  the activity assumption.

## Behavior contract (gate 3)

The ballistic coefficient, exponential atmosphere density, decay rate,
decay per orbit and per day, deorbit lifetime, and 25-year disposal
logic are exercised by the gate 3 contract test:
scripts/test_orbital_decay.py against scripts/orbital_decay_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_orbital_decay.py

## Compliance

- Standards referenced, not reproduced: the ECSS space engineering
  series (systems engineering ECSS-E-ST-10C, space environment
  ECSS-E-ST-10-04C) frames space environment and disposal engineering
  for European projects; the exponential-atmosphere decay model and
  the 25-year disposal guideline are common astrodynamics practice,
  summary-only per standards-map.yaml (ecss is a free ESA download).
- compliance: STANDARDS-REF, gated: false.
