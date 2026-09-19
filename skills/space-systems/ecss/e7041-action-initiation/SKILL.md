---
name: e7041-action-initiation
description: "Determine whether a detected on-board event actually releases its bound request, under ECSS-E-ST-70-41C clause 6.19.5.2. Use when an event was reported and the expected command never went out, or when one noisy sensor turned a single binding into a command storm: reading the function-level switch before the per-definition one so the answer names the switch that stopped it, separating an event no definition covers from one whose definition is disarmed, releasing the request the definition already holds, treating every occurrence as its own release rather than coalescing repeats, and computing the peak release rate against a stated limit. Trigger: ecss, e-st-70-41c, event-action-initiation, event-action-release-decision, event-action-two-level-arming, event-action-release-storm, event-action-uncovered-event-detected, event-action-peak-release-rate."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-action-initiation, event-action-initiation, event-action-release-decision, event-action-two-level-arming, event-action-release-storm, event-action-peak-release-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Event-Action Initiation (space-systems/ecss/e7041-action-initiation)

Use when the task is the action initiation of ECSS-E-ST-70-41C clause
6.19.5.2 -- the two requirements that decide, at the moment an event
report is generated, whether the bound request is released and which
request that is.

## Domain quick reference

- This is the decision, not the table. The definition says what an
  event is bound to; this says what happens the instant the event
  occurs. A sound table and a silent spacecraft are entirely
  compatible, and the difference is here.
- Arming is two-level and the levels are ordered. The function-level
  switch is read first: with the function off nothing is released, the
  per-definition statuses are not consulted, and the answer for every
  occurrence is the function switch.
- The order matters for diagnosis as much as for behaviour. If the
  per-definition status were reported while the function was off, an
  operator would go and re-arm definitions that were already armed.
- No definition and a disarmed definition are different answers. The
  first is a gap in the table -- an event nobody bound to anything.
  The second is a state somebody deliberately set. They release the
  same nothing and call for opposite responses.
- The released request is the one the definition already holds. It is
  not assembled at detection time, so the release has no parameters
  to resolve, no lookups to fail and nothing to decide under whatever
  condition raised the event.
- Every occurrence is its own decision. Two detections of one event
  release the action twice, because the second detection is fresh
  evidence that the condition persists. That is the correct behaviour
  and it is also how a chattering sensor becomes a command storm.
- The storm is measurable before it is dangerous. A peak release rate
  over a stated window, compared against a limit, turns "the binding
  looks busy" into a number, and it does so without changing a single
  release decision.

## Workflow

1. Normalise the binding table: a two-part event key, an action that
   is a non-empty request, and an arming status defaulting to
   disarmed.
2. Normalise each occurrence: the generating application process, the
   event definition identifier and the detection time.
3. Walk the occurrences in order and raise a finding on any detection
   time that sits before its predecessor -- the release order is the
   detection order, so a backwards time makes the sequence unreadable.
4. Decide each occurrence with the switches read in order: function
   first, then the existence of a definition, then that definition's
   own status.
5. On a release, attach a copy of the request the definition holds, so
   nothing downstream can edit the table through the release record.
6. Record a disposition for every occurrence, released or not, and
   tally the four dispositions.
7. Count releases per event and report any event that released more
   than once, and name each uncovered event once however often it was
   detected.
8. Compute the peak release rate over the chosen window and compare it
   with the stated limit, reporting the number either way.

## Pitfalls

- Reporting the per-definition status when the function switch is what
  stopped the release. The operator re-arms definitions that were
  never disarmed and the behaviour does not change.
- Treating an uncovered event as a disarmed binding. One needs a new
  definition, the other needs an enable, and the telemetry looks the
  same from a distance.
- Coalescing repeated detections into one release. The second
  detection is evidence the condition persists; dropping it turns a
  worsening situation into a silent one.
- Building the request at detection time. Every lookup it needs is a
  lookup that can fail exactly when the spacecraft is already in the
  condition that raised the event.
- Reading the peak rate from the average. A burst of six inside a
  second averages away over a minute and is still six commands the
  link had to carry at once.
- Handing out the table's own action object with the release. Anything
  downstream that edits it has edited the definition.

## Behavior contract (gate 3)

The binding and occurrence validation, the ordered two-level arming
decision, the distinction between an uncovered event and a disarmed
definition, release of a copy of the held request, a disposition for
every occurrence, the four-way tally, per-event release counts,
once-only uncovered-event naming, backwards-time finding and the peak
release rate against a stated limit are exercised by the gate 3
contract test: scripts/test_e7041_action_initiation.py against
scripts/e7041_action_initiation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_action_initiation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
