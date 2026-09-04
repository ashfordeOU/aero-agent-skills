# Wave-36 leaf spec: fuel-tank-inerting-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/fuel-tank-inerting-sizing/
- Pack: sizing. Closest siblings: fuel-tank-sizing (owns the ullage
  VOLUME allowance from fuel volume and expansion; the ullage volume is
  an INPUT here), fuel-feed-system-sizing (engine feed pumps/NPSH,
  unrelated to ullage washout), fuel-jettison-sizing (dump to landing
  weight, unrelated), fire-protection-sizing (extinguishing agent for
  compartments, not fuel-ullage inerting). Whole-tree grep: "inerting" /
  "OBIGGS" / "NEA" / "nitrogen enriched" have zero hits in vehicle-design
  and zero owning claims repo-wide. ZERO owners.
- Standards id: far-25 (reference-only; 25.981 fuel tank flammability
  reduction context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the fuel tank inerting system at the conceptual level from the
ullage oxygen washout by nitrogen-enriched air: model the ullage as a
well-mixed volume with the exponential decay of the oxygen fraction
C(t) = C_NEA + (C0 - C_NEA) exp(-Q t / V), and solve the required NEA
volumetric flow to reach a target oxygen fraction within a required time
Q = (V/t) ln((C0-C_NEA)/(C_tgt-C_NEA)). Produces the required NEA flow
in m3/s and in SCFM, the oxygen fraction at the required time, the
washout time at a given flow, and a verdict against an NEA generator
capacity limit.

Does NOT do: fuel volume and ullage allowance (fuel-tank-sizing); feed
pumps and NPSH (fuel-feed-system-sizing); jettison flow (fuel-jettison-
sizing); extinguishing agent for fire zones (fire-protection-sizing);
flammability exposure analysis and the 25.981 compliance argument
(regulatory, out of scope).

## Model (implement exactly)

Module constants:
- C0_AIR = 0.21 (initial ullage oxygen fraction, air).
- C_NEA_DEFAULT = 0.05 (oxygen fraction of nitrogen-enriched air).
- SCFM_PER_M3S = 2118.88 (1 m3/s = 2118.88 SCFM; equivalently 1 m3/min
  = 35.3147 CFM; use the m3/s factor).

Conventions: ullage volume V in m3; flows in m3/s; oxygen fractions as
volume fractions 0..1; time in s.

Functions (pure stdlib):
- nea_flow_required(ullage_m3, target_o2_fraction, time_s, c_nea =
  C_NEA_DEFAULT, c0 = C0_AIR) -> dict {flow_m3_s, flow_scfm} with
  flow = (V/t) ln((c0-c_nea)/(target-c_nea)); scfm = flow*SCFM_PER_M3S.
  ValueErrors: ullage <= 0; time_s <= 0; target <= c_nea or target >= c0;
  c_nea <= 0 or >= c0; c0 <= 0 or >= 1.
- ullage_o2_fraction(ullage_m3, nea_flow_m3_s, time_s, c_nea =
  C_NEA_DEFAULT, c0 = C0_AIR) -> float C(t) = c_nea + (c0-c_nea)*
  exp(-flow*t/V). ValueErrors: ullage <= 0; flow < 0; time_s < 0 (0
  allowed, returns c0); c bounds as above.
- washout_time(ullage_m3, nea_flow_m3_s, target_o2_fraction, c_nea =
  C_NEA_DEFAULT, c0 = C0_AIR) -> float s = (V/flow)
  ln((c0-c_nea)/(target-c_nea)). ValueErrors: flow <= 0; others as above.
- inerting_summary(ullage_m3, target_o2_fraction, time_s,
  max_nea_capacity_m3_s, c_nea = C_NEA_DEFAULT, c0 = C0_AIR) -> dict
  with flow_m3_s, flow_scfm, o2_at_time, capacity_verdict (PASS when
  flow <= max capacity).

Identity to test: C(nea_flow_required(V,t,target)) == target within 1e-9
(washout at the required flow lands exactly on the target); doubling
target delta halves the required flow for the same time.

## Worked example

Reference installation: center tank ullage 3.2 m3 must reach 9% oxygen
in 300 s with 5% NEA; NEA generator capacity 0.02 m3/s.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- flow = (3.2/300)*ln(0.16/0.04) = 0.010667*1.386294 = 0.014787 m3/s.
- SCFM = 0.014787*2118.88 = 31.33 SCFM.
- C(300) = 0.05 + 0.16*exp(-0.014787*300/3.2) = 0.05 + 0.16*0.2500 =
  0.0900 exactly.
- capacity verdict vs 0.02 m3/s: PASS (0.014787 <= 0.02).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: ullage <= 0; time <= 0; target <= c_nea (unreachable) or
  >= c0; flow <= 0 in washout_time; non-physical c0/c_nea.
- Required flow: 0.014787 m3/s within 1e-6; 31.33 SCFM within 1e-2.
- Washout identity: C at required flow == target within 1e-9.
- Time: washout_time at the required flow == 300 within 1e-6.
- Scaling: double the target delta time halves required flow at fixed V.
- Verdict PASS vs 0.02, FAIL vs 0.01 capacity.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-fuel-tank-inerting-sizing.yaml)

Query 1 (copy verbatim):
  "size the nitrogen enriched air flow to inert a 3.2 cubic meter fuel tank ullage to 9 percent oxygen in 300 seconds"
  intent: "vehicle-design; OBIGGS NEA flow for ullage oxygen washout"
  expected_skill: "vehicle-design/sizing/fuel-tank-inerting-sizing"
Query 2 (copy verbatim):
  "compute the fuel tank ullage oxygen fraction decay during nitrogen inerting at a fixed nea flow"
  intent: "vehicle-design; ullage oxygen washout exponential decay"
  expected_skill: "vehicle-design/sizing/fuel-tank-inerting-sizing"
Task ids: w36-fuel-tank-inerting-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the fuel tank inerting
system:" and include the outputs in the Claim. First tag:
fuel-tank-inerting-sizing. Additional tags ONLY: obiggs-flow-sizing,
ullage-oxygen-washout, nitrogen-enriched-air, fuel-ullage-inerting,
nea-generator-capacity. NEVER single generic words (inerting, nitrogen,
oxygen, ullage, tank, fuel, washout, flow). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): ullage allowance, expansion
volume, tank capacity (fuel-tank-sizing); npsh, boost pump, pressure
loss (fuel-feed-system-sizing); jettison, dump rate (fuel-jettison-
sizing); extinguishing agent, total flooding (fire-protection-sizing).
