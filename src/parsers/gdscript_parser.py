"""GDScript parser for extracting code structure and relationships."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base_parser import (
    BaseParser,
    ParseResult,
    ParsedNode,
    ParsedEdge,
    NodeType,
    EdgeType,
    Confidence,
)


@dataclass
class FunctionContext:
    """Tracks current function context during parsing."""
    name: str
    node_id: str
    start_line: int
    indent_level: int


class GDScriptParser(BaseParser):
    """Parser for GDScript (.gd) files."""

    # Regex patterns for GDScript constructs
    PATTERNS = {
        # Class and inheritance
        "class_name": re.compile(r"^class_name\s+(\w+)"),
        "extends": re.compile(r"^extends\s+(\w+)"),
        "inner_class": re.compile(r"^(\s*)class\s+(\w+)(?:\s+extends\s+(\w+))?:"),

        # Functions
        "func_def": re.compile(
            r"^(\s*)func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\w+))?\s*:"
        ),
        "static_func": re.compile(
            r"^(\s*)static\s+func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\w+))?\s*:"
        ),

        # Variables
        "var_decl": re.compile(
            r"^(\s*)var\s+(\w+)(?:\s*:\s*(\w+))?(?:\s*=\s*(.+))?"
        ),
        "const_decl": re.compile(
            r"^(\s*)const\s+(\w+)(?:\s*:\s*(\w+))?\s*=\s*(.+)"
        ),
        "export_var": re.compile(
            r"^(\s*)@export(?:_\w+)?\s+var\s+(\w+)(?:\s*:\s*(\w+))?(?:\s*=\s*(.+))?"
        ),
        "onready_var": re.compile(
            r"^(\s*)@onready\s+var\s+(\w+)(?:\s*:\s*(\w+))?\s*=\s*(.+)"
        ),

        # Signals
        "signal_def": re.compile(
            r"^signal\s+(\w+)(?:\s*\(([^)]*)\))?"
        ),
        "signal_emit_new": re.compile(
            r"(\w+)\.emit\s*\(([^)]*)\)"
        ),
        "signal_emit_old": re.compile(
            r'emit_signal\s*\(\s*["\'](\w+)["\'](?:\s*,\s*([^)]*))?\)'
        ),
        "signal_connect_new": re.compile(
            r"(\w+)\.connect\s*\(\s*(\w+)"
        ),
        "signal_connect_old": re.compile(
            r'connect\s*\(\s*["\'](\w+)["\']'
        ),

        # Resource loading
        "preload": re.compile(
            r'preload\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),
        "load": re.compile(
            r'load\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),

        # Node references
        "dollar_path": re.compile(r'\$([A-Za-z0-9_/]+)'),
        "get_node": re.compile(r'get_node\s*\(\s*["\']([^"\']+)["\']\s*\)'),
        "get_node_var": re.compile(r'get_node\s*\(\s*(\w+)\s*\)'),
        "find_child": re.compile(r'find_child\s*\(\s*["\']([^"\']+)["\']\s*\)'),

        # Function calls
        "method_call": re.compile(r'(\w+)\s*\('),
        "object_method": re.compile(r'(\w+)\.(\w+)\s*\('),

        # Autoload access (PascalCase singleton followed by method/property)
        "autoload_access": re.compile(r'\b([A-Z][a-zA-Z0-9]+)\.(\w+)'),

        # Dynamic calls (mark as ambiguous)
        "dynamic_call": re.compile(r'call\s*\(\s*["\']?(\w+)'),
        "dynamic_get": re.compile(r'\bget\s*\(\s*["\'](\w+)["\']\s*\)'),
        "dynamic_set": re.compile(r'\bset\s*\(\s*["\'](\w+)["\']\s*,'),
    }

    # Built-in functions to ignore
    BUILTIN_FUNCTIONS = {
        # Lifecycle
        "_init", "_ready", "_process", "_physics_process", "_input",
        "_unhandled_input", "_notification", "_enter_tree", "_exit_tree",
        # Common methods
        "print", "push_error", "push_warning", "str", "int", "float", "bool",
        "typeof", "len", "range", "abs", "min", "max", "clamp", "lerp",
        "get", "set", "has", "keys", "values", "append", "remove", "erase",
        "is_instance_valid", "is_instance_of", "await",
        # Math
        "sin", "cos", "tan", "sqrt", "pow", "floor", "ceil", "round",
        # Node methods (very common)
        "add_child", "remove_child", "get_parent", "get_children",
        "queue_free", "get_tree", "get_viewport",
    }

    def supported_extensions(self) -> list[str]:
        return [".gd"]

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a GDScript file and extract all code elements."""
        result = ParseResult(
            file_path=str(file_path),
            file_hash=self.compute_file_hash(file_path),
        )

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

        # Track parsing state
        current_class: Optional[str] = None
        current_function: Optional[FunctionContext] = None
        class_variables: dict[str, str] = {}  # name -> node_id
        defined_signals: dict[str, str] = {}  # name -> node_id
        defined_functions: dict[str, str] = {}  # name -> node_id

        # First pass: Extract definitions
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                continue

            # Class name
            match = self.PATTERNS["class_name"].match(stripped)
            if match:
                current_class = match.group(1)
                node = ParsedNode(
                    id=self.generate_node_id(NodeType.CLASS, file_path, current_class, line_num),
                    type=NodeType.CLASS,
                    name=current_class,
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata={"is_class_name": True}
                )
                result.nodes.append(node)
                continue

            # Extends
            match = self.PATTERNS["extends"].match(stripped)
            if match:
                parent_class = match.group(1)
                if current_class:
                    # Add inheritance edge later when we have class node
                    result.edges.append(ParsedEdge(
                        source_id=f"class_{file_path.stem}_{current_class}_*",
                        target_id=f"class_*_{parent_class}_*",
                        relationship=EdgeType.INHERITS,
                        context=f"extends {parent_class} (line {line_num})",
                        confidence=Confidence.MEDIUM  # May not resolve to actual class
                    ))
                continue

            # Signal definitions
            match = self.PATTERNS["signal_def"].match(stripped)
            if match:
                signal_name = match.group(1)
                params_str = match.group(2) or ""
                params = self._parse_params(params_str)

                node_id = self.generate_node_id(NodeType.SIGNAL, file_path, signal_name, line_num)
                defined_signals[signal_name] = node_id

                node = ParsedNode(
                    id=node_id,
                    type=NodeType.SIGNAL,
                    name=signal_name,
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata={"params": params}
                )
                result.nodes.append(node)
                continue

            # Function definitions
            match = self.PATTERNS["func_def"].match(line) or self.PATTERNS["static_func"].match(line)
            if match:
                indent = len(match.group(1))
                func_name = match.group(2)
                params_str = match.group(3) or ""
                return_type = match.group(4)

                params = self._parse_params(params_str)
                node_id = self.generate_node_id(NodeType.FUNCTION, file_path, func_name, line_num)
                defined_functions[func_name] = node_id

                node = ParsedNode(
                    id=node_id,
                    type=NodeType.FUNCTION,
                    name=func_name,
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num, context_lines=5),
                    metadata={
                        "params": params,
                        "return_type": return_type,
                        "is_static": "static" in line,
                        "is_private": func_name.startswith("_"),
                    }
                )
                result.nodes.append(node)

                current_function = FunctionContext(
                    name=func_name,
                    node_id=node_id,
                    start_line=line_num,
                    indent_level=indent
                )
                continue

            # Variable declarations (class-level)
            if current_function is None:
                var_node = self._parse_variable(line, stripped, file_path, line_num, lines)
                if var_node:
                    class_variables[var_node.name] = var_node.id
                    result.nodes.append(var_node)
                    continue

            # Check if we've exited current function (based on indentation)
            if current_function and stripped and not line.startswith(" " * (current_function.indent_level + 1)):
                if not stripped.startswith("#"):
                    # Check if this is a new function or class-level code
                    if self.PATTERNS["func_def"].match(line) or not line.startswith(" "):
                        current_function = None

        # Second pass: Extract relationships (calls, usage, emissions)
        current_function = None

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                continue

            # Track function context
            match = self.PATTERNS["func_def"].match(line) or self.PATTERNS["static_func"].match(line)
            if match:
                func_name = match.group(2)
                if func_name in defined_functions:
                    current_function = FunctionContext(
                        name=func_name,
                        node_id=defined_functions[func_name],
                        start_line=line_num,
                        indent_level=len(match.group(1))
                    )
                continue

            # Only process relationships inside functions
            if current_function is None:
                continue

            # Signal emissions (new style: signal_name.emit())
            for match in self.PATTERNS["signal_emit_new"].finditer(stripped):
                signal_name = match.group(1)
                if signal_name in defined_signals:
                    result.edges.append(ParsedEdge(
                        source_id=current_function.node_id,
                        target_id=defined_signals[signal_name],
                        relationship=EdgeType.EMITS,
                        context=f"line {line_num}: {stripped[:60]}",
                    ))

            # Signal emissions (old style: emit_signal("name"))
            for match in self.PATTERNS["signal_emit_old"].finditer(stripped):
                signal_name = match.group(1)
                if signal_name in defined_signals:
                    result.edges.append(ParsedEdge(
                        source_id=current_function.node_id,
                        target_id=defined_signals[signal_name],
                        relationship=EdgeType.EMITS,
                        context=f"line {line_num}: {stripped[:60]}",
                    ))

            # Signal connections (new style: signal.connect(handler))
            for match in self.PATTERNS["signal_connect_new"].finditer(stripped):
                signal_name = match.group(1)
                handler_name = match.group(2)

                # Create connection node
                conn_id = self.generate_node_id(
                    NodeType.SIGNAL_CONNECTION, file_path, f"{signal_name}_to_{handler_name}", line_num
                )
                result.nodes.append(ParsedNode(
                    id=conn_id,
                    type=NodeType.SIGNAL_CONNECTION,
                    name=f"{signal_name} -> {handler_name}",
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata={"signal": signal_name, "handler": handler_name}
                ))

                # Connect signal to handler
                if signal_name in defined_signals:
                    result.edges.append(ParsedEdge(
                        source_id=defined_signals[signal_name],
                        target_id=conn_id,
                        relationship=EdgeType.CONNECTS_TO,
                        context=f"line {line_num}",
                    ))
                if handler_name in defined_functions:
                    result.edges.append(ParsedEdge(
                        source_id=conn_id,
                        target_id=defined_functions[handler_name],
                        relationship=EdgeType.CONNECTS_TO,
                        context=f"line {line_num}",
                    ))

            # Function calls
            for match in self.PATTERNS["method_call"].finditer(stripped):
                called_func = match.group(1)

                # Skip built-ins and self-calls
                if called_func in self.BUILTIN_FUNCTIONS:
                    continue
                if called_func == current_function.name:
                    continue

                # Check if it's a known function
                if called_func in defined_functions:
                    result.edges.append(ParsedEdge(
                        source_id=current_function.node_id,
                        target_id=defined_functions[called_func],
                        relationship=EdgeType.CALLS,
                        context=f"line {line_num}: {stripped[:60]}",
                    ))

            # Variable reads/writes
            for var_name, var_id in class_variables.items():
                if var_name in stripped:
                    # Simple heuristic: if followed by = it's a write, otherwise read
                    # This is simplified - real analysis would need AST
                    pattern = rf'\b{re.escape(var_name)}\s*='
                    if re.search(pattern, stripped) and not re.search(rf'==', stripped):
                        result.edges.append(ParsedEdge(
                            source_id=current_function.node_id,
                            target_id=var_id,
                            relationship=EdgeType.WRITES,
                            context=f"line {line_num}",
                            confidence=Confidence.MEDIUM
                        ))
                    elif re.search(rf'\b{re.escape(var_name)}\b', stripped):
                        result.edges.append(ParsedEdge(
                            source_id=current_function.node_id,
                            target_id=var_id,
                            relationship=EdgeType.READS,
                            context=f"line {line_num}",
                            confidence=Confidence.MEDIUM
                        ))

            # Resource loading
            for match in self.PATTERNS["preload"].finditer(stripped):
                res_path = match.group(1)
                self._add_resource_reference(result, file_path, current_function.node_id, res_path, line_num, lines, "preload")

            for match in self.PATTERNS["load"].finditer(stripped):
                res_path = match.group(1)
                self._add_resource_reference(result, file_path, current_function.node_id, res_path, line_num, lines, "load")

            # Node references
            for match in self.PATTERNS["dollar_path"].finditer(stripped):
                node_path = match.group(1)
                self._add_node_reference(result, file_path, current_function.node_id, node_path, line_num, lines)

            for match in self.PATTERNS["get_node"].finditer(stripped):
                node_path = match.group(1)
                self._add_node_reference(result, file_path, current_function.node_id, node_path, line_num, lines)

            # Dynamic calls (mark as ambiguous)
            for match in self.PATTERNS["dynamic_call"].finditer(stripped):
                method_name = match.group(1)
                result.warnings.append(f"Dynamic call at line {line_num}: call(\"{method_name}\")")
                result.nodes.append(ParsedNode(
                    id=self.generate_node_id(NodeType.AMBIGUOUS, file_path, f"dynamic_call_{method_name}", line_num),
                    type=NodeType.AMBIGUOUS,
                    name=f"call(\"{method_name}\")",
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata={"reason": "dynamic_method_call", "method_name": method_name},
                    confidence=Confidence.AMBIGUOUS
                ))

            # Variable-based get_node (ambiguous)
            for match in self.PATTERNS["get_node_var"].finditer(stripped):
                var_name = match.group(1)
                result.warnings.append(f"Variable node path at line {line_num}: get_node({var_name})")
                result.nodes.append(ParsedNode(
                    id=self.generate_node_id(NodeType.AMBIGUOUS, file_path, f"dynamic_node_{var_name}", line_num),
                    type=NodeType.AMBIGUOUS,
                    name=f"get_node({var_name})",
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata={"reason": "variable_node_path", "variable": var_name},
                    confidence=Confidence.AMBIGUOUS
                ))

        # Also extract class-level preloads/loads (constants)
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Constant preloads (class level)
            match = self.PATTERNS["const_decl"].match(stripped)
            if match:
                const_name = match.group(2)
                value = match.group(4) or ""

                # Check for preload in value
                preload_match = self.PATTERNS["preload"].search(value)
                if preload_match:
                    res_path = preload_match.group(1)
                    node_id = self.generate_node_id(NodeType.RESOURCE, file_path, const_name, line_num)
                    result.nodes.append(ParsedNode(
                        id=node_id,
                        type=NodeType.RESOURCE,
                        name=const_name,
                        file_path=str(file_path),
                        line_number=line_num,
                        language="gdscript",
                        code_snippet=self.get_code_snippet(lines, line_num),
                        metadata={
                            "resource_path": res_path,
                            "load_type": "preload",
                            "is_constant": True
                        }
                    ))

        return result

    def _parse_params(self, params_str: str) -> list[dict]:
        """Parse function/signal parameters."""
        if not params_str.strip():
            return []

        params = []
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Parse "name: Type = default"
            parts = param.split("=")[0].strip()  # Remove default value
            if ":" in parts:
                name, type_hint = parts.split(":", 1)
                params.append({"name": name.strip(), "type": type_hint.strip()})
            else:
                params.append({"name": parts, "type": None})

        return params

    def _parse_variable(
        self,
        line: str,
        stripped: str,
        file_path: Path,
        line_num: int,
        lines: list[str]
    ) -> Optional[ParsedNode]:
        """Parse a variable declaration."""
        # Try different variable patterns
        for pattern_name in ["export_var", "onready_var", "var_decl"]:
            match = self.PATTERNS[pattern_name].match(stripped)
            if match:
                indent = match.group(1)
                var_name = match.group(2)
                var_type = match.group(3)
                initial_value = match.group(4) if len(match.groups()) > 3 else None

                # Determine scope based on indent
                scope = "class" if len(indent) == 0 else "function"

                metadata = {
                    "type": var_type,
                    "initial_value": initial_value[:50] if initial_value else None,
                    "scope": scope,
                    "is_exported": pattern_name == "export_var",
                    "is_onready": pattern_name == "onready_var",
                }

                # Check for node reference in onready
                if pattern_name == "onready_var" and initial_value:
                    dollar_match = self.PATTERNS["dollar_path"].search(initial_value)
                    if dollar_match:
                        metadata["node_path"] = dollar_match.group(1)

                return ParsedNode(
                    id=self.generate_node_id(NodeType.VARIABLE, file_path, var_name, line_num),
                    type=NodeType.VARIABLE,
                    name=var_name,
                    file_path=str(file_path),
                    line_number=line_num,
                    language="gdscript",
                    code_snippet=self.get_code_snippet(lines, line_num),
                    metadata=metadata
                )

        return None

    def _add_resource_reference(
        self,
        result: ParseResult,
        file_path: Path,
        source_id: str,
        res_path: str,
        line_num: int,
        lines: list[str],
        load_type: str
    ) -> None:
        """Add a resource reference node and edge."""
        node_id = self.generate_node_id(NodeType.RESOURCE, file_path, res_path.replace("/", "_"), line_num)

        result.nodes.append(ParsedNode(
            id=node_id,
            type=NodeType.RESOURCE,
            name=res_path.split("/")[-1],
            file_path=str(file_path),
            line_number=line_num,
            language="gdscript",
            code_snippet=self.get_code_snippet(lines, line_num),
            metadata={
                "resource_path": res_path,
                "load_type": load_type,
                "actual_path": str(self.convert_godot_path(res_path)) if res_path.startswith("res://") else None
            }
        ))

        result.edges.append(ParsedEdge(
            source_id=source_id,
            target_id=node_id,
            relationship=EdgeType.REFERENCES,
            context=f"{load_type}(\"{res_path}\") at line {line_num}"
        ))

    def _add_node_reference(
        self,
        result: ParseResult,
        file_path: Path,
        source_id: str,
        node_path: str,
        line_num: int,
        lines: list[str]
    ) -> None:
        """Add a node reference and edge."""
        node_id = self.generate_node_id(NodeType.NODE_REFERENCE, file_path, node_path.replace("/", "_"), line_num)

        result.nodes.append(ParsedNode(
            id=node_id,
            type=NodeType.NODE_REFERENCE,
            name=node_path.split("/")[-1],
            file_path=str(file_path),
            line_number=line_num,
            language="gdscript",
            code_snippet=self.get_code_snippet(lines, line_num),
            metadata={"node_path": node_path}
        ))

        result.edges.append(ParsedEdge(
            source_id=source_id,
            target_id=node_id,
            relationship=EdgeType.REFERENCES,
            context=f"${node_path} at line {line_num}"
        ))
