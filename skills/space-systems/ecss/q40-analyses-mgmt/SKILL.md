---
name: q40-analyses-mgmt
description: "Determine the safety analysis suite an ECSS-Q-ST-40C clause 7.2 to 7.4 programme owes at a given lifecycle phase, reading the Annex A applicability matrix: resolve which analyses are mandatory and which only recommended, degrade an analysis to recommended where the worst severity carried sits below its floor, compare the resolution with the declared plan to expose missing analyses, analyses the phase has no use for and analyses due after the phase review, and report the coverage achieved. Use when an analysis plan is drafted, tailored for a phase, or audited before a project review. Trigger: ecss, q-st-40c, annex-a-analyses-applicability-matrix, safety-analysis-suite-selection, lifecycle-phase-analysis-set, safety-analysis-plan-gap, mandatory-safety-analysis."
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
  tags: [ecss, q-st-40c-safety-assurance-scope, q40-analyses-mgmt, annex-a-analyses-applicability-matrix, safety-analysis-suite-selection, lifecycle-phase-analysis-set, safety-analysis-plan-gap, mandatory-safety-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety Analyses Management (space-systems/ecss/q40-analyses-mgmt)

Use when the task is clauses 7.2 to 7.4 of ECSS-Q-ST-40C with the Annex A
matrix: deciding which safety analyses a project owes at the phase it is in,
and whether the analysis plan on the table actually delivers them in time for
the review that closes that phase.

## Domain quick reference

- The matrix has two axes, not one. An analysis is read against the phase and
  against the worst severity the project carries, so the same analysis can be
  owed outright on one project and merely advised on another at the same
  phase.
- Severity floors are what stop the suite from being a ritual. An analysis
  built for catastrophic consequences degrades to recommended on a project
  whose worst case is major, which keeps effort where the hazard is instead
  of spreading it evenly.
- Recommended is not optional-and-ignorable. It is a separate column in the
  report so a deliberate decision not to run it is visible, rather than
  landing in the same bucket as a mandatory analysis somebody forgot.
- The phase fixes a deadline, not just a scope. An analysis owed at a phase
  and scheduled after the review closing it is not planned, it is deferred,
  and the plan reads complete until the due phases are compared.
- An analysis the phase has no use for is also a finding. Running a
  design-stage analysis in a concept phase consumes the budget the owed
  analyses need and produces a result nothing is ready to act on.
- Coverage is a ratio over the mandatory set only. Counting the recommended
  ones in flatters a plan that skipped an owed analysis, which is the one
  number a reviewer must not be given.

## Workflow

1. Validate the phase, the worst severity carried and the plan, refusing an
   unknown analysis name, a repeated entry or an unknown key.
2. Read the raw matrix entry for every analysis at the phase.
3. Apply the severity floor: a mandatory entry degrades to recommended when
   the worst severity does not reach the floor that analysis exists for.
4. Resolve the mandatory set and the recommended set, both in declaration
   order so two runs are comparable.
5. Compare the plan with the resolution: mandatory analyses missing,
   recommended analyses nobody took up, planned analyses the phase has no use
   for.
6. Compare each planned analysis's due phase with the current phase and flag
   every mandatory analysis due after the review that closes it.
7. Compute coverage over the mandatory set alone and report the findings
   against the named closing review.

## Pitfalls

- Reading the matrix on phase alone. The severity axis is what separates a
  proportionate suite from a ritual one, in both directions.
- Folding recommended analyses into the mandatory set. The plan then looks
  short whenever a team reasonably declined one, and real gaps stop standing
  out.
- Accepting a plan because every owed analysis appears in it. The due phase
  is half the commitment; an analysis promised for a later phase is not
  available to the review that needs it.
- Counting recommended analyses in the coverage ratio. A plan that skipped an
  owed analysis then reports high coverage.
- Leaving an analysis in the plan after tailoring moved the phase. It is
  reported as planned without use rather than silently dropped, because the
  budget it holds is real.

## Behavior contract (gate 3)

The matrix shape, the phase and severity token validation, the severity-floor
degradation, the mandatory and recommended set resolution, the plan
validation, the missing/unused/not-taken-up gap split, the lateness check
against the phase review and the coverage ratio over the mandatory set are
exercised by the gate 3 contract test: scripts/test_q40_analyses_mgmt.py
against scripts/q40_analyses_mgmt_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_analyses_mgmt.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
