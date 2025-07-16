from pathlib import Path
import tomlkit
import yaml
import os
import importlib
import logging
import datetime

LOGGER = logging.getLogger("PySeq")

# Local machine specific settings
MACHINE_SETTINGS_PATH = Path.home() / ".config/pyseq2500/machine_settings.yaml"
if not MACHINE_SETTINGS_PATH.exists():
    # Use settings from package if local machine setting do not exist
    MACHINE_SETTINGS_PATH = importlib.resources.files("pyseq_core").joinpath(
        "resources/machine_settings.yaml"
    )

with open(MACHINE_SETTINGS_PATH, "r") as f:
    all_settings = yaml.safe_load(f)  # Machine config
    machine_name = all_settings["name"]
    HW_CONFIG = all_settings[machine_name]

# Default settings for experiment/software
machine_name = machine_name.lower()
if os.environ.get("PYTEST_VERSION") is not None and (
    "test" not in machine_name or "virtual" not in machine_name
):
    LOGGER.info("Using package default.toml")
    # use default experiment config and machine settings from package resources
    resource_path = importlib.resources.files("pyseq_core")
    DEFAULT_CONFIG_PATH = resource_path.joinpath("resources/default.toml")
    MACHINE_SETTINGS_PATH = resource_path.joinpath("resources/machine_settings.yaml")

    # override HW_CONFIG with package resource
    with open(MACHINE_SETTINGS_PATH, "r") as f:
        LOGGER.info("Using package machine_settings.yaml")
        all_settings = yaml.safe_load(f)  # Machine config
        machine_name = all_settings["name"]
        HW_CONFIG = all_settings[machine_name]
else:
    # use default experiment config and machine settings from local machine
    DEFAULT_CONFIG_PATH = Path.home() / ".config/pyseq2500/default.toml"


# Read default config and machine settings
DEFAULT_CONFIG = tomlkit.parse(open(DEFAULT_CONFIG_PATH).read())


def deep_merge(src_dict, dst_dict):
    """Recursive dict merge."""

    for k, v in src_dict.items():
        if k in dst_dict and isinstance(dst_dict[k], dict) and isinstance(v, dict):
            deep_merge(src_dict[k], dst_dict[k])
        else:
            dst_dict[k] = v

    return dst_dict


def setup_experiment_path(exp_config: dict) -> dict:
    """Set up paths for imaging & focusing."""

    # Get experiment name, image path, and log path
    exp_name = exp_config["experiment"]["name"]
    if len(exp_name) == 0:
        exp_name = "PySeq_" + datetime.now().strftime("%Y%m%d")
    output_path = Path(exp_config["experiment"]["output_path"]) / exp_name
    image_path = output_path / exp_config["experiment"]["image_path"]
    log_path = output_path / exp_config["experiment"]["log_path"]
    # Allow custom focus path with default = output_path / focus
    focus_path = exp_config["experiment"]["focus_path"]
    if len(focus_path) == 0:
        focus_path = output_path / "focus"
    else:
        focus_path = Path(focus_path)
    # Make paths
    image_path.mkdir(parents=True, exist_ok=True)
    focus_path.mkdir(parents=True, exist_ok=True)
    log_path.mkdir(parents=True, exist_ok=True)
    # Update config file
    exp_config["experiment"]["name"] = exp_name
    exp_config["experiment"]["image_path"] = str(image_path)
    exp_config["experiment"]["focus_path"] = str(focus_path)
    exp_config["experiment"]["log_path"] = str(log_path)

    return exp_config
