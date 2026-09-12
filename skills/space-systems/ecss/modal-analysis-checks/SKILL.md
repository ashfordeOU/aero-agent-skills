---
name: modal-analysis-checks
description: "Use when verify modal analysis outputs from a spacecraft or launch-vehicle finite element model against ECSS-E-ST-32C §5.7 acceptance criteria: confirm the rigid-body mode count equals six for a free-free model, confirm each rigid-body mode has a near-zero frequency below the programme threshold, evaluate the cumulative effective mass fraction per translational axis and confirm it meets the required minimum (typically 90 %), and check that the first elastic mode in each axis satisfies the stated minimum frequency requirement. Modes are categorized as rigid-body or elastic before any acceptance criterion is applied. Trigger: ecss, e-st-32-structures-scope, modal-analysis, effective-mass, rigid-body-modes, natural-frequency, mode-shapes, finite-element-model."
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
  tags: [ecss, e-st-32-structures-scope, modal-analysis, effective-mass, rigid-body-modes, natural-frequency, mode-shapes, finite-element-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Modal Analysis Checks (space-systems/ecss/modal-analysis-checks)

Use when the task is verifying that a finite element model's modal analysis
results satisfy the programme criteria defined in ECSS-E-ST-32C §5.7 —
covering rigid-body mode identification, effective mass participation, and
minimum frequency acceptance.

## Domain quick reference

- §5.7 defines three families of acceptance criterion applied after a normal
  modes (eigenvalue) analysis: rigid-body mode criteria, effective mass
  fraction criteria, and minimum frequency criteria.
- **Rigid-body modes** are the six zero-energy modes of an unconstrained
  (free-free) model — three translational and three rotational — with natural
  frequencies that should be negligibly small (below a programme-defined
  near-zero threshold, typically 0.01 Hz). Their count confirms the model has
  no spurious constraints or mechanism modes.
- **Effective mass fraction** measures, for each translational axis, what
  proportion of the structure's total mass participates in the computed modes.
  Summing the translational effective masses over all modes and dividing by the
  total structural mass yields the cumulative fraction; ECSS-E-ST-32C §5.7
  requires this to reach a specified minimum (often 90 %) to confirm that
  enough modes have been retained to represent the dynamic response adequately.
  Modes with near-zero effective mass contribution are still included in the
  running sum because their absence would indicate a truncated modal basis.
- **Minimum frequency** acceptance compares the first elastic-mode frequency
  (the lowest mode above the rigid-body threshold) against a programme-stated
  floor. Rigid-body modes are excluded from this comparison so their near-zero
  frequency does not create a spurious failure.

## Workflow

1. Collect the full modal output: for each mode, record the mode number,
   natural frequency, and the six effective mass components (three
   translational, three rotational). Confirm the total structural mass used
   in the FE model is recorded — it is the denominator for all fraction checks.

2. Categorize each mode as rigid-body or elastic by comparing its frequency
   against the near-zero threshold. For a free-free model, expect exactly six
   rigid-body modes; report any deviation before proceeding.

3. Verify that every mode categorized as rigid-body has a frequency strictly
   below the near-zero threshold. A mode with a frequency above the threshold
   but below the first genuine elastic mode indicates a mechanism or a
   modelling error and must be investigated before accepting the results.

4. For each translational axis (X, Y, Z), accumulate the effective mass over
   all modes in ascending mode-number order and divide by the total mass to
   form the running cumulative fraction. Check that the final cumulative
   fraction equals or exceeds the programme threshold. Report the axis, the
   achieved fraction, and the threshold for any axis that does not meet the
   criterion.

5. Identify the first elastic mode (lowest frequency above the rigid-body
   threshold) and compare it against each stated minimum frequency requirement.
   A separate requirement may apply per axis or per launch load direction;
   apply each requirement independently and report any shortfall.

6. Collect the results of steps 2–5 and produce a consolidated finding list.
   The model meets the §5.7 modal check criteria only when all of the
   following are clear: rigid-body count is correct, all rigid-body
   frequencies are below threshold, effective mass fractions meet the limit on
   every required axis, and every minimum frequency requirement is satisfied.

## Pitfalls

- Applying the effective mass fraction check without first excluding modes with
  zero or near-zero effective mass contribution leads to over-counting if the
  modal basis has been truncated; the check is on cumulative fraction, not on
  mode count, so a missing high-frequency mode with significant mass
  participation will cause a genuine failure that must not be suppressed.
- Treating a near-zero rigid-body frequency as a frequency requirement
  violation — the minimum frequency check is applied only to elastic modes;
  including rigid-body modes in the comparison will always produce a false
  failure.
- Accepting a rigid-body mode count of fewer than six without investigation —
  a constrained model may legitimately have fewer, but the constraint
  conditions must be explicitly documented and the expected count stated in the
  configuration before the check is run.
- Computing effective mass fractions along only one axis and treating the
  result as representative of all axes — coupled modes contribute differently
  to each axis, and a model may be adequate in X while under-representing mass
  in Z; all three translational axes must be checked independently.

## Behavior contract (gate 3)

The rigid-body identification, effective mass fraction, and minimum frequency
logic is exercised by the gate 3 contract test:
scripts/test_modal_analysis_checks.py against
scripts/modal_analysis_checks_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_modal_analysis_checks.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
