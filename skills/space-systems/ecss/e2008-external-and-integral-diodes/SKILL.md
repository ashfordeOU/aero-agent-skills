---
name: e2008-external-and-integral-diodes
description: "Use when a diode generic specification, agreement record or acceptance baseline is under review. Determine whether the generic specification governing acceptance of external and integral diodes was settled between customer and supplier before the work began, as clause 9.4.4 of ECSS-E-ST-20-08C asks. Confirm a specification is identified by issue, that both parties recorded agreement on that issue, that the later of the two agreement dates precedes the earliest acceptance activity, that external and integral diodes are each covered, and that no activity cites a superseded issue. Return an agreement verdict naming late, one-sided, uncovered and superseded cases. Trigger: ecss, e-st-20-08c, external-and-integral-diodes, diode-generic-specification-agreement, diode-specification-issue-currency, diode-customer-supplier-agreement-date, diode-specification-coverage-gap, diode-acceptance-baseline-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-external-and-integral-diodes, external-and-integral-diodes, diode-generic-specification-agreement, diode-specification-issue-currency, diode-customer-supplier-agreement-date, diode-specification-coverage-gap, diode-acceptance-baseline-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS External and Integral Diodes — Generic Specification (space-systems/ecss/e2008-external-and-integral-diodes)

Use when the task is clause 9.4.4 of ECSS-E-ST-20-08C: the generic specification
used for acceptance testing of external and integral diodes is settled between
customer and supplier beforehand. This leaf grades an acceptance baseline on
whether that agreement exists, covers both diode kinds, and predates the work it
is supposed to govern.

## Domain quick reference

- "Beforehand" is the whole clause. A specification agreed after the first
  acceptance activity has run does not govern that activity, it describes it,
  and the distinction is the difference between acceptance and a write-up.
- The comparison is against the EARLIER of the two dates in play: the agreement
  must precede the earliest acceptance activity, not the latest. Grading against
  the last activity in the campaign passes a baseline that was settled halfway
  through it.
- Agreement is two-sided by construction. A specification the supplier issued
  and the customer never countersigned is a supplier position; reporting it as
  agreed is the most common way this clause is missed on paper.
- The binding date is the later of the two party dates. The agreement is not in
  force until the second party has signed, so the earlier signature cannot be
  the one compared against the work.
- Agreement is per issue, not per document. A party that agreed issue 2 has not
  agreed issue 3, and carrying the old signature forward across a re-issue is a
  silent baseline change.
- An activity citing a superseded issue was run against a specification that no
  longer governs. It is reported as its own case because the remedy is a re-run
  or a justification, not a paperwork correction.
- Both diode kinds are named by the clause, and integral diodes are the ones
  that get dropped. A diode integral to the cell assembly is easy to read as
  covered by the assembly's own specification; the clause puts it here.
- An acceptance activity whose kind the specification does not cover is a
  coverage gap even when the activity itself is faultless, because nothing
  declares what its pass criteria were.
- The agreed share is a quotient of two party counts, so a baseline that meets
  the declared minimum exactly can evaluate a unit in the last place below it;
  the comparison absorbs that while the minimum stays as declared.

## Workflow

1. Validate the specification: a non-empty identifier, an issue number that is a
   positive integer, and a covered-kind list drawn only from the two kinds the
   clause names.
2. Validate each agreement record: a known party, the issue it was given
   against, and a calendar date in an unambiguous ordered form.
3. Grade agreement: which parties agreed the current issue, the agreed share
   against the declared minimum, and the binding date as the later of them.
4. Validate each acceptance activity: an identifier, a diode kind, a start date
   and the specification issue it cites.
5. Compare the binding date against the earliest activity start date and report
   the lead in days, negative where the baseline was settled late.
6. Report coverage gaps: a diode kind the specification does not cover, and a
   kind present in the activities but absent from the specification.
7. Report citation currency: every activity citing an issue other than the
   current one, kept apart from the coverage and timing findings.
8. Roll up one baseline verdict with late, one-sided, uncovered and superseded
   cases ranked.

## Pitfalls

- Grading the agreement date against the last acceptance activity. A baseline
  settled halfway through the campaign then reads as settled beforehand.
- Taking the earlier party date as binding. The agreement is not in force until
  the second party has signed.
- Accepting a one-sided record. A specification only the supplier signed is a
  supplier position, not an agreement.
- Carrying a signature across a re-issue. Agreement is per issue; the old
  signature is not evidence for the new one.
- Reading integral diodes as covered by the assembly specification. The clause
  names both kinds here, and the integral one is the one that gets dropped.
- Folding a superseded citation into the timing finding. The remedy differs -- a
  re-run or a justification, not a corrected date.
- Comparing dates as raw strings in mixed formats. The order has to come from
  parsed dates, or a baseline settled a year late can read as early.
- Judging an agreed share that lands exactly on its declared minimum by bare
  arithmetic, when the share is a quotient of two party counts.

## Behavior contract (gate 3)

The specification validation, the per-issue agreement rule, the two-party
binding date, the agreed share against the declared minimum, the lead in days
against the earliest acceptance activity, the coverage gaps over both diode
kinds, the superseded citation detector and the rolled-up baseline verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_external_and_integral_diodes.py against
scripts/e2008_external_and_integral_diodes_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_external_and_integral_diodes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
