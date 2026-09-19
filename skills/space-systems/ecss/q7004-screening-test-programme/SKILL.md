---
name: q7004-screening-test-programme
description: "Define the screening variant of an ECSS thermal test: how many cycles the class runs, on how many specimens, in how many chamber loads. Use when the ECSS-Q-ST-70-04C method variants have to become a bookable screening programme: read the cycle and specimen counts from the class table, pull a claimed class back towards novel for each process, supplier or heritage flag standing against it, split the specimens into chamber runs, multiply the duration out per run, and carry the limit that a screening result evidences gross defects only. Trigger: ecss, q-st-70-04-thermal-testing-scope, screening-cycle-count-per-class, screening-class-escalation, screening-specimen-batch-sizing, screening-chamber-run-count, screening-programme-duration."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-screening-test-programme, screening-cycle-count-per-class, screening-class-escalation, screening-specimen-batch-sizing, screening-chamber-run-count, screening-programme-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Screening Test Programme (space-systems/ecss/q7004-screening-test-programme)

Use when the task is the screening variant of ECSS-Q-ST-70-04C — the cheap
run that looks for gross defects — and it has to come out as a class, a
cycle count, a specimen count and a chamber booking.

## Domain quick reference

- Screening is defined by its class table and nothing else. The class is a
  statement about how much is already known: novel material and process are
  screened hardest, a modified one less, a heritage one least.
- The class an item is booked under is not always the class it is entitled
  to. A process change, a supplier change or an absence of flight heritage
  each pull it one step back towards novel, and the effective class is what
  the programme runs.
- Escalation saturates. An item already at the hardest class cannot be
  escalated further, and reporting three flags as three steps when two of
  them changed nothing overstates what the programme responded to.
- Specimen count and chamber capacity are separate numbers. Specimens beyond
  one chamber load turn into sequential runs, and the programme duration
  multiplies by runs, not by specimens.
- A declared specimen count below what the class calls for is a finding, not
  a tailoring. The cycle count still reads as the class's, so the programme
  looks like a class it is not carrying.
- A screening result is evidence of gross defects. It never becomes a
  qualification by running the cycles again, and the programme has to say so
  where it will be read.

## Workflow

1. Take the claimed class and the standing flags, and resolve the effective
   class before touching any count.
2. Read the cycle count and the default specimen count for the effective
   class; treat a declared specimen count as a deliberate override and
   compare it against the class default.
3. Split the specimens into chamber loads by integer ceiling division — a
   float ceiling here is the classic off-by-one.
4. Multiply cycles by the cycle duration by the run count for the programme
   duration.
5. Raise findings for an escalated class, a thin specimen batch and a
   multi-run booking, each naming the number that caused it.
6. Close with the duties: the screening limit, and re-screening whenever a
   flag changes after the programme was written.

## Pitfalls

- Screening on the claimed class. It is the one mistake that makes the whole
  programme cheap and meaningless at the same time.
- Counting every flag as a step. Escalation stops at the hardest class, and
  a step count that ignores that cannot be reconciled against the class it
  produced.
- Multiplying the duration by specimens. The chamber runs a load, not a
  specimen, and the booking comes out several times too long.
- Rounding the run count with floating-point arithmetic. Nine specimens in
  loads of eight is two runs; a float ceiling that lands on 1.9999999999 is
  one run and a specimen left out of the programme.
- Taking a declared specimen count silently. The report then carries a
  class's cycle count against a batch too thin to support it.
- Citing a screening pass as qualification evidence. The cycles were never
  the qualification cycles and the specimens were never the qualification
  articles.

## Behavior contract (gate 3)

The class tables and their ordering, flag escalation with saturation, the
specimen source and thin-batch finding, integer run-count arithmetic, the
programme duration and the standing duties are exercised by the gate 3
contract test: scripts/test_q7004_screening_test_programme.py against
scripts/q7004_screening_test_programme_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_screening_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
