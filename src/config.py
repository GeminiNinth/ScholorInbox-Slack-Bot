"""Configuration management module."""

import os
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from .models import Config
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration from YAML and environment variables."""
    
    def __init__(self, config_path: str = "config.yaml", env_path: str = ".env"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to config.yaml file
            env_path: Path to .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        
        # Load environment variables
        if self.env_path.exists():
            load_dotenv(self.env_path)
            logger.info(f"Loaded environment variables from {self.env_path}")
        else:
            logger.warning(f".env file not found at {self.env_path}")
        
        # Load YAML configuration
        self.config = self._load_config()
        
        # Validate required environment variables
        self._validate_env_vars()
    
    def _load_config(self) -> Config:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return Config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            logger.info(f"Loaded configuration from {self.config_path}")
            return Config(**config_dict)
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            raise
    
    def _validate_env_vars(self):
        """Validate required environment variables."""
        required_vars = [
            "SCHOLAR_INBOX_SECRET_URL",
            "SLACK_BOT_TOKEN",
            "SLACK_CHANNEL_ID"
        ]
        
        # Check LLM provider API key
        llm_provider = self.config.llm.provider
        if llm_provider == "openai":
            required_vars.append("OPENAI_API_KEY")
        elif llm_provider == "anthropic":
            required_vars.append("ANTHROPIC_API_KEY")
        elif llm_provider == "google":
            required_vars.append("GOOGLE_API_KEY")
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("All required environment variables are set")
    
    def get_scholar_inbox_url(self) -> str:
        """Get Scholar Inbox secret URL."""
        return os.getenv("SCHOLAR_INBOX_SECRET_URL", "")
    
    def get_slack_token(self) -> str:
        """Get Slack bot token."""
        return os.getenv("SLACK_BOT_TOKEN", "")
    
    def get_slack_channel_id(self) -> str:
        """Get Slack channel ID."""
        return os.getenv("SLACK_CHANNEL_ID", "")
    
    def get_llm_api_key(self) -> str:
        """Get LLM API key based on configured provider."""
        provider = self.config.llm.provider
        if provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        elif provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY", "")
        elif provider == "google":
            return os.getenv("GOOGLE_API_KEY", "")
        return ""
    
    def get_config(self) -> Config:
        """Get the loaded configuration object."""
        return self.config
