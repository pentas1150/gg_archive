from dataclasses import dataclass


@dataclass
class VersionConfig:
    """Version configuration."""
    version: str = "1.0.1"
