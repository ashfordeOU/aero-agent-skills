---
name: failure-rate-estimation
description: "Use when you must estimate or demonstrate aircraft system failure-rates from test or service data per ARP4761A: compute the point failure-rate estimate from the number of failures and the test-hours, derive the exact poisson chi-square upper-bound on the failure-rate at a stated confidence, apply the zero-failure rule (1.609 million test-hours demonstrate a 1e-6 per hour rate at 80 percent confidence), size the test-hours needed to demonstrate a target rate with allowed failures, and bound the MTBF. Produces the failure-rate, confidence bound, and MTBF numbers that feed the FTA, Markov, and PSSA/SSA quantitative models. Trigger: failure-rate estimation, failure rate, test-hours, chi-square, MTBF, confidence upper-bound, zero-failure rule, reliability demonstration, poisson."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [failure-rate, failure-rate-estimation, test-hours, chi-square, poisson, mtbf, upper-bound, lower-bound, zero-failure, demonstrate, arp4761a, reliability]
  version: 0.1.0
  author: AeroSkills
---

# Failure-Rate Estimation (systems-engineering-safety/arp4761a/failure-rate-estimation)

Use when the task is estimating or demonstrating a system failure rate
from test or service data: the point estimate, the exact confidence
upper-bound, the zero-failure demonstration rule, the test-hours needed
to demonstrate a target rate, and the MTBF bounds. This leaf produces
the rate numbers that feed the FTA, Markov, and PSSA/SSA quantitative
models; it does not run those models.

## Domain quick reference

- ARP4761A quantitative analyses (FTA, Markov, PSSA/SSA) need a failure
  rate per basic event. Rates come from service data, bench tests, or
  demonstration campaigns, modeled as a Poisson process with constant
  rate lambda per flight hour.
- Point estimate: lambda_hat = n / T with n failures in T test-hours.
  Worked: 5 failures in 1,000,000 h gives 5e-6 per hour and an MTBF
  point value of 200,000 h.
- Exact Poisson upper confidence bound: lambda_upper = chi2(confidence,
  2n + 2) / (2 T). Worked: n = 0, T = 1,000,000 h, 80 percent confidence
  gives chi2(0.80, 2) = 3.21888 over 2e6 = 1.60944e-6 per hour.
- Zero-failure rule: a test with zero failures demonstrates
  -ln(1 - confidence) / T. Worked: 1,000,000 h demonstrates 1.60944e-6
  per hour at 80 percent, 2.30259e-6 at 90 percent, 0.91629e-6 at 60
  percent confidence.
- Test-hours planning: T = chi2(confidence, 2n + 2) / (2 * target_rate)
  with n the allowed failures. Worked: a 1e-6 per hour rate at 80
  percent confidence with zero allowed failures needs 1.60944e6
  test-hours; at 95 percent with two allowed failures it needs
  6.29579e6 test-hours.
- MTBF lower confidence bound: 2 T / chi2(confidence, 2n + 2). Worked:
  n = 1, T = 1,000,000 h, 95 percent gives 2e6 / 9.48773 = 210,797 h.
- Acceptance probability of a plan: P(X <= k) = Q(k + 1, lambda * T)
  with X Poisson. Worked: lambda * T = 1.0 gives P(0 failures) = 0.3679
  and P(<= 1 failure) = 0.7358.
- Maximum confidence demonstrated by a zero-failure test of T hours
  against a target rate: 1 - exp(-target_rate * T). Worked: 1.60944e6 h
  against 1e-6 per hour demonstrates 80.0 percent confidence.
- Chi-square quantiles used above (standard tables): chi2(0.80, 2) =
  3.21888, chi2(0.95, 2) = 5.99146, chi2(0.95, 4) = 9.48773,
  chi2(0.95, 6) = 12.59159.

## Workflow

1. Collect the failure count n and the exposure test-hours T from test
   or service data; confirm the constant-rate (Poisson) assumption
   holds for the exposure period.
2. Compute the point estimates with point_estimate_failure_rate(n, T)
   and mtbf_estimate(n, T) (the latter requires n >= 1).
3. Derive the exact upper-bound with poisson_rate_upper_bound(n, T,
   confidence); for n = 0 cross-check against
   zero_failure_demonstrated_rate(T, confidence).
4. Plan the demonstration campaign with test_time_to_demonstrate(
   target_rate, confidence, allowed_failures).
5. Bound the MTBF with mtbf_lower_bound(n, T, confidence).
6. Check the acceptance probability of the chosen plan with
   poisson_cdf(rate, T, k) and state the demonstrated confidence with
   confidence_from_zero_failure_test(T, target_rate).
7. Feed the rate (prefer the conservative upper-bound) into the
   FTA/Markov models and compare against the PSSA/SSA probability
   requirement for the failure condition.

## Pitfalls

- Routing here, not to markov-analysis: Markov analysis models a
  system with given transition rates, availability, and MTTF; this leaf
  produces or demonstrates the rates from data before any model runs.
- Routing here, not to fta-fmea: fault tree cut-set computation consumes
  rates as inputs; the statistical estimate of those rates is this
  leaf's job.
- Routing here, not to verification-planning: assigning the
  verification method (test, analysis, demonstration, inspection) to
  each requirement belongs to the ARP4754A verification-planning leaf;
  the confidence math behind a demonstrated rate claim is this leaf.
- Quoting the point estimate as the claimed rate: with n = 0 the point
  estimate is zero, which is never the demonstrated rate; use the
  zero-failure upper-bound instead.
- Quoting 1 / lambda_hat as a demonstrated MTBF without the chi-square
  lower-bound, which understates the uncertainty for small n.
- Swapping confidence levels: chi2(0.95, 2) = 5.99146 is 86 percent
  larger than chi2(0.80, 2) = 3.21888, so the required test-hours scale
  by the same factor.
- Confusing statistical confidence with reliability: "80 percent
  confidence" does not mean "80 percent probability of no failure".
- Applying the zero-failure rule to a repairable system that actually
  failed and was repaired during the exposure; that is the two-state
  repair model in markov-analysis.
- Planning with allowed_failures = 0 but accepting failures during the
  run: re-plan with the real allowed count, or the demonstration claim
  is void.
- Forgetting the constant-rate assumption: infant mortality and wear-out
  data violate the Poisson model and the chi-square bound is not valid.
- Double-counting evidence: the same test-hours cannot both size the
  estimate and serve as independent verification of the requirement.

## Behavior contract (gate 3)

The estimation and demonstration logic is exercised by the gate 3
contract test: scripts/test_failure_rate_estimation.py against
scripts/failure_rate_estimation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_failure_rate_estimation.py

## Compliance

- Standards referenced, not reproduced: ARP4761A quantitative analysis
  methods and ARP4754A verification context are proprietary (SAE);
  summary-only per standards-map.yaml and brief 06.
- The chi-square and Poisson bounds are common reliability statistics
  (Abramowitz and Stegun table 26.7 class methods), paraphrased; no
  verbatim standard text.
- compliance: STANDARDS-REF, gated: false.
