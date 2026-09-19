---
name: q2007-security
description: "Audit test-centre site security and access control under ECSS-Q-ST-20-07C clause 5.5.4. Use when a centre has to show who may enter which zone, who was inside it, and where the hardware and its data were left: decide each access request against zone tier, badge validity and authorised hours, treat the escort as the admitting party for a visitor, list every reason a request fails instead of the first, find visits signed in and never signed out, reconstruct zone occupancy, and flag items or data held below their sensitivity tier. Trigger: ecss, q-st-20-07-test-centre, q2007-security, test-centre-zone-access-tier, visitor-escort-admission-authority, test-centre-visit-signout-gap, test-item-storage-sensitivity-tier."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-security, test-centre-zone-access-tier, visitor-escort-admission-authority, test-centre-visit-signout-gap, test-item-storage-sensitivity-tier, test-centre-zone-occupancy-reconstruction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Site Security and Access Control (space-systems/ecss/q2007-security)

Use when the task is the security step of ECSS-Q-ST-20-07C clause 5.5.4 --
controlling who reaches each part of a test centre, keeping an account of
visitors, and protecting the test items and the data they generate while
they sit on site.

## Domain quick reference

- Three different things are being protected and they fail in three
  different ways: the facility (who gets in), the visit (who is inside
  right now), and the holdings (where the article and its data are left).
  A centre with excellent doors and no sign-out discipline fails the second
  one entirely.
- Zones carry a protection tier, from the site perimeter up to the
  enclosure the flight article sits in. A request is decided on four
  independent facts: badge validity on the day, the hours the zone is open,
  the tier required, and the escort where one is needed.
- The escort rule is the one that is usually implemented wrong. Escorting
  exists precisely so that an unauthorised person can enter under someone
  else's authority, so for an escorted visitor it is the escort's tier that
  is graded against the zone, not the visitor's. Grading the visitor's own
  tier as well makes every escorted visit a denial and the rule then gets
  switched off entirely.
- An unescorted visitor is refused for the missing escort alone. Adding a
  second "tier too low" reason is noise: the escort was going to supply the
  tier, and one fix closes both.
- Report every failing reason, not the first one hit. A request that fails
  on three counts needs three fixes, and a first-reason-only denial sends
  the badge holder back to the desk three times.
- An open visit -- signed in, never signed out -- is not a paperwork nit.
  It means the centre cannot say who is inside a zone during an evacuation,
  and cannot say whose hands were near the article in the window a defect
  appeared in.
- Occupancy is reconstructed from the log at a stated minute, so an
  evacuation list and a defect window use the same reconstruction rather
  than two different informal readings of the same sheet.
- A test item and its data both carry a sensitivity tier and both are held
  somewhere. The protection an item actually receives is the tier of the
  place it was left in, not the tier of the place the plan assigned it, so
  the holding location is what gets graded.
- The evaluation day and the time of day are inputs, never the clock. A
  security report that changes because it was re-run an hour later cannot
  be attached to an incident record.

## Workflow

1. Declare the zones: identifier, protection tier, and the minutes of the
   day the zone is open. Refuse a zone that closes before it opens or whose
   tier sits outside the scale.
2. Declare the people: authorisation tier, whether they are a visitor, and
   the day their badge lapses. A person with no badge record is treated as
   badgeless, not as trusted.
3. Decide each access request at an explicit day and minute. Collect every
   reason for refusal. Record which party admitted the request, so a later
   review can see whose authority was used.
4. Walk the visit log for entries with no sign-out, and reject a log whose
   entries sign out before they sign in or repeat an identifier.
5. Reconstruct occupancy per zone at the minute under review.
6. Compare each held item and each data record against the tier of the zone
   holding it, and flag a holding pointing at a zone nobody declared.
7. Roll the site up: the denied requests, the open visits, the holding
   findings. The site is secure only when all three are empty.

## Pitfalls

- Grading an escorted visitor on their own tier, which denies every
  escorted visit and gets the escort rule quietly bypassed instead.
- Returning the first denial reason. Three defects then take three trips to
  the badge desk to discover.
- Treating a missing sign-out as an administrative tidy-up. It is the
  evacuation list and the defect-window list that are missing.
- Grading an item against the zone it was assigned to rather than the zone
  it is in. The assignment is an intention; the location is the protection.
- Letting a holding point at a zone that was never declared, so it silently
  drops out of the assessment instead of being flagged.
- Reading the clock inside the assessment, so the same log yields two
  different occupancy lists an hour apart.
- Assuming a person with no badge record is staff. An absent record is an
  absent authorisation.

## Behavior contract (gate 3)

The zone, person, visit and holding validation, the four-fact access
decision with the escort-as-admitting-party rule, full reason collection,
open-visit detection, occupancy reconstruction and holding-tier findings are
exercised by the gate 3 contract test: scripts/test_q2007_security.py
against scripts/q2007_security_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_security.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
