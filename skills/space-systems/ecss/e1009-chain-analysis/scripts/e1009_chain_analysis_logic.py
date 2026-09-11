#!/usr/bin/env python3
"""ECSS-E-ST-10C §5.2.3 coordinate system chain analysis (paraphrase, not copy).

Common-knowledge summary: a spacecraft project must establish a complete,
traceable transformation graph from every user coordinate system (body,
sensor, structural, orbital, ground) back to the mission-level inertial
root. This module implements CS registration, inter-frame transformation
linking, breadth-first chain finding, completeness verification,
directed-graph cycle detection, and handedness consistency checking. A
project is chain-compliant only when every user has a resolved path to the
root, the directed transformation graph is acyclic, and every frame in
each resolved chain shares the handedness convention of the root.
"""

from collections import deque

VALID_CS_TYPES = frozenset({"inertial", "body", "sensor", "structural", "ground", "orbital"})
VALID_HANDEDNESS = frozenset({"right", "left"})
VALID_XFORM_TYPES = frozenset({"rotation", "translation", "rigid_body"})


class ChainError(Exception):
    """Raised for invalid inputs or unresolvable chains."""


class CoordinateSystem:
    """A named coordinate system with a type and handedness convention."""

    def __init__(self, name, cs_type, handedness="right"):
        if not name or not isinstance(name, str):
            raise ChainError(f"Coordinate system name must be a non-empty string, got {name!r}")
        if cs_type not in VALID_CS_TYPES:
            raise ChainError(
                f"Unknown CS type {cs_type!r}; must be one of {sorted(VALID_CS_TYPES)}"
            )
        if handedness not in VALID_HANDEDNESS:
            raise ChainError(
                f"Unknown handedness {handedness!r}; must be 'right' or 'left'"
            )
        self.name = name
        self.cs_type = cs_type
        self.handedness = handedness

    def __repr__(self):
        return f"CoordinateSystem({self.name!r}, {self.cs_type!r}, {self.handedness!r})"


class Transformation:
    """A directional link between two registered coordinate systems."""

    def __init__(self, source, target, xform_type, bidirectional=True):
        if source == target:
            raise ChainError(
                f"Self-loop transformation from {source!r} to itself is structurally invalid"
            )
        if xform_type not in VALID_XFORM_TYPES:
            raise ChainError(
                f"Unknown transformation type {xform_type!r}; must be one of {sorted(VALID_XFORM_TYPES)}"
            )
        self.source = source
        self.target = target
        self.xform_type = xform_type
        self.bidirectional = bidirectional

    def __repr__(self):
        arrow = "<->" if self.bidirectional else "->"
        return f"Transformation({self.source!r} {arrow} {self.target!r}, {self.xform_type!r})"


class ChainAnalyzer:
    """Builds and analyses coordinate system transformation chains per §5.2.3."""

    def __init__(self):
        self._systems = {}
        self._transforms = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add_system(self, system):
        """Register a CoordinateSystem. Raises ChainError on duplicate name."""
        if not isinstance(system, CoordinateSystem):
            raise ChainError("system must be a CoordinateSystem instance")
        if system.name in self._systems:
            raise ChainError(f"Coordinate system {system.name!r} is already registered")
        self._systems[system.name] = system

    def add_transformation(self, transform):
        """Register a Transformation. Both endpoints must already be registered."""
        if not isinstance(transform, Transformation):
            raise ChainError("transform must be a Transformation instance")
        for name in (transform.source, transform.target):
            if name not in self._systems:
                raise ChainError(
                    f"Coordinate system {name!r} is not registered; register it before adding links"
                )
        self._transforms.append(transform)

    # ------------------------------------------------------------------
    # Internal graph builders
    # ------------------------------------------------------------------

    def _undirected_adjacency(self):
        """Adjacency map used for chain finding (bidirectional traversal)."""
        adj = {name: set() for name in self._systems}
        for t in self._transforms:
            adj[t.source].add(t.target)
            if t.bidirectional:
                adj[t.target].add(t.source)
        return adj

    def _directed_adjacency(self):
        """Adjacency map used for cycle detection (directed edges only)."""
        adj = {name: [] for name in self._systems}
        for t in self._transforms:
            adj[t.source].append(t.target)
        return adj

    # ------------------------------------------------------------------
    # Chain finding
    # ------------------------------------------------------------------

    def find_chain(self, source_name, target_name):
        """Return the shortest ordered list of CS names from source to target.

        Raises ChainError if either name is unregistered or no path exists.
        Returns a single-element list when source equals target.
        """
        for name in (source_name, target_name):
            if name not in self._systems:
                raise ChainError(f"Coordinate system {name!r} is not registered")
        if source_name == target_name:
            return [source_name]
        adj = self._undirected_adjacency()
        queue = deque([[source_name]])
        visited = {source_name}
        while queue:
            path = queue.popleft()
            current = path[-1]
            for neighbor in sorted(adj[current]):
                if neighbor == target_name:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        raise ChainError(
            f"No transformation chain exists between {source_name!r} and {target_name!r}"
        )

    # ------------------------------------------------------------------
    # Completeness verification
    # ------------------------------------------------------------------

    def verify_completeness(self, user_names, root_name):
        """Check that every user CS has a chain to the root CS.

        Returns a dict:
          complete  bool    — True when all users have a resolved chain
          chains    dict    — user_name -> list of CS names (or None if missing)
          missing   list    — user names with no path to root
        Raises ChainError for an unregistered root or user name.
        """
        if root_name not in self._systems:
            raise ChainError(f"Root coordinate system {root_name!r} is not registered")
        chains = {}
        missing = []
        for user in user_names:
            if user not in self._systems:
                raise ChainError(f"User coordinate system {user!r} is not registered")
            try:
                chains[user] = self.find_chain(user, root_name)
            except ChainError:
                chains[user] = None
                missing.append(user)
        return {
            "complete": len(missing) == 0,
            "chains": chains,
            "missing": missing,
        }

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def detect_cycles(self):
        """Find directed cycles in the transformation graph.

        Returns a list of cycles; each cycle is an ordered list of CS names
        where the first and last element are the same node (the node where
        the back-edge was detected). Returns an empty list when no cycles exist.
        """
        adj = self._directed_adjacency()
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {name: WHITE for name in self._systems}
        cycles = []
        path = []

        def dfs(node):
            color[node] = GRAY
            path.append(node)
            for neighbor in sorted(adj[node]):
                if color[neighbor] == GRAY:
                    idx = path.index(neighbor)
                    cycles.append(list(path[idx:]) + [neighbor])
                elif color[neighbor] == WHITE:
                    dfs(neighbor)
            path.pop()
            color[node] = BLACK

        for node in sorted(self._systems):
            if color[node] == WHITE:
                dfs(node)
        return cycles

    # ------------------------------------------------------------------
    # Handedness consistency
    # ------------------------------------------------------------------

    def check_handedness_consistency(self, chain):
        """Check that all CS in chain share the same handedness.

        chain: ordered list of CS names (as returned by find_chain).
        Returns a dict:
          consistent  bool   — True when all handedness values match
          mismatches  list   — [(cs_name, handedness), ...] for non-matching entries
        Raises ChainError for any name not registered.
        """
        if not chain:
            return {"consistent": True, "mismatches": []}
        for name in chain:
            if name not in self._systems:
                raise ChainError(f"Coordinate system {name!r} is not registered")
        reference = self._systems[chain[0]].handedness
        mismatches = [
            (name, self._systems[name].handedness)
            for name in chain
            if self._systems[name].handedness != reference
        ]
        return {
            "consistent": len(mismatches) == 0,
            "mismatches": mismatches,
        }

    # ------------------------------------------------------------------
    # Full analysis
    # ------------------------------------------------------------------

    def analyze_all_chains(self, user_names, root_name):
        """Run the full §5.2.3 end-to-end chain analysis.

        Returns a structured report dict:
          complete        bool   — all users reachable
          missing_users   list   — users without a chain to root
          chains          dict   — user -> path list or None
          cycles          list   — detected directed cycles
          handedness      dict   — user -> {consistent, mismatches}
          compliant       bool   — True only when complete, acyclic, and handedness-consistent
        """
        completeness = self.verify_completeness(user_names, root_name)
        cycles = self.detect_cycles()
        handedness_results = {}
        for user, chain in completeness["chains"].items():
            if chain is not None:
                handedness_results[user] = self.check_handedness_consistency(chain)
            else:
                handedness_results[user] = {"consistent": None, "mismatches": []}
        all_handedness_ok = all(
            r["consistent"] is True for r in handedness_results.values()
        )
        return {
            "complete": completeness["complete"],
            "missing_users": completeness["missing"],
            "chains": completeness["chains"],
            "cycles": cycles,
            "handedness": handedness_results,
            "compliant": completeness["complete"] and len(cycles) == 0 and all_handedness_ok,
        }
