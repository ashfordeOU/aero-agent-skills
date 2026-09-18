---
name: e50-bandwidth-allocation
description: "Allocate link bandwidth across the data flows a space communication system carries, under ECSS-E-ST-50C clause 5.3.1: each flow is sized from its own rate and the overhead its protocol stack adds, and the sum of the allocations plus the reserved margin stays inside the capacity of the link they share. Compute per-flow allocations, the aggregate, the margin actually achieved and the shortfall when there is one, separating a link that eats its margin from one that does not fit at all, and cut proportionally when it cannot. Use when sizing or reviewing a spacecraft communication link budget. Trigger: ecss, e-st-50-communications, communication-bandwidth-allocation, link-capacity-oversubscription, protocol-overhead-factor, per-flow-rate-sizing, link-bandwidth-margin-policy."
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
  tags: [ecss, e-st-50-communications, e50-bandwidth-allocation, communication-bandwidth-allocation, link-capacity-oversubscription, protocol-overhead-factor, per-flow-rate-sizing, link-bandwidth-margin-policy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Bandwidth Allocation (space-systems/ecss/e50-bandwidth-allocation)

Use when the data flows of a space communication system are being sized
against the link that carries them, per ECSS-E-ST-50C clause 5.3.1 — what each
flow is allocated, and whether the set fits.

## Domain quick reference

- Two obligations, and they bite at different moments. Each flow is
  allocated what it needs. And the allocations together, with the
  margin the design reserves, stay inside the link capacity.
- What a flow needs is not what the application emits. Framing, headers,
  coding and acknowledgement traffic all ride on the same link, so the
  allocation is the source rate multiplied by the overhead the stack
  adds to it. An overhead factor below one is not a saving, it is an
  input error.
- Margin is capacity the design refuses to allocate. Reporting the
  achieved margin alongside the reserved one is what separates a design
  with headroom from a design that happens to fit today.
- Three outcomes matter, not two. The flows fit inside the usable
  capacity; they fit the link but only by consuming the margin; or they
  do not fit at all. The middle case passes an is-it-under-capacity
  check and is the one that surprises a programme later.
- When the set does not fit, one common scale factor applied to every
  flow is the neutral answer. It holds the relative sizing the design
  chose and states the size of the problem as a single number someone
  can argue about.

## Workflow

1. Declare each flow with a name, its own rate and its overhead factor.
   A flow with no overhead declared is being asserted to cost exactly
   its payload, which is a claim, so make it explicit as 1.0.
2. Reject a duplicate flow name. Two entries under one name are two
   teams sizing the same traffic, and the total silently doubles it.
3. Allocate each flow as rate times overhead, and record its share of
   the capacity — the share is what makes one flow's dominance visible
   without reading the totals.
4. Sum the allocations, then compare against the usable capacity, which
   is the link capacity less the reserved margin.
5. Compare with a relative tolerance. A flow set sized to exactly fill
   the usable capacity must come out feasible, and an exact-equality
   comparison on floating point decides that by rounding.
6. Report which of the three outcomes holds, with the shortfall in bit/s
   where there is one, rather than a pass or fail.
7. Where the set does not fit, report the capacity it would need at the
   declared margin, and the single factor every flow would scale by to
   fit the capacity that exists.

## Pitfalls

- Sizing flows on payload rate alone. The overhead is real traffic on a
  real link, and a stack that adds a fifth to everything turns a link
  with twenty percent margin into a link with none.
- Treating margin as slack to be allocated when things get tight. It is
  reserved against the things not yet in the flow list, and the first
  flow to spend it is never the last.
- Passing a link that fits only by eating its margin. It satisfies the
  capacity check, fails the margin policy, and is reported as fine by
  any check that only asked whether the total was under the line.
- Comparing the total against capacity with a bare equality or a strict
  inequality. Two arithmetically identical totals can straddle the bound
  on different platforms, so the verdict changes with the machine.
- Cutting the flow that is easiest to argue with rather than scaling the
  set. The proportional cut is at least a stated policy; a negotiated
  one leaves no record of what the design intended.

## Behavior contract (gate 3)

Rate, overhead and margin validation, per-flow allocation with shares,
the three-way verdict with a tolerance at the usable bound, the
shortfall, the required capacity at a declared margin and the
proportional scale-back are exercised by the gate 3 contract test:
scripts/test_e50_bandwidth_allocation.py against
scripts/e50_bandwidth_allocation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_bandwidth_allocation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
