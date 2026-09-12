#!/usr/bin/env python3
"""ECSS-E-ST-32C Annex F fracture control plan (FCP) screening logic
(paraphrase, not verbatim ECSS text).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
structures standard's fracture control annex requires the programme to
identify fracture-critical items (FCIs) — hardware whose fracture-mode
failure would be catastrophic — and to demonstrate, for each FCI, that
the critical flaw size derived from fracture toughness and operating
stress exceeds the largest flaw assumed to survive non-destructive
inspection, that the proof-test factor is sufficient to screen out
flaws at or above the critical size, and that the safe-life factor
covers the required analysis lifetime with adequate margin. This module
implements FCI categorization, critical-flaw-size computation (plane-
strain fracture mechanics), proof-test and safe-life factor threshold
checks, NDI detectability screening, and aggregated FCI review; it
does not implement fatigue crack growth integration or residual
strength computation.
"""

import math

FRACTURE_CONSEQUENCE_MAP = {
    "catastrophic": "fracture_critical",
    "non_catastrophic": "fracture_non_critical",
}

MIN_PROOF_TEST_FACTOR = 1.25
MIN_SAFE_LIFE_FACTOR = 4.0


def categorize_item(failure_consequence):
    """Return 'fracture_critical' or 'fracture_non_critical' for a
    structural item based on its failure consequence string.
    Raises ValueError for an unrecognized failure_consequence."""
    if failure_consequence not in FRACTURE_CONSEQUENCE_MAP:
        raise ValueError(
            "unrecognized failure consequence %r; expected one of %s"
            % (failure_consequence, sorted(FRACTURE_CONSEQUENCE_MAP))
        )
    return FRACTURE_CONSEQUENCE_MAP[failure_consequence]


def critical_flaw_size_m(K_Ic_MPa_sqrt_m, geometry_factor_Y, applied_stress_MPa):
    """Critical half-crack length (m) from plane-strain fracture
    mechanics: a_c = (K_Ic / (Y * sigma * sqrt(pi)))^2.
    Raises ValueError for non-positive K_Ic, geometry factor, or stress."""
    if K_Ic_MPa_sqrt_m <= 0:
        raise ValueError(
            "K_Ic_MPa_sqrt_m must be > 0, got %r" % K_Ic_MPa_sqrt_m
        )
    if geometry_factor_Y <= 0:
        raise ValueError(
            "geometry_factor_Y must be > 0, got %r" % geometry_factor_Y
        )
    if applied_stress_MPa <= 0:
        raise ValueError(
            "applied_stress_MPa must be > 0, got %r" % applied_stress_MPa
        )
    return (
        K_Ic_MPa_sqrt_m
        / (geometry_factor_Y * applied_stress_MPa * math.sqrt(math.pi))
    ) ** 2


def check_proof_test_factor(proof_factor, min_required=MIN_PROOF_TEST_FACTOR):
    """Violation list for a proof-test factor below the minimum
    threshold. Empty list if the factor meets or exceeds the threshold.
    Does not mutate arguments."""
    if proof_factor < min_required:
        return [
            {
                "issue": "proof_test_factor_below_threshold",
                "proof_factor": proof_factor,
                "min_required": min_required,
            }
        ]
    return []


def check_safe_life_factor(safe_life_factor, min_required=MIN_SAFE_LIFE_FACTOR):
    """Violation list for a safe-life factor below the minimum threshold.
    Empty list if the factor meets or exceeds the threshold.
    Does not mutate arguments."""
    if safe_life_factor < min_required:
        return [
            {
                "issue": "safe_life_factor_below_threshold",
                "safe_life_factor": safe_life_factor,
                "min_required": min_required,
            }
        ]
    return []


def check_ndi_detectability(assumed_flaw_size_m, ndi_detection_threshold_m):
    """Violation list for NDI detectability: the NDI technique's
    detection threshold must be <= the assumed initial flaw size so
    the technique can detect every flaw at or above that size.
    Returns a violation when the threshold exceeds the assumed flaw.
    Raises ValueError for non-positive inputs."""
    if assumed_flaw_size_m <= 0:
        raise ValueError(
            "assumed_flaw_size_m must be > 0, got %r" % assumed_flaw_size_m
        )
    if ndi_detection_threshold_m <= 0:
        raise ValueError(
            "ndi_detection_threshold_m must be > 0, got %r" % ndi_detection_threshold_m
        )
    if ndi_detection_threshold_m > assumed_flaw_size_m:
        return [
            {
                "issue": "ndi_cannot_detect_assumed_flaw",
                "assumed_flaw_size_m": assumed_flaw_size_m,
                "ndi_detection_threshold_m": ndi_detection_threshold_m,
            }
        ]
    return []


def check_critical_vs_assumed(item_id, critical_flaw_m, assumed_flaw_m):
    """Violation list when the critical flaw size does not strictly
    exceed the assumed initial flaw: a flaw that NDI may have missed
    could propagate to fracture at the operating stress.
    Does not mutate arguments."""
    if critical_flaw_m <= assumed_flaw_m:
        return [
            {
                "issue": "critical_flaw_not_larger_than_assumed",
                "item": item_id,
                "critical_flaw_m": critical_flaw_m,
                "assumed_flaw_m": assumed_flaw_m,
            }
        ]
    return []


def fci_review(item):
    """Full FCP Annex-F review for one structural item.

    item keys:
      item_id: str
      failure_consequence: str  -- 'catastrophic' | 'non_catastrophic'
      K_Ic_MPa_sqrt_m: float   -- plane-strain fracture toughness
      geometry_factor_Y: float -- geometry/stress-intensity factor
      applied_stress_MPa: float -- peak operating stress
      assumed_flaw_size_m: float -- largest NDI-undetectable flaw
      ndi_detection_threshold_m: float -- minimum detectable flaw size
      proof_factor: float      -- proof load / limit load
      safe_life_factor: float  -- analysis lifetime / design lifetime

    Returns {'categorization': str, 'violations': [...]}.
    Fracture-non-critical items return an empty violation list.
    Raises ValueError for an unrecognized failure_consequence or
    non-positive numeric inputs on fracture-critical items."""
    item_id = item["item_id"]
    category = categorize_item(item["failure_consequence"])
    if category == "fracture_non_critical":
        return {"categorization": category, "violations": []}

    violations = []
    a_c = critical_flaw_size_m(
        item["K_Ic_MPa_sqrt_m"],
        item["geometry_factor_Y"],
        item["applied_stress_MPa"],
    )
    assumed = item["assumed_flaw_size_m"]
    violations = (
        check_critical_vs_assumed(item_id, a_c, assumed)
        + check_ndi_detectability(assumed, item["ndi_detection_threshold_m"])
        + check_proof_test_factor(item["proof_factor"])
        + check_safe_life_factor(item["safe_life_factor"])
    )
    return {"categorization": category, "violations": violations}


def is_fcp_compliant(review):
    """True when an fci_review result carries no violations."""
    return len(review["violations"]) == 0
