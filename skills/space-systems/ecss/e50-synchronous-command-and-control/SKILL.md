---
name: e50-synchronous-command-and-control
description: "Size the time-slot schedule that carries synchronous command and control traffic on an on-board network under ECSS-E-ST-50C clause 5.7.1.3. Turn each periodic exchange into a slot of payload, protocol overhead and guard time, check its repetition period divides the control cycle, add up the time reserved per cycle, and report synchronous utilisation, delivery phase error and the spare time left for everything else. Use when laying out a control cycle or reviewing a cyclic schedule quoted only as average load. Trigger: ecss, e-st-50-communications, synchronous-command-and-control, control-cycle-slot-schedule, cyclic-slot-allocation, synchronous-network-utilisation, command-delivery-phase-error."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.7.1.3
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-synchronous-command-and-control, control-cycle-slot-schedule, cyclic-slot-allocation, synchronous-network-utilisation, command-delivery-phase-error, harmonic-repetition-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Synchronous Command and Control (space-systems/ecss/e50-synchronous-command-and-control)

Use when an on-board network has to carry command and control exchanges
synchronously under ECSS-E-ST-50C clause 5.7.1.3 — laying out the repeating
control cycle that gives each exchange a reserved place, and showing the cycle
actually holds them.

## Domain quick reference

- Synchronous means placed, not merely frequent. Each exchange recurs on
  its own period, occupies a reserved slot inside a repeating control
  cycle, and arrives within a bounded deviation of its nominal instant.
  A link fast enough on average has not met any of those three.
- A slot is bigger than its payload. Protocol overhead rides with every
  activation, and a guard time separates one slot from the next so a
  late finish does not eat into its neighbour. Both belong in the
  reservation, and both are what a payload-only estimate leaves out.
- A period only fits a cycle when the two are harmonic: the cycle a
  whole multiple of the period, or the period a whole multiple of the
  cycle. Anything else has no fixed slot at all, which is a layout
  failure rather than a load problem, and no amount of link rate cures
  it.
- The reservation to check is the busiest cycle, not the average one. An
  exchange four times per cycle needs four slots in every cycle it runs;
  an exchange slower than the cycle still needs a whole slot in the
  cycles where it does occur, never a fraction of one.
- Delivery phase error is what "synchronous" costs. Guard time, the
  granularity the schedule can place a slot on, and the error of the
  on-board time reference add up into the worst deviation a command can
  show, and that is the figure a control loop budgets against.
- The spare time left in the cycle is not slack to be spent quietly. It
  is the entire budget every asynchronous transfer will ever run in, so
  it is an output of this layout and an input to the next one.

## Workflow

1. State the control cycle, the link rate, the protocol overhead per
   activation and the guard time. A zero cycle, a zero rate or an empty
   exchange set is an input error, not a degenerate schedule.
2. List every synchronous exchange the sensors and actuators on board
   need — each reading collected and each command issued — as a name, a
   size and a repetition period. Refuse two exchanges under one name — a
   duplicate silently halves the reservation it was meant to add.
3. Test each period against the cycle for harmonicity first. A
   non-harmonic period is reported before any load figure, because a
   schedule that cannot be laid out has no meaningful utilisation.
4. Size each slot as payload plus overhead at the link rate, plus the
   guard time, and count the slots the busiest cycle has to hold, so
   that every sensor reading and every actuator command has a place
   reserved for it in each cycle it runs in.
5. Add the reservation, and compare it with the cycle using a relative
   tolerance so a schedule sized to exactly fill its cycle is accepted
   everywhere rather than on some hosts.
6. Report utilisation, the spare time, and the worst delivery phase
   error against its budget when one is stated.
7. On an oversubscribed cycle report both remedies with numbers: the
   link rate that makes the reservation fit, and the cycle length that
   would hold it at the rate already available. Where guard time alone
   fills the cycle, say plainly that no rate fixes it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.1.3a | 4 |

## Pitfalls

- Sizing the cycle on payload bits. Overhead and guard time are charged
  per activation, so a schedule with many small fast exchanges can be
  dominated by everything except its payload.
- Reserving the average number of activations. The cycle has to hold the
  busiest one; an average reservation passes a schedule that overruns
  every cycle where two fast exchanges coincide.
- Rounding a near-harmonic period into place. A period that is nearly a
  divisor drifts against the cycle and its slot walks into a neighbour's
  after enough cycles, which shows up in flight and not in the budget.
- Giving an exchange slower than the cycle a fractional slot. It still
  occupies a whole slot in the cycles where it runs, and the fraction
  quietly under-reserves the cycle that carries it.
- Reporting utilisation for a non-harmonic schedule. The number looks
  reassuring and describes a layout that does not exist.
- Treating the spare time as free. It is the asynchronous budget;
  spending it here means the next clause has nothing to work with.
- Deciding the cycle fit with a bare inequality. A schedule built to
  exactly fill its cycle then passes or fails according to the build
  host rather than the design.

## Behavior contract (gate 3)

Exchange validation including duplicate names, slot sizing with overhead
and guard, the harmonic test in both directions, the busiest-cycle slot
count, the reservation at and beyond the cycle bound, delivery phase
error against its budget, and the link-rate inverse checked against the
same model are exercised by the gate 3 contract test:
scripts/test_e50_synchronous_command_and_control.py against
scripts/e50_synchronous_command_and_control_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_synchronous_command_and_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
