from typing import Type
from murmur.core import Transformer


class TransformerRegistry:
    """Registry for transformer classes."""

    def __init__(self):
        self._transformers: dict[str, Transformer] = {}

    def register(self, transformer_class: Type[Transformer]) -> None:
        """Register a transformer class."""
        instance = transformer_class()
        self._transformers[instance.name] = instance

    def get(self, name: str) -> Transformer:
        """Get a transformer by name."""
        if name not in self._transformers:
            raise KeyError(f"Unknown transformer: '{name}'")
        return self._transformers[name]

    def list_all(self) -> list[str]:
        """List all registered transformer names."""
        return list(self._transformers.keys())
