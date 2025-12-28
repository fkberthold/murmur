from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TransformerIO:
    """Universal I/O container for all transformers."""
    data: dict = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)
