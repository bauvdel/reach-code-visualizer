# REACH Code Visualizer - Technical Specification

## Project Overview
Build a standalone local application that provides interactive visualization and tracing of the REACH game codebase, including Godot (GDScript) and PlayFab MPS server (TypeScript/CloudScript) components.

## 1. Project Scope

### Target Codebase
- **Primary Location**: `F:/Reach`
- **File Counts**: ~100 `.gd` files, ~100 `.tscn` files, TypeScript/CloudScript files
- **Organization**: Mixed structure organized by features
- **Additional Components**: TypeScript/CloudScript on PlayFab MPS server

### Core Objective
Enable AI-like execution path tracing for debugging. Example flow:
```
"Here is func A" → "Creates var B" → "Where else is var B used?" → "Called in func C" → etc.
```

## 2. Technical Architecture

### Application Type
- **Standalone local application** (web-based, runs locally)
- **Technology Stack Recommendation**:
  - Backend: Python (Flask or FastAPI) for file parsing and analysis
  - Frontend: HTML/CSS/JavaScript with vis.js or D3.js for graph visualization
  - File Watching: watchdog (Python library)
  - Graph Database: NetworkX (Python) for in-memory graph operations
  - Natural Language Processing: Simple keyword matching or lightweight NLP library

### Directory Structure
```
reach-code-visualizer/
├── src/
│   ├── parsers/
│   │   ├── gdscript_parser.py      # Parse .gd files
│   │   ├── tscn_parser.py          # Parse .tscn files
│   │   ├── typescript_parser.py    # Parse TypeScript/CloudScript
│   │   └── base_parser.py          # Common parsing utilities
│   ├── analyzers/
│   │   ├── dependency_analyzer.py  # Build dependency graph
│   │   ├── flow_tracer.py          # Trace execution flows
│   │   └── query_engine.py         # Process natural language queries
│   ├── graph/
│   │   ├── graph_builder.py        # Construct graph from parsed data
│   │   ├── graph_queries.py        # Graph traversal and queries
│   │   └── graph_export.py         # Export graph data
│   ├── watchers/
│   │   └── file_watcher.py         # Monitor file changes
│   ├── server/
│   │   └── app.py                  # Web server (Flask/FastAPI)
│   └── utils/
│       ├── config.py               # Configuration management
│       └── logger.py               # Logging utilities
├── frontend/
│   ├── index.html                  # Main UI
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── graph-renderer.js       # Graph visualization
│   │   ├── query-interface.js      # Query UI
│   │   ├── node-inspector.js       # Node details panel
│   │   └── api-client.js           # Backend communication
│   └── assets/
├── tests/
├── docs/
├── config/
│   └── config.yaml                 # User configuration
├── exports/                        # Generated exports for Claude
├── requirements.txt
└── README.md
```

## 3. Parsing Requirements

### 3.1 GDScript Parser (.gd files)

**Detect and Extract:**
1. **Function Definitions**
   ```gdscript
   func function_name(param1: Type, param2: Type) -> ReturnType:
   ```
   - Function name
   - Parameters with types
   - Return type
   - Location (file, line number)

2. **Function Calls**
   ```gdscript
   some_function()
   object.method_call()
   get_node("Path").function()
   ```
   - Caller → Callee relationship
   - Location in source

3. **Variable Declarations and Assignments**
   ```gdscript
   var variable_name: Type = value
   @export var exported_var: int
   @onready var node_ref = $NodePath
   ```
   - Variable name
   - Type (if specified)
   - Initial value/assignment
   - Scope (class-level, function-local)

4. **Variable Usage**
   ```gdscript
   variable_name = new_value
   result = variable_name.property
   function(variable_name)
   ```
   - Read vs Write operations
   - Context (where used)

5. **Signal Definitions and Emissions**
   ```gdscript
   signal signal_name(param1: Type, param2: Type)
   signal_name.emit(arg1, arg2)
   emit_signal("signal_name", arg1, arg2)
   ```
   - Signal name
   - Parameters
   - Emission points

6. **Signal Connections**
   ```gdscript
   signal_name.connect(handler_function)
   connect("signal_name", object, "method_name")
   ```
   - Signal source
   - Handler function
   - Connection location

7. **Node References**
   ```gdscript
   get_node("NodePath")
   $NodePath
   @onready var node = $Path/To/Node
   find_child("NodeName")
   ```
   - Path to node
   - Variable storing reference

8. **Scene/Resource Loading**
   ```gdscript
   preload("res://path/to/scene.tscn")
   load("res://path/to/resource.tres")
   var scene = preload("res://scenes/Enemy.tscn")
   var instance = scene.instantiate()
   ```
   - Resource path
   - Type (scene, resource, script)
   - Usage context

9. **Class Definitions and Inheritance**
   ```gdscript
   class_name ClassName extends BaseClass
   ```
   - Class name
   - Parent class
   - Inner classes

10. **Autoload/Singleton Usage**
    ```gdscript
    GlobalManager.function()
    GameState.player_health = 100
    ```
    - Identify autoload references

### 3.2 TSCN Parser (.tscn files)

**Detect and Extract:**

1. **Scene Structure**
   ```
   [node name="NodeName" type="NodeType" parent="."]
   ```
   - Node hierarchy
   - Node types
   - Node names
   - Parent-child relationships

2. **Script Attachments**
   ```
   [node name="Player" type="CharacterBody2D"]
   script = ExtResource("1_abc123")
   
   [ext_resource type="Script" path="res://scripts/player.gd" id="1_abc123"]
   ```
   - Which scripts are attached to which nodes
   - Script paths

3. **Signal Connections**
   ```
   [connection signal="pressed" from="Button" to="." method="_on_button_pressed"]
   ```
   - Source node and signal
   - Target node and method
   - Connection metadata

4. **Exported Variables**
   ```
   [node name="Enemy"]
   health = 100
   speed = 5.0
   ```
   - Exported variable overrides
   - Default values from scenes

5. **Instanced Scenes**
   ```
   [node name="EnemyInstance" instance=ExtResource("2_xyz789")]
   ```
   - Scene dependencies
   - Nested scene structure

### 3.3 TypeScript/CloudScript Parser

**Detect and Extract:**

1. **Function Definitions**
   ```typescript
   function functionName(param: Type): ReturnType { }
   const funcName = (param: Type) => { }
   ```

2. **Function Calls**
   ```typescript
   functionName(args)
   object.method()
   ```

3. **Variable Declarations**
   ```typescript
   let/const/var variableName: Type = value
   ```

4. **Variable Usage**
   - Assignments
   - References

5. **PlayFab API Calls**
   ```typescript
   server.UpdateUserData(...)
   server.GetTitleData(...)
   ```
   - API endpoint calls
   - Data flow to/from PlayFab

6. **Data Serialization/Deserialization**
   - JSON.parse/stringify
   - Data transformations

7. **Async Operations**
   ```typescript
   async function() { }
   await promise
   ```

8. **Export/Import Statements**
   ```typescript
   import { Function } from './module'
   export function Function() { }
   ```
   - Module dependencies

### 3.4 Cross-Language Connection Points

**Identify:**
1. **PlayFab CloudScript Calls from Godot**
   ```gdscript
   PlayFabManager.execute_cloud_script("FunctionName", {data})
   ```

2. **Data Structures Shared Between Systems**
   - Item data formats
   - Player state schemas
   - Inventory structures

3. **HTTP/API Endpoints**
   - REST calls from Godot to server
   - Server callbacks to game

## 4. Graph Data Model

### Node Types
```python
class Node:
    id: str                    # Unique identifier
    type: NodeType             # Enum: FUNCTION, VARIABLE, SIGNAL, SCENE, CLASS, etc.
    name: str                  # Display name
    file_path: str             # Source file
    line_number: int           # Line in source
    language: str              # 'gdscript', 'typescript', 'scene'
    code_snippet: str          # Surrounding code context
    metadata: dict             # Additional info (params, types, etc.)
    confidence: str            # 'high', 'medium', 'low', 'ambiguous'
```

### Node Types Enum
- `FUNCTION` - Function/method definitions
- `VARIABLE` - Variable declarations
- `SIGNAL` - Signal definitions
- `SIGNAL_CONNECTION` - Signal-to-handler connections
- `SCENE` - Scene files (.tscn)
- `CLASS` - Class definitions
- `NODE_REFERENCE` - References to scene tree nodes
- `RESOURCE` - Loaded resources
- `API_CALL` - External API calls (PlayFab, etc.)
- `MODULE` - TypeScript modules/files
- `AMBIGUOUS` - Cannot be definitively resolved

### Edge Types
```python
class Edge:
    source_id: str
    target_id: str
    relationship: EdgeType     # Type of relationship
    context: str               # Where this relationship occurs
    metadata: dict             # Additional info
    confidence: str            # 'high', 'medium', 'low', 'ambiguous'
```

### Edge Types Enum
- `CALLS` - Function A calls Function B
- `CALLED_BY` - Reverse of CALLS
- `READS` - Reads variable value
- `WRITES` - Writes variable value
- `EMITS` - Emits signal
- `CONNECTS_TO` - Signal connects to handler
- `INSTANTIATES` - Creates instance of scene/class
- `INHERITS` - Class inheritance
- `REFERENCES` - References node/resource
- `IMPORTS` - Module import
- `DATA_FLOW` - Data flows from A to B
- `CONTAINS` - Hierarchical containment (scene contains node)

### Graph Structure
```python
{
    "nodes": [
        {
            "id": "func_player_gd_take_damage_15",
            "type": "FUNCTION",
            "name": "take_damage",
            "file_path": "F:/Reach/scripts/player.gd",
            "line_number": 15,
            "language": "gdscript",
            "code_snippet": "func take_damage(amount: int) -> void:\n    health -= amount\n    ...",
            "metadata": {
                "params": [{"name": "amount", "type": "int"}],
                "return_type": "void"
            },
            "confidence": "high"
        },
        {
            "id": "var_player_gd_health_5",
            "type": "VARIABLE",
            "name": "health",
            "file_path": "F:/Reach/scripts/player.gd",
            "line_number": 5,
            "language": "gdscript",
            "code_snippet": "var health: int = 100",
            "metadata": {
                "type": "int",
                "initial_value": "100",
                "scope": "class"
            },
            "confidence": "high"
        }
    ],
    "edges": [
        {
            "source_id": "func_player_gd_take_damage_15",
            "target_id": "var_player_gd_health_5",
            "relationship": "WRITES",
            "context": "health -= amount (line 16)",
            "metadata": {
                "operation": "subtract_assign"
            },
            "confidence": "high"
        }
    ]
}
```

## 5. Analysis Features

### 5.1 Flow Tracing
**Objective**: Trace execution paths like an AI debugger

**Example Query Flow:**
```
User: "Trace inventory item persistence"

System Analysis:
1. Find all nodes matching "inventory" or "item"
2. Identify persistence-related functions (save, load, serialize)
3. Build execution path:
   - ItemPickup.gd::pickup() [line 45]
     ↓ CALLS
   - InventoryManager.gd::add_item(item_data) [line 120]
     ↓ WRITES
   - InventoryManager.inventory_items (variable)
     ↓ READS
   - InventoryManager.gd::save_inventory() [line 200]
     ↓ CALLS
   - SaveManager.gd::serialize_data(inventory_data) [line 88]
     ↓ CALLS
   - PlayFabManager.gd::update_user_data() [line 150]
     ↓ API_CALL
   - CloudScript::SaveInventory() [TypeScript]
```

**Output**: Interactive graph showing this path with ability to:
- Expand/collapse branches
- Click any node to see code
- Highlight the full path
- Show all alternative paths

### 5.2 Impact Analysis
**Objective**: "If I change X, what else is affected?"

**Features:**
- Forward impact: What does X call/use?
- Backward impact: What calls/uses X?
- Depth-limited traversal (1-5 levels)
- Confidence scoring (high/medium/low/ambiguous)

### 5.3 Dead Code Detection
**Objective**: Find unused code

**Method:**
- Build call graph from entry points (autoloads, _ready(), _process())
- Mark all reachable nodes
- Report unreachable nodes as potential dead code

### 5.4 Circular Dependency Detection
**Objective**: Find problematic circular references

**Method:**
- Run cycle detection on graph
- Report all cycles with visualization
- Highlight strongest dependencies in cycles

### 5.5 Scene Validation
**Objective**: Ensure scenes are properly connected

**Checks:**
- Scripts attached to nodes exist
- Signal connections have valid handlers
- Node paths referenced in scripts exist in scene
- Required exported variables are set

## 6. Query System

### 6.1 Natural Language Query Engine

**Supported Query Patterns:**

1. **Path Finding**
   - "Show path from X to Y"
   - "How does X reach Y?"
   - "Trace from ItemPickup to SaveManager"
   - "What's the flow from UI click to data save?"

2. **Usage Queries**
   - "Where is X used?"
   - "What uses variable health?"
   - "Show all callers of save_game()"
   - "What emits the player_died signal?"

3. **Definition Queries**
   - "What is X?"
   - "Show me function handle_input"
   - "Find class WeaponData"

4. **Relationship Queries**
   - "What does X call?"
   - "What signals does PlayerController emit?"
   - "What scenes use Player.tscn?"
   - "What scripts are in the UI folder?"

5. **Data Flow Queries**
   - "Trace variable item_data"
   - "Where does player.position get set?"
   - "Follow inventory_items through the code"

6. **Cross-Language Queries**
   - "Show PlayFab calls from Godot"
   - "What CloudScript functions are called?"
   - "Trace data from GDScript to TypeScript"

### 6.2 Query Processing

**Pipeline:**
```python
1. Parse natural language → Extract keywords and intent
2. Identify query type (path, usage, definition, etc.)
3. Extract entities (function names, variable names, etc.)
4. Translate to graph query
5. Execute query on graph
6. Format results for visualization
7. Highlight confidence levels
```

**Example Implementation:**
```python
def process_query(query: str) -> QueryResult:
    # Keyword extraction
    keywords = extract_keywords(query)
    
    # Intent classification
    intent = classify_intent(query)
    # Possible intents: PATH, USAGE, DEFINITION, RELATIONSHIP, DATA_FLOW
    
    # Entity extraction
    entities = extract_entities(query, keywords)
    
    # Build graph query
    graph_query = build_graph_query(intent, entities)
    
    # Execute
    results = execute_query(graph_query)
    
    return QueryResult(
        results=results,
        query_type=intent,
        entities=entities,
        visualization_hint=suggest_visualization(intent)
    )
```

### 6.3 Predefined Query Templates

**Fast Access Common Queries:**
- "Show all autoloads and their dependencies"
- "Find all signal connections in project"
- "List all scenes and their scripts"
- "Show all PlayFab API calls"
- "Find all file I/O operations"
- "Show inventory system architecture"
- "Trace player death flow"

## 7. Visualization Requirements

### 7.1 Interactive Graph Rendering

**Graph Layout Algorithms:**
- Force-directed (default) - Good for general relationships
- Hierarchical - Good for call trees and inheritance
- Circular - Good for showing cycles
- Tree - Good for scene hierarchies

**Node Visualization:**
- **Shape** based on type:
  - Functions: Rounded rectangles
  - Variables: Ellipses
  - Signals: Diamonds
  - Scenes: Hexagons
  - Classes: Rectangles
  - API Calls: Triangles
  - Ambiguous: Dashed outline

- **Color** based on language/category:
  - GDScript: Blue palette
  - TypeScript: Green palette
  - Scenes: Purple palette
  - Ambiguous: Yellow/Orange
  - Confidence overlay (opacity)

- **Size** based on:
  - Connection count (degree centrality)
  - Importance score

**Edge Visualization:**
- **Line Style**:
  - Solid: High confidence
  - Dashed: Medium confidence
  - Dotted: Low confidence/Ambiguous
  
- **Color** based on relationship:
  - CALLS: Blue
  - READS/WRITES: Green
  - SIGNALS: Orange
  - DATA_FLOW: Purple
  - Cross-language: Red

- **Arrows**: Directional

**Interaction Features:**
- **Click Node**: 
  - Show node inspector panel
  - Display code snippet
  - Show file location (clickable to open in editor)
  - List all incoming/outgoing edges
  
- **Double-Click Node**:
  - Expand/focus on node's immediate neighbors
  
- **Hover Node**:
  - Tooltip with basic info
  - Highlight connected edges
  
- **Right-Click Node**:
  - Context menu:
    - "Show all paths to..."
    - "Show all callers"
    - "Show all callees"
    - "Find similar nodes"
    - "Hide this node"
    - "Export subgraph"
  
- **Click Edge**:
  - Show context (where relationship occurs)
  - Display code snippet

- **Drag**: Pan canvas
- **Scroll**: Zoom in/out
- **Box Select**: Multi-select nodes
- **Ctrl+Click**: Add to selection

### 7.2 UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  REACH Code Visualizer                                    [―][□][×]│
├─────────────────────────────────────────────────────────────────┤
│  Query: [Show path from ItemPickup to SaveManager         ] [🔍]│
│  Filters: [Type▼] [Language▼] [Confidence▼] [Custom▼]          │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────┬─────────────────────────┐│
│ │                                     │  Node Inspector         ││
│ │                                     │  ┌───────────────────┐  ││
│ │                                     │  │ Function: pickup()│  ││
│ │                                     │  ├───────────────────┤  ││
│ │       Graph Canvas                  │  │ File: ItemPickup  │  ││
│ │                                     │  │ Line: 45          │  ││
│ │                                     │  │ Language: GDScript│  ││
│ │                                     │  │ Confidence: High  │  ││
│ │                                     │  └───────────────────┘  ││
│ │                                     │                         ││
│ │                                     │  Code Snippet:          ││
│ │                                     │  ┌───────────────────┐  ││
│ │                                     │  │func pickup():     │  ││
│ │                                     │  │  item = create... │  ││
│ │                                     │  │  InventoryMgr...  │  ││
│ │                                     │  └───────────────────┘  ││
│ │                                     │                         ││
│ │                                     │  Relationships (15):    ││
│ │                                     │  • CALLS add_item()     ││
│ │                                     │  • READS item_data      ││
│ │                                     │  • ...                  ││
│ └─────────────────────────────────────┴─────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ Status: Watching 200 files | Last update: 2 seconds ago         │
│ Stats: 1,234 nodes | 3,456 edges | 12 ambiguous                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Advanced Visualization Features

**Minimap**
- Small overview of entire graph
- Current viewport indicator
- Click to navigate

**Path Highlighting**
- Highlight full path between two nodes
- Show path statistics (length, confidence)
- Multiple paths side-by-side

**Filtering**
- By node type (show only functions)
- By language (GDScript only)
- By confidence (hide low confidence)
- By file/directory
- By custom criteria

**Clustering**
- Group nodes by file
- Group by feature/module
- Color-coded clusters
- Collapsible clusters

**Search**
- Fuzzy search by node name
- Filter results in real-time
- Highlight matching nodes

**Bookmarks**
- Save interesting views
- Quick navigation to bookmarks
- Share bookmarks (export view state)

**Time Travel** (if git integration)
- See how graph evolved over commits
- Compare current vs previous state
- Animate changes

## 8. Watch Mode

### File Monitoring
**Libraries**: `watchdog` (Python)

**Behavior:**
- Monitor all files in project directory
- Debounce rapid changes (wait 500ms after last change)
- Process changed files incrementally

**Events to Watch:**
- File created
- File modified
- File deleted
- File renamed

**Update Strategy:**
```python
1. Detect file change
2. Determine affected files (dependencies)
3. Re-parse changed files
4. Update graph incrementally:
   - Remove old nodes/edges from changed files
   - Add new nodes/edges from re-parsed files
5. Notify frontend via WebSocket
6. Frontend incrementally updates visualization
```

**Performance Considerations:**
- Parse only changed files (not full rescan)
- Use file hashing to detect real changes
- Batch updates if many files change at once
- Configurable exclusions (ignore build dirs, etc.)

**WebSocket Communication:**
```javascript
// Frontend receives updates
socket.on('graph_update', (data) => {
    // data = { added_nodes: [], removed_nodes: [], added_edges: [], removed_edges: [] }
    graphRenderer.updateGraph(data);
});
```

## 9. Export Capabilities

### 9.1 Export for Claude

**Format**: Structured text document optimized for LLM context

**Structure:**
```markdown
# REACH Codebase Map
Generated: 2025-01-09 14:30:00

## Project Overview
- Total Files: 200
- GDScript Files: 100
- TSCN Files: 100
- TypeScript Files: 50
- Total Functions: 450
- Total Variables: 800
- Total Signals: 120

## Architecture Overview
### Key Components
1. **Inventory System** (15 files)
   - Entry Points: ItemPickup, InventoryUI
   - Core Logic: InventoryManager, ItemData
   - Persistence: SaveManager
   - External: PlayFab integration

2. **Player System** (20 files)
   - ...

### Cross-Cutting Concerns
- Save/Load: SaveManager ↔ PlayFab CloudScript
- Signal Bus: EventBus (autoload)

## Detailed Mappings

### Function Call Graph
```
ItemPickup.pickup() [scripts/items/item_pickup.gd:45]
  ↓ CALLS
InventoryManager.add_item(item_data: ItemData) [scripts/inventory/manager.gd:120]
  ↓ WRITES
InventoryManager.inventory_items [scripts/inventory/manager.gd:15]
  ↓ READS (in)
InventoryManager.save_inventory() [scripts/inventory/manager.gd:200]
  ↓ CALLS
SaveManager.serialize_data(data: Dictionary) [scripts/core/save_manager.gd:88]
  ↓ CALLS
PlayFabManager.update_user_data(key: String, value: String) [scripts/playfab/manager.gd:150]
  ↓ API_CALL
CloudScript.SaveInventory(data: any) [server/handlers/inventory.ts:45]
```

### Variable Dependency Map
```
player.health [scripts/player/player.gd:10]
  WRITTEN BY:
    - take_damage() [line 45]
    - heal() [line 60]
    - respawn() [line 120]
  READ BY:
    - update_health_ui() [line 80]
    - check_death() [line 100]
    - HealthBar._process() [scenes/ui/health_bar.gd:15]
```

### Signal Flow Map
```
SIGNAL: player_died [scripts/player/player.gd:8]
  EMITTED BY:
    - check_death() [line 105]
  CONNECTED TO:
    - GameManager._on_player_died() [scripts/core/game_manager.gd:200]
    - UIManager._on_player_died() [scripts/ui/ui_manager.gd:150]
    - AudioManager._on_player_died() [scripts/audio/audio_manager.gd:80]
```

### Scene Dependencies
```
Player.tscn [scenes/player/player.tscn]
  ATTACHED SCRIPTS:
    - Player.gd [scripts/player/player.gd]
  INSTANCED SCENES:
    - WeaponSlot.tscn [scenes/weapons/weapon_slot.tscn]
    - HealthBar.tscn [scenes/ui/health_bar.tscn]
  SIGNAL CONNECTIONS:
    - Button.pressed → _on_shoot_pressed()
    - Area3D.body_entered → _on_hitbox_entered()
```

### Ambiguous References
```
⚠️ AMBIGUOUS: get_node("../Manager")
   Location: scripts/items/item.gd:67
   Context: Unclear which Manager node is referenced
   Possible targets:
     - InventoryManager
     - GameManager
     - UIManager

⚠️ LOW CONFIDENCE: call("handle_" + action_name)
   Location: scripts/player/player.gd:180
   Context: Dynamic method call cannot be statically resolved
```

## File Index
[Alphabetical list of all files with brief descriptions]

---
*Generated by REACH Code Visualizer v1.0*
*This map is optimized for LLM context and debugging assistance*
```

**Export Triggers:**
- Manual export button
- Auto-export on significant changes (optional)
- Export specific subgraphs
- Export based on query results

### 9.2 Other Export Formats

**JSON Graph**
```json
{
  "format": "graph_v1",
  "metadata": {...},
  "nodes": [...],
  "edges": [...]
}
```
- Full graph data
- Importable by other tools

**GraphML**
- Standard graph interchange format
- Compatible with tools like Gephi, yEd

**DOT (Graphviz)**
```dot
digraph REACH {
  "func_player_take_damage" -> "var_player_health" [label="WRITES"];
  ...
}
```
- Can be rendered with Graphviz
- Static visualization

**CSV**
- Nodes.csv
- Edges.csv
- Good for data analysis in Excel/Python

**Markdown Report**
- Human-readable summary
- Statistics and insights
- Top-level architecture

## 10. Configuration

### config.yaml
```yaml
project:
  root_path: "F:/Reach"
  name: "REACH"
  
parsing:
  # File patterns to include
  include_patterns:
    - "**/*.gd"
    - "**/*.tscn"
    - "**/*.ts"
    - "**/*.js"
  
  # File patterns to exclude
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.godot/**"
    - "**/build/**"
    - "**/.git/**"
  
  # Parser-specific settings
  gdscript:
    parse_comments: true
    extract_docstrings: true
  
  typescript:
    tsconfig_path: "server/tsconfig.json"
  
analysis:
  # Confidence thresholds
  high_confidence: 0.9
  medium_confidence: 0.6
  low_confidence: 0.3
  
  # Max depth for path finding
  max_path_depth: 10
  
  # Dead code detection entry points
  entry_points:
    - "res://autoload/*.gd"
    - "res://scenes/main.tscn"

watch_mode:
  enabled: true
  debounce_ms: 500
  excluded_dirs:
    - ".godot"
    - "node_modules"
    - "build"

server:
  host: "localhost"
  port: 5000
  debug: false

visualization:
  default_layout: "force-directed"
  max_visible_nodes: 500  # Auto-cluster if exceeded
  edge_bundling: true
  
export:
  output_dir: "./exports"
  auto_export_on_analysis: false
  claude_export_format: "markdown"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "./logs/visualizer.log"
```

## 11. Error Handling & Edge Cases

### Ambiguous Cases
**Mark as ambiguous when:**
1. **Dynamic method calls**
   ```gdscript
   call("method_" + variable_name)
   ```
   
2. **String-based node paths**
   ```gdscript
   get_node(node_path_variable)
   ```
   
3. **Reflection/dynamic access**
   ```gdscript
   get(property_name)
   set(property_name, value)
   ```
   
4. **Multiple definitions with same name**
   - Functions with same name in different files
   - Variables with same name in different scopes

**Display Strategy:**
- Mark node/edge with "ambiguous" confidence
- Show dashed outline
- List possible interpretations in inspector
- Allow user to manually confirm correct interpretation

### Parse Errors
**When parsing fails:**
1. Log error with file and line number
2. Mark file as "partially parsed"
3. Include successfully parsed portions in graph
4. Show error in UI with link to file
5. Continue processing other files

**Common Issues:**
- Syntax errors in source files
- Encoding issues (non-UTF-8)
- Corrupted scene files
- Missing files referenced by includes

### Performance Issues
**If graph becomes too large:**
1. Implement pagination (load graph in chunks)
2. Use clustering (group related nodes)
3. Provide filtering to reduce visible nodes
4. Offer "focus mode" (show only N hops from selected node)
5. Consider using graph database (Neo4j) for very large projects

### File System Issues
**Handle:**
- Files deleted while being processed
- Permission errors
- Network drive disconnections (if project on network)
- Symlinks and junctions

## 12. Implementation Phases

### Phase 1: Core Parsing (Week 1-2)
- [ ] Set up project structure
- [ ] Implement GDScript parser
  - [ ] Function definitions and calls
  - [ ] Variable declarations and usage
  - [ ] Signals (emit and connect)
- [ ] Implement TSCN parser
  - [ ] Scene structure
  - [ ] Script attachments
  - [ ] Signal connections
- [ ] Build initial graph from parsed data
- [ ] Basic command-line output of graph stats

### Phase 2: Graph Analysis (Week 2-3)
- [ ] Implement graph query system
- [ ] Path finding algorithms
- [ ] Dependency analysis (forward/backward)
- [ ] Dead code detection
- [ ] Circular dependency detection
- [ ] Basic text-based query interface

### Phase 3: Web Interface (Week 3-4)
- [ ] Set up web server (Flask/FastAPI)
- [ ] Create frontend HTML/CSS structure
- [ ] Implement graph renderer (vis.js or D3.js)
- [ ] Basic node/edge visualization
- [ ] Click interactions (show details)
- [ ] Search functionality

### Phase 4: Advanced Features (Week 4-5)
- [ ] Natural language query processing
- [ ] Advanced filtering and clustering
- [ ] Path highlighting
- [ ] Multi-select and bulk operations
- [ ] Export functionality (JSON, DOT, CSV)
- [ ] Node inspector panel with code snippets

### Phase 5: TypeScript Integration (Week 5-6)
- [ ] TypeScript/CloudScript parser
- [ ] Cross-language linking
- [ ] PlayFab API call detection
- [ ] Data flow tracing across languages

### Phase 6: Watch Mode (Week 6-7)
- [ ] File watching with watchdog
- [ ] Incremental graph updates
- [ ] WebSocket communication
- [ ] Real-time UI updates
- [ ] Performance optimization

### Phase 7: Export & Documentation (Week 7-8)
- [ ] Claude-optimized export format
- [ ] Multiple export formats
- [ ] Auto-export triggers
- [ ] User documentation
- [ ] Configuration guide

### Phase 8: Polish & Testing (Week 8)
- [ ] Error handling improvements
- [ ] Performance profiling and optimization
- [ ] UI/UX refinements
- [ ] Testing on full REACH codebase
- [ ] Bug fixes
- [ ] README and setup instructions

## 13. Success Criteria

### Functional Requirements
✅ Parse 100+ GDScript files without errors
✅ Parse 100+ TSCN files and extract connections
✅ Parse TypeScript/CloudScript files
✅ Build complete dependency graph
✅ Trace execution paths accurately (e.g., "item pickup to save")
✅ Respond to natural language queries
✅ Provide interactive visualization
✅ Update in real-time (watch mode)
✅ Export Claude-readable documentation
✅ Handle ambiguous cases gracefully

### Performance Requirements
✅ Initial parse of 200 files < 30 seconds
✅ Query response time < 2 seconds
✅ Real-time update propagation < 1 second
✅ Smooth visualization (60fps) with 500+ visible nodes

### Usability Requirements
✅ Intuitive UI (no manual required for basic tasks)
✅ Clear visual distinction between node types
✅ Easy navigation (zoom, pan, search)
✅ Helpful error messages
✅ Documentation and examples

## 14. Future Enhancements (Post-MVP)

### Advanced Analysis
- **Complexity metrics**: Cyclomatic complexity per function
- **Code smells**: Detect long functions, deep nesting, etc.
- **Performance analysis**: Identify hot paths, bottlenecks
- **Test coverage visualization**: Show tested vs untested code

### AI-Powered Features
- **Smart refactoring suggestions**: "Function X is too complex, consider splitting"
- **Architecture recommendations**: "High coupling detected between A and B"
- **Auto-documentation**: Generate docs from code structure
- **Predictive queries**: "You might want to see..." suggestions

### IDE Integration
- **VS Code extension**: View graph directly in editor
- **Jump-to-definition**: Click node → open file in editor
- **Inline annotations**: Show usage count next to functions
- **Refactoring support**: Update graph on rename/move operations

### Collaboration
- **Shared views**: Generate shareable URLs for specific graph states
- **Annotations**: Add notes to nodes/edges
- **Team insights**: Show which files each team member works on
- **Change impact reports**: "Your PR affects 15 files"

### Version Control Integration
- **Git history analysis**: See how architecture evolved
- **Blame integration**: Who last modified each function?
- **Branch comparison**: Compare graphs across branches
- **Merge conflict prediction**: "These changes will conflict"

## 15. Technical Dependencies

### Python Libraries
```
flask==3.0.0              # Web server
flask-socketio==5.3.0     # WebSocket support
watchdog==3.0.0           # File watching
networkx==3.2.0           # Graph operations
pyyaml==6.0.0             # Configuration
regex==2023.12.0          # Advanced pattern matching
python-dotenv==1.0.0      # Environment variables
```

### Frontend Libraries
```
vis-network==9.1.0        # Graph visualization (or d3.js)
bootstrap==5.3.0          # UI framework
jquery==3.7.0             # DOM manipulation
socket.io-client==4.6.0   # WebSocket client
highlight.js==11.9.0      # Code syntax highlighting
```

### Optional/Advanced
```
tree-sitter==0.20.0       # Better parsing (if needed)
neo4j==5.14.0             # Graph database (for very large projects)
spacy==3.7.0              # NLP for query processing
```

## 16. Deliverables

### Code Deliverables
1. **Source code** (fully commented)
2. **requirements.txt** with all dependencies
3. **config.yaml.example** template
4. **Setup script** (setup.py or setup.sh)

### Documentation
1. **README.md**
   - Project overview
   - Installation instructions
   - Quick start guide
   - Configuration options
   
2. **USER_GUIDE.md**
   - Detailed feature explanations
   - Query examples
   - Visualization tips
   - Export guides
   
3. **DEVELOPER_GUIDE.md**
   - Architecture overview
   - Code structure
   - Adding new parsers
   - Extending functionality
   
4. **API_REFERENCE.md**
   - Backend API endpoints
   - Graph query API
   - WebSocket events

### Example Files
1. **example_queries.txt** - Common query examples
2. **example_export.md** - Sample Claude export
3. **screenshots/** - UI screenshots for documentation

## 17. Notes for Implementation

### Critical Design Decisions

1. **Parser Approach**: Use regex + simple state machines rather than full AST parsers initially. GDScript/TypeScript parsers are complex; focus on extracting key relationships first.

2. **Graph Storage**: In-memory NetworkX for MVP. Consider Neo4j if project scales beyond 10,000 nodes.

3. **Visualization Library**: Recommend `vis.js` over D3.js for faster implementation. D3.js offers more control but requires more code.

4. **Natural Language Processing**: Start with keyword matching and pattern recognition. Advanced NLP (spaCy) can be added later if needed.

5. **Cross-Language Linking**: Requires manual hints initially. Look for:
   - Function names that match exactly
   - Comments like "# Calls CloudScript.SaveInventory"
   - PlayFab API method names

6. **Performance**: Profile early. Scene file parsing may be slow; consider caching parsed results with file hashes.

### Testing Strategy

1. **Unit Tests**: Test each parser independently with sample files
2. **Integration Tests**: Test full pipeline on small sample project
3. **Regression Tests**: Keep sample project and expected graph output
4. **Manual Testing**: Use on REACH project regularly during development

### Brandon's Feedback Loop

- Weekly demos of new features
- Test on real REACH issues ("Can you trace this bug?")
- Iterate on UI/UX based on actual usage
- Refine query system based on Brandon's natural questions

---

**End of Specification Document**

*This spec should provide Claude Code with everything needed to implement the REACH Code Visualizer. Adjust phases and priorities based on development progress and Brandon's feedback.*
