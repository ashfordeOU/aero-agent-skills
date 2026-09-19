---
name: e2040-device-feasibility-risk-assessment
description: "Assess whether a device development is achievable and band the risk carried into architecture work, as ECSS-E-ST-20-40C clause 5.2.6 requires: fold every feasibility driver onto a verdict, treat one unachievable driver as decisive, measure technology readiness against what the programme demands, and band each risk on its residual severity and likelihood after the declared mitigation rather than before it, counting an unowned mitigation as no mitigation at all. Use when a device development case is judged before the definition-phase review, or when a risk register is read for residuals nobody owns. Trigger: ecss, e-st-20-electrical-scope, device-feasibility-risk-assessment, feasibility-driver-verdict, device-technology-readiness-gap, residual-risk-banding, unowned-mitigation-detection, device-risk-exposure-limit."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-feasibility-risk-assessment, device-feasibility-risk-assessment, feasibility-driver-verdict, device-technology-readiness-gap, residual-risk-banding, unowned-mitigation-detection, device-risk-exposure-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Feasibility and Risk Assessment (space-systems/ecss/e2040-device-feasibility-risk-assessment)

Use when the task is the judgement duty of ECSS-E-ST-20-40C clause 5.2.6
-- saying whether the device can actually be developed with the
technology, people, money, time and supply available, and recording what
is carried forward as risk if the answer is a qualified yes.

## Domain quick reference

- Five drivers carry the judgement: technology, resources, schedule,
  cost and supply. A driver that was never assessed is not a silent
  pass; feasibility asserted over a gap reads exactly like feasibility
  demonstrated across all five.
- One driver reported unachievable is decisive. Four comfortable
  drivers do not average away the fifth, and an assessment that scores
  and means them is the assessment that ships an impossible device.
- A driver that is achievable only with an action has to name the
  action. The qualified verdict without the action is a yes with the
  condition quietly dropped.
- Technology readiness is the one driver with a number behind it. A
  device one step short is recoverable inside the phase while a
  maturation action is named; two steps short is not, and calling it a
  risk instead of an infeasibility moves the same problem later at
  higher cost.
- Risk is banded from severity and likelihood on 1..5 scales, and the
  band that governs is the RESIDUAL one, after the declared mitigation.
  Banding the initial risk and filing the mitigation beside it is how an
  unacceptable residual reaches architecture work unnoticed.
- A mitigation with no owner reduces the number on the page and nothing
  in the project, so it is treated as absent rather than as a reduction.
- Exposure is a mean of residual indices over the maximum index. It is a
  fraction that lands on a limit only by arithmetic accident, so a limit
  met exactly is met.

## Workflow

1. Fold every driver entry onto one of the five drivers and one of the
   three verdicts, refusing a repeat or an unknown key as an input
   defect, and report any driver the assessment never covered.
2. Report each unachievable driver as blocking, and each qualified
   driver that names no action as blocking too.
3. Compute the readiness gap against the required level. Report a gap
   over one step as not recoverable; report a one-step gap with no
   maturation action on the technology driver as blocking.
4. For every risk, resolve the mitigation, apply its reductions inside
   the scale, and band the residual severity and likelihood.
5. Report an unacceptable residual as blocking and a high residual as an
   owned action to carry forward; report a mitigation with no owner, and
   a risk already banding high with no mitigation at all.
6. Compute exposure across the register and compare it against the
   declared limit, absorbing representation error at the boundary.
7. Return the verdict: not-feasible on any blocking finding,
   feasible-with-actions when something is carried, feasible otherwise.

## Pitfalls

- Averaging the drivers. Feasibility is a conjunction, not a score, and
  a mean lets four green drivers carry one that cannot be done.
- Banding the initial risk and reporting that. The residual is what the
  next phase inherits; the initial band only says how much work the
  mitigation is claiming to do.
- Accepting a mitigation with no owner. It lowers the band on paper,
  nobody is accountable for it, and the risk arrives at the next review
  at its original size with the reduction already spent.
- Treating a two-step readiness gap as a risk. It is an infeasibility
  inside this phase, and recording it as a risk defers the decision past
  the point where the architecture can still change.
- Failing an exposure figure that lands exactly on its limit. A mean of
  small integers over twenty-five can sit a unit in the last place under
  the limit and red a case that is precisely on target.

## Behavior contract (gate 3)

The driver folding, verdict resolution, readiness-gap arithmetic,
mitigation resolution, residual banding, unowned-mitigation detection
and exposure-limit comparison are exercised by the gate 3 contract test:
scripts/test_e2040_device_feasibility_risk_assessment.py against
scripts/e2040_device_feasibility_risk_assessment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_feasibility_risk_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
