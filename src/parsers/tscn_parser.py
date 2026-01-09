"""TSCN (Godot Scene) parser for extracting scene structure and relationships."""

import re
from dataclasses import dataclass, field
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
class ExtResource:
    """Represents an external resource reference in a TSCN file."""
    id: str
    type: str
    path: str
    uid: Optional[str] = None


@dataclass
class SceneNode:
    """Represents a node in the scene tree."""
    name: str
    type: str
    parent: Optional[str] = None
    instance: Optional[str] = None  # ExtResource ID for instanced scenes
    script: Optional[str] = None  # ExtResource ID for attached script
    properties: dict = field(default_factory=dict)
    line_number: int = 0


class TSCNParser(BaseParser):
    """Parser for Godot scene files (.tscn)."""

    # Regex patterns for TSCN format
    PATTERNS = {
        # Scene header
        "scene_header": re.compile(
            r'\[gd_scene\s+load_steps=(\d+)\s+format=(\d+)(?:\s+uid="([^"]+)")?\]'
        ),

        # External resources
        "ext_resource": re.compile(
            r'\[ext_resource\s+type="([^"]+)"(?:\s+uid="([^"]+)")?\s+path="([^"]+)"\s+id="([^"]+)"\]'
        ),
        # Alternative format (type at end)
        "ext_resource_alt": re.compile(
            r'\[ext_resource\s+path="([^"]+)"\s+type="([^"]+)"\s+id="([^"]+)"\]'
        ),

        # Sub-resources (internal)
        "sub_resource": re.compile(
            r'\[sub_resource\s+type="([^"]+)"\s+id="([^"]+)"\]'
        ),

        # Node definitions
        "node": re.compile(
            r'\[node\s+name="([^"]+)"\s+type="([^"]+)"(?:\s+parent="([^"]*)")?\]'
        ),
        "node_instance": re.compile(
            r'\[node\s+name="([^"]+)"(?:\s+parent="([^"]*)")?\s+instance=ExtResource\("([^"]+)"\)\]'
        ),
        "node_instance_alt": re.compile(
            r'\[node\s+name="([^"]+)"\s+instance=ExtResource\("([^"]+)"\)(?:\s+parent="([^"]*)")?\]'
        ),

        # Script attachment
        "script_attach": re.compile(
            r'script\s*=\s*ExtResource\("([^"]+)"\)'
        ),

        # Signal connections
        "connection": re.compile(
            r'\[connection\s+signal="([^"]+)"\s+from="([^"]+)"\s+to="([^"]+)"\s+method="([^"]+)"\]'
        ),
        # Connection with flags
        "connection_flags": re.compile(
            r'\[connection\s+signal="([^"]+)"\s+from="([^"]+)"\s+to="([^"]+)"\s+method="([^"]+)"\s+flags=(\d+)\]'
        ),

        # Property assignments
        "property": re.compile(
            r'^(\w+)\s*=\s*(.+)$'
        ),

        # ExtResource reference in properties
        "ext_resource_ref": re.compile(
            r'ExtResource\("([^"]+)"\)'
        ),
    }

    def supported_extensions(self) -> list[str]:
        return [".tscn"]

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a TSCN scene file and extract structure and relationships."""
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

        # Parse state
        ext_resources: dict[str, ExtResource] = {}
        scene_nodes: list[SceneNode] = []
        current_node: Optional[SceneNode] = None
        scene_uid: Optional[str] = None

        # Create scene node for the file itself
        scene_name = file_path.stem
        scene_node_id = self.generate_node_id(NodeType.SCENE, file_path, scene_name, 1)

        result.nodes.append(ParsedNode(
            id=scene_node_id,
            type=NodeType.SCENE,
            name=scene_name,
            file_path=str(file_path),
            line_number=1,
            language="scene",
            code_snippet=lines[0] if lines else "",
            metadata={
                "scene_path": self.get_relative_path(file_path),
                "godot_path": f"res://{self.get_relative_path(file_path)}"
            }
        ))

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if not stripped:
                continue

            # Scene header
            match = self.PATTERNS["scene_header"].match(stripped)
            if match:
                scene_uid = match.group(3)
                result.nodes[0].metadata["uid"] = scene_uid
                result.nodes[0].metadata["load_steps"] = int(match.group(1))
                result.nodes[0].metadata["format"] = int(match.group(2))
                continue

            # External resources
            match = self.PATTERNS["ext_resource"].match(stripped)
            if match:
                res_type = match.group(1)
                res_uid = match.group(2)
                res_path = match.group(3)
                res_id = match.group(4)

                ext_resources[res_id] = ExtResource(
                    id=res_id,
                    type=res_type,
                    path=res_path,
                    uid=res_uid
                )
                continue

            # Alternative ext_resource format
            match = self.PATTERNS["ext_resource_alt"].match(stripped)
            if match:
                res_path = match.group(1)
                res_type = match.group(2)
                res_id = match.group(3)

                ext_resources[res_id] = ExtResource(
                    id=res_id,
                    type=res_type,
                    path=res_path
                )
                continue

            # Node definitions
            match = self.PATTERNS["node"].match(stripped)
            if match:
                node_name = match.group(1)
                node_type = match.group(2)
                parent = match.group(3)

                current_node = SceneNode(
                    name=node_name,
                    type=node_type,
                    parent=parent if parent else None,
                    line_number=line_num
                )
                scene_nodes.append(current_node)
                continue

            # Node instances
            match = self.PATTERNS["node_instance"].match(stripped) or self.PATTERNS["node_instance_alt"].match(stripped)
            if match:
                groups = match.groups()
                # Handle both orderings
                if len(groups) == 3:
                    if groups[1] and groups[1].startswith("res://"):
                        # Alt format: name, instance, parent
                        node_name = groups[0]
                        instance_id = groups[1]
                        parent = groups[2]
                    else:
                        # Standard format: name, parent, instance
                        node_name = groups[0]
                        parent = groups[1]
                        instance_id = groups[2]
                else:
                    node_name = groups[0]
                    parent = groups[1] if len(groups) > 1 else None
                    instance_id = groups[2] if len(groups) > 2 else None

                current_node = SceneNode(
                    name=node_name,
                    type="(instance)",
                    parent=parent if parent else None,
                    instance=instance_id,
                    line_number=line_num
                )
                scene_nodes.append(current_node)
                continue

            # Script attachment (inside node properties)
            if current_node:
                match = self.PATTERNS["script_attach"].search(stripped)
                if match:
                    current_node.script = match.group(1)
                    continue

                # Other properties
                match = self.PATTERNS["property"].match(stripped)
                if match and not stripped.startswith("["):
                    prop_name = match.group(1)
                    prop_value = match.group(2)
                    current_node.properties[prop_name] = prop_value

            # Signal connections
            match = self.PATTERNS["connection"].match(stripped) or self.PATTERNS["connection_flags"].match(stripped)
            if match:
                signal_name = match.group(1)
                from_node = match.group(2)
                to_node = match.group(3)
                method_name = match.group(4)

                # Create connection node
                conn_id = self.generate_node_id(
                    NodeType.SIGNAL_CONNECTION,
                    file_path,
                    f"{from_node}_{signal_name}_to_{method_name}",
                    line_num
                )

                result.nodes.append(ParsedNode(
                    id=conn_id,
                    type=NodeType.SIGNAL_CONNECTION,
                    name=f"{from_node}.{signal_name} -> {to_node}.{method_name}",
                    file_path=str(file_path),
                    line_number=line_num,
                    language="scene",
                    code_snippet=stripped,
                    metadata={
                        "signal": signal_name,
                        "from_node": from_node,
                        "to_node": to_node,
                        "method": method_name,
                        "defined_in_scene": True
                    }
                ))

                # Connection belongs to this scene
                result.edges.append(ParsedEdge(
                    source_id=scene_node_id,
                    target_id=conn_id,
                    relationship=EdgeType.CONTAINS,
                    context=f"Scene connection at line {line_num}"
                ))

        # Process scene nodes to create graph nodes and edges
        for scene_node in scene_nodes:
            node_id = self.generate_node_id(
                NodeType.NODE_REFERENCE,
                file_path,
                scene_node.name,
                scene_node.line_number
            )

            # Determine actual type for instances
            actual_type = scene_node.type
            instanced_scene_path = None

            if scene_node.instance and scene_node.instance in ext_resources:
                ext_res = ext_resources[scene_node.instance]
                instanced_scene_path = ext_res.path
                actual_type = f"instance of {ext_res.path.split('/')[-1]}"

            result.nodes.append(ParsedNode(
                id=node_id,
                type=NodeType.NODE_REFERENCE,
                name=scene_node.name,
                file_path=str(file_path),
                line_number=scene_node.line_number,
                language="scene",
                code_snippet=f"[node name=\"{scene_node.name}\" type=\"{scene_node.type}\"]",
                metadata={
                    "node_type": scene_node.type,
                    "parent_path": scene_node.parent,
                    "is_instance": scene_node.instance is not None,
                    "instanced_scene": instanced_scene_path,
                    "properties": scene_node.properties
                }
            ))

            # Edge: Scene contains this node
            result.edges.append(ParsedEdge(
                source_id=scene_node_id,
                target_id=node_id,
                relationship=EdgeType.CONTAINS,
                context=f"Node in scene tree"
            ))

            # Edge: Script attachment
            if scene_node.script and scene_node.script in ext_resources:
                script_res = ext_resources[scene_node.script]
                script_path = script_res.path

                # Create resource node for the script
                script_node_id = self.generate_node_id(
                    NodeType.RESOURCE,
                    file_path,
                    script_path.replace("/", "_"),
                    scene_node.line_number
                )

                result.nodes.append(ParsedNode(
                    id=script_node_id,
                    type=NodeType.RESOURCE,
                    name=script_path.split("/")[-1],
                    file_path=str(file_path),
                    line_number=scene_node.line_number,
                    language="scene",
                    code_snippet="",
                    metadata={
                        "resource_path": script_path,
                        "resource_type": "Script",
                        "attached_to_node": scene_node.name
                    }
                ))

                result.edges.append(ParsedEdge(
                    source_id=node_id,
                    target_id=script_node_id,
                    relationship=EdgeType.ATTACHES_TO,
                    context=f"Script attached to {scene_node.name}"
                ))

            # Edge: Scene instantiation
            if instanced_scene_path:
                instanced_node_id = self.generate_node_id(
                    NodeType.RESOURCE,
                    file_path,
                    instanced_scene_path.replace("/", "_"),
                    scene_node.line_number
                )

                result.nodes.append(ParsedNode(
                    id=instanced_node_id,
                    type=NodeType.RESOURCE,
                    name=instanced_scene_path.split("/")[-1],
                    file_path=str(file_path),
                    line_number=scene_node.line_number,
                    language="scene",
                    code_snippet="",
                    metadata={
                        "resource_path": instanced_scene_path,
                        "resource_type": "PackedScene",
                        "instanced_as": scene_node.name
                    }
                ))

                result.edges.append(ParsedEdge(
                    source_id=scene_node_id,
                    target_id=instanced_node_id,
                    relationship=EdgeType.INSTANTIATES,
                    context=f"Scene instances {instanced_scene_path}"
                ))

        # Create external resource references
        for ext_id, ext_res in ext_resources.items():
            # Skip scripts (already handled above)
            if ext_res.type == "Script":
                continue

            res_node_id = self.generate_node_id(
                NodeType.RESOURCE,
                file_path,
                f"ext_{ext_id}_{ext_res.path.replace('/', '_')}",
                1
            )

            result.nodes.append(ParsedNode(
                id=res_node_id,
                type=NodeType.RESOURCE,
                name=ext_res.path.split("/")[-1],
                file_path=str(file_path),
                line_number=1,
                language="scene",
                code_snippet="",
                metadata={
                    "resource_path": ext_res.path,
                    "resource_type": ext_res.type,
                    "ext_resource_id": ext_id,
                    "uid": ext_res.uid
                }
            ))

            result.edges.append(ParsedEdge(
                source_id=scene_node_id,
                target_id=res_node_id,
                relationship=EdgeType.REFERENCES,
                context=f"External resource: {ext_res.type}"
            ))

        return result
