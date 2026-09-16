---
name: e2008-bare-cell-acceptance-criteria
description: "Use when measured bare-cell currents have to become an acceptance verdict. Assess whether each measured bare cell reaches the current thresholds its source control drawing fixes under ECSS-E-ST-20-08C clause 7.3.2.2.3: refuse a threshold set carrying no drawing reference, judge every cell against both the short-circuit and the on-load minimum with a tie admissible, report each margin and name every shortfall rather than the first, take the rejected share of the lot against the declared allowance, and flag an accepted cell with almost nothing left for degradation. Trigger: ecss, e-st-20-08c-clause-7-3-2-2-3, bare-cell-acceptance-thresholds, source-control-drawing-current-minimum, bare-cell-short-circuit-current-margin, bare-cell-on-load-current-margin, bare-cell-lot-reject-allowance, marginal-bare-cell-advisory."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-acceptance-criteria, bare-cell-acceptance-thresholds, source-control-drawing-current-minimum, bare-cell-short-circuit-current-margin, bare-cell-on-load-current-margin, bare-cell-lot-reject-allowance, marginal-bare-cell-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Bare Cell Acceptance Criteria (space-systems/ecss/e2008-bare-cell-acceptance-criteria)

Use when the task is the clause 7.3.2.2.3 acceptance decision of
ECSS-E-ST-20-08C: bare cells have been measured, and each one is
admissible only if the currents measured on it reach the thresholds its
own source control drawing fixes.

## Domain quick reference

- The thresholds come from the drawing that governs this cell type.
  Not the vendor datasheet typical, not the value the last programme
  flew, not a house minimum carried forward. A verdict quoted with no
  drawing reference behind it is not a verdict against this clause, so
  an unreferenced threshold set closes the assessment instead of
  passing it.
- The judgement is per cell. A bare cell is an article that will be
  laid down or will not, so a lot mean that clears the threshold over a
  cell that does not clear it has decided nothing about that cell. This
  is the sharpest difference between a cell-level criterion and the
  averaged criteria elsewhere in the acceptance flow.
- Both currents have to reach their own minimum. A cell that clears the
  short-circuit threshold and misses the on-load one is failing exactly
  where the array design will feel it, because the string is sized from
  the on-load current; the short-circuit pass does not offset it.
- The sense is a floor in both cases -- more current is better -- so a
  cell landing exactly on a threshold is admissible and the comparison
  tolerance exists to absorb representation error rather than to widen
  the drawing.
- The drawing thresholds are themselves checked for sense before use.
  An on-load minimum above the short-circuit minimum describes no cell,
  and a threshold set with that shape is a drawing transcription defect
  rather than a hard lot.
- How many rejected cells a delivery may carry is a separate, declared
  question. It is a lot acceptance allowance, not arithmetic on the
  cells, and it does not change any individual cell's verdict.
- The margin is worth as much as the verdict. A cell accepted at half a
  per cent over the drawing and one accepted at fifteen per cent over
  carry the same word and very different remaining life, and nobody can
  recover the difference later from the word alone.

## Workflow

1. Validate the acceptance policy first: the largest rejected share the
   lot may carry and the band inside which an accepted cell counts as
   marginal. A share above one, or a marginal band above one, is
   refused rather than used.
2. Read the drawing thresholds and check them for sense: both current
   minima positive, the stated test voltage positive, and the on-load
   minimum not above the short-circuit minimum. An absent threshold
   set, or one whose drawing reference is blank, closes the assessment
   on requirement not established.
3. Validate every measured cell record: a non-blank identifier, no
   duplicate identifier, and both currents finite and positive. An
   empty measured population is refused rather than reported as a clean
   lot.
4. Judge each cell against both thresholds, admitting a tie, and record
   both margins along with the smaller of the two as the limiting
   margin. Name every threshold a cell missed, not only the first one
   found.
5. Take the rejected share of the lot and compare it against the
   declared allowance, a share landing exactly on the allowance being
   admissible.
6. Report the weakest cell and its limiting margin beside the verdict,
   and raise a marginal advisory for every accepted cell inside the
   policy band. Advisories are reported with the verdict and do not
   move it.
7. Close on one verdict: source control drawing requirement not
   established, lot reject fraction exceeded, or lot meets drawing
   limits.

## Pitfalls

- Judging the lot on its mean current. The criterion is per cell, and a
  comfortable mean over a cell that misses its threshold accepts an
  article the drawing rejects.
- Letting a short-circuit pass carry an on-load miss. They are separate
  thresholds because they answer separate questions, and the on-load
  one is the one the string sizing depends on.
- Comparing against a remembered threshold. The drawing is the only
  source of the required value, and a criterion applied from memory is
  a criterion nobody can audit.
- Judging raw bench currents. The thresholds are stated at the
  reference illumination and temperature, so uncorrected readings are
  being compared against a value they do not share a condition with.
- Reporting a pass with no margin and no weakest cell. The verdict
  alone hides the difference between a lot that comfortably clears the
  drawing and one that grazed it, and the next build has nothing to
  compare against.

## Behavior contract (gate 3)

The policy validation, drawing threshold validation, per-cell
judgement against both minima with an admissible tie, the margins and
the limiting margin, the lot reject fraction against its allowance, the
weakest cell, the marginal advisories and the acceptance verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_acceptance_criteria.py against
scripts/e2008_bare_cell_acceptance_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
