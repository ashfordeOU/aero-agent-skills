# ITAR / EAR Overview for Aerospace Engineers

Reference doc for the export-control-awareness skill. Regulatory citations
point to the public regulations; always check the current text before
relying on a citation, because both the USML and the CCL are revised
regularly.

Primary sources:
- ITAR: 22 CFR parts 120 through 130, in particular 22 CFR 120.33
  (technical data), 22 CFR 120.34 (public domain), 22 CFR 120.50 (deemed
  export), 22 CFR part 121 (USML).
- EAR: 15 CFR parts 730 through 774, in particular 15 CFR 734.7 through
  734.8 (publicly available and fundamental research), 15 CFR 734.13
  (deemed export), 15 CFR 774 (CCL).
- Public mirrors: https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M
  and https://www.ecfr.gov/current/title-15/subtitle-B/chapter-VII/subchapter-C

## 1. Jurisdiction: ITAR vs EAR

An item is either under ITAR jurisdiction or EAR jurisdiction, never both.

- ITAR jurisdiction: the item is described by the USML (22 CFR part 121).
  Such items are defense articles. Their technical data and related
  defense services are ITAR-controlled.
- EAR jurisdiction: everything else that is subject to US export controls,
  including items described by the CCL (15 CFR 774) and EAR99 items.

Jurisdiction and classification are determined by the US government
(DDTC for the USML, BIS for the CCL) and by the company's export
compliance program. An engineer cannot self-certify jurisdiction; the
trade compliance office must confirm it.

## 2. USML categories (22 CFR part 121)

Aerospace-relevant categories:

| Cat | Subject |
|-----|---------|
| IV  | Launch vehicles, guided missiles, ballistic missiles, rockets, torpedoes, bombs and mines |
| V   | Explosives and energetic materials, propellants and their constituents |
| VI  | Surface vessels of war and special naval equipment |
| VII | Ground vehicles |
| VIII| Aircraft and related articles |
| IX  | Military training equipment and training |
| X   | Personal protective equipment |
| XI  | Military electronics |
| XII | Fire control, laser, imaging and guidance equipment |
| XIII| Materials and miscellaneous articles |
| XIV | Toxicological agents and associated equipment |
| XV  | Spacecraft and related articles |
| XVI | Nuclear weapons related articles |
| XVII| Articles, technical data and defense services not otherwise enumerated |
| XVIII| Directed energy weapons |
| XX  | Submersible vessels, oceanographic and associated equipment |
| XXI | Articles, technical data and defense services not otherwise enumerated |

Category XIX is reserved. Category XVII is the catch-all for defense
articles and defense services not otherwise enumerated (its official
title begins with a term that is outside this document's content policy).

Aerospace examples of defense articles: military aircraft and their
parts, components, accessories and attachments (USML VIII); guided
missiles and launch vehicles (USML IV); spacecraft and related items
(USML XV); military gas turbine engines when not transitioned to EAR.

## 3. EAR 600-series and EAR99

Export control reform moved most defense articles from the USML to
600-series ECCNs under EAR jurisdiction. The 600 series covers military
items across all ten EAR categories (0 through 9), with software and
technology entries in each category (for example 9D610 and 9E610).

Aerospace-relevant 600-series examples:

| ECCN | Subject |
|------|---------|
| 0A606| Military ground vehicles and related items |
| 8A609| Marine gas turbine engines and associated equipment |
| 9A610| Military aircraft and related items |
| 9A619| Military gas turbine engines and associated equipment |
| 9D610| Software specially designed for 9A610 or 9A619 items |
| 9E610| Technology for 9A610 or 9A619 items |

Items not described by the USML or the CCL default to EAR99. EAR99 is
still EAR jurisdiction: end-use and end-user screening applies, general
prohibitions apply (for example no support to embargoed destinations or
denied persons), and anti-boycott rules apply.

## 4. Technical data (ITAR)

Technical data means information required for the design, development,
production, manufacture, assembly, operation, repair, testing,
maintenance, or modification of defense articles. It includes
blueprints, drawings, photographs, plans, instructions, and
documentation, in any form (paper, electronic, oral).

Excluded from technical data:
- General scientific, mathematical, or engineering principles commonly
  taught in schools, colleges, and universities.
- Information in the public domain (see section 5).
- Basic marketing information.
- Telemetry data for certain missiles, as specified in the regulation.

Under EAR the analogous term is technology (15 CFR 772), which means
specific information necessary for the development, production, or use
of a product. Technology takes the form of technical data or technical
assistance.

## 5. Public domain and publicly available

Public domain under ITAR (22 CFR 120.34) includes information that is:
- Published and sold or otherwise made available to the public without
  restriction, for example textbooks, journals, and unrestricted
  subscriptions.
- Available in libraries open to the public.
- Published patents or patent applications open to public inspection.
- Distributed without restriction at conferences, meetings, lectures,
  or speeches open to the public.
- The results of fundamental research (see section 6).
- Approved for public release by the US government.

EAR publicly available (15 CFR 734.7 through 734.8) covers the same
families: published information, fundamental research, educational
information, and information in certain patent applications. Publicly
available information is not subject to the EAR, with narrow exceptions
for encryption source code in some cases.

Important limits: information that was obtained or published in
violation of law or regulation is not public domain just because it
appears in print, and information that was placed in the public domain
by an unauthorized disclosure remains controlled. Publication does not
cure an unauthorized release.

## 6. Fundamental research exclusion

Fundamental research is basic and applied research in science and
engineering performed at an accredited institution of higher learning in
the US where the resulting information is ordinarily published and
shared broadly within the scientific community. Its results are public
domain / publicly available even before formal publication.

The exclusion is lost when:
- The research is funded by the US government with specific controls on
  the resulting information (for example access and dissemination
  restrictions in the award).
- The research agreement restricts publication or sharing, for example
  a side letter or a pre-publication review clause that lets the sponsor
  withhold results.

A common engineering trap: a project that starts as open academic work
becomes controlled the day a publication restriction is signed. Check
every agreement before relying on the exclusion.

## 7. Deemed exports

A deemed export is the release of technology or technical data to a
foreign person in the US, treated as an export to that person's country
of nationality. Deemed exports apply under both ITAR (22 CFR 120.50) and
EAR (15 CFR 734.13), and deemed reexports apply to foreign persons
located in third countries.

Release includes:
- Visual or other inspection of controlled items or data.
- Oral or written exchanges of controlled information.
- Application of personal knowledge or experience acquired from
  controlled technology.

Consequence for engineering teams: hiring a foreign national, or sharing
a controlled specification with a foreign collaborator in the same
building, can require a license or a license exception, exactly like a
physical export across a border.

## 8. Red-flag topic table

The logic module screens item descriptions against these topics. A match
is a stop-and-verify signal, not a classification.

| Red-flag topic | Why it is restricted |
|----------------|----------------------|
| Turbine blade alloys and high-temperature materials | Single-crystal and directionally solidified superalloys for gas turbine blades are controlled materials; composition and processing know-how is technical data |
| Propulsion technology | Military gas turbine engines (9A619) and rocket, ramjet and scramjet propulsion are controlled |
| Missiles, rockets and launch vehicles | USML Category IV; MTCR-controlled items stay on the USML or on EAR missile-technology ECCNs |
| Controlled sensors and seekers | Infrared focal plane arrays, night vision, laser rangefinders and designators, high-grade inertial sensors: CCL categories 6 and 7 or USML XII |
| Avionics and navigation equipment | 600-series ECCNs (for example 7A611) or USML XI and XII; high-performance GNSS and inertial navigation is CCL-controlled |
| Low-observable design and radar-absorbing materials | Low-observable design and radar cross-section reduction know-how is controlled |
| Spacecraft and launch vehicles | USML XV (with exceptions moved to EAR); orbital maneuvering and rendezvous technology is controlled |
| Unmanned aerial systems | Performance thresholds decide between 9A610 and 9A012; payload and autonomy software matter |
| Radiation-hardened electronics | CCL category 3; common in military and space systems |
| Cryptographic items | EAR category 5 part 2; some mass-market encryption has license exceptions |
| Hypersonic technology | Emerging-controlled technology under EAR and USML IV |
| Directed energy weapons | USML XVIII |
| Specialty composites and ceramics | Carbon-carbon and ceramic-matrix composites are CCL 9C materials |
| Energetic materials and propellants | USML V or CCL 1C |
| Fire control and targeting | USML XII or 600-series |
| Military aircraft and engines | USML VIII or 600-series 9A610 and 9A619 |
| Defense services and training | Training or assistance to a foreign person on a defense article is a controlled defense service |

## 9. Handling guidance

- Verify jurisdiction and classification with the trade compliance office
  before sharing, publishing, or transferring anything that could be
  controlled. An engineer's own assessment is a screening input, not an
  authorization.
- Never mark or represent an item, data set, or document as compliant,
  certified, or authorized on your own authority. Only the compliance
  office can issue that determination.
- Never export, deemed export, or reexport controlled data without
  authorization: no email to a foreign collaborator, no shared drive
  access for a foreign national, no conference presentation, no
  publication, without a license or a valid license exception.
- Do not destroy or alter records of a release after the fact; keep the
  classification basis, the recipient, and any license exception relied
  upon.
- Re-run the screening whenever the item, audience, or purpose changes;
  a verdict is only valid for the inputs it was computed from.
- If in doubt, treat the data as controlled until the compliance office
  says otherwise. The cost of an unauthorized release far exceeds the
  cost of a review.

See the handling checklist in the skill's assets directory for the
operational form of these rules.
