---
name: e50-error-detection
description: "Compute the error detection a space data transfer protocol owes under ECSS-E-ST-50C clause 5.6.13.4, whose three normative items ask that the link protocol detect errors at all, that the project set its own figure for the units the code lets through undetected, and — a recommendation, not a requirement — that the detection chosen suit the telemetry and telecommand performance of clause 5.6.11. Header coverage is not among the three and is graded here as this leaf's own discipline. Derive the corruption rate a channel bit error rate produces over a unit, the fraction that escapes a checksum or a CRC, the undetected units expected across a pass, and the weakest catalogue code that still meets the bound. Use when choosing a transfer-layer code or reviewing a data integrity budget. Trigger: ecss, e-st-50-communications, data-unit-error-detection, undetected-error-probability-budget, crc-coverage-of-header-and-payload, residual-error-rate-after-crc, transfer-layer-detection-code-selection."
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
    clause: 5.6.13.4
    items: [a, b, c]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-error-detection, data-unit-error-detection, undetected-error-probability-budget, crc-coverage-of-header-and-payload, residual-error-rate-after-crc, transfer-layer-detection-code-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Error Detection (space-systems/ecss/e50-error-detection)

Use when a space data transfer protocol has to say what it does about
corrupted data units, per ECSS-E-ST-50C clause 5.6.13.4 — which three
obligations the design meets, how many corrupted units the chosen code lets
through, and which code would meet the bound if this one does not.

## Domain quick reference

- Three items sit in the clause and they fail independently: the protocol
  detects errors at all, the project has actually set and written down its
  own figure for how many units may pass as sound while corrupted, and the
  detection used lines up with the telemetry and telecommand performance
  of clause 5.6.11. A unit with no code fails the first before the
  arithmetic starts. Header coverage is not among the three and is checked
  here anyway — the clause is silent on it, and a misrouted unit usually
  costs more than a corrupted one.
- Coverage is the check designs actually miss. A code computed over
  the payload alone leaves a corrupted destination or length field to be
  acted on as if it were sound, and the damage from a misrouted unit is
  usually worse than the damage from a corrupted one.
- Corruption and escape are two separate numbers. The channel decides how
  often a unit arrives corrupted; the code decides what fraction of those
  corruptions it fails to notice. Multiplying them gives the undetected
  rate, and quoting either one alone understates or overstates the risk.
- The corruption probability over a unit is one minus the chance every bit
  survives, and at the bit error rates a space link runs at that is a
  difference of two numbers very close to one. Computed directly it loses
  most of its significant digits, so it is worth computing through the
  logarithm of one plus a small quantity instead.
- An n-bit code lets through about one corrupted unit in two-to-the-n for
  error patterns it was not designed to catch. That is a rule of thumb for
  budget work, not a burst-length guarantee, and a burst analysis of the
  actual polynomial belongs alongside it for the patterns that matter.
- The bound is per unit or per pass, and the two differ by the unit count.
  A per-unit probability that looks comfortable turns into several missed
  units a day once the pass length is put in.

## Workflow

1. State the unit as its total length in bits, the header length inside
   that, the code applied, the extent the code covers, and the channel bit
   error rate. Take with them the figure this project owns and has
   written down for the link: how many of the units the code lets through
   undetected it is prepared to accept. Where nobody has set one, that
   absence is itself the finding. The uplink and the downlink may each
   carry their own figure.
2. Check that the link protocol detects errors at all. An unprotected unit
   fails here and the remaining numbers are advisory.
3. Check the coverage: the covered extent reaches the whole unit, header
   included. Report a payload-only code as a coverage finding, not as a
   weaker version of the same code.
4. Compute the corruption probability over the unit using a numerically
   stable form, so the result stays meaningful at the small bit error
   rates a real link has.
5. Multiply by the escape fraction of the code to get the undetected
   probability per unit, then by the units in a pass to get the undetected
   units expected.
6. Compare with the bound using a relative tolerance, so a design that
   lands exactly on it is compliant on every build host.
7. Take each direction in turn and hold the detection it uses against the
   telemetry and telecommand performance figures the mission carries under
   clause 5.6.11: the two should work together at the link's operating
   point. The clause recommends this rather than requiring it, so a
   direction where they do not is reported as a recommendation not met.
8. Where it fails, name the weakest catalogue code that meets the bound on
   the same channel, and check that recommendation against the same model
   before reporting it.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.13.4a | 2 |
| ECSS-E-ST-50C Rev.2 5.6.13.4b | 1 |
| ECSS-E-ST-50C Rev.2 5.6.13.4c | 7 |

## Pitfalls

- Grading the code and skipping the coverage. A strong code over the
  payload only meets the arithmetic and misses the obligation that matters
  most for a misrouted unit.
- Computing the corruption probability as one minus a power directly. At a
  bit error rate around ten to the minus seven the subtraction cancels
  almost every significant digit, and the undetected rate that follows is
  noise.
- Quoting the escape fraction as the undetected error rate. It is a
  conditional fraction of corrupted units, and without the corruption
  probability in front of it the number is meaningless as a budget.
- Comparing against a per-unit bound with a per-pass number, or the other
  way round. The two differ by the unit count of the pass and the mistake
  always flatters the design.
- Deciding compliance with a bare inequality at the bound. The margin at
  the boundary is a representation question and a tolerance answers it;
  moving the bound to make a design pass does not.

## Behavior contract (gate 3)

Unit and code validation, the three obligations separately, the stable
corruption probability, the escape fraction of each catalogue code, the
per-unit and per-pass undetected rates, compliance at the exact bound and
the weakest sufficient code are exercised by the gate 3 contract test:
scripts/test_e50_error_detection.py against
scripts/e50_error_detection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_error_detection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
