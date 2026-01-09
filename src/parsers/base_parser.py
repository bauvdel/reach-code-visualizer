"""Base parser class and data models for code analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Optional
import hashlib


class NodeType(Enum):
    """Types of nodes in the code graph."""
    FUNCTION = auto()
    VARIABLE = auto()
    SIGNAL = auto()
    SIGNAL_CONNECTION = auto()
    SCENE = auto()
    CLASS = auto()
    NODE_REFERENCE = auto()
    RESOURCE = auto()
    API_CALL = auto()
    MODULE = auto()
    AMBIGUOUS = auto()


class EdgeType(Enum):
    """Types of relationships between nodes."""
    CALLS = auto()
    CALLED_BY = auto()
    READS = auto()
    WRITES = auto()
    EMITS = auto()
    CONNECTS_TO = auto()
    INSTANTIATES = auto()
    INHERITS = auto()
    REFERENCES = auto()
    IMPORTS = auto()
    DATA_FLOW = auto()
    CONTAINS = auto()
    ATTACHES_TO = auto()


class Confidence(Enum):
    """Confidence level for parsed relationships."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AMBIGUOUS = "ambiguous"


@dataclass
class ParsedNode:
    """Represents a parsed code element (function, variable, signal, etc.)."""
    id: str
    type: NodeType
    name: str
    file_path: str
    line_number: int
    language: str
    code_snippet: str = ""
    metadata: dict = field(default_factory=dict)
    confidence: Confidence = Confidence.HIGH

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.name,
            "name": self.name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "language": self.language,
            "code_snippet": self.code_snippet,
            "metadata": self.metadata,
            "confidence": self.confidence.value
        }


@dataclass
class ParsedEdge:
    """Represents a relationship between two code elements."""
    source_id: str
    target_id: str
    relationship: EdgeType
    context: str = ""
    metadata: dict = field(default_factory=dict)
    confidence: Confidence = Confidence.HIGH

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship.name,
            "context": self.context,
            "metadata": self.metadata,
            "confidence": self.confidence.value
        }


@dataclass
class ParseResult:
    """Result of parsing a file."""
    file_path: str
    file_hash: str
    nodes: list[ParsedNode] = field(default_factory=list)
    edges: list[ParsedEdge] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if parsing was successful (no critical errors)."""
        return len(self.errors) == 0

    @property
    def node_count(self) -> int:
        """Number of nodes parsed."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges parsed."""
        return len(self.edges)


class BaseParser(ABC):
    """Base class for all language-specific parsers."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    @abstractmethod
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a single file and return nodes and edges."""
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of file extensions this parser handles."""
        pass

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the given file."""
        return file_path.suffix.lower() in self.supported_extensions()

    def generate_node_id(
        self,
        node_type: NodeType,
        file_path: Path,
        name: str,
        line_number: int
    ) -> str:
        """Generate a unique ID for a node.

        Format: {type}_{file_stem}_{name}_{line}
        """
        # Normalize file path relative to project root
        try:
            rel_path = file_path.relative_to(self.project_root)
        except ValueError:
            rel_path = file_path

        # Create safe file identifier
        file_id = str(rel_path).replace("\\", "/").replace("/", "_").replace(".", "_")

        # Create safe name identifier
        safe_name = name.replace(".", "_").replace("/", "_").replace(" ", "_")

        return f"{node_type.name.lower()}_{file_id}_{safe_name}_{line_number}"

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of file contents for change detection."""
        try:
            content = file_path.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""

    def get_code_snippet(
        self,
        lines: list[str],
        line_number: int,
        context_lines: int = 2
    ) -> str:
        """Extract code snippet around a specific line.

        Args:
            lines: All lines of the file
            line_number: 1-based line number
            context_lines: Number of lines before/after to include

        Returns:
            Code snippet with surrounding context
        """
        idx = line_number - 1  # Convert to 0-based
        start = max(0, idx - context_lines)
        end = min(len(lines), idx + context_lines + 1)

        snippet_lines = lines[start:end]
        return "\n".join(snippet_lines)

    def get_relative_path(self, file_path: Path) -> str:
        """Get path relative to project root as string."""
        try:
            return str(file_path.relative_to(self.project_root)).replace("\\", "/")
        except ValueError:
            return str(file_path).replace("\\", "/")

    def convert_godot_path(self, godot_path: str) -> Optional[Path]:
        """Convert Godot res:// path to actual file path.

        Args:
            godot_path: Path like 'res://scripts/player.gd'

        Returns:
            Absolute Path or None if invalid
        """
        if not godot_path.startswith("res://"):
            return None

        relative_path = godot_path[6:]  # Remove 'res://'
        return self.project_root / relative_path
