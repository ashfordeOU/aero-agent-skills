---
name: e50-telemetry-authentication-and-encryption
description: "Assess the protection applied to a telemetry stream under ECSS-E-ST-50C clause 5.5.7: map each stream's declared sensitivity tier onto the authentication and confidentiality services it owes, refuse confidentiality offered without integrity, compute the per-frame overhead of tag, initialisation vector and block padding, check the remaining useful throughput still carries the source demand, size the key against the years it must stand, and find the frame counter that exhausts inside one key period. Use when specifying telemetry security services, reviewing a key and counter plan, or costing protection overhead. Trigger: ecss, e-st-50-communications-scope, telemetry-authentication-and-encryption, telemetry-sensitivity-tier-mapping, frame-authentication-tag-overhead, telemetry-key-strength-lifetime, frame-counter-exhaustion, protected-telemetry-throughput."
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
    clause: 5.5.7
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications-scope, e50-telemetry-authentication-and-encryption, telemetry-protection-services, telemetry-sensitivity-tier-mapping, frame-authentication-tag-overhead, telemetry-key-strength-lifetime, frame-counter-exhaustion, protected-telemetry-throughput]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telemetry Authentication and Encryption (space-systems/ecss/e50-telemetry-authentication-and-encryption)

Use when the task is the telemetry protection provision of ECSS-E-ST-50C
clause 5.5.7 — deciding which telemetry streams are authenticated, which
are encrypted, and showing that the resulting protection is both strong
enough for the mission and affordable in the downlink budget.

## Domain quick reference

- Authentication and confidentiality are separate services answering
  separate questions. Authentication says the frame came from this
  spacecraft and was not altered; confidentiality says a third party
  cannot read it. A mission can need either, both, or neither per
  stream, and the sensitivity tier of the data is what decides.
- Confidentiality without integrity is a defect, not a cheaper option.
  An encrypted frame that carries no tag can be altered in flight and
  will decrypt to something; the receiver has no way to tell. Wherever
  encryption is applied, the integrity service goes with it.
- Overhead is per frame, and it is not only the tag. The tag, the
  initialisation vector or counter that makes each frame unique, and the
  padding a block cipher needs to reach a whole block all consume
  payload space, so the useful throughput of a protected downlink is
  measurably below its raw rate.
- Key strength is judged against the time the data must stay protected,
  not against the mission duration. Data that must stay protected for
  twenty years needs a key that is credible in twenty years, which is
  usually a longer key than the one that protects a housekeeping stream
  for the length of a pass.
- The uniqueness counter is a hard limit. A counter of n bits admits
  two-to-the-n frames under one key; once it wraps, two frames share an
  initialisation vector, and for most modes that is a break. The key
  rotation period has to come before the counter wraps, which is
  arithmetic on the frame rate, not a policy preference.
- Grouping streams by tier is how this stays proportionate. Protecting
  everything at the highest tier costs throughput on every stream;
  leaving the tiers unmapped means the decision is made per stream by
  whoever implements it.

## Workflow

1. Validate each stream: a name, a sensitivity tier the mapping knows,
   a positive frame payload in bits and a positive frame rate.
2. Map the tier onto the services owed — authentication, confidentiality
   or both — setting aside whatever the mission already covers by some
   other means it can point to, since these services are owed for what
   is left over. Compare that remainder with the services the design
   actually applies; report a shortfall and report encryption applied
   without integrity.
3. Compute the per-frame overhead: the authentication tag when
   authentication applies, the initialisation vector or counter when
   confidentiality applies, and the padding needed to fill the last
   cipher block.
4. Compute the protected useful throughput as the frame rate times the
   payload that survives the overhead, and compare with the demand the
   stream has to carry.
5. Size the key: compare the declared key length with the minimum for
   the number of years the data must stay protected.
6. Compute the frames sent under one key as the frame rate times the key
   rotation period, and compare with the span of the uniqueness counter.
7. Report per stream the services owed and applied, the overhead, the
   useful throughput, and every finding.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.5.7a | 2 |

## Pitfalls

- Applying encryption to a stream and leaving it unauthenticated. It
  reads as the stronger choice and is the weaker one: the receiver
  cannot detect a modified frame at all.
- Costing the overhead as the tag alone. The initialisation vector and
  the block padding together are often larger than the tag, and on a
  small frame they can cost a tenth of the payload.
- Sizing the key from the mission length. The protection period is how
  long the content stays sensitive, which routinely outlives the
  spacecraft.
- Choosing the key rotation period by operational convenience. The
  counter span divided by the frame rate is an upper bound on it, and a
  high-rate stream can exhaust a short counter in hours.
- Leaving the tier mapping implicit. Without a stated tier per stream,
  the protection decision migrates into the implementation and cannot be
  reviewed as a whole.

## Behavior contract (gate 3)

The stream validation, tier-to-service mapping, integrity pairing rule,
per-frame overhead computation, useful-throughput comparison, key
sizing and counter-exhaustion arithmetic are exercised by the gate 3
contract test:
scripts/test_e50_telemetry_authentication_and_encryption.py against
scripts/e50_telemetry_authentication_and_encryption_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e50_telemetry_authentication_and_encryption.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
