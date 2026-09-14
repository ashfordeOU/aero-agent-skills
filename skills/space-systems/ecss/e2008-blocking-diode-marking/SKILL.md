---
name: e2008-blocking-diode-marking
description: "Assess the marking approach settled with the customer for delivered planar blocking diodes under ECSS-E-ST-20-08C clause 12.2.3: read the standing of the agreement before reading the mark, refuse a scheme the supplier chose alone or one whose agreement was superseded, size the identity code against the carrier face it is written on at the height it stays legible at, weigh how far down handling a mark on that carrier survives, count the diodes one mark really resolves a delivered part to, and name the approach to settle instead. Use when a planar blocking diode marking approach, customer marking agreement or delivery identity claim has to be reviewed. Trigger: ecss, e-st-20-08c, planar-blocking-diode-marking-approach, blocking-diode-marking-customer-agreement, blocking-diode-code-face-fit, blocking-diode-mark-carrier-retention, blocking-diode-identity-granularity, planar-blocking-diode-delivery-identity."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-marking, planar-blocking-diode-marking-approach, blocking-diode-marking-customer-agreement, blocking-diode-code-face-fit, blocking-diode-mark-carrier-retention, blocking-diode-identity-granularity, planar-blocking-diode-delivery-identity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Marking (space-systems/ecss/e2008-blocking-diode-marking)

Use when the task is clause 12.2.3 of ECSS-E-ST-20-08C: how delivered planar
blocking diodes are marked is not a method the standard fixes, it is an
approach settled together with the customer. The review therefore starts at
the agreement and only then looks at the mark itself.

## Domain quick reference

- Agreement is the first requirement, not a wrapper around a technical one. A
  scheme the supplier picked alone fails the clause however legible, however
  permanent and however cleverly coded the mark is, because nobody on the
  receiving side committed to reading it that way.
- Agreement has five standings, not two. A recorded agreement binds, and only
  if it actually names a document somebody can read it back from. A verbal
  agreement binds the delivery it was made for and nothing at the next one.
  A superseded agreement was real once, which is exactly why the difference
  between the two schemes has to be dispositioned. A proposal nobody answered
  and a scheme nobody was asked about bind nothing at all.
- An agreement that settles no approach settles nothing, however warmly both
  sides remember the meeting.
- Once the agreement stands, three physical questions decide whether the
  approach delivers an identity at all, and they pull against each other on a
  part this small: fit, retention and granularity.
- Fit is arithmetic, not judgement. An identity code has a character count and
  a height below which it stops being legible, and the carrier it is written
  on has a finite face. A code that does not fit is an aspiration.
- Retention is the stage the mark survives to. A label on a shipping carrier
  stops at incoming inspection: the diode leaves the bag and the identity
  stays behind. Body marks reach further, and how much further depends on
  whether the mark survives cleaning, mounting and integration.
- Granularity is what one mark resolves a delivered diode to. A lot bag label
  resolves it to the whole lot, so a part pulled from the bag carries no
  identity of its own. Counting a lot label as traceability is how a delivery
  claims part identity it never had.
- The order of the three matters. A code that does not fit is reported before
  the retention it would have had, because the mark that was measured cannot
  be applied in the first place.

## Workflow

1. Resolve policy: whether a verbal agreement is accepted, the handling stage
   identity is owed through, and how many diodes one mark may resolve a
   delivered part to. All three are project positions.
2. Grade the agreement standing and check it names a catalogued approach and,
   where it claims to be recorded, a document to read it back from.
3. Size the identity code on the carrier face the agreed approach writes on,
   at the declared character height or the approach's legible minimum.
4. Read how far down handling a mark on that carrier survives, against the
   stage identity is owed through.
5. Count the diodes one mark resolves a delivered part to -- one for a body
   mark, the package for a carrier label, the lot for a bag label.
6. Rank the approach: not agreed first, then a code that does not fit, then
   retention short, then granularity short.
7. Grade every catalogued approach the same way and name the longest-lived
   workable one as the approach to settle with the customer instead.
8. Report the delivery: the agreement standing, the graded approach, the
   acceptable alternatives and every finding in order.

## Pitfalls

- Starting at the mark. A legible, permanent, part-level mark that nobody
  agreed still fails this clause, and the review that opened with a
  magnifier never asks the question the clause is actually about.
- Reading a recorded agreement that names no document as recorded. Nothing can
  be read back from it, so it is a memory rather than an agreement.
- Treating a verbal agreement as binding on the next delivery. It bound the
  room it was made in, and the next lot is a different room.
- Waving a superseded agreement through. It was the standard once, which is
  precisely why the delta between the two schemes needs a disposition.
- Reading a lot or package label as part identity. The mark resolves a
  delivered diode to a population, and the part pulled out of the bag is
  carrying nothing.
- Checking legibility without checking the face. A character height chosen for
  readability writes a code wider than the diode it is going on.
- Reporting retention on a code that does not fit. The mark that survives well
  is one that could never be applied, so the fit finding comes first.
- Assuming the marking face is generous because the carrier is. A planar
  blocking diode body is millimetres across, and the approach that survives
  furthest is usually the one with the least room to write on.
- Judging a code footprint that lands exactly on the face by bare arithmetic.
  The footprint is a sum of products of a character height, so a code laid out
  to exactly fill its face can evaluate a unit in the last place above it; the
  comparison absorbs that while the declared face stays as declared.

## Behavior contract (gate 3)

The five agreement standings and which of them bind, the code footprint and
its fit against the declared carrier face, the legible character height
minimum, the handling stage each carrier's mark survives to, the diodes one
mark resolves a delivered part to, the ranked approach verdict, the
recommended alternative and the rolled-up delivery verdict are exercised by
the gate 3 contract test: scripts/test_e2008_blocking_diode_marking.py
against scripts/e2008_blocking_diode_marking_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_blocking_diode_marking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
