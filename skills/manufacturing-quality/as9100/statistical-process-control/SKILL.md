---
name: statistical-process-control
description: "Use when you must run statistical process control on an aerospace production process: compute the X-bar and R chart control limits from subgroup data with the A2, D3, and D4 constants, estimate the process standard deviation from the average range with the d2 constant, calculate the Cp and Cpk capability indices against the specification limits, and detect out-of-control conditions with the Western Electric rules. Produces the control limits, the sigma estimate, the capability indices, and the violated rule list that gate the production process control review. Trigger: statistical process control, spc, x-bar chart, r chart, control limits, cpk, process capability, out of control, western electric."
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
  tags: [statistical-process-control, x-bar-chart, r-chart, control-limits, process-capability, cpk-index, out-of-control-rules, western-electric-rules]
  version: 0.1.0
  author: AeroSkills
---

# Statistical Process Control (manufacturing-quality/as9100/statistical-process-control)

Use when the task is monitoring an aerospace production process with
variable control charts: subgroup data feeds X-bar and R chart limits,
the average range gives the process sigma, and the capability indices
Cp and Cpk score the process against the specification limits.

## Domain quick reference

- X-bar chart limits from the subgroup average xbar and the average
  range rbar: UCL = xbar + A2 * rbar, LCL = xbar - A2 * rbar.
- R chart limits: UCL = D4 * rbar, LCL = D3 * rbar.
- Process standard deviation estimate from the average range:
  sigma = rbar / d2.
- Capability indices: Cp = (USL - LSL) / (6 * sigma), CPU =
  (USL - xbar) / (3 * sigma), CPL = (xbar - LSL) / (3 * sigma),
  Cpk = min(CPU, CPL).
- Constants A2, D3, D4, d2 depend on the subgroup size n; the module
  table covers n = 2 through 10, the usual aerospace sampling range.
- Out-of-control rules (Western Electric): one point beyond 3 sigma,
  eight consecutive points on one side of the centerline, two of three
  points beyond 2 sigma on one side, four of five points beyond 1
  sigma on one side.
- AS9100 clause 8.5.1 frames production process control; SPC charts
  are the common aerospace evidence that a special process stays in
  statistical control, summarized here without clause text.

## Workflow

1. Collect the subgroup averages, the average range, and the subgroup
   size n (2 through 10).
2. Compute the X-bar and R chart control limits with xbar_r_limits.
3. Estimate the process sigma from the average range with
   process_sigma.
4. Compute Cp, CPU, CPL, and Cpk with capability_indices against the
   specification limits USL and LSL.
5. Detect out-of-control conditions on a point sequence with
   out_of_control_rules.
6. Validate inputs first: a subgroup size outside 2-10, a negative
   range, or inverted specification limits raise ValueError.

## Pitfalls

- Using a subgroup size outside the constants table: sizes 2-10 are
  supported; an unsupported n raises ValueError instead of returning
  bogus limits.
- Confusing the R chart limits with the X-bar limits: R chart limits
  come from D3 and D4, never from A2.
- Computing Cpk without the process sigma estimate: capability
  indices need the range-derived sigma, not the sample standard
  deviation of the subgroup means.
- Inverting the specification limits: USL must exceed LSL or the
  capability indices are meaningless.
- Reading the Western Electric rules as point rules only: the
  consecutive-point rules need the run context, not single points.
- A zero average range with a subgroup of identical parts: sigma
  becomes zero and the capability indices divide by zero.

## Behavior contract (gate 3)

The SPC logic is exercised by the gate 3 contract test:
scripts/test_statistical_process_control.py against
scripts/statistical_process_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_statistical_process_control.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1 frames
  production process control; the chart constants and capability
  formulas are common SPC methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
