---
name: e2008-long-duration-life-test-process
description: "Use when selecting or auditing a long duration life test approach. Determine which of the four long duration life test approaches ECSS-E-ST-20-08C clause 6.4.3.18.2 accepts the supplier has chosen, and whether that choice is documented: refuse a name off the closed menu and a subgroup declared two ways at once, hold each approach to its own evidence set so an accelerated run carries the activation energy a real time run does not, convert the approach into the laboratory hours it costs, and weigh those against the window the programme has left. Trigger: ecss, e-st-20-08c, clause-6-4-3-18-2, long-duration-life-test-approach-selection, accepted-life-test-approach-menu, life-test-approach-documentation-record, laboratory-hours-feasibility-window, qualified-heritage-equivalence-argument."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-long-duration-life-test-process, long-duration-life-test-approach-selection, accepted-life-test-approach-menu, life-test-approach-documentation-record, laboratory-hours-feasibility-window, qualified-heritage-equivalence-argument]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Long Duration Life Test Process (space-systems/ecss/e2008-long-duration-life-test-process)

Use when the task is the clause 6.4.3.18.2 step of ECSS-E-ST-20-08C: the
supplier has to pick one of the four accepted long duration life test
approaches for a photovoltaic assembly and write down what that choice
commits the campaign to, and somebody has to decide whether the pick and the
record behind it hold.

## Domain quick reference

- The menu is closed and it has four entries: a real time run at
  representative conditions, an accelerated temperature run, an accelerated
  cycling run, and an equivalence argument against previously qualified
  hardware. An approach that is not one of those four is outside the clause,
  and that is a finding to raise before the article is in a chamber rather
  than in the test report afterwards.
- The selection is singular. Two approaches declared together is not
  belt-and-braces; the two need different evidence and convert laboratory
  time back into service time by different arithmetic, so a subgroup run half
  each way has no single statement of what it stands for.
- The documentation set is approach-specific, and that asymmetry is the
  point. A real time run needs the article, the conditions, the schedule and
  the measurement intervals. An accelerated temperature run needs all of that
  plus the activation energy it leans on, the derivation of the factor and
  the ceiling above which the assumed mechanism is no longer the mechanism
  present. A cycling run needs the cycle, the rate and the conversion back to
  service. An equivalence argument runs nothing new, so it needs the
  reference programme, a delta analysis against it and the exposure that
  programme actually accumulated.
- Feasibility is arithmetic. A real time run costs the service hours
  themselves; an accelerated run costs those hours divided by its factor; a
  cycling run costs the required cycles divided by the achievable rate; an
  equivalence argument costs no chamber time at all but needs the reference
  exposure to reach the demand. Set that against the usable window — the
  programme window less a declared schedule margin — and an approach that
  will be abandoned at month nine is visible on day one.
- The preference order, the schedule margin and the heritage exposure ratio
  are declared policy, not physical constants: a project substitutes its own.

## Workflow

1. Read the declared approaches and normalise them, collapsing a repeated
   declaration to one entry rather than treating it as two.
2. Close the review immediately on nothing declared, on a name that is not on
   the menu, or on more than one approach declared together; each of those is
   a different finding and they are not interchangeable.
3. Look up the evidence set the selected approach owns and name every item
   the documentation record does not carry.
4. Convert the approach into the laboratory hours it implies, from the
   service hours, the acceleration factor, the cycle rate or the reference
   exposure as the approach requires.
5. Hold back the policy schedule margin from the programme window and compare
   the two, absorbing floating-point representation error at the boundary
   with a named tolerance rather than by padding the window.
6. Rank every approach the programme could actually run, so the record can
   say why the selected one was preferred over the alternatives that fit.
7. Report the selection, the evidence gaps, the hours, the usable window and
   the admissible alternatives.

## Pitfalls

- Judging feasibility before documentation. A run nobody can schedule and a
  run nobody wrote down are different problems with different owners; report
  the missing evidence first so the record can be fixed while the window is
  still open.
- Applying one evidence checklist to all four approaches. It either
  over-documents the real time run or lets the accelerated one through
  without the activation energy that is the only thing making it a life test.
- Quoting an acceleration factor as a schedule saving. The factor shortens
  the run only while it is derived; an undocumented factor shortens the run
  and the evidence together.
- Treating an equivalence argument as the cheap option. It costs no chamber
  time, which is exactly why the reference exposure and the delta analysis
  have to be real; a reference programme that ran a third of the life being
  claimed from it supports a third of the claim.
- Spending the whole programme window. A life test that finishes on the last
  day of the window has no room for the re-measurement a marginal reading
  will demand, which is what the schedule margin is held back for.

## Behavior contract (gate 3)

The closed menu, the singular selection, the approach-specific evidence sets,
the laboratory hours conversion, the usable window comparison and the
admissible alternatives ranking are exercised by the gate 3 contract test:
scripts/test_e2008_long_duration_life_test_process.py against
scripts/e2008_long_duration_life_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_long_duration_life_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
