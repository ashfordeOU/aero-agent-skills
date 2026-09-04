---
name: fuel-tank-inerting-sizing
description: "Use when you must size the fuel tank inerting system at the conceptual level: model the ullage as a well-mixed volume washed by nitrogen-enriched air (NEA), compute the required NEA flow from the exponential oxygen decay C(t) = C_NEA + (C0 - C_NEA) exp(-Q t / V), and solve the flow that reaches a target oxygen fraction within a required time Q = (V/t) ln((C0 - C_NEA)/(C_tgt - C_NEA)). Produces the required NEA flow in m3/s and in SCFM, the ullage oxygen fraction at the required time, the washout time at a given flow, and a PASS or FAIL verdict against the NEA generator capacity limit (FAR 25.981 fuel tank flammability reduction context). Trigger: obiggs flow sizing, ullage oxygen washout, nitrogen enriched air, fuel ullage inerting, nea generator capacity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [fuel-tank-inerting-sizing, obiggs-flow-sizing, ullage-oxygen-washout, nitrogen-enriched-air, fuel-ullage-inerting, nea-generator-capacity]
  version: 0.1.0
  author: AeroSkills
---

# Fuel Tank Inerting Sizing (vehicle-design/sizing/fuel-tank-inerting-sizing)

Use when you must size the fuel tank inerting system at the conceptual
level: the on-board inert gas generation system (OBIGGS) delivers
nitrogen-enriched air (NEA) into the fuel tank ullage, and the ullage
oxygen fraction washes down toward the NEA oxygen fraction as a
well-mixed exponential decay. This leaf sizes the NEA flow that reaches
a target oxygen fraction within a required time, converts it to SCFM
for generator selection, and checks it against a generator capacity
limit. It implements the washout model in pure Python, stdlib only,
and pairs with vehicle-design/sizing/fuel-tank-sizing, which owns the
fuel volume and ullage volume side of the tank layout; the ullage
volume is an input here.

## Domain quick reference

- Well-mixed washout: C(t) = C_NEA + (C0 - C_NEA) * exp(-Q * t / V),
  with V the ullage volume in m3, Q the NEA volumetric flow in m3/s,
  C0 the initial ullage oxygen fraction and C_NEA the NEA oxygen
  fraction. The oxygen fraction decays exponentially toward C_NEA.
- Required NEA flow for a target within a required time: Q = (V / t) *
  ln((C0 - C_NEA) / (C_tgt - C_NEA)). Larger required washdown (target
  far below C0) and shorter time both drive Q up.
- Washout time at a fixed flow: t = (V / Q) * ln((C0 - C_NEA) /
  (C_tgt - C_NEA)), the inverse of the flow relation.
- Units: ullage volume in m3, flows in m3/s, oxygen fractions as volume
  fractions in 0..1, time in s. 1 m3/s = 2118.88 SCFM.
- Module defaults: C0 = 0.21 (air) and C_NEA = 0.05; both overridable.
- FAR 25.981 flammability reduction context: a fuel tank with an ullage
  oxygen fraction at or above the flammability limit must be inerted or
  otherwise protected; a 9% target is a common design point for
  nitrogen inerting. The standard is referenced for context only, not
  reproduced here.

## Workflow

1. Fix the inerting design point: ullage volume V in m3 (take it from
   the fuel-tank-sizing loop), target oxygen fraction, and the required
   time to reach it.
2. Compute the required NEA flow with nea_flow_required; it returns the
   flow in m3/s and in SCFM for the generator data sheet.
3. Check the resulting oxygen trajectory with ullage_o2_fraction at the
   required time; it confirms the target is met at the design point.
4. For a given available generator flow, find how long the washdown
   takes with washout_time.
5. Run inerting_summary with the generator capacity limit; read the
   capacity_verdict PASS or FAIL against that limit.
6. Confirm the deterministic checks with the contract test
   scripts/test_fuel_tank_inerting_sizing.py.

## Worked example

Reference installation: center tank ullage 3.2 m3 must reach 9% oxygen
in 300 s with 5% NEA; NEA generator capacity 0.02 m3/s.

- Required flow: nea_flow_required(3.2, 0.09, 300.0) returns flow_m3_s
  = 0.014787 m3/s and flow_scfm = 31.33 SCFM. Hand check: (3.2 / 300) *
  ln(0.16 / 0.04) = 0.010667 * 1.386294 = 0.014787.
- Oxygen at the required time: ullage_o2_fraction at that flow and
  300 s returns 0.0900 exactly: 0.05 + 0.16 * exp(-0.014787 * 300 /
  3.2) = 0.05 + 0.16 * 0.2500 = 0.09.
- Washout time: washout_time(3.2, 0.014787, 0.09) returns 300.0 s,
  recovering the design time.
- Capacity verdict: inerting_summary(3.2, 0.09, 300.0, 0.02) returns
  capacity_verdict PASS (0.014787 <= 0.02); against a 0.01 m3/s
  generator the same design returns FAIL.
- Scaling: raising the target to 0.13 (doubling the target delta
  0.04 to 0.08) halves the required flow to 0.007394 m3/s at the same
  volume and time.

## Verification

- Confirm nea_flow_required(3.2, 0.09, 300.0) returns flow_m3_s =
  0.014787 (within 1e-6 of the spec bound) and flow_scfm = 31.33
  (within 1e-2).
- Confirm the washout identity: ullage_o2_fraction at the required
  flow and time equals the target 0.09 within 1e-9, and washout_time at
  the required flow returns 300 s within 1e-6.
- Confirm the scaling law: doubling the target delta halves the
  required flow at fixed volume and time.
- Confirm every non-positive ullage volume, time or capacity, a flow of
  zero in washout_time, a negative flow or time in ullage_o2_fraction,
  and every out-of-range oxygen fraction (target <= C_NEA, target >=
  C0, C_NEA or C0 non-physical) raises ValueError.
- Run the contract test offline: python3
  scripts/test_fuel_tank_inerting_sizing.py (31 tests, deterministic).

## Related leaves

- vehicle-design/sizing/fuel-tank-sizing: fuel volume and the ullage
  volume side of the tank layout; its ullage volume is the input to
  this washout sizing.
- vehicle-design/sizing/fuel-feed-system-sizing: the engine feed and
  pump side of the fuel system, a separate sizing problem.
- vehicle-design/sizing/fuel-jettison-sizing: emergency fuel offload
  for landing weight, unrelated to ullage washout.
- vehicle-design/sizing/fire-protection-sizing: compartment fire
  suppression agent sizing, distinct from fuel-ullage inerting.

## Pitfalls

- Treating the target fraction as reachable with unlimited NEA flow:
  the log ratio ln((C0 - C_NEA) / (C_tgt - C_NEA)) diverges as the
  target approaches C_NEA, so a target at or below the NEA oxygen
  fraction is physically unreachable and raises ValueError.
- Mixing flow units: the module works in m3/s and converts with
  2118.88 SCFM per m3/s; applying a per-minute factor to a per-second
  flow mis-sizes the generator by a factor of 60.
- Ignoring the capacity verdict: the washout model gives the required
  flow with no limit; the generator capacity check in inerting_summary
  is what turns the physics into an installation verdict.
- Confusing this washout sizing with tank geometry sizing: fuel volume
  and ullage volume are owned by fuel-tank-sizing and are inputs here,
  not recomputed.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fuel_tank_inerting_sizing.py

The test covers the 3.2 m3 reference sizing contract (required flow
0.014787 m3/s and 31.33 SCFM within the spec bounds), the washout
identity C at the required flow equals the target within 1e-9, the
washout time round trip to 300 s, the capacity verdict PASS at 0.02
and FAIL at 0.01 m3/s, the flow scaling laws (doubling the target
delta or the time halves the flow, doubling the ullage doubles it),
the exponential decay behavior at zero time, zero flow and long time,
the exact dict keys of every return, determinism, and ValueError
rejection of non-positive ullage, time, flow and capacity and of
out-of-range oxygen fractions.

## Compliance

- Standards referenced, not reproduced: FAR 25.981 provides the fuel
  tank flammability reduction context; the washout relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
