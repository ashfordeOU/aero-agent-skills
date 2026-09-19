---
name: q7046-thread-rolling-and-forming
description: "Determine how a threaded fastener's thread must be formed and when, then prove the geometry and the fatigue allowable that choice earns. Use when a drawing, a supplier substitution or a cost proposal turns on cutting a thread instead of rolling it: force a rolled thread at and above the class floor and on any fatigue duty, force rolling after heat treatment where the soak would relax the compressive root stress away, derive pitch diameter, minor diameter, rolling blank and the root-radius notch floor from the designation rather than a table, then compare the duty load against the allowable the method and sequence actually earn. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-rolled-versus-cut-thread, fastener-roll-after-heat-treatment, fastener-thread-blank-diameter, fastener-root-radius-notch-floor, fastener-thread-fatigue-benefit."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-thread-rolling-and-forming, fastener-rolled-versus-cut-thread, fastener-roll-after-heat-treatment, fastener-thread-blank-diameter, fastener-root-radius-notch-floor, fastener-thread-fatigue-benefit, fastener-forming-schedule-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Thread Rolling and Forming (space-systems/ecss/q7046-thread-rolling-and-forming)

Use when the task is the thread-forming part of the ECSS-Q-ST-70-46
manufacturing clause -- deciding whether a thread may be cut or has to
be rolled, where rolling sits relative to heat treatment, and what
either choice is worth in fatigue.

## Domain quick reference

- Cutting and rolling are not two ways to the same thread. Cutting
  removes metal and leaves the grain severed where the profile crosses
  it. Rolling displaces metal, so the grain follows the profile and
  the root carries a compressive residual stress. The root is where a
  fastener fails in fatigue, which makes the forming method a strength
  decision wearing a manufacturing costume.
- The method is forced, not chosen. At and above the class floor, and
  on any fatigue-critical part whatever its class, the thread is
  rolled; below both, cutting is permitted. A low-class part with a
  fatigue duty is rolled on the duty alone.
- Sequence matters as much as method. Rolling after heat treatment
  leaves the compressive root stress in the finished part; rolling
  before it lets the austenitizing soak relax most of it away, so a
  part rolled before hardening has the geometry of a rolled thread and
  the fatigue behaviour of something much closer to a cut one.
- Rolling after heat treatment is not free. Hardened stock is harder
  to displace, so the decision carries a machine-capability question
  with it and that question belongs on the route, not in the shop's
  head.
- The geometry follows from the designation. Pitch diameter and minor
  diameter come from the nominal diameter and the pitch through the
  profile constants, and the rolling blank sits just above the pitch
  diameter because the displaced metal has to fill the crest -- a
  blank cut to the nominal diameter produces a thread that is oversize
  and short of material at the crest at once.
- The root radius has a floor whatever the method. Below it the root
  is a notch, and a rolled thread with a starved root radius has
  bought nothing with the rolling.
- The fatigue benefit is a factor on the allowable, and it is compared
  against the duty load rather than asserted. That is what turns the
  method question into a number a reviewer can check.

## Workflow

1. Resolve the property class and the fatigue duty, then derive the
   forming method they force, taking the duty as sufficient on its own.
2. Derive the sequence relative to heat treatment, returning no
   sequence at all where the part is not hardened rather than
   inventing one.
3. Compare the declared method and sequence against the derived ones
   and separate the two failures: a cut thread where rolling is
   required, and a rolled thread formed on the wrong side of the
   furnace.
4. Compute the thread geometry from the designation -- pitch
   diameter, minor diameter, the root-radius floor, and the rolling
   blank where the thread is rolled.
5. Judge the measured root radius against the floor for its pitch,
   since a starved root cancels the benefit the method was chosen for.
6. Take the fatigue benefit factor the declared method and sequence
   earn, apply it to the base allowable, compare the duty load, then
   roll the worst thread up into the build disposition.

## Pitfalls

- Treating the forming method as a cost line. The supplier quoting a
  cut thread is quoting a different fatigue allowable, and the saving
  is real only where the duty never reaches it.
- Rolling before hardening because the machine is easier to set. The
  part passes every dimensional check and has given back most of the
  residual stress the rolling was for.
- Accepting a rolled thread on a starved root radius. The radius floor
  is a notch limit, and a rolled root sharper than the floor
  concentrates stress exactly where the rolling was supposed to help.
- Sizing the rolling blank at the nominal diameter. The metal for the
  crest comes from the blank, so a blank sized as if metal were being
  removed gives an oversize thread with unfilled crests.
- Reading the class floor as the only trigger. A fatigue-critical part
  two classes below the floor is still rolled, because the duty and
  not the strength grade is what puts the load at the root.
- Comparing a duty against an allowable, or a radius against its
  floor, by bare arithmetic. Both sides are products of measured
  floats, so a case sitting exactly on the bound can land a few units
  in the last place outside it; the comparison absorbs that while the
  bound stays untouched.

## Behavior contract (gate 3)

The class ranking, forced method and sequence, thread geometry,
rolling blank, root-radius floor, fatigue benefit factor, duty
comparison and build roll-up are exercised by the gate 3 contract test:
scripts/test_q7046_thread_rolling_and_forming.py against
scripts/q7046_thread_rolling_and_forming_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_thread_rolling_and_forming.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
