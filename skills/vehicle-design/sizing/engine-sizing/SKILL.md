---
name: engine-sizing
description: "Use when you must size the propulsion system for the transport aircraft: compute the sea level static thrust from the design thrust to weight ratio and the takeoff gross weight, lapse the thrust to the cruise and top of climb altitude through the ISA density ratio, apply the installed thrust loss for the takeoff thrust, check the thrust margin against the cruise drag, estimate the engine weight from the engine thrust to weight ratio, and split the total thrust across the number of engines. Produces the sea level static thrust, the altitude thrust, the takeoff thrust, the top of climb margin, the fuel flow from the specific fuel consumption, and the thrust per engine that gate the engine selection in the conceptual sizing loop. Trigger: engine sizing, thrust lapse, sea level static thrust, takeoff thrust, top of climb, engine weight, specific fuel consumption."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [engine-sizing, sea-level-static-thrust, thrust-lapse, takeoff-thrust, top-of-climb, thrust-margin, specific-fuel-consumption, engine-weight, installed-thrust-loss, altitude-thrust, thrust-per-engine, thrust-to-weight-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# Engine Sizing (vehicle-design/sizing/engine-sizing)

Use when the task is sizing the propulsion for a transport aircraft:
sea level static thrust from the design thrust to weight ratio and the
takeoff gross weight, thrust lapse with altitude, installed takeoff
thrust, cruise and top of climb thrust margin, SFC fuel flow, engine
weight, and the thrust split across the number of engines.

## Domain quick reference

- Sea level static thrust: T_SL = (T/W) * W, with T/W the design
  thrust to weight ratio and W the takeoff gross weight in newtons.
  A 500000 N transport at a 0.25 design ratio needs 125000 N of sea
  level static thrust; this is the engine selection design point.
- ISA density ratio: sigma = (1 - L * h / T0) ** (g0 / (R * L) - 1)
  in the troposphere, with L = 0.0065 K/m, T0 = 288.15 K, and the
  exponent g0 / (R * L) - 1 = 4.255879. Sigma is 1.0 at sea level,
  about 0.601 at 5000 m, 0.337 at 10000 m, and 0.297 at the 11000 m
  tropopause.
- Thrust lapse with altitude: T(h) = T_SL * sigma ** m, with m the
  thrust lapse exponent. High bypass turbofans retain altitude thrust
  well, m near 0.7; a turbojet lapses closer to the density ratio
  itself, m near 1.0. At 11000 m a 125000 N engine with m = 0.7 still
  delivers about 53446 N, versus 37134 N with m = 1.0.
- Installed takeoff thrust: T_TO = T_SL * (1 - loss), with the
  installation loss covering intake, nacelle, and bleed, typically
  0.02 to 0.04 for a padded turbofan installation.
- Cruise thrust required: T_req = W / (L/D), the drag the engines must
  overcome in level cruise. A 500000 N aircraft at 18 to 1 needs about
  27778 N.
- Thrust margin: available / required. The margin is 1.0 when the
  thrust exactly meets the demand; the top of climb check keeps it
  above 1.0 so the aircraft can hold the climb condition at altitude.
- Top of climb: the thrust available at the top of climb altitude
  (sigma ** m lapse applied to T_SL) against W_TOC / (L/D)_TOC. An
  undersized engine shows a margin below 1.0 and the sea level thrust
  must grow.
- Specific fuel consumption: 1 lb/(lbf*h) equals 2.8325e-5 kg/(N*s),
  so 0.5 lb/(lbf*h) is about 1.4163e-5 kg/(N*s). Fuel flow is
  mdot = SFC * T, about 0.3934 kg/s at the cruise thrust point,
  roughly 1416 kg/h.
- Engine weight: W_eng = T_SL / (T/W)_eng with the engine thrust to
  weight ratio near 5 for a modern turbofan (4 to 6 is the typical
  band). A 125000 N total at ratio 5 weighs 25000 N, about 2549 kg.
- Thrust split: T_per = T_total / N across N engines. The per engine
  thrust is the entry to the engine catalogue; matched_engine_count
  returns the smallest whole number of catalogue engines that covers
  the demand.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context:
  the climb gradients of FAR 25.121 and CS 25.121, including the
  one engine inoperative cases, are among the thrust sizing drivers;
  the lapse and margin formulas above are common conceptual sizing
  practice.

## Workflow

1. Set the design point: takeoff gross weight W and design thrust to
   weight ratio, then compute the sea level static thrust with
   sea_level_static_thrust.
2. Apply the installation loss with takeoff_thrust to get the installed
   takeoff thrust, the thrust available at the start of the takeoff
   roll.
3. Lapse the thrust to the design altitude with thrust_at_altitude,
   using the ISA density ratio from isa_density_ratio and the lapse
   exponent that matches the engine class (0.7 high bypass turbofan,
   1.0 turbojet).
4. Compute the cruise thrust required with cruise_thrust_required and
   the margin with thrust_margin; check the top of climb with
   top_of_climb_margin and grow T_SL if the margin falls below 1.0.
5. Estimate the cruise fuel flow with fuel_flow from the SFC, using
   sfc_from_lb_per_lbf_hr when the catalogue quotes English units.
6. Size the engines: engine_weight from the engine thrust to weight
   ratio, thrust_per_engine for the chosen number of units, and
   matched_engine_count when the catalogue engine must cover the
   demand.
7. Close the loop: feed the engine weight and thrust back into the
   takeoff gross weight estimate and re-run until the design ratio and
   the top of climb margin are both met.

## Pitfalls

- Using the aircraft thrust to weight ratio as the engine thrust to
  weight ratio: T/W of the aircraft is the design demand, T/W of the
  engine is a measure of engine technology; the two differ by an order
  of magnitude (0.25 versus 5).
- Lapsing with the density ratio directly for a high bypass turbofan:
  m = 1.0 underpredicts the altitude thrust by a third at 11000 m;
  use m near 0.7 for high bypass engines.
- Forgetting the installation loss: uninstalled sea level static
  thrust overstates the takeoff thrust; apply the 0.02 to 0.04 loss
  before checking the takeoff constraint.
- Checking the cruise margin at the wrong weight: the top of climb
  check must use the weight and lift to drag ratio at the top of
  climb, not the sea level takeoff values.
- Mixing fuel flow units: SFC in lb/(lbf*h) must be converted before
  it multiplies a newton thrust, or the fuel flow comes out off by
  three orders of magnitude.
- Sizing the engine for cruise alone: the takeoff and top of climb
  constraints usually bind; the sea level static thrust must satisfy
  all three, and the binding condition sets the size.
- Treating engine weight as a constant: engine weight scales with the
  sea level static thrust through the engine thrust to weight ratio,
  and a heavier engine feeds back into the takeoff gross weight and
  the design thrust demand.
- Confusing this leaf with the matching chart: ws-tw-trade computes
  the required aircraft level T/W from takeoff distance, climb
  gradient, and cruise constraints; this leaf turns that requirement
  into an engine: sea level static thrust, lapse, installed thrust,
  margin, SFC, and weight.

## Behavior contract (gate 3)

The engine sizing math is exercised by the gate 3 contract test:
scripts/test_engine_sizing.py against scripts/engine_sizing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_engine_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25.121 and CS-25.121 frame
  the climb gradient certification basis that drives thrust sizing
  (including the one engine inoperative gradients), and FAR-25.101 and
  CS-25.101 set the general performance basis; the lapse, margin, SFC,
  and weight formulas above are common conceptual sizing methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
