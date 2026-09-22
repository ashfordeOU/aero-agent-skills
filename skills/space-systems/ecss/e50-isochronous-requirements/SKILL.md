---
name: e50-isochronous-requirements
description: "Validate a stated isochronous requirement set against the obligation of ECSS-E-ST-50C clause 5.6.14.5, which asks that the requirements placed on an isochronous service be stated rather than assumed. Name every figure the set omits, then test the figures against each other: a jitter bound past half the period that makes slot ordering undecidable, a latency budget below the jitter it already permits, a link too slow to clock one payload out inside a period. Derive what the set silently commits to — minimum link rate, utilisation, playout buffer, clock stability. Use when writing or reviewing an isochronous service specification. Trigger: ecss, e-st-50-communications, isochronous-requirement-completeness, isochronous-jitter-budget-conflict, isochronous-latency-budget, isochronous-clock-stability-ppm, isochronous-spec-satisfiability."
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
    clause: 5.6.14.5
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-isochronous-requirements, isochronous-requirement-completeness, isochronous-jitter-budget-conflict, isochronous-latency-budget, isochronous-clock-stability-ppm, isochronous-spec-satisfiability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Isochronous Requirements (space-systems/ecss/e50-isochronous-requirements)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.14.5 —
that the requirements on an isochronous service are stated — and the question
is whether the set written down is complete, and whether it can be met at all.

## Domain quick reference

- This clause grades the specification, not the service. An observed run
  can be measured against a requirement set that was never satisfiable,
  and the measurement then blames an implementation for an arithmetic
  impossibility nobody checked before build.
- Absent and wrong are different findings with different owners. A
  figure nobody wrote down goes back to the author of the set; a figure
  written down badly goes back to whoever computed it, and defaulting
  the first silently converts it into the second.
- Half the period is a hard ceiling on the jitter bound, not a style
  preference. Beyond it, a delivery late in its slot and one early in
  the next can swap, and no receiver anywhere downstream can decide
  which slot either belonged to.
- A latency bound below the jitter bound is self-refuting. The jitter
  bound already licenses a delivery that late, so the worst case the
  specification permits is the one it also forbids.
- Serialisation is a requirement, not an implementation detail. If
  clocking one payload out takes longer than the period, no scheduling,
  buffering or priority scheme recovers the cadence.
- Every isochronous set already commits to figures nobody wrote down —
  minimum link rate, utilisation, playout depth, clock stability in ppm
  over the service duration. Deriving them turns an argument about
  intent into an argument about numbers.

## Workflow

1. Take the set as stated and list what is absent before touching what
   is present. Three of those figures are the ones the clause obliges the
   service to be written with — the rate it runs at, the longest delivery
   delay it is allowed, and how far an individual delivery may stray from
   that delay — so a set silent on any of them specifies no service at
   all. An incomplete set is not judged consistent.
2. Validate each figure that is present for type, finiteness and sign,
   and raise rather than coerce. A negative period is malformed input,
   not a requirement with an unusual value.
3. Compare the jitter bound against half the period and report the
   ceiling with the finding, so the author sees the number to write.
4. Compare the latency bound against the jitter bound, and against the
   serialisation time on its own, before any propagation or processing
   is added.
5. Compare the serialisation time against the period and report the
   minimum link rate the payload and cadence already demand.
6. Derive the implied figures — minimum rate, utilisation, playout
   buffer, clock stability — and return each as unknown, never as zero,
   where its inputs were not stated.
7. Grade incomplete before inconsistent, and check any rate or bound
   offered as a remedy against the same model before reporting it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.14.5a | 1 |

## Pitfalls

- Defaulting an absent figure to a house value. The set then reads as
  complete and satisfiable, and the assumption surfaces at integration
  as a requirement nobody agreed to.
- Reporting a missing figure as zero. Zero jitter and unstated jitter
  are opposite situations, and a report that renders them identically
  makes the tighter one invisible.
- Checking completeness and stopping. Every figure can be present and
  the set still be impossible, which is the case that costs a build.
- Treating the jitter ceiling as advisory. Slot ordering is not a
  quality metric; past half a period it is simply not recoverable from
  the received stream.
- Budgeting latency without serialisation. On a slow link the payload's
  own transmission time can exhaust the budget before propagation,
  processing or queueing are counted at all.
- Deciding a bound with a bare inequality. A set written to sit exactly
  on half the period, or on its own jitter bound, then passes or fails
  by the rounding of the host that graded it.

## Behavior contract (gate 3)

Field-by-field validation with absence distinguished from malformation, the
required-field census, serialisation time, minimum link rate, utilisation, the
half-period jitter ceiling, the playout buffer, clock stability in ppm and its
undefined case, each consistency conflict including the exact-bound cases, the
incomplete-before-inconsistent ordering and the remedy checked against the same
model are exercised by the gate 3 contract test:
scripts/test_e50_isochronous_requirements.py against
scripts/e50_isochronous_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_isochronous_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
