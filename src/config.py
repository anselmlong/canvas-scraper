"""Configuration management for Canvas Scraper."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for Canvas Scraper."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.yaml file. Defaults to project root.
        """
        self.project_root = Path(__file__).parent.parent
        self.config_path = config_path or self.project_root / "config.yaml"
        self.env_path = self.project_root / ".env"

        # Load environment variables
        load_dotenv(self.env_path)

        # Load YAML config
        self.config = self._load_yaml_config()

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            return self._get_default_config()

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "canvas": {"base_url": ""},
            "download": {
                "base_path": "~/CanvasFiles",
                "max_file_size_mb": 50,
                "concurrent_downloads": 3,
            },
            "filters": {
                "extension_blacklist": [
                    ".mp4",
                    ".avi",
                    ".mov",
                    ".mkv",
                    ".webm",
                    ".flv",
                    ".wmv",
                    ".m4v",
                    ".mpeg",
                    ".mpg",
                    ".epub",
                    ".mobi",
                ],
                "name_patterns_to_skip": [
                    "textbook",
                    "ebook",
                    "full book",
                    "recording",
                    "lecture recording",
                    "video lecture",
                ],
                "pdf_max_size_mb": 30,
            },
            "courses": {"sync_mode": "whitelist", "whitelist": []},
            "notification": {
                "email": {
                    "enabled": True,
                    "recipient": "",
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "from_name": "Canvas Scraper",
                }
            },
            "scheduling": {"enabled": True, "cron_time": "12:00"},
        }

    def save(self):
        """Save current configuration to YAML file."""
        with open(self.config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)

    def get(self, key_path: str, default=None) -> Any:
        """Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., 'canvas.base_url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """Set configuration value by dot-separated path.

        Args:
            key_path: Dot-separated path (e.g., 'canvas.base_url')
            value: Value to set
        """
        keys = key_path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value
        """
        return os.getenv(key, default)

    def set_env(self, key: str, value: str):
        """Set environment variable and save to .env file.

        Args:
            key: Environment variable name
            value: Value to set
        """
        os.environ[key] = value

        # Update .env file
        env_lines = []
        key_found = False

        if self.env_path.exists():
            with open(self.env_path, "r") as f:
                for line in f:
                    if line.startswith(f"{key}="):
                        env_lines.append(f"{key}={value}\n")
                        key_found = True
                    else:
                        env_lines.append(line)

        if not key_found:
            env_lines.append(f"{key}={value}\n")

        with open(self.env_path, "w") as f:
            f.writelines(env_lines)

    @property
    def canvas_api_token(self) -> Optional[str]:
        """Get Canvas API token from environment."""
        return self.get_env("CANVAS_API_TOKEN")

    @property
    def canvas_base_url(self) -> str:
        """Get Canvas base URL."""
        return self.get("canvas.base_url", "")

    @property
    def download_path(self) -> Path:
        """Get download base path."""
        path = self.get("download.base_path", "~/CanvasFiles")
        return Path(path).expanduser()

    @property
    def email_username(self) -> Optional[str]:
        """Get email username from environment."""
        return self.get_env("EMAIL_USERNAME")

    @property
    def email_password(self) -> Optional[str]:
        """Get email password from environment."""
        return self.get_env("EMAIL_APP_PASSWORD")

    def is_configured(self) -> bool:
        """Check if minimum configuration is present."""
        return (
            bool(self.canvas_api_token)
            and bool(self.canvas_base_url)
            and len(self.get("courses.whitelist", [])) > 0
        )

    def validate(self) -> tuple[bool, list[str]]:
        """Validate configuration.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        if not self.canvas_api_token:
            errors.append("Canvas API token not set in .env file")

        if not self.canvas_base_url:
            errors.append("Canvas base URL not set in config.yaml")

        if not self.get("courses.whitelist"):
            errors.append("No courses selected for syncing")

        if self.get("notification.email.enabled"):
            if not self.email_username:
                errors.append("Email username not set in .env file")
            if not self.email_password:
                errors.append("Email app password not set in .env file")
            if not self.get("notification.email.recipient"):
                errors.append("Email recipient not set in config.yaml")

        return (len(errors) == 0, errors)
