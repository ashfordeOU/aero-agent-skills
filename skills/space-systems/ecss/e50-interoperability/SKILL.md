---
name: e50-interoperability
description: "Evaluate whether a space link can actually work with the external assets its mission claims cross-support from, per ECSS-E-ST-50C Rev.2 clause 5.6.4. Use when an interoperability requirement has to be stated and then shown: compare the link profile against each partner on frequency band, modulation, channel coding and frame format, separate a partner that shares no option from one that simply never declared an attribute, pick a deterministic operating option where both sides overlap, and name the options the link would have to add to recover a partner it cannot reach today. Trigger: ecss, e-st-50c-clause-5-6-4, space-link-interoperability, ground-station-cross-support, link-profile-compatibility, cross-support-option-negotiation, undeclared-partner-attribute."
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
  tags: [ecss, e-st-50-communications-scope, e50-interoperability, e-st-50c-clause-5-6-4, space-link-interoperability, ground-station-cross-support, link-profile-compatibility, cross-support-option-negotiation, undeclared-partner-attribute]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Space Link Interoperability (space-systems/ecss/e50-interoperability)

Use when the task is the interoperability statement of ECSS-E-ST-50C Rev.2
clause 5.6.4 — naming the external assets a space link has to work with, and
showing on what terms it can, rather than asserting that it does.

## Domain quick reference

- Interoperability is a requirement before it is a property. The clause asks
  the mission to say who it must work with; a link that happens to be
  compatible with a station nobody named has satisfied nothing, and a link
  with no named partner has an unstated requirement, which is the defect.
- Compatibility is per attribute and it is set intersection. Frequency band,
  modulation, channel coding and frame format each have a set of options a
  side can operate, and the two sides work together on an attribute only
  where those sets overlap.
- One clashing attribute is enough. A partner that matches on three of four
  is not three quarters supported; it is unsupported, and the whole value of
  the assessment is naming which attribute did it.
- Undeclared is a third outcome, not a failure. A partner that never stated
  its frame format may well be compatible, and reporting that as
  incompatible sends a team to redesign a link when the fix was an email.
- The operating option has to be picked deterministically. Where two bands
  overlap, the pair must agree the same one every time the assessment is
  run, or two documents describe two different links.
- The remedy belongs on the mission side. The partner is a fact of the
  ground segment; what can change is the option list the link supports, so
  the report names the options to add rather than the options to demand.
- Required and optional partners are graded differently. An optional asset
  that cannot be reached is worth reporting and does not fail the link; a
  required one does, and the two must not be summed into one fraction.

## Workflow

1. State the link profile and each partner profile as attribute to option
   set. Refuse a profile that omits a required attribute rather than reading
   the gap as unconstrained.
2. Name the partners the mission requires. An empty required set is refused:
   the missing requirement is the finding, not an empty result.
3. Intersect the two profiles attribute by attribute, over the attributes
   both sides declare.
4. Grade each partner into supported, unsupported with the clashing
   attributes named, or unconfirmed with the undeclared attributes named.
5. For a supported partner, derive the operating option per attribute by a
   fixed rule so the agreement is reproducible.
6. For an unsupported partner, report the options the link would have to add
   per clashing attribute, and check that adding them does restore support
   before reporting them.
7. Close on the required set alone — supported, partial or unsupported —
   while still reporting every optional partner that cannot be reached.

## Pitfalls

- Reading an undeclared attribute as a wildcard. A side that declared no
  modulation has declared no profile, and the assumption invents an
  agreement neither party made.
- Scoring a partner by how many attributes matched. Links do not partially
  connect; a single clashing band makes the pass useless however well the
  rest lines up.
- Collapsing unconfirmed into unsupported. The remedies differ by orders of
  magnitude — one is a question to the partner, the other is a change to
  the spacecraft.
- Picking the operating option by iteration order. Set iteration is not
  ordered, so the same pair can be documented with two different bands in
  two runs of the same assessment.
- Reporting an incompatibility with no remedy. The mission side is the side
  that can change, and a finding that does not say what to add leaves the
  decision to whoever reads it last.
- Averaging required and optional partners into one coverage number. A link
  that reaches three optional stations and misses its prime station reads
  as mostly fine and is not.

## Behavior contract (gate 3)

Profile and catalogue validation including the required attributes, the per
attribute intersection, the three way partner verdict, the deterministic
operating option, the remedy options checked to restore support, the cross
support fraction and the required only disposition are exercised by the gate
3 contract test: scripts/test_e50_interoperability.py against
scripts/e50_interoperability_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_interoperability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
