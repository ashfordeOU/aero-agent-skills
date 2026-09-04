---
name: entry-descent-landing
description: "Size the atmospheric entry, descent, and landing phase of a spacecraft mission: check the entry corridor against the flight path angle, compute the ballistic coefficient beta = m / (Cd * A), estimate the peak deceleration g-load of a steep ballistic entry, apply the Sutton-Graves convective heating correlation q_dot = k * sqrt(rho) * V^3 for the stagnation point heat rate and integrate the heat load, and size the parachute descent with the terminal velocity v = sqrt(2 * W / (rho * Cd * S)). Produce the corridor verdict, peak g-load, heat rate and heat load, and terminal velocity for Earth or Mars conditions. Use when the task is entry corridor, ballistic coefficient, deceleration loads, convective heating, or parachute descent sizing for an entry vehicle. Trigger: entry corridor, flight path angle, ballistic coefficient, sutton-graves, convective heating, heat load, deceleration g-load, parachute terminal velocity, mars entry, reentry heating."
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
  subdomain: mission-design
  tags: [entry-descent-landing, entry-corridor, flight-path-angle, ballistic-coefficient, deceleration-g-load, sutton-graves, convective-heating, heat-load, parachute-terminal-velocity, mars-entry]
  version: 0.1.0
  author: Aero Agent Skills
---

# Entry Descent and Landing (space-systems/mission-design/entry-descent-landing)

Use when the task is the atmospheric entry, descent, and landing (EDL)
phase of a spacecraft mission: checking the entry corridor against the
flight path angle, computing the ballistic coefficient, estimating the
peak deceleration g-load and the stagnation point convective heating of
a ballistic entry, and sizing the parachute descent. This leaf is the
entry-side counterpart of the mission delta-v budget leaf (which sizes
the propulsion to reach the entry interface) and sits next to the
radiation-debris leaf (environment hazards on the same trajectory); the
hohmann-transfer leaf covers the interplanetary transfer that sets the
entry speed.

## Domain quick reference

- Entry corridor: the band of flight path angles between the undershoot
  limit (too shallow: skip-out or excessive altitude float) and the
  overshoot limit (too steep: excessive g-load and heating). Corridor
  angles are negative for descent; a shallower angle is numerically
  greater (for example -6 degrees) and a steeper angle numerically
  smaller (for example -11.5 degrees).
- Ballistic coefficient: beta = m / (Cd * A), the entry mass divided by
  the product of the drag coefficient and the reference area, in kg/m^2.
  A high beta (heavy, small drag area) penetrates deep and peaks the
  deceleration and heating low and hard; a low beta (light, large drag
  area) decelerates high and soft.
- Peak deceleration of a steep ballistic entry:
  a_peak = V^2 * sin(|gamma|) / (2 * e * H), with V the entry speed
  (m/s), gamma the flight path angle (deg, negative for descent), e the
  base of natural logarithms, and H the atmospheric scale height (m).
  The g-load is a_peak / g0; it scales as V^2 and with the sine of the
  flight path angle, so doubling the entry speed quadruples the load.
- Convective heating (Sutton-Graves): stagnation point heat rate
  q_dot = k * sqrt(rho / r_n) * V^3 (W/m^2), with rho the freestream
  density (kg/m^3), r_n the nose radius (m), V the flight speed (m/s),
  and k a correlation constant near 1.83e-4 for Earth and Mars
  stagnation flows. The cubic speed dependence makes heating the
  entry-speed driver: an 8 km/s Earth return heats about 4.6 times a
  5.5 km/s Mars-class entry at equal density and nose radius.
- Heat load: the integral of q_dot over the heating pulse, in J/m^2.
  For a discrete heat rate history sampled at a constant time step it
  is the rectangle-rule sum dt * sum(q_dot); the heat load drives the
  thermal protection system thickness.
- Ballistic vs lifting entry: a purely ballistic entry flies at zero
  lift and takes whatever g-load and heating the corridor gives; a
  lifting entry modulates the flight path angle with L/D to flatten the
  deceleration and heating peak (Apollo's lifting entry kept the crew
  g-load near 6 g where a steep ballistic return at the same speed
  would exceed 30 g). The formulas in this leaf are the ballistic
  baseline; lifting entries stay below them.
- Parachute descent terminal velocity: v = sqrt(2 * W / (rho * Cd * S)),
  with W the payload weight (m * g_local), rho the descent density,
  Cd the canopy drag coefficient (about 0.75 for a disk-gap-band
  canopy), and S the canopy reference area. Terminal velocity scales as
  the square root of the weight-to-drag ratio, so a 4x canopy area
  halves the touchdown speed.
- Landing site constraints: the touchdown speed (v at the surface
  density) must stay under the landing system limit, the descent
  duration sets the landing ellipse dispersion from winds, and the
  deceleration at chute deployment must stay under the payload and
  parachute load limits.
- Mars vs Earth atmospheres: Mars surface density is about 0.02 kg/m^3
  versus Earth's 1.225 kg/m^3, and Mars gravity is 3.711 m/s^2 versus
  9.80665 m/s^2, so a Mars parachute descent is much faster at equal
  canopy loading; Mars entry speeds from low orbit are near 5.5 km/s
  versus Earth orbital return near 7.8 km/s and direct lunar return
  near 11 km/s. Use the local gravity and the deployment altitude
  density for each planet.
- ECSS-E-ST-10C (systems engineering general requirements) frames the
  mission analysis and entry sequence within the ECSS lifecycle; ECSS
  standards are free to download from https://ecss.nl/standards/ (name
  + paraphrase + link only). The entry mechanics above are common
  hypersonic methodology, summary-only.

## Workflow

1. Record the entry interface state: entry speed (m/s), flight path
   angle (deg, negative), atmospheric scale height (m), and the local
   gravity for the target planet.
2. Check the flight path angle against the corridor with
   entry_corridor_check; a shallow angle risks skip-out and a steep
   angle risks excessive g-load and heating.
3. Compute the ballistic coefficient with ballistic_coefficient from
   the entry mass, drag coefficient, and reference area; a high beta
   pushes the peak deceleration and heating lower into the atmosphere.
4. Estimate the peak deceleration g-load with entry_deceleration from
   the entry speed, flight path angle, and scale height; compare it
   with the payload and crew structural limits.
5. Estimate the stagnation point convective heat rate with
   sutton_graves_heat_rate at the peak heating density and speed, and
   integrate the heat rate history with heat_load to get the thermal
   protection sizing driver.
6. Size the parachute descent with parachute_terminal_velocity from
   the payload weight, canopy drag coefficient, reference area, and
   deployment altitude density; check the touchdown speed against the
   landing system limit.
7. Confirm the deterministic checks with the contract test
   scripts/test_entry_descent_landing.py.

## Worked example

A Mars mission ballistic entry check, Curiosity-style (approximately
1000 kg entry mass, 4.5 m diameter capsule at Cd = 1.3, entry at
5500 m/s and -12 degrees, Mars scale height 11.1 km):

- Entry corridor: entry_corridor_check(-12.0, -6.0, -11.5) reports the
  -12 degree angle below the -11.5 degree steep limit, so the entry is
  outside the corridor and must be lifted shallower or flown with lift
  modulation. A -8 degree angle sits inside the corridor.
- Ballistic coefficient: beta = 1000 / (1.3 * 15.9) about 48 kg/m^2,
  a low-ballistic coefficient Mars entry (light capsule, large drag
  area) that decelerates high in the thin atmosphere.
- Peak deceleration: entry_deceleration(5500.0, -12.0, 11100.0)
  returns about 104 m/s^2, about 10.6 g, within the entry system
  design load of a Mars lander; a steeper -20 degree angle at the same
  speed would push past 17 g.
- Peak heat rate: sutton_graves_heat_rate(2e-4, 4800.0) with a 1 m
  nose radius returns about 0.29 MW/m^2 at the peak heating point;
  doubling the speed to 9600 m/s would raise it 8x to about
  2.3 MW/m^2, the difference between a Mars-class and an Earth-return
  thermal protection system.
- Heat load: over a 60 s heating pulse sampled every 10 s at
  [1e5, 2.5e5, 3.0e5, 2.5e5, 1.5e5, 5e4] W/m^2, heat_load returns
  1.1e7 J/m^2, the ablator sizing driver.
- Parachute descent: parachute_terminal_velocity(600.0, 0.75, 110.0,
  0.02, g=3.711) returns about 52 m/s at 0.02 kg/m^3; deploying the
  same canopy at a 2x larger area (220 m^2) cuts the descent speed by
  the square root of 2 to about 37 m/s.


## Pitfalls

- Reading corridor angles with the wrong sign sense: corridor angles
  are negative for descent and a shallower angle is numerically
  greater (-6 deg) than a steeper one (-11.5 deg); the worked example
  -12 deg entry sits below the steep limit and is outside the
  corridor.
- Using the planet surface density for the parachute terminal
  velocity: v = sqrt(2 W / (rho Cd S)) must be evaluated at the
  deployment altitude density (0.02 kg/m^3 on Mars, not 1.225); the
  touchdown speed check then uses the surface density.
- Scaling heating linearly with speed: the Sutton-Graves rate is
  cubic in V (doubling 4800 to 9600 m/s raises q_dot 8x), so an
  entry-speed change of a few percent is a double-digit percent
  change in the heat rate.
- Forgetting the entry speed - g-load square law: peak deceleration
  scales as V^2 and with sin(|gamma|); a steeper angle at the same
  speed (the -20 deg case at about 17 g) or a faster entry at the
  same angle can exceed the payload load limit even when the nominal
  corridor point is fine.
- Applying Earth gravity to a Mars descent: the ballistic and
  terminal-velocity formulas take the local gravity (3.711 m/s^2 on
  Mars), so pass g explicitly instead of assuming g0.
- Treating the ballistic formulas as lifting-entry loads: these are
  the zero-lift baseline, and a lifting entry (Apollo-style L/D)
  stays below them; sizing the TPS or structure off the ballistic
  peak for a lifting vehicle over-penalizes the design.
## Related leaves

- mission-design/mission-delta-v-budget: sizes the propulsion and the
  entry interface state (speed and angle) that feed the EDL sizing.
- mission-design/radiation-debris: the environment hazards on the same
  trajectory, with their own gating treatment.
- orbit-mechanics/hohmann-transfer: the interplanetary transfer that
  sets the entry speed at the target planet.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_entry_descent_landing.py

The test covers the ballistic coefficient, the peak deceleration g-load
(V^2 scaling, angle and speed monotonicity, very high speed finiteness),
the entry corridor check, the Sutton-Graves heat rate (V^3 and sqrt(rho)
scaling, nose radius effect, zero density, very high velocity), the heat
load integration, the parachute terminal velocity (canopy area and
density monotonicity, massless payload), and invalid-input edge cases.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10C (systems
  engineering general requirements) frames the mission analysis and
  entry sequence within the ECSS lifecycle, name + paraphrase + link
  only per standards-map.yaml; the entry mechanics above are common
  hypersonic methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
