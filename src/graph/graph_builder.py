"""Graph builder for constructing the code dependency graph."""

import json
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

import networkx as nx

from ..parsers.base_parser import (
    ParseResult,
    ParsedNode,
    ParsedEdge,
    NodeType,
    EdgeType,
    Confidence,
)
from ..parsers.gdscript_parser import GDScriptParser
from ..parsers.tscn_parser import TSCNParser
from ..utils.logger import setup_logger


@dataclass
class GraphStatistics:
    """Statistics about the code graph."""
    total_files: int = 0
    gdscript_files: int = 0
    tscn_files: int = 0
    typescript_files: int = 0

    total_nodes: int = 0
    total_edges: int = 0

    nodes_by_type: dict[str, int] = field(default_factory=dict)
    edges_by_type: dict[str, int] = field(default_factory=dict)

    ambiguous_nodes: int = 0
    low_confidence_edges: int = 0

    parse_errors: list[str] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "files": {
                "total": self.total_files,
                "gdscript": self.gdscript_files,
                "tscn": self.tscn_files,
                "typescript": self.typescript_files
            },
            "graph": {
                "total_nodes": self.total_nodes,
                "total_edges": self.total_edges,
                "nodes_by_type": self.nodes_by_type,
                "edges_by_type": self.edges_by_type,
            },
            "quality": {
                "ambiguous_nodes": self.ambiguous_nodes,
                "low_confidence_edges": self.low_confidence_edges,
                "parse_errors": len(self.parse_errors),
                "parse_warnings": len(self.parse_warnings)
            }
        }

    def __str__(self) -> str:
        """Human-readable summary."""
        lines = [
            "=== Graph Statistics ===",
            f"Files: {self.total_files} total ({self.gdscript_files} .gd, {self.tscn_files} .tscn)",
            f"Nodes: {self.total_nodes}",
            f"Edges: {self.total_edges}",
            "",
            "Nodes by type:"
        ]
        for node_type, count in sorted(self.nodes_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {node_type}: {count}")

        lines.extend([
            "",
            "Edges by type:"
        ])
        for edge_type, count in sorted(self.edges_by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {edge_type}: {count}")

        if self.ambiguous_nodes > 0 or self.low_confidence_edges > 0:
            lines.extend([
                "",
                "Quality warnings:",
                f"  Ambiguous nodes: {self.ambiguous_nodes}",
                f"  Low confidence edges: {self.low_confidence_edges}"
            ])

        if self.parse_errors:
            lines.extend([
                "",
                f"Parse errors: {len(self.parse_errors)}"
            ])

        return "\n".join(lines)


class GraphBuilder:
    """Builds and manages the code dependency graph."""

    def __init__(self, project_root: Path, config: Optional[dict] = None):
        """Initialize the graph builder.

        Args:
            project_root: Root directory of the project to analyze
            config: Optional configuration dictionary
        """
        self.project_root = Path(project_root)
        self.config = config or {}
        self.logger = setup_logger("graph_builder")

        # Initialize parsers
        self.gdscript_parser = GDScriptParser(self.project_root)
        self.tscn_parser = TSCNParser(self.project_root)

        # Initialize graph
        self.graph = nx.DiGraph()

        # Store parsed results
        self.parse_results: dict[str, ParseResult] = {}
        self.file_hashes: dict[str, str] = {}

        # Configuration
        self.include_patterns = self.config.get("include_patterns", ["**/*.gd", "**/*.tscn"])
        self.exclude_patterns = self.config.get("exclude_patterns", [
            "**/node_modules/**",
            "**/.godot/**",
            "**/build/**",
            "**/.git/**",
            "**/addons/**"
        ])

    def scan_files(self) -> list[Path]:
        """Scan project directory for files to parse.

        Returns:
            List of file paths matching include patterns and not excluded
        """
        files = []

        for pattern in self.include_patterns:
            for file_path in self.project_root.glob(pattern):
                if file_path.is_file() and not self._is_excluded(file_path):
                    files.append(file_path)

        return sorted(set(files))

    def _is_excluded(self, file_path: Path) -> bool:
        """Check if a file should be excluded from analysis."""
        rel_path = str(file_path.relative_to(self.project_root)).replace("\\", "/")

        for pattern in self.exclude_patterns:
            if fnmatch(rel_path, pattern):
                return True
            # Also check with leading slash
            if fnmatch(f"/{rel_path}", pattern):
                return True

        return False

    def build_graph(self, files: Optional[list[Path]] = None) -> GraphStatistics:
        """Build the complete code graph from project files.

        Args:
            files: Optional list of files to parse. If None, scans project.

        Returns:
            Statistics about the built graph
        """
        if files is None:
            files = self.scan_files()

        stats = GraphStatistics()
        stats.total_files = len(files)

        self.logger.info(f"Building graph from {len(files)} files...")

        for file_path in files:
            result = self._parse_file(file_path)

            if result is None:
                continue

            # Track file types
            if file_path.suffix == ".gd":
                stats.gdscript_files += 1
            elif file_path.suffix == ".tscn":
                stats.tscn_files += 1
            elif file_path.suffix in (".ts", ".js"):
                stats.typescript_files += 1

            # Store parse result
            self.parse_results[str(file_path)] = result

            # Add to graph
            self._add_parse_result_to_graph(result)

            # Track errors/warnings
            stats.parse_errors.extend(result.errors)
            stats.parse_warnings.extend(result.warnings)

        # Calculate statistics
        stats.total_nodes = self.graph.number_of_nodes()
        stats.total_edges = self.graph.number_of_edges()

        # Count by type
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get("type", "UNKNOWN")
            stats.nodes_by_type[node_type] = stats.nodes_by_type.get(node_type, 0) + 1

            if data.get("confidence") == "ambiguous":
                stats.ambiguous_nodes += 1

        for u, v, data in self.graph.edges(data=True):
            edge_type = data.get("relationship", "UNKNOWN")
            stats.edges_by_type[edge_type] = stats.edges_by_type.get(edge_type, 0) + 1

            if data.get("confidence") in ("low", "ambiguous"):
                stats.low_confidence_edges += 1

        self.logger.info(f"Graph built: {stats.total_nodes} nodes, {stats.total_edges} edges")

        return stats

    def _parse_file(self, file_path: Path) -> Optional[ParseResult]:
        """Parse a single file with the appropriate parser."""
        try:
            if file_path.suffix == ".gd":
                return self.gdscript_parser.parse_file(file_path)
            elif file_path.suffix == ".tscn":
                return self.tscn_parser.parse_file(file_path)
            else:
                self.logger.debug(f"No parser for {file_path.suffix}")
                return None
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}")
            result = ParseResult(
                file_path=str(file_path),
                file_hash=""
            )
            result.errors.append(str(e))
            return result

    def _add_parse_result_to_graph(self, result: ParseResult) -> None:
        """Add nodes and edges from a parse result to the graph."""
        # Add nodes
        for node in result.nodes:
            self.graph.add_node(
                node.id,
                type=node.type.name,
                name=node.name,
                file_path=node.file_path,
                line_number=node.line_number,
                language=node.language,
                code_snippet=node.code_snippet,
                metadata=node.metadata,
                confidence=node.confidence.value
            )

        # Add edges
        for edge in result.edges:
            # Only add edge if both nodes exist or will exist
            self.graph.add_edge(
                edge.source_id,
                edge.target_id,
                relationship=edge.relationship.name,
                context=edge.context,
                metadata=edge.metadata,
                confidence=edge.confidence.value
            )

    def get_node(self, node_id: str) -> Optional[dict]:
        """Get a node's data by ID."""
        if node_id in self.graph:
            return dict(self.graph.nodes[node_id])
        return None

    def get_node_by_name(self, name: str, node_type: Optional[NodeType] = None) -> list[dict]:
        """Find nodes by name (partial match)."""
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if name.lower() in data.get("name", "").lower():
                if node_type is None or data.get("type") == node_type.name:
                    results.append({"id": node_id, **data})
        return results

    def get_outgoing_edges(self, node_id: str) -> list[dict]:
        """Get all edges originating from a node."""
        edges = []
        if node_id in self.graph:
            for _, target, data in self.graph.out_edges(node_id, data=True):
                edges.append({
                    "target": target,
                    "target_data": dict(self.graph.nodes.get(target, {})),
                    **data
                })
        return edges

    def get_incoming_edges(self, node_id: str) -> list[dict]:
        """Get all edges pointing to a node."""
        edges = []
        if node_id in self.graph:
            for source, _, data in self.graph.in_edges(node_id, data=True):
                edges.append({
                    "source": source,
                    "source_data": dict(self.graph.nodes.get(source, {})),
                    **data
                })
        return edges

    def export_json(self, output_path: Path) -> None:
        """Export the graph to JSON format."""
        data = {
            "format": "reach_code_graph_v1",
            "project_root": str(self.project_root),
            "nodes": [],
            "edges": []
        }

        for node_id, node_data in self.graph.nodes(data=True):
            data["nodes"].append({
                "id": node_id,
                **node_data
            })

        for source, target, edge_data in self.graph.edges(data=True):
            data["edges"].append({
                "source": source,
                "target": target,
                **edge_data
            })

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Exported graph to {output_path}")

    def import_json(self, input_path: Path) -> None:
        """Import a graph from JSON format."""
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Clear existing graph
        self.graph.clear()

        # Add nodes
        for node in data.get("nodes", []):
            node_id = node.pop("id")
            self.graph.add_node(node_id, **node)

        # Add edges
        for edge in data.get("edges", []):
            source = edge.pop("source")
            target = edge.pop("target")
            self.graph.add_edge(source, target, **edge)

        self.logger.info(f"Imported graph from {input_path}")

    def clear(self) -> None:
        """Clear the graph and all cached data."""
        self.graph.clear()
        self.parse_results.clear()
        self.file_hashes.clear()
