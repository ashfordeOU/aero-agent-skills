# Wave-27 leaf spec: winglet-design (aerodynamics, wing-design pack)

- Path: skills/aerodynamics/wing-design/winglet-design/
- Pack: wing-design (existing sibling: wing-planform-design)
- Standards ids: naca-tr-824, far-25  (Ledger Standard: naca-tr-824,
  far-25)
- Family: aerodynamics

## Claim

Size a wingtip device (winglet) for induced-drag reduction on a
fixed-wing aircraft: from the wing geometry and the target span
efficiency gain, estimate the winglet height and cant required,
compute the effective aspect ratio increase, the induced-drag factor
reduction, the induced-drag coefficient at a reference lift
coefficient, and the bending-moment penalty at the wing root from the
added winglet load. Produces the winglet height, cant angle, effective
AR, drag reduction, and root bending moment penalty that gate the
wingtip device trade.

Does NOT do: derive the wing reference planform or the spanwise load
distribution with the Schrenk method (wing-planform-design); size the
wing area from wing loading at the vehicle level
(vehicle-design wing-planform-sizing); or estimate the full drag polar
including parasite drag (drag-polar, parasite-drag). Winglet design
here is the tip-device induced-drag and structural-penalty trade only.

## Model (implement exactly)

Inputs:
- span_m (float, reference span), area_m2 (float, reference area),
- e_base (float, span efficiency without winglet, <= 1.0),
- cl_ref (float, reference lift coefficient for the drag check),
- height_frac (float, winglet height as a fraction of the local
  semi-span, e.g. 0.15), cant_deg (float, winglet cant from vertical,
  deg), taper_frac (float, winglet tip-to-root chord ratio, default
  0.35),
- load_m (float or None, root bending moment context, optional).

Constants (documented typicals):
- K_HEIGHT = 0.8 (fraction of the winglet height that acts as an
  effective span extension, typical range 0.7-0.9),
- CANT_LOSS = 0.6 (cosine weighting exponent used for cant: effective
  factor = 1 - (1 - cos(cant)) * CANT_LOSS... the model uses
  cant_factor = cos(cant_rad) so a vertical winglet keeps full effect
  and a flat tip loses it),
- RHO_REF = 1.225, V_REF = 100.0 (reference density and speed only for
  the optional dimensional bending check).

Functions:
- effective_span_extension(height_frac) -> float
  K_HEIGHT * height_frac.
- cant_factor(cant_deg) -> float: cos(cant_deg in rad).
- ar_eff(span_m, area_m2, height_frac, cant_deg) -> float:
  AR = span^2/area; AR_eff = AR * (1 + 2 * cant_factor * extension /
  ... ) -> implement exactly: extension of both tips in fraction of
  span: b_eff = b * (1 + 2 * cant_factor * K_HEIGHT * height_frac);
  AR_eff = b_eff^2 / area.
- e_winglet(e_base, height_frac, cant_deg) -> float:
  e = 1 - (1 - e_base) / (1 + 2 * cant_factor * K_HEIGHT *
  height_frac)  (documented improvement model: the drag factor k =
  1/(pi e AR) shrinks with the effective-AR gain; equivalent form
  e_eff = 1 - (1 - e_base)/(AR_eff/AR)). Implement the equivalent
  e_eff form and label it a documented approximation.
- induced_drag_factor(e, ar) -> float k = 1/(pi * e * ar).
- cd_i(cl, e, ar) -> float cl^2 * k.
- drag_reduction_pct(cl_ref, base, wl) -> float:
  100 * (1 - cd_i_wl / cd_i_base).
- root_bending_penalty_pct(height_frac, cant_deg) -> float:
  added moment proxy = cant_factor * K_HEIGHT * height_frac * 100 *
  (1 + 0.5 * height_frac) (documented typical scaling; the winglet
  load acts near the tip so the root moment penalty grows roughly with
  the height fraction). Label approximate.
- size_winglet(span_m, area_m2, e_base, target_reduction_pct,
  cl_ref, cant_deg=0.0) -> dict: bisection on height_frac in [0.01,
  0.5] to hit the target drag reduction (tol 0.1 pct); returns
  {height_frac, height_m = height_frac * (span_m/2) * local factor
  (use semi-span for the local reference), ar_eff, e_eff, cd_i,
  reduction_pct, bending_penalty_pct}.

ValueError on: span <= 0, area <= 0, e_base <= 0 or > 1, cl_ref <= 0,
height_frac outside [0, 0.6] (for the direct function), cant_deg
outside [-90, 90], taper_frac <= 0 or > 1, target_reduction_pct <= 0
or >= 100.

## Worked example

Wing: span 30 m, area 100 m2 (AR 9), e_base 0.80, cl_ref 0.5.
Direct case height_frac 0.12, cant 0 deg, taper 0.35:
- extension = 0.8*0.12 = 0.096; cant_factor = 1.0;
- b_eff = 30*(1 + 2*1.0*0.096) = 30*1.192 = 35.76 m; AR_eff =
  35.76^2/100 = 12.788 (assert within 0.01),
- e_eff = 1 - 0.2/(AR_eff/9) = 1 - 0.2/1.4209 = 1 - 0.14075 = 0.85925
  (assert within 1e-4),
- k_base = 1/(pi*0.8*9) = 0.0442097; k_wl = 1/(pi*0.85925*12.788) =
  0.028987 (assert within 1e-6),
- cd_i base = 0.25*0.0442097 = 0.0110524; cd_i wl = 0.25*0.028987 =
  0.0072468; reduction = 100*(1 - 0.0072468/0.0110524) = 34.43 pct
  (assert within 0.05),
- bending penalty = 1.0*0.8*0.12*100*(1+0.06) = 10.18 pct (assert
  within 0.05).
Sizing case: target 25 pct reduction -> height_frac between 0.05 and
0.10 (assert monotonic: size_winglet with target 25 returns a
height_frac in [0.05, 0.12] and its reduction_pct within 0.1 of 25).
ValueErrors: span 0, e_base 1.2, cant 120, height_frac 0.8.
Keep at least 16 test methods.

## Corpus tasks (ids w27-winglet-design-1/2)

Distinctive tokens: winglet design, wingtip device, induced drag
reduction, effective aspect ratio, span efficiency, cant angle, root
bending moment penalty, winglet height. Avoid: mean aerodynamic chord,
Schrenk, washout (wing-planform-design); wing area from wing loading
(wing-planform-sizing vehicle-design); drag polar cd0
(drag-polar, parasite-drag).

1. "size a winglet for the transport wing to cut induced drag by 25
   percent: find the winglet height fraction and the effective aspect
   ratio gain at the 0.5 lift coefficient with 0.8 base span
   efficiency"
2. "compare the wingtip device options: compute the induced drag
   reduction and the root bending moment penalty for a 0.12 height
   fraction vertical winglet on the 9 aspect ratio wing"

## SKILL body notes

Pair with wing-planform-design (planform source) and the
vehicle-design wing-planform-sizing and drag-polar leaves (system
context). The e_eff improvement and bending-penalty models are
documented conceptual approximations for a preliminary trade; real
winglet design needs a VLM/CFD and structural FEM pass. Cite
vortex-lattice-method and calculix-linear as the higher-fidelity
follow-ons. Standards referenced (NACA TR-824 induced-drag basis;
FAR 25 structural context) not reproduced.
