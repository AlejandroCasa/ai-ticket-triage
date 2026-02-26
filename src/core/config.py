import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Initialize logger
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads the YAML configuration file from the project root.

    Args:
        config_path (str): Relative path to the config file.

    Returns:
        Dict[str, Any]: The configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        yaml.YAMLError: If the file contains invalid YAML.
    """
    # Resolve the absolute path to ensure we find the file regardless of execution context
    # We assume config.yaml is in the project root (2 levels up from src/core/config.py? 
    # No, usually run from root. Let's make it robust).

    # Strategy: Look in the current working directory first (Best for Docker/Root run)
    path = Path(config_path)

    if not path.exists():
        # Fallback: Try to find it relative to this file (useful during dev/testing)
        base_dir = Path(__file__).resolve().parent.parent.parent
        path = base_dir / config_path

    if not path.exists():
        logger.critical(f"Configuration file not found at: {path.absolute()}")
        raise FileNotFoundError(f"Config file '{config_path}' is missing.")

    try:
        with open(path, "r") as file:
            config = yaml.safe_load(file)
            logger.info(f"Configuration loaded successfully from {path}")
            return config

    except yaml.YAMLError as e:
        logger.critical(f"Error parsing YAML configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error loading config: {e}")
        sys.exit(1)

def get_categories(config: Dict[str, Any]) -> List[str]:
    """
    Helper to extract categories safely.
    """
    try:
        return config["triage"]["categories"]
    except KeyError:
        logger.critical("Invalid Config: 'triage.categories' key is missing.")
        sys.exit(1)