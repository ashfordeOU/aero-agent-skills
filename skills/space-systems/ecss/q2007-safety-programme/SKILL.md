---
name: q2007-safety-programme
description: "Audit the safety programme of a space test centre under ECSS-Q-ST-20-07C clause 5.9.1: rank each facility hazard by consequence and likelihood into a risk index and acceptance band, place its controls on the control hierarchy and refuse a severe hazard held only by a procedure, confirm the safety officer is appointed, deputised and reporting outside the test-execution line, and grade accident, incident and emergency preparedness on response plans, reporting routes and drill intervals per 5.9.1.2. Use when a centre safety programme, hazard register or emergency drill schedule has to be assessed. Trigger: ecss, q-st-20-07c, test-centre-safety-programme, safety-organization-independence, facility-hazard-risk-index, hazard-control-hierarchy, emergency-drill-interval, accident-incident-preparedness."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-safety-programme, test-centre-safety-programme, safety-organization-independence, facility-hazard-risk-index, hazard-control-hierarchy, accident-incident-preparedness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Safety Programme (space-systems/ecss/q2007-safety-programme)

Use when the task is the safety-programme step of ECSS-Q-ST-20-07C clause
5.9.1 — deciding whether the way a test centre is organised, controls its
hazards and prepares for accidents, incidents and emergencies actually
holds, rather than whether the paperwork exists.

## Domain quick reference

- The programme has three legs and none substitutes for another: who is
  accountable for safety, what holds each hazard, and what happens when a
  hazard is realised anyway. A thorough hazard register at a centre with no
  emergency response is not a safety programme.
- Risk is two-dimensional and the index only orders hazards; it never decides
  anything on its own. Consequence and likelihood both come from ordered
  categories, so the index is an integer and a band boundary is exact,
  which matters because a hazard must never sit ambiguously between bands.
- The control hierarchy is the substance of hazard control. Elimination and
  substitution remove the hazard, engineered controls and interlocks contain
  it without asking anything of a person, and warnings, procedures and
  protective equipment only ask a person not to make a mistake. A severe
  hazard held by the last group alone is a design finding, whatever its
  likelihood is claimed to be.
- A control that has not been verified is a plan, not a control. On a severe
  hazard the verification is part of the control, because the whole argument
  rests on the control behaving as assumed.
- Independence of the safety function is structural, not personal. A safety
  officer reporting into test operations is overseeing the people who direct
  the officer, and the conflict appears exactly when a test has to be
  stopped. A deputy matters for the same reason: safety cover cannot lapse
  because one person is on leave.
- Preparedness is per scenario, and a drill interval is a claim about
  currency. A response plan with a drill overdue is evidence the plan has
  not been exercised in the state the facility is in now.

## Workflow

1. Assess the organization: safety officer appointed, reporting line outside
   test execution, deputy appointed, and the trained fraction of the staff
   on shift against the required fraction, with a named tolerance at the
   boundary.
2. For each hazard, form the risk index from its consequence and likelihood
   ordinals and read its acceptance band on exact integer bounds.
3. Rank every control named for the hazard and keep the strongest; a hazard
   with no control named is an input error, not a zero-control hazard.
4. Raise a finding when a hazard sits in the unacceptable band, when a severe
   hazard's strongest control is weaker than an engineered control, or when
   a severe hazard's control is unverified.
5. For each accident, incident or emergency scenario, confirm a documented
   response plan and a reporting route, and grade the drill as current, due
   or overdue against its interval.
6. Aggregate: report the worst risk index and its band, the count of
   unacceptable hazards and overdue drills, and call the programme sound
   only when the finding list is empty.

## Pitfalls

- Reducing a hazard's risk index by arguing the likelihood down instead of
  strengthening the control. The index orders hazards; it does not control
  them, and a likelihood argument is the easiest part of the register to
  revise without changing anything physical.
- Counting a procedure or protective equipment as the control for a
  catastrophic hazard. Both depend on a person performing correctly under
  the conditions the hazard creates, which is when performance is worst.
- Accepting a hazard because every individual control is reasonable. Only the
  strongest control in the set determines what holds the hazard; adding three
  weak controls does not make an engineered one.
- Treating a due drill as overdue, or an overdue drill as a scheduling item.
  Due is the trigger to run it; overdue means the plan's currency can no
  longer be claimed.
- Appointing a safety officer inside the test-execution line and recording
  the programme as staffed. The appointment is satisfied; the independence
  the appointment exists for is not.
- Widening a required training fraction to make an exact-equality case pass.
  An equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the requirement stays as specified.

## Behavior contract (gate 3)

The risk-index construction, acceptance banding, control-hierarchy ranking,
hazard findings, drill-currency decision, scenario preparedness, safety
organization assessment and programme aggregation are exercised by the gate 3
contract test:
scripts/test_q2007_safety_programme.py against
scripts/q2007_safety_programme_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_safety_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
