---
name: q6012-design-models-and-tools
description: "Validate the simulation models, foundry design kit and tools an MMIC development runs on, against ECSS-Q-ST-60-12C clause 5.3: compare each model's validated frequency, bias and temperature envelope with the envelope the design actually exercises, match every model to the process release the wafers are run on, hold measurement-correlation error inside tolerance, require electromagnetic verification of passive structures once the band reaches the frequency a lumped equivalent stops holding at, and require the tools themselves to be version-controlled with validation evidence. Use when a design kit, model library or simulator version is accepted for a monolithic microwave circuit. Trigger: ecss, q-st-60-12c-clause-5-3, mmic-design-kit-acceptance, mmic-model-usage-envelope, mmic-process-release-model-match, mmic-model-correlation-error, mmic-passive-electromagnetic-verification, mmic-simulation-tool-control."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-design-models-and-tools, mmic-design-kit-acceptance, mmic-model-usage-envelope, mmic-process-release-model-match, mmic-model-correlation-error, mmic-passive-electromagnetic-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Design Models and Tools (space-systems/ecss/q6012-design-models-and-tools)

Use when the task is the clause 5.3 step of ECSS-Q-ST-60-12C: deciding
whether the models, the foundry design kit and the simulation software a
monolithic microwave circuit is being designed with are fit to carry that
design to a mask set. The question is not whether the simulator converges
— it is whether the numbers it converges on were fitted to measurements
that reach as far as the design does.

## Domain quick reference

- A microwave model is a fit, and a fit has an envelope. It was extracted
  from measurements taken over a frequency span, a bias span and a
  temperature span, and it says nothing dependable outside them. A model
  that covers 1 GHz to 28 GHz is not a model for a 30 GHz amplifier, even
  though the simulator will return a number for 30 GHz without comment.
- The envelope is three-axis, and a design can leave it on the axis
  nobody is watching. A device model validated to 40 GHz but only over a
  laboratory temperature range is short on the axis that a qualification
  thermal cycle exercises, and the frequency headroom hides it.
- A design kit belongs to a process release. The foundry re-extracts its
  models when the process moves, so a kit version and a wafer-run release
  are one pair, not two facts. Simulating on last year's kit and
  fabricating on this year's process is a finding on the kit whatever the
  simulation says.
- Correlation error is the model's own declared accuracy against measured
  parts, and it is budget spent before the design starts. It belongs in
  the margin arithmetic, not in a footnote.
- Passive structures are geometry, not device physics. A spiral inductor
  or a coupled line behaves as its lumped equivalent until the structure
  becomes an appreciable fraction of a wavelength, after which only an
  electromagnetic solution predicts it. The crossover is a frequency, and
  above it a lumped passive model is an assumption rather than a model.
- A simulation is evidence only if it can be repeated. That takes a named
  tool version under configuration control and evidence that the tool was
  validated for the analysis it is being used for.

## Workflow

1. Establish the usage envelope the design exercises: the band, the bias
   range across all operating modes, the temperature range including the
   qualification extremes, and the process release the wafers will run on.
2. For each model in the kit, compute per-axis coverage of that usage
   envelope and keep the worst axis; a coverage shortfall is refused as
   extrapolation unless the programme has explicitly allowed it.
3. Compare each model's process release with the release being fabricated
   and raise a mismatch as its own finding, independent of coverage.
4. Compare each model's correlation error with the tolerance the
   programme set, absorbing representation error at the boundary with a
   named tolerance rather than by widening the limit.
5. For every passive structure model, require electromagnetic
   verification once the usage band reaches the crossover frequency.
6. Assess each simulation tool for version control and validation
   evidence, so the analysis can be re-run and defended.
7. Report one verdict naming the most severe finding, the fraction of
   models that carry none, and the per-model coverage behind both.

## Pitfalls

- Reading a returned number as a valid number. A simulator extrapolates
  silently; only the envelope comparison distinguishes a prediction from
  an invention, so the check has to be made against the model card, not
  against the convergence report.
- Checking frequency coverage alone. Bias and temperature are equal axes,
  and the worst axis is usually not the one the designer was thinking
  about when they picked the model.
- Treating a kit update as an optional refresh. A kit and a process
  release move together; keeping an old kit to avoid re-simulating means
  the design is no longer for the wafers being bought.
- Leaving correlation error out of the margin. A model quoted at five
  percent has already spent part of the specification margin, and a
  design that passes only in simulation is failing that arithmetic.
- Using a lumped passive model above its crossover because the kit offers
  one. The kit offering it is not a statement that it is valid there.
- Accepting an uncontrolled tool version because the results look right.
  A result that cannot be reproduced is not evidence, and the version is
  discovered to be uncontrolled only after the design review asks.

## Behavior contract (gate 3)

The envelope validation, per-axis coverage, process-release matching,
correlation-error tolerance, passive electromagnetic rule, tool control
checks and the precedence of the reported verdict are exercised by the
gate 3 contract test:
scripts/test_q6012_design_models_and_tools.py against
scripts/q6012_design_models_and_tools_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_design_models_and_tools.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
