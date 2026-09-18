---
name: e5053-ccsds-packet-transfer-service
description: "Assess the CCSDS Packet Transfer Service a SpaceWire node offers its user application under ECSS-E-ST-50-53C clause 5.2.1: validate the request parameters handed in, decide whether the transfer raises an indication or is discarded on its end marker, compare the delivered packet against the one given as unmodified, truncated, extended or altered, check the parameters survived, and confirm packet boundaries were neither merged nor split. Use when a packet arrives changed, doubled or not at all. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, ccsds-packet-transfer-service, service-request-indication, packet-boundary-preservation, error-end-of-packet-discard, unmodified-packet-delivery."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-ccsds-packet-transfer-service, ccsds-packet-transfer-service, service-request-indication, packet-boundary-preservation, error-end-of-packet-discard, unmodified-packet-delivery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Packet Transfer Service (space-systems/ecss/e5053-ccsds-packet-transfer-service)

Use when the task is the service itself that ECSS-E-ST-50-53C clause 5.2.1
obliges the protocol to provide — one CCSDS packet handed in with its
destination parameters at the sending end, the same packet handed out whole
and unchanged at the receiving end, as one delivery.

## Domain quick reference

- The service is defined by what the two user applications see, not by the
  octets on the link. Assessing it at the primitive level keeps the
  assessment valid across implementations that lay the fields out
  differently, and it is the level at which the obligation is written.
- Four failures are possible and they are genuinely different: the packet
  was not delivered at all, it was delivered changed, it was delivered as
  more or fewer deliveries than it was given, or it arrived with different
  parameters. Each points at a different part of the stack, so collapsing
  them into one "transfer failed" costs the investigation its first clue.
- The end marker decides delivery before the content does. A transfer that
  ends on the error marker is discarded and raises no indication at all;
  that is the service working as specified, not a fault of the service. A
  transfer that ends with no marker never had a packet boundary, and that
  is a fault.
- Whole and unchanged is not the same as long enough. A delivery that is a
  correct leading run of the packet was cut short; one that carries extra
  octets after the packet picked something up; one that differs inside is
  corrupted. The three have different causes and the comparison can tell
  them apart cheaply.
- Packet boundaries are part of the delivery, not a detail of it. Two
  packets given in and one delivery out is a failure even when every octet
  is present, because the receiving application can no longer tell where
  one packet ended.

## Workflow

1. Validate the request the sending application makes: a packet long enough
   to hold a CCSDS primary header and at least one octet of data, a
   routing prefix of octets or none at all, and the destination and user
   parameters each within the octet that carries them.
2. Validate how the transfer ended. The normal marker permits an
   indication; the error marker means discard; the absence of any marker
   means the boundary was never established.
3. On a normal end, raise the indication and carry the parameters into it,
   taking the delivered parameter values where they are known rather than
   assuming the requested ones arrived.
4. Group the delivered packet against the one given: unmodified,
   truncated, extended or altered. Test the leading-run cases explicitly so
   a short delivery is not reported as corruption and a corrupted short
   delivery is not reported as a clean truncation.
5. Compare the delivered parameters with the requested ones and report each
   disagreement as its own finding, so a parameter fault and a packet fault
   are never merged.
6. Across a run, compare the sequence of packet lengths given in with the
   sequence delivered out. Equal sequences mean boundaries survived;
   anything else means the service merged or split deliveries.

## Pitfalls

- Reporting an error-marker discard as a service failure. Discarding a
  transfer that ended on the error marker is what the service is supposed
  to do; the fault it reflects lies on the link, and the service met its
  obligation by not delivering a damaged packet upward.
- Checking only the delivered length. Equal lengths with different content
  is the corruption case the length check cannot see, and it is the one
  that reaches the application as plausible data.
- Treating a short delivery as corruption. A delivery that matches the
  start of the packet exactly was cut, which points at a buffer or an
  early marker, not at bit errors.
- Assuming the requested parameters are the delivered ones. That makes the
  parameter check tautological, and a service that quietly rewrites a
  parameter passes it every time.
- Judging boundary preservation from the total octet count. Two packets
  merged into one delivery preserve every octet and still destroy the
  boundary the receiving application needs.

## Behavior contract (gate 3)

The request validation, end-marker handling, the indication and discard
outcomes, the four-way delivery grouping including both leading-run cases,
the parameter comparisons and the boundary-sequence check are exercised by
the gate 3 contract test:
scripts/test_e5053_ccsds_packet_transfer_service.py against
scripts/e5053_ccsds_packet_transfer_service_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e5053_ccsds_packet_transfer_service.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
