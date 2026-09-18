---
name: q1009-customer-meeting
description: "Coordinate the customer review board sitting on a submitted major nonconformance under ECSS-Q-ST-10-09 clauses 5.2.3.1 to 5.2.3.3. Use when a supplier's package has reached the customer and the board has to establish whether it can take a disposition at all. Separates the two ways a sitting fails: the customer functions that constitute the board, and the supplier representative without whom nothing can be confirmed. Assesses the impacts the supplier cannot see from inside its own scope, meaning system budget share, every interface parameter against its agreed range and slip against the activity float, then holds each submitted cause and consequence to a confirmed, disputed or open state. Trigger: ecss, q-st-10-09, customer-review-board-sitting, higher-level-impact-assessment, interface-parameter-range-breach, activity-float-consumption, supplier-confirmation-of-causes, disposition-deferral."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-customer-meeting, customer-review-board-sitting, higher-level-impact-assessment, interface-parameter-range-breach, activity-float-consumption, supplier-confirmation-of-causes]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Customer Review Board (space-systems/ecss/q1009-customer-meeting)

Use when the task is the customer-side processing of ECSS-Q-ST-10-09
clauses 5.2.3.1 to 5.2.3.3 — the board that actually disposes of a major
departure meeting on it, working out what it costs at a level the
supplier cannot see, and settling with the supplier what is true.

## Domain quick reference

- A customer board fails in two independent ways and they have different
  repairs. Missing a customer function leaves it unconstituted and it
  cannot sit at all. Missing the supplier representative leaves it
  perfectly constituted and unable to confirm anything, because
  confirmation is a two-party act. Merging the two verdicts sends the
  wrong people to the next meeting.
- The customer board owns the impacts the supplier's analysis structurally
  cannot reach. The supplier knows what the departure does to its own
  item; only the customer knows what it does to the system budget it was
  allocated from, to the interface the neighbouring unit was built to,
  and to the schedule the activity sits in.
- A budget is assessed as a share of its allocation, and consuming the
  whole allocation is not an overrun. A share that lands exactly on its
  limit is a representation question absorbed by a named tolerance, not
  a reason to widen the allocation.
- An interface parameter is judged against the range the interface
  document agreed, and a value exactly on a bound conforms. Interface
  bounds are the classic place where a strict comparison on a float
  turns a conforming unit into a finding on one machine and not on
  another.
- Schedule impact is float first, critical path second. A slip inside
  the activity float costs float and nothing else; a slip equal to the
  float exhausts it without delaying anything, and is worth saying
  because the next slip has nowhere to go; a slip beyond it delays the
  programme by the difference.
- Confirmation is per statement, not per package. Each submitted cause
  and each submitted consequence comes back confirmed, disputed or still
  open, and a single disputed statement defers the disposition — the
  board cannot dispose of a departure whose cause the two parties do not
  agree on.
- An unacceptable impact is not a reason to defer. The board that
  discovers the departure blows the mass budget is exactly the board
  that has to decide what happens to the item; deferring on bad news is
  how a departure sits open for two quarters.

## Workflow

1. Validate attendance and split the verdict: the mandatory customer
   functions sitting, and the supplier representative present. Report
   quorum and confirmation capability separately.
2. Assess the system budget: the consumed share of the allocation, with
   the at-allocation boundary absorbed by a named tolerance.
3. Assess every interface parameter against its agreed range, refusing
   an inverted range as an input error and treating an on-bound value as
   conforming. Name every breaching parameter.
4. Assess the schedule: float remaining, float exhausted, and the delay
   in days when the slip runs past the float.
5. Take each submitted statement's confirmation state. With the supplier
   absent nothing can be confirmed, so every statement reverts to open
   for this sitting and the block is named as the absent supplier rather
   than as a supplier disagreement.
6. Decide the outcome: not quorate, deferred pending confirmation, or a
   disposition the board can decide. Impact findings are reported
   against the decision, never used to defer it.

## Pitfalls

- Reporting one attendance verdict. "The board was not quorate" sends a
  customer delegate when what was missing was the supplier engineer who
  could have answered the cause question in five minutes.
- Accepting the supplier's impact assessment as the higher-level one. It
  was made from inside the supplier's scope and cannot see the budget
  the item was allocated from or the unit on the other side of the
  interface.
- Using a strict comparison on an interface bound. A parameter landing
  exactly on its limit then fails or passes on floating-point rounding,
  and the same unit is judged differently by two sites.
- Reading an exhausted float as a schedule impact. Nothing is late yet;
  saying so loudly is right, recording a delay that does not exist is
  not.
- Confirming the package rather than the statements. One disputed cause
  hidden inside a confirmed package is exactly the disagreement that
  reopens the disposition later.
- Deferring because the impacts came back bad. The bad news is the
  board's own business; deferral is for what it cannot yet know, which
  is an unconfirmed cause or an empty supplier chair.

## Behavior contract (gate 3)

The split attendance verdict, the budget-share assessment with its
at-allocation boundary, the interface-range check with its on-bound
case, the float-then-critical-path schedule assessment, the per-statement
confirmation with the absent-supplier case and the outcome selection are
exercised by the gate 3 contract test:
scripts/test_q1009_customer_meeting.py against
scripts/q1009_customer_meeting_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q1009_customer_meeting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
