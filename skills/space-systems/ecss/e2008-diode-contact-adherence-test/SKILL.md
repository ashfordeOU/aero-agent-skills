---
name: e2008-diode-contact-adherence-test
description: "Assess whether the contacts of an external protection diode still hold after the contact adherence test of ECSS-E-ST-20-08C clause 9.6.10, and whether an integral unit with no terminal to grip was covered by a declared equivalent route rather than quietly skipped: validate the adherence policy, read every required contact site, turn each recorded force into a stress over the bonded area it acted on, sentence each device by its weakest site rather than its mean, refuse a lot presented with sites unpulled, and hold an integral unit to an admissible substitute reaching the same sites. Use when a protection diode contact adherence run is planned or its records are reviewed. Trigger: ecss, e-st-20-08c-clause-9-6-10, protection-diode-contact-adherence-test, external-protection-diode-contact-durability, integral-diode-equivalent-adherence-route, protection-diode-contact-adherence-stress, protection-diode-weakest-contact-site, protection-diode-adherence-site-coverage."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-contact-adherence-test, protection-diode-contact-adherence-test, external-protection-diode-contact-durability, integral-diode-equivalent-adherence-route, protection-diode-contact-adherence-stress, protection-diode-weakest-contact-site, protection-diode-adherence-site-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Contact Adherence Test (space-systems/ecss/e2008-diode-contact-adherence-test)

Use when the task is the contact adherence test of ECSS-E-ST-20-08C clause
9.6.10 -- showing that the contacts of an external protection diode are
durable, and deciding what an integral unit, which has no free terminal to
pull, is allowed to offer in place of that pull. The clause is short and the
two configurations are easy to conflate; the failure it guards against is a
lot sentenced on a route that never reached the contacts at all.

## Domain quick reference

- The result is a stress, not a force. Two contacts laid down by the same
  process over different bonded areas let go at different forces, and only the
  force divided by the area it acted on compares across package styles or
  across a drawing change.
- The device is sentenced by its weakest site. A mean over the anode and the
  cathode hides the one that released, and the array only ever sees the one
  that released.
- Every required site has to be present in the record. A device pulled at one
  terminal and quietly not at the other is not a passed device; it is a
  half-tested device, and the difference does not show in the numbers that were
  taken.
- An integral diode is a different route, not a lighter one. With no terminal
  to grip, durability is shown by an assembly-level pull, a witness coupon
  carrying the same contact process, or a destructive physical analysis -- and
  the route is only equivalent if it reaches the sites the direct pull would
  have reached.
- "Equivalent" is a claim that has to carry evidence. An undeclared route, a
  route that names no sites, or a route outside the admissible set leaves the
  contacts unassessed rather than assessed another way, and that is the finding
  to report.
- The minimum stress is a project value. It comes from the drawing or the
  procurement specification, and hard-coding a number from a neighbouring
  programme is how an acceptable lot gets scrapped or a marginal one gets
  shipped.

## Workflow

1. Validate the adherence policy first: minimum stress, the required site
   list, the admissible equivalent routes and the coverage share a substitute
   must reach. A repeated site name or a coverage share above one is refused
   rather than used.
2. Read the declared configuration and reduce it to external or integral. A
   record that does not say which closes immediately, because the two take
   different routes through the clause.
3. For an integral unit, read the declared equivalent route and the sites it
   covers. Report an undeclared route, a route naming no sites, an
   inadmissible method and insufficient coverage together, so the
   qualification argument is repaired once rather than in three passes.
4. For an external lot, read each device, rejecting a duplicate device
   identifier and a site repeated within one device.
5. For each site, turn the recorded adherence force into a stress over its
   bonded area, and keep both the force and the area in the record so the
   stress can be audited or recomputed under a revised drawing area.
6. Sentence each device by its weakest site and carry that site's name, not
   just its number, into the device record.
7. Close on one verdict: configuration not stated, equivalent route not
   demonstrated, required contact sites missing, diode contacts not durable,
   diode contacts durable, or the integral equivalent route accepted.

## Pitfalls

- Reporting the adherence force as the result. It is a property of the bonded
  area as much as of the bond, so two package styles will disagree for reasons
  that have nothing to do with process quality.
- Averaging the sites on a device. The mean of a strong anode and a weak
  cathode looks like a healthy device and is not one.
- Treating an integral unit as exempt. The clause offers a different route, not
  an exemption, and a lot recorded as "integral, not applicable" has no
  durability evidence behind it.
- Accepting the word "equivalent" without the coverage behind it. A witness
  coupon that carries only the anode process is half a demonstration however
  carefully it was pulled.
- Discarding the bonded area once the stress is computed. A drawing revision
  that changes the contact footprint cannot then be applied to the historical
  record, and the lot has to be pulled again.
- Sentencing a lot from the devices that happened to have both sites pulled.
  The unpulled site is the finding; dropping the device from the population
  makes the finding disappear.

## Behavior contract (gate 3)

The policy validation, the configuration reduction, the stress conversion, the
minimum-stress comparison, the site coverage and missing-site report, the
weakest-site sentencing, the equivalent-route admissibility and coverage
checks, and the assessment verdict are exercised by the gate 3 contract test:
scripts/test_e2008_diode_contact_adherence_test.py against
scripts/e2008_diode_contact_adherence_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_adherence_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
