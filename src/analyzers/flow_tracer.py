"""Flow tracing for variables, execution paths, and signals."""

from dataclasses import dataclass, field
from typing import Optional
import networkx as nx

from ..graph.graph_queries import GraphQueries


@dataclass
class FlowStep:
    """Single step in a flow trace."""
    node_id: str
    node_name: str
    node_type: str
    file_path: str
    line_number: int
    action: str  # READ, WRITE, EMIT, CONNECT, CALL, etc.
    context: str = ""
    code_snippet: str = ""


@dataclass
class VariableFlowResult:
    """Result of tracing a variable through the codebase."""
    variable_name: str
    variable_id: Optional[str] = None
    found: bool = False
    definition: Optional[FlowStep] = None
    writes: list[FlowStep] = field(default_factory=list)
    reads: list[FlowStep] = field(default_factory=list)
    total_usages: int = 0

    def format(self) -> str:
        """Format variable flow for display."""
        if not self.found:
            return f"VARIABLE NOT FOUND: '{self.variable_name}'"

        lines = [
            f"VARIABLE FLOW: '{self.variable_name}'",
            f"Total usages: {self.total_usages}",
            ""
        ]

        if self.definition:
            lines.extend([
                "=== DEFINITION ===",
                f"  {self.definition.node_type}: {self.definition.node_name}",
                f"  @ {self.definition.file_path}:{self.definition.line_number}",
                ""
            ])

        if self.writes:
            lines.append(f"=== WRITES ({len(self.writes)}) ===")
            for step in self.writes:
                lines.append(f"  [{step.action}] in {step.node_name}")
                lines.append(f"       @ {step.file_path}:{step.line_number}")
                if step.context:
                    lines.append(f"       {step.context[:60]}")
            lines.append("")

        if self.reads:
            lines.append(f"=== READS ({len(self.reads)}) ===")
            for step in self.reads:
                lines.append(f"  [{step.action}] in {step.node_name}")
                lines.append(f"       @ {step.file_path}:{step.line_number}")
                if step.context:
                    lines.append(f"       {step.context[:60]}")
            lines.append("")

        return "\n".join(lines)


@dataclass
class ExecutionPathResult:
    """Result of tracing execution from function A to function B."""
    start_function: str
    end_function: str
    found: bool = False
    paths: list[list[FlowStep]] = field(default_factory=list)
    total_paths: int = 0
    shortest_length: int = 0

    def format(self) -> str:
        """Format execution path for display."""
        if not self.found:
            return f"NO EXECUTION PATH: {self.start_function} → {self.end_function}"

        lines = [
            f"EXECUTION PATH: {self.start_function} → {self.end_function}",
            f"Paths found: {self.total_paths}, Shortest: {self.shortest_length} calls",
            ""
        ]

        for i, path in enumerate(self.paths[:5], 1):
            lines.append(f"=== Path {i} ===")
            for j, step in enumerate(path):
                indent = "  " * j
                arrow = "└─>" if j > 0 else ""
                lines.append(f"{indent}{arrow} {step.node_name}()")
                lines.append(f"{indent}    @ {step.file_path}:{step.line_number}")
                if step.action and j < len(path) - 1:
                    lines.append(f"{indent}    {step.action}")
            lines.append("")

        if self.total_paths > 5:
            lines.append(f"... and {self.total_paths - 5} more paths")

        return "\n".join(lines)


@dataclass
class SignalFlowResult:
    """Result of tracing a signal through the codebase."""
    signal_name: str
    signal_id: Optional[str] = None
    found: bool = False
    definition: Optional[FlowStep] = None
    emissions: list[FlowStep] = field(default_factory=list)
    connections: list[dict] = field(default_factory=list)  # signal -> handler mappings
    handlers: list[FlowStep] = field(default_factory=list)

    def format(self) -> str:
        """Format signal flow for display."""
        if not self.found:
            return f"SIGNAL NOT FOUND: '{self.signal_name}'"

        lines = [
            f"SIGNAL FLOW: '{self.signal_name}'",
            ""
        ]

        if self.definition:
            lines.extend([
                "=== DEFINITION ===",
                f"  signal {self.definition.node_name}",
                f"  @ {self.definition.file_path}:{self.definition.line_number}",
                ""
            ])

        if self.emissions:
            lines.append(f"=== EMITTED BY ({len(self.emissions)}) ===")
            for step in self.emissions:
                lines.append(f"  {step.node_name}()")
                lines.append(f"       @ {step.file_path}:{step.line_number}")
                if step.context:
                    lines.append(f"       {step.context[:60]}")
            lines.append("")

        if self.connections:
            lines.append(f"=== CONNECTIONS ({len(self.connections)}) ===")
            for conn in self.connections:
                lines.append(f"  {conn['signal']} → {conn['handler']}()")
                lines.append(f"       @ {conn['file']}:{conn['line']}")
                if conn.get('defined_in'):
                    lines.append(f"       Defined in: {conn['defined_in']}")
            lines.append("")

        if self.handlers:
            lines.append(f"=== HANDLERS ({len(self.handlers)}) ===")
            for step in self.handlers:
                lines.append(f"  {step.node_name}()")
                lines.append(f"       @ {step.file_path}:{step.line_number}")
            lines.append("")

        return "\n".join(lines)


class FlowTracer:
    """Traces data and execution flow through the codebase."""

    def __init__(self, graph: nx.DiGraph, queries: Optional[GraphQueries] = None):
        self.graph = graph
        self.queries = queries or GraphQueries(graph)

    def trace_variable_flow(
        self,
        variable_name: str,
        starting_file: Optional[str] = None
    ) -> VariableFlowResult:
        """Trace a variable through all its reads and writes.

        Args:
            variable_name: Name of the variable to trace
            starting_file: Optional file to narrow search

        Returns:
            VariableFlowResult with all usages
        """
        result = VariableFlowResult(variable_name=variable_name)

        # Find all variable nodes matching the name
        matches = self.queries.find_node_by_name(
            variable_name,
            node_type="VARIABLE",
            file_pattern=starting_file
        )

        if not matches:
            return result

        result.found = True

        # Process each matching variable
        for var_match in matches:
            var_id = var_match["id"]
            result.variable_id = var_id

            # Get the variable definition
            var_data = self.graph.nodes.get(var_id, {})
            result.definition = FlowStep(
                node_id=var_id,
                node_name=var_match["name"],
                node_type="VARIABLE",
                file_path=self._short_path(var_match["file"]),
                line_number=var_match["line"],
                action="DEFINE",
                code_snippet=var_data.get("code_snippet", "")
            )

            # Find all edges pointing to this variable
            for source, _ in self.graph.in_edges(var_id):
                source_data = self.graph.nodes.get(source, {})
                edge_data = self.graph.get_edge_data(source, var_id, {})
                relationship = edge_data.get("relationship", "")

                step = FlowStep(
                    node_id=source,
                    node_name=source_data.get("name", source),
                    node_type=source_data.get("type", "UNKNOWN"),
                    file_path=self._short_path(source_data.get("file_path", "")),
                    line_number=source_data.get("line_number", 0),
                    action=relationship,
                    context=edge_data.get("context", "")
                )

                if relationship == "WRITES":
                    result.writes.append(step)
                elif relationship == "READS":
                    result.reads.append(step)

        result.total_usages = len(result.writes) + len(result.reads)
        return result

    def trace_execution_path(
        self,
        start_function: str,
        end_function: str,
        max_depth: int = 10
    ) -> ExecutionPathResult:
        """Trace execution path from one function to another.

        Args:
            start_function: Starting function name
            end_function: Ending function name
            max_depth: Maximum call depth

        Returns:
            ExecutionPathResult with all paths
        """
        result = ExecutionPathResult(
            start_function=start_function,
            end_function=end_function
        )

        # Find function nodes
        start_matches = self.queries.find_node_by_name(start_function, node_type="FUNCTION")
        end_matches = self.queries.find_node_by_name(end_function, node_type="FUNCTION")

        if not start_matches or not end_matches:
            return result

        # Build call-only subgraph for faster path finding
        call_edges = [
            (u, v) for u, v, d in self.graph.edges(data=True)
            if d.get("relationship") == "CALLS"
        ]
        call_graph = nx.DiGraph(call_edges)

        # Try all combinations of start/end
        all_paths = []
        for start_node in start_matches:
            for end_node in end_matches:
                start_id = start_node["id"]
                end_id = end_node["id"]

                if start_id not in call_graph or end_id not in call_graph:
                    continue

                try:
                    paths = list(nx.all_simple_paths(
                        call_graph, start_id, end_id, cutoff=max_depth
                    ))
                    all_paths.extend(paths)
                except nx.NetworkXNoPath:
                    continue

        if not all_paths:
            return result

        result.found = True
        result.total_paths = len(all_paths)
        result.shortest_length = min(len(p) - 1 for p in all_paths)

        # Convert paths to FlowSteps
        all_paths.sort(key=len)
        for path_nodes in all_paths[:5]:
            path_steps = []
            for i, node_id in enumerate(path_nodes):
                node_data = self.graph.nodes.get(node_id, {})

                action = ""
                if i < len(path_nodes) - 1:
                    edge_data = self.graph.get_edge_data(node_id, path_nodes[i+1], {})
                    action = f"CALLS {self.graph.nodes.get(path_nodes[i+1], {}).get('name', '?')}()"

                step = FlowStep(
                    node_id=node_id,
                    node_name=node_data.get("name", node_id),
                    node_type="FUNCTION",
                    file_path=self._short_path(node_data.get("file_path", "")),
                    line_number=node_data.get("line_number", 0),
                    action=action
                )
                path_steps.append(step)

            result.paths.append(path_steps)

        return result

    def trace_signal_flow(self, signal_name: str) -> SignalFlowResult:
        """Trace a signal from definition to all handlers.

        Args:
            signal_name: Name of the signal to trace

        Returns:
            SignalFlowResult with complete signal flow
        """
        result = SignalFlowResult(signal_name=signal_name)

        # Find signal definition
        signal_matches = self.queries.find_node_by_name(signal_name, node_type="SIGNAL")

        if not signal_matches:
            return result

        result.found = True

        for signal_match in signal_matches:
            signal_id = signal_match["id"]
            result.signal_id = signal_id

            signal_data = self.graph.nodes.get(signal_id, {})
            result.definition = FlowStep(
                node_id=signal_id,
                node_name=signal_match["name"],
                node_type="SIGNAL",
                file_path=self._short_path(signal_match["file"]),
                line_number=signal_match["line"],
                action="DEFINE",
                code_snippet=signal_data.get("code_snippet", "")
            )

            # Find emissions (functions that emit this signal)
            for source, _ in self.graph.in_edges(signal_id):
                source_data = self.graph.nodes.get(source, {})
                edge_data = self.graph.get_edge_data(source, signal_id, {})

                if edge_data.get("relationship") == "EMITS":
                    result.emissions.append(FlowStep(
                        node_id=source,
                        node_name=source_data.get("name", source),
                        node_type=source_data.get("type", "UNKNOWN"),
                        file_path=self._short_path(source_data.get("file_path", "")),
                        line_number=source_data.get("line_number", 0),
                        action="EMIT",
                        context=edge_data.get("context", "")
                    ))

            # Find connections (signal -> handler)
            for _, target in self.graph.out_edges(signal_id):
                target_data = self.graph.nodes.get(target, {})
                edge_data = self.graph.get_edge_data(signal_id, target, {})

                if edge_data.get("relationship") == "CONNECTS_TO":
                    # This is a SIGNAL_CONNECTION node
                    if target_data.get("type") == "SIGNAL_CONNECTION":
                        metadata = target_data.get("metadata", {})
                        result.connections.append({
                            "signal": signal_name,
                            "handler": metadata.get("handler", target_data.get("name", "")),
                            "file": self._short_path(target_data.get("file_path", "")),
                            "line": target_data.get("line_number", 0),
                            "defined_in": metadata.get("defined_in_scene", "code")
                        })

                        # Find the actual handler function
                        for _, handler in self.graph.out_edges(target):
                            handler_data = self.graph.nodes.get(handler, {})
                            if handler_data.get("type") == "FUNCTION":
                                result.handlers.append(FlowStep(
                                    node_id=handler,
                                    node_name=handler_data.get("name", handler),
                                    node_type="FUNCTION",
                                    file_path=self._short_path(handler_data.get("file_path", "")),
                                    line_number=handler_data.get("line_number", 0),
                                    action="HANDLE"
                                ))

        # Also search for SIGNAL_CONNECTION nodes that reference this signal
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == "SIGNAL_CONNECTION":
                metadata = data.get("metadata", {})
                if metadata.get("signal") == signal_name:
                    # Add connection if not already found
                    conn_key = (metadata.get("handler", ""), data.get("file_path", ""))
                    existing = [(c.get("handler"), c.get("file")) for c in result.connections]
                    if conn_key not in existing:
                        result.connections.append({
                            "signal": signal_name,
                            "handler": metadata.get("handler", ""),
                            "file": self._short_path(data.get("file_path", "")),
                            "line": data.get("line_number", 0),
                            "defined_in": "scene" if metadata.get("defined_in_scene") else "code"
                        })

        return result

    def _short_path(self, file_path: str) -> str:
        """Shorten file path for display."""
        if not file_path:
            return ""
        for prefix in ["F:/Reach/", "F:\\Reach\\", "/", "\\"]:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break
        return file_path.replace("\\", "/")
