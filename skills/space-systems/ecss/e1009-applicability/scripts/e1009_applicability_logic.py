"""
e1009_applicability_logic.py

Engineering logic for ECSS-E-ST-10C §5.3.1 coordinate-definition applicability.
Checks that coordinate-frame definitions are applied across all five required
activity domains: mission_definition, engineering, verification, operations,
and data_processing.

Paraphrased from ECSS-E-ST-10C §5.3.1 (coordinate system applicability).
Stdlib only — deterministic, offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# ---------------------------------------------------------------------------
# Domain and frame-type vocabularies  (paraphrased from §5.3.1 / §5.2)
# ---------------------------------------------------------------------------

REQUIRED_DOMAINS: frozenset = frozenset({
    "mission_definition",
    "engineering",
    "verification",
    "operations",
    "data_processing",
})

# Frame families recognised under ECSS-E-ST-10C §5.2
VALID_FRAME_TYPES: frozenset = frozenset({
    "inertial",     # e.g. J2000, EME2000
    "earth_fixed",  # e.g. ECEF, ITRF
    "body",         # spacecraft body reference frame
    "orbital",      # e.g. LVLH, RSW, TNW
    "instrument",   # sensor or payload boresight frame
    "topocentric",  # ground-station-centred frame
    "structural",   # mechanical / CAD reference frame
})

# Minimum frame-type families required per domain (paraphrased §5.3.1)
DOMAIN_REQUIRED_TYPES: Dict[str, frozenset] = {
    "mission_definition": frozenset({"inertial", "earth_fixed"}),
    "engineering":        frozenset({"body", "structural"}),
    "verification":       frozenset({"body", "inertial"}),
    "operations":         frozenset({"inertial", "earth_fixed", "orbital"}),
    "data_processing":    frozenset({"inertial", "instrument"}),
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CoordinateFrame:
    name: str
    frame_type: str
    domain: str
    description: str = ""


@dataclass
class Finding:
    domain: str
    issue: str
    severity: str  # "error" | "warning"


@dataclass
class ApplicabilityReport:
    covered_domains: List[str] = field(default_factory=list)
    missing_domains: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
    compliant: bool = False

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_frame(frame: CoordinateFrame) -> List[str]:
    """Return a list of validation error strings for one frame entry."""
    errors: List[str] = []
    if not frame.name or not frame.name.strip():
        errors.append("frame name must not be empty")
    if frame.frame_type not in VALID_FRAME_TYPES:
        errors.append(
            f"frame_type '{frame.frame_type}' is not recognised; "
            f"allowed: {sorted(VALID_FRAME_TYPES)}"
        )
    if frame.domain not in REQUIRED_DOMAINS:
        errors.append(
            f"domain '{frame.domain}' is not a required applicability domain; "
            f"allowed: {sorted(REQUIRED_DOMAINS)}"
        )
    return errors


def check_duplicate_names(frames: List[CoordinateFrame]) -> List[str]:
    """Return error strings for any duplicate frame names in the list."""
    counts: Dict[str, int] = {}
    for f in frames:
        counts[f.name] = counts.get(f.name, 0) + 1
    return [
        f"duplicate frame name '{name}' appears {n} times"
        for name, n in counts.items()
        if n > 1
    ]

# ---------------------------------------------------------------------------
# Domain coverage analysis
# ---------------------------------------------------------------------------

def _group_by_domain(frames: List[CoordinateFrame]) -> Dict[str, List[CoordinateFrame]]:
    result: Dict[str, List[CoordinateFrame]] = {d: [] for d in REQUIRED_DOMAINS}
    for f in frames:
        if f.domain in result:
            result[f.domain].append(f)
    return result


def check_domain_coverage(frames: List[CoordinateFrame]) -> ApplicabilityReport:
    """
    Verify that coordinate-frame definitions cover all five §5.3.1 domains and
    that each domain carries the required frame-type families.

    Raises ValueError if any frame fails individual validation.
    """
    # Validate each frame before analysis
    for f in frames:
        errs = validate_frame(f)
        if errs:
            raise ValueError(
                f"Invalid frame '{f.name}': " + "; ".join(errs)
            )

    report = ApplicabilityReport()

    # Global duplicate check
    for dup_err in check_duplicate_names(frames):
        report.findings.append(Finding(domain="global", issue=dup_err, severity="error"))

    by_domain = _group_by_domain(frames)

    for domain in sorted(REQUIRED_DOMAINS):
        domain_frames = by_domain[domain]

        if not domain_frames:
            report.missing_domains.append(domain)
            report.findings.append(Finding(
                domain=domain,
                issue=f"no coordinate frame defined for domain '{domain}'",
                severity="error",
            ))
            continue

        present_types = frozenset(f.frame_type for f in domain_frames)
        required_types = DOMAIN_REQUIRED_TYPES[domain]
        missing_types = sorted(required_types - present_types)

        if missing_types:
            report.findings.append(Finding(
                domain=domain,
                issue=f"missing required frame type(s) {missing_types}",
                severity="error",
            ))
        else:
            report.covered_domains.append(domain)

    error_count = sum(1 for f in report.findings if f.severity == "error")
    report.compliant = error_count == 0
    return report

# ---------------------------------------------------------------------------
# Single-domain assessment
# ---------------------------------------------------------------------------

def assess_single_domain(domain: str, frames: List[CoordinateFrame]) -> Dict:
    """
    Assess whether frames satisfy §5.3.1 requirements for one domain.

    Raises ValueError for an unrecognised domain name.
    Returns a dict: {domain, covered, present_types, missing_types, findings}.
    """
    if domain not in REQUIRED_DOMAINS:
        raise ValueError(
            f"'{domain}' is not a recognised §5.3.1 applicability domain; "
            f"allowed: {sorted(REQUIRED_DOMAINS)}"
        )

    domain_frames = [f for f in frames if f.domain == domain]
    required = DOMAIN_REQUIRED_TYPES[domain]
    present = frozenset(f.frame_type for f in domain_frames)
    missing = sorted(required - present)
    findings: List[str] = []

    if not domain_frames:
        findings.append(f"no frames defined for domain '{domain}'")
    else:
        if missing:
            findings.append(f"missing frame type(s): {missing}")

    return {
        "domain": domain,
        "covered": len(findings) == 0,
        "present_types": sorted(present),
        "missing_types": missing,
        "findings": findings,
    }

# ---------------------------------------------------------------------------
# Completeness gate
# ---------------------------------------------------------------------------

def completeness_gate(frames: List[CoordinateFrame]) -> Dict:
    """
    Top-level gate: returns a summary dict indicating whether all five §5.3.1
    domains have sufficient coordinate-frame coverage, with a list of any gaps.

    Does NOT raise; returns structured result for caller inspection.
    """
    valid_frames = []
    pre_errors: List[str] = []

    for f in frames:
        errs = validate_frame(f)
        if errs:
            pre_errors.append(f"frame '{f.name}': " + "; ".join(errs))
        else:
            valid_frames.append(f)

    if pre_errors:
        return {
            "pass": False,
            "pre_validation_errors": pre_errors,
            "covered_domains": [],
            "gaps": [],
        }

    report = check_domain_coverage(valid_frames)
    gaps = [f"{fn.domain}: {fn.issue}" for fn in report.findings]

    return {
        "pass": report.compliant,
        "pre_validation_errors": [],
        "covered_domains": sorted(report.covered_domains),
        "gaps": gaps,
    }
