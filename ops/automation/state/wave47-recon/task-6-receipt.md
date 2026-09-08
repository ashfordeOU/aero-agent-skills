# WAVE-47 CROSS-CUTTING EXTENSION PROBE RECEIPT (task-6, whole-family FRESH at HEAD)

- Repo: the local AeroSkills repo at ~/AeroSkills, git HEAD `a4ae6d1e` (Wave-47:
  close-out must auto-update products-state (FIX)), verified via
  `git log --oneline -1`. Working tree clean apart from untracked wave-47 recon
  receipts (this probe writes nothing else).
- Scope: ENTIRE cross-cutting family, 56 leaves, probed FRESH at wave-47 HEAD.
  Read-only probe: no writes to skills/, eval/, standards-map.yaml, scripts/, or
  any brief. One write only: this receipt (ops/automation/state/wave47-recon/).
- Doctrine (wave47-brief.md): cross-cutting is a SATURATED family whose wave-46
  whole-family NO_CANDIDATES receipt STANDS; this run is the pool-drop EXTENSION
  probe permitted once the viable pool drops (wave-47 primary pool = 8 GO, below
  the ~12 viability line). Wave-45 precedent under the same rule yielded
  fir-bandpass-bandstop-filter-design; wave-46 extension then closed the family
  at NO_CANDIDATES and stated: re-probe only if a GENUINELY NEW SEAM appears that
  the wave-46 receipt never adjudicated.
- Wave-46 receipt read first (ops/automation/state/wave46-recon/task-10-
  receipt.md, NO_CANDIDATES at wave-46 HEAD 45931c16, ~12:07 UTC): 1 GO + 32
  wave-45 decline rows re-verified FRESH, seams F1-F9 adjudicated, closed-vein
  inventory. Wave-45 extension receipt (task-11) also on disk. Both stand below.
- PROOF THE FAMILY IS UNCHANGED SINCE WAVE-46:
  `git log --oneline 45931c16..HEAD -- skills/cross-cutting/` returns EMPTY.
  Wave-46 added leaves only to FM/AV/PROP/GNC/VD/STRUCT; commits since wave-46
  HEAD (a544f421 ops brief, a4ae6d1e ops fix) touch no skill leaf. Every wave-46
  decline row therefore keeps its premise; none is re-litigated below. This probe
  re-ran the family census FRESH and hunted only seams no wave-44/45/46 receipt
  ever adjudicated (keyword sweep over all three receipt sets = 0 hits for every
  seam keyword below before this probe named them).

## Family census (FRESH at HEAD a4ae6d1e)

`find skills/cross-cutting -mindepth 3 -name SKILL.md` = 56 leaves:
- data-sources (1): aeronautical-data-sources
- documentation (2): engineering-margins, engineering-report
- export-control (1): export-control-awareness
- numerics (38): bandpass-bandstop-filter-design, chi-square-goodness-of-fit,
  complex-number-algebra, confidence-interval-estimation, convergence-verification,
  cross-correlation-analysis, descriptive-statistics, digital-filter-design,
  eigenvalue-decomposition, exact-binomial-test, fast-fourier-transform,
  finite-difference-derivatives, fir-bandpass-bandstop-filter-design,
  fir-filter-design, fisher-exact-test, grubbs-outlier-test, hypothesis-testing,
  information-entropy, interpolation, kruskal-wallis-test, least-squares-regression,
  matrix-operations, monte-carlo-sampling, multiple-linear-regression,
  numerical-integration, ode-solvers, optimization-algorithms,
  poisson-confidence-interval, power-analysis, power-spectral-density,
  probability-distributions, proportion-confidence-interval, quaternion-algebra,
  rank-based-hypothesis-testing, root-finding, runs-test,
  singular-value-decomposition, uncertainty-propagation
- sep2640 (3): skill-authoring, skill-delivery, skill-evaluation
- tolerancing (5): datum-reference-frames, fastener-position-tolerance-calc,
  gdandt-basics, position-tolerance-calc, tolerance-stackup
- units-atmos (6): airspeed-conversion, density-altitude, dimensional-analysis,
  isa-atmosphere, temperature-conversion, unit-conversion
- Total 1+2+1+38+3+5+6 = 56. Router parity FRESH: `grep -c '^| cross-cutting/'`
  in the family router = 56 rows = 56 leaves (leaf count and router rows both
  56).
- Corpus baseline FRESH: eval/hit1-corpus.yaml = 1286 tasks (1286/1286 task
  blocks carry expected_skill; 635 unique skills). Cross-cutting targets: 112
  tasks over all 56 leaves, per-leaf min = max = 2 (zero leaves below 2, zero
  orphan rows).

## Verdict

NO_CANDIDATES. The wave-46 whole-family receipt stands (family byte-unchanged
since, git-log proof above), and the FRESH seam hunt this run found NO genuinely
new seam that clears the GO gate: every candidate seam below is either owned at
HEAD, or carries zero corpus demand with no documented empty cell and no adjacent
corpus vocabulary (the exact test the wave-45 GO passed and wave-46 F5 McNemar
failed), or collides with domain-owned vocabulary. No GO under the
receipts-over-lists doctrine.

## Fresh seams probed this run (each previously unadjudicated by any wave-44/45/46 CC receipt)

### S1. Tukey HSD / ANOVA post-hoc multiple-comparison procedures - DECLINE

(a) Zero-owner grep FRESH, whole skills/ tree (SKILL.md + logic): `tukey` /
`bonferroni` / `dunnett` / `multiple comparison` = 0 computation hits anywhere.
The only `post-hoc` hits are semantically unrelated usage: power-analysis
SKILL.md line 178 ("Treating power as a post-hoc verdict: this leaf plans and
reports...") and gnc-autonomy cramer-rao-lower-bound lines 37/162/191 (post-hoc
consistency metric of filter runs). No leaf reduces the studentized-range
statistic or applies any multiplicity correction. Genuinely unowned.
(b) Sibling fence (quoted): hypothesis-testing description: "...the one-sample
and two-sample Student t tests (pooled and Welch), the paired t test, the
two-variance F test, the chi-square test of independence, and the one-way ANOVA
F test, computing each statistic, its degrees of freedom, and its p-value from
the incomplete beta and gamma functions and returning the reject-null or
fail-to-reject verdict at a stated significance level." Router bullet 189:
"Significance test questions (t test, Welch, paired t, ANOVA, F variance test,
chi-square independence, p-value verdicts) route to the numerics
hypothesis-testing sub-skill." The fence stops at the GLOBAL ANOVA F verdict;
no sibling documents a missing post-hoc cell (contrast the wave-45 FIR cell,
which the family's own router guidance documented as missing).
(c) Standards-map: map-able under the numerics convention (naca-tr-824,
reference-only: true, exactly as every numerics leaf carries at HEAD), so the
map is not the binding constraint.
(d) Anchor: Tukey's HSD has a published deterministic closed form
(HSD = q_{alpha}(k, df) x sqrt(MS_within/n) against the studentized-range
distribution; critical q tables in standard texts), so an anchor exists.
(e) Corpus demand FRESH: tukey = 2 tasks, BOTH the Cooley-Tukey FFT decomposition
routing to cross-cutting/numerics/fast-fourier-transform (fft1/fft2) - zero
HSD usage. post-hoc 0, post hoc 0, bonferroni 0, dunnett 0, multiple comparison
0, holm 0. No wordable Hit@1 query distinct from existing corpus tasks can be
worded that the router would not send to hypothesis-testing (one-way ANOVA F) or
to the manufacturing-quality gage-rr-anova domain owner of the two-way/ANOVA
vein.
Decline: identical class to wave-46 F5 (McNemar) - genuinely unowned clean
closed form, but zero corpus demand, no documented empty cell, and the ANOVA
vein is owned on both the cross-cutting side (hypothesis-testing, global F) and
the domain side (manufacturing-quality gage-rr-anova). Doctrine-consistent
decline.

### S2. Polynomial regression (univariate OLS in polynomial basis) - DECLINE

(a) Zero-owner grep FRESH: `polyfit` 0, `vandermonde` 0, `polynomial regress` 0
tree-wide. But `design matrix` is NOT unowned: multiple-linear-regression
SKILL.md line 41 states "Normal equations: (X^T X) b = X^T y, where X is the
design matrix with..." and vehicle-design/mdo/surrogate-modeling line 54 owns
the quadratic response surface ("with Phi the n by m design matrix of..."). The
linear-model design-matrix vein is owned; a polynomial-basis variant is a
re-parameterization of the owned normal-equations solver.
(b) Sibling fence (quoted): least-squares-regression description: "fit a
straight line to paired measurements by ordinary least squares: compute the
slope and intercept of the best fit, the residual standard deviation, and the
coefficient of determination, and predict the response at a new input" -
simple linear only, but no fence documents a polynomial-basis empty cell, and
multiple-linear-regression's description (coefficient standard errors, t
p-values, regression-F, R^2/adjusted-R^2, VIF, prediction at a new design point)
already carries every diagnostic a polynomial fit would report.
(c) Standards-map: naca-tr-824 reference-only available (not binding).
(d) Anchor: closed-form OLS exists (Vandermonde design matrix, normal
equations) - deterministic and published; anchor is not the failure.
(e) Corpus demand FRESH: polynomial regress 0, polyfit 0, vandermonde 0; the
22 reynolds corpus tasks and all surrogate-modeling tasks route to their
aerodynamics/vehicle-design owners. Demand-zero.
Decline on ownership adjacency (design-matrix/normal-equations vein) plus zero
demand plus no documented empty cell.

### S3. Standalone special-functions leaf (erf / gamma / beta machinery) - DECLINE

(a) Zero-owner grep FRESH: no leaf COMPUTES special functions as a deliverable.
The tree deliberately keeps special-function math INLINE in each leaf: chi-
square-goodness-of-fit line 31 "its own self-contained regularized lower
incomplete gamma" (series/continued-fraction branches, erf(sqrt(x)) cross-check
at line 143); proportion-confidence-interval line 27/50 "in-leaf regularized
incomplete beta"; rank-based-hypothesis-testing line 50 Phi(z) = 0.5(1 +
erf(z/sqrt(2))); hypothesis-testing computes p-values "from the incomplete beta
and gamma functions". fast-fourier-transform's logic file states the design
convention outright: the Cooley-Tukey decomposition "are generic mathematics
(the...)" implemented in pure stdlib per leaf. A standalone leaf would be a
library leaf in a tree whose numerics convention is self-contained per-leaf
stdlib math.
(b) Sibling fence: no numerics sibling fences a "special functions" cell; the
family routes engineering triggers (p-values, intervals, GOF) to the leaf that
owns the test, never to a math-library row.
(c) Standards-map: naca-tr-824 reference-only available (not binding).
(d) Anchor: DLMF/NIST published series and continued fractions exist for
erf/gamma/beta (deterministic, verifiable) - anchor exists but is not
aerospace-magnitude.
(e) Corpus demand FRESH: erf( 0, incomplete gamma 0, incomplete beta 0, special
function 0. No engineering query in the 1286-task corpus would route to a
math-library leaf; wordable Hit@1 queries would have to be bare math questions
("evaluate the incomplete gamma function at x=...") that no aeronautics corpus
task asks and that the router vocabulary (hypothesis-testing triggers, GOF
triggers) already absorbs.
Decline on demand, no empty-cell fence, and collision with the family's
documented self-contained-math convention.

### S4. Sutherland viscosity law / viscosity-at-state leaf under units-atmos - DECLINE

(a) Zero-owner grep FRESH: `sutherland` tree-wide = 0 computation hits; the
only mention is aerodynamics/high-speed/compressible-couette-flow (SKILL.md
line 48 "Sutherland-free, uniform mu and k" - an ASSUMPTION of constancy, not a
formula). No leaf evaluates mu(T) = mu_ref (T/T_ref)^1.5 (T_ref + S)/(T + S).
(b) Sibling fences (quoted): unit-conversion description: "...length (m, ft,
NM), speed (m/s, kt, ft/s, Mach), temperature (K, C, F, R), pressure (Pa, hPa,
psi, inHg), density (kg/m3, slug/ft3), mass (kg, lb, slug), and force (N, lbf).
Converts with a deterministic factor table, handles offset temperature scales,
computes Mach from true airspeed and speed of sound, and relates pressure
altitude to geometric altitude." - the factor table ends at force; no
viscosity row and no fence documenting one. Viscosity as a physical input is
consumed domain-side: reynolds/viscosity vocabulary lives across 10+
aerodynamics boundary-layer/drag-polars leaves, and dimensionless-group
handling (Reynolds) is owned by cross-cutting dimensional-analysis.
(c) Standards-map: no dedicated viscosity id exists in the 30-id map; naca-tr-824
reference-only is the only numerics mapping, and this leaf is an input-service
leaf, not a mapped deliverable.
(d) Anchor: Sutherland's two-coefficient formula with mu_ref = 1.716e-5 Pa.s,
S = 110.4 K is published deterministic closed form (standard: White, Viscous
Fluid Flow) - anchor exists.
(e) Corpus demand FRESH: sutherland 0/1286; altimeter-setting-style service
vocabulary is absent (qnh 0, qfe 0); reynolds 22 tasks all route to
aerodynamics owners.
Decline: input-service leaf in the wave-45 "data/format converter" decline
class - domain leaves own their viscosity consumption inline, zero corpus
demand, no empty-cell fence, no map id.

### S5. Z-transform as a cross-cutting numerics leaf - DECLINE (OWNED)

(a) Owner grep FRESH: gnc-autonomy/control/digital-control-design owns the
z-transform outright (tree-wide z-transform hits confined to that leaf and the
gnc-autonomy router); the discrete-filter z-plane vocabulary is additionally
owned inside cross-cutting digital-filter-design (IIR pole/zero mapping) and
fir-filter-design. A cross-cutting z-transform leaf would steal owned triggers.
(b) Corpus demand FRESH: z-transform 0/1286 tasks word the term; domain leaves
route their own transforms.
Decline on ownership (no further evidence required).

## Sub-pack re-scans at HEAD (wave-46 declines stand; token-level FRESH checks)

- tolerancing: datum shift is OWNED vocabulary - datum-reference-frames
  description: "...apply the material condition modifiers (MMB, LMB, RMB) to
  the datum feature references... the datum shift from the material condition
  modifier" with the MMB/LMB datum-shift math spelled out (SKILL.md lines 53-55:
  "MMB... allows datum shift equal to the departure of the actual mating size
  from the MMB size"). resultant-condition / inner-boundary / outer-boundary:
  0 corpus tasks, 0 leaf computation. Stackup (WC + RSS), position verification
  with MMC bonus/virtual condition, fastener fixed/floating sizing, DRF
  establishment, FCF interpretation = the five owned cells, unchanged; the
  runout/orientation/profile/concentricity verification declines (wave-46 F2-F4:
  interpretation-only or best-fit optimization, not clean closed form) stand.
- units-atmos: geopotential altitude OWNED inside unit-conversion (lines 52/66/
  78: "geometric altitude converts to geopotential altitude with the...",
  convert_altitude geom<->geopotential) and used by density-altitude (line 110);
  altimeter-setting surface 29.92 inHg = 14.6959 psi owned by unit-conversion
  line 43. QNH/QFE: corpus 0/1286 and standards-map grep FRESH confirms no
  far-121 / ac-120-42b id among the 30 (map-blocked, wave-45 row, stands). ISA
  state, density altitude, airspeed chain, temperature/dimensional conversion
  unchanged owners.
- sep2640: zero commits to the pack since wave-46; author -> deliver -> evaluate
  trio complete; skill-authoring description states "SEP-2640 stays an emerging
  spec" - no deterministic numeric surface for a fourth leaf. Wave-46 decline
  stands unchanged.
- data-sources (1), documentation (2), export-control (1): unchanged, non-
  numeric by their own descriptions (source-credibility scoring, margin-of-
  safety/report structure, ITAR/EAR verdicts); out of the clean-deterministic
  mandate scope. Wave-46 note stands.

## Method note

All greps and scans were read-only runs over skills/ and eval/ at HEAD a4ae6d1e:
family census find, router parity grep (56 = 56), full corpus parse (1286/1286
task blocks with expected_skill, 635 unique skills, 112 cross-cutting tasks,
per-leaf min = max = 2), token-demand counts over the whole corpus, zero-owner
greps tree-wide (SKILL.md and logic) for every seam keyword, keyword sweep of
all wave-44/45/46 CC receipts proving the S1-S5 seams were never adjudicated
before this run, and git-log proof that skills/cross-cutting is unchanged since
the wave-46 receipt (empty diff 45931c16..HEAD on that path). No git operations
performed. Prior receipts read: wave-46 task-10 (cross-cutting, NO_CANDIDATES),
wave-45 task-11 (cross-cutting, 1 GO + 32 declines). This receipt contains no
machine-local absolute paths.

Receipt end. No files other than this receipt were written; no git operations
were performed.
