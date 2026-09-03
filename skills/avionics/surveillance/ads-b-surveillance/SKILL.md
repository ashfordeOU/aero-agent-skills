---
name: ads-b-surveillance
description: "Use when you must assess an ADS-B Out installation and ADS-B In reception geometry against the DO-260B-style performance categories: map the navigation integrity category (NIC) to its containment radius, map the navigation accuracy category for position (NACp) to its 95-percent accuracy bound, map the source integrity level (SIL) to its per-flight-hour probability bound, select the NIC and NACp category whose bound covers a required containment or accuracy value, and compute the 1090 MHz extended squitter radio line-of-sight range between two altitudes. Produces the containment radius, accuracy bound, integrity probability, chosen categories, and coverage range that gate an ADS-B surveillance assessment. Trigger: ads-b-out, ads-b-in, extended-squitter, nic, nacp, sil, containment-radius, ads-b-range."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-260b
    reference-only: true
gated: false
domain: avionics
pack: surveillance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: surveillance
  tags: [ads-b-surveillance, extended-squitter, containment-radius, nacp-accuracy, sil-integrity, ads-b-range]
  version: 0.1.0
  author: Aero Agent Skills
---

# ADS-B Surveillance (avionics/surveillance/ads-b-surveillance)

Use when the task is assessing an ADS-B Out installation and an ADS-B
In reception geometry against the DO-260B-style performance
categories: the containment radius guaranteed by a navigation
integrity category (NIC), the 95-percent horizontal accuracy bound of
a navigation accuracy category for position (NACp), the per-flight-hour
integrity probability of a source integrity level (SIL), the NIC and
NACp whose bounds cover a required containment or accuracy value, and
the 1090 MHz extended squitter radio line-of-sight range between two
altitudes. This leaf is the second of the avionics/surveillance pack;
avionics/surveillance/tcas-resolution-advisory owns the TCAS sense
logic on measured state, while this leaf sizes the surveillance
performance claims that gate an equipage assessment. The category
bounds are paraphrased DO-260B summary values held as module constants
in the logic file, never a reproduction of the MOPS tables. Pure
Python stdlib, deterministic and offline. Units: containment radius
and accuracy in metres, altitude in feet, range in kilometres,
integrity as a probability per flight hour.

## Domain quick reference

- NIC containment radius: each navigation integrity category 1 to 11
  maps to the containment radius the position source guarantees, from
  7.5 m at NIC 11 down to 37040 m at NIC 1; NIC 0 means unknown and
  maps to None. NIC 8, for example, bounds containment to 185.2 m (one
  tenth of a nautical mile). Exact per-category values live in the
  NIC_RADIUS_M module constant in ads_b_surveillance_logic.py.
- NACp accuracy: each navigation accuracy category for position 1 to
  11 maps to the 95-percent horizontal accuracy bound, from 3 m at
  NACp 11 down to 18520 m at NACp 1; NACp 0 is unknown. NACp 9 bounds
  the 95-percent position error to 30 m. Values live in NACp_95_M.
- SIL integrity: each source integrity level 1 to 3 maps to the
  maximum probability of an undetected failure per flight hour, 1e-7
  at SIL 3, 1e-5 at SIL 2 and 1e-3 at SIL 1; SIL 0 is unknown. Values
  live in SIL_PROB.
- Category selection: nic_for_radius(required_radius_m) and
  nacp_for_accuracy(required_95_m) walk the categories from the
  tightest bound (highest number) down to category 1 and return the
  first whose bound is >= the required value, the least-integrity
  category that still bounds the requirement. A returned 0 means no
  category covers the requirement, not even category 1.
- Radio line-of-sight range: d = RANGE_COEFF * (sqrt(h_own * FT_TO_M) +
  sqrt(h_other * FT_TO_M)) with RANGE_COEFF = 4.12 km per sqrt(metre)
  and FT_TO_M = 0.3048, the standard-atmosphere 4/3-earth radio
  horizon used for 1090 MHz extended squitter coverage.
- Assessment bundle: adsb_assessment(nic, nacp, sil, alt_ft_own,
  alt_ft_other) returns {containment_radius_m, accuracy_95_m,
  integrity_prob, range_km} in one call.

## Workflow

1. Fix the assessment state: the candidate NIC, NACp and SIL from the
   position source and the own and other altitudes in feet.
2. Map the categories to bounds with nic_containment_radius(nic),
   nacp_accuracy(nacp) and sil_probability(sil); category 0 returns
   None, meaning the value is unknown.
3. For a required containment radius or 95-percent accuracy, select
   the covering category with nic_for_radius(required_radius_m) or
   nacp_for_accuracy(required_95_m); a returned 0 flags that no
   category bound covers the requirement.
4. Compute the reception coverage with
   adsb_range_km(alt_ft_own, alt_ft_other), passing 0 ft for the
   altitude of a ground ADS-B receiver.
5. Bundle the whole case with adsb_assessment(nic, nacp, sil,
   alt_ft_own, alt_ft_other) and read containment_radius_m,
   accuracy_95_m, integrity_prob and range_km.
6. Confirm the deterministic checks with the contract test
   scripts/test_ads_b_surveillance.py.

## Worked example

Own ship at 10 000 ft receiving an ADS-B In target at 30 000 ft, with
the source reporting NIC 8, NACp 9, SIL 2.

- nic_containment_radius(8) = 185.2 m: the position source guarantees
  containment within 185.2 m.
- nacp_accuracy(9) = 30.0 m: the 95-percent horizontal position error
  stays within 30 m.
- sil_probability(2) = 1e-5: at most one undetected failure per
  100 000 flight hours.
- nic_for_radius(100.0) = 8: NIC 9 bounds only 75 m, too small for the
  100 m required containment radius; NIC 8 bounds 185.2 m and covers
  it, so NIC 8 is the chosen category.
- nacp_for_accuracy(50.0) = 8: NACp 9 bounds only 30 m, too small for
  the 50 m required accuracy; NACp 8 bounds 92.6 m and covers it.
- adsb_range_km(10000, 30000) = 621.4 km: sqrt(3048) = 55.21,
  sqrt(9144) = 95.62, sum 150.83 times 4.12 gives 621.4 km, inside the
  600 to 650 km band for the altitude pair.
- adsb_assessment(8, 9, 2, 10000, 30000) returns {containment_radius_m:
  185.2, accuracy_95_m: 30.0, integrity_prob: 1e-5, range_km: 621.4}.

## Verification

- nic_containment_radius(8) is 185.2 m and nacp_accuracy(9) is 30.0 m,
  exactly the table entries (equal within 1e-9 relative).
- nic_for_radius(7.5) is 11 and nic_for_radius(1e6) is 0, the
  exact-bound and no-coverage ends of the selection rule;
  nacp_for_accuracy(50.0) is 8.
- adsb_range_km(0, 0) is 0.0 and the 10 000/30 000 ft case sits inside
  the 600 to 650 km bound; SIL 3 gives the stricter probability (1e-7
  below the 1e-5 of SIL 2).
- Every out-of-range category (NIC or NACp outside 0 to 11, SIL
  outside 0 to 3), every negative altitude and every non-positive
  required radius or accuracy raises ValueError.
- Run the contract test offline: python3
  scripts/test_ads_b_surveillance.py (34 tests, deterministic).

## Related leaves

- avionics/surveillance/tcas-resolution-advisory: the sibling leaf in
  the surveillance pack; it owns the TCAS II sense logic on measured
  range and altitude state, this leaf owns the surveillance
  performance categories.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the position
  solution whose accuracy and integrity feed the NACp and NIC claims.
- gnc-autonomy/navigation/gnss-raim-fde: fault detection that backs a
  source integrity level claim.
- avionics/flight-management/radio-navigation-aids: navaid sensing
  context for the airborne navigation suite.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ads_b_surveillance.py

The test covers the exact table anchors (NIC 8 at 185.2 m, NACp 9 at
30.0 m, SIL 2 at 1e-5), table spot checks with unknown-category None
returns, the selection rule for required containment radii and
accuracies including the exact-bound and no-coverage cases, the
10 000/30 000 ft range worked example (621.4 km inside the 600 to
650 km bound), the zero-altitude range, the assessment bundle,
ValueError rejection of out-of-range categories, negative altitudes
and non-positive requirements, and determinism of the repeated calls.

## Compliance

- Standards referenced, not reproduced: rtca-do-260b (DO-260B) is a
  gated RTCA standard; the category bounds above are paraphrased
  summary values used in equipage assessments, stated as module data,
  never as reproduced MOPS tables.
- compliance: STANDARDS-REF, gated: false.
