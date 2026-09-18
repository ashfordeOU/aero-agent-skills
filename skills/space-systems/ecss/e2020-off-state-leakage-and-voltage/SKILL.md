---
name: e2020-off-state-leakage-and-voltage
description: "Assess the leakage current and residual output voltage a limiter presents while it is commanded off, per clause 5.4.1.3.1 of ECSS-E-ST-20-20C. Use when an off-state data set has to be graded before a switched channel is accepted, or when a load is suspected of never fully de-energising. Cross-check the two declared limits against each other through the off-state load resistance, derive the governing leakage ceiling, grade every temperature corner against both limits, name the worst corner on each, and report a corner set that leaves the parameter unbounded. Trigger: ecss, e-st-20-20c, lcl-off-state-leakage-current, off-state-residual-output-voltage, off-state-leakage-temperature-corners, residual-voltage-off-state-load-coupling, governing-off-state-leakage-ceiling."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-off-state-leakage-and-voltage, off-state-leakage-and-voltage, lcl-off-state-leakage-current, off-state-residual-output-voltage, off-state-leakage-temperature-corners, residual-voltage-off-state-load-coupling, governing-off-state-leakage-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Off-State Leakage and Residual Voltage (space-systems/ecss/e2020-off-state-leakage-and-voltage)

Use when the task is clause 5.4.1.3.1 of ECSS-E-ST-20-20C: the maximum leakage
current and the maximum residual output voltage a limiter is permitted to
present at its output while the device is off. This leaf grades a declared
pair of limits, then grades the measured corners against the tighter of them.

## Domain quick reference

- The two limits describe one phenomenon seen twice. Leakage flowing into
  whatever impedance the load presents when it is off develops a voltage, so a
  leakage figure and a residual voltage figure are not independent budgets and
  cannot be signed off one at a time.
- That coupling is where the pair goes wrong. A leakage limit that develops
  more than the declared residual voltage across the off-state load means the
  two limits cannot both be honoured; the ceiling the channel actually has to
  meet is the tighter of the two, and it is usually not the one on the data
  sheet.
- Leakage is temperature-driven. It is smallest where it is easiest to
  measure, so an ambient-only data set is not a bound — it is the best corner
  reported as though it were the worst, and the hot corner is the one the
  limit exists for.
- Residual voltage has to be measured, not inferred. The leakage path is not
  the only way a voltage appears at a switched-off output, so a corner records
  both numbers and the implied voltage sits beside the measured one as a
  cross-check rather than replacing it.
- Both limits are one-sided. A margin of exactly zero is a part sitting on its
  limit, which passes; a margin that is negative by a representation error is
  the same part, and only a named tolerance keeps the two from being graded
  differently.
- The categories matter. The clause addresses devices holding a commanded off
  state; a retriggerable or foldback limiter regulates rather than switching
  off, and grading one here is a scope error reported as out of scope.

## Workflow

1. Normalise the category and decide whether the clause applies; report an
   out-of-scope device rather than failing it.
2. Validate the limits: a positive leakage limit, a positive residual voltage
   limit and the positive off-state load resistance that couples them.
3. Validate the measurements: one entry per corner, a non-negative leakage and
   a non-negative residual voltage, with a repeated corner refused outright.
4. Cross-check the limits before any measurement — push the leakage limit
   through the off-state load resistance and compare the voltage it develops
   against the residual voltage limit.
5. Take the governing leakage ceiling as the tighter of the declared leakage
   limit and the leakage the residual voltage limit permits.
6. Grade every corner against the governing ceiling and the residual voltage
   limit, with an exact equality at either bound absorbed by a tolerance.
7. Name the worst corner on each limit, and report any required corner the
   data set never reached.
8. Return the verdict with both ceilings, the per-corner records and margins,
   the worst corners, the missing corners and every finding.

## Pitfalls

- Signing off the two limits separately. Each can look generous on its own
  while the pair is unachievable, and nothing in a per-corner grading will
  reveal it.
- Grading leakage against the data-sheet figure. Where the residual voltage
  limit binds first, the data-sheet leakage was never the ceiling the channel
  had to meet.
- Accepting an ambient-only data set. Leakage rises with temperature, so the
  corner that was measured is the one least able to fail.
- Replacing the measured residual voltage with the implied one. Leakage is one
  path to a voltage at a switched-off output, not the only one; the implied
  figure is a cross-check, not a substitute for the measurement.
- Failing a part that measures exactly on its limit. On the limit is inside
  it; only a value below the bound by more than representation error is a
  finding.
- Grading a retriggerable or foldback limiter here. Those hold no commanded
  off state, and the honest result is an out-of-scope report.

## Behavior contract (gate 3)

The category and corner normalisation, limit and measurement validation, the
leakage-to-residual-voltage coupling through the off-state load resistance,
the governing leakage ceiling, per-corner margins with their bound-equality
tolerances, worst-corner selection, required-corner coverage and the verdict
ladder — compliant, non-compliant, out of scope — are exercised by the gate 3
contract test:
scripts/test_e2020_off_state_leakage_and_voltage.py against
scripts/e2020_off_state_leakage_and_voltage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_off_state_leakage_and_voltage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
