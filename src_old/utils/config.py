"""Configuration management."""
import os
import getpass
from pathlib import Path


class Config:
    """Application configuration."""
    
    def __init__(self):
        """Initialize configuration with defaults."""
        self.annotations_dir = os.getenv(
            "TATER_ANNOTATIONS_DIR",
            "./annotations"
        )
        self.annotations_file = os.getenv(
            "TATER_ANNOTATIONS_FILE",
            "annotations.json"
        )
        self.port = int(os.getenv("TATER_PORT", "8050"))
        self.debug = os.getenv("TATER_DEBUG", "False").lower() == "true"
        self.annotator = os.getenv("TATER_ANNOTATOR", getpass.getuser())
        
        # Ensure annotations directory exists
        Path(self.annotations_dir).mkdir(parents=True, exist_ok=True)
    
    @property
    def annotations_path(self) -> str:
        """Get full path to annotations file."""
        return os.path.join(self.annotations_dir, self.annotations_file)


# Global config instance
config = Config()
