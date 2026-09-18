---
name: e5053-user-application-value
description: "Verify that the user application value of a CCSDS packet transfer protocol data unit reaches the receiving application unchanged under ECSS-E-ST-50-53C clause 5.1.6: check the value fits the field, compare what was sent against what was delivered and count the bits that moved, resolve the delivered value against the receiving application's own assignment, and keep a transport alteration apart from an unrecognised but faithfully carried value. Use when a value arrives that the receiving application cannot interpret. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, user-application-value, transparent-value-carriage, application-value-assignment, end-to-end-value-integrity, unrecognised-application-value."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-user-application-value, user-application-value, transparent-value-carriage, application-value-assignment, end-to-end-value-integrity, unrecognised-application-value]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — User Application Value (space-systems/ecss/e5053-user-application-value)

Use when the task is the user application value of the CCSDS packet transfer
protocol data unit of ECSS-E-ST-50-53C clause 5.1.6 — a value the sending
application chooses, the protocol carries without interpreting, and the
receiving application is handed exactly as it was written.

## Domain quick reference

- The obligation on the protocol is transparency, nothing more. The
  protocol does not validate the value, does not act on it and does not
  assign it a meaning; it moves it. Any behaviour conditioned on the value
  inside the transfer layer is outside what the clause allows.
- The meaning is an agreement between the two applications. It is recorded
  in an interface document or an application value assignment, and it is
  entirely legitimate for a value to be meaningless to a receiver that was
  not party to the agreement.
- Those two facts separate two very different faults. A value the transport
  changed is a transport fault, chargeable to the link, the relay or the
  buffer handling. A value the transport carried faithfully that the
  receiving application does not recognise is an agreement fault,
  chargeable to the interface definition. They have no corrective action in
  common.
- Because the value is not consumed or rewritten anywhere on the way, an
  end-to-end comparison is meaningful in a way that a comparison of the
  routing prefix never is. The count of bits that differ is a usable
  signature: a single bit points at the link, a wholesale change points at
  a buffer.
- A field with no declared assignment at the receiving end is not an error
  condition in itself. It becomes one only where the receiving application
  has declared that it accepts assigned values only.

## Workflow

1. Validate the value the sending application offered against the width of
   the field; a value that does not fit cannot be carried and is refused at
   the source rather than truncated into it.
2. Validate the receiving application's value assignment, refusing an
   assignment that reuses one meaning for two values, since that makes the
   delivered value ambiguous on arrival.
3. Compare the value delivered against the value sent and group the
   carriage as transparent or altered, recording how many bits differ.
4. Resolve the delivered value against the assignment and group it as
   registered or unregistered. Do this on the delivered value, never on the
   sent one, so an alteration cannot be masked by a meaning that was only
   ever true at the sending end.
5. Report an alteration as a finding always; report an unregistered value
   as a limitation by default and as a finding only where the receiving
   application has declared it accepts assigned values only.
6. Over a run of transfers, keep the altered count, the index of the first
   altered transfer and the accumulated bit differences so an intermittent
   transport fault shows as a rate and a signature rather than a single
   anomaly.

## Pitfalls

- Letting the transfer layer act on the value. The moment routing,
  discard or priority is conditioned on it, the field stops being a user
  value and the two applications lose a channel they were promised.
- Resolving the meaning from the sent value. That hides exactly the case
  the end-to-end comparison exists to catch, because the meaning looks
  correct while the delivered value is wrong.
- Treating an unregistered value as corruption. A faithfully carried value
  with no local meaning is an interface agreement gap, and sending it to
  the link team wastes the investigation.
- Reporting an alteration without the bit count. One flipped bit and a
  wholesale substitution are different failures with different causes, and
  the count is the cheapest discriminator available.
- Building an assignment where two values share a meaning. Resolution then
  cannot be inverted, and an operator reading a decoded log cannot tell
  which value actually arrived.

## Behavior contract (gate 3)

The field validation, assignment construction and its uniqueness refusal,
the transparent versus altered grouping with its bit count, meaning
resolution on the delivered value, the finding-versus-limitation split and
the run summary are exercised by the gate 3 contract test:
scripts/test_e5053_user_application_value.py against
scripts/e5053_user_application_value_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e5053_user_application_value.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
