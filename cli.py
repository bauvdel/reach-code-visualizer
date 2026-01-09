#!/usr/bin/env python3
"""REACH Code Visualizer - Command Line Interface.

A tool for analyzing and visualizing the REACH game codebase.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.graph.graph_builder import GraphBuilder
from src.graph.graph_queries import GraphQueries, Direction
from src.analyzers.flow_tracer import FlowTracer
from src.analyzers.dependency_analyzer import DependencyAnalyzer
from src.utils.config import config
from src.utils.logger import setup_logger


console = Console()

# Cache for built graph (avoid rebuilding for multiple commands)
_graph_cache = {}


def _get_builder(project_root: Path = None) -> GraphBuilder:
    """Get or create a graph builder with cached graph."""
    if project_root is None:
        project_root = config.project_root

    cache_key = str(project_root)

    if cache_key not in _graph_cache:
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
        builder = GraphBuilder(project_root, builder_config)

        with console.status("[bold blue]Building graph...[/bold blue]"):
            builder.build_graph()

        _graph_cache[cache_key] = builder

    return _graph_cache[cache_key]


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, verbose):
    """REACH Code Visualizer - Analyze and visualize the REACH codebase."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose

    if verbose:
        setup_logger(level="DEBUG")


@cli.command()
@click.option(
    "--project-root", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory (default: F:/Reach)"
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output JSON file for graph export"
)
@click.option(
    "--include", "-i",
    multiple=True,
    help="Include pattern (e.g., '**/*.gd')"
)
@click.option(
    "--exclude", "-e",
    multiple=True,
    help="Exclude pattern (e.g., '**/addons/**')"
)
@click.pass_context
def scan(ctx, project_root, output, include, exclude):
    """Scan the project and build the code graph.

    Example:
        python cli.py scan
        python cli.py scan -p F:/Reach -o graph.json
    """
    if project_root is None:
        project_root = config.project_root

    console.print(Panel(
        f"[bold blue]REACH Code Visualizer[/bold blue]\n"
        f"Project: [cyan]{project_root}[/cyan]",
        title="Scanning",
        border_style="blue"
    ))

    builder_config = {}
    if include:
        builder_config["include_patterns"] = list(include)
    if exclude:
        builder_config["exclude_patterns"] = list(exclude)
    else:
        builder_config["exclude_patterns"] = [
            "**/node_modules/**", "**/.godot/**", "**/build/**",
            "**/.git/**", "**/addons/**", "**/tools/data-visualizer/**"
        ]

    builder = GraphBuilder(project_root, builder_config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)
        files = builder.scan_files()
        progress.update(task, description=f"Found {len(files)} files")
        progress.update(task, description="Parsing files...")
        stats = builder.build_graph(files)

    _display_statistics(stats)

    if output:
        builder.export_json(output)
        console.print(f"\n[green]Graph exported to:[/green] {output}")


@cli.command()
@click.argument("name")
@click.option("--project-root", "-p", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
@click.option("--type", "-t", type=click.Choice(["function", "variable", "signal", "class", "scene", "all"]), default="all")
@click.pass_context
def find(ctx, name, project_root, type):
    """Find nodes by name in the code graph.

    Example:
        python cli.py find "player"
        python cli.py find "health" --type variable
    """
    builder = _get_builder(project_root)

    type_map = {"function": "FUNCTION", "variable": "VARIABLE", "signal": "SIGNAL",
                "class": "CLASS", "scene": "SCENE", "all": None}
    type_filter = type_map.get(type)

    from src.parsers.base_parser import NodeType
    node_type = NodeType[type_filter] if type_filter else None
    results = builder.get_node_by_name(name, node_type)

    if not results:
        console.print(f"[yellow]No nodes found matching '{name}'[/yellow]")
        return

    table = Table(title=f"Found {len(results)} nodes")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("File", style="blue")
    table.add_column("Line", style="magenta")

    for node in results[:50]:
        file_path = node.get("file_path", "")
        try:
            rel_path = Path(file_path).relative_to(builder.project_root)
        except ValueError:
            rel_path = file_path
        table.add_row(node.get("type", "?"), node.get("name", "?"), str(rel_path), str(node.get("line_number", "?")))

    console.print(table)
    if len(results) > 50:
        console.print(f"[dim]... and {len(results) - 50} more[/dim]")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def parse(file_path):
    """Parse a single file and show extracted information.

    Example:
        python cli.py parse F:/Reach/src/player/player.gd
    """
    from src.parsers.gdscript_parser import GDScriptParser
    from src.parsers.tscn_parser import TSCNParser

    project_root = config.project_root

    if file_path.suffix == ".gd":
        parser = GDScriptParser(project_root)
    elif file_path.suffix == ".tscn":
        parser = TSCNParser(project_root)
    else:
        console.print(f"[red]Unsupported file type: {file_path.suffix}[/red]")
        return

    result = parser.parse_file(file_path)
    console.print(f"[bold]Parsing:[/bold] {file_path}\n")

    nodes_table = Table(title=f"Nodes ({len(result.nodes)})")
    nodes_table.add_column("Type", style="cyan")
    nodes_table.add_column("Name", style="green")
    nodes_table.add_column("Line", style="magenta")

    for node in result.nodes[:30]:
        nodes_table.add_row(node.type.name, node.name, str(node.line_number))
    console.print(nodes_table)
    if len(result.nodes) > 30:
        console.print(f"[dim]... and {len(result.nodes) - 30} more[/dim]")


# ===== NEW PHASE 2 COMMANDS =====

@cli.command()
@click.argument("query_text")
@click.option("--project-root", "-p", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
def query(query_text, project_root):
    """Run a natural language query on the code graph.

    Supports queries like:
        "show path from X to Y"
        "where is X used?"
        "what calls X?"
        "what does X call?"

    Example:
        python cli.py query "show path from pickup to SaveManager"
        python cli.py query "where is player.health used?"
        python cli.py query "what calls add_item?"
    """
    builder = _get_builder(project_root)
    queries = GraphQueries(builder.graph)

    query_lower = query_text.lower()

    # Parse query intent
    if "path from" in query_lower or "path to" in query_lower:
        _handle_path_query(queries, query_text)
    elif "where is" in query_lower and "used" in query_lower:
        _handle_usage_query(queries, query_text)
    elif "what calls" in query_lower:
        _handle_callers_query(queries, query_text)
    elif "what does" in query_lower and "call" in query_lower:
        _handle_callees_query(queries, query_text)
    elif "depends on" in query_lower or "dependencies" in query_lower:
        _handle_dependency_query(queries, query_text)
    else:
        # Default: search for the term
        _handle_search_query(queries, query_text)


def _handle_path_query(queries: GraphQueries, query_text: str):
    """Handle 'show path from X to Y' queries."""
    import re
    # Extract source and target
    match = re.search(r'(?:from|between)\s+["\']?(\w+)["\']?\s+(?:to|and)\s+["\']?(\w+)["\']?', query_text, re.I)

    if not match:
        console.print("[yellow]Could not parse path query. Use: 'show path from X to Y'[/yellow]")
        return

    source_name = match.group(1)
    target_name = match.group(2)

    console.print(f"[dim]Finding path from '{source_name}' to '{target_name}'...[/dim]\n")

    # Find matching nodes
    source_nodes = queries.find_node_by_name(source_name)
    target_nodes = queries.find_node_by_name(target_name)

    if not source_nodes:
        console.print(f"[red]No nodes found matching '{source_name}'[/red]")
        return
    if not target_nodes:
        console.print(f"[red]No nodes found matching '{target_name}'[/red]")
        return

    # Try to find path between any combination
    for source in source_nodes[:3]:
        for target in target_nodes[:3]:
            result = queries.find_path(source["id"], target["id"], max_depth=10)
            if result.found:
                console.print(result.format())
                return

    console.print(f"[yellow]No path found between '{source_name}' and '{target_name}'[/yellow]")


def _handle_usage_query(queries: GraphQueries, query_text: str):
    """Handle 'where is X used?' queries."""
    import re
    match = re.search(r'where is\s+["\']?([^\'"]+)["\']?\s+used', query_text, re.I)

    if not match:
        console.print("[yellow]Could not parse usage query. Use: 'where is X used?'[/yellow]")
        return

    name = match.group(1).strip()
    console.print(f"[dim]Finding usages of '{name}'...[/dim]\n")

    nodes = queries.find_node_by_name(name)
    if not nodes:
        console.print(f"[red]No nodes found matching '{name}'[/red]")
        return

    for node in nodes[:3]:
        result = queries.find_usages(node["id"])
        if result.total_count > 0:
            console.print(result.format())
            return

    console.print(f"[yellow]No usages found for '{name}'[/yellow]")


def _handle_callers_query(queries: GraphQueries, query_text: str):
    """Handle 'what calls X?' queries."""
    import re
    match = re.search(r'what calls\s+["\']?([^\'"?]+)["\']?', query_text, re.I)

    if not match:
        console.print("[yellow]Could not parse query. Use: 'what calls X?'[/yellow]")
        return

    name = match.group(1).strip()
    console.print(f"[dim]Finding callers of '{name}'...[/dim]\n")

    nodes = queries.find_node_by_name(name, node_type="FUNCTION")
    if not nodes:
        console.print(f"[red]No functions found matching '{name}'[/red]")
        return

    for node in nodes[:3]:
        result = queries.find_callers(node["id"])
        if result.total_count > 0:
            console.print(f"[bold]CALLERS OF: {node['name']}()[/bold]")
            console.print(f"Total: {result.total_count}\n")
            for usage in result.usages[:20]:
                console.print(f"  {usage['name']}()")
                console.print(f"       @ {usage['file']}:{usage['line']}")
            return

    console.print(f"[yellow]No callers found for '{name}'[/yellow]")


def _handle_callees_query(queries: GraphQueries, query_text: str):
    """Handle 'what does X call?' queries."""
    import re
    match = re.search(r'what does\s+["\']?([^\'"]+)["\']?\s+call', query_text, re.I)

    if not match:
        console.print("[yellow]Could not parse query. Use: 'what does X call?'[/yellow]")
        return

    name = match.group(1).strip()
    console.print(f"[dim]Finding functions called by '{name}'...[/dim]\n")

    nodes = queries.find_node_by_name(name, node_type="FUNCTION")
    if not nodes:
        console.print(f"[red]No functions found matching '{name}'[/red]")
        return

    for node in nodes[:3]:
        callees = queries.find_callees(node["id"])
        if callees:
            console.print(f"[bold]FUNCTIONS CALLED BY: {node['name']}()[/bold]")
            console.print(f"Total: {len(callees)}\n")
            for callee in callees[:20]:
                console.print(f"  {callee['name']}()")
                console.print(f"       @ {callee['file']}:{callee['line']}")
            return

    console.print(f"[yellow]'{name}' doesn't call any tracked functions[/yellow]")


def _handle_dependency_query(queries: GraphQueries, query_text: str):
    """Handle dependency queries."""
    import re
    match = re.search(r'(?:dependencies|depends on)\s+["\']?([^\'"]+)["\']?', query_text, re.I)

    if not match:
        console.print("[yellow]Could not parse query.[/yellow]")
        return

    name = match.group(1).strip()
    nodes = queries.find_node_by_name(name)

    if not nodes:
        console.print(f"[red]No nodes found matching '{name}'[/red]")
        return

    result = queries.find_dependencies(nodes[0]["id"], Direction.BOTH, depth=3)
    console.print(result.format())


def _handle_search_query(queries: GraphQueries, query_text: str):
    """Default: search for nodes matching the query."""
    results = queries.find_node_by_name(query_text)

    if not results:
        console.print(f"[yellow]No nodes found matching '{query_text}'[/yellow]")
        return

    console.print(f"[bold]Found {len(results)} nodes matching '{query_text}':[/bold]\n")
    for node in results[:20]:
        console.print(f"  [{node['type']}] {node['name']}")
        console.print(f"       @ {node['file']}:{node['line']}")


@cli.command()
@click.option("--dead-code", is_flag=True, help="Detect potentially dead code")
@click.option("--circular-deps", is_flag=True, help="Detect circular dependencies")
@click.option("--coupling", is_flag=True, help="Find highly coupled nodes")
@click.option("--impact", type=str, default=None, help="Analyze impact of changing a node")
@click.option("--project-root", "-p", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
def analyze(dead_code, circular_deps, coupling, impact, project_root):
    """Run code analysis on the project.

    Example:
        python cli.py analyze --dead-code
        python cli.py analyze --circular-deps
        python cli.py analyze --coupling
        python cli.py analyze --impact "InventoryManager"
    """
    builder = _get_builder(project_root)
    analyzer = DependencyAnalyzer(builder.graph)

    if dead_code:
        console.print("[bold blue]Running dead code detection...[/bold blue]\n")
        result = analyzer.detect_dead_code()
        console.print(result.format())

    if circular_deps:
        console.print("[bold blue]Detecting circular dependencies...[/bold blue]\n")
        result = analyzer.detect_circular_dependencies(max_cycles=20)
        console.print(result.format())

    if coupling:
        console.print("[bold blue]Finding highly coupled nodes...[/bold blue]\n")
        results = analyzer.find_highly_coupled_nodes(min_connections=15)

        if not results:
            console.print("[green]No highly coupled nodes found (> 15 connections)[/green]")
        else:
            table = Table(title=f"Highly Coupled Nodes ({len(results)})")
            table.add_column("Name", style="green")
            table.add_column("Type", style="cyan")
            table.add_column("In", style="yellow", justify="right")
            table.add_column("Out", style="yellow", justify="right")
            table.add_column("Total", style="red", justify="right")

            for node in results[:20]:
                table.add_row(
                    node["name"], node["type"],
                    str(node["in_degree"]), str(node["out_degree"]),
                    str(node["total_connections"])
                )
            console.print(table)

    if impact:
        console.print(f"[bold blue]Analyzing impact of changing '{impact}'...[/bold blue]\n")
        queries = GraphQueries(builder.graph)
        nodes = queries.find_node_by_name(impact)

        if not nodes:
            console.print(f"[red]No nodes found matching '{impact}'[/red]")
            return

        result = analyzer.analyze_impact(nodes[0]["id"], depth=3)
        console.print(result.format())

    if not any([dead_code, circular_deps, coupling, impact]):
        console.print("[yellow]Specify an analysis type: --dead-code, --circular-deps, --coupling, or --impact[/yellow]")


@cli.command()
@click.argument("trace_type", type=click.Choice(["variable", "signal", "execution"]))
@click.argument("name")
@click.option("--to", "target", default=None, help="Target function for execution trace")
@click.option("--project-root", "-p", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
def trace(trace_type, name, target, project_root):
    """Trace data or execution flow through the codebase.

    Example:
        python cli.py trace variable "inventory_items"
        python cli.py trace signal "player_died"
        python cli.py trace execution "pickup" --to "save_inventory"
    """
    builder = _get_builder(project_root)
    tracer = FlowTracer(builder.graph)

    if trace_type == "variable":
        console.print(f"[bold blue]Tracing variable '{name}'...[/bold blue]\n")
        result = tracer.trace_variable_flow(name)
        console.print(result.format())

    elif trace_type == "signal":
        console.print(f"[bold blue]Tracing signal '{name}'...[/bold blue]\n")
        result = tracer.trace_signal_flow(name)
        console.print(result.format())

    elif trace_type == "execution":
        if not target:
            console.print("[red]Execution trace requires --to parameter[/red]")
            console.print("Example: python cli.py trace execution 'pickup' --to 'save_inventory'")
            return

        console.print(f"[bold blue]Tracing execution from '{name}' to '{target}'...[/bold blue]\n")
        result = tracer.trace_execution_path(name, target, max_depth=10)
        console.print(result.format())


@cli.command()
@click.argument("source_name")
@click.argument("target_name")
@click.option("--project-root", "-p", type=click.Path(exists=True, file_okay=False, path_type=Path), default=None)
def path(source_name, target_name, project_root):
    """Find path between two nodes (shortcut for query).

    Example:
        python cli.py path "pickup" "SaveManager"
        python cli.py path "add_item" "PlayFabManager"
    """
    builder = _get_builder(project_root)
    queries = GraphQueries(builder.graph)

    console.print(f"[dim]Finding path from '{source_name}' to '{target_name}'...[/dim]\n")

    source_nodes = queries.find_node_by_name(source_name)
    target_nodes = queries.find_node_by_name(target_name)

    if not source_nodes:
        console.print(f"[red]No nodes found matching '{source_name}'[/red]")
        return
    if not target_nodes:
        console.print(f"[red]No nodes found matching '{target_name}'[/red]")
        return

    # Show what we found
    console.print(f"Source matches: {len(source_nodes)} nodes")
    console.print(f"Target matches: {len(target_nodes)} nodes\n")

    # Try combinations
    found_any = False
    for source in source_nodes[:5]:
        for target in target_nodes[:5]:
            result = queries.find_path(source["id"], target["id"], max_depth=12)
            if result.found:
                console.print(result.format())
                found_any = True
                break
        if found_any:
            break

    if not found_any:
        console.print(f"[yellow]No path found between '{source_name}' and '{target_name}'[/yellow]")
        console.print("\n[dim]Tip: Try more specific names or check if nodes exist with 'find' command[/dim]")


# ===== HELPER FUNCTIONS =====

def _display_statistics(stats):
    """Display graph statistics."""
    files_table = Table(title="Files Scanned", show_header=False)
    files_table.add_column("Type", style="cyan")
    files_table.add_column("Count", style="green", justify="right")
    files_table.add_row("GDScript (.gd)", str(stats.gdscript_files))
    files_table.add_row("Scenes (.tscn)", str(stats.tscn_files))
    files_table.add_row("[bold]Total[/bold]", f"[bold]{stats.total_files}[/bold]")
    console.print(files_table)
    console.print()

    graph_table = Table(title="Graph Statistics", show_header=False)
    graph_table.add_column("Metric", style="cyan")
    graph_table.add_column("Value", style="green", justify="right")
    graph_table.add_row("Total Nodes", str(stats.total_nodes))
    graph_table.add_row("Total Edges", str(stats.total_edges))
    console.print(graph_table)
    console.print()

    if stats.nodes_by_type:
        nodes_table = Table(title="Nodes by Type")
        nodes_table.add_column("Type", style="cyan")
        nodes_table.add_column("Count", style="green", justify="right")
        for node_type, count in sorted(stats.nodes_by_type.items(), key=lambda x: -x[1]):
            nodes_table.add_row(node_type, str(count))
        console.print(nodes_table)
        console.print()

    if stats.edges_by_type:
        edges_table = Table(title="Edges by Type")
        edges_table.add_column("Relationship", style="yellow")
        edges_table.add_column("Count", style="green", justify="right")
        for edge_type, count in sorted(stats.edges_by_type.items(), key=lambda x: -x[1]):
            edges_table.add_row(edge_type, str(count))
        console.print(edges_table)

    if stats.ambiguous_nodes > 0:
        console.print(Panel(
            f"[yellow]Ambiguous nodes: {stats.ambiguous_nodes}[/yellow]",
            title="Quality Warnings", border_style="yellow"
        ))


if __name__ == "__main__":
    cli()
