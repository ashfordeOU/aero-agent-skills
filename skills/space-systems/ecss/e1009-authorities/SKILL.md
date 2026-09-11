---
name: e1009-authorities
description: "Use when identify the appropriate international standards authority for
  a space mission's time scale, reference frame, ephemeris, geodesy, or data-format
  requirement; map each required data product to its originating body (IERS, IAU,
  USNO, BIPM, IMCCE/JPL, CCSDS, NIMA, WGCCRE); verify that citations are correctly
  attributed to the producing authority; and audit a product list for coverage gaps
  against the Annex C authority registry. Trigger: ecss, e-st-10-system-scope,
  authorities, reference-frames, time-scales, ephemerides, geodesy, iers, iau,
  bipm, ccsds."
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
  tags: [ecss, e-st-10-system-scope, authorities, reference-frames, time-scales, ephemerides, geodesy, iers, iau, bipm, ccsds]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Standards Authorities (space-systems/ecss/e1009-authorities)

Use when the task is to identify which international body or service is the
authoritative source for a specific data product needed by a space mission —
such as Earth orientation parameters, time scales, planetary ephemerides,
geodetic reference ellipsoids, or space data format standards — and to confirm
that every product cited in a mission's reference-frame or time-budget document
is attributed to the correct originating authority per ECSS-E-ST-10C Annex C.

## Domain quick reference

The eight recognised authorities and their primary products:

- **IERS** (International Earth Rotation and Reference Systems Service) —
  International Terrestrial Reference System (ITRS), International Celestial
  Reference System (ICRS) realisation, Earth Orientation Parameters (EOP),
  leap-second bulletins, UT1–UTC difference. Primary source for all Earth
  orientation and polar-motion data.
- **IAU** (International Astronomical Union) — defines the ICRS, the set of
  adopted astronomical constants, time-scale definitions (TDB, TCB, TCG), and
  delegates planetary-orientation standards to the WGCCRE.
- **USNO** (United States Naval Observatory) — co-maintains the IERS rapid
  EOP files (IERS Bulletin A), operates one of the two primary UTC master
  clocks, and publishes the Astronomical Almanac jointly with HMNAO.
- **BIPM** (Bureau International des Poids et Mesures) — defines and maintains
  International Atomic Time (TAI), coordinates the dissemination of UTC,
  and is the custodian of the SI unit definitions underpinning all physical
  constants used in astrodynamics.
- **IMCCE** (Institut de Mécanique Céleste et de Calcul des Éphémérides) —
  produces the INPOP planetary and lunar ephemeris series; used as an
  alternative or cross-check to JPL ephemerides for European missions.
- **JPL** (Jet Propulsion Laboratory, NASA) — produces the DE planetary
  ephemeris series (DE440, DE441, etc.) and the SPICE toolkit; the most
  widely adopted source for interplanetary trajectory and body-state data.
- **CCSDS** (Consultative Committee for Space Data Systems) — defines
  space-mission time-code formats (CCSDS 301.0-B), orbit and attitude data
  message standards (OEM, AEM, APM, ADM), and cross-support service
  protocols. Mandatory reference for any mission exchanging orbit products
  with a multi-agency ground network.
- **NIMA** (National Imagery and Mapping Agency, now NGA) — defined the
  WGS-84 geodetic reference ellipsoid and its associated EGM96 (and later
  EGM2008) global gravity model; the baseline terrestrial coordinate frame
  for GPS-referenced missions.
- **WGCCRE** (IAU Working Group for Cartographic Coordinates and Rotational
  Elements) — publishes the rotation poles, prime meridians, and body radii
  for solar system bodies; the mandatory reference for any mission addressing
  the surface of a non-Earth body.

## Workflow

1. Enumerate every external data product the mission requires: time scales
   (TAI, UTC, UT1, TDB …), reference frames (ITRS realisation, ICRS, body-fixed),
   ephemerides (planetary states, satellite orbits), geodetic parameters
   (ellipsoid, geoid), and data-exchange formats (time codes, orbit messages).
   One product per row in the authority traceability table.
2. For each product, consult the authority registry to identify the originating
   body. If more than one authority covers a product (e.g. UTC is maintained by
   BIPM and operationally disseminated by USNO and IERS), record the primary
   authority first; note secondary sources in the "remarks" column.
3. Verify each citation: confirm the authority name, the specific data series
   or bulletin, and the edition or version used (e.g. "IERS Conventions 2010",
   "JPL DE440", "CCSDS 301.0-B-4"). A citation naming an authority that does
   not produce that product is a traceability error — flag it for correction.
4. Audit for coverage gaps: every product in the requirements set must resolve
   to at least one authority. A product with no matching authority indicates
   either a novel or non-standard data source that requires project-level
   justification, or a product description that does not match any known
   canonical name and needs normalisation.
5. Record findings in the authority traceability table:
   - COVERED — product resolves to one or more authorities.
   - GAP — no authority covers the product as stated; action required.
   - CITATION-ERROR — the cited authority does not produce the product; action required.
6. The table is complete when every required product has a COVERED status and
   all citation errors are resolved.

## Pitfalls

- Confusing BIPM and IERS for UTC custody: BIPM defines and computes TAI and
  UTC; IERS issues the bulletin announcing leap seconds and publishes EOP.
  Citing IERS as the authority for the SI second or TAI is a citation error.
- Using JPL ephemeris identifiers without specifying the DE version: DE405,
  DE430, DE440, and DE441 differ in accuracy and covered bodies; the version
  number is part of the citation.
- Treating NIMA/NGA and IERS as interchangeable for the terrestrial frame:
  WGS-84 (NIMA/NGA) and the ITRS realisation (IERS) are closely aligned but
  are not identical; GPS-based missions should specify which realisation is
  used and at what epoch.
- Omitting WGCCRE when the mission addresses a non-Earth body: IAU does not
  itself publish rotation elements; the WGCCRE report is the correct citation.
- Citing USNO as the primary TAI authority: USNO operates a contributing
  clock ensemble but BIPM computes and disseminates TAI; the citation should
  name BIPM.

## Behavior contract (gate 3)

The authority-registry lookup, citation-validation, domain-resolution, and
coverage-audit logic is exercised by the gate 3 contract test:
scripts/test_e1009_authorities.py against scripts/e1009_authorities_logic.py
(stdlib unittest, offline). Run:

    python3 scripts/test_e1009_authorities.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
