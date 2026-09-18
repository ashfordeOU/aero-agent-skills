---
name: e2020-status-reading-failure-independence
description: "Assess whether the true state of a device stays readable once its command interface has failed, the independence requirement of ECSS-E-ST-20-20C clause 5.2.9.1.1. Use when a status acquisition architecture has to be judged rather than assumed: separate the paths that sense the achieved device state from the ones that only replay the ordered state, intersect each sensing path with the command chain and the command power domain, categorize every path as independent, shared or command-derived, compute the elements whose single failure blinds all sensing at once, and close with the duty that would restore an independent reading. Trigger: ecss, e-st-20-20c-clause-5-2-9-1-1, status-readout-command-independence, device-state-sensing-path, command-echo-status-limitation, status-path-common-cause-element, command-power-domain-dependency, status-blinding-element."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-status-reading-failure-independence, status-readout-command-independence, device-state-sensing-path, command-echo-status-limitation, status-path-common-cause-element, command-power-domain-dependency, status-blinding-element]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Status Reading Failure Independence (space-systems/ecss/e2020-status-reading-failure-independence)

Use when the task is the clause 5.2.9.1.1 requirement of
ECSS-E-ST-20-20C: the state a device is actually in has to stay
readable after the interface that commands it has failed, so the
question is whether any status path survives that failure and still
witnesses the device.

## Domain quick reference

- Two different defects break this requirement, and only one of them
  is visible on a block diagram. The visible one is a shared element: a
  status path routed through the same driver, connector, harness run or
  power domain as the command chain fails with it.
- The invisible one is a path that never observed the device. A command
  echo, a driver register readback or a commanded-state memory reports
  what was ordered. A welded relay, a latch that failed to transfer or
  an open fuse is exactly the case where the ordered state and the
  achieved state diverge, and such a path keeps reporting the order.
- So a path only counts when it senses the device -- a contact, a
  position switch, a load current or an output voltage -- and shares
  nothing with the command chain. Every other path is recorded, but it
  is not the independent reading the clause is asking for.
- The power domain is a shared element like any other. A sensing path
  fed from the command bus is fully independent right up to the moment
  the command side loses power, which is one of the failures the
  reading is meant to survive.
- Where several sensing paths exist, the elements common to all of them
  are what a redundancy claim has to break. That intersection, not the
  count of paths, is the honest measure: three paths through one
  connector are one path as far as this clause is concerned.
- A shared or command-derived path is still worth keeping. It is
  diagnostic data, and the useful output is the label that stops it
  being read as an independent confirmation later.

## Workflow

1. Take the architecture: the elements of the command chain, the
   command power domain, and each status acquisition path with its
   source, the elements it shares and where it draws power. Reject an
   undeclared source rather than guessing what it observes.
2. Split the paths by what they observe. A source that senses the
   device is a candidate; a source that replays the order is recorded
   as command-derived with the reason attached.
3. Intersect each sensing path with the command chain, and add the
   command power domain to that intersection where the path is fed
   from it. A declared shared element that is not in the chain is a
   finding rather than a constraint.
4. Categorize each path as independent, shared or command-derived, and
   take the verdict from whether any independent path remains.
5. Compute the blinding elements: the intersection of the shared sets
   across every sensing path, or the whole command chain where no path
   senses the device at all.
6. Close with the verdict, the independent paths, the blinding elements
   and the duty each shortfall creates -- reroute, duplicate the shared
   element, or add a path that senses the achieved state.

## Pitfalls

- Counting a command echo as status. It confirms the order left the
  decoder, not that the device moved, so an architecture resting on it
  reports a healthy device through exactly the failures it exists to
  catch.
- Counting paths instead of intersecting them. Several sensing paths
  through one connector or one power domain fail together, and the
  redundancy in the block diagram is not redundancy in the failure
  case.
- Forgetting where the sensing path draws power. Power is not on the
  signal diagram, so a path fed from the command side looks independent
  until the failure being analysed is a command-side power loss.
- Accepting a declared shared element without checking it against the
  chain. An element nobody in the command path uses constrains nothing,
  and carrying it inflates the apparent coupling while the real shared
  element stays unlisted.
- Discarding the shared and command-derived paths once the verdict is
  in. They are useful data; what they are not is an independent
  confirmation, and only the recorded label keeps the next reader from
  treating them as one.

## Behavior contract (gate 3)

The architecture validation, source separation, per-path
categorization against the command chain and the command power domain,
undeclared-element findings, blinding-element intersection,
independent-path listing, redundancy flag and the independence verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_status_reading_failure_independence.py against
scripts/e2020_status_reading_failure_independence_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_status_reading_failure_independence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
