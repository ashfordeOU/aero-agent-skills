---
name: e2008-reverse-bias-test-purpose
description: "Determine what a reverse-bias test must deliver before a photovoltaic cell assembly is called undegraded. Use when scoping or reviewing the ECSS-E-ST-20-08C clause 6.4.3.14.1 purpose: check that every performance parameter the purpose rests on was characterised on both sides of the exposure, derive maximum power from the knee pair rather than trusting a reported number, compute the fractional loss in short-circuit current, open-circuit voltage and maximum power, compare each against its declared allowance, and confirm the allowance stands clear of the measurement uncertainty so a real loss is separable from instrument noise. Trigger: ecss, e-st-20-08c-clause-6-4-3-14-1, solar-cell-assembly-reverse-bias-purpose, reverse-bias-performance-degradation, pre-and-post-exposure-characterisation, degradation-allowance-versus-measurement-uncertainty, maximum-power-retention-after-reverse-bias, reverse-bias-shunt-path-formation."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reverse-bias-test-purpose, solar-cell-assembly-reverse-bias-purpose, reverse-bias-performance-degradation, pre-and-post-exposure-characterisation, degradation-allowance-versus-measurement-uncertainty, maximum-power-retention-after-reverse-bias]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reverse-Bias Test Purpose (space-systems/ecss/e2008-reverse-bias-test-purpose)

Use when the task is to state and defend why a cell assembly is driven into
reverse bias under ECSS-E-ST-20-08C clause 6.4.3.14.1 -- what the test has to
settle about the assembly's performance afterwards, what evidence that
question needs on both sides of the exposure, and whether the declared
allowances are coarse enough for the answer to mean anything.

## Domain quick reference

- An assembly goes into reverse bias when the string it sits in keeps
  pushing current through it while it stops producing any: a shadow edge
  crossing the wing, a cracked cell, a string mismatch. It then dissipates
  instead of generating, and the clause exists to ask one narrow question --
  after that, does it still perform as it did before?
- That makes the purpose a comparison, not a measurement. One
  post-exposure characterisation settles nothing; only a before-and-after
  pair read against a declared allowance does.
- Maximum power carries the verdict. Reverse bias degrades an assembly
  through shunt paths and localised heating, and both move the knee of the
  curve long before the open-circuit voltage or the short-circuit current
  notice. An assembly can come back with its endpoints intact and its power
  gone.
- Maximum power is a derived number, not a reported one. Taking it as the
  product of the maximum-power current and voltage makes an inconsistent
  characterisation visible instead of letting it average in.
- An allowance that sits inside the measurement uncertainty is not a
  criterion. If the instrument scatter is half a percent and the allowance
  is six tenths, a run that reports "within allowance" has reported the
  noise floor, not the assembly.

## Workflow

1. Validate the pre-exposure characterisation: short-circuit current,
   open-circuit voltage and the maximum-power pair, with the knee held
   inside the two endpoints. A maximum-power point outside them is an
   inconsistent measurement and stops the assessment there.
2. Resolve each purpose objective to the parameter it rests on, and fail the
   objective when the allowance table names no allowance for that parameter
   -- an objective without a criterion cannot be answered.
3. If no post-exposure characterisation exists, stop and report that the
   purpose is undemonstrated, per objective. An absent comparison is not a
   pass.
4. Derive maximum power on both sides and compute the fractional loss of
   every parameter that carries an allowance, absorbing representation error
   at the boundary with a named tolerance rather than by widening the
   allowance.
5. Check each allowance against its declared measurement uncertainty at the
   stated margin, and report an allowance that cannot outrun the noise as a
   finding against the evidence, not against the assembly.
6. Report per-parameter records, the findings, and an outcome in which a
   real loss outranks an unresolvable allowance -- an assembly measured
   badly and degraded is still degraded.

## Pitfalls

- Reading the endpoints as the performance. Short-circuit current and
  open-circuit voltage can survive an exposure that has already cost the
  assembly several percent of its power; only the knee moves early.
- Trusting a reported maximum power. A characterisation that reports a power
  inconsistent with its own maximum-power pair has an instrumentation or
  transcription defect, and deriving the value is what surfaces it.
- Declaring an allowance without an uncertainty. The allowance then looks
  like a criterion and behaves like one, while being smaller than the spread
  between two measurements of the same untouched assembly.
- Treating an absent post-exposure characterisation as an absent problem. No
  comparison means the purpose is undemonstrated, which is a finding, not a
  silent pass.
- Letting an evidence finding mask a degradation. A coarse allowance and a
  real loss can coexist; reporting only the evidence problem hides the
  assembly that actually lost power.

## Behavior contract (gate 3)

The characterisation validation, derived maximum power, fractional loss,
allowance comparison, allowance-versus-uncertainty resolution check,
objective coverage and the outcome precedence are exercised by the gate 3
contract test: scripts/test_e2008_reverse_bias_test_purpose.py against
scripts/e2008_reverse_bias_test_purpose_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_reverse_bias_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
