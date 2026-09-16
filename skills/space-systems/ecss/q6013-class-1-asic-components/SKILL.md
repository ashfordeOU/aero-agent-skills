---
name: q6013-class-1-asic-components
description: "Use when a device is offered as heritage rather than new development. Determine which assurance route a class 1 application-specific device follows under ECSS-Q-ST-60-13C clause 4.6.2: recognise a full-custom, standard-cell, gate-array or structured part and point it at the dedicated microelectronics assurance standard rather than the generic component flow, then weigh any heritage claim by comparing foundry, process node, package, design revision, temperature envelope and qualified total dose with the new application, re-opening one named development activity per difference and applying the dose margin factor before comparing. Reports the reuse credit and every re-opened activity. Trigger: ecss, q-st-60-13c-clause-4-6-2, class-1-asic-routing, microelectronics-assurance-referral, asic-heritage-reuse-delta, asic-foundry-and-node-change, asic-total-dose-margin-factor, reopened-development-activity."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-asic-components, class-1-asic-routing, microelectronics-assurance-referral, asic-heritage-reuse-delta, asic-foundry-and-node-change, asic-total-dose-margin-factor, reopened-development-activity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 ASIC Components (space-systems/ecss/q6013-class-1-asic-components)

Use when the task is the clause 4.6.2 disposal of ECSS-Q-ST-60-13C: a
class 1 parts list carries an application-specific device, and the
question is whether the generic commercial-component flow governs it at
all, or whether it belongs on the dedicated microelectronics assurance
route together with whatever a heritage claim can still carry over.

## Domain quick reference

- The distinction is who owns the design, not how the device is built.
  A full-custom, standard-cell, gate-array or structured part, and a
  hard-macro programmed to a project function, all have a function the
  project specified. A catalogue microcircuit does not, however complex
  it is, and it stays where the generic flow put it.
- The referral is a routing decision, not a waiver. Sending the device
  to the microelectronics assurance route does not lighten it; it moves
  the assurance work to a standard written for a design with no prior
  production history, which is where the development activities live.
- A heritage claim is graded attribute by attribute. Foundry, process
  node, package, design revision, temperature envelope and qualified
  total dose each carry one development activity behind them, and a
  difference in one re-opens that activity and no other. This keeps the
  outcome a list of named activities rather than a yes or no.
- The dose comparison is against the mission dose scaled by a declared
  margin factor, not against the mission dose itself. A heritage part
  that qualified to exactly the scaled figure has met the requirement,
  and the representation error at that equality belongs inside the
  comparison rather than in a loosened factor.
- Reuse has a limit. Past a declared number of re-opened activities the
  claim is describing a new development with a familiar starting point,
  and calling it reuse only hides how much work is actually open.
- No heritage record at all is not a small case of the same thing. It
  opens every activity, and it is reported that way rather than as a
  reuse claim scoring zero.

## Workflow

1. Read the declared device kind and route it. An unknown kind is an
   input error, not a device to guess at; a catalogue kind returns with
   the generic route and a note that this clause does not move it.
2. Validate the application design record: foundry, process node,
   package, design revision, temperature envelope and total dose, each
   present, each of the right type, the envelope the right way round.
3. With no heritage record, return a new development with every
   activity open, and stop.
4. Validate the heritage record the same way, then compare the four
   discrete attributes; each mismatch records a delta naming the
   attribute, both values and the activity it re-opens.
5. Compare the envelopes: the heritage range has to enclose the
   application range within the declared slack, with an exact boundary
   treated as enclosed.
6. Scale the application dose by the margin factor and compare the
   heritage dose against it, again treating an exact equality as met.
7. Reduce the deltas to the ordered set of re-opened activities, take
   the reuse credit as the share that carry over, and return one
   verdict: reuse accepted, reuse with re-opened activities, or a new
   development once the allowance is passed. Report the dose ratio, the
   scaled dose and every finding.

## Pitfalls

- Reading complexity as the test. A large catalogue microcircuit is
  still a catalogue part, and a small gate array is still application
  specific; routing on transistor count sends both the wrong way.
- Treating the referral as relief from the generic flow's screening.
  The device leaves one route and arrives on another, and the arriving
  route is the heavier of the two for a design with no production
  history behind it.
- Accepting a heritage claim on part number alone. The number survives
  a foundry move, a shrink and a repackage, which is exactly the set of
  changes that re-opens the qualification the claim was leaning on.
- Comparing the heritage dose with the mission dose and forgetting the
  factor. That passes a part with no margin at all, and the shortfall
  surfaces late, in radiation verification nobody planned for.
- Widening the margin factor so a part that lands just under it passes.
  An exact equality is a representation question the comparison already
  absorbs; a part below the figure is below it.
- Counting a missing heritage record as a reuse with a low score. There
  is nothing to carry over, so the honest output is a new development
  with the full activity set open, not a reuse claim that looks weak.

## Behavior contract (gate 3)

The kind routing, design-record validation, attribute deltas, envelope
enclosure, dose margin comparison, reuse credit and verdict precedence
are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_asic_components.py against
scripts/q6013_class_1_asic_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_asic_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
