# Wave-38 leaf spec: variables-acceptance-sampling (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/variables-acceptance-sampling/
- Pack: as9100. Closest siblings: acceptance-sampling (ATTRIBUTE
  acceptance sampling: code letter, single-sampling plan n/Ac/Re, binomial
  operating characteristic - wave-37; zero variables content),
  statistical-process-control (control charts, capability), measurement-
  systems-analysis. Whole-tree grep: "variables sampling", "ANSI Z1.9",
  "MIL-STD-414", "acceptability constant k", "form Q" = ZERO owning hits
  (acceptance-sampling is attribute-only, verified). ZERO owners of the
  variables (measurement) acceptance sampling method. GENUINE MQ gap
  (fresh probe).
- Standards id: as9100 (reference-only; sibling convention - the plan
  structure paraphrases the public ANSI Z1.9 / MIL-STD-414 k-method, named
  not reproduced; no z1.9 id in standards-map.yaml). Ledger Standard:
  as9100.
- Family: manufacturing-quality

## Claim

Design and run a variables acceptance sampling plan for measured quality
characteristics: map the lot size and inspection level to the sample size
code letter, look up the sample size and the acceptability constant k for
the required AQL from an embedded reference table (paraphrased public
ANSI Z1.9 / MIL-STD-414 k-method values), form the Q statistic from the
specification limit, the sample mean and the sample standard deviation,
and decide accept or reject by comparing Q with k, including the estimated
percent-nonconforming M-method check. Produces the code letter, the sample
size, the acceptability constant, the Q statistic and the accept or reject
verdict that gate lot disposition by measurement. Does NOT do: attribute
acceptance sampling by count of nonconforming units (acceptance-sampling);
control-chart monitoring (statistical-process-control).

## Model (implement exactly)

Conventions: single specification limit (upper USL or lower LSL) k-method,
sigma unknown estimated by the sample standard deviation s (normal
distribution assumption, documented). Lot size and inspection level map to
a code letter; the embedded reference table is a small public-domain-style
subset (paraphrased values in the MIL-STD-414 tradition; treat as data,
documented as a reduced table, not the full standard).

Module table (reduced reference values in the style of the public ANSI
Z1.9 / MIL-STD-414 k-method, documented as a small training table, never
the full standard - same convention as the wave-37 attribute acceptance-
sampling leaf):
- code_letter(lot, level): level II rows (reduced): 91-150 -> E,
  151-280 -> F, 281-500 -> G, 501-1200 -> H, 1201-3200 -> J,
  3201-10000 -> K (paraphrase of the code-letter progression).
- PLAN table (normal inspection, one-sided k-method, sigma unknown):
  code E: n=15, {AQL 0.65: k 1.75, 1.0: k 1.62, 1.5: k 1.47, 2.5: k
  1.28, 4.0: k 1.09}; code F: n=20, {1.75, 1.62, 1.47, 1.28, 1.09};
  code G: n=25, same k set; code H: n=30, same k set; code J: n=35,
  same k set; code K: n=40, same k set. M (maximum allowable percent
  nonconforming, M-method): code E: 4.17/3.61/2.98/2.28/1.66; F:
  4.05/3.50/2.89/2.21/1.61; G: 3.97/3.43/2.83/2.16/1.58; H:
  3.90/3.37/2.78/2.13/1.55; J: 3.85/3.33/2.75/2.10/1.53; K:
  3.80/3.29/2.72/2.08/1.52 (paired with AQL 0.65/1.0/1.5/2.5/4.0; k
  falls as AQL loosens, M falls as AQL tightens, both monotone - the
  spec body fixes these exact values for the tests). The anchor row used
  in the worked example is code H at AQL 1.0: n=30, k=1.62, M=3.37.

Form-Q method:
- Upper limit: Q_u = (USL - xbar) / s; accept if Q_u >= k.
- Lower limit: Q_l = (xbar - LSL) / s; accept if Q_l >= k.
- M-method (estimated percent nonconforming): estimate p_hat from Q via
  the standard normal tail (in-leaf normal survival function) and compare
  with the maximum allowable percent nonconforming M for the plan
  (M = the table value paired with k; accept if p_hat <= M).

Functions (pure stdlib):
- code_letter(lot_size, level="II") -> str. ValueErrors: lot_size <= 0,
  level not in ("I", "II", "III").
- plan_lookup(code, aql) -> dict {n, k, M}. ValueErrors: unknown code or
  AQL not in the table.
- form_q_upper(usl, xbar, s) / form_q_lower(lsl, xbar, s) -> float.
  ValueError: s <= 0.
- normal_survival(z) -> float (in-leaf).
- estimated_pct_nonconforming(Q, tail="upper") -> float: 100 *
  normal_survival(Q) for an upper limit (and normal CDF for a lower
  limit).
- accept_verdict(Q, k) -> bool.
- variables_sampling_decision(lot_size, aql, usl_or_lsl, xbar, s,
  level="II") -> dict {code, n, k, M, Q, p_hat, accept}.
Identity to test: a sample mean far inside the limit gives accept; a mean
near or past the limit gives reject; the same physical margin gives
accept at a looser AQL and reject at a tighter AQL; Q and p_hat are
consistent through the normal survival function.

## Worked example

Verified at prep (the spec body reduced table; the worked example uses the
H row: lot 800, level II -> code H, n = 30 for AQL 1.0 in the training
table; k = 1.62, M = 3.37 documented values for the anchor):
- USL 50.2, xbar 49.97, s 0.12: Q_u = (50.2 - 49.97)/0.12 = 1.9167;
  accept True (1.9167 >= 1.62).
- p_hat = 100 * normal_survival(1.9167) = 2.76 percent; accept by the
  M-method (2.76 <= 3.37).
- Same stats with the LSL 49.4 (lower limit): Q_l = (49.97 - 49.4)/0.12
  = 4.75; accept True.
Run your module and take the real outputs as assert targets; the Q values
and the accept verdict are the prep-verified anchors (the reduced table
values are the module constants the spec body fixes; the builder copies
them exactly, so the acceptance verdict is deterministic).

## Validation list (contract test must include)

- code_letter boundaries (281 -> G, 501 -> H, 1201 -> J).
- plan_lookup returns the spec-body table values for the codes/AQLs in
  the tests.
- Q form and accept verdict at the worked example (Q 1.9167, accept).
- Reject case: xbar 50.1 with USL 50.2 -> Q 0.833 < k -> reject.
- Lower-limit truth table.
- p_hat = 2.76 percent at Q 1.9167 within 0.05 percent.
- ValueErrors: s <= 0, lot_size <= 0, unknown AQL/code.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-variables-acceptance-sampling.yaml)

Query 1 (copy verbatim):
  "design a variables-acceptance-sampling plan with the code letter and acceptability constant k from the lot size and AQL"
  intent: "manufacturing-quality; variables sampling plan lookup"
  expected_skill: "manufacturing-quality/as9100/variables-acceptance-sampling"
Query 2 (copy verbatim):
  "form the Q statistic from the upper specification limit and the sample standard deviation and run the mil-std-414 k-method accept verdict"
  intent: "manufacturing-quality; form-Q variables acceptance decision"
  expected_skill: "manufacturing-quality/as9100/variables-acceptance-sampling"
Task ids: w38-variables-acceptance-sampling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a variables acceptance
sampling plan:" and include the outputs in the Claim. First tag:
variables-acceptance-sampling. Additional tags ONLY: k-method,
acceptability-constant, form-q-statistic, estimated-percent-nonconforming,
code-letter-lot-size, aql-variables-plan. NEVER single generic words
(sampling, variables, acceptance, lot, AQL, limit, plan). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): attribute plan, accept number,
reject number, binomial OC curve (acceptance-sampling); control chart,
capability index (statistical-process-control).
