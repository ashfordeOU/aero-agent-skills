---
name: e5052-initiator-only
description: "Assess whether a SpaceWire RMAP unit declaring the initiator role only is internally consistent. Use when an ECSS-E-ST-50-52C clause 5.8.2.2 initiator-only conformance claim needs grading: confirm the unit builds commands, generates the header and data check fields, allocates transaction identifiers, supplies a reply address and reads the returned status, while claiming none of the target-side services it never executes; then check that acknowledged commands carry a non-zero identifier width, that the outstanding-transaction budget fits inside it, and that the reply timeout covers the round-trip estimate. Refuses an unknown role word, an unknown capability token and a negative identifier width. Trigger: ecss, e-st-50-52c, rmap-initiator-only-role, rmap-transaction-identifier-width, rmap-outstanding-transaction-budget, rmap-reply-address-generation, rmap-target-side-duty-claim, spacewire-rmap-conformance-profile."
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
  tags: [ecss, e-st-50-52-rmap-scope, e5052-initiator-only, rmap-initiator-only-role, rmap-transaction-identifier-width, rmap-outstanding-transaction-budget, rmap-reply-address-generation, rmap-target-side-duty-claim]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire RMAP — Initiator-Only Conformance (space-systems/ecss/e5052-initiator-only)

Use when the task is the initiator-only provision of ECSS-E-ST-50-52C
clause 5.8.2.2 — a unit that issues remote memory access commands but
never services one, and the question is whether its declared
conformance profile actually carries the initiator duties and stops
there.

## Domain quick reference

- A remote memory access transaction has exactly two sides. The
  initiator builds a command, puts it on the link and, when the command
  is acknowledged, waits for a reply. The target authorises the command,
  performs the memory access and builds the reply. An implementation
  that takes only the first of those two roles is graded against the
  first list alone.
- The initiator duty list is not only transmission. It also covers the
  header and data check fields the command carries, the allocation and
  retirement of a transaction identifier, the reply address that tells
  the target how to route the answer back, reception of that reply, and
  interpretation of the status the reply carries. Dropping any one of
  them leaves a device that can emit a command but cannot close a
  transaction.
- Claiming a target-side service is a scope error, not a bonus.
  Destination-key authorisation, memory access execution, reply
  generation, status generation and verify-buffer management belong to
  the servicing side; an initiator-only device that declares them has
  either mis-stated its role or built code it will never run and cannot
  test.
- The transaction identifier is what separates concurrent transactions.
  A device that issues acknowledged commands with a zero-width
  identifier cannot match a reply to the command that caused it, and a
  device whose outstanding-transaction budget exceeds its identifier
  space will reuse an identifier that is still in flight.
- The reply timeout is a link budget, not a preference. It has to cover
  the bytes of the command and the reply at ten bit times per character
  on the declared link rate, plus the turnaround the target is allowed.

## Workflow

1. Normalise the declared profile: role word, capability tokens,
   identifier width, outstanding-transaction budget, acknowledged-
   command flag and the optional timing figures. An unknown role word or
   capability token is an input error, not a finding to be softened.
2. Derive the owed and out-of-scope capability sets from the role, so a
   dual-role or target-only profile is not graded against the
   initiator-only list by accident.
3. Difference the claimed set against both derived sets: owed-but-absent
   tokens and claimed-but-out-of-scope tokens are separate findings and
   are reported separately.
4. Grade the identifier arithmetic. Acknowledged commands owe a non-zero
   width, and the outstanding budget must fit inside the identifier
   space; an unacknowledged-only device cannot track several outstanding
   transactions at all.
5. When link rate, command size, reply size and timeout are declared,
   form the round-trip estimate and compare it with the timeout,
   absorbing floating-point representation error at the boundary with a
   named tolerance rather than by inflating the timeout.
6. Report the missing list, the surplus list, the identifier space, the
   timeout record and a single conformant flag that is true only when
   every list is empty.

## Pitfalls

- Reading initiator-only as "transmits commands". The reply side of the
  transaction is still the initiator's work; a profile that omits reply
  reception or status interpretation is incomplete even though it can
  put a valid command on the link.
- Treating a target-side claim as harmless over-delivery. It is
  untestable code in a unit that is never addressed as a target, and it
  hides which of the two roles the declaration actually means.
- Sizing the identifier field from the average number of outstanding
  transactions instead of the declared maximum. The reuse hazard is set
  by the peak, and the peak is what the budget declares.
- Grading a dual-role profile with this clause. The clause governs the
  initiator-only declaration; a device that also answers commands owes
  the full list and has a different conformance question.
- Widening the reply timeout to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the budget stays as computed.

## Behavior contract (gate 3)

The profile validation, role-derived duty sets, missing and surplus
capability differencing, identifier-space arithmetic, round-trip
estimate and reply-timeout comparison are exercised by the gate 3
contract test: scripts/test_e5052_initiator_only.py against
scripts/e5052_initiator_only_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5052_initiator_only.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
