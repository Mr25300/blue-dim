import os
from pathlib import Path
from platformdirs import user_data_path, user_config_path
from dotenv import load_dotenv, set_key
from configparser import ConfigParser

APP_NAME = "BlueDim"

class ConfigFileManager:
    env_path: Path
    settings_path: Path
    config_parser: ConfigParser

    def __init__(self):
        config_dir = user_config_path(APP_NAME)
        config_dir.mkdir(parents=True, exist_ok=True)

        self.env_path = config_dir / ".env"
        self.settings_path = config_dir / "settings.conf"
        self.config_parser = ConfigParser()
    
    def get_env_var(self, key: str, default=None):
        if not self.env_path.exists():
            self.env_path.touch()
        
        load_dotenv(dotenv_path=self.env_path)

        return os.getenv(key, default) or None
    
    def set_env_var(self, key: str, value: str):
        if not self.env_path.exists():
            self.env_path.touch()

        set_key(str(self.env_path), key, value)

    def get_setting(self, section: str, key: str):
        if not self.settings_path.exists():
            self.settings_path.touch()

        self.config_parser.read(self.settings_path)

        if self.config_parser.has_section(section) and self.config_parser.has_option(section, key):
            return self.config_parser.get(section, key)
        
        return None
    
    def set_setting(self, section: str, key: str, value: str):
        if not self.settings_path.exists():
            self.settings_path.touch()

        self.config_parser.read(self.settings_path)

        if not self.config_parser.has_section(section):
            self.config_parser.add_section(section)

        self.config_parser.set(section, key, value)

        with self.settings_path.open("w") as f:
            self.config_parser.write(f)

