from pathlib import Path
import tomlkit
import yaml
import os
import importlib
import logging
import logging.config  # Need to import, or I get an AttributeError?
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


def setup_experiment_path(exp_config: dict, exp_name: str) -> dict:
    """Set up paths for imaging & focusing."""

    # Get experiment name
    if len(exp_name) == 0:
        exp_name = exp_config["experiment"]["name"]
    if len(exp_name) == 0:
        exp_name = "PySeq_" + datetime.now().strftime("%Y%m%d")
    exp_config["experiment"]["name"] = exp_name
    # Setup paths output paths for images, logs, and focus data
    output_path = Path(exp_config["experiment"]["output_path"]) / exp_name
    paths = ["images", "focus", "log"]
    for p in paths:
        config_path = exp_config["experiment"][f"{p}_path"]
        if len(config_path) == 0:
            p_ = output_path / p
        else:
            p_ = Path(config_path) / exp_name / p
        p_.mkdir(parents=True, exist_ok=True)
        exp_config["experiment"][f"{p}_path"] = str(p_)

    # Update logger configuration
    exp_config["logging"]["handlers"]["fileHandler"]["filename"] = (
        f"{p_}/{exp_name}.log"
    )
    return exp_config


def update_logger(logger_conf: dict, rotating: bool = False):
    if rotating:
        # Remove FileHandler if running tests or idleing
        del logger_conf["handlers"]["fileHandler"]
        logger_conf["loggers"]["PySeq"]["handlers"].append("rotatingHandler")
    else:
        # Remove RotatingFileHandler during experiment runs
        del logger_conf["handlers"]["rotatingHandler"]
        logger_conf["loggers"]["PySeq"]["handlers"].append("fileHandler")
    # Need to import logging.config ?
    logging.config.dictConfig(logger_conf)
