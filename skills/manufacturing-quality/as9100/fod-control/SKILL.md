---
name: fod-control
description: "Use when you must audit a foreign object debris (FOD) prevention program for aerospace production: classify the FOD zone from the part criticality and debris exposure, compute the FOD risk score, derive the FOD sweep interval and the tool-control and housekeeping controls for the zone, reconcile the issued tool count against the returned tools, and score the program against the required control set for the audit verdict with findings. Produces the zone class, the risk score, the sweep interval, the tool-count reconciliation result, the control completeness, and the fod-pass or fod-fail verdict that gates the FOD prevention assessment. Trigger: FOD prevention, foreign object debris, FOD zone classification, FOD risk score, FOD sweep interval, tool count reconciliation, FOD audit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [fod-control, fod-prevention, foreign-object-debris, fod-zone-classification, fod-risk-score, fod-sweep-interval, tool-count-reconciliation, fod-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# AS9100 FOD Control (manufacturing-quality/as9100/fod-control)

Use when the task is building or auditing a foreign object debris (FOD)
prevention program for an aerospace production area: classifying the FOD
zone from the part criticality and the debris-generation exposure,
computing the FOD risk score, deriving the sweep interval and the
tool-control and housekeeping controls for the zone, reconciling the
issued tool count against the returned tools, and scoring the program
against the required control set for the pass or fail verdict. This leaf
implements the zone model and audit logic in pure Python, stdlib only.
It pairs with manufacturing-quality/as9100/counterfeit-prevention, the
other program-level scoring leaf in the pack, and with
manufacturing-quality/as9100/risk-management, whose FMEA risk priority
number scoring is a different scale from the FOD risk score.

## Domain quick reference

- FOD risk score: score = 3 * part_criticality + 2 * debris_exposure +
  2 * open_cavity_exposure. part_criticality is 1-3 (3 flight-control or
  propulsion critical, 2 structural, 1 non-flight); debris_exposure 1-3
  (3 machining or cutting, 2 assembly with fasteners and rework,
  1 inspection or bench work); open_cavity_exposure 0-2 (2 open fuel
  tank or engine inlet cavity, 1 open assembly, 0 enclosed).
- Zone classes (program policy input): score >= 14 is zone A, score
  >= 10 is zone B, below 10 is zone C. Zone A areas hold critical
  hardware and get the strictest control set.
- Sweep cadence (example policy input, user-definable): zone A every
  8 h, zone B every 40 h, zone C every 160 h.
- Control sets (example policy input): zone A needs tool-control,
  count-reconcile, sweep-log, tethering, fod-mats and training; zone B
  needs tool-control, count-reconcile, sweep-log and fod-mats; zone C
  needs tool-control and sweep-log.
- Tool reconciliation: every issued tool must come back; each issued
  tool whose returned quantity falls short of the issued quantity is
  reported with its shortfall. Extra returned tools that were never
  issued are ignored.
- Audit verdict: fod-pass requires control completeness 1.0 AND a
  reconciled tool count; otherwise fod-fail. Findings list each missing
  required control plus missing-tool when the count is not reconciled.
- AS9100 frames the production quality context; FOD prevention is a
  production-environment program control, distinct from parts-provenance
  counterfeit controls, operational-risk RPN scoring, and audit clause
  scoping. The zone cuts, cadence and control sets above are program
  policy values a site defines, not AS9100 clause text.

## Workflow

1. Collect the program inputs: part_criticality, debris_exposure and
   open_cavity_exposure for the work area (risk_score).
2. Compute the score and classify the zone: risk_score then zone_class,
   and read the sweep cadence for the zone with sweep_interval_h.
3. Load the zone control set with required_controls.
4. Reconcile the tool count with reconcile_tools on the issued and
   returned tool dicts; read off the missing shortfalls.
5. Run program_audit with the inputs, the tool dicts and the
   controls_present list to get completeness, findings and the verdict.
6. Close the gaps named in the findings (add the missing control, find
   the missing tool) and re-audit until fod-pass; log the sweep at the
   required cadence.
7. Confirm the deterministic checks with the contract test
   scripts/test_fod_control.py.

## Worked example

Engine module assembly line: criticality 3, debris exposure 3 (machining
adjacent to the line), open cavity exposure 2 (engine inlet open).

- Score: 3*3 + 2*3 + 2*2 = 9 + 6 + 4 = 19, zone A, sweep interval 8 h,
  required set the six-item zone A control list.
- Tool reconciliation: issued {"torque-wrench-1": 1, "drill-7": 2},
  returned {"torque-wrench-1": 1} gives missing {"drill-7": 2} and
  reconciled False.
- Audit with controls_present ["tool-control", "count-reconcile",
  "sweep-log", "fod-mats", "training"] (tethering absent): completeness
  5/6 = 0.8333, findings ["tethering", "missing-tool"], verdict fod-fail.
- Clean case: all six controls present and both tools returned gives
  completeness 1.0, findings [] and verdict fod-pass.
- Zone B case: criticality 2, debris 2, open cavity 1 gives score
  6 + 4 + 2 = 12, zone B, the four-item control set, sweep 40 h.
- Zone C case: 1/1/0 gives score 3 + 2 + 0 = 5, zone C, the two-item
  control set, sweep 160 h.

## Verification

- Confirm risk_score(3, 3, 2) returns 19 and program_audit on the
  worked example returns zone A, sweep 8 h, completeness 0.8333,
  findings ["tethering", "missing-tool"] and verdict fod-fail.
- Confirm the zone boundaries: score 14 is A, 13 is B, 10 is B, 9 is C.
- Confirm reconcile_tools on the exact, partial (shortfall as the
  missing value) and extra-return cases.
- Confirm every out-of-band criticality, debris exposure and open cavity
  exposure, every negative tool quantity, and every unknown control name
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_fod_control.py (35 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/counterfeit-prevention: the other
  program-level scoring leaf in the pack, for parts provenance rather
  than production-environment debris.
- manufacturing-quality/as9100/risk-management: operational risk RPN
  scoring, a different scale from the FOD risk score.
- manufacturing-quality/as9100/quality: audit scoping across the AS9100
  quality management system, of which the FOD program is one control.

## Pitfalls

- Treating the zone cuts, sweep cadence and control sets as fixed
  standard text: they are example program policy values a site defines
  (score >= 14 zone A, >= 10 zone B, sweeps 8/40/160 h), so an audit
  against them scores the site's declared policy, not AS9100 itself.
- Passing a fod-pass on completeness alone: the verdict requires
  completeness 1.0 AND a reconciled tool count, so a complete control
  set with one missing tool still returns fod-fail with a
  missing-tool finding.
- Reconciling tool counts in aggregate: each issued tool is tracked
  individually, so a shortfall is reported per tool with its missing
  quantity - and extra returned tools that were never issued are
  ignored rather than credited against a different tool's shortfall.
- Scoring the wrong scale: the FOD risk score (3 * part_criticality +
  2 * debris_exposure + 2 * open_cavity_exposure) is not the FMEA RPN
  of the risk-management leaf nor the provenance scoring of
  counterfeit-prevention; mixing scales corrupts the zone and the
  verdict.
- Leaving findings open: the workflow closes the gaps named in the
  findings (add the missing control, find the missing tool) and
  re-audits until fod-pass, and the sweep must still be logged at the
  required cadence.
- Feeding out-of-band inputs: criticality, debris exposure or open
  cavity exposure outside 1-3/1-3/0-2, negative tool quantities and
  unknown control names raise ValueError - a plausible-looking audit
  dict with a typo'd control name is rejected, not silently scored.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fod_control.py

The test covers the worked-example contract (score 19, zone A, sweep
8 h, missing drill-7 shortfall, completeness 5/6 = 0.8333, findings
["tethering", "missing-tool"], verdict fod-fail), the clean fod-pass
case, the zone B and C scores and boundaries (14, 13, 10, 9) with their
required control sets and sweep intervals, the tool reconciliation
exact, partial, extra-return and over-return cases, audit completeness
values and findings contents, and ValueError rejection of non-physical
inputs and unknown control names.

## Compliance

- Standards referenced, not reproduced: AS9100 is proprietary
  (IAQG/SAE); the zone cuts, sweep cadence and control sets above are
  documented example policy values, not AS9100 clause text, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
