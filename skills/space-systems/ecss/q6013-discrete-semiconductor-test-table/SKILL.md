---
name: q6013-discrete-semiconductor-test-table
description: "Use when a discrete semiconductor lot's test table has to become an accept or hold verdict. Determine whether a discrete semiconductor test matrix meets the ECSS-Q-ST-60-13C Table 8-3 programme for its device family: resolve the family and refuse an unknown one, confirm every required group for diodes, transistors or optocouplers is declared once, take each row's failures against its accept number, and judge each measured parameter as a drift in the direction it degrades in, so a reverse leakage rise, a gain shift either way and an optocoupler transfer ratio fall are each caught. Trigger: ecss, q-st-60-13c-table-8-3, discrete-semiconductor-test-matrix, diode-transistor-optocoupler-family, parameter-drift-direction, current-transfer-ratio-degradation, reverse-leakage-drift-limit, semiconductor-row-accept-number."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-discrete-semiconductor-test-table, discrete-semiconductor-test-matrix, diode-transistor-optocoupler-family, parameter-drift-direction, current-transfer-ratio-degradation, reverse-leakage-drift-limit, semiconductor-row-accept-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Discrete Semiconductor Test Matrix (space-systems/ecss/q6013-discrete-semiconductor-test-table)

Use when the task is the Table 8-3 test matrix of ECSS-Q-ST-60-13C: a lot of
discrete semiconductors -- diodes, transistors or optocouplers -- has a
declared programme of test groups, methods and acceptance limits, and the
question is whether that programme is the right one for the family and
whether its results accept or hold the lot.

## Domain quick reference

- The family decides the matrix. A two-terminal diode, a three-terminal
  transistor and a four-terminal optocoupler share the environmental and
  construction groups, but their electrical groups and their acceptance
  parameters differ, and the optocoupler carries an isolation group that
  neither of the others has. A matrix is judged against the family it was
  written for; an unknown family is refused rather than defaulted to one.
- The acceptance decision is a drift, not an end-point reading. What the
  burn-in and life groups exist to expose is a device that still meets its
  datasheet window but moved while it was stressed, so the initial and the
  post-stress readings are both needed and a single final value loses the
  result entirely.
- Drift is directional and the direction is a property of the parameter. A
  forward voltage is bounded on the magnitude of its change; a reverse
  leakage or a collector cutoff current only matters when it rises; an
  optocoupler current transfer ratio only matters when it falls, because a
  falling ratio is the emitter degrading. Applying one direction across all
  three families turns two thirds of the parameters into pass-everything.
- A rising transfer ratio is not a reject, and a falling leakage is not a
  reject. Bounding the magnitude of every parameter flags devices that
  improved, which then either get waived by hand or quietly loosen the limit
  for the ones that degraded.
- The count path and the drift path are independent. A row with zero
  failures on a lot where several devices left their drift limits is still a
  hold, because the drift check is what the row was stressed to produce.
- Drift is referenced to the magnitude of the initial reading, so a negative
  bias parameter drifts in the same sense as a positive one, and a zero
  initial reading makes a relative drift undefined rather than infinite.

## Workflow

1. Resolve the device family and refuse one outside the covered set; the
   required groups and the acceptance parameters both follow from it.
2. Check coverage against that family: every required group present, each
   declared once, and any group outside the family's set reported as an
   addition rather than counted towards coverage.
3. Validate each row -- a named group, a method reference, a sample of at
   least one device, and failures and an accept number no larger than the
   sample -- then take its failures against its accept number.
4. For each device, compute the signed drift of every declared parameter
   against the magnitude of its initial reading, refusing a zero initial
   reading where the relative drift is undefined.
5. Judge each drift in the direction that parameter degrades in, absorbing
   an exact equality at the limit with a named tolerance rather than by
   relaxing the limit.
6. Hold the lot when any row rejects or any device drifted, naming every
   rejecting group rather than the first and reporting the drift reject
   count alongside, with a marginal-row advisory where a row used its accept
   number in full.

## Pitfalls

- Reusing one family's matrix for another. A diode matrix offered for an
  optocoupler is missing the isolation and transfer-ratio groups and carries
  a reverse-bias group the part has no terminals for.
- Bounding every parameter on the magnitude of its change. That makes an
  improved device a reject and, once those are waived by hand, the waiver is
  what the degraded devices are judged against.
- Reading only the post-stress value. A device inside its datasheet window
  that moved more than its drift limit is a reject, and an end-point-only
  record cannot show it.
- Accepting a row on its failure count while devices drifted. The two paths
  are independent; the drift count is reported in the same disposition.
- Dividing by a signed initial reading. A negative bias parameter then
  drifts in the opposite sense to a positive one, and the direction rule
  inverts for exactly those parameters.
- Widening a limit to pass an exact-equality case. An equality at the limit
  is a representation question handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The family resolution, per-family required groups, signed relative drift,
directional drift limits, per-device verdict, matrix coverage, per-row count
verdict and the overall accept-or-hold disposition are exercised by the gate
3 contract test:
scripts/test_q6013_discrete_semiconductor_test_table.py against
scripts/q6013_discrete_semiconductor_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_discrete_semiconductor_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
