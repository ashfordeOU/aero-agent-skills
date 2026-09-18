---
name: q6005-hybrid-manufacturer-category-definitions
description: "Identify which of the two hybrid microcircuit procurement categories a maker falls in for a given build, and say what decided it. Use when a hybrid buy has to be routed under ECSS-Q-ST-60-05 clause 5.2: test every production-line approval the maker offers against the site, the line and the process technology the part will actually be built on, and against the standing and dates the approval carries, put the maker in the approved-line category only when one approval covers all of them at once, and name the near misses that would otherwise promote it. Trigger: ecss, q-st-60-05-clause-5-2, hybrid-microcircuit-procurement-category, hybrid-category-split-per-build, hybrid-line-approval-scope-match, hybrid-manufacturer-category-boundary, sister-line-approval-near-miss."
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
  tags: [ecss, q-st-60-eee-scope, q6005-hybrid-manufacturer-category-definitions, hybrid-microcircuit-procurement-category, hybrid-category-split-per-build, hybrid-line-approval-scope-match, hybrid-manufacturer-category-boundary, sister-line-approval-near-miss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Manufacturer Category Boundary (space-systems/ecss/q6005-hybrid-manufacturer-category-definitions)

Use when the task is the clause 5.2 category split of ECSS-Q-ST-60-05 — the
standard recognises two kinds of hybrid microcircuit maker, one whose
production line already carries an approval and one whose line does not, and
everything downstream hangs off which of the two this maker is for this
particular part.

## Domain quick reference

- The category is a property of a build, not of a company. The same maker can
  be in one category for a thick-film hybrid on one line and in the other for
  a multi-chip module on the line next to it. Asking which category a company
  is in, without naming the site, the line and the technology, has no answer.
- An approval names three things and is bounded by all of them. A site, a
  production line inside that site, and the process technologies it was
  granted for. A line approval carried over from a sister site, or from the
  line that runs alongside, is a different approval that happens to share a
  name, and the corporate group holding an approval somewhere is not the
  line holding one here.
- Dates and standing sit on top of scope. An approval that covers the build
  perfectly but has lapsed, been suspended or been withdrawn puts the maker
  in the other category as surely as no approval at all, and a suspension
  with years of nominal validity left is the version of this that reads as
  healthy on a file listing.
- The split is not a quality judgement. The second category is not a worse
  maker; it is a maker whose line evaluation and line approval are still in
  front of it, and the procurement sequence it runs is longer for that
  reason alone.
- Near misses are the failure mode worth reporting by name. An approval that
  covers the line but not the technology, or the technology but not this
  line, is the one a buyer is most likely to read as covering, and the split
  is decided wrongly far more often by a plausible near miss than by an
  absent approval.

## Workflow

1. Pin the build down: the site, the production line within it, and the
   process technology of the hybrid. A missing element is an input error,
   not a wildcard.
2. Canonicalise every offered approval: an identifier, the site and line it
   was granted for, the technologies it covers, its issue and expiry dates
   and its standing. Reject a record that expires before it was issued, and
   reject a repeated identifier rather than merging the two.
3. Test each approval on every dimension at once and keep all the reasons it
   fails, not just the first. A verdict alone cannot tell a sister-line
   approval apart from an approval that is wrong in three ways.
4. Report a site miss and a line miss as distinct reasons, so an approval for
   another plant is never read as an approval for the line next door.
5. Put the maker in the approved-line category only when at least one
   approval covers the site, the line and the technology and is in force on
   the decision date; otherwise place it in the other category.
6. When no approval covers, list the near misses — an approval failing on
   exactly one count — with the reason, and state that the near miss does
   not move the category.

## Pitfalls

- Categorising the company rather than the build. A maker with an approved
  thin-film line is in the second category for a thick-film part, and a
  category recorded against the supplier name will be reused on the wrong
  part later.
- Reading an approval for the same line number at another site as covering.
  Line names repeat across plants, and the site is the half of the pair that
  gets dropped.
- Checking the expiry and stopping. A suspended or withdrawn approval usually
  has a perfectly good expiry date, and it is the standing that decides.
- Treating a near miss as a technicality to be waived. A waiver may well be
  the right project decision, but it is a decision taken outside this split;
  the category itself is not what bends.
- Assuming the shorter procurement route once the maker is grouped as
  approved-line without having fixed the decision date. An approval that
  lapses between the category decision and the order puts the buy back on the
  longer route, so the date the category was decided on travels with it.

## Behavior contract (gate 3)

The build validation, approval record validation, site, line and technology
coverage tests, in-force and standing resolution, exclusion-reason
enumeration, near-miss detection and the two-category decision are exercised
by the gate 3 contract test:
scripts/test_q6005_hybrid_manufacturer_category_definitions.py against
scripts/q6005_hybrid_manufacturer_category_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_hybrid_manufacturer_category_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
