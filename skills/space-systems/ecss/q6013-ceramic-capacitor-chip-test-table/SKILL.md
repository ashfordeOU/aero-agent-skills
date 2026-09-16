---
name: q6013-ceramic-capacitor-chip-test-table
description: "Use when a ceramic chip capacitor lot's test table has to become an accept or hold verdict. Evaluate whether a declared ceramic capacitor chip test matrix meets the ECSS-Q-ST-60-13C Table 8-1 programme: confirm every required test group is present and none is declared twice, resolve each row's sample size from a whole-lot, fixed or percent-of-lot rule without inflating a sample that lands on a whole device, take each row's failures against its accept number, and judge measured capacitance drift, dissipation factor, insulation resistance and dielectric withstanding voltage against their limits in the written direction. Trigger: ecss, q-st-60-13c-table-8-1, ceramic-capacitor-chip-test-matrix, capacitance-drift-limit, dissipation-factor-limit, insulation-resistance-limit, chip-lot-sampling-rule, chip-row-accept-number."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-ceramic-capacitor-chip-test-table, ceramic-capacitor-chip-test-matrix, capacitance-drift-limit, dissipation-factor-limit, insulation-resistance-limit, chip-lot-sampling-rule, chip-row-accept-number]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Ceramic Capacitor Chip Test Matrix (space-systems/ecss/q6013-ceramic-capacitor-chip-test-table)

Use when the task is the Table 8-1 test matrix of ECSS-Q-ST-60-13C: a lot of
ceramic capacitor chips has a declared programme of test groups, methods,
sample sizes and limits, and the question is whether that programme is
complete and whether its results accept or hold the lot.

## Domain quick reference

- The matrix is three things at once, and a row is only meaningful when all
  three are present: the test group (what is stressed), the method reference
  (how it is run) and the sampling rule with its accept number (on how many
  devices, and how many may fail). A row naming a group with no method is a
  declaration of intent, not a test.
- Sample sizes are written three ways. A screen applies to the whole lot; a
  characterisation test takes a fixed sample; a periodic check takes a
  percentage of the lot with a floor so a small lot is not sampled into a
  single device. The percentage resolves to whole devices by rounding up,
  never down, because half a chip cannot be tested.
- The rounding is where a matrix quietly gains a device. A percentage of an
  integer lot is a binary floating-point product, and one that should land
  exactly on a whole device can land a few units in the last place above it.
  The representation error is absorbed before the rounding, not by relaxing
  the declared percentage.
- A ceramic chip has two independent reject paths in the same row. The count
  path is failures against the accept number; the parameter path is measured
  capacitance drift, dissipation factor, insulation resistance and
  dielectric withstanding voltage against their limits. A row with zero
  failures and an insulation resistance under its floor is a reject.
- Limits are directional. Dissipation factor carries an upper bound,
  insulation resistance a lower one, and capacitance drift a bound on the
  magnitude of a change that may move either way. Reading a lower-bound
  parameter as an upper bound inverts the verdict of the whole row.
- Duplication is a coverage defect, not a redundancy. The same group
  declared twice under two methods is two programmes, and the weaker of the
  two would otherwise be the one that decides the lot.

## Workflow

1. Validate the lot the matrix applies to; a zero or negative device count
   is an input error, and no sample may be drawn larger than its lot.
2. Check coverage: every required group for a ceramic chip present, each
   declared once, and any group outside the required set reported as an
   addition rather than silently counted towards coverage.
3. Resolve each row's sample size from its rule -- whole lot, fixed sample,
   or percentage with a floor -- rounding up to whole devices and absorbing
   the representation error of the product before the rounding.
4. Refuse a row whose failures or accept number exceed the sample it was
   drawn from; those are bookkeeping errors, not results to be clamped.
5. Take each row's failures against its accept number, then each measured
   parameter against its limit in the direction that limit is written in,
   absorbing an exact equality at the limit with a named tolerance.
6. Hold the lot when any row rejects, naming every rejecting group rather
   than the first, and report a row that consumed its accept number in full
   as a marginal-row advisory alongside the accept.

## Pitfalls

- Rounding a percentage sample down, or letting the floating-point product
  round it up by one device. Both are silent: the first under-tests the lot,
  the second makes a matrix look stricter than the one that was declared.
- Judging a row on its failure count alone. The measured parameters are an
  independent reject path in the same row, and a clean count with a drifted
  capacitance is still a reject.
- Reading every limit as an upper bound. Insulation resistance is a floor
  and capacitance drift is a magnitude, so a single direction applied across
  the row inverts two verdicts out of four.
- Accepting a matrix that declares a group twice. Two methods against one
  group is two programmes; the lot must be judged against one, declared
  before the results are in.
- Widening a limit to pass an exact-equality case. An equality at the limit
  is a representation question handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The lot validation, sampling-rule resolution, directional limit comparison,
matrix coverage, per-row verdict and the overall accept-or-hold disposition
are exercised by the gate 3 contract test:
scripts/test_q6013_ceramic_capacitor_chip_test_table.py against
scripts/q6013_ceramic_capacitor_chip_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_ceramic_capacitor_chip_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
