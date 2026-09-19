---
name: q2007-tf-calibration
description: "Evaluate the calibration control of a test facility measurement chain under ECSS-Q-ST-20-07 clause 5.6.3, and say whether the chain may carry the campaign. Use when facility instrumentation has to be shown fit before a run rather than after it: refuse a chain with no calibration plan, combine the element uncertainties in quadrature, form the accuracy ratio against the tolerance the measured parameter owes, check every certificate stays valid to the last run day, and separate a certificate already expired from one expiring inside the campaign. Trigger: ecss, q-st-20-07-test-facility-clause-5-6-3, test-facility-measurement-chain-uncertainty, test-facility-calibration-certificate-validity, test-facility-calibration-accuracy-ratio, test-facility-calibration-plan-coverage."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-tf-calibration, q-st-20-07-test-facility-clause-5-6-3, test-facility-measurement-chain-uncertainty, test-facility-calibration-certificate-validity, test-facility-calibration-accuracy-ratio, test-facility-calibration-plan-coverage, test-facility-instrument-range-cover]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Facility Calibration Control (space-systems/ecss/q2007-tf-calibration)

Use when the task is clause 5.6.3 of ECSS-Q-ST-20-07: a facility
measurement chain is to be used for a campaign, a calibration plan and
its records are what stand behind it, and the question is whether the
numbers the chain will produce can be relied on for the whole run.

## Domain quick reference

- A measurement is a chain, not an instrument. A transducer, its
  conditioner, the cabling loss and the acquisition card each contribute
  uncertainty, and the chain uncertainty is their root-sum-square, not
  the worst single element and not their arithmetic sum.
- The accuracy ratio is the decision, not the uncertainty. A chain is
  fit when the tolerance the measured parameter owes is enough times
  wider than the chain uncertainty; the same chain is fit for a coarse
  parameter and unfit for a tight one.
- Calibration validity is read at the last day of the run, not at the
  day the plan was written. A certificate expiring mid-campaign has the
  same effect as one already expired, and the two are reported
  differently only because the corrective action differs.
- A chain element outside its calibrated range is uncalibrated at the
  point of use, whatever its certificate says. The range the campaign
  will drive the element to is the range that has to be covered.
- A plan that names fewer elements than the chain contains is not a
  smaller plan. The unplanned elements carry unbounded uncertainty, so
  plan coverage is measured against the chain and not against itself.
- Uncertainties combine in quadrature only when the contributions are
  independent. A declared correlated pair is added linearly before the
  quadrature step, because treating it as independent understates the
  chain.

## Workflow

1. Validate the calibration policy first: the accuracy ratio the test
   centre requires, the notice period inside which an expiry counts as
   expiring during the campaign, and the coverage the plan owes. A
   non-positive ratio is refused rather than used.
2. Refuse a chain with no calibration plan; that closes the assessment
   on the chain not being under calibration control.
3. Validate the chain elements: a label, a positive uncertainty in the
   units of the measured parameter, a calibrated range that is not
   inverted, and a certificate expiry day each.
4. Measure plan coverage across the chain, naming the elements the plan
   never mentions.
5. Check each element's calibrated range against the range the campaign
   will drive it to, and collect the elements the campaign leaves.
6. Combine the uncertainties: sum any declared correlated group
   linearly, then take the root-sum-square across the groups and the
   independent elements.
7. Form the accuracy ratio as the parameter tolerance over the chain
   uncertainty and compare it with the required value, absorbing
   representation error at the boundary with a named tolerance rather
   than by relaxing the ratio.
8. Read certificate validity against the last run day, then against the
   notice period, and close on one verdict in order: no plan, a
   certificate already expired, an element outside its calibrated range,
   plan coverage short, accuracy ratio short, a certificate expiring
   inside the campaign, or the chain fit for the campaign.

## Pitfalls

- Adding the element uncertainties arithmetically. That inflates the
  chain, fails a chain that is fit, and sends a test centre to buy
  instrumentation it did not need.
- Taking the worst element as the chain uncertainty. Three comparable
  elements combine to appreciably more than any one of them, and the
  chain is then reported better than it is.
- Reading certificate validity at the first day of the campaign. A four
  week run outlives a certificate that was valid at kickoff, and the
  data recorded after the expiry has nothing standing behind it.
- Judging a chain fit in the abstract. Fitness is against a parameter
  tolerance; without one the accuracy ratio has no denominator and the
  chain cannot be graded at all.
- Treating a correlated pair as independent to keep the quadrature
  simple. That understates the chain uncertainty and quietly inflates
  the accuracy ratio the decision rests on.

## Behavior contract (gate 3)

The policy validation, element validation, plan coverage, range cover,
the correlated-group linear sum, the root-sum-square combination, the
accuracy ratio with its boundary tolerance, certificate validity at the
last run day and inside the notice period, and the verdict ordering are
exercised by the gate 3 contract test:
scripts/test_q2007_tf_calibration.py against
scripts/q2007_tf_calibration_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_tf_calibration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
