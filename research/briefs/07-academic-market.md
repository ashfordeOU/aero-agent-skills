# AeroSkills Brief 07 — The Academic Aerospace Market: Landscape, Curriculum, AI Adoption, and GTM

**Date:** 2026-08-30 · **Author:** research subagent · **Status:** verified against primary sources (ABET, ASEE, DataUSA/IPEDS, university catalogs & facts pages, MathWorks/ANSYS academic pages, ASEE/AIAA papers)

---

## 0. Executive summary

- **~100 ABET-accredited aerospace programs across ~90 U.S. institutions** (~87 institutions on the canonical list; ABET program titles include Aerospace Engineering, Aeronautical and Astronautical Engineering, Aerospace Engineering and Mechanics, Aerospace Science and Engineering, Astronautical variants). Aerospace is the **only engineering discipline where essentially every program is ABET-accredited**.
- **Students:** ~9,600 aerospace degrees awarded in 2024 (all levels, +4.1% YoY; IPEDS/DataUSA). Estimated **~30,000–35,000 total aerospace engineering students** (UG + grad) nationally — roughly 3% of all U.S. engineering students. Growth is strong: enrollments up ~18% 2020–2024 (e.g., Penn State core-course enrollment 160→250+/yr in 4 years; CU Boulder ASEN 1,138→1,285 in 2 years; UIUC UG 356→645 in a decade; Embry-Riddle campuses +60% over a decade).
- **Curriculum is remarkably standardized** across programs — the same ~12–15 core courses (aerodynamics, propulsion, structures, flight mechanics, dynamics/controls, orbital mechanics/astrodynamics, design) appear at every school. This makes a domain skill library **directly mappable to course numbers and textbook chapters** (Curtis, Anderson, Bate/Mueller/White, Raymer, etc.).
- **AI is already in the classroom, chaotically.** 88% of surveyed students use GenAI for assessments (HEPI 2025, up from 53%); engineering faculty report "reluctant engagement" — concern about cognitive offloading but acceptance of inevitability; ABET issued an AI policy (2025); aerospace-specific ASEE papers and AIAA short courses on GenAI are appearing. **Nobody yet sells a domain-grounded, curriculum-aligned agent skill library for aerospace — this is an open wedge.**
- **Licensing precedents are well-established:** MATLAB campus-wide Total Academic Headcount (TAH) licenses (~$30/student/yr at campus rates, negotiated by headcount), ANSYS teaching licenses ~$55–330/yr vs research ~$440–1,500/yr, free student software from every major vendor (ANSYS Student, Altair Student, Siemens), and free open-source teaching stacks (OpenFOAM, SU2, XFOIL, JSBSim — all agent-drivable per Brief 10). Academic buyers expect **free-for-students + professor-led adoption + modest site-license fees**.
- **Who decides:** the professor (course tools), the department head/chair (budget authority for small fees), college IT/licensing office (procurement, security review, contracts), and TAs (day-to-day usage). Prices under ~$1K/yr typically need only department sign-off; above that, college/central IT and legal get involved (RFP, security review, accessibility, data privacy).

---

## 1. Landscape: ABET-accredited aerospace programs

### 1.1 How many programs

- ABET (2026): **4,863 accredited programs at 950 institutions in 42 countries**; engineering accredited under the EAC. Aerospace programs are accredited under "Aerospace and Similarly Named Engineering Programs" program criteria.
- The canonical list (**~87 U.S. institutions** offering aerospace/aeronautical degrees) includes: Air Force Institute of Technology, ASU, Auburn, Boston University, Caltech, Cal Poly SLO, Cal Poly Pomona, CSU Long Beach, Case Western, Capitol Tech, Clarkson, Cornell, Embry-Riddle (Daytona, Prescott, Worldwide), Florida Tech, Georgia Tech, Illinois Tech, Iowa State, LeTourneau, Lehigh (MS/minor), MIT, Mississippi State, Missouri S&T, Montana State (minor), Naval Postgraduate School, New Mexico State, NC State, Ohio State, Oklahoma State, Penn State, NYU (Poly), Princeton, Purdue, RPI, Rutgers, Saint Louis, San Diego State, San Jose State, Southern New Hampshire, Stanford, Syracuse, Texas A&M, Tuskegee, USAFA, USNA, SUNY Buffalo, Alabama Huntsville, Alabama, Alaska Fairbanks (new BS), Arizona, UC Davis, UC Irvine, UCLA, UC San Diego, UCF, Cincinnati, CU Boulder, Florida, Hartford, UIUC, Kansas, Maryland, Miami, Michigan, Minnesota, Missouri, UNLV (MS only), Notre Dame, North Dakota, Oklahoma, USC, South Carolina, Tennessee Knoxville, Tennessee Space Institute, UT Arlington, UT Austin, Virginia, Washington, Wisconsin–Madison, Utah State, Virginia Tech, Washington Univ. St. Louis, West Virginia, Western Michigan, Wichita State, WPI.
- **New entrants:** NC A&T launched a B.S. in aeronautical & astronautical engineering (Fall 2025) — first new flagship program in years; minority-serving institutions are growing (Tuskegee, NC A&T) with NASA MSI partnerships.
- Counting ABET program *titles* (Aerospace Engineering; Aeronautical and Astronautical Engineering; Aerospace Engineering and Mechanics; Aerospace Science and Engineering; Aerospace Science Engineering; plus ~5 more variants) yields **~100 accredited programs** — matching the commonly cited figure of "80–100+ ABET-accredited aerospace programs."

### 1.2 Rankings and prestige tiers (US News anchor)

- **Undergraduate top-10 (US News 2023, via Wikipedia):** 1. Georgia Tech / 1. MIT (tie), 3. Michigan, 4. Purdue, 5. Caltech, 6. Stanford, 7. Princeton, 8. UIUC, 9. Maryland, 10. CU Boulder / UT Austin (tie).
- **Graduate top-10 (2016, similar composition):** MIT, Georgia Tech, Stanford, Michigan, Caltech, Purdue, UT Austin, UIUC, CU Boulder, Texas A&M / Maryland.
- Current 2025–26: Purdue UG #3 / grad #2 (tie, public #1), Georgia Tech UG #2 / grad #2 (public #1), Michigan UG #7 / grad #6, Texas A&M UG #6 / grad #5 (public), Penn State UG #15 / grad #15.
- **Tiering for GTM:** Tier 1 (MIT, Stanford, Caltech, Princeton — elite, small, research-first), Tier 2 (Georgia Tech, Purdue, Michigan, CU Boulder, UIUC, Texas A&M, Maryland, Virginia Tech, Penn State, USC — large research powerhouses with biggest enrollments), Tier 3 (regional publics: Wichita State, UAH, Oklahoma, Iowa State, NC State, Ohio State, Auburn, Mississippi State, Missouri S&T, Utah State, West Virginia, Western Michigan), Tier 4 (teaching-focused/private: Embry-Riddle, ERAU Worldwide, Capitol Tech, LeTourneau, Saint Louis, Syracuse, SNHU — highest teaching-to-software-intensity), Tier 5 (new/MSI: NC A&T, Tuskegee, UAF).

### 1.3 Student counts (verified program-level data)

| Institution | Undergrad | Grad | Total | Notes |
|---|---|---|---|---|
| Georgia Tech (AE School) | ~1,800–2,000 | ~500 | **2,300+** | Largest single AE school; 12% of nation's AE PhDs; $54.5M FY25 research |
| Purdue (AAE) | 1,240 (Fall 2024) | ~600–627 | **~1,850** | Graduated most AE degrees in US 2024 (6.56% of all AE degrees); 44–53 faculty |
| Embry-Riddle (all) | 27,302 | 5,866 | **33,168** (all campuses) | Daytona 9,092, Prescott 3,410, Worldwide 12,770+; AE-adjacent aviation-heavy |
| CU Boulder (ASEN) | ~1,100 | ~180 | **1,285** (Fall 2025 census; 1,138 in 2023) | Fast-growing; astrodynamics/space powerhouse |
| Michigan (AERO) | 503 (2023-24) | 256 | **759** | Oldest aero program in US (1914); $19M FY24 research |
| UIUC (AE) | 645 (2023) | ~300 | **~950** | Grew from 356 (2012) |
| Penn State | ~1,000+ | ~300 | ~1,300 | 250+/yr in third-year core courses (up from 160); 1 in 25 US BS holders |
| MIT (Course 16) | ~170–200 | ~250 | **~450** | Small, elite, research-driven |
| Stanford (AA) | ~200–300 | ~150 | ~350–400 | Ranked #2 overall; online + professional ed strong |
| Caltech (Ae) | ~100 | ~150 | ~250 | Grad-heavy, JPL-adjacent |
| Texas A&M | ~1,500 | ~400 | ~1,900 | #6 UG/#5 grad public |
| Others (USC, Maryland, Virginia Tech, Wichita State, UAH, NC State, Ohio State, Auburn, Iowa State, Oklahoma, Missouri S&T, Utah State, West Virginia, WMU, Mississippi State…) | ~300–1,400 each | — | — | Regional publics average ~400–800 total |

**National totals (verified):**
- Degrees awarded 2024 (CIP 14.0201, all levels): **9,596** (+4.08% YoY) — DataUSA/IPEDS.
- Degree mix: bachelor's is the most common; ~8,671 total degrees (NCES-cited figure); ASEE tracks aerospace BS ~4,500–5,000/yr.
- **Estimated total enrolled students: ~30,000–35,000** (UG ≈ 20–23K, grad ≈ 9–11K, incl. online MS students; online aero MS enrollment +35% over 5 years).
- Top degree producers 2024: Georgia Tech (544), Purdue (543), Embry-Riddle Daytona (413) — DataUSA.
- PhD: 66 U.S. universities offer aerospace PhD (PhDportal); ~12% of AE PhDs from Georgia Tech alone.

---

## 2. Curriculum structure: the courses that map to AeroSkills domains

Aerospace curricula are **standardized by ABET program criteria + a de facto national canon** (AIAA education series textbooks, industry feedback, and faculty movement between schools). Core structure (typical 120–135 credit hours):

**Common spine (every ABET program):** math (calc I–III, ODE, linear algebra), physics, chemistry, statics/dynamics, thermodynamics, fluid mechanics, materials science, programming, engineering design, capstone design.

**Aero-specific core (the AeroSkills target) — with verified course names:**

| AeroSkills domain | Representative courses (verified) |
|---|---|
| **Aerodynamics / CFD** | Purdue AAE 334 Aerodynamics + Lab; Georgia Tech AE 2020/3450 Thermo & Fluids, AE 4802 Configuration Aerodynamics & Flight Performance, AE 6353 Orbital Mechanics (grad); Michigan AEROSP 325 Aerodynamics; CU ASEN 2001/2701 Intro to Thermo & Aerodynamics, ASEN 3112 Aerodynamics; MIT 16.100 Aerodynamics; Texas A&M AERO 351 Aerodynamics; Penn State AERSP 309; Purdue AAE 412 Intro to CFD, AAE 416 Viscous Flows |
| **Propulsion** | Purdue AAE 339 Aerospace Propulsion, AAE 438 Air-Breathing Propulsion, AAE 439 Rocket Propulsion; MIT 16.50 Aerospace Propulsion, 16.004 Unified Eng: Thermodynamics & Propulsion; Michigan AEROSP 335 Aerospace Propulsion, AEROSP 536 Electric Propulsion (grad); CU ASEN 4018 Propulsion (Space); Georgia Tech AE 4450 Propulsion; UIUC AE 460 Aerodynamics & Propulsion Lab |
| **Structures & materials** | Purdue AAE 352 Structural Analysis I + Lab, AAE 454 Design of Aerospace Structures; MIT 16.20 Structural Mechanics; Michigan AEROSP 320 Aerospace Structures; CU ASEN 3111/3711 Structures; Georgia Tech AE 3120 Aerospace Structures; Texas A&M AERO 404 Aerospace Structures; Rutgers 14:650:458 Aerospace Structures |
| **Flight mechanics / dynamics** | Purdue AAE 421 Flight Dynamics & Control; MIT 16.07 Dynamics; Michigan AEROSP 341 Aircraft Dynamics, AEROSP 348 Aircraft Dyn Control, AEROSP 445 Flight Dynamics; CU ASEN 2704 Intro to Aerospace Vehicle Design & Performance; Georgia Tech AE 4220 Flight Mechanics; Notre Dame AME 40461 Flight Mechanics & Intro to Design; Texas A&M AERO 351 Flight Dynamics |
| **GNC / controls / autonomy** | Purdue AAE 364 Control System Analysis + Lab, AAE 440 Spacecraft Attitude Dynamics; MIT 16.06 Principles of Automatic Control, 16.30 Feedback Control Systems, 16.85 Design & Testing of Autonomous Vehicles; Michigan AEROSP 443/447/448 controls sequence; CU ASEN 3700 Orbital Mechanics/Attitude Dynamics & Control, ASEN 4018/5018 GNC; Georgia Tech AE 3530 Controls; Texas A&M AERO 401 Controls; UIUC AE 452/456 GNSS |
| **Orbital mechanics / astrodynamics / space systems** | Purdue AAE 432 Orbital Analysis, AAE 450 Spacecraft Design; Michigan AEROSP 347 Space Mechanics, AEROSP 548 Astrodynamics (grad); CU ASEN 3700 Orbital Mechanics, ASEN 5050 Astrodynamics (grad); Georgia Tech AE 6353 Orbital Mechanics (grad, Curtis textbook); MIT 16.83 Space Systems Engineering; USC ASTE 580 Orbital Mechanics I (Battin); SJSU AE 142 Astrodynamics |
| **Design / capstone / systems** | Purdue AAE 251 Intro to Aerospace Design, AAE 351 Aerospace Systems Design, AAE 450 Spacecraft Design, AAE 451 Aircraft Design; Georgia Tech AE 1355/2355 Design Competition, AE 1601 Intro, AE 3340 Design & Systems Engineering Methods; MIT 16.82 Flight Vehicle Engineering, 16.83/16.85 capstones; CU ASEN 2704/4012 (Spacecraft Design) + 4028 capstone; AIAA Design/Build/Fly & rocket competitions at ~200 schools |

**Standard textbooks** (skill content should cite these so agents and students speak the same language): Anderson *Fundamentals of Aerodynamics* & *Aircraft Performance and Design*; Curtis *Orbital Mechanics for Engineering Students* (used at CU, GT, most astrodynamics courses); Bate/Mueller/White *Fundamentals of Astrodynamics*; Raymer *Aircraft Design: A Conceptual Approach* (AIAA Education Series); Stevens & Lewis *Aircraft Control and Simulation*; Hill & Peterson *Mechanics and Thermodynamics of Propulsion*; AIAA Education Series (adopted for classroom use at top programs worldwide).

**Key insight for AeroSkills:** the course-to-skill mapping is stable and enumerable — a "course pack" per domain (e.g., "Aerodynamics 334 pack" at Purdue ≈ "AEROSP 325 pack" at Michigan ≈ "AE 2020 pack" at Georgia Tech) is the natural product unit. Graduate courses (AE 6353, AEROSP 548, ASEN 5050, ASTE 580) use the same canonical texts, so grad-level skills (trajectory optimization with dymos, GMAT mission design, SU2 CFD) map directly to research groups.

---

## 3. AI/LLM adoption in engineering education (2024–2026 evidence)

### 3.1 Student usage — pervasive and rising
- **88% of surveyed students use GenAI for assessments** (HEPI Student Generative AI Survey 2025, n=1,041; up from 53% the prior year).
- Survey of 1,000 college students (Jan 2023, 2 months after ChatGPT launch): **~90% had used it for homework**; 2025–26: 92% of students report using AI (Programs.com), two-thirds+ in Germany (Nature study).
- Aerospace-specific: students use LLMs for homework, reports, and code in aerodynamics/aeronautics courses — the ASEE paper "Aerospace Engineering Education in the Era of Generative AI" (Penn State, 2025, #48756) evaluated ChatGPT-4/Gemini on undergrad aero MCQs: **performance degrades as Bloom's cognitive level rises** — LLMs solve remember/understand questions but fail apply/analyze/evaluate — the exact tier where engineering homework lives. Cheating concern is real but the deeper story is assessment redesign.

### 3.2 Faculty — "reluctant engagement"
- Frontiers in Education (2026, Oklahoma State, n=16 engineering faculty focus groups): faculty adopt a posture of **reluctant engagement** — accepting AI's inevitability while worried about cognitive offloading, loss of "productive struggle," assessment integrity, and intra-team conflict; they **anticipate curricular redesign** and want institutional governance + support.
- 60% of faculty see ChatGPT as useful for writing/debugging code; 53% for extracting data from text (Frontiers 2025).
- Faculty adoption is uneven: some integrate GenAI into assignment design/feedback; others ban it (UTAUT study, 2025).

### 3.3 Institutional/policy layer
- **ABET issued "ABET Accreditation and Artificial Intelligence Technologies"** (2025) focusing on AI in QA/assessment; ABET is also releasing program criteria for AI/ML-degree programs (Oct 2025) — accreditation bodies are actively normalizing AI.
- MIT TLL "Generative AI & Your Course" resources; universities publish AI syllabus statements (Pitt, MIT); Lance Eaton's crowd-sourced syllabus policy database is widely used.
- Coding agents in education: GitHub Copilot studies in CS (SIGCSE 2025, ICER 2025) show students work more efficiently with agents but with differing process outcomes; AIAA now runs a **"Generative AI with LLMs in Aviation and Aerospace" short course** (2025) — professional signal that GenAI fluency is an expected aerospace skill.
- Purdue AAE students already do **LLM research** (AAE 497 "Large Language Model Research" special topics) — evidence that aero departments are past the debate stage.

### 3.4 What this means for AeroSkills
1. Students are **already using generic LLMs on aero homework** — badly, with wrong methods. A domain skill library that teaches the correct, textbook-aligned procedure (XFOIL for an airfoil assignment, not a hallucinated answer) is a **natural upgrade path**, and professors are looking for exactly this to channel AI use constructively.
2. **Assessment redesign** is the professor's pain: skills that scaffold "show your work," run real solvers, and produce verifiable artifacts (plots, convergence histories) fit the new assessment model.
3. No academic-specific competitor exists; generic coding-agent skills (Claude skills, etc.) don't know an airfoil from a fuselage.

---

## 4. Academic licensing models & precedents (the template for AeroSkills pricing)

### 4.1 MATLAB/Simulink — the campus-license archetype
- **Total Academic Headcount (TAH)** campus-wide license: all students/faculty/staff get MATLAB+Simulink+toolboxes at zero out-of-pocket (BU, Rochester, Tsukuba, most large schools). **Pricing is negotiated by total headcount** — public data points: University of Utah individual campus-rate student license **~$30/yr**; standard individual commercial list $940/yr; student suite $119/yr (10+ toolboxes). Vendr: academic pricing typically **50–80% below commercial**, with TAH discounts scaling by institution size.
- Dept-level licenses exist (~$400/active install reported by one dept admin); perpetual + maintenance is the classic model; MATLAB Online free 20 hrs/mo.

### 4.2 ANSYS — teaching vs research tiers (the two-tier academic template)
- **Free ANSYS Student** download for any student (workbench tools, tutorials, community); educators get free teaching resources and courseware.
- **Teaching licenses:** Purdue KB: "teaching license may only be used for student instruction… available at no cost" to the professor; UW lists **Ansys Academic Teaching (Mech, Struc, CFD) 1 CUL: $55/yr**.
- **Research licenses:** UW: **$1,500 new / $880 renewal** (1 CUL, research); UIUC campus research license **$440/yr**; Cambridge ~£144/yr; LRZ (Munich) €750/yr. Budget-code internal billing ("UW budget number only") is the norm at R1s.
- ANSYS invests heavily in academia (free software + courses + community) because **student familiarity drives career-long purchasing** — the exact funnel AeroSkills should copy.

### 4.3 Open-source in teaching — the free tier precedent
- **OpenFOAM** (GPLv3): free, industry-standard CFD, widely taught at the grad level (CU, GT, many ME/AAE depts) with university-run clusters; per Brief 10, fully agent-drivable (case-dir CLI, PyFoam).
- **SU2, XFOIL, AVL, JSBSim, OpenVSP, GMAT, OpenMDAO, dymos, CalculiX, Gmsh** — the standard undergrad teaching stack for aerodynamics/design/astrodynamics/structures, all free, all agent-drivable (Brief 10 matrix). **AeroSkills skills that script these tools are license-free to ship** and work in any lab or laptop.
- OER (open educational resources) adoption is a documented faculty preference driver (cost savings, cumulative student savings metrics) — free skill packs align with this.

### 4.4 Other academic precedents
- **Siemens DesignCenter CAD for educators** (free curriculum CAD), **Altair Student Edition** (free, .edu email), **SAS Educator Portal** (free teaching hub), COMSOL teaching licenses, Wolfram, GitHub Education (free Copilot for students/teachers) — the industry norm is **free for students, cheap for teaching, paid for research/production**.
- **AIAA student membership: $37/yr** ($27.75 with country discounts) — the price anchor for student-facing professional products.
- University procurement realities: purchases >$5–10K go through RFP/bidding; IT security review is mandatory for anything networked; FERPA/data-privacy review applies to student data; accessibility (VPAT) increasingly required; EDUCAUSE and state consortia (MEEC, etc.) negotiate contracts.

---

## 5. AeroSkills academic adoption path — realistic tiers with price points

Grounding: brief 04 established skills-marketplace pricing (free OSS lead-gen; subscriptions $9–999/mo; enterprise $2K–50K/mo) and that aerospace engineers are used to $940–50K/yr engineering software. Academia needs **much lower absolute prices + high free-touch**:

### Tier 0 — Free for students (loss leader, the funnel)
- Free student skill packs: "Aerodynamics 101" (XFOIL/airfoil analysis), "Orbital Mechanics 101" (poliastro→Orekit/GMAT basics), "Flight Dynamics 101" (JSBSim), "Structures 101" (CalculiX beam/truss).
- Free professor starter pack: course-pack template + 2 sample labs.
- **Why free:** MATLAB/ANSYS/OpenFOAM all proved students-as-funnel. Every aero student who graduates with AeroSkills muscle memory becomes an industry buyer. Cost of free tier: negligible (skills are text + open-source tool scripts).
- Institutional hook: publish to GitHub + skill marketplaces (Anthropic Skills Marketplace 85% creator split, per brief 04) for distribution; badge/verification for students ("AeroSkills-certified" lab completion) to drive engagement.

### Tier 1 — Professor adoption (~$0–500/yr per course)
- **Price point: $49–99/course pack per semester** or free-with-license ("pilot a course pack free; pay if you keep it").
- Unit of sale: **course pack** = the full skill set + lab assignments + solution-verification scripts for ONE course (e.g., "AE 334 Aerodynamics pack").
- Decision: individual professor or department chair (<$1K = department budget discretion, no RFP).
- What unlocks adoption: syllabus-ready materials, sample assignments, rubric/verification scripts, AI-use syllabus statement templates, 30-min faculty onboarding, alignment table to the school's own course numbers.

### Tier 2 — Department / course-integration license (~$500–3,000/yr per department)
- **Price point: $1,000–3,000/yr per aerospace department** (all course packs, all sections, TAs included). Benchmark vs ANSYS teaching ($55/CUL) and MATLAB TAH (~$30/student) — AeroSkills undercuts software budgets while adding the missing "how to use the tools correctly" layer.
- Included: full course-pack library, TA training, LMS integration (Canvas/Blackboard/Moodle assignment drop-ins), usage analytics, instructor support.
- Decision: department head + college IT/licensing office; funded from department teaching software budget (software fees line) — often budget-code-funded like UW's ANSYS model.

### Tier 3 — Research-group licenses (~$500–2,500/yr per group)
- **Price point: $500–2,500/yr per research group** (5–30 researchers), priced by group size; pro pack includes research-grade skills (dymos trajectory optimization, GMAT mission design, SU2/OpenFOAM CFD workflows, Python/Julia tooling, MBSE with OpenMDAO), training, priority support.
- Funded from **grant overhead/indirect costs or research group discretionary funds** (R1 aero groups run $1–55M/yr research; Purdue AAE $25M/yr; GT $54.5M — $2.5K is negligible).
- Hook: research groups generate publications & students who carry the tool into industry.

### Tier 4 — Academic site license (~$5,000–25,000/yr per institution)
- **Price point: $5K–25K/yr** for all aerospace/ME-adjacent departments at one university (all courses + research + student access), scaled by program size and headcount (mirror MathWorks TAH: negotiated by total aero students).
- Decision: college dean/associate dean + central IT + procurement (RFP above $10K) — 9–18 month sales cycle; sell through Tier 1/2 beachheads first.
- Bundles: all course packs + research packs + TA/professor training + LMS + analytics + priority support + annual curriculum-update subscription (ABET/curriculum refreshes).

### Revenue pacing (academic channel)
- Realistic 12-month: 3–5 pilot professors (Tier 1, ~$250–500), 1–2 departments (Tier 2, ~$2–5K), 1–2 research groups (Tier 3, ~$1–5K) → **~$10–25K/yr academic revenue** in year one; scale via AIAA/ASEE conference presence and course-pack virality. (Consistent with brief 04's €2–5K MRR organic median; academic channel is a foundation layer, not the primary revenue engine — industry/defense remains the money.)

---

## 6. Who decides, and what they need

| Role | Authority | Pain / motivation | What they need from AeroSkills |
|---|---|---|---|
| **Professor / course instructor** | Chooses course tools; controls syllabus, assignments, TAs | Assessment integrity under AI; grading load (250+ students/semester); students "using ChatGPT wrong"; curriculum modernization pressure; ABET student-outcomes evidence | Course-pack with syllabus-ready labs, auto-verifiable solutions, AI-use policy templates, ABET outcome mapping, 30-min setup, sample data |
| **Department head / chair** | Approves small purchases (<$1–5K); sets teaching strategy | Enrollment surges (staffing strain); software budget; industry-alignment of curriculum; faculty morale | Low-friction pricing, one-page proposal, evidence of student outcomes, references from peer schools |
| **College IT / licensing office** | Procurement, contracts, security review, LMS admin, license servers | Security review for any networked tool; FERPA; contract terms; accessibility (VPAT); budget codes | Security/compliance one-pager, data-handling statement (skills = local files; no student data leaves campus), accessible docs, standard contract (no unusual terms) |
| **Teaching assistants** | Day-to-day lab/homework operation; grading | Grading scale; students stuck at 2am; reproducing solutions | TA training pack, solution-verification scripts, FAQ, office-hours helper skills |
| **Dean / associate dean (site license)** | Budget authority for $10K+ | Enrollment growth management, "AI-ready curriculum" narrative, rankings pressure | Multi-department value case, ROI vs per-course pricing, pilot evidence |
| **Research PI / lab manager** | Group discretionary + grant funds | PhD students need reproducible toolchains; proposal competitiveness (AI/ML in proposals) | Research-grade skills, citation/license clarity (Brief 10), support SLAs, publication examples |

**Cross-cutting needs:** documentation (README + skill-level docs), worked examples with real outputs, curriculum alignment tables (their course numbers ↔ skill packs), LMS integration, accessibility, data-privacy statement (no student data upload), and an academic EULA (no commercial use at free tier; export-control note — see Brief 06).

---

## 7. Academic GTM plan (90-day / 12-month)

### Phase 0 — Foundation (Weeks 1–4)
1. Ship free student packs + 2 sample course packs on GitHub + Anthropic Skills Marketplace + SkillExchange (85/15 split, per brief 04).
2. Build the **curriculum alignment matrix** (this brief's Section 2 table expanded: course numbers at top 25 schools ↔ skill packs ↔ textbooks) — the moat and the sales asset.
3. Publish at ASEE conference + AIAA SciTech/education tracks: "AeroSkills: curriculum-aligned agent skills for aerospace education" paper/poster (the ASEE GenAI paper shows the venue accepts this exact topic).
4. Academic EULA + VPAT-lite accessibility statement + privacy one-pager.

### Phase 1 — Beachhead professors (Weeks 4–12)
5. Recruit 5–10 pilot professors: target Penn State (Coder group — already studying LLMs in aero ed), Purdue AAE (LLM research already happening), Georgia Tech, CU Boulder (ASEN), Michigan, plus one Tier-3 school each region (Wichita State, UAH, Embry-Riddle).
6. Offer: free pilot semester + $250–500 honorarium-equivalent support; deliverable: verified course-pack use in ≥1 course, testimonial + anonymized outcome data.
7. Use AIAA student branches + AIAA Design/Build/Fly + rocket teams as distribution (200+ schools; $37 student membership anchor; DBF used as capstone at many schools).

### Phase 2 — Departments & research groups (Months 3–9)
8. Convert pilots → Tier 2 department licenses ($1–3K) via department chairs; lead with "AI-ready curriculum" + ABET outcomes narrative.
9. Sell Tier 3 research packs to funded groups (R1 aero research is $1–55M/yr per school — $500–2.5K is trivial); target space/astrodynamics groups (CU, GT, Purdue, Michigan, USC, Texas A&M) where GMAT/dymos/Orekit skills shine.
10. Present at AIAA SciTech education sessions, ASEE Annual Conference, regional AIAA student conferences.

### Phase 3 — Site licenses (Months 9–18)
11. Convert 1–2 flagship institutions to Tier 4 ($5–25K/yr) as reference deals; then target the remaining top-20 programs and the state-system consortia (Maryland MEEC model, CSU system, SUNY).
12. Partner with AIAA Education Series / AIAA for co-branded course packs (AIAA already runs GenAI-in-aerospace courses); explore university bookstore/OER channels.

### 12-month KPI targets (academic channel)
- 10–15 active pilot/paid professors; 3–5 department licenses; 2–3 research groups; 1 site license in negotiation.
- 1,500+ student free-tier activations (funnel into industry pipeline).
- 1 ASEE paper + 1 AIAA presentation + 1 conference workshop.
- **$15–40K academic-channel revenue in year one** (below industry/defense, but creates the curriculum-aligned credibility that enterprise sales leverage).

---

## 8. Key numbers card (for proposals and memos)

- Programs: ~87 institutions / ~100 ABET-accredited aerospace programs
- Degrees/yr: 9,596 (2024, all levels; +4.1% YoY); top producers GT 544, Purdue 543, ERAU-DB 413
- Enrolled students: ~30–35K (UG ~20–23K, grad ~9–11K)
- Growth: enrollment +18% (2020–24); online aero MS +35% (5 yrs); Penn State core courses 160→250+/yr (4 yrs); CU ASEN 1,138→1,285 (2023→25); ERAU campuses +60% (decade)
- Student AI usage: 88% (HEPI 2025); faculty: "reluctant engagement" (Frontiers 2026)
- Licensing anchors: MATLAB TAH ~$30/student/yr; ANSYS teaching $55/yr, research $440–1,500/yr; AIAA student dues $37/yr; free student tiers at every major vendor
- AeroSkills academic pricing: free (students) → $49–99/course pack → $1–3K/department/yr → $500–2.5K/research group/yr → $5–25K/site license/yr

## 9. Sources
ABET (abet.org; ABET AI policy; program search), ASEE Profiles/By the Numbers 2023 + ASEE paper #48756 (Penn State, GenAI in aero ed), DataUSA/IPEDS CIP 14.0201 (2024), Wikipedia "List of aerospace engineering schools" + ABET article, Purdue AAE facts & enrollment pages + BoilerClasses AAE course list, Georgia Tech AE school pages + GT catalog (ae.pdf), Michigan Aero facts & figures + AEROSP bulletin, CU Boulder ASEN accreditation/enrollment data + ASEN catalog, MIT Course 16 catalog + degree chart, Texas A&M aero catalog, UIUC AE statistics, Penn State aero, Stanford AA, Caltech Aerospace, Embry-Riddle enrollment/facts, MathWorks pricing & TAH guides, Vendr MathWorks benchmark, ANSYS academic program + UW/Purdue/UIUC/Cambridge/LRZ license pages, OpenFOAM.org, HEPI Student GenAI Survey 2025, Frontiers in Education (faculty perceptions 2026; ChatGPT perceptions 2025), ABET AI policy, AIAA (student membership dues, Design/Build/Fly, GenAI short course, Education Series), HEP "Understanding the Procurement Process in Higher Education" (2025), NCES/NCSES NSF doctorate data, research.com online-aero-MS statistics, collegefactual aerospace degree counts, briefs 04 (GTM/pricing) and 10 (tool licensing) for cross-references.
