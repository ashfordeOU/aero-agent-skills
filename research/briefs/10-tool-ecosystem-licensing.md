# AeroSkills Brief 10 — Open-Source Aerospace Tool Ecosystem, Licensing, and Agent Usability

**Date:** 2026-08-30 · **Author:** research subagent · **Status:** verified against primary sources (GitHub, project sites, vendor licensing pages)

---

## 0. Executive summary

- Every tool AeroSkills will reference is **legal to script from a skill**. A skill is text (instructions); it is not a derivative work of any tool, so copyleft (GPL/LGPL) never attaches to the skill itself. The boundary rule: **skills may reference, invoke, and script tools via CLI/API; they must not vendor tool source code or modified binaries into the skill library.**
- License families in the 13-tool set: **GPLv3** (OpenFOAM), **LGPL 2.1** (SU2, JSBSim, pyNastran), **GPLv2+** (XFOIL, AVL, CalculiX, Gmsh), **Apache-2.0** (GMAT, dymos, OpenMDAO, cFS, F´, Orekit, Open Space Toolkit), **MIT** (poliastro — but **archived**), **NOSA 1.3** (OpenVSP — NASA-specific, not OSI-approved).
- Maintenance status is a bigger risk than licensing: **poliastro is archived** (last release 0.17.0, Jul 2022, Python <3.11); everything else is active, with OpenMDAO (v3.45.0, Jul 2026), dymos (v1.15.1, Mar 2026), F´ (11.7k★), OpenFOAM (v14/v2512), GMAT (R2026a), OpenVSP (3.51.3), CalculiX (2.23), JSBSim (v1.3.1) all releasing within the last ~12 months.
- **Agent-usability verdict:** 13 of 13 open-source tools are drivable headlessly by an agent today (CLI or Python API). Commercial tools are drivable too — MATLAB `-batch`, Fluent `.jou` journaling, STAR-CCM+ Java macros, Abaqus input decks, Nastran bulk data — **but only under the user's paid license**, and Abaqus's license terms explicitly restrict "services that do not add value attributable to the intervention of specific human skills."

---

## 1. Tool-by-tool matrix — open-source tools

| Tool | License | Stars | Latest release | Maintenance | Agent interface | Headless? |
|---|---|---|---|---|---|---|
| OpenFOAM | GPL v3 | 2,214 (Foundation dev repo) | Foundation **v14** (2025); ESI-OpenCFD **v2512** (Dec 2025) | Very active, 2 forks, huge user base | Case-dir CLI (`blockMesh`, `snappyHexMesh`, `simpleFoam`, `foamRun`), PyFoam, casefoam | Yes |
| SU2 | LGPL 2.1 | 1,787 | **v8.5.0 "Harrier"** (2025) | Very active (19.9k commits) | CLI (`SU2_CFD`), SU2_PY, `pysu2` (SWIG) | Yes |
| JSBSim | LGPL 2.1 (Python module LGPL; MATLAB S-fn BSD; Unreal MIT) | 2,211 | **v1.3.1** | Active; NASA-verified 6DoF FDM | `JSBSim --script=…` CLI, `pip install jsbsim` | Yes |
| AVL | GPL v2+ (Drela) | n/a (mirrors) | 3.36/3.52 (Drela; static) | Dormant upstream, stable | Interactive stdin-driven Fortran CLI; wrappers: AVLWrapper (GPL-3), JAVL (MIT, Julia) | Yes (stdin piping) |
| XFOIL | GPL v2+ (Drela) | n/a (mirrors) | **6.996** (Jan 2026) | Maintained by Drela/Youngren | Interactive stdin-driven CLI (`xfoil < input`) | Yes (stdin piping) |
| OpenVSP | **NOSA 1.3** | 821 | **3.51.3** (Aug 2026) | Active, NASA Langley + community | C++ API, SWIG **Python API** (`vsp`), VSPAERO; headless build flags | Yes (with caveats) |
| poliastro | MIT | 987 | 0.17.0 (Jul 2022) | **ARCHIVED** (unmaintained.tech) | Pure Python (`pip install poliastro`) | Yes — but do not build new skills on it |
| GMAT | Apache 2.0 | 91 (new official `nasa/GMAT` 2026 repo) | **R2026a** (Apr 2026) on SourceForge | Active (NASA/industry) | GUI + custom `.script` language; `gmat-run` Python driver | Yes |
| dymos | Apache 2.0 | 293 | **1.15.1** (Mar 2026) | Very active (OpenMDAO org) | Pure Python (`pip install dymos`) | Yes |
| CalculiX | GPL v2+ | n/a (dhondt.de) | **2.23** (Nov 2025) | Active (2 releases/yr cadence) | `ccx -i input.inp` CLI (Abaqus-like input); `cgx` GUI pre/post | Yes (solver) |
| cFS | Apache 2.0 | 1,476 | Bundle **v7.0.1** (2026, "Draco") | Active (NASA GSFC release process) | `make`/CMake build; headless Linux/QEMU targets; ground systems | Yes |
| F´ (F Prime) | Apache 2.0 | **11,691** | v3.5.x line (devel active) | Very active (JPL) | `fprime-util` (generate/build), `fprime-gds -g none`, `fprime-cli` | Yes |
| OpenMDAO | Apache 2.0 | 753 | **3.45.0** (Jul 2026) | Very active (NASA Glenn) | Pure Python (`pip install openmdao`), pyOptSparse/IPOPT/SNOPT drivers | Yes |

Supporting ecosystem tools every skill set should also know:

| Tool | License | Notes |
|---|---|---|
| Gmsh | GPL v2+ | The CAD→mesh bridge: Python API, imports STEP/IGES via OpenCASCADE, exports .msh/.su2/.cgns |
| ParaView | BSD-3-Clause (1,643★) | Post-processing; `pvpython` headless scripting; reads VTK/VTU/CGNS |
| VTK | BSD-3-Clause (3,111★) | Visualization toolkit; format used by most CFD post tools |
| CGNS | Open standard (BSD-style lib) | HDF5-based CFD interchange; AIAA recommended practice; NASA/Boeing heritage; read/write by Fluent, SU2, OpenFOAM (cgnsToFoam) |
| pyNastran | LGPL v3 | Python reader/writer for Nastran BDF/OP2 — agent path to commercial Nastran files |
| Orekit | Apache 2.0 (290★) | **The healthy successor to poliastro**: Java + Python wrapper, Airbus/ESA/CNES-backed, v13.1.x (2026) |

---

## 2. License analysis — what each permits for skill-writing and embedding

### Core principle (applies to every tool below)
A skill = documentation + invocation instructions. Running a tool as a separate process (`subprocess`, shell), writing its input files, and parsing its outputs is **aggregation, not a derivative work** (FSF FAQ; established practice — e.g., PyFoam's own license note that it works "strictly from the outside… without compiled parts or being linked to OpenFOAM"). Therefore: **no copyleft implication for AeroSkills itself, regardless of tool license.** Constraints only appear if a skill *ships* tool code:

- **GPL v3 / GPL v2+ tools (OpenFOAM, XFOIL, AVL, CalculiX, Gmsh):** If AeroSkills distributed *modified* source of these tools, the modifications would have to be GPL. Skills must therefore **never vendor GPL source or binaries**; they reference and script the user's installed tool. Fine: documenting commands, providing case/config templates *written by us* (a config file is data, not a derivative of the solver). Note OpenFOAM's ESI branch is GPLv3 with a trademark (OpenCFD owns the "OpenFOAM" mark — use "OpenFOAM®" attribution in public materials); CalculiX GPLv2 is why commercial pre-processors ship their own wrappers but never link ccx.
- **LGPL 2.1 tools (SU2, JSBSim):** Weak copyleft. Proprietary code may link/embed them (with relink obligations); scripting is entirely unrestricted. SU2 explicitly supports commercial embedding; JSBSim is used inside commercial flight simulators (FlightGear, Unreal).
- **Apache 2.0 tools (GMAT, dymos, OpenMDAO, cFS, F´, Orekit):** Permissive + explicit patent grant + "no trademark" clause. Skills can even *contain derivative code* (e.g., a dymos trajectory script) as long as attribution/NOTICE is kept when redistributing derived code. Lowest-friction family.
- **MIT (poliastro):** Keep copyright notice; otherwise unrestricted.
- **NOSA 1.3 (OpenVSP):** NASA Open Source Agreement — **not OSI-approved**, NASA-specific terms, US Government as intended third-party beneficiary, "User Registration Requested" (informational). Scripting/referencing is fine; embedding OpenVSP source in a distributed product may raise compliance questions for corporate legal. Prefer referencing binaries/build instructions.
- **NASA open-source + export:** All NASA code here (OpenFOAM Foundation, cFS, F´, GMAT, OpenMDAO, dymos, OpenVSP) carries NASA docket numbers and standard open-source terms; no ITAR/EAR restriction on the code itself (users are responsible for their own compliance context).

---

## 3. Commercial tools aerospace actually uses — licensing reality and the skill boundary

| Tool | Vendor | Licensing reality (2026) | Agent drivability | Skill boundary |
|---|---|---|---|---|
| MATLAB/Simulink | MathWorks | Proprietary, per-seat; Standard (quote-only, ~$2–5k/yr typical w/ toolboxes), Academic, Student (~$149), Home (~$149), Startup; annual or perpetual + maintenance | **Good:** `matlab -batch "script"` headless, MATLAB Engine API for Python | Skills may reference; runs only under user's license; never redistribute toolbox code; codegen toolboxes have their own terms |
| ANSYS Fluent | ANSYS | Proprietary; capability tiers **Pro/Premium/Enterprise**; HPC/token licensing; academic seats | **Good:** `.jou` journal files, `fluent 3d -g -i run.jou -t4` batch; Python scripting in Workbench | Reference only; journal templates we write are ours; requires licensed install + license server |
| CATIA | Dassault Systèmes | Proprietary; entry seat **~$7,560/yr** (subscription) or perpetual + maintenance; 3DEXPERIENCE platform | **Poor:** EKL/CAA/VBA automation exists but GUI-bound, Windows desktop, no real headless mode | Reference only; native 3DXML proprietary — exchange via **STEP AP242**; CGM kernel not externally accessible |
| NX | Siemens | Proprietary; role-based **~$9,000/seat** + ~20%/yr maintenance; token-based options; cloud tiers from $119–$750/mo | **Fair:** NX Open (Python, .NET, Java, C/C++), journal recording/playback | Reference only; journal files are user-authored text |
| SolidWorks | Dassault Systèmes | Proprietary; **$2,820–$4,716/yr** (Standard→Premium); COM-based API (VBA/C#/C++), Windows desktop | **Poor–fair:** COM automation possible (community MCP servers exist) but requires a running GUI session | Reference only; API access requires active subscription; COM desktop automation is fragile for agents |
| Abaqus | Dassault Systèmes (SIMULIA) | Proprietary; **~$17k/yr lease, ~$37k purchase + ~$8.5k/yr maintenance**; ULM token licensing | **Good:** text `.inp` input decks (CalculiX-compatible subset), Python scripting (`abaqus cae noGUI`), batch jobs | **⚠ Critical clause:** LPT forbids using the software to "develop software code for general distribution" or "services that do not add value attributable to the intervention of specific human skills" — an agent offering automated Abaqus SaaS without licensed human-engineered value-add is contractually risky. Skills reference it for users with licenses; do not build a "free Abaqus service" skill |
| NASTRAN (MSC / NX / Simcenter) | MSC (Cadence) / Siemens | Proprietary; **MSC Nastran ~$18k/yr**; NX/Simcenter Nastran ~$660/mo (Femap bundle); text bulk-data input | **Good:** `.bdf`/`.dat` are plain text; `nastran input.dat` batch; **pyNastran (LGPL) automates file generation/parsing** | Reference only; the *format* is open de facto — pyNastran can generate models an agent runs under license |
| STAR-CCM+ | Siemens | Proprietary; perpetual/time/token ("Power") licensing; academic tiers | **Good:** **Java macro automation**, `starccm+ -batch -macro run.java` | Reference only; macros are user-authored |

### The skill boundary (open vs commercial), stated plainly
1. **Skills are allowed to reference and script any tool, open or commercial**, provided the user has a lawful install/license. This is how every engineering consultancy and vendor's own scripting docs work.
2. AeroSkills must never: redistribute vendor binaries, ship license files/keys, bypass licensing, or reproduce copyrighted manuals/UI text.
3. Commercial tools make AeroSkills **environment-dependent** — skills should gate on "is the binary/license present?" and fall back to open alternatives (Fluent→SU2/OpenFOAM; Abaqus→CalculiX; Nastran→pyNastran+CalculiX; MATLAB→Python/Octave; CATIA/NX/SW→OpenVSP/Gmsh/FreeCAD) when not.
4. Abaqus EULA is the one genuine legal tripwire for *agent-mediated* use (human-skill-value clause); treat Fluent/STAR-CCM+/Nastran journal/macro automation as normal licensed scripting.

---

## 4. How the tools connect — file formats and canonical workflows

### Formats (all open, freely generated/parsed by skills)
- **STEP (ISO 10303, AP203/AP214/AP242):** the neutral CAD exchange standard; AP242 carries PMI. CATIA/NX/SolidWorks all export it; Gmsh and OpenVSP import it. This is the seam where commercial CAD hands geometry to open meshing.
- **STL:** tessellated triangles; the workhorse for OpenFOAM (`snappyHexMesh`), 3D printing, and quick geometry exchange. No topology — watertight meshes required.
- **CGNS:** HDF5-based CFD data standard (AIAA recommended practice R-101A-2005); grid + solution + BCs in one self-describing file; supported by SU2 (read/write), Fluent/CFX, OpenFOAM (via `cgnsToFoam`/`foamToCGNS`), ParaView.
- **VTK/VTU (XML):** post-processing standard; ParaView native; OpenFOAM converts via `foamToVTK`; SU2/CalculiX write VTK directly.
- **CSV:** the lingua franca for polars (XFOIL/AVL `*.pol`, JSBSim output), trajectory tables, optimizer histories; every tool above can emit it.
- **Tool-native:** SU2 `.su2` mesh/config, OpenFOAM `polyMesh` + `dict` cases, CalculiX/Abaqus `.inp`, Nastran `.bdf`, XFOIL/AVL `.dat`/`.avl`/`.run`, JSBSim XML (`aircraft/*.xml`, `systems/*.xml`), GMAT `.script`, OpenVSP `.vsp3`, dymos/OpenMDAO (Python objects → CSV/NETCDF).

### Canonical workflows
1. **CAD → Mesh → CFD → Post**
   CATIA/NX/SolidWorks (or OpenVSP) → **STEP/STL** → **Gmsh** (STEP import via OpenCASCADE → tetrahedral/prismatic mesh) or OpenFOAM `snappyHexMesh` (STL) → **SU2_CFD / OpenFOAM / Fluent** (read CGNS or native mesh) → **VTK** → **ParaView** (`pvpython` headless) → CSV of forces/polars. CalculiX/Abaqus/Nastran slot in at the same point for structural FEA on the same geometry.
2. **Trajectory → GNC → Flight software**
   **dymos** (optimal control, OpenMDAO) or **GMAT** (mission design) or poliastro/Orekit (orbit propagation) → trajectory tables (CSV/SPK) → **JSBSim** (6DoF dynamics with aircraft XML models, aerodynamics from XFOIL/AVL polars) → implement GNC on **F´ or cFS** (headless build → ground system commanding via `fprime-cli` / cFS ground tools).
3. **MDAO loops:** **OpenMDAO** orchestrates any of the above as components (SU2 has a first-class OpenMDAO wrapper; pyNastran+CalculiX cover structures); dymos adds optimal control; gradients from SU2 adjoint or OpenMDAO's analytic derivatives.
4. **FSI:** preCICE couples CalculiX ↔ OpenFOAM/SU2.

---

## 5. What each tool's skill must know (installation, version quirks, failure modes)

- **OpenFOAM:** two incompatible-ish forks — Foundation (v14, `openfoam.org`, annual, sequential numbers) vs ESI-OpenCFD (v2512, `openfoam.com`, year-month, industry standard, owns trademark). Dictionary syntax differs between forks/versions (pre-1912 `divSchemes` etc.). Install: Ubuntu `apt`/`openfoam.org` tarball or `brew`/Docker (container is the reliable path on macOS). Failure modes: missing `0/` field files, patch names not matching `boundaryField`, wrong `fvSolution` solvers → diverge, decomposition with wrong `decomposeParDict`, running from wrong directory (must be case root). Always `foamCleanTutorials`-style cleanup before reruns; check `log.simpleFoam` residual behavior.
- **SU2:** config-file driven; v7→v8 broke many config keys (e.g., `MATH_PROBLEM`, marker syntax); use the tutorial configs as templates, not memory. Failure modes: NaN at high CFL on bad meshes (lower `CFL_NUMBER`), mixed element meshes need `MESH_FORMAT=SU2` or CGNS, missing `MARKER_PLOT`/`MARKER_MONITORING`. `pysu2` requires building with `-Denable-pywrapper=true` — ship the CLI-only path first.
- **JSBSim:** XML model files are strict (XSD-validated); `pip install jsbsim` wheels include aircraft data; `--script`, `--end`, `--logdirectivefile` CLI. Failure modes: missing `aircraft/`/`systems/` paths (use `get_default_root_dir()`), unit mismatch (feet vs meters — always set `units`), script file references to non-existent properties silently zero-force.
- **AVL/XFOIL:** interactive menus over stdin — skills must pipe full command scripts (`xfoil <<EOF … EOF`) and know the exact command names (`OPER`, `ALFA`, `PACC`, `PSAV`); version differences: XFOIL 6.99 vs 6.996 (2026) minor. Failure modes: XFOIL convergence near stall (increase `N`/`ITER`), AVL file format is whitespace-exact (never reformat `.avl`), non-dimensional vs dimensional confusion (AVL works in normalized units).
- **OpenVSP:** NOSA + registration; install via installer (needs X11 on Linux for GUI); Python API requires SWIG-built `vsp` module (or `vspapi` from the installer on some platforms); headless build with `VSP_NO_GRAPHICS`. Failure modes: geometry not watertight → VSPAERO/SURFACES fail; file version incompatibilities (.vsp3); GUI-first design means agent skills should use the Python API for param sweeps.
- **poliastro:** **archived** — pin skills to 0.17.0, note Python <3.11 constraint, and prefer **Orekit (Python wrapper)** for new astrodynamics work.
- **GMAT:** script language is its own DSL; run headless with the GUI binary's `-s script.gmat` (or `gmat-run`); needs SPICE kernels + ephemeris files (downloads are large); version differences R2022a→R2026a; failure modes: missing `data/` paths, coordinate-frame typos, solvers (SNOPT via plugin is not in the open build — use built-in `VNS`/`PSOPT` or NLP).
- **dymos/OpenMDAO:** pure pip installs; pin versions (API changes between OpenMDAO 3.x minors); failure modes: transcription grid too coarse → large defects, optimizer scaling (set `scaler`/`adder`), driver not converging (switch IPOPT↔SLSQP), `setup` ordering; MPI/PETSc paths need pixi/conda.
- **CalculiX:** `ccx` is a plain CLI — `ccx -i jobname` (no extension); input is Abaqus-*like* but not identical (no `*Part` assembly, `*INCLUDE` supported, `*USER MATERIAL` needs compile); install via apt/brew/Windows (bConverged). Failure modes: contact non-convergence (use `*CONTACT PAIR` + penalty), element type restrictions, SPOOLES/PARDISO solver selection, results in `.frd` (read by cgx/ParaView via converter).
- **cFS:** build via `make`/CMake with submodules (cFE, OSAL, PSP); run on Linux native or QEMU; the bundle is "lab apps" — **not a flight distribution**; commanding via cFS Ground System or COSMOS; failure modes: submodule checkout, toolchain flags for cross-compile, `targets.cmake` config errors.
- **F´:** `pip install fprime-tools`, then `fprime-util new --project`, `generate`, `build`; GDS: `fprime-gds -g none` (headless) + `fprime-cli` for commands/telemetry; Python 3.8+, CMake 3.16+, compilers; failure modes: virtualenv not activated (tools vanish), CMake cache staleness (`fprime-util purge`), dictionary/version mismatch between binary and GDS.
- **GMAT/cFS/F´ common:** NASA release cadence is slow and scripted — check for new dockets before promising "latest".

---

## 6. Agent-usability ranking (can an AI agent drive it today?)

**Tier A — fully headless, native automation, ideal skill targets (open source):**
1. **dymos** — pure Python, pip-installable, deterministic.
2. **OpenMDAO** — pure Python; the orchestration hub for everything else.
3. **JSBSim** — `pip install jsbsim` + CLI; deterministic batch sims.
4. **SU2** — CLI config-driven + SU2_PY optimization scripts; headless.
5. **OpenFOAM** — fully case-driven CLI; PyFoam/casefoam for automation; heavy but agent-friendly (containers).
6. **CalculiX (ccx)** — single-binary CLI; trivial to drive.
7. **XFOIL / AVL** — stdin-scripted interactive CLIs; very agent-friendly with canned command sequences.
8. **GMAT** — script language + `gmat-run` Python driver; some env setup (SPICE).
9. **F´** — `fprime-util`/`fprime-cli` make build→run→command fully scriptable.
10. **Gmsh** — Python API; the meshing bridge.
11. **ParaView** — `pvpython` headless post-processing.
12. **cFS** — build + run headless on Linux/QEMU; needs ground-system plumbing.
13. **OpenVSP** — Python API exists but GUI-centric culture + SWIG build friction; **Tier A−**.
14. **poliastro** — trivially scriptable but archived; only for legacy/teaching skills.

**Tier B — drivable under license, still headless-capable (commercial):**
MATLAB (`-batch` + Engine), ANSYS Fluent (`.jou` batch), STAR-CCM+ (Java macros), Abaqus (input deck + Python), Nastran (bulk data + pyNastran).

**Tier C — GUI-bound or desktop-fragile (commercial CAD):**
SolidWorks (COM, needs GUI session), CATIA (CAA/VBA, Windows desktop), NX (journaling works but heavyweight). Agents can automate these via their APIs on a licensed workstation, but expect brittle, GUI-session-dependent runs; prefer STEP-based handoff to open tools where the goal is analysis rather than CAD authoring.

---

## 7. Recommendations for AeroSkills

1. **License posture:** Open-source tools first, always. Mark every skill with the tool's license and an "install prerequisite" gate. Never vendor GPL/NOSA source into the skill repo.
2. **Interop layer skills are the highest value:** STEP→Gmsh→mesh conversion, CGNS read/write, VTK→ParaView rendering, CSV schema conventions — these glue the whole ecosystem and touch zero license problems.
3. **Watch maintenance risk:** build the astrodynamics skill set on **Orekit** (Apache-2.0, active) or **dymos**, not poliastro.
4. **Commercial skills:** reference-only, gated on license presence, with open fallbacks documented (Fluent→SU2, Abaqus→CalculiX, Nastran→pyNastran/CalculiX, MATLAB→Octave/Python).
5. **Abaqus caveat:** keep agent-mediated Abaqus use inside the user's licensed engineering workflow; do not ship a skill that implies unattended Abaqus service provision.
6. **Version pinning:** every skill should pin the tool version it was validated against (OpenFOAM fork+version; SU2 ≥8.x; GMAT R20xx; XFOIL 6.99+/6.996; OpenVSP 3.5x) and note migration deltas.

---

## Sources (key receipts)
- GitHub: OpenFOAM/OpenFOAM-dev (GPLv3, 2,214★), su2code/SU2 (LGPL-2.1, 1,787★, v8.5.0), JSBSim-Team/jsbsim (LGPL-2.1, 2,211★, v1.3.1), OpenVSP/OpenVSP (NOSA, 821★, 3.51.3), poliastro/poliastro (MIT, 987★, archived), nasa/GMAT (Apache-2.0), OpenMDAO/dymos (Apache-2.0, 293★, 1.15.1), nasa/cFS (Apache-2.0, 1,476★, v7.0.1), nasa/fprime (Apache-2.0, 11,691★), OpenMDAO/OpenMDAO (Apache-2.0, 753★, 3.45.0), Kitware/ParaView (BSD-3, 1,643★), CS-SI/Orekit (Apache-2.0, 290★)
- dhondt.de (CalculiX 2.23, GPLv2), web.mit.edu/drela (XFOIL 6.996 GPL, AVL), openfoam.com (GPLv3 + trademark), openfoam.org (v14), su2code.github.io (LGPL 2.1), openvsp.org (NOSA 1.3 text), gmatcentral.org/SourceForge (R2026a), cgns.org (standard), gmsh.info (GPLv2+, Python API), pyNastran PyPI (LGPLv3)
- Vendor pricing/licensing: mathworks.com/pricing-licensing, trimech.com (CATIA $7,560/yr), worquick.com (NX ~$9k/seat), solidworks.com (Design $2,820–4,716/yr), fidelisfea.com (Abaqus $17k/yr, $37k purchase), cadguide.tools (MSC Nastran $18k/yr), 3ds.com Abaqus 2025 LPT (human-skill-value clause), cfdland.com (Fluent journaling + Pro/Premium/Enterprise), volupe.com (STAR-CCM+ licensing), supergood.ai (SolidWorks API report card)
