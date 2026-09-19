---
name: q2007-process-validation
description: "Validate a designed test process and the service built on it before formal use, under ECSS-Q-ST-20-07C clause 5.7.4.2: show from replicate runs that the process returns the answer it is supposed to, by pooling the within-group spread into a repeatability figure, separating the between-operator and between-rig spread as reproducibility, estimating bias against a reference specimen of known value, combining the three into an expanded uncertainty and comparing that with the tolerance the process must resolve. Use when a new or altered test process is being released for customer work. Returns run counts, the three components and a validated-or-not verdict. Trigger: ecss, q-st-20-07c-clause-5-7-4-2, test-process-validation-evidence, test-repeatability-pooled-spread, test-reproducibility-between-groups, reference-specimen-bias, expanded-uncertainty-capability."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-process-validation, test-process-validation-evidence, test-repeatability-pooled-spread, test-reproducibility-between-groups, reference-specimen-bias, expanded-uncertainty-capability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Validation of the Test Process (space-systems/ecss/q2007-process-validation)

Use when the task is the validation clause of ECSS-Q-ST-20-07C clause
5.7.4.2 -- the evidence a test centre produces before a designed process
is used on customer work, showing that the process as built returns
results a customer can rely on rather than results the designer expected
it to return.

## Domain quick reference

- Validation is evidence from running the process, not review of the
  document that describes it. A procedure can be internally perfect and
  still fail here, because the rig, the operators and the instruments
  are what get validated, not the intent.
- Repeatability and reproducibility are different numbers and both are
  needed. Repeatability is the spread inside one group -- same operator,
  same rig, same day; reproducibility is what changing the operator or
  the rig adds on top. A process quoted on repeatability alone looks
  better than it is in service, because service changes operators.
- Pooling is the right way to combine group spreads. Each group
  contributes its degrees of freedom, so a pooled standard deviation
  from several small groups is worth more than the spread of the best
  group and is not the plain average of the group spreads.
- Between-group scatter already contains repeatability. The spread of
  the group means is inflated by the within-group noise divided by the
  group size, so that part is subtracted before it is called
  reproducibility, and a negative result means the data does not resolve
  a reproducibility term at all.
- Bias needs an artefact of known value, and it is not a spread. A
  process can be tight and wrong; the reference specimen is what
  separates the two, and the bias enters the combined uncertainty
  alongside the two spreads rather than instead of them.
- The verdict is the comparison against what the process has to resolve.
  An expanded uncertainty is not good or bad in itself -- it is measured
  against the tolerance the process is asked to decide conformance
  against, which is where the capability ratio comes from.

## Workflow

1. Validate the run groups: each group a sequence of finite results with
   at least two runs, and enough runs in total for the validation to be
   worth quoting.
2. Compute each group's mean and sample standard deviation on n minus
   one degrees of freedom.
3. Pool the group spreads by degrees of freedom into the repeatability
   standard deviation.
4. Take the spread of the group means, subtract the repeatability
   contribution the group size already explains, and report the
   remainder as reproducibility -- flooring it at zero when the data
   does not resolve one.
5. Estimate bias as the overall mean less the reference specimen's known
   value, and compare its magnitude with the bias the process is allowed.
6. Combine repeatability, reproducibility and bias in quadrature and
   expand by the coverage factor.
7. Form the capability ratio against the tolerance and return a
   validated-or-not verdict with each failing component named.

## Pitfalls

- Averaging group standard deviations instead of pooling them. The
  average ignores group size and quietly favours whichever group was
  smallest, which is usually the one that looks tightest.
- Quoting repeatability as the process uncertainty. In service the
  operator and the rig change, and the figure the customer experiences
  is the combined one.
- Reading a small bias as no bias. A bias inside the allowance is still
  carried into the combined uncertainty; dropping it understates the
  expanded figure by exactly the amount that mattered.
- Validating on one long group. Degrees of freedom accumulate, but a
  single group cannot resolve reproducibility at all, so the process
  ships with an unmeasured component.
- Widening the tolerance to make the capability ratio pass. The
  tolerance belongs to the requirement; when the ratio is short the
  process is improved or its scope is narrowed, and a value exactly on
  the ratio limit is a representation question handled by the tolerance
  inside the comparison.

## Behavior contract (gate 3)

The run-group validation, group statistics, pooled repeatability,
between-group reproducibility with its floor, reference bias, combined
and expanded uncertainty, capability ratio and the validated-or-not
verdict are exercised by the gate 3 contract test:
scripts/test_q2007_process_validation.py against
scripts/q2007_process_validation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q2007_process_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
