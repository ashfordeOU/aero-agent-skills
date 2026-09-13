---
name: e2007-harness-category-definition
description: "Use when define the wire-category scheme and the bundle-routing separation rules of a spacecraft harness under ECSS-E-ST-20-07C clause 4.2.13.1: assign each wire a category from its function family, promote a fast-switching line to the interfering category from its current-slew and voltage-slew rates, demote a low-amplitude high-source-impedance line to the sensitive category, require each bundle to carry one category only, derive the bundle-to-bundle route separation from the category pair, and apply the extra critical-line treatment of twisted-shielded-pair construction and a routing path distinct from its redundant partner. Trigger: ecss, e-st-20-07c, wire-category-scheme, harness-bundle-segregation, route-separation-matrix, critical-line-routing, twisted-shielded-pair, current-slew-rate, redundant-partner-routing."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-harness-category-definition, wire-category-scheme, harness-bundle-segregation, route-separation-matrix, critical-line-routing, twisted-shielded-pair]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Harness Category Definition (space-systems/ecss/e2007-harness-category-definition)

Use when the task is the wire-category and routing-segregation scheme
of ECSS-E-ST-20-07C clause 4.2.13.1 -- deciding which category each
wire belongs to, keeping a bundle uniform, spacing bundle routes by
the category pair they carry, and giving critical lines the extra
treatment the clause asks for.

## Domain quick reference

- Four categories carry the scheme. The sensitive category holds
  low-level analog sensor and detector-readout lines. The signal
  category holds digital-data-bus, discrete-command and
  telemetry-acquisition lines. The power category holds primary and
  secondary distribution and their returns. The interfering category
  holds pyrotechnic-firing, motor-drive, heater-switching and
  radiofrequency-feed lines. Every wire is categorized into exactly
  one of the four before any routing decision is taken.
- The function family is the starting point, not the verdict. Two
  measured quantities adjust it. A line whose current-slew rate or
  voltage-slew rate exceeds the switching limits is promoted to the
  interfering category whatever its family, because a fast edge makes
  it an aggressor. A signal-category line whose amplitude is at or
  below the sensitive threshold and whose source impedance is at or
  above the high-impedance threshold is demoted to the sensitive
  category, because a quiet high-impedance node is a victim. Promotion
  is checked first: an aggressor is never treated as a victim.
- A bundle is uniform by construction. Wires sharing one bundle sit at
  zero separation, so they must share one category; a bundle mixing
  categories is a finding no matter how the routes are laid out. A
  critical line sharing its bundle with a non-critical wire is a
  separate finding.
- Route separation comes from a category-pair matrix. Two bundles of
  the same category need none; signal against power is a modest gap;
  signal against interfering is wider; sensitive against interfering is
  the widest. The requirement for a bundle pair is the widest entry
  over every category pair the two bundles carry between them.
- Critical lines carry three extra obligations: twisted and shielded
  construction, a named redundant partner, and a routing path for that
  partner that is not the path the line itself uses. Redundancy routed
  along one path is not redundancy.

## Workflow

1. Validate each wire record: identifier, function family, criticality
   flag, amplitude, peak current, rise time, source impedance,
   construction, redundant-partner identifier. Reject an unknown
   function family or a non-positive rise time.
2. Categorize each wire: read its base category from the function
   family, compute its current-slew and voltage-slew rates, promote to
   the interfering category on either limit, otherwise apply the
   sensitive demotion test.
3. Check each bundle: one category across its wires, and no mixing of
   critical with non-critical lines. Reject a bundle naming an unknown
   wire, an empty bundle, or a wire that appears in two bundles.
4. For every pair of bundles, take the widest separation the category
   pairs demand. Two bundles on one route satisfy it only when that
   requirement is zero; otherwise read the declared route separation,
   summing the measured offset segments when they are given.
5. Compare declared against required. Treat a separation short only by
   the offset-summation representation error as satisfied -- the named
   tolerance is far below harness measurement resolution and the
   engineering limit is never widened.
6. For every critical line, confirm the construction, the named
   redundant partner, and that the partner is routed elsewhere. The
   harness definition is compliant only when the wire, bundle and route
   finding lists are all empty.

## Pitfalls

- Categorizing from the function name alone and never computing the
  slew rates -- a secondary-power feed switched in a microsecond is an
  aggressor, and leaving it in the power category understates every
  separation it drives.
- Applying the sensitive demotion to a line that already tripped a
  switching limit. The two tests are ordered, not alternatives, and
  reversing them turns an aggressor into a victim on paper.
- Reading a wide route separation as compliance while the bundle
  itself mixes categories -- bundle uniformity is checked separately,
  and inside a bundle the separation is zero by definition.
- Taking the requirement for a bundle pair from one category each
  instead of the widest pairing. A bundle carrying two categories
  drives the wider of the two requirements against every neighbour.
- Declaring redundant critical lines and then routing both along one
  path, or leaving the partner unrouted. The partner's route is part
  of the check, not a bookkeeping detail.

## Behavior contract (gate 3)

The wire-categorization, slew-rate promotion, sensitive demotion,
bundle-uniformity, separation-matrix, declared-separation and
critical-line-treatment logic is exercised by the gate 3 contract
test: scripts/test_e2007_harness_category_definition.py against
scripts/e2007_harness_category_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_harness_category_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
