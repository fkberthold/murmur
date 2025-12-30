from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TransformerIO:
    """Universal I/O container for all transformers."""
    data: dict = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)


@dataclass
class DataSource:
    """
    Standardized output from data source fetchers.

    Enables plugin-style architecture where:
    - Fetchers output DataSource objects
    - Planner consumes them generically without source-specific code
    - Each source provides its own prompt fragment describing how to use its data

    Attributes:
        name: Identifier for this source (e.g., "slack", "news", "github")
        data: Raw structured data from the source
        prompt_fragment_path: Path to markdown file describing how to interpret this data
    """
    name: str
    data: dict = field(default_factory=dict)
    prompt_fragment_path: Path | None = None


class Transformer(ABC):
    """
    Base class for all graph nodes.

    Subclasses must define:
    - name: str - unique identifier
    - inputs: list[str] - required input keys
    - outputs: list[str] - produced output keys
    - input_effects: list[str] - side effects consumed (e.g., ["llm", "http"])
    - output_effects: list[str] - side effects produced (e.g., ["filesystem", "tts"])
    """
    name: str
    inputs: list[str] = []
    outputs: list[str] = []
    input_effects: list[str] = []
    output_effects: list[str] = []

    @abstractmethod
    def process(self, input: TransformerIO) -> TransformerIO:
        """Transform input to output."""
        pass
