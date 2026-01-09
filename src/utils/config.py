"""Configuration management for REACH Code Visualizer."""

from pathlib import Path
from typing import Any, Optional
import yaml


class Config:
    """Configuration manager with lazy loading and defaults."""

    _instance: Optional["Config"] = None
    _config: dict = {}

    DEFAULT_CONFIG = {
        "project": {
            "root_path": "F:/Reach",
            "name": "REACH"
        },
        "parsing": {
            "include_patterns": ["**/*.gd", "**/*.tscn", "**/*.ts"],
            "exclude_patterns": ["**/node_modules/**", "**/.godot/**", "**/build/**", "**/.git/**"],
            "gdscript": {"parse_comments": True, "extract_docstrings": True}
        },
        "analysis": {
            "high_confidence": 0.9,
            "medium_confidence": 0.6,
            "low_confidence": 0.3,
            "max_path_depth": 10
        },
        "logging": {
            "level": "INFO",
            "file": "./logs/visualizer.log"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: Optional[Path] = None) -> None:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value using dot notation (e.g., 'project.root_path')."""
        if not self._config:
            self.load()

        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                # Try default config
                default_value = self.DEFAULT_CONFIG
                for dk in keys:
                    if isinstance(default_value, dict) and dk in default_value:
                        default_value = default_value[dk]
                    else:
                        return default
                return default_value

        return value

    @property
    def project_root(self) -> Path:
        """Get project root path."""
        return Path(self.get("project.root_path", "F:/Reach"))

    @property
    def include_patterns(self) -> list:
        """Get file include patterns."""
        return self.get("parsing.include_patterns", ["**/*.gd", "**/*.tscn"])

    @property
    def exclude_patterns(self) -> list:
        """Get file exclude patterns."""
        return self.get("parsing.exclude_patterns", [])


# Global config instance
config = Config()
