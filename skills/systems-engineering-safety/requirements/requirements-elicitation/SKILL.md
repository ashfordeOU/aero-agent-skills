---
name: requirements-elicitation
description: "Use when you must capture the system requirements from stakeholder needs and operational scenarios per ARP4754A: document the stakeholder needs, convert each operational scenario into candidate requirement statements, and record every candidate in the requirements elicitation log with its source. Assess each requirement statement against the quality criteria: atomicity (one shall clause), verifiability (measurable acceptance bound and an assigned method), unambiguity (no weasel words such as approximately, etc, suitable, and/or), single-verb structure, and traceability to its source; then run the elicitation completeness checklist that flags missing needs, uncovered scenarios, and unlogged candidates before the requirement enters the requirements baseline. Produces the populated elicitation log, the per-statement quality assessment, and the completeness verdict. Trigger: requirements elicitation, stakeholder needs, needs capture, operational scenarios, elicitation log, requirement statement quality."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: requirements
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: requirements
  tags: [requirements-elicitation, stakeholder-needs, needs-capture, operational-scenario, elicitation-log, requirement-statement, requirement-quality-criteria, weasel-words, unambiguity, atomicity, verifiability, completeness-checklist]
  version: 0.1.0
  author: AeroSkills
---

# Requirements Elicitation (systems-engineering-safety/requirements/requirements-elicitation)

Use when the task is capturing the system requirements from stakeholder
needs and operational scenarios: documenting the needs, converting the
scenarios into candidate requirement statements, recording the
candidates in the requirements elicitation log, assessing statement
quality against the criteria, and running the completeness checklist
before the requirements baseline.

## Domain quick reference

- Elicitation is the front end of the requirements process: the source
  material is the stakeholder needs (capability, performance, cost,
  schedule, regulatory) and the operational scenarios (how the system
  is used, in normal and degraded operation).
- Each candidate requirement statement must carry a source: the
  stakeholder need or operational scenario it came from. A statement
  with no source cannot be traced and is not ready for the baseline.
- Atomicity: a requirement statement states exactly one shall clause.
  Two shall clauses in one statement are two requirements.
- Verifiability: the statement gives a measurable acceptance bound
  (a numeric value with a bound phrase such as within, at least, not
  exceed) and has an assigned verification method (test, analysis,
  demonstration, or inspection).
- Unambiguity: no weasel words such as approximately, etc, suitable,
  or and/or; each word has one reading so two engineers agree on what
  is being required.
- Single-verb structure: the statement uses exactly one modal verb,
  the shall that states the requirement; must, will, should, or may in
  the same statement blur the obligation level.
- Completeness checklist: every stakeholder need and every operational
  scenario is covered by at least one log entry; anything uncovered is
  a gap that blocks the requirements baseline.

Worked example: the stakeholder need "pilots must know remaining fuel
at a glance" and the scenario "crew flies a 2-hour diversion at night"
produce the candidate statement "the system shall display the fuel
quantity within 1.5 percent of the measured value." It has one shall
clause, a measurable bound, no weasel words, one verb, a source, and
method test: it passes all quality criteria and is logged as ready.

## Workflow

1. Document the stakeholder needs and list the operational scenarios.
2. Convert each scenario into candidate requirement statements; each
   candidate gets one shall clause and a source.
3. Record every candidate in the requirements elicitation log with its
   source and its quality assessment.
4. Assess each statement with assess_requirement_statement: atomicity
   (count_shall_clauses), unambiguity (find_weasel_words), verifiability
   (has_measurable_bound plus the method), single-verb structure
   (check_single_verb), and traceability fields (check_traceability).
5. Run the completeness checklist with elicitation_completeness_check:
   needs and scenarios without a log entry are gaps.
6. Fix every flagged statement and every gap before the requirements
   baseline; the verdict is ready only when no issues remain.

## Pitfalls

- Writing statements from memory instead of from the stakeholder needs
  and operational scenarios; the source field on every statement is the
  trace that protects the baseline.
- Treating a statement with two shall clauses as one requirement;
  atomicity is one clause per statement, and the split happens during
  elicitation, before the baseline.
- Accepting approximately or suitable in a statement; a weasel word
  has no measurable bound and the statement cannot be verified as
  written.
- Confusing this leaf with requirements-modeling: modeling builds the
  SysML requirement diagram with derive and satisfy and verify links;
  elicitation captures and qualifies the statement text before it is
  modeled.
- Confusing this leaf with derived-requirements: derivation classifies
  requirements that have no parent trace; elicitation captures the
  source material for all requirements, derived or allocated, up front.
- Confusing this leaf with requirements-traceability: traceability maps
  links between requirement levels after the baseline; elicitation
  records the source so those links can be built later.
- Declaring the elicitation complete while a need or scenario has no
  log entry; the completeness checklist verdict is the gate.
- Skipping the verification method during elicitation; a statement
  without a method is not verifiable no matter how precise the bound.

## Behavior contract (gate 3)

The elicitation logic is exercised by the gate 3 contract test:
scripts/test_requirements_elicitation.py against
scripts/requirements_elicitation_logic.py (stdlib unittest, offline).
Run:
python3 skills/systems-engineering-safety/requirements/requirements-elicitation/scripts/test_requirements_elicitation.py

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the
  requirements development process that elicitation feeds; it is
  proprietary (SAE), summary-only per standards-map.yaml and brief 06.
  Requirement statement quality criteria (atomic, verifiable,
  unambiguous, traceable) are common systems engineering knowledge.
- compliance: STANDARDS-REF, gated: false.
