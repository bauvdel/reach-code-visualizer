"""Flask web server for REACH Code Visualizer."""

import os
import re
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.graph import GraphBuilder, GraphQueries
from src.analyzers import FlowTracer, DependencyAnalyzer


def create_app(scan_path: str = "F:/Reach") -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder=None)
    CORS(app)

    # Store graph data in app context
    app.config["SCAN_PATH"] = scan_path
    app.config["GRAPH_BUILDER"] = None
    app.config["GRAPH_QUERIES"] = None
    app.config["FLOW_TRACER"] = None
    app.config["DEPENDENCY_ANALYZER"] = None

    frontend_path = Path(__file__).parent.parent.parent / "frontend"

    def get_builder() -> GraphBuilder:
        """Get or create graph builder."""
        if app.config["GRAPH_BUILDER"] is None:
            builder_config = {
                "exclude_patterns": [
                    "**/node_modules/**",
                    "**/.godot/**",
                    "**/build/**",
                    "**/.git/**",
                    "**/addons/**",
                    "**/tools/data-visualizer/**"
                ]
            }
            builder = GraphBuilder(app.config["SCAN_PATH"], builder_config)
            builder.build_graph()
            app.config["GRAPH_BUILDER"] = builder
            app.config["GRAPH_QUERIES"] = GraphQueries(builder.graph)
            app.config["FLOW_TRACER"] = FlowTracer(builder.graph, app.config["GRAPH_QUERIES"])
            app.config["DEPENDENCY_ANALYZER"] = DependencyAnalyzer(builder.graph, app.config["GRAPH_QUERIES"])
        return app.config["GRAPH_BUILDER"]

    def get_queries() -> GraphQueries:
        """Get graph queries instance."""
        get_builder()
        return app.config["GRAPH_QUERIES"]

    def get_tracer() -> FlowTracer:
        """Get flow tracer instance."""
        get_builder()
        return app.config["FLOW_TRACER"]

    def get_analyzer() -> DependencyAnalyzer:
        """Get dependency analyzer instance."""
        get_builder()
        return app.config["DEPENDENCY_ANALYZER"]

    def short_path(file_path: str) -> str:
        """Shorten file path for display."""
        if not file_path:
            return ""
        for prefix in ["F:/Reach/", "F:\\Reach\\", "/", "\\"]:
            if file_path.startswith(prefix):
                file_path = file_path[len(prefix):]
                break
        return file_path.replace("\\", "/")

    def get_code_snippet(file_path: str, line_number: int, context: int = 5) -> str:
        """Get code snippet from file."""
        if not file_path or line_number <= 0:
            return ""

        # Try to resolve the path
        full_path = file_path
        if not os.path.isabs(file_path):
            full_path = os.path.join(app.config["SCAN_PATH"], file_path)

        if not os.path.exists(full_path):
            return ""

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            start = max(0, line_number - context - 1)
            end = min(len(lines), line_number + context)

            snippet_lines = []
            for i in range(start, end):
                line_num = i + 1
                marker = "→ " if line_num == line_number else "  "
                snippet_lines.append(f"{marker}{line_num:4d} | {lines[i].rstrip()}")

            return "\n".join(snippet_lines)
        except Exception:
            return ""

    # =====================
    # Static File Routes
    # =====================

    @app.route("/")
    def index():
        """Serve main page."""
        return send_from_directory(frontend_path, "index.html")

    @app.route("/css/<path:filename>")
    def css(filename):
        """Serve CSS files."""
        return send_from_directory(frontend_path / "css", filename)

    @app.route("/js/<path:filename>")
    def js(filename):
        """Serve JavaScript files."""
        return send_from_directory(frontend_path / "js", filename)

    # =====================
    # API Routes
    # =====================

    @app.route("/api/graph")
    def get_graph():
        """Get full graph data as JSON."""
        builder = get_builder()
        graph = builder.graph

        # Get filter parameters
        node_type = request.args.get("type", "").upper()
        language = request.args.get("language", "").lower()
        limit = request.args.get("limit", type=int, default=500)

        nodes = []
        node_ids = set()

        for node_id, data in graph.nodes(data=True):
            # Apply filters
            if node_type and data.get("type") != node_type:
                continue
            if language and data.get("language", "").lower() != language:
                continue

            node_ids.add(node_id)
            nodes.append({
                "id": node_id,
                "name": data.get("name", node_id),
                "type": data.get("type", "UNKNOWN"),
                "file": short_path(data.get("file_path", "")),
                "line": data.get("line_number", 0),
                "language": data.get("language", ""),
                "confidence": data.get("confidence", "HIGH")
            })

            if len(nodes) >= limit:
                break

        edges = []
        for source, target, data in graph.edges(data=True):
            if source in node_ids and target in node_ids:
                edges.append({
                    "from": source,
                    "to": target,
                    "relationship": data.get("relationship", "UNKNOWN"),
                    "confidence": data.get("confidence", "HIGH")
                })

        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges()
        })

    @app.route("/api/node/<path:node_id>")
    def get_node(node_id: str):
        """Get detailed node information."""
        builder = get_builder()
        graph = builder.graph

        if node_id not in graph:
            return jsonify({"error": "Node not found"}), 404

        data = graph.nodes[node_id]
        file_path = data.get("file_path", "")
        line_number = data.get("line_number", 0)

        # Get relationships
        outgoing = []
        for _, target, edge_data in graph.out_edges(node_id, data=True):
            target_data = graph.nodes.get(target, {})
            outgoing.append({
                "relationship": edge_data.get("relationship", "UNKNOWN"),
                "target_id": target,
                "target_name": target_data.get("name", target),
                "target_type": target_data.get("type", "UNKNOWN")
            })

        incoming = []
        for source, _, edge_data in graph.in_edges(node_id, data=True):
            source_data = graph.nodes.get(source, {})
            incoming.append({
                "relationship": edge_data.get("relationship", "UNKNOWN"),
                "source_id": source,
                "source_name": source_data.get("name", source),
                "source_type": source_data.get("type", "UNKNOWN")
            })

        return jsonify({
            "id": node_id,
            "name": data.get("name", node_id),
            "type": data.get("type", "UNKNOWN"),
            "file": short_path(file_path),
            "full_path": file_path,
            "line": line_number,
            "language": data.get("language", ""),
            "confidence": data.get("confidence", "HIGH"),
            "code_snippet": get_code_snippet(file_path, line_number),
            "outgoing": outgoing,
            "incoming": incoming,
            "metadata": data.get("metadata", {})
        })

    @app.route("/api/stats")
    def get_stats():
        """Get graph statistics."""
        builder = get_builder()
        graph = builder.graph

        # Count by type
        type_counts = {}
        language_counts = {}
        confidence_counts = {}

        for _, data in graph.nodes(data=True):
            node_type = data.get("type", "UNKNOWN")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1

            language = data.get("language", "unknown")
            language_counts[language] = language_counts.get(language, 0) + 1

            confidence = data.get("confidence", "HIGH")
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        # Count edge types
        edge_counts = {}
        for _, _, data in graph.edges(data=True):
            rel = data.get("relationship", "UNKNOWN")
            edge_counts[rel] = edge_counts.get(rel, 0) + 1

        return jsonify({
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "nodes_by_type": type_counts,
            "nodes_by_language": language_counts,
            "nodes_by_confidence": confidence_counts,
            "edges_by_type": edge_counts
        })

    @app.route("/api/search")
    def search():
        """Fuzzy search for nodes by name."""
        query = request.args.get("q", "").lower()
        limit = request.args.get("limit", type=int, default=50)
        node_type = request.args.get("type", "").upper()

        if not query:
            return jsonify({"results": []})

        builder = get_builder()
        graph = builder.graph

        results = []
        for node_id, data in graph.nodes(data=True):
            name = data.get("name", "").lower()

            # Apply type filter
            if node_type and data.get("type") != node_type:
                continue

            # Simple fuzzy matching
            if query in name or query in node_id.lower():
                score = 100 if name == query else (90 if name.startswith(query) else 50)
                results.append({
                    "id": node_id,
                    "name": data.get("name", node_id),
                    "type": data.get("type", "UNKNOWN"),
                    "file": short_path(data.get("file_path", "")),
                    "line": data.get("line_number", 0),
                    "score": score
                })

        # Sort by score descending
        results.sort(key=lambda x: (-x["score"], x["name"]))

        return jsonify({"results": results[:limit]})

    @app.route("/api/query", methods=["POST"])
    def execute_query():
        """Execute a query and return results."""
        data = request.get_json()
        if not data:
            return jsonify({"error": "No query provided"}), 400

        query_text = data.get("query", "").lower()
        query_type = data.get("type", "auto")

        queries = get_queries()
        tracer = get_tracer()
        builder = get_builder()
        graph = builder.graph

        # Parse query
        result_nodes = []
        result_edges = []
        message = ""

        # Path query: "show path from X to Y" or "path X to Y"
        path_match = re.search(r"(?:show\s+)?path\s+(?:from\s+)?['\"]?(\w+)['\"]?\s+(?:to\s+)?['\"]?(\w+)['\"]?", query_text)
        if path_match or query_type == "path":
            if path_match:
                start_name = path_match.group(1)
                end_name = path_match.group(2)
            else:
                parts = query_text.split()
                start_name = parts[0] if parts else ""
                end_name = parts[-1] if len(parts) > 1 else ""

            path_result = tracer.trace_execution_path(start_name, end_name)

            if path_result.found and path_result.paths:
                message = f"Found {path_result.total_paths} path(s) from {start_name} to {end_name}"

                # Get nodes and edges from shortest path
                path_node_ids = set()
                for path in path_result.paths[:3]:  # Top 3 paths
                    for step in path:
                        path_node_ids.add(step.node_id)

                for node_id in path_node_ids:
                    node_data = graph.nodes.get(node_id, {})
                    result_nodes.append({
                        "id": node_id,
                        "name": node_data.get("name", node_id),
                        "type": node_data.get("type", "UNKNOWN"),
                        "file": short_path(node_data.get("file_path", "")),
                        "line": node_data.get("line_number", 0),
                        "highlight": True
                    })

                # Add edges between path nodes
                for source in path_node_ids:
                    for target in path_node_ids:
                        if graph.has_edge(source, target):
                            edge_data = graph.get_edge_data(source, target, {})
                            result_edges.append({
                                "from": source,
                                "to": target,
                                "relationship": edge_data.get("relationship", "UNKNOWN"),
                                "highlight": True
                            })
            else:
                message = f"No path found from {start_name} to {end_name}"

        # Usage query: "where is X used?" or "what uses X?"
        elif "used" in query_text or "uses" in query_text or query_type == "usage":
            name_match = re.search(r"(?:where\s+is\s+)?['\"]?(\w+)['\"]?\s+used|what\s+uses\s+['\"]?(\w+)['\"]?", query_text)
            if name_match:
                name = name_match.group(1) or name_match.group(2)
                usage_result = queries.find_usages(name)

                if usage_result.found:
                    message = f"Found {usage_result.total_usages} usage(s) of {name}"

                    # Add the target node
                    result_nodes.append({
                        "id": usage_result.node_id,
                        "name": usage_result.node_name,
                        "type": "TARGET",
                        "file": "",
                        "line": 0,
                        "highlight": True
                    })

                    for usage in usage_result.usages[:20]:
                        node_data = graph.nodes.get(usage["node_id"], {})
                        result_nodes.append({
                            "id": usage["node_id"],
                            "name": usage["node_name"],
                            "type": node_data.get("type", "UNKNOWN"),
                            "file": short_path(node_data.get("file_path", "")),
                            "line": node_data.get("line_number", 0)
                        })
                        result_edges.append({
                            "from": usage["node_id"],
                            "to": usage_result.node_id,
                            "relationship": usage["relationship"]
                        })
                else:
                    message = f"No usages found for {name}"

        # Caller query: "what calls X?"
        elif "calls" in query_text or query_type == "callers":
            name_match = re.search(r"what\s+calls\s+['\"]?(\w+)['\"]?", query_text)
            if name_match:
                name = name_match.group(1)
                callers_result = queries.find_callers(name)

                if callers_result and callers_result.total_count > 0:
                    message = f"Found {callers_result.total_count} caller(s) of {name}"

                    # Find target node
                    target_matches = queries.find_node_by_name(name, node_type="FUNCTION")
                    if target_matches:
                        target = target_matches[0]
                        result_nodes.append({
                            "id": target["id"],
                            "name": target["name"],
                            "type": "FUNCTION",
                            "file": short_path(target["file"]),
                            "line": target["line"],
                            "highlight": True
                        })

                        for caller in callers_result.usages[:20]:
                            result_nodes.append({
                                "id": caller["node_id"],
                                "name": caller["node_name"],
                                "type": "FUNCTION",
                                "file": short_path(caller.get("file", "")),
                                "line": caller.get("line", 0)
                            })
                            result_edges.append({
                                "from": caller["node_id"],
                                "to": target["id"],
                                "relationship": "CALLS"
                            })
                else:
                    message = f"No callers found for {name}"

        # Signal trace: "trace signal X"
        elif "signal" in query_text or query_type == "signal":
            name_match = re.search(r"(?:trace\s+)?signal\s+['\"]?(\w+)['\"]?", query_text)
            if name_match:
                name = name_match.group(1)
                signal_result = tracer.trace_signal_flow(name)

                if signal_result.found:
                    message = f"Signal '{name}': {len(signal_result.emissions)} emitter(s), {len(signal_result.connections)} connection(s)"

                    # Add signal definition
                    if signal_result.definition:
                        result_nodes.append({
                            "id": signal_result.signal_id,
                            "name": signal_result.definition.node_name,
                            "type": "SIGNAL",
                            "file": signal_result.definition.file_path,
                            "line": signal_result.definition.line_number,
                            "highlight": True
                        })

                    # Add emitters
                    for emission in signal_result.emissions[:10]:
                        result_nodes.append({
                            "id": emission.node_id,
                            "name": emission.node_name,
                            "type": emission.node_type,
                            "file": emission.file_path,
                            "line": emission.line_number
                        })
                        if signal_result.signal_id:
                            result_edges.append({
                                "from": emission.node_id,
                                "to": signal_result.signal_id,
                                "relationship": "EMITS"
                            })

                    # Add handlers
                    for handler in signal_result.handlers[:10]:
                        result_nodes.append({
                            "id": handler.node_id,
                            "name": handler.node_name,
                            "type": handler.node_type,
                            "file": handler.file_path,
                            "line": handler.line_number
                        })
                        if signal_result.signal_id:
                            result_edges.append({
                                "from": signal_result.signal_id,
                                "to": handler.node_id,
                                "relationship": "CONNECTS_TO"
                            })
                else:
                    message = f"Signal '{name}' not found"

        # Default: search and show related
        else:
            # Extract a name from the query
            words = re.findall(r'\b\w+\b', query_text)
            search_term = max(words, key=len) if words else query_text

            matches = queries.find_node_by_name(search_term)
            if matches:
                message = f"Found {len(matches)} match(es) for '{search_term}'"

                for match in matches[:10]:
                    node_data = graph.nodes.get(match["id"], {})
                    result_nodes.append({
                        "id": match["id"],
                        "name": match["name"],
                        "type": match["type"],
                        "file": short_path(match["file"]),
                        "line": match["line"],
                        "highlight": True
                    })

                    # Add connected nodes
                    for _, target in graph.out_edges(match["id"]):
                        target_data = graph.nodes.get(target, {})
                        edge_data = graph.get_edge_data(match["id"], target, {})
                        result_nodes.append({
                            "id": target,
                            "name": target_data.get("name", target),
                            "type": target_data.get("type", "UNKNOWN"),
                            "file": short_path(target_data.get("file_path", "")),
                            "line": target_data.get("line_number", 0)
                        })
                        result_edges.append({
                            "from": match["id"],
                            "to": target,
                            "relationship": edge_data.get("relationship", "UNKNOWN")
                        })
            else:
                message = f"No matches found for '{search_term}'"

        # Deduplicate nodes
        seen_ids = set()
        unique_nodes = []
        for node in result_nodes:
            if node["id"] not in seen_ids:
                seen_ids.add(node["id"])
                unique_nodes.append(node)

        return jsonify({
            "message": message,
            "nodes": unique_nodes,
            "edges": result_edges
        })

    @app.route("/api/neighbors/<path:node_id>")
    def get_neighbors(node_id: str):
        """Get neighboring nodes for expansion."""
        builder = get_builder()
        graph = builder.graph

        if node_id not in graph:
            return jsonify({"error": "Node not found"}), 404

        depth = request.args.get("depth", type=int, default=1)

        nodes = [{
            "id": node_id,
            **{k: v for k, v in graph.nodes[node_id].items() if k != "metadata"}
        }]
        edges = []
        visited = {node_id}
        frontier = [node_id]

        for _ in range(depth):
            next_frontier = []
            for current in frontier:
                # Outgoing
                for _, target in graph.out_edges(current):
                    if target not in visited:
                        visited.add(target)
                        next_frontier.append(target)
                        target_data = graph.nodes.get(target, {})
                        nodes.append({
                            "id": target,
                            "name": target_data.get("name", target),
                            "type": target_data.get("type", "UNKNOWN"),
                            "file": short_path(target_data.get("file_path", "")),
                            "line": target_data.get("line_number", 0)
                        })

                    edge_data = graph.get_edge_data(current, target, {})
                    edges.append({
                        "from": current,
                        "to": target,
                        "relationship": edge_data.get("relationship", "UNKNOWN")
                    })

                # Incoming
                for source, _ in graph.in_edges(current):
                    if source not in visited:
                        visited.add(source)
                        next_frontier.append(source)
                        source_data = graph.nodes.get(source, {})
                        nodes.append({
                            "id": source,
                            "name": source_data.get("name", source),
                            "type": source_data.get("type", "UNKNOWN"),
                            "file": short_path(source_data.get("file_path", "")),
                            "line": source_data.get("line_number", 0)
                        })

                    edge_data = graph.get_edge_data(source, current, {})
                    edges.append({
                        "from": source,
                        "to": current,
                        "relationship": edge_data.get("relationship", "UNKNOWN")
                    })

            frontier = next_frontier

        return jsonify({
            "nodes": nodes,
            "edges": edges
        })

    return app


def run_server(host: str = "127.0.0.1", port: int = 5000, scan_path: str = "F:/Reach"):
    """Run the development server."""
    app = create_app(scan_path)
    print(f"Starting server at http://{host}:{port}")
    print(f"Scanning: {scan_path}")
    app.run(host=host, port=port, debug=True, threaded=True)


if __name__ == "__main__":
    run_server()
