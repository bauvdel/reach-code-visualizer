# REACH Code Visualizer

A code analysis and visualization tool for the REACH game project. Parses GDScript (.gd) and scene (.tscn) files to build a dependency graph for code exploration and debugging.

## Features

- **GDScript Parser**: Extracts functions, variables, signals, signal connections, class definitions, and resource loading
- **TSCN Parser**: Extracts scene structure, node hierarchy, script attachments, and signal connections
- **Graph Builder**: Builds a NetworkX graph of code relationships
- **CLI Tool**: Scan projects, find nodes, parse individual files, and export graph data

## Quick Start

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Scan the REACH project
python cli.py scan

# Export graph to JSON
python cli.py scan -o exports/graph.json

# Find functions by name
python cli.py find "raid" --type function

# Parse a single file
python cli.py parse F:/Reach/src/player/player.gd
```

## CLI Commands

### `scan`
Scan the project and build the code graph.

```bash
python cli.py scan                           # Scan default project (F:/Reach)
python cli.py scan -p /path/to/project       # Scan custom project
python cli.py scan -o graph.json             # Export to JSON
python cli.py scan --exclude "**/addons/**"  # Custom exclusions
```

### `find`
Find nodes in the code graph by name.

```bash
python cli.py find "player"                  # Find all nodes containing "player"
python cli.py find "health" --type variable  # Find only variables
python cli.py find "raid" --type function    # Find only functions
```

### `parse`
Parse a single file and display extracted information.

```bash
python cli.py parse src/player/player.gd     # Parse GDScript file
python cli.py parse scenes/nest/nest.tscn    # Parse scene file
```

## Graph Data Model

### Node Types
- `FUNCTION` - Function/method definitions
- `VARIABLE` - Variable declarations
- `SIGNAL` - Signal definitions
- `SIGNAL_CONNECTION` - Signal-to-handler connections
- `SCENE` - Scene files (.tscn)
- `CLASS` - Class definitions
- `NODE_REFERENCE` - References to scene tree nodes
- `RESOURCE` - Loaded resources (preload/load)
- `AMBIGUOUS` - Cannot be definitively resolved

### Edge Types
- `CALLS` - Function A calls Function B
- `READS` / `WRITES` - Variable access
- `EMITS` - Emits signal
- `CONNECTS_TO` - Signal connects to handler
- `INSTANTIATES` - Creates instance of scene/class
- `INHERITS` - Class inheritance
- `REFERENCES` - References node/resource
- `CONTAINS` - Scene contains node

## Configuration

Edit `config/config.yaml` to customize:

```yaml
project:
  root_path: "F:/Reach"
  name: "REACH"

parsing:
  include_patterns:
    - "**/*.gd"
    - "**/*.tscn"
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.godot/**"
    - "**/addons/**"
```

## Project Structure

```
reach-code-visualizer/
├── src/
│   ├── parsers/
│   │   ├── base_parser.py      # Base parser class and data models
│   │   ├── gdscript_parser.py  # GDScript parser
│   │   └── tscn_parser.py      # TSCN scene parser
│   ├── graph/
│   │   └── graph_builder.py    # Graph construction with NetworkX
│   └── utils/
│       ├── config.py           # Configuration management
│       └── logger.py           # Logging utilities
├── config/
│   └── config.yaml             # Default configuration
├── exports/                    # Generated exports
├── cli.py                      # Command-line interface
├── requirements.txt
└── README.md
```

## Roadmap

- [x] Phase 1: Core parsing (GDScript, TSCN)
- [ ] Phase 2: Graph analysis (path finding, impact analysis)
- [ ] Phase 3: Web interface (vis.js visualization)
- [ ] Phase 4: Natural language queries
- [ ] Phase 5: TypeScript/CloudScript parsing
- [ ] Phase 6: Watch mode (real-time updates)
- [ ] Phase 7: Claude-optimized exports

## License

MIT
