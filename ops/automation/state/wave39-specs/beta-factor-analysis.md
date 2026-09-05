# Wave-39 leaf spec: beta-factor-analysis (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/beta-factor-analysis/
- Pack: arp4761a. Closest siblings: common-cause-analysis (its logic module
  computes exactly two qualitative functions, zsa_zone_check and
  cca_complete; its SKILL body limits the claim to zonal safety scoring,
  analysis set completeness over ZSA/PRA/CMA, and action flags - zero
  probability math), reliability-block-diagram (its own Pitfalls text defers
  common-cause failures to common-cause-analysis, which cannot compute a
  probability), markov-analysis (k-of-n and state dynamics assume unit
  independence), particular-risk-analysis (single external-event exposure,
  not beta-factor CCF between redundant channels), fta-fmea. Whole-tree
  greps at prep: "beta factor", "beta-factor", "CCF" = 0 hits in skills/.
  GENUINE SES gap (fresh probe): the tree routes CCF quantification to a
  leaf that cannot compute it.
- Standards id: arp4761a (reference-only). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Quantify the common-cause contribution to redundant-channel failure with
the beta-factor model: split a component failure rate into the independent
rate (1 - beta) * lambda and the shared common-cause rate beta * lambda,
compute the common-cause shock probability Q_cc = 1 - exp(-beta * lambda *
t) that fails both channels, compute the dual-channel failure probability
that combines the independent double failure with the common-cause shock by
inclusion-exclusion, and compute the CCF enhancement ratio over the
independence-only assumption. Produces the rate split, Q_cc, the
dual-channel CCF-inclusive probability and the enhancement ratio that gate
redundancy credit decisions. Does NOT do: zonal safety scoring, ZSA/PRA/CMA
set coverage (common-cause-analysis); series-parallel or k-out-of-n
reliability (reliability-block-diagram); Markov state dynamics
(markov-analysis); external-event particular-risk exposure
(particular-risk-analysis).

## Model (implement exactly)

Functions (pure stdlib):
- split_failure_rate(failure_rate, beta) -> dict {"independent": (1 - beta)
  * lambda, "common_cause": beta * lambda}; ValueError if failure_rate <= 0
  or beta outside [0, 1].
- common_cause_probability(failure_rate, beta, time) -> float
  Q_cc = 1 - exp(-beta * lambda * t); ValueError if failure_rate <= 0, beta
  outside [0, 1], time < 0.
- dual_channel_ccf_probability(failure_rate, beta, time) -> float
  Q_dual = q_i^2 + q_c - q_i^2 * q_c with q_i = 1 - exp(-(1 - beta) *
  lambda * t) (independent single-channel failure probability) and
  q_c = 1 - exp(-beta * lambda * t) (common-cause shock probability), the
  inclusion-exclusion union of the independent double failure and the
  shared shock. ValueErrors as above.
- ccf_enhancement(failure_rate, beta, time) -> float
  Q_dual / (1 - exp(-lambda * t))^2, the ratio of the CCF-inclusive
  dual-channel probability to the independence-only parallel probability;
  ValueError as above and if time == 0 (division by zero is guarded by
  returning 1.0 at beta == 0 first).
Module constants: BETA_MIN = 0.0, BETA_MAX = 1.0.

Identity to test: beta = 0 reduces Q_dual to the pure-parallel
(1 - exp(-lambda*t))^2 and ccf_enhancement to 1.0; beta = 1 reduces Q_dual
to the single-unit 1 - exp(-lambda*t); Q_cc = 0 at beta = 0; Q_dual is
monotone increasing in beta and in time; Q_dual <= 1.

## Worked example

lambda = 1e-5 per hour, beta = 0.1, t = 1000 hours:
- split_failure_rate -> independent 9e-6/h, common_cause 1e-6/h.
- q_i^2 = (1 - exp(-0.009))^2 = 8.02748e-5.
- Q_cc = 1 - exp(-0.001) = 9.99500e-4.
- Q_dual = 1.079695e-3.
- Independence-only (beta 0) (1 - exp(-0.01))^2 = 9.90058e-5.
- ccf_enhancement = Q_dual / 9.90058e-5 = 10.9054.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (reproduced at prep with bc -l and stdlib
math).

## Validation list (contract test must include)

- split_failure_rate on the worked example (9e-6 and 1e-6).
- common_cause_probability = 9.99500e-4 within 1e-8.
- dual_channel_ccf_probability = 1.079695e-3 within 1e-8.
- ccf_enhancement = 10.9054 within 1e-3.
- beta 0: Q_dual equals (1 - exp(-lambda*t))^2; enhancement 1.0.
- beta 1: Q_dual equals 1 - exp(-lambda*t).
- time 0 returns Q_cc = 0, Q_dual = 0, enhancement 1.0 (beta 0 path).
- ValueErrors: lambda 0 or negative, beta -0.1 or 1.1, negative time.
- Monotonicity: Q_dual(beta=0.05) < Q_dual(beta=0.2) at fixed t.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-beta-factor-analysis.yaml)

Query 1 (copy verbatim):
  "apply the beta-factor-analysis to split the redundant-channel failure rate into the independent and the common-cause-fraction and compute the dual-channel ccf-probability"
  intent: "systems-engineering-safety; beta-factor rate split and CCF dual-channel probability"
  expected_skill: "systems-engineering-safety/arp4761a/beta-factor-analysis"
Query 2 (copy verbatim):
  "compute the common-cause-probability of the beta-factor common-cause model and the CCF enhancement over the independence-only assumption for the redundant channels"
  intent: "systems-engineering-safety; common-cause shock probability and enhancement ratio"
  expected_skill: "systems-engineering-safety/arp4761a/beta-factor-analysis"
Task ids: w39-beta-factor-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must quantify the common-cause
contribution to redundant-channel failure:" and include the outputs in the
Claim. First tag: beta-factor-analysis. Additional tags ONLY: beta-factor,
common-cause-fraction, ccf-probability, common-cause-model. NEVER single
generic words (common, cause, factor, probability, redundancy, channel).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): zsa, zonal safety, particular-risk-
analysis, common-mode-analysis, zone score (common-cause-analysis);
k-of-n, series-parallel reliability (reliability-block-diagram); state
probability, transition rate (markov-analysis); minimal cut set (fta-fmea);
RPN (manufacturing-quality risk-management).
