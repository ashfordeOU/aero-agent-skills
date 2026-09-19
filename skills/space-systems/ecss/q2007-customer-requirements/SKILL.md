---
name: q2007-customer-requirements
description: "Evaluate a customer test request before a test centre commits to it, under ECSS-Q-ST-20-07C clause 5.7.2: check the request carries every content item the centre needs to quote and run it, compare each requested parameter against the facility envelope and against the schedule capacity left, and confirm the safety input the specimen demands actually arrived with it. Use when a request lands and someone has to answer whether the centre accepts it, accepts it against named actions, or declines. Returns the missing content, the out-of-envelope parameters with their margins, the safety gaps and a commitment decision. Trigger: ecss, q-st-20-07c-clause-5-7-2, test-request-completeness-review, facility-envelope-feasibility, test-centre-schedule-capacity, customer-safety-input, test-request-commitment-decision."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-customer-requirements, test-request-completeness-review, facility-envelope-feasibility, test-centre-schedule-capacity, customer-safety-input, test-request-commitment-decision]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Review of Customer Requirements (space-systems/ecss/q2007-customer-requirements)

Use when the task is the review-of-requirements clause of ECSS-Q-ST-20-07C
clause 5.7.2 -- the decision a test centre makes before it commits: does
the incoming test request say enough, can this facility actually deliver
it, and did the customer supply the safety input the specimen needs.

## Domain quick reference

- The review happens before commitment, not after. Once the centre has
  accepted a request it owns the schedule slot, the facility
  configuration and the safety case; a gap found afterwards is a
  contract change, whereas the same gap found here is a question back
  to the customer.
- Completeness is about content, not length. A request that names an
  objective, the specimen, the parameters to be applied, the acceptance
  criteria, a schedule window, the deliverables expected and the safety
  data of the item is reviewable; a request missing any one of those
  cannot be quoted without the centre inventing the missing part.
- Feasibility is per parameter against the facility envelope, and the
  envelope is two-sided. A level under the smallest the facility can
  hold steady is as infeasible as one over its maximum, and a requested
  parameter the envelope says nothing about is an unknown rather than a
  pass -- the centre has no evidence either way.
- Capacity is a separate axis from capability. A facility that can reach
  every requested level and has no free weeks inside the customer's
  window is still unable to take the request, and saying so early is
  what the clause is for.
- Safety input belongs to the customer and the review checks it arrived.
  A specimen declared hazardous with no safety data, or with hazards
  listed but no measures against them, is a stop; hazard entries against
  a specimen declared non-hazardous is a contradiction the customer has
  to resolve before anything is scheduled.
- The outcome is a graded decision, not a yes or no. Missing content and
  safety gaps are recoverable against named actions; an out-of-envelope
  parameter or no capacity in the window is a refusal, because no action
  by the customer changes what the facility can do.

## Workflow

1. Validate the request: identifiers and text fields non-empty, the
   requested parameters a non-empty mapping of finite numbers, the
   requested schedule a positive number of weeks, and the hazard and
   safety-data declarations real booleans.
2. List the missing content items against the mandatory set, treating a
   blank or whitespace-only field as missing rather than present.
3. Score each requested parameter against the facility envelope as
   inside, outside or unknown, absorbing float representation error at
   the envelope bounds with a named tolerance, and report how much of
   the envelope span the request leaves as margin.
4. Compare the requested duration with the capacity free inside the
   customer's window.
5. Collect the safety findings: hazardous with no data, hazardous with
   no measures, or hazards declared against a non-hazardous item.
6. Combine into a decision -- accepted, accepted against actions, or
   refused -- and return the actions and refusal reasons separately so
   the reply to the customer writes itself.

## Pitfalls

- Reading a present-but-empty field as supplied. A key that exists with
  an empty string is the commonest way an incomplete request passes a
  completeness check, so the test is on the content, not the key.
- Treating a parameter the envelope does not mention as acceptable. The
  absence of a limit is the absence of evidence; it becomes an action on
  the centre to characterise the facility, not a silent pass.
- Merging capability and capacity into one verdict. They fail for
  different reasons and are answered by different people, so a request
  refused for capacity must not read as a facility that cannot do it.
- Accepting a hazardous specimen on the promise of safety data later.
  The data is an input to the review, and scheduling before it arrives
  puts an uncharacterised hazard into the facility calendar.
- Rounding an envelope bound outward to let a request through. A request
  exactly at a bound is a representation question, handled by the
  tolerance inside the comparison; the bound itself stays where the
  facility characterisation put it.

## Behavior contract (gate 3)

The request validation, missing-content list, per-parameter envelope
scoring with its margins, capacity comparison, safety findings and the
graded commitment decision are exercised by the gate 3 contract test:
scripts/test_q2007_customer_requirements.py against
scripts/q2007_customer_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q2007_customer_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
