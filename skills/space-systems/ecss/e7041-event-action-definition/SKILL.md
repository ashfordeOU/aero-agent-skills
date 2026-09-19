---
name: e7041-event-action-definition
description: "Define the on-board table entry that binds an event report to the request it releases, under ECSS-E-ST-70-41C clause 6.19.4. Use when two application processes reuse one event identifier and the wrong action fires, or when an action turns out to re-raise its own trigger: keying every definition on the generating application process together with the event definition identifier, holding exactly one complete request per entry rather than a list assembled at release time, refusing an action that would rewrite the event-action table from inside an event, and walking the graph of actions that generate events to find release cycles before they run. Trigger: ecss, e-st-70-41c, event-action-definition-table, event-action-two-part-event-key, event-action-single-request-per-entry, event-action-release-cycle, event-action-self-triggering-entry."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-event-action-definition, event-action-definition-table, event-action-two-part-event-key, event-action-single-request-per-entry, event-action-release-cycle, event-action-self-triggering-entry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Event-Action Definition (space-systems/ecss/e7041-event-action-definition)

Use when the task is the event-action definition of ECSS-E-ST-70-41C
clause 6.19.4 -- the two requirements that fix what one entry of the
on-board event-action table is: which event identifies it, and what
single thing it releases.

## Domain quick reference

- The key has two halves. A definition is identified by the
  application process that generates the event report and by the
  event's own definition identifier. Keying on the identifier alone is
  the classic table defect: two application processes legitimately use
  the same number for unrelated events, and one of them then inherits
  the other's action.
- The action is one request, complete at definition time. Not a list,
  not a sequence to be built when the event arrives. That is what
  makes the release deterministic -- when the event is detected there
  is nothing left for the engine to decide.
- A definition's enable status belongs to the entry, not to the table.
  Defining an entry and arming it are separate acts, so a freshly
  defined entry is inert until something enables it.
- An action that is itself an event-action management request lets the
  table rewrite itself from inside an event. The table then reaches
  configurations no operator commanded, and the telemetry showing the
  table is the same telemetry that was right a moment ago.
- Actions generate events. Once one does, the definitions form a
  directed graph -- event to action to event -- and a cycle in that
  graph is a loop that keeps releasing until something unrelated stops
  it. The shortest cycle is an entry whose action re-raises its own
  trigger; the expensive ones are two and three entries long and are
  invisible in any single entry.
- An action that raises an event no definition covers is not a defect,
  but it is a loose end worth naming: it is exactly where the next
  definition will be added, and the cycle check has to be run again
  when it is.
- The table is bounded. A definition past the bound is refused, not
  swapped in over an existing one, so the entry that fails to appear
  is the new one and not a working one.

## Workflow

1. Build the two-part key for each definition and refuse an
   application process identifier outside its field or a negative
   event definition identifier.
2. Normalise the action as exactly one request: refuse a list
   outright, then check the service type, the message subtype and the
   target application process.
3. Record the entry's own enable status, defaulting to inert rather
   than armed.
4. Insert into the table under the two-part key. A repeated key is a
   finding and the existing entry stands -- the new one does not
   silently replace it.
5. Refuse an insertion past the table bound, naming the entry that did
   not go in.
6. Check each action's scope: an event-action management request is a
   table-rewriting finding, and an action that re-raises its own
   trigger is a self-triggering finding.
7. Build the graph of definitions to the events their actions
   generate, name any raised event no definition covers, and report
   every release cycle once.

## Pitfalls

- Keying the table on the event identifier alone. It works until a
  second application process defines an event with the same number,
  and then it binds the wrong action with no error anywhere.
- Storing a list of requests as the action. The release stops being
  one deterministic act and becomes a small sequence with its own
  partial-failure behaviour, decided at the worst possible moment.
- Overwriting on a duplicate key. The table accepts the load and the
  entry that disappears is the one that was working.
- Letting an action manage the event-action table. The table becomes
  self-modifying, and reconstructing what it held at the time of an
  anomaly stops being possible from the command history.
- Checking only for an entry that triggers itself. The two-entry loop
  is just as live and no single entry looks wrong.
- Treating a defined entry as an armed one. Definition and enabling
  are separate, and an entry that was never enabled looks identical in
  a table dump to one that was.

## Behavior contract (gate 3)

The two-part event key, field validation, single-request action
normalisation, list refusal, default-inert enable status, duplicate-key
retention of the existing entry, table-bound refusal, table-rewriting
action detection, self-triggering detection, the action graph,
uncovered-raised-event naming and once-only cycle reporting are
exercised by the gate 3 contract test:
scripts/test_e7041_event_action_definition.py against
scripts/e7041_event_action_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_event_action_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
