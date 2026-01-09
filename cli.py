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
from src.utils.config import config
from src.utils.logger import setup_logger


console = Console()


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

    This command scans all GDScript (.gd) and scene (.tscn) files in the
    project, parses them to extract code structure, and builds a dependency
    graph.

    Example:
        python cli.py scan
        python cli.py scan -p F:/Reach -o graph.json
        python cli.py scan --include "src/**/*.gd" --exclude "**/test/**"
    """
    # Get project root
    if project_root is None:
        project_root = config.project_root

    console.print(Panel(
        f"[bold blue]REACH Code Visualizer[/bold blue]\n"
        f"Project: [cyan]{project_root}[/cyan]",
        title="Scanning",
        border_style="blue"
    ))

    # Build configuration
    builder_config = {}

    if include:
        builder_config["include_patterns"] = list(include)

    if exclude:
        builder_config["exclude_patterns"] = list(exclude)
    else:
        builder_config["exclude_patterns"] = [
            "**/node_modules/**",
            "**/.godot/**",
            "**/build/**",
            "**/.git/**",
            "**/addons/**",
            "**/tools/data-visualizer/**"
        ]

    # Initialize builder
    builder = GraphBuilder(project_root, builder_config)

    # Scan files
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

    # Display statistics
    _display_statistics(stats)

    # Export if requested
    if output:
        builder.export_json(output)
        console.print(f"\n[green]Graph exported to:[/green] {output}")

    # Show sample nodes if verbose
    if ctx.obj.get("verbose"):
        _display_sample_nodes(builder)


@cli.command()
@click.argument("name")
@click.option(
    "--project-root", "-p",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Project root directory"
)
@click.option(
    "--type", "-t",
    type=click.Choice(["function", "variable", "signal", "class", "scene", "all"]),
    default="all",
    help="Filter by node type"
)
@click.pass_context
def find(ctx, name, project_root, type):
    """Find nodes by name in the code graph.

    Example:
        python cli.py find "player"
        python cli.py find "health" --type variable
        python cli.py find "raid" --type function
    """
    if project_root is None:
        project_root = config.project_root

    console.print(f"[dim]Searching for '[bold]{name}[/bold]' in {project_root}...[/dim]\n")

    # Build graph first
    builder = GraphBuilder(project_root)
    builder.build_graph()

    # Convert type filter
    type_map = {
        "function": "FUNCTION",
        "variable": "VARIABLE",
        "signal": "SIGNAL",
        "class": "CLASS",
        "scene": "SCENE",
        "all": None
    }
    type_filter = type_map.get(type)

    # Search
    from src.parsers.base_parser import NodeType
    node_type = NodeType[type_filter] if type_filter else None
    results = builder.get_node_by_name(name, node_type)

    if not results:
        console.print(f"[yellow]No nodes found matching '{name}'[/yellow]")
        return

    # Display results
    table = Table(title=f"Found {len(results)} nodes")
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("File", style="blue")
    table.add_column("Line", style="magenta")

    for node in results[:50]:  # Limit to 50 results
        file_path = node.get("file_path", "")
        # Shorten path
        try:
            rel_path = Path(file_path).relative_to(project_root)
        except ValueError:
            rel_path = file_path

        table.add_row(
            node.get("type", "?"),
            node.get("name", "?"),
            str(rel_path),
            str(node.get("line_number", "?"))
        )

    console.print(table)

    if len(results) > 50:
        console.print(f"[dim]... and {len(results) - 50} more[/dim]")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def parse(ctx, file_path):
    """Parse a single file and show extracted information.

    This is useful for debugging the parser output.

    Example:
        python cli.py parse F:/Reach/src/player/player.gd
        python cli.py parse F:/Reach/scenes/screens/nest/nest.tscn
    """
    console.print(f"[bold]Parsing:[/bold] {file_path}\n")

    # Determine parser
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

    # Show nodes
    console.print(f"[bold cyan]Nodes ({len(result.nodes)}):[/bold cyan]")

    nodes_table = Table(show_header=True)
    nodes_table.add_column("Type", style="cyan")
    nodes_table.add_column("Name", style="green")
    nodes_table.add_column("Line", style="magenta")
    nodes_table.add_column("Metadata", style="dim")

    for node in result.nodes[:30]:
        meta_str = ", ".join(f"{k}={v}" for k, v in list(node.metadata.items())[:3])
        nodes_table.add_row(
            node.type.name,
            node.name,
            str(node.line_number),
            meta_str[:50]
        )

    console.print(nodes_table)

    if len(result.nodes) > 30:
        console.print(f"[dim]... and {len(result.nodes) - 30} more nodes[/dim]")

    # Show edges
    console.print(f"\n[bold cyan]Edges ({len(result.edges)}):[/bold cyan]")

    edges_table = Table(show_header=True)
    edges_table.add_column("Relationship", style="yellow")
    edges_table.add_column("Context", style="dim")

    for edge in result.edges[:20]:
        edges_table.add_row(
            edge.relationship.name,
            edge.context[:60] if edge.context else ""
        )

    console.print(edges_table)

    if len(result.edges) > 20:
        console.print(f"[dim]... and {len(result.edges) - 20} more edges[/dim]")

    # Show errors/warnings
    if result.errors:
        console.print(f"\n[bold red]Errors ({len(result.errors)}):[/bold red]")
        for err in result.errors:
            console.print(f"  [red]• {err}[/red]")

    if result.warnings:
        console.print(f"\n[bold yellow]Warnings ({len(result.warnings)}):[/bold yellow]")
        for warn in result.warnings:
            console.print(f"  [yellow]• {warn}[/yellow]")


def _display_statistics(stats):
    """Display graph statistics in a nice format."""
    # File counts
    files_table = Table(title="Files Scanned", show_header=False)
    files_table.add_column("Type", style="cyan")
    files_table.add_column("Count", style="green", justify="right")

    files_table.add_row("GDScript (.gd)", str(stats.gdscript_files))
    files_table.add_row("Scenes (.tscn)", str(stats.tscn_files))
    files_table.add_row("TypeScript (.ts)", str(stats.typescript_files))
    files_table.add_row("[bold]Total[/bold]", f"[bold]{stats.total_files}[/bold]")

    console.print(files_table)
    console.print()

    # Graph stats
    graph_table = Table(title="Graph Statistics", show_header=False)
    graph_table.add_column("Metric", style="cyan")
    graph_table.add_column("Value", style="green", justify="right")

    graph_table.add_row("Total Nodes", str(stats.total_nodes))
    graph_table.add_row("Total Edges", str(stats.total_edges))

    console.print(graph_table)
    console.print()

    # Nodes by type
    if stats.nodes_by_type:
        nodes_table = Table(title="Nodes by Type")
        nodes_table.add_column("Type", style="cyan")
        nodes_table.add_column("Count", style="green", justify="right")

        for node_type, count in sorted(stats.nodes_by_type.items(), key=lambda x: -x[1]):
            nodes_table.add_row(node_type, str(count))

        console.print(nodes_table)
        console.print()

    # Edges by type
    if stats.edges_by_type:
        edges_table = Table(title="Edges by Type")
        edges_table.add_column("Relationship", style="yellow")
        edges_table.add_column("Count", style="green", justify="right")

        for edge_type, count in sorted(stats.edges_by_type.items(), key=lambda x: -x[1]):
            edges_table.add_row(edge_type, str(count))

        console.print(edges_table)
        console.print()

    # Quality warnings
    if stats.ambiguous_nodes > 0 or stats.low_confidence_edges > 0:
        console.print(Panel(
            f"[yellow]Ambiguous nodes: {stats.ambiguous_nodes}[/yellow]\n"
            f"[yellow]Low confidence edges: {stats.low_confidence_edges}[/yellow]",
            title="Quality Warnings",
            border_style="yellow"
        ))

    if stats.parse_errors:
        console.print(f"\n[bold red]Parse errors: {len(stats.parse_errors)}[/bold red]")
        for err in stats.parse_errors[:5]:
            console.print(f"  [red]• {err}[/red]")
        if len(stats.parse_errors) > 5:
            console.print(f"  [dim]... and {len(stats.parse_errors) - 5} more[/dim]")


def _display_sample_nodes(builder):
    """Display a sample of parsed nodes."""
    console.print("\n[bold]Sample Nodes:[/bold]")

    count = 0
    for node_id, data in builder.graph.nodes(data=True):
        if count >= 10:
            break

        console.print(f"  [cyan]{data.get('type')}[/cyan] "
                     f"[green]{data.get('name')}[/green] "
                     f"[dim]@ {data.get('file_path')}:{data.get('line_number')}[/dim]")
        count += 1


if __name__ == "__main__":
    cli()
