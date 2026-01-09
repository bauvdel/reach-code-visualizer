"""Graph query system for finding paths, dependencies, and usages."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Iterator
import networkx as nx

from ..parsers.base_parser import NodeType, EdgeType, Confidence


class Direction(Enum):
    """Direction for dependency traversal."""
    FORWARD = "forward"    # What does this node affect?
    BACKWARD = "backward"  # What affects this node?
    BOTH = "both"


@dataclass
class PathStep:
    """Single step in a path."""
    node_id: str
    node_name: str
    node_type: str
    file_path: str
    line_number: int
    edge_type: Optional[str] = None  # Edge to next node
    edge_context: Optional[str] = None
    confidence: str = "high"


@dataclass
class PathResult:
    """Result of a path query."""
    source: str
    target: str
    found: bool
    paths: list[list[PathStep]] = field(default_factory=list)
    total_paths: int = 0
    shortest_length: int = 0
    confidence: str = "high"

    def format(self, max_paths: int = 3) -> str:
        """Format path result for display."""
        if not self.found:
            return f"NO PATH FOUND: {self.source} → {self.target}"

        lines = [
            f"PATH FOUND: {self.source} → {self.target}",
            f"Total paths: {self.total_paths}, Shortest: {self.shortest_length} hops",
            f"Confidence: {self.confidence.upper()}",
            ""
        ]

        for i, path in enumerate(self.paths[:max_paths], 1):
            lines.append(f"=== Path {i} ({len(path)-1} hops) ===")
            for j, step in enumerate(path):
                prefix = f"[{j+1}]" if j == 0 else "    └─"
                edge_info = f" {step.edge_type} →" if step.edge_type else ""
                lines.append(f"{prefix} {step.node_type}: {step.node_name}")
                lines.append(f"       @ {step.file_path}:{step.line_number}")
                if step.edge_type and j < len(path) - 1:
                    lines.append(f"       {edge_info}")
            lines.append("")

        if self.total_paths > max_paths:
            lines.append(f"... and {self.total_paths - max_paths} more paths")

        return "\n".join(lines)


@dataclass
class DependencyResult:
    """Result of a dependency query."""
    node_id: str
    node_name: str
    direction: Direction
    depth: int
    dependencies: list[dict] = field(default_factory=list)
    total_count: int = 0

    def format(self) -> str:
        """Format dependency result for display."""
        direction_str = {
            Direction.FORWARD: "depends on (affects)",
            Direction.BACKWARD: "depended upon by (affected by)",
            Direction.BOTH: "related to"
        }[self.direction]

        lines = [
            f"DEPENDENCIES: {self.node_name}",
            f"Direction: {direction_str}",
            f"Depth: {self.depth}, Total: {self.total_count}",
            ""
        ]

        # Group by depth level
        by_depth: dict[int, list] = {}
        for dep in self.dependencies:
            d = dep.get("depth", 1)
            if d not in by_depth:
                by_depth[d] = []
            by_depth[d].append(dep)

        for depth_level in sorted(by_depth.keys()):
            lines.append(f"--- Depth {depth_level} ---")
            for dep in by_depth[depth_level]:
                edge = dep.get("edge_type", "?")
                lines.append(f"  [{edge}] {dep['type']}: {dep['name']}")
                lines.append(f"         @ {dep['file']}:{dep['line']}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class UsageResult:
    """Result of a usage query."""
    node_id: str
    node_name: str
    node_type: str
    usages: list[dict] = field(default_factory=list)
    total_count: int = 0

    def format(self) -> str:
        """Format usage result for display."""
        lines = [
            f"USAGES OF: {self.node_type} '{self.node_name}'",
            f"Total usages: {self.total_count}",
            ""
        ]

        # Group by usage type
        by_type: dict[str, list] = {}
        for usage in self.usages:
            ut = usage.get("edge_type", "UNKNOWN")
            if ut not in by_type:
                by_type[ut] = []
            by_type[ut].append(usage)

        for usage_type, items in sorted(by_type.items()):
            lines.append(f"--- {usage_type} ({len(items)}) ---")
            for item in items:
                lines.append(f"  {item['type']}: {item['name']}")
                lines.append(f"       @ {item['file']}:{item['line']}")
                if item.get("context"):
                    lines.append(f"       Context: {item['context'][:60]}")
            lines.append("")

        return "\n".join(lines)


class GraphQueries:
    """Query engine for the code graph."""

    def __init__(self, graph: nx.DiGraph):
        self.graph = graph

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 10,
        max_paths: int = 10
    ) -> PathResult:
        """Find all paths between two nodes.

        Args:
            source_id: Starting node ID
            target_id: Ending node ID
            max_depth: Maximum path length
            max_paths: Maximum number of paths to return

        Returns:
            PathResult with all found paths
        """
        result = PathResult(
            source=self._get_node_display_name(source_id),
            target=self._get_node_display_name(target_id),
            found=False
        )

        if source_id not in self.graph or target_id not in self.graph:
            return result

        try:
            # Find all simple paths up to max_depth
            all_paths = list(nx.all_simple_paths(
                self.graph, source_id, target_id, cutoff=max_depth
            ))

            if not all_paths:
                return result

            result.found = True
            result.total_paths = len(all_paths)
            result.shortest_length = min(len(p) - 1 for p in all_paths)

            # Sort by length and take top paths
            all_paths.sort(key=len)

            # Calculate overall confidence
            confidences = []

            for path_nodes in all_paths[:max_paths]:
                path_steps = []
                path_confidence = "high"

                for i, node_id in enumerate(path_nodes):
                    node_data = self.graph.nodes.get(node_id, {})
                    step = PathStep(
                        node_id=node_id,
                        node_name=node_data.get("name", node_id),
                        node_type=node_data.get("type", "UNKNOWN"),
                        file_path=self._short_path(node_data.get("file_path", "")),
                        line_number=node_data.get("line_number", 0),
                        confidence=node_data.get("confidence", "high")
                    )

                    # Add edge info to previous step
                    if i > 0 and path_steps:
                        edge_data = self.graph.get_edge_data(path_nodes[i-1], node_id, {})
                        path_steps[-1].edge_type = edge_data.get("relationship", "?")
                        path_steps[-1].edge_context = edge_data.get("context", "")

                        # Track confidence
                        edge_conf = edge_data.get("confidence", "high")
                        if edge_conf in ("low", "ambiguous"):
                            path_confidence = "medium" if path_confidence == "high" else "low"

                    path_steps.append(step)

                confidences.append(path_confidence)
                result.paths.append(path_steps)

            # Overall confidence is the worst among paths
            if "low" in confidences:
                result.confidence = "low"
            elif "medium" in confidences:
                result.confidence = "medium"

        except nx.NetworkXNoPath:
            pass

        return result

    def find_dependencies(
        self,
        node_id: str,
        direction: Direction = Direction.BOTH,
        depth: int = 5
    ) -> DependencyResult:
        """Find all dependencies of a node.

        Args:
            node_id: Node to analyze
            direction: Forward (what it affects), backward (what affects it), or both
            depth: How many hops to traverse

        Returns:
            DependencyResult with all dependencies
        """
        node_data = self.graph.nodes.get(node_id, {})
        result = DependencyResult(
            node_id=node_id,
            node_name=node_data.get("name", node_id),
            direction=direction,
            depth=depth
        )

        if node_id not in self.graph:
            return result

        visited = set()
        to_visit = [(node_id, 0, None, None)]  # (id, depth, edge_type, from_id)

        while to_visit:
            current_id, current_depth, edge_type, from_id = to_visit.pop(0)

            if current_id in visited or current_depth > depth:
                continue

            visited.add(current_id)

            # Don't add the starting node
            if current_id != node_id:
                data = self.graph.nodes.get(current_id, {})
                result.dependencies.append({
                    "id": current_id,
                    "name": data.get("name", current_id),
                    "type": data.get("type", "UNKNOWN"),
                    "file": self._short_path(data.get("file_path", "")),
                    "line": data.get("line_number", 0),
                    "depth": current_depth,
                    "edge_type": edge_type,
                    "confidence": data.get("confidence", "high")
                })

            # Get neighbors based on direction
            if direction in (Direction.FORWARD, Direction.BOTH):
                for _, neighbor in self.graph.out_edges(current_id):
                    if neighbor not in visited:
                        edge_data = self.graph.get_edge_data(current_id, neighbor, {})
                        to_visit.append((
                            neighbor,
                            current_depth + 1,
                            edge_data.get("relationship"),
                            current_id
                        ))

            if direction in (Direction.BACKWARD, Direction.BOTH):
                for neighbor, _ in self.graph.in_edges(current_id):
                    if neighbor not in visited:
                        edge_data = self.graph.get_edge_data(neighbor, current_id, {})
                        to_visit.append((
                            neighbor,
                            current_depth + 1,
                            edge_data.get("relationship"),
                            current_id
                        ))

        result.total_count = len(result.dependencies)
        return result

    def find_usages(self, node_id: str) -> UsageResult:
        """Find all usages of a node (incoming edges).

        Args:
            node_id: Node to find usages of

        Returns:
            UsageResult with all usages
        """
        node_data = self.graph.nodes.get(node_id, {})
        result = UsageResult(
            node_id=node_id,
            node_name=node_data.get("name", node_id),
            node_type=node_data.get("type", "UNKNOWN")
        )

        if node_id not in self.graph:
            return result

        for source, _ in self.graph.in_edges(node_id):
            source_data = self.graph.nodes.get(source, {})
            edge_data = self.graph.get_edge_data(source, node_id, {})

            result.usages.append({
                "id": source,
                "name": source_data.get("name", source),
                "type": source_data.get("type", "UNKNOWN"),
                "file": self._short_path(source_data.get("file_path", "")),
                "line": source_data.get("line_number", 0),
                "edge_type": edge_data.get("relationship", "UNKNOWN"),
                "context": edge_data.get("context", ""),
                "confidence": edge_data.get("confidence", "high")
            })

        result.total_count = len(result.usages)
        return result

    def find_callers(self, function_id: str) -> UsageResult:
        """Find all functions that call this function.

        Args:
            function_id: Function node ID

        Returns:
            UsageResult with only CALLS relationships
        """
        result = self.find_usages(function_id)
        result.usages = [
            u for u in result.usages
            if u.get("edge_type") == "CALLS"
        ]
        result.total_count = len(result.usages)
        return result

    def find_callees(self, function_id: str) -> list[dict]:
        """Find all functions called by this function.

        Args:
            function_id: Function node ID

        Returns:
            List of called functions
        """
        if function_id not in self.graph:
            return []

        callees = []
        for _, target in self.graph.out_edges(function_id):
            edge_data = self.graph.get_edge_data(function_id, target, {})
            if edge_data.get("relationship") == "CALLS":
                target_data = self.graph.nodes.get(target, {})
                callees.append({
                    "id": target,
                    "name": target_data.get("name", target),
                    "type": target_data.get("type", "UNKNOWN"),
                    "file": self._short_path(target_data.get("file_path", "")),
                    "line": target_data.get("line_number", 0),
                    "context": edge_data.get("context", "")
                })

        return callees

    def find_node_by_name(
        self,
        name: str,
        node_type: Optional[str] = None,
        file_pattern: Optional[str] = None,
        exact: bool = False
    ) -> list[dict]:
        """Find nodes by name with optional filters.

        Args:
            name: Name to search for
            node_type: Filter by node type (FUNCTION, VARIABLE, etc.)
            file_pattern: Filter by file path pattern
            exact: Require exact name match

        Returns:
            List of matching nodes
        """
        results = []
        name_lower = name.lower()

        for node_id, data in self.graph.nodes(data=True):
            node_name = data.get("name", "")

            # Name matching
            if exact:
                if node_name != name:
                    continue
            else:
                if name_lower not in node_name.lower():
                    continue

            # Type filter
            if node_type and data.get("type") != node_type:
                continue

            # File filter
            if file_pattern:
                file_path = data.get("file_path", "").lower()
                if file_pattern.lower() not in file_path:
                    continue

            results.append({
                "id": node_id,
                "name": node_name,
                "type": data.get("type", "UNKNOWN"),
                "file": self._short_path(data.get("file_path", "")),
                "line": data.get("line_number", 0),
                "confidence": data.get("confidence", "high")
            })

        return results

    def get_node_context(self, node_id: str) -> dict:
        """Get full context for a node including neighbors.

        Args:
            node_id: Node to get context for

        Returns:
            Dictionary with node data and relationships
        """
        if node_id not in self.graph:
            return {}

        data = dict(self.graph.nodes[node_id])
        data["id"] = node_id

        # Incoming edges
        data["incoming"] = []
        for source, _ in self.graph.in_edges(node_id):
            source_data = self.graph.nodes.get(source, {})
            edge_data = self.graph.get_edge_data(source, node_id, {})
            data["incoming"].append({
                "from_id": source,
                "from_name": source_data.get("name", source),
                "from_type": source_data.get("type"),
                "relationship": edge_data.get("relationship"),
                "context": edge_data.get("context")
            })

        # Outgoing edges
        data["outgoing"] = []
        for _, target in self.graph.out_edges(node_id):
            target_data = self.graph.nodes.get(target, {})
            edge_data = self.graph.get_edge_data(node_id, target, {})
            data["outgoing"].append({
                "to_id": target,
                "to_name": target_data.get("name", target),
                "to_type": target_data.get("type"),
                "relationship": edge_data.get("relationship"),
                "context": edge_data.get("context")
            })

        return data

    def _get_node_display_name(self, node_id: str) -> str:
        """Get display name for a node."""
        if node_id in self.graph:
            data = self.graph.nodes[node_id]
            return f"{data.get('name', node_id)}"
        return node_id

    def _short_path(self, file_path: str) -> str:
        """Shorten file path for display."""
        if not file_path:
            return ""
        # Remove common prefixes
        for prefix in ["F:/Reach/", "F:\\Reach\\", "/", "\\"]:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break
        return file_path.replace("\\", "/")
