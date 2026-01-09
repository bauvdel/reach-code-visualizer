"""Dependency analysis for circular dependencies, dead code, and impact analysis."""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional
import networkx as nx

from ..graph.graph_queries import GraphQueries, Direction


@dataclass
class CircularDependency:
    """Represents a circular dependency cycle."""
    cycle: list[dict]  # List of nodes in the cycle
    cycle_length: int = 0
    severity: str = "medium"  # low, medium, high
    cycle_type: str = "unknown"  # call, signal, resource, etc.

    def format(self) -> str:
        """Format cycle for display."""
        lines = [
            f"CIRCULAR DEPENDENCY ({self.cycle_type}, {self.severity})",
            f"Length: {self.cycle_length} nodes",
            ""
        ]

        for i, node in enumerate(self.cycle):
            arrow = " → " if i < len(self.cycle) - 1 else " ↩"
            lines.append(f"  [{i+1}] {node['type']}: {node['name']}")
            lines.append(f"       @ {node['file']}:{node['line']}{arrow}")

        return "\n".join(lines)


@dataclass
class CircularDependencyResult:
    """Result of circular dependency detection."""
    total_cycles: int = 0
    cycles: list[CircularDependency] = field(default_factory=list)
    by_type: dict[str, int] = field(default_factory=dict)

    def format(self) -> str:
        """Format all cycles for display."""
        if self.total_cycles == 0:
            return "NO CIRCULAR DEPENDENCIES FOUND"

        lines = [
            f"CIRCULAR DEPENDENCIES DETECTED: {self.total_cycles}",
            "",
            "By type:"
        ]

        for cycle_type, count in sorted(self.by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {cycle_type}: {count}")

        lines.append("")

        for i, cycle in enumerate(self.cycles[:10], 1):
            lines.append(f"--- Cycle {i} ---")
            lines.append(cycle.format())
            lines.append("")

        if len(self.cycles) > 10:
            lines.append(f"... and {len(self.cycles) - 10} more cycles")

        return "\n".join(lines)


@dataclass
class DeadCodeResult:
    """Result of dead code detection."""
    total_unreachable: int = 0
    unreachable_functions: list[dict] = field(default_factory=list)
    unreachable_classes: list[dict] = field(default_factory=list)
    unreachable_signals: list[dict] = field(default_factory=list)
    entry_points_used: list[str] = field(default_factory=list)
    total_reachable: int = 0

    def format(self) -> str:
        """Format dead code results for display."""
        lines = [
            f"DEAD CODE ANALYSIS",
            f"Entry points: {len(self.entry_points_used)}",
            f"Reachable nodes: {self.total_reachable}",
            f"Potentially unreachable: {self.total_unreachable}",
            ""
        ]

        if self.unreachable_functions:
            lines.append(f"=== UNREACHABLE FUNCTIONS ({len(self.unreachable_functions)}) ===")
            for func in self.unreachable_functions[:20]:
                lines.append(f"  {func['name']}()")
                lines.append(f"       @ {func['file']}:{func['line']}")
            if len(self.unreachable_functions) > 20:
                lines.append(f"  ... and {len(self.unreachable_functions) - 20} more")
            lines.append("")

        if self.unreachable_classes:
            lines.append(f"=== UNREACHABLE CLASSES ({len(self.unreachable_classes)}) ===")
            for cls in self.unreachable_classes[:10]:
                lines.append(f"  class {cls['name']}")
                lines.append(f"       @ {cls['file']}:{cls['line']}")
            if len(self.unreachable_classes) > 10:
                lines.append(f"  ... and {len(self.unreachable_classes) - 10} more")
            lines.append("")

        if self.unreachable_signals:
            lines.append(f"=== UNUSED SIGNALS ({len(self.unreachable_signals)}) ===")
            for sig in self.unreachable_signals[:10]:
                lines.append(f"  signal {sig['name']}")
                lines.append(f"       @ {sig['file']}:{sig['line']}")
            if len(self.unreachable_signals) > 10:
                lines.append(f"  ... and {len(self.unreachable_signals) - 10} more")
            lines.append("")

        if self.total_unreachable == 0:
            lines.append("No obvious dead code detected!")

        return "\n".join(lines)


@dataclass
class ImpactResult:
    """Result of impact analysis."""
    node_id: str
    node_name: str
    node_type: str
    direct_impact: list[dict] = field(default_factory=list)
    indirect_impact: list[dict] = field(default_factory=list)
    total_affected: int = 0
    affected_files: set = field(default_factory=set)
    risk_level: str = "low"  # low, medium, high, critical

    def format(self) -> str:
        """Format impact analysis for display."""
        lines = [
            f"IMPACT ANALYSIS: {self.node_type} '{self.node_name}'",
            f"Risk Level: {self.risk_level.upper()}",
            f"Total affected nodes: {self.total_affected}",
            f"Affected files: {len(self.affected_files)}",
            ""
        ]

        if self.direct_impact:
            lines.append(f"=== DIRECT IMPACT ({len(self.direct_impact)}) ===")
            for item in self.direct_impact[:15]:
                lines.append(f"  [{item['relationship']}] {item['type']}: {item['name']}")
                lines.append(f"       @ {item['file']}:{item['line']}")
            if len(self.direct_impact) > 15:
                lines.append(f"  ... and {len(self.direct_impact) - 15} more")
            lines.append("")

        if self.indirect_impact:
            lines.append(f"=== INDIRECT IMPACT ({len(self.indirect_impact)}) ===")
            for item in self.indirect_impact[:15]:
                depth = item.get('depth', '?')
                lines.append(f"  [depth {depth}] {item['type']}: {item['name']}")
                lines.append(f"       @ {item['file']}:{item['line']}")
            if len(self.indirect_impact) > 15:
                lines.append(f"  ... and {len(self.indirect_impact) - 15} more")
            lines.append("")

        if self.affected_files:
            lines.append(f"=== AFFECTED FILES ({len(self.affected_files)}) ===")
            for f in sorted(self.affected_files)[:20]:
                lines.append(f"  {f}")
            if len(self.affected_files) > 20:
                lines.append(f"  ... and {len(self.affected_files) - 20} more")

        return "\n".join(lines)


class DependencyAnalyzer:
    """Analyzes dependencies for issues like cycles and dead code."""

    def __init__(self, graph: nx.DiGraph, queries: Optional[GraphQueries] = None):
        self.graph = graph
        self.queries = queries or GraphQueries(graph)

    def detect_circular_dependencies(
        self,
        edge_types: Optional[list[str]] = None,
        max_cycles: int = 50
    ) -> CircularDependencyResult:
        """Detect circular dependencies in the graph.

        Args:
            edge_types: Filter by edge types (CALLS, READS, etc.). None = all.
            max_cycles: Maximum number of cycles to return

        Returns:
            CircularDependencyResult with all detected cycles
        """
        result = CircularDependencyResult()

        # Build filtered subgraph if needed
        if edge_types:
            edges = [
                (u, v) for u, v, d in self.graph.edges(data=True)
                if d.get("relationship") in edge_types
            ]
            subgraph = nx.DiGraph(edges)
        else:
            subgraph = self.graph

        # Find all simple cycles
        try:
            cycles = list(nx.simple_cycles(subgraph))
        except Exception:
            return result

        # Process cycles
        for cycle_nodes in cycles[:max_cycles]:
            if len(cycle_nodes) < 2:
                continue

            cycle_data = []
            cycle_types = set()

            for i, node_id in enumerate(cycle_nodes):
                node_data = self.graph.nodes.get(node_id, {})
                cycle_data.append({
                    "id": node_id,
                    "name": node_data.get("name", node_id),
                    "type": node_data.get("type", "UNKNOWN"),
                    "file": self._short_path(node_data.get("file_path", "")),
                    "line": node_data.get("line_number", 0)
                })

                # Get edge type to next node
                next_idx = (i + 1) % len(cycle_nodes)
                edge_data = self.graph.get_edge_data(node_id, cycle_nodes[next_idx], {})
                cycle_types.add(edge_data.get("relationship", "UNKNOWN"))

            # Determine cycle type
            if "CALLS" in cycle_types:
                cycle_type = "call"
            elif "EMITS" in cycle_types or "CONNECTS_TO" in cycle_types:
                cycle_type = "signal"
            elif "REFERENCES" in cycle_types:
                cycle_type = "resource"
            else:
                cycle_type = "data"

            # Determine severity
            if len(cycle_nodes) <= 2:
                severity = "high"
            elif len(cycle_nodes) <= 4:
                severity = "medium"
            else:
                severity = "low"

            cycle = CircularDependency(
                cycle=cycle_data,
                cycle_length=len(cycle_nodes),
                severity=severity,
                cycle_type=cycle_type
            )
            result.cycles.append(cycle)

            # Track by type
            result.by_type[cycle_type] = result.by_type.get(cycle_type, 0) + 1

        result.total_cycles = len(result.cycles)
        return result

    def detect_dead_code(
        self,
        entry_points: Optional[list[str]] = None
    ) -> DeadCodeResult:
        """Detect potentially dead (unreachable) code.

        Args:
            entry_points: List of glob patterns for entry point files.
                         Default: autoload files, _ready(), _process(), etc.

        Returns:
            DeadCodeResult with unreachable nodes
        """
        result = DeadCodeResult()

        # Default entry points
        if entry_points is None:
            entry_points = [
                "**/autoload/*.gd",
                "**/main.tscn",
                "**/main.gd"
            ]

        # Find entry point nodes
        entry_node_ids = set()

        for node_id, data in self.graph.nodes(data=True):
            file_path = data.get("file_path", "")
            node_type = data.get("type", "")
            node_name = data.get("name", "")

            # Check if file matches entry point patterns
            for pattern in entry_points:
                if fnmatch(self._short_path(file_path), pattern):
                    entry_node_ids.add(node_id)
                    break

            # Godot lifecycle methods are always entry points
            if node_type == "FUNCTION" and node_name in (
                "_ready", "_process", "_physics_process", "_input",
                "_unhandled_input", "_notification", "_init",
                "_enter_tree", "_exit_tree"
            ):
                entry_node_ids.add(node_id)

            # Scene files are entry points
            if node_type == "SCENE":
                entry_node_ids.add(node_id)

            # Signal handlers connected in scenes are entry points
            if node_type == "SIGNAL_CONNECTION":
                metadata = data.get("metadata", {})
                if metadata.get("defined_in_scene"):
                    entry_node_ids.add(node_id)

        result.entry_points_used = [
            self.graph.nodes[nid].get("name", nid) for nid in list(entry_node_ids)[:20]
        ]

        # Build reachability from entry points
        reachable = set()
        to_visit = list(entry_node_ids)

        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue
            reachable.add(current)

            # Add all nodes reachable via outgoing edges
            for _, target in self.graph.out_edges(current):
                if target not in reachable:
                    to_visit.append(target)

            # Also add nodes that this node references (incoming REFERENCES edges mean the target is used)
            for source, _ in self.graph.in_edges(current):
                edge_data = self.graph.get_edge_data(source, current, {})
                # If something calls or references this, it's reachable
                if edge_data.get("relationship") in ("CALLS", "REFERENCES", "CONNECTS_TO"):
                    if source not in reachable:
                        to_visit.append(source)

        result.total_reachable = len(reachable)

        # Find unreachable nodes
        for node_id, data in self.graph.nodes(data=True):
            if node_id in reachable:
                continue

            node_type = data.get("type", "")
            node_name = data.get("name", "")
            file_path = self._short_path(data.get("file_path", ""))

            # Skip certain types that are often false positives
            if node_type in ("NODE_REFERENCE", "RESOURCE", "AMBIGUOUS", "UNKNOWN"):
                continue

            # Skip private functions that might be dynamically called
            if node_type == "FUNCTION" and node_name.startswith("_") and node_name not in (
                "_ready", "_process", "_physics_process"
            ):
                continue

            node_info = {
                "id": node_id,
                "name": node_name,
                "type": node_type,
                "file": file_path,
                "line": data.get("line_number", 0)
            }

            if node_type == "FUNCTION":
                result.unreachable_functions.append(node_info)
            elif node_type == "CLASS":
                result.unreachable_classes.append(node_info)
            elif node_type == "SIGNAL":
                # Check if signal is ever emitted or connected
                has_emitter = any(
                    self.graph.get_edge_data(s, node_id, {}).get("relationship") == "EMITS"
                    for s, _ in self.graph.in_edges(node_id)
                )
                has_connection = any(
                    self.graph.get_edge_data(node_id, t, {}).get("relationship") == "CONNECTS_TO"
                    for _, t in self.graph.out_edges(node_id)
                )
                if not has_emitter and not has_connection:
                    result.unreachable_signals.append(node_info)

        result.total_unreachable = (
            len(result.unreachable_functions) +
            len(result.unreachable_classes) +
            len(result.unreachable_signals)
        )

        return result

    def analyze_impact(
        self,
        node_id: str,
        depth: int = 3
    ) -> ImpactResult:
        """Analyze what would be affected if a node changed.

        Args:
            node_id: Node to analyze
            depth: How deep to trace impact

        Returns:
            ImpactResult with affected nodes
        """
        node_data = self.graph.nodes.get(node_id, {})

        result = ImpactResult(
            node_id=node_id,
            node_name=node_data.get("name", node_id),
            node_type=node_data.get("type", "UNKNOWN")
        )

        if node_id not in self.graph:
            return result

        # Direct impact: immediate dependencies (what depends on this node)
        for source, _ in self.graph.in_edges(node_id):
            source_data = self.graph.nodes.get(source, {})
            edge_data = self.graph.get_edge_data(source, node_id, {})

            file_path = self._short_path(source_data.get("file_path", ""))
            result.direct_impact.append({
                "id": source,
                "name": source_data.get("name", source),
                "type": source_data.get("type", "UNKNOWN"),
                "file": file_path,
                "line": source_data.get("line_number", 0),
                "relationship": edge_data.get("relationship", "UNKNOWN")
            })

            if file_path:
                result.affected_files.add(file_path)

        # Indirect impact: transitive dependencies
        visited = {node_id}
        current_level = [node_id]

        for d in range(1, depth + 1):
            next_level = []
            for current_id in current_level:
                for source, _ in self.graph.in_edges(current_id):
                    if source in visited:
                        continue
                    visited.add(source)

                    source_data = self.graph.nodes.get(source, {})
                    file_path = self._short_path(source_data.get("file_path", ""))

                    # Only add to indirect if not in direct
                    if source not in [d["id"] for d in result.direct_impact]:
                        result.indirect_impact.append({
                            "id": source,
                            "name": source_data.get("name", source),
                            "type": source_data.get("type", "UNKNOWN"),
                            "file": file_path,
                            "line": source_data.get("line_number", 0),
                            "depth": d
                        })

                    if file_path:
                        result.affected_files.add(file_path)

                    next_level.append(source)

            current_level = next_level

        result.total_affected = len(result.direct_impact) + len(result.indirect_impact)

        # Determine risk level
        if result.total_affected > 50 or len(result.affected_files) > 10:
            result.risk_level = "critical"
        elif result.total_affected > 20 or len(result.affected_files) > 5:
            result.risk_level = "high"
        elif result.total_affected > 5:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"

        return result

    def find_highly_coupled_nodes(self, min_connections: int = 10) -> list[dict]:
        """Find nodes with many connections (potential coupling issues).

        Args:
            min_connections: Minimum number of connections

        Returns:
            List of highly coupled nodes
        """
        results = []

        for node_id in self.graph.nodes():
            in_degree = self.graph.in_degree(node_id)
            out_degree = self.graph.out_degree(node_id)
            total = in_degree + out_degree

            if total >= min_connections:
                data = self.graph.nodes[node_id]
                results.append({
                    "id": node_id,
                    "name": data.get("name", node_id),
                    "type": data.get("type", "UNKNOWN"),
                    "file": self._short_path(data.get("file_path", "")),
                    "line": data.get("line_number", 0),
                    "in_degree": in_degree,
                    "out_degree": out_degree,
                    "total_connections": total
                })

        results.sort(key=lambda x: -x["total_connections"])
        return results

    def _short_path(self, file_path: str) -> str:
        """Shorten file path for display."""
        if not file_path:
            return ""
        for prefix in ["F:/Reach/", "F:\\Reach\\", "/", "\\"]:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break
        return file_path.replace("\\", "/")
