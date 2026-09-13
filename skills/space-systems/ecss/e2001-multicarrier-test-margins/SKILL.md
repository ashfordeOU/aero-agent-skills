---
name: e2001-multicarrier-test-margins
description: "Use when derive the multicarrier multipactor test-margins of ECSS-E-ST-20-01C clause 4.7.3.1 for a radio-frequency article: categorize the item against the recognized equipment-type and component-type list, resolve its design-heritage level and the model-philosophy of the article on the bench, credit the sample-count relief earned by testing more than one unit, build the multicarrier peak-envelope-power of the carrier set, raise it by the resolved test-margin to the level the campaign must actually reach, and verify the facility holds that power-headroom before the run is scheduled. Trigger: ecss, e-st-20-electrical-scope, multicarrier-test-margin, multipactor-test-level, peak-envelope-power, design-heritage-margin, component-type-categorisation, model-philosophy-selection, facility-power-headroom."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multicarrier-test-margins, multicarrier-test-margin, multipactor-test-level, peak-envelope-power, design-heritage-margin, component-type-categorisation, model-philosophy-selection, facility-power-headroom]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Multicarrier Test Margins (space-systems/ecss/e2001-multicarrier-test-margins)

Use when the task is the multicarrier test margin of ECSS-E-ST-20-01C
clause 4.7.3.1 -- how far above its operating condition a multicarrier
multipactor test has to be driven, set from the equipment or component
type on the bench, the design heritage behind it, and the build
standard of the article actually being tested.

## Domain quick reference

- A multipactor test demonstrates the absence of a discharge at a level
  raised above the operating condition. The raise is the test margin,
  and it is smaller than the analysis margin of the same item: a test
  observes the real hardware, so it buys the same confidence with less
  elevation than a computed threshold does. Reusing the analysis number
  as the test number over-drives every campaign.
- The operating condition for a multicarrier article is the in-phase
  envelope peak of the carrier set, not the summed average. Carrier
  voltages add when they align, so the envelope power is the square of
  the sum of the carrier root-powers -- sixteen equal carriers peak at
  twenty-four decibel above one of them. The test level is that peak
  raised by the margin.
- The base margin follows the article type and the level the campaign
  sits at. An equipment-level article carrying the full transmit chain
  or an output multiplexer owes more than a component-level waveguide
  filter or coaxial connector, which owes more than a low-power receive
  chain; a dielectric-loaded component owes an extra increment because
  the dielectric surface adds a second discharge mechanism the metal
  parts do not have.
- Design heritage moves the margin the same way it moves the analysis
  margin: nothing extra for a recurring item already flown in a
  comparable configuration, an increment for a modified design, the
  largest increment for a wholly new one.
- The build standard of the tested article matters as much as its type.
  A dedicated qualification article earns no penalty. A protoflight
  article that has to fly afterwards earns a small one, because the
  campaign is necessarily shorter and gentler. An engineering article
  earns a larger one, because its build standard is not the flight
  standard. A breadboard earns the largest -- and cannot close the
  requirement at all, whatever level it survives.
- Testing more than one article earns a bounded relief, because a
  second and third sample start covering the manufacturing spread that
  a single unit cannot. The relief is capped, and no combination of
  relief may drive the margin below the project floor.
- The resolved level is only useful if the facility can deliver it. The
  campaign is planned against the facility ceiling, and an article
  whose required level sits above that ceiling is blocked before the
  run is scheduled, not discovered on the day.

## Workflow

1. Collect the carrier set for the article and build the peak envelope
   power by in-phase voltage addition. Refuse a set with fewer than two
   carriers: that is the single-carrier clause, not this one.
2. Categorize the article against the recognized equipment-type and
   component-type list. That fixes the base test margin and records
   whether the campaign sits at equipment or component level.
3. Resolve the design-heritage level and add its increment.
4. Resolve the model philosophy of the article on the bench and add its
   adder. Record a finding when the build standard cannot close the
   requirement however the run goes.
5. Credit the sample-count relief for the number of articles tested,
   capped at its bound, then clamp the result at the test-margin floor
   and note the clamp when it bites.
6. Raise the envelope peak by the resolved margin to obtain the level
   the campaign has to reach, and express it in both decibel-watt and
   watt so the facility booking is unambiguous.
7. Compare that level against the facility ceiling and report the
   headroom. A ceiling landing exactly on the requirement is
   sufficient -- the comparison absorbs representation error rather
   than moving the engineering limit.
8. Aggregate. The campaign is schedulable only when no article is
   blocked, and the highest required level across articles is the one
   the facility has to be booked for.

## Pitfalls

- Testing at the summed average power of the carriers. The article sees
  the in-phase envelope, so a multicarrier campaign run at the average
  is a single-carrier campaign with extra steps and passes gaps that
  would have discharged.
- Reusing the analysis margin as the test margin. The two exist to buy
  the same confidence from different evidence; swapping them either
  over-drives the article or, in the other direction, under-tests it.
- Treating an engineering article as a qualification article because it
  is electrically identical. The adder is about the build standard --
  surface finish, cleanliness and assembly torque are exactly what
  multipactor responds to.
- Accepting breadboard evidence because the level was reached. A
  breadboard can survive any level and still say nothing about the
  flight build; the finding stands regardless of the result.
- Stacking sample-count relief without its cap or its floor. Relief
  reflects coverage of the manufacturing spread, which saturates; an
  uncapped credit eventually removes the margin the clause exists to
  impose.
- Booking the facility against the operating power instead of the
  required level. The ceiling has to clear the envelope peak plus the
  margin, and the shortfall is usually discovered only once the article
  is already in the chamber.
- Reading a ceiling that lands a few units in the last place below the
  requirement as a real shortfall. When the required level is reached
  through summed root-powers and the ceiling was quoted through the
  envelope factor, the two differ by representation error alone.

## Behavior contract (gate 3)

The peak-envelope-power construction, article-type categorization,
design-heritage and model-philosophy resolution, sample-count relief
and floor clamp, required-level derivation in decibel-watt and watt,
facility-headroom comparison and campaign-level verdict are exercised
by the gate 3 contract test:
scripts/test_e2001_multicarrier_test_margins.py against
scripts/e2001_multicarrier_test_margins_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_multicarrier_test_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
