---
name: e1011-assessment-tools
description: "Use when validate human factors engineering assessment tool selection and coverage under ECSS-E-ST-10-11C §4.10.3: categorize each candidate tool into one of the four recognized families (simulation, development test, space analogue via neutral buoyancy facility or partial-gravity parabolic flight, or consensus report), confirm every identified HFE concern area is addressed by at least one tool, and verify that EVA-related concern areas are backed by a space analogue test rather than ground simulation alone. Trigger: ecss, e-st-10-11c, human-factors, hfe, assessment-tools, simulation, neutral-buoyancy, space-analogue, development-test, consensus-report."
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
  tags: [ecss, e-st-10-11c, human-factors, hfe, assessment-tools, simulation, neutral-buoyancy, space-analogue, development-test, consensus-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Engineering — Assessment Tools (space-systems/ecss/e1011-assessment-tools)

Use when the task is selecting and validating the assessment tools employed
in an HFE programme under ECSS-E-ST-10-11C §4.10.3 — confirming that each
tool belongs to a recognized family, that every identified HFE concern area
is addressed by at least one tool, and that EVA-related concerns are
covered by a space analogue test.

## Domain quick reference

- §4.10.3 defines four assessment tool families. **Simulation tools** use
  computer models, physical mockups, or virtual environments to evaluate
  crew interaction with designs before hardware exists. **Development tests**
  are ground-based functional or usability tests performed on engineering
  models; they establish that a design can be operated by the target crew
  population under representative procedural conditions. **Space analogue
  tests** include the neutral buoyancy facility (NBF), which submerges suited
  crew in a water tank to approximate the inertia environment of EVA, and
  partial-gravity parabolic flight (PF), which provides short-duration
  microgravity or fractional-g exposure. **Consensus reports** are structured
  expert panel reviews used where physical testing is not feasible; they
  cannot substitute for an analogue test when one is required.
- EVA-related HFE concern areas (suit donning, task execution in
  weightlessness, reach envelope in suit, tool handling) must be addressed
  by at least one NBF or PF analogue test. Ground simulation and expert
  review cannot replicate the biomechanical loading of a weightless
  environment, so an assessment plan that covers EVA concerns with only
  simulation or development tests is non-compliant regardless of fidelity.
- A non-EVA concern area (e.g. anthropometry, visual access, cognitive
  workload, workstation layout, display legibility) may be fully addressed
  by simulation, development test, or consensus report; no analogue
  requirement applies to those areas.

## Workflow

1. Enumerate every HFE concern area identified for the design item (from
   the task analysis, the user population characterization, and the
   operational scenario inventory). Separate EVA concern areas from
   non-EVA concern areas.
2. For each proposed assessment tool, confirm its tool_type is one of the
   five recognized families: `simulation`, `development_test`,
   `analogue_nbf`, `analogue_pf`, `consensus_report`. Reject any
   tool with an unrecognized type before it enters the plan.
3. Map each tool to the concern areas it addresses. A tool may address
   multiple concern areas; a concern area may be covered by multiple tools.
   Only the mapping from tool to concern matters — the plan is compliant
   when coverage is complete, regardless of how many tools cover any one
   area.
4. Check coverage: for each concern area, at least one tool must address it.
   Flag every concern area with no tool assigned as `concern_not_covered`.
5. For each EVA concern area that has at least one tool addressing it,
   verify that at least one of those tools is `analogue_nbf` or
   `analogue_pf`. Flag every EVA concern area covered only by
   non-analogue tools as `eva_concern_lacks_analogue`.
6. The assessment plan is compliant when both violation lists are empty.

## Pitfalls

- Accepting a high-fidelity computer simulation as sufficient evidence for
  an EVA concern area — §4.10.3 requires an analogue test (NBF or PF)
  because simulation cannot reproduce the inertial and biomechanical
  conditions of suited work in weightlessness. No fidelity argument
  overrides this requirement.
- Treating a consensus report as a substitute for analogue testing on EVA
  concerns — expert panel agreement documents the current state of
  knowledge but does not replace physical demonstration in the relevant
  gravity environment.
- Leaving a non-EVA concern area with no tool assigned and reading
  "no violation on EVA checks" as overall compliance — each concern area
  in the inventory must be addressed independently.
- Conflating `analogue_nbf` and `analogue_pf` as interchangeable — NBF
  provides sustained underwater EVA simulation appropriate for task-duration
  studies, while PF provides very short microgravity windows suited for
  discrete motion studies. Both satisfy the analogue requirement, but the
  programme manager must select the right facility for the concern's
  fidelity need.

## Behavior contract (gate 3)

The tool categorization, space-analogue identification, EVA concern
identification, coverage checking, and plan violation logic are exercised
by the gate 3 contract test:
scripts/test_e1011_assessment_tools.py against
scripts/e1011_assessment_tools_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_assessment_tools.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
