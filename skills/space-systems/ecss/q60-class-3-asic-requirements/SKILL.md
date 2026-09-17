---
name: q60-class-3-asic-requirements
description: "Determine which flow of the dedicated ASIC development standard a class 3 application specific integrated circuit enters under ECSS-Q-ST-60C clause 6.6.2, and defend the tailoring that referral is granted: weigh the flight heritage behind a reuse claim on units flown, cumulative hours and whether the environment flown was as harsh as the one ahead, build the activity plan the device category carries, grade every waiver against the core activities, its justification record and the authority entitled to grant it, then take the residual risk index as the weighted share of the waivable plan given up. Use when a class 3 ASIC is developed, reused or tailored. Trigger: ecss, q-st-60c-clause-6-6-2, class-3-asic-referral, class-3-asic-tailoring-waiver, asic-flight-heritage-sufficiency, asic-waiver-approval-authority, asic-residual-risk-index."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-asic-requirements, class-3-asic-referral, class-3-asic-tailoring-waiver, asic-flight-heritage-sufficiency, asic-waiver-approval-authority, asic-residual-risk-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 ASIC Referral (space-systems/ecss/q60-class-3-asic-requirements)

Use when the task is the clause 6.6.2 referral of ECSS-Q-ST-60C: a class 3
application specific integrated circuit is on the parts list, and the general
component rules are not the text it is developed or reused under. The
dedicated ASIC and programmable device development standard is. At class 3
that referral arrives with a second half attached — the device is allowed to
enter the flow tailored, and the tailoring is the part somebody has to
defend.

## Domain quick reference

- The referral itself is not the decision. Naming the dedicated standard on a
  parts list costs nothing; what the standard then charges is an activity
  plan, and the class 3 question is how much of that plan this particular
  device is entitled to leave unrun.
- Class 3 reuse is argued on flight heritage rather than on a paper axis
  comparison. Units flown and cumulative hours say whether the claim is
  weighable at all; the environment the referenced build actually flew in says
  whether it reaches this application. A part with a thousand hours in a
  benign orbit is not heritage for a harsher one.
- The environment ratio is directional. A candidate going somewhere milder
  than the reference keeps its heritage intact; a candidate going somewhere
  harsher is a delta whatever the hour count says, because the evidence was
  taken under the gentler condition.
- Some activities are not on the table at any class. The requirements review
  belongs to this order, the functional simulation to this design, the lot
  acceptance definition to this lot, and an unarchived design cannot be
  maintained by anybody afterwards. A waiver naming one of them is a
  misunderstanding of what tailoring is for.
- A waiver is three things or it is nothing: the activity, a justification
  reference somebody can pull, and a compensating measure offered in its
  place. Two of the three is a gap with a signature on it.
- Authority is per activity, not per project. Dropping a design rule check and
  dropping the radiation evaluation are not the same decision, and the second
  is not the project's to make alone.
- Waivers do not cost the same, so they are not counted. The residual risk
  index weights each activity by the assurance it carries and reports the
  share of the waivable plan actually given up, against a limit the function
  criticality sets rather than the class alone.

## Workflow

1. Route the device. A declared new development enters the full flow with
   nothing to argue. A reuse claim is weighed on its heritage record first.
2. Test the heritage against the unit and hour floors. Below either, the claim
   is not weak — it is unweighable, and the device goes to the full flow with
   that finding recorded.
3. Compare the candidate environment against the referenced one and take the
   ratio. A modified design or a harsher environment routes to the delta flow;
   an unmodified design in an equal or milder environment allows a reviewed
   reuse.
4. Build the activity plan the flow and the device category carry, and read
   off the subset class 3 tailoring is allowed to touch.
5. Grade every requested waiver in order: a core activity is refused outright,
   a missing justification or compensating measure stops it, and the granting
   authority is checked against the one that activity demands.
6. Take the residual risk index as the weighted share of the waivable plan
   given up by the waivers that survived, and test it against the criticality
   limit.
7. Return the flow, the tailored plan, the granted waivers, the index against
   its limit and one verdict naming the first thing that stops the tailoring.

## Pitfalls

- Treating the referral as a cross-reference and running the general component
  activities anyway. Screening a device whose internal design was never
  verified grades the package and leaves the logic untested.
- Reading flight hours as heritage on their own. Hours accumulate in whatever
  environment the reference flew in, and a mild one does not reach a harsh
  application however many of them there are.
- Waiving an activity the plan never carried and counting the saving. An
  analogue characterisation waiver on a digital array removes nothing, and the
  risk index is right to ignore it.
- Signing a waiver at the wrong level because the project holds the schedule.
  The authority table exists precisely where the schedule pressure is highest,
  and a radiation evaluation dropped inside the project is a decision the
  customer never saw.
- Counting waivers instead of weighting them. Three cheap waivers and one
  radiation evaluation are not the same tailoring, and an unweighted count
  makes the second look like the safer file.
- Reading the criticality limit as a target to spend. It is the point past
  which the tailoring stops being a class 3 relaxation and starts being a
  different assurance argument, and landing just under it on a critical
  function is not the same as needing to be there.

## Behavior contract (gate 3)

The policy merge, heritage record validation, environment severity ratio,
heritage sufficiency test, flow routing, category activity plan, waivable
subset, waiver validation and findings, granted waiver set, tailored plan,
weighted residual risk index and verdict precedence are exercised by the gate
3 contract test: scripts/test_q60_class_3_asic_requirements.py against
scripts/q60_class_3_asic_requirements_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_asic_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
