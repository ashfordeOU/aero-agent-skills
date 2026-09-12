"""
Element topology checks — ECSS-E-ST-32C §5.3.

Implements three families of topology quality checks for finite element
models: element distortions (aspect ratio, warping, skewness), node
connectivity (broken references, orphan nodes), and duplicate elements
(identical node sets). No third-party dependencies; stdlib only.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Node:
    id: int
    x: float
    y: float
    z: float


@dataclass
class Element:
    id: int
    etype: str          # e.g. "TRIA3", "QUAD4", "BEAM2", "TET4"
    nodes: Tuple[int, ...]


# ---------------------------------------------------------------------------
# Thresholds (ECSS-E-ST-32C §5.3 paraphrased guidance)
# ---------------------------------------------------------------------------

ASPECT_RATIO_WARN: float = 5.0
ASPECT_RATIO_FAIL: float = 20.0
WARPING_WARN_DEG: float = 5.0    # QUAD4 out-of-plane twist
WARPING_FAIL_DEG: float = 15.0
SKEWNESS_WARN_DEG: float = 45.0  # max interior-angle deviation from 60°
SKEWNESS_FAIL_DEG: float = 60.0


# ---------------------------------------------------------------------------
# Finding types
# ---------------------------------------------------------------------------

@dataclass
class DistortionFinding:
    element_id: int
    metric: str        # "aspect_ratio" | "warping" | "skewness"
    value: float
    threshold: float
    severity: str      # "WARN" | "FAIL"


@dataclass
class ConnectivityFinding:
    finding_type: str  # "broken_ref" | "orphan_node"
    node_id: int
    element_id: Optional[int] = None


@dataclass
class DuplicateFinding:
    element_ids: Tuple[int, int]
    node_set: Tuple[int, ...]


@dataclass
class TopologyReport:
    distortion_findings: List[DistortionFinding] = field(default_factory=list)
    connectivity_findings: List[ConnectivityFinding] = field(default_factory=list)
    duplicate_findings: List[DuplicateFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        fail_distortions = [f for f in self.distortion_findings if f.severity == "FAIL"]
        return (
            not fail_distortions
            and not self.connectivity_findings
            and not self.duplicate_findings
        )


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _dist(a: Node, b: Node) -> float:
    return math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2)


def _vec(a: Node, b: Node) -> Tuple[float, float, float]:
    return (b.x - a.x, b.y - a.y, b.z - a.z)


def _dot(u: Tuple[float, float, float], v: Tuple[float, float, float]) -> float:
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _cross(
    u: Tuple[float, float, float], v: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    return (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )


def _norm(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
    m = math.sqrt(_dot(v, v))
    if m < 1e-15:
        return (0.0, 0.0, 0.0)
    return (v[0] / m, v[1] / m, v[2] / m)


# ---------------------------------------------------------------------------
# Distortion metrics
# ---------------------------------------------------------------------------

def _aspect_ratio(ns: List[Node]) -> float:
    """Longest / shortest edge length for any polygon."""
    n = len(ns)
    edges = [_dist(ns[i], ns[(i + 1) % n]) for i in range(n)]
    min_e = min(edges)
    if min_e < 1e-15:
        return float("inf")
    return max(edges) / min_e


def _skewness_tria3(ns: List[Node]) -> float:
    """Maximum deviation of any interior angle from the ideal 60° (degrees)."""
    n0, n1, n2 = ns

    def interior_angle(apex: Node, wing_a: Node, wing_b: Node) -> float:
        va = _vec(apex, wing_a)
        vb = _vec(apex, wing_b)
        denom = math.sqrt(_dot(va, va)) * math.sqrt(_dot(vb, vb))
        if denom < 1e-15:
            return 0.0
        cos_a = max(-1.0, min(1.0, _dot(va, vb) / denom))
        return math.degrees(math.acos(cos_a))

    a0 = interior_angle(n0, n1, n2)
    a1 = interior_angle(n1, n0, n2)
    a2 = interior_angle(n2, n0, n1)
    return max(abs(a - 60.0) for a in (a0, a1, a2))


def _warping_quad4(ns: List[Node]) -> float:
    """
    Warping angle for a QUAD4: dihedral angle (degrees) between the normals
    of the two triangles formed by splitting along diagonal n0–n2.
    Zero for a planar element; increases with out-of-plane twist.
    """
    n0, n1, n2, n3 = ns
    v01 = _vec(n0, n1)
    v02 = _vec(n0, n2)
    v03 = _vec(n0, n3)
    na = _norm(_cross(v01, v02))   # normal of triangle n0-n1-n2
    nb = _norm(_cross(v02, v03))   # normal of triangle n0-n2-n3
    cos_a = max(-1.0, min(1.0, _dot(na, nb)))
    return math.degrees(math.acos(cos_a))


# ---------------------------------------------------------------------------
# Registered checks per element type
# Each entry: (metric_name, metric_fn, warn_threshold, fail_threshold)
# ---------------------------------------------------------------------------

_DISTORTION_REGISTRY: Dict[str, List] = {
    "TRIA3": [
        ("aspect_ratio", _aspect_ratio, ASPECT_RATIO_WARN, ASPECT_RATIO_FAIL),
        ("skewness", _skewness_tria3, SKEWNESS_WARN_DEG, SKEWNESS_FAIL_DEG),
    ],
    "QUAD4": [
        ("aspect_ratio", _aspect_ratio, ASPECT_RATIO_WARN, ASPECT_RATIO_FAIL),
        ("warping", _warping_quad4, WARPING_WARN_DEG, WARPING_FAIL_DEG),
    ],
}


# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------

def check_distortions(
    nodes: Dict[int, Node],
    elements: List[Element],
) -> List[DistortionFinding]:
    """
    Compute distortion metrics for every element whose type has a registered
    check. Elements with an unregistered type are skipped (not an error).
    Elements with broken node references are skipped; connectivity errors
    are reported separately by check_connectivity.
    """
    findings: List[DistortionFinding] = []
    for elem in elements:
        checks = _DISTORTION_REGISTRY.get(elem.etype)
        if checks is None:
            continue
        ns = [nodes[nid] for nid in elem.nodes if nid in nodes]
        if len(ns) != len(elem.nodes):
            continue  # broken ref — handled by check_connectivity
        for metric, fn, warn_t, fail_t in checks:
            val = fn(ns)
            if val >= fail_t:
                findings.append(DistortionFinding(elem.id, metric, val, fail_t, "FAIL"))
            elif val >= warn_t:
                findings.append(DistortionFinding(elem.id, metric, val, warn_t, "WARN"))
    return findings


def check_connectivity(
    nodes: Dict[int, Node],
    elements: List[Element],
) -> List[ConnectivityFinding]:
    """
    Verify element-to-node references and flag orphan nodes.
    - broken_ref: an element references a node ID not in the node table.
    - orphan_node: a node exists in the table but is referenced by no element.
    """
    findings: List[ConnectivityFinding] = []
    referenced: Set[int] = set()
    for elem in elements:
        for nid in elem.nodes:
            if nid not in nodes:
                findings.append(ConnectivityFinding("broken_ref", nid, elem.id))
            else:
                referenced.add(nid)
    for nid in nodes:
        if nid not in referenced:
            findings.append(ConnectivityFinding("orphan_node", nid))
    return findings


def check_duplicates(elements: List[Element]) -> List[DuplicateFinding]:
    """
    Detect element pairs sharing an identical node set (order-independent).
    Only the first collision per unique node set is reported; subsequent
    duplicates of the same set are paired against the first-seen element.
    """
    findings: List[DuplicateFinding] = []
    seen: Dict[Tuple[int, ...], int] = {}
    for elem in elements:
        key = tuple(sorted(elem.nodes))
        if key in seen:
            findings.append(DuplicateFinding((seen[key], elem.id), key))
        else:
            seen[key] = elem.id
    return findings


def run_topology_checks(
    nodes: Dict[int, Node],
    elements: List[Element],
) -> TopologyReport:
    """Run all three topology check families and return a consolidated report."""
    report = TopologyReport()
    report.connectivity_findings = check_connectivity(nodes, elements)
    report.distortion_findings = check_distortions(nodes, elements)
    report.duplicate_findings = check_duplicates(elements)
    return report
