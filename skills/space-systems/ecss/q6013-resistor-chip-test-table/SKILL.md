---
name: q6013-resistor-chip-test-table
description: "Evaluate whether a declared resistor chip test matrix meets its programme and turns a lot into an accept or hold verdict. Use when a resistor chip lot carries a table of test groups, methods, sample sizes and acceptance limits under ECSS-Q-ST-60-13C Table 8-7: confirm every required group is present and none declared twice, resolve each row's sample from a whole-lot, fixed or percent-of-lot rule without gaining a device to rounding, take each row's failures against its accept number, check measured resistance against its marked tolerance band, and judge temperature coefficient, insulation resistance, dielectric withstanding voltage and noise against their limits in the written direction. Trigger: ecss, q-st-60-13c-table-8-7, resistor-chip-test-matrix, resistor-chip-lot-sampling-rule, resistance-tolerance-band-check, resistor-temperature-coefficient-limit, resistor-chip-row-accept-number."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-resistor-chip-test-table, resistor-chip-test-matrix, resistor-chip-lot-sampling-rule, resistance-tolerance-band-check, resistor-temperature-coefficient-limit, resistor-chip-row-accept-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Resistor Chip Test Matrix (space-systems/ecss/q6013-resistor-chip-test-table)

Use when the task is the Table 8-7 test matrix of ECSS-Q-ST-60-13C: a lot
of resistor chips has a declared programme of test groups, methods,
sample sizes and acceptance limits, and the question is whether that
programme is complete and whether its results accept or hold the lot.

## Domain quick reference

- A row is only meaningful when it carries three things at once: the test
  group that says what is stressed, the method reference that says how it
  is run, and the sampling rule with its accept number that says on how
  many devices and how many may fail. A group with no method is an
  intention, not a test.
- Sample sizes are written three ways. A screen applies to the whole lot;
  a characterisation test takes a fixed sample; a periodic check takes a
  percentage of the lot with a floor so a small lot is not sampled into a
  single device. A percentage resolves upward to whole devices, because
  half a chip cannot be tested.
- The rounding is where a matrix quietly gains a device. A percentage of
  an integer lot is a binary floating-point product, and one that should
  land exactly on a whole device can land a few units in the last place
  above it. The representation error is absorbed before the rounding, not
  by relaxing the declared percentage.
- A resistor chip has three independent reject paths in one row. The
  count path is failures against the accept number. The band path is the
  measured resistance against the tolerance the chip is marked to. The
  parameter path is temperature coefficient, insulation resistance,
  dielectric withstanding voltage and noise against their limits.
- The tolerance band is symmetric about the marked nominal and is the
  resistor's own acceptance criterion; a chip that measures outside it
  is a reject even with a clean failure count and every other parameter
  inside its limit.
- The temperature coefficient is not a measurement but a derived figure:
  the fractional change in resistance over the temperature change that
  produced it, in parts per million per kelvin. Two readings taken at the
  same temperature yield no coefficient at all, so that input is refused
  rather than divided by zero.
- Limits are directional. Noise and temperature coefficient carry upper
  bounds, insulation resistance a lower one, and a drift figure bounds a
  magnitude that may move either way. One direction applied across the
  row inverts verdicts.
- Duplication is a coverage defect, not redundancy. A group declared
  twice under two methods is two programmes, and the weaker of the two
  would otherwise decide the lot.

## Workflow

1. Validate the lot the matrix applies to; a zero or negative device
   count is an input error, and no sample may exceed its lot.
2. Check coverage with matrix_coverage: every required resistor group
   present, each declared once, and any group outside the required set
   reported as an addition rather than counted towards coverage.
3. Resolve each row's sample with resolve_sample_size -- whole lot, fixed
   sample, or percentage with a floor -- absorbing the representation
   error of the product before rounding up.
4. Refuse a row whose failures or accept number exceed the sample it was
   drawn from; those are bookkeeping errors, not results to clamp.
5. Take each row's failures against its accept number, the measured
   resistance against its marked band with within_tolerance_band, and
   each declared parameter against its limit in the direction it is
   written in.
6. Hold the lot when any row rejects, naming every rejecting group rather
   than the first, and report a row that consumed its accept number in
   full as a marginal-row advisory alongside the accept.

## Pitfalls

- Rounding a percentage sample down, or letting the floating-point
  product round it up by one device. The first under-tests the lot and
  the second makes the matrix look stricter than the one declared.
- Judging a row on its failure count alone. The band and the parameters
  are independent reject paths in the same row, and a clean count with a
  resistance outside its marked band is still a reject.
- Reading every limit as an upper bound. Insulation resistance is a
  floor, so a single direction across the row inverts that verdict every
  time.
- Taking a temperature coefficient from two readings at the same
  temperature. There is no coefficient to take, and a computed one is an
  artefact of the tolerance in the arithmetic.
- Widening a band edge or a limit to pass an exact-equality case. The
  equality is a representation question handled inside the comparison;
  the declared band and limit stay as specified.
- Accepting a matrix that declares a group twice. Two methods against one
  group is two programmes, and the lot has to be judged against one that
  was fixed before the results came in.

## Behavior contract (gate 3)

The lot validation, sampling-rule resolution, tolerance-band check,
temperature-coefficient derivation, directional limit comparison, matrix
coverage, per-row verdict and the accept-or-hold disposition are
exercised by the gate 3 contract test:
scripts/test_q6013_resistor_chip_test_table.py against
scripts/q6013_resistor_chip_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_resistor_chip_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
