---
name: e4008-global-event-subscription-requirements
description: "Validate the global event subscriptions a simulation configuration enters, under ECSS-E-ST-40-08 clause 5.2.5.2, and derive the dispatch order they produce. Use when the task is wiring environment-raised events to model entry points: confirming the named event is published and open to subscription rather than merely spelled correctly, that the entry point is published by the target instance and takes no arguments because a global event carries no payload, and that no entry point is subscribed to the same event twice. Trigger: ecss, e-st-40-08, global-event-subscription, simulation-environment-event-registry, model-entry-point-arity, entry-point-publication, duplicate-event-subscription, event-dispatch-order."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-global-event-subscription-requirements, global-event-subscription, simulation-environment-event-registry, model-entry-point-arity, duplicate-event-subscription, event-dispatch-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Global Event Subscription Requirements (space-systems/ecss/e4008-global-event-subscription-requirements)

Use when the task is the subscription check of ECSS-E-ST-40-08 clause
5.2.5.2 -- deciding whether the wiring a configuration makes between an
environment-raised global event and a model's entry point is well
formed, and what dispatch order the surviving subscriptions imply.

## Domain quick reference

- A global event belongs to the simulation environment, not to a
  model. The subscription therefore spans two registries: the
  environment's published events on one side and the instance's
  published entry points on the other, and the two failures look
  nothing alike to whoever has to fix them.
- Published and open to subscription are two different properties. An
  event the environment raises for its own sequencing can be visible
  and still closed; reporting it as unknown sends the reviewer looking
  for a typing mistake in a name that is perfectly correct.
- An entry point is argument-free by construction. A global event
  carries no payload, so anything with a parameter list cannot be
  dispatched to no matter how well the names line up -- and an entry
  point with a default argument is still not argument-free.
- Publication applies on the entry-point side too. An internal
  callback the model keeps for its own scheduling is not a
  subscription target even when the configuration can name it.
- Duplicates are defined by the triple, not by the entry point. The
  same entry point on two events is normal, two instances on one event
  is normal, and only the same event with the same instance and the
  same entry point is the repeat that makes dispatch ambiguous.
- The dispatch plan is the output, not a by-product. Subscribers keep
  the order the configuration entered them in, which is what makes the
  call order reproducible from the document alone; a plan built from a
  set loses it.

## Workflow

1. Build the event registry from the environment's declarations and
   the instance registry from the configuration's instances, refusing
   a duplicate event, a duplicate instance or a duplicate entry point
   before any subscription is graded.
2. For each subscription, resolve the event first, distinguishing an
   unpublished name from a published but closed one.
3. Resolve the instance, then the entry point on it, then its
   publication flag, then its arity -- reporting the first of the four
   that fails so one defect makes one finding.
4. Form the canonical event-instance-entry triple and refuse it when
   an earlier subscription already took it.
5. Build the dispatch plan from the compliant subscriptions only, in
   document order, so a rejected subscription never appears in the
   order the reviewer reads.
6. Report per-subscription verdicts over the three items, the plan,
   the number of events that ended up with subscribers, and the
   findings.

## Pitfalls

- Treating a closed event as a missing one. The name resolves; the
  defect is the permission, and the repair is a different conversation
  with whoever owns the environment.
- Subscribing an entry point that takes an argument. It reads as a
  perfectly ordinary callback and cannot be dispatched, because the
  event has nothing to pass it.
- Deduplicating on the entry point alone. One entry point legitimately
  serves several events, and collapsing those rejects a normal wiring.
- Building the dispatch plan from every subscription rather than the
  compliant ones. A plan that includes a subscription the same report
  rejected tells the reviewer two different things at once.
- Losing the entry order when forming the plan. The order is the part
  of the answer that is not recoverable from the document afterwards.
- Assuming an instance with no entry points is malformed. It is simply
  not a subscription target, and the finding belongs to the
  subscription that names it, not to the instance.

## Behavior contract (gate 3)

Event and instance registry construction, published-versus-closed
event resolution, entry-point publication and arity checking, canonical
subscription keying, duplicate detection and ordered dispatch-plan
construction are exercised by the gate 3 contract test:
scripts/test_e4008_global_event_subscription_requirements.py against
scripts/e4008_global_event_subscription_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e4008_global_event_subscription_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
