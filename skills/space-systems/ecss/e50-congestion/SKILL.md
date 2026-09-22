---
name: e50-congestion
description: "Model congestion on a space communication link under ECSS-E-ST-50C clause 5.3.2, which asks that offered load running above the service rate be held and drained rather than resolved by loss. Compute the backlog a burst leaves, whether the provided buffer contains it, how long an overload runs before that buffer fills, and how long the backlog takes to clear once the burst ends. Where it does not fit, report both ways out: the buffer this burst needs, and the service rate that would hold it inside the buffer already there. Use when sizing buffers or reviewing flow control on a spacecraft link. Trigger: ecss, e-st-50-communications, communication-link-congestion, link-buffer-overflow-time, offered-load-versus-service-rate, burst-backlog-sizing, link-flow-control-margin."
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
    clause: 5.3.2
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-congestion, communication-link-congestion, link-buffer-overflow-time, offered-load-versus-service-rate, burst-backlog-sizing, link-flow-control-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Congestion (space-systems/ecss/e50-congestion)

Use when a space communication link has to absorb more offered load than it can
serve, per ECSS-E-ST-50C clause 5.3.2 — whether the design holds the excess or
loses it, and what it would take to hold it.

## Domain quick reference

- The obligation is containment, not absence. A link that never sees a
  burst above its service rate is not a design achievement; a link that
  sees one and drops nothing is.
- The model that answers it is deterministic and small. Excess load is
  offered rate less service rate; backlog is that excess over the
  duration of the burst; the buffer either holds the backlog or it does
  not; and once the burst ends the backlog drains at whatever capacity
  the following load leaves spare.
- Time to overflow is the number an operator can act on. Backlog says
  how much trouble the burst is, time to overflow says how long anyone
  has to do something about it — and it is not defined at all when the
  service rate keeps up.
- Drain time is where a design quietly fails. A burst can be contained
  and still be a problem if the load that follows it sits at the service
  rate, because then there is no spare capacity and the backlog never
  clears; the buffer stays full until the next burst overflows it.
- There are always two ways out of an overflow, and both belong in the
  report: more buffer, or more service rate. Which is cheaper is a
  system decision, and offering only one of them makes it for someone
  else.

## Workflow

1. State the burst as four numbers: offered rate, service rate, how long
   the burst lasts, and the buffer provided behind the link.
2. Compute the excess and the backlog. Where offered load is at or below
   the service rate there is no backlog and no congestion, and the rest
   of the assessment is not applicable rather than zero.
3. Compare the backlog against the buffer with a relative tolerance. A
   burst sized to exactly fill the buffer must come out contained, and
   an exact comparison on floating point decides that by rounding. A
   backlog the buffer cannot hold is data the design loses to
   congestion, so carry it as a defect the design has to remove and not
   as a quantity to note in passing.
4. Report the time to overflow where there is an overload, and report it
   as undefined where there is not — a number there would imply a
   deadline that does not exist.
5. Compute the drain time from the capacity the following load leaves
   spare, and say plainly when there is none.
6. On an overflow, report both remedies with their numbers: the buffer
   this burst needs, and the service rate that holds it inside the
   buffer already provided. Where neither can move, flow control that
   holds the source back before the buffer fills may close the same
   gap, and belongs in the report beside them.
7. Check the remedy against the same model before reporting it. A
   recommended rate that does not itself contain the burst is a
   rounding error someone will build to.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.3.2a | 3 |

## Pitfalls

- Sizing a buffer for the average rate. Congestion is a property of the
  peak and its duration, and an average that fits says nothing about a
  burst that does not.
- Reporting containment and stopping. A contained burst behind a link
  with no spare capacity afterwards leaves a buffer that never empties,
  which is the state the next burst overflows from.
- Treating an undefined overflow time as zero or as infinity. It means
  the service rate keeps up, and coercing it to a number puts a fake
  deadline or a fake guarantee into whatever reads the result.
- Deciding containment with a bare inequality on the computed backlog.
  Two arithmetically identical designs can straddle the bound on
  different machines, and the verdict then depends on the build host.
- Offering only the bigger buffer. Memory is not always the cheap axis
  on a spacecraft, and the rate that would fix it is the same
  calculation read in the other direction.

## Behavior contract (gate 3)

Rate, duration and buffer validation, the backlog model, the undefined
overflow and drain times, containment at the exact buffer bound, and the
two sizing inverses checked against the same model are exercised by the
gate 3 contract test:
scripts/test_e50_congestion.py against
scripts/e50_congestion_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_congestion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
