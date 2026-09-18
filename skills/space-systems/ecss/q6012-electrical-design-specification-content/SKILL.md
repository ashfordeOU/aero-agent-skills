---
name: q6012-electrical-design-specification-content
description: "Evaluate whether the electrical design specification written for a microwave monolithic integrated circuit states the performance, interface and operating-condition data that circuit design needs, under ECSS-Q-ST-60-12 clause 7.2.1. Use when a draft MMIC electrical specification is submitted and someone must release or hold it before circuit design starts: name the mandated parameters it omits, refuse a limit whose minimum exceeds its maximum, flag a parameter given without the unit or the test condition that makes it verifiable, check every stated condition against the declared temperature and supply envelope, confirm each RF and DC interface carries an impedance and a bias definition, and return a completeness ratio with a verdict. Trigger: ecss, q-st-60-12, mmic-electrical-design-specification, mmic-performance-parameter-limits, mmic-specification-test-conditions, mmic-operating-condition-envelope, mmic-interface-definition-completeness."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-electrical-design-specification-content, mmic-performance-parameter-limits, mmic-specification-test-conditions, mmic-operating-condition-envelope, mmic-interface-definition-completeness, mmic-specification-release-or-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMICs — Electrical Design Specification Content (space-systems/ecss/q6012-electrical-design-specification-content)

Use when the task is the electrical-design-specification step of
ECSS-Q-ST-60-12 clause 7.2.1 — deciding whether the performance parameters,
the interfaces and the operating conditions written down before a microwave
circuit is designed are complete enough to design against, so the draft is
released or held with the gap named.

## Domain quick reference

- This document is the input to circuit design, not a record of it. Every
  decision the designer makes about topology, device periphery, matching and
  bias comes from it, so a quantity it does not bound is a quantity the
  designer is free to choose and nobody can later reject.
- The mandated performance parameters are the operating frequency band,
  small-signal gain, gain flatness, noise figure, output power, input and
  output return loss, supply voltage and supply current. A project may add
  parameters of its own; an addition is reported, and it never fills a gap in
  the mandated set.
- A bound is only meaningful with its unit and its test condition. Gain in dBm,
  supply current in amperes, or a noise figure with no stated temperature and
  bias, are all statements that cannot be verified on a wafer or at incoming
  inspection, which makes them indistinguishable from an absent requirement.
- One bound is enough where the quantity is one-sided — a maximum noise figure,
  a minimum output power — so a parameter is refused only when it states
  neither. A minimum above its maximum is a different thing: the requirement is
  unsatisfiable and is refused as an input error rather than reported.
- The operating envelope governs the conditions, not the other way round. A
  parameter stated at a temperature or a supply voltage the circuit is never
  required to survive is either a wrong condition or a wrong envelope, and both
  are found by comparing them rather than by reading either alone.
- Interfaces carry their own obligations. An RF port without a reference
  impedance leaves return loss undefined, and a DC port without a bias voltage
  leaves the supply parameters unanchored. A ground reference has to be named
  even though it carries no number.

## Workflow

1. Validate the declared operating envelope: an ordered ambient temperature
   range and an ordered supply voltage range. An inverted range stops the
   assessment.
2. Validate every performance parameter: a canonical name, at least one bound,
   ordered bounds, and any stated condition as a real finite number. Refuse a
   parameter stated twice under two spellings.
3. Compare the declared parameters with the mandated set, reporting the
   omissions in a stable order and the project additions separately.
4. Grade each mandated parameter against the unit its quantity is stated in,
   treating an absent unit as a mismatch rather than a separate lesser defect.
5. List the parameters carrying no test condition; without one the bound cannot
   be measured and is not a requirement anybody can meet.
6. Compare every stated condition with the declared envelope, absorbing
   representation error at the bound with a named tolerance so a condition
   sitting exactly on the limit stays inside it.
7. Grade the interface definitions: every mandated port defined, every RF port
   carrying a reference impedance, every DC port carrying a bias voltage.
8. Return the completeness ratio over the mandated parameters and ports, and
   release the draft only when it carries no finding at all.

## Pitfalls

- Reading a populated parameter table as a complete specification. Coverage is
  measured against the mandated set; a long table of project parameters can sit
  beside an unbounded noise figure.
- Accepting a bound because a number is present. A number with no unit and no
  test condition is an aspiration, and it passes a table-of-contents review
  while failing at the first measurement.
- Repairing a minimum above its maximum by swapping the two. The pair as
  written is unsatisfiable and somebody has to say which one was meant; the
  swap invents a requirement nobody wrote.
- Widening the operating envelope so an out-of-range test condition fits. The
  envelope is the mission requirement; moving it to absorb a condition changes
  what the circuit has to survive.
- Treating a one-sided quantity as incomplete. A maximum noise figure is a
  whole requirement, and demanding a minimum for it produces a defect report
  the designer cannot act on.
- Leaving the ground reference out because it carries no number. An undefined
  ground is what makes two otherwise identical return-loss measurements
  disagree.

## Behavior contract (gate 3)

The envelope validation, parameter validation and ordered-bound refusal, the
mandated-parameter coverage, unit grading, test-condition list, envelope
comparison, interface grading, the completeness ratio and the release verdict
are exercised by the gate 3 contract test:
scripts/test_q6012_electrical_design_specification_content.py against
scripts/q6012_electrical_design_specification_content_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_electrical_design_specification_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
