---
name: e7041-forward-control-definitions
description: "Maintain the real-time forwarding control definition store of a service 14 subservice under ECSS-E-ST-70-41C clause 6.14.3.2: add and delete definitions across the application process, service type and message subtype levels, absorb a narrower definition under a wider one already held, refuse an unknown application process, a delete of an entry that is not there and an add past a declared capacity limit, then answer whether a given report is covered. Use when a forwarding definition list, its capacity or its add and delete behaviour is being designed or reviewed. Trigger: ecss, e-st-70-41c, pus-service-14, real-time-forwarding-control, forward-control-definition-store, apid-service-subtype-hierarchy, forwarding-definition-capacity, definition-absorption."
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
  tags: [ecss, e-st-70-41c, pus-service-14, e7041-forward-control-definitions, real-time-forwarding-control, forward-control-definition-store, apid-service-subtype-hierarchy, forwarding-definition-capacity, definition-absorption]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Real-Time Forwarding Control — Definitions (space-systems/ecss/e7041-forward-control-definitions)

Use when the task is the forward-control definition step of
ECSS-E-ST-70-41C clause 6.14.3.2 — holding, extending and trimming the list
that says which reports a service 14 subservice forwards to the real-time
downlink, expressed at the application process, service type or message
subtype level.

## Domain quick reference

- The definition store is a three-level hierarchy, not a flat list: an
  application process, a service type inside it, a message subtype inside
  that. A definition at any level covers everything below it, so the level a
  definition sits at is what decides how much traffic it lets through.
- A wider definition absorbs the narrower ones under it. Adding an
  application process wholesale makes every service type and subtype entry
  it already held redundant, and keeping those entries afterwards leaves a
  store whose size no longer reflects what it forwards.
- Adding a narrower definition under a wider one that is already held changes
  nothing. It is not an error, but it has to be reported, because the
  operator who sent it believes they have narrowed the forwarding and they
  have not.
- The store has a hard capacity per level, and it is a real constraint: an
  add that would exceed it is refused outright rather than making room by
  dropping an entry the operator still expects to be there.
- Only an application process the subservice is able to forward at all can
  appear in a definition. An unknown one is a request error, and accepting it
  builds a store that silently never matches anything.
- Deleting an entry that is not held is an error, not an idempotent success.
  It usually means the operator is deleting at the wrong level, and reporting
  it is what stops a forwarding definition being left in place by accident.

## Workflow

1. Start from an empty store, or from one that has already been validated as
   a three-level structure of application processes, service types and
   subtypes.
2. For every add, validate the level triple first: a subtype may not be given
   without its service type, and the application process must be one the
   subservice can forward.
3. Resolve the add against what is already held. A wider entry already in
   place makes the add redundant and it is recorded as a finding; an add at
   application process level absorbs the narrower entries beneath it and that
   absorption is recorded too.
4. Check the capacity of the level being extended before writing: application
   processes in the store, service types under one application process,
   subtypes under one service type. Refuse an add that would exceed any of
   them.
5. For every delete, resolve the exact level named and refuse a delete that
   does not match an entry that is held; remove empty parents so the store
   does not keep an application process that forwards nothing.
6. Answer coverage questions from the store by walking the hierarchy from the
   widest level down, and report the store as a deterministic, sorted
   structure together with its definition count and all findings.

## Pitfalls

- Storing a subtype entry beside the application process entry that already
  covers it. The store then reports two definitions where one is live, and
  deleting the narrower one appears to change nothing.
- Treating a redundant add as an error. It is accepted, but silently
  accepting it is worse: the operator believes forwarding was narrowed, and
  only a reported finding corrects that.
- Making room for an add by evicting the oldest definition. Capacity is a
  refusal, not a replacement policy, because the evicted definition is one an
  operator still expects to be forwarding.
- Letting a delete of an absent entry pass as success. The usual cause is a
  delete issued at the wrong level, and the definition the operator meant to
  remove is still forwarding afterwards.
- Leaving an application process in the store once its last service type is
  deleted. An empty parent is indistinguishable from a wholesale application
  process entry unless the two are kept apart explicitly.

## Behavior contract (gate 3)

The level validation, wider-entry absorption, redundant-add reporting,
per-level capacity refusal, exact-level delete, empty-parent pruning,
coverage lookup and the assembled definition assessment are exercised by the
gate 3 contract test: scripts/test_e7041_forward_control_definitions.py
against scripts/e7041_forward_control_definitions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_forward_control_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
