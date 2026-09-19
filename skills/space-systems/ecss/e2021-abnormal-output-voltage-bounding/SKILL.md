---
name: e2021-abnormal-output-voltage-bounding
description: "Assess whether every abnormal output an actuator electronics can present stays bounded by its own input supply voltage, per clause 5.5.2 of ECSS-E-ST-20-21C. Use when a fault case list has to become a bounding statement rather than a hope: take the bound from the top of the input supply envelope rather than from the nominal bus or the output rating, compare each analysed or injected fault peak against it with a named tolerance at exact equality, name the internal path that lifted any exceedance, group repeated exceedances under that path, and refuse a case list that never covered a required fault category. Trigger: ecss, e-st-20-21c, abnormal-output-voltage-bounding, input-supply-voltage-bound, actuator-fault-case-coverage, inductive-kick-path, boost-conversion-exceedance, peak-output-voltage."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-5-2, e2021-abnormal-output-voltage-bounding, e-st-20-21c, abnormal-output-voltage-bounding, input-supply-voltage-bound, actuator-fault-case-coverage, inductive-kick-path, peak-output-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Abnormal Output Voltage Bounding (space-systems/ecss/e2021-abnormal-output-voltage-bounding)

Use when the task is clause 5.5.2 of ECSS-E-ST-20-21C: whatever the
actuator electronics does when it misbehaves, the voltage it can put on
its output has to stay bounded by the voltage coming into it. This leaf
reads one fault case list and returns the bounding statement, or the
reason it cannot be made.

## Domain quick reference

- The requirement is about provenance, not about damage. The unit is
  allowed to fail; what it is not allowed to do is present potential the
  input supply never gave it, because downstream protection is sized on
  the assumption that the supply is the ceiling.
- The bound is one number, and it is the top of the input supply
  envelope. Taking the nominal bus instead understates it and fails
  cases that comply; taking the output rating instead answers a
  different requirement, since the rating is what the output is
  specified to deliver, not what a fault may present.
- An output above that bound has an internal path that lifted it, and
  the path is the finding. Stored energy in the actuator or harness
  inductance flying back when a drive stage opens, a boost stage, a
  charge pump, a transformer-coupled winding -- each is a design feature
  somebody put there, and each has a different containment.
- An exceedance with no named path is a separate finding from the
  exceedance itself. It says the case was measured but not understood,
  and a containment designed against an unidentified path is a guess.
- Grouping the exceedances under their paths turns a list of events back
  into a list of causes. One flyback path shared by six drive lines is
  one design issue, and reporting it six times hides that.
- A bounding statement is only as strong as the fault set behind it. A
  case list that never covered a required category has bounded the cases
  someone thought of, which is a coverage finding rather than a pass, and
  the coverage question is decided before the peaks are.

## Workflow

1. Resolve the bound from the input supply envelope: a positive lower
   end, an upper end not below it, and the upper end is the bound.
2. Validate each fault case: a name, a recognized fault category, a
   non-negative peak output voltage, and a recognized internal path when
   one is declared.
3. Compare each peak against the bound, absorbing floating-point
   representation error at an exact match with a named tolerance rather
   than by lifting the bound.
4. Report each exceedance in volts and as a fraction of the bound, so a
   small overshoot and a doubled output are distinguishable at a glance.
5. Name the internal path for every exceeding case, and raise a separate
   finding for an exceedance that names none.
6. Group the exceeding cases under their paths so repeated instances of
   one design feature read as one issue.
7. Check the case list against the required fault categories and raise a
   coverage finding for every category no case covered, then return the
   worst case, the groups, the gaps and the bounding token.

## Pitfalls

- Comparing the fault peaks against the nominal bus voltage. The bound
  is the top of the supply envelope; a unit qualified to a higher input
  is allowed to present that higher value, and grading it against the
  nominal figure raises findings that are not findings.
- Comparing against the output rating instead. The rating bounds what
  the output delivers in service, which is a different and usually
  lower number, so the two requirements pass and fail independently.
- Accepting an exceedance because the actuator survived it. The clause
  bounds what the interface presents, and the protection downstream of
  it was sized against the supply, not against this actuator.
- Recording an exceedance without naming the path. The containment then
  gets designed against a guess, and a second path through the same
  stage stays undiscovered.
- Reporting one shared flyback path once per drive line. That inflates
  the finding count and splits one design action into several, which is
  how the underlying feature survives the review.
- Declaring the output bounded on a case list nobody checked for
  coverage. An uncovered fault category is not a bounded case; it is an
  unasked question, and it holds the statement exactly as an exceedance
  does.

## Behavior contract (gate 3)

The supply bound resolution, fault case validation, bound comparison,
exceedance reporting, internal path naming, path grouping and required
category coverage are exercised by the gate 3 contract test:
scripts/test_e2021_abnormal_output_voltage_bounding.py against
scripts/e2021_abnormal_output_voltage_bounding_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_abnormal_output_voltage_bounding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
