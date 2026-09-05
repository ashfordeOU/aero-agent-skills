---
name: beta-factor-analysis
description: "Use when you must quantify the common-cause contribution to redundant-channel failure: split a component failure rate into the independent rate (1 - beta) * lambda and the shared common-cause rate beta * lambda, compute the common-cause shock probability Q_cc = 1 - exp(-beta * lambda * t), compute the dual-channel failure probability that combines the independent double failure with the common-cause shock by inclusion-exclusion, and compute the CCF enhancement ratio over the independence-only assumption. Produces the rate split, Q_cc, the dual-channel CCF-inclusive probability and the enhancement ratio that gate redundancy credit decisions. Trigger: beta-factor-analysis, beta-factor, common-cause-fraction, ccf-probability, common-cause-model, redundant-channel failure, common-cause shock."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [beta-factor-analysis, beta-factor, common-cause-fraction, ccf-probability, common-cause-model]
  version: 0.1.0
  author: AeroSkills
---

# Beta-Factor Common-Cause Analysis (systems-engineering-safety/arp4761a/beta-factor-analysis)

Use when the task is quantifying the common-cause contribution to
redundant-channel failure per ARP4761A common-cause practice: split the
per-channel failure rate into an independent part and a shared
common-cause part with the beta-factor model, then carry the shared
part through to the dual-channel failure probability and the CCF
enhancement ratio that gates redundancy credit. This leaf implements the
standard engineering beta-factor method in pure Python, stdlib only. It
pairs with systems-engineering-safety/arp4761a/reliability-block-diagram
for the parallel network the channels sit in and with
systems-engineering-safety/arp4761a/common-cause-analysis for the
qualitative analysis-set scope that surrounds this quantification.

## Domain quick reference

- Beta-factor split: the per-channel failure rate lambda is the sum of
  the independent rate lambda_i = (1 - beta) * lambda and the shared
  common-cause rate lambda_cc = beta * lambda, with the beta factor in
  [0, 1]. A beta of 0.1 means 10% of the failure rate is shared between
  the channels.
- Single-channel independent failure probability over exposure time t:
  q_i = 1 - exp(-(1 - beta) * lambda * t). The independent double
  failure, both channels failing on their own, is q_i^2.
- Common-cause shock probability: Q_cc = 1 - exp(-beta * lambda * t),
  the probability that the shared cause strikes within t and fails both
  channels together.
- Dual-channel CCF-inclusive failure probability: Q_dual = q_i^2 + q_c -
  q_i^2 * q_c, the inclusion-exclusion union of the independent double
  failure and the common-cause shock (their overlap q_i^2 * q_c is
  subtracted once).
- Independence-only parallel probability: (1 - exp(-lambda * t))^2,
  the beta 0 reference that assumes the channels fail independently.
- CCF enhancement ratio: Q_dual / (1 - exp(-lambda * t))^2, the factor
  by which the common-cause contribution raises dual-channel failure
  over the independence-only assumption; it is at least 1.0 and drives
  the redundancy credit decision.
- Model identities: beta 0 reduces Q_dual to (1 - exp(-lambda * t))^2
  with enhancement exactly 1.0; beta 1 reduces Q_dual to the
  single-channel 1 - exp(-lambda * t); Q_dual is monotone increasing in
  beta and in time and stays at or below 1.
- Units: failure rate in failures per hour, time in hours; beta is
  dimensionless. ARP4761A frames the common-cause analysis context; the
  beta-factor relations are standard engineering methodology,
  summary-only.

## Workflow

1. Fix the channel inputs: the per-channel component failure rate
   lambda (failures per hour), the beta factor in [0, 1], and the
   exposure time t in hours. Non-physical values (lambda at or below 0,
   beta outside the unit interval, negative time) are rejected with
   ValueError.
2. Split the failure rate with split_failure_rate into the independent
   rate (1 - beta) * lambda and the common-cause rate beta * lambda;
   the parts sum back to lambda.
3. Compute the common-cause shock probability Q_cc with
   common_cause_probability from the shared rate and the exposure time.
4. Compute the dual-channel CCF-inclusive failure probability with
   dual_channel_ccf_probability, combining the independent double
   failure q_i^2 with the common-cause shock q_c by inclusion-exclusion.
5. Compute the CCF enhancement ratio with ccf_enhancement over the
   independence-only parallel probability, and weigh it when granting
   redundancy credit.
6. Check the model identities: beta 0 reduces Q_dual to the pure
   parallel probability and the enhancement to 1.0, beta 1 reduces
   Q_dual to the single-channel probability, and Q_dual is monotone in
   beta and in time.
7. Confirm the deterministic checks by running the contract test
   python3 scripts/test_beta_factor_analysis.py.

## Worked example

A dual-redundant channel pair with per-channel failure rate lambda =
1e-5 per hour, beta factor 0.1, exposure time t = 1000 hours:

- Failure rate split (step 2): independent rate (1 - 0.1) * 1e-5 =
  9.0e-6 per hour, common-cause rate 0.1 * 1e-5 = 1.0e-6 per hour.
- Independent single-channel probability: q_i = 1 - exp(-0.009) =
  8.95962e-3, so the independent double failure q_i^2 = 8.02748e-5.
- Common-cause shock probability (step 3): Q_cc = 1 - exp(-0.001) =
  9.99500e-4.
- Dual-channel CCF-inclusive probability (step 4): Q_dual = q_i^2 + q_c
  - q_i^2 * q_c = 1.079695e-3.
- Independence-only reference: (1 - exp(-0.01))^2 = 9.90058e-5.
- CCF enhancement ratio (step 5): Q_dual / 9.90058e-5 = 10.9054: the
  shared shock dominates the dual-channel risk, so the redundancy credit
  is roughly 11 times lower than the independence-only estimate suggests.

## Verification

- split_failure_rate(1e-5, 0.1) returns independent 9.0e-6 and
  common-cause 1.0e-6 per hour with exactly the documented dict keys.
- common_cause_probability(1e-5, 0.1, 1000) returns 9.99500e-4 within
  1e-8; dual_channel_ccf_probability returns 1.079695e-3 within 1e-8;
  ccf_enhancement returns 10.9054 within 1e-3.
- Confirm the identities: beta 0 gives Q_dual equal to the pure
  parallel (1 - exp(-lambda * t))^2 and enhancement 1.0, including at
  zero time; beta 1 gives Q_dual equal to 1 - exp(-lambda * t); Q_cc and
  Q_dual are 0 at zero time.
- Confirm monotonicity: Q_dual at beta 0.05 is below Q_dual at beta
  0.2 at fixed time, and Q_dual grows with time.
- Confirm every non-positive failure rate, every beta outside [0, 1],
  and every negative time raises ValueError; ccf_enhancement with beta
  above 0 at zero time also raises ValueError.
- Run the contract test offline: python3
  scripts/test_beta_factor_analysis.py (35 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/reliability-block-diagram: the
  series and parallel network reduction the redundant channels sit in;
  its own pitfalls text defers common-cause failure quantification to
  this leaf.
- systems-engineering-safety/arp4761a/common-cause-analysis: the
  qualitative companion that checks analysis-set completeness and its
  scoring scope; it performs no CCF probability computation, so
  redundant-channel common-cause quantification routes here.
- systems-engineering-safety/arp4761a/markov-analysis: state dynamics
  for k-out-of-n redundancy under unit independence, where the beta
  factor is not carried.
- systems-engineering-safety/arp4761a/particular-risk-analysis:
  single external-event exposure assessment, distinct from the shared
  cause that binds redundant channels.
- systems-engineering-safety/arp4761a/fta-fmea: fault tree and FMEA
  context where the dual-channel CCF-inclusive probability feeds the
  top event.

## Pitfalls

- Treating beta as a failure rate: beta is a dimensionless fraction in
  [0, 1]; the shared rate is beta * lambda, and only the product has
  per-hour units.
- Granting full redundancy credit on the independence-only estimate: the
  common-cause contribution raises dual-channel failure by the
  enhancement ratio (10.9054 in the worked example), so an
  independence-only parallel probability understates the risk by an
  order of magnitude when beta is 0.1.
- Reporting Q_cc as the dual-channel probability: Q_cc is only the
  shock term that fails both channels at once; the dual-channel
  CCF-inclusive probability must add the independent double failure
  q_i^2 and subtract the overlap q_i^2 * q_c by inclusion-exclusion.
- Splitting the rate without renormalizing: raising beta must move
  rate out of the independent part, so independent plus common-cause
  parts always sum back to lambda.
- Forgetting the exposure time: Q_cc and Q_dual are functions of
  beta * lambda * t and (1 - beta) * lambda * t, so a mission time of
  zero or a mismatched time unit collapses the shock terms to zero.
- Feeding out-of-range beta: beta below 0 or above 1 is non-physical
  and must raise ValueError, not silently clamp.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_beta_factor_analysis.py

The test covers the worked-example contract (independent and
common-cause rates 9e-6 and 1e-6 per hour, Q_cc 9.99500e-4, Q_dual
1.079695e-3, enhancement 10.9054), the beta 0 and beta 1 limit
identities, zero-time behavior, monotonicity of Q_dual in beta and
time, the Q_dual unit bound, the inclusion-exclusion bounds, dict key
exactness, rate conservation, determinism, and ValueError rejection of
non-positive failure rate, out-of-range beta and negative or undefined
time.

## Compliance

- Standards referenced, not reproduced: ARP4761A (SAE, reference-only
  per standards-map.yaml); the beta-factor relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
