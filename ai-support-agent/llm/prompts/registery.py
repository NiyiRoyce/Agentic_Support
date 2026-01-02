"""Prompt registry for versioning and A/B testing."""

from typing import Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class PromptVersion(str, Enum):
    """Prompt versions for A/B testing."""
    V1 = "v1"
    V2 = "v2"
    STABLE = "stable"
    EXPERIMENTAL = "experimental"


@dataclass
class PromptMetadata:
    """Metadata for a prompt template."""
    name: str
    version: PromptVersion
    description: str
    created_at: str
    performance_metrics: Dict[str, float] = None


class PromptRegistry:
    """
    Registry for managing versioned prompts and A/B testing.
    """

    def __init__(self):
        self._prompts: Dict[str, Dict[str, Callable]] = {}
        self._metadata: Dict[str, Dict[str, PromptMetadata]] = {}
        self._active_versions: Dict[str, str] = {}

    def register(
        self,
        name: str,
        version: PromptVersion,
        template_func: Callable,
        description: str = "",
    ):
        """Register a prompt template."""
        if name not in self._prompts:
            self._prompts[name] = {}
            self._metadata[name] = {}

        self._prompts[name][version.value] = template_func
        self._metadata[name][version.value] = PromptMetadata(
            name=name,
            version=version,
            description=description,
            created_at="",  # Could use datetime.now()
        )

        # Set stable version as active by default
        if version == PromptVersion.STABLE:
            self._active_versions[name] = version.value

    def get(
        self,
        name: str,
        version: Optional[str] = None,
    ) -> Optional[Callable]:
        """Get prompt template by name and version."""
        if name not in self._prompts:
            return None

        # Use specified version or active version
        version_key = version or self._active_versions.get(name, PromptVersion.STABLE.value)

        return self._prompts[name].get(version_key)

    def set_active_version(self, name: str, version: str):
        """Set active version for a prompt."""
        if name in self._prompts and version in self._prompts[name]:
            self._active_versions[name] = version

    def get_metadata(self, name: str, version: str) -> Optional[PromptMetadata]:
        """Get metadata for a prompt."""
        if name in self._metadata and version in self._metadata[name]:
            return self._metadata[name][version]
        return None

    def list_prompts(self) -> Dict[str, list]:
        """List all registered prompts and their versions."""
        return {
            name: list(versions.keys())
            for name, versions in self._prompts.items()
        }

    def update_metrics(
        self,
        name: str,
        version: str,
        metrics: Dict[str, float],
    ):
        """Update performance metrics for a prompt version."""
        if name in self._metadata and version in self._metadata[name]:
            metadata = self._metadata[name][version]
            if metadata.performance_metrics is None:
                metadata.performance_metrics = {}
            metadata.performance_metrics.update(metrics)


# Global prompt registry instance
_registry = PromptRegistry()


def register_prompt(
    name: str,
    version: PromptVersion = PromptVersion.STABLE,
    description: str = "",
):
    """Decorator to register a prompt template."""
    def decorator(func: Callable):
        _registry.register(name, version, func, description)
        return func
    return decorator


def get_prompt(name: str, version: Optional[str] = None) -> Optional[Callable]:
    """Get a registered prompt template."""
    return _registry.get(name, version)


# Example usage:
# @register_prompt("intent_classification", PromptVersion.STABLE)
# def intent_classification_prompt(user_message: str) -> str:
#     return f"Classify: {user_message}"