---
name: e2007-emission-identification-rule
description: "Assess every emission under ECSS-E-ST-20-07C clause 5.2.9.2. Use when a survey must be held to the bandwidth its frequency range prescribes whatever character the signal is judged to have: normalize the recorded character without letting it act, decide whether the receiver was set to the prescribed bandwidth, quantify the level shift a substitution carries, refuse an emission left out of the record on character grounds, grade every level against its limit and name the ones that must be reported, then group the survey by character and catch a bandwidth that tracks the character instead of the range. Trigger: ecss, e-st-20-07c, emission-identification-rule, signal-character-neutrality, prescribed-emission-bandwidth, broadband-narrowband-neutral-measurement, character-based-omission, emission-record-completeness, emission-limit-grading."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-emission-identification-rule, signal-character-neutrality, prescribed-emission-bandwidth, broadband-narrowband-neutral-measurement, character-based-omission, emission-limit-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Emission Identification Rule (space-systems/ecss/e2007-emission-identification-rule)

Use when the task is the identification rule of ECSS-E-ST-20-07C clause
5.2.9.2 -- the demand that every emission a survey finds is measured
with the bandwidth its frequency range prescribes, whatever character
the signal is judged to have, and reported on that basis.

## Domain quick reference

- The rule is a negative one and that is its whole force. It does not
  say how to judge a signal; it says the judgement may not reach the
  measurement. A character noted in the record is a note, not an input
  to a bandwidth, a limit or a decision to report.
- The bandwidth therefore comes from one place only: the frequency
  range the emission sits in. Two emissions at the same frequency are
  measured identically even if one is a carrier and the other is a
  commutation transient, and the record has to show that.
- A bandwidth substitution is not a neutral bookkeeping change. Reported
  against a limit written for the prescribed bandwidth, a level taken
  in another bandwidth is off by the ratio of the two taken as a voltage
  ratio. That shift is worth computing and reporting, so the size of the
  substitution is visible -- but it is never applied as a correction to
  bring the level back onto the limit, because the correction would
  quietly legitimise the substitution.
- Omission is the second failure mode and the harder one to see. An
  emission left out because it was taken for an artefact, a harmonic of
  the ambient or a broadband feature leaves no trace in a levels table.
  A record that carries a reason for the omission at least admits the
  decision was made; the rule admits no such omission at all.
- Whether an emission has to be reported follows from its level against
  its limit, and from nothing else. An exceedance marked unreported is a
  finding whatever the character beside it says.
- Character-driven bandwidth is visible in the aggregate even when no
  single record looks wrong. Group the survey by the character recorded
  and compare: a character whose every emission was taken at one and
  the same non-prescribed ratio, while other characters were taken as
  prescribed, is the rule being broken systematically rather than by
  accident. A survey that deviates everywhere is a different defect --
  a wrong bandwidth table -- and a survey whose deviations scatter is a
  third.
- A level sitting exactly on its limit does not exceed it. The
  comparison absorbs representation error rather than moving the limit.

## Workflow

1. Normalize the emission record: identifier, frequency, recorded
   character, prescribed and applied bandwidth, level, optional limit,
   optional reported flag and optional omission reason. Reject an
   unknown key, a missing required key, a blank identifier, an
   unrecognized character, a non-boolean reported flag and a blank
   omission reason.
2. Fold the character to a canonical spelling so that hyphenation and
   casing cannot split one group into two, and keep an undetermined
   character as a first-class value rather than a reason to skip.
3. Decide whether the applied bandwidth is the prescribed one, treating
   a last-place difference as equality, and compute the level shift the
   substitution would carry as a voltage ratio in decibels.
4. Grade the level against its limit when one is given, with the equal
   case counted as meeting the limit. Leave the grade open, not false,
   when no limit was supplied.
5. Raise a finding for a non-prescribed bandwidth, for any omission
   reason at all, and for an exceedance marked unreported.
6. Group the evaluated survey by recorded character and look for a
   group whose every member deviates by one identical ratio while some
   other group conforms; that pattern, and not a scattered one, is the
   character-driven bandwidth this clause forbids.
7. Name every emission above its limit, whatever its character, as the
   set that has to be reported.
8. Aggregate: report the as-prescribed fraction, the graded count, the
   reportable identifiers and the character audit, and accept the
   survey only when no finding remains.

## Pitfalls

- Widening the receiver for a signal taken to be broadband. That is the
  exact substitution the clause exists to stop, and it makes the level
  incomparable with the limit it is reported against.
- Correcting a level by the bandwidth ratio so the substituted
  measurement can still be graded. The shift is reported to expose the
  substitution, not to repair it; applying it makes an unprescribed
  measurement look prescribed.
- Dropping an emission because it was taken for an artefact or an
  ambient harmonic. Ambient separation is a different rule with its own
  evidence; a character judgement is never the licence to omit.
- Treating an undetermined character as a reason to defer a point. The
  bandwidth does not depend on the character, so an undetermined
  character blocks nothing and the point is measured like any other.
- Auditing only record by record. A character-driven bandwidth can be
  perfectly consistent inside each record and only shows when the
  survey is grouped by character and the groups are compared.
- Reading any deviation as character-driven. A survey that deviates
  across every character is a wrong bandwidth table, and scattered
  ratios are sloppy setup; calling either one a character effect sends
  the investigation to the wrong place.
- Grading a level that sits exactly on its limit as an exceedance. The
  equality is a representation question, settled with a tolerance
  inside the comparison and never by moving the limit.

## Behavior contract (gate 3)

The character normalization, the prescribed-bandwidth decision, the
substitution level-shift computation, the limit grading, the omission
and unreported-exceedance findings, the character grouping audit, the
reportable set and the whole-survey verdict are exercised by the gate 3
contract test:
scripts/test_e2007_emission_identification_rule.py against
scripts/e2007_emission_identification_rule_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_emission_identification_rule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
