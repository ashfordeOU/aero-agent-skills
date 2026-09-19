---
name: e50-uplink-assumed-bit-error-rate-ber
description: "Validate the bit error rate a mission states for its uplink and that every later figure inherited it, per ECSS-E-ST-50C clause 5.6.11.5: carry the rate as an exact decimal rather than a binary power of ten, rank the declared conditions, confirm the stated rate is no better than the worst of them, and name any derived figure computed from a friendlier rate. Use when an uplink performance case quotes rejection or corrupted-frame numbers and the rate behind them is absent, typical rather than worst case, or different per page. Trigger: ecss, e-st-50c-communications-scope, uplink-assumed-bit-error-rate, worst-case-uplink-condition, unstated-ber-assumption, derived-figure-ber-consistency, rain-fade-uplink-ber."
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
  tags: [ecss, e-st-50c-communications-scope, e50-uplink-assumed-bit-error-rate-ber, uplink-assumed-bit-error-rate, worst-case-uplink-condition, unstated-ber-assumption, derived-figure-ber-consistency, rain-fade-uplink-ber]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Uplink Assumed Bit Error Rate (space-systems/ecss/e50-uplink-assumed-bit-error-rate-ber)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.11.5 —
that the bit error rate assumed for the uplink is stated — and the question is
whether the number every later uplink figure was derived from is written down,
worst case, and the same number throughout.

## Domain quick reference

- This is an assumption, not a result. Nothing downstream can check it,
  because every downstream figure is computed from it; an optimistic
  assumption produces a whole uplink case that is internally consistent
  and wrong.
- An unstated rate is the worst outcome, not a neutral one. Each analyst
  then supplies their own, the frame rejection page and the corrupted
  frame page disagree silently, and nobody can reproduce either number.
- A typical or mid-pass rate is the wrong statistic. The requirement has
  to hold at the worst declared condition, so the assumption has to be no
  better than the worst of low elevation, rain fade, interference and any
  other condition the mission declares.
- Equality with the worst condition is coverage. An assumption that
  exactly equals the worst declared rate satisfies the clause; only a
  rate that is genuinely better than a declared condition is optimistic.
- Consistency is half the obligation. A derived figure that recorded no
  rate, or recorded a different one, breaks the chain just as effectively
  as an absent assumption, and reads as compliant on its own page.
- Rates belong in exact decimal arithmetic. Writing one as ten raised to
  a negative power in binary floating point makes the same assumption a
  slightly different number on different hosts, and a consistency check
  then fails for a rounding reason rather than an engineering one.
- A margin in decades is a report, never a pass criterion. It is the one
  quantity here that needs a logarithm, and a logarithm is the one
  operation whose last bit differs between platforms.

## Workflow

1. Read the stated rate, accepting a number, a text rate or a mantissa
   and decimal exponent, and refuse a rate that is zero, negative, or so
   small or large that it is a unit mistake rather than a link.
2. Normalise the declared conditions, refusing a duplicate name, and rank
   them to find the worst.
3. Compare the stated rate with every condition in exact decimal, and
   name each condition the assumption is better than.
4. Compare the stated rate with the rate each derived figure recorded,
   treating an unrecorded rate as a disagreement.
5. Report the conservatism margin in decades for the reader, keeping it
   out of the pass criterion.
6. Return one verdict: unstated, optimistic, inconsistent, or sound, with
   the worst-case condition named either way.

## Pitfalls

- Leaving the assumption implicit because the link budget "obviously"
  implies it. Two pages then imply two different rates.
- Quoting a mid-pass or median rate. It is the friendliest condition on
  the sheet and the requirement is about the worst one.
- Grading an assumption that exactly equals the worst condition as
  optimistic. Equality is coverage, and failing it pushes designers to
  pad the assumption for no engineering reason.
- Checking the assumption and skipping the derived figures. A stated rate
  nobody used is documentation, not an input.
- Treating a derived figure with no recorded rate as agreeing. It agrees
  with nothing; it simply never said.
- Reconstructing the rate by raising ten to a power in binary floating
  point. The comparison then turns on the last bit and disagrees across
  hosts.
- Turning the decade margin into a pass criterion. It is the only
  logarithm in the clause and the least reproducible number in it.

## Behavior contract (gate 3)

Exact decimal rate parsing from a number, text or mantissa and exponent,
the credibility bounds, same-rate tolerance, condition normalisation with
duplicate rejection, worst-case ranking, coverage detection including the
equality case, derived-figure consistency including an unrecorded rate,
the decade margin and the four-way unstated / optimistic / inconsistent /
sound verdict are exercised by the gate 3 contract test:
scripts/test_e50_uplink_assumed_bit_error_rate_ber.py against
scripts/e50_uplink_assumed_bit_error_rate_ber_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_uplink_assumed_bit_error_rate_ber.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
