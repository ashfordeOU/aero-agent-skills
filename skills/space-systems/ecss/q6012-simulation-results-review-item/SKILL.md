---
name: q6012-simulation-results-review-item
description: "Evaluate the simulation-results item of an ECSS-Q-ST-60-12C clause 7.3.4 die-form MMIC design review: build the corner matrix as the cross product of process, temperature and supply extremes, confirm every corner carries a run, take each specification parameter at its worst corner in the direction its target is written, and report the signed margin plus the corners nobody simulated. Use when predicted MMIC performance is tabled at a design review and the question is whether the corner coverage and the margins together support release rather than the nominal numbers alone. Trigger: ecss, q-st-60-12c-clause-7-3-4, mmic-simulation-results-review, mmic-corner-matrix-coverage, worst-corner-selection, specification-margin-fraction, flat-corner-sweep-finding, mmic-process-temperature-supply-corners."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-simulation-results-review-item, mmic-simulation-results-review, mmic-corner-matrix-coverage, worst-corner-selection, specification-margin-fraction, flat-corner-sweep-finding, mmic-process-temperature-supply-corners]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC -- Simulation Results Review Item (space-systems/ecss/q6012-simulation-results-review-item)

Use when the task is the simulation-results item of the design review of
ECSS-Q-ST-60-12C clause 7.3.4 -- taking the predicted performance shown
at the review, establishing that it was predicted over the corners the
design has to survive, and setting it against the electrical
specification targets.

## Domain quick reference

- The reviewable unit is the corner matrix, not the run list. The matrix
  is the cross product of the declared process corners, the temperature
  extremes and the supply extremes; a set of runs is only gradeable once
  every cell of that cross product carries one. Coverage is therefore
  established before a single number is compared with a target.
- Worst case is direction-dependent. A minimum-type target -- small
  signal gain, output power, efficiency -- is worst at its lowest
  sample; a maximum-type target -- noise figure, current draw, return
  loss magnitude -- is worst at its highest. Different parameters of the
  same design land their worst case at different corners, which is why
  one nominated worst corner cannot serve the whole specification.
- The useful output is a signed margin in the parameter's own units plus
  that margin as a fraction of the target, because the fraction is what
  makes two parameters in different units comparable and identifies
  which one is actually driving the design.
- A parameter whose samples do not move across the corners is the
  characteristic silent defect of this item: it usually means the sweep
  variable never reached that measurement, or the result was pasted from
  the nominal run. It is a finding even when the flat value passes.
- A run at a corner the matrix never asked for is also a finding. It
  either signals a matrix that was changed without the specification
  being updated, or a corner substituted for one that was too slow to
  converge.

## Workflow

1. Build the required corner matrix from the three declared axes,
   refusing a repeated process corner, temperature or supply, since a
   duplicated axis value silently shrinks the matrix.
2. Normalise the delivered runs onto that matrix. A corner reported
   twice is an input error; a corner outside the matrix is a finding.
3. Report the corners with no run before grading, so an incomplete set
   cannot be read as a pass on the corners that happen to be present.
4. For each specification parameter, gather its value at every covered
   corner, take the worst sample in the direction the target is written,
   and name the corner it came from.
5. Compute the signed margin and the fractional margin, treating a
   parameter that lands exactly on its target as meeting it through a
   named tolerance rather than by moving the target.
6. Flag a parameter absent from a covered corner, and a parameter whose
   spread across corners is zero.
7. Report the tightest parameter by fractional margin as the one the
   design is driven by, and pass the item only when the matrix is
   complete and every parameter is clean.

## Pitfalls

- Grading margins on a partial corner set. Missing corners are the
  finding; the margins computed over the corners that did run say
  nothing about the ones that did not.
- Nominating one worst corner for the whole specification. Gain and
  noise figure routinely bottom out at opposite process corners, so the
  worst corner is resolved per parameter.
- Comparing a maximum-type target against the lowest sample. The
  direction the target is written in decides which end of the sample set
  is the worst case; reversing it converts a breach into a comfortable
  margin.
- Accepting a parameter that reads identically at every corner. That is
  evidence the sweep did not reach it, not evidence of an insensitive
  design; the sensitivity item is where insensitivity gets demonstrated.
- Ranking parameters by absolute margin. Units differ, so 0.1 dB and
  0.1 mA are not comparable; the fractional margin is what identifies
  the driving parameter.
- Widening a target so a value that lands exactly on it passes. The
  equality is a representation question handled inside the comparison;
  the specification target stays as written.

## Behavior contract (gate 3)

The corner-matrix construction, run normalisation, coverage reporting,
worst-corner selection per direction, signed and fractional margin,
flat-sweep detection and the assembled item verdict are exercised by the
gate 3 contract test:
scripts/test_q6012_simulation_results_review_item.py against
scripts/q6012_simulation_results_review_item_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_simulation_results_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
