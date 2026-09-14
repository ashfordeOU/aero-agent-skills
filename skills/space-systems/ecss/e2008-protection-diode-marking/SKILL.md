---
name: e2008-protection-diode-marking
description: "Audit the marking approach chosen for delivered external protection diodes under ECSS-E-ST-20-08C clause 9.2.3: establish that the customer actually agreed the approach and that the agreement is recorded and still in force, catch a carrier the delivery changed without asking, work out how far down the handling chain a mark on that carrier survives against the stage identity is owed to, check the code physically fits the face it is put on, and size what a package or lot level scheme really resolves a part to. Use when a protection diode marking agreement, part marking scheme or diode delivery traceability claim has to be reviewed. Trigger: ecss, e-st-20-08c, external-protection-diode-marking, diode-marking-customer-agreement, diode-mark-carrier-retention, diode-code-face-fit, diode-identity-granularity, protection-diode-delivery-traceability."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-protection-diode-marking, external-protection-diode-marking, diode-marking-customer-agreement, diode-mark-carrier-retention, diode-code-face-fit, diode-identity-granularity, protection-diode-delivery-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- External Protection Diode Marking (space-systems/ecss/e2008-protection-diode-marking)

Use when the task is clause 9.2.3 of ECSS-E-ST-20-08C: external protection
diodes are delivered as discrete parts, and how they are marked is not a
method the standard fixes -- it is a choice made with the customer. The review
therefore starts at the agreement and only then looks at the mark.

## Domain quick reference

- Agreement is the first requirement, not a formality wrapped around a
  technical one. A scheme the supplier picked alone fails this clause however
  legible, however permanent and however cleverly coded the mark is, because
  nobody on the receiving side committed to reading it that way.
- Agreement has five standings, not two. Recorded agreement binds. A verbal
  agreement binds the delivery in the room and nothing at the next one. A
  superseded agreement was real once, which is exactly why the difference
  between the two schemes has to be dispositioned. A proposal nobody answered
  and a scheme nobody was asked about bind nothing at all.
- An agreement names a carrier, so a delivery that moved the mark somewhere
  else is delivering against an agreement about something different. That is a
  change the customer has not seen, whatever its merits.
- Where the mark is carried decides how long identity lasts, and the chain has
  stages. A mark on the part itself is still there when it is fitted into the
  wiring. A mark on a lead goes when the lead is trimmed and formed. A mark on
  the bag ends when the part comes out of the bag; a mark on the shipping tray
  ends when the shipper is opened.
- The stage identity is owed to is set by what the part is for. An external
  protection diode is fitted into the harness by somebody kitting loose parts,
  so a scheme that stops at incoming inspection stops two steps before the
  moment it was needed.
- A code that does not fit is not a scheme. The characters times the pitch is a
  length, the face is a length, and a review that never compares the two hands
  the problem to the marking bench.
- Granularity decides what the mark resolves to. An item code resolves a part
  to itself; a package code resolves it to whatever else shared the bag; a lot
  code resolves it to the delivery. Coarse granularity is not a smaller version
  of fine granularity, it is a different answer to the question.
- Resolution is therefore a number, one over the size of the set the part
  resolves to, and it drops fast: ten to a bag is a tenth of an identification.

## Workflow

1. Take the delivery as a list of external diode types, each carrying its part
   type, the standing of the marking agreement, the carrier the agreement
   names, the carrier the delivery actually used, the identity granularity, the
   delivered and per-package counts, and the code length, character pitch and
   available face length.
2. Resolve the agreement standing first: binding, binding under concession, or
   not binding, and compare the agreed carrier with the delivered one.
3. Read the retention stage off the carrier the delivery used, and report the
   step that loses the mark rather than the carrier alone.
4. Compare that stage with the stage identity is owed to and record the
   shortfall in handling steps.
5. Where something is marked, multiply the code length by the character pitch
   and hold it against the available face with a comparison that absorbs
   representation error.
6. Work out what the granularity resolves a part to, as one over the size of
   that set, and hold it against the resolution floor.
7. Grade each type: no binding agreement or nothing marked is not established;
   a shortfall, a code that does not fit, a coarse resolution or a concession
   standing is short; anything else is adequate.
8. Roll the delivery up: the verdict, the types with nothing established, the
   adequate share and the weakest type by verdict then by shortfall.

## Pitfalls

- Reviewing the mark and never asking who agreed to it. This clause is about a
  bilateral choice, and a perfect unilateral scheme does not satisfy it.
- Accepting a verbal agreement because everyone remembers the conversation.
  Nothing on file survives the people who were in the room.
- Treating a superseded agreement as no agreement, or as the current one. It
  binds under concession once the difference has been looked at, and both of
  the simpler readings skip that step.
- Waving through a carrier change on the grounds that the new carrier is
  better. Better is still different from what was agreed.
- Grading the marking method and stopping there. A code on the bag and a code
  on the body are the same code; only one of them is still there at mounting.
- Assuming a mark on a lead is a mark on the part. Leads are trimmed and formed
  at mounting, which is precisely the step the mark was needed for.
- Approving a scheme nobody measured. A code that needs more face than the
  diode body offers fails at the bench, not at the review.
- Reading a package code as a slightly weaker item code. It resolves a part to
  a set, and a set is not a part however small the bag is.
- Comparing a code length against the face, or a resolution share against its
  floor, by bare arithmetic. A code cut exactly to the face is a product of
  measured lengths and can evaluate a unit in the last place over, so the
  comparison absorbs that while the face stays as measured.

## Behavior contract (gate 3)

The five agreement standings, the agreed-against-delivered carrier comparison,
the carrier retention table, the shortfall in handling steps including the
unmarked delivery, the code-against-face fit with its exact-boundary case, the
identity resolution share, the per-type verdict and the delivery roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_protection_diode_marking.py against
scripts/e2008_protection_diode_marking_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_protection_diode_marking.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
