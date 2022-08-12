from configparser import ConfigParser
from pathlib import Path


def load_configuration():
    system_config_path = Path("/etc") / "wave" / "wave.ini"
    user_config_path = Path.home() / "config" / "wave.ini"

    config = ConfigParser()
    if user_config_path.exists():
        config.read(user_config_path)
    elif system_config_path.exists():
        config.read(system_config_path)

    return config.get("config", {})
