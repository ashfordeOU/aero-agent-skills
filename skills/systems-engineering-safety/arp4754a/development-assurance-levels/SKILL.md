---
name: development-assurance-levels
description: "Use when you must assign development assurance levels per ARP4754A development assurance: rate the failure condition severity into catastrophic, hazardous, major, minor, and no safety effect, map the severity onto the DAL scale A through E, assign the FDAL to each function and the IDAL to each item, and check that no item DAL is lower than its function DAL. Independence between redundant items is evaluated as the alternative to raising the item DAL, and the ARP4761A FHA severity rating feeds the assignment. Trigger: development-assurance-levels, DAL, FDAL, IDAL, severity to DAL mapping, catastrophic failure condition, DAL propagation, independence alternative."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [development-assurance-levels, dal, fdal, idal, severity-categorization, severity-to-dal-mapping, dal-propagation, arp4754a, arp4761a]
  version: 0.1.0
  author: AeroSkills
---

# Development Assurance Levels (systems-engineering-safety/arp4754a/development-assurance-levels)

Use when the task is ARP4754A development assurance assignment:
rating failure condition severity, mapping it to a development
assurance level A through E, assigning the FDAL to functions and the
IDAL to items, and checking that the item levels hold up when the
function level propagates down.

## Domain quick reference

- A failure condition is rated by severity from its effect on the
  aircraft and occupants, not from its failure rate. The five
  categories (ARP4761A FHA framing) are Catastrophic, Hazardous,
  Major, Minor, and No safety effect.
- The severity drives the development assurance level (DAL) of the
  function that can cause the failure condition. Worked numbers,
  verified by running scripts/test_development_assurance_levels.py:

| Severity | DAL | Level meaning (summary) |
|---|---|---|
| Catastrophic | A | failure condition can prevent continued safe flight and landing |
| Hazardous | B | large reduction in safety margins, serious or fatal injuries possible |
| Major | C | significant reduction in safety margins, physical distress possible |
| Minor | D | slight reduction in safety margins, passenger inconvenience |
| No safety effect | E | no effect on operational capability or safety |

- FDAL (function development assurance level) is assigned to each
  function; the most severe failure condition the function can cause
  sets its FDAL. IDAL (item development assurance level) is assigned
  to each item that implements a function.
- DAL propagation rule (paraphrase of ARP4754A): the IDAL of an item
  must not be lower than the FDAL of the function it implements unless
  an approved justification supports the lower level.
- Independence alternative: for a function with a severe failure
  condition, validated independence between redundant or dissimilar
  items (no common cause, established per the ARP4761A common-cause
  analysis) can justify a lower item IDAL than the function FDAL.
  Independence is the classic alternative to raising the DAL of every
  contributing item; the argument must be validated and approved.
- Relationship to ARP4761A: the FHA rates each failure condition
  severity, and that severity feeds the DAL mapping here. FHA severity
  rating and probability targets live in functional-hazard-assessment;
  the PSSA/SSA closure of the safety objectives lives in
  safety-assessment.

Worked anchors (all verified by the contract test):

- Failure condition "Loss of all pitch authority" for the Autopilot
  function is rated Catastrophic, so the FDAL is A and the autopilot
  items start at IDAL A; the propagation check passes.
- The same items at IDAL C would fail the propagation check for the
  FDAL A function (C is lower than A) and raise ValueError.
- A function with a Hazardous failure condition (FDAL B) and items at
  IDAL D: the reduction is not accepted without a validated
  independence argument, and is accepted with one.

## Workflow

1. Collect the failure conditions per function from the FHA worksheet
   (see functional-hazard-assessment) with the rated severity of each.
2. Confirm each severity from the effect on the aircraft and
   occupants; record the flight phase if the effect is phase dependent.
3. Map each severity to its DAL with dal_from_severity, and assign the
   FDAL to the function from its most severe failure condition.
4. Assign the initial IDAL to the items implementing the function with
   assurance_assignment: the starting point is IDAL equal to the FDAL.
5. Check every (function, item) pair with validate_dal_propagation;
   any item DAL below the function DAL must carry a justification.
6. Evaluate the independence alternative for the severe failure
   conditions: document the validated independence argument (per the
   ARP4761A common-cause analysis) before accepting a lower item IDAL,
   and confirm the bookkeeping with
   independence_justifies_lower_item_dal.
7. Record the FDAL/IDAL assignments and their justifications in the
   development plan for the certification review.

## Pitfalls

- Routing FHA severity rating here: rating failure conditions and
  mapping their probability targets belongs to
  functional-hazard-assessment; this leaf maps the rated severity to
  the DAL, it does not re-run the FHA.
- Routing the safety assessment sequence here: safety-assessment runs
  the FHA/PSSA/SSA process and selects the analysis set; this leaf
  assigns the assurance levels that the plan then references.
- Routing requirements coverage here: requirements-allocation assigns
  requirements to items and functions; DAL assignment decides the
  assurance level of those elements, not their requirement ownership.
- Confusing FDAL with IDAL: the FDAL is per function, the IDAL is per
  item, and they are assigned by different arguments that are reviewed
  separately.
- Rating severity from the failure rate: a very rare failure can still
  be catastrophic. Severity comes from the effect on the aircraft and
  occupants, never from how often the failure is expected.
- Reversing the mapping direction: severity drives the DAL; the DAL
  does not change the severity. The FHA rates severity first.
- Reading DAL E as "no process": DAL E still applies the normal
  development and verification activities; it only removes the
  additional assurance rigor of levels A through D.
- Accepting a lower IDAL without a validated independence argument:
  independence must be established and validated (common-cause
  analysis per ARP4761A); an unsubstantiated independence claim does
  not reduce the item DAL.
- Checking propagation in the wrong direction: the item DAL must be at
  or above the function DAL. A lower item DAL is the violation; a
  higher item DAL is conservative, not an error.
- Dropping the most-severe-failure-condition rule: a function with
  several failure conditions takes the FDAL of its most severe one.

## Behavior contract (gate 3)

The severity-to-DAL mapping, the FDAL/IDAL assignment, the DAL
propagation check, and the independence alternative are exercised by
the gate 3 contract test: scripts/test_development_assurance_levels.py
against scripts/development_assurance_levels_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_development_assurance_levels.py

## Compliance

- Standards referenced, not reproduced: ARP4754A / ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml. The severity
  categories and the A through E mapping are common development
  assurance methodology summarized here.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.
