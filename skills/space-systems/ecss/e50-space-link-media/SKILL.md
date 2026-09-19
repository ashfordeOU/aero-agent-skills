---
name: e50-space-link-media
description: "Assess the transmission media carrying a mission's space links against what those links must deliver, under ECSS-E-ST-50C clause 5.6.12.1: every link names a medium the mission declared and agreed, and that medium supports the link's required rate, range and availability. Compute per-criterion utilisation, separate a medium with headroom from one that only just fits from one that cannot carry the link, rank the media a link could use, and flag a medium outside the interoperable set. Use when choosing or reviewing the RF or optical medium of a spacecraft space link. Trigger: ecss, e-st-50-communications, space-link-medium-selection, space-link-media-capability-envelope, rf-versus-optical-space-link-medium, space-link-medium-availability-margin, space-link-medium-interoperability."
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
  tags: [ecss, e-st-50-communications, e50-space-link-media, space-link-medium-selection, space-link-media-capability-envelope, rf-versus-optical-space-link-medium, space-link-medium-availability-margin, space-link-medium-interoperability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Space Link Media (space-systems/ecss/e50-space-link-media)

Use when the medium a space link will fly on is being chosen or reviewed, per
ECSS-E-ST-50C clause 5.6.12.1 — which medium each link names, and whether that
medium can actually carry it.

## Domain quick reference

- Two obligations, and they fail in different ways. Every link names the
  medium it uses, and that medium is one the mission declared and agreed.
  Separately, the named medium supports what the link has to deliver.
- A link with an unstated medium is not a small gap. It is a link nobody
  has sized, nobody has licensed and nobody has booked ground assets for,
  and it surfaces at commissioning rather than at design review.
- Capability is three numbers, not one. The information rate the medium
  sustains, the range it closes, and the availability it achieves once
  propagation is accounted for. A medium can be generous on two and
  disqualifying on the third, which is exactly the optical case.
- Three outcomes matter. The medium carries the link with headroom; it
  carries the link with none worth the name; or it cannot carry it. The
  middle case passes a does-it-fit check and is the one a growth in data
  volume turns into a redesign.
- Availability is not a rate derating. A medium that delivers ten times
  the rate for seventy percent of the year has not met a link that asked
  for ninety-eight, and averaging the two hides that.
- Interoperability is a separate question from capability. A medium that
  closes the link but sits outside the agreed set costs a ground station
  nobody has, and it is worth reporting even when every number passes.

## Workflow

1. Declare the media catalogue: each medium with the rate it sustains,
   the range it closes, the availability it achieves, and whether it is
   inside the agreed interoperable set.
2. Declare each link with the medium it names and what it requires. A
   link with no stated availability is asserting it does not care, so
   make that explicit as zero rather than leaving it absent.
3. Reject a duplicate medium name and a duplicate link name. Two entries
   under one name are two teams describing different things.
4. Check the first obligation before the second. A link naming a medium
   outside the catalogue has no envelope to be measured against, and
   reporting it as under-capable misnames the defect.
5. Compute each criterion as a utilisation of the medium's envelope, and
   take the worst of them as the headroom figure for the link.
6. Compare against the bound with a relative tolerance. A link sized
   exactly to a medium's envelope must come out the same way on every
   platform, not fit on one and fail on another.
7. Where the medium is still open, rank the catalogue by headroom rather
   than picking the first that passes — the ranking is what makes the
   cost of the marginal choice visible.

## Pitfalls

- Treating the medium as settled because a band was named in a proposal.
  The band is not the medium plus its envelope, and the envelope is what
  the link is measured against.
- Sizing on rate alone. Range and availability disqualify media that win
  every throughput comparison, and optical loses on both while winning
  on rate by an order of magnitude.
- Averaging availability into the rate to get a single effective number.
  It produces a medium that looks adequate and is unavailable exactly
  when the pass matters.
- Accepting a medium that only just fits. Data volumes grow, degradation
  accumulates and operations concepts change; a link at full utilisation
  on day one has spent its margin before launch.
- Deciding the envelope comparison with a bare strict inequality. Two
  arithmetically identical utilisations can straddle one on different
  platforms, so the verdict changes with the machine.
- Reporting an unlisted medium as under-capable. It is a different
  finding with a different owner, and merging the two loses the one that
  needed an agreement rather than a redesign.

## Behavior contract (gate 3)

Envelope and fraction validation, medium and link normalisation, the
per-criterion utilisations, the availability shortfall, the three-way
verdict with a tolerance at the envelope bound, the headroom ranking of
candidate media, and the plan-level separation of undeclared,
non-interoperable, unsuitable and marginal links are exercised by the
gate 3 contract test: scripts/test_e50_space_link_media.py against
scripts/e50_space_link_media_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_space_link_media.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
