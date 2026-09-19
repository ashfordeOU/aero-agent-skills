---
name: q6012-wafer-screening-and-acceptance-testing
description: "Assess a wafer level screening and acceptance flow run before dicing, under ECSS-Q-ST-60-12C clause 10.2. Use when stress and measurement activities have been applied to a microwave wafer and the lot must be accepted or held: order the declared flow, hold an activity that needs separated dies, refuse a stress step with no parametric measurement bracketing it before and after, compute the relative drift of every monitored parameter at every probed site, group the sites as passing or failing against the drift limits with the boundary case absorbed by a named tolerance, and compare the failing fraction with the percentage defective allowed. Trigger: ecss, q-st-60-12c-clause-10-2, wafer-level-screening-flow, pre-dicing-stress-bracketing, wafer-site-parametric-drift, wafer-percent-defective-allowed, wafer-lot-accept-or-hold."
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
  tags: [ecss, q-st-60-microwave-die-scope, q6012-wafer-screening-and-acceptance-testing, wafer-level-screening-flow, pre-dicing-stress-bracketing, wafer-site-parametric-drift, wafer-percent-defective-allowed, wafer-lot-accept-or-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Wafer Screening And Acceptance (space-systems/ecss/q6012-wafer-screening-and-acceptance-testing)

Use when the task is the wafer level step of ECSS-Q-ST-60-12C clause
10.2 — the stress and measurement activities applied to a microwave
wafer while it is still whole, arranged as a flow that has to finish
before the saw, and the acceptance decision that flow produces.

## Domain quick reference

- Working at wafer level is a deliberate economy: a parameter read at
  a probed site before and after a stress costs a probe pass, while
  the same evidence recovered after dicing costs a handling operation
  per die. That is why the flow exists and why its order matters.
- The flow can only hold activities a whole wafer supports. Die shear,
  wire bond pull, die serialisation, die visual and package seal all
  need separated parts, and an activity like that sitting in a
  pre-dicing flow is a planning error, not a sequencing preference.
- A stress activity says nothing on its own. Burn-in and high
  temperature storage are judged on the change they produce, so each
  one needs a parametric measurement before it and another after it.
  An unbracketed stress has consumed schedule and produced no data.
- Drift is relative, not absolute: the change between the two readings
  over the pre-stress reading. That makes a zero pre-stress reading
  unusable rather than a special case, and it makes the limits
  comparable across parameters with different units.
- A drift landing exactly on its limit is a representation question.
  It is absorbed by a named tolerance inside the comparison, never by
  widening the engineering limit itself.
- Site acceptance and lot acceptance are two decisions. Sites are
  grouped as passing or failing on their own drifts; the lot is
  decided by comparing the failing fraction with the percentage
  defective allowed. A wafer with several failing sites can still be
  accepted, and one with a single missing reading pair need not be.

## Workflow

1. Fold each declared activity to its canonical spelling, refuse one
   that is not recognised, and refuse one declared twice.
2. Report every activity in the flow that needs separated dies; those
   invalidate a pre-dicing flow whatever the measurements show.
3. Walk the flow and report each stress activity without a parametric
   measurement both before and after it.
4. Note a flow that declares no stress activity at all — it is a
   measurement sequence, not a screen, and the reader should be told.
5. For each probed site and each monitored parameter, pair the pre and
   post readings and compute the relative drift; a parameter with only
   one of the two readings is unmeasured, not passing.
6. Group the sites: a site passes only when every monitored parameter
   is measured and inside its limit, with the boundary absorbed by the
   named tolerance.
7. Divide the failing sites by the measured sites and compare with the
   percentage defective allowed, again with the boundary absorbed,
   then return flow-invalid, rejected or accepted with findings.

## Pitfalls

- Reading a stress result without its pre-stress baseline. The post
  reading alone looks like a parametric pass; only the change carries
  the screening information, so the bracketing is checked first.
- Letting a die level activity sit in the wafer flow. It cannot be
  performed where it is written, so the flow will be re-planned mid
  campaign — and the acceptance evidence gathered so far re-examined.
- Treating an unmeasured parameter as a pass. A missing reading pair
  is silence, and grouping it with the passing sites hides exactly the
  parameter the probe pass failed to capture.
- Comparing a drift with its limit by a strict inequality. A value
  that should sit exactly on the bound can land either side of it in
  floating point; the named tolerance is what keeps the verdict
  reproducible across machines.
- Rejecting the wafer on the first failing site. The lot decision is
  the failing fraction against the allowance, and conflating the two
  scraps wafers the allowance was written to accept.

## Behavior contract (gate 3)

The activity normalisation, die level activity detection, stress
bracketing rule, relative drift computation, per-site grouping with
its unmeasured parameter handling, the failing fraction and its
comparison with the percentage defective allowed, and the
flow-invalid / rejected / accepted verdict are exercised by the gate 3
contract test:
scripts/test_q6012_wafer_screening_and_acceptance_testing.py against
scripts/q6012_wafer_screening_and_acceptance_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_wafer_screening_and_acceptance_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
