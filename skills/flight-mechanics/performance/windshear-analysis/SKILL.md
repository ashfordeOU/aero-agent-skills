---
name: windshear-analysis
description: "Use when you must assess a low-altitude windshear or microburst encounter on fixed-wing aircraft performance and choose the escape response: compute the windshear F-factor from thrust, drag, weight and the along-track headwind shear rate, or from the headwind gradient and the downdraft; classify the shear severity against the typical escape-guidance thresholds; compute the energy height loss rate and the altitude loss over the encounter; check whether the aircraft can out-climb the downdraft at the current thrust; and find the thrust increment needed for the recovery. Produces the F-factor, the severity class, the energy height loss trend, the out-climb verdict, and the recovery increment that gate the windshear escape decision. Trigger: windshear, microburst, F-factor, downdraft, headwind shear, wind shear hazard, escape guidance, energy height loss, shear encounter."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [windshear-analysis, windshear, microburst, f-factor, downdraft, headwind-shear, wind-shear-hazard, escape-guidance, shear-encounter, energy-height-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# Windshear Analysis (flight-mechanics/performance/windshear-analysis)

Use when the task is the low-altitude windshear and microburst HAZARD
assessment for the escape decision: the F-factor of the encounter, the
severity class against the typical escape-guidance thresholds, the
energy height loss over the shear, the out-climb capability against the
downdraft, and the thrust increment needed for recovery. This leaf
implements the simplified energy-based F-factor model used in windshear
training (FAA windshear training guidance, paraphrased reference-only)
in pure Python, stdlib only. It pairs with wind-effects for the steady
wind triangle (headwind and crosswind components, crab angle,
groundspeed), with energy-height for the energy state and zoom climb
trades, and with climb-performance for the excess-thrust capability.
This leaf does NOT decompose steady winds or trade energy: it sizes the
transient shear hazard itself.

## Domain quick reference

- Along-track wind acceleration: a_wind = d(HW)/dt in m/s^2, positive
  when the headwind component increases with time. An increasing
  headwind is a PERFORMANCE INCREASE (it raises the airspeed without
  thrust); a decreasing headwind, or an increasing tailwind, is the
  hazard that erodes the airspeed.
- F-factor, standard form: F = (T - D)/W - a_wind/g, with T thrust, D
  drag, W weight in N and g = 9.80665 m/s^2. In calm air with T = D the
  F-factor is zero; a decreasing headwind of 8 kt/s (4.116 m/s^2)
  contributes about 0.42 to F.
- Capability and demand split used for escape guidance:
  F_available = (T - D)/W and F_demand = -a_wind/g + w_d/v, where w_d
  is the downdraft (positive downward, m/s) and v the true airspeed.
  The total encounter F-factor is F_total = F_available + F_demand.
- Headwind-gradient form: the altitude shear d(HW)/dh (1/s) is
  converted to the along-track time rate with the aircraft vertical
  speed; this module uses the steady-flight relation dh/dt =
  v*(T - D)/W (sin(gamma) = (T - D)/W for unaccelerated flight), so
  a_wind = (dHW/dh)*v*(T - D)/W and
  F = (T - D)/W - a_wind/g + w_d/v. A descent through a shear layer in
  which the headwind decreases with decreasing altitude raises F.
- Severity classes (typical training thresholds, NOT a regulation):
  F below 0.05 low, 0.05 to 0.1 moderate, 0.1 to 0.15 high, above
  0.15 severe. Applied to the encounter demand F_demand.
- Energy height loss: with specific energy E_s = h + v^2/(2g), the
  shear erodes energy height at dH_e/dt = v*(F_demand - F_available);
  at the approach escape condition (engines near the drag level,
  F_available about zero) this equals v*F_total. Altitude loss over
  the encounter is the rate times the encounter time.
- Downdraft out-climb check: the still-air maximum climb rate from the
  excess thrust is RC = v*(T - D)/W. If the downdraft exceeds RC the
  aircraft descends even at full current thrust.
- Recovery: the thrust increase that lifts F_available to the demand
  level is dT = W*(F_demand - F_available); report it and the
  thrust-to-weight increment.
- Escape ladder (deterministic): demand at or above 0.15 escape, 0.10
  high-alert, 0.05 moderate-alert, below 0.05 monitor.
- Units are SI throughout: N, m/s, m/s^2, m, s. Module constants fix
  the scale: G0 = 9.80665 m/s^2 and KT_TO_MS = 463/900 m/s per knot,
  so every number in this leaf is exactly reproducible.
- FAR 25 and CS 25 set the certification context (reference-only); the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the encounter state: mass to weight with weight_from_mass
   (W = m*g), true airspeed v, thrust T and drag D at the encounter
   start, and the wind inputs: the along-track wind acceleration
   a_wind = d(HW)/dt (from the observed headwind rate, e.g. 8 kt/s of
   decreasing headwind becomes -8*KT_TO_MS m/s^2) or the headwind
   gradient d(HW)/dh, plus the downdraft w_d.
2. Compute the total F-factor: f_factor_from_thrust with the direct
   wind acceleration, or f_factor_from_wind_gradients with the
   altitude gradient, downdraft, speed, weight, thrust and drag.
3. Classify the encounter with severity_class on the demand component
   (F_total - F_available); at the approach condition where thrust
   equals drag the total and the demand coincide.
4. Get the energy height loss rate with energy_height_loss_rate and
   the altitude loss over the encounter with altitude_loss, or let
   windshear_verdict apply the exact v*(F_demand - F_available) form.
5. Run the downdraft out-climb check with
   max_climb_rate_in_downdraft (excess thrust, weight, downdraft,
   speed): RC = v*(T - D)/W against the downdraft.
6. Size the recovery with required_thrust_increment: the demand
   F_demand as f_target and the current excess-thrust ratio (T - D)/W
   as current_f gives dT = W*(F_demand - F_available).
7. For the full picture call windshear_verdict(t, d, w, v, a_wind,
   downdraft, time_s) and read the f_available, f_demand, f_total,
   severity, energy_height_loss_rate_mps, altitude_loss_m, climb
   verdict and escape_verdict fields.
8. Confirm the deterministic checks with the contract test
   scripts/test_windshear_analysis.py.

## Worked example

A transport on approach at v = 75 m/s, mass 55,000 kg (W = m*g =
539,365.75 N), engines at the approach setting with thrust equal to
drag at T = D = 77,000 N (L/D about 7.0), so F_available = 0. The
aircraft penetrates a microburst outflow: the headwind decreases at
8 kt/s, a_wind = -8 * 463/900 = -4.11556 m/s^2, and the downdraft is
w_d = 6 m/s. Encounter time 20 s.

- Shear F-factor: F = 0 - (-4.11556)/9.80665 = 0.41967
  (f_factor_from_thrust returns 0.419670).
- Downdraft component: F_z = w_d/v = 6/75 = 0.08.
- Total F-factor of the encounter: F_total = 0.49967.
- Severity: severe (well above the 0.15 training threshold): the
  escape decision is required (escape_verdict "escape").
- Energy height loss rate: v*F_total = 37.475 m/s.
- Altitude loss over the 20 s encounter: 749.5 m of energy height.
- Out-climb check: RC = 75 * 0 / 539,365.75 = 0 m/s, far below the
  6 m/s downdraft, so the aircraft descends through the shear
  (climb_verdict "descend", out_climbs False).
- Recovery: dT = W*(F_demand - F_available) = 539,365.75 * 0.49967 =
  269,505 N, a thrust-to-weight increment of 0.4997. That exceeds the
  excess thrust ratio a go-around can deliver (about 0.3 to 0.4 for a
  transport), so the aircraft cannot neutralize the shear by thrust
  alone: escape now, do not attempt to continue the approach.

## Verification

- Confirm f_factor_from_thrust(77000, 77000, 539365.75, -4.11556)
  returns 0.419670 and that adding w_d/v = 0.08 gives 0.499670.
- Confirm f_factor_from_thrust with the same magnitude but an
  INCREASING headwind (+4.11556 m/s^2) returns -0.419670 (the wind
  adds energy: negative F, severity low).
- Confirm severity_class hits moderate at exactly 0.05, high at 0.1
  and severe at 0.15, with 0.0499 low and 0.1499 high.
- Confirm energy_height_loss_rate(0.499670, 75) = 37.475 m/s and
  altitude_loss(0.499670, 75, 20) = 749.505 m (rate times time).
- Confirm max_climb_rate_in_downdraft returns out_climbs False with
  verdict descend for zero excess thrust against a 6 m/s downdraft,
  and out_climbs True (RC = 7.5 m/s) for an excess thrust ratio of
  0.1.
- Confirm required_thrust_increment(0.499670, 0.0, 539365.75) =
  269,504.8 N, and zero when current_f already equals f_target.
- Confirm windshear_verdict on the worked example returns f_total
  0.499670, severity severe, energy_height_loss_rate_mps 37.475,
  altitude_loss_m 749.505, out_climbs False and escape_verdict
  "escape"; a calm encounter (a_wind = 0, w_d = 0, T = D) returns
  f_total 0.0, severity low, zero loss and escape_verdict "monitor".
- Confirm every non-positive weight, mass, speed or thrust, negative
  drag, and negative encounter time raises ValueError.
- Run the contract test offline: python3
  scripts/test_windshear_analysis.py (deterministic, exit 0).

## Related leaves

- flight-mechanics/performance/wind-effects: the steady wind triangle,
  groundspeed and crab angle; this leaf is the transient shear hazard.
- flight-mechanics/performance/energy-height: the energy state, zoom
  climb and specific excess power context behind the energy height
  loss rate.
- flight-mechanics/performance/climb-performance: excess-thrust climb
  capability and rates for the out-climb and recovery checks.
- flight-mechanics/performance/takeoff-performance and
  flight-mechanics/performance/landing-performance: distance
  performance under steady wind, adjacent to the shear hazard cases.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_windshear_analysis.py

The test covers the worked-example contract (F-factor 0.419670 from an
8 kt/s decreasing headwind at the stated weight, total 0.499670 with
the 6 m/s downdraft, severity severe, energy height loss rate
37.475 m/s, altitude loss 749.5 m over 20 s, recovery increment
269,505 N), the thrust and headwind-gradient F-factor forms, the
severity band boundaries, the downdraft out-climb verdicts including
the marginal equality case, energy height loss rate and altitude loss
scaling, the recovery increment including the already-sufficient zero
case, the full windshear_verdict dict on the example and on a calm
encounter, the round-trip zero-F identity in calm air, and ValueError
rejection of non-positive weight, mass, airspeed and thrust, negative
drag and negative encounter time.

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 are public
  regulation context (certification of transport category airplanes);
  the F-factor relations and severity bands are standard engineering
  methodology summarized from FAA windshear training guidance,
  summary-only per standards-map.yaml. No regulatory or training text
  is reproduced.
- compliance: STANDARDS-REF, gated: false.
