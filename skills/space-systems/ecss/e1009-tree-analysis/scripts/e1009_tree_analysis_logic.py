"""
Transformation tree and Franck diagram analysis per ECSS-E-ST-10C Annex B.

Implements: frame-node management, tree validation (cycle/connectivity),
chain resolution via lowest common ancestor, homogeneous-transform
composition, and Franck diagram edge export.

All stdlib — no external dependencies.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 4x4 homogeneous transform helpers (row-major flat list of 16 floats)
# ---------------------------------------------------------------------------

def identity_4x4() -> List[float]:
    """Return a 4x4 identity matrix as a flat row-major list of 16 floats."""
    m = [0.0] * 16
    for i in range(4):
        m[i * 4 + i] = 1.0
    return m


def mat_mul_4x4(A: List[float], B: List[float]) -> List[float]:
    """Multiply two 4x4 row-major flat matrices; raises ValueError on wrong size."""
    if len(A) != 16 or len(B) != 16:
        raise ValueError("Both matrices must be 4x4 (16 elements).")
    result = [0.0] * 16
    for i in range(4):
        for j in range(4):
            for k in range(4):
                result[i * 4 + j] += A[i * 4 + k] * B[k * 4 + j]
    return result


def build_transform(
    rotation: List[List[float]], translation: List[float]
) -> List[float]:
    """
    Build a 4x4 homogeneous transform from a 3x3 rotation and a 3-element
    translation vector.  Returns a flat row-major list of 16 floats.

    Layout:
        [ R(3x3) | t(3) ]
        [ 0  0  0 |  1  ]
    """
    if len(rotation) != 3 or any(len(row) != 3 for row in rotation):
        raise ValueError("rotation must be a 3x3 list-of-lists.")
    if len(translation) != 3:
        raise ValueError("translation must have exactly 3 elements.")
    m = [0.0] * 16
    for i in range(3):
        for j in range(3):
            m[i * 4 + j] = float(rotation[i][j])
    for i in range(3):
        m[i * 4 + 3] = float(translation[i])
    m[15] = 1.0
    return m


def invert_homogeneous(T: List[float]) -> List[float]:
    """
    Invert a 4x4 homogeneous transform [R | t ; 0 | 1] using the
    closed-form expression: inverse = [R^T | -R^T * t ; 0 | 1].
    Avoids floating-point errors introduced by general matrix inversion.
    """
    R = [[T[i * 4 + j] for j in range(3)] for i in range(3)]
    t = [T[i * 4 + 3] for i in range(3)]
    Rt = [[R[j][i] for j in range(3)] for i in range(3)]
    neg_Rt_t = [
        -sum(Rt[i][k] * t[k] for k in range(3))
        for i in range(3)
    ]
    return build_transform(Rt, neg_Rt_t)


# keep a private alias used by tests that import the underscore name
_invert_homogeneous = invert_homogeneous


# ---------------------------------------------------------------------------
# Frame node
# ---------------------------------------------------------------------------

class FrameNode:
    """One element in the product tree, carrying its body frame definition."""

    def __init__(
        self,
        name: str,
        parent: Optional[str] = None,
        transform_to_parent: Optional[List[float]] = None,
    ) -> None:
        if not name:
            raise ValueError("Frame node name must be non-empty.")
        self.name = name
        self.parent = parent
        self.transform_to_parent: List[float] = (
            transform_to_parent
            if transform_to_parent is not None
            else identity_4x4()
        )


# ---------------------------------------------------------------------------
# Transformation tree
# ---------------------------------------------------------------------------

class TransformationTree:
    """
    Directed acyclic graph of body frames following the product-tree
    hierarchy per ECSS-E-ST-10C Annex B.

    Each edge carries the 4x4 homogeneous transform from the child frame
    expressed in the parent frame (child.transform_to_parent).
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, FrameNode] = {}

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def add_node(
        self,
        name: str,
        parent: Optional[str] = None,
        transform_to_parent: Optional[List[float]] = None,
    ) -> None:
        """
        Register a frame node.

        Raises ValueError if the name already exists or if the parent
        has not yet been registered (children must follow parents).
        """
        if name in self._nodes:
            raise ValueError(f"Node '{name}' already exists in the tree.")
        if parent is not None and parent not in self._nodes:
            raise ValueError(
                f"Parent '{parent}' of node '{name}' is not registered. "
                "Add the parent before adding this child."
            )
        self._nodes[name] = FrameNode(name, parent, transform_to_parent)

    # ------------------------------------------------------------------
    # Read-only queries
    # ------------------------------------------------------------------

    def nodes(self) -> List[str]:
        """Return all registered node names."""
        return list(self._nodes.keys())

    def children_of(self, name: str) -> List[str]:
        """Return the direct children of node *name*."""
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not found.")
        return [n for n, nd in self._nodes.items() if nd.parent == name]

    def root(self) -> Optional[str]:
        """Return the unique root name, or None if zero or multiple roots exist."""
        roots = [n for n, nd in self._nodes.items() if nd.parent is None]
        return roots[0] if len(roots) == 1 else None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """
        Return a list of error strings describing structural defects.
        An empty list means the tree is well-formed.

        Checks performed:
        - Non-empty tree
        - Exactly one root
        - No cycles (depth-first, greyscale marking)
        - All nodes reachable from the root
        """
        errors: List[str] = []

        if not self._nodes:
            errors.append("Tree is empty.")
            return errors

        roots = [n for n, nd in self._nodes.items() if nd.parent is None]
        if len(roots) == 0:
            errors.append(
                "No root node found (every node has a parent — cycle likely)."
            )
        elif len(roots) > 1:
            errors.append(
                f"Multiple root nodes found: {sorted(roots)}. "
                "A transformation tree must have exactly one root."
            )

        WHITE, GREY, BLACK = 0, 1, 2
        colour: Dict[str, int] = {n: WHITE for n in self._nodes}

        def _dfs(node: str) -> bool:
            colour[node] = GREY
            for child in self.children_of(node):
                if colour[child] == GREY:
                    return True
                if colour[child] == WHITE and _dfs(child):
                    return True
            colour[node] = BLACK
            return False

        for r in roots:
            if _dfs(r):
                errors.append("Cycle detected in the transformation tree.")
                break

        if len(roots) == 1 and not errors:
            visited: set = set()
            queue: deque = deque([roots[0]])
            while queue:
                cur = queue.popleft()
                visited.add(cur)
                queue.extend(self.children_of(cur))
            unreachable = set(self._nodes) - visited
            if unreachable:
                errors.append(
                    "Disconnected nodes (unreachable from root): "
                    f"{sorted(unreachable)}"
                )

        return errors

    # ------------------------------------------------------------------
    # Chain resolution
    # ------------------------------------------------------------------

    def _ancestor_list(self, name: str) -> List[str]:
        """Return [name, parent, grandparent, ..., root] for *name*."""
        if name not in self._nodes:
            raise KeyError(f"Node '{name}' not found.")
        path: List[str] = []
        cur: Optional[str] = name
        seen: set = set()
        while cur is not None:
            if cur in seen:
                raise RuntimeError(
                    f"Cycle detected while tracing ancestors of '{name}'."
                )
            seen.add(cur)
            path.append(cur)
            cur = self._nodes[cur].parent
        return path

    def find_chain(self, source: str, target: str) -> List[str]:
        """
        Return the ordered node list from *source* to *target* through
        the lowest common ancestor.

        Path: source → ... → LCA → ... → target

        Raises KeyError if either node is absent.
        Raises RuntimeError if no path exists (disconnected trees).
        """
        if source not in self._nodes:
            raise KeyError(f"Source node '{source}' not found.")
        if target not in self._nodes:
            raise KeyError(f"Target node '{target}' not found.")
        if source == target:
            return [source]

        src_anc = self._ancestor_list(source)
        tgt_anc = self._ancestor_list(target)

        src_idx = {n: i for i, n in enumerate(src_anc)}

        lca: Optional[str] = None
        lca_tgt_idx: int = 0
        for i, node in enumerate(tgt_anc):
            if node in src_idx:
                lca = node
                lca_tgt_idx = i
                break

        if lca is None:
            raise RuntimeError(
                f"No path between '{source}' and '{target}' "
                "(nodes are in disconnected subtrees)."
            )

        up_path = src_anc[: src_idx[lca] + 1]          # source … LCA inclusive
        down_path = tgt_anc[:lca_tgt_idx][::-1]        # LCA exclusive … target

        return up_path + down_path

    # ------------------------------------------------------------------
    # Transform composition
    # ------------------------------------------------------------------

    def compose_chain(self, chain: List[str]) -> List[float]:
        """
        Compose the homogeneous transforms along *chain* into one matrix.

        Convention:
        - Ascending edge (child → parent): use child.transform_to_parent
        - Descending edge (parent → child): use inverse of child.transform_to_parent

        Composition is left-to-right, starting from identity.

        Raises ValueError on an empty chain.
        Raises RuntimeError if adjacent nodes are not connected.
        """
        if not chain:
            raise ValueError("Chain must contain at least one node.")
        if len(chain) == 1:
            return identity_4x4()

        result = identity_4x4()
        for i in range(len(chain) - 1):
            a, b = chain[i], chain[i + 1]
            node_a = self._nodes[a]
            node_b = self._nodes[b]

            if node_b.parent == a:
                # Descending: a is parent, b is child — use inverse of b's T
                T = invert_homogeneous(node_b.transform_to_parent)
            elif node_a.parent == b:
                # Ascending: b is parent, a is child — use a's T directly
                T = node_a.transform_to_parent
            else:
                raise RuntimeError(
                    f"Nodes '{a}' and '{b}' are not adjacent in the tree."
                )
            result = mat_mul_4x4(result, T)

        return result

    # ------------------------------------------------------------------
    # Franck diagram export
    # ------------------------------------------------------------------

    def franck_edges(self) -> List[Tuple[str, str]]:
        """
        Return all directed edges (parent, child) that form the
        Franck diagram — one arrow per parent-to-child frame link.
        """
        return [
            (nd.parent, name)
            for name, nd in self._nodes.items()
            if nd.parent is not None
        ]
