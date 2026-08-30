# AeroSkills — Aerospace Domain Research & Skills Taxonomy Skeleton

**Purpose:** Domain-content research to serve as the taxonomy skeleton for AeroSkills, an aerospace engineering skills library for AI agents. All tools named are real; standards are the ones practicing engineers and certification authorities actually use.

---

## 1. The Domain Landscape: Core Disciplines & Their Reality

Aerospace engineering splits into **aeronautics** (atmospheric flight) and **astronautics** (space). Both share the same core disciplinary trunk. Every discipline below is a candidate skill domain; the industry organizes teams exactly this way (Purdue, MIT, Georgia Tech, and the major OEMs all use this decomposition).

| # | Discipline | What engineers actually do | Dominant software reality |
|---|---|---|---|
| 1 | Aerodynamics & CFD | Airfoil/wing design, drag polars, CFD analysis & validation, shape optimization, wind-tunnel testing | OpenFOAM, SU2, XFOIL/XFLR5/AVL (industry: ANSYS Fluent, STAR-CCM+) |
| 2 | Propulsion | Engine cycle analysis, turbomachinery, combustion thermochemistry, rocket sizing, engine-airframe integration | NASA CEA, Cantera, NPSS/GSP, RocketPy (industry: GasTurb, ANSYS CFX) |
| 3 | Structures & Materials | Loads, FEM stress analysis, composites, fatigue/damage tolerance, allowables, NDT | CalculiX, pyNastran, Code_Aster (industry: Nastran, Abaqus, HyperSizer) |
| 4 | Flight Mechanics (Performance, Stability & Control) | Sizing, performance (range/payload), trim, stability derivatives, handling qualities | AVL, XFLR5, JSBSim, FlightGear, pdas codes |
| 5 | GNC / Autonomy | Control law design, estimation/filtering, trajectory optimization, autopilots, UAVs | dymos/OpenMDAO, CasADi, python-control, PX4/ArduPilot (industry: MATLAB/Simulink) |
| 6 | Avionics & Flight Software | Data buses, embedded software, DO-178C/DO-254 assurance, IMA | NASA cFS, F Prime, RTEMS, Zephyr, KiCad |
| 7 | Systems Engineering & Safety | Requirements, MBSE, safety assessment (FHA/PSSA/SSA), certification coordination | Capella, Papyrus, OSATE/AADL, OpenMDAO (industry: DOORS, Polarion, Jama) |
| 8 | Space Systems & Astrodynamics | Orbital mechanics, mission design, spacecraft subsystems, launch/reentry | poliastro, Orekit, GMAT, Skyfield (industry: STK) |
| 9 | Aircraft/Vehicle Design & Integration | Conceptual design, sizing loops, MDO, design reviews | OpenVSP, AeroSandbox, OpenMDAO, TASOPT |
| 10 | Manufacturing & Quality | Production engineering, special processes, first article, QMS | FreeCAD, AS9102 workflows, Nadcap evidence |
| 11 | Flight Test & Operations | Envelope expansion, performance/stability flight tests, instrumentation, airspace ops | JSBSim (sim), MAVLink/telemetry, flight test guides |
| 12 | Cross-cutting / Foundational | Units & atmospheres, numerics/V&V, data sources, documentation | ISA model, UIUC airfoil DB, NASA NTRS |

**Key structural insight for the library:** aerospace is a *standards- and evidence-driven* domain. An agent skill that produces numbers without a compliance/validation check is not genuinely useful. Every skill should carry a "compliance & validation" step (see §6 template).

---

## 2. Standards & Regulations Map (the compliance backbone)

This is the single most important thing an aerospace skill set must know. Hierarchically:

```
Regulations (law)         FAR 23/25/27/29, 33, 34, 35, 36 (FAA) · CS-23/25/27/29, CS-E, CS-P (EASA)
   │                      Part 21 (TC/STC/TSO/PMO), Part 43/145 (maintenance), Part 91 (ops), Part 107 (UAS)
   ▼
Accepted Means of Compliance (guidance)
   ├─ System level:      SAE ARP4754A/B (development, FDAL/IDAL) · ARP4761A (FHA/PSSA/SSA/CCA)
   ├─ Software:          RTCA DO-178C / EUROCAE ED-12C  (+ DO-330 tool qual., DO-331 MBD, DO-332 OOTI, DO-333 formal)
   ├─ Hardware:          RTCA DO-254 / ED-80 (complex AEH) · DO-160G / ED-14G (environmental qualification)
   ├─ IMA:               DO-297
   ├─ Security:          DO-326A/ED-202A (airworthiness security), DO-356A (security methods)
   └─ FAA acceptance:    AC 20-115D (software), AC 20-152A (hardware), AC 20-174 (ARP4754A), AC 25.1309-1 (safety)
Quality / Production      AS9100D (ISO 9001:2015 + ~115 aerospace clauses), AS9102 (FAI), AS9103 (key characteristics),
                          AS9110 (maintenance), AS9120 (distributors), Nadcap (special processes), SAE AMS specs
Materials data            MMPDS (metallic allowables, ex-MIL-HDBK-5) · CMH-17 (composites, ex-MIL-HDBK-17)
Test & environment        MIL-STD-810H (env. testing), MIL-STD-461G (EMC), MIL-STD-704 (aircraft power), DO-160G
Data buses                ARINC 429/629, ARINC 664 (AFDX), MIL-STD-1553B, CAN, Ethernet
Space (separate regime)   ECSS (E-ST-10C SE, E-ST-32C structures, E-ST-40C SW eng, Q-ST-80C SW assurance, M-ST-40 CM),
                          CCSDS (telemetry 133.0, CFDP 727.0), NASA NPR 7120/7150.2, NASA-STD-8739.8, GEVS-SE, SMC-S-016
Defense airworthiness     MIL-HDBK-516C (USAF), DEF STAN 00-970 (UK), STANAG 4671 (UAS)
UAS / new tech            Part 107, EASA UAS regs, JARUS SORA (ops risk), ASTM F3269/F38 (Part 23 consensus)
Export control            ITAR (22 CFR 120-130), EAR (15 CFR 730-774) — every aerospace repo/skill must respect this
```

**DAL levels (must be memorized by any agent doing safety work):**
A = Catastrophic · B = Hazardous · C = Major · D = Minor · E = No safety effect.
ARP4761A propagates severity → DAL; ARP4754A splits **FDAL** (function) vs **IDAL** (item). DO-178C coverage depth scales with DAL: Level A requires 100% MC/DC; B requires 100% decision; C requires 100% statement; D requires no structural coverage.

**Regulatory basics an agent needs:** a Type Certificate (TC) is the design approval; Supplemental TC (STC) for modifications; TSO/ETSO for equipment; PMA for parts. Certification basis = the specific FAR/CS amendments + special conditions + exemptions agreed with the authority. EASA uses Design/Production Organisation Approvals (21J/21G); FAA uses delegation (DER/ODA).

---

## 3. Open-Source Tool Ecosystem by Discipline

Concrete, real, mostly CLI-scriptable (the *italic* annotation is the agent-usability judgment — prefer text-driven tools).

### Aerodynamics & CFD
- **XFOIL** (MIT Drela) — 2D airfoil analysis/design, viscous-inviscid; scriptable via input files. *Excellent for agents.*
- **XFLR5** — XFOIL + 3D panel/VLM; GUI-heavy but batch-capable. *Good; prefer CLI wrapper.*
- **AVL** (MIT Drela) — 3D vortex-lattice + slender-body, trim & stability derivatives; text-input driven. *Excellent for agents.*
- **OpenFOAM** (ESI `openfoam.org` / OpenCFD `openfoam.com`, GPL) — general CFD; case structure `0/ constant/ system/`, `blockMesh`, `snappyHexMesh`, `simpleFoam`/`rhoCentralFoam`/`pimpleFoam`; PyFoam for scripting. *Excellent.*
- **SU2** (LGPL-2.1) — CFD + discrete adjoint aerodynamic shape optimization; single `.cfg` config file. *Excellent for agents.*
- **Meshing:** Gmsh (GPL, scriptable `.geo`), Salome (LGPL), cfMesh. **Post:** ParaView (BSD-3), PyVista (MIT). *All scriptable.*
- **Aeroelasticity:** SHARPy (Imperial, BSD-3, low-fidelity aero + beam FEM, flutter), preCICE (LGPL, partitioned FSI coupling). *Good.*
- **Experimental:** OpenPIV (GPL, PIV analysis), wind-tunnel data reduction in Python. 
- **Data:** UIUC Airfoil Database, AirfoilTools, NASA NTRS, OpenVSP model library.

### Propulsion
- **NASA CEA** (Chemical Equilibrium with Applications, open Fortran) — rocket/combustion equilibrium & performance (Isp, C*). *Industry standard.*
- **Cantera** (BSD) — combustion thermochemistry/kinetics in Python. *Excellent.*
- **CoolProp** (MIT) — thermophysical properties.
- **NPSS** (consortium-licensed, source available to members) — gas-turbine cycle; **GSP** (NLR freeware) — turbofan/turboshaft cycle decks; **PyCycle** (NASA, open) — Python object-oriented cycle analysis. *PyCycle best for agents.*
- **RocketPy** (MIT) — 6-DOF rocket trajectory + motor performance. **OpenRocket** (GPL) — model-rocket sizing. **RPA** (free tier) — rocket engine preliminary design. **CHARM** (Stanford, open) — 2D Hall-thruster plasma simulation (electric propulsion).
- Turbomachinery: OpenFOAM tutorials; SU2 has turbomachinery modes.

### Structures & Materials
- **CalculiX** (GPL-2; ccx solver + cgx pre/post; ABAQUS-format input) — linear/nonlinear static, dynamic, thermal. *Excellent; text input.*
- **Code_Aster** (EDF, GPL/LGPL) — advanced FEA (fracture, composites, dynamics). *Good.*
- **pyNastran** (open) — read/write/convert Nastran BDF/OP2/OP4; enables the whole industrial Nastran ecosystem without the solver. *Excellent for agents.*
- **preCICE** — FSI coupling; **OpenMDAO + CalculiX + strip-aero** patterns exist for aeroelastic sizing.
- **Fatigue/fracture:** NASGRO (NASA, free license) — crack growth; AFGROW (AFRL, freeware) — crack growth; MMPDS for allowables, CMH-17 for composite allowables (A-/B-basis statistics, K-factors).
- **Composites:** eLamX (TU Dresden, free) — CLT laminate analysis; open-source Python CLT/laminate packages; ASTM D3039/D3410/D5528/D5766/D6671 test methods for data.
- **Materials data:** MMPDS, CMH-17, SAE AMS specs, Cambridge CES (commercial).
- CAD/CAM: FreeCAD (GPL) for geometry/prep; Gmsh/Salome for meshing.

### Flight Mechanics (Performance, Stability & Control)
- **AVL, XFLR5, XFOIL** (above) — S&C derivatives, trim.
- **JSBSim** (LGPL) — object-oriented flight dynamics model (FDM); XML aircraft models; Python bindings; used by FlightGear. *Excellent for agents.*
- **FlightGear** (GPL) — full flight sim (visualization, autopilot testing).
- **pdas / Public Domain Aeronautical Software** (Ralph Carmichael) — classic FORTRAN codes: `FLIGHT` (performance), `AERO`, `ATMOS`, `STABC` etc. Free, deterministic, great for validation.
- **TASOPT** (MIT Drela, freeware) — transport aircraft performance/sizing.
- Handling qualities: MIL-STD-1797A / MIL-F-8785C criteria, Cooper-Harper rating scale (for reports).

### GNC / Autonomy
- **dymos** (NASA/OpenMDAO org, Apache-2.0) — optimal control / trajectory optimization (Gauss-Lobatto, Radau pseudospectral), tight OpenMDAO integration. *Excellent for agents.*
- **OpenMDAO** (NASA, Apache-2.0) — MDO framework (used with everything above).
- **CasADi** (LGPL) — algorithmic differentiation + NLP; **acados** (BSD-2) — real-time NMPC; **gpopt** — open successor to GPOPS-II (pseudospectral).
- **python-control** (BSD-3) — transfer functions, state space, LQR/H∞/root locus; **harfang/Slycot** for state-space.
- Estimation: Kalman/UKF via `filterpy`, `pykalman`, `stonesoup` (tracking).
- **PX4** (BSD-3), **ArduPilot** (GPL-3) — open autopilots; **QGroundControl** (Apache/GPL); **MAVLink/MAVSDK** protocol stack. The de-facto open UAV stack.
- Simulation: JSBSim (air), dymos (space trajectories), `GNC_orbital` (ROS2, proximity ops).

### Avionics & Flight Software
- **NASA cFS** (Apache-2.0) — core Flight Executive (cFE) + OSAL + PSP; flight-proven architecture (apps: CFDP, housekeeping, health & safety). *The reference architecture.*
- **F Prime (F´)** (JPL, Apache-2.0) — component-driven C++ flight software framework, code-gen modeling, used on smallsats. *Excellent for agents (CLI-driven).*
- **RTEMS** (BSD-2) — space-grade RTOS; **Zephyr** (Apache-2.0), **FreeRTOS** (MIT) — embedded.
- **KiCad** (GPL) — PCB design for avionics hardware (DO-254 simple/complex AEH context).
- Data buses: ARINC 429 (spec-driven; open decoders in Python), MIL-STD-1553B, ARINC 664/AFDX (Ethernet), CAN (ARINC 825).
- Verification tooling (open): **CppUTest/Unity** (unit), **gcov/lcov** (structural coverage — the DO-178C "statement/decision" evidence baseline), **cppcheck** (static analysis), **PVS-Studio** (free for OSS). Commercial mainstays: VectorCAST, LDRA, Tessy, Polyspace — know them as the industrial baseline.
- MBSE for avionics architecture: **OSATE** (AADL, EPL) — architecture analysis (latency, safety, FTA from models).

### Systems Engineering & Safety
- **Capella** (Eclipse, EPL) — MBSE method (ArcCapella), SysML-ish modeling. *Excellent, scriptable models.*
- **Papyrus** (Eclipse, EPL) — SysML/UML modeling.
- **OSATE** (Eclipse, EPL) — AADL for embedded/safety-critical architecture + error-model annexes (FMEA/FTA from models).
- Requirements: industrial = DOORS, Polarion, Jama; open = OpenProject/Redmine + markdown (fine for agent workflows); key concept = **bidirectional traceability** (the audit asks for it, always).
- Safety methods (ARP4761A): FHA, PSSA, SSA, CCA (ZSA/PRA/CMA), FTA, FMEA/FMECA, Markov; open tools: **OpenFTA** (free), Python `fta`/`scram` libraries, **Py-Agrum** (Bayesian nets for safety).
- MDO/trade studies: OpenMDAO, **Dakota** (Sandia, LGPL — DOE/optimization/UQ), **pymoo** (Apache-2.0, NSGA-II etc.), **BoTorch** (Bayesian optimization).

### Space Systems & Astrodynamics
- **poliastro** (MIT) — orbital mechanics, maneuvers, Lambert, Hohmann, J2 perturbations. *Excellent for agents.*
- **Orekit** (Apache-2.0, Java, Python wrapper) — full astrodynamics library (propagators, frames, TLEs).
- **GMAT** (NASA, Apache-2.0) — full mission design/optimization tool, scriptable.
- **Skyfield** (MIT) — ephemerides (JPL DE), TLE propagation (SGP4).
- Spacecraft subsystems context: CCSDS protocols, ECSS standards, radiation environment (SPENVIS, IRENE), power (EPS), thermal (Thermal Desktop commercial; open: **ESATAN** is commercial — note limitation).
- cFS/F Prime (above) for flight software; ground systems: **NASA cFS Ground System**, **YAMCS**, COSMOS (Ball, open).

### Aircraft Design & Integration
- **OpenVSP** (NASA, NOSA 1.3) — parametric geometry (fuselage/wing/nacelle components, airfoils, user parameters/links); exports to meshes & analysis; has a Python API (vsp3 bindings). *The conceptual-design hub.*
- **AeroSandbox** (MIT) — aircraft design optimization with automatic differentiation; composable aero/propulsion/structures/trajectory models.
- **OpenMDAO + dymos + SU2 + CalculiX** — the high-fidelity MDO stack.
- **TASOPT** — transport sizing. **OpenVSP + VSPAERO** (its own VLM/panel aero solver) for quick polars.
- Classic sizing loop: requirements → weight estimation → wing loading (W/S) & thrust loading (T/W) trades → geometry (OpenVSP) → aero (VSPAERO/AVL) → performance (Breguet/JSBSim) → iterate; wrap in OpenMDAO.

### Manufacturing & Quality
- AS9100D QMS clauses (8.1.1 operational risk, 8.1.2 configuration mgmt, 8.1.3 product safety, 8.1.4 counterfeit prevention, 8.4.1 external providers, 8.5.1.3 special-process verification).
- **AS9102 First Article Inspection**: Form 1 (part accountability), Form 2 (material/special processes), Form 3 (characteristic accountability, measured values) — FAI "Not Complete" until all nonconformances cleared; delta/partial FAI after changes.
- **AS9103** variation management of key characteristics; **Nadcap** commodities: heat treating, chemical processing, welding, NDT (UT/RT/MT/PT/ET), coatings, shot peening, composites (layup, autoclave cure, ultrasonic C-scan).
- NDT methods: ultrasonic, radiography, eddy current, penetrant, magnetic particle, thermography.
- AM: LPBF (metal powder bed), NASA AM standards (MSFC-STD-3716/3717), ASTM F42 committee.
- Composites manufacturing: prepreg layup, autoclave cure cycle, ply books, C-scan NDI.
- Machining: CNC (FreeCAD CAM/Path), tolerancing (GD&T per ASME Y14.5 — essential!), metrology (CMM).
- Document/evidence culture: process parameter logging, calibration, material traceability, certificate of conformance.

### Flight Test & Operations
- FAA/EASA flight test guides (Part 23/25 performance & S&C testing), USAF TPS curriculum structure.
- Workflow: test plan → instrumentation → envelope expansion → performance (V speeds, climb, accelerate-stop, noise) → stability & control (static/dynamic, trim) → data reduction → report.
- Tools: JSBSim for pre-test simulation, MAVLink telemetry, OpenSky Network (data), flight-data analysis in Python (pandas).
- Ops: Part 91 (general), Part 107 (UAS), EASA UAS, JARUS SORA for BVLOS risk assessment.

---

## 4. Academic Curriculum Shape (taxonomy basis)

Verified against MIT Course 16, Purdue AAE, Georgia Tech AE, UMD, USNA, and a standard semester plan. The curriculum maps 1:1 onto the skill taxonomy and is a good naming/layering guide.

**Years 1–2 (foundations):** Calculus I–III, ODEs, linear algebra; physics (mechanics, E&M, thermo); chemistry; statics/dynamics; mechanics of solids/strength of materials; fluid mechanics; thermodynamics; materials science; programming (MATLAB/Python); intro "Elements of Aeronautics"; engineering graphics/CAD.
→ *Taxonomy layer: numerics, units/atmosphere, statics/dynamics, intro aero.*

**Year 3 (core disciplines):** Aerodynamics I–II; Gas Dynamics; Propulsion I–II; Aircraft Structures I–II; Flight Dynamics I (performance); Stability & Control; Control Systems; Avionics/intro systems; Experimental Methods & Wind Tunnel Lab; Vibration.
→ *Taxonomy layer: the five analytical domains + experimental.*

**Year 4 (integration):** CFD; Aircraft Design (year-long capstone, team-based, PDR/CDR structure, national competitions); Flight Dynamics II; Astrodynamics/Spacecraft Design; Avionics & Systems Integration; Electric/elective specialization; Senior Project.
→ *Taxonomy layer: design/integration, space, capstone workflows.*

**Grad school (specialization):** Aeroelasticity, computational aero, propulsion (combustion/turbomachinery), composite structures, robust/multivariable control, estimation, optimization, flight test, human factors.

**Career roles** (the library's "user personas"): aerodynamics engineer, propulsion engineer, structures engineer, flight dynamics engineer, GNC engineer, systems engineer, avionics/software engineer, manufacturing/quality engineer, flight test engineer, astrodynamics engineer.

---

## 5. Proposed AeroSkills Taxonomy (the skeleton)

Naming convention: `domain/sub-area/skill-action-tool`. Each leaf is a skill; each skill carries the §6 template. Priority: **P0** = MVP must-haves, **P1** = fast follow, **P2** = later/niche.

### 5.1 Aerodynamics & CFD
- `aero/airfoil/xfoil-analysis` (P0) — polars, cl/cd/cm, transition, Re effects, UIUC DB lookup
- `aero/airfoil/xfoil-design` (P1) — inverse design, thickness/camber trades
- `aero/wing/vlm-avl` (P0) — lift distribution, induced drag, stability derivatives, trim
- `aero/wing/xflr5-wing` (P1) — 3D panel + viscous, CL-alpha sweeps
- `aero/cfd/openfoam-run` (P0) — case anatomy, meshing, solvers, residual tracking
- `aero/cfd/su2-aerodynamic-shape-optimization` (P1) — adjoint gradient loop
- `aero/cfd/mesh-gmsh-snappy` (P1) — mesh convergence (y+, Richardson extrapolation)
- `aero/cfd/postprocess-paraview-pyvista` (P0) — forces, Cp, separation detection
- `aero/cfd/validation` (P0) — case matching (NACA 0012 drag divergence, ONERA M6, DLR-F6), AIAA/ASME V&V practice
- `aero/aeroelasticity/sharppy-flutter` (P2) — flutter/divergence screening
- `aero/experimental/windtunnel-data-reduction` (P2) — corrections, OpenPIV

### 5.2 Propulsion
- `prop/cycle/gas-turbine-turbofan` (P0) — on-design/off-design decks (PyCycle/GSP-style), BPR/FPR trades
- `prop/thermo/cea-rocket-combustion` (P0) — Isp, chamber conditions, mixture ratio
- `prop/thermo/cantera-kinetics` (P1) — ignition, flame speed, emissions
- `prop/rocket/rocketpy-trajectory` (P1) — thrust curve, drag, staging
- `prop/rocket/openrocket-sizing` (P1) — preliminary motor/vehicle sizing
- `prop/turbomachinery/openfoam` (P2) — axial compressor stage analysis
- `prop/electric/hall-thruster-charm` (P2)
- `prop/integration/engine-airframe` (P1) — thrust-drag bookkeeping, install losses
- Compliance hooks: FAR 33 / CS-E (engine certification), FAR 34/36 + ICAO Annex 16 (emissions/noise)

### 5.3 Structures & Materials
- `struct/fem/calculix-linear` (P0) — static stress, margins of safety, ABAQUS-style input
- `struct/fem/pynastran-interop` (P1) — BDF/OP2 read/write, model checks
- `struct/fem/code-aster-advanced` (P2) — nonlinear, fracture, composites
- `struct/materials/mmpsd-allowables` (P0) — A/B-basis, K-factors, metallic allowables lookup
- `struct/composites/clt-laminate` (P1) — CLT, ply schedule, failure criteria (Tsai-Wu, Hashin)
- `struct/composites/cmh17-allowables` (P2)
- `struct/fatigue/damage-tolerance` (P1) — NASGRO/AFGROW crack growth, FAR 25.571
- `struct/loads/environmental` (P1) — gust, maneuver, random vibration (MIL-STD-810), modal
- `struct/aeroelastic/sizing-loop` (P2) — preCICE/OpenMDAO coupling
- Compliance hooks: FAR 25.301–25.307 (loads), 25.571 (damage tolerance), 25.581 (lightning), MMPDS/CMH-17, AS9100 8.x for production

### 5.4 Flight Mechanics (Performance, Stability & Control)
- `flight/perf/mission-sizing` (P0) — Breguet, payload-range, W/S & T/W trades, pdas `FLIGHT`
- `flight/snc/stability-derivatives-avl` (P0) — static stability, neutral point, trim
- `flight/snc/handling-qualities` (P1) — MIL-STD-1797A/Cooper-Harper assessment
- `flight/sim/jsbsim-fdm` (P0) — build/trim/linearize an FDM, XML aircraft model
- `flight/sim/flightgear-visual` (P2)
- `flight/dynamics/linearization-modes` (P1) — short period/phugoid/dutch roll/spiral/roll modes
- Compliance hooks: FAR 25.143–25.253 (controllability/stability), CS-25 subpart B; flight test validation

### 5.5 GNC / Autonomy
- `gnc/optimal-control/dymos-trajectory` (P0) — launch/ascent/reentry/rendezvous optimal control
- `gnc/optimal-control/casadi-acados` (P1) — real-time NMPC
- `gnc/control/python-control-design` (P0) — PID/LQR/H∞, root locus, bode, margins
- `gnc/estimation/kalman-filter` (P1) — linear/UKF, sensor fusion
- `gnc/uav/px4-ardupilot` (P1) — firmware build, SITL, MAVLink, QGroundControl
- `gnc/space/orbit-dynamics` (P0) — poliastro/Orekit propagation, Lambert, J2
- Compliance hooks: DO-178C DAL A/B for flight-critical software; DO-331 for model-based; ARP4754A/ARP4761 for the safety case; Part 107/EASA UAS for ops

### 5.6 Avionics & Flight Software
- `avionics/do178c/planning` (P0) — PSAC, DAL determination, objectives tables (A-1…A-10)
- `avionics/do178c/verification-coverage` (P0) — requirements-based testing, MC/DC via gcov/lcov, coupling analysis
- `avionics/do254/hardware-assurance` (P1) — simple vs complex AEH, PHAC, design assurance
- `avionics/do160/environmental-qualification` (P1) — section-by-section test matrix (temp, vibration, EMC, lightning)
- `avionics/fsw/cfs-architecture` (P1) — cFE/OSAL/PSP app skeleton
- `avionics/fsw/fprime-component` (P1) — component model → code-gen → unit test
- `avionics/buses/arinc429-1553-afdx` (P2) — protocol parsing/simulation
- `avionics/hw/kicad-pcb` (P2)
- `avionics/ima/do297` (P2)
- Compliance hooks: DO-178C/ED-12C + supplements, DO-254/ED-80, DO-160G, DO-297, AC 20-115D/20-152A, AMC 20-115

### 5.7 Systems Engineering & Safety
- `sys/requirements/traceability` (P0) — SRATS → HLR → LLR → code → tests; derived requirements
- `sys/mbse/capella-sysml` (P1) — functional architecture, allocation
- `sys/mbse/aadl-osate` (P2) — architecture + error modeling (FTA/FMEA from model)
- `sys/safety/arp4761-fha-pssa-ssa` (P0) — failure conditions, DAL allocation, safety budgets
- `sys/safety/fta-fmea` (P1) — fault trees, FMECA tables, common cause analysis
- `sys/certification/certification-basis` (P0) — FAR/CS applicability, special conditions, TC/STC/TSO paths
- `sys/mdo/openmdao-trade-study` (P1) — DOE, optimization, sensitivity
- Compliance hooks: ARP4754A/B, ARP4761A, 14 CFR 25.1309 / CS-25.1309, AC 25.1309-1

### 5.8 Space Systems & Astrodynamics
- `space/orbit/poliastro-mission` (P0) — transfer design, Δv budgeting
- `space/orbit/gmat-mission-design` (P1) — full mission design, targeting/optimization
- `space/orbit/orekit-propagation` (P1) — high-fidelity propagation, TLE/SGP4
- `space/subsystems/power-thermal-budget` (P2)
- `space/fsw/cfs-fprime` (P1) — flight software on smallsats
- `space/env/radiation-debris` (P2)
- Compliance hooks: ECSS-E-ST/Q-ST series, CCSDS, NASA NPR 7150.2/8739.8, GEVS-SE/SMC-S-016 testing

### 5.9 Vehicle Design & Integration
- `design/conceptual/openvsp-geometry` (P0) — parametric model, user parameters, mass properties
- `design/conceptual/vspaero-polars` (P1)
- `design/sizing/weight-estimation` (P1) — class-I/II weight, CG envelope
- `design/mdo/aerosandbox-optimization` (P1)
- `design/reviews/pdr-cdr-package` (P2) — design review artifact checklist
- Umbrella skill: `design/full-loop/aircraft-sizing` (P0) — requirements → geometry → aero → weights → performance → iterate (ties 5.1–5.4 together)

### 5.10 Manufacturing & Quality
- `mfg/quality/as9100-qms` (P0) — clause map, audit evidence
- `mfg/quality/as9102-fai` (P0) — Forms 1–3 generation, delta FAI logic
- `mfg/quality/as9103-key-characteristics` (P2)
- `mfg/special-processes/nadcap-evidence` (P1) — parameter logging for each commodity
- `mfg/ndt/inspection-methods` (P1) — UT/RT/ET/PT/MT technique selection
- `mfg/composites/layup-cure` (P1) — ply books, cure cycle, C-scan
- `mfg/am/lpbf` (P2) — NASA MSFC-STD-3716/3717, ASTM F42
- `mfg/gdnt/asme-y14.5-tolerancing` (P1) — GD&T interpretation (essential for FAI!)
- `mfg/traceability/counterfeit-prevention` (P1) — IDEA-STD-1010, cert-of-conformance chains
- Compliance hooks: AS9100D, AS9102, AS9103, Nadcap, ASME Y14.5, ITAR/EAR export control awareness

### 5.11 Flight Test & Operations
- `ftest/planning/test-matrix` (P2) — FAA/EASA flight test guides
- `ftest/performance/envelope-expansion` (P2) — V speeds, climb, accelerate-stop
- `ftest/snc/stability-testing` (P2)
- `ftest/data/telemetry-analysis` (P2)
- `ops/uas/part107-sora` (P1) — operational risk assessment for drones

### 5.12 Cross-cutting / Foundational
- `found/units/isa-atmosphere` (P0) — ISA model, unit discipline (SL, knots, ft-lb vs SI; always state!)
- `found/numerics/convergence-verification` (P0) — grid/time convergence, Richardson, residuals
- `found/data/sources` (P0) — UIUC DB, NTRS, OpenVSP library, OpenSky, NASA software catalog
- `found/reporting/engineering-report` (P0) — margins of safety, assumptions, references
- `found/compliance/standards-map` (P0) — which standard applies to which artifact (this document, machine-readable)
- `found/export-control/itar-ear` (P1) — what an agent may/may not handle

---

## 6. What a Discipline Skill Contains (template)

Every AeroSkills leaf skill = `SKILL.md` with this structure (frontmatter: name, discipline, tools, standards, difficulty):

1. **Trigger** — "Use when: analyzing an airfoil polar / sizing an engine / running a DO-178C coverage pass…"
2. **Domain quick-reference** — the 5–10 equations/constants that matter (e.g., L=½ρV²SC_L, Breguet, ISA lapse rate, CLα ≈ 2π, DAL table). Agents must not fumble fundamentals.
3. **Workflow** — numbered steps with exact commands (e.g., `xfoil < naca2412.in`, `blockMesh && simpleFoam`, `su2_cfd inv_NACA0012.cfg`, `python -m dymos run ascent.py`).
4. **Tools & environment** — pinned versions/install paths, input-file formats, licenses (GPL/LGPL/Apache — matters for reuse), GUI-vs-CLI note.
5. **Data sources** — UIUC airfoil DB, MMPDS/CMH-17, NTRS, OpenVSP library, JSBSim aircraft XML, GMAT example missions.
6. **Pitfalls** — the classic failure modes per discipline:
   - CFD: non-converged residuals, y+ wrong for wall functions, mesh-dependence, incompressible-vs-compressible misuse, symmetry planes.
   - Structures: unit errors (Pa vs MPa), missing margin-of-safety sign convention, buckling ignored, fatigue vs static load confusion.
   - S&C: derivative sign conventions, stability-axis vs body-axis mixing, neglecting CG shift.
   - GNC: discrete-vs-continuous controller mismatch, ignoring actuator saturation/delay, frame conventions in propagation.
   - DO-178C: traceability gaps (no derived requirements), coverage computed on wrong object code, tool qualification forgotten.
   - Manufacturing: FAI "Not Complete" state until nonconformances cleared, delta-FAI trigger events, calibration/traceability gaps.
7. **Verification / sanity checks** — cross-check against a reference (NACA 0012 at Re=6M: cl≈0.82 @ 10°, Cd0≈0.0079; ISA sea level ρ=1.225 kg/m³; a=340.3 m/s; standard day lapse). "If your answer is outside the plausible band, stop and debug."
8. **Compliance & validation checks** — the standards checklist for that discipline (from §2 map) + what evidence to produce (reports, plots, coverage tables, trace matrices).
9. **Deliverables** — exact artifacts (polar plot + data file, margin table, PSAC outline, FAI Forms 1–3, coverage report).

### Example leaf skill (condensed): `aero/airfoil/xfoil-analysis`
- Trigger: user needs lift/drag polars or airfoil comparison for a design.
- Workflow: pick airfoil (UIUC DB / NACA series) → set Re/Mach → viscous analysis → cl/alpha sweep → extract polars → sanity-check against known data → deliverable: polar CSV + plot + validation note.
- Pitfalls: XFOIL overpredicts at high α / near stall; low-Re transition issues; viscous mode required (inviscid drag is meaningless); Mach limits (subsonic only).
- Compliance: none regulatory, but document validation against wind-tunnel data (e.g., NACA TR-824) per V&V practice.

### Example leaf skill (condensed): `avionics/do178c/verification-coverage`
- Trigger: need DO-178C structural coverage evidence (e.g., DAL B decision coverage).
- Workflow: identify applicable objectives (Table A-6/A-7 by DAL) → requirements-based test cases (CppUTest) → instrument with gcov → run on target-representative executable → analyze statement/decision/MC-DC → resolve unachievable code with rationale → produce coverage report + trace matrix (SRATS↔HLR↔LLR↔tests).
- Pitfalls: coverage on wrong build (debug vs release), "requirements-based" tests that don't trace, ignoring data/control coupling (§6.4.4.2), tool qualification (DO-330) for the coverage tool if not already qualified.
- Compliance: DO-178C §6.4.4, Tables A-6/A-7; AC 20-115D context; ARP4754A traceability up.

---

## 7. Cross-Cutting Skills (needed in every discipline)

- **Documentation & traceability** (P0) — every skill emits artifacts that feed certification; teach the audit mindset.
- **Units & conventions** (P0) — imperial vs SI, nautical miles, knots, flight levels; state conventions in every output.
- **Validation culture** (P0) — no simulation result is "done" until compared to a reference/sanity band.
- **Data management** — NTRS, OpenVSP library, UIUC DB, MMPDS/CMH-17 access paths.
- **Export control awareness** (P1) — ITAR/EAR; agents must flag restricted data (turbine blade alloys, missile tech, etc.).

---

## 8. Recommendations (MVP order)

1. **Build P0 set first (≈20 skills):** airfoil (XFLR5/XFOIL), AVL S&C, OpenFOAM run, SU2 shape opt, validation practice; gas-turbine cycle + CEA; CalculiX linear FEM + MMPDS allowables; JSBSim FDM; dymos trajectory; python-control; poliastro; DO-178C planning + coverage; ARP4761 FHA/PSSA/SSA; certification-basis; AS9100/AS9102; OpenVSP geometry; ISA/units; engineering-report; standards-map.
2. **Prefer CLI/text-driven tools** (OpenFOAM, SU2, AVL, XFOIL, JSBSim, dymos, CalculiX, GMAT, poliastro, OpenVSP Python API, cFS/F´) — GUI tools (OpenVSP GUI, XFLR5, FlightGear visual) are secondary or wrapped.
3. **Every skill ships with: exact commands, a validation reference, and a compliance hook.** Numbers without sanity checks are the #1 way an aerospace agent becomes useless.
4. **Keep the standards map (§2) as a machine-readable cross-reference** (YAML) so skills can cite it programmatically.
5. **Later phases:** space subsystems (P2), electric propulsion (P2), IMA/DO-297 (P2), flight test execution (P2), handling qualities (P1), composites deep (P1), NDT (P1).

---

## 9. Source Anchors (verified during research)

- MIT AeroAstro Course 16 core curriculum; Purdue AAE disciplines list; Georgia Tech AE BS; USNA Aero curriculum; standard 8-semester B.Tech aerospace plan (semester-by-semester course map).
- SU2 (LGPL-2.1, GitHub su2code/SU2); OpenVSP (NASA Open Source Agreement 1.3, NASA Ground School + AIAA 2022-0004); JSBSim (LGPL); CalculiX (GPL-2, ABAQUS-format); pyNastran; preCICE; OpenMDAO + dymos (NASA, Apache-2.0); AeroSandbox (MIT); SHARPy; GMAT (Apache-2.0); Orekit; poliastro; NASA cFS & F´ (Apache-2.0); NASA CEA; RocketPy; Cantera; PX4/ArduPilot/QGroundControl/MAVLink.
- LDRA DO-178C technical briefing (lifecycle, objectives, coverage, supplements, SOI audits); spilma DO-178C/DO-254 guide (ARP4754A/ARP4761 relationship, DAL mapping, AC 20-115D / AMC 20-115, FAR/CS Parts 23/25/27/29); SAE ARP4761A/ED-135 scope; Jama ARP4754A guide (FDAL/IDAL, AC 20-174, AMC 25.1309, ARP4754B additions); IAQG AS9102 FAI requirements & FAQ (Forms 1–3, delta FAI); AS9100D text (ISO 9001:2015 + aerospace clauses incl. 8.1.1–8.1.4, 8.4.1, 8.5.1.3); aerospace-quality ecosystem article (Nadcap commodities, parameter logging, counterfeit prevention).
