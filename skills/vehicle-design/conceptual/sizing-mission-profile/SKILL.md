---
name: sizing-mission-profile
description: "Use when defining the design mission profile and estimating block fuel and block time for conceptual aircraft sizing: model mission segments (taxi, takeoff, climb, cruise, descent, loiter, reserve) with their distinct fuel models, compute cruise fuel from the Breguet range equation and loiter and hold fuel from Breguet endurance, model climb and descent on fuel flow and time, apply reserve fuel rules (45 minute hold at 1500 ft plus 5 percent, or FAR 121 alternate plus hold), sum segment fuels into block fuel and segment times into block time, derive the mission fuel fraction, and size required fuel weight including reserves. Produces per-segment fuel burns, block fuel and block time, reserve fuel, mission fuel fraction, payload-range trade point, and total required fuel. Trigger: mission profile, block fuel, block time, breguet range, breguet endurance, reserve fuel, loiter, hold, fuel fraction, required fuel, climb, cruise, descent, taxi, takeoff, FAR 121, payload range."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: conceptual
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: conceptual
  tags: [mission-profile, block-fuel, block-time, breguet, reserve-fuel, payload-range, conceptual-design]
  version: 0.1.0
  author: Aero Agent Skills
---

# Design Mission Profile and Block Fuel/Time (vehicle-design/conceptual/sizing-mission-profile)

Use when the task is defining the design mission profile and estimating
block fuel and block time for conceptual aircraft sizing: building the
ordered segment list, computing per-segment fuel burns, applying
reserve fuel rules, and sizing the required fuel weight that feeds the
sizing weight fraction and the payload-range trade.

## Domain quick reference

- Mission profile: an ordered list of segments (taxi, takeoff, climb,
  cruise, descent, loiter, reserve). Every segment carries a distinct
  fuel model; each segment burns from the weight remaining after all
  earlier segments, so the weight chains through the mission.
- Units: weight W in lb, range R in nautical miles, speed V in knots
  (nm/hr), time in hours, TSFC in lb fuel per lbf thrust per hour
  (treated as 1/hr, lbf and lb weight numerically equal on Earth),
  lift-to-drag ratio L/D unitless. This matches the transport-category
  sizing practice the equations come from.
- Cruise fuel, Breguet range equation: W_fuel = W_start * (1 - exp(-R /
  (V * TSFC * (L/D)))). The fuel fraction is the weight ratio the range
  equation leaves after the cruise leg.
- Loiter and hold fuel, Breguet endurance: W_fuel = W_start *
  (1 - exp(-E * TSFC / (L/D))), with E the endurance in hours. Used for
  the loiter segment and for reserve holds such as 45 minutes at
  1500 ft.
- Taxi, takeoff, descent: fuel flow (lb/hr) times segment time (hr).
  Climb: fuel flow times time, or a fraction of the segment start
  weight when only a climb fuel fraction is known.
- Block fuel: sum of the segment fuels. Block time: sum of the segment
  times (cruise time derives from R/V, loiter and reserve time from the
  endurance E).
- Reserve rules: hold45_5pct = 45 minute hold at 1500 ft plus 5 percent
  contingency on trip fuel; far121 = alternate airport fuel plus a
  30 minute hold at 1500 ft (FAR 121.645 style). FAR-25 sets the
  certification context for transport-category reserves and payload
  rules; the fuel models are common conceptual sizing methodology.
- Mission fuel fraction: block fuel divided by takeoff weight, the
  quantity the sizing weight fraction method chains segment by segment.
- Payload-range trade point: the knee of the payload-range curve, the
  range at the design payload when the fuel on board equals the minimum
  of tank capacity and the fuel the takeoff weight allows with payload
  and operating empty weight on board.

## Workflow

1. Define the design mission as an ordered segment list, one dict per
   segment with type and params. Choose the segment types and their
   fuel models: taxi, takeoff, and descent burn fuel flow times time;
   climb burns fuel flow times time or a fraction of start weight;
   cruise burns by the Breguet range equation; loiter and the reserve
   hold burn by Breguet endurance.
2. Set the aircraft inputs: takeoff weight, cruise speed, TSFC, and
   L/D per segment (the hold L/D and TSFC are usually worse than the
   cruise values).
3. Compute cruise fuel with breguet_cruise_fuel, or let segment_fuel
   dispatch by segment type. The cruise and hold equations are exact
   analytic results, not tables.
4. Sum the mission with block_fuel_and_time: it chains the segment
   weights (each segment burns from the weight after earlier segments)
   and returns block fuel, block time, and the landing weight.
5. Apply the reserve rule with reserve_fuel: hold45_5pct for the
   common 45 minute hold at 1500 ft plus 5 percent contingency, far121
   for an alternate plus 30 minute hold. The reserve burns from the
   landing weight.
6. Size the required fuel with required_fuel (block plus reserves),
   derive the mission fuel fraction with mission_fuel_fraction, and
   locate the payload-range trade point with payload_range_trade_point.
7. Feed the mission fuel fraction and required fuel into the sizing
   weight fraction (see related skills) and iterate until takeoff
   weight converges.

## Worked example

Turbofan transport, W0 = 150000 lb, cruise at V = 450 kt, TSFC =
0.6 lb/lbf/hr, L/D = 18, design range 3000 nm.

- Cruise fuel, hand Breguet: W_fuel = 150000 * (1 - exp(-3000 / (450 *
  0.6 * 18))) = 69088.9 lb. breguet_cruise_fuel(3000, 450, 0.6, 18,
  150000) returns the same value.
- Full mission (taxi 0.25 hr at 1200 lb/hr, takeoff 0.05 hr at
  18000 lb/hr, climb 0.25 hr at 24000 lb/hr, cruise 3000 nm, descent
  0.30 hr at 2500 lb/hr, loiter 0.5 hr at L/D 15): block fuel
  75233.0 lb, block time 8.017 hr, landing weight 74767.0 lb, mission
  fuel fraction 0.5016.
- Reserve hold45_5pct at the landing weight: hold 1846.0 lb plus
  5 percent of trip fuel 3761.7 lb = 5607.7 lb reserve.
- Required fuel including reserves: 75233.0 + 5607.7 = 80840.7 lb.

## Verification checklist

- [ ] Cruise fuel matches the hand Breguet value within 1 percent for
      the contract case (3000 nm, L/D 18, TSFC 0.6, V 450 kt,
      W0 150000 lb).
- [ ] Loiter and reserve hold fuel come from Breguet endurance, not
      from a fuel flow estimate.
- [ ] Block fuel chains segment weights: every segment burns from the
      weight after earlier segments.
- [ ] Block time sums explicit and derived times (cruise R/V, hold E).
- [ ] Reserve fuel includes the contingency or alternate leg, not just
      the hold.
- [ ] Required fuel equals block fuel plus reserve fuel.
- [ ] Unknown segment types and missing params raise ValueError, never
      silently burn zero.
- [ ] Contract test passes: python3 scripts/test_mission_profile.py.

## Scripts

- scripts/mission_profile_logic.py: segment_fuel, breguet_cruise_fuel,
  breguet_loiter_fuel, block_fuel_and_time, reserve_fuel,
  mission_fuel_fraction, payload_range_trade_point, required_fuel.
- scripts/test_mission_profile.py: gate 3 contract test (stdlib
  unittest, offline, deterministic). Run:
  python3 scripts/test_mission_profile.py

## Related skills

- skills/vehicle-design/conceptual/tow-estimation/: closes the sizing
  loop with the takeoff weight estimate the fuel fraction feeds.
- skills/vehicle-design/conceptual/payload-range-diagram/: builds the
  payload-range curve whose knee is the trade point computed here.
- skills/vehicle-design/conceptual/constraint-analysis/: fixes the
  thrust to weight and wing loading that set the cruise L/D and fuel
  burn assumptions.
- skills/vehicle-design/sizing/fuel-tank-sizing/: checks the required
  fuel against the tank volume available.
- skills/vehicle-design/sizing/weight-estimation/: the weight
  breakdown that supplies operating empty weight to the trade point.
- skills/vehicle-design/sizing/ws-tw-trade/: the sizing trade that
  consumes the mission fuel fraction.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the Breguet equations and reserve rules are common
  conceptual design methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
