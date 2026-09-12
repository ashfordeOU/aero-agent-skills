---
name: reduced-model-requirements
description: "Use when verify that a structural finite element reduced model — Craig-Bampton component mode synthesis, Guyan static condensation, or generic superelement — meets ECSS-E-ST-32 clause 4.4 requirements: confirm that all boundary interface nodes and their active degrees of freedom are completely defined, check that the retained internal mode set covers the target analysis frequency with the required margin, validate mass and frequency accuracy against the allowable fractional error limits, determine whether residual flexibility correction must be applied for truncated modal content, and assess overall reduced-model adequacy before delivery or system-level integration. Trigger: ecss, e-st-32-structures-scope, reduced-model, superelement, craig-bampton, guyan, condensation, boundary-dof, residual-flexibility, component-mode-synthesis."
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
  tags: [ecss, e-st-32-structures-scope, reduced-model, superelement, craig-bampton, guyan, condensation, boundary-dof, residual-flexibility, component-mode-synthesis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Analysis — Reduced Model Requirements (space-systems/ecss/reduced-model-requirements)

Use when the task is verifying that a structural finite element reduced
model satisfies the requirements of ECSS-E-ST-32 clause 4.4. This leaf
covers three reduction methods — Craig-Bampton component mode synthesis,
Guyan static condensation, and generic superelements — and checks
interface-node completeness, internal-mode frequency coverage, mass and
frequency accuracy, and the need for residual flexibility correction.

## Domain quick reference

- Clause 4.4 addresses reduced models formed by condensing a large
  finite element model into a compact representation that preserves
  behaviour at a defined set of boundary (interface) nodes. Three
  techniques are commonly used: Craig-Bampton, Guyan reduction, and
  generic superelements (which may use either technique internally).
  Each technique must be verifiable against the full model from which
  it was derived.
- Craig-Bampton condensation retains all boundary degrees of freedom
  and augments them with a truncated set of fixed-interface normal
  modes. The retained mode set must cover the target analysis frequency
  range with a prescribed margin (typically 1.5 times the target
  frequency); modes above the cutoff contribute residual modal mass and
  stiffness that are lost unless a residual flexibility correction is
  applied. The method is applicable across a wide frequency range and
  is the standard choice for dynamic substructuring.
- Guyan static condensation partitions the model degrees of freedom
  into master (retained) and slave (eliminated) sets. The slave
  response is recovered by a static relationship to the masters.
  Accuracy is adequate only when the target frequency is well below
  the natural frequencies associated with the slave degrees of freedom;
  when the target approaches those frequencies, dynamic content is lost
  and Craig-Bampton should be substituted. Guyan models are often
  used for quasi-static or interface-stiffness purposes.
- Interface-node completeness is a prerequisite for all three methods:
  every boundary node must be listed with the full set of active
  degrees of freedom (coded 1 through 6), and no node may appear more
  than once in the interface definition.
- Mass accuracy (fractional error between reduced and full model total
  mass) and, for Craig-Bampton, frequency accuracy (fractional error
  on the lowest retained frequencies) must both fall within the
  allowable limits before the reduced model is accepted.

## Workflow

1. Identify the reduction method applied to the model (Craig-Bampton,
   Guyan, or superelement) and confirm it is one of the three accepted
   methods. Reject any unrecognized method before continuing.
2. Verify interface-node completeness: list every boundary node, confirm
   each carries a non-empty set of active degree-of-freedom codes (1–6),
   and confirm that no node ID appears more than once. Flag every
   violation as a blocking finding.
3. For Craig-Bampton models, check that the highest retained
   fixed-interface mode frequency is at least 1.5 times the target
   analysis frequency; if it is not, flag the finding and determine
   whether residual flexibility correction is applied — its absence
   when modes are truncated below the required cutoff is also a
   blocking finding.
4. For Guyan models, check that the target analysis frequency is
   strictly below the lowest natural frequency associated with the
   slave degree-of-freedom set; when this condition is not met, flag
   the reduction method as inadequate for the intended frequency range.
   Also verify that the master degree-of-freedom count is positive and
   less than the total degree-of-freedom count.
5. For all three methods, compute the fractional mass error between
   the reduced model and the full model; flag an exceedance of the
   1 % limit. For Craig-Bampton, also compute the fractional frequency
   error on the lowest retained modes; flag an exceedance of the 2 %
   limit.
6. Aggregate all findings per reduced model; the model is not accepted
   for delivery or system-level integration until every finding is
   resolved.

## Pitfalls

- Treating a Craig-Bampton model as compliant when the retained mode
  set reaches exactly the target frequency rather than 1.5 times it —
  the margin exists to capture the dynamic stiffness contribution of
  modes just above the target, which are not negligible.
- Omitting residual flexibility correction when the mode cutoff is
  below the required frequency — without this correction the reduced
  model is softer than the full model for loads near the cutoff, which
  can cause under-prediction of interface forces.
- Applying Guyan reduction at a target frequency that is a significant
  fraction of the lowest slave-mode frequency — the static relationship
  used to eliminate slave degrees of freedom is no longer accurate and
  the reduced model will misrepresent the dynamic stiffness seen at the
  master degrees of freedom.
- Accepting an interface-node list with missing degree-of-freedom codes
  or duplicate node IDs — incomplete or ambiguous boundary definitions
  lead to incorrect constraint mode computation and corrupt the reduced
  mass and stiffness matrices.
- Checking mass accuracy alone and skipping frequency accuracy for
  Craig-Bampton models — a model may conserve total mass while still
  misrepresenting the modal frequencies if the mode shapes are
  distorted by an incomplete boundary definition.

## Behavior contract (gate 3)

The reduction-method validation, interface-node completeness check,
Craig-Bampton mode-coverage and residual-flexibility logic, Guyan
frequency-range check, and mass/frequency accuracy checks are exercised
by the gate 3 contract test: scripts/test_reduced_model_requirements.py
against scripts/reduced_model_requirements_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_reduced_model_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
