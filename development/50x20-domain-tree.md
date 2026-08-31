# AeroSkills 50x20 Domain Tree (founder release bar 2026-08-31)

Founder, verbatim (Veda decision ledger, 2026-08-31,
`~/company-ops/veda/knowledge/decision-ledger.md`):

> "Not good enough for release until there are at least 20 skills per
> domain and verified and tested and reliable. And 50+ domains each
> ready."

**Release gate:** 50+ domain packs x 20+ verified leaf skills = 1,000+
leaf skills minimum, all make-validate green, reliable (decision ledger
2026-08-31). CEO audits the bar at >=9.5 before any release.

This tree decomposes the 12 aerospace disciplines into **73 sub-domain
packs** (-> 1,460 leaf skills at 20 each). It is the reworked version
from the Phase A R1 review: pack terminology is now one-way, pack
lists are reconciled with the live disk layout, and the build plan
carries a throughput model and calendar.

## 1. Terminology (one definition each)

- **Family** = 1 of 12 disciplines. Buyer-facing grouping. 11 domain
  families + 1 infrastructure family (cross-cutting, see section 9).
- **Pack** = 1 sub-domain. The installable unit. Every leaf in every
  pack is listed by `make packs`; a pack is a directory
  `skills/<family>/<pack>/`.
- **Leaf** = 1 skill = one `SKILL.md` + `scripts/` behavior contract
  test + corpus tasks. "Verified" = make validate 5/5 and make attest
  3/3 on the commit you are looking at, with the offline router
  deterministic (README definition, nothing more; not certification,
  not approval, not airworthy).

Decomposition is explicit, one direction only:

    family (12) -> pack (73) -> leaf (20 per pack)

No other use of "pack" in this document. The old two-way usage
(sub-domain = pack vs discipline = pack) is gone.

## 2. Live layout (verified 2026-08-31, make packs)

`make packs` on the dev tree reports 12 packs and 55 leaf skills: 12
families with a router SKILL.md, **55 leaf skills in 35 sub-domain
packs**. The Hit@1 corpus holds 126 tasks (gate 5). These are the
disk numbers the build plan starts from; section 3 is the full
taxonomy target.

Wave 2 (2026-08-31, Ops Manager): fan-out build to 69 leaf skills in
36 sub-domain packs (navigation pack opened under gnc-autonomy), 81
SKILL.md total, 154 Hit@1 corpus tasks. Fourteen new leaves:
avionics +3 (far-cs25/special-conditions,
flight-management/vertical-navigation, do254/configuration-management),
gnc-autonomy +3 (control/root-locus-design,
optimal-control/lqr-design, navigation/navigation-frames),
manufacturing-quality +1 (as9102/delta-fai), space-systems +2
(ecss/software-verification, subsystems/communication-link-budget),
structures +3 (fem/modal-analysis, composites/failure-criteria,
damage-tolerance/residual-strength), propulsion +2
(rocket/nozzle-design, turbofan/bypass-ratio-trade).

| Family | Live packs on disk (leaf count) | Planned packs (0 leaves) |
|---|---|---|
| Aerodynamics | airfoil (2) · cfd (2) | high-speed · aeroelasticity · wind-tunnel · drag-polars |
| Propulsion | gas-turbine-cycle (1) · turbofan (1) · rocket (1) | turbomachinery · combustion · electric-propulsion · engine-airframe |
| Structures | fem (1) · composites (1) · fatigue (1) · materials (1) · damage-tolerance (1) | thermal-structures |
| Flight mechanics | performance (2) · stability-control (1) | handling-qualities · flight-dynamics-sim |
| GNC / autonomy | control (1) · optimal-control (1) · space (2) | estimation-filtering · guidance · navigation · autopilots |
| Avionics | do178c (6) · do254 (3) · do160 (2) · far-cs25 (1) · flight-management (1) | data-bus · ima · displays |
| Systems engineering | arp4754a (3) · arp4761a (3) · mbse (1) | requirements · certification · config-mgmt |
| Space systems | ecss (2) · subsystems (2) · adcs (2) | orbit-mechanics · mission-design · propulsion-subsystems · launch-reentry · ground-systems |
| Vehicle design | conceptual (1) · sizing (1) · mass-properties (1) | mdo · cost-estimation |
| Manufacturing & quality | as9100 (2) · as9102 (1) | special-processes · supply-chain · additive |
| Flight test | envelope (1) · performance (1) | performance-test · stability-test · instrumentation · telemetry |
| Cross-cutting (infra) | units-atmos (1) · sep2640 (1) | numerics · data-sources · documentation · compliance · project-mgmt |

Notes on the reconciliation (R1 item 3):

- far-cs25 and flight-management are on disk under avionics and were
  missing from the R1 tree pack list; added (flight-management is NOT
  empty: it carries flight-planning).
- ecss is on disk under space-systems (2 leaves) and was missing from
  the R1 tree; added.
- sep2640 is on disk under cross-cutting (1 leaf) and was missing from
  the R1 tree; added.
- data-bus, ima, displays remain planned with 0 leaves (they exist in
  the R1 tree list and stay listed, marked 0).
- The R1 tree listed one systems-engineering pack "safety-assessment";
  the disk realizes it as arp4761a and adds arp4754a (development
  assurance), which had no home in the R1 list. Both are live packs
  now.
- The R1 tree names qms/fai are realized on disk as as9100/as9102
  (standard-anchored pack names, same style as do178c/arp4754a); the
  planned manufacturing packs keep their taxonomy names.
- GNC live directories are control, optimal-control, space (the space
  pack holds the orbit-dynamics and rendezvous-phasing leaves).

Pack count consequence: the R1 68-pack list omitted far-cs25, ecss,
sep2640, the gnc/space pack, and arp4754a, so the reconciled total is
73 packs, not 68. Arithmetic is re-stated in section 3 and verified in
the R2 pass.

## 3. The 73-pack tree (taxonomy target)

| Family | Packs (LIVE = leaf count on disk) | Leaf skills at 20 |
|---|---|---|
| Aerodynamics | airfoil (LIVE 2) · cfd (LIVE 1) · high-speed · aeroelasticity · wind-tunnel · drag-polars | 120 |
| Propulsion | gas-turbine-cycle · turbomachinery · combustion · rocket · electric-propulsion · engine-airframe | 120 |
| Structures | fem (LIVE 1) · composites (LIVE 1) · fatigue (LIVE 1) · materials (LIVE 1) · damage-tolerance · thermal-structures | 120 |
| Flight mechanics | performance · stability-control · handling-qualities · flight-dynamics-sim | 80 |
| GNC / autonomy | control (LIVE 1) · optimal-control (LIVE 1) · space (LIVE 2) · estimation-filtering · guidance · navigation · autopilots | 140 |
| Avionics | do178c (LIVE 6) · do254 (LIVE 3) · do160 (LIVE 1) · far-cs25 (LIVE 1) · flight-management (LIVE 1) · data-bus · ima · displays | 160 |
| Systems engineering | arp4754a (LIVE 3) · arp4761a (LIVE 3) · mbse (LIVE 1) · requirements · certification · config-mgmt | 120 |
| Space systems | ecss (LIVE 2) · subsystems (LIVE 2) · adcs (LIVE 1) · orbit-mechanics · mission-design · propulsion-subsystems · launch-reentry · ground-systems | 160 |
| Vehicle design | conceptual (LIVE 1) · sizing (LIVE 1) · mass-properties (LIVE 1) · mdo · cost-estimation | 100 |
| Manufacturing & quality | as9100 (LIVE 2) · as9102 (LIVE 1) · special-processes · supply-chain · additive | 100 |
| Flight test | envelope · performance-test · stability-test · instrumentation · telemetry | 100 |
| Cross-cutting (infra) | units-atmos (LIVE 1) · sep2640 (LIVE 1) · numerics · data-sources · documentation · compliance · project-mgmt | 140 |
| **Total** | **73 packs (35 live / 38 planned)** | **1,460** |

Arithmetic: 6+6+6+4+7+8+6+8+5+5+5+7 = 73 packs. At 20 per pack:
120+120+120+80+140+160+120+160+100+100+100+140 = 1,460. Release bar
math: 66 domain packs x 20 = 1,320 domain leaf skills (>= 1,000, and
66 >= 50 domains) plus 7 infra packs x 20 = 140, total 1,460. The
infra 140 are counted separately so they cannot pad the domain claim
(section 9).

## 4. Per-pack researched coverage (taxonomy leaves)

The 1,460 target is not a uniform 20x multiplier. Each planned pack
carries a researched leaf mapping from research/briefs/05-domain-taxonomy.md
(section 5 lists leaves with P0/P1/P2 priority; section 3 lists tools).
Packs marked PENDING have no enumerated leaf in the brief and need a
leaf-research pass before their fill wave. This mapping is the input
to each pack's build plan.

| Pack | Researched leaves (brief 05 ref) | Priority | Status |
|---|---|---|---|
| high-speed | compressible flow, shock-expansion, Mach effects (sec 4 curriculum; no leaf yet) | P0 | PENDING research |
| aeroelasticity | sharppy-flutter (5.1), preCICE FSI (3) | P2 | 1 leaf |
| wind-tunnel | windtunnel-data-reduction (5.1), OpenPIV (3) | P2 | 1 leaf |
| drag-polars | vlm-avl (5.1), xflr5-wing (5.1) | P0 | 2 leaves |
| gas-turbine-cycle | gas-turbine-turbofan decks, PyCycle/GSP (5.2) | P0 | 1 leaf (Scout flag) |
| turbomachinery | openfoam axial compressor stage (5.2) | P2 | 1 leaf |
| combustion | cea-rocket-combustion (5.2), cantera-kinetics (5.2) | P0 | 2 leaves (Scout flag) |
| rocket | rocketpy-trajectory (5.2), openrocket-sizing (5.2) | P1 | 2 leaves |
| electric-propulsion | hall-thruster-charm (5.2) | P2 | 1 leaf |
| engine-airframe | engine-airframe integration, install losses (5.2) | P1 | 1 leaf |
| damage-tolerance | damage-tolerance crack growth, NASGRO/AFGROW, FAR 25.571 (5.3) | P1 | 1 leaf |
| thermal-structures | loads/environmental, vibration (5.3), aeroelastic sizing loop (5.3) | P1 | 1-2 leaves |
| performance | mission-sizing, Breguet, pdas FLIGHT, W/S and T/W trades (5.4) | P0 | 1 leaf |
| stability-control | stability-derivatives-avl (5.4), linearization-modes (5.4) | P0 | 2 leaves |
| handling-qualities | MIL-STD-1797A / Cooper-Harper assessment (5.4) | P1 | 1 leaf |
| flight-dynamics-sim | jsbsim-fdm (5.4), flightgear-visual (5.4) | P0 | 2 leaves |
| estimation-filtering | kalman-filter, UKF, sensor fusion (5.5; filterpy/pykalman in 3) | P1 | 1 leaf |
| guidance | no leaf in brief; guidance laws, proportional nav, launch/reentry guidance | P0 | PENDING research |
| navigation | no leaf in brief; GPS/INS, frames ECEF/ECI/NED, SGP4 context | P0 | PENDING research |
| autopilots | px4-ardupilot, SITL, MAVLink, QGroundControl (5.5) | P1 | 1 leaf |
| data-bus | arinc429-1553-afdx parsing/simulation (5.6) | P2 | 1 leaf |
| ima | do297 (5.6) | P2 | 1 leaf |
| displays | no leaf in brief; cockpit display systems, ARINC 661, DAL A context | P1 | PENDING research |
| requirements | traceability, derived requirements (5.7) | P0 | 1 leaf |
| certification | certification-basis, TC/STC/TSO paths (5.7) | P0 | 1 leaf |
| config-mgmt | no leaf in brief; DO-178C CM realized by live do178c leaf, baseline/change control | P1 | PENDING research |
| orbit-mechanics | poliastro-mission (5.8), gmat-mission-design (5.8), orekit-propagation (5.8) | P0 | 3 leaves |
| mission-design | gmat mission design end-to-end (5.8), radiation-debris (5.8) | P1 | 2 leaves |
| propulsion-subsystems | no leaf in brief; chemical thruster sizing, electric propulsion, delta-v budgeting (RocketPy/CHARM in 3) | P1 | PENDING research |
| launch-reentry | no leaf in brief; ascent (dymos), reentry aeroheating, launcher sizing | P2 | PENDING research |
| ground-systems | ground tooling: cFS Ground System, YAMCS, COSMOS (5.8) | P2 | 1 leaf |
| mdo | aerosandbox-optimization (5.9), openmdao-trade-study (5.7), Dakota/pymoo (3) | P1 | 2-3 leaves |
| cost-estimation | no leaf in brief; CERs, parametric cost, NASA Cost Estimating Handbook | P1 | PENDING research |
| special-processes | nadcap-evidence (5.10), ndt inspection-methods (5.10), composites layup-cure (5.10), asme-y14.5 tolerancing (5.10) | P1 | 4 leaves |
| supply-chain | traceability, counterfeit-prevention, IDEA-STD-1010 (5.10) | P1 | 1 leaf |
| additive | lpbf, NASA MSFC-STD-3716/3717, ASTM F42 (5.10) | P2 | 1 leaf |
| envelope | envelope-expansion, V speeds (5.11) | P2 | 1 leaf |
| performance-test | performance flight testing, accelerate-stop (5.11 context) | P2 | 1 leaf |
| stability-test | stability-testing (5.11) | P2 | 1 leaf |
| instrumentation | no leaf in brief; flight test instrumentation, sensors, data acquisition, MAVLink | P2 | PENDING research |
| telemetry | telemetry-analysis (5.11), MAVLink (3) | P2 | 1 leaf |
| numerics | convergence-verification, Richardson, residuals (5.12) | P0 | 1 leaf |
| data-sources | UIUC DB, NTRS, OpenVSP library, OpenSky, NASA catalog (5.12) | P0 | 1 leaf |
| documentation | engineering-report, margins, assumptions (5.12) | P0 | 1 leaf |
| compliance | standards-map (5.12), itar-ear (5.12) | P0 | 2 leaves |
| project-mgmt | no leaf in brief; design review packages (5.9), certification program mgmt | P1 | PENDING research |

P0 packs ship in Wave 5 (section 7). PENDING packs get a leaf-research
pass inside their fill wave before build, so no pack is filled on a
uniform template.

## 5. SKU / bundle layer (buyer-facing, above packs)

73 installable packs are an engineering decomposition, not a buyer
story (Intel lens). 19 bundles sit above the packs: 12 discipline
bundles (one per family) plus 7 standard/program bundles. A bundle is
a curated pack set with a program story; pricing and positioning are
owned by GTM (research briefs 04 and 09), not by this tree.

| Bundle | Packs | Program story |
|---|---|---|
| Certification spine | do178c, do254, do160, do330 coverage via do178c tool-qualification | DO-178C/DO-254 certification team |
| Development assurance | arp4754a, arp4761a, do178c, do254 | FDAL/IDAL development program |
| Safety case | arp4761a, arp4754a | FHA/PSSA/SSA/CCA safety assessment |
| QMS and production | as9100, as9102, special-processes, supply-chain, additive | Production and FAI readiness |
| Airworthiness | far-cs25, do178c, do254 | TC/STC airworthiness scoping |
| Space ECSS | ecss, subsystems, adcs, orbit-mechanics, propulsion-subsystems | European space procurement |
| SEP-2640 delivery | sep2640, documentation, compliance | Skills-over-MCP host delivery |
| + 12 discipline bundles | each family's full pack set | per-discipline install |

## 6. Build order: demand-pull (standards first)

Order follows buyer pull, not taxonomy order (Intel lens): standards
packs speak procurement language and their verification bar is
replayable for buyers (Market lens). Tiers:

- **Tier 0, cert spine (finish to 20 first):** do178c (6/20),
  arp4754a (3/20), arp4761a (3/20), as9100 (2/20), ecss (2/20).
- **Tier 1, next standards packs:** do254 (3/20), do160 (2/20),
  far-cs25 (1/20), as9102 (1/20).
- **Tier 2, remaining live packs (26) toward 20:** airfoil, cfd,
  fem, composites, fatigue, materials, damage-tolerance, conceptual,
  sizing, mass-properties, control, optimal-control, space,
  subsystems, adcs, mbse, units-atmos, sep2640, flight-management,
  performance (flight-mechanics), stability-control,
  gas-turbine-cycle, turbofan, rocket, envelope, performance
  (flight-test).
- **Tier 3, new packs (38) in family lanes, Wave 6+:** combustion,
  electric-propulsion, engine-airframe, high-speed,
  aeroelasticity, wind-tunnel, drag-polars, thermal-structures,
  handling-qualities, flight-dynamics-sim, estimation-filtering,
  guidance, navigation, autopilots, data-bus, ima, displays,
  requirements, certification, config-mgmt, orbit-mechanics,
  mission-design, propulsion-subsystems, launch-reentry,
  ground-systems, mdo, cost-estimation, special-processes,
  supply-chain, additive, stability-test,
  instrumentation, telemetry, numerics, data-sources, documentation,
  compliance, project-mgmt.

Wave 5 (next) = fill the 35 live packs toward 20 each, Tier 0 first:
55 leaf skills -> 700 at completion of Wave 5 (35 x 20). Decompose
first: the 12 families already decompose into the full 73-pack list;
filling proceeds pack by pack, and the 38 remaining packs open in
Waves 6+ (38 x 20 = 760; 700 + 760 = 1,460).

## 7. Throughput model and calendar

Measured evidence: the Wave 4 session (2026-08-31, commit 2973701)
landed 16 verified leaf skills + 36 corpus tasks (66 -> 102) with make
validate 5/5, make attest 3/3, and run-tests all green in one builder
session. The Wave 5 session (2026-08-31) landed twelve verified leaf
skills + 24 corpus tasks (102 -> 126) plus the three new family
routers. Planning rate is conservative: **10 verified leaf skills per
builder per working session**, session = build + corpus batch + gates
+ commit.

Parallelism: 2 to 4 builders in disjoint pack lanes (Ops Manager,
Bheem, plus builder-capable team members; Scout/Intel/Market keep
review lenses). Shared assets are the serialization points:
eval/hit1-corpus.yaml (one file), README catalog table, and
standards-map additions. Mitigation: corpus tasks are added per wave
(batch), never per skill mid-wave; lanes are pack-disjoint so the
router eval only merges at wave close.

| Builders | Rate | Days to 1,320 domain leaves (bar) | Wall clock |
|---|---|---|---|
| 2 | 20/day | 66 working days | ~13-14 weeks |
| 3 | 30/day | 44 working days | ~9 weeks |
| 4 | 40/day | 33 working days | ~7 weeks |

Add decomposition, standards research, and review overhead: plan
3-4 months to the release bar, 4-5 months to the full 1,460. Waves
6+ run as parallel family lanes (aero/structures/vehicle;
gnc/space; avionics/sys-eng; mfg/flight-test), one lane per builder,
with a wave close = corpus batch + README refresh + gates + commit.

Constraint (Market lens, flagged): the WikiSkill usage loop stays
blocked until founder-gated distribution starts, so early growth
depends on taxonomy research and review gates, not usage feedback.
This is accepted; the throughput model does not assume usage data.

## 8. Corpus scale plan

Current gate-5 corpus: 126 tasks / 55 leaf skills = 2.3 tasks per
leaf (Wave 5 policy: 2 tasks per new skill + adversarial cross-pairs).
At 1,460 leaves the budget is:

- 2 tasks per leaf = 2,920 base tasks
- ~10-15% adversarial cross-pair tasks = ~350-440 (router sharpness)
- ~3,270-3,360 tasks total, roughly 2.2-2.3 per leaf on average
  (3,270 / 1,460 = 2.24, 3,360 / 1,460 = 2.30; 2.4 would imply
  3,504, outside the stated range)

Per-skill budget is not uniform: cert-spine and safety-critical leaves
get 3-4 tasks (DAL, coverage, traceability angles); commodity leaves
get 2. Corpus growth is batched per wave and committed with the wave;
gate 5 stays deterministic and offline. Corpus size is tracked in
eval/hit1-corpus.yaml and asserted by make validate.

## 9. Cross-cutting is infrastructure, not domain depth

The 7 cross-cutting packs (units-atmos, numerics, data-sources,
documentation, compliance, project-mgmt, sep2640) are shared
infrastructure: units and atmospheres underpin every aero/space
computation, compliance and standards-map underpin the cert spine,
sep2640 is the delivery format, documentation is the audit-trail
discipline. They are built once and reused everywhere.

They are counted separately from the 66 domain packs, so the release
claim rests on 1,320 domain leaf skills and cannot be padded with
commodity skills (Intel/Market integrity concern). Infra skills are
still gated by the full verification bar; they just do not count as
domain depth.

## 10. Verification bar (every leaf)

- make validate 5/5: spec lint, desc lint, per-skill behavior
  contract, no-verbatim copyright scan, Hit@1 corpus routing
- make attest 3/3: number snapshot offline, brief audit, content
  policy sweep
- Per-skill behavior contract test shipped with the skill
- Deterministic offline router

"Verified" means the full bar passes on the commit you are looking at
(README wording). It is not certification, not approval, not airworthy.

## 11. Registry

Tracked in the Veda project registry:
`~/company-ops/veda/knowledge/_PROJECTS.md` and
`~/company-ops/veda/knowledge/_ASSIGNMENTS.md` (decision ledger
2026-08-31, `~/company-ops/veda/knowledge/decision-ledger.md`). CEO
audits the 50x20 bar at >=9.5 before any release.
