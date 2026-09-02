---
name: operating-cost
description: "Use when you must estimate the direct operating cost of the aircraft: compute the block fuel cost from the fuel price, the crew cost from the crew complement, the maintenance cost from the man-hours per flight hour, the insurance cost from the annual rate and utilization, and roll the elements into the cost per flight and the cost per flight hour. Produces the DOC breakdown and the per flight hour cost that gate the operating economics assessment. Trigger: direct operating cost, block fuel cost, crew cost, maintenance cost, flight hour cost."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: cost-estimation
  tags: [operating-cost, direct-operating-cost, block-fuel-cost, crew-cost, maintenance-cost, insurance-rate, flight-hour-cost, cost-per-flight, utilization]
  version: 0.1.0
  author: Aero Agent Skills
---

# Operating Cost Estimation (vehicle-design/cost-estimation/operating-cost)

Use when the task is estimating the direct operating cost (DOC) of the
aircraft: the block fuel cost, the crew cost, the maintenance cost,
the insurance cost, and the landing and navigation fees, rolled into
the cost per flight and the cost per flight hour.

## Domain quick reference

- Direct operating cost per flight hour decomposes into fuel, crew,
  maintenance (labor plus material), insurance, and landing and
  navigation fees; this is common airline operating economics
  practice.
- Fuel cost per flight: block fuel in kg times the fuel price per kg.
- Crew cost per flight: flight hours times the crew size times the
  cost per crew hour.
- Maintenance cost per flight: flight hours times the man-hours per
  flight hour times the labor rate times (1 + material factor), where
  the material factor is the ratio of material cost to labor cost.
- Insurance cost per flight: aircraft price times the annual insurance
  rate times the fraction of the year the aircraft flies, that is,
  flight hours divided by the utilization hours per year.
- Landing and navigation fees per flight are added as fixed costs.
- DOC per flight is the sum of the five elements; DOC per flight hour
  divides that sum by the flight hours.
- DOC estimation sits in the FAR-25 / CS-25 transport context where
  the certified aircraft mass and fuel planning feed the operating
  economics assessment.

## Workflow

1. Collect the block fuel, fuel price, flight hours, crew size, crew
   cost per hour, man-hours per flight hour, labor rate, material
   factor, aircraft price, annual insurance rate, utilization, and the
   landing and navigation fees.
2. Compute the fuel cost with fuel_cost_per_flight.
3. Compute the crew cost with crew_cost_per_flight.
4. Compute the maintenance cost with maintenance_cost_per_flight.
5. Compute the insurance cost with insurance_cost_per_flight.
6. Sum the fees with landing_fees_per_flight, then roll up the five
   elements with doc_per_flight and divide by the flight hours with
   doc_per_flight_hour.

## Pitfalls

- Forgetting the material factor: maintenance material cost is
  typically a sizeable fraction of the labor cost, not zero.
- Scaling insurance by the wrong utilization: the annual rate covers a
  year of flying, so a low-utilization aircraft pays more insurance
  per flight hour.
- Mixing block hours and flight hours in the same element; keep one
  hours basis per calculation.
- Double counting the fees: they are per flight, not per hour, so
  divide by the flight hours before quoting a per hour figure.
- Passing negative rates or a zero utilization; the module raises
  ValueError instead of guessing.

## Behavior contract (gate 3)

The fuel, crew, maintenance, insurance, fee, and rollup logic are
exercised by the gate 3 contract test: scripts/test_operating_cost.py
against scripts/operating_cost_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_operating_cost.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the DOC element
  equations are common operating economics methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
