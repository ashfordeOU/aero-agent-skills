---
name: q6012-application-approval-general-requirements
description: "Determine whether a microwave die may be approved for the application it is actually intended to serve, and by which route. Use when an ECSS-Q-ST-60-12C clause 8.1 application approval has to be established: widen every declared usage condition to its worst case in the direction of the bound it is judged against, normalise the margin on the envelope span so a temperature scale with an arbitrary zero still decides, then pick between reuse of an approval already held, a delta approval for bounded excursions, and a full application approval. A condition the envelope never bounded, or one the application never declared, is an open item rather than a pass. Trigger: ecss, q-st-60-12c-clause-8-1, die-application-approval, intended-usage-envelope, usage-condition-excursion, approval-route-selection, application-specific-approval-scope."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-application-approval-general-requirements, q-st-60-12c-clause-8-1, die-application-approval, intended-usage-envelope, usage-condition-excursion, approval-route-selection, application-specific-approval-scope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die Application Approval -- General Requirements (space-systems/ecss/q6012-application-approval-general-requirements)

Use when the task is the application-approval purpose and route of
ECSS-Q-ST-60-12C clause 8.1: a microwave die is proposed for a particular
use, the conditions that use imposes are declared, and the question is
whether the die can be approved for it and what has to be run first.

## Domain quick reference

- The approval attaches to a pairing, not to a part. It says that one die,
  built on one process, is acceptable inside one declared envelope of usage
  conditions. A die "already approved" is only approved for the envelope
  that approval was granted against, so the first question is always which
  envelope, not whether.
- The envelope bounds each condition in one direction. An upper bound is a
  maximum the usage stays under -- junction temperature, drive level, bias
  voltage, the top of the frequency band. A lower bound is a minimum the
  usage stays over, which is where the bottom of the band sits. The
  direction is a property of the condition, not a project choice.
- The value judged is the worst case, not the nominal. Tolerance, thermal
  spread and end-of-life drift open the declared value up, and the widening
  runs towards the bound: upward against a maximum, downward against a
  minimum.
- The margin is normalised on a declared span, never on the limit itself. A
  junction temperature in degrees Celsius has no physical zero, so a
  percentage of the limit is an artefact of the scale; the span is the
  range over which the bound is meaningful and it makes excursions on
  unlike conditions comparable.
- The route follows from the comparison. Everything inside a held approval
  on the same process is a reuse; a small number of bounded excursions is a
  delta approval that evaluates only what moved; anything else -- no
  approval held, a different process, an excursion past the allowance -- is
  a full application approval.
- A condition the envelope never bounded and a mandatory condition the
  application never declared are both open items. Neither is silence that
  can be read as approval, because the statement is a coverage claim as
  much as a comparison.

## Workflow

1. Validate the envelope first: every entry carries a limit, a bound
   direction and a positive span, and every condition that must be bound is
   bound in the direction its physics fixes. An envelope that is short of a
   condition stops the assessment rather than defaulting it.
2. Open each declared condition up to its worst case with the declared
   uncertainty, widening towards the bound it is judged against.
3. Take the signed margin to the limit, normalise it on the span, and
   absorb an exact equality at the bound with a named tolerance instead of
   relaxing the envelope.
4. Collect the gaps as gaps: conditions the envelope does not bound, and
   mandatory conditions the application never declared.
5. Select the route -- reuse, delta approval, or full application approval
   -- from the held approval, the process identity and the size and count
   of the excursions, and attach the duty each finding creates.
6. Close with a disposition and the tightest normalised margin, which is
   the condition the next design or mission change has to protect.

## Pitfalls

- Treating an approval as a property of the die. Carrying it across to a
  hotter, harder-driven or wider-band application re-uses a statement that
  was never made about those conditions.
- Judging the nominal usage condition. The nominal is one point of a spread
  that tolerance and end-of-life drift widen, and the approval covers the
  worst case of that spread.
- Normalising an excursion on the limit rather than on a declared span. On
  a scale whose zero is arbitrary the resulting percentage looks
  authoritative and means nothing, and the reviewer cannot see the scale
  was the problem.
- Reading an unbound condition as acceptable because nothing failed. An
  unjudged condition is an open coverage item; a bound has to exist before
  a verdict can.
- Widening the delta allowance to absorb an excursion. The allowance is a
  declared policy for what targeted evaluation can cover; stretching it to
  fit the case is how a full approval quietly becomes a paper one.
- Reusing an approval across a process change. The envelope may be
  identical and the die identifier unchanged, yet the evidence behind the
  approval was produced on other material.

## Behavior contract (gate 3)

The envelope validation, worst-case widening in both bound directions, the
span-normalised margin, the uncovered and undeclared condition findings,
the route selection across reuse, delta and full approval, approval
transferability and the final disposition are exercised by the gate 3
contract test:
scripts/test_q6012_application_approval_general_requirements.py against
scripts/q6012_application_approval_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_application_approval_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
